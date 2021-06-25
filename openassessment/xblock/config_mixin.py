"""
Mixin for determining configuration and feature-toggle state relevant to an ORA block.
"""


from edx_django_utils.monitoring import set_custom_attribute
from edx_toggles.toggles import WaffleSwitch

from django.conf import settings
from django.utils.functional import cached_property

WAFFLE_NAMESPACE = 'openresponseassessment'

ALL_FILES_URLS = 'all_files_urls'
TEAM_SUBMISSIONS = 'team_submissions'
USER_STATE_UPLOAD_DATA = 'user_state_upload_data'
RUBRIC_REUSE = 'rubric_reuse'

FEATURE_TOGGLES_BY_FLAG_NAME = {
    ALL_FILES_URLS: 'ENABLE_ORA_ALL_FILE_URLS',
    TEAM_SUBMISSIONS: 'ENABLE_ORA_TEAM_SUBMISSIONS',
    USER_STATE_UPLOAD_DATA: 'ENABLE_ORA_USER_STATE_UPLOAD_DATA',
    RUBRIC_REUSE: 'ENABLE_ORA_RUBRIC_REUSE',
}


def import_waffle_switch():
    """
    Helper method that imports WaffleSwitch from edx-platform at runtime.
    WARNING: This method is now deprecated and should not be relied upon.
    """
    set_custom_attribute("deprecated_edx_ora2", "import_waffle_switch")
    return WaffleSwitch


def import_course_waffle_flag():
    """
    Helper method that imports CourseWaffleFlag from edx-platform at runtime.
    https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/waffle_utils/__init__.py#L345
    """
    # pylint: disable=import-error
    from openedx.core.djangoapps.waffle_utils import CourseWaffleFlag
    return CourseWaffleFlag


def import_waffle_flag():
    """
    Helper method that imports WaffleFlag from edx_toggles at runtime.
    """
    # pylint: disable=import-error
    from edx_toggles.toggles import WaffleFlag
    return WaffleFlag


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
        # pylint: disable=toggle-missing-annotation
        return WaffleSwitch(f"{WAFFLE_NAMESPACE}.{switch_name}", module_name=__name__)

    @staticmethod
    def _course_waffle_flag(flag_name):
        """
        Returns a ``CourseWaffleFlag`` object in WAFFLE_NAMESPACE
        with the given ``flag_name``.
        """
        CourseWaffleFlag = import_course_waffle_flag()  # pylint: disable=invalid-name
        # pylint: disable=toggle-missing-annotation
        return CourseWaffleFlag(WAFFLE_NAMESPACE, flag_name, module_name=__name__)

    @staticmethod
    def _waffle_flag(flag_name):
        """
        Return a ``WaffleFlag`` object in WAFFLE_NAMESPACE
        with the given ``flag_name``.
        """
        WaffleFlag = import_waffle_flag()  # pylint: disable=invalid-name
        # pylint: disable=toggle-missing-annotation
        return WaffleFlag(f"{WAFFLE_NAMESPACE}.{flag_name}", module_name=__name__)

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

        if self._waffle_flag(flag).is_enabled():
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

    @cached_property
    def is_mobile_support_enabled(self):
        """
        Returns a boolean indicating if the mobile support feature flag is enabled or not.
        """
        # .. toggle_name: FEATURES['ENABLE_ORA_MOBILE_SUPPORT']
        # .. toggle_implementation: SettingToggle
        # .. toggle_default: False
        # .. toggle_description: Set to True to enable the ORA2 Xblock to be rendered
        #     in mobile apps.
        # .. toggle_use_cases: open_edx
        # .. toggle_creation_date: 2020-10-14
        # .. toggle_tickets: https://github.com/edx/edx-ora2/pull/1445
        return settings.FEATURES.get('ENABLE_ORA_MOBILE_SUPPORT', False)

    @cached_property
    def is_rubric_reuse_enabled(self):
        """
        Return a boolean indicating the reuse of rubric feature is enabled or not.
        """
        # pylint: disable=toggle-missing-target-removal-date
        # .. toggle_name: FEATURES['ENABLE_ORA_RUBRIC_REUSE']
        # .. toggle_implementation: WaffleFlag
        # .. toggle_default: False
        # .. toggle_description: Set to True to enable the reuse of rubric feature
        # .. toggle_use_cases: temporary
        # .. toggle_creation_date: 2021-05-18
        # .. toggle_tickets:  https://openedx.atlassian.net/browse/EDUCATOR-5751
        return self.is_feature_enabled(RUBRIC_REUSE)
