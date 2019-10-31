"""
Mixin for determining waffle state relevant to an ORA block.
"""
from __future__ import absolute_import


WAFFLE_NAMESPACE = 'openresponseassessment'

TEAM_SUBMISSIONS = 'team_submissions'


def import_waffle_switch():
    """
    Helper method that imports WaffleSwitch from edx-platform at runtime.
    https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/waffle_utils/__init__.py#L187
    """
    # pylint: disable=import-error
    from openedx.core.djangoapps.waffle_utils import WaffleSwitch
    return WaffleSwitch


def import_course_waffle_flag():
    """
    Helper method that imports CourseWaffleFlag from edx-platform at runtime.
    https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/waffle_utils/__init__.py#L345
    """
    # pylint: disable=import-error
    from openedx.core.djangoapps.waffle_utils import CourseWaffleFlag
    return CourseWaffleFlag


class WaffleMixin(object):
    """
    Mixin class for determining waffle state relevant to an ORA block.
    """
    @staticmethod
    def _waffle_switch(switch_name):
        """
        Returns a ``WaffleSwitch`` object in WAFFLE_NAMESPACE
        with the given ``switch_name``.
        """
        WaffleSwitch = import_waffle_switch()  # pylint: disable=invalid-name
        return WaffleSwitch(WAFFLE_NAMESPACE, switch_name)  # pylint: disable=feature-toggle-needs-doc

    @staticmethod
    def _course_waffle_flag(flag_name):
        """
        Returns a ``CourseWaffleFlag`` object in WAFFLE_NAMESPACE
        with the given ``flag_name``.
        """
        CourseWaffleFlag = import_course_waffle_flag()  # pylint: disable=invalid-name
        return CourseWaffleFlag(WAFFLE_NAMESPACE, flag_name)  # pylint: disable=feature-toggle-needs-doc

    def team_submissions_enabled(self):
        """
        Returns True if a WaffleSwitch or CourseWaffleFlag
        for team submissions is enabled for this block,
        False otherwise.
        """
        if self._waffle_switch(TEAM_SUBMISSIONS).is_enabled():
            return True

        if self._course_waffle_flag(TEAM_SUBMISSIONS).is_enabled(self.location.course_key):
            return True

        return False
