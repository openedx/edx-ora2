from unittest import TestCase
from mock import Mock
from uuid import uuid4

from xblock.exceptions import JsonHandlerError
from openassessment.staffgrader.staff_grader_mixin import require_submission_uuid

class RequireSubmissionUUIDTest(TestCase):
    def setUp(self):
        self.mock_self = Mock()
        self.mock_function = Mock()
        self.mock_suffix = Mock()
        self.wrapped_function = require_submission_uuid(self.mock_function)

    def test_no_submission_uuid(self):
        with self.assertRaises(JsonHandlerError) as error_context:
            self.wrapped_function(self.mock_self, {'some_key': 1, 'other_key': 2})

        self.mock_function.assert_not_called()
        self.assertEqual(error_context.exception.status_code, 400)
        self.assertEqual(error_context.exception.message, 'Body must contain a submission_id')

    def test_arguments_passed(self):
        data = {str(i): str((i * 2) - 1) for i in range(10)}
        submission_uuid = uuid4()
        data['submission_id'] = submission_uuid

        result = self.wrapped_function(self.mock_self, data, suffix=self.mock_suffix)

        self.assertEqual(result, self.mock_function.return_value)
        self.mock_function.assert_called_once_with(self.mock_self, submission_uuid, data, suffix=self.mock_suffix)
