"""
Tests for PageDataSerializer
"""
from copy import deepcopy
from json import dumps, loads
from unittest import TestCase
from unittest.case import skip
from unittest.mock import Mock, PropertyMock, patch
import ddt
from openassessment.fileupload.api import TeamFileDescriptor
from openassessment.workflow.api import cancel_workflow
from openassessment.xblock.apis.submissions.submissions_actions import create_team_submission
from openassessment.xblock.apis.submissions.submissions_api import SubmissionAPI
from openassessment.xblock.test.base import (
    PEER_ASSESSMENTS,
    SELF_ASSESSMENT,
    SubmitAssessmentsMixin,
    XBlockHandlerTestCase,
    scenario,
)
from openassessment.xblock.test.test_submission import setup_mock_team
from openassessment.xblock.ui_mixins.mfe.page_context_serializer import (
    PageDataSerializer,
    ProgressSerializer,
    TeamInfoSerializer,
)


class TestPageContextSerializer(XBlockHandlerTestCase, SubmitAssessmentsMixin):
    @patch("openassessment.xblock.ui_mixins.mfe.page_context_serializer.AssessmentResponseSerializer")
    @patch("openassessment.xblock.ui_mixins.mfe.page_context_serializer.DraftResponseSerializer")
    @scenario("data/basic_scenario.xml", user_id="Alan")
    def test_submission_view(self, xblock, mock_submission_serializer, mock_assessment_serializer):
        # Given we are asking for the submission view
        context = {"view": "submission", "step": "submission"}

        # When I ask for my submission data
        _ = PageDataSerializer(xblock, context=context).data

        # Then I use the correct serializer and the call doesn't fail
        mock_submission_serializer.assert_called_once()
        mock_assessment_serializer.assert_not_called()

    @patch("openassessment.xblock.ui_mixins.mfe.page_context_serializer.AssessmentResponseSerializer")
    @patch("openassessment.xblock.ui_mixins.mfe.page_context_serializer.SubmissionSerializer")
    @scenario("data/basic_scenario.xml", user_id="Alan")
    def test_assessment_view(self, xblock, mock_submission_serializer, mock_assessment_serializer):
        # Given we are asking for the assessment view
        self.create_test_submission(xblock)
        context = {"view": "assessment", "step": "peer"}

        # When I ask for assessment data
        _ = PageDataSerializer(xblock, context=context).data

        # Then I use the correct serializer and the call doesn't fail
        mock_assessment_serializer.assert_called_once()
        mock_submission_serializer.assert_not_called()


@ddt.ddt
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
        self.context = {"view": "assessment", "step": "submission"}

        # When I load my response
        # Then I get an Exception
        with self.assertRaises(Exception):
            _ = PageDataSerializer(xblock, context=self.context).data

    @scenario("data/student_training.xml", user_id="Alan")
    def test_student_training(self, xblock):
        # Given we are on the student training step
        self.create_test_submission(xblock)
        self.context = {"view": "assessment", "step": "training"}

        # When I load my response
        response_data = PageDataSerializer(xblock, context=self.context).data["response"]

        # I get the appropriate response
        expected_response = {
            "textResponses": ["This is my answer."],
            "uploadedFiles": None,
            "teamUploadedFiles": None,
        }
        self.assertDictEqual(expected_response, response_data)

    @ddt.data(True, False)
    @scenario("data/peer_only_scenario.xml", user_id="Alan")
    def test_peer_response(self, xblock, request_peer):
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

        # ... and I do or do not have a submission assigned to me for grading
        if request_peer:
            xblock.peer_assessment_data().get_peer_submission()

        # When I load my response
        self.context = {"view": "assessment", "step": "peer"}
        response_data = PageDataSerializer(xblock, context=self.context).data["response"]

        # I get my current assessment, if I had one, and if I didn't, one is assigned to me
        expected_response = {
            "textResponses": other_text_responses,
            "uploadedFiles": None,
            "teamUploadedFiles": None,
        }
        self.assertDictEqual(expected_response, response_data)

    @scenario("data/peer_only_scenario.xml", user_id="Alan")
    def test_peer_response_not_available(self, xblock):
        # Given I am on the peer grading step
        self.create_test_submission(xblock)

        # ... but with no responses to assess

        # When I load my response
        self.context = {"view": "assessment", "step": "peer"}
        response_data = PageDataSerializer(xblock, context=self.context).data["response"]

        # I get the appropriate response
        expected_response = {}
        self.assertDictEqual(expected_response, response_data)

    @scenario("data/staff_grade_scenario.xml", user_id="Alan")
    def test_staff_response(self, xblock):
        # Given I'm on the staff step
        self.create_test_submission(xblock)

        # When I load my response
        self.context = {"view": "assessment", "step": "staff"}
        response_data = PageDataSerializer(xblock, context=self.context).data["response"]

        # Then I get an empty object
        expected_response = {}
        self.assertDictEqual(expected_response, response_data)

    @scenario("data/staff_grade_scenario.xml", user_id="Alan")
    def test_waiting_response(self, xblock):
        # Given I'm on the staff step
        self.create_test_submission(xblock)

        # When I load my response
        self.context = {"view": "assessment", "step": "staff"}
        response_data = PageDataSerializer(xblock, context=self.context).data["response"]

        # Then I get an empty object
        expected_response = {}
        self.assertDictEqual(expected_response, response_data)

    @scenario("data/self_assessment_scenario.xml", user_id="Alan")
    def test_done_response(self, xblock):
        # Given I'm on the done step
        submission_text = ["Danger", "Will Robinson"]
        self.create_submission_and_assessments(xblock, submission_text, [], [], SELF_ASSESSMENT)

        # When I load my response
        self.context = {"view": "assessment", "step": "done"}
        response_data = PageDataSerializer(xblock, context=self.context).data["response"]

        # Then I get my response back
        expected_response = {
            "textResponses": submission_text,
            "uploadedFiles": [],
            "teamUploadedFiles": None,
        }
        self.assertDictEqual(expected_response, response_data)

    @scenario("data/grade_scenario_peer_only.xml", user_id="Bernard")
    def test_jump_to_peer_response__no_active_assessment(self, xblock):
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
        self.context = {"view": "assessment", "step": "done"}
        self.context["jump_to_step"] = "peer"
        response_data = PageDataSerializer(xblock, context=self.context).data

        # I recieve an empty response because I have not yet requested a submission to assess
        self.assertDictEqual({}, response_data["response"])

    @scenario("data/grade_scenario_peer_only.xml", user_id="Bernard")
    def test_jump_to_peer_response__active_assessment(self, xblock):
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

        # ... and I have been assigned a peer submission to review
        sub = xblock.peer_assessment_data().get_peer_submission()
        self.assertIsNotNone(sub)

        # When I try to jump back to that step
        self.context = {"view": "assessment", "step": "done"}
        self.context["jump_to_step"] = "peer"
        response_data = PageDataSerializer(xblock, context=self.context).data

        # Then I can continue to receive peer responses to grade
        expected_response = {
            "textResponses": other_text_responses,
            "uploadedFiles": None,
            "teamUploadedFiles": None,
        }
        self.assertDictEqual(expected_response, response_data["response"])

    @scenario("data/grade_scenario_peer_only.xml", user_id="Bernard")
    def test_jump_to_bad_step(self, xblock):
        # Given I'm on assessment steps
        self.create_test_submission(xblock)

        # When I try to jump to a bad step
        self.context = {"view": "assessment", "step": "peer"}
        self.context["jump_to_step"] = "to the left"

        # Then I expect the serializer to raise an exception
        # NOTE - this is exceedingly unlikely since the handler should only add
        # this context when the step name is valid.
        with self.assertRaises(Exception):
            _ = PageDataSerializer(xblock, context=self.context).data

    @scenario("data/self_only_scenario.xml", user_id="Alan")
    def test_self_response(self, xblock):
        # Given I am on the self grading step
        submission_text = ["This is MYYYYYY submissionnninoinoioin", "also this"]
        self.create_test_submission(xblock, submission_text=submission_text)

        # When I load my response
        self.context = {"view": "assessment", "step": "self"}
        response_data = PageDataSerializer(xblock, context=self.context).data["response"]

        # I get the appropriate response
        expected_response = {
            "textResponses": submission_text,
            "uploadedFiles": [],
            "teamUploadedFiles": None,
        }
        self.assertDictEqual(expected_response, response_data)


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
            "stepInfo": {
                "submission": {
                    "closed": False,
                    "closedReason": None,
                    "hasSubmitted": False,
                    "hasCancelled": False,
                    "cancelledAt": None,
                    "cancelledBy": None,
                    "teamInfo": {},
                },
                "peer": None,
                "self": None
            },
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
                "submission": {
                    "closed": False,
                    "closedReason": None,
                    "hasSubmitted": True,
                    "hasCancelled": False,
                    "cancelledAt": None,
                    "cancelledBy": None,
                    "teamInfo": {},
                },
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
                "submission": {
                    "closed": True,
                    "closedReason": "pastDue",
                    "hasSubmitted": True,
                    "hasCancelled": False,
                    "cancelledAt": None,
                    "cancelledBy": None,
                    "teamInfo": {},
                },
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
                "submission": {
                    "closed": False,
                    "closedReason": None,
                    "hasSubmitted": True,
                    "hasCancelled": False,
                    "cancelledAt": None,
                    "cancelledBy": None,
                    "teamInfo": {},
                },
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
                "submission": {
                    "closed": False,
                    "closedReason": None,
                    "hasSubmitted": True,
                    "hasCancelled": False,
                    "cancelledAt": None,
                    "cancelledBy": None,
                    "teamInfo": {},
                },
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

    @scenario("data/peer_only_scenario.xml", user_id="Alan")
    def test_peer_assessment__cancelled(self, xblock):
        # Given I am on the peer step and then get cancelled
        submission = self.create_test_submission(xblock)
        staff_id, staff_username = 'staff12341234', 'Staff 1234'
        cancel_workflow(submission['uuid'], "Test Cancel", staff_id, {}, {})

        mock_cancellation_info = {
            "cancelled_by": staff_username,
            "cancelled_at": "2023-10-25T10:27:04.432546",
        }
        mock_get_cancellation_info = PropertyMock(return_value=mock_cancellation_info)
        with patch.object(SubmissionAPI, 'cancellation_info', new_callable=mock_get_cancellation_info):
            # When I ask for progress
            context = {"step": "peer"}
            progress_data = ProgressSerializer(xblock, context=context).data

        # Then I get the expected shapes
        expected_data = {
            "activeStepName": "submission",
            "hasReceivedFinalGrade": False,
            "receivedGrades": {
                "peer": {},
                "staff": {},
            },
            "stepInfo": {
                "submission": {
                    "closed": False,
                    "closedReason": None,
                    "hasSubmitted": True,
                    "hasCancelled": True,
                    "cancelledAt": mock_cancellation_info["cancelled_at"],
                    "cancelledBy": staff_username,
                    "teamInfo": {},
                },
                "peer": None,
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
                "submission": {
                    "closed": False,
                    "closedReason": None,
                    "hasSubmitted": True,
                    "hasCancelled": False,
                    "cancelledAt": None,
                    "cancelledBy": None,
                    "teamInfo": {},
                },
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
                "submission": {
                    "closed": True,
                    "closedReason": "pastDue",
                    "hasSubmitted": True,
                    "hasCancelled": False,
                    "cancelledAt": None,
                    "cancelledBy": None,
                    "teamInfo": {},
                },
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
                "submission": {
                    "closed": False,
                    "closedReason": None,
                    "hasSubmitted": True,
                    "hasCancelled": False,
                    "cancelledAt": None,
                    "cancelledBy": None,
                    "teamInfo": {},
                },
                "peer": None,
                "self": {
                    "closed": True,
                    "closedReason": "notAvailableYet",
                },
            },
        }

        self.assertNestedDictEquals(expected_data, progress_data)

    @skip
    @scenario("data/team_submission.xml", user_id="Alan")
    def test_team_assignment(self, xblock):
        # Given I am on a team assignment
        setup_mock_team(xblock)
        xblock.is_team_assignment = Mock(return_value=True)
        self.create_test_submission(xblock)

        create_team_submission(
            xblock.get_student_item_dict(),
            {"answer": {"parts": ["a", "b"]}},
            xblock.config_data,
            xblock.submission_data,
            xblock.workflow_data
        )

        # When I ask for progress
        context = {"step": "staff"}
        progress_data = ProgressSerializer(xblock, context=context).data

        # Then I get the expected shapes
        expected_data = {
            "activeStepName": "staff",
            "hasReceivedFinalGrade": False,
            "receivedGrades": {
                # NOTE - Teams actually have a different step type that should go here
            },
            "stepInfo": {
                "submission": {
                    "closed": False,
                    "closedReason": None,
                    "hasSubmitted": True,
                    "hasCancelled": False,
                    "cancelledAt": None,
                    "cancelledBy": None,
                    "teamInfo": {
                        "teamName": "Red Squadron",
                        "teamUsernames": ["Red Leader", "Red Two", "Red Five"],
                        "previousTeamName": None,
                        "hasSubmitted": True,
                    },
                },
            },
        }

        self.assertNestedDictEquals(expected_data, progress_data)


class TestTeamInfoSerializer(TestCase):
    def test_serialize(self):
        team_info = {
            'team_name': 'Team1',
            'team_usernames': ['Bob', 'Alice'],
            'previous_team_name': 'Team4',
            'has_submitted': True,
            'team_uploaded_files': [
                TeamFileDescriptor('www.example.com/files/123', 'desc-123', 'name-123', 123, 'Chrissy')._asdict(),
                TeamFileDescriptor('www.example.com/files/5555', 'desc-5555', 'name-5555', 5555, 'Billy')._asdict(),
            ]
        }
        assert TeamInfoSerializer(team_info).data == {
            'teamName': 'Team1',
            'teamUsernames': ['Bob', 'Alice'],
            'previousTeamName': 'Team4',
            'hasSubmitted': True,
        }

    def test_no_team(self):
        team_info = {
            'team_uploaded_files': []
        }
        assert not TeamInfoSerializer(team_info).data

    def test_no_files(self):
        team_info = {
            'team_name': 'Team1',
            'team_usernames': ['Bob', 'Alice'],
            'previous_team_name': None,
            'has_submitted': False,
            'team_uploaded_files': []
        }
        assert TeamInfoSerializer(team_info).data == {
            'teamName': 'Team1',
            'teamUsernames': ['Bob', 'Alice'],
            'previousTeamName': None,
            'hasSubmitted': False,
        }
