""" Tests for ORA workflow models """

from contextlib import contextmanager
import ddt
import mock
from freezegun import freeze_time

from django.utils.timezone import now

from openassessment.test_utils import CacheResetTest
from openassessment.workflow.errors import AssessmentWorkflowInternalError
from openassessment.workflow.models import TeamAssessmentWorkflow, AssessmentWorkflowStep
from openassessment.workflow.test.factories import AssessmentWorkflowStepFactory


@ddt.ddt
class TeamAssessmentTest(CacheResetTest):
    """ Tests for the TeamAssessmentWorkflow model """
    team_submission_uuid = 'team-submission-uuid'
    submission_uuids = ['submission-uuid-' + str(i) for i in range(5)]
    course_id = 'edx/Teamwork/Cooperation'
    item_id = 'this-is-an-item-id-i-guess'
    MOCK_TEAM_SUBMISSION = {
        'team_submission_uuid': team_submission_uuid,
        'submission_uuids': submission_uuids,
        'course_id': course_id,
        'item_id': item_id
    }

    def setUp(self):
        super(TeamAssessmentTest, self).setUp()
        self.workflow_step_api_patcher = mock.patch.object(AssessmentWorkflowStep, 'api')
        mocked_workflow_api = self.workflow_step_api_patcher.start()
        self.mock_assessment_api = mock.Mock()
        mocked_workflow_api.return_value = self.mock_assessment_api

    def tearDown(self):
        super(TeamAssessmentTest, self).tearDown()
        self.workflow_step_api_patcher.stop()

    @contextmanager
    def mock_submissions_api_get(self, return_value=None):
        return_value = return_value or self.MOCK_TEAM_SUBMISSION
        with mock.patch(
            'openassessment.workflow.models.sub_team_api.get_team_submission',
            return_value=return_value
        ):
            yield

    def test_start_workflow(self):
        with self.mock_submissions_api_get():
            team_workflow = TeamAssessmentWorkflow.start_workflow(self.team_submission_uuid)
        self.assertEqual(team_workflow.team_submission_uuid, self.team_submission_uuid)
        self.assertIn(team_workflow.submission_uuid, self.submission_uuids)
        self.assertEqual(team_workflow.status, TeamAssessmentWorkflow.STATUS.teams)
        self.assertEqual(team_workflow.course_id, self.course_id)
        self.assertEqual(team_workflow.item_id, self.item_id)

        step_names = [step.name for step in team_workflow.steps.all()]
        self.assertEqual(step_names, ['teams'])

        self.mock_assessment_api.on_init.assert_called_once()

    def test_start_workflow_no_individual_submissions(self):
        submission = dict(self.MOCK_TEAM_SUBMISSION)
        submission['submission_uuids'] = []
        with self.assertRaises(AssessmentWorkflowInternalError):
            with self.mock_submissions_api_get(submission):
                TeamAssessmentWorkflow.start_workflow(self.team_submission_uuid)

    def test_get_steps(self):
        with self.mock_submissions_api_get():
            workflow = TeamAssessmentWorkflow.start_workflow(self.team_submission_uuid)
        steps = workflow._get_steps()  # pylint: disable=protected-access
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].name, TeamAssessmentWorkflow.TEAM_STAFF_STEP_NAME)

    def test_get_steps_multiple_step_error(self):
        with self.mock_submissions_api_get():
            workflow = TeamAssessmentWorkflow.start_workflow(self.team_submission_uuid)
        AssessmentWorkflowStepFactory.create(workflow=workflow)
        workflow.refresh_from_db()
        with self.assertRaises(AssessmentWorkflowInternalError):
            workflow._get_steps()  # pylint: disable=protected-access

    def test_get_steps_wrong_type(self):
        with self.mock_submissions_api_get():
            workflow = TeamAssessmentWorkflow.start_workflow(self.team_submission_uuid)
        step = workflow._get_steps()[0]  # pylint: disable=protected-access
        step.name = 'peer'
        step.save()
        with self.assertRaises(AssessmentWorkflowInternalError):
            workflow._get_steps()  # pylint: disable=protected-access

    def _update_from_assessments(self, workflow, submissions_api_fake_score, assessment_api_fake_score):
        self.mock_assessment_api.get_score.return_value = assessment_api_fake_score
        with mock.patch(
            'openassessment.workflow.models.sub_api.get_latest_score_for_submission',
            return_value=submissions_api_fake_score
        ):
            workflow.update_from_assessments()

    @freeze_time("2020-05-03")
    @ddt.data(None, 5)
    @mock.patch('openassessment.workflow.models.sub_team_api.set_score')
    def test_update_from_assessments(self, old_score_points_earned, mock_set_team_score):
        """
        There is no score recorded in the submissions api, or the score is different than the one we
        have gotten from the assessment module
        """
        submissions_api_fake_score = None
        if old_score_points_earned:
            submissions_api_fake_score = {
                'annotations': [{'annotation_type': TeamAssessmentWorkflow.STAFF_ANNOTATION_TYPE}],
                'points_earned': old_score_points_earned
            }

        assessment_api_fake_score = {
            "points_earned": 9,
            "points_possible": 10,
            "contributing_assessments": ['assessment_1_id'],
            "staff_id": 'staff_id',
        }

        with self.mock_submissions_api_get():
            workflow = TeamAssessmentWorkflow.start_workflow(self.team_submission_uuid)

        self.mock_assessment_api.assessment_is_finished.return_value = True
        self._update_from_assessments(workflow, submissions_api_fake_score, assessment_api_fake_score)

        workflow.refresh_from_db()
        self.assertEqual(workflow.status, TeamAssessmentWorkflow.STATUS.done)
        self.assertEqual(workflow._team_staff_step.assessment_completed_at, now())  # pylint: disable=protected-access
        mock_set_team_score.assert_called_with(
            self.team_submission_uuid,
            9,
            10,
            annotation_creator='staff_id',
            annotation_type=TeamAssessmentWorkflow.STAFF_ANNOTATION_TYPE,
            annotation_reason='A staff member has defined the score for this submission'
        )

    @freeze_time("2020-05-03")
    @mock.patch('openassessment.workflow.models.sub_team_api.set_score')
    def test_update_from_assessments_old_and_new_points_equal(self, mock_set_team_score):
        """ There is already an equal score recorded in the submissions API """
        submissions_api_fake_score = {
            'annotations': [{'annotation_type': TeamAssessmentWorkflow.STAFF_ANNOTATION_TYPE}],
            'points_earned': 9
        }
        assessment_api_fake_score = {
            "points_earned": 9,
            "points_possible": 10,
            "contributing_assessments": ['assessment_1_id'],
            "staff_id": 'staff_id',
        }
        with self.mock_submissions_api_get():
            workflow = TeamAssessmentWorkflow.start_workflow(self.team_submission_uuid)

        self.mock_assessment_api.assessment_is_finished.return_value = True
        self._update_from_assessments(workflow, submissions_api_fake_score, assessment_api_fake_score)
        workflow.refresh_from_db()

        self.assertEqual(workflow.status, TeamAssessmentWorkflow.STATUS.done)
        self.assertEqual(workflow._team_staff_step.assessment_completed_at, now())  # pylint: disable=protected-access
        mock_set_team_score.assert_not_called()
