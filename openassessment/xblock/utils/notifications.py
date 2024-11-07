"""
This module contains utility functions for sending notifications.
"""
import logging

from opaque_keys.edx.keys import UsageKey, CourseKey
from opaque_keys import InvalidKeyError

from django.conf import settings
from django.core.exceptions import FieldError
from openedx_events.learning.signals import COURSE_NOTIFICATION_REQUESTED, USER_NOTIFICATION_REQUESTED
from openedx_events.learning.data import CourseNotificationData, UserNotificationData
from django.contrib.auth import get_user_model
from openassessment.runtime_imports.functions import modulestore
from openassessment.workflow.errors import ItemNotFoundError

logger = logging.getLogger(__name__)
User = get_user_model()


def send_staff_notification(course_id, problem_id, ora_name):
    """
    Send a staff notification for a course
    """
    try:
        audience_filters = {
            'course_roles': ['staff', 'instructor']
        }
        course = modulestore().get_course(course_id)
        notification_data = CourseNotificationData(
            course_key=course_id,
            content_context={
                'ora_name': ora_name,
                'course_name': course.display_name,
            },
            notification_type='ora_staff_notification',
            content_url=f"{getattr(settings, 'ORA_GRADING_MICROFRONTEND_URL', '')}/{problem_id}",
            app_name="grading",
            audience_filters=audience_filters,
        )
        COURSE_NOTIFICATION_REQUESTED.send_event(course_notification_data=notification_data)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"Error while sending ora staff notification: {e}")


def send_grade_assigned_notification(usage_id, ora_user_anonymized_id, score):
    """
        Send a user notification for a course for a new grade being assigned
    """
    from openassessment.data import map_anonymized_ids_to_usernames as map_to_username

    user_name_list = []
    try:
        # Get ORA user name
        user_name_list = map_to_username([ora_user_anonymized_id])
    except FieldError as exc:
        logger.error(f'Error while getting user name for the user id {ora_user_anonymized_id}: {exc}')

    try:
        if (not user_name_list) or (not user_name_list[ora_user_anonymized_id]):
            return
        # Get ORA user
        ora_user = User.objects.get(username=user_name_list[ora_user_anonymized_id])
        # Get ORA block
        ora_usage_key = UsageKey.from_string(usage_id)
        ora_metadata = modulestore().get_item(ora_usage_key)
        # Get course metadata
        course_id = CourseKey.from_string(str(ora_usage_key.course_key))
        course_metadata = modulestore().get_course(course_id)
        notification_data = UserNotificationData(
            user_ids=[ora_user.id],
            context={
                'ora_name': ora_metadata.display_name,
                'course_name': course_metadata.display_name,
                'points_earned': score['points_earned'],
                'points_possible': score['points_possible'],
            },
            notification_type="ora_grade_assigned",
            content_url=f"{getattr(settings, 'LMS_ROOT_URL', '')}/courses/{str(course_id)}"
                        f"/jump_to/{str(ora_usage_key)}",
            app_name="grading",
            course_key=course_id,
        )
        USER_NOTIFICATION_REQUESTED.send_event(notification_data=notification_data)

    # Catch bad ORA location
    except (InvalidKeyError, ItemNotFoundError):
        logger.error(f"Bad ORA location provided: {usage_id}")

    # Error with getting User
    except User.DoesNotExist as exc:
        logger.error(f'Unknown User Error: {exc}')
