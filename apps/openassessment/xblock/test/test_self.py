# -*- coding: utf-8 -*-
"""
Tests for self assessment handlers in Open Assessment XBlock.
"""
import copy
import json
import mock
from openassessment.assessment import self_api
from openassessment.workflow import api as workflow_api
from .base import XBlockHandlerTestCase, scenario


class TestSelfAssessment(XBlockHandlerTestCase):

    maxDiff = None

    SUBMISSION = u'ՇﻉรՇ รપ๒๓ٱรรٱѻก'

    ASSESSMENT = {
        'submission_uuid': None,
        'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
    }

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_self_assess_handler(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        # Submit a self-assessment
        assessment = copy.deepcopy(self.ASSESSMENT)
        assessment['submission_uuid'] = submission['uuid']
        resp = self.request(xblock, 'self_assess', json.dumps(assessment), response_format='json')
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
    def test_self_assess_updates_workflow(self, xblock):

        # Create a submission for the student
        student_item = xblock.get_student_item_dict()
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        with mock.patch('openassessment.xblock.workflow_mixin.workflow_api') as mock_api:

            # Submit a self-assessment
            assessment = copy.deepcopy(self.ASSESSMENT)
            assessment['submission_uuid'] = submission['uuid']
            resp = self.request(xblock, 'self_assess', json.dumps(assessment), response_format='json')

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
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        with mock.patch('openassessment.xblock.workflow_mixin.workflow_api') as mock_api:

            # Simulate a workflow error
            mock_api.update_from_assessments.side_effect = workflow_api.AssessmentWorkflowError

            # Submit a self-assessment
            assessment = copy.deepcopy(self.ASSESSMENT)
            assessment['submission_uuid'] = submission['uuid']
            resp = self.request(xblock, 'self_assess', json.dumps(assessment), response_format='json')

            # Verify that the we get an error response
            self.assertFalse(resp['success'])
            self.assertIn('workflow', resp['msg'].lower())


    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_self_assess_handler_missing_keys(self, xblock):
        # Missing submission_uuid
        assessment = copy.deepcopy(self.ASSESSMENT)
        del assessment['submission_uuid']
        resp = self.request(xblock, 'self_assess', json.dumps(assessment), response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn('submission_uuid', resp['msg'])

        # Missing options_selected
        assessment = copy.deepcopy(self.ASSESSMENT)
        del assessment['options_selected']
        resp = self.request(xblock, 'self_assess', json.dumps(assessment), response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn('options_selected', resp['msg'])

    # No user specified, to simulate the Studio preview runtime
    @scenario('data/self_assessment_scenario.xml')
    def test_render_self_assessment_preview(self, xblock):
        resp = self.request(xblock, 'render_self_assessment', json.dumps(dict()))
        self.assertIn("Unavailable", resp)

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_render_self_assessment_complete(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        # Self-assess the submission
        assessment = copy.deepcopy(self.ASSESSMENT)
        assessment['submission_uuid'] = submission['uuid']
        resp = self.request(xblock, 'self_assess', json.dumps(assessment), response_format='json')
        self.assertTrue(resp['success'])

        # Expect that the self assessment shows that we've completed the step
        resp = self.request(xblock, 'render_self_assessment', json.dumps(dict()))
        self.assertIn("Complete", resp)

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_render_self_assessment_open(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = xblock.create_submission(student_item, self.SUBMISSION)
        with mock.patch('openassessment.assessment.peer_api.is_complete') as mock_complete:
            mock_complete.return_value = True
            # Expect that the self-assessment step is open
            resp = self.request(xblock, 'render_self_assessment', json.dumps(dict()))
            self.assertIn("Not Completed", resp)

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_render_self_assessment_no_submission(self, xblock):
        # Without creating a submission, render the self-assessment step
        # Expect that the step is closed
        resp = self.request(xblock, 'render_self_assessment', json.dumps(dict()))
        self.assertIn("Unavailable", resp)

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_render_self_assessessment_api_error(self, xblock):
        # Create a submission for the student
        student_item = xblock.get_student_item_dict()
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        # Simulate an error and expect a failure response
        with mock.patch('openassessment.xblock.self_assessment_mixin.self_api') as mock_api:
            mock_api.SelfAssessmentRequestError = self_api.SelfAssessmentRequestError
            mock_api.get_assessment.side_effect = self_api.SelfAssessmentRequestError
            resp = self.request(xblock, 'render_self_assessment', json.dumps(dict()))
        self.assertIn("error", resp.lower())

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_self_assess_api_error(self, xblock):
        # Create a submission for the student
        student_item = xblock.get_student_item_dict()
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        # Submit a self-assessment
        assessment = copy.deepcopy(self.ASSESSMENT)
        assessment['submission_uuid'] = submission['uuid']

        # Simulate an error and expect a failure response
        with mock.patch('openassessment.xblock.self_assessment_mixin.self_api') as mock_api:
            mock_api.SelfAssessmentRequestError = self_api.SelfAssessmentRequestError
            mock_api.create_assessment.side_effect = self_api.SelfAssessmentRequestError
            resp = self.request(xblock, 'self_assess', json.dumps(assessment), response_format='json')

        self.assertFalse(resp['success'])
