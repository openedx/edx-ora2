"""
Basic tests for waffle configuration of the ORA XBlock.
"""

from __future__ import absolute_import

from unittest import TestCase

import ddt
import mock

from openassessment.xblock.waffle_mixin import WaffleMixin


class MockBlock(WaffleMixin):
    """
    Fixture class for testing ``WaffleMixin``.
    """
    location = mock.MagicMock()


@ddt.ddt
class StudioViewTest(TestCase):
    """
    Tests for waffle feature-gating of ORA XBlocks.
    """
    @ddt.data(
        (True, True, True),
        (True, False, True),
        (False, True, True),
        (False, False, False),
    )
    @ddt.unpack
    @mock.patch('openassessment.xblock.waffle_mixin.import_waffle_switch')
    @mock.patch('openassessment.xblock.waffle_mixin.import_course_waffle_flag')
    def test_team_submission_enabled(
            self, switch_enabled, flag_enabled, expected_teams_enabled, mock_waffle_flag, mock_waffle_switch
    ):
        # pylint: disable=invalid-name
        MockWaffleSwitch = mock_waffle_flag.return_value
        MockWaffleSwitch.return_value.is_enabled.return_value = switch_enabled
        MockCourseWaffleFlag = mock_waffle_switch.return_value
        MockCourseWaffleFlag.return_value.is_enabled.return_value = flag_enabled

        my_block = MockBlock()
        self.assertEqual(expected_teams_enabled, my_block.team_submissions_enabled)
