"""
Basic tests for teams functionality of the ORA XBlock.
"""

from __future__ import absolute_import

from unittest import TestCase

import ddt
import mock

from openassessment.xblock.team_mixin import TeamMixin
from django.core.exceptions import ObjectDoesNotExist
from xblock.exceptions import NoSuchServiceError


class MockTeamsService(object):
    """
    Fixture class for testing ``TeamMixin``.
    """
    get_team_detail_url = mock.MagicMock(return_value='this-is-a-url')

    def __init__(self, has_team):
        self.has_team = has_team
        self.team = mock.MagicMock()
        # This is required because 'name' is a reserved property for mocks
        self.team.configure_mock(name='TeamName', team_id='TeamID')
        self.team.users.all.return_value = [
            mock.MagicMock(username='UserA'),
            mock.MagicMock(username='UserB'),
            mock.MagicMock(username='UserC'),
        ]

    def get_team(self, user, course_id, teamset_id):  # pylint: disable=unused-argument
        return self.team if self.has_team else None


class MockBlock(TeamMixin):
    """
    Fixture class for testing ``TeamMixin``.
    """
    location = mock.MagicMock()
    selected_teamset_id = "teamset-id-0001"
    get_anonymous_user_id_from_xmodule_runtime = mock.MagicMock()
    course_id = mock.MagicMock()
    is_course_staff = False
    in_studio_preview = False

    def __init__(self, has_service=True, has_user=True, has_team=True):
        self.has_service = has_service
        self.has_user = has_user
        if has_service:
            self.service = MockTeamsService(has_team)

    def get_real_user(self, anonymous_user_id):  # pylint: disable=unused-argument
        return mock.MagicMock() if self.has_user else None

    @property
    def teams_service(self):
        if self.has_service:
            return self.service
        else:
            raise NoSuchServiceError()


@ddt.ddt
class TeamMixinTest(TestCase):
    """
    Tests for team-based functionality for the openassessment block
    """

    def test_no_user_found(self):
        block = MockBlock(has_user=False)
        with self.assertRaises(ObjectDoesNotExist):
            _ = block.team

    def test_no_service(self):
        block = MockBlock(has_service=False)
        with self.assertRaises(NoSuchServiceError):
            _ = block.team

    def test_no_user(self):
        block = MockBlock(has_team=False)
        self.assertIsNone(block.team)

    def test_get_team_info_student(self):
        block = MockBlock()
        self.assertDictEqual(
            block.get_team_info(),
            {
                'team_id': "TeamID",
                'team_name': 'TeamName',
                'team_usernames': [
                    'UserA',
                    'UserB',
                    'UserC',
                ],
                'team_url': 'this-is-a-url',
            }
        )

    @ddt.unpack
    @ddt.data(
        (False, False, False, False),  # Student in LMS with no team
        (True, False, False, True),  # Student in LMS with a team
        (False, False, True, True),  # Studio preview
        (False, True, False, True),  # Course staff in LMS
        (False, True, True, True),   # Course Staff in studio preview
    )
    def test_valid_access_to_team_assessment(self, has_team, is_course_staff, in_studio_preview, expected_valid):
        block = MockBlock(has_team=has_team)
        block.is_course_staff = is_course_staff
        block.in_studio_preview = in_studio_preview
        valid_access_to_team_assessment = block.valid_access_to_team_assessment()
        self.assertEqual(expected_valid, valid_access_to_team_assessment)
