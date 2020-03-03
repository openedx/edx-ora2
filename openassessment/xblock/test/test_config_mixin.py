"""
Basic tests for configuration/feature toggles of the ORA XBlock.
"""

from __future__ import absolute_import

import itertools
import mock

import ddt
from django.test import TestCase

from openassessment.xblock.config_mixin import (
    ConfigMixin,
    ALL_FILES_URLS,
    FEATURE_TOGGLES_BY_FLAG_NAME,
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
    @mock.patch('openassessment.xblock.config_mixin.import_waffle_switch', autospec=True)
    @mock.patch('openassessment.xblock.config_mixin.import_course_waffle_flag', autospec=True)
    def test_team_submission_enabled(
            self, waffle_switch_input, waffle_flag_input, settings_input, mock_waffle_flag, mock_waffle_switch
    ):
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
            mock_waffle_flag,
            mock_waffle_switch,
            'team_submissions_enabled',
        )

    @ddt.data(
        *list(itertools.product([True, False], repeat=3))
    )
    @ddt.unpack
    @mock.patch('openassessment.xblock.config_mixin.import_waffle_switch', autospec=True)
    @mock.patch('openassessment.xblock.config_mixin.import_course_waffle_flag', autospec=True)
    def test_user_state_upload_data_enabled(
            self, waffle_switch_input, waffle_flag_input, settings_input, mock_waffle_flag, mock_waffle_switch
    ):
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
            mock_waffle_flag,
            mock_waffle_switch,
            'user_state_upload_data_enabled',
        )

    @ddt.data(
        *list(itertools.product([True, False], repeat=3))
    )
    @ddt.unpack
    @mock.patch('openassessment.xblock.config_mixin.import_waffle_switch', autospec=True)
    @mock.patch('openassessment.xblock.config_mixin.import_course_waffle_flag', autospec=True)
    def test_all_files_urls_enabled(
            self, waffle_switch_input, waffle_flag_input, settings_input, mock_waffle_flag, mock_waffle_switch
    ):
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
            mock_waffle_flag,
            mock_waffle_switch,
            'is_fetch_all_urls_waffle_enabled',
        )

    def _run_feature_toggle_test(
            self, flag_name, waffle_switch_input, waffle_flag_input, settings_input,
            mock_waffle_flag, mock_waffle_switch, feature_property
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

        # pylint: disable=invalid-name
        MockWaffleSwitch, MockCourseWaffleFlag = self._setup_waffle_switch_and_flag(
            mock_waffle_switch, waffle_switch_input, mock_waffle_flag, waffle_flag_input
        )

        settings_feature_key = FEATURE_TOGGLES_BY_FLAG_NAME[flag_name]
        with self.settings(FEATURES={settings_feature_key: settings_input}):
            self.assertEqual(expected_output, getattr(my_block, feature_property, None))

        mock_flag_instance = MockCourseWaffleFlag.return_value
        mock_flag_instance.is_enabled.assert_called_once_with(my_block.location.course_key)

        if not waffle_flag_input:
            mock_switch_instance = MockWaffleSwitch.return_value
            mock_switch_instance.is_enabled.assert_called_once_with()

    def _setup_waffle_switch_and_flag(
            self, mock_waffle_switch, switch_return_value, mock_waffle_flag, flag_return_value
    ):
        """
        Configures and returns mocked WaffleSwitch and CourseWaffleFlag objects.
        """
        # pylint: disable=invalid-name
        MockWaffleSwitch = mock_waffle_switch.return_value
        MockWaffleSwitch.return_value.is_enabled.return_value = switch_return_value
        MockCourseWaffleFlag = mock_waffle_flag.return_value
        MockCourseWaffleFlag.return_value.is_enabled.return_value = flag_return_value
        return MockWaffleSwitch, MockCourseWaffleFlag
