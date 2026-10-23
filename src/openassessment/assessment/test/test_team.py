"""
Tests for team assessments.
"""


from unittest import mock
from freezegun import freeze_time

from django.utils.timezone import now

from submissions import team_api as team_submissions_api

from openassessment.assessment.api import teams as teams_api
from openassessment.assessment.models.staff import TeamStaffWorkflow
from openassessment.assessment.test.constants import OPTIONS_SELECTED_DICT, RUBRIC
from openassessment.tests.factories import TeamStaffWorkflowFactory, UserFactory
from openassessment.test_utils import CacheResetTest


STAFF_TYPE = "ST"


class TestTeamApi(CacheResetTest):
    """ Tests for the Team Assessment API """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Users for testing
        staff_user = UserFactory.create()
        staff_user.is_staff = True
        staff_user.save()
        cls.staff_user_id = staff_user.id

        cls.submitting_user_id = UserFactory.create().id
        team_member_1_id = UserFactory.create().id
        team_member_2_id = UserFactory.create().id
        user_ids = [cls.submitting_user_id, team_member_1_id, team_member_2_id]
        cls.team_member_ids = [f'anon_id_for_{user_id}' for user_id in user_ids]

        cls.default_assessment = (
            cls.staff_user_id,  # scorer_id
            OPTIONS_SELECTED_DICT["few"]["options"],  # options_selected
            {},  # critereon_feedback
            '',  # overall_feedback
            RUBRIC  # rubric_dict
        )

    def test_submitter_is_finished(self):
        team_submission_uuid = 'foo'
        team_requirements = {}

        self.assertTrue(teams_api.submitter_is_finished(
            team_submission_uuid,
            team_requirements
        ))

    def test_assessment_is_not_required(self):
        # Given a submission but unifinshed assessment
        team_submission_uuid = self._create_test_submission_for_team()['team_submission_uuid']
        staff_requirements = None

        # When I ask the API if the assessment is finished
        api_response = teams_api.assessment_is_finished(team_submission_uuid, staff_requirements, {})

        # Then it returns False
        self.assertFalse(api_response)

    def test_assessment_is_not_finished(self):
        # Given a submission but unifinshed assessment
        team_submission_uuid = self._create_test_submission_for_team()['team_submission_uuid']
        staff_requirements = {'required': True}

        # When I ask the API if the assessment is finished
        api_response = teams_api.assessment_is_finished(team_submission_uuid, staff_requirements, {})

        # Then it returns False
        self.assertFalse(api_response)

    def test_assessment_is_finished(self):
        # Given a submission and assessment
        team_submission_uuid = self._create_test_submission_for_team()['team_submission_uuid']
        self._create_test_assessments_for_team(team_submission_uuid)
        staff_requirements = {'required': True}

        # When I ask the API if the assessment is finished
        api_response = teams_api.assessment_is_finished(team_submission_uuid, staff_requirements, {})

        # Then it returns True
        self.assertTrue(api_response)

    @mock.patch('submissions.team_api.get_team_submission')
    def test_on_init(self, mock_get_submission):
        # Given a team submission
        team_submission_uuid = 'foo'
        mock_get_submission.return_value = {
            'team_submission_uuid': team_submission_uuid,
            'course_id': 'fake_course',
            'item_id': 'fake_item',
            'submission_uuids': ['uuid1', 'uuid2', 'uuid3']
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

    def test_get_score_none(self):
        # Given there's no assessment for a submission
        team_submission_uuid = self._create_test_submission_for_team()['team_submission_uuid']
        staff_requirements = {'required': True}

        # When I use the API to get the score
        score = teams_api.get_score(team_submission_uuid, staff_requirements, {})

        # Then None is returned
        self.assertIsNone(score)

    def test_get_score(self):
        # Given an assessment fora  submission
        team_submission_uuid = self._create_test_submission_for_team()['team_submission_uuid']
        assessments = self._create_test_assessments_for_team(team_submission_uuid)
        staff_requirements = {'required': True}

        # When I query the API for the score
        score = teams_api.get_score(team_submission_uuid, staff_requirements, {})

        # Then the score is returned (from test constants)
        assessment = assessments[-1]
        self.assertEqual(score, {
            "points_earned": assessment["points_earned"],
            "points_possible": assessment["points_possible"],
            "contributing_assessments": [assessment['id']],
            "staff_id": assessment["scorer_id"],
        })

    def test_get_latest_assessment_none(self):
        # Given no assessments for a team, when I try to get latest
        team_submission = self._create_test_submission_for_team()
        assessment = teams_api.get_latest_staff_assessment(team_submission['team_submission_uuid'])

        # Then None is returned
        self.assertIsNone(assessment)

    def test_get_latest_assessment(self):
        # Given an assessment for a team submission
        team_submission_uuid = self._create_test_submission_for_team()['team_submission_uuid']
        assessments = self._create_test_assessments_for_team(team_submission_uuid)

        # When I ask the API for the latest
        returned_assessment = teams_api.get_latest_staff_assessment(team_submission_uuid)

        # Then the correct assessment is returned
        self.assertIsNotNone(returned_assessment)
        self.assertEqual(returned_assessment['id'], assessments[-1]['id'])

    def test_get_assessment_scores_by_criteria(self):
        # Given an assessment for a team submission
        team_submission_uuid = self._create_test_submission_for_team()['team_submission_uuid']
        self._create_test_assessments_for_team(team_submission_uuid)

        # When I ask the API for assessment scores
        score_criteria = teams_api.get_assessment_scores_by_criteria(team_submission_uuid)

        # Then the API returns the rubric dictionary...
        # TODO... with the correct scores
        self.assertEqual(
            set(score_criteria.keys()),
            set(OPTIONS_SELECTED_DICT["few"]["options"].keys())
        )

    def test_get_submission_to_assess_none(self):
        # Given no submissions to assess
        # When I ask the API for another submission
        submission_to_assess = teams_api.get_submission_to_assess(
            'mock-course',
            'mock-item',
            self.staff_user_id
        )

        # Then the API returns None
        self.assertIsNone(submission_to_assess)

    def test_get_submission_to_assess(self):
        # Given ungraded submissions to assess
        team_submission = self._create_test_submission_for_team()

        # When I ask the API for a submission
        submission_to_assess = teams_api.get_submission_to_assess(
            'mock-course',
            'mock-item',
            self.staff_user_id
        )

        # Then I recieve a submission to assess
        self.assertEqual(team_submission, submission_to_assess)

    def test_get_grading_statistics(self):
        # Given an open response item
        mock_ora = ('mock-course', 'mock-item')

        # Initially, nothing listed
        self.assertEqual(
            teams_api.get_staff_grading_statistics(*mock_ora),
            {
                'graded': 0,
                'ungraded': 0,
                'in-progress': 0
            }
        )

        # New submissions count towards 'ungraded'
        submission = self._create_test_submission_for_team()
        self.assertEqual(
            teams_api.get_staff_grading_statistics(*mock_ora),
            {
                'graded': 0,
                'ungraded': 1,
                'in-progress': 0
            }
        )
        # Complete assessments count towards 'graded'
        teams_api.create_assessment(
            submission['team_submission_uuid'],
            *self.default_assessment
        )
        self.assertEqual(
            teams_api.get_staff_grading_statistics(*mock_ora),
            {
                'graded': 1,
                'ungraded': 0,
                'in-progress': 0
            }
        )

    def test_create_assessment(self):
        # Given a team submission and workflow
        team_submission = self._create_test_submission_for_team()

        # When I create an assessment
        assessments = teams_api.create_assessment(
            team_submission['team_submission_uuid'],
            *self.default_assessment
        )

        # Assessments are created for each memeber of the team
        self.assertEqual(
            [assessment['submission_uuid'] for assessment in assessments],
            [str(uuid) for uuid in team_submission['submission_uuids']]
        )

    def _create_test_assessments_for_team(self, team_submission_uuid):
        """
        Helper to create team assessments.
        Implicitly creates a submission and workflow to link the assessment to.

        Returns:
            Assessments
        """
        # Create submission and workflow
        if team_submission_uuid is None:
            team_submission_uuid = self._create_test_submission_for_team()['team_submission_uuid']

        # Create assessment
        assessments = teams_api.create_assessment(
            team_submission_uuid,
            self.staff_user_id,
            OPTIONS_SELECTED_DICT["few"]["options"], {}, "",
            RUBRIC
        )
        return assessments

    def _create_test_submission_for_team(self):
        """
        Helper to create a team submission.
        Implicitly creates a TeamStaffWorkflow linked to the submission.

        Returns:
            TeamSubmission
        """
        # Create a team submission
        team_submission = team_submissions_api.create_submission_for_team(
            'mock-course',
            'mock-item',
            'mock-team-id',
            self.submitting_user_id,
            self.team_member_ids,
            '42'
        )

        # Create a team staff workflow linked to the team submission
        self._create_test_workflow(
            team_submission['team_submission_uuid'],
            course_id='mock-course',
            item_id='mock-item'
        )

        return team_submission

    def _create_test_workflow(self, team_submission_uuid, course_id=None, item_id=None):
        """
        Creates a test team workflow and links to a team submission

        Returns:
            Created workflow
        """
        workflow = TeamStaffWorkflowFactory.create()
        workflow.team_submission_uuid = team_submission_uuid
        workflow.course_id = course_id if course_id else workflow.course_id
        workflow.item_id = item_id if item_id else workflow.item_id
        workflow.save()

        return workflow
