"""
This module contains utility functions for sending notifications.
"""
import logging

from django.conf import settings
from openedx_events.learning.signals import COURSE_NOTIFICATION_REQUESTED
from openedx_events.learning.data import CourseNotificationData
from openassessment.runtime_imports.functions import modulestore

logger = logging.getLogger(__name__)


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
    except Exception as e:
        logger.error(f"Error while sending ora staff notification: {e}")
