from copy import deepcopy

from openassessment.xblock.test.base import (
    SubmissionTestMixin,
    XBlockHandlerTestCase,
    scenario,
)
from openassessment.xblock.ui_mixins.mfe.assessment_serializers import (
    AssessmentResponseSerializer,
)


class TestSubmissionAssessmentResponse(XBlockHandlerTestCase, SubmissionTestMixin):
    """
    Test for Assessment view: Submission Step
    """

    @scenario("data/basic_scenario.xml", user_id="Alan")
    def test_response(self, xblock):
        # Given we are asking for assessment data too early (still on submission step)
        context = {"step": "submission"}

        # When I load my response
        # Then I get an Exception
        with self.assertRaises(Exception):
            AssessmentResponseSerializer(xblock.api_data, context=context).data


class TestTrainingAssessmentResponse(XBlockHandlerTestCase, SubmissionTestMixin):
    """
    Test for ResponseAssessmentSerializer
    """

    @scenario("data/student_training.xml", user_id="Alan")
    def test_response(self, xblock):
        # Given we are on the student training step
        self.create_test_submission(xblock)

        # When I load my response
        context = {"step": "training"}
        data = AssessmentResponseSerializer(xblock.api_data, context=context).data

        # I get the appropriate response
        expected_response = {
            "textResponses": ["This is my answer."],
            "uploadedFiles": None,
        }
        self.assertDictEqual(expected_response, data["response"])

        # ... along with these always-none fields assessments
        self.assertIsNone(data["hasSubmitted"])
        self.assertIsNone(data["hasCancelled"])
        self.assertIsNone(data["hasReceivedGrade"])
        self.assertIsNone(data["teamInfo"])


class TestPeerAssessmentResponse(XBlockHandlerTestCase, SubmissionTestMixin):
    """
    Test for ResponseAssessmentSerializer
    """

    @scenario("data/peer_only_scenario.xml", user_id="Alan")
    def test_response(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Given responses available for peer grading
        other_student_item = deepcopy(student_item)
        other_student_item["student_id"] = "Joan"
        other_text_responses = ["Answer 1", "Answer 2"]
        other_submission = self.create_test_submission(
            xblock,
            student_item=other_student_item,
            submission_text=other_text_responses,
        )

        # ... and that I have submitted and am on the peer grading step        # Given we are on the peer grading step
        student_item = xblock.get_student_item_dict()
        text_responses = ["Answer A", "Answer B"]
        self.create_test_submission(
            xblock, student_item=student_item, submission_text=text_responses
        )

        # When I load my response
        context = {"step": "peer"}
        data = AssessmentResponseSerializer(xblock.api_data, context=context).data

        # I get the appropriate response
        expected_response = {
            "textResponses": other_text_responses,
            "uploadedFiles": None,
        }
        self.assertDictEqual(expected_response, data["response"])

        # ... along with these always-none fields assessments
        self.assertIsNone(data["hasSubmitted"])
        self.assertIsNone(data["hasCancelled"])
        self.assertIsNone(data["hasReceivedGrade"])
        self.assertIsNone(data["teamInfo"])

    @scenario("data/peer_only_scenario.xml", user_id="Alan")
    def test_response_not_available(self, xblock):
        # Given I am on the peer grading step
        context = {"step": "peer"}
        self.create_test_submission(xblock)

        # ... but with no responses to assess

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


class TestOtherAssessmentResponses(XBlockHandlerTestCase, SubmissionTestMixin):
    """
    Tests for ResponseAssessmentSerializer staff, waiting, done, and bad steps.
    """

    @scenario("data/basic_scenario.xml", user_id="Alan")
    def test_staff_response(self, xblock):
        # Given a bad step name
        context = {"step": "DANGER, WILL ROBINSON"}
        self.create_test_submission(xblock)

        # When I ask for a response
        # Then I get an exception
        with self.assertRaises(Exception):
            AssessmentResponseSerializer(xblock.api_data, context=context).data

    @scenario("data/staff_grade_scenario.xml", user_id="Alan")
    def test_staff_response(self, xblock):
        # Given I'm on the staff step
        context = {"step": "staff"}
        self.create_test_submission(xblock)

        # When I ask for a response
        data = AssessmentResponseSerializer(xblock.api_data, context=context).data

        # Then I get an empty object
        expected_response = {}
        self.assertDictEqual(expected_response, data["response"])

    @scenario("data/staff_grade_scenario.xml", user_id="Alan")
    def test_waiting_response(self, xblock):
        # Given I'm on the staff step
        context = {"step": "waiting"}
        self.create_test_submission(xblock)

        # When I ask for a response
        data = AssessmentResponseSerializer(xblock.api_data, context=context).data

        # Then I get an empty object
        expected_response = {}
        self.assertDictEqual(expected_response, data["response"])

    @scenario("data/self_assessment_scenario.xml", user_id="Alan")
    def test_done_response(self, xblock):
        # Given I'm on the done step
        context = {"step": "done"}
        self.create_test_submission(xblock)

        # When I ask for a response
        data = AssessmentResponseSerializer(xblock.api_data, context=context).data

        # Then I get an empty object
        expected_response = {}
        self.assertDictEqual(expected_response, data["response"])
