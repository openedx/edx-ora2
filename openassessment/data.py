"""
Aggregate data for openassessment.
"""

from collections import OrderedDict, defaultdict, namedtuple
import csv
from io import StringIO
from itertools import chain
import json
import logging
import os
from urllib.parse import urljoin
from zipfile import ZipFile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import CharField, F, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.utils.translation import gettext as _
import requests

from submissions.models import Submission
from submissions import api as sub_api
from submissions.errors import SubmissionNotFoundError
from openassessment.runtime_imports.classes import import_block_structure_transformers, import_external_id
from openassessment.runtime_imports.functions import get_course_blocks, modulestore
from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.models import Assessment, AssessmentFeedback, AssessmentPart
from openassessment.fileupload.api import get_download_url
from openassessment.workflow.models import AssessmentWorkflow, TeamAssessmentWorkflow
from openassessment.assessment.score_type_constants import PEER_TYPE, SELF_TYPE, STAFF_TYPE

logger = logging.getLogger(__name__)


def _usernames_enabled():
    """
    Checks if toggle for deanonymized usernames in report enabled.
    """

    return settings.FEATURES.get('ENABLE_ORA_USERNAMES_ON_DATA_EXPORT', False)


def _use_read_replica(queryset):
    """
    If there's a read replica that can be used, return a cursor to that.
    Otherwise, return a cursor to the regular database.

    Args:
        queryset (QuerySet): The queryset that we would like to use the read replica for.
    Returns:
        QuerySet
    """
    return (
        queryset.using("read_replica")
        if "read_replica" in settings.DATABASES
        else queryset
    )


def _get_course_blocks(course_id):  # pragma: no cover
    """
    Returns untransformed block structure for a given course key.

    Args:
        course_id - CourseLocator instance
    Returns:
        BlockStructureBlockData instance
    """
    BlockStructureTransformers = import_block_structure_transformers()
    store = modulestore()
    course_usage_key = store.make_course_usage_key(course_id)

    # Passing an empty block structure transformer here to avoid user access checks
    return get_course_blocks(None, course_usage_key, BlockStructureTransformers())


def map_anonymized_ids_to_usernames(anonymized_ids):
    """
    Args:
        anonymized_ids - list of anonymized user ids.
    Returns:
        dictionary, that contains mapping between anonymized user ids and
        actual usernames.
    """
    User = get_user_model()

    users = _use_read_replica(
        User.objects.filter(anonymoususerid__anonymous_user_id__in=anonymized_ids)
        .annotate(anonymous_id=F("anonymoususerid__anonymous_user_id"))
        .values("username", "anonymous_id")
    )

    anonymous_id_to_username_mapping = {
        user["anonymous_id"]: user["username"] for user in users
    }

    return anonymous_id_to_username_mapping

def map_anonymized_ids_to_emails(anonymized_ids):
    """
    Args:
        anonymized_ids - list of anonymized user ids.
    Returns:
        dictionary, that contains mapping between anonymized user ids and
        actual user emails.
    """
    User = get_user_model()

    users = _use_read_replica(
        User.objects.filter(anonymoususerid__anonymous_user_id__in=anonymized_ids)
        .annotate(anonymous_id=F("anonymoususerid__anonymous_user_id"))
        .values("email", "anonymous_id")
    )
    anonymous_id_to_email_mapping = {
        user["anonymous_id"]: user["email"] for user in users
    }
    return anonymous_id_to_email_mapping


def map_anonymized_ids_to_fullname(anonymized_ids):
    """
    Args:
        anonymized_ids - list of anonymized user ids.
    Returns:
        dictionary, that contains mapping between anonymized user ids and
        actual user fullname.
    """
    User = get_user_model()

    users = _use_read_replica(
        User.objects.filter(anonymoususerid__anonymous_user_id__in=anonymized_ids)
        .select_related("profile")
        .annotate(anonymous_id=F("anonymoususerid__anonymous_user_id"))
        .values("profile__name", "anonymous_id")
    )

    anonymous_id_to_fullname_mapping = {
        user["anonymous_id"]: user["profile__name"] for user in users
    }
    return anonymous_id_to_fullname_mapping

class CsvWriter:
    """
    Dump openassessment data to CSV files.
    """

    MODELS = [
        'assessment', 'assessment_part',
        'assessment_feedback', 'assessment_feedback_option',
        'submission', 'score'
    ]

    HEADERS = {
        'assessment': [
            'id', 'submission_uuid', 'scored_at',
            'scorer_id', 'score_type',
            'points_possible', 'feedback',
        ],
        'assessment_part': [
            'assessment_id', 'points_earned',
            'criterion_name', 'criterion_label',
            'option_name', 'option_label', 'feedback'
        ],
        'assessment_feedback': [
            'submission_uuid', 'feedback_text', 'options'
        ],
        'assessment_feedback_option': [
            'id', 'text'
        ],
        'submission': [
            'uuid', 'student_id', 'item_id',
            'submitted_at', 'created_at', 'raw_answer'
        ],
        'score': [
            'submission_uuid',
            'points_earned', 'points_possible',
            'created_at',
        ]
    }

    # Number of submissions to retrieve at a time
    # from the database.  We need to do this in order
    # to avoid loading thousands of records into memory at once.
    QUERY_INTERVAL = 100

    def __init__(self, output_streams, progress_callback=None):
        """
        Configure where the writer will write data.

        You can provide open file handles for each of the available
        models (see `AssessmentCsvWriter.MODELS`).  If you don't
        provide an output stream, the writer won't produce data
        for that model.

        Args:
            output_streams (dictionary): Provide the file handles
                to write CSV data to.

        Keyword Arguments:
            progress_callback (callable): Callable that accepts
                no arguments.  Called once per submission loaded
                from the database.

        Example usage:
            >>> output_streams = {
            >>>     "submission": open('submissions.csv', 'w'),
            >>>     "score": open('scores.csv', 'w')
            >>> }
            >>> writer = AssessmentsCsvWriter(output_streams)
            >>> writer.write_to_csv()

        """
        self.writers = {
            key: csv.writer(file_handle)
            for key, file_handle in output_streams.items()
            if key in self.MODELS
        }
        self._progress_callback = progress_callback

    def write_to_csv(self, course_id):
        """
        Write assessment and submission data for a course to CSV files.

        NOTE: The current implementation optimizes for memory usage,
        but not for the number of database queries.  All the queries
        use indexed fields (the submission uuid), so they should be
        relatively quick.

        Args:
            course_id (unicode): The course ID from which to pull data.

        Returns:
            None

        """
        self._write_csv_headers()

        rubric_points_cache = {}
        feedback_option_set = set()
        for submission_uuid in self._submission_uuids(course_id):
            self._write_submission_to_csv(submission_uuid)

            # Django 1.4 doesn't follow reverse relations when using select_related,
            # so we select AssessmentPart and follow the foreign key to the Assessment.
            parts = _use_read_replica(
                AssessmentPart.objects.select_related('assessment', 'option', 'option__criterion')
                .filter(assessment__submission_uuid=submission_uuid)
                .order_by('assessment__pk')
            )
            self._write_assessment_to_csv(parts, rubric_points_cache)

            feedback_query = _use_read_replica(
                AssessmentFeedback.objects
                .filter(submission_uuid=submission_uuid)
                .prefetch_related('options')
            )
            for assessment_feedback in feedback_query:
                self._write_assessment_feedback_to_csv(assessment_feedback)
                # pylint: disable=unnecessary-comprehension
                feedback_option_set.update({
                    option for option in assessment_feedback.options.all()
                })

            if self._progress_callback is not None:
                self._progress_callback()

        # The set of available options should be relatively small,
        # since they're not (currently) user-defined.
        self._write_feedback_options_to_csv(feedback_option_set)

    def _submission_uuids(self, course_id):
        """
        Iterate over submission uuids.
        Makes database calls every N submissions to avoid loading
        all submission uuids into memory at once.

        Args:
            course_id (unicode): The ID of the course to retrieve submissions from.

        Yields:
            submission_uuid (unicode)

        """
        num_results = 0
        start = 0
        total_results = _use_read_replica(
            AssessmentWorkflow.objects.filter(course_id=course_id)
        ).count()

        while num_results < total_results:
            # Load a subset of the submission UUIDs
            # We're assuming that peer workflows are immutable,
            # so if we counted N at the start of the loop,
            # there should be >= N for us to process.
            end = start + self.QUERY_INTERVAL
            query = _use_read_replica(
                AssessmentWorkflow.objects
                .filter(course_id=course_id)
                .order_by('created')
            ).values('submission_uuid')[start:end]

            for workflow_dict in query:
                num_results += 1
                yield workflow_dict['submission_uuid']

            start += self.QUERY_INTERVAL

    def _write_csv_headers(self):
        """
        Write the headers (first row) for each output stream.
        """
        for name, writer in self.writers.items():
            writer.writerow(self.HEADERS[name])

    def _write_submission_to_csv(self, submission_uuid):
        """
        Write submission data to CSV.

        Args:
            submission_uuid (unicode): The UUID of the submission to write.

        Returns:
            None

        """
        submission = sub_api.get_submission_and_student(submission_uuid, read_replica=True)
        self._write_unicode('submission', [
            submission['uuid'],
            submission['student_item']['student_id'],
            submission['student_item']['item_id'],
            submission['submitted_at'],
            submission['created_at'],
            json.dumps(submission['answer'])
        ])

        score = sub_api.get_latest_score_for_submission(submission_uuid, read_replica=True)
        if score is not None:
            self._write_unicode('score', [
                score['submission_uuid'],
                score['points_earned'],
                score['points_possible'],
                score['created_at']
            ])

    def _write_assessment_to_csv(self, assessment_parts, rubric_points_cache):
        """
        Write assessments and assessment parts to CSV.

        Args:
            assessment_parts (list of AssessmentPart): The assessment parts to write,
                not necessarily from the same assessment.
            rubric_points_cache (dict): in-memory cache of points possible by rubric ID.

        Returns:
            None

        """
        assessment_id_set = set()

        for part in assessment_parts:
            self._write_unicode('assessment_part', [
                part.assessment.id,
                part.points_earned,
                part.criterion.name,
                part.criterion.label,
                part.option.name if part.option is not None else "",
                part.option.label if part.option is not None else "",
                part.feedback
            ])

            # If we haven't seen this assessment before, write it
            if part.assessment.id not in assessment_id_set:
                assessment = part.assessment

                # The points possible in the rubric will be the same for
                # every assessment that shares a rubric.  To avoid querying
                # the rubric criteria/options each time, we cache points possible
                # for each rubric ID.
                if assessment.rubric_id in rubric_points_cache:
                    points_possible = rubric_points_cache[assessment.rubric_id]
                else:
                    points_possible = assessment.points_possible
                    rubric_points_cache[assessment.rubric_id] = points_possible

                self._write_unicode('assessment', [
                    assessment.id,
                    assessment.submission_uuid,
                    assessment.scored_at,
                    assessment.scorer_id,
                    assessment.score_type,
                    points_possible,
                    assessment.feedback
                ])
                assessment_id_set.add(assessment.id)

    def _write_assessment_feedback_to_csv(self, assessment_feedback):
        """
        Write feedback on assessments to CSV.

        Args:
            assessment_feedback (AssessmentFeedback): The feedback model to write.

        Returns:
            None

        """
        options_string = ",".join([
            str(option.id) for option in assessment_feedback.options.all()
        ])

        self._write_unicode('assessment_feedback', [
            assessment_feedback.submission_uuid,
            assessment_feedback.feedback_text,
            options_string
        ])

    def _write_feedback_options_to_csv(self, feedback_options):
        """
        Write feedback on assessment options to CSV.

        Args:
            feedback_options (iterable of AssessmentFeedbackOption)

        Returns:
            None

        """
        for option in feedback_options:
            self._write_unicode(
                'assessment_feedback_option',
                [option.id, option.text]
            )

    def _write_unicode(self, output_name, row):
        """
        Encode a row as a UTF-8 bytestring, then write it to a CSV file.
        Non-string values are first converted to unicode.

        Args:
            output_name (str): The name of the output stream to write to.
            row (list): List of fields, which must be serializable as UTF-8.

        Returns:
            None

        """
        writer = self.writers.get(output_name)
        if writer is not None:
            encoded_row = [str(field) for field in row]
            writer.writerow(encoded_row)


class OraAggregateData:
    """
    Aggregate all the ORA data into a single table-like data structure.
    """

    @classmethod
    def _map_students_and_scorers_ids_to_usernames(cls, all_submission_information):
        """
        Args:
            all_submission_information - list of tuples with submission data,
            that returned by submissions api's
            `get_all_course_submission_information` method.
        Returns:
            dictionary, that contains mapping between students and scoreres
            anonymized user ids and actual usernames.
        """

        student_ids = []
        submission_uuids = []

        for student_item, submission, _ in all_submission_information:
            student_ids.append(student_item["student_id"])
            submission_uuids.append(submission["uuid"])

        scorer_ids = _use_read_replica(
            Assessment.objects.filter(submission_uuid__in=submission_uuids).values_list(
                "scorer_id", flat=True
            )
        )

        return map_anonymized_ids_to_usernames(student_ids + list(scorer_ids))

    @classmethod
    def _map_block_usage_keys_to_display_names(cls, course_id):
        """
        Builds a mapping between block usage key string and block display
        name for those ones, whoose category is equal to ``openassessment``.

        Args:
            course_id (string or CourseLocator instance) - id of course
            resourse
        Returns:
            dictionary, that contains mapping between block usage
            keys (locations) and block display names.
        """

        blocks = _get_course_blocks(course_id)

        block_display_name_map = {}

        for block_key in blocks:
            block_type = blocks.get_xblock_field(block_key, 'category')
            if block_type == 'openassessment':
                block_display_name_map[str(block_key)] = blocks.get_xblock_field(block_key, 'display_name')

        return block_display_name_map

    @classmethod
    def _build_assessments_cell(cls, assessments, usernames_map, scored_peer_assessment_ids=None):
        """
        Args:
            assessments (QuerySet) - assessments that we would like to collate into one column.
            usernames_map - dictionary that maps anonymous ids to usernames.
        Returns:
            string that should be included in the 'assessments' column for this set of assessments' row
        """
        scored_peer_assessment_ids = scored_peer_assessment_ids or set()
        returned_string = ""
        for assessment in assessments:
            returned_string += f"Assessment #{assessment.id}\n"
            returned_string += f"-- scored_at: {assessment.scored_at}\n"
            returned_string += f"-- type: {assessment.score_type}\n"
            if assessment.score_type == peer_api.PEER_TYPE:
                returned_string += f'-- used to calculate peer grade: {assessment.id in scored_peer_assessment_ids}\n'
            if _usernames_enabled():
                returned_string += "-- scorer_username: {}\n".format(usernames_map.get(assessment.scorer_id, ''))
            returned_string += f"-- scorer_id: {assessment.scorer_id}\n"
            if assessment.feedback != "":
                returned_string += f"-- overall_feedback: {assessment.feedback}\n"
        return returned_string

    @classmethod
    def _build_assessments_parts_cell(cls, assessments):
        """
        Args:
            assessments (QuerySet) - assessments containing the parts that we would like to collate into one column.
        Returns:
            string that should be included in the relevant 'assessments_parts' column for this set of assessments' row
        """
        returned_string = ""
        for assessment in assessments:
            returned_string += f"Assessment #{assessment.id}\n"
            for part in assessment.parts.order_by('criterion__order_num'):
                returned_string += f"-- {part.criterion.label}"
                if part.option is not None and part.option.label is not None:
                    option_label = part.option.label
                    returned_string += ": {option_label} ({option_points})\n".format(
                        option_label=option_label, option_points=part.option.points
                    )
                if part.feedback != "":
                    returned_string += f"-- feedback: {part.feedback}\n"
        return returned_string

    @classmethod
    def _build_assessment_parts_array(cls, assessment, median_scores):
        """
        Args:
            assessment - assessment containing the parts that we would like to report on.
            median_scores - dictionary with criterion name keys and median score values,
               as returned by Assessment.get_median_score_dict()

        Returns:
            OrderedDict that contains an entries for each criterion of the assessment(s).
        """
        parts = OrderedDict()
        number = 1
        for part in assessment.parts.order_by('criterion__order_num'):
            option_label = None
            option_points = None
            if part.option:
                option_label = part.option.label
                option_points = part.option.points

            criterion_col_label = _('Criterion {number}: {label}').format(number=number, label=part.criterion.label)
            parts[criterion_col_label] = option_label or ''
            parts[_('Points {number}').format(number=number)] = option_points or 0
            parts[_('Median Score {number}').format(number=number)] = median_scores.get(part.criterion.name)
            parts[_('Feedback {number}').format(number=number)] = part.feedback or ''
            number += 1
        return parts

    @classmethod
    def _build_feedback_options_cell(cls, assessments):
        """
        Args:
            assessments (QuerySet) - assessment that we would like to use to fetch and read the feedback options.
        Returns:
            string that should be included in the relevant 'feedback_options' column for this set of assessments' row
        """

        returned_string = ""
        for assessment in assessments:
            for feedback in assessment.assessment_feedback.all():
                for option in feedback.options.all():
                    returned_string += option.text + "\n"

        return returned_string

    @classmethod
    def _build_feedback_cell(cls, submission_uuid):
        """
        Args:
            submission_uuid (string) - the submission_uuid associated with this particular assessment feedback
        Returns:
            string that should be included in the relevant 'feedback' column for this set of assessments' row
        """
        try:
            feedback = AssessmentFeedback.objects.get(submission_uuid=submission_uuid)
        except AssessmentFeedback.DoesNotExist:
            return ""
        return feedback.feedback_text

    @classmethod
    def _build_response_file_links(cls, submission):
        """
        Args:
            submission - object
        Returns:
            string that contains newline-separated URLs to each of the files uploaded for this submission.
        """
        file_links = ''
        base_url = getattr(settings, 'LMS_ROOT_URL', '')

        from openassessment.xblock.openassessmentblock import OpenAssessmentBlock
        file_downloads = OpenAssessmentBlock.get_download_urls_from_submission(submission)
        file_links = [urljoin(base_url, file_download.get('download_url')) for file_download in file_downloads]
        return "\n".join(file_links)

    @classmethod
    def collect_ora2_data(cls, course_id):
        """
        Query database for aggregated ora2 response data.

        Args:
            course_id (string) - the course id of the course whose data we would like to return

        Returns:
            A tuple containing two lists: headers and data.

            headers is a list containing strings corresponding to the column headers of the data.
            data is a list of lists, where each sub-list corresponds to a row in the table of all the data
                for this course.

        """
        all_submission_information = list(sub_api.get_all_course_submission_information(course_id, 'openassessment'))
        usernames_enabled = _usernames_enabled()

        usernames_map = (
            cls._map_students_and_scorers_ids_to_usernames(all_submission_information)
            if usernames_enabled
            else {}
        )
        block_display_names_map = cls._map_block_usage_keys_to_display_names(course_id)

        all_submission_uuids = [submission['uuid'] for _, submission, _ in all_submission_information]
        all_scored_peer_assessment_ids = {
            assessment.id for assessment in peer_api.get_bulk_scored_assessments(all_submission_uuids)
        }

        rows = []
        for student_item, submission, score in all_submission_information:
            assessments = _use_read_replica(
                Assessment.objects.prefetch_related('parts').
                prefetch_related('rubric').
                filter(
                    submission_uuid=submission['uuid']
                )
            )

            assessments_cell = cls._build_assessments_cell(assessments, usernames_map, all_scored_peer_assessment_ids)
            assessments_parts_cell = cls._build_assessments_parts_cell(assessments)
            feedback_options_cell = cls._build_feedback_options_cell(assessments)
            feedback_cell = cls._build_feedback_cell(submission['uuid'])

            row_username_cell = (
                [usernames_map.get(student_item["student_id"], "")]
                if usernames_enabled
                else []
            )

            problem_name = block_display_names_map.get(student_item['item_id'])

            row = [
                submission['uuid'],
                student_item['item_id'],
                problem_name,
                submission['student_item'],
            ] + row_username_cell + [
                student_item['student_id'],
                submission['submitted_at'],
                #  Dumping required to render special characters in CSV
                json.dumps(submission['answer'], ensure_ascii=False),
                assessments_cell,
                assessments_parts_cell,
                score.get('created_at', ''),
                score.get('points_earned', ''),
                score.get('points_possible', ''),
                feedback_options_cell,
                feedback_cell
            ]
            rows.append(row)

        header_username_cell = (
            ['Username']
            if usernames_enabled
            else []
        )

        header = [
            'Submission ID',
            'Location',
            'Problem Name',
            'Item ID'
        ] + header_username_cell + [
            'Anonymized Student ID',
            'Date/Time Response Submitted',
            'Response',
            'Assessment Details',
            'Assessment Scores',
            'Date/Time Final Score Given',
            'Final Score Points Earned',
            'Final Score Points Possible',
            'Feedback Statements Selected',
            'Feedback on Peer Assessments'
        ]
        return header, rows

    @classmethod
    def collect_ora2_summary(cls, course_id):
        """
        Query database for aggregated ora2 summary data.

        Args:
            course_id (string) - the course id of the course whose data we would like to return

        Returns:
            A tuple containing two lists: headers and data.

            headers is a list containing strings corresponding to the column headers of the data.
            data is a list of lists, where each sub-list corresponds to a row in the table of all the data
                for this course.

            Headers details:

            block_name: id of ora block
            student_id: anonymized student id
            status: string indicating the current step or status the student is
                at. Eg. 'peer', 'done', 'cancelled'. Values are from the AssessmentWorkflow
                STEPS + STATUSES
            is_<STEP>_complete: boolean 'complete' status for STEP (0 or 1, or
                empty if workflow does not include this step)
            is_<STEP>_graded: boolean 'graded' status for STEP (0 or 1, or
                empty if workflow does not include this step)
            num_peers_graded: number of peers that 'student_id' has graded in the peer step
            num_graded_by_peers: number of peer grades that 'student_id' has received in the peer step
            is_staff_grade_received: boolean (0 or 1)
            is_final_grade_received: boolean (0 or 1)
            final_grade_points_earned: number of points earned in final grade.
                will be empty if no final grade yet
            final_grade_points_possible: max number of points possible for
                final grade. will be empty if no final grade
        """

        items = AssessmentWorkflow.objects.filter(course_id=course_id)

        # need the workflow steps set and sorted here so the data columns line
        # up with the headers
        steps = sorted(AssessmentWorkflow.STEPS)

        rows = []
        for aw in items:
            statuses = aw.status_details()
            try:
                submission_dict = sub_api.get_submission_and_student(aw.submission_uuid)
            except SubmissionNotFoundError:
                continue

            steps_statuses = []
            peers_graded = 0
            graded_by_count = 0
            for step in steps:
                if not statuses.get(step):
                    # if no status for step, then the 'complete' and 'graded'
                    # statuses should be empty.
                    steps_statuses.append('')
                    steps_statuses.append('')
                    continue

                # if we get to here, then a status exists for `step`

                if statuses[step]['complete']:
                    steps_statuses.append(1)
                else:
                    steps_statuses.append(0)

                if statuses[step]['graded']:
                    steps_statuses.append(1)
                else:
                    steps_statuses.append(0)

                # the peer step is special and has extra metadata
                if step == 'peer':
                    peers_graded = statuses[step]['peers_graded_count'] or 0
                    graded_by_count = statuses[step]['graded_by_count'] or 0

            is_staff_grade_received = 1 if aw.staff_score_exists() else 0
            is_final_grade_received = 1 if aw.status == AssessmentWorkflow.STATUS.done else 0

            score = aw.score
            if score is not None:
                final_grade_points_earned = score['points_earned']
                final_grade_points_possible = score['points_possible']
            else:
                final_grade_points_earned = ''
                final_grade_points_possible = ''

            row = [
                aw.item_id,
                submission_dict['student_item']['student_id'],
                aw.status,
            ] + steps_statuses + [
                peers_graded,
                graded_by_count,
                is_staff_grade_received,
                is_final_grade_received,
                final_grade_points_earned,
                final_grade_points_possible,
            ]
            rows.append(row)

        steps_headers = list(chain.from_iterable(
            (
                f"is_{step}_complete",
                f"is_{step}_graded",
            )
            for step in steps
        ))

        header = [
            'block_name',
            'student_id',
            'status',
        ] + steps_headers + [
            'num_peers_graded',
            'num_graded_by_peers',
            'is_staff_grade_received',
            'is_final_grade_received',
            'final_grade_points_earned',
            'final_grade_points_possible',
        ]

        return header, rows

    @classmethod
    def collect_ora2_responses(cls, course_id, desired_statuses=None):
        """
        Get information about all ora2 blocks in the course with response count for each step

        Args:
            course_id (string) - the course id of the course whose data we would like to return
            desired_statuses (list) - statuses to return in the result dict for each ora item

        Returns:
            A dict in the format:

            {
             'block-v1:test-org+cs101+2017_TEST+type@openassessment+block@fb668396b505470e914bad8b3178e9e7:
                 {'training': 0, 'self': 0, 'done': 2, 'peer': 1, 'staff': 0, 'total': 3},
             'block-v1:test-org+cs101+2017_TEST+type@openassessment+block@90b4edff50bc47d9ba037a3180c44e97:
                 {'training': 0, 'self': 2, 'done': 0, 'peer': 0, 'staff': 2, 'total': 4},
             ...
            }

        """

        all_valid_ora_statuses = set()
        all_valid_ora_statuses.update(AssessmentWorkflow().STATUS_VALUES)
        all_valid_ora_statuses.update(TeamAssessmentWorkflow().STATUS_VALUES)

        if desired_statuses:
            statuses = [st for st in all_valid_ora_statuses if st in desired_statuses]
        else:
            statuses = all_valid_ora_statuses

        items = AssessmentWorkflow.objects.filter(course_id=course_id, status__in=statuses).values('item_id', 'status')

        result = defaultdict(lambda: {status: 0 for status in statuses})
        for item in items:
            item_id = item['item_id']
            status = item['status']
            result[item_id]['total'] = result[item_id].get('total', 0) + 1
            if status in statuses:
                result[item_id][status] += 1

        return result

    @classmethod
    def generate_assessment_data(cls, xblock_id, submission_uuid=None):
        """
        Generates an OrderedDict for each submission and/or assessment for the given user state.

        Arguments:
        * xblock_id: unique identifier for the current XBlock
        * submission_uuid: unique identifier for the submission, or None
        """
        row = OrderedDict()
        row[_('Item ID')] = xblock_id
        row[_('Submission ID')] = submission_uuid or ''

        submission = None
        if submission_uuid:
            submission = sub_api.get_submission_and_student(submission_uuid)

        if not submission:
            # If no submission, just report block Item ID.
            yield row
            return

        student_item = submission['student_item']
        row[_('Anonymized Student ID')] = student_item['student_id']

        assessments = _use_read_replica(
            Assessment.objects.prefetch_related('parts').
            prefetch_related('rubric').
            filter(
                submission_uuid=submission['uuid']
            )
        )
        if assessments:
            scores = Assessment.scores_by_criterion(assessments)
            median_scores = Assessment.get_median_score_dict(scores)
        else:
            # If no assessments, just report submission data.
            median_scores = []
            assessments = [None]

        score = sub_api.get_score(student_item) or {}
        feedback_cell = cls._build_feedback_cell(submission_uuid)
        response_files = cls._build_response_file_links(submission)

        for assessment in assessments:
            assessment_row = row.copy()
            if assessment:
                assessment_cells = cls._build_assessment_parts_array(assessment, median_scores)
                feedback_options_cell = cls._build_feedback_options_cell([assessment])

                score_created_at = score.get('created_at', '')
                if score_created_at:
                    score_created_at = score_created_at.strftime('%F %T %Z')

                assessment_row[_('Assessment ID')] = assessment.id
                assessment_row[_('Assessment Scored Date')] = assessment.scored_at.strftime('%F')
                assessment_row[_('Assessment Scored Time')] = assessment.scored_at.strftime('%T %Z')
                assessment_row[_('Assessment Type')] = assessment.score_type
                assessment_row[_('Anonymous Scorer Id')] = assessment.scorer_id
                assessment_row.update(assessment_cells)
                assessment_row[_('Overall Feedback')] = assessment.feedback or ''
                assessment_row[_('Assessment Score Earned')] = assessment.points_earned
                assessment_row[_('Assessment Scored At')] = assessment.scored_at.strftime('%F %T %Z')
                assessment_row[_('Date/Time Final Score Given')] = score_created_at
                assessment_row[_('Final Score Earned')] = score.get('points_earned', '')
                assessment_row[_('Final Score Possible')] = score.get('points_possible', assessment.points_possible)
                assessment_row[_('Feedback Statements Selected')] = feedback_options_cell
                assessment_row[_('Feedback on Assessment')] = feedback_cell

            assessment_row[_('Response Files')] = response_files
            yield assessment_row


class OraDownloadData:
    """
    Helper class, that is used for downloading and compressing data related
    to submissions (attachments, answer texts).
    """

    ATTACHMENT = 'attachment'
    TEXT = 'text'
    SUBMISSIONS_CSV_HEADER = (
        'course_id',
        'block_id',
        'student_id',
        'key',
        'name',
        'type',
        'description',
        'size',
        'file_path',
        'file_found',
    )
    MAX_FILE_NAME_LENGTH = 255

    @classmethod
    def _download_file_by_key(cls, key):
        url = get_download_url(key)
        if not url:
            raise FileMissingException
        download_url = urljoin(
            settings.LMS_ROOT_URL, url
        )

        response = requests.get(download_url)
        response.raise_for_status()
        return response.content

    @classmethod
    def _map_ora_usage_keys_to_path_info(cls, course_id):
        """
        Helper function that accepts course key and returns mapping in the form of a dictionary,
        where key is a string representation of ORA's usage key, and value is a dictionary with
        all information needed to build the submission file path.
        """
        blocks = _get_course_blocks(course_id)
        logger.info("[%s] _get_course_blocks returned %d blocks", course_id, len(blocks))

        path_info = {}

        def children(usage_key, condition=None):
            # pylint: disable=filter-builtin-not-iterating
            child_blocks = blocks.get_children(usage_key)
            filtered = filter(condition, child_blocks)
            for index, child in enumerate(filtered, 1):
                yield index, blocks.get_xblock_field(child, 'display_name'), child

        def only_ora_blocks(block):
            return block.block_type == "openassessment"

        for section_index, section_name, section in children(blocks.root_block_usage_key):
            for sub_section_index, sub_section_name, sub_section in children(section):
                for unit_index, unit_name, unit in children(sub_section):
                    for block_index, block_name, block in children(unit, only_ora_blocks):
                        ora_block_path_info = {
                            "section_index": section_index,
                            "section_name": section_name,
                            "sub_section_index": sub_section_index,
                            "sub_section_name": sub_section_name,
                            "unit_index": unit_index,
                            "unit_name": unit_name,
                            "ora_index": block_index,
                            "ora_name": block_name,
                        }
                        path_info[str(block)] = ora_block_path_info

        return path_info

    @classmethod
    def _map_student_ids_to_path_ids(cls, all_submission_information):
        """
        Builds a mapping between anonymized student ids and their identifier for
        submission filename.

        The identifier can take three different forms:
        - External ID of `mb_coaching` type.
        - edX username, if external ID is absent.
        - Anonymized username, if `ENABLE_ORA_USERNAMES_ON_DATA_EXPORT` feature is disabled.
        """
        student_ids = [item[0]["student_id"] for item in all_submission_information]
        if not student_ids:
            return {}
        User = get_user_model()
        ExternalId = import_external_id()

        users = _use_read_replica(
            User.objects.filter(
                anonymoususerid__anonymous_user_id__in=student_ids,
            )
            .annotate(
                student_id=F("anonymoususerid__anonymous_user_id"),
                path_id=Coalesce(
                    Subquery(
                        ExternalId.objects.filter(
                            user=OuterRef("pk"), external_id_type__name="mb_coaching"
                        ).values("external_user_id")
                    ),
                    F(
                        "username"
                        if _usernames_enabled()
                        else "anonymoususerid__anonymous_user_id"
                    ),
                    output_field=CharField(),
                ),
            )
            .values("student_id", "path_id")
        )

        return {user["student_id"]: user["path_id"] for user in users}

    @classmethod
    def _submission_directory_name(
        cls,
        section_index,
        section_name,
        sub_section_index,
        sub_section_name,
        unit_index,
        unit_name,
        **__,
    ):
        """
        Returns submissions directory name in format:
        `[{section_index}]{section_name}, [sub_section_index]{sub_section_name}, [{unit_index}]{unit_name}`

        Example:
        `[1]Introduction, [1]Demo Course Overview, [1]Introduction: Video and Sequences`

        If the resulting name length is greater than 255, it truncates name parts in the following order:
        - Subsection name.
        - Unit name.
        - Section name.
        """

        def get_name_and_diff():
            name = (
                f"[{section_index}]{section_name}, "
                f"[{sub_section_index}]{sub_section_name}, "
                f"[{unit_index}]{unit_name}"
            )
            diff = cls.MAX_FILE_NAME_LENGTH - len(name)
            return name, diff

        directory_name, diff = get_name_and_diff()
        if diff >= 0:
            return directory_name

        sub_section_name = sub_section_name[:diff]
        directory_name, diff = get_name_and_diff()
        if diff >= 0:
            return directory_name

        unit_name = unit_name[:diff]
        directory_name, diff = get_name_and_diff()
        if diff >= 0:
            return directory_name

        section_name = section_name[:diff]

        return get_name_and_diff()[0]

    @classmethod
    def _submission_filename(cls, ora_index, student_id, original_filename):
        """
        Returns submission file name in format:
        `[{ora_index}] - {student_id} - {attachment_base}{attachment_extention}`

        Example:
        `[1] - 703dee642c9872a35d84fa9b2d96950f - prompt_1.txt`

        If the resulting name length is greater than 255, it truncates original file base.
        """

        file_base, file_extention = os.path.splitext(original_filename)

        def get_name(file_base):
            return (
                f"[{ora_index}] - {student_id} - {file_base}{file_extention}"
                if file_base
                else f"[{ora_index}] - {student_id}{file_extention}"
            )

        file_name = get_name(file_base)

        diff = cls.MAX_FILE_NAME_LENGTH - len(file_name)

        return file_name if diff >= 0 else get_name(file_base[:diff])

    @classmethod
    def _submission_filepath(cls, ora_path_info, student_id, original_filename):
        """
        Returns the full zip file path for the submission text or attachment.
        """

        directory_name = (
            cls._submission_directory_name(**ora_path_info)
            if ora_path_info
            else "Removed from course"
        )

        submission_filename = cls._submission_filename(
            ora_path_info["ora_index"] if ora_path_info else "x",
            student_id,
            original_filename
        )

        return os.path.join(directory_name, submission_filename)

    @classmethod
    def create_zip_with_attachments(cls, file, submission_files_data):
        """
        Opens given stream as a zip file and writes into it all submission
        attachments and csv with list of all downloads.

        Files that cannot be found in the backend will not be included in the zip. It will be listed as file_found=False
        in the csv file.

        Example of result zip file structure:
        ```
        .
        ├── [1]Some Section, [1]Some Subsection, [1]Unit
        │   ├── [1] - 00f636b9ac6d480c9fb95c23bf1d2129 - prompt_0.txt
        │   ├── [1] - 00f636b9ac6d480c9fb95c23bf1d2129 - prompt_1.txt
        │   ├── [1] - edx - prompt_0.txt
        │   ├── [1] - edx - prompt_1.txt
        │   ├── [2] - edx - prompt_0.txt
        │   └── [2] - edx - Structure and Interpretation of Computer Programs.pdf
        ├── [1]Some Section, [2]Some Subsection, [1]Unit
        │   └── [1] - edx - prompt_0.txt
        ├── [1]Some Section, [2]Some Subsection, [2]Unit
        │   ├── [1] - edx - prompt_0.txt
        │   └── [1] - edx - the_most_dangerous_kitten.jpg
        └── submissions.csv
        ```
        """
        csv_output_buffer = StringIO()

        csvwriter = csv.DictWriter(csv_output_buffer, cls.SUBMISSIONS_CSV_HEADER, extrasaction='ignore')
        csvwriter.writeheader()

        with ZipFile(file, 'w') as zip_file:
            for file_data in submission_files_data:
                key = file_data['key']
                file_path = file_data['file_path']
                file_found = False
                try:
                    file_content = (
                        cls._download_file_by_key(key)
                        if file_data['type'] == cls.ATTACHMENT
                        else file_data['content']
                    )
                except FileMissingException:
                    # added a header to csv file to indicate that the file was found or not.
                    # TODO: (EDUCATOR-5777) should we create a {file_path}.error.txt
                    # to indicate the file error more clearly?
                    file_info_string = (
                        "Course Id: {course_id} | "
                        "Block Id: {block_id} | "
                        "Student Id: {student_id} | "
                        "Key: {file_key} | "
                        "Name: {file_name} | "
                        "Type: {file_type}"
                    ).format(
                        course_id=file_data['course_id'],
                        block_id=file_data['block_id'],
                        student_id=file_data['student_id'],
                        file_key=file_data['key'],
                        file_name=file_data['name'],
                        file_type=file_data['type'],
                    )
                    logger.warning(
                        'File for submission could not be downloaded for ORA submission archive. %s',
                        file_info_string
                    )
                else:
                    file_found = True
                    zip_file.writestr(file_path, file_content)
                finally:
                    csvwriter.writerow({**file_data, 'file_found': file_found})

            zip_file.writestr(
                'submissions.csv',
                csv_output_buffer.getvalue().encode('utf-8')
            )

        file.seek(0)
        return True

    @classmethod
    def collect_ora2_submission_files(cls, course_id):
        """
        Generator, that yields dictionaries with information about submission
        attachment or answer text.
        """
        all_submission_information = list(sub_api.get_all_course_submission_information(course_id, 'openassessment'))
        logger.info(
            "[%s] Submission information loaded from submission API (len=%d)",
            course_id,
            len(all_submission_information)
        )
        all_ora_path_information = cls._map_ora_usage_keys_to_path_info(course_id)
        logger.info("[%s] Loaded ORA path info (len=%d)", course_id, len(all_ora_path_information))
        student_identifiers_map = cls._map_student_ids_to_path_ids(all_submission_information)
        logger.info("[%s] Loaded student identifiers (len=%d)", course_id, len(student_identifiers_map))

        for student, submission, _ in all_submission_information:
            # Submissions created from the studio authoring view will create a submission for
            # a student called `student` with no mapping to a real django User. Doing so should no longer be allowed,
            # but this remains for backwards compatibility.
            if student['student_id'] not in student_identifiers_map:
                logger.info(
                    "[%s] Student id %s has no mapping to a user and will be skipped",
                    course_id,
                    student['student_id']
                )
                continue

            raw_answer = submission.get('answer', {})
            answer = OraSubmissionAnswerFactory.parse_submission_raw_answer(raw_answer)
            for index, uploaded_file in enumerate(answer.get_file_uploads()):
                yield {
                    'type': cls.ATTACHMENT,
                    'course_id': course_id,
                    'block_id': student['item_id'],
                    'student_id': student['student_id'],
                    'key': uploaded_file.key,
                    'name': uploaded_file.name,
                    'description': uploaded_file.description,
                    'size': uploaded_file.size,
                    'file_path': cls._submission_filepath(
                        all_ora_path_information.get(student['item_id']),
                        student_identifiers_map[student['student_id']],
                        uploaded_file.name,
                    ),
                }

            # collecting submission answer texts
            for index, text_response in enumerate(answer.get_text_responses()):
                file_name = f'prompt_{index}.txt'

                yield {
                    'type': cls.TEXT,
                    'course_id': course_id,
                    'block_id': student['item_id'],
                    'student_id': student['student_id'],
                    'key': '',
                    'name': file_name,
                    'description': 'Submission text.',
                    'content': text_response,
                    'size': len(text_response),
                    'file_path': cls._submission_filepath(
                        all_ora_path_information.get(student['item_id']),
                        student_identifiers_map[student['student_id']],
                        file_name,
                    ),
                }


class SubmissionFileUpload:
    """
    A SubmissionFileUpload represents a file that was uploaded and submitted as a part of an ORA
    submission. It has the following fields:
        - key: The unique key used by the file upload backend to identify the file.
        - name: The filename of the submitted file.
        - description: An uploader-provided description of the submitted file.
        - size: The filesize of the submitted file.

    Due to historical considerations, only the file key is _required_ to exist,
    but all files uploaded after November 25th, 2019, _should_ contain all fields.

    If fields are missing, they will default to the following values:
        - name: key
        - description: SubmissionFileUpload.DEFAULT_DESCRIPTION
        - size: 0

    A SubmissionFileUpload is distinct from any of the data classes in openassessment/fileupload/api.py.
    FileDescriptor is a display-level construct and FileUpload represents a file that has been uploaded
    but not submitted.
    """

    DEFAULT_DESCRIPTION = _("No description provided.")

    def __init__(self, key, name=None, description=None, size=0):
        self.key = key
        self.name = name if name is not None else SubmissionFileUpload.generate_name_from_key(key)
        self.description = description if description is not None else SubmissionFileUpload.DEFAULT_DESCRIPTION
        self.size = size

    @staticmethod
    def generate_name_from_key(key):
        """
        Return the hex representation of the absolute hash of a value.
        Used to generate arbitrary file names for files with no name.
        """
        return format(abs(hash(key)), 'x')


class OraSubmissionAnswerFactory:
    """ A factory class that takes the parsed json raw_answer from a submission and returns an OraSubmissionAnswer """

    @staticmethod
    def parse_submission_raw_answer(raw_answer):
        """
        Currently this function does a basic test and returns a ZippedListSubmissionAnswer or a TextOnlySubmissionAnswer
        In the future if we were to change the way we do submissions, we would check here and return accordingly.
        """
        if TextOnlySubmissionAnswer.matches(raw_answer):
            return TextOnlySubmissionAnswer(raw_answer)
        elif ZippedListSubmissionAnswer.matches(raw_answer):
            return ZippedListSubmissionAnswer(raw_answer)
        else:
            raise VersionNotFoundException(f"No ORA Submission Answer version recognized for {raw_answer}")


class OraSubmissionAnswer:
    """ Abstract interface for ORA Submissions """
    def __init__(self, raw_answer):
        self.raw_answer = raw_answer

    @staticmethod
    def matches(raw_answer):
        """
        Check if the raw answer fits this type of OraSubmissionAnswer
        """
        raise NotImplementedError()

    def get_text_responses(self):
        """
        Get the list of text responses for the submission

        Returns: list of strings
        """
        raise NotImplementedError()

    def get_file_uploads(self, missing_blank=False):
        """
        Get the list of FileUploads for this submission
        """
        raise NotImplementedError()


class TextOnlySubmissionAnswer(OraSubmissionAnswer):

    @staticmethod
    def matches(raw_answer):
        keys = list(raw_answer.keys())
        return len(keys) == 1 and keys == ['parts']

    def __init__(self, submission):
        super().__init__(submission)
        self.text_responses = None

    def get_text_responses(self):
        """
        Parse and cache text responses from the submission
        """
        if self.text_responses is None:
            self.text_responses = [part.get('text') for part in self.raw_answer.get('parts', [])]
        return self.text_responses

    def get_file_uploads(self, missing_blank=False):
        return []


# This namedtuple represents the different shapes different versions of ORA Submissions have taken.
# Below is a table of the dates and commits that introduced each version:
#   Version | Date              | Commit
#   -----------------------------------------------------------------------
#   1       | July      8, 2014 | 42cf870695c3f2ca010abcf4e69a47d34dc56275
#   2       | April    27, 2017 | 7568a7008706db6fee5d3081e455b6687d84d659
#   3       | October  28, 2019 | 9d8b2de0a04c410c3da7d2894ce0eab8bbc9f254
#   4       | November 12, 2019 | 6c062ecc03e9bcc93d3dc78345cf63bcf910c58f
#   5       | November 25, 2019 | e0e56ac6bc054b7cd71c5e10c8cb99592511cac9
#  -------------------------------------------------------------------------

ZippedListsSubmissionVersion = namedtuple(
    'ZippedListsSubmissionVersion',
    ['key', 'description', 'name', 'size']
)

VERSION_1 = ZippedListsSubmissionVersion('file_key', None, None, None)
VERSION_2 = ZippedListsSubmissionVersion('file_keys', 'files_descriptions', None, None)
VERSION_3 = ZippedListsSubmissionVersion('file_keys', 'files_descriptions', 'files_name', None)
VERSION_4 = ZippedListsSubmissionVersion(
    'file_keys', 'files_descriptions', 'files_name', 'files_sizes'
)
VERSION_5 = ZippedListsSubmissionVersion(
    'file_keys', 'files_descriptions', 'files_names', 'files_sizes'
)
ZIPPED_LIST_SUBMISSION_VERSIONS = [
    VERSION_1, VERSION_2, VERSION_3, VERSION_4, VERSION_5
]


class VersionNotFoundException(Exception):
    """ Raised when we are unable to resolve a given submission to a submission version """


class FileMissingException(Exception):
    """ Raise when file is not found on generated CSV """


class ZippedListSubmissionAnswer(OraSubmissionAnswer):
    """
    Representation of a type of ORA submission where there are multiple lists, each
    representing a field. They are "zipped" together to represent individual files.
    """
    CURRENT_VERSION = 5

    @staticmethod
    def matches(raw_answer):
        try:
            ZippedListSubmissionAnswer.get_version(raw_answer)
        except VersionNotFoundException:
            return False
        else:
            return True

    @staticmethod
    def does_version_match(submission_keys, version):
        """
        Given a ZippedListsSubmissionVersion and a set of keys from a raw_answer,
        returns whether or not the version and keys match.

        Matching means that either the set of keys in the version matches the given set of keys,
        or the version keys plus the key "parts" matches the given set.
        """
        version_keys = {version_key for version_key in version if version_key}
        if version_keys == submission_keys:
            return True
        version_keys.add('parts')
        return version_keys == submission_keys

    @staticmethod
    def get_version(raw_answer):
        """
        Determines the version associated with a submission by working backwards from the most recent
        submission version and checking if the set of keys in the given submission matches the set
        of keys in the version.

        Raises:
            - VersionNotFoundException if the version cannot be determined.
        """
        submission_keys = set(raw_answer.keys())
        for version in reversed(ZIPPED_LIST_SUBMISSION_VERSIONS):
            if ZippedListSubmissionAnswer.does_version_match(submission_keys, version):
                return version
        raise VersionNotFoundException(f"No zipped list version found with keys {submission_keys}")

    def __init__(self, raw_answer):
        """
        Raises:
            - VersionNotFoundException if a version cannot be matched against the given submission
        """
        super().__init__(raw_answer)
        self.text_responses = None
        self.file_uploads = None
        self.version = ZippedListSubmissionAnswer.get_version(raw_answer)

    def get_text_responses(self):
        """
        Parse and cache text responses from the submission
        """
        if self.text_responses is None:
            self.text_responses = [part.get('text') for part in self.raw_answer.get('parts', [])]
        return self.text_responses

    def _index_safe_get(self, i, target_list, default=None):
        """
        Attempts to get item at target_list[i]. If the index is out of bounds, returns default.
        More or less dict.get() but for lists
        """
        try:
            return target_list[i]
        except IndexError:
            return default

    def get_file_uploads(self, missing_blank=False):
        """
        Parse and cache file upload responses from the raw_answer
        """
        default_missing_value = '' if missing_blank else None
        if self.file_uploads is None:
            file_keys = self.raw_answer.get(self.version.key, [])
            # The very earliest version of ora submissions with files only allowed one file, and so is the only
            #  situation in which any of these fields is not a list
            if not isinstance(file_keys, list):
                file_keys = [file_keys]

            files = []
            file_names = self.raw_answer.get(self.version.name, [])
            file_descriptions = self.raw_answer.get(self.version.description, [])
            file_sizes = self.raw_answer.get(self.version.size, [])
            for i, key in enumerate(file_keys):
                name = self._index_safe_get(i, file_names, default_missing_value)
                description = self._index_safe_get(i, file_descriptions, default_missing_value)
                size = self._index_safe_get(i, file_sizes, 0)

                file_upload = SubmissionFileUpload(key, name=name, description=description, size=size)
                files.append(file_upload)
            self.file_uploads = files
        return self.file_uploads


def score_type_to_string(score_type):
    """
    Converts the given score type into its string representation.
    """
    SCORE_TYPE_MAP = {
        PEER_TYPE: "Peer",
        SELF_TYPE: "Self",
        STAFF_TYPE: "Staff",
        }
    return SCORE_TYPE_MAP.get(score_type, "Unknown")

def parts_summary(assessment_obj):
    """
    Retrieves a summary of the parts from a given assessment object.
    """
    return [
        {
            'type': part.criterion.name,
            'score': part.points_earned,
            'score_type': part.option.name if part.option else "None",
        }
        for part in assessment_obj.parts.all()
    ]

def get_scorer_data(anonymous_scorer_id):
    """
    Retrieves the grader's data (full name, username, and email) based on their anonymous ID.
    """
    scorer_username = map_anonymized_ids_to_usernames([anonymous_scorer_id]).get(anonymous_scorer_id, "Unknown")
    scorer_name = map_anonymized_ids_to_fullname([anonymous_scorer_id]).get(anonymous_scorer_id, "Unknown")
    scorer_email = map_anonymized_ids_to_emails([anonymous_scorer_id]).get(anonymous_scorer_id, "Unknown")
    return scorer_name, scorer_username, scorer_email

def generate_assessment_data(assessment_list):
    results = []
    for assessment in assessment_list:

        scorer_name, scorer_username, scorer_email = get_scorer_data(assessment.scorer_id)

        assessment_data = {
            "idAssessment": str(assessment.id),
            "grader_name": scorer_name,
            "grader_username": scorer_username,
            "grader_email": scorer_email,
            "assesmentDate": assessment.scored_at.strftime('%d-%m-%Y'),
            "assesmentScores": parts_summary(assessment),
            "problemStep": score_type_to_string(assessment.score_type),
            "feedback": assessment.feedback or ''
        }

        results.append(assessment_data)
    return results

def generate_received_assessment_data(submission_uuid=None):
    """
    Generates a list of received assessments data based on the submission UUID.

    Args:
        submission_uuid (str, optional): The UUID of the submission. Defaults to None.

    Returns:
        list[dict]: A list containing assessment data dictionaries.
    """

    results = []

    submission = None
    if submission_uuid:
        submission = sub_api.get_submission_and_student(submission_uuid)

    if not submission:
        return results

    assessments = _use_read_replica(
        Assessment.objects.prefetch_related('parts').
        prefetch_related('rubric').
        filter(
            submission_uuid=submission['uuid']
        )
    )
    return generate_assessment_data(assessments)


def generate_given_assessment_data(item_id=None, submission_uuid=None):
    """
    Generates a list of given assessments data based on the submission UUID as scorer.

    Args:
        submission_uuid (str, optional): The UUID of the submission. Defaults to None.

    Returns:
        list[dict]: A list containing assessment data dictionaries.
    """
    results = []
    # Getting the scorer student id
    primary_submission = sub_api.get_submission_and_student(submission_uuid)

    if not primary_submission:
        return results

    scorer_student_id = primary_submission['student_item']['student_id']
    submissions = None
    if item_id:
        submissions = Submission.objects.filter(student_item__item_id=item_id).values('uuid')
        submission_uuids = [sub['uuid'] for sub in submissions]

    if not submission_uuids or not submissions:
        return results

    # Now fetch all assessments made by this student for these submissions
    assessments_made_by_student = _use_read_replica(
        Assessment.objects.prefetch_related('parts')
        .prefetch_related('rubric')
        .filter(scorer_id=scorer_student_id, submission_uuid__in=submission_uuids)
    )

    return generate_assessment_data(assessments_made_by_student)