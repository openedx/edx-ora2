"""This module contains the tests for the allow_resubmission module."""

import datetime
import unittest
from unittest.mock import patch, Mock

import ddt

from openassessment.xblock.utils.allow_resubmission import allow_resubmission, has_been_graded


class ConfigDataMock:
    """Mock class for the ORAConfigAPI object."""

    def __init__(self):
        self.allow_learner_resubmissions = True
        self.resubmissions_grace_period = ""
        self.assessment_steps = ["staff-assessment"]

    def is_closed(self, step: str):  # pylint: disable=unused-argument
        return (False, None, None, None)


class WorkflowDataMock:
    """Mock class for the WorkflowAPI object."""

    def __init__(self):
        self.status = "waiting"
        self.status_details = {
            "staff": {"complete": True, "graded": False, "skipped": False},
            "peer": {
                "complete": False,
                "graded": False,
                "skipped": True,
                "peers_graded_count": 0,
                "graded_by_count": 0,
            },
        }


@ddt.ddt
class TestAllowResubmission(unittest.TestCase):
    """Tests for the allow_resubmission module."""

    patch_submission_lock = patch(
        "openassessment.xblock.utils.allow_resubmission.SubmissionGradingLock.get_submission_lock"
    )

    def setUp(self):
        self.config_data = ConfigDataMock()
        self.workflow_data = WorkflowDataMock()
        self.submission_data = {
            "created_at": datetime.datetime.now(tz=datetime.timezone.utc),
            "uuid": "submission_uuid",
        }

    @patch_submission_lock
    def test_allow_resubmission_all_conditions_met(self, submission_lock_mock: Mock):
        """
        Test case for the `allow_resubmission` function when all conditions are met.

        This test checks if the function returns True when:
        - Learner resubmissions are allowed
        - The submission date has not been exceeded
        - The submission has not been graded
        - The submission does not have a grade in process
        - The assessment has not a peer step
        """
        submission_lock_mock.return_value = None

        result = allow_resubmission(
            self.config_data, self.workflow_data, self.submission_data
        )

        self.assertTrue(result)

    @ddt.data(
        "01:00:00",
        "00:00:30",
        "10:00:59",
        "00:10:00"
    )
    @patch_submission_lock
    def test_allow_resubmission_resubmissions_with_grace_period(
        self, time: str, submission_lock_mock: Mock
    ):
        """
        Test case for the `allow_resubmission` function when the resubmissions grace period is set.
        """
        self.config_data.resubmissions_grace_period = time
        submission_lock_mock.return_value = None

        result = allow_resubmission(
            self.config_data, self.workflow_data, self.submission_data
        )

        self.assertTrue(result)

    def test_allow_resubmission_resubmissions_with_grace_period_exceeded(self):
        """
        Test case for the `allow_resubmission` function when the resubmissions grace period is exceeded.
        """
        self.submission_data["created_at"] = datetime.datetime(
            2020, 1, 1, tzinfo=datetime.timezone.utc
        )
        self.config_data.resubmissions_grace_period = "00:00:30"

        result = allow_resubmission(
            self.config_data, self.workflow_data, self.submission_data
        )

        self.assertFalse(result)

    def test_allow_resubmission_resubmissions_not_allowed(self):
        """
        Test case for the `allow_resubmission` function when learner resubmissions are not allowed.
        """
        self.config_data.allow_learner_resubmissions = False

        result = allow_resubmission(
            self.config_data, self.workflow_data, self.submission_data
        )

        self.assertFalse(result)

    def test_allow_resubmission_submission_date_exceeded(self):
        """
        Test case for the `allow_resubmission` function when the submission date has been exceeded.
        """
        self.config_data.is_closed = lambda step: (True, "due", None, None)

        result = allow_resubmission(
            self.config_data, self.workflow_data, self.submission_data
        )

        self.assertFalse(result)

    @ddt.data("done", "cancelled")
    def test_allow_resubmission_has_been_graded_or_cancelled(self, status: str):
        """
        Test case for the `allow_resubmission` function when the
        learner's response has been graded or cancelled.
        """
        self.workflow_data.status = status

        result = allow_resubmission(
            self.config_data, self.workflow_data, self.submission_data
        )

        self.assertFalse(result)

    @patch_submission_lock
    def test_allow_resubmission_has_peer_step(self, submission_lock_mock: Mock):
        """
        Test case for the `allow_resubmission` function when the assignment has a peer step.
        """
        self.config_data.assessment_steps = ["peer-assessment"]
        submission_lock_mock.return_value = None

        result = allow_resubmission(
            self.config_data, self.workflow_data, self.submission_data
        )

        self.assertFalse(result)

    @patch_submission_lock
    def test_allow_resubmission_has_grade_in_process(self, submission_lock_mock: Mock):
        """
        Test case for the `allow_resubmission` function when the submission has a grade in process.
        """
        submission_lock_mock.return_value = Mock(is_active=True)

        result = allow_resubmission(
            self.config_data, self.workflow_data, self.submission_data
        )

        self.assertFalse(result)

    @ddt.data(
        ("waiting", False),
        ("done", True),
        ("cancelled", True),
        ("another_status", False),
    )
    @ddt.unpack
    def test_has_been_graded(self, status: str, expected: bool):
        """
        Test case for the `has_been_graded` function.
        """
        self.workflow_data.status = status

        result = has_been_graded(self.workflow_data)

        self.assertEqual(result, expected)
