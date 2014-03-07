# -*- coding: utf-8 -*-
"""
Tests for self assessment handlers in Open Assessment XBlock.
"""
import copy
import json
import mock
from submissions import api as submission_api
from openassessment.assessment import self_api
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
        submission = submission_api.create_submission(student_item, self.SUBMISSION)

        # Submit a self-assessment
        assessment = copy.deepcopy(self.ASSESSMENT)
        assessment['submission_uuid'] = submission['uuid']
        resp = self.request(xblock, 'self_assess', json.dumps(assessment), response_format='json')
        self.assertTrue(resp['success'])

        # Expect that a self-assessment was created
        _, assessment = self_api.get_submission_and_assessment(student_item)
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
        self.assertIn("Incomplete", resp)

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_render_self_assessment_complete(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = submission_api.create_submission(student_item, self.SUBMISSION)

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
        submission = submission_api.create_submission(student_item, self.SUBMISSION)

        # Expect that the self-assessment step is open
        resp = self.request(xblock, 'render_self_assessment', json.dumps(dict()))
        self.assertIn("Grading", resp)

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_render_self_assessment_no_submission(self, xblock):
        # Without creating a submission, render the self-assessment step
        # Expect that the step is closed
        resp = self.request(xblock, 'render_self_assessment', json.dumps(dict()))
        self.assertIn("Incomplete", resp)

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_render_self_assessessment_api_error(self, xblock):
        # Create a submission for the student
        student_item = xblock.get_student_item_dict()
        submission = submission_api.create_submission(student_item, self.SUBMISSION)

        # Simulate an error and expect a failure response
        with mock.patch('openassessment.xblock.self_assessment_mixin.self_api') as mock_api:
            mock_api.SelfAssessmentRequestError = self_api.SelfAssessmentRequestError
            mock_api.get_submission_and_assessment.side_effect = self_api.SelfAssessmentRequestError
            resp = self.request(xblock, 'render_self_assessment', json.dumps(dict()))
        self.assertIn("error", resp.lower())

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_self_assess_api_error(self, xblock):
        # Create a submission for the student
        student_item = xblock.get_student_item_dict()
        submission = submission_api.create_submission(student_item, self.SUBMISSION)

        # Submit a self-assessment
        assessment = copy.deepcopy(self.ASSESSMENT)
        assessment['submission_uuid'] = submission['uuid']

        # Simulate an error and expect a failure response
        with mock.patch('openassessment.xblock.self_assessment_mixin.self_api') as mock_api:
            mock_api.SelfAssessmentRequestError = self_api.SelfAssessmentRequestError
            mock_api.create_assessment.side_effect = self_api.SelfAssessmentRequestError
            resp = self.request(xblock, 'self_assess', json.dumps(assessment), response_format='json')

        self.assertFalse(resp['success'])
