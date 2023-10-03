"""
Tests for AssessmentResponseSerializer
"""
from unittest.mock import patch

from openassessment.fileupload.api import FileUpload
from openassessment.xblock.test.base import (
    SubmissionTestMixin,
    XBlockHandlerTestCase,
    scenario,
)
from openassessment.xblock.ui_mixins.mfe.assessment_serializers import (
    AssessmentResponseSerializer,
)


class TestAssessmentResponseSerializer(XBlockHandlerTestCase, SubmissionTestMixin):
    """
    Test for AssessmentResponseSerializer
    """

    # Show full dictionary diff
    maxDiff = None

    @scenario("data/basic_scenario.xml", user_id="Alan")
    def test_no_response(self, xblock):
        # Given we are asking for assessment data too early (still on submission step)
        context = {"response": None}

        # When I load my response
        data = AssessmentResponseSerializer(xblock.api_data, context=context).data

        # I get the appropriate response
        expected_response = {}
        self.assertDictEqual(expected_response, data["response"])

        # ... along with these always-none fields assessments
        self.assertIsNone(data["hasSubmitted"])
        self.assertIsNone(data["hasCancelled"])
        self.assertIsNone(data["hasReceivedGrade"])
        self.assertIsNone(data["teamInfo"])

    @scenario("data/basic_scenario.xml", user_id="Alan")
    def test_response(self, xblock):
        # Given we have a response
        submission_text = ["Foo", "Bar"]
        submission = self.create_test_submission(
            xblock, submission_text=submission_text
        )
        context = {"response": submission}

        # When I load my response
        data = AssessmentResponseSerializer(xblock.api_data, context=context).data

        # I get the appropriate response
        expected_response = {
            "textResponses": submission_text,
            "uploadedFiles": None,
        }
        self.assertDictEqual(expected_response, data["response"])

        # ... along with these always-none fields assessments
        self.assertIsNone(data["hasSubmitted"])
        self.assertIsNone(data["hasCancelled"])
        self.assertIsNone(data["hasReceivedGrade"])
        self.assertIsNone(data["teamInfo"])

    @scenario("data/file_upload_scenario.xml", user_id="Alan")
    def test_files_empty(self, xblock):
        # Given we have a response
        submission_text = ["Foo", "Bar"]
        submission = self.create_test_submission(
            xblock, submission_text=submission_text
        )
        context = {"response": submission}

        # When I load my response
        data = AssessmentResponseSerializer(xblock.api_data, context=context).data

        # I get the appropriate response
        expected_response = {
            "textResponses": submission_text,
            "uploadedFiles": None,
        }
        self.assertDictEqual(expected_response, data["response"])

        # ... along with these always-none fields assessments
        self.assertIsNone(data["hasSubmitted"])
        self.assertIsNone(data["hasCancelled"])
        self.assertIsNone(data["hasReceivedGrade"])
        self.assertIsNone(data["teamInfo"])

    def _mock_file(self, xblock, student_item_dict=None, **file_data):
        """Turn mock file data into a FileUpload for testing"""
        student_item_dict = (
            xblock.get_student_item_dict()
            if not student_item_dict
            else student_item_dict
        )
        return FileUpload(**file_data, **student_item_dict)

    @patch(
        "openassessment.xblock.apis.submissions.submissions_api.FileAPI.get_uploads_for_submission"
    )
    @scenario("data/file_upload_scenario.xml", user_id="Alan")
    def test_files(self, xblock, mock_get_files):
        # Given we have a response
        submission_text = ["Foo", "Bar"]
        submission = None

        # .. with some uploaded files (and a deleted one)
        mock_file_data = [
            {
                "name": "foo",
                "description": "bar",
                "size": 1337,
            },
            {
                "name": None,
                "description": None,
                "size": None,
            },
            {
                "name": "baz",
                "description": "buzz",
                "size": 2049,
            },
        ]

        mock_files = []
        for i, file in enumerate(mock_file_data):
            file["index"] = i
            mock_files.append(self._mock_file(xblock, **file))

        mock_get_files.return_value = mock_files
        submission = self.create_test_submission(
            xblock, submission_text=submission_text
        )

        # When I load my response
        context = {"response": submission}
        data = AssessmentResponseSerializer(xblock.api_data, context=context).data

        # I get the appropriate response (test URLs use usage ID)
        expected_url = f"Alan/edX/Enchantment_101/April_1/{xblock.scope_ids.usage_id}"
        expected_response = {
            "textResponses": submission_text,
            "uploadedFiles": [
                {
                    "fileUrl": expected_url,
                    "fileDescription": "bar",
                    "fileName": "foo",
                    "fileSize": 1337,
                    "fileIndex": 0,
                },
                {
                    "fileUrl": f"{expected_url}/2",
                    "fileDescription": "buzz",
                    "fileName": "baz",
                    "fileSize": 2049,
                    "fileIndex": 2,
                },
            ],
        }
        self.assertDictEqual(expected_response, data["response"])

        # ... along with these always-none fields assessments
        self.assertIsNone(data["hasSubmitted"])
        self.assertIsNone(data["hasCancelled"])
        self.assertIsNone(data["hasReceivedGrade"])
        self.assertIsNone(data["teamInfo"])
