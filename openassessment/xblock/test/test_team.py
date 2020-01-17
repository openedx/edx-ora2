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

TEAMSET_ID = 'teamset-1-id'
TEAMSET_NAME = 'teamset-1-name'


class MockTeamsConfigurationService(object):
    """
    Fixture class for testing ``TeamMixin``.
    """
    def __init__(self):
        self.teamset = mock.MagicMock()
        self.teamset.configure_mock(name=TEAMSET_NAME)

    def get_teams_configuration(self, _):
        return mock.MagicMock(
            teamsets_by_id={TEAMSET_ID: self.teamset}
        )


class MockTeamsService(object):
    """
    Fixture class for testing ``TeamMixin``.
    """
    get_team_detail_url = mock.MagicMock(return_value='this-is-a-url')

    def __init__(self, has_team):
        self.has_team = has_team
        self.team = mock.MagicMock()
        # This is required because 'name' is a reserved property for mocks
        self.team.configure_mock(name='TeamName')
        self.team.users.all.return_value = [
            mock.MagicMock(username='UserA'),
            mock.MagicMock(username='UserB'),
            mock.MagicMock(username='UserC'),
        ]

    def get_team(self, user, course_id, teamset_id):  # pylint: disable=unused-argument
        return self.team if self.has_team else None


class MockRuntime(object):
    """
    Fixture class for testing ``TeamMixin``.
    """
    def __init__(self, has_teams_service, has_team, has_teams_configuration_service):
        self.has_teams_service = has_teams_service
        self.teams_service = MockTeamsService(has_team)
        self.has_teams_configuration_service = has_teams_configuration_service
        self.teams_configuration_service = MockTeamsConfigurationService()

    def service(self, _, service_name):
        """
        Mocked version of `runtime.service(self, service_name)`
        """
        if service_name == 'teams':
            if self.has_teams_service:
                return self.teams_service
        elif service_name == 'teams_configuration':
            if self.has_teams_configuration_service:
                return self.teams_configuration_service
        raise NoSuchServiceError()


class MockBlock(TeamMixin):
    """
    Fixture class for testing ``TeamMixin``.
    """
    location = mock.MagicMock()
    selected_teamset_id = TEAMSET_ID
    get_anonymous_user_id_from_xmodule_runtime = mock.MagicMock()
    course_id = mock.MagicMock()
    is_course_staff = False
    in_studio_preview = False

    def __init__(
        self, has_teams_service=True, has_teams_configuration_service=True,
        has_user=True, has_team=True,
    ):
        self.runtime = MockRuntime(has_teams_service, has_team, has_teams_configuration_service)
        self.has_user = has_user

    def get_real_user(self, anonymous_user_id):  # pylint: disable=unused-argument
        return mock.MagicMock() if self.has_user else None


@ddt.ddt
class TeamMixinTest(TestCase):
    """
    Tests for team-based functionality for the openassessment block
    """

    def test_team_no_user_found(self):
        block = MockBlock(has_user=False)
        with self.assertRaises(ObjectDoesNotExist):
            _ = block.team

    def test_team_no_teams_service(self):
        block = MockBlock(has_teams_service=False)
        with self.assertRaises(NoSuchServiceError):
            _ = block.team

    def test_team_no_user(self):
        block = MockBlock(has_team=False)
        self.assertIsNone(block.team)

    def test_get_team_info_student(self):
        block = MockBlock()
        self.assertDictEqual(
            block.get_team_info(),
            {
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

    def test_teamset_config_no_teams_configuration_service(self):
        block = MockBlock(has_teams_configuration_service=False)
        with self.assertRaises(NoSuchServiceError):
            _ = block.teamset_config

    def test_teamset_config(self):
        block = MockBlock()
        self.assertIsNotNone(block.teamset_config)
        self.assertEqual(block.teamset_config.name, TEAMSET_NAME)

    def test_teamset_config_no_teamset(self):
        block = MockBlock()
        block.selected_teamset_id = 'some-other-teamset'
        self.assertIsNone(block.teamset_config)
