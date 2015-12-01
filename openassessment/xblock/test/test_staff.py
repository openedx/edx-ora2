# -*- coding: utf-8 -*-
"""
Tests for staff assessment handlers in Open Assessment XBlock.
"""
import json
import mock
import copy
from openassessment.assessment.api import staff as staff_api
from .base import XBlockHandlerTestCase, scenario
from .test_grade import SubmitAssessmentsMixin

class StaffAssessmentTestBase(XBlockHandlerTestCase):
    maxDiff = None

    SUBMISSION = (u'ՇﻉรՇ', u'รપ๒๓ٱรรٱѻก')

    ASSESSMENT = {
        'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
        'criterion_feedback': {},
        'overall_feedback': ""
    }

    def set_staff_access(self, xblock):
        xblock.xmodule_runtime = mock.Mock(user_is_staff=True)
        xblock.xmodule_runtime.anonymous_student_id = 'Bob'

    def _assert_path_and_context(self, xblock, expected_context):
        path, context = xblock.staff_path_and_context()

        self.assertEqual('openassessmentblock/staff/oa_staff_grade.html', path)
        self.assertItemsEqual(expected_context, context)

        # Verify that we render without error
        resp = self.request(xblock, 'render_staff_assessment', json.dumps({}))
        self.assertGreater(len(resp), 0)

    @staticmethod
    def _set_mock_workflow_info(xblock, workflow_status, status_details, submission_uuid):
        xblock.get_workflow_info = mock.Mock(return_value={
            'status': workflow_status,
            'status_details': status_details,
            'submission_uuid': submission_uuid
        })

    def _submit_staff_assessment(self, xblock, submission):
        # Submit a staff-assessment
        self.set_staff_access(xblock)
        self.ASSESSMENT['submission_uuid'] = submission['uuid']
        resp = self.request(xblock, 'staff_assess', json.dumps(self.ASSESSMENT), response_format='json')
        self.assertTrue(resp['success'])


class TestStaffAssessmentRender(StaffAssessmentTestBase, SubmitAssessmentsMixin):

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
            'step_classes': 'is--unavailable is--empty is--collapsed',
        }
        # Problem not yet started, Staff Grade section is marked "Not Available"
        self._assert_path_and_context(xblock, unavailable_context)

        # Create a submission for the student
        submission = xblock.create_submission(xblock.get_student_item_dict(), self.SUBMISSION)

        # Response has been created, waiting for self assessment (no staff assessment exists either)
        self._assert_path_and_context(xblock, unavailable_context)

        # Submit a staff-assessment
        self._submit_staff_assessment(xblock, submission)

        # Staff assessment exists, still waiting for self assessment.
        self._assert_path_and_context(
            xblock,
            {
                'status_value': 'Complete',
                'icon_class': 'fa-check',
                'message_title': 'You Must Complete the Steps Above to View Your Grade',
                'message_content': 'Although a course staff member has assessed your response, you will receive your grade only after you have completed all the required steps of this problem.'
            }
        )

        # Verify that once the required step (self assessment) is done, the staff grade is shown as complete.
        status_details = {'peer': {'complete': True}}
        self._set_mock_workflow_info(
            xblock, workflow_status='done', status_details=status_details, submission_uuid=submission['uuid']
        )
        self._assert_path_and_context(
            xblock,
            {
                'status_value': 'Complete',
                'icon_class': 'fa-check',
                'step_classes': 'is--complete is--empty is--collapsed',
            }
        )

        # Verify that if the problem is cancelled, the staff grade reflects this.
        self._set_mock_workflow_info(
            xblock, workflow_status='cancelled', status_details=status_details, submission_uuid=submission['uuid']
        )
        self._assert_path_and_context(
            xblock,
            {
                'status_value': 'Cancelled',
                'icon_class': 'fa-exclamation-triangle',
            }
        )

    @scenario('data/grade_waiting_scenario.xml', user_id='Omar')
    def test_staff_grade_templates_no_peer(self, xblock):
        # Waiting to be assessed by a peer
        submission = self._create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, self.ASSESSMENTS, self.ASSESSMENTS[0], waiting_for_peer=True
        )

        # Waiting for a peer assessment (though it is not used because staff grading is required),
        # no staff grade exists.
        self._assert_path_and_context(
            xblock,
            {
                'status_value': 'Not Available',
                'message_title': 'Waiting for a Staff Grade',
                'message_content': 'Check back later to see if a course staff member has assessed your response. You will receive your grade after the assessment is complete.',
            }
        )

        # Submit a staff-assessment. The student can now see the score even though no peer assessments have been done.
        self._submit_staff_assessment(xblock, submission)
        self._assert_path_and_context(
            xblock,
            {
                'status_value': 'Complete',
                'icon_class': 'fa-check',
                'step_classes': 'is--complete is--empty is--collapsed',
            }
        )


class TestStaffAssessment(StaffAssessmentTestBase):

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_staff_assess_handler(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        # Submit a staff-assessment
        self._submit_staff_assessment(xblock, submission)

        # Expect that a staff-assessment was created
        assessment = staff_api.get_latest_staff_assessment(submission['uuid'])
        self.assertEqual(assessment['submission_uuid'], submission['uuid'])
        self.assertEqual(assessment['points_earned'], 5)
        self.assertEqual(assessment['points_possible'], 6)
        self.assertEqual(assessment['scorer_id'], 'Bob')
        self.assertEqual(assessment['score_type'], 'ST')
        self.assertEqual(assessment['feedback'], u'')

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

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_permission_error(self, xblock):
        # Create a submission for the student
        student_item = xblock.get_student_item_dict()
        xblock.create_submission(student_item, self.SUBMISSION)
        resp = self.request(xblock, 'staff_assess', json.dumps(self.ASSESSMENT))
        self.assertIn("You do not have permission", resp)

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_invalid_options(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        self.set_staff_access(xblock)
        self.ASSESSMENT['submission_uuid'] = submission['uuid']

        for key in self.ASSESSMENT:
            assessment_copy = copy.copy(self.ASSESSMENT)
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
        self.ASSESSMENT['submission_uuid'] = submission['uuid']
        with mock.patch('openassessment.xblock.staff_assessment_mixin.staff_api') as mock_api:
            #  Simulate a error
            mock_api.create_assessment.side_effect = staff_api.StaffAssessmentRequestError
            resp = self.request(xblock, 'staff_assess', json.dumps(self.ASSESSMENT), response_format='json')
            self.assertFalse(resp['success'])
            self.assertIn('msg', resp)

            #  Simulate a different error
            mock_api.create_assessment.side_effect = staff_api.StaffAssessmentInternalError
            resp = self.request(xblock, 'staff_assess', json.dumps(self.ASSESSMENT), response_format='json')
            self.assertFalse(resp['success'])
            self.assertIn('msg', resp)
