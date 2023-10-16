"""
Tests for openassessment data aggregation.
"""

from collections import OrderedDict
import csv
from copy import deepcopy
from io import StringIO, BytesIO, TextIOWrapper
import json
import os.path
import zipfile
from unittest.mock import call, Mock, patch

import ddt
from freezegun import freeze_time

from django.core.management import call_command
from django.test import TestCase, override_settings

from submissions import api as sub_api, team_api as team_sub_api
import openassessment.assessment.api.peer as peer_api
from openassessment.data import (
    CsvWriter, OraAggregateData, OraDownloadData, SubmissionFileUpload, OraSubmissionAnswerFactory,
    VersionNotFoundException, ZippedListSubmissionAnswer, OraSubmissionAnswer, ZIPPED_LIST_SUBMISSION_VERSIONS,
    TextOnlySubmissionAnswer, FileMissingException, map_anonymized_ids_to_usernames, map_anonymized_ids_to_user_data,
    generate_given_assessment_data, generate_received_assessment_data, generate_assessment_data, get_scorer_data,
    parts_summary,
)
from openassessment.test_utils import TransactionCacheResetTest
from openassessment.tests.factories import *  # pylint: disable=wildcard-import
from openassessment.workflow import api as workflow_api, team_api as team_workflow_api


COURSE_ID = "Test_Course"

STUDENT_ID = "Student"

STUDENT_USERNAME = "Student Username"

STUDENT_EMAIL = "Student Email"

STUDENT_FULL_NAME = "Student Full Name"

PRE_FILE_SIZE_STUDENT_ID = "Pre_FileSize_Student"

PRE_FILE_SIZE_STUDENT_USERNAME = 'Pre_FileSize_Student_Username'

PRE_FILE_SIZE_STUDENT_EMAIL = 'Pre_FileSize_Student_Email'

PRE_FILE_SIZE_STUDENT_FULL_NAME = 'Pre_FileSize_Student_Full_Name'

PRE_FILE_NAME_STUDENT_ID = "Pre_FileName_Student"

PRE_FILE_NAME_STUDENT_USERNAME = 'Pre_FileName_Student_Username'

PRE_FILE_NAME_STUDENT_EMAIL = 'Pre_FileName_Student_Email'

PRE_FILE_NAME_STUDENT_FULL_NAME = 'Pre_FileName_Student_Full_Name'

SCORER_ID = "Scorer"

SCORER_USERNAME = "Scorer Username"

SCORER_EMAIL = "Scorer Email"

SCORER_FULL_NAME = "Scorer Full Name"

TEST_SCORER_ID = "Test Scorer"

TEST_SCORER_USERNAME = "Test Scorer Username"

TEST_SCORER_EMAIL = "Test Scorer Email"

TEST_SCORER_FULL_NAME = "Test Scorer Full Name"

USERNAME_MAPPING = {
    STUDENT_ID: STUDENT_USERNAME,
    SCORER_ID: SCORER_USERNAME,
    TEST_SCORER_ID: TEST_SCORER_USERNAME,
    PRE_FILE_SIZE_STUDENT_ID: PRE_FILE_SIZE_STUDENT_USERNAME,
    PRE_FILE_NAME_STUDENT_ID: PRE_FILE_NAME_STUDENT_USERNAME,
}

USER_DATA_MAPPING = {
    STUDENT_ID: {"username": STUDENT_USERNAME, "email": STUDENT_EMAIL, "fullname": STUDENT_FULL_NAME},
    SCORER_ID: {"username": SCORER_USERNAME, "email": SCORER_EMAIL, "fullname": SCORER_FULL_NAME},
    TEST_SCORER_ID: {"username": TEST_SCORER_USERNAME, "email": TEST_SCORER_EMAIL, "fullname": TEST_SCORER_FULL_NAME},
    PRE_FILE_SIZE_STUDENT_ID: {
        "username": PRE_FILE_SIZE_STUDENT_USERNAME,
        "email": PRE_FILE_SIZE_STUDENT_EMAIL,
        "fullname": PRE_FILE_SIZE_STUDENT_FULL_NAME,
    },
    PRE_FILE_NAME_STUDENT_ID: {
        "username": PRE_FILE_NAME_STUDENT_USERNAME,
        "email": PRE_FILE_NAME_STUDENT_EMAIL,
        "fullname": PRE_FILE_NAME_STUDENT_FULL_NAME,
    },
}

ITEM_ID = "item"

ITEM_DISPLAY_NAME = "Open Response Assessment"

ITEM_PATH_INFO = {
    "section_index": "1",
    "section_name": "Section",
    "sub_section_index": "1",
    "sub_section_name": "Sub Section",
    "unit_index": "1",
    "unit_name": "Unit",
    "ora_index": "1",
    "ora_name": ITEM_DISPLAY_NAME,
}

STUDENT_ITEM = {
    "student_id": STUDENT_ID,
    "course_id": COURSE_ID,
    "item_id": ITEM_ID,
    "item_type": "openassessment"
}

PRE_FILE_SIZE_STUDENT_ITEM = {
    "student_id": PRE_FILE_SIZE_STUDENT_ID,
    "course_id": COURSE_ID,
    "item_id": ITEM_ID,
    "item_type": "openassessment"
}

PRE_FILE_NAME_STUDENT_ITEM = {
    "student_id": PRE_FILE_NAME_STUDENT_ID,
    "course_id": COURSE_ID,
    "item_id": ITEM_ID,
    "item_type": "openassessment"
}

SCORER_ITEM = {
    "student_id": SCORER_ID,
    "course_id": COURSE_ID,
    "item_id": ITEM_ID,
    "item_type": "openassessment"
}

ITEM_DISPLAY_NAMES_MAPPING = {
    SCORER_ITEM['item_id']: ITEM_DISPLAY_NAME,
    STUDENT_ITEM['item_id']: ITEM_DISPLAY_NAME
}

ANSWER = {'parts': 'THIS IS A TEST ANSWER'}

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
            "name": "criterion_2",
            "label": "criterion_2",
            "prompt": "Did the writer keep it safe?",
            "options": [
                {"name": "option_1", "label": "option_1", "points": "0", "explanation": ""},
                {"name": "option_2", "label": "option_2", "points": "1", "explanation": ""},
            ]
        },
    ]
}

ASSESSMENT_DICT = {
    'overall_feedback': "这是中国",
    'criterion_feedback': {
        "criterion_2": "𝓨𝓸𝓾 𝓼𝓱𝓸𝓾𝓵𝓭𝓷'𝓽 𝓰𝓲𝓿𝓮 𝓾𝓹!"
    },
    'options_selected': {
        "criterion_1": "option_1",
        "criterion_2": "option_2",
    },
}

FEEDBACK_TEXT = "𝓨𝓸𝓾 𝓼𝓱𝓸𝓾𝓵𝓭𝓷'𝓽 𝓰𝓲𝓿𝓮 𝓾𝓹!"

FEEDBACK_OPTIONS = {
    "feedback_text": FEEDBACK_TEXT,
    "options": [
        'I disliked this assessment',
        'I felt this assessment was unfair',
    ]
}

STEP_REQUIREMENTS = {
    "peer": {
        "must_grade": 0,
        "must_be_graded_by": 1
    }
}

COURSE_SETTINGS = {
    "force_on_flexible_peer_openassessments": False
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
                    msg=f"Output name: {output_name}"
                )

            # Check for extra rows
            try:
                extra_row = next(actual_csv)
            except StopIteration:
                extra_row = None

            if extra_row is not None:
                self.fail(f"CSV contains extra row: {extra_row}")

    def test_many_submissions(self):
        # Create a lot of submissions
        num_submissions = 234
        for index in range(num_submissions):
            student_item = {
                'student_id': f"test_user_{index}",
                'course_id': 'test_course',
                'item_id': 'test_item',
                'item_type': 'openassessment',
            }
            submission_text = f"test submission {index}"
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
        CsvWriter(output_streams).write_to_csv("𝓽𝓮𝓼𝓽_𝓬𝓸𝓾𝓻𝓼𝓮")

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
        output_streams = {}

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
        print(f"Loading database fixtures from {fixture_path}")
        call_command('loaddata', fixture_path)


@ddt.ddt
@patch.dict('django.conf.settings.FEATURES', {'ENABLE_ORA_USERNAMES_ON_DATA_EXPORT': True})
class TestOraAggregateData(TransactionCacheResetTest):
    """
    Test the component parts of OraAggregateData
    """

    @classmethod
    def build_criteria_and_assessment_parts(cls, num_criteria=1, feedback="",
                                            assessment_options=None, criterion_options=None):
        """ Build a set of criteria and assessment parts for the rubric. """
        if criterion_options:
            # Extract the criteria and rubric from the options, if provided.
            criteria = [option.criterion for option in criterion_options]
            rubric = criteria[0].rubric
        else:
            # Generate the rubric, criteria, and options
            rubric = RubricFactory()
            criteria = [CriterionFactory(rubric=rubric, order_num=n + 1) for n in range(num_criteria)]
            criterion_options = []
            for criterion in criteria:
                criterion_options.append(CriterionOptionFactory(criterion=criterion))

        assessment_options = assessment_options or {'scorer_id': TEST_SCORER_ID}
        assessment_data = {
            "rubric": rubric,
            "feedback": feedback,
            **assessment_options
        }
        assessment = AssessmentFactory(**assessment_data)
        for criterion, option in zip(criteria, criterion_options):
            AssessmentPartFactory(assessment=assessment, criterion=criterion, option=option, feedback=feedback)
        return assessment

    def _assessment_cell(self, assessment, feedback=""):
        """ Build a string for the given assessment information. """
        cell = [
            f"Assessment #{assessment.id}",
            f"-- scored_at: {assessment.scored_at}",
            f"-- type: {assessment.score_type}",
        ]
        if assessment.score_type == peer_api.PEER_TYPE:
            cell.append("-- used to calculate peer grade: False")

        cell += [
            f"-- scorer_username: {USERNAME_MAPPING[assessment.scorer_id]}",
            f"-- scorer_id: {assessment.scorer_id}"
        ]
        if feedback:
            cell.append(f"-- overall_feedback: {feedback}")

        return "\n".join(cell) + "\n"

    def test_map_anonymized_ids_to_usernames(self):
        with patch('openassessment.data.get_user_model') as get_user_model_mock:
            get_user_model_mock.return_value.objects.filter.return_value.annotate.return_value.values.return_value = [
                {'anonymous_id': STUDENT_ID, 'username': STUDENT_USERNAME},
                {'anonymous_id': PRE_FILE_SIZE_STUDENT_ID, 'username': PRE_FILE_SIZE_STUDENT_USERNAME},
                {'anonymous_id': PRE_FILE_NAME_STUDENT_ID, 'username': PRE_FILE_NAME_STUDENT_USERNAME},
                {'anonymous_id': SCORER_ID, 'username': SCORER_USERNAME},
                {'anonymous_id': TEST_SCORER_ID, 'username': TEST_SCORER_USERNAME},
            ]

            # pylint: disable=protected-access
            mapping = map_anonymized_ids_to_usernames(
                [
                    STUDENT_ID,
                    PRE_FILE_SIZE_STUDENT_ID,
                    PRE_FILE_NAME_STUDENT_ID,
                    SCORER_ID,
                    TEST_SCORER_ID,
                ]
            )

        self.assertEqual(mapping, USERNAME_MAPPING)

    def test_map_anonymized_ids_to_user_data(self):
        with patch('openassessment.data.get_user_model') as get_user_model_mock:
            get_user_model_mock.return_value.objects.filter.return_value \
                .select_related.return_value.annotate.return_value.values.return_value = [
                    {
                        'anonymous_id': STUDENT_ID,
                        'username': STUDENT_USERNAME,
                        'email': STUDENT_EMAIL,
                        'profile__name': STUDENT_FULL_NAME,
                    },
                    {
                        'anonymous_id': PRE_FILE_SIZE_STUDENT_ID,
                        'username': PRE_FILE_SIZE_STUDENT_USERNAME,
                        'email': PRE_FILE_SIZE_STUDENT_EMAIL,
                        'profile__name': PRE_FILE_SIZE_STUDENT_FULL_NAME,
                    },
                    {
                        'anonymous_id': PRE_FILE_NAME_STUDENT_ID,
                        'username': PRE_FILE_NAME_STUDENT_USERNAME,
                        'email': PRE_FILE_NAME_STUDENT_EMAIL,
                        'profile__name': PRE_FILE_NAME_STUDENT_FULL_NAME,
                    },
                    {
                        'anonymous_id': SCORER_ID,
                        'username': SCORER_USERNAME,
                        'email': SCORER_EMAIL,
                        'profile__name': SCORER_FULL_NAME,
                    },
                    {
                        'anonymous_id': TEST_SCORER_ID,
                        'username': TEST_SCORER_USERNAME,
                        'email': TEST_SCORER_EMAIL,
                        'profile__name': TEST_SCORER_FULL_NAME,
                    },
                ]

            # pylint: disable=protected-access
            mapping = map_anonymized_ids_to_user_data(
                [
                    STUDENT_ID,
                    PRE_FILE_SIZE_STUDENT_ID,
                    PRE_FILE_NAME_STUDENT_ID,
                    SCORER_ID,
                    TEST_SCORER_ID,
                ]
            )

        self.assertEqual(mapping, USER_DATA_MAPPING)

    def test_map_students_and_scorers_ids_to_usernames(self):
        test_submission_information = [
            (
                {
                    "student_id": STUDENT_ID,
                    "course_id": COURSE_ID,
                    "item_id": "some_id",
                    "item_type": "openassessment",
                },
                sub_api.create_submission(STUDENT_ITEM, ANSWER),
                (),
            ),
            (
                {
                    "student_id": SCORER_ID,
                    "course_id": COURSE_ID,
                    "item_id": "some_id",
                    "item_type": "openassessment",
                },
                sub_api.create_submission(SCORER_ITEM, ANSWER),
                (),
            ),
        ]

        with patch("openassessment.data.map_anonymized_ids_to_usernames") as map_mock:
            # pylint: disable=protected-access
            OraAggregateData._map_students_and_scorers_ids_to_usernames(
                test_submission_information
            )
            map_mock.assert_called_once_with([STUDENT_ID, SCORER_ID])

    def test_build_assessments_cell(self):
        # One assessment
        assessment1 = self.build_criteria_and_assessment_parts()

        # pylint: disable=protected-access
        assessment_cell = OraAggregateData._build_assessments_cell([assessment1], USERNAME_MAPPING)

        a1_cell = self._assessment_cell(assessment1)
        self.assertEqual(assessment_cell, a1_cell)

        # Multiple assessments
        assessment2 = self.build_criteria_and_assessment_parts(feedback="Test feedback")

        # pylint: disable=protected-access
        assessment_cell = OraAggregateData._build_assessments_cell([assessment1, assessment2], USERNAME_MAPPING)

        a2_cell = self._assessment_cell(assessment2, feedback="Test feedback")

        self.assertEqual(assessment_cell, a1_cell + a2_cell)

    @ddt.data(True, False)
    def test_build_assessments_cell__scored_peer_assessment(self, scored):
        assessment1 = self.build_criteria_and_assessment_parts()
        assessment2 = self.build_criteria_and_assessment_parts()
        assert assessment1.score_type == peer_api.PEER_TYPE
        assert assessment2.score_type == peer_api.PEER_TYPE

        scored_peer_assessment_ids = {assessment1.id}
        if scored:
            scored_peer_assessment_ids.add(assessment2.id)

        # pylint: disable=protected-access
        assessment_cell = OraAggregateData._build_assessments_cell(
            [assessment2],
            USERNAME_MAPPING,
            scored_peer_assessment_ids
        )
        assert f"used to calculate peer grade: {scored}" in assessment_cell

    def test_build_assessments_cell__non_peer_assessment(self):
        assessment = self.build_criteria_and_assessment_parts()
        assessment.score_type = "XX"
        assessment.save()

        # pylint: disable=protected-access
        assessment_cell = OraAggregateData._build_assessments_cell([assessment], USERNAME_MAPPING)
        assert "used to calculate peer grade" not in assessment_cell

    def _assessment_part_cell(self, assessment_part, feedback=""):
        """ Build the string representing an assessment part. """

        cell = "-- {criterion_label}: {option_label} ({option_points})\n".format(
            criterion_label=assessment_part.criterion.label,
            option_label=assessment_part.option.label,
            option_points=assessment_part.option.points,
        )
        if feedback:
            cell += f"-- feedback: {feedback}\n"
        return cell

    def test_build_assessments_parts_cell(self):
        assessment1 = self.build_criteria_and_assessment_parts()
        a1_cell = f"Assessment #{assessment1.id}\n"

        for part in assessment1.parts.all():
            a1_cell += self._assessment_part_cell(part)

        # pylint: disable=protected-access
        assessment_part_cell = OraAggregateData._build_assessments_parts_cell([assessment1])
        self.assertEqual(a1_cell, assessment_part_cell)

        # Second assessment with 2 component parts and individual option feedback
        assessment2 = self.build_criteria_and_assessment_parts(num_criteria=2, feedback="Test feedback")
        a2_cell = f"Assessment #{assessment2.id}\n"

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

    @override_settings(LMS_ROOT_URL="https://example.com")
    @patch('openassessment.xblock.openassessmentblock.OpenAssessmentBlock.get_download_urls_from_submission')
    def test_build_response_file_links(self, mock_method):
        """
        Test _build_response_file_links method.

        Ensures that the method returns the expected file links based on the given submission.
        """
        expected_result = "https://example.com/file1.pdf\nhttps://example.com/file2.png\nhttps://example.com/file3.jpeg"
        file_downloads = [
            {'download_url': '/file1.pdf'},
            {'download_url': '/file2.png'},
            {'download_url': '/file3.jpeg'},
        ]
        mock_method.return_value = file_downloads
        # pylint: disable=protected-access
        result = OraAggregateData._build_response_file_links('test submission')

        self.assertEqual(result, expected_result)


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
        super().setUp()
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
        peer_api.get_score(self.submission['uuid'], STEP_REQUIREMENTS['peer'], COURSE_SETTINGS)
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
        workflow_api.update_from_assessments(submission_uuid, STEP_REQUIREMENTS, COURSE_SETTINGS)
        self.score = sub_api.get_score(STUDENT_ITEM)

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
        with patch('openassessment.data.map_anonymized_ids_to_usernames') as map_mock:
            with patch('openassessment.data.peer_api.get_bulk_scored_assessments') as mock_get_scored_assessments:
                map_mock.return_value = USERNAME_MAPPING
                mock_get_scored_assessments.return_value = {Mock(id=self.assessment['id'])}
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
            '',
            '',
            '',
            '',
            '',
            '',
            '',
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
            (
                f"Assessment #{self.assessment['id']}\n"
                f"-- scored_at: {self.assessment['scored_at']}\n"
                "-- type: PE\n"
                "-- used to calculate peer grade: True\n"
                f"-- scorer_username: {USERNAME_MAPPING[self.assessment['scorer_id']]}\n"
                f"-- scorer_id: {self.assessment['scorer_id']}\n"
                f"-- overall_feedback: {self.assessment['feedback']}\n"
            ),
            "Assessment #{id}\n-- {label}: {option_label} ({points})\n".format(
                id=self.assessment['id'],
                label=self.assessment['parts'][0]['criterion']['label'],
                option_label=self.assessment['parts'][0]['criterion']['options'][0]['label'],
                points=self.assessment['parts'][0]['criterion']['options'][0]['points'],
            ) + "-- {label}: {option_label} ({points})\n-- feedback: {feedback}\n".format(
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
            with patch('openassessment.data.peer_api.get_bulk_scored_assessments', return_value=set()):
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
            '',
            '',
            '',
            '',
            '',
            '',
            '',
        ])
        self.assertEqual(data[1], [
            self.submission['uuid'],
            ITEM_ID,
            ITEM_DISPLAY_NAME,
            self.submission['student_item'],
            STUDENT_ID,
            self.submission['submitted_at'],
            json.dumps(self.submission['answer']),
            (
                f"Assessment #{self.assessment['id']}\n"
                f"-- scored_at: {self.assessment['scored_at']}\n"
                "-- type: PE\n"
                "-- used to calculate peer grade: False\n"
                f"-- scorer_id: {self.assessment['scorer_id']}\n"
                f"-- overall_feedback: {self.assessment['feedback']}\n"
            ),
            "Assessment #{id}\n-- {label}: {option_label} ({points})\n".format(
                id=self.assessment['id'],
                label=self.assessment['parts'][0]['criterion']['label'],
                option_label=self.assessment['parts'][0]['criterion']['options'][0]['label'],
                points=self.assessment['parts'][0]['criterion']['options'][0]['points'],
            ) + "-- {label}: {option_label} ({points})\n-- feedback: {feedback}\n".format(
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
        'ゅせ第1図 ГЂіи', "lіиэ ъэтшээи",
        {'parts': [{'text': 'ぞひのぽ ГЂіи lіиэ ъэтшээи'}]},
        {'files_descriptions': ["Ámate a ti mismo primero y todo lo demás"]}
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
        with patch('openassessment.data.map_anonymized_ids_to_usernames') as map_mock:
            with patch('openassessment.data.peer_api.get_bulk_scored_assessments', return_value=set()):
                map_mock.return_value = USERNAME_MAPPING
                _, rows = OraAggregateData.collect_ora2_data(COURSE_ID)
        self.assertEqual(json.dumps(answer, ensure_ascii=False), rows[1][7])

    def test_collect_ora2_summary(self):
        headers, data = OraAggregateData.collect_ora2_summary(COURSE_ID)

        self.assertEqual(headers, [
            'block_name',
            'student_id',
            'status',
            'is_peer_complete',
            'is_peer_graded',
            'is_self_complete',
            'is_self_graded',
            'is_staff_complete',
            'is_staff_graded',
            'is_training_complete',
            'is_training_graded',
            'num_peers_graded',
            'num_graded_by_peers',
            'is_staff_grade_received',
            'is_final_grade_received',
            'final_grade_points_earned',
            'final_grade_points_possible',
        ])

        # one row for each user, ora pair
        self.assertEqual(len(data), 2)

        self.assertEqual(data[0], [
            ITEM_ID,
            SCORER_ID,
            'peer',
            0,
            0,
            '',
            '',
            1,
            1,
            '',
            '',
            1,
            0,
            0,
            0,
            '',
            '',
        ])

        self.assertEqual(data[1], [
            ITEM_ID,
            STUDENT_ID,
            'done',
            1,
            1,
            '',
            '',
            1,
            1,
            '',
            '',
            0,
            1,
            0,
            1,
            1,
            2,
        ])

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

        self._create_submission({
            "student_id": STUDENT_ID,
            "course_id": COURSE_ID,
            "item_id": item_id2,
            "item_type": "openassessment"
        }, ['self'])
        self._create_submission({
            "student_id": student_id2,
            "course_id": COURSE_ID,
            "item_id": item_id2,
            "item_type": "openassessment"
        }, STEPS)

        self._create_submission({
            "student_id": STUDENT_ID,
            "course_id": COURSE_ID,
            "item_id": item_id3,
            "item_type": "openassessment"
        }, ['self'])
        self._create_submission({
            "student_id": student_id2,
            "course_id": COURSE_ID,
            "item_id": item_id3,
            "item_type": "openassessment"
        }, ['self'])
        self._create_submission({
            "student_id": student_id3,
            "course_id": COURSE_ID,
            "item_id": item_id3,
            "item_type": "openassessment"
        }, STEPS)

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
            'total': 2, 'training': 0, 'peer': 1, 'self': 0, 'staff': 0, 'waiting': 0,
            'done': 1, 'cancelled': 0, 'teams': 0
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
            'total': 2, 'training': 0, 'peer': 0, 'self': 0, 'staff': 0, 'waiting': 2,
            'done': 0, 'cancelled': 0, 'teams': 0
        })

        data = OraAggregateData.collect_ora2_responses(COURSE_ID, ['staff', 'peer'])

        self.assertIn(ITEM_ID, data)
        self.assertIn(item_id2, data)
        self.assertIn(item_id3, data)
        for item in [ITEM_ID, item_id2, item_id3]:
            self.assertEqual({'total', 'peer', 'staff'}, set(data[item].keys()))
        self.assertEqual(data[ITEM_ID], {'total': 1, 'peer': 1, 'staff': 0})
        self.assertEqual(data[item_id2], {'total': 1, 'peer': 1, 'staff': 0})
        self.assertEqual(data[item_id3], {'total': 1, 'peer': 1, 'staff': 0})

    def test_generate_assessment_data_no_submission(self):
        rows = list(OraAggregateData.generate_assessment_data('block_id_goes_here'))
        self.assertEqual(rows, [OrderedDict([
            ('Item ID', 'block_id_goes_here'),
            ('Submission ID', ''),
        ])])

    def test_generate_assessment_data_no_assessment(self):
        submission = self._create_submission(STUDENT_ITEM)
        submission_uuid = submission['uuid']
        rows = list(OraAggregateData.generate_assessment_data('block_id_goes_here', submission_uuid))
        self.assertEqual(rows, [OrderedDict([
            ('Item ID', 'block_id_goes_here'),
            ('Submission ID', submission_uuid),
            ('Anonymized Student ID', 'Student'),
            ('Response Files', ''),
        ])])

    @freeze_time("2020-01-01 12:23:34")
    def test_generate_assessment_data(self):
        # Create a submission with many assessments and a final score.
        submission = self._create_submission(STUDENT_ITEM)
        submission_uuid = submission['uuid']

        rubric = RubricFactory()
        criteria = [CriterionFactory(rubric=rubric,
                                     order_num=n + 1,
                                     name=f'Criteria {n}',
                                     label=f'label_{n}')
                    for n in range(2)]

        assessments = []
        for index in range(1, 4):
            criterion_options = [
                CriterionOptionFactory(criterion=criterion,
                                       points=index,
                                       name=f'Option {n}',
                                       label=f'option_{n}')
                for (n, criterion) in enumerate(criteria)
            ]
            assessment = TestOraAggregateData.build_criteria_and_assessment_parts(
                feedback='feedback for {}'.format(STUDENT_ITEM['student_id']),
                assessment_options={
                    'submission_uuid': submission_uuid,
                    'scorer_id': f'test_scorer_{index}',
                },
                criterion_options=criterion_options,
            )
            assessments.append(assessment)

        sub_api.set_score(submission_uuid, 9, 10)
        peer_api.get_score(submission_uuid, {'must_be_graded_by': 1, 'must_grade': 0}, {})
        self._create_assessment_feedback(submission_uuid)

        # Generate the assessment report
        rows = []
        for row in OraAggregateData.generate_assessment_data('block_id_goes_here', submission_uuid):
            rows.append(row)

        self.assertEqual([
            OrderedDict([
                ('Item ID', 'block_id_goes_here'),
                ('Submission ID', assessments[2].submission_uuid),
                ('Anonymized Student ID', 'Student'),
                ('Assessment ID', assessments[2].id),
                ('Assessment Scored Date', '2020-01-01'),
                ('Assessment Scored Time', '12:23:34 UTC'),
                ('Assessment Type', 'PE'),
                ('Anonymous Scorer Id', 'test_scorer_3'),
                ('Criterion 1: label_0', 'option_0'),
                ('Points 1', 3),
                ('Median Score 1', 2),
                ('Feedback 1', 'feedback for Student'),
                ('Criterion 2: label_1', 'option_1'),
                ('Points 2', 3),
                ('Median Score 2', 2),
                ('Feedback 2', 'feedback for Student'),
                ('Overall Feedback', 'feedback for Student'),
                ('Assessment Score Earned', 6),
                ('Assessment Scored At', '2020-01-01 12:23:34 UTC'),
                ('Date/Time Final Score Given', '2020-01-01 12:23:34 UTC'),
                ('Final Score Earned', 9),
                ('Final Score Possible', 10),
                ('Feedback Statements Selected', ''),
                ('Feedback on Assessment', "𝓨𝓸𝓾 𝓼𝓱𝓸𝓾𝓵𝓭𝓷'𝓽 𝓰𝓲𝓿𝓮 𝓾𝓹!"),
                ('Response Files', ''),
            ]),
            OrderedDict([
                ('Item ID', 'block_id_goes_here'),
                ('Submission ID', assessments[1].submission_uuid),
                ('Anonymized Student ID', 'Student'),
                ('Assessment ID', assessments[1].id),
                ('Assessment Scored Date', '2020-01-01'),
                ('Assessment Scored Time', '12:23:34 UTC'),
                ('Assessment Type', 'PE'),
                ('Anonymous Scorer Id', 'test_scorer_2'),
                ('Criterion 1: label_0', 'option_0'),
                ('Points 1', 2),
                ('Median Score 1', 2),
                ('Feedback 1', 'feedback for Student'),
                ('Criterion 2: label_1', 'option_1'),
                ('Points 2', 2),
                ('Median Score 2', 2),
                ('Feedback 2', 'feedback for Student'),
                ('Overall Feedback', 'feedback for Student'),
                ('Assessment Score Earned', 4),
                ('Assessment Scored At', '2020-01-01 12:23:34 UTC'),
                ('Date/Time Final Score Given', '2020-01-01 12:23:34 UTC'),
                ('Final Score Earned', 9),
                ('Final Score Possible', 10),
                ('Feedback Statements Selected', ''),
                ('Feedback on Assessment', "𝓨𝓸𝓾 𝓼𝓱𝓸𝓾𝓵𝓭𝓷'𝓽 𝓰𝓲𝓿𝓮 𝓾𝓹!"),
                ('Response Files', ''),
            ]),
            OrderedDict([
                ('Item ID', 'block_id_goes_here'),
                ('Submission ID', assessments[0].submission_uuid),
                ('Anonymized Student ID', 'Student'),
                ('Assessment ID', assessments[0].id),
                ('Assessment Scored Date', '2020-01-01'),
                ('Assessment Scored Time', '12:23:34 UTC'),
                ('Assessment Type', 'PE'),
                ('Anonymous Scorer Id', 'test_scorer_1'),
                ('Criterion 1: label_0', 'option_0'),
                ('Points 1', 1),
                ('Median Score 1', 2),
                ('Feedback 1', 'feedback for Student'),
                ('Criterion 2: label_1', 'option_1'),
                ('Points 2', 1),
                ('Median Score 2', 2),
                ('Feedback 2', 'feedback for Student'),
                ('Overall Feedback', 'feedback for Student'),
                ('Assessment Score Earned', 2),
                ('Assessment Scored At', '2020-01-01 12:23:34 UTC'),
                ('Date/Time Final Score Given', '2020-01-01 12:23:34 UTC'),
                ('Final Score Earned', 9),
                ('Final Score Possible', 10),
                ('Feedback Statements Selected', ''),
                ('Feedback on Assessment', "𝓨𝓸𝓾 𝓼𝓱𝓸𝓾𝓵𝓭𝓷'𝓽 𝓰𝓲𝓿𝓮 𝓾𝓹!"),
                ('Response Files', ''),
            ]),
        ], rows)


@ddt.ddt
class TestOraDownloadDataIntegration(TransactionCacheResetTest):
    """ Unit tests for OraDownloadData """

    def setUp(self):
        super().setUp()
        self.maxDiff = None  # pylint: disable=invalid-name

        self.submission = self._create_submission(STUDENT_ITEM)
        self.pre_file_size_submission = self._create_submission(PRE_FILE_SIZE_STUDENT_ITEM)
        self.pre_file_name_submission = self._create_submission(PRE_FILE_NAME_STUDENT_ITEM)
        self.scorer_submission = self._create_submission(SCORER_ITEM)

        self.file_name_1 = 'file_name_1.jpg'
        self.file_name_2 = 'file_name_2.pdf'
        self.file_name_3 = 'file_name_3.png'
        self.file_name_4 = 'file_name_4.png'

        self.file_key_1 = f'{STUDENT_ID}/{COURSE_ID}/{ITEM_ID}'
        self.file_key_2 = f'{STUDENT_ID}/{COURSE_ID}/{ITEM_ID}/1'
        self.file_key_3 = f'{STUDENT_ID}/{COURSE_ID}/{ITEM_ID}/2'
        self.file_key_4 = f'{PRE_FILE_SIZE_STUDENT_ID}/{COURSE_ID}/{ITEM_ID}'
        self.file_key_5 = f'{PRE_FILE_NAME_STUDENT_ID}/{COURSE_ID}/{ITEM_ID}'

        self.file_description_1 = 'Some Description 1'
        self.file_description_2 = 'Some Description 2'
        self.file_description_3 = 'Some Description 3'
        self.file_description_4 = 'Some Description 4'
        self.file_description_5 = 'Some Description 5'

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

        # Older responses (approx. pre-2020) won't have files_sizes
        # and will have the key 'files_name' rather than 'files_names'
        self.pre_file_size_answer = {
            'parts': [{'text': self.answer_text}],
            'file_keys': [self.file_key_4],
            'files_descriptions': [self.file_description_4],
            'files_name': [self.file_name_4]
        }

        # And answers a bit older than that (approx. pre-Nov. 2019) won't
        # have any file name data
        self.pre_file_name_answer = {
            'parts': [{'text': self.answer_text}],
            'file_keys': [self.file_key_5],
            'files_descriptions': [self.file_description_5],
        }
        file_5_generated_name = SubmissionFileUpload.generate_name_from_key(self.file_key_5)

        submission_directory = (
            f"[{ITEM_PATH_INFO['section_index']}]{ITEM_PATH_INFO['section_name']}, "
            f"[{ITEM_PATH_INFO['sub_section_index']}]{ITEM_PATH_INFO['sub_section_name']}, "
            f"[{ITEM_PATH_INFO['unit_index']}]{ITEM_PATH_INFO['unit_name']}"
        )
        self.submission_files_data = [
            {
                'course_id': COURSE_ID,
                'block_id': ITEM_ID,
                'student_id': PRE_FILE_NAME_STUDENT_ID,
                'key': self.file_key_5,
                'name': file_5_generated_name,
                'type': OraDownloadData.ATTACHMENT,
                'description': self.file_description_5,
                'size': 0,
                'file_path': (
                    f"{submission_directory}/[{ITEM_PATH_INFO['ora_index']}]"
                    f" - {USERNAME_MAPPING[PRE_FILE_NAME_STUDENT_ID]} - {file_5_generated_name}"
                ),
            },
            {
                'course_id': COURSE_ID,
                'block_id': ITEM_ID,
                'student_id': PRE_FILE_NAME_STUDENT_ID,
                'key': '',
                'name': 'prompt_0.txt',
                'type': OraDownloadData.TEXT,
                'description': 'Submission text.',
                'content': self.answer_text,
                'size': len(self.answer_text),
                'file_path': (
                    f"{submission_directory}/[{ITEM_PATH_INFO['ora_index']}]"
                    f" - {USERNAME_MAPPING[PRE_FILE_NAME_STUDENT_ID]} - prompt_0.txt"
                ),
            },
            {
                'course_id': COURSE_ID,
                'block_id': ITEM_ID,
                'student_id': PRE_FILE_SIZE_STUDENT_ID,
                'key': self.file_key_4,
                'name': self.file_name_4,
                'type': OraDownloadData.ATTACHMENT,
                'description': self.file_description_4,
                'size': 0,
                'file_path': (
                    f"{submission_directory}/[{ITEM_PATH_INFO['ora_index']}]"
                    f" - {USERNAME_MAPPING[PRE_FILE_SIZE_STUDENT_ID]} - {self.file_name_4}"
                ),
            },
            {
                'course_id': COURSE_ID,
                'block_id': ITEM_ID,
                'student_id': PRE_FILE_SIZE_STUDENT_ID,
                'key': '',
                'name': 'prompt_0.txt',
                'type': OraDownloadData.TEXT,
                'description': 'Submission text.',
                'content': self.answer_text,
                'size': len(self.answer_text),
                'file_path': (
                    f"{submission_directory}/[{ITEM_PATH_INFO['ora_index']}]"
                    f" - {USERNAME_MAPPING[PRE_FILE_SIZE_STUDENT_ID]} - prompt_0.txt"
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
                'file_path': (
                    f"{submission_directory}/[{ITEM_PATH_INFO['ora_index']}]"
                    f" - {USERNAME_MAPPING[STUDENT_ID]} - {self.file_name_1}"
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
                'file_path': (
                    f"{submission_directory}/[{ITEM_PATH_INFO['ora_index']}]"
                    f" - {USERNAME_MAPPING[STUDENT_ID]} - {self.file_name_2}"
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
                'file_path': (
                    f"{submission_directory}/[{ITEM_PATH_INFO['ora_index']}]"
                    f" - {USERNAME_MAPPING[STUDENT_ID]} - {self.file_name_3}"
                ),
            },
            {
                'course_id': COURSE_ID,
                'block_id': ITEM_ID,
                'student_id': STUDENT_ID,
                'key': '',
                'name': 'prompt_0.txt',
                'type': OraDownloadData.TEXT,
                'description': 'Submission text.',
                'content': self.answer_text,
                'size': len(self.answer_text),
                'file_path': (
                    f"{submission_directory}/[{ITEM_PATH_INFO['ora_index']}]"
                    f" - {USERNAME_MAPPING[STUDENT_ID]} - prompt_0.txt"
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

    def _override_default_answers(self):
        """
        _create_submission creates lightweight "dummy" submissons,
        with an answer defined as the constant ANSWER in this file.
        This method modifies the answer values for tests that actually
        care about the values of the answers
        """
        submission = sub_api._get_submission_model(self.submission['uuid'])  # pylint: disable=protected-access
        submission.answer = self.answer
        submission.save()

        # older submission formats
        pre_filesize_uuid = self.pre_file_size_submission['uuid']
        pre_file_size_submission = sub_api._get_submission_model(pre_filesize_uuid)  # pylint: disable=protected-access
        pre_file_size_submission.answer = self.pre_file_size_answer
        pre_file_size_submission.save()

        pre_filename_uuid = self.pre_file_name_submission['uuid']
        pre_file_name_submission = sub_api._get_submission_model(pre_filename_uuid)  # pylint: disable=protected-access
        pre_file_name_submission.answer = self.pre_file_name_answer
        pre_file_name_submission.save()

        # answer for scorer submission is just a string, and `collect_ora2_submission_files`
        # raises exception because of it, so we change it to empty dict
        scorer_submission = sub_api._get_submission_model(  # pylint: disable=protected-access
            self.scorer_submission['uuid']
        )
        scorer_submission.answer = {'parts': []}
        scorer_submission.save()

    @patch(
        'openassessment.data.OraDownloadData._map_ora_usage_keys_to_path_info',
        Mock(return_value={ITEM_ID: ITEM_PATH_INFO})
    )
    @patch(
        'openassessment.data.OraDownloadData._map_student_ids_to_path_ids',
        Mock(return_value=USERNAME_MAPPING)
    )
    def test_collect_ora2_submission_files(self):
        """
        Test that `collect_ora2_submission_files` returns correct set of
        submission texts and attachments for a given course.
        """
        self._override_default_answers()
        collected_ora_files_data = list(OraDownloadData.collect_ora2_submission_files(COURSE_ID))
        assert collected_ora_files_data == self.submission_files_data

    @patch(
        'openassessment.data.OraDownloadData._map_ora_usage_keys_to_path_info',
        Mock(return_value={ITEM_ID: ITEM_PATH_INFO})
    )
    def test_collect_ora2_submission_files__no_user(self):
        """
        Test for behavior when a user isn't included in the username map
        """
        self._override_default_answers()
        username_mapping_no_default_student = USERNAME_MAPPING.copy()
        del username_mapping_no_default_student[STUDENT_ID]

        with patch('openassessment.data.OraDownloadData._map_student_ids_to_path_ids') as mock_map_student_ids:
            mock_map_student_ids.return_value = username_mapping_no_default_student
            collected_ora_files_data = list(OraDownloadData.collect_ora2_submission_files(COURSE_ID))

        expected_files = [
            expected_file for expected_file in self.submission_files_data
            if expected_file.get('student_id') != STUDENT_ID
        ]
        assert collected_ora_files_data == expected_files

    def test_create_zip_with_attachments(self):
        """
        Test that ZIP file generated by `create_zip_with_attachments` contains
        correct files and their paths are also correct.
        """

        file = BytesIO()

        file_content = b'file_content'

        with patch(
            'openassessment.data.OraDownloadData._download_file_by_key', return_value=file_content
        ) as download_mock:
            OraDownloadData.create_zip_with_attachments(file, self.submission_files_data)

            download_mock.assert_has_calls([
                call(self.file_key_5),
                call(self.file_key_4),
                call(self.file_key_1),
                call(self.file_key_2),
                call(self.file_key_3),
            ])

        with zipfile.ZipFile(file) as zip_file:

            # archive should contain five attachments, three parts text file and one csv
            self.assertEqual(len(zip_file.infolist()), 9)

            def get_filepath(submission_index):
                # pylint: disable=protected-access
                return OraDownloadData._submission_filepath(
                    ITEM_PATH_INFO,
                    USERNAME_MAPPING[self.submission_files_data[submission_index]['student_id']],
                    self.submission_files_data[submission_index]['name'],
                )

            # check for pre_file_name_user's file and text
            self.assertEqual(
                zip_file.read(get_filepath(0)), file_content
            )
            self.assertEqual(
                zip_file.read(get_filepath(1)), self.answer_text.encode('utf-8')
            )
            # check for pre_file_size_user's file and text
            self.assertEqual(
                zip_file.read(get_filepath(2)), file_content
            )
            self.assertEqual(
                zip_file.read(get_filepath(3)), self.answer_text.encode('utf-8')
            )
            # check that main user's attachments have been written to the archive
            self.assertEqual(
                zip_file.read(get_filepath(4)), file_content
            )
            self.assertEqual(
                zip_file.read(get_filepath(5)), file_content
            )
            self.assertEqual(
                zip_file.read(get_filepath(6)), file_content
            )
            # main user's text response
            self.assertEqual(
                zip_file.read(get_filepath(7)), self.answer_text.encode('utf-8')
            )

            self.assertTrue(zip_file.read('submissions.csv'))

    def test_csv_file_for_create_zip_with_attachments(self):
        file = BytesIO()

        file_content = b'file_content'

        with patch('openassessment.data.OraDownloadData._download_file_by_key', return_value=file_content):
            OraDownloadData.create_zip_with_attachments(file, self.submission_files_data)

        with zipfile.ZipFile(file) as zip_file:
            self.assertTrue(zip_file.read('submissions.csv'))

            with zip_file.open('submissions.csv') as csv_file:
                csv_reader = csv.DictReader(TextIOWrapper(csv_file, 'utf-8'))
                for row in csv_reader:
                    # csv file contains OraDownloadData.SUBMISSIONS_CSV_HEADER
                    for column in OraDownloadData.SUBMISSIONS_CSV_HEADER:
                        # prove that all column exist
                        self.assertIn(column, row)
                    # file_found column is True for all of them
                    self.assertEqual(row['file_found'], 'True')
                    # all those file exist in the zipfile
                    self.assertTrue(zipfile.Path(zip_file, row['file_path']).exists())

    def test_create_zip_with_failed_attachments(self):
        file = BytesIO()

        with patch(
            'openassessment.data.OraDownloadData._download_file_by_key'
        ) as download_mock:
            download_mock.side_effect = FileMissingException
            OraDownloadData.create_zip_with_attachments(file, self.submission_files_data)

            download_mock.assert_has_calls([
                call(self.file_key_5),
                call(self.file_key_4),
                call(self.file_key_1),
                call(self.file_key_2),
                call(self.file_key_3),
            ])

        with zipfile.ZipFile(file) as zip_file:
            # archive should contain only three parts text file and one csv because all of the attachments are invalid
            self.assertEqual(len(zip_file.infolist()), 4)

            # expect text file found in the zip file
            self.assertTrue(zipfile.Path(zip_file, self.submission_files_data[1]['file_path']).exists())
            self.assertTrue(zipfile.Path(zip_file, self.submission_files_data[3]['file_path']).exists())
            self.assertTrue(zipfile.Path(zip_file, self.submission_files_data[7]['file_path']).exists())

            # check for pre_file_name_user's text file
            self.assertEqual(
                zip_file.read(self.submission_files_data[1]['file_path']),
                self.answer_text.encode('utf-8')
            )
            self.assertEqual(
                zip_file.read(self.submission_files_data[3]['file_path']),
                self.answer_text.encode('utf-8')
            )

            # main user's text response
            self.assertEqual(
                zip_file.read(self.submission_files_data[7]['file_path']),
                self.answer_text.encode('utf-8')
            )

            # expect file not found in the zip file
            self.assertFalse(zipfile.Path(zip_file, self.submission_files_data[0]['file_path']).exists())
            self.assertFalse(zipfile.Path(zip_file, self.submission_files_data[2]['file_path']).exists())
            self.assertFalse(zipfile.Path(zip_file, self.submission_files_data[4]['file_path']).exists())
            self.assertFalse(zipfile.Path(zip_file, self.submission_files_data[6]['file_path']).exists())

    def test_csv_file_for_create_zip_with_failed_attachments(self):
        file = BytesIO()

        with patch(
            'openassessment.data.OraDownloadData._download_file_by_key'
        ) as download_mock:
            download_mock.side_effect = FileMissingException
            OraDownloadData.create_zip_with_attachments(file, self.submission_files_data)

        with zipfile.ZipFile(file) as zip_file:
            self.assertTrue(zip_file.read('submissions.csv'))

            with zip_file.open('submissions.csv') as csv_file:
                csv_reader = csv.DictReader(TextIOWrapper(csv_file, 'utf-8'))
                for row in csv_reader:
                    # csv file contains OraDownloadData.SUBMISSIONS_CSV_HEADER
                    for column in OraDownloadData.SUBMISSIONS_CSV_HEADER:
                        # prove that all column exist
                        self.assertIn(column, row)
                    # csv and data in the zip file are consistence
                    if row['file_found'] == 'False':
                        self.assertFalse(zipfile.Path(zip_file, row['file_path']).exists())
                    else:
                        self.assertTrue(zipfile.Path(zip_file, row['file_path']).exists())

    @ddt.data(
        (
            "Section",
            "Sub Section",
            "Unit",
            "test.jpg",
            "username",
            "[1]Section, [1]Sub Section, [1]Unit/[1] - username - test.jpg",
        ),
        (
            "Section",
            "x" * 1000,
            "Unit",
            "test.jpg",
            "username",
            # subsection name truncated
            f"[1]Section, [1]{'x' * 231}, [1]Unit/[1] - username - test.jpg",
        ),
        (
            "Section",
            "x" * 1000,
            "y" * 1000,
            "test.jpg",
            "username",
            # subsection name removed, unit name truncated
            f"[1]Section, [1], [1]{'y' * 235}/[1] - username - test.jpg",
        ),
        (
            "z" * 1000,
            "x" * 1000,
            "y" * 1000,
            "test.jpg",
            "username",
            # everything removed, section name truncated
            f"[1]{'z' * 242}, [1], [1]/[1] - username - test.jpg",
        ),
        (
            "Section",
            "Sub Section",
            "Unit",
            f"{'x' * 251}.jpg",
            "username",
            # filename base truncated
            f"[1]Section, [1]Sub Section, [1]Unit/[1] - username - {'x' * 234}.jpg",
        ),
    )
    @ddt.unpack
    def test_truncation_of_submission_filepath(
        self, section_name, sub_section_name, unit_name, file_name, username, file_path
    ):
        """
        Test that `_submission_filepath` truncates less important data first and keeps
        file name less than 255.
        """

        path_info = {
            "section_index": 1,
            "section_name": section_name,
            "sub_section_index": 1,
            "sub_section_name": sub_section_name,
            "unit_index": 1,
            "unit_name": unit_name,
            "ora_index": 1,
            "ora_name": ITEM_DISPLAY_NAME,
        }
        # pylint: disable=protected-access
        assert OraDownloadData._submission_filepath(path_info, username, file_name) == file_path


submission_test_parts = [{'text': 'text_response_' + str(i)} for i in range(3)]
submission_test_file_keys = ['test-key-' + str(i) for i in range(3)]
submission_test_file_names = ['test-name-' + str(i) for i in range(3)]
submission_test_file_descriptions = ['Description for file ' + str(i) for i in range(3)]
submission_test_file_sizes = list(range(3))

version_1_submission_answer = {
    'file_key': 'test-key-0',
    'parts': submission_test_parts
}
version_2_submission_answer = {
    'file_keys': submission_test_file_keys,
    'files_descriptions': submission_test_file_descriptions,
    'parts': submission_test_parts
}
version_3_submission_answer = {
    'file_keys': submission_test_file_keys,
    'files_descriptions': submission_test_file_descriptions,
    'files_name': submission_test_file_names,
    'parts': submission_test_parts
}
version_4_submission_answer = {
    'file_keys': submission_test_file_keys,
    'files_descriptions': submission_test_file_descriptions,
    'files_name': submission_test_file_names,
    'files_sizes': submission_test_file_sizes,
    'parts': submission_test_parts
}
version_5_submission_answer = {
    'file_keys': submission_test_file_keys,
    'files_descriptions': submission_test_file_descriptions,
    'files_names': submission_test_file_names,
    'files_sizes': submission_test_file_sizes,
    'parts': submission_test_parts
}
all_version_submission_answers = [
    version_1_submission_answer,
    version_2_submission_answer,
    version_3_submission_answer,
    version_4_submission_answer,
    version_5_submission_answer
]
unknown_submission_answer = {'color': 'Bronze Mist Metallic', 'year': 2002, 'make': 'Chevrolet', 'model': 'Tracker'}
text_only_submission_answer = {'parts': submission_test_parts}


class SubmissionFileUploadTest(TestCase):
    """ Unit tests for SubmissionFileUpload """
    KEY = 'test-key'

    def test_default_values(self):
        upload = SubmissionFileUpload(self.KEY)
        self.assertEqual(upload.name, SubmissionFileUpload.generate_name_from_key(self.KEY))
        self.assertEqual(upload.description, SubmissionFileUpload.DEFAULT_DESCRIPTION)
        self.assertEqual(upload.size, 0)


class OraSubmissionAnswerFactoryTest(TestCase):
    """ Unit tests for OraSubmissionAnswerFactory """

    def test_parse_submission_raw_answer__text_only(self):
        submission = OraSubmissionAnswerFactory.parse_submission_raw_answer(
            {'parts': submission_test_parts}
        )
        self.assertTrue(isinstance(submission, OraSubmissionAnswer))
        self.assertTrue(isinstance(submission, TextOnlySubmissionAnswer))

    def test_parse_submission_raw_answer__zipped_list_submission(self):
        submission = OraSubmissionAnswerFactory.parse_submission_raw_answer(
            version_1_submission_answer
        )
        self.assertTrue(isinstance(submission, OraSubmissionAnswer))
        self.assertTrue(isinstance(submission, ZippedListSubmissionAnswer))

    def test_parse_submission_raw_answer__unknown(self):
        with self.assertRaisesMessage(VersionNotFoundException, "No ORA Submission Answer version recognized"):
            OraSubmissionAnswerFactory.parse_submission_raw_answer(unknown_submission_answer)


@ddt.ddt
class TextOnlySubmissionAnswerTest(TestCase):
    """ Unit tests for TextOnlySubmissionAnswer """
    @ddt.unpack
    @ddt.data(
        (version_1_submission_answer, False),
        (version_2_submission_answer, False),
        (version_3_submission_answer, False),
        (version_4_submission_answer, False),
        (version_5_submission_answer, False),
        (text_only_submission_answer, True),
        (unknown_submission_answer, False),
    )
    def test_matches(self, submission, should_match):
        self.assertEqual(TextOnlySubmissionAnswer.matches(submission), should_match)

    def test_get_responses(self):
        submission = TextOnlySubmissionAnswer(text_only_submission_answer)
        text_responses = submission.get_text_responses()
        self.assertEqual(len(text_responses), 3)
        for i, text_response in enumerate(text_responses):
            self.assertEqual(text_response, f'text_response_{i}')
        self.assertEqual(submission.get_file_uploads(), [])


@ddt.ddt
class ZippedListSubmissionAnswerTest(TestCase):
    """ Unit tests for ZippedListSubmissionAnswer """

    @ddt.unpack
    @ddt.data(
        (version_1_submission_answer, True),
        (version_2_submission_answer, True),
        (version_3_submission_answer, True),
        (version_4_submission_answer, True),
        (version_5_submission_answer, True),
        (text_only_submission_answer, False),
        (unknown_submission_answer, False),
    )
    def test_matches(self, submission, should_match):
        self.assertEqual(ZippedListSubmissionAnswer.matches(submission), should_match)

    @ddt.data(
        (version_1_submission_answer, 1),
        (version_2_submission_answer, 2),
        (version_3_submission_answer, 3),
        (version_4_submission_answer, 4),
        (version_5_submission_answer, 5),
    )
    @ddt.unpack
    def test_does_version_match(self, raw_answer, version):
        version = ZIPPED_LIST_SUBMISSION_VERSIONS[version - 1]
        # Keys from submission should match version
        raw_answer_keys = set(raw_answer.keys())
        self.assertTrue(ZippedListSubmissionAnswer.does_version_match(raw_answer_keys, version))
        # Missing 'parts' should still match version
        raw_answer_keys.remove('parts')
        self.assertTrue(ZippedListSubmissionAnswer.does_version_match(raw_answer_keys, version))
        # Unrecognized keys should not match.
        raw_answer_keys.add('something_else')
        self.assertFalse(ZippedListSubmissionAnswer.does_version_match(raw_answer_keys, version))
        # No other version answer should match this version
        all_other_version_answers = [answer for answer in all_version_submission_answers if answer is not raw_answer]
        for other_version_raw_answer in all_other_version_answers:
            self.assertFalse(
                ZippedListSubmissionAnswer.does_version_match(
                    set(other_version_raw_answer.keys()),
                    version
                )
            )

    @ddt.data(
        (version_1_submission_answer, 1),
        (version_2_submission_answer, 2),
        (version_3_submission_answer, 3),
        (version_4_submission_answer, 4),
        (version_5_submission_answer, 5),
    )
    @ddt.unpack
    def test_get_version(self, submission, version):
        self.assertEqual(
            ZippedListSubmissionAnswer.get_version(submission),
            ZIPPED_LIST_SUBMISSION_VERSIONS[version - 1]  # Adjusted version -> index
        )

    def test_get_version_not_found(self):
        """ Test that a non-recognized submission version will raise an exception """
        with self.assertRaisesMessage(VersionNotFoundException, "No zipped list version found with keys"):
            ZippedListSubmissionAnswer.get_version(unknown_submission_answer)

    @ddt.data(*all_version_submission_answers)
    def test_get_submission_values(self, raw_submission):
        """
        Test that the files are parsed from the submission correctly
        """
        submission = ZippedListSubmissionAnswer(raw_submission)
        self.assertEqual(
            submission.get_text_responses(),
            ['text_response_0', 'text_response_1', 'text_response_2']
        )
        file_uploads = submission.get_file_uploads()
        if raw_submission == version_1_submission_answer:
            self.assertEqual(len(file_uploads), 1)
        else:
            self.assertEqual(len(file_uploads), 3)

        for i, file_upload in enumerate(file_uploads):
            self.assertTrue(isinstance(file_upload, SubmissionFileUpload))
            self.assertEqual(file_upload.key, submission_test_file_keys[i])
            self.assertEqual(
                file_upload.name,
                submission_test_file_names[i] if submission.version.name
                else SubmissionFileUpload.generate_name_from_key(file_upload.key)
            )
            self.assertEqual(
                file_upload.description,
                submission_test_file_descriptions[i] if submission.version.description
                else SubmissionFileUpload.DEFAULT_DESCRIPTION
            )
            self.assertEqual(
                file_upload.size,
                submission_test_file_sizes[i] if submission.version.size else 0
            )

    @ddt.data(True, False)
    def test_get_file_uploads_empty_fields(self, missing_blank):
        """ Test that for submissions with missing data, files can still be parsed correctly """
        # Submission with no descriptions. The key will exist, but it will be an empty list
        version_5 = ZIPPED_LIST_SUBMISSION_VERSIONS[4]
        no_description_submission = deepcopy(version_5_submission_answer)
        no_description_submission[version_5.description] = []

        submission = ZippedListSubmissionAnswer(no_description_submission)
        self.assertEqual(submission.version, version_5)

        file_uploads = submission.get_file_uploads(missing_blank=missing_blank)
        self.assertEqual(len(file_uploads), 3)
        for i, file_upload in enumerate(file_uploads):
            self.assertEqual(file_upload.key, submission_test_file_keys[i])
            self.assertEqual(file_upload.name, submission_test_file_names[i])
            self.assertEqual(
                file_upload.description,
                '' if missing_blank else SubmissionFileUpload.DEFAULT_DESCRIPTION
            )
            self.assertEqual(file_upload.size, submission_test_file_sizes[i])

    def test_get_file_uploads_misaligned_fields(self):
        """ Test that for submissions with missing data, files can still be parsed correctly """
        # Submission with only one file name
        version_5 = ZIPPED_LIST_SUBMISSION_VERSIONS[4]
        misaligned_names_submission = deepcopy(version_5_submission_answer)
        misaligned_names_submission[version_5.name].pop()

        submission = ZippedListSubmissionAnswer(misaligned_names_submission)
        self.assertEqual(submission.version, version_5)

        file_uploads = submission.get_file_uploads()
        self.assertEqual(len(file_uploads), 3)
        for i, file_upload in enumerate(file_uploads):
            self.assertEqual(file_upload.key, submission_test_file_keys[i])
            if i == 2:
                self.assertEqual(file_upload.name, SubmissionFileUpload.generate_name_from_key(file_upload.key))
            else:
                self.assertEqual(file_upload.name, submission_test_file_names[i])
            self.assertEqual(file_upload.description, submission_test_file_descriptions[i])
            self.assertEqual(file_upload.size, submission_test_file_sizes[i])


@ddt.ddt
class ListAssessmentsTest(TestCase):
    """ Unit tests for List Assessments """

    @patch("openassessment.data.sub_api.get_submission_and_student")
    @patch("openassessment.data.Submission.objects.filter")
    @patch("openassessment.data._use_read_replica")
    @patch("openassessment.data.map_anonymized_ids_to_user_data")
    @patch("openassessment.data.generate_assessment_data")
    def test_generate_given_assessment_data(
        self,
        mock_generate_assessment_data,
        mock_map_anonymized_ids_to_user_data,
        mock__use_read_replica,
        mock_filter,
        mock_get_submission_and_student,
    ):
        mock_get_submission_and_student.return_value = {"student_item": {"student_id": "student1"}}
        mock_filter.return_value.values.return_value = [{"uuid": "uuid2"}]
        mock__use_read_replica.return_value = [Mock(scorer_id="scorer1"), Mock(scorer_id="scorer2")]
        mock_map_anonymized_ids_to_user_data.return_value = {"student1": "user1"}
        mock_generate_assessment_data.return_value = ["data1"]

        result = generate_given_assessment_data("test_item_id", "test_submission_uuid")

        self.assertEqual(result, ["data1"])

    @patch("openassessment.data.sub_api.get_submission_and_student")
    def test_generate_given_assessment_data_no_scorer_submission(
        self, mock_get_submission_and_student
    ):
        mock_get_submission_and_student.return_value = None

        result = generate_given_assessment_data("test_item_id", "test_submission_uuid")

        mock_get_submission_and_student.assert_called_once_with("test_submission_uuid")
        self.assertEqual(result, [])

    @patch("openassessment.data.sub_api.get_submission_and_student")
    @patch("openassessment.data.Submission.objects.filter")
    def test_generate_given_assessment_data_no_submissions(
        self, mock_filter, mock_get_submission_and_student
    ):
        mock_get_submission_and_student.return_value = {"student_item": {"student_id": "test_student_id"}}
        mock_filter.return_value.values.return_value = []

        result = generate_given_assessment_data("test_item_id", "test_uuid")

        mock_get_submission_and_student.assert_called_once_with("test_uuid")
        mock_filter.assert_called_once()
        self.assertEqual(result, [])

    @patch("openassessment.data.sub_api.get_submission_and_student")
    @patch("openassessment.data._use_read_replica")
    @patch("openassessment.data.map_anonymized_ids_to_user_data")
    @patch("openassessment.data.generate_assessment_data")
    def test_generate_received_assessment_data(
        self,
        mock_generate_assessment_data,
        mock_map_anonymized_ids_to_user_data,
        mock__use_read_replica,
        mock_get_submission_and_student
    ):
        mock_get_submission_and_student.return_value = {"uuid": "test_uuid"}
        mock_assessment = Mock(scorer_id="test_scorer_id")
        mock__use_read_replica.return_value = [mock_assessment]
        mock_map_anonymized_ids_to_user_data.return_value = {"test_scorer_id": "test_user_data"}
        mock_generate_assessment_data.return_value = "test_assessment_data"

        result = generate_received_assessment_data("submission_uuid")

        mock_get_submission_and_student.assert_called_once_with("submission_uuid")
        mock__use_read_replica.assert_called_once()
        mock_map_anonymized_ids_to_user_data.assert_called_once_with(["test_scorer_id"])
        mock_generate_assessment_data.assert_called_once_with([mock_assessment], {"test_scorer_id": "test_user_data"})
        self.assertEqual(result, "test_assessment_data")

    @patch("openassessment.data.sub_api.get_submission_and_student")
    def test_generate_received_assessment_data_no_submission(self, mock_get_submission_and_student):
        mock_get_submission_and_student.return_value = None

        result = generate_received_assessment_data("submission_uuid")

        mock_get_submission_and_student.assert_called_once_with("submission_uuid")
        self.assertEqual(result, [])

    @patch('openassessment.data.get_scorer_data')
    @patch('openassessment.data.parts_summary')
    @patch('openassessment.data.score_type_to_string')
    def test_generate_assessment_data(self, mock_score_type_to_string, mock_parts_summary, mock_get_scorer_data):
        mock_get_scorer_data.return_value = ('Scorer Name', 'Scorer Username', 'Scorer Email')
        mock_parts_summary.return_value = 'Summary'
        mock_score_type_to_string.return_value = 'Step'
        mock_assessment = Mock(id=1, scorer_id='scorer_id', scored_at='2022-01-01', feedback='Good job!')
        assessment_list = [mock_assessment]
        user_data_mapping = {
            'scorer_id': {
                'email': 'scorer@email.com',
                'username': 'scorer_username',
                'fullname': 'Scorer Fullname',
            }
        }
        expected_result = [{
            "assessment_id": "1",
            "scorer_name": 'Scorer Name',
            "scorer_username": 'Scorer Username',
            "scorer_email": 'Scorer Email',
            "assesment_date": '2022-01-01',
            "assesment_scores": 'Summary',
            "problem_step": 'Step',
            "feedback": 'Good job!',
        }]

        result = generate_assessment_data(assessment_list, user_data_mapping)

        self.assertEqual(result, expected_result)
        mock_get_scorer_data.assert_called_once_with('scorer_id', user_data_mapping)
        mock_parts_summary.assert_called_once_with(mock_assessment)
        mock_score_type_to_string.assert_called_once_with(mock_assessment.score_type)

    @ddt.data(
        ("anon_scorer_1", "John Doe", "johndoe", "johndoe@example.com"),
        ("anon_scorer_non_existing_user", "", "", ""),
    )
    @ddt.unpack
    def test_get_scorer_data(self, scored_id, fullname_mock, username_mock, email_mock):
        user_data_mapping = {
            "anon_scorer_1": {
                "fullname": "John Doe",
                "username": "johndoe",
                "email": "johndoe@example.com"
            },
            "anon_scorer_2": {
                "fullname": "Jane Doe",
                "username": "janedoe",
                "email": "janedoe@example.com"
            }
        }

        fullname, username, email = get_scorer_data(scored_id, user_data_mapping)

        self.assertEqual(fullname, fullname_mock)
        self.assertEqual(username, username_mock)
        self.assertEqual(email, email_mock)

    def test_get_scorer_data_empty_mapping(self):
        fullname, username, email = get_scorer_data("anon_scorer_1", {})

        self.assertEqual(fullname, "")
        self.assertEqual(username, "")
        self.assertEqual(email, "")

    def test_parts_summary_with_multiple_parts(self):
        assessment_obj = Mock()
        part1 = Mock()
        part1.criterion.name = "Criterion 1"
        part1.points_earned = 10
        part1.option.name = "Good"

        part2 = Mock()
        part2.criterion.name = "Criterion 2"
        part2.points_earned = 8
        part2.option.name = "Excellent"

        assessment_obj.parts.all.return_value = [part1, part2]

        expected_parts_summary = [
            {
                "criterion_name": "Criterion 1",
                "score_earned": 10,
                "score_type": "Good",
            },
            {
                "criterion_name": "Criterion 2",
                "score_earned": 8,
                "score_type": "Excellent",
            },
        ]

        result = parts_summary(assessment_obj)
        self.assertEqual(result, expected_parts_summary)

    def test_parts_summary_empty(self):
        assessment_obj = Mock()
        assessment_obj.parts.all.return_value = []

        result = parts_summary(assessment_obj)

        self.assertEqual(result, [])
