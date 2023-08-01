"""
Tests for data layer of ORA XBlock
"""

from openassessment.xblock.data_layer.serializers import (
    AssessmentStepsSerializer,
    LeaderboardConfigSerializer,
)
from openassessment.xblock.test.base import XBlockHandlerTestCase, scenario


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
