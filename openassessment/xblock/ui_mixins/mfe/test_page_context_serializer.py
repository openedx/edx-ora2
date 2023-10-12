"""
Tests for PageDataSerializer
"""
from copy import deepcopy

from json import dumps, loads
from unittest.mock import patch


from openassessment.xblock.test.base import (
    PEER_ASSESSMENTS,
    SELF_ASSESSMENT,
    SubmitAssessmentsMixin,
    XBlockHandlerTestCase,
    scenario,
)
from openassessment.xblock.ui_mixins.mfe.page_context_serializer import PageDataSerializer, ProgressSerializer


class TestPageContextSerializer(XBlockHandlerTestCase, SubmitAssessmentsMixin):
    @patch("openassessment.xblock.ui_mixins.mfe.page_context_serializer.AssessmentResponseSerializer")
    @patch("openassessment.xblock.ui_mixins.mfe.page_context_serializer.PageDataSubmissionSerializer")
    @scenario("data/basic_scenario.xml", user_id="Alan")
    def test_submission_view(self, xblock, mock_submission_serializer, mock_assessment_serializer):
        # Given we are asking for the submission view
        context = {"view": "submission"}

        # When I ask for my submission data
        _ = PageDataSerializer(xblock, context=context).data

        # Then I use the correct serializer and the call doesn't fail
        mock_submission_serializer.assert_called_once()
        mock_assessment_serializer.assert_not_called()

    @patch("openassessment.xblock.ui_mixins.mfe.page_context_serializer.AssessmentResponseSerializer")
    @patch("openassessment.xblock.ui_mixins.mfe.page_context_serializer.PageDataSubmissionSerializer")
    @scenario("data/basic_scenario.xml", user_id="Alan")
    def test_assessment_view(self, xblock, mock_submission_serializer, mock_assessment_serializer):
        # Given we are asking for the assessment view
        self.create_test_submission(xblock)
        context = {"view": "assessment"}

        # When I ask for assessment data
        _ = PageDataSerializer(xblock, context=context).data

        # Then I use the correct serializer and the call doesn't fail
        mock_assessment_serializer.assert_called_once()
        mock_submission_serializer.assert_not_called()


class TestPageDataSerializerAssessment(XBlockHandlerTestCase, SubmitAssessmentsMixin):
    """
    Test for PageDataSerializer: Assessment view
    """

    def setUp(self):
        """For these tests, we are always in assessment view"""
        self.context = {"view": "assessment"}
        return super().setUp()

    @scenario("data/basic_scenario.xml", user_id="Alan")
    def test_submission(self, xblock):
        # Given we are asking for assessment data too early (still on submission step)
        # When I load my response
        # Then I get an Exception
        with self.assertRaises(Exception):
            _ = PageDataSerializer(xblock, context=self.context).data

    @scenario("data/student_training.xml", user_id="Alan")
    def test_student_training(self, xblock):
        # Given we are on the student training step
        self.create_test_submission(xblock)

        # When I load my response
        response_data = PageDataSerializer(xblock, context=self.context).data["submission"]

        # I get the appropriate response
        expected_response = {
            "textResponses": ["This is my answer."],
            "uploadedFiles": None,
        }
        self.assertDictEqual(expected_response, response_data["response"])

        # ... along with these always-none fields assessments
        self.assertIsNone(response_data["hasSubmitted"])
        self.assertIsNone(response_data["hasCancelled"])
        self.assertIsNone(response_data["hasReceivedGrade"])
        self.assertIsNone(response_data["teamInfo"])

    @scenario("data/peer_only_scenario.xml", user_id="Alan")
    def test_peer_response(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Given responses available for peer grading
        other_student_item = deepcopy(student_item)
        other_student_item["student_id"] = "Joan"
        other_text_responses = ["Answer 1", "Answer 2"]
        self.create_test_submission(
            xblock,
            student_item=other_student_item,
            submission_text=other_text_responses,
        )

        # ... and that I have submitted and am on the peer grading step
        student_item = xblock.get_student_item_dict()
        text_responses = ["Answer A", "Answer B"]
        self.create_test_submission(xblock, student_item=student_item, submission_text=text_responses)

        # When I load my response
        response_data = PageDataSerializer(xblock, context=self.context).data["submission"]

        # I get the appropriate response
        expected_response = {
            "textResponses": other_text_responses,
            "uploadedFiles": None,
        }
        self.assertDictEqual(expected_response, response_data["response"])

        # ... along with these always-none fields assessments
        self.assertIsNone(response_data["hasSubmitted"])
        self.assertIsNone(response_data["hasCancelled"])
        self.assertIsNone(response_data["hasReceivedGrade"])
        self.assertIsNone(response_data["teamInfo"])

    @scenario("data/peer_only_scenario.xml", user_id="Alan")
    def test_peer_response_not_available(self, xblock):
        # Given I am on the peer grading step
        self.create_test_submission(xblock)

        # ... but with no responses to assess

        # When I load my response
        response_data = PageDataSerializer(xblock, context=self.context).data["submission"]

        # I get the appropriate response
        expected_response = {}
        self.assertDictEqual(expected_response, response_data["response"])

        # ... along with these always-none fields assessments
        self.assertIsNone(response_data["hasSubmitted"])
        self.assertIsNone(response_data["hasCancelled"])
        self.assertIsNone(response_data["hasReceivedGrade"])
        self.assertIsNone(response_data["teamInfo"])

    @scenario("data/staff_grade_scenario.xml", user_id="Alan")
    def test_staff_response(self, xblock):
        # Given I'm on the staff step
        self.create_test_submission(xblock)

        # When I load my response
        response_data = PageDataSerializer(xblock, context=self.context).data["submission"]

        # Then I get an empty object
        expected_response = {}
        self.assertDictEqual(expected_response, response_data["response"])

    @scenario("data/staff_grade_scenario.xml", user_id="Alan")
    def test_waiting_response(self, xblock):
        # Given I'm on the staff step
        self.create_test_submission(xblock)

        # When I load my response
        response_data = PageDataSerializer(xblock, context=self.context).data["submission"]

        # Then I get an empty object
        expected_response = {}
        self.assertDictEqual(expected_response, response_data["response"])

    @scenario("data/self_assessment_scenario.xml", user_id="Alan")
    def test_done_response(self, xblock):
        # Given I'm on the done step
        self.create_submission_and_assessments(xblock, self.SUBMISSION, [], [], SELF_ASSESSMENT)
        # When I load my response
        response_data = PageDataSerializer(xblock, context=self.context).data["submission"]

        # Then I get an empty object
        expected_response = {}
        self.assertDictEqual(expected_response, response_data["response"])

    @scenario("data/grade_scenario_peer_only.xml", user_id="Bernard")
    def test_jump_to_peer_response(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Given responses available for peer grading
        other_student_item = deepcopy(student_item)
        other_student_item["student_id"] = "Joan"
        other_text_responses = ["Answer 1", "Answer 2"]
        self.create_test_submission(
            xblock,
            student_item=other_student_item,
            submission_text=other_text_responses,
        )

        # ... and I have completed the peer step of an ORA
        self.create_submission_and_assessments(xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, None)

        # When I try to jump back to that step
        self.context["jump_to_step"] = "peer"
        response_data = PageDataSerializer(xblock, context=self.context).data["submission"]

        # Then I can continue to receive peer responses to grade
        expected_response = {
            "textResponses": other_text_responses,
            "uploadedFiles": None,
        }
        self.assertDictEqual(expected_response, response_data["response"])

    @scenario("data/grade_scenario_peer_only.xml", user_id="Bernard")
    def test_jump_to_bad_step(self, xblock):
        # Given I'm on assessment steps
        self.create_test_submission(xblock)

        # When I try to jump to a bad step
        self.context["jump_to_step"] = "to the left"

        # Then I expect the serializer to raise an exception
        # NOTE - this is exceedingly unlikely since the handler should only add
        # this context when the step name is valid.
        with self.assertRaises(Exception):
            _ = PageDataSerializer(xblock, context=self.context).data

    @scenario("data/student_training.xml", user_id="Bernard")
    def test_jump_to_inaccessible_step(self, xblock):
        # Given I'm on an early step like student training
        self.create_test_submission(xblock)

        # When I try to jump ahead to a step I can't yet access
        self.context["jump_to_step"] = "peer"

        # Then I expect the serializer to raise an exception
        with self.assertRaises(Exception):
            _ = PageDataSerializer(xblock, context=self.context).data


class TestPageContextProgress(XBlockHandlerTestCase, SubmitAssessmentsMixin):
    # Show full dict diffs
    maxDiff = None

    def assertNestedDictEquals(self, dict_1, dict_2):
        # Manually expand nested dicts for comparison
        dict_1_expanded = loads(dumps(dict_1))
        dict_2_expanded = loads(dumps(dict_2))
        return self.assertDictEqual(dict_1_expanded, dict_2_expanded)

    @scenario("data/basic_scenario.xml", user_id="Alan")
    def test_submission(self, xblock):
        # Given I am on the submission step

        # When I ask for progress
        context = {"step": "submission"}
        progress_data = ProgressSerializer(xblock, context=context).data

        # Then I get the expected shapes
        expected_data = {
            "activeStepName": "submission",
            "hasReceivedFinalGrade": False,
            "receivedGrades": {},
            "stepInfo": {"peer": None, "self": None},
        }

        self.assertNestedDictEquals(expected_data, progress_data)

    @scenario("data/student_training.xml", user_id="Alan")
    def test_student_training(self, xblock):
        # Given I am on the student training step
        self.create_test_submission(xblock)

        # When I ask for progress
        context = {"step": "training"}
        progress_data = ProgressSerializer(xblock, context=context).data

        # Then I get the expected shapes
        expected_data = {
            "activeStepName": "studentTraining",
            "hasReceivedFinalGrade": False,
            "receivedGrades": {
                "peer": {},
                "staff": {},
            },
            "stepInfo": {
                "studentTraining": {
                    "closed": False,
                    "closedReason": None,
                    "numberOfAssessmentsCompleted": 0,
                    "expectedRubricSelections": [
                        {
                            "name": "Vocabulary",
                            "selection": "Good",
                        },
                        {"name": "Grammar", "selection": "Excellent"},
                    ],
                },
                "peer": None,
            },
        }

        self.assertNestedDictEquals(expected_data, progress_data)

    @scenario("data/student_training_due.xml", user_id="Alan")
    def test_student_training_due(self, xblock):
        # Given I am on the student training step, but it is past due
        self.create_test_submission(xblock)

        # When I ask for progress
        context = {"step": "training"}
        progress_data = ProgressSerializer(xblock, context=context).data

        # Then I get the expected shapes
        expected_data = {
            "activeStepName": "studentTraining",
            "hasReceivedFinalGrade": False,
            "receivedGrades": {
                "peer": {},
                "staff": {},
            },
            "stepInfo": {
                "studentTraining": {
                    "closed": True,
                    "closedReason": "pastDue",
                    "numberOfAssessmentsCompleted": 0,
                    "expectedRubricSelections": [
                        {
                            "name": "Vocabulary",
                            "selection": "Good",
                        },
                        {"name": "Grammar", "selection": "Excellent"},
                    ],
                },
                "peer": None,
            },
        }

        self.assertNestedDictEquals(expected_data, progress_data)

    @scenario("data/student_training_future.xml", user_id="Alan")
    def test_student_training_not_yet_available(self, xblock):
        # Given I am on the student training step, but it is past due
        self.create_test_submission(xblock)

        # When I ask for progress
        context = {"step": "training"}
        progress_data = ProgressSerializer(xblock, context=context).data

        # Then I get the expected shapes
        expected_data = {
            "activeStepName": "studentTraining",
            "hasReceivedFinalGrade": False,
            "receivedGrades": {
                "peer": {},
                "staff": {},
            },
            "stepInfo": {
                "studentTraining": {
                    "closed": True,
                    "closedReason": "notAvailableYet",
                    "numberOfAssessmentsCompleted": 0,
                    "expectedRubricSelections": [
                        {
                            "name": "Vocabulary",
                            "selection": "Good",
                        },
                        {"name": "Grammar", "selection": "Excellent"},
                    ],
                },
                "peer": None,
            },
        }

        self.assertNestedDictEquals(expected_data, progress_data)

    @scenario("data/peer_only_scenario.xml", user_id="Alan")
    def test_peer_assessment(self, xblock):
        # Given I am on the peer step
        self.create_test_submission(xblock)

        # When I ask for progress
        context = {"step": "peer"}
        progress_data = ProgressSerializer(xblock, context=context).data

        # Then I get the expected shapes
        expected_data = {
            "activeStepName": "peer",
            "hasReceivedFinalGrade": False,
            "receivedGrades": {
                "peer": {},
                "staff": {},
            },
            "stepInfo": {
                "peer": {
                    "closed": False,
                    "closedReason": None,
                    "numberOfAssessmentsCompleted": 0,
                    "isWaitingForSubmissions": True,
                    "numberOfReceivedAssessments": 0,
                }
            },
        }

        self.assertNestedDictEquals(expected_data, progress_data)

    @scenario("data/self_only_scenario.xml", user_id="Alan")
    def test_self_assessment(self, xblock):
        # Given I am on the self step
        self.create_test_submission(xblock)

        # When I ask for progress
        context = {"step": "self"}
        progress_data = ProgressSerializer(xblock, context=context).data

        # Then I get the expected shapes
        expected_data = {
            "activeStepName": "self",
            "hasReceivedFinalGrade": False,
            "receivedGrades": {
                "self": {},
                "staff": {},
            },
            "stepInfo": {
                "self": {
                    "closed": False,
                    "closedReason": None,
                }
            },
        }

        self.assertNestedDictEquals(expected_data, progress_data)

    @scenario("data/self_assessment_closed.xml", user_id="Alan")
    def test_self_assessment_closed(self, xblock):
        # Given I am on the self step, but it is closed
        self.create_test_submission(xblock)

        # When I ask for progress
        context = {"step": "self"}
        progress_data = ProgressSerializer(xblock, context=context).data

        # Then I get the expected shapes
        expected_data = {
            "activeStepName": "self",
            "hasReceivedFinalGrade": False,
            "receivedGrades": {
                "self": {},
                "peer": {},
                "staff": {},
            },
            "stepInfo": {
                "peer": None,
                "self": {
                    "closed": True,
                    "closedReason": "pastDue",
                },
            },
        }

        self.assertNestedDictEquals(expected_data, progress_data)

    @scenario("data/self_assessment_unavailable.xml", user_id="Alan")
    def test_self_assessment_not_available(self, xblock):
        # Given I am on the self step, but it is closed
        self.create_test_submission(xblock)

        # When I ask for progress
        context = {"step": "self"}
        progress_data = ProgressSerializer(xblock, context=context).data

        # Then I get the expected shapes
        expected_data = {
            "activeStepName": "self",
            "hasReceivedFinalGrade": False,
            "receivedGrades": {
                "self": {},
                "peer": {},
                "staff": {},
            },
            "stepInfo": {
                "peer": None,
                "self": {
                    "closed": True,
                    "closedReason": "notAvailableYet",
                },
            },
        }

        self.assertNestedDictEquals(expected_data, progress_data)
