# -*- coding: utf-8 -*-
"""
Test OpenAssessment XBlock validation.
"""

import copy
from datetime import datetime as dt
import mock
import pytz
import ddt
from django.test import TestCase
from openassessment.xblock.openassessmentblock import OpenAssessmentBlock
from openassessment.xblock.validation import validator, validate_assessments, validate_rubric, validate_dates


@ddt.ddt
class AssessmentValidationTest(TestCase):

    @ddt.file_data('data/valid_assessments.json')
    def test_valid_assessment(self, data):
        success, msg = validate_assessments(data["assessments"], data["current_assessments"], data["is_released"])
        self.assertTrue(success)
        self.assertEqual(msg, u'')

    @ddt.file_data('data/invalid_assessments.json')
    def test_invalid_assessment(self, data):
        success, msg = validate_assessments(data["assessments"], data["current_assessments"], data["is_released"])
        self.assertFalse(success)
        self.assertGreater(len(msg), 0)

    def test_no_assessments(self):
        success, msg = validate_assessments([], [], False)
        self.assertFalse(success)
        self.assertGreater(len(msg), 0)

    # Make sure only legal assessment combinations are allowed. For now, that's
    # (peer -> self), and (self)
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
        success, msg = validate_assessments(assessments, current_assessments, is_released)
        self.assertEqual(success, expected_is_valid, msg=msg)

        if not success:
            self.assertGreater(len(msg), 0)


@ddt.ddt
class RubricValidationTest(TestCase):

    @ddt.file_data('data/valid_rubrics.json')
    def test_valid_assessment(self, data):
        success, msg = validate_rubric(data['rubric'], data['current_rubric'], data['is_released'])
        self.assertTrue(success)
        self.assertEqual(msg, u'')

    @ddt.file_data('data/invalid_rubrics.json')
    def test_invalid_assessment(self, data):
        success, msg = validate_rubric(data['rubric'], data['current_rubric'], data['is_released'])
        self.assertFalse(success)
        self.assertGreater(len(msg), 0)


@ddt.ddt
class DateValidationTest(TestCase):

    def setUp(self):
        self.DATES = {
            (day - 1): dt(2014, 1, day).replace(tzinfo=pytz.UTC).isoformat()
            for day in range(1, 15)
        }
        self.DATES[None] = None

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

        # Input data dict specifies the index for each date
        date = lambda key: self.DATES[data[key]]

        # This lambda is a convenience to map these dates to (start, due) tuples
        date_range = lambda start_key, due_key: (date(start_key), date(due_key))

        success, msg = validate_dates(
            date('xblock_start'), date('xblock_due'),
            [
                date_range('submission_start', 'submission_due'),
                date_range('peer_start', 'peer_due'),
                date_range('self_start', 'self_due'),
            ]
        )

        self.assertTrue(success, msg=msg)
        self.assertEqual(msg, u'')

    @ddt.file_data('data/invalid_dates.json')
    def test_invalid_dates(self, data):
        # Input data dict specifies the index for each date
        date = lambda key: self.DATES[data[key]]

        # This lambda is a convenience to map these dates to (start, due) tuples
        date_range = lambda start_key, due_key: (date(start_key), date(due_key))

        success, msg = validate_dates(
            date('xblock_start'), date('xblock_due'),
            [
                date_range('submission_start', 'submission_due'),
                date_range('peer_start', 'peer_due'),
                date_range('self_start', 'self_due'),
            ]
        )

        self.assertFalse(success)
        self.assertGreater(len(msg), 0)

    def test_invalid_date_format(self):
        valid = dt(2014, 1, 1).replace(tzinfo=pytz.UTC).isoformat()

        success, _ = validate_dates("invalid", valid, [(valid, valid)])
        self.assertFalse(success)

        success, _ = validate_dates(valid, "invalid", [(valid, valid)])
        self.assertFalse(success)

        success, _ = validate_dates(valid, valid, [("invalid", valid)])
        self.assertFalse(success)

        success, _ = validate_dates(valid, valid, [(valid, "invalid")])
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

    SUBMISSION = {
        "due": None
    }

    ASSESSMENTS = [
        {
            "name": "student-training",
            "start": None,
            "due": None,
            "examples": [
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
        self.oa_block = mock.MagicMock(OpenAssessmentBlock)
        self.oa_block.is_released.return_value = False
        self.oa_block.rubric_assessments.return_value = []
        self.oa_block.prompt = ""
        self.oa_block.rubric_criteria = []
        self.oa_block.start = None
        self.oa_block.due = None
        self.validator = validator(self.oa_block)

    def test_student_training_examples_match_rubric(self):
        is_valid, msg = self.validator(self.RUBRIC, self.SUBMISSION, self.ASSESSMENTS)
        self.assertTrue(is_valid, msg=msg)
        self.assertEqual(msg, "")

    def test_student_training_examples_invalid_criterion(self):
        # Mutate the assessment training examples so the criterion names don't match the rubric
        mutated_assessments = copy.deepcopy(self.ASSESSMENTS)
        mutated_assessments[0]['examples'][0]['options_selected'][0]['criterion'] = 'Invalid criterion!'

        # Expect a validation error
        is_valid, msg = self.validator(self.RUBRIC, self.SUBMISSION, mutated_assessments)
        self.assertFalse(is_valid)
        self.assertEqual(msg, u'Example 1 has an extra option for "Invalid criterion!"\nExample 1 is missing an option for "vocabulary"')

    def test_student_training_examples_invalid_option(self):
        # Mutate the assessment training examples so the option names don't match the rubric
        mutated_assessments = copy.deepcopy(self.ASSESSMENTS)
        mutated_assessments[0]['examples'][0]['options_selected'][0]['option'] = 'Invalid option!'

        # Expect a validation error
        is_valid, msg = self.validator(self.RUBRIC, self.SUBMISSION, mutated_assessments)
        self.assertFalse(is_valid)
        self.assertEqual(msg, u'Example 1 has an invalid option for "vocabulary": "Invalid option!"')
