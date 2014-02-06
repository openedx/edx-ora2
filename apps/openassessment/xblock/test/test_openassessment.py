"""
Tests the Open Assessment XBlock functionality.
"""

import json
import webob

from django.test import TestCase
from mock import patch

from workbench.runtime import WorkbenchRuntime
from submissions import api
from submissions.api import SubmissionRequestError, SubmissionInternalError


class TestOpenAssessment(TestCase):

    runtime = None
    assessment = None

    def setUp(self):
        self.runtime = WorkbenchRuntime()
        self.runtime.user_id = "Bob"
        assessment_id = self.runtime.parse_xml_string(
            """<openassessment
                  prompt="This is my prompt. There are many like it, but this one is mine."
                  course_id="RopesCourse"
                />
            """, self.runtime.id_generator)
        self.assessment = self.runtime.get_block(assessment_id)
        self.default_json_submission = json.dumps({"submission": "This is my answer to this test question!"})

    def make_request(self, body):
        """Mock request method."""
        request = webob.Request({})
        request.body = body
        return request

    def test_submit_submission(self):
        """XBlock accepts response, returns true on success."""
        resp = self.runtime.handle(
            self.assessment, 'submit',
            self.make_request(self.default_json_submission)
        )
        result = json.loads(resp.body)
        self.assertTrue(result[0])

    @patch.object(api, 'create_submission')
    def test_submission_general_failure(self, mock_submit):
        """Internal errors return some code for submission failure."""
        mock_submit.side_effect = SubmissionInternalError("Cat on fire.")
        resp = self.runtime.handle(
            self.assessment, 'submit',
            self.make_request(self.default_json_submission)
        )
        result = json.loads(resp.body)
        self.assertFalse(result[0])
        self.assertEqual(result[1], "EUNKNOWN")
        self.assertEqual(result[2], self.assessment.submit_errors["EUNKNOWN"])

    @patch.object(api, 'create_submission')
    def test_submission_API_failure(self, mock_submit):
        """API usage errors return code and meaningful message."""
        mock_submit.side_effect = SubmissionRequestError("Cat on fire.")
        resp = self.runtime.handle(
            self.assessment, 'submit',
            self.make_request(self.default_json_submission)
        )
        result = json.loads(resp.body)
        self.assertFalse(result[0])
        self.assertEqual(result[1], "EBADFORM")
        self.assertEqual(result[2], "Cat on fire.")

    def test_load_student_view(self):
        """OA XBlock returns some HTML to the user.

        View basic test for verifying we're returned some HTML about the
        Open Assessment XBlock. We don't want to match too heavily against the
        contents.
        """
        xblock_fragment = self.runtime.render(self.assessment, "student_view")
        self.assertTrue(xblock_fragment.body_html().find("Openassessmentblock"))
