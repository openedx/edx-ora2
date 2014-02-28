"""
Tests the Open Assessment XBlock functionality.
"""
import json
import datetime

from mock import patch

from openassessment.xblock.submission_mixin import SubmissionMixin
from submissions import api as sub_api
from submissions.api import SubmissionRequestError, SubmissionInternalError

from .base import XBlockHandlerTestCase, scenario


class TestOpenAssessment(XBlockHandlerTestCase):

    SUBMISSION = json.dumps({"submission": "This is my answer to this test question!"})

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_submit_submission(self, xblock):
        """XBlock accepts response, returns true on success"""
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertTrue(resp[0])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_submission_multisubmit_failure(self, xblock):
        """XBlock returns true on first, false on second submission"""

        # We don't care about return value of first one
        self.request(xblock, 'submit', self.SUBMISSION, response_format='json')

        # This one should fail becaus we're not allowed to submit multiple times
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "ENOMULTI")
        self.assertEqual(resp[2], xblock.submit_errors["ENOMULTI"])

    @scenario('data/basic_scenario.xml')
    @patch.object(sub_api, 'create_submission')
    def test_submission_general_failure(self, xblock, mock_submit):
        """Internal errors return some code for submission failure."""
        mock_submit.side_effect = SubmissionInternalError("Cat on fire.")
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "EUNKNOWN")
        self.assertEqual(resp[2], SubmissionMixin().submit_errors["EUNKNOWN"])

    @scenario('data/basic_scenario.xml')
    @patch.object(sub_api, 'create_submission')
    def test_submission_API_failure(self, xblock, mock_submit):
        """API usage errors return code and meaningful message."""
        mock_submit.side_effect = SubmissionRequestError("Cat on fire.")
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "EBADFORM")
        self.assertEqual(resp[2], "Cat on fire.")

    @scenario('data/basic_scenario.xml')
    def test_load_student_view(self, xblock):
        """OA XBlock returns some HTML to the user.

        View basic test for verifying we're returned some HTML about the
        Open Assessment XBlock. We don't want to match too heavily against the
        contents.
        """
        xblock_fragment = self.runtime.render(xblock, "student_view")
        self.assertTrue(xblock_fragment.body_html().find("Openassessmentblock"))

        # Validate Submission Rendering.
        submission_response = xblock.render_submission({})
        self.assertIsNotNone(submission_response)
        self.assertTrue(submission_response.body.find("openassessment__response"))

        # Validate Peer Rendering.
        peer_response = xblock.render_peer_assessment({})
        self.assertIsNotNone(peer_response)
        self.assertTrue(peer_response.body.find("openassessment__peer-assessment"))

        # Validate Self Rendering.
        self_response = xblock.render_self_assessment({})
        self.assertIsNotNone(self_response)
        self.assertTrue(self_response.body.find("openassessment__peer-assessment"))

        # Validate Grading.
        grade_response = xblock.render_grade({})
        self.assertIsNotNone(grade_response)
        self.assertTrue(grade_response.body.find("openassessment__grade"))

    @scenario('data/basic_scenario.xml')
    def test_start_end_date_checks(self, xblock):
        """
        Check if the start and end date checks work appropriately.
        """
        now = datetime.datetime.utcnow()
        past = now - datetime.timedelta(minutes = 10)
        future = now + datetime.timedelta(minutes = 10)
        way_future = now + datetime.timedelta(minutes = 20)
        xblock.start_datetime = past.isoformat()
        xblock.due_datetime = past.isoformat()
        problem_open, reason = xblock.is_open()
        self.assertFalse(problem_open)
        self.assertEqual("due", reason)

        xblock.start_datetime = past.isoformat()
        xblock.due_datetime = future.isoformat()
        problem_open, reason = xblock.is_open()
        self.assertTrue(problem_open)
        self.assertEqual(None, reason)

        xblock.start_datetime = future.isoformat()
        xblock.due_datetime = way_future.isoformat()
        problem_open, reason = xblock.is_open()
        self.assertFalse(problem_open)
        self.assertEqual("start", reason)
