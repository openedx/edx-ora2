"""
Tests for team assessments.
"""
from __future__ import absolute_import

import mock
from freezegun import freeze_time

from django.utils.timezone import now

from openassessment.assessment.api import teams as teams_api
from openassessment.assessment.models.staff import TeamStaffWorkflow
from openassessment.tests.factories import TeamStaffWorkflowFactory
from openassessment.test_utils import CacheResetTest

from submissions import (
    api as submissions_api,
    team_api as team_submissions_api
)


class TestTeamApi(CacheResetTest):
    """ Tests for the Team Assessment API """

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
