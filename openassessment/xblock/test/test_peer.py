"""
Tests for peer assessment handlers in Open Assessment XBlock.
"""

import logging

from collections import namedtuple
import copy
import datetime as dt
import json
from unittest import mock

import ddt
import pytz

from openassessment.assessment.api import peer as peer_api
from openassessment.workflow import api as workflow_api
from openassessment.xblock.utils.data_conversion import create_submission_dict

from .base import SubmissionTestMixin, XBlockHandlerTestCase, scenario

logger = logging.getLogger(__name__)


class TestPeerAssessment(XBlockHandlerTestCase, SubmissionTestMixin):
    """
    Test integration of the OpenAssessment XBlock with the peer assessment API.
    """

    ASSESSMENT = {
        'options_selected': {'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': 'ﻉซƈﻉɭɭﻉกՇ', 'Form': 'Fair'},
        'criterion_feedback': {'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': 'ı ʇɥonƃɥʇ ʇɥıs ʍɐs ʌǝɹʎ ɔouɔısǝ.'},
        'overall_feedback': 'єאςєɭɭєภՇ ฬ๏гк!',
    }

    @scenario('data/over_grade_scenario.xml', user_id='Bob')
    def test_load_peer_student_view_with_dates(self, xblock):

        self._sally_and_hal_grade_each_other_helper(xblock)

        # If Over Grading is on, this should now return Sally or Hal's response to Bob.
        submission = self.create_test_submission(xblock, submission_text=("Bob's answer 1", "Bob's answer 2"))
        workflow_info = xblock.get_workflow_info()

        # peer step is skipable. So we expect next status to be current status.
        self.assertEqual(workflow_info["status"], 'self')

        # Validate Submission Rendering.
        request = namedtuple('Request', 'params')
        request.params = {}
        peer_response = xblock.render_peer_assessment(request)
        self.assertIsNotNone(peer_response)
        self.assertNotIn(submission["answer"]["parts"][0]["text"].encode('utf-8'), peer_response.body)
        self.assertNotIn(submission["answer"]["parts"][1]["text"].encode('utf-8'), peer_response.body)

        # Validate Peer Rendering.
        self.assertTrue(
            b"Sally" in peer_response.body or b"Hal" in peer_response.body
        )

    @mock.patch('openassessment.xblock.workflow_mixin.WorkflowMixin.workflow_requirements')
    @scenario('data/peer_assessment_scenario.xml', user_id='Sally')
    def test_requirements_changed(self, xblock, mock_requirements):
        """
        Test to verify that if requirements change, student workflows are immediately updated to
        reflect their done status with regards to the new requirements.
        """
        # Setup the peer grading scenario, using the default requirements
        self._sally_and_hal_grade_each_other_helper(xblock)

        # Verify that Sally's workflow is not marked done, as the requirements are higher than 1.
        mock_requirements.return_value = {"peer": {"must_grade": 2, "must_be_graded_by": 2}}
        workflow_info = xblock.get_workflow_info()

        # peer step is skipable. So we expect next status to be current status.
        self.assertEqual(workflow_info["status"], 'self')

        # Now, change the requirements and verify that Sally's workflow updates to 'self' status.
        mock_requirements.return_value = {"peer": {"must_grade": 1, "must_be_graded_by": 1}}
        workflow_info = xblock.get_workflow_info()
        self.assertEqual(workflow_info["status"], 'self')

    def _sally_and_hal_grade_each_other_helper(self, xblock):
        """
        A helper method to set up 2 submissions, one for each of Sally and Hal, and then have each assess the other.
        """
        student_item = xblock.get_student_item_dict()

        # Sally submits a response.
        sally_student_item = copy.deepcopy(student_item)
        sally_student_item["student_id"] = "Sally"
        sally_submission = self.create_test_submission(
            xblock, student_item=sally_student_item, submission_text=("Sally's answer 1", "Sally's answer 2")
        )

        # Hal comes and submits a response.
        hal_student_item = copy.deepcopy(student_item)
        hal_student_item["student_id"] = "Hal"
        hal_submission = self.create_test_submission(
            xblock, student_item=hal_student_item, submission_text=("Hal's answer 1", "Hal's answer 2")
        )

        # Now Hal will assess Sally.
        assessment = copy.deepcopy(self.ASSESSMENT)
        peer_api.get_submission_to_assess(hal_submission['uuid'], 1)
        peer_api.create_assessment(
            hal_submission['uuid'],
            hal_student_item['student_id'],
            assessment['options_selected'],
            assessment['criterion_feedback'],
            assessment['overall_feedback'],
            {'criteria': xblock.rubric_criteria},
            1
        )

        # Now Sally will assess Hal.
        assessment = copy.deepcopy(self.ASSESSMENT)
        peer_api.get_submission_to_assess(sally_submission['uuid'], 1)
        peer_api.create_assessment(
            sally_submission['uuid'],
            sally_student_item['student_id'],
            assessment['options_selected'],
            assessment['criterion_feedback'],
            assessment['overall_feedback'],
            {'criteria': xblock.rubric_criteria},
            1
        )

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_assess_before_submission(self, xblock):
        # Submit a peer assessment without a submission
        resp = self.request(xblock, 'peer_assess', json.dumps(self.ASSESSMENT), response_format='json')
        self.assertEqual(resp['success'], False)
        self.assertGreater(len(resp['msg']), 0)

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_assess_without_leasing_submission(self, xblock):
        # Create a submission
        self.create_test_submission(xblock)

        # Attempt to assess a peer without first leasing their submission
        # (usually occurs by rendering the peer assessment step)
        resp = self.request(xblock, 'peer_assess', json.dumps(self.ASSESSMENT), response_format='json')
        self.assertEqual(resp['success'], False)
        self.assertGreater(len(resp['msg']), 0)

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_assess_for_already_cancelled_submission(self, xblock):
        # Create a submission for this problem from another user
        student_item = xblock.get_student_item_dict()
        submission = self.create_test_submission(xblock, student_item=student_item)

        # Create a submission for the scorer (required before assessing another student)
        another_student = copy.deepcopy(student_item)
        another_submission = self.create_test_submission(xblock, student_item=another_student)

        assessment = self.ASSESSMENT
        assessment['submission_uuid'] = assessment.get('submission_uuid', submission.get('uuid', None))

        # Pull the submission to assess
        peer_api.get_submission_to_assess(another_submission['uuid'], 3)
        requirements = {
            "peer": {
                "must_grade": 1,
                "must_be_graded_by": 1
            },
        }

        workflow_api.cancel_workflow(
            submission_uuid=submission['uuid'],
            comments="Inappropriate language",
            cancelled_by_id=another_student['student_id'],
            assessment_requirements=requirements,
            course_settings={}
        )

        # Submit an assessment and expect a failure
        resp = self.request(xblock, 'peer_assess', json.dumps(assessment), response_format='json')

        self.assertEqual(resp['success'], False)
        self.assertGreater(len(resp['msg']), 0)

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_missing_keys_in_request(self, xblock):
        for missing in ['criterion_feedback', 'overall_feedback', 'options_selected']:
            assessment = copy.deepcopy(self.ASSESSMENT)
            del assessment[missing]
            resp = self.request(xblock, 'peer_assess', json.dumps(assessment), response_format='json')
            self.assertEqual(resp['success'], False)

    @scenario('data/assessment_not_started.xml', user_id='Bob')
    def test_start_dates(self, xblock):
        submission = self.create_test_submission(xblock)
        workflow_info = xblock.get_workflow_info()

        # peer step is skipable. So we expect next status to be current status.
        self.assertEqual(workflow_info["status"], 'self')

        # Validate Submission Rendering.
        request = namedtuple('Request', 'params')
        request.params = {}
        peer_response = xblock.render_peer_assessment(request)
        self.assertIsNotNone(peer_response)
        self.assertNotIn(submission["answer"]["parts"][0]["text"].encode('utf-8'), peer_response.body)
        self.assertNotIn(submission["answer"]["parts"][1]["text"].encode('utf-8'), peer_response.body)

        # Validate Peer Rendering.
        self.assertIn(b"available", peer_response.body)

    @scenario('data/over_grade_scenario.xml', user_id='Bob')
    def test_turbo_grading(self, xblock):
        student_item = xblock.get_student_item_dict()

        sally_student_item = copy.deepcopy(student_item)
        sally_student_item['student_id'] = "Sally"
        sally_submission = self.create_test_submission(
            xblock, student_item=sally_student_item, submission_text=("Sally's answer 1", "Sally's answer 2")
        )

        # Hal comes and submits a response.
        hal_student_item = copy.deepcopy(student_item)
        hal_student_item['student_id'] = "Hal"
        hal_submission = self.create_test_submission(
            xblock, student_item=hal_student_item, submission_text=("Hal's answer 1", "Hal's answer 2")
        )

        # Now Hal will assess Sally.
        assessment = copy.deepcopy(self.ASSESSMENT)
        sally_sub = peer_api.get_submission_to_assess(hal_submission['uuid'], 1)
        assessment['submission_uuid'] = sally_sub['uuid']
        peer_api.create_assessment(
            hal_submission['uuid'],
            hal_student_item['student_id'],
            assessment['options_selected'],
            assessment['criterion_feedback'],
            assessment['overall_feedback'],
            {'criteria': xblock.rubric_criteria},
            1
        )

        # Now Sally will assess Hal.
        assessment = copy.deepcopy(self.ASSESSMENT)
        hal_sub = peer_api.get_submission_to_assess(sally_submission['uuid'], 1)
        assessment['submission_uuid'] = hal_sub['uuid']
        peer_api.create_assessment(
            sally_submission['uuid'],
            sally_student_item['student_id'],
            assessment['options_selected'],
            assessment['criterion_feedback'],
            assessment['overall_feedback'],
            {'criteria': xblock.rubric_criteria},
            1
        )

        # If Over Grading is on, this should now return Sally's response to Bob.
        submission = self.create_test_submission(xblock, student_item=student_item)
        workflow_info = xblock.get_workflow_info()

        # peer step is skipable. So we expect next status to be current status.
        self.assertEqual(workflow_info["status"], 'self')

        # Validate Submission Rendering.
        request = namedtuple('Request', 'params')
        request.params = {'continue_grading': True}
        peer_response = xblock.render_peer_assessment(request)
        self.assertIsNotNone(peer_response)
        self.assertNotIn(submission["answer"]["parts"][0]["text"].encode('utf-8'), peer_response.body)
        self.assertNotIn(submission["answer"]["parts"][1]["text"].encode('utf-8'), peer_response.body)

        peer_api.create_assessment(
            submission['uuid'],
            student_item['student_id'],
            assessment['options_selected'],
            assessment['criterion_feedback'],
            assessment['overall_feedback'],
            {'criteria': xblock.rubric_criteria},
            1
        )

        # Validate Submission Rendering.
        request = namedtuple('Request', 'params')
        request.params = {'continue_grading': True}
        peer_response = xblock.render_peer_assessment(request)
        self.assertIsNotNone(peer_response)
        self.assertNotIn(submission["answer"]["parts"][0]["text"], peer_response.body.decode('utf-8'))
        self.assertNotIn(submission["answer"]["parts"][1]["text"], peer_response.body.decode('utf-8'))

        peer_api.create_assessment(
            submission['uuid'],
            student_item['student_id'],
            assessment['options_selected'],
            assessment['criterion_feedback'],
            assessment['overall_feedback'],
            {'criteria': xblock.rubric_criteria},
            1
        )

        # A Final over grading will not return anything.
        request = namedtuple('Request', 'params')
        request.params = {'continue_grading': True}
        peer_response = xblock.render_peer_assessment(request)
        self.assertIsNotNone(peer_response)
        self.assertNotIn(submission["answer"]["parts"][0]["text"], peer_response.body.decode('utf-8'))
        self.assertNotIn(submission["answer"]["parts"][1]["text"], peer_response.body.decode('utf-8'))
        self.assertIn("You have successfully completed", peer_response.body.decode('utf-8'))


@ddt.ddt
class TestPeerAssessmentRender(XBlockHandlerTestCase, SubmissionTestMixin):
    """
    Test rendering of the peer assessment step.
    The basic strategy is to verify that we're providing the right
    template and context for each possible state,
    plus an integration test to verify that the context
    is being rendered correctly.
    """

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_released_no_submission(self, xblock):
        # No submission, so the peer step should be unavailable
        expected_context = {
            'graded': 0,
            'submit_button_text': 'Submit your assessment & move to response #2',
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': pytz.utc,
            'user_language': 'en'
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_unavailable.html', expected_context
        )

    @scenario('data/peer_closed_scenario.xml', user_id='Bob')
    def test_closed_no_submission(self, xblock):
        expected_context = {
            'peer_due': dt.datetime(2000, 1, 1).replace(tzinfo=pytz.utc),
            'graded': 0,
            'submit_button_text': 'Submit your assessment & move to response #2',
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': pytz.utc,
            'user_language': 'en'
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_closed.html', expected_context
        )

    @scenario('data/peer_future_scenario.xml', user_id='Bob')
    def test_before_release(self, xblock):
        expected_context = {
            'peer_start': dt.datetime(2999, 1, 1).replace(tzinfo=pytz.utc),
            'graded': 0,
            'submit_button_text': 'Submit your assessment & move to response #2',
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': pytz.utc,
            'user_language': 'en'
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_unavailable.html', expected_context
        )

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_waiting_for_peers(self, xblock):
        # Make a submission, but no peer assessments available
        self.create_test_submission(xblock)

        # Expect to be in the waiting for peers state
        expected_context = {
            'graded': 0,
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'submit_button_text': 'submit your assessment & move to response #2',
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': pytz.utc,
            'user_language': 'en'
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_waiting.html',
            expected_context,
            workflow_status='peer',
            graded_enough=False,
            was_graded_enough=False,
        )

    @scenario('data/peer_assessment_scenario.xml', user_id='Richard')
    def test_peer_assessment_available(self, xblock):
        # Make a submission, so we get to peer assessment
        self.create_test_submission(xblock)

        # Create a submission from another user so we have something to assess
        other_student = copy.deepcopy(xblock.get_student_item_dict())
        other_student['student_id'] = 'Tyler'
        submission = self.create_test_submission(xblock, student_item=other_student)

        # We should pull the other student's submission
        expected_context = {
            'graded': 0,
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'peer_submission': create_submission_dict(submission, xblock.prompts),
            'file_upload_type': None,
            'peer_file_urls': [],
            'submit_button_text': 'submit your assessment & move to response #2',
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': pytz.utc,
            'user_language': 'en'
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_assessment.html',
            expected_context,
            workflow_status='peer',
        )

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_cancelled_workflow(self, xblock):
        # Make a submission, so we get to peer assessment
        self.create_test_submission(xblock)

        expected_context = {
            'graded': 0,
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'submit_button_text': 'submit your assessment & move to response #2',
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': pytz.utc,
            'user_language': 'en'
        }

        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_cancelled.html',
            expected_context,
            workflow_status='cancelled',
            graded_enough=True,
        )

    @scenario('data/peer_closed_scenario.xml', user_id='Bob')
    def test_peer_closed_no_assessments_available(self, xblock):
        # Make a submission, so we get to peer assessment
        self.create_test_submission(xblock)

        # No assessments are available, and the step has closed
        expected_context = {
            'peer_due': dt.datetime(2000, 1, 1).replace(tzinfo=pytz.utc),
            'graded': 0,
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'submit_button_text': 'submit your assessment & move to response #2',
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': pytz.utc,
            'user_language': 'en'
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_closed.html',
            expected_context,
            workflow_status='peer',
        )

    @scenario('data/peer_closed_scenario.xml', user_id='Richard')
    def test_peer_closed_assessments_available(self, xblock):
        # Make a submission, so we get to peer assessment
        self.create_test_submission(xblock)

        # Create a submission from another user so we have something to assess
        other_student = copy.deepcopy(xblock.get_student_item_dict())
        other_student['student_id'] = 'Tyler'
        self.create_test_submission(xblock, student_item=other_student)

        # ... but the problem is closed, so we can't assess them
        expected_context = {
            'peer_due': dt.datetime(2000, 1, 1).replace(tzinfo=pytz.utc),
            'graded': 0,
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'submit_button_text': 'submit your assessment & move to response #2',
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': pytz.utc,
            'user_language': 'en'
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_closed.html',
            expected_context,
            workflow_status='peer',
        )

    @ddt.data('self', 'waiting', 'done')
    @scenario('data/peer_closed_scenario.xml', user_id='Tyler')
    def test_completed_and_past_due(self, xblock, workflow_status):
        # Simulate having complete peer-assessment
        # Even though the problem is closed, we should still see
        # that the step is complete.
        self.create_test_submission(xblock)

        # Simulate a workflow status of "done" and expect to see the "completed" step
        expected_context = {
            'peer_due': dt.datetime(2000, 1, 1).replace(tzinfo=pytz.utc),
            'graded': 0,
            'submit_button_text': 'submit your assessment & move to response #2',
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': pytz.utc,
            'user_language': 'en'
        }

        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_complete.html',
            expected_context,
            workflow_status=workflow_status,
            graded_enough=True,
            was_graded_enough=True,
        )

    @ddt.data('self', 'done')
    @scenario('data/peer_closed_scenario.xml', user_id='Marla')
    def test_turbo_grade_past_due(self, xblock, workflow_status):
        self.create_test_submission(xblock)

        # Try to continue grading after the due date has passed
        # Continued grading should still be available,
        # but since there are no other submissions, we're in the waiting state.
        expected_context = {
            'graded': 0,
            'must_grade': 5,
            'peer_due': dt.datetime(2000, 1, 1).replace(tzinfo=pytz.utc),
            'review_num': 1,
            'rubric_criteria': xblock.rubric_criteria,
            'submit_button_text': 'Submit your assessment & review another response',
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': pytz.utc,
            'user_language': 'en'
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_turbo_mode_waiting.html',
            expected_context,
            continue_grading=True,
            workflow_status=workflow_status,
            graded_enough=True,
            was_graded_enough=True,
        )

        # Create a submission from another student.
        # We should now be able to continue grading that submission
        other_student_item = copy.deepcopy(xblock.get_student_item_dict())
        other_student_item['student_id'] = "Tyler"
        submission = self.create_test_submission(xblock, student_item=other_student_item)

        expected_context = {
            'graded': 0,
            'must_grade': 5,
            'peer_due': dt.datetime(2000, 1, 1).replace(tzinfo=pytz.utc),
            'peer_submission': create_submission_dict(submission, xblock.prompts),
            'file_upload_type': None,
            'peer_file_urls': [],
            'review_num': 1,
            'rubric_criteria': xblock.rubric_criteria,
            'submit_button_text': 'Submit your assessment & review another response',
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': pytz.utc,
            'user_language': 'en'
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_turbo_mode.html',
            expected_context,
            continue_grading=True,
            workflow_status='done',
            graded_enough=True,
            was_graded_enough=True,
        )

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_continued_grading_no_submission(self, xblock):
        # Bugfix: This used to cause a KeyError when students would click "Peer Assessment"
        # (indicating "continued grading") before making a submission.
        expected_context = {
            'graded': 0,
            'must_grade': 5,
            'review_num': 1,
            'rubric_criteria': xblock.rubric_criteria,
            'submit_button_text': 'Submit your assessment & review another response',
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': pytz.utc,
            'user_language': 'en'
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_unavailable.html',
            expected_context,
            continue_grading=True,
        )

    def _assert_path_and_context(
            self, xblock, expected_path, expected_context,
            continue_grading=False, workflow_status=None,
            graded_enough=False,
            was_graded_enough=False,
    ):
        """
        Render the peer assessment step and verify:
            1) that the correct template and context were used
            2) that the rendering occurred without an error

        Args:
            xblock (OpenAssessmentBlock): The XBlock under test.
            expected_path (str): The expected template path.
            expected_context (dict): The expected template context.

        Keyword Arguments:
            continue_grading (bool): If true, the user has chosen to continue grading.
            workflow_status (str): If provided, simulate this status from the workflow API.
            graded_enough (bool): Did the student meet the requirement by assessing enough peers?
            was_graded_enough (bool): Did the student receive enough assessments from peers?
        """
        # Simulate the response from the workflow API
        if workflow_status is not None:
            workflow_info = {
                'status': workflow_status,
                'status_details': {'peer': {'complete': graded_enough}}
            }
            xblock.get_workflow_info = mock.Mock(return_value=workflow_info)

        # Simulate that we've either finished or not finished required grading
        patched_module = 'openassessment.assessment.api.peer'
        with mock.patch(patched_module + '.has_finished_required_evaluating') as mock_finished:
            mock_finished.return_value = (was_graded_enough, 1)
            path, context = xblock.peer_path_and_context(continue_grading)

        expected_context['xblock_id'] = xblock.scope_ids.usage_id
        self.assertEqual(path, expected_path)
        self.assertCountEqual(context, expected_context)

        # Verify that we render without error
        resp = self.request(xblock, 'render_peer_assessment', json.dumps({}))
        self.assertGreater(len(resp), 0)


class TestPeerAssessHandler(XBlockHandlerTestCase, SubmissionTestMixin):
    """
    Tests for submitting a peer assessment.
    """

    ASSESSMENT = {
        'options_selected': {'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': 'ﻉซƈﻉɭɭﻉกՇ', 'Form': 'Fair'},
        'criterion_feedback': {'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': 'ı ʇɥonƃɥʇ ʇɥıs ʍɐs ʌǝɹʎ ɔouɔısǝ.'},
        'overall_feedback': 'єאςєɭɭєภՇ ฬ๏гк!',
    }

    ASSESSMENT_WITH_INVALID_SUBMISSION_UUID = {  # pylint: disable=invalid-name
        'options_selected': {'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': 'ﻉซƈﻉɭɭﻉกՇ', 'Form': 'Fair'},
        'criterion_feedback': {'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': 'ı ʇɥonƃɥʇ ʇɥıs ʍɐs ʌǝɹʎ ɔouɔısǝ.'},
        'overall_feedback': 'єאςєɭɭєภՇ ฬ๏гк!',
        'submission_uuid': "Complete and Random Junk."
    }

    ASSESSMENT_WITH_INVALID_OPTION = {
        'options_selected': {
            '𝓒𝓸𝓷𝓬𝓲𝓼𝓮': 'ﻉซƈﻉɭɭﻉกՇ',
            'Form': 'Fair',
            'invalid': 'not a part of the rubric!'
        },
        'criterion_feedback': {'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': 'ı ʇɥonƃɥʇ ʇɥıs ʍɐs ʌǝɹʎ ɔouɔısǝ.'},
        'overall_feedback': 'єאςєɭɭєภՇ ฬ๏гк!',
    }

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_assess_handler(self, xblock):
        # Submit a peer assessment
        submission_uuid, assessment = self._submit_peer_assessment(xblock, 'Sally', 'Bob', self.ASSESSMENT)

        # Check that the stored assessment matches what we expect
        self.assertEqual(assessment['submission_uuid'], submission_uuid)
        self.assertEqual(assessment['points_earned'], 5)
        self.assertEqual(assessment['points_possible'], 6)
        self.assertEqual(assessment['scorer_id'], 'Bob')
        self.assertEqual(assessment['score_type'], 'PE')

        self.assertEqual(len(assessment['parts']), 2)

        self.assert_assessment_event_published(xblock, 'openassessmentblock.peer_assess', assessment)

        parts = assessment['parts']
        parts.sort(key=lambda x: x['option']['name'])

        self.assertEqual(parts[0]['option']['criterion']['name'], 'Form')
        self.assertEqual(parts[0]['option']['name'], 'Fair')
        self.assertEqual(parts[1]['option']['criterion']['name'], '𝓒𝓸𝓷𝓬𝓲𝓼𝓮')
        self.assertEqual(parts[1]['option']['name'], 'ﻉซƈﻉɭɭﻉกՇ')

    @scenario('data/feedback_per_criterion.xml', user_id='Bob')
    def test_peer_assess_feedback(self, xblock):
        # Submit a peer assessment
        _, assessment = self._submit_peer_assessment(xblock, 'Sally', 'Bob', self.ASSESSMENT)

        # Retrieve the assessment and check the feedback
        self.assertEqual(assessment['feedback'], self.ASSESSMENT['overall_feedback'])

        for part in assessment['parts']:
            part_criterion_name = part['option']['criterion']['name']
            expected_feedback = self.ASSESSMENT['criterion_feedback'].get(part_criterion_name, '')
            self.assertEqual(part['feedback'], expected_feedback)

    @scenario('data/grade_scenario.xml', user_id='Bob')
    def test_peer_assess_send_unsolicited_criterion_feedback(self, xblock):
        # Submit an assessment containing per-criterion feedback,
        # even though the rubric in this scenario has per-criterion feedback disabled.
        _, assessment = self._submit_peer_assessment(xblock, 'Sally', 'Bob', self.ASSESSMENT)

        # Expect that per-criterion feedback were ignored
        for part in assessment['parts']:
            self.assertEqual(part['feedback'], '')

    @scenario('data/feedback_only_criterion_peer.xml', user_id='Bob')
    def test_peer_assess_feedback_only_criterion(self, xblock):
        # Submit a peer assessment for a rubric with a feedback-only criterion
        assessment_dict = {
            'options_selected': {'vocabulary': 'good'},
            'criterion_feedback': {'𝖋𝖊𝖊𝖉𝖇𝖆𝖈𝖐 𝖔𝖓𝖑𝖞': 'Ṫḧïṡ ïṡ ṡöṁë ḟëëḋḅäċḳ'},
            'overall_feedback': ''
        }
        _, assessment = self._submit_peer_assessment(xblock, 'Sally', 'Bob', assessment_dict)

        # Check the assessment for the criterion that has options
        self.assertEqual(assessment['parts'][0]['criterion']['name'], 'vocabulary')
        self.assertEqual(assessment['parts'][0]['option']['name'], 'good')
        self.assertEqual(assessment['parts'][0]['option']['points'], 1)

        # Check the feedback-only criterion score/feedback
        self.assertEqual(assessment['parts'][1]['criterion']['name'], '𝖋𝖊𝖊𝖉𝖇𝖆𝖈𝖐 𝖔𝖓𝖑𝖞')
        self.assertIs(assessment['parts'][1]['option'], None)
        self.assertEqual(assessment['parts'][1]['feedback'], 'Ṫḧïṡ ïṡ ṡöṁë ḟëëḋḅäċḳ')

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_submission_uuid_input_regression(self, xblock):
        # Submit a peer assessment
        assessment = self._submit_peer_assessment(
            xblock,
            'Sally',
            'Bob',
            self.ASSESSMENT_WITH_INVALID_SUBMISSION_UUID,
            expect_failure=True,
        )

        self.assertIsNone(assessment)

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_assess_rubric_option_mismatch(self, xblock):
        # Submit an assessment, but mutate the options selected so they do NOT match the rubric
        # Expect a failure response
        self._submit_peer_assessment(
            xblock, 'Sally', 'Bob', self.ASSESSMENT_WITH_INVALID_OPTION,
            expect_failure=True
        )

    @mock.patch('openassessment.assessment.api.peer')
    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_api_request_error(self, xblock, mock_api):
        mock_api.create_assessment.side_effect = peer_api.PeerAssessmentRequestError
        self._submit_peer_assessment(xblock, "Sally", "Bob", self.ASSESSMENT, expect_failure=True)

    @mock.patch('openassessment.assessment.api.peer')
    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_api_internal_error(self, xblock, mock_api):
        mock_api.create_assessment.side_effect = peer_api.PeerAssessmentInternalError
        self._submit_peer_assessment(xblock, "Sally", "Bob", self.ASSESSMENT, expect_failure=True)

    @mock.patch('openassessment.xblock.workflow_mixin.workflow_api.update_from_assessments')
    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_api_workflow_error(self, xblock, mock_call):
        mock_call.side_effect = workflow_api.AssessmentWorkflowInternalError
        self._submit_peer_assessment(xblock, "Sally", "Bob", self.ASSESSMENT, expect_failure=True)

    def _submit_peer_assessment(self, xblock, student_id, scorer_id, assessment, expect_failure=False):
        """
        Create submissions for a student and scorer, then create a peer assessment
        from the scorer.

        Args:
            xblock (OpenAssessmentBlock)
            student_id (unicode): The ID of the student being assessed.
            scorer_id (unicode): The ID of the student creating the assessment.
            assessment (dict): Serialized assessment model.

        Keyword Arguments:
            expect_failure (bool): If true, expect a failure response and return None

        Returns:
            dict: The peer assessment retrieved from the API.

        """
        # Create a submission for this problem from another user
        student_item = xblock.get_student_item_dict()
        student_item['student_id'] = student_id
        submission = self.create_test_submission(xblock, student_item=student_item)

        # Create a submission for the scorer (required before assessing another student)
        another_student = copy.deepcopy(student_item)
        another_student['student_id'] = scorer_id
        another_submission = self.create_test_submission(xblock, student_item=another_student)

        # Pull the submission to assess
        peer_api.get_submission_to_assess(another_submission['uuid'], 3)

        # Submit an assessment and expect a successful response
        assessment = copy.deepcopy(assessment)
        assessment['submission_uuid'] = assessment.get('submission_uuid', submission.get('uuid', None))
        resp = self.request(xblock, 'peer_assess', json.dumps(assessment), response_format='json')

        if expect_failure:
            self.assertFalse(resp['success'])
            return None
        self.assertTrue(resp['success'])

        # Retrieve the peer assessment
        retrieved_assessment = peer_api.get_assessments(submission['uuid'])[0]
        return submission['uuid'], retrieved_assessment
