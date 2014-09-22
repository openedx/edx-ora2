# -*- coding: utf-8 -*-
"""
Tests for peer assessment handlers in Open Assessment XBlock.
"""
from collections import namedtuple

import copy
import json
import mock
import datetime as dt
import pytz
import ddt
from openassessment.assessment.api import peer as peer_api
from openassessment.workflow import api as workflow_api
from .base import XBlockHandlerTestCase, scenario


class TestPeerAssessment(XBlockHandlerTestCase):
    """
    Test integration of the OpenAssessment XBlock with the peer assessment API.
    """

    ASSESSMENT = {
        'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
        'criterion_feedback': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ı ʇɥonƃɥʇ ʇɥıs ʍɐs ʌǝɹʎ ɔouɔısǝ.'},
        'overall_feedback': u'єאςєɭɭєภՇ ฬ๏гк!',
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

        # If Over Grading is on, this should now return Sally or Hal's response to Bob.
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
        self.assertTrue("Sally".encode('utf-8') in peer_response.body or
            "Hal".encode('utf-8') in peer_response.body)

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_assess_before_submission(self, xblock):
        # Submit a peer assessment without a submission
        resp = self.request(xblock, 'peer_assess', json.dumps(self.ASSESSMENT), response_format='json')
        self.assertEqual(resp['success'], False)
        self.assertGreater(len(resp['msg']), 0)

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_assess_without_leasing_submission(self, xblock):
        # Create a submission
        student_item = xblock.get_student_item_dict()
        submission = xblock.create_submission(student_item, u"Bob's answer")

        # Attempt to assess a peer without first leasing their submission
        # (usually occurs by rendering the peer assessment step)
        resp = self.request(xblock, 'peer_assess', json.dumps(self.ASSESSMENT), response_format='json')
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
        submission = xblock.create_submission(student_item, u"Bob's answer")
        workflow_info = xblock.get_workflow_info()
        self.assertEqual(workflow_info["status"], u'peer')

        # Validate Submission Rendering.
        request = namedtuple('Request', 'params')
        request.params = {'continue_grading': True}
        peer_response = xblock.render_peer_assessment(request)
        self.assertIsNotNone(peer_response)
        self.assertNotIn(submission["answer"]["text"].encode('utf-8'), peer_response.body)

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
        self.assertNotIn(submission["answer"]["text"].encode('utf-8'), peer_response.body)

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
        self.assertNotIn(submission["answer"]["text"].encode('utf-8'), peer_response.body)
        self.assertIn("Peer Assessments Complete", peer_response.body)


@ddt.ddt
class TestPeerAssessmentRender(XBlockHandlerTestCase):
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
            'estimated_time': '20 minutes',
            'submit_button_text': 'Submit your assessment & move to response #2',
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'allow_latex': False,
            'track_changes': '',
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_unavailable.html', expected_context
        )

    @scenario('data/peer_closed_scenario.xml', user_id='Bob')
    def test_closed_no_submission(self, xblock):
        expected_context = {
            'peer_due': dt.datetime(2000, 1, 1).replace(tzinfo=pytz.utc),
            'graded': 0,
            'estimated_time': '20 minutes',
            'submit_button_text': 'Submit your assessment & move to response #2',
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'allow_latex': False,
            'track_changes': '',
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_closed.html', expected_context
        )

    @scenario('data/peer_future_scenario.xml', user_id='Bob')
    def test_before_release(self, xblock):
        expected_context = {
            'peer_start': dt.datetime(2999, 1, 1).replace(tzinfo=pytz.utc),
            'graded': 0,
            'estimated_time': '20 minutes',
            'submit_button_text': 'Submit your assessment & move to response #2',
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'allow_latex': False,
            'track_changes': '',
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_unavailable.html', expected_context
        )

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_waiting_for_peers(self, xblock):
        # Make a submission, but no peer assessments available
        xblock.create_submission(xblock.get_student_item_dict(), u'Ǥø ȺħɇȺđ, Ȼøɍnɇłɨᵾs, ɏøᵾ ȼȺn ȼɍɏ')

        # Expect to be in the waiting for peers state
        expected_context = {
            'graded': 0,
            'estimated_time': '20 minutes',
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'submit_button_text': 'submit your assessment & move to response #2',
            'allow_latex': False,
            'track_changes': '',
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
        xblock.create_submission(
            xblock.get_student_item_dict(),
            u"𝒀𝒆𝒔. 𝑴𝒂𝒌𝒆 𝒕𝒉𝒆𝒔𝒆 𝒚𝒐𝒖𝒓 𝒑𝒓𝒊𝒎𝒂𝒓𝒚 𝒂𝒄𝒕𝒊𝒐𝒏 𝒊𝒕𝒆𝒎𝒔."
        )

        # Create a submission from another user so we have something to assess
        other_student = copy.deepcopy(xblock.get_student_item_dict())
        other_student['student_id'] = 'Tyler'
        submission = xblock.create_submission(
            other_student,
            (
                u"ησω, αη¢ιєηт ρєσρℓє ƒσυη∂ тнєιя ¢ℓσтнєѕ ﻭσт ¢ℓєαηєя"
                u" ιƒ тнєу ωαѕнє∂ тнєм αт α ¢єятαιη ѕρσт ιη тнє яινєя."
            )
        )

        # We should pull the other student's submission
        expected_context = {
            'graded': 0,
            'estimated_time': '20 minutes',
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'peer_submission': submission,
            'allow_file_upload': False,
            'peer_file_url': '',
            'submit_button_text': 'submit your assessment & move to response #2',
            'allow_latex': False,
            'track_changes': '',
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_assessment.html',
            expected_context,
            workflow_status='peer',
        )

    @scenario('data/peer_closed_scenario.xml', user_id='Bob')
    def test_peer_closed_no_assessments_available(self, xblock):
        # Make a submission, so we get to peer assessment
        xblock.create_submission(xblock.get_student_item_dict(), u"ฬє'гє รՇเɭɭ ๓єภ")

        # No assessments are available, and the step has closed
        expected_context = {
            'peer_due': dt.datetime(2000, 1, 1).replace(tzinfo=pytz.utc),
            'graded': 0,
            'estimated_time': '20 minutes',
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'submit_button_text': 'submit your assessment & move to response #2',
            'allow_latex': False,
            'track_changes': '',
        }
        self._assert_path_and_context(
            xblock, 'openassessmentblock/peer/oa_peer_closed.html',
            expected_context,
            workflow_status='peer',
        )

    @scenario('data/peer_closed_scenario.xml', user_id='Richard')
    def test_peer_closed_assessments_available(self, xblock):
        # Make a submission, so we get to peer assessment
        xblock.create_submission(
            xblock.get_student_item_dict(),
            u"𝒀𝒆𝒔. 𝑴𝒂𝒌𝒆 𝒕𝒉𝒆𝒔𝒆 𝒚𝒐𝒖𝒓 𝒑𝒓𝒊𝒎𝒂𝒓𝒚 𝒂𝒄𝒕𝒊𝒐𝒏 𝒊𝒕𝒆𝒎𝒔."
        )

        # Create a submission from another user so we have something to assess
        other_student = copy.deepcopy(xblock.get_student_item_dict())
        other_student['student_id'] = 'Tyler'
        xblock.create_submission(
            other_student,
            (
                u"ησω, αη¢ιєηт ρєσρℓє ƒσυη∂ тнєιя ¢ℓσтнєѕ ﻭσт ¢ℓєαηєя"
                u" ιƒ тнєу ωαѕнє∂ тнєм αт α ¢єятαιη ѕρσт ιη тнє яινєя."
            )
        )

        # ... but the problem is closed, so we can't assess them
        expected_context = {
            'peer_due': dt.datetime(2000, 1, 1).replace(tzinfo=pytz.utc),
            'graded': 0,
            'estimated_time': '20 minutes',
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'submit_button_text': 'submit your assessment & move to response #2',
            'allow_latex': False,
            'track_changes': '',
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
        xblock.create_submission(
            xblock.get_student_item_dict(),
            u"𝕿𝖍𝖊 𝖋𝖎𝖗𝖘𝖙 𝖗𝖚𝖑𝖊 𝖔𝖋 𝖋𝖎𝖌𝖍𝖙 𝖈𝖑𝖚𝖇 𝖎𝖘 𝖞𝖔𝖚 𝖉𝖔 𝖓𝖔𝖙 𝖙𝖆𝖑𝖐 𝖆𝖇𝖔𝖚𝖙 𝖋𝖎𝖌𝖍𝖙 𝖈𝖑𝖚𝖇."
        )

        # Simulate a workflow status of "done" and expect to see the "completed" step
        expected_context = {
            'peer_due': dt.datetime(2000, 1, 1).replace(tzinfo=pytz.utc),
            'graded': 0,
            'estimated_time': '20 minutes',
            'submit_button_text': 'submit your assessment & move to response #2',
            'rubric_criteria': xblock.rubric_criteria,
            'must_grade': 5,
            'review_num': 1,
            'allow_latex': False,
            'track_changes': '',
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
        xblock.create_submission(
            xblock.get_student_item_dict(),
            u"ı ƃoʇ ʇɥıs pɹǝss ɐʇ ɐ ʇɥɹıɟʇ sʇoɹǝ ɟoɹ ouǝ poןןɐɹ."
        )

        # Try to continue grading after the due date has passed
        # Continued grading should still be available,
        # but since there are no other submissions, we're in the waiting state.
        expected_context = {
            'estimated_time': '20 minutes',
             'graded': 0,
             'must_grade': 5,
             'peer_due': dt.datetime(2000, 1, 1).replace(tzinfo=pytz.utc),
             'review_num': 1,
             'rubric_criteria': xblock.rubric_criteria,
             'submit_button_text': 'Submit your assessment & review another response',
             'allow_latex': False,
             'track_changes': '',
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
        submission = xblock.create_submission(other_student_item, u"Other submission")

        expected_context = {
            'estimated_time': '20 minutes',
             'graded': 0,
             'must_grade': 5,
             'peer_due': dt.datetime(2000, 1, 1).replace(tzinfo=pytz.utc),
             'peer_submission': submission,
             'allow_file_upload': False,
             'peer_file_url': '',
             'review_num': 1,
             'rubric_criteria': xblock.rubric_criteria,
             'submit_button_text': 'Submit your assessment & review another response',
             'allow_latex': False,
            'track_changes': '',
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
            'estimated_time': '20 minutes',
            'graded': 0,
            'must_grade': 5,
            'review_num': 1,
            'rubric_criteria': xblock.rubric_criteria,
            'submit_button_text': 'Submit your assessment & review another response',
            'allow_latex': False,
            'track_changes': '',
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
        patched_module = 'openassessment.xblock.peer_assessment_mixin.peer_api'
        with mock.patch(patched_module + '.has_finished_required_evaluating') as mock_finished:
            mock_finished.return_value = (was_graded_enough, 1)
            path, context = xblock.peer_path_and_context(continue_grading)

        self.assertEqual(path, expected_path)
        self.assertItemsEqual(context, expected_context)

        # Verify that we render without error
        resp = self.request(xblock, 'render_peer_assessment', json.dumps({}))
        self.assertGreater(len(resp), 0)


class TestPeerAssessHandler(XBlockHandlerTestCase):
    """
    Tests for submitting a peer assessment.
    """

    ASSESSMENT = {
        'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
        'criterion_feedback': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ı ʇɥonƃɥʇ ʇɥıs ʍɐs ʌǝɹʎ ɔouɔısǝ.'},
        'overall_feedback': u'єאςєɭɭєภՇ ฬ๏гк!',
    }

    ASSESSMENT_WITH_SUBMISSION_UUID = {
        'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
        'criterion_feedback': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ı ʇɥonƃɥʇ ʇɥıs ʍɐs ʌǝɹʎ ɔouɔısǝ.'},
        'overall_feedback': u'єאςєɭɭєภՇ ฬ๏гк!',
        'submission_uuid': "Complete and Random Junk."
    }

    ASSESSMENT_WITH_INVALID_OPTION = {
        'options_selected': {
            u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ',
            u'Form': u'Fair',
            u'invalid': 'not a part of the rubric!'
        },
        'criterion_feedback': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ı ʇɥonƃɥʇ ʇɥıs ʍɐs ʌǝɹʎ ɔouɔısǝ.'},
        'overall_feedback': u'єאςєɭɭєภՇ ฬ๏гк!',
    }

    SUBMISSION = u'ՇﻉรՇ รપ๒๓ٱรรٱѻก'

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
        parts = sorted(assessment['parts'])
        self.assertEqual(parts[0]['option']['criterion']['name'], u'Form')
        self.assertEqual(parts[0]['option']['name'], 'Fair')
        self.assertEqual(parts[1]['option']['criterion']['name'], u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮')
        self.assertEqual(parts[1]['option']['name'], u'ﻉซƈﻉɭɭﻉกՇ')

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
            'options_selected': {u'vocabulary': u'good'},
            'criterion_feedback': {u'𝖋𝖊𝖊𝖉𝖇𝖆𝖈𝖐 𝖔𝖓𝖑𝖞': u'Ṫḧïṡ ïṡ ṡöṁë ḟëëḋḅäċḳ'},
            'overall_feedback': u''
        }
        _, assessment = self._submit_peer_assessment(xblock, 'Sally', 'Bob', assessment_dict)

        # Check the assessment for the criterion that has options
        self.assertEqual(assessment['parts'][0]['criterion']['name'], 'vocabulary')
        self.assertEqual(assessment['parts'][0]['option']['name'], 'good')
        self.assertEqual(assessment['parts'][0]['option']['points'], 1)

        # Check the feedback-only criterion score/feedback
        self.assertEqual(assessment['parts'][1]['criterion']['name'], u'𝖋𝖊𝖊𝖉𝖇𝖆𝖈𝖐 𝖔𝖓𝖑𝖞')
        self.assertIs(assessment['parts'][1]['option'], None)
        self.assertEqual(assessment['parts'][1]['feedback'], u'Ṫḧïṡ ïṡ ṡöṁë ḟëëḋḅäċḳ')

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_submission_uuid_input_regression(self, xblock):
        # Submit a peer assessment
        submission_uuid, assessment = self._submit_peer_assessment(
            xblock, 'Sally', 'Bob', self.ASSESSMENT_WITH_SUBMISSION_UUID
        )

        # Retrieve the assessment and check that it matches what we sent
        self.assertEqual(assessment['submission_uuid'], submission_uuid)
        self.assertEqual(assessment['points_earned'], 5)
        self.assertEqual(assessment['points_possible'], 6)
        self.assertEqual(assessment['scorer_id'], 'Bob')
        self.assertEqual(assessment['score_type'], 'PE')

    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_assess_rubric_option_mismatch(self, xblock):
        # Submit an assessment, but mutate the options selected so they do NOT match the rubric
        # Expect a failure response
        self._submit_peer_assessment(
            xblock, 'Sally', 'Bob', self.ASSESSMENT_WITH_INVALID_OPTION,
            expect_failure=True
        )

    @mock.patch('openassessment.xblock.peer_assessment_mixin.peer_api')
    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_peer_api_request_error(self, xblock, mock_api):
        mock_api.create_assessment.side_effect = peer_api.PeerAssessmentRequestError
        self._submit_peer_assessment(xblock, "Sally", "Bob", self.ASSESSMENT, expect_failure=True)

    @mock.patch('openassessment.xblock.peer_assessment_mixin.peer_api')
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
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        # Create a submission for the scorer (required before assessing another student)
        another_student = copy.deepcopy(student_item)
        another_student['student_id'] = scorer_id
        another_submission = xblock.create_submission(another_student, self.SUBMISSION)

        # Pull the submission to assess
        peer_api.get_submission_to_assess(another_submission['uuid'], 3)

        # Submit an assessment and expect a successful response
        assessment = copy.deepcopy(assessment)
        resp = self.request(xblock, 'peer_assess', json.dumps(assessment), response_format='json')

        if expect_failure:
            self.assertFalse(resp['success'])
            return None
        else:
            self.assertTrue(resp['success'])

            # Retrieve the peer assessment
            retrieved_assessment = peer_api.get_assessments(submission['uuid'], scored_only=False)[0]
            return submission['uuid'], retrieved_assessment

    @scenario('data/grade_scenario.xml', user_id='Bob')
    def test_track_changes(self, xblock):
        student_item = xblock.get_student_item_dict()

        sally_student_item = copy.deepcopy(student_item)
        sally_student_item['student_id'] = "Sally"
        sallys_answer = u"Sally's answer"
        sally_submission = xblock.create_submission(sally_student_item, sallys_answer)

        # Hal comes and submits a response.
        hal_student_item = copy.deepcopy(student_item)
        hal_student_item['student_id'] = "Hal"
        hals_answer = u"Hal's answer"
        hal_submission = xblock.create_submission(hal_student_item, hals_answer)

        number_of_required_grades = 1
        track_changes_edits_hal = sallys_answer + u'<span class="ins"> is wrong!</span>'
        track_changes_edits_sally = hals_answer + u'<span class="ins"> is wrong!</span>'

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
            number_of_required_grades,
            track_changes_edits=track_changes_edits_hal,
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
            number_of_required_grades,
            track_changes_edits=track_changes_edits_sally,
        )

        # If Over Grading is on, this should now return Sally or Hal's response to Bob.
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
        self.assertTrue("Sally".encode('utf-8') in peer_response.body or
            "Hal".encode('utf-8') in peer_response.body)
