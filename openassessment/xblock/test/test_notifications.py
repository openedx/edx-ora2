"""
Unit test for notification util
"""
import unittest
from unittest.mock import patch

from openassessment.xblock.utils.notifications import send_staff_notification


class TestSendStaffNotification(unittest.TestCase):
    """
    Test for send_staff_notification function
    """
    @patch('openassessment.xblock.utils.notifications.COURSE_NOTIFICATION_REQUESTED.send_event')
    def test_send_staff_notification(self, mock_send_event):
        """
        Test send_staff_notification function
        """
        # Mocked data
        course_id = 'course_id'
        problem_id = 'problem_id'
        ora_name = 'ora_name'

        # Call the function
        send_staff_notification(course_id, problem_id, ora_name)

        # Assertions
        mock_send_event.assert_called_once()
        args, kwargs = mock_send_event.call_args
        notification_data = kwargs['course_notification_data']

        # Check if CourseNotificationData is properly initialized
        self.assertEqual(notification_data.course_key, course_id)
        self.assertEqual(notification_data.content_context['ora_name'], ora_name)
        self.assertEqual(notification_data.notification_type, 'ora_staff_notification')
        self.assertEqual(notification_data.content_url, f"/{problem_id}")
        self.assertEqual(notification_data.app_name, "ora")
        self.assertEqual(notification_data.audience_filters['course_roles'], ['staff', 'instructor'])

    @patch('openassessment.xblock.utils.notifications.logger.error')
    @patch('openassessment.xblock.utils.notifications.COURSE_NOTIFICATION_REQUESTED.send_event')
    def test_send_staff_notification_error_logging(self, mock_send_event, mock_logger_error):
        """
        Test send_staff_notification function when an exception is raised
        """
        # Mocked data
        course_id = 'course_id'
        problem_id = 'problem_id'
        ora_name = 'ora_name'

        # Mock exception
        mock_exception = Exception('Test exception')

        mock_send_event.side_effect = mock_exception

        # Call the function
        send_staff_notification(course_id, problem_id, ora_name)

        # Assertions
        mock_logger_error.assert_called_once_with(f"Error while sending ora staff notification: {mock_exception}")
