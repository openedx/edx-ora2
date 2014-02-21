"""
Tests the Open Assessment XBlock functionality.
"""
import json

from django.test import TestCase
from mock import patch
from workbench.runtime import WorkbenchRuntime
import webob

from openassessment.xblock.submission_mixin import SubmissionMixin
from submissions import api as sub_api
from submissions.api import SubmissionRequestError, SubmissionInternalError

RUBRIC_CONFIG = """
    <openassessment start="2014-12-19T23:00-7:00" due="2014-12-21T23:00-7:00">
        <prompt>
            Given the state of the world today, what do you think should be done to
            combat poverty? Please answer in a short essay of 200-300 words.
        </prompt>
        <rubric>
            Read for conciseness, clarity of thought, and form.
            <criterion name="concise">
                How concise is it?
                <option val="0">Neal Stephenson (late)</option>
                <option val="1">HP Lovecraft</option>
                <option val="3">Robert Heinlein</option>
                <option val="4">Neal Stephenson (early)</option>
                <option val="5">Earnest Hemingway</option>
            </criterion>
            <criterion name="clearheaded">
                How clear is the thinking?
                <option val="0">Yogi Berra</option>
                <option val="1">Hunter S. Thompson</option>
                <option val="2">Robert Heinlein</option>
                <option val="3">Isaac Asimov</option>
                <option val="10">Spock</option>
            </criterion>
            <criterion name="form">
                Lastly, how is it's form? Punctuation, grammar, and spelling all count.
                <option val="0">lolcats</option>
                <option val="1">Facebook</option>
                <option val="2">Reddit</option>
                <option val="3">metafilter</option>
                <option val="4">Usenet, 1996</option>
                <option val="5">The Elements of Style</option>
            </criterion>
        </rubric>
        <assessments>
            <peer-assessment name="peer-assessment"
              start="2014-12-20T19:00-7:00"
              due="2014-12-21T22:22-7:00"
              must_grade="5"
              must_be_graded_by="3" />
            <self-assessment/>
        </assessments>
    </openassessment>
"""


class TestOpenAssessment(TestCase):

    runtime = None
    assessment = None

    def setUp(self):
        self.runtime = WorkbenchRuntime()
        self.runtime.user_id = "Bob"
        assessment_id = self.runtime.parse_xml_string(
            RUBRIC_CONFIG, self.runtime.id_generator)
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

    @patch.object(sub_api, 'create_submission')
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
        self.assertEqual(result[2], SubmissionMixin().submit_errors["EUNKNOWN"])

    @patch.object(sub_api, 'create_submission')
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

