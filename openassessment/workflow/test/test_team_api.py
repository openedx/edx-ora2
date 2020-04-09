""" Test Cases for Team Workflow API """
import uuid

from openassessment.workflow.models import TeamAssessmentWorkflow
from openassessment.test_utils import CacheResetTest
from openassessment.workflow import team_api


class TestTeamAssessmentWorkflowApi(CacheResetTest):
    """ Test team assessment workflow API """

    def test_create_workflow(self):
        # Given a test UUID
        # When I create a workflow
        team_workflow = team_api.create_workflow('foo')

        # TODO - Complete in https://openedx.atlassian.net/browse/EDUCATOR-4986
        assert team_workflow is not None

    def test_get_workflow(self):
        # Given a workflow
        self._create_test_workflow('foo')

        # When I get the workflow
        team_workflow = team_api.get_workflow_for_submission('foo')

        # It is updated and returns a correctly serialized version
        assert team_workflow['team_submission_uuid'] == 'foo'
        assert 'staff' in team_workflow['status_details']

    def test_get_status_counts(self):
        expected_steps = ['staff', 'waiting', 'done', 'cancelled']

        # Initially, counts for all expected steps should be 0
        initial_counts = team_api.get_status_counts('test course', 'test item')

        for step in expected_steps:
            assert {'status': step, 'count': 0} in initial_counts

        # Given some assessments
        self._create_test_workflow('foo', 'staff')
        self._create_test_workflow('bar', 'waiting')
        self._create_test_workflow('baz', 'done')
        self._create_test_workflow('biz', 'cancelled')

        # When we get updated counts
        counts = team_api.get_status_counts('test course', 'test item')

        for step in expected_steps:
            assert {'status': step, 'count': 1} in counts

    def test_cancel_workflow(self):
        # Given a workflow
        team_submission_uuid = 'foo'
        team_workflow = self._create_test_workflow(team_submission_uuid)

        # When I cancel the workflow
        team_api.cancel_workflow(
            team_submission_uuid=team_submission_uuid,
            comments='cancelled',
            cancelled_by_id='my-id'
        )

        # The workflow status should be cancelled...
        team_workflow = team_api._get_workflow_model(team_submission_uuid)
        self.assertTrue(team_api.is_workflow_cancelled(team_submission_uuid))
        self.assertEqual(team_workflow.status, 'cancelled')

        # and the points/score should be 0
        self.assertEqual(team_workflow.score, None)

    def test_get_workflow_cancellation(self):
        # Given a cancelled workflow
        team_submission_uuid = 'foo'
        team_workflow = self._create_test_workflow(team_submission_uuid)
        team_api.cancel_workflow(
            team_submission_uuid=team_submission_uuid,
            comments='cancelled',
            cancelled_by_id='my-id'
        )

        # When I query for a cancelled flow
        cancellation = team_api.get_assessment_workflow_cancellation(team_submission_uuid)

        # Then I get serialized info from the cancellation
        self.assertEquals(cancellation['comments'], 'cancelled')
        self.assertEquals(cancellation['cancelled_by_id'], 'my-id')

    def _create_test_workflow(self, team_submission_uuid, status=TeamAssessmentWorkflow.STATUS.waiting):
        """ Create a team workflow with filler values """
        return TeamAssessmentWorkflow.objects.create(
            team_submission_uuid=team_submission_uuid,
            submission_uuid=uuid.uuid4(),  # generated to fulfill unique constraint
            status=status,
            course_id='test course',
            item_id='test item'
        )
