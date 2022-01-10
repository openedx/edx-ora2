"""
Create dummy submissions and assessments for testing.
"""

import json
import copy
from re import sub
from uuid import uuid4
from os.path import exists

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

from opaque_keys.edx.keys import CourseKey

import loremipsum
from submissions import api as sub_api
from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.assessment.api import staff as staff_api
from openassessment.workflow import api as workflow_api
from openassessment.xblock import submission_mixin
from openassessment.xblock import data_conversion
from openassessment.xblock.data_conversion import create_rubric_dict
from openassessment.staffgrader.models import SubmissionGradingLock

SUPERUSER_USERNAME = 'edx'

EPILOG = """
The path to the file describing the format and structure of the submissions and assessments to generate. The path should be relative from the the ora2 src directory.'

Input files should be placed somewhere in WORKSPACE_ROOT/src/edx-ora2/ on local disk, which corresponds to
/edx/src/edx-ora2 in the edx-platform docker container.

Input files should be in the format:
{format to come}
"""

# def generate_lorem_sentences(num_sentences=1):
    
# def generate_lorem_sentence():
#     result = []
#     lorem_sentence = loremipsum.get_sentence().split()
#     for word in lorem_sentence:
#         result = 


class Command(BaseCommand):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username_to_anonymous_user_id = None
        self.display_name_to_block = None
        self.display_name_to_rubric_dict = None

    def add_arguments(self, parser):
        parser.add_argument(
            'course_id',
            type=CourseKey.from_string,
            help='The id of the course for which to create submissions'
        )
        parser.add_argument(
            'submissions_config_file_path',
            help='Path to the config file relative to and within the ORA directory'
        )
        parser.add_argument(
            '--init',
            action='store_true',
            help='Create and enroll users, create submissions, assessments, and locks'
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Clear all ORA submission state from the given course'
        )        
        parser.add_argument(
            '--submit',
            action='store_true',
            help='Create submissions, assessments, and locks d'
        )
        parser.epilog = EPILOG
        
    def _check_args(self, options):
        active_flags = sum([1 if options[flag] else 0 for flag in ['init', 'reset', 'submit']])
        if active_flags == 0:
            raise CommandError("One of --init --reset --submit is required.")
        if active_flags > 1:
            raise CommandError("--init --reset --submit are mutually exclusive")

    def handle(self, *args, **options):
        """
        """
        self._check_args(options)

        course_id = options['course_id']
        submissions_config = self.read_config_file(options['submissions_config_file_path'])
        self.load_anonymous_ids_and_block_locations(course_id, submissions_config)   
        if options['reset']:
            self.reset_ora_test_data(course_id, submissions_config)
        elif options['init']:
            self.init_ora_test_data(course_id, submissions_config)
        elif options['submit']:
            self.submit_ora_test_data(course_id, submissions_config)
        
    def get_display_names(self, submissions_config):
        display_names = []
        for ora_config in submissions_config:
            display_name = ora_config['displayName']
            if display_name in display_names:
                raise CommandError('Duplicate ORA display name found:' + display_name)
            display_names.append(display_name)
        return display_names

    def load_anonymous_ids_and_block_locations(self, course_id, submissions_config):
        learners, course_staff = self.get_usernames(submissions_config)
        self.load_anonymous_user_ids(course_id, learners | course_staff)
        ora_display_names = self.get_display_names(submissions_config)
        self.load_modulestore_data(course_id, ora_display_names)

    def read_config_file(self, file_path):
        file_path = '/edx/src/edx-ora2/' + file_path
        if not exists(file_path):
            raise CommandError(f'File {file_path} not found.')

        with open(file_path) as f:
            try:
                submissions_config = json.load(f)
                if not isinstance(submissions_config, list):
                    submissions_config = [submissions_config]
                return submissions_config
            except json.JSONDecodeError as e:
                raise CommandError(f'Unable to parse file {file_path}: {e}') from e

    def get_usernames(self, submissions_config):        
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

    def init_ora_test_data(self, course_id, submissions_config):
        print('Running the init.')
        learners, course_staff = self.get_usernames(submissions_config)

        print(f'Creating and enrolling {len(learners)} learners')
        call_command('create_test_users', *learners, course=course_id, ignore_user_already_exists=True)
        
        print(f'Creating and enrolling {len(course_staff)} course staff')
        call_command('create_test_users', *course_staff, course=course_id, course_staff=True, ignore_user_already_exists=True)
        
        self.submit_ora_test_data(course_id, submissions_config)

    def load_anonymous_user_ids(self, course_id, usernames):
        from common.djangoapps.student.models import anonymous_id_for_user
        anonymous_user_ids = dict()
        usernames.add(SUPERUSER_USERNAME)
        users = get_user_model().objects.filter(username__in=usernames).all()
        for user in users:
            anonymous_user_ids[user.username] = anonymous_id_for_user(user=user, course_id=course_id)
        
        missing_usernames = set(usernames) - set(anonymous_user_ids.keys())
        if missing_usernames:
            raise CommandError("Unable to load anonymous id for user(s) " + ' '.join(missing_usernames))
        
        self.username_to_anonymous_user_id = anonymous_user_ids
    
    def load_modulestore_data(self, course_id, display_names):
        from xmodule.modulestore.django import modulestore  # pylint: disable=import-error
        openassessment_blocks = modulestore().get_items(
            course_id, qualifiers={'category': 'openassessment'}
        )
        openassessment_blocks = [
            block for block in openassessment_blocks if block.parent is not None
        ]
        display_name_to_block = {block.display_name: block for block in openassessment_blocks}
        self.display_name_to_block = display_name_to_block
    
    
    def student_item(self, username, course_id, ora_display_name):
        return {
            'student_id': self.username_to_anonymous_user_id[username],
            'course_id': str(course_id),
            'item_id': str(self.display_name_to_block[ora_display_name].location),
            'item_type': 'openassessment'
        }
        
    def submit_ora_test_data(self, course_id, submissions_config):
        print('Running the submit.')
        for ora_config in submissions_config:
            for submission_config in ora_config['submissions']:
                    student_item = self.student_item(
                        submission_config['username'],
                        course_id,
                        ora_config['displayName']
                    )
                    text_response = submission_config['username'] + '\n' + ' '.join(loremipsum.get_sentences(3))
                    submission = sub_api.create_submission(student_item, {'parts':[{'text': text_response}]})
                    workflow_api.create_workflow(submission['uuid'], ['staff'])
                    workflow_api.update_from_assessments(submission['uuid'], None)
                    
                    if submission_config['lockOwner']:
                        SubmissionGradingLock.claim_submission_lock(
                            submission['uuid'],
                            self.username_to_anonymous_user_id[submission_config['lockOwner']]
                        )
                    
                    if submission_config['gradeData']:
                        grade_data = submission_config['gradeData']
                        options_selected, criterion_feedback = self.api_format_criteria(grade_data['criteria'])
                        block = self.display_name_to_block[ora_config['displayName']]
                        staff_api.create_assessment(
                            submission['uuid'],
                            self.username_to_anonymous_user_id[grade_data['gradedBy']],
                            options_selected,
                            criterion_feedback,
                            grade_data['overallFeedback'],
                            create_rubric_dict(block.prompts, block.rubric_criteria_with_labels)   
                        )
                        workflow_api.update_from_assessments(submission['uuid'], None)

    
    def api_format_criteria(self, criteria):
        options_selected = {}
        criterion_feedback = {}
        for criterion in criteria:
            options_selected[criterion['name']] = criterion['selectedOption']
            criterion_feedback[criterion['name']] = criterion['feedback']
        return options_selected, criterion_feedback

    
    def reset_ora_test_data(self, course_id, submissions_config):
        from xmodule.modulestore.django import modulestore  # pylint: disable=import-error
        store = modulestore()
        learner_usernames, _ = self.get_usernames(submissions_config)
        display_names = self.get_display_names(submissions_config)
        print('Resetting ORA state for the following ORAs and users')
        print('ORAs: ' + ' ,'.join(display_names))
        print('Users: ' + ' ,'.join(learner_usernames))
        
        for display_name in display_names:
            block = self.display_name_to_block[display_name]
            for learner_username in learner_usernames:
                block.clear_student_state(
                    self.username_to_anonymous_user_id[learner_username],
                    str(course_id),
                    str(block.location),
                    self.username_to_anonymous_user_id[SUPERUSER_USERNAME],
                )
