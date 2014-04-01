# -*- coding: utf-8 -*-
"""
Tests for peer assessment handlers in Open Assessment XBlock.
"""
from collections import namedtuple

import copy
import json
import mock
import submissions.api as sub_api
from openassessment.workflow import api as workflow_api
from openassessment.assessment import peer_api
from .base import XBlockHandlerTestCase, scenario


class TestPeerAssessment(XBlockHandlerTestCase):

    ASSESSMENT = {
        'submission_uuid': None,
        'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
        'feedback': u'єאςєɭɭєภՇ ฬ๏гк!',
    }

    SUBMISSION = u'ՇﻉรՇ รપ๒๓ٱรรٱѻก'

    @scenario('data/over_grade_scenario.xml', user_id='Bob')
    def test_load_peer_student_view_with_dates(self, xblock):
        student_item = xblock.get_student_item_dict()

        sally_student_item = copy.deepcopy(student_item)
        sally_student_item['student_id'] = "Sally"
        sally_submission = xblock.create_submission(sally_student_item, u"Sally's answer")

        # Hal comes and submits a response.
        hal_student_item = copy.deepcopy(student_item)
        hal_student_item['student_id'] = "Hal"
        hal_submission = xblock.create_submission(hal_student_item, u"Hal's answer")

        # Now Hal will assess Sally.
        assessment = copy.deepcopy(self.ASSESSMENT)
        sub = peer_api.get_submission_to_assess(hal_student_item, 1)
        assessment['submission_uuid'] = sub['uuid']
        peer_api.create_assessment(
            sub['uuid'],
            hal_student_item['student_id'],
            assessment,
            {'criteria': xblock.rubric_criteria},
            1
        )

        # Now Sally will assess Hal.
        assessment = copy.deepcopy(self.ASSESSMENT)
        sub = peer_api.get_submission_to_assess(sally_student_item, 1)
        assessment['submission_uuid'] = sub['uuid']
        peer_api.create_assessment(
            sub['uuid'],
            sally_student_item['student_id'],
            assessment,
            {'criteria': xblock.rubric_criteria},
            1
        )

        # If Over Grading is on, this should now return Sally or Hal's response
        # to Bob.
        submission = xblock.create_submission(student_item, u"Bob's answer")
        workflow_info = xblock.get_workflow_info()
        self.assertEqual(workflow_info["status"], u'peer')

        # Validate Submission Rendering.
        request = namedtuple('Request', 'params')
        request.params = {}
        peer_response = xblock.render_peer_assessment(request)
        self.assertIsNotNone(peer_response)
        self.assertNotIn(submission["answer"]["text"].encode('utf-8'), peer_response.body)

        #Validate Peer Rendering.
        self.assertTrue("Sally".encode('utf-8') in peer_response.body or
            "Hal".encode('utf-8') in peer_response.body)

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_assess_handler(self, xblock):

        # Create a submission for this problem from another user
        student_item = xblock.get_student_item_dict()
        student_item['student_id'] = 'Sally'

        submission = xblock.create_submission(student_item, self.SUBMISSION)

        # Create a submission for the scorer (required before assessing another student)
        another_student = copy.deepcopy(student_item)
        another_student['student_id'] = "Bob"
        xblock.create_submission(another_student, self.SUBMISSION)
        peer_api.get_submission_to_assess(another_student, 3)


        # Submit an assessment and expect a successful response
        assessment = copy.deepcopy(self.ASSESSMENT)
        assessment['submission_uuid'] = submission['uuid']
        resp = self.request(xblock, 'peer_assess', json.dumps(assessment), response_format='json')
        self.assertTrue(resp['success'])

        # Retrieve the assessment and check that it matches what we sent
        actual = peer_api.get_assessments(submission['uuid'], scored_only=False)
        self.assertEqual(len(actual), 1)
        self.assertEqual(actual[0]['submission_uuid'], assessment['submission_uuid'])
        self.assertEqual(actual[0]['points_earned'], 5)
        self.assertEqual(actual[0]['points_possible'], 6)
        self.assertEqual(actual[0]['scorer_id'], 'Bob')
        self.assertEqual(actual[0]['score_type'], 'PE')

        self.assertEqual(len(actual[0]['parts']), 2)
        parts = sorted(actual[0]['parts'])
        self.assertEqual(parts[0]['option']['criterion']['name'], u'Form')
        self.assertEqual(parts[0]['option']['name'], 'Fair')
        self.assertEqual(parts[1]['option']['criterion']['name'], u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮')
        self.assertEqual(parts[1]['option']['name'], u'ﻉซƈﻉɭɭﻉกՇ')

        self.assertEqual(actual[0]['feedback'], assessment['feedback'])

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_assess_rubric_option_mismatch(self, xblock):

        # Create a submission for this problem from another user
        student_item = xblock.get_student_item_dict()
        student_item['student_id'] = 'Sally'
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        # Create a submission for the scorer (required before assessing another student)
        another_student = copy.deepcopy(student_item)
        another_student['student_id'] = "Bob"
        xblock.create_submission(another_student, self.SUBMISSION)

        # Submit an assessment, but mutate the options selected so they do NOT match the rubric
        assessment = copy.deepcopy(self.ASSESSMENT)
        assessment['submission_uuid'] = submission['uuid']
        assessment['options_selected']['invalid'] = 'not a part of the rubric!'
        resp = self.request(xblock, 'peer_assess', json.dumps(assessment), response_format='json')

        # Expect an error response
        self.assertFalse(resp['success'])

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_missing_keys_in_request(self, xblock):
        for missing in ['feedback', 'submission_uuid', 'options_selected']:
            assessment = copy.deepcopy(self.ASSESSMENT)
            del assessment[missing]
            resp = self.request(xblock, 'peer_assess', json.dumps(assessment), response_format='json')
            self.assertEqual(resp['success'], False)

    @scenario('data/assessment_not_started.xml', user_id='Bob')
    def test_start_dates(self, xblock):
        student_item = xblock.get_student_item_dict()

        submission = xblock.create_submission(student_item, u"Bob's answer")
        workflow_info = xblock.get_workflow_info()
        self.assertEqual(workflow_info["status"], u'peer')

        # Validate Submission Rendering.
        request = namedtuple('Request', 'params')
        request.params = {}
        peer_response = xblock.render_peer_assessment(request)
        self.assertIsNotNone(peer_response)
        self.assertNotIn(submission["answer"]["text"].encode('utf-8'), peer_response.body)

        # Validate Peer Rendering.
        self.assertIn("available".encode('utf-8'), peer_response.body)
        
    @scenario('data/over_grade_scenario.xml', user_id='Bob')
    def test_turbo_grading(self, xblock):
        student_item = xblock.get_student_item_dict()

        sally_student_item = copy.deepcopy(student_item)
        sally_student_item['student_id'] = "Sally"
        sally_submission = xblock.create_submission(sally_student_item, u"Sally's answer")

        # Hal comes and submits a response.
        hal_student_item = copy.deepcopy(student_item)
        hal_student_item['student_id'] = "Hal"
        hal_submission = xblock.create_submission(hal_student_item, u"Hal's answer")

        # Now Hal will assess Sally.
        assessment = copy.deepcopy(self.ASSESSMENT)
        sally_sub = peer_api.get_submission_to_assess(hal_student_item, 1)
        assessment['submission_uuid'] = sally_sub['uuid']
        peer_api.create_assessment(
            sally_sub['uuid'],
            hal_student_item['student_id'],
            assessment,
            {'criteria': xblock.rubric_criteria},
            1
        )

        # Now Sally will assess Hal.
        assessment = copy.deepcopy(self.ASSESSMENT)
        hal_sub = peer_api.get_submission_to_assess(sally_student_item, 1)
        assessment['submission_uuid'] = hal_sub['uuid']
        peer_api.create_assessment(
            hal_sub['uuid'],
            sally_student_item['student_id'],
            assessment,
            {'criteria': xblock.rubric_criteria},
            1
        )

        # If Over Grading is on, this should now return Sally's response to Bob.
        submission = xblock.create_submission(student_item, u"Bob's answer")
        workflow_info = xblock.get_workflow_info()
        self.assertEqual(workflow_info["status"], u'peer')

        # Validate Submission Rendering.
        request = namedtuple('Request', 'params')
        request.params = {'continue_grading': True}
        peer_response = xblock.render_peer_assessment(request)
        self.assertIsNotNone(peer_response)
        self.assertNotIn(submission["answer"]["text"].encode('utf-8'), peer_response.body)

        hal_response = "Hal".encode('utf-8') in peer_response.body
        sally_response = "Sally".encode('utf-8') in peer_response.body

        # Validate Peer Rendering.
        if hal_response:
            peer_uuid = hal_sub['uuid']
        elif sally_response:
            peer_uuid = sally_sub['uuid']
        else:
            self.fail("Response was neither Hal or Sally's submission.")

        peer_api.create_assessment(
            peer_uuid,
            student_item['student_id'],
            assessment,
            {'criteria': xblock.rubric_criteria},
            1
        )

        # Validate Submission Rendering.
        request = namedtuple('Request', 'params')
        request.params = {'continue_grading': True}
        peer_response = xblock.render_peer_assessment(request)
        self.assertIsNotNone(peer_response)
        self.assertNotIn(submission["answer"]["text"].encode('utf-8'), peer_response.body)

        # Validate Peer Rendering. Check that if Sally or Hal were selected
        # the first time around, the other is selected this time.
        if not hal_response and "Hal".encode('utf-8') in peer_response.body:
            peer_uuid = hal_sub['uuid']
        elif not sally_response and "Sally".encode('utf-8') in peer_response.body:
            peer_uuid = sally_sub['uuid']
        else:
            self.fail("Response was neither Hal or Sally's submission.")

        peer_api.create_assessment(
            peer_uuid,
            student_item['student_id'],
            assessment,
            {'criteria': xblock.rubric_criteria},
            1
        )

        # A Final over grading will not return anything.
        request = namedtuple('Request', 'params')
        request.params = {'continue_grading': True}
        peer_response = xblock.render_peer_assessment(request)
        self.assertIsNotNone(peer_response)
        self.assertNotIn(submission["answer"]["text"].encode('utf-8'), peer_response.body)
        self.assertIn("Complete".encode('utf-8'), peer_response.body)