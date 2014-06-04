# -*- coding: utf-8 -*-
"""
Tests for self assessment handlers in Open Assessment XBlock.
"""
import copy
import json
import datetime
import mock
import pytz
from openassessment.assessment.api import self as self_api
from openassessment.workflow import api as workflow_api
from .base import XBlockHandlerTestCase, scenario


class TestSelfAssessment(XBlockHandlerTestCase):
    """
    Tests for the self-assessment XBlock handler.
    """

    maxDiff = None

    SUBMISSION = u'ՇﻉรՇ รપ๒๓ٱรรٱѻก'

    ASSESSMENT = {
        'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
    }

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_self_assess_handler(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        # Submit a self-assessment
        resp = self.request(xblock, 'self_assess', json.dumps(self.ASSESSMENT), response_format='json')
        self.assertTrue(resp['success'])

        # Expect that a self-assessment was created
        assessment = self_api.get_assessment(submission["uuid"])
        self.assertEqual(assessment['submission_uuid'], submission['uuid'])
        self.assertEqual(assessment['points_earned'], 5)
        self.assertEqual(assessment['points_possible'], 6)
        self.assertEqual(assessment['scorer_id'], 'Bob')
        self.assertEqual(assessment['score_type'], 'SE')
        self.assertEqual(assessment['feedback'], u'')

        parts = sorted(assessment['parts'])
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0]['option']['criterion']['name'], u'Form')
        self.assertEqual(parts[0]['option']['name'], 'Fair')
        self.assertEqual(parts[1]['option']['criterion']['name'], u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮')
        self.assertEqual(parts[1]['option']['name'], u'ﻉซƈﻉɭɭﻉกՇ')

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_self_assess_no_submission(self, xblock):
        # Submit a self-assessment without first creating a submission
        resp = self.request(xblock, 'self_assess', json.dumps(self.ASSESSMENT), response_format='json')
        self.assertFalse(resp['success'])
        self.assertGreater(len(resp['msg']), 0)

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_self_assess_updates_workflow(self, xblock):

        # Create a submission for the student
        student_item = xblock.get_student_item_dict()
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        with mock.patch('openassessment.xblock.workflow_mixin.workflow_api') as mock_api:

            # Submit a self-assessment
            resp = self.request(xblock, 'self_assess', json.dumps(self.ASSESSMENT), response_format='json')

            # Verify that the workflow is updated when we submit a self-assessment
            self.assertTrue(resp['success'])
            expected_reqs = {
                "peer": { "must_grade": 5, "must_be_graded_by": 3 }
            }
            mock_api.update_from_assessments.assert_called_once_with(submission['uuid'], expected_reqs)

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_self_assess_workflow_error(self, xblock):
        # Create a submission for the student
        student_item = xblock.get_student_item_dict()
        xblock.create_submission(student_item, self.SUBMISSION)

        with mock.patch('openassessment.xblock.workflow_mixin.workflow_api') as mock_api:

            # Simulate a workflow error
            mock_api.update_from_assessments.side_effect = workflow_api.AssessmentWorkflowInternalError

            # Submit a self-assessment
            resp = self.request(xblock, 'self_assess', json.dumps(self.ASSESSMENT), response_format='json')

            # Verify that the we get an error response
            self.assertFalse(resp['success'])

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_self_assess_handler_missing_keys(self, xblock):
        # Missing options_selected
        assessment = copy.deepcopy(self.ASSESSMENT)
        del assessment['options_selected']
        resp = self.request(xblock, 'self_assess', json.dumps(assessment), response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn('options_selected', resp['msg'])

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_self_assess_api_error(self, xblock):
        # Create a submission for the student
        student_item = xblock.get_student_item_dict()
        xblock.create_submission(student_item, self.SUBMISSION)

        # Submit a self-assessment
        # Simulate an error and expect a failure response
        with mock.patch('openassessment.xblock.self_assessment_mixin.self_api') as mock_api:
            mock_api.SelfAssessmentRequestError = self_api.SelfAssessmentRequestError
            mock_api.create_assessment.side_effect = self_api.SelfAssessmentRequestError
            resp = self.request(xblock, 'self_assess', json.dumps(self.ASSESSMENT), response_format='json')

        self.assertFalse(resp['success'])


class TestSelfAssessmentRender(XBlockHandlerTestCase):
    """
    Test rendering of the self-assessment step.
    The basic strategy is to verify that we're providing the right
    template and context for each possible state,
    plus an integration test to verify that the context
    is being rendered correctly.
    """

    @scenario('data/self_assessment_unavailable.xml', user_id='Bob')
    def test_unavailable(self, xblock):
        # Start date is in the future for this scenario
        self._assert_path_and_context(
            xblock,
            'openassessmentblock/self/oa_self_unavailable.html',
            {'self_start': datetime.datetime(5999, 1, 1).replace(tzinfo=pytz.utc)}
        )

    @scenario('data/self_assessment_closed.xml', user_id='Bob')
    def test_closed(self, xblock):
        # Due date is in the past for this scenario
        self._assert_path_and_context(
            xblock,
            'openassessmentblock/self/oa_self_closed.html',
            {'self_due': datetime.datetime(2000, 1, 1).replace(tzinfo=pytz.utc)}
        )

    @scenario('data/self_assessment_open.xml', user_id='Bob')
    def test_open_no_submission(self, xblock):
        # Without making a submission, this step should be unavailable
        self._assert_path_and_context(
            xblock, 'openassessmentblock/self/oa_self_unavailable.html', {}
        )

    @scenario('data/self_assessment_open.xml', user_id='James Brown')
    def test_open_in_peer_step(self, xblock):
        # Make a submission, so we're in the peer-assessment step
        xblock.create_submission(
            xblock.get_student_item_dict(), u"ⱣȺꝑȺ đøn'ŧ ŧȺꝁɇ nø mɇss."
        )

        # Should still not be able to access self-assessment
        self._assert_path_and_context(
            xblock, 'openassessmentblock/self/oa_self_unavailable.html', {}
        )

    @scenario('data/self_assessment_open.xml', user_id='James Brown')
    def test_open_in_waiting_for_peer_step(self, xblock):
        # Simulate the workflow status being "waiting"
        # Currently, this implies that we've completed the self assessment module,
        # but this may change in the future.
        xblock.create_submission(
            xblock.get_student_item_dict(), u"𝓟𝓪𝓼𝓼 𝓽𝓱𝓮 𝓹𝓮𝓪𝓼"
        )
        self._assert_path_and_context(
            xblock, 'openassessmentblock/self/oa_self_complete.html', {},
            workflow_status='waiting'
        )

    @scenario('data/self_assessment_open.xml', user_id='James Brown')
    def test_open_done_status(self, xblock):
        # Simulate the workflow status being "done"
        xblock.create_submission(
            xblock.get_student_item_dict(), u"Ⱥɨn'ŧ ɨŧ fᵾnꝁɏ"
        )
        self._assert_path_and_context(
            xblock, 'openassessmentblock/self/oa_self_complete.html', {},
            workflow_status='done'
        )

    @scenario('data/self_assessment_open.xml', user_id='James Brown')
    def test_open_self_assessing(self, xblock):
        # Simulate the workflow being in the self assessment step
        submission = xblock.create_submission(
            xblock.get_student_item_dict(), u"Đøɨn' ɨŧ ŧø đɇȺŧħ"
        )
        self._assert_path_and_context(
            xblock, 'openassessmentblock/self/oa_self_assessment.html',
            {
                'rubric_criteria': xblock.rubric_criteria,
                'estimated_time': '20 minutes',
                'self_submission': submission
            },
            workflow_status='self',
            submission_uuid=submission['uuid']
        )

    @scenario('data/self_assessment_open.xml', user_id='Bob')
    def test_open_completed_self_assessment(self, xblock):
        # Simulate the workflow being in the self assessment step
        # and we've created a self-assessment
        submission = xblock.create_submission(
            xblock.get_student_item_dict(), u"Đøɨn' ɨŧ ŧø đɇȺŧħ"
        )
        self_api.create_assessment(
            submission['uuid'],
            xblock.get_student_item_dict()['student_id'],
            {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
            {'criteria': xblock.rubric_criteria}
        )
        self._assert_path_and_context(
            xblock, 'openassessmentblock/self/oa_self_complete.html', {},
            workflow_status='self',
            submission_uuid=submission['uuid']
        )

    @scenario('data/self_assessment_closed.xml', user_id='Bob')
    def test_started_and_past_due(self, xblock):
        # Simulate the workflow being in the self assessment step
        # Since we're past the due date, the step should appear closed.
        submission = xblock.create_submission(
            xblock.get_student_item_dict(), u"Đøɨn' ɨŧ ŧø đɇȺŧħ"
        )
        self._assert_path_and_context(
            xblock,
            'openassessmentblock/self/oa_self_closed.html',
            {'self_due': datetime.datetime(2000, 1, 1).replace(tzinfo=pytz.utc)},
            workflow_status='self',
            submission_uuid=submission['uuid']
        )

    @scenario('data/self_assessment_closed.xml', user_id='Bob')
    def test_completed_and_past_due(self, xblock):
        # Simulate having completed self assessment
        # Even though the problem is closed, we should still see
        # that we completed the step.
        submission = xblock.create_submission(
            xblock.get_student_item_dict(), u"Đøɨn' ɨŧ ŧø đɇȺŧħ"
        )
        self_api.create_assessment(
            submission['uuid'],
            xblock.get_student_item_dict()['student_id'],
            {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
            {'criteria': xblock.rubric_criteria}
        )

        # This case probably isn't possible, because presumably when we create
        # the self-assessment, the workflow status will be "waiting" or "done".
        # We're checking it anyway to be overly defensive: if the user has made a self-assessment,
        # we ALWAYS show complete, even if the workflow tells us we're still have status 'self'.
        self._assert_path_and_context(
            xblock, 'openassessmentblock/self/oa_self_complete.html',
            {'self_due': datetime.datetime(2000, 1, 1).replace(tzinfo=pytz.utc)},
            workflow_status='self',
            submission_uuid=submission['uuid']
        )

    @scenario('data/self_assessment_open.xml', user_id='Bob')
    def test_integration(self, xblock):
        # Simulate the workflow being in the self assessment step
        # and we've created a self-assessment
        submission = xblock.create_submission(
            xblock.get_student_item_dict(), u"Test submission"
        )

        xblock.get_workflow_info = mock.Mock(return_value={
            'status': 'self', 'submission_uuid': submission['uuid']
        })

        resp = self.request(xblock, 'render_self_assessment', json.dumps({}))
        self.assertIn(u'in progress', resp.decode('utf-8').lower())
        self.assertIn(u'Test submission', resp.decode('utf-8'))

    @scenario('data/self_assessment_open.xml', user_id='Bob')
    def test_retrieve_api_error(self, xblock):
        # Simulate the workflow being in the self assessment step
        xblock.get_workflow_info = mock.Mock(return_value={'status': 'self'})

        # Simulate an error from the submission API
        with mock.patch('openassessment.xblock.self_assessment_mixin.self_api') as mock_self:
            mock_self.get_assessment.side_effect = self_api.SelfAssessmentRequestError
            resp = self.request(xblock, 'render_self_assessment', json.dumps({}))
            self.assertIn(u'error', resp.decode('utf-8').lower())

    def _assert_path_and_context(
        self, xblock, expected_path, expected_context,
        workflow_status=None, submission_uuid=None
    ):
        """
        Render the self assessment step and verify:
            1) that the correct template and context were used
            2) that the rendering occurred without an error

        Args:
            xblock (OpenAssessmentBlock): The XBlock under test.
            expected_path (str): The expected template path.
            expected_context (dict): The expected template context.

        Kwargs:
            workflow_status (str): If provided, simulate this status from the workflow API.
            submission_uuid (str): If provided, simulate this submision UUI for the current workflow.
        """
        if workflow_status is not None:
            xblock.get_workflow_info = mock.Mock(return_value={
                'status': workflow_status,
                'submission_uuid': submission_uuid
            })
        path, context = xblock.self_path_and_context()

        self.assertEqual(path, expected_path)
        self.assertItemsEqual(context, expected_context)

        # Verify that we render without error
        resp = self.request(xblock, 'render_self_assessment', json.dumps({}))
        self.assertGreater(len(resp), 0)
