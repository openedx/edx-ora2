"""
Test submission to the OpenAssessment XBlock.
"""

import json
from mock import patch, Mock
from submissions import api as sub_api
from submissions.api import SubmissionRequestError, SubmissionInternalError
from openassessment.xblock.submission_mixin import SubmissionMixin
from .base import XBlockHandlerTestCase, scenario


class SubmissionTest(XBlockHandlerTestCase):

    SUBMISSION = json.dumps({"submission": "This is my answer to this test question!"})

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_submit_submission(self, xblock):
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertTrue(resp[0])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_submission_multisubmit_failure(self, xblock):
        # We don't care about return value of first one
        self.request(xblock, 'submit', self.SUBMISSION, response_format='json')

        # This one should fail because we're not allowed to submit multiple times
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "ENOMULTI")
        self.assertEqual(resp[2], xblock.submit_errors["ENOMULTI"])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    @patch.object(sub_api, 'create_submission')
    def test_submission_general_failure(self, xblock, mock_submit):
        mock_submit.side_effect = SubmissionInternalError("Cat on fire.")
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "EUNKNOWN")
        self.assertEqual(resp[2], SubmissionMixin().submit_errors["EUNKNOWN"])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    @patch.object(sub_api, 'create_submission')
    def test_submission_API_failure(self, xblock, mock_submit):
        mock_submit.side_effect = SubmissionRequestError("Cat on fire.")
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "EBADFORM")

    # In Studio preview mode, the runtime sets the user ID to None
    @scenario('data/basic_scenario.xml', user_id=None)
    def test_cannot_submit_in_preview_mode(self, xblock,):

        # The Studio runtime apparently provides an anonymous student ID,
        # even though we're running in Preview mode.  We should check the scope id
        # to determine whether we're in Preview mode or not.
        xblock.xmodule_runtime = Mock(
            course_id='test_course',
            anonymous_student_id='test_student'
        )

        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "ENOPREVIEW")
        self.assertEqual(resp[2], "To submit a response, view this component in Preview or Live mode.")

    # In Studio preview mode, the runtime sets the user ID to None
    @scenario('data/over_grade_scenario.xml', user_id='Alice')
    def test_closed_submissions(self, xblock,):
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        self.assertIn("Incomplete", resp)
