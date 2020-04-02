""" Test Cases for Team Workflow API """
from openassessment.test_utils import CacheResetTest
from openassessment.workflow import team_api


class TestTeamAssessmentWorkflowApi(CacheResetTest):
    """ Test team assessment workflow API """

    def test_create_workflow(self):
        team_submission_uuid = 'foo'

        team_workflow = team_api.create_workflow(team_submission_uuid)

        assert team_workflow is not None

    def test_get_workflow(self):
        # Given a workflow
        team_submission_uuid = 'foo'
        TeamAssessmentWorkflow.objects.create(
            team_submission_uuid=team_submission_uuid,
            status=AssessmentWorkflow.STATUS.waiting,
            course_id='test course',
            item_id='test item'
        )

        # When I get the workflow
        team_workflow = team_api.get_workflow_for_submission(team_submission_uuid)

        # It is updated and returns a correctly serialized version
        assert team_workflow['team_submission_uuid'] == team_submission_uuid
        assert 'staff' in team_workflow['status_details']
