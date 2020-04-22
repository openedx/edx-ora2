"""
Tests for team assessments.
"""
from __future__ import absolute_import

import mock
from freezegun import freeze_time

from django.utils.timezone import now

from openassessment.assessment.api import teams as teams_api
from openassessment.assessment.models.staff import TeamStaffWorkflow
from openassessment.tests.factories import TeamStaffWorkflowFactory, AssessmentFactory, UserFactory
from openassessment.test_utils import CacheResetTest

from submissions import (
    api as submissions_api,
    team_api as team_submissions_api
)

from .constants import OPTIONS_SELECTED_DICT, RUBRIC

STAFF_TYPE = "ST"


class TestTeamApi(CacheResetTest):
    """ Tests for the Team Assessment API """

    def _create_users(self):
        """ Create test users on a team """
        submitting_user = UserFactory.create()
        team_member_1 = UserFactory.create()
        team_member_2 = UserFactory.create()

        self.team_member_ids = [submitting_user.id, team_member_1.id, team_member_2.id]
        return self.team_member_ids

    def test_submitter_is_finished(self):
        team_submission_uuid = 'foo'
        team_requirements = {}

        self.assertTrue(teams_api.submitter_is_finished(
            team_submission_uuid,
            team_requirements
        ))

    @mock.patch('submissions.team_api.get_team_submission')
    def test_on_init(self, mock_get_submission):
        # Given a team submission
        team_submission_uuid = 'foo'
        mock_get_submission.return_value = {
            'team_submission_uuid': team_submission_uuid,
            'course_id': 'fake_course',
            'item_id': 'fake_item'
        }

        # When I initialize an assessment
        teams_api.on_init(team_submission_uuid)

        # Then I generate a new TeamStaffWorkflow for the submission
        new_workflow = TeamStaffWorkflow.objects.get(team_submission_uuid=team_submission_uuid)
        assert new_workflow is not None

    @freeze_time("2020-04-10 12:00:01", tz_offset=-4)
    def test_cancel(self):
        # Given a team submission
        workflow = TeamStaffWorkflowFactory.create()

        # When I cancel through the API
        teams_api.on_cancel(workflow.team_submission_uuid)

        # The workflow, gets cancelled
        cancelled_workflow = TeamStaffWorkflow.objects.get(team_submission_uuid=workflow.team_submission_uuid)
        self.assertEqual(cancelled_workflow.cancelled_at, now())

    def test_get_latest_assessment_none(self):
        # Given no assessments for a team, when I try to get latest
        team_submission = self._create_test_submission_for_team()
        assessment = teams_api.get_latest_staff_assessment(team_submission['team_submission_uuid'])

        # Then None is returned
        self.assertIsNone(assessment)

    def test_get_latest_assessment(self):
        # Given an assessment for a team submission
        team_submission = self._create_test_submission_for_team()
        assessments = self._create_test_assessments_for_team(
            team_submission_uuid=team_submission['team_submission_uuid']
        )

        # When I ask the API for the latest
        returned_assessment = teams_api.get_latest_staff_assessment(team_submission['team_submission_uuid'])

        # Then the correct assessment is returned
        self.assertIsNotNone(returned_assessment)
        self.assertEqual(returned_assessment['id'], assessments[-1]['id'])

    def test_create_assessment(self):
        # Given a team submission and workflow
        team_submission = self._create_test_submission_for_team()

        # When I create an assessment
        assessments = teams_api.create_assessment(
            team_submission['team_submission_uuid'],
            "Snape",
            OPTIONS_SELECTED_DICT["few"]["options"], dict(), "",
            RUBRIC
        )

        # Assessments are created for each memeber of the team
        self.assertEqual(
            [assessment['submission_uuid'] for assessment in assessments],
            [str(uuid) for uuid in team_submission['submission_uuids']]
        )

    def _create_test_assessments_for_team(self, team_submission_uuid=None, team_member_ids=None):
        """
        Helper to create team assessments.
        Implicitly creates a submission and workflow to link the assessment to.

        Returns:
            Assessments
        """
        # Create submission and workflow
        if team_submission_uuid is None:
            team_submission_uuid = self._create_test_submission_for_team(team_member_ids)['team_submission_uuid']

        # Create assessment
        assessments = teams_api.create_assessment(
            team_submission_uuid,
            "Snape",
            OPTIONS_SELECTED_DICT["few"]["options"], dict(), "",
            RUBRIC
        )
        return assessments

    def _create_test_submission_for_team(self, team_member_ids=None):
        """
        Helper to create a team submission.
        Implicitly creates a TeamStaffWorkflow linked to the submission.

        Returns:
            TeamSubmission
        """
        # Create users if not supplied
        if team_member_ids is None:
            team_member_ids = self._create_users()

        # Create a team submission
        team_submission = team_submissions_api.create_submission_for_team(
            'mock-course',
            'mock-item',
            'mock-team-id',
            team_member_ids[0],
            team_member_ids,
            '42'
        )

        # Create a team staff workflow linked to the team submission
        self._create_test_workflow(team_submission['team_submission_uuid'])

        return team_submission

    def _create_test_workflow(self, team_submission_uuid):
        """
        Creates a test team workflow and links to a team submission

        Returns:
            Created workflow
        """
        workflow = TeamStaffWorkflowFactory.create()
        workflow.team_submission_uuid = team_submission_uuid
        workflow.save()

        return workflow
