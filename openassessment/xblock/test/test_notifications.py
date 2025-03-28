"""
Unit test for notification util
"""
import unittest
from unittest.mock import patch, MagicMock

from opaque_keys import InvalidKeyError

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldError
from openassessment.xblock.utils.notifications import send_staff_notification, send_grade_assigned_notification
from openassessment.workflow.errors import ItemNotFoundError

User = get_user_model()


class TestSendStaffNotification(unittest.TestCase):
    """
    Test for send_staff_notification function
    """
    @patch('openassessment.xblock.utils.notifications.modulestore')
    @patch('openassessment.xblock.utils.notifications.COURSE_NOTIFICATION_REQUESTED.send_event')
    def test_send_staff_notification(self, mock_send_event, mocked_modulestore):
        """
        Test send_staff_notification function
        """
        # Mocked data
        course_id = 'course_id'
        problem_id = 'problem_id'
        ora_name = 'ora_name'

        mocked_modulestore.return_value = MagicMock()

        # Call the function
        send_staff_notification(course_id, problem_id, ora_name)

        # Assertions
        mock_send_event.assert_called_once()
        args, kwargs = mock_send_event.call_args
        notification_data = kwargs['course_notification_data']

        # Check if CourseNotificationData is properly initialized
        self.assertEqual(notification_data.course_key, course_id)
        self.assertEqual(notification_data.content_context['ora_name'], ora_name)
        self.assertEqual(notification_data.notification_type, 'ora_staff_notifications')
        self.assertEqual(notification_data.content_url, f"/{problem_id}")
        self.assertEqual(notification_data.app_name, "grading")
        self.assertEqual(notification_data.audience_filters['course_roles'], ['staff', 'instructor'])

    @patch('openassessment.xblock.utils.notifications.modulestore')
    @patch('openassessment.xblock.utils.notifications.logger.error')
    @patch('openassessment.xblock.utils.notifications.COURSE_NOTIFICATION_REQUESTED.send_event')
    def test_send_staff_notification_error_logging(self, mock_send_event, mock_logger_error, mocked_modulestore):
        """
        Test send_staff_notification function when an exception is raised
        """
        # Mocked data
        course_id = 'course_id'
        problem_id = 'problem_id'
        ora_name = 'ora_name'

        mocked_modulestore.return_value = MagicMock()

        # Mock exception
        mock_exception = Exception('Test exception')

        mock_send_event.side_effect = mock_exception

        # Call the function
        send_staff_notification(course_id, problem_id, ora_name)

        # Assertions
        mock_logger_error.assert_called_once_with(f"Error while sending ora staff notification: {mock_exception}")


class TestSendGradeAssignedNotification(unittest.TestCase):

    def setUp(self):
        self.usage_id = 'block-v1:TestX+TST+TST+type@problem+block@ora'
        self.ora_user_anonymized_id = 'anon_user_1'
        self.score = {
            'points_earned': 10,
            'points_possible': 20,
        }

    @patch('openassessment.xblock.utils.notifications.User.objects.get')
    @patch('openassessment.xblock.utils.notifications.UsageKey.from_string')
    @patch('openassessment.xblock.utils.notifications.modulestore')
    @patch('openassessment.xblock.utils.notifications.USER_NOTIFICATION_REQUESTED.send_event')
    @patch('openassessment.data.map_anonymized_ids_to_usernames')
    # pylint: disable=too-many-positional-arguments
    def test_send_notification_success(self, mock_map_to_username, mock_send_event, mock_modulestore, mock_from_string,
                                       mock_get_user):
        """
        Test that the notification is sent when all data is valid.
        """
        mock_map_to_username.return_value = {self.ora_user_anonymized_id: 'student1'}
        mock_get_user.return_value = MagicMock(id=2)
        mock_from_string.return_value = MagicMock(course_key='course-v1:TestX+TST+TST')
        mock_modulestore.return_value.get_item.return_value = MagicMock(display_name="ORA Assignment")
        mock_modulestore.return_value.get_course.return_value = MagicMock(display_name="Test Course")

        send_grade_assigned_notification(self.usage_id, self.ora_user_anonymized_id, self.score)

        mock_send_event.assert_called_once()
        args, kwargs = mock_send_event.call_args
        notification_data = kwargs['notification_data']
        self.assertEqual(notification_data.user_ids, [2])
        self.assertEqual(notification_data.context['ora_name'], 'ORA Assignment')
        self.assertEqual(notification_data.context['course_name'], 'Test Course')
        self.assertEqual(notification_data.context['points_earned'], 10)
        self.assertEqual(notification_data.context['points_possible'], 20)
        self.assertEqual(notification_data.notification_type, "ora_grade_assigned")

    @patch('openassessment.xblock.utils.notifications.User.objects.get')
    @patch('openassessment.xblock.utils.notifications.UsageKey.from_string')
    @patch('openassessment.xblock.utils.notifications.logger.error')
    @patch('openassessment.xblock.utils.notifications.USER_NOTIFICATION_REQUESTED.send_event')
    @patch('openassessment.data.map_anonymized_ids_to_usernames')
    # pylint: disable=too-many-positional-arguments
    def test_invalid_key_error_logging(self, mock_map_to_username, mock_send_event, mock_logger_error,
                                       mock_from_string, mock_get_user):
        """
        Test error logging when InvalidKeyError is raised.
        """
        mock_map_to_username.return_value = {self.ora_user_anonymized_id: 'student1'}
        mock_get_user.return_value = MagicMock(id=2)
        mock_from_string.return_value = MagicMock(course_key='course-v1:TestX+TST+TST')
        mock_exception = InvalidKeyError('Invalid key error', 'some_serialized_data')

        # Force the exception
        with patch('openassessment.xblock.utils.notifications.UsageKey.from_string', side_effect=mock_exception):
            send_grade_assigned_notification(self.usage_id, self.ora_user_anonymized_id, self.score)

        # Assertions
        mock_logger_error.assert_called_once_with(f"Bad ORA location provided: {self.usage_id}")
        mock_send_event.assert_not_called()

    @patch('openassessment.xblock.utils.notifications.User.objects.get')
    @patch('openassessment.xblock.utils.notifications.UsageKey.from_string')
    @patch('openassessment.xblock.utils.notifications.modulestore')
    @patch('openassessment.xblock.utils.notifications.logger.error')
    @patch('openassessment.xblock.utils.notifications.USER_NOTIFICATION_REQUESTED.send_event')
    @patch('openassessment.data.map_anonymized_ids_to_usernames')
    # pylint: disable=too-many-positional-arguments
    def test_item_not_found_error_logging(self, mock_map_to_username, mock_send_event, mock_logger_error,
                                          mock_modulestore, mock_from_string, mock_get_user):
        """
        Test error logging when ItemNotFoundError is raised.
        """
        mock_map_to_username.return_value = {self.ora_user_anonymized_id: 'student1'}
        mock_get_user.return_value = MagicMock(id=2)
        mock_from_string.return_value = MagicMock(course_key='course-v1:TestX+TST+TST')
        mock_exception = ItemNotFoundError('Item not found')
        mock_modulestore.return_value.get_item.side_effect = mock_exception

        send_grade_assigned_notification(self.usage_id, self.ora_user_anonymized_id, self.score)

        # Assertions
        mock_logger_error.assert_called_once_with(f"Bad ORA location provided: {self.usage_id}")
        mock_send_event.assert_not_called()

    @patch('openassessment.xblock.utils.notifications.logger.error')
    @patch('openassessment.xblock.utils.notifications.USER_NOTIFICATION_REQUESTED.send_event')
    @patch('openassessment.data.map_anonymized_ids_to_usernames')
    @patch('openassessment.xblock.utils.notifications.User.objects.get')
    def test_user_does_not_exist_error_logging(self, mock_get_user, mock_map_to_username, mock_send_event,
                                               mock_logger_error):
        """
        Test error logging when User.DoesNotExist is raised.
        """
        mock_map_to_username.return_value = {self.ora_user_anonymized_id: 'non_existent_user'}
        mock_get_user.side_effect = User.DoesNotExist('User does not exist')

        send_grade_assigned_notification(self.usage_id, self.ora_user_anonymized_id, self.score)

        # Assertions
        mock_logger_error.assert_called_once_with('Unknown User Error: User does not exist')
        mock_send_event.assert_not_called()

    @patch('openassessment.xblock.utils.notifications.logger.error')
    @patch('openassessment.xblock.utils.notifications.USER_NOTIFICATION_REQUESTED.send_event')
    @patch('openassessment.data.map_anonymized_ids_to_usernames')
    def test_getting_user_name_error_logging(self, mock_map_to_username, mock_send_event, mock_logger_error):
        """
        Test error logging when FieldError is raised.
        """
        mock_map_to_username.side_effect = FieldError('FieldError: Cannot resolve keyword \'anonymoususerid\'')

        send_grade_assigned_notification(self.usage_id, self.ora_user_anonymized_id, self.score)

        # Assertions
        mock_logger_error.assert_called_once_with('Error while getting user name for the user id anon_user_1: '
                                                  'FieldError: Cannot resolve keyword \'anonymoususerid\'')
        mock_send_event.assert_not_called()
