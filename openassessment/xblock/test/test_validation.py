"""
Test OpenAssessment XBlock validation.
"""
import copy
from datetime import datetime as dt
from unittest import mock

import ddt
import pytz

from django.test import TestCase

from openassessment.xblock.openassessmentblock import OpenAssessmentBlock
from openassessment.xblock.utils.validation import (
    validate_assessment_examples,
    validate_assessments,
    validate_dates,
    validate_rubric,
    validate_submission,
    validator
)


def STUB_I18N(x):
    return x


@ddt.ddt
class AssessmentValidationTest(TestCase):
    """ Test ora for Assessments. """

    @ddt.file_data('data/valid_assessments.json')
    def test_valid_assessment(self, data):
        success, msg = validate_assessments(
            data["assessments"], data["current_assessments"], data["is_released"], STUB_I18N
        )
        self.assertTrue(success)
        self.assertEqual(msg, '')

    @ddt.file_data('data/invalid_assessments.json')
    def test_invalid_assessment(self, data):
        success, msg = validate_assessments(
            data["assessments"], data["current_assessments"], data["is_released"], STUB_I18N
        )
        self.assertFalse(success)
        self.assertGreater(len(msg), 0)

    def test_no_assessments(self):
        success, msg = validate_assessments([], [], False, STUB_I18N)
        self.assertFalse(success)
        self.assertGreater(len(msg), 0)

    # Make sure only legal assessment combinations are allowed.
    @ddt.file_data('data/assessment_combo.json')
    def test_enforce_assessment_combo_restrictions(self, data):
        self._assert_validation(
            data["assessments"], data["current_assessments"],
            data["is_released"], data['valid']
        )

    @ddt.file_data('data/student_training_combo.json')
    def test_student_training_combos(self, data):
        self._assert_validation(
            data["assessments"], data["current_assessments"],
            data["is_released"], data['valid']
        )

    def _assert_validation(self, assessments, current_assessments, is_released, expected_is_valid):
        """
        Check that the validation function gives the expected result.
        If there is a validation error, check that the validation error message isn't empty.

        Args:
            assessments (list): The updated list of assessments
            current_assessments (list): The current assessments in the problem definition.
            is_released (bool): Whether the problem has been released yet.
            expected_is_valid (bool): Whether the inputs should be marked valid or invalid

        Returns:
            None

        Raises:
            AssertionError

        """
        success, msg = validate_assessments(assessments, current_assessments, is_released, STUB_I18N)
        self.assertEqual(success, expected_is_valid, msg=msg)

        if not success:
            self.assertGreater(len(msg), 0)


@ddt.ddt
class RubricValidationTest(TestCase):
    """ Test ora for example rubrics"""

    @ddt.file_data('data/valid_rubrics.json')
    def test_valid_rubric(self, data):
        current_rubric = data.get('current_rubric')
        is_released = data.get('is_released', False)
        success, msg = validate_rubric(
            data['rubric'],
            current_rubric,
            is_released,
            STUB_I18N
        )
        self.assertTrue(success)
        self.assertEqual(msg, '')

    @ddt.file_data('data/invalid_rubrics.json')
    def test_invalid_rubric(self, data):
        current_rubric = data.get('current_rubric')
        is_released = data.get('is_released', False)
        success, msg = validate_rubric(
            data['rubric'], current_rubric, is_released, STUB_I18N
        )
        self.assertFalse(success)
        self.assertGreater(len(msg), 0)


@ddt.ddt
class AssessmentExamplesValidationTest(TestCase):
    """ Test ora for example assessments. """

    @ddt.file_data('data/valid_assessment_examples.json')
    def test_valid_assessment_examples(self, data):
        success, msg = validate_assessment_examples(data['rubric'], data['assessments'], STUB_I18N)
        self.assertTrue(success)
        self.assertEqual(msg, '')

    @ddt.file_data('data/invalid_assessment_examples.json')
    def test_invalid_assessment_examples(self, data):
        success, msg = validate_assessment_examples(data['rubric'], data['assessments'], STUB_I18N)
        self.assertFalse(success)
        self.assertGreater(len(msg), 0)


@ddt.ddt
class DateValidationTest(TestCase):
    """ Test ora for example dates. """

    def setUp(self):
        super().setUp()
        self.DATES = {  # pylint: disable=invalid-name
            (day - 1): dt(2014, 1, day).replace(tzinfo=pytz.UTC).isoformat()
            for day in range(1, 15)
        }
        self.DATES[None] = None

    def date(self, data, key):
        """
        Input data dict specifies the index for each date
        """
        return self.DATES[data[key]]

    def date_range(self, data, start_key, due_key):
        """
        This function is a convenience to map these dates to (start, due) tuples
        """
        return (self.date(data, start_key), self.date(data, due_key))

    # There are a few test cases here that might seem incorrect:
    # * xblock_due_before_self_due
    # * xblock_start_equals_xblock_due
    # * xblock_start_past_submission_start
    # * xblock_start_past_xblock_due
    #
    # We count these as valid because the start/due date are inherited
    # from the LMS, thus bypassing our validation rules.
    # See the docstring for `resolve_dates` for a more detailed justification.
    @ddt.file_data('data/valid_dates.json')
    def test_valid_dates(self, data):
        success, msg = validate_dates(
            self.date(data, 'xblock_start'), self.date(data, 'xblock_due'),
            [
                self.date_range(data, 'submission_start', 'submission_due'),
                self.date_range(data, 'peer_start', 'peer_due'),
                self.date_range(data, 'self_start', 'self_due'),
            ],
            STUB_I18N
        )

        self.assertTrue(success, msg=msg)
        self.assertEqual(msg, '')

    @ddt.file_data('data/invalid_dates.json')
    def test_invalid_dates(self, data):
        success, msg = validate_dates(
            self.date(data, 'xblock_start'), self.date(data, 'xblock_due'),
            [
                self.date_range(data, 'submission_start', 'submission_due'),
                self.date_range(data, 'peer_start', 'peer_due'),
                self.date_range(data, 'self_start', 'self_due'),
            ],
            STUB_I18N
        )

        self.assertFalse(success)
        self.assertGreater(len(msg), 0)

    def test_invalid_date_format(self):
        valid = dt(2014, 1, 1).replace(tzinfo=pytz.UTC).isoformat()

        success, _ = validate_dates("invalid", valid, [(valid, valid)], STUB_I18N)
        self.assertFalse(success)

        success, _ = validate_dates(valid, "invalid", [(valid, valid)], STUB_I18N)
        self.assertFalse(success)

        success, _ = validate_dates(valid, valid, [("invalid", valid)], STUB_I18N)
        self.assertFalse(success)

        success, _ = validate_dates(valid, valid, [(valid, "invalid")], STUB_I18N)
        self.assertFalse(success)


class ValidationIntegrationTest(TestCase):
    """
    Each validation function is combined into a single function
    used by the OA XBlock itself.

    This tests the combined function, rather than the
    individual validation functions.
    """

    CRITERION_OPTIONS = [
        {
            "order_num": 0,
            "points": 0,
            "name": "Poor",
            "explanation": "Poor job!"
        },
        {
            "order_num": 1,
            "points": 1,
            "name": "Good",
            "explanation": "Good job!"
        }
    ]

    RUBRIC = {
        "criteria": [
            {
                "order_num": 0,
                "name": "vocabulary",
                "prompt": "How good is the vocabulary?",
                "options": CRITERION_OPTIONS
            },
            {
                "order_num": 1,
                "name": "grammar",
                "prompt": "How good is the grammar?",
                "options": CRITERION_OPTIONS
            }
        ]
    }

    EXAMPLES = [
        {
            "answer": "ẗëṡẗ äṅṡẅëṛ",
            "options_selected": [
                {
                    "criterion": "vocabulary",
                    "option": "Good"
                },
                {
                    "criterion": "grammar",
                    "option": "Poor"
                }
            ]
        }
    ]

    ASSESSMENTS = [
        {
            "name": "student-training",
            "start": None,
            "due": None,
            "examples": EXAMPLES,
        },
        {
            "name": "peer-assessment",
            "start": None,
            "due": None,
            "must_grade": 5,
            "must_be_graded_by": 3
        }
    ]

    def setUp(self):
        """
        Mock the OA XBlock and create a validator function.
        """
        super().setUp()
        self.oa_block = mock.MagicMock(OpenAssessmentBlock)
        self.oa_block.is_released.return_value = False
        self.oa_block.rubric_assessments.return_value = []
        self.oa_block.prompt = ""
        self.oa_block.rubric_criteria = []
        self.oa_block.start = None
        self.oa_block.due = None
        self.validator = validator(self.oa_block, STUB_I18N)

    def test_validates_successfully(self):
        is_valid, msg = self.validator(self.RUBRIC, self.ASSESSMENTS)
        self.assertTrue(is_valid, msg=msg)
        self.assertEqual(msg, "")

    def test_student_training_examples_invalid_criterion(self):
        # Mutate the assessment training examples so the criterion names don't match the rubric
        mutated_assessments = copy.deepcopy(self.ASSESSMENTS)
        mutated_assessments[0]['examples'][0]['options_selected'][0]['criterion'] = 'Invalid criterion!'

        # Expect a validation error
        is_valid, msg = self.validator(self.RUBRIC, mutated_assessments)
        self.assertFalse(is_valid)
        self.assertEqual(msg, (
            'Example 1 has an extra option for \"Invalid criterion!"; '
            'Example 1 is missing an option for "vocabulary"'
        ))

    def test_student_training_examples_invalid_option(self):
        # Mutate the assessment training examples so the option names don't match the rubric
        mutated_assessments = copy.deepcopy(self.ASSESSMENTS)
        mutated_assessments[0]['examples'][0]['options_selected'][0]['option'] = 'Invalid option!'

        # Expect a validation error
        is_valid, msg = self.validator(self.RUBRIC, mutated_assessments)
        self.assertFalse(is_valid)
        self.assertEqual(msg, 'Example 1 has an invalid option for "vocabulary": "Invalid option!"')

    def test_leaderboard_num_validation(self):
        self._assert_leaderboard_num_valid(-1, False)
        self._assert_leaderboard_num_valid(0, True)
        self._assert_leaderboard_num_valid(1, True)
        self._assert_leaderboard_num_valid(100, True)
        self._assert_leaderboard_num_valid(101, False)
        self._assert_leaderboard_num_valid(102, False)

    def _assert_leaderboard_num_valid(self, num, expected_is_valid):
        """
        Check that the leaderboard number is either valid or invalid.

        Args:
            num (int): The leaderboard number to check
            expected_is_valid (bool): Whether the number is valid or invalid.

        Raises:
            AssertionError

        """
        is_valid, msg = self.validator(self.RUBRIC, self.ASSESSMENTS, num)
        if expected_is_valid:
            self.assertTrue(is_valid, msg=f"Leaderboard num {num} should be valid")
            self.assertEqual(msg, '')
        else:
            self.assertFalse(is_valid, msg=f"Leaderboard num {num} should be invalid")
            self.assertEqual(msg, 'Leaderboard number is invalid.')


class ValidationSubmissionTest(TestCase):
    """
    Test validate_submission function.
    """

    PROMPT = [{"description": "A prompt."}, {"description": "Another prompt."}]

    def test_valid_submissions(self):
        success, _ = validate_submission(["A response."], [{"description": "A prompt."}], STUB_I18N)
        self.assertTrue(success)

        success, _ = validate_submission(
            ["Response 1.", "Response 2"], self.PROMPT, STUB_I18N
        )
        self.assertTrue(success)

    def test_invalid_submissions(self):
        # Submission is not list.
        success, _ = validate_submission("A response.", self.PROMPT, STUB_I18N)
        self.assertFalse(success)

        # Submission count does not match prompt count.
        success, _ = validate_submission(["A response."], self.PROMPT, STUB_I18N)
        self.assertFalse(success)

        # Submission is not unicode.
        success, _ = validate_submission(["A response.", b"Another response"], self.PROMPT, STUB_I18N)
        self.assertFalse(success)
