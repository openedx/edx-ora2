""" Test Cases for Team Workflow API """
import uuid

from submissions import team_api as sub_team_api

from openassessment.workflow.models import TeamAssessmentWorkflow, AssessmentWorkflowStep
from openassessment.test_utils import CacheResetTest
from openassessment.workflow import team_api
from openassessment.tests.factories import UserFactory


class TestTeamAssessmentWorkflowApi(CacheResetTest):
    """ Test team assessment workflow API """

    course_id = 'edx/Teamwork/Cooperation'
    item_id = 'this-is-an-item-id-i-guess'
    users = []
    team_submission_dict = {}
    team_submission_uuid = None
    submission_uuids = []

    def _create_submission(self):
        """
        Create a test team submission through the submissions api
        """
        self.users = [UserFactory.create() for _ in range(5)]
        anonymous_user_ids = ['anonymous_user_id_for_' + user.username for user in self.users]

        self.team_submission_dict = sub_team_api.create_submission_for_team(
            self.course_id,
            self.item_id,
            'team-rocket',
            self.users[0].id,
            anonymous_user_ids,
            'this-is-my-answer',
        )
        self.team_submission_uuid = self.team_submission_dict['team_submission_uuid']
        self.submission_uuids = self.team_submission_dict['submission_uuids']

    def test_create_workflow(self):
        self._create_submission()
        team_workflow = team_api.create_workflow(self.team_submission_uuid)

        self.assertEqual(team_workflow.team_submission_uuid, self.team_submission_uuid)
        self.assertIn(team_workflow.submission_uuid, self.submission_uuids)
        self.assertEqual(team_workflow.status, TeamAssessmentWorkflow.STATUS.teams)
        self.assertEqual(team_workflow.course_id, self.course_id)
        self.assertEqual(team_workflow.item_id, self.item_id)

        step_names = [step.name for step in team_workflow.steps.all()]
        self.assertEqual(step_names, ['teams'])

    def test_get_workflow(self):
        self._create_submission()
        team_api.create_workflow(self.team_submission_uuid)

        # When I get the workflow
        team_workflow = team_api.get_workflow_for_submission(self.team_submission_uuid)

        # It is updated and returns a correctly serialized version
        assert team_workflow['team_submission_uuid'] == self.team_submission_uuid
        assert 'teams' in team_workflow['status_details']

    def test_get_status_counts(self):
        expected_steps = ['teams', 'waiting', 'done', 'cancelled']

        # Initially, counts for all expected steps should be 0
        initial_counts = team_api.get_status_counts('test course', 'test item')

        for step in expected_steps:
            assert {'status': step, 'count': 0} in initial_counts

        # Given some assessments
        self._create_test_workflow('foo', 'teams')
        self._create_test_workflow('bar', 'waiting')
        self._create_test_workflow('baz', 'done')
        self._create_test_workflow('biz', 'cancelled')

        # When we get updated counts
        counts = team_api.get_status_counts('test course', 'test item')

        for step in expected_steps:
            assert {'status': step, 'count': 1} in counts

    def test_cancel_workflow(self):
        # Given a workflow
        self._create_submission()
        team_workflow = team_api.create_workflow(self.team_submission_uuid)

        # When I cancel the workflow
        team_api.cancel_workflow(
            team_submission_uuid=self.team_submission_uuid,
            comments='cancelled',
            cancelled_by_id='my-id'
        )

        # The workflow status should be cancelled...
        team_workflow = team_api.get_workflow_for_submission(self.team_submission_uuid)
        self.assertTrue(team_api.is_workflow_cancelled(self.team_submission_uuid))
        self.assertEqual(team_workflow['status'], 'cancelled')

        # and the points/score should be 0
        self.assertEqual(team_workflow['score'], None)

    def test_get_workflow_cancellation(self):
        # Given a cancelled workflow
        self._create_submission()
        team_api.create_workflow(self.team_submission_uuid)
        team_api.cancel_workflow(
            team_submission_uuid=self.team_submission_uuid,
            comments='cancelled',
            cancelled_by_id='my-id'
        )

        # When I query for a cancelled flow
        cancellation = team_api.get_assessment_workflow_cancellation(self.team_submission_uuid)

        # Then I get serialized info from the cancellation
        self.assertEqual(cancellation['comments'], 'cancelled')
        self.assertEqual(cancellation['cancelled_by_id'], 'my-id')

    def _create_test_workflow(self, team_submission_uuid, status=TeamAssessmentWorkflow.STATUS.waiting):
        """ Create a team workflow with filler values """
        workflow = TeamAssessmentWorkflow.objects.create(
            team_submission_uuid=team_submission_uuid,
            submission_uuid=uuid.uuid4(),  # generated to fulfill unique constraint
            status=status,
            course_id='test course',
            item_id='test item'
        )
        AssessmentWorkflowStep.objects.create(
            workflow=workflow,
            name='teams',
            order_num=1
        )
        return workflow
