"""
Mixin for determining configuration and feature-toggle state relevant to an ORA block.
"""


from django.conf import settings
from django.utils.functional import cached_property


WAFFLE_NAMESPACE = 'openresponseassessment'

ALL_FILES_URLS = "all_files_urls"
TEAM_SUBMISSIONS = 'team_submissions'
USER_STATE_UPLOAD_DATA = "user_state_upload_data"

FEATURE_TOGGLES_BY_FLAG_NAME = {
    TEAM_SUBMISSIONS: 'ENABLE_ORA_TEAM_SUBMISSIONS',
    ALL_FILES_URLS: 'ENABLE_ORA_ALL_FILE_URLS',
    USER_STATE_UPLOAD_DATA: 'ENABLE_ORA_USER_STATE_UPLOAD_DATA'
}


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


class ConfigMixin:
    """
    Mixin class for determining configuration and feature-toggle state relevant to an ORA block.
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

    @staticmethod
    def _settings_toggle_enabled(toggle_name):
        """
        Returns True iff ``toggle_name`` is defined and set to ``True``
        in Django settings ``FEATURES`` dict.
        """
        if not toggle_name:
            return False

        toggle_state = settings.FEATURES.get(toggle_name)
        # If the feature toggle is not defined in settings, this will return False
        return toggle_state is True

    def is_feature_enabled(self, flag):
        """
        Returns True if a CourseWaffleFlag, WaffleSwitch, or Django settings ``FEATURE``
        is enabled for this block, False otherwise.
        """
        if hasattr(self, 'location') and self._course_waffle_flag(flag).is_enabled(self.location.course_key):
            return True

        if self._waffle_switch(flag).is_enabled():
            return True

        if self._settings_toggle_enabled(FEATURE_TOGGLES_BY_FLAG_NAME.get(flag)):
            return True

        return False

    @cached_property
    def team_submissions_enabled(self):
        """
        Returns a boolean specifying if the team submission is enabled.
        """
        return self.is_feature_enabled(TEAM_SUBMISSIONS)

    @cached_property
    def user_state_upload_data_enabled(self):
        """
        Returns a boolean indicating the user state upload data flag is enabled or not.
        """
        return self.is_feature_enabled(USER_STATE_UPLOAD_DATA)

    @cached_property
    def is_fetch_all_urls_waffle_enabled(self):
        """
        Returns a boolean indicating the all files urls feature flag is enabled or not.
        """
        return self.is_feature_enabled(ALL_FILES_URLS)
