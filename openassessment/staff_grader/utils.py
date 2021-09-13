"""
Utilities (largely reproduced from LMS) for supporting Enhanced Staff Grader (ESG)

Note: ESG APIs operate outside of the context of a traditional XBlock so we don't have access to
the runtime services we normally would. This requires we reproduce their functionalities here.
"""
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from openassessment.data import _use_read_replica


def get_anonymous_id(user_id, course_id):
    """
    Get an anonymous user ID for the user/course

    Returns: String or None
    """
    try:
        user_anon_id = _use_read_replica(
            User.objects.filter(
                anonymoususerid__user_id=user_id,
                anonymoususerid__course_id=course_id
            ).values(
                "anonymoususerid__anonymous_user_id"
            )
        ).get()
        return user_anon_id["anonymoususerid__anonymous_user_id"]
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return None


def has_access(user, course_id, access_level="staff"):
    """
    Determine whether the user has access to the given course.
    i.e. whether they have "staff"-level access
    """
    if user.is_anonymous:
        return False

    access_roles = get_roles(user.id, course_id)

    return access_level in access_roles


def get_roles(user_id, course_id):
    """
    Get access roles for the user in context of the course
    """
    access_roles = _use_read_replica(
        User.objects.filter(
            courseaccessrole__user_idc=user_id,
            courseaccessrole__course_id=course_id
        ).values(
            "courseaccessrole__role"
        )
    )

    return [role["courseaccessrole__role"] for role in access_roles]
