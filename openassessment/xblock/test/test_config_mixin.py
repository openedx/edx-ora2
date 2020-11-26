"""
Basic tests for configuration/feature toggles of the ORA XBlock.
"""

import itertools
import mock

import ddt
from django.test import TestCase

from openassessment.xblock.config_mixin import (
    ConfigMixin,
    ALL_FILES_URLS,
    FEATURE_TOGGLES_BY_FLAG_NAME,
    MOBILE_SUPPORT,
    TEAM_SUBMISSIONS,
    USER_STATE_UPLOAD_DATA,
)


class MockBlock(ConfigMixin):
    """
    Fixture class for testing ``ConfigMixin``.
    """
    location = mock.MagicMock()


@ddt.ddt
class ConfigMixinTest(TestCase):
    """
    Tests for configuration/feature-gating of ORA XBlocks.
    """
    @ddt.data(
        *list(itertools.product([True, False], repeat=3))
    )
    @ddt.unpack
    def test_team_submission_enabled(self, waffle_switch_input, waffle_flag_input, settings_input):
        """
        Team submissions are expected to be enabled if at least one of the following conditions holds:
          1) The team_submissions waffle switch is enabled.
          2) The team_submissions course waffle flag is enabled.
          3) The settings.FEATURES['ENABLE_ORA_TEAM_SUBMISSIONS'] value is True.
        """
        self._run_feature_toggle_test(
            TEAM_SUBMISSIONS,
            waffle_switch_input,
            waffle_flag_input,
            settings_input,
            'team_submissions_enabled',
        )

    @ddt.data(
        *list(itertools.product([True, False], repeat=3))
    )
    @ddt.unpack
    def test_user_state_upload_data_enabled(self, waffle_switch_input, waffle_flag_input, settings_input):
        """
        The user state data workaround is expected to be enabled if at least one of the following conditions holds:
          1) The user_state_upload_data waffle switch is enabled.
          2) The user_state_upload_data course waffle flag is enabled.
          3) The settings.FEATURES['ENABLE_ORA_USER_STATE_UPLOAD_DATA'] value is True.
        """
        self._run_feature_toggle_test(
            USER_STATE_UPLOAD_DATA,
            waffle_switch_input,
            waffle_flag_input,
            settings_input,
            'user_state_upload_data_enabled',
        )

    @ddt.data(
        *list(itertools.product([True, False], repeat=3))
    )
    @ddt.unpack
    def test_all_files_urls_enabled(self, waffle_switch_input, waffle_flag_input, settings_input):
        """
        The "all file urls" workaround is expected to be enabled if at least one of the following conditions holds:
          1) The all_files_urls waffle switch is enabled.
          2) The all_files_urls course waffle flag is enabled.
          3) The settings.FEATURES['ENABLE_ORA_ALL_FILE_URLS'] value is True.
        """
        self._run_feature_toggle_test(
            ALL_FILES_URLS,
            waffle_switch_input,
            waffle_flag_input,
            settings_input,
            'is_fetch_all_urls_waffle_enabled',
        )

    @ddt.data(
        (True, True),
        (False, False),
        (None, False),
    )
    @ddt.unpack
    def test_mobile_support_enabled(self, settings_input, expected_output):
        """
        The mobile support is expected to be enabled only if:
          1) The settings.FEATURES['ENABLE_ORA_MOBILE_SUPPORT'] value is True.
        """
        my_block = MockBlock()
        settings_feature_key = FEATURE_TOGGLES_BY_FLAG_NAME[MOBILE_SUPPORT]
        with self.settings(FEATURES={settings_feature_key: settings_input}):
            self.assertEqual(expected_output, my_block.is_mobile_support_enabled)

    def _run_feature_toggle_test(
        self, flag_name, waffle_switch_input, waffle_flag_input, settings_input, feature_property
    ):
        """
        Any feature name is expected to be enabled if at least one of the following conditions holds:
          1) It's associated waffle switch is enabled.
          2) It's associated course waffle flag is enabled.
          3) The settings.FEATURES keyed by ``flag_name`` is True.
        """

        expected_output = True
        if not any((waffle_switch_input, waffle_flag_input, settings_input)):
            expected_output = False

        my_block = MockBlock()
        settings_feature_key = FEATURE_TOGGLES_BY_FLAG_NAME[flag_name]

        with mock.patch('openassessment.xblock.config_mixin.WaffleSwitch', autospec=True) as MockWaffleSwitch:
            MockWaffleSwitch.return_value.is_enabled.return_value = waffle_switch_input
            with mock.patch(
                'openassessment.xblock.config_mixin.import_course_waffle_flag', autospec=True
            ) as mock_course_waffle_flag:
                MockCourseWaffleFlag = mock_course_waffle_flag.return_value
                MockCourseWaffleFlag.return_value.is_enabled.return_value = waffle_flag_input
                with self.settings(FEATURES={settings_feature_key: settings_input}):
                    self.assertEqual(expected_output, getattr(my_block, feature_property, None))

        mock_flag_instance = MockCourseWaffleFlag.return_value
        mock_flag_instance.is_enabled.assert_called_once_with(my_block.location.course_key)

        if not waffle_flag_input:
            mock_switch_instance = MockWaffleSwitch.return_value
            mock_switch_instance.is_enabled.assert_called_once_with()
