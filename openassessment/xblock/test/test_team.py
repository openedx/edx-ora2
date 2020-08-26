"""
Basic tests for teams functionality of the ORA XBlock.
"""

from unittest import TestCase

import ddt
import mock

from mock import patch
from django.core.exceptions import ObjectDoesNotExist
from xblock.exceptions import NoSuchServiceError
from openassessment.xblock.team_mixin import TeamMixin

TEAMSET_ID = 'teamset-1-id'
TEAMSET_NAME = 'teamset-1-name'

MOCK_TEAM_MEMBERS = ['UserA', 'UserB', 'UserC']
MOCK_TEAM_NAME = 'TeamName'
MOCK_TEAM_NAME_2 = 'TeamName2'
MOCK_TEAM_ID = 'TeamID'
MOCK_TEAM_ID_2 = 'TeamID2'


class MockTeamsConfigurationService:
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


class MockTeamsService:
    """
    Fixture class for testing ``TeamMixin``.
    """
    get_team_detail_url = mock.MagicMock(return_value='this-is-a-url')

    def __init__(self, has_team):
        self.has_team = has_team
        self.team = mock.MagicMock(team_id='the-team-id')
        # This is required because 'name' is a reserved property for mocks
        self.team.configure_mock(name=MOCK_TEAM_NAME, team_id=MOCK_TEAM_ID)
        self.team.users.all.return_value = [
            mock.MagicMock(username=MOCK_TEAM_MEMBERS[0]),
            mock.MagicMock(username=MOCK_TEAM_MEMBERS[1]),
            mock.MagicMock(username=MOCK_TEAM_MEMBERS[2]),
        ]

    def get_team(self, user, course_id, teamset_id):  # pylint: disable=unused-argument
        return self.team if self.has_team else None

    def get_team_by_team_id(self, team_id):  # pylint: disable=unused-argument
        team = mock.MagicMock(team_id='the-team-id')
        # This is required because 'name' is a reserved property for mocks
        team.configure_mock(name=MOCK_TEAM_NAME_2, team_id=MOCK_TEAM_ID_2)
        team.users.all.return_value = [
            mock.MagicMock(username=MOCK_TEAM_MEMBERS[0]),
            mock.MagicMock(username=MOCK_TEAM_MEMBERS[1]),
            mock.MagicMock(username=MOCK_TEAM_MEMBERS[2]),
        ]
        return team if self.has_team else None


class MockRuntime:
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

    def get_student_item_dict(self):
        return mock.MagicMock()


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

    @patch('openassessment.xblock.team_mixin.get_team_submission_for_student')
    def test_get_team_info_student_has_previous_team(self, mock_student_submission):
        block = MockBlock()
        mock_student_submission.return_value = {'team_id': 'previous team'}
        self.assertDictEqual(
            block.get_team_info(),
            {
                'team_id': MOCK_TEAM_ID,
                'team_name': MOCK_TEAM_NAME,
                'previous_team_name': MOCK_TEAM_NAME_2,
                'team_usernames': [
                    'UserA',
                    'UserB',
                    'UserC',
                ],
                'team_url': 'this-is-a-url',
            }
        )

    @patch('openassessment.xblock.team_mixin.get_team_submission_for_student')
    def test_get_team_info_student_no_previous_team(self, mock_student_submission):
        block = MockBlock()
        mock_student_submission.return_value = {'team_id': MOCK_TEAM_ID}
        self.assertDictEqual(
            block.get_team_info(),
            {
                'team_id': MOCK_TEAM_ID,
                'team_name': MOCK_TEAM_NAME,
                'previous_team_name': None,
                'team_usernames': [
                    'UserA',
                    'UserB',
                    'UserC',
                ],
                'team_url': 'this-is-a-url',
            }
        )

    def test_get_team_info_no_team(self):
        block = MockBlock(has_team=False)
        self.assertEqual({}, block.get_team_info())

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
