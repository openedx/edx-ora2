"""
Tests the Open Assessment XBlock functionality.
"""

import json
import webob

from django.test import TestCase
from mock import patch

from workbench.runtime import WorkbenchRuntime
from submissions import api
from submissions.api import SubmissionInternalError


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

    def make_request(self, body):
        """Mock request method."""
        request = webob.Request({})
        request.body = body
        return request

    def text_of_response(self, response):
        """Return the text of response."""
        return "".join(response.app_iter)

    def test_submit_submission(self):
        """
        Verify we can submit an answer to the XBlock and get the expected return
        value.
        """
        json_data = json.dumps(
            {"submission": "This is my answer to this test question!"}
        )

        resp = self.runtime.handle(
            self.assessment, 'submit',
            self.make_request(json_data)
        )
        result = self.text_of_response(resp)
        self.assertEqual("true", result)

    @patch.object(api, 'create_submission')
    def test_submission_failure(self, mock_submit):
        """
        Nothing from the front end currently causes an exception. However the
        backend could have an internal error that will bubble up. This will
        mock an internal error and ensure the front end returns the proper
        value.
        """
        mock_submit.side_effect = SubmissionInternalError("Cat on fire.")
        json_data = json.dumps(
            {"submission": "This is my answer to this test question!"}
        )

        resp = self.runtime.handle(
            self.assessment, 'submit',
            self.make_request(json_data)
        )
        result = self.text_of_response(resp)
        self.assertEquals("false", result)


    def test_load_student_view(self):
        """
        View basic test for verifying we're returned some HTML about the
        Open Assessment XBlock. We don't want to match too heavily against the
        contents.
        """
        xblock_fragment = self.runtime.render(self.assessment, "student_view")
        self.assertTrue(xblock_fragment.body_html().find("Openassessmentblock"))
