"""
Aggregate data for openassessment.
"""
import csv
import json

from django.conf import settings
from submissions import api as sub_api
from openassessment.workflow.models import AssessmentWorkflow
from openassessment.assessment.models import Assessment, AssessmentPart, AssessmentFeedback


class CsvWriter(object):
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
            for key, file_handle in output_streams.iteritems()
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
        for name, writer in self.writers.iteritems():
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
            unicode(option.id) for option in assessment_feedback.options.all()
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
            encoded_row = [unicode(field).encode('utf-8') for field in row]
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


class OraAggregateData(object):
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
    def _build_assessments_cell(cls, assessments):
        """
        Args:
            assessments (QuerySet) - assessments that we would like to collate into one column.
        Returns:
            string that should be included in the 'assessments' column for this set of assessments' row
        """
        returned_string = u""
        for assessment in assessments:
            returned_string += u"Assessment #{}\n".format(assessment.id)
            returned_string += u"-- scored_at: {}\n".format(assessment.scored_at)
            returned_string += u"-- type: {}\n".format(assessment.score_type)
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

        all_submission_information = sub_api.get_all_course_submission_information(course_id, 'openassessment')

        rows = []
        for student_item, submission, score in all_submission_information:
            row = []
            assessments = cls._use_read_replica(
                Assessment.objects.prefetch_related('parts').
                prefetch_related('rubric').
                filter(
                    submission_uuid=submission['uuid']
                )
            )
            assessments_cell = cls._build_assessments_cell(assessments)
            assessments_parts_cell = cls._build_assessments_parts_cell(assessments)
            feedback_options_cell = cls._build_feedback_options_cell(assessments)
            feedback_cell = cls._build_feedback_cell(submission['uuid'])

            row = [
                submission['uuid'],
                submission['student_item'],
                student_item['student_id'],
                submission['submitted_at'],
                submission['answer'],
                assessments_cell,
                assessments_parts_cell,
                score.get('created_at', ''),
                score.get('points_earned', ''),
                score.get('points_possible', ''),
                feedback_options_cell,
                feedback_cell
            ]
            rows.append(row)

        header = [
            'Submission ID',
            'Item ID',
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
    def collect_ora2_responses(cls, course_id):
        """
        Get information about all ora2 blocks in the course with response count for each step

        Args:
            course_id (string) - the course id of the course whose data we would like to return

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
        except_statuses = ['ai', 'cancelled']
        statuses = [st for st in AssessmentWorkflow().STATUS_VALUES if st not in except_statuses]
        statuses.append('total')

        items = AssessmentWorkflow.objects.filter(course_id=course_id).values('item_id', 'status')

        result = {}
        for item in items:
            item_id = item['item_id']
            status = item['status']
            if item_id not in result:
                result[item_id] = {}
                for st in statuses:
                    result[item_id][st] = 0
            if status in statuses:
                result[item_id][status] += 1
                result[item_id]['total'] += 1

        return result
