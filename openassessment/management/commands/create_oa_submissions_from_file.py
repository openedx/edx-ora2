"""
Management command to create submissions, assessments, and locks to make testing easier.
"""
import logging
import json
from os.path import exists, join

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

from opaque_keys.edx.keys import CourseKey

import loremipsum
from submissions import api as sub_api
from openassessment.assessment.api import staff as staff_api
from openassessment.runtime_imports.functions import anonymous_id_for_user, modulestore
from openassessment.workflow import api as workflow_api
from openassessment.xblock.utils.data_conversion import create_rubric_dict
from openassessment.staffgrader.models import SubmissionGradingLock

log = logging.getLogger('create_oa_submissions_from_file')

SUPERUSER_USERNAME = 'edx'

EPILOG = """
{
    "displayName": <Display Name for the target ORA>,
    "submissions": [
        {
            "username": <Username of submitter>,
            "lockOwner": <Username of lock owner, or null for no lock>,
            "gradeData":{
                "gradedBy": <Username of grader>,
                "overallFeedback": <Overall feedback>,
                "criteria": [ # Note: There must be a criterion for all criteria in the ORA rubric
                    {
                        "label": <Criterion label>,
                        "selectedOption": <label of selected option for this criterion>,
                        "feedback": <feedback for criterion>,
                    },
                    ...
                ]
            }
        },
        ...
    ]
}

The input file can be a single JSON object describing a single ORA or it can be a list of multiple objects
describing multiple ORAs in one course. If you have multiple ORAs specified, they must have unique display
names or the command won't know which is which. Also, any ORA display name must be unique *withon the course*.
Display name is the only way we currently identify blocks in this command so there bust be uniqueness.

Unfortunately due to how argparse works this will have no formatting on the command line, check this management
command's source for a formatted version.
"""


def generate_lorem_sentences(num_sentences=4):
    """
    Generate some number of sentences of lorem ipsum
    """
    sentences = [generate_lorem_sentence() for _ in range(num_sentences)]
    return " ".join(sentences)


def generate_lorem_sentence():
    """
    Generate a sentence of lorem ipsum. The loremipsum library is broken and returns things like
    "B'lorem' b'ipsum' b'next' b'nextword'."
    This just trims off the byte string markers that we're getting.
    """
    result = []
    lorem_sentence = loremipsum.get_sentence().split()
    for word in lorem_sentence:
        if word[-1] != "'":
            end_trim_index = len(word) - 2
        else:
            end_trim_index = len(word) - 1
        result.append(word[2:end_trim_index])
    return " ".join(result) + '.'


class Command(BaseCommand):
    """
    Management command to create submissions, assessments, and locks to make testing easier.
    """

    CONFIG_FILE_LOCATION_BASE = join('/', 'edx', 'src', 'edx-ora2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username_to_anonymous_user_id = None
        self.display_name_to_block = None

    def add_arguments(self, parser):
        parser.add_argument(
            'course_id',
            type=CourseKey.from_string,
            help='The id of the course for which to create submissions'
        )
        parser.add_argument(
            'submissions_config_file_path',
            help=(
                'The path to the file describing the format and structure of the submissions and assessments to '
                'generate. The path should be relative from the the ora2 src directory. Input files should be placed '
                'somewhere in WORKSPACE_ROOT/src/edx-ora2/ on local disk, which corresponds to /edx/src/edx-ora2 in '
                'the edx-platform docker container. \n For file format, call this management command with --help to '
                'view a description of the file format.'
            )
        )
        modes_group = parser.add_mutually_exclusive_group(required=True)
        modes_group.add_argument(
            '--init',
            action='store_true',
            help='Create and enroll users, create submissions, assessments, and locks.'
        )
        modes_group.add_argument(
            '--reset',
            action='store_true',
            help='Clear all ORA submission state from the given course.'
        )
        modes_group.add_argument(
            '--submit',
            action='store_true',
            help='Create submissions, assessments, and locks.'
        )
        parser.epilog = EPILOG

    def handle(self, *args, **options):
        """
        Run the command. Do additional arg checking, parse and load the input file,
        do up-front loading, and then do either init, reset, or submit.
        """
        course_id = options['course_id']
        submissions_config = self.read_config_file(options['submissions_config_file_path'])
        if options['init']:
            self.init_ora_test_data(course_id, submissions_config)

        # We have to do the init first because otherwise the users won't exist, and we won't
        # be able to look up their anonymous ids.
        self.load_anonymous_ids_and_block_locations(course_id, submissions_config)

        if options['reset']:
            self.reset_ora_test_data(course_id, submissions_config)
        elif options['submit'] or options['init']:
            self.submit_ora_test_data(course_id, submissions_config)

    def read_config_file(self, file_path):
        """
        Check that the input file exits, and attempt to open and json parse the file.
        Returns the json parsed input file.
        """
        file_path = join(self.CONFIG_FILE_LOCATION_BASE, file_path)
        if not exists(file_path):
            raise CommandError(f'File {file_path} not found.')

        with open(file_path, 'r') as f:
            try:
                submissions_config = json.load(f)
                if not isinstance(submissions_config, list):
                    submissions_config = [submissions_config]
                return submissions_config
            except json.JSONDecodeError as e:
                raise CommandError(f'Unable to parse file {file_path}: {e}') from e

    def load_anonymous_ids_and_block_locations(self, course_id, submissions_config):
        """
        Do all upfront database and modulestore lookups.
        Look up anonymous user ids and grab ORA blocks from the modulestore.
        """
        learners, course_staff = self.get_usernames(submissions_config)
        self.load_anonymous_user_ids(course_id, learners | course_staff)

        ora_display_names = self.get_display_names(submissions_config)
        self.load_ora_blocks(course_id, ora_display_names)

    def get_usernames(self, submissions_config):
        """
        Go through the submissions config and gather all usernames into two sets:
        -usernames of people who submitted (learners)
        -usernames mentioned in the file as graders or lock owners (course staff)
        """
        learners = set()
        course_staff = set()
        for ora_config in submissions_config:
            for submission in ora_config['submissions']:
                learners.add(submission['username'])
                if submission['gradeData']:
                    course_staff.add(submission['gradeData']['gradedBy'])
                if submission['lockOwner'] is not None:
                    course_staff.add(submission['lockOwner'])

        return learners, course_staff

    def load_anonymous_user_ids(self, course_id, usernames):
        """
        Look up all Users with the given usernames, look up their anonymous user ids for the specified course, and
        store a mapping from username to anonaymous id in self.username_to_anonymous_user_id
        """
        # Also include a superuser because when we reset we need to include a "reset by" anonymous id
        usernames.add(SUPERUSER_USERNAME)

        anonymous_user_ids = {}
        users = get_user_model().objects.filter(username__in=usernames).all()
        for user in users:
            anonymous_user_ids[user.username] = anonymous_id_for_user(user=user, course_id=course_id)

        missing_usernames = set(usernames) - set(anonymous_user_ids.keys())
        if missing_usernames:
            raise CommandError("Unable to load anonymous id for user(s) " + ' '.join(missing_usernames))

        self.username_to_anonymous_user_id = anonymous_user_ids

    def get_display_names(self, submissions_config):
        """
        Returns a list of all ORA display names mentioned in the submissions config
        """
        display_names = []
        for ora_config in submissions_config:
            display_name = ora_config['displayName']
            if display_name in display_names:
                raise CommandError('Duplicate ORA display name found in configuration file: ' + display_name)
            display_names.append(display_name)
        return display_names

    def _load_ora_blocks_from_modulestore(self, course_id):
        """
        Look up openassessment blocks for the course from the modulestore
        """
        try:
            return modulestore().get_items(
                course_id, qualifiers={'category': 'openassessment'}
            )
        except ModuleNotFoundError as e:
            raise CommandError((
                "Cannot import xmodule.modulestore.django.modulestore. "
                "This management command must be run from the LMS shell."
            )) from e

    def load_ora_blocks(self, course_id, display_names):
        """
        Look up openassessment blocks for the course from the modulestore, and save the ones that match the given
        display names in a dict mapping from display name to block in self.display_name_to_block
        """
        openassessment_blocks = self._load_ora_blocks_from_modulestore(course_id)
        display_name_to_block = {}
        for block in openassessment_blocks:
            if block.parent is not None and block.display_name in display_names:
                if block.display_name in display_name_to_block:
                    raise CommandError((
                        f"The ORA '{block.display_name}' is specified in the input file. "
                        "The course contains more than one ORA with that display name. "
                        f"First two found:  [{display_name_to_block[block.display_name].location}, {block.location}]"
                    ))
                display_name_to_block[block.display_name] = block

        missing_display_names = set(display_names) - set(display_name_to_block.keys())
        if missing_display_names:
            raise CommandError(
                f"The following Display Name(s) were not found in {str(course_id)} {', '.join(missing_display_names)}"
            )
        self.display_name_to_block = display_name_to_block

    def init_ora_test_data(self, course_id, submissions_config):
        """
        Run the initialization. Create all users and enroll in the course.
        """
        learners, course_staff = self.get_usernames(submissions_config)

        log.info('Creating and enrolling %d learners', len(learners))
        call_command(
            'create_test_users',
            *learners,
            course=course_id,
            ignore_user_already_exists=True
        )

        log.info('Creating and enrolling %d course staff', len(course_staff))
        call_command(
            'create_test_users',
            *course_staff,
            course=course_id,
            course_staff=True,
            ignore_user_already_exists=True
        )

    def submit_ora_test_data(self, course_id, submissions_config):
        """
        Run the submit action. For each specified submission, create the submission, create an assessment if specified,
        and create a lock if specified.
        """
        for ora_config in submissions_config:
            log.info('Creating test submissions for course %s', course_id)
            for submission_config in ora_config['submissions']:
                log.info("Creating submission for user %s", submission_config['username'])
                student_item = self.student_item(
                    submission_config['username'],
                    course_id,
                    ora_config['displayName']
                )
                # Submissions consist of username, a line break, and then some lorem
                text_response = submission_config['username'] + '\n' + generate_lorem_sentences()
                submission = sub_api.create_submission(student_item, {'parts': [{'text': text_response}]})
                workflow_api.create_workflow(submission['uuid'], ['staff'])
                workflow_api.update_from_assessments(submission['uuid'], None, {})
                log.info("Created submission %s for user %s", submission['uuid'], submission_config['username'])

                if submission_config['lockOwner']:
                    log.info(
                        "Creating lock on submission %s owned by %s",
                        submission['uuid'],
                        submission_config['lockOwner']
                    )
                    SubmissionGradingLock.claim_submission_lock(
                        submission['uuid'],
                        self.username_to_anonymous_user_id[submission_config['lockOwner']]
                    )

                if submission_config['gradeData']:
                    grade_data = submission_config['gradeData']
                    log.info(
                        "Creating assessment from user %s for submission %s",
                        grade_data['gradedBy'],
                        submission['uuid']
                    )
                    block = self.display_name_to_block[ora_config['displayName']]
                    rubric_dict = create_rubric_dict(block.prompts, block.rubric_criteria_with_labels)
                    options_selected, criterion_feedback = self.api_format_criteria(grade_data['criteria'], rubric_dict)
                    staff_api.create_assessment(
                        submission['uuid'],
                        self.username_to_anonymous_user_id[grade_data['gradedBy']],
                        options_selected,
                        criterion_feedback,
                        grade_data['overallFeedback'],
                        rubric_dict,
                    )
                    workflow_api.update_from_assessments(submission['uuid'], None, {})

    def student_item(self, username, course_id, ora_display_name):
        """Helper for creating student item dicts"""
        return {
            'student_id': self.username_to_anonymous_user_id[username],
            'course_id': str(course_id),
            'item_id': str(self.display_name_to_block[ora_display_name].location),
            'item_type': 'openassessment'
        }

    def lookup_criterion_and_option_name(self, criterion_label, option_label, rubric_dict):
        """
        The label that users see in Studio for criteria and options are the LABELs not the NAMEs.
        The API expects names, and we have labels, so we need to look at the block's rubric definition to convert.
        """
        for criterion in rubric_dict['criteria']:
            if criterion['label'] == criterion_label:
                criterion_name = criterion['name']
                for option in criterion['options']:
                    if option['label'] == option_label:
                        return criterion_name, option['name']
        raise ValueError(f"Can't find criterion and option names for labels {criterion_label}, {option_label}")

    def api_format_criteria(self, criteria, rubric_dict):
        """
        Our input file is specifying assessments as a list of objects that link one criterion with the selected
        option name and any feedback for that criterion.
        The API wants two dicts, one from criteria name to selected option name, and one from criteria name to
        feedback for that criterion.
        """
        options_selected = {}
        criterion_feedback = {}
        for criterion in criteria:
            criterion_label = criterion['label']
            option_label = criterion['selectedOption']
            criterion_name, option_name = self.lookup_criterion_and_option_name(
                criterion_label, option_label, rubric_dict
            )
            options_selected[criterion_name] = option_name
            feedback = criterion.get('feedback')
            if feedback is not None:
                criterion_feedback[criterion_name] = feedback
        return options_selected, criterion_feedback

    def reset_ora_test_data(self, course_id, submissions_config):
        """
        Reset all mentioned submitters in all mentioned ORAs by calling clear_student_state
        """
        learner_usernames, _ = self.get_usernames(submissions_config)
        display_names = self.get_display_names(submissions_config)

        for display_name in display_names:
            block = self.display_name_to_block[display_name]
            for learner_username in learner_usernames:
                log.info("Resetting learner state for user %s ORA '%s'", learner_username, display_name)
                block.clear_student_state(
                    self.username_to_anonymous_user_id[learner_username],
                    str(course_id),
                    str(block.location),
                    self.username_to_anonymous_user_id[SUPERUSER_USERNAME],
                )
