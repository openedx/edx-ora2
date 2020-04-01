""" Test Cases for Team Workflow API """
from openassessment.test_utils import CacheResetTest
from openassessment.workflow import team_api


class TestTeamAssessmentWorkflowApi(CacheResetTest):
    """ Test team assessment workflow API """

    def test_create_workflow(self):
        team_submission_uuid = 'foo'

        team_workflow = team_api.create_workflow(team_submission_uuid)

        assert team_workflow is not None
