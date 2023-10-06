"""
Tests for AssessmentResponseSerializer
"""
import json
from unittest.mock import patch

from openassessment.fileupload.api import FileUpload
from openassessment.xblock.test.base import (
    PEER_ASSESSMENTS,
    STAFF_GOOD_ASSESSMENT,
    SubmissionTestMixin,
    SubmitAssessmentsMixin,
    XBlockHandlerTestCase,
    scenario,
)
from openassessment.xblock.ui_mixins.mfe.assessment_serializers import (
    AssessmentResponseSerializer,
    AssessmentStepSerializer,
    AssessmentGradeSerializer,
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
        context = {"response": None, "step": "submission"}

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
        context = {"response": submission, "step": "self"}

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
        context = {"response": submission, "step": "self"}

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
        context = {"response": submission, "step": "self"}
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


class TestAssessmentGradeSerializer(XBlockHandlerTestCase, SubmitAssessmentsMixin):
    ASSESSMENT = {
        'options_selected': {'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': 'ﻉซƈﻉɭɭﻉกՇ', 'Form': 'Fair'},
        'criterion_feedback': {},
        'overall_feedback': ""
    }

    @scenario("data/self_assessment_scenario.xml", user_id="Alan")
    def test_self_assessment_step(self, xblock):
        submission_text = ["Foo", "Bar"]

        submission = self.create_test_submission(
            xblock, submission_text=submission_text
        )

        context = {"response": submission, "step": "self"}

        resp = self.request(
            xblock, "self_assess", json.dumps(self.ASSESSMENT), response_format="json"
        )
        self.assertTrue(resp["success"])

        # When I load my response
        data = AssessmentGradeSerializer(xblock.api_data, context=context).data
        # I get the appropriate response
        self.assertEqual(context["step"], data["effectiveAssessmentType"])
        self.assertEqual(
            data["self"],
            AssessmentStepSerializer(
                xblock.api_data.self_assessment_data.assessment, context=context
            ).data,
        )

    @scenario("data/grade_scenario.xml", user_id="Alan")
    def test_staff_assessment_step(self, xblock):
        submission_text = ["Foo", "Bar"]
        submission = self.create_test_submission(
            xblock, submission_text=submission_text
        )

        self.submit_staff_assessment(xblock, submission, STAFF_GOOD_ASSESSMENT)

        context = {"response": submission, "step": "staff"}
        # When I load my response
        data = AssessmentGradeSerializer(xblock.api_data, context=context).data

        # I get the appropriate response
        self.assertEqual(context["step"], data["effectiveAssessmentType"])
        self.assertEqual(
            data["staff"],
            AssessmentStepSerializer(
                xblock.api_data.staff_assessment_data.assessment, context=context
            ).data,
        )

    @scenario("data/grade_scenario.xml", user_id="Bernard")
    def test_peer_assement_steps(self, xblock):
        # Create a submission from the user
        student_item = xblock.get_student_item_dict()
        submission = self.create_test_submission(
            xblock, student_item=student_item, submission_text=self.SUBMISSION
        )

        # Create submissions from other users
        scorer_subs = self.create_peer_submissions(
            student_item, self.PEERS, self.SUBMISSION
        )

        graded_by = xblock.get_assessment_module("peer-assessment")["must_be_graded_by"]
        for scorer_sub, scorer_name, assessment in list(
            zip(scorer_subs, self.PEERS, PEER_ASSESSMENTS)
        )[:-1]:
            self.create_peer_assessment(
                scorer_sub,
                scorer_name,
                submission,
                assessment,
                xblock.rubric_criteria,
                graded_by,
            )

        context = {"response": submission, "step": "peer"}

        # When I load my response
        data = AssessmentGradeSerializer(xblock.api_data, context=context).data

        # I get the appropriate response
        self.assertEqual(context["step"], data["effectiveAssessmentType"])
        for i in range(len(data["peers"])):
            peer = data["peers"][i]
            serialize_peer = AssessmentStepSerializer(
                xblock.api_data.peer_assessment_data().assessments[i], context=context
            ).data
            self.assertEqual(serialize_peer["stepScore"], peer["stepScore"])
            self.assertEqual(serialize_peer["assessment"], serialize_peer["assessment"])
