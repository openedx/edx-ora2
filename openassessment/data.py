"""
Aggregate data for openassessment.
"""
import csv
import json
from submissions import api as sub_api
from openassessment.workflow.models import AssessmentWorkflow
from openassessment.assessment.models import AssessmentPart, AssessmentFeedback


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
            'criterion_name', 'option_name', 'feedback'
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

        Kwargs:
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
            parts = AssessmentPart.objects.select_related(
                'assessment', 'option', 'option__criterion'
            ).filter(assessment__submission_uuid=submission_uuid).order_by('assessment__pk')
            self._write_assessment_to_csv(parts, rubric_points_cache)

            feedback_query = AssessmentFeedback.objects.filter(
                submission_uuid=submission_uuid
            ).prefetch_related('options')
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
        total_results = AssessmentWorkflow.objects.filter(
            course_id=course_id
        ).count()

        while num_results < total_results:
            # Load a subset of the submission UUIDs
            # We're assuming that peer workflows are immutable,
            # so if we counted N at the start of the loop,
            # there should be >= N for us to process.
            end = start + self.QUERY_INTERVAL
            query = AssessmentWorkflow.objects.filter(
                course_id=course_id
            ).order_by('created').values('submission_uuid')[start:end]

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
        submission = sub_api.get_submission_and_student(submission_uuid)
        self._write_unicode('submission', [
            submission['uuid'],
            submission['student_item']['student_id'],
            submission['student_item']['item_id'],
            submission['submitted_at'],
            submission['created_at'],
            json.dumps(submission['answer'])
        ])

        score = sub_api.get_latest_score_for_submission(submission_uuid)
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
                part.option.name if part.option is not None else u"",
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
