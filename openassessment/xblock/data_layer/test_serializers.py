"""
Tests for data layer of ORA XBlock
"""

import ddt
import pytest

from openassessment.xblock.defaults import (
    DEFAULT_RUBRIC_FEEDBACK_PROMPT,
    DEFAULT_RUBRIC_FEEDBACK_TEXT,
)

from openassessment.xblock.data_layer.serializers import (
    AssessmentStepsSerializer,
    LeaderboardConfigSerializer,
    RubricConfigSerializer,
)
from openassessment.xblock.test.base import XBlockHandlerTestCase, scenario


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
        self.assertEqual(rubric_config["show_during_response"], mock_show_rubric)

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
        self.assertTrue(criterion["feedback_enabled"])
        self.assertTrue(criterion["feedback_required"])

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
        self.assertTrue(criterion["feedback_enabled"])
        self.assertTrue(criterion["feedback_required"])

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
        feedback_config = RubricConfigSerializer(xblock).data["feedback_config"]

        # Then I get the expected defaults
        self.assertEqual(feedback_config["description"], xblock.rubric_feedback_prompt)
        self.assertEqual(
            feedback_config["default_text"], xblock.rubric_feedback_default_text
        )


class TestAssessmentStepsSerializer(XBlockHandlerTestCase):
    """
    Test for AssessmentStepsSerializer
    """

    @scenario("data/basic_scenario.xml")
    def test_order(self, xblock):
        # Given a basic setup
        expected_order = ["peer-assessment", "self-assessment"]
        expected_step_keys = {"training_step", "peer_step", "self_step", "staff_step"}

        # When I ask for assessment step config
        steps_config = AssessmentStepsSerializer(xblock).data

        # Then I get the right ordering and step keys
        self.assertListEqual(steps_config["order"], expected_order)
        steps = {step for step in steps_config["settings"].keys()}
        self.assertSetEqual(steps, expected_step_keys)


class TestPeerSettingsSerializer(XBlockHandlerTestCase):
    """Tests for PeerSettingsSerializer"""

    @scenario("data/basic_scenario.xml")
    def test_peer_settings(self, xblock):
        # Given a basic setup
        expected_must_grade = 5
        expected_grade_by = 3

        # When I ask for peer step config
        peer_config = AssessmentStepsSerializer(xblock).data["settings"]["peer_step"]

        # Then I get the right config
        self.assertEqual(peer_config["min_number_to_grade"], expected_must_grade)
        self.assertEqual(peer_config["min_number_to_be_graded_by"], expected_grade_by)

    @scenario("data/dates_scenario.xml")
    def test_peer_dates(self, xblock):
        # Given a basic setup
        expected_start = "2015-01-02T00:00:00"
        expected_due = "2015-04-01T00:00:00"

        # When I ask for peer step config
        peer_config = AssessmentStepsSerializer(xblock).data["settings"]["peer_step"]

        # Then I get the right dates
        self.assertEqual(peer_config["start"], expected_start)
        self.assertEqual(peer_config["due"], expected_due)

    @scenario("data/peer_assessment_flex_grading_scenario.xml")
    def test_flex_grading(self, xblock):
        # Given a peer step with flex grading

        # When I ask for peer step config
        peer_config = AssessmentStepsSerializer(xblock).data["settings"]["peer_step"]

        # Then I get the right steps and ordering
        self.assertTrue(peer_config["flexible_grading"])


class TestTrainingSettingsSerializer(XBlockHandlerTestCase):
    """
    Test for TrainingSettingsSerializer
    """

    step_config_key = "training_step"

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

    step_config_key = "self_step"

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

    step_config_key = "staff_step"

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
        self.assertEqual(leaderboard_config["number_to_show"], number_to_show)

    @scenario("data/basic_scenario.xml")
    def test_no_leaderboard(self, xblock):
        # Given I don't have a leaderboard configured
        # When I ask for leaderboard config
        leaderboard_config = LeaderboardConfigSerializer(xblock).data

        # Then I get the expected config
        self.assertFalse(leaderboard_config["enabled"])
        self.assertEqual(leaderboard_config["number_to_show"], 0)
