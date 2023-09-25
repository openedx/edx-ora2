"""
Tests for staff assessment handlers in Open Assessment XBlock.
"""


import copy
import json

from unittest.mock import Mock, patch

from submissions import team_api as team_sub_api
from openassessment.assessment.api import (
    staff as staff_api,
    teams as teams_api
)
from openassessment.tests.factories import UserFactory
from openassessment.xblock.test.test_team import MockTeamsService, MOCK_TEAM_ID
from openassessment.workflow import team_api as team_workflow_api

from .base import (
    PEER_ASSESSMENTS,
    SELF_ASSESSMENT,
    STAFF_GOOD_ASSESSMENT,
    TEAM_GOOD_ASSESSMENT,
    TEAM_GOOD_ASSESSMENT_REGRADE,
    SubmitAssessmentsMixin,
    XBlockHandlerTestCase,
    scenario
)
from .test_staff_area import NullUserService, UserStateService, STUDENT_ITEM


class StaffAssessmentTestBase(XBlockHandlerTestCase, SubmitAssessmentsMixin):
    maxDiff = None

    def _assert_path_and_context(self, xblock, expected_context):
        """ Check Staff Assessment path and context correct. """
        path, context = xblock.staff_path_and_context()

        self.assertEqual('legacy/staff/oa_staff_grade.html', path)
        self.assertCountEqual(expected_context, context)

        # Verify that we render without error
        resp = self.request(xblock, 'render_staff_assessment', json.dumps({}))
        self.assertGreater(len(resp), 0)


class TestStaffAssessmentRender(StaffAssessmentTestBase):
    """ Test Staff Assessment Render correctly. """

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_staff_grade_templates(self, xblock):
        self._verify_grade_templates_workflow(xblock)

    @scenario('data/self_assessment_closed.xml', user_id='Bob')
    def test_staff_grade_templates_closed(self, xblock):
        # Whether or not a problem is closed (past due date) has no impact on Staff Grade section.
        self._verify_grade_templates_workflow(xblock)

    def _verify_grade_templates_workflow(self, xblock):
        """ Verify grade templates workflow. """
        unavailable_context = {
            'status_value': 'Not Available',
            'button_active': 'disabled="disabled" aria-expanded="false"',
            'step_classes': 'is--unavailable',
            'xblock_id': xblock.scope_ids.usage_id
        }
        # Problem not yet started, Staff Grade section is marked "Not Available"
        self._assert_path_and_context(xblock, unavailable_context)

        # Create a submission for the student
        submission = self.create_test_submission(xblock)

        # Response has been created, waiting for self assessment (no staff assessment exists either)
        self._assert_path_and_context(xblock, unavailable_context)

        # Submit a staff-assessment
        self.submit_staff_assessment(xblock, submission, assessment=STAFF_GOOD_ASSESSMENT)

        # Staff assessment exists, still waiting for self assessment.
        self._assert_path_and_context(
            xblock,
            {
                'status_value': 'Complete',
                'icon_class': 'fa-check',
                'message_title': 'You Must Complete the Steps Above to View Your Grade',
                'message_content': 'Although a course staff member has assessed your response, '
                                   'you will receive your grade only after you have completed all '
                                   'the required steps of this problem.',
                'button_active': 'aria-expanded="false"',
                'step_classes': 'is--initially--collapsed',
                'xblock_id': xblock.scope_ids.usage_id
            }
        )

        # Verify that once the required step (self assessment) is done, the staff grade is shown as complete.
        status_details = {'peer': {'complete': True}}
        self.set_mock_workflow_info(
            xblock, workflow_status='done', status_details=status_details, submission_uuid=submission['uuid']
        )
        self._assert_path_and_context(
            xblock,
            {
                'status_value': 'Complete',
                'icon_class': 'fa-check',
                'step_classes': 'is--showing',
                'button_active': 'aria-expanded="true"',
                'xblock_id': xblock.scope_ids.usage_id
            }
        )

        # Verify that if the problem is cancelled, the staff grade reflects this.
        self.set_mock_workflow_info(
            xblock, workflow_status='cancelled', status_details=status_details, submission_uuid=submission['uuid']
        )
        self._assert_path_and_context(
            xblock,
            {
                'status_value': 'Cancelled',
                'icon_class': 'fa-exclamation-triangle',
                'button_active': 'disabled="disabled" aria-expanded="false"',
                'step_classes': 'is--unavailable',
                'xblock_id': xblock.scope_ids.usage_id
            }
        )

    @scenario('data/grade_waiting_scenario.xml', user_id='Omar')
    def test_staff_grade_templates_no_peer(self, xblock):
        # Waiting to be assessed by a peer
        submission = self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT, waiting_for_peer=True
        )

        # Waiting for a peer assessment (though it is not used because staff grading is required),
        # no staff grade exists.
        self._assert_path_and_context(
            xblock,
            {
                'status_value': 'Not Available',
                'message_title': 'Waiting for a Staff Grade',
                'message_content': 'Check back later to see if a course staff member has assessed your response. '
                                   'You will receive your grade after the assessment is complete.',
                'step_classes': 'is--showing',
                'button_active': 'aria-expanded="true"',
                'xblock_id': xblock.scope_ids.usage_id
            }
        )

        # Submit a staff-assessment. The student can now see the score even though no peer assessments have been done.
        self.submit_staff_assessment(xblock, submission, assessment=STAFF_GOOD_ASSESSMENT)
        self._assert_path_and_context(
            xblock,
            {
                'status_value': 'Complete',
                'icon_class': 'fa-check',
                'step_classes': 'is--complete is--empty',
                'button_active': 'disabled="disabled" aria-expanded="false"',
                'xblock_id': xblock.scope_ids.usage_id
            }
        )


class TestStaffAssessment(StaffAssessmentTestBase):
    """ Test Staff Assessment Workflow. """

    @patch('openassessment.xblock.ui_mixins.legacy.staff_assessments.views.staff_api.create_assessment')
    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_staff_assess_handler_missing_id(self, xblock, mock_create_assessment):
        self.set_staff_access(xblock)

        # Create a submission for the student
        self.create_test_submission(xblock)

        # Try to submit an assessment without providing a good submission UUID
        resp = self.request(xblock, 'staff_assess', json.dumps(STAFF_GOOD_ASSESSMENT), response_format='json')

        # Expect that a staff-assessment was not created
        mock_create_assessment.assert_not_called()
        self.assertDictEqual(resp, {
            'success': False,
            'msg': "The submission ID of the submission being assessed was not found."
        })

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_staff_assess_handler(self, xblock):
        # Create a submission for the student
        submission = self.create_test_submission(xblock)

        # Submit a staff-assessment
        self.submit_staff_assessment(xblock, submission, assessment=STAFF_GOOD_ASSESSMENT)

        # Expect that a staff-assessment was created
        assessment = staff_api.get_latest_staff_assessment(submission['uuid'])
        self.assertEqual(assessment['submission_uuid'], submission['uuid'])
        self.assertEqual(assessment['points_earned'], 5)
        self.assertEqual(assessment['points_possible'], 6)
        self.assertEqual(assessment['scorer_id'], 'Bob')
        self.assertEqual(assessment['score_type'], 'ST')
        self.assertEqual(assessment['feedback'], 'Staff: good job!')

        self.assert_assessment_event_published(
            xblock, 'openassessmentblock.staff_assess', assessment, type='full-grade'
        )

        parts = assessment['parts']
        parts.sort(key=lambda x: x['option']['name'])

        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0]['option']['criterion']['name'], 'Form')
        self.assertEqual(parts[0]['option']['name'], 'Fair')
        self.assertEqual(parts[1]['option']['criterion']['name'], '𝓒𝓸𝓷𝓬𝓲𝓼𝓮')
        self.assertEqual(parts[1]['option']['name'], 'ﻉซƈﻉɭɭﻉกՇ')

        # get the assessment scores by criteria
        assessment_by_crit = staff_api.get_assessment_scores_by_criteria(submission["uuid"])
        self.assertEqual(assessment_by_crit['𝓒𝓸𝓷𝓬𝓲𝓼𝓮'], 3)
        self.assertEqual(assessment_by_crit['Form'], 2)

        score = staff_api.get_score(submission["uuid"], None, {})
        self.assertEqual(assessment['points_earned'], score['points_earned'])
        self.assertEqual(assessment['points_possible'], score['points_possible'])

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_staff_assess_handler_regrade(self, xblock):
        # Create a submission for the student
        submission = self.create_test_submission(xblock)

        assessment_copy = copy.copy(STAFF_GOOD_ASSESSMENT)
        assessment_copy['assess_type'] = 'regrade'
        # Submit a staff-assessment
        self.submit_staff_assessment(xblock, submission, assessment=assessment_copy)
        assessment = staff_api.get_latest_staff_assessment(submission['uuid'])
        self.assert_assessment_event_published(xblock, 'openassessmentblock.staff_assess', assessment, type='regrade')

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_permission_error(self, xblock):
        # Create a submission for the student
        self.create_test_submission(xblock)
        resp = self.request(xblock, 'staff_assess', json.dumps(STAFF_GOOD_ASSESSMENT))
        self.assertIn("You do not have permission", resp.decode('utf-8'))

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_invalid_options(self, xblock):
        # Create a submission for the student
        submission = self.create_test_submission(xblock)

        self.set_staff_access(xblock)

        for key in STAFF_GOOD_ASSESSMENT:
            # We don't want to fail if the assess_type is not submitted to the
            # backend, since it's only used for eventing right now.
            if key != 'assess_type':
                assessment_copy = copy.copy(STAFF_GOOD_ASSESSMENT)
                assessment_copy['submission_uuid'] = submission['uuid']
                del assessment_copy[key]
                resp = self.request(xblock, 'staff_assess', json.dumps(assessment_copy), response_format='json')
                self.assertFalse(resp['success'])
                self.assertIn('msg', resp)

    @scenario('data/self_assessment_scenario.xml', user_id='bob')
    def test_assessment_error(self, xblock):
        # Create a submission for the student
        submission = self.create_test_submission(xblock)

        self.set_staff_access(xblock)
        assessment = copy.deepcopy(STAFF_GOOD_ASSESSMENT)
        assessment['submission_uuid'] = submission['uuid']

        with patch('openassessment.xblock.ui_mixins.legacy.staff_assessments.views.staff_api') as mock_api:
            #  Simulate a error
            mock_api.create_assessment.side_effect = staff_api.StaffAssessmentRequestError
            resp = self.request(xblock, 'staff_assess', json.dumps(STAFF_GOOD_ASSESSMENT), response_format='json')
            self.assertFalse(resp['success'])
            self.assertIn('msg', resp)

            #  Simulate a different error
            mock_api.create_assessment.side_effect = staff_api.StaffAssessmentInternalError
            resp = self.request(xblock, 'staff_assess', json.dumps(STAFF_GOOD_ASSESSMENT), response_format='json')
            self.assertFalse(resp['success'])
            self.assertIn('msg', resp)


class TestStaffTeamAssessment(StaffAssessmentTestBase):
    """ Test Staff Team Assessment Workflow"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expected_answer = {
            'points_earned': 2,
            'parts0_criterion_name': 'Form',
            'parts1_criterion_name': 'Concise',
            'parts2_criterion_name': 'Clear-headed',
            'parts0_option_name': 'Facebook',
            'parts1_option_name': 'HP Lovecraft',
            'parts2_option_name': 'Yogi Berra'
        }
        cls.regrade_expected_answer = {
            'points_earned': 3,
            'parts0_criterion_name': 'Concise',
            'parts1_criterion_name': 'Form',
            'parts2_criterion_name': 'Clear-headed',
            'parts0_option_name': 'HP Lovecraft',
            'parts1_option_name': 'Reddit',
            'parts2_option_name': 'Yogi Berra'
        }

    @patch('openassessment.xblock.apis.assessments.staff_assessment_api.teams_api.create_assessment')
    @scenario('data/team_submission.xml', user_id='Bob')
    def test_staff_assess_handler_missing_id(self, xblock, mock_create_team_assessment):
        self.set_staff_access(xblock)

        # Create a team submission
        self._setup_xblock_and_create_team_submission(xblock)

        # Try to submit an assessment without providing a good submission UUID
        resp = self.request(xblock, 'staff_assess', json.dumps(TEAM_GOOD_ASSESSMENT), response_format='json')

        # Expect that a staff assessment was not created
        mock_create_team_assessment.assert_not_called()
        self.assertDictEqual(resp, {
            'success': False,
            'msg': "The submission ID of the submission being assessed was not found."
        })

    @scenario('data/team_submission.xml', user_id='Bob')
    def test_staff_assess_handler(self, xblock):

        submission = self._setup_xblock_and_create_team_submission(xblock)
        submission["uuid"] = str(submission["submission_uuids"][0])

        self.submit_staff_assessment(xblock, submission, assessment=TEAM_GOOD_ASSESSMENT)

        assessment = teams_api.get_latest_staff_assessment(submission['team_submission_uuid'])
        self._assert_team_assessment(assessment, submission, self.expected_answer)

    @scenario('data/team_submission.xml', user_id='Bob')
    def test_staff_assess_handler_regrade(self, xblock):
        """
        To test regrade we first need to create/setup xblock, create an initial team submission and then
        regrade it.
        """
        # create initial team submission
        submission = self._setup_xblock_and_create_team_submission(xblock)
        submission["uuid"] = str(submission["submission_uuids"][0])
        # assesss initial team submission
        self.submit_staff_assessment(xblock, submission, assessment=TEAM_GOOD_ASSESSMENT)
        # get assessment via API for asserts
        assessment = teams_api.get_latest_staff_assessment(submission['team_submission_uuid'])
        self._assert_team_assessment(assessment, submission, self.expected_answer)
        # assess the submission as a regrade by passing in a modified assessment
        self.submit_staff_assessment(xblock, submission, assessment=TEAM_GOOD_ASSESSMENT_REGRADE)
        # get the assessment via API for asserts
        assessment = teams_api.get_latest_staff_assessment(submission['team_submission_uuid'])
        self._assert_team_assessment(assessment, submission, self.regrade_expected_answer)

    @scenario('data/team_submission.xml', user_id='Bob')
    def test_assessment_error(self, xblock):
        # Create a submission for the team
        submission = self._setup_xblock_and_create_team_submission(xblock)
        submission["uuid"] = str(submission["submission_uuids"][0])

        with patch('openassessment.xblock.apis.assessments.staff_assessment_api.teams_api') as mock_api:
            # Simulate an error
            mock_api.create_assessment.side_effect = teams_api.StaffAssessmentRequestError
            resp = self.request(xblock, 'staff_assess', json.dumps(TEAM_GOOD_ASSESSMENT), response_format='json')
            self.assertFalse(resp['success'])
            self.assertIn('msg', resp)

            #  Simulate a different error
            mock_api.create_assessment.side_effect = teams_api.StaffAssessmentInternalError
            resp = self.request(xblock, 'staff_assess', json.dumps(TEAM_GOOD_ASSESSMENT), response_format='json')
            self.assertFalse(resp['success'])
            self.assertIn('msg', resp)

    def _assert_team_assessment(self, assessment, submission, expected_answer):
        """
        Helper function to perform asserts
        """
        self.assertEqual(assessment['points_earned'], expected_answer['points_earned'])
        self.assertEqual(assessment['scorer_id'], 'Bob')
        self.assertEqual(assessment['score_type'], 'ST')
        self.assertEqual(assessment['feedback'], 'Staff: good job!')
        parts = assessment['parts']
        parts.sort(key=lambda x: x['option']['name'])
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0]['option']['criterion']['name'], expected_answer['parts0_criterion_name'])
        self.assertEqual(parts[1]['option']['criterion']['name'], expected_answer['parts1_criterion_name'])
        self.assertEqual(parts[2]['option']['criterion']['name'], expected_answer['parts2_criterion_name'])
        self.assertEqual(parts[0]['option']['name'], expected_answer['parts0_option_name'])
        self.assertEqual(parts[1]['option']['name'], expected_answer['parts1_option_name'])
        self.assertEqual(parts[2]['option']['name'], expected_answer['parts2_option_name'])

        score = teams_api.get_score(submission['team_submission_uuid'], {}, {})
        self.assertEqual(assessment['points_earned'], score['points_earned'])
        self.assertEqual(assessment['points_possible'], score['points_possible'])

    def _setup_xblock_and_create_team_submission(self, xblock):
        """
        A shortcut method to setup ORA xblock and add a user submission or a team submission to the block.
        """
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, 'Bob'
        )
        # pylint: disable=protected-access
        xblock.runtime._services['user'] = NullUserService()
        xblock.runtime._services['user_state'] = UserStateService()
        xblock.runtime._services['teams'] = MockTeamsService(True)

        usage_id = xblock.scope_ids.usage_id
        xblock.location = usage_id
        xblock.user_state_upload_data_enabled = Mock(return_value=True)
        student_item = STUDENT_ITEM.copy()
        student_item["item_id"] = usage_id

        xblock.is_team_assignment = Mock(return_value=True)
        anonymous_user_ids_for_team = ['Bob', 'Alice', 'Chris']
        xblock.get_anonymous_user_ids_for_team = Mock(return_value=anonymous_user_ids_for_team)
        arbitrary_test_user = UserFactory.create()
        return self._create_team_submission(
            STUDENT_ITEM['course_id'],
            usage_id,
            MOCK_TEAM_ID,
            arbitrary_test_user.id,
            anonymous_user_ids_for_team,
            "this is an answer to a team assignment",
        )

    @staticmethod
    def _create_mock_runtime(
            item_id,
            is_staff,
            is_admin,
            anonymous_user_id,
            user_is_beta=False,
    ):
        """
        Internal helper to define a mock runtime.
        """
        mock_runtime = Mock(
            course_id='test_course',
            item_id=item_id,
            anonymous_student_id='Bob',
            user_is_staff=is_staff,
            user_is_admin=is_admin,
            user_is_beta=user_is_beta,
            service=lambda self, service: Mock(
                get_anonymous_student_id=lambda user_id, course_id: anonymous_user_id
            )
        )
        return mock_runtime

    def _create_team_submission(self, course_id, item_id, team_id, submitting_user_id, team_member_student_ids, answer):
        """
        Create a team submission and initialize a team workflow
        """
        team_submission = team_sub_api.create_submission_for_team(
            course_id,
            item_id,
            team_id,
            submitting_user_id,
            team_member_student_ids,
            answer,
        )
        team_workflow_api.create_workflow(team_submission['team_submission_uuid'])
        return team_submission
