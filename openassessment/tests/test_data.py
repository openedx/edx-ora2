# -*- coding: utf-8 -*-
"""
Tests for openassessment data aggregation.
"""

import os.path

from StringIO import StringIO
import csv
from django.core.management import call_command
import ddt
from submissions import api as sub_api
from openassessment.test_utils import TransactionCacheResetTest
from openassessment.tests.factories import *  # pylint: disable=wildcard-import
from openassessment.workflow import api as workflow_api
from openassessment.data import CsvWriter, OraAggregateData
import openassessment.assessment.api.peer as peer_api


COURSE_ID = "Test_Course"

STUDENT_ID = "Student"
STUDENT_ID2 = "Student2"
STUDENT_ID3 = "Student3"

SCORER_ID = "Scorer"

ITEM_ID = "item_one"
ITEM_ID2 = "item_two"
ITEM_ID3 = "item_three"

STUDENT_ITEM = dict(
    student_id=STUDENT_ID,
    course_id=COURSE_ID,
    item_id=ITEM_ID,
    item_type="openassessment"
)

SCORER_ITEM = dict(
    student_id=SCORER_ID,
    course_id=COURSE_ID,
    item_id=ITEM_ID,
    item_type="openassessment"
)

ANSWER = u"THIS IS A TEST ANSWER"

STEPS = ['peer']

RUBRIC_DICT = {
    "criteria": [
        {
            "name": "criterion_1",
            "label": "criterion_1",
            "prompt": "Did the writer keep it secret?",
            "options": [
                {"name": "option_1", "points": "0", "explanation": ""},
                {"name": "option_2", "points": "1", "explanation": ""},
            ]
        },
        {
            "name": u"criterion_2",
            "label": u"criterion_2",
            "prompt": "Did the writer keep it safe?",
            "options": [
                {"name": "option_1", "label": "option_1", "points": "0", "explanation": ""},
                {"name": "option_2", "label": "option_2", "points": "1", "explanation": ""},
            ]
        },
    ]
}

ASSESSMENT_DICT = {
    'overall_feedback': u"这是中国",
    'criterion_feedback': {
        "criterion_2": u"𝓨𝓸𝓾 𝓼𝓱𝓸𝓾𝓵𝓭𝓷'𝓽 𝓰𝓲𝓿𝓮 𝓾𝓹!"
    },
    'options_selected': {
        "criterion_1": "option_1",
        "criterion_2": "option_2",
    },
}

FEEDBACK_TEXT = u"𝓨𝓸𝓾 𝓼𝓱𝓸𝓾𝓵𝓭𝓷'𝓽 𝓰𝓲𝓿𝓮 𝓾𝓹!"

FEEDBACK_OPTIONS = {
    "feedback_text": FEEDBACK_TEXT,
    "options": [
        'I disliked this assessment',
        'I felt this assessment was unfair',
    ]
}


@ddt.ddt
class CsvWriterTest(TransactionCacheResetTest):
    """
    Test for writing openassessment data to CSV.
    """
    longMessage = True
    maxDiff = None

    @ddt.file_data('data/write_to_csv.json')
    def test_write_to_csv(self, data):
        # Create in-memory buffers for the CSV file data
        output_streams = self._output_streams(data['expected_csv'].keys())

        # Load the database fixture
        # We use the database fixture to ensure that this test will
        # catch backwards-compatibility issues even if the Django model
        # implementation or API calls change.
        self._load_fixture(data['fixture'])

        # Write the data to CSV
        writer = CsvWriter(output_streams)
        writer.write_to_csv(data['course_id'])

        # Check that the CSV matches what we expected
        for output_name, expected_csv in data['expected_csv'].iteritems():
            output_buffer = output_streams[output_name]
            output_buffer.seek(0)
            actual_csv = csv.reader(output_buffer)
            for expected_row in expected_csv:
                try:
                    actual_row = actual_csv.next()
                except StopIteration:
                    actual_row = None
                self.assertEqual(
                    actual_row, expected_row,
                    msg="Output name: {}".format(output_name)
                )

            # Check for extra rows
            try:
                extra_row = actual_csv.next()
            except StopIteration:
                extra_row = None

            if extra_row is not None:
                self.fail(u"CSV contains extra row: {}".format(extra_row))

    def test_many_submissions(self):
        # Create a lot of submissions
        num_submissions = 234
        for index in range(num_submissions):
            student_item = {
                'student_id': "test_user_{}".format(index),
                'course_id': 'test_course',
                'item_id': 'test_item',
                'item_type': 'openassessment',
            }
            submission_text = "test submission {}".format(index)
            submission = sub_api.create_submission(student_item, submission_text)
            workflow_api.create_workflow(submission['uuid'], ['peer', 'self'])

        # Generate a CSV file for the submissions
        output_streams = self._output_streams(['submission'])
        writer = CsvWriter(output_streams)
        writer.write_to_csv('test_course')

        # Parse the generated CSV
        content = output_streams['submission'].getvalue()
        rows = content.split('\n')

        # Remove the first row (header) and last row (blank line)
        rows = rows[1:-1]

        # Check that we have the right number of rows
        self.assertEqual(len(rows), num_submissions)

    def test_other_course_id(self):
        # Try a course ID with no submissions
        self._load_fixture('db_fixtures/scored.json')
        output_streams = self._output_streams(CsvWriter.MODELS)
        writer = CsvWriter(output_streams)
        writer.write_to_csv('other_course')

        # Expect that each output has only two lines (the header and a blank line)
        # since this course has no submissions
        for output in output_streams.values():
            content = output.getvalue()
            rows = content.split('\n')
            self.assertEqual(len(rows), 2)

    def test_unicode(self):
        # Flush out unicode errors
        self._load_fixture('db_fixtures/unicode.json')
        output_streams = self._output_streams(CsvWriter.MODELS)
        CsvWriter(output_streams).write_to_csv(u"𝓽𝓮𝓼𝓽_𝓬𝓸𝓾𝓻𝓼𝓮")

        # Check that data ended up in the reports
        for output in output_streams.values():
            content = output.getvalue()
            rows = content.split('\n')
            self.assertGreater(len(rows), 2)

    def _output_streams(self, names):
        """
        Create in-memory buffers.

        Args:
            names (list of unicode): The output names.

        Returns:
            dict: map of output names to StringIO objects.

        """
        output_streams = dict()

        for output_name in names:
            output_buffer = StringIO()
            self.addCleanup(output_buffer.close)
            output_streams[output_name] = output_buffer

        return output_streams

    def _load_fixture(self, fixture_relpath):
        """
        Load a database fixture into the test database.

        Args:
            fixture_relpath (unicode): Path to the fixture,
                relative to the test/data directory.

        Returns:
            None
        """
        fixture_path = os.path.join(
            os.path.dirname(__file__), 'data', fixture_relpath
        )
        print "Loading database fixtures from {}".format(fixture_path)
        call_command('loaddata', fixture_path)


@ddt.ddt
class TestOraAggregateData(TransactionCacheResetTest):
    """
    Test the component parts of OraAggregateData
    """

    def _build_criteria_and_assessment_parts(self, num_criteria=1, feedback=""):
        """ Build a set of criteria and assessment parts for the rubric. """
        rubric = RubricFactory()
        criteria = [CriterionFactory(rubric=rubric, order_num=n-1) for n in range(num_criteria)]

        criterion_options = []
        # for every criterion, make a criterion option
        for criterion in criteria:
            criterion_options.append(CriterionOptionFactory(criterion=criterion))

        assessment = AssessmentFactory(rubric=rubric, feedback=feedback)
        for criterion, option in zip(criteria, criterion_options):
            AssessmentPartFactory(assessment=assessment, criterion=criterion, option=option, feedback=feedback)
        return assessment

    def _assessment_cell(self, assessment, feedback=""):
        """ Build a string for the given assessment information. """
        cell = "Assessment #{id}\n-- scored_at: {scored_at}\n-- type: {type}\n-- scorer_id: {scorer}\n".format(
            id=assessment.id,
            scored_at=assessment.scored_at,
            type=assessment.score_type,
            scorer=assessment.scorer_id
        )
        if feedback:
            cell += "-- overall_feedback: {}\n".format(feedback)
        return cell

    def test_build_assessments_cell(self):
        # One assessment
        assessment1 = self._build_criteria_and_assessment_parts()

        # pylint: disable=protected-access
        assessment_cell = OraAggregateData._build_assessments_cell([assessment1])

        a1_cell = self._assessment_cell(assessment1)
        self.assertEqual(assessment_cell, a1_cell)

        # Multiple assessments
        assessment2 = self._build_criteria_and_assessment_parts(feedback="Test feedback")

        # pylint: disable=protected-access
        assessment_cell = OraAggregateData._build_assessments_cell([assessment1, assessment2])

        a2_cell = self._assessment_cell(assessment2, feedback="Test feedback")

        self.assertEqual(assessment_cell, a1_cell + a2_cell)

    def _assessment_part_cell(self, assessment_part, feedback=""):
        """ Build the string representing an assessment part. """

        cell = "-- {criterion_label}: {option_label} ({option_points})\n".format(
            criterion_label=assessment_part.criterion.label,
            option_label=assessment_part.option.label,
            option_points=assessment_part.option.points,
        )
        if feedback:
            cell += "-- feedback: {}\n".format(feedback)
        return cell

    def test_build_assessments_parts_cell(self):
        assessment1 = self._build_criteria_and_assessment_parts()
        a1_cell = "Assessment #{}\n".format(assessment1.id)  # pylint: disable=no-member

        for part in assessment1.parts.all():  # pylint: disable=no-member
            a1_cell += self._assessment_part_cell(part)

        # pylint: disable=protected-access
        assessment_part_cell = OraAggregateData._build_assessments_parts_cell([assessment1])
        self.assertEqual(a1_cell, assessment_part_cell)

        # Second assessment with 2 component parts and individual option feedback
        assessment2 = self._build_criteria_and_assessment_parts(num_criteria=2, feedback="Test feedback")
        a2_cell = "Assessment #{}\n".format(assessment2.id)  # pylint: disable=no-member

        for part in assessment2.parts.all():  # pylint: disable=no-member
            a2_cell += self._assessment_part_cell(part, feedback="Test feedback")

        # pylint: disable=protected-access
        assessment_part_cell = OraAggregateData._build_assessments_parts_cell([assessment1, assessment2])
        self.assertEqual(assessment_part_cell, a1_cell + a2_cell)

    def test_build_feedback_options_cell(self):
        # Test with one assessment and one option
        assessment1 = AssessmentFactory()
        option1_text = "Test Feedback"
        option1 = AssessmentFeedbackOptionFactory(text=option1_text)
        AssessmentFeedbackFactory(assessments=(assessment1,), options=(option1,))
        # pylint: disable=protected-access
        feedback_option_cell = OraAggregateData._build_feedback_options_cell([assessment1])

        self.assertEqual(feedback_option_cell, option1_text+'\n')

        assessment2 = AssessmentFactory()
        option2_text = "More test feedback"
        option2 = AssessmentFeedbackOptionFactory(text=option2_text)
        AssessmentFeedbackFactory(assessments=(assessment2,), options=(option1, option2))
        # pylint: disable=protected-access
        feedback_option_cell = OraAggregateData._build_feedback_options_cell([assessment1, assessment2])

        self.assertEqual(feedback_option_cell, "\n".join([option1_text, option1_text, option2_text]) + "\n")

    def test_build_feedback_cell(self):

        assessment1 = AssessmentFactory()
        test_text = "Test feedback text"
        AssessmentFeedbackFactory(
            assessments=(assessment1,),
            feedback_text=test_text,
            submission_uuid=assessment1.submission_uuid
        )
        # pylint: disable=protected-access
        feedback_cell = OraAggregateData._build_feedback_cell(assessment1.submission_uuid)

        self.assertEqual(feedback_cell, test_text)

        assessment2 = AssessmentFactory()
        # pylint: disable=protected-access
        feedback_cell = OraAggregateData._build_feedback_cell(assessment2.submission_uuid)

        self.assertEqual(feedback_cell, "")


class TestOraAggregateDataIntegration(TransactionCacheResetTest):
    """
    Test that OraAggregateData behaves as expected when integrated.
    """

    def setUp(self):
        super(TestOraAggregateDataIntegration, self).setUp()
        # Create submissions and assessments
        self.submission = self._create_submission(STUDENT_ITEM)
        self.scorer_submission = self._create_submission(SCORER_ITEM)
        self.earned_points = 1
        self.possible_points = 2
        peer_api.get_submission_to_assess(self.scorer_submission['uuid'], 1)
        self.assessment = self._create_assessment(self.scorer_submission['uuid'])

        sub_api.set_score(self.submission['uuid'], self.earned_points, self.possible_points)
        self.score = sub_api.get_score(STUDENT_ITEM)
        peer_api.get_score(self.submission['uuid'], {'must_be_graded_by': 1, 'must_grade': 0})
        self._create_assessment_feedback(self.submission['uuid'])

    def _create_submission(self, student_item_dict, steps=None):
        """
        Creates a submission and initializes a peer grading workflow.
        """
        submission = sub_api.create_submission(student_item_dict, ANSWER)
        submission_uuid = submission['uuid']
        peer_api.on_start(submission_uuid)
        workflow_api.create_workflow(submission_uuid, steps if steps else STEPS)
        return submission

    def _create_assessment(self, submission_uuid):
        """
        Creates an assessment for the given submission.
        """
        return peer_api.create_assessment(
            submission_uuid,
            "scorer",
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            2
        )

    def _create_assessment_feedback(self, submission_uuid):
        """
        Creates an assessment for the given submission.
        """
        feedback_dict = FEEDBACK_OPTIONS.copy()
        feedback_dict['submission_uuid'] = submission_uuid
        peer_api.set_assessment_feedback(feedback_dict)

    def test_collect_ora2_data(self):
        headers, data = OraAggregateData.collect_ora2_data(COURSE_ID)

        self.assertEqual(headers, [
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
        ])


        self.assertEqual(data[0], [
            self.scorer_submission['uuid'],
            self.scorer_submission['student_item'],
            SCORER_ID,
            self.scorer_submission['submitted_at'],
            self.scorer_submission['answer'],
            u'',
            u'',
            u'',
            u'',
            u'',
            u'',
            u'',
        ])

        self.assertEqual(data[1], [
            self.submission['uuid'],
            self.submission['student_item'],
            STUDENT_ID,
            self.submission['submitted_at'],
            self.submission['answer'],
            u"Assessment #{id}\n-- scored_at: {scored_at}\n-- type: PE\n".format(
                id=self.assessment['id'],
                scored_at=self.assessment['scored_at'],
            ) +
            u"-- scorer_id: {scorer}\n-- overall_feedback: {feedback}\n".format(
                scorer=self.assessment['scorer_id'],
                feedback=self.assessment['feedback']
            ),
            u"Assessment #{id}\n-- {label}: {option_label} ({points})\n".format(
                id=self.assessment['id'],
                label=self.assessment['parts'][1]['criterion']['label'],
                option_label=self.assessment['parts'][1]['criterion']['options'][0]['label'],
                points=self.assessment['parts'][1]['criterion']['options'][0]['points'],
            ) +
            u"-- {label}: {option_label} ({points})\n-- feedback: {feedback}\n".format(
                label=self.assessment['parts'][0]['criterion']['label'],
                option_label=self.assessment['parts'][0]['criterion']['options'][1]['label'],
                points=self.assessment['parts'][0]['criterion']['options'][1]['points'],
                feedback=self.assessment['parts'][0]['feedback'],
            ),
            self.score['created_at'],
            self.score['points_earned'],
            self.score['points_possible'],
            FEEDBACK_OPTIONS['options'][0] + '\n' + FEEDBACK_OPTIONS['options'][1]+'\n',
            FEEDBACK_TEXT,
        ])

    def test_collect_ora2_responses(self):
        self._create_submission(dict(
            student_id=STUDENT_ID,
            course_id=COURSE_ID,
            item_id=ITEM_ID2,
            item_type="openassessment"
        ), ['self'])
        self._create_submission(dict(
            student_id=STUDENT_ID2,
            course_id=COURSE_ID,
            item_id=ITEM_ID2,
            item_type="openassessment"
        ), STEPS)

        self._create_submission(dict(
            student_id=STUDENT_ID,
            course_id=COURSE_ID,
            item_id=ITEM_ID3,
            item_type="openassessment"
        ), ['self'])
        self._create_submission(dict(
            student_id=STUDENT_ID2,
            course_id=COURSE_ID,
            item_id=ITEM_ID3,
            item_type="openassessment"
        ), ['self'])
        self._create_submission(dict(
            student_id=STUDENT_ID3,
            course_id=COURSE_ID,
            item_id=ITEM_ID3,
            item_type="openassessment"
        ), STEPS)

        data = OraAggregateData.collect_ora2_responses(COURSE_ID)

        self.assertIn(ITEM_ID, data)
        self.assertIn(ITEM_ID2, data)
        self.assertIn(ITEM_ID3, data)
        for item in [ITEM_ID, ITEM_ID2, ITEM_ID3]:
            self.assertEqual({'total', 'training', 'peer', 'self', 'staff', 'waiting', 'done'}, set(data[item].keys()))
        self.assertEqual(data[ITEM_ID], {
            'total': 2, 'training': 0, 'peer': 2, 'self': 0, 'staff': 0, 'waiting': 0, 'done': 0
        })
        self.assertEqual(data[ITEM_ID2], {
            'total': 2, 'training': 0, 'peer': 1, 'self': 1, 'staff': 0, 'waiting': 0, 'done': 0
        })
        self.assertEqual(data[ITEM_ID3], {
            'total': 3, 'training': 0, 'peer': 1, 'self': 2, 'staff': 0, 'waiting': 0, 'done': 0
        })
