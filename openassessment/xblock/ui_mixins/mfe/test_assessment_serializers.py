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
