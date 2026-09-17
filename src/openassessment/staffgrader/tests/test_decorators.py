"""
Tests for decorators used in Staff Grading
"""
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from mock import Mock
from xblock.exceptions import JsonHandlerError
from submissions.errors import (
    SubmissionInternalError,
    SubmissionNotFoundError,
    SubmissionRequestError,
    TeamSubmissionInternalError,
    TeamSubmissionNotFoundError
)
from openassessment.staffgrader.staff_grader_mixin import require_submission_uuid


class RequireSubmissionUUIDTest(TestCase):
    valid_data = {"submission_uuid": uuid4()}

    def setUp(self):
        super().setUp()
        self.mock_self = Mock(is_team_assignment=lambda: False)
        self.mock_function = Mock()
        self.mock_suffix = Mock()
        self.wrapped_function = require_submission_uuid()(self.mock_function)

    def test_no_submission_uuid(self):
        with self.assertRaises(JsonHandlerError) as error_context:
            self.wrapped_function(self.mock_self, {'some_key': 1, 'other_key': 2})

        self.mock_function.assert_not_called()
        self.assertEqual(error_context.exception.status_code, 400)
        self.assertEqual(error_context.exception.message, 'Body must contain a submission_uuid')

    def test_arguments_passed(self):
        self.wrapped_function = require_submission_uuid(validate=False)(self.mock_function)

        data = {str(i): str((i * 2) - 1) for i in range(10)}
        submission_uuid = uuid4()
        data['submission_uuid'] = submission_uuid

        result = self.wrapped_function(self.mock_self, data, suffix=self.mock_suffix)

        self.assertEqual(result, self.mock_function.return_value)
        self.mock_function.assert_called_once_with(self.mock_self, submission_uuid, data, suffix=self.mock_suffix)

    @patch('openassessment.staffgrader.staff_grader_mixin.get_submission')
    def test_validate_submission(self, mock_get_submission):  # pylint: disable=unused-argument
        mock_get_submission.return_value = {}
        submission_uuid = self.valid_data['submission_uuid']
        result = self.wrapped_function(self.mock_self, self.valid_data, suffix=self.mock_suffix)

        self.assertEqual(result, self.mock_function.return_value)
        self.mock_function.assert_called_once_with(
            self.mock_self,
            submission_uuid,
            self.valid_data,
            suffix=self.mock_suffix,
        )

    @patch('openassessment.staffgrader.staff_grader_mixin.get_team_submission')
    def test_validate_team_submission(self, mock_get_team_submission):  # pylint: disable=unused-argument
        self.mock_self.is_team_assignment = lambda: True
        mock_get_team_submission.return_value = {}
        team_submission_uuid = self.valid_data['submission_uuid']
        result = self.wrapped_function(self.mock_self, self.valid_data, suffix=self.mock_suffix)

        self.assertEqual(result, self.mock_function.return_value)
        self.mock_function.assert_called_once_with(
            self.mock_self,
            team_submission_uuid,
            self.valid_data,
            suffix=self.mock_suffix,
        )

    @patch('openassessment.staffgrader.staff_grader_mixin.get_submission')
    def test_validate_submission_not_found(self, mock_get_submission):
        mock_get_submission.side_effect = SubmissionNotFoundError

        with self.assertRaises(JsonHandlerError) as error_context:
            self.wrapped_function(self.mock_self, self.valid_data)

        self.mock_function.assert_not_called()
        self.assertEqual(error_context.exception.status_code, 404)
        self.assertEqual(error_context.exception.message, 'Submission not found')

    @patch('openassessment.staffgrader.staff_grader_mixin.get_team_submission')
    def test_validate_team_submission_not_found(self, mock_get_team_submission):
        self.mock_self.is_team_assignment = lambda: True
        mock_get_team_submission.side_effect = TeamSubmissionNotFoundError

        with self.assertRaises(JsonHandlerError) as error_context:
            self.wrapped_function(self.mock_self, self.valid_data)

        self.mock_function.assert_not_called()
        self.assertEqual(error_context.exception.status_code, 404)
        self.assertEqual(error_context.exception.message, 'Submission not found')

    @patch('openassessment.staffgrader.staff_grader_mixin.get_submission')
    def test_validate_bad_submission_uuid(self, mock_get_submission):
        mock_get_submission.side_effect = SubmissionRequestError

        with self.assertRaises(JsonHandlerError) as error_context:
            self.wrapped_function(self.mock_self, self.valid_data)

        self.mock_function.assert_not_called()
        self.assertEqual(error_context.exception.status_code, 400)
        self.assertEqual(error_context.exception.message, 'Bad submission_uuid provided')

    @patch('openassessment.staffgrader.staff_grader_mixin.get_team_submission')
    def test_validate_bad_team_submission_uuid(self, mock_get_team_submission):
        mock_get_team_submission.side_effect = TeamSubmissionInternalError

        with self.assertRaises(JsonHandlerError) as error_context:
            self.wrapped_function(self.mock_self, self.valid_data)

        # NOTE - The team API is slightly different, a non-UUID is
        # handled as an internal error instead of a request error
        self.mock_function.assert_not_called()
        self.assertEqual(error_context.exception.status_code, 500)
        self.assertEqual(error_context.exception.message, 'Internal error getting submission info')

    @patch('openassessment.staffgrader.staff_grader_mixin.get_submission')
    def test_validate_submission_error(self, mock_get_submission):
        mock_get_submission.side_effect = SubmissionInternalError

        with self.assertRaises(JsonHandlerError) as error_context:
            self.wrapped_function(self.mock_self, self.valid_data)

        self.mock_function.assert_not_called()
        self.assertEqual(error_context.exception.status_code, 500)
        self.assertEqual(error_context.exception.message, 'Internal error getting submission info')
