"""
Tests for data layer of ORA XBlock
"""

from unittest.mock import MagicMock

import ddt


from openassessment.xblock.ui_mixins.mfe.serializers import (
    AssessmentStepsSerializer,
    LeaderboardConfigSerializer,
    RubricConfigSerializer,
    SubmissionConfigSerializer,
)
from openassessment.xblock.test.base import XBlockHandlerTestCase, scenario


class TestSubmissionConfigSerializer(XBlockHandlerTestCase):
    """
    Test for SubmissionConfigSerializer
    """

    def _enable_team_ora(self, xblock):
        """Utility function for mocking team dependencies on the passed xblock"""
        xblock.is_team_assignment = MagicMock(return_value=True)

        xblock.teamset_config = MagicMock()
        xblock.teamset_config.name = xblock.selected_teamset_id

    @scenario("data/submission_open.xml")
    def test_dates(self, xblock):
        # Given an individual (non-teams) ORA
        xblock.teamset_config = MagicMock(return_value=None)

        # When I ask for the submission config
        submission_config = SubmissionConfigSerializer(xblock).data

        # Then I get the expected values
        expected_start = xblock.submission_start
        expected_due = xblock.submission_due
        self.assertEqual(submission_config["startDatetime"], expected_start)
        self.assertEqual(submission_config["endDatetime"], expected_due)

    @scenario("data/basic_scenario.xml")
    def test_dates_missing(self, xblock):
        # Given an individual (non-teams) ORA
        xblock.teamset_config = MagicMock(return_value=None)

        # When I ask for submission config
        submission_config = SubmissionConfigSerializer(xblock).data

        # Then I get the expected values
        self.assertIsNone(submission_config["startDatetime"])
        self.assertIsNone(submission_config["endDatetime"])

    @scenario("data/basic_scenario.xml")
    def test_text_response_config(self, xblock):
        # Given an individual (non-teams) ORA with a text response
        xblock.teamset_config = MagicMock(return_value=None)

        # When I ask for text response config
        submission_config = SubmissionConfigSerializer(xblock).data
        text_response_config = submission_config["textResponseConfig"]

        # Then I get the expected values
        self.assertTrue(text_response_config["enabled"])
        self.assertTrue(text_response_config["required"])
        self.assertEqual(text_response_config["editorType"], "text")
        self.assertFalse(text_response_config["allowLatexPreview"])

    @scenario("data/basic_scenario.xml")
    def test_html_response_config(self, xblock):
        # Given an individual (non-teams) ORA with an html response
        xblock.teamset_config = MagicMock(return_value=None)
        xblock.text_response_editor = "html"

        # When I ask for text response config
        submission_config = SubmissionConfigSerializer(xblock).data
        text_response_config = submission_config["textResponseConfig"]

        # Then I get the expected values
        self.assertEqual(text_response_config["editorType"], "html")

    @scenario("data/basic_scenario.xml")
    def test_latex_preview(self, xblock):
        # Given an individual (non-teams) ORA
        xblock.teamset_config = MagicMock(return_value=None)
        # ... with latex preview enabled
        xblock.allow_latex = True

        # When I ask for text response config
        submission_config = SubmissionConfigSerializer(xblock).data
        text_response_config = submission_config["textResponseConfig"]

        # Then I get the expected values
        self.assertTrue(text_response_config["allowLatexPreview"])

    @scenario("data/file_upload_scenario.xml")
    def test_file_response_config(self, xblock):
        # Given an individual (non-teams) ORA with file upload enabled
        xblock.teamset_config = MagicMock(return_value=None)

        # When I ask for file upload config
        submission_config = SubmissionConfigSerializer(xblock).data
        file_response_config = submission_config["fileResponseConfig"]

        # Then I get the expected values
        self.assertTrue(file_response_config["enabled"])
        self.assertEqual(
            file_response_config["fileUploadLimit"], xblock.MAX_FILES_COUNT
        )
        self.assertEqual(
            file_response_config["fileTypeDescription"],
            xblock.file_upload_type,
        )
        self.assertEqual(
            file_response_config["allowedExtensions"],
            xblock.get_allowed_file_types_or_preset(),
        )
        self.assertEqual(
            file_response_config["blockedExtensions"], xblock.FILE_EXT_BLACK_LIST
        )

    @scenario("data/team_submission.xml")
    def test_team_ora_config(self, xblock):
        # Given a team ORA
        self._enable_team_ora(xblock)

        # When I ask for teams config
        submission_config = SubmissionConfigSerializer(xblock).data
        teams_config = submission_config["teamsConfig"]

        # Then I get the expected values
        self.assertTrue(teams_config["enabled"])
        self.assertEqual(teams_config["teamsetName"], xblock.selected_teamset_id)


@ddt.ddt
class TestRubricConfigSerializer(XBlockHandlerTestCase):
    """
    Test for RubricConfigSerializer
    """

    @ddt.data(True, False)
    @scenario("data/basic_scenario.xml")
    def test_show_during_response(self, xblock, mock_show_rubric):
        # Given a basic setup where I do/not have rubric shown during response
        xblock.show_rubric_during_response = mock_show_rubric

        # When I ask for rubric config
        rubric_config = RubricConfigSerializer(xblock).data

        # Then I get the right values
        self.assertEqual(rubric_config["showDuringResponse"], mock_show_rubric)

    @scenario("data/feedback_only_criterion_staff.xml")
    def test_overall_feedback(self, xblock):
        # Given an ORA block with one criterion

        # When I ask for rubric config
        rubric_config = RubricConfigSerializer(xblock).data

        # Then I get the expected defaults
        criteria = rubric_config["criteria"]
        criterion = criteria[0]
        self.assertEqual(len(criteria), 1)
        self.assertEqual(criterion["name"], "vocabulary")
        self.assertEqual(
            criterion["description"],
            "This criterion accepts only written feedback, so it has no options",
        )

        # ... In this example, feedback is required
        self.assertTrue(criterion["feedbackEnabled"])
        self.assertTrue(criterion["feedbackRequired"])

    @scenario("data/feedback_only_criterion_staff.xml")
    def test_criterion(self, xblock):
        # Given an ORA block with one criterion

        # When I ask for rubric config
        rubric_config = RubricConfigSerializer(xblock).data

        # Then I get the expected defaults
        criteria = rubric_config["criteria"]
        criterion = criteria[0]
        self.assertEqual(len(criteria), 1)
        self.assertEqual(criterion["name"], "vocabulary")
        self.assertEqual(
            criterion["description"],
            "This criterion accepts only written feedback, so it has no options",
        )

        # ... In this example, feedback is required
        self.assertTrue(criterion["feedbackEnabled"])
        self.assertTrue(criterion["feedbackRequired"])

    @scenario("data/feedback_only_criterion_self.xml")
    def test_criterion_disabled_required(self, xblock):
        # Given an ORA block with two criterion

        # When I ask for rubric config
        rubric_config = RubricConfigSerializer(xblock).data

        # Then I get the expected defaults
        criteria = rubric_config["criteria"]

        # .. the first criterion has feedback disabled
        self.assertFalse(criteria[0]["feedbackEnabled"])
        self.assertFalse(criteria[0]["feedbackRequired"])

        # .. the first criterion has feedback required
        self.assertTrue(criteria[1]["feedbackEnabled"])
        self.assertTrue(criteria[1]["feedbackRequired"])

    @scenario("data/file_upload_missing_scenario.xml")
    def test_criterion_optional(self, xblock):
        # Given an ORA block with one criterion, feedback optional

        # When I ask for rubric config
        rubric_config = RubricConfigSerializer(xblock).data

        # Then I get the feedback enabled / required values
        criteria = rubric_config["criteria"]
        criterion = criteria[0]
        self.assertTrue(criterion["feedbackEnabled"])
        self.assertFalse(criterion["feedbackRequired"])

    @scenario("data/basic_scenario.xml")
    def test_criteria(self, xblock):
        # Given an ORA block with multiple criteria
        expected_criteria = xblock.rubric_criteria

        # When I ask for rubric config
        rubric_config = RubricConfigSerializer(xblock).data

        # Then I get the expected number of criteria
        criteria = rubric_config["criteria"]
        self.assertEqual(len(criteria), len(expected_criteria))

    @scenario("data/basic_scenario.xml")
    def test_feedback_config(self, xblock):
        # Given an ORA block with feedback
        xblock.rubric_feedback_prompt = "foo"
        xblock.rubric_feedback_default_text = "bar"

        # When I ask for rubric config
        feedback_config = RubricConfigSerializer(xblock).data["feedbackConfig"]

        # Then I get the expected defaults
        self.assertEqual(feedback_config["description"], xblock.rubric_feedback_prompt)
        self.assertEqual(
            feedback_config["defaultText"], xblock.rubric_feedback_default_text
        )


class TestAssessmentStepsSerializer(XBlockHandlerTestCase):
    """
    Test for AssessmentStepsSerializer
    """

    @scenario("data/basic_scenario.xml")
    def test_order(self, xblock):
        # Given a basic setup
        expected_order = ["peer-assessment", "self-assessment"]
        expected_step_keys = {"training", "peer", "self", "staff"}

        # When I ask for assessment step config
        steps_config = AssessmentStepsSerializer(xblock).data

        # Then I get the right ordering and step keys
        self.assertListEqual(steps_config["order"], expected_order)
        steps = set(steps_config["settings"].keys())
        self.assertSetEqual(steps, expected_step_keys)


class TestPeerSettingsSerializer(XBlockHandlerTestCase):
    """Tests for PeerSettingsSerializer"""

    step_config_key = "peer"

    @scenario("data/basic_scenario.xml")
    def test_peer_settings(self, xblock):
        # Given a basic setup
        expected_must_grade = 5
        expected_grade_by = 3

        # When I ask for peer step config
        peer_config = AssessmentStepsSerializer(xblock).data["settings"][
            self.step_config_key
        ]

        # Then I get the right config
        self.assertEqual(peer_config["minNumberToGrade"], expected_must_grade)
        self.assertEqual(peer_config["minNumberToBeGradedBy"], expected_grade_by)

    @scenario("data/dates_scenario.xml")
    def test_peer_dates(self, xblock):
        # Given a basic setup
        expected_start = "2015-01-02T00:00:00"
        expected_due = "2015-04-01T00:00:00"

        # When I ask for peer step config
        peer_config = AssessmentStepsSerializer(xblock).data["settings"][
            self.step_config_key
        ]

        # Then I get the right dates
        self.assertEqual(peer_config["startTime"], expected_start)
        self.assertEqual(peer_config["endTime"], expected_due)

    @scenario("data/peer_assessment_flex_grading_scenario.xml")
    def test_flex_grading(self, xblock):
        # Given a peer step with flex grading

        # When I ask for peer step config
        peer_config = AssessmentStepsSerializer(xblock).data["settings"][
            self.step_config_key
        ]

        # Then I get the right steps and ordering
        self.assertTrue(peer_config["enableFlexibleGrading"])


class TestTrainingSettingsSerializer(XBlockHandlerTestCase):
    """
    Test for TrainingSettingsSerializer
    """

    step_config_key = "training"

    @scenario("data/student_training.xml")
    def test_enabled(self, xblock):
        # Given an ORA with a training step
        # When I ask for step config
        step_config = AssessmentStepsSerializer(xblock).data["settings"][
            self.step_config_key
        ]

        # Then I get the right config
        self.assertTrue(step_config["required"])

    @scenario("data/basic_scenario.xml")
    def test_disabled(self, xblock):
        # Given an ORA without a training step
        # When I ask for step config
        step_config = AssessmentStepsSerializer(xblock).data["settings"][
            self.step_config_key
        ]

        # Then I get the right config
        self.assertFalse(step_config["required"])


class TestSelfSettingsSerializer(XBlockHandlerTestCase):
    """
    Test for SelfSettingsSerializer
    """

    step_config_key = "self"

    @scenario("data/self_assessment_scenario.xml")
    def test_enabled(self, xblock):
        # Given an ORA with a self assessment step
        # When I ask for step config
        step_config = AssessmentStepsSerializer(xblock).data["settings"][
            self.step_config_key
        ]

        # Then I get the right config
        self.assertTrue(step_config["required"])

    @scenario("data/peer_only_scenario.xml")
    def test_disabled(self, xblock):
        # Given an ORA without a self assessment step
        # When I ask for step config
        step_config = AssessmentStepsSerializer(xblock).data["settings"][
            self.step_config_key
        ]

        # Then I get the right config
        self.assertFalse(step_config["required"])


class TestStaffSettingsSerializer(XBlockHandlerTestCase):
    """
    Test for StaffSettingsSerializer
    """

    step_config_key = "staff"

    @scenario("data/staff_grade_scenario.xml")
    def test_enabled(self, xblock):
        # Given an ORA with a staff assessment step
        # When I ask for step config
        step_config = AssessmentStepsSerializer(xblock).data["settings"][
            self.step_config_key
        ]

        # Then I get the right config
        self.assertTrue(step_config["required"])

    @scenario("data/peer_only_scenario.xml")
    def test_disabled(self, xblock):
        # Given an ORA without a staff assessment step
        # When I ask for step config
        step_config = AssessmentStepsSerializer(xblock).data["settings"][
            self.step_config_key
        ]

        # Then I get the right config
        self.assertFalse(step_config["required"])


class TestLeaderboardConfigSerializer(XBlockHandlerTestCase):
    """
    Test for LeaderboardConfigSerializer
    """

    @scenario("data/leaderboard_show.xml")
    def test_leaderboard(self, xblock):
        # Given I have a leaderboard configured
        number_to_show = xblock.leaderboard_show

        # When I ask for leaderboard config
        leaderboard_config = LeaderboardConfigSerializer(xblock).data

        # Then I get the expected config
        self.assertTrue(leaderboard_config["enabled"])
        self.assertEqual(leaderboard_config["numberOfEntries"], number_to_show)

    @scenario("data/basic_scenario.xml")
    def test_no_leaderboard(self, xblock):
        # Given I don't have a leaderboard configured
        # When I ask for leaderboard config
        leaderboard_config = LeaderboardConfigSerializer(xblock).data

        # Then I get the expected config
        self.assertFalse(leaderboard_config["enabled"])
        self.assertEqual(leaderboard_config["numberOfEntries"], 0)
