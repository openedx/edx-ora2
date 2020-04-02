""" Test Cases for Team Workflow API """
from openassessment.test_utils import CacheResetTest
from openassessment.workflow import team_api


class TestTeamAssessmentWorkflowApi(CacheResetTest):
    """ Test team assessment workflow API """

    def test_create_workflow(self):
        team_submission_uuid = 'foo'

    def test_create_workflow(self):
        # Given a test UUID
        # When I create a workflow
        team_workflow = team_api.create_workflow(self.team_submission_uuid)

        # This is stubbed for now
        assert team_workflow is not None

    def test_get_workflow(self):
        # Given a workflow
        self._create_test_workflow(self.team_submission_uuid)

        # When I get the workflow
        team_workflow = team_api.get_workflow_for_submission(self.team_submission_uuid)

        # It is updated and returns a correctly serialized version
        assert team_workflow['team_submission_uuid'] == self.team_submission_uuid
        assert 'staff' in team_workflow['status_details']

    def test_cancel_workflow(self):
        # Given a workflow
        self._create_test_workflow(self.team_submission_uuid)

        # When I cancel the workflow, for fun
        team_api.cancel_workflow(self.team_submission_uuid, "Cancellation comment", "Cancelled by ID")

        # Then workflow is cancelled...
        # status for workflow should be cancelled...
        # and score points_earned should be 0.

    def _create_test_workflow(self, team_submission_uuid, status=TeamAssessmentWorkflow.STATUS.waiting):
        return TeamAssessmentWorkflow.objects.create(
            team_submission_uuid=team_submission_uuid,
            status=status,
            course_id='test course',
            item_id='test item'
        )
