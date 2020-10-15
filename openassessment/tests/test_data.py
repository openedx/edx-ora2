# -*- coding: utf-8 -*-
"""
Tests for openassessment data aggregation.
"""

import csv
from io import StringIO, BytesIO
import json
import os.path
import zipfile

import ddt
from mock import call, Mock, patch

from django.core.management import call_command

from submissions import api as sub_api, team_api as team_sub_api
import openassessment.assessment.api.peer as peer_api
from openassessment.data import CsvWriter, OraAggregateData, OraDownloadData
from openassessment.test_utils import TransactionCacheResetTest
from openassessment.tests.factories import *  # pylint: disable=wildcard-import
from openassessment.workflow import api as workflow_api, team_api as team_workflow_api


COURSE_ID = "Test_Course"

STUDENT_ID = u"Student"
OLD_STUDENT_ID = "Old_Student"

STUDENT_USERNAME = "Student Username"

SCORER_ID = "Scorer"

SCORER_USERNAME = "Scorer Username"

TEST_SCORER_ID = "Test Scorer"

TEST_SCORER_USERNAME = "Test Scorer Username"

USERNAME_MAPPING = {
    STUDENT_ID: STUDENT_USERNAME,
    SCORER_ID: SCORER_USERNAME,
    TEST_SCORER_ID: TEST_SCORER_USERNAME,
}

ITEM_ID = "item"

ITEM_DISPLAY_NAME = "Open Response Assessment"

STUDENT_ITEM = dict(
    student_id=STUDENT_ID,
    course_id=COURSE_ID,
    item_id=ITEM_ID,
    item_type="openassessment"
)

OLD_STUDENT_ITEM = dict(
    student_id=OLD_STUDENT_ID,
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

ITEM_DISPLAY_NAMES_MAPPING = {
    SCORER_ITEM['item_id']: ITEM_DISPLAY_NAME,
    STUDENT_ITEM['item_id']: ITEM_DISPLAY_NAME
}

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
        u'I disliked this assessment',
        u'I felt this assessment was unfair',
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
        output_streams = self._output_streams(list(data['expected_csv'].keys()))

        # Load the database fixture
        # We use the database fixture to ensure that this test will
        # catch backwards-compatibility issues even if the Django model
        # implementation or API calls change.
        self._load_fixture(data['fixture'])

        # Write the data to CSV
        writer = CsvWriter(output_streams)
        writer.write_to_csv(data['course_id'])

        # Check that the CSV matches what we expected
        for output_name, expected_csv in data['expected_csv'].items():
            output_buffer = output_streams[output_name]
            output_buffer.seek(0)
            actual_csv = csv.reader(output_buffer)
            for expected_row in expected_csv:
                try:
                    actual_row = next(actual_csv)
                except StopIteration:
                    actual_row = None
                self.assertEqual(
                    actual_row, expected_row,
                    msg=u"Output name: {}".format(output_name)
                )

            # Check for extra rows
            try:
                extra_row = next(actual_csv)
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
            submission_text = u"test submission {}".format(index)
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
        print(u"Loading database fixtures from {}".format(fixture_path))
        call_command('loaddata', fixture_path)


@ddt.ddt
@patch.dict('django.conf.settings.FEATURES', {'ENABLE_ORA_USERNAMES_ON_DATA_EXPORT': True})
class TestOraAggregateData(TransactionCacheResetTest):
    """
    Test the component parts of OraAggregateData
    """

    def _build_criteria_and_assessment_parts(self, num_criteria=1, feedback=""):
        """ Build a set of criteria and assessment parts for the rubric. """
        rubric = RubricFactory()
        criteria = [CriterionFactory(rubric=rubric, order_num=n + 1) for n in range(num_criteria)]

        criterion_options = []
        # for every criterion, make a criterion option
        for criterion in criteria:
            criterion_options.append(CriterionOptionFactory(criterion=criterion))

        assessment = AssessmentFactory(rubric=rubric, feedback=feedback, scorer_id=TEST_SCORER_ID)
        for criterion, option in zip(criteria, criterion_options):
            AssessmentPartFactory(assessment=assessment, criterion=criterion, option=option, feedback=feedback)
        return assessment

    def _assessment_cell(self, assessment, feedback=""):
        """ Build a string for the given assessment information. """
        cell = u"Assessment #{id}\n" \
               u"-- scored_at: {scored_at}\n" \
               u"-- type: {type}\n" \
               u"-- scorer_username: {scorer_username}\n" \
               u"-- scorer_id: {scorer_id}\n"\
            .format(
                id=assessment.id,
                scored_at=assessment.scored_at,
                type=assessment.score_type,
                scorer_username=USERNAME_MAPPING[assessment.scorer_id],
                scorer_id=assessment.scorer_id,
            )
        if feedback:
            cell += u"-- overall_feedback: {}\n".format(feedback)
        return cell

    def test_map_anonymized_ids_to_usernames(self):
        with patch('openassessment.data.get_user_model') as get_user_model_mock:
            get_user_model_mock.return_value.objects.filter.return_value.annotate.return_value.values.return_value = [
                {'anonymous_id': STUDENT_ID, 'username': STUDENT_USERNAME},
                {'anonymous_id': SCORER_ID, 'username': SCORER_USERNAME},
                {'anonymous_id': TEST_SCORER_ID, 'username': TEST_SCORER_USERNAME},
            ]

            # pylint: disable=protected-access
            mapping = OraAggregateData._map_anonymized_ids_to_usernames([STUDENT_ID, SCORER_ID, TEST_SCORER_ID])

        self.assertEqual(mapping, USERNAME_MAPPING)

    def test_map_sudents_and_scorers_ids_to_usernames(self):
        test_submission_information = [
            (
                dict(
                    student_id=STUDENT_ID,
                    course_id=COURSE_ID,
                    item_id="some_id",
                    item_type="openassessment",
                ),
                sub_api.create_submission(STUDENT_ITEM, ANSWER),
                (),
            ),
            (
                dict(
                    student_id=SCORER_ID,
                    course_id=COURSE_ID,
                    item_id="some_id",
                    item_type="openassessment",
                ),
                sub_api.create_submission(SCORER_ITEM, ANSWER),
                (),
            ),
        ]

        with patch("openassessment.data.OraAggregateData._map_anonymized_ids_to_usernames") as map_mock:
            # pylint: disable=protected-access
            OraAggregateData._map_sudents_and_scorers_ids_to_usernames(
                test_submission_information
            )
            map_mock.assert_called_once_with([STUDENT_ID, SCORER_ID])

    def test_build_assessments_cell(self):
        # One assessment
        assessment1 = self._build_criteria_and_assessment_parts()

        # pylint: disable=protected-access
        assessment_cell = OraAggregateData._build_assessments_cell([assessment1], USERNAME_MAPPING)

        a1_cell = self._assessment_cell(assessment1)
        self.assertEqual(assessment_cell, a1_cell)

        # Multiple assessments
        assessment2 = self._build_criteria_and_assessment_parts(feedback="Test feedback")

        # pylint: disable=protected-access
        assessment_cell = OraAggregateData._build_assessments_cell([assessment1, assessment2], USERNAME_MAPPING)

        a2_cell = self._assessment_cell(assessment2, feedback="Test feedback")

        self.assertEqual(assessment_cell, a1_cell + a2_cell)

    def _assessment_part_cell(self, assessment_part, feedback=""):
        """ Build the string representing an assessment part. """

        cell = u"-- {criterion_label}: {option_label} ({option_points})\n".format(
            criterion_label=assessment_part.criterion.label,
            option_label=assessment_part.option.label,
            option_points=assessment_part.option.points,
        )
        if feedback:
            cell += u"-- feedback: {}\n".format(feedback)
        return cell

    def test_build_assessments_parts_cell(self):
        assessment1 = self._build_criteria_and_assessment_parts()
        a1_cell = u"Assessment #{}\n".format(assessment1.id)

        for part in assessment1.parts.all():
            a1_cell += self._assessment_part_cell(part)

        # pylint: disable=protected-access
        assessment_part_cell = OraAggregateData._build_assessments_parts_cell([assessment1])
        self.assertEqual(a1_cell, assessment_part_cell)

        # Second assessment with 2 component parts and individual option feedback
        assessment2 = self._build_criteria_and_assessment_parts(num_criteria=2, feedback="Test feedback")
        a2_cell = u"Assessment #{}\n".format(assessment2.id)

        for part in assessment2.parts.all():
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

        self.assertEqual(feedback_option_cell, option1_text + '\n')

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


@ddt.ddt
@patch.dict('django.conf.settings.FEATURES', {'ENABLE_ORA_USERNAMES_ON_DATA_EXPORT': True})
@patch(
    'openassessment.data.OraAggregateData._map_block_usage_keys_to_display_names',
    Mock(return_value=ITEM_DISPLAY_NAMES_MAPPING)
)
class TestOraAggregateDataIntegration(TransactionCacheResetTest):
    """
    Test that OraAggregateData behaves as expected when integrated.
    """

    def setUp(self):
        super(TestOraAggregateDataIntegration, self).setUp()
        self.maxDiff = None  # pylint: disable=invalid-name
        # Create submissions and assessments
        self.submission = self._create_submission(STUDENT_ITEM)
        self.scorer_submission = self._create_submission(SCORER_ITEM)
        self.earned_points = 1
        self.possible_points = 2
        peer_api.get_submission_to_assess(self.scorer_submission['uuid'], 1)
        self.assessment = self._create_assessment(self.scorer_submission['uuid'])
        self.assertEqual(self.assessment['parts'][0]['criterion']['label'], "criterion_1")

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

    def _create_team_submission(self, course_id, item_id, team_id, submitting_user_id, team_member_student_ids):
        """
        Create a team submission and initialize a team workflow
        """
        team_submission = team_sub_api.create_submission_for_team(
            course_id,
            item_id,
            team_id,
            submitting_user_id,
            team_member_student_ids,
            ANSWER,
        )
        team_workflow_api.create_workflow(team_submission['team_submission_uuid'])
        return team_submission

    def _create_assessment(self, submission_uuid):
        """
        Creates an assessment for the given submission.
        """
        return peer_api.create_assessment(
            submission_uuid,
            SCORER_ID,
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

    def _other_student(self, no_of_student):
        """
        n is an integer to postfix, for example _other_student(3) would return "Student_3"
        """
        return STUDENT_ID + '_' + str(no_of_student)

    def _other_item(self, no_of_student):
        """
        n is an integer to postfix, for example _other_item(4) would return "item_4"
        """
        return ITEM_ID + '_' + str(no_of_student)

    def test_collect_ora2_data(self):
        with patch('openassessment.data.OraAggregateData._map_anonymized_ids_to_usernames') as map_mock:
            map_mock.return_value = USERNAME_MAPPING
            headers, data = OraAggregateData.collect_ora2_data(COURSE_ID)

        self.assertEqual(headers, [
            'Submission ID',
            'Location',
            'Problem Name',
            'Item ID',
            'Username',
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
            ITEM_ID,
            ITEM_DISPLAY_NAME,
            self.scorer_submission['student_item'],
            SCORER_USERNAME,
            SCORER_ID,
            self.scorer_submission['submitted_at'],
            json.dumps(self.scorer_submission['answer']),
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
            ITEM_ID,
            ITEM_DISPLAY_NAME,
            self.submission['student_item'],
            STUDENT_USERNAME,
            STUDENT_ID,
            self.submission['submitted_at'],
            json.dumps(self.submission['answer']),
            u"Assessment #{id}\n-- scored_at: {scored_at}\n-- type: PE\n".format(
                id=self.assessment['id'],
                scored_at=self.assessment['scored_at'],
            ) + u"-- scorer_username: {scorer_username}\n".format(
                scorer_username=USERNAME_MAPPING[self.assessment['scorer_id']]
            ) + u"-- scorer_id: {scorer_id}\n-- overall_feedback: {feedback}\n".format(
                scorer_id=self.assessment['scorer_id'],
                feedback=self.assessment['feedback']
            ),
            u"Assessment #{id}\n-- {label}: {option_label} ({points})\n".format(
                id=self.assessment['id'],
                label=self.assessment['parts'][0]['criterion']['label'],
                option_label=self.assessment['parts'][0]['criterion']['options'][0]['label'],
                points=self.assessment['parts'][0]['criterion']['options'][0]['points'],
            ) + u"-- {label}: {option_label} ({points})\n-- feedback: {feedback}\n".format(
                label=self.assessment['parts'][1]['criterion']['label'],
                option_label=self.assessment['parts'][1]['criterion']['options'][1]['label'],
                points=self.assessment['parts'][1]['criterion']['options'][1]['points'],
                feedback=self.assessment['parts'][1]['feedback'],
            ),
            self.score['created_at'],
            self.score['points_earned'],
            self.score['points_possible'],
            FEEDBACK_OPTIONS['options'][0] + '\n' + FEEDBACK_OPTIONS['options'][1] + '\n',
            FEEDBACK_TEXT,
        ])

    def test_collect_ora2_data_when_usernames_disabled(self):
        """
        Tests that ``OraAggregateData.collect_ora2_data`` generated report
        without usernames when `ENABLE_ORA_USERNAMES_ON_DATA_EXPORT`
        settings toggle equals ``False``.
        """

        with patch.dict('django.conf.settings.FEATURES', {'ENABLE_ORA_USERNAMES_ON_DATA_EXPORT': False}):
            headers, data = OraAggregateData.collect_ora2_data(COURSE_ID)

        self.assertEqual(headers, [
            'Submission ID',
            'Location',
            'Problem Name',
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
            ITEM_ID,
            ITEM_DISPLAY_NAME,
            self.scorer_submission['student_item'],
            SCORER_ID,
            self.scorer_submission['submitted_at'],
            json.dumps(self.scorer_submission['answer']),
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
            ITEM_ID,
            ITEM_DISPLAY_NAME,
            self.submission['student_item'],
            STUDENT_ID,
            self.submission['submitted_at'],
            json.dumps(self.submission['answer']),
            u"Assessment #{id}\n-- scored_at: {scored_at}\n-- type: PE\n".format(
                id=self.assessment['id'],
                scored_at=self.assessment['scored_at'],
            ) + u"-- scorer_id: {scorer_id}\n-- overall_feedback: {feedback}\n".format(
                scorer_id=self.assessment['scorer_id'],
                feedback=self.assessment['feedback']
            ),
            u"Assessment #{id}\n-- {label}: {option_label} ({points})\n".format(
                id=self.assessment['id'],
                label=self.assessment['parts'][0]['criterion']['label'],
                option_label=self.assessment['parts'][0]['criterion']['options'][0]['label'],
                points=self.assessment['parts'][0]['criterion']['options'][0]['points'],
            ) + u"-- {label}: {option_label} ({points})\n-- feedback: {feedback}\n".format(
                label=self.assessment['parts'][1]['criterion']['label'],
                option_label=self.assessment['parts'][1]['criterion']['options'][1]['label'],
                points=self.assessment['parts'][1]['criterion']['options'][1]['points'],
                feedback=self.assessment['parts'][1]['feedback'],
            ),
            self.score['created_at'],
            self.score['points_earned'],
            self.score['points_possible'],
            FEEDBACK_OPTIONS['options'][0] + '\n' + FEEDBACK_OPTIONS['options'][1] + '\n',
            FEEDBACK_TEXT,
        ])

    @ddt.data(
        u'ゅせ第1図 ГЂіи', u"lіиэ ъэтшээи",
        {'parts': [{'text': u'ぞひのぽ ГЂіи lіиэ ъэтшээи'}]},
        {'files_descriptions': [u"Ámate a ti mismo primero y todo lo demás"]}
    )
    def test_collect_ora2_data_with_special_characters(self, answer):
        """
        Scenario: Verify the data collection for ORA2 works with special or non-ascii characters.

        Given the submission object
        Then update its answer with a non-ascii value
        And the submission is saved
        When the ORA2 data for the submissions is obtained
        Then the data's answer will be same as json dumped answer
        """
        submission = sub_api._get_submission_model(self.submission['uuid'])  # pylint: disable=protected-access
        submission.answer = answer
        submission.save()
        with patch('openassessment.data.OraAggregateData._map_anonymized_ids_to_usernames') as map_mock:
            map_mock.return_value = USERNAME_MAPPING
            _, rows = OraAggregateData.collect_ora2_data(COURSE_ID)
        self.assertEqual(json.dumps(answer, ensure_ascii=False), rows[1][7])

    def test_collect_ora2_responses(self):
        item_id2 = self._other_item(2)
        item_id3 = self._other_item(3)
        team_item_id = self._other_item(4)

        student_id2 = self._other_student(2)
        student_id3 = self._other_student(3)
        team_1_ids = [STUDENT_ID, student_id2, student_id3]

        student_id4 = self._other_student(4)
        student_id5 = self._other_student(5)
        team_2_ids = [student_id4, student_id5]

        student_model_1 = UserFactory.create()
        student_model_2 = UserFactory.create()

        self._create_submission(dict(
            student_id=STUDENT_ID,
            course_id=COURSE_ID,
            item_id=item_id2,
            item_type="openassessment"
        ), ['self'])
        self._create_submission(dict(
            student_id=student_id2,
            course_id=COURSE_ID,
            item_id=item_id2,
            item_type="openassessment"
        ), STEPS)

        self._create_submission(dict(
            student_id=STUDENT_ID,
            course_id=COURSE_ID,
            item_id=item_id3,
            item_type="openassessment"
        ), ['self'])
        self._create_submission(dict(
            student_id=student_id2,
            course_id=COURSE_ID,
            item_id=item_id3,
            item_type="openassessment"
        ), ['self'])
        self._create_submission(dict(
            student_id=student_id3,
            course_id=COURSE_ID,
            item_id=item_id3,
            item_type="openassessment"
        ), STEPS)

        self._create_team_submission(
            COURSE_ID,
            team_item_id,
            'team_1',
            student_model_1.id,
            team_1_ids,
        )
        self._create_team_submission(
            COURSE_ID,
            team_item_id,
            'team_2',
            student_model_2.id,
            team_2_ids
        )

        data = OraAggregateData.collect_ora2_responses(COURSE_ID)

        self.assertIn(ITEM_ID, data)
        self.assertIn(item_id2, data)
        self.assertIn(item_id3, data)
        self.assertIn(team_item_id, data)
        for item in [ITEM_ID, item_id2, item_id3, team_item_id]:
            self.assertEqual({'total', 'training', 'peer', 'self', 'staff', 'waiting', 'done', 'cancelled', 'teams'},
                             set(data[item].keys()))
        self.assertEqual(data[ITEM_ID], {
            'total': 2, 'training': 0, 'peer': 2, 'self': 0, 'staff': 0, 'waiting': 0,
            'done': 0, 'cancelled': 0, 'teams': 0
        })
        self.assertEqual(data[item_id2], {
            'total': 2, 'training': 0, 'peer': 1, 'self': 1, 'staff': 0, 'waiting': 0,
            'done': 0, 'cancelled': 0, 'teams': 0
        })
        self.assertEqual(data[item_id3], {
            'total': 3, 'training': 0, 'peer': 1, 'self': 2, 'staff': 0, 'waiting': 0,
            'done': 0, 'cancelled': 0, 'teams': 0
        })
        self.assertEqual(data[team_item_id], {
            'total': 2, 'training': 0, 'peer': 0, 'self': 0, 'staff': 0, 'waiting': 0,
            'done': 0, 'cancelled': 0, 'teams': 2
        })

        data = OraAggregateData.collect_ora2_responses(COURSE_ID, ['staff', 'peer'])

        self.assertIn(ITEM_ID, data)
        self.assertIn(item_id2, data)
        self.assertIn(item_id3, data)
        for item in [ITEM_ID, item_id2, item_id3]:
            self.assertEqual({'total', 'peer', 'staff'}, set(data[item].keys()))
        self.assertEqual(data[ITEM_ID], {'total': 2, 'peer': 2, 'staff': 0})
        self.assertEqual(data[item_id2], {'total': 1, 'peer': 1, 'staff': 0})
        self.assertEqual(data[item_id3], {'total': 1, 'peer': 1, 'staff': 0})


@ddt.ddt
class TestOraDownloadDataIntegration(TransactionCacheResetTest):
    def setUp(self):
        super().setUp()
        self.maxDiff = None  # pylint: disable=invalid-name

        self.submission = self._create_submission(STUDENT_ITEM)
        self.old_style_submission = self._create_submission(OLD_STUDENT_ITEM)
        self.scorer_submission = self._create_submission(SCORER_ITEM)

        self.file_name_1 = 'file_name_1.jpg'
        self.file_name_2 = 'file_name_2.pdf'
        self.file_name_3 = 'file_name_3.png'
        self.file_name_4 = 'file_name_4.png'

        self.file_key_1 = '{}/{}/{}'.format(STUDENT_ID, COURSE_ID, ITEM_ID)
        self.file_key_2 = '{}/{}/{}/1'.format(STUDENT_ID, COURSE_ID, ITEM_ID)
        self.file_key_3 = '{}/{}/{}/2'.format(STUDENT_ID, COURSE_ID, ITEM_ID)
        self.file_key_4 = '{}/{}/{}'.format(OLD_STUDENT_ID, COURSE_ID, ITEM_ID)

        self.file_description_1 = 'Some Description 1'
        self.file_description_2 = 'Some Description 2'
        self.file_description_3 = 'Some Description 3'
        self.file_description_4 = 'Some Description 4'

        self.file_size_1 = 2 ** 20
        self.file_size_2 = 2 ** 21
        self.file_size_3 = 2 ** 22

        self.answer_text = 'First Response'
        self.answer = {
            'parts': [{'text': self.answer_text}],
            'file_keys': [
                self.file_key_1,
                self.file_key_2,
                self.file_key_3,
            ],
            'files_descriptions': [
                self.file_description_1,
                self.file_description_2,
                self.file_description_3],
            'files_names': [self.file_name_1, self.file_name_2, self.file_name_3],
            'files_sizes': [self.file_size_1, self.file_size_2, self.file_size_3],
        }
        self.old_style_answer = {
            'parts': [{'text': self.answer_text}],
            'file_keys': [self.file_key_4],
            'files_descriptions': [self.file_description_4],
            'files_name': [self.file_name_4]
        }

        self.submission_files_data = [
            {
                'course_id': COURSE_ID,
                'block_id': ITEM_ID,
                'student_id': OLD_STUDENT_ID,
                'key': self.file_key_4,
                'name': self.file_name_4,
                'type': OraDownloadData.ATTACHMENT,
                'description': self.file_description_4,
                'size': 0,
                'file_path': '{}/{}/{}/attachments/{}'.format(
                    COURSE_ID, ITEM_ID, OLD_STUDENT_ID, self.file_name_4
                ),
            },
            {
                'course_id': COURSE_ID,
                'block_id': ITEM_ID,
                'student_id': OLD_STUDENT_ID,
                'key': '',
                'name': 'part_0.txt',
                'type': OraDownloadData.TEXT,
                'description': 'Submission text.',
                'content': self.answer_text,
                'size': len(self.answer_text),
                'file_path': '{}/{}/{}/{}'.format(
                    COURSE_ID, ITEM_ID, OLD_STUDENT_ID, 'part_0.txt'
                ),
            },
            {
                'course_id': COURSE_ID,
                'block_id': ITEM_ID,
                'student_id': STUDENT_ID,
                'key': self.file_key_1,
                'name': self.file_name_1,
                'type': OraDownloadData.ATTACHMENT,
                'description': self.file_description_1,
                'size': self.file_size_1,
                'file_path': '{}/{}/{}/attachments/{}'.format(
                    COURSE_ID, ITEM_ID, STUDENT_ID, self.file_name_1
                ),
            },
            {
                'course_id': COURSE_ID,
                'block_id': ITEM_ID,
                'student_id': STUDENT_ID,
                'key': self.file_key_2,
                'name': self.file_name_2,
                'type': OraDownloadData.ATTACHMENT,
                'description': self.file_description_2,
                'size': self.file_size_2,
                'file_path': '{}/{}/{}/attachments/{}'.format(
                    COURSE_ID, ITEM_ID, STUDENT_ID, self.file_name_2
                ),
            },
            {
                'course_id': COURSE_ID,
                'block_id': ITEM_ID,
                'student_id': STUDENT_ID,
                'key': self.file_key_3,
                'name': self.file_name_3,
                'type': OraDownloadData.ATTACHMENT,
                'description': self.file_description_3,
                'size': self.file_size_3,
                'file_path': '{}/{}/{}/attachments/{}'.format(
                    COURSE_ID, ITEM_ID, STUDENT_ID, self.file_name_3
                ),
            },
            {
                'course_id': COURSE_ID,
                'block_id': ITEM_ID,
                'student_id': STUDENT_ID,
                'key': '',
                'name': 'part_0.txt',
                'type': OraDownloadData.TEXT,
                'description': 'Submission text.',
                'content': self.answer_text,
                'size': len(self.answer_text),
                'file_path': '{}/{}/{}/{}'.format(
                    COURSE_ID, ITEM_ID, STUDENT_ID, 'part_0.txt'
                ),
            },
        ]

    def _create_submission(self, student_item_dict, steps=None):
        """
        Creates a submission and initializes a peer grading workflow.
        """
        submission = sub_api.create_submission(student_item_dict, ANSWER)
        submission_uuid = submission['uuid']
        peer_api.on_start(submission_uuid)
        workflow_api.create_workflow(submission_uuid, steps if steps else STEPS)
        return submission

    def test_collect_ora2_submission_files(self):
        submission = sub_api._get_submission_model(self.submission['uuid'])  # pylint: disable=protected-access
        submission.answer = self.answer
        submission.save()

        # Answers once had a different format
        old_style_submission = sub_api._get_submission_model(self.old_style_submission['uuid'])  # pylint: disable=protected-access
        old_style_submission.answer = self.old_style_answer
        old_style_submission.save()

        # answer for scorer submission is just a string, and `collect_ora2_submission_files`
        # raises exception because of it, so we change it to empty dict
        scorer_submission = sub_api._get_submission_model(  # pylint: disable=protected-access
            self.scorer_submission['uuid']
        )
        scorer_submission.answer = {}
        scorer_submission.save()

        collected_ora_files_data = list(OraDownloadData.collect_ora2_submission_files(COURSE_ID))
        assert collected_ora_files_data == self.submission_files_data

    def test_create_zip_with_attachments(self):
        file = BytesIO()

        file_content = b'file_content'

        with patch(
            'openassessment.data.OraDownloadData._download_file_by_key', return_value=file_content
        ) as download_mock:
            OraDownloadData.create_zip_with_attachments(file, COURSE_ID, self.submission_files_data)

            download_mock.assert_has_calls([
                call(self.file_key_4),
                call(self.file_key_1),
                call(self.file_key_2),
                call(self.file_key_3),
            ])

        zip_file = zipfile.ZipFile(file)

        # archive should contain four attachments, two parts text file and one csv
        self.assertEqual(len(zip_file.infolist()), 7)

        # check for old_user's file and text
        self.assertEqual(
            zip_file.read(self.submission_files_data[0]['file_path']),
            file_content
        )
        self.assertEqual(
            zip_file.read(self.submission_files_data[1]['file_path']),
            self.answer_text.encode('utf-8')
        )
        # check that main user's attachments have been written to the archive
        self.assertEqual(
            zip_file.read(self.submission_files_data[2]['file_path']),
            file_content
        )
        self.assertEqual(
            zip_file.read(self.submission_files_data[3]['file_path']),
            file_content
        )
        self.assertEqual(
            zip_file.read(self.submission_files_data[4]['file_path']),
            file_content
        )
        # main user's text response
        self.assertEqual(
            zip_file.read(self.submission_files_data[5]['file_path']),
            self.answer_text.encode('utf-8')
        )

        self.assertTrue(zip_file.read(os.path.join(COURSE_ID, 'downloads.csv')))
