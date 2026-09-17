"""
Tests for AssessmentResponseSerializer
"""
import json
from unittest.mock import patch

from django.test import TestCase
from openassessment.workflow import api as workflow_api
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
    AssessmentGradeSerializer,
    AssessmentScoreSerializer,
    AssessmentDataSerializer,
    AssessmentCriterionSerializer,
    AssessmentSubmitRequestSerializer,
)


class TestAssessmentResponseSerializer(XBlockHandlerTestCase, SubmissionTestMixin):
    """
    Test for AssessmentResponseSerializer
    """

    # Show full dictionary diff
    maxDiff = None

    @scenario("data/basic_scenario.xml", user_id="Alan")
    def test_no_response(self, xblock):  # pylint: disable=unused-argument
        # Given we don't have a response to serialize
        response = None

        # When I load my response
        data = AssessmentResponseSerializer(response).data

        # I get the appropriate response
        expected_response = {}
        self.assertDictEqual(expected_response, data)

    @scenario("data/basic_scenario.xml", user_id="Alan")
    def test_response(self, xblock):
        # Given we have a response
        submission_text = ["Foo", "Bar"]
        submission = self.create_test_submission(
            xblock, submission_text=submission_text
        )

        # When I load my response
        data = AssessmentResponseSerializer(submission).data

        # I get the appropriate response
        expected_response = {
            "textResponses": submission_text,
            "uploadedFiles": [],
            "teamUploadedFiles": None,
        }
        self.assertDictEqual(expected_response, data)

    @scenario("data/file_upload_scenario.xml", user_id="Alan")
    def test_files_empty(self, xblock):
        # Given we have a response
        submission_text = ["Foo", "Bar"]
        submission = self.create_test_submission(
            xblock, submission_text=submission_text
        )

        # When I load my response
        data = AssessmentResponseSerializer(submission).data

        # I get the appropriate response
        expected_response = {
            "textResponses": submission_text,
            "uploadedFiles": [],
            "teamUploadedFiles": None,
        }
        self.assertDictEqual(expected_response, data)

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
    @patch("openassessment.data.ZippedListSubmissionAnswer._safe_get_download_url")
    @scenario("data/file_upload_scenario.xml", user_id="Alan")
    def test_files(self, xblock, mock_get_download_url, mock_get_files):
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

        mock_urls = [
            f"Alan/edX/Enchantment_101/April_1/{xblock.scope_ids.usage_id}",
            None,
            f"Alan/edX/Enchantment_101/April_1/{xblock.scope_ids.usage_id}/2",
        ]

        mock_get_download_url.side_effect = mock_urls

        # When I load my response
        data = AssessmentResponseSerializer(submission).data

        # I get the appropriate response (test URLs use usage ID)
        expected_response = {
            "textResponses": submission_text,
            "uploadedFiles": [
                {
                    "fileUrl": mock_urls[0],
                    "fileDescription": "bar",
                    "fileName": "foo",
                    "fileSize": 1337,
                    "fileIndex": 0,
                },
                {
                    "fileUrl": mock_urls[2],
                    "fileDescription": "buzz",
                    "fileName": "baz",
                    "fileSize": 2049,
                    "fileIndex": 2,
                },
            ],
            "teamUploadedFiles": None,
        }
        self.assertDictEqual(expected_response, data)


class TestPeerSplit(XBlockHandlerTestCase, SubmitAssessmentsMixin):
    ASSESSMENT = {
        'options_selected': {'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': 'ﻉซƈﻉɭɭﻉกՇ', 'Form': 'Fair'},
        'criterion_feedback': {},
        'overall_feedback': ""
    }

    @scenario("data/grade_scenario.xml", user_id="Bernard")
    def test_scored_unscored(self, xblock):
        student_item = xblock.get_student_item_dict()
        submission = self.create_test_submission(
            xblock, student_item=student_item, submission_text=self.SUBMISSION
        )

        other_learners = ['u1', 'u2', 'u3', 'u4']
        # Create submissions from other users
        scorer_subs = self.create_peer_submissions(
            student_item, other_learners, self.SUBMISSION
        )

        # All four assess the target learner even though we only need two
        for scorer_sub, scorer_name in list(zip(scorer_subs, other_learners)):
            self.create_peer_assessment(
                scorer_sub,
                scorer_name,
                submission,
                self.ASSESSMENT,
                xblock.rubric_criteria,
                2,
            )

        # Have the target learner submit one assessment so they can recieve a grade, and update their status
        self.create_peer_assessment(submission, 'Bernard', scorer_subs[0], self.ASSESSMENT, xblock.rubric_criteria, 2)
        workflow_api.update_from_assessments(
            submission['uuid'],
            {'peer': {'must_be_graded_by': 2, 'must_grade': 1}},
            {}
        )

        context = {"response": submission, "step": "done"}

        # When I load my response
        data = AssessmentGradeSerializer(xblock.api_data, context=context).data

        # I get the appropriate response
        self.assertEqual("peer", data["effectiveAssessmentType"])
        self.assertEqual(data["peer"]["stepScore"], {'earned': 5, 'possible': 6})
        self.assertEqual(len(data["peer"]["assessments"]), 2)
        self.assertIsNone(data["peerUnweighted"]["stepScore"])
        self.assertEqual(len(data["peerUnweighted"]["assessments"]), 2)


class TestAssessmentGradeSerializer(XBlockHandlerTestCase, SubmitAssessmentsMixin):

    maxDiff = None

    def assertNestedDictEquals(self, dict_1, dict_2):
        # Manually expand nested dicts for comparison
        dict_1_expanded = json.loads(json.dumps(dict_1))
        dict_2_expanded = json.loads(json.dumps(dict_2))
        return self.assertDictEqual(dict_1_expanded, dict_2_expanded)

    ASSESSMENT = {
        'options_selected': {'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': 'ﻉซƈﻉɭɭﻉกՇ', 'Form': 'Fair'},
        'criterion_feedback': {},
        'overall_feedback': ""
    }

    @scenario("data/self_only_scenario.xml", user_id="Alan")
    def test_self_assessment_step(self, xblock):
        submission_text = ["Foo", "Bar"]

        submission = self.create_test_submission(
            xblock, submission_text=submission_text
        )

        context = {"response": submission, "step": "done"}

        # The self-only example uses a different rubric
        self_assessment = {
            'options_selected': {'Concise': 'Robert Heinlein', 'Clear-headed': 'Spock', 'Form': 'Reddit'},
            'criterion_feedback': {},
            'overall_feedback': "I'm so cool",
        }

        resp = self.request(
            xblock, "self_assess", json.dumps(self_assessment), response_format="json"
        )
        self.assertTrue(resp["success"])

        # When I load my response
        data = AssessmentGradeSerializer(xblock.api_data, context=context).data

        # Then I get the appropriate assessment data
        expected_assessment_type = "self"
        self.assertEqual(expected_assessment_type, data["effectiveAssessmentType"])

        score_details = data[expected_assessment_type]
        self.assertDictEqual(score_details["assessment"], {
            "overallFeedback": self_assessment['overall_feedback'],
            "criteria": [
                {"selectedOption": 2, "feedback": ""},
                {"selectedOption": 4, "feedback": ""},
                {"selectedOption": 2, "feedback": ""},
            ]
        })
        self.assertDictEqual(score_details["stepScore"], {"earned": 15, "possible": 20})

    @scenario("data/grade_scenario.xml", user_id="Alan")
    def test_staff_assessment_step(self, xblock):
        submission_text = ["Foo", "Bar"]
        submission = self.create_test_submission(
            xblock, submission_text=submission_text
        )

        self.submit_staff_assessment(xblock, submission, STAFF_GOOD_ASSESSMENT)

        context = {"response": submission, "step": "done"}

        # When I load my response
        data = AssessmentGradeSerializer(xblock.api_data, context=context).data

        # Then I get the appropriate assessment data
        expected_assessment_type = "staff"
        self.assertEqual(expected_assessment_type, data["effectiveAssessmentType"])

        score_details = data[expected_assessment_type]
        self.assertNestedDictEquals(score_details["assessment"], {
            "overallFeedback": STAFF_GOOD_ASSESSMENT["overall_feedback"],
            "criteria": [
                {
                    "selectedOption": 0,
                    "feedback": '',
                },
                {
                    "selectedOption": 1,
                    "feedback": '',
                }
            ]
        })
        self.assertDictEqual(score_details["stepScore"], {"earned": 5, "possible": 6})

    @scenario("data/grade_scenario.xml", user_id="Bernard")
    def test_peer_assessment_steps(self, xblock):
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
        ):
            self.create_peer_assessment(
                scorer_sub,
                scorer_name,
                submission,
                assessment,
                xblock.rubric_criteria,
                graded_by,
            )

        context = {"response": submission, "step": "done"}

        # When I load my response
        data = AssessmentGradeSerializer(xblock.api_data, context=context).data

        # Then I get the appropriate assessment data
        expected_assessment_type = "peer"
        self.assertEqual(expected_assessment_type, data["effectiveAssessmentType"])

        score_details = data[expected_assessment_type]
        self.assertDictEqual(score_details, {'stepScore': None, 'assessments': []})

        self.assertIsNone(data["peerUnweighted"]['stepScore'])
        self.assertEqual(len(data["peerUnweighted"]['assessments']), len(self.PEERS))

    @scenario("data/grade_scenario.xml", user_id="Bernard")
    def test_staff_override(self, xblock):
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
        ):
            self.create_peer_assessment(
                scorer_sub,
                scorer_name,
                submission,
                assessment,
                xblock.rubric_criteria,
                graded_by,
            )

        # Create a staff override
        self.submit_staff_assessment(xblock, submission, STAFF_GOOD_ASSESSMENT)

        context = {"response": submission, "step": "done"}

        # When I load my response
        data = AssessmentGradeSerializer(xblock.api_data, context=context).data

        # Then I get the appropriate assessment data
        expected_assessment_type = "staff"
        self.assertEqual(expected_assessment_type, data["effectiveAssessmentType"])

        score_details = data[expected_assessment_type]
        # Feedback is disabled in this assignment
        self.assertNestedDictEquals(score_details["assessment"], {
            "overallFeedback": STAFF_GOOD_ASSESSMENT["overall_feedback"],
            "criteria": [
                {
                    "selectedOption": 0,
                    "feedback": '',
                },
                {
                    "selectedOption": 1,
                    "feedback": '',
                }
            ]
        })
        self.assertDictEqual(score_details["stepScore"], {"earned": 5, "possible": 6})

        # With peer responses all listed as unweighted
        self.assertDictEqual(data["peer"], {'stepScore': None, 'assessments': []})
        self.assertIsNone(data["peerUnweighted"]['stepScore'])
        self.assertEqual(len(data["peerUnweighted"]['assessments']), len(self.PEERS))


class TestAssessmentScoreSerializer(TestCase):
    """
    Test for AssessmentScoreSerializer
    """

    def test_assessment_score(self):
        score = AssessmentScoreSerializer({
            "points_earned": 5,
            "points_possible": 10,
        }).data
        self.assertEqual(score["earned"], 5)
        self.assertEqual(score["possible"], 10)


class TestAssessmentCriterionSerializer(TestCase):
    """
    Test for AssessmentCriterionSerializer
    """

    def test_assessment_criterion(self):
        criterion = AssessmentCriterionSerializer({
            "option": {
                "order_num": 3,
            },
            "feedback": "Baz",
        }).data
        self.assertEqual(criterion["selectedOption"], 3)
        self.assertEqual(criterion["feedback"], "Baz")


class TestAssessmentDataSerializer(TestCase):
    """
    Test for AssessmentDataSerializer
    """

    def test_assessment_data(self):
        assessment_data = AssessmentDataSerializer({
            "feedback": "Foo",
            "parts": [
                {
                    "option": {
                        "order_num": 3,
                    },
                    "feedback": "Baz",
                },
            ],
        }).data

        self.assertEqual(assessment_data["overallFeedback"], "Foo")
        self.assertEqual(len(assessment_data["criteria"]), 1)


class TestAssessmentSubmitRequestSerializer(TestCase):
    """
    Test for AssessmentSubmitRequestSerializer
    """

    def test_assessment_data(self):
        assessment_submit_request_data = AssessmentSubmitRequestSerializer({
            "criteria": [
                {
                    "selectedOption": 3,
                    "feedback": "Baz",
                }
            ],
            "overallFeedback": "Foo",
            "step": "Wham"
        }).data

        self.assertEqual(assessment_submit_request_data["overallFeedback"], "Foo")
        self.assertEqual(len(assessment_submit_request_data["criteria"]), 1)
        self.assertEqual(assessment_submit_request_data["step"], "Wham")
