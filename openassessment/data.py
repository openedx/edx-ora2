"""
Aggregate data for openassessment.
"""

from collections import defaultdict
from io import StringIO
from urllib.parse import urljoin
from zipfile import ZipFile
import csv
import json
import os

import requests

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F

from submissions import api as sub_api
from openassessment.assessment.models import Assessment, AssessmentFeedback, AssessmentPart
from openassessment.fileupload.api import get_download_url
from openassessment.workflow.models import AssessmentWorkflow, TeamAssessmentWorkflow


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

        rubric_points_cache = dict()
        feedback_option_set = set()
        for submission_uuid in self._submission_uuids(course_id):
            self._write_submission_to_csv(submission_uuid)

            # Django 1.4 doesn't follow reverse relations when using select_related,
            # so we select AssessmentPart and follow the foreign key to the Assessment.
            parts = self._use_read_replica(
                AssessmentPart.objects.select_related('assessment', 'option', 'option__criterion')
                .filter(assessment__submission_uuid=submission_uuid)
                .order_by('assessment__pk')
            )
            self._write_assessment_to_csv(parts, rubric_points_cache)

            feedback_query = self._use_read_replica(
                AssessmentFeedback.objects
                .filter(submission_uuid=submission_uuid)
                .prefetch_related('options')
            )
            for assessment_feedback in feedback_query:
                self._write_assessment_feedback_to_csv(assessment_feedback)
                feedback_option_set.update(set(
                    option for option in assessment_feedback.options.all()
                ))

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
        total_results = self._use_read_replica(
            AssessmentWorkflow.objects.filter(course_id=course_id)
        ).count()

        while num_results < total_results:
            # Load a subset of the submission UUIDs
            # We're assuming that peer workflows are immutable,
            # so if we counted N at the start of the loop,
            # there should be >= N for us to process.
            end = start + self.QUERY_INTERVAL
            query = self._use_read_replica(
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
                part.option.name if part.option is not None else u"",
                part.option.label if part.option is not None else u"",
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

    def _use_read_replica(self, queryset):
        """
        Use the read replica if it's available.

        Args:
            queryset (QuerySet)

        Returns:
            QuerySet

        """
        return (
            queryset.using("read_replica")
            if "read_replica" in settings.DATABASES
            else queryset
        )


class OraAggregateData:
    """
    Aggregate all the ORA data into a single table-like data structure.
    """

    @classmethod
    def _use_read_replica(cls, queryset):
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

    @classmethod
    def _usernames_enabled(cls):
        """
        Checks if toggle for deanonymized usernames in report enabled.
        """

        return settings.FEATURES.get('ENABLE_ORA_USERNAMES_ON_DATA_EXPORT', False)

    @classmethod
    def _map_anonymized_ids_to_usernames(cls, anonymized_ids):
        """
        Args:
            anonymized_ids - list of anonymized user ids.
        Returns:
            dictionary, that contains mapping between anonymized user ids and
            actual usernames.
        """
        User = get_user_model()

        users = cls._use_read_replica(
            User.objects.filter(anonymoususerid__anonymous_user_id__in=anonymized_ids)
            .annotate(anonymous_id=F("anonymoususerid__anonymous_user_id"))
            .values("username", "anonymous_id")
        )

        anonymous_id_to_username_mapping = {
            user["anonymous_id"]: user["username"] for user in users
        }

        return anonymous_id_to_username_mapping

    @classmethod
    def _map_sudents_and_scorers_ids_to_usernames(cls, all_submission_information):
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

        scorer_ids = cls._use_read_replica(
            Assessment.objects.filter(submission_uuid__in=submission_uuids).values_list(
                "scorer_id", flat=True
            )
        )

        return cls._map_anonymized_ids_to_usernames(student_ids + list(scorer_ids))

    @classmethod
    def _map_block_usage_keys_to_display_names(cls, course_id):
        """
        Fetches all course blocks and build mapping between block usage key
        string and block display name for those ones, whoose category is equal
        to ``openassessment``.

        Args:
            course_id (string or CourseLocator instance) - id of course
            resourse
        Returns:
            dictionary, that contains mapping between block usage
            keys (locations) and block display names.
        """
        # pylint: disable=import-error

        from lms.djangoapps.course_blocks.api import get_course_blocks
        from openedx.core.djangoapps.content.block_structure.transformers import BlockStructureTransformers

        from xmodule.modulestore.django import modulestore

        store = modulestore()
        course_usage_key = store.make_course_usage_key(course_id)

        # Passing an empty block structure transformer here to avoid user access checks
        blocks = get_course_blocks(None, course_usage_key, BlockStructureTransformers())

        block_display_name_map = {}

        for block_key in blocks:
            block_type = blocks.get_xblock_field(block_key, 'category')
            if block_type == 'openassessment':
                block_display_name_map[str(block_key)] = blocks.get_xblock_field(block_key, 'display_name')

        return block_display_name_map

    @classmethod
    def _build_assessments_cell(cls, assessments, usernames_map):
        """
        Args:
            assessments (QuerySet) - assessments that we would like to collate into one column.
            usernames_map - dictionary that maps anonymous ids to usernames.
        Returns:
            string that should be included in the 'assessments' column for this set of assessments' row
        """
        usernames_enabled = cls._usernames_enabled()

        returned_string = u""
        for assessment in assessments:
            returned_string += u"Assessment #{}\n".format(assessment.id)
            returned_string += u"-- scored_at: {}\n".format(assessment.scored_at)
            returned_string += u"-- type: {}\n".format(assessment.score_type)
            if usernames_enabled:
                returned_string += u"-- scorer_username: {}\n".format(usernames_map.get(assessment.scorer_id, ''))
            returned_string += u"-- scorer_id: {}\n".format(assessment.scorer_id)
            if assessment.feedback != u"":
                returned_string += u"-- overall_feedback: {}\n".format(assessment.feedback)
        return returned_string

    @classmethod
    def _build_assessments_parts_cell(cls, assessments):
        """
        Args:
            assessments (QuerySet) - assessments containing the parts that we would like to collate into one column.
        Returns:
            string that should be included in the relevant 'assessments_parts' column for this set of assessments' row
        """
        returned_string = u""
        for assessment in assessments:
            returned_string += u"Assessment #{}\n".format(assessment.id)
            for part in assessment.parts.order_by('criterion__order_num'):
                returned_string += u"-- {}".format(part.criterion.label)
                if part.option is not None and part.option.label is not None:
                    option_label = part.option.label
                    returned_string += u": {option_label} ({option_points})\n".format(
                        option_label=option_label, option_points=part.option.points
                    )
                if part.feedback != u"":
                    returned_string += u"-- feedback: {}\n".format(part.feedback)
        return returned_string

    @classmethod
    def _build_feedback_options_cell(cls, assessments):
        """
        Args:
            assessments (QuerySet) - assessment that we would like to use to fetch and read the feedback options.
        Returns:
            string that should be included in the relevant 'feedback_options' column for this set of assessments' row
        """

        returned_string = u""
        for assessment in assessments:
            for feedback in assessment.assessment_feedback.all():
                for option in feedback.options.all():
                    returned_string += option.text + u"\n"

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
            return u""
        return feedback.feedback_text

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
        usernames_enabled = cls._usernames_enabled()

        usernames_map = (
            cls._map_sudents_and_scorers_ids_to_usernames(all_submission_information)
            if usernames_enabled
            else {}
        )
        block_display_names_map = cls._map_block_usage_keys_to_display_names(course_id)

        rows = []
        for student_item, submission, score in all_submission_information:
            assessments = cls._use_read_replica(
                Assessment.objects.prefetch_related('parts').
                prefetch_related('rubric').
                filter(
                    submission_uuid=submission['uuid']
                )
            )
            assessments_cell = cls._build_assessments_cell(assessments, usernames_map)
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


class OraDownloadData:
    """
    Helper class, that is used for downloading and compressing data related
    to submissions (attachments, answer texts).
    """

    ATTACHMENT = 'attachment'
    TEXT = 'text'
    DOWNLOADS_CSV_HEADER = (
        'course_id',
        'block_id',
        'student_id',
        'key',
        'name',
        'type',
        'description',
        'size',
        'file_path',
    )

    @classmethod
    def _download_file_by_key(cls, key):
        download_url = urljoin(
            settings.LMS_ROOT_URL, get_download_url(key)
        )

        response = requests.get(download_url)
        response.raise_for_status()

        return response.content

    @classmethod
    def create_zip_with_attachments(cls, file, course_id, submission_files_data):
        """
        Opens given stream as a zip file and writes into it all submission
        attachments and csv with list of all downloads.

        Example of result zip file structure:
        ```
        .
        └── CourseId
            ├── BlockId1
            │   ├── StudentId1
            │   │   ├── attachments
            │   │   │   ├── SomeFile1
            │   │   │   └── SomeFile2
            │   │   ├── part_0.txt
            │   │   └── part_1.txt
            │   └── StudentId2
            │       ├── part_0.txt
            │       └── part_1.txt
            ├── BlockId2
            │   └── StudentId3
            │       ├── attachments
            │       │   └── SomeFile4
            │       └── part_0.txt
            └── downloads.csv
        ```
        """
        csv_output_buffer = StringIO()

        csvwriter = csv.DictWriter(csv_output_buffer, cls.DOWNLOADS_CSV_HEADER, extrasaction='ignore')
        csvwriter.writeheader()

        with ZipFile(file, 'w') as zip_file:
            for file_data in submission_files_data:
                file_content = (
                    cls._download_file_by_key(file_data['key'])
                    if file_data['type'] == cls.ATTACHMENT
                    else file_data['content']
                )

                zip_file.writestr(file_data['file_path'], file_content)
                csvwriter.writerow(file_data)

            downloads_csv_path = os.path.join(str(course_id), 'downloads.csv')

            zip_file.writestr(
                downloads_csv_path,
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

        all_submission_information = sub_api.get_all_course_submission_information(course_id, 'openassessment')

        for student, submission, _ in all_submission_information:
            answer = submission.get('answer', dict())

            # collecting submission attachments with metadata
            for index, file_key in enumerate(answer.get('file_keys', [])):
                # Old submissions (approx. pre-2020) have file names under the key "files_name",
                # and even older ones don't have file names at all
                file_names = answer.get('files_names', answer.get('files_name', []))
                try:
                    file_name = file_names[index]
                except IndexError:
                    file_name = "File_" + str(index + 1)

                # 'files_sizes' was added sometime around the beginning of 2020, so older submissions
                # will not have it
                file_size = 0
                file_sizes = answer.get('files_sizes')
                if file_sizes:
                    file_size = file_sizes[index]

                yield {
                    'type': cls.ATTACHMENT,
                    'course_id': course_id,
                    'block_id': student['item_id'],
                    'student_id': student['student_id'],
                    'key': file_key,
                    'name': file_name,
                    'description': answer['files_descriptions'][index],
                    'size': file_size,
                    'file_path': os.path.join(
                        str(course_id),
                        student['item_id'],
                        student['student_id'],
                        'attachments',
                        file_name,
                    )
                }

            # collecting submission answer texts
            for index, part in enumerate(answer.get('parts', [])):
                content = part['text']

                file_name = 'part_{}.txt'.format(index)

                yield {
                    'type': cls.TEXT,
                    'course_id': course_id,
                    'block_id': student['item_id'],
                    'student_id': student['student_id'],
                    'key': '',
                    'name': file_name,
                    'description': 'Submission text.',
                    'content': content,
                    'size': len(content),
                    'file_path': os.path.join(
                        str(course_id),
                        student['item_id'],
                        student['student_id'],
                        file_name,
                    )
                }
