# -*- coding: utf-8 -*-
"""
Tests for staff assessment handlers in Open Assessment XBlock.
"""
import json
import mock
import copy

from openassessment.assessment.api import staff as staff_api

from .base import (
    scenario, SubmitAssessmentsMixin, XBlockHandlerTestCase,
    PEER_ASSESSMENTS, SELF_ASSESSMENT, STAFF_GOOD_ASSESSMENT,
)


class StaffAssessmentTestBase(XBlockHandlerTestCase, SubmitAssessmentsMixin):
    maxDiff = None

    def _assert_path_and_context(self, xblock, expected_context):
        path, context = xblock.staff_path_and_context()

        self.assertEqual('openassessmentblock/staff/oa_staff_grade.html', path)
        self.assertItemsEqual(expected_context, context)

        # Verify that we render without error
        resp = self.request(xblock, 'render_staff_assessment', json.dumps({}))
        self.assertGreater(len(resp), 0)


class TestStaffAssessmentRender(StaffAssessmentTestBase):

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_staff_grade_templates(self, xblock):
        self._verify_grade_templates_workflow(xblock)

    @scenario('data/self_assessment_closed.xml', user_id='Bob')
    def test_staff_grade_templates_closed(self, xblock):
        # Whether or not a problem is closed (past due date) has no impact on Staff Grade section.
        self._verify_grade_templates_workflow(xblock)

    def _verify_grade_templates_workflow(self, xblock):
        unavailable_context = {
            'status_value': 'Not Available',
            'button_active': 'disabled="disabled" aria-expanded="false"',
            'step_classes': 'is--unavailable',
            'xblock_id': xblock.scope_ids.usage_id
        }
        # Problem not yet started, Staff Grade section is marked "Not Available"
        self._assert_path_and_context(xblock, unavailable_context)

        # Create a submission for the student
        submission = xblock.create_submission(xblock.get_student_item_dict(), self.SUBMISSION)

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

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_staff_assess_handler(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        # Submit a staff-assessment
        self.submit_staff_assessment(xblock, submission, assessment=STAFF_GOOD_ASSESSMENT)

        # Expect that a staff-assessment was created
        assessment = staff_api.get_latest_staff_assessment(submission['uuid'])
        self.assertEqual(assessment['submission_uuid'], submission['uuid'])
        self.assertEqual(assessment['points_earned'], 5)
        self.assertEqual(assessment['points_possible'], 6)
        self.assertEqual(assessment['scorer_id'], 'Bob')
        self.assertEqual(assessment['score_type'], 'ST')
        self.assertEqual(assessment['feedback'], u'Staff: good job!')

        parts = sorted(assessment['parts'])
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0]['option']['criterion']['name'], u'Form')
        self.assertEqual(parts[0]['option']['name'], 'Fair')
        self.assertEqual(parts[1]['option']['criterion']['name'], u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮')
        self.assertEqual(parts[1]['option']['name'], u'ﻉซƈﻉɭɭﻉกՇ')

        # get the assessment scores by criteria
        assessment_by_crit = staff_api.get_assessment_scores_by_criteria(submission["uuid"])
        self.assertEqual(assessment_by_crit[u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮'], 3)
        self.assertEqual(assessment_by_crit[u'Form'], 2)

        score = staff_api.get_score(submission["uuid"], None)
        self.assertEqual(assessment['points_earned'], score['points_earned'])
        self.assertEqual(assessment['points_possible'], score['points_possible'])

        self.assert_assessment_event_published(
            xblock, 'openassessmentblock.staff_assess', assessment, type='full-grade'
        )

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_staff_assess_handler_regrade(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        assessment_copy = copy.copy(STAFF_GOOD_ASSESSMENT)
        assessment_copy['assess_type'] = 'regrade'
        # Submit a staff-assessment
        self.submit_staff_assessment(xblock, submission, assessment=assessment_copy)
        assessment = staff_api.get_latest_staff_assessment(submission['uuid'])
        self.assert_assessment_event_published(xblock, 'openassessmentblock.staff_assess', assessment, type='regrade')

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_permission_error(self, xblock):
        # Create a submission for the student
        student_item = xblock.get_student_item_dict()
        xblock.create_submission(student_item, self.SUBMISSION)
        resp = self.request(xblock, 'staff_assess', json.dumps(STAFF_GOOD_ASSESSMENT))
        self.assertIn("You do not have permission", resp)

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_invalid_options(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        self.set_staff_access(xblock)
        STAFF_GOOD_ASSESSMENT['submission_uuid'] = submission['uuid']

        for key in STAFF_GOOD_ASSESSMENT:
            # We don't want to fail if the assess_type is not submitted to the
            # backend, since it's only used for eventing right now.
            if key != 'assess_type':
                assessment_copy = copy.copy(STAFF_GOOD_ASSESSMENT)
                del assessment_copy[key]
                resp = self.request(xblock, 'staff_assess', json.dumps(assessment_copy), response_format='json')
                self.assertFalse(resp['success'])
                self.assertIn('msg', resp)

    @scenario('data/self_assessment_scenario.xml', user_id='bob')
    def test_assessment_error(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        self.set_staff_access(xblock)
        STAFF_GOOD_ASSESSMENT['submission_uuid'] = submission['uuid']
        with mock.patch('openassessment.xblock.staff_assessment_mixin.staff_api') as mock_api:
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
