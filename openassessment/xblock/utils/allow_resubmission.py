"""This module contains functions that determine if a learner's assessment is eligible for resubmission."""

from datetime import datetime, timedelta
import pytz

from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock


def allow_resubmission(config_data, workflow_data, submission_data: dict) -> bool:
    """
    Determines if a learner can reset their submission and try again. A learner
    can resubmit if the following conditions are met:
    - Whether the assignment allows learner resubmissions
    - Whether the submission date has not been exceeded
    - Whether the learner's response has not been graded staff
    - Whether the learner's response has not a grade in process
    - Wheter the assignment has not a peer step

    Args:
        config_data (ORAConfigAPI): Object with all the configuration data of the ORA assignment.
        workflow_data (WorkflowAPI): Object containing necessary data for time and workflow status checks.
        submission_data (dict): Dictionary containing the submission data of the learner.

    Returns:
        bool: True if the learner's submission is eligible for retry, False otherwise.
    """
    return (
        allow_learner_resubmissions(config_data) and not
        submission_date_exceeded(config_data, submission_data) and not
        has_been_graded(workflow_data) and not
        has_grade_in_process(submission_data["uuid"]) and not
        has_peer_step(config_data)
    )


def allow_learner_resubmissions(config_data) -> bool:
    """
    Checks if the ORA assignment allows learner resubmissions.

    Args:
        config_data (ORAConfigAPI): Object with all the configuration data of the ORA assignment.

    Returns:
        bool: True if the assignment allows learner resubmissions, False otherwise
    """
    return config_data.allow_learner_resubmissions


def submission_date_exceeded(config_data, submission_data: dict) -> bool:
    """
    Checks if the submission due date has been exceeded and if the learner is
    within the grace period. The grace period is the time after the learner
    submission date that the learner can still resubmit their response.

    If the grace period is set to 0 days, 0 hours and 0 minutes, means that the learner
    can resubmit their response at any time before the submission due date.

    Args:
        config_data (ORAConfigAPI): Object with all the configuration data of the ORA assignment.
        submission_data (dict): Dictionary containing the submission data of the learner.

    Returns:
        bool: True if the submission date has been exceeded, False otherwise.
    """
    is_closed, reason, _, _ = config_data.is_closed(step="submission")
    if is_closed and reason == "due":
        return True

    if not config_data.resubmissions_grace_period:
        return False

    days, hours, minutes = list(map(int, config_data.resubmissions_grace_period.split(":")))
    current_datetime = datetime.now(pytz.UTC)
    grace_period = timedelta(days=days, hours=hours, minutes=minutes)
    deadline_datetime = submission_data["created_at"] + grace_period
    return current_datetime > deadline_datetime


def has_been_graded(workflow_data) -> bool:
    """
    Checks if the learner's submission hasn't been graded staff.

    Args:
        workflow_data (WorkflowAPI): Object containing necessary data for time and workflow status checks.

    Returns:
        bool: True if the learner's response hasn't been graded staff, False otherwise.
    """
    if workflow_data.status == "waiting":
        return False

    if workflow_data.status in ["done", "cancelled"]:
        return True

    return False


def has_peer_step(config_data) -> bool:
    """
    Checks if the ORA assignment has a peer step.

    Args:
        config_data (ORAConfigAPI): Object with all the configuration data of the ORA assignment.

    Returns:
        bool: True if the assignment has a peer step, False otherwise.
    """
    return "peer-assessment" in config_data.assessment_steps


def has_grade_in_process(submission_uuid: str) -> bool:
    """
    Check if the submission has a grade in process.

    Args:
        submission_uuid (str): The UUID of the submission.

    Returns:
        bool: True if the submission has a grade in process, False otherwise.
    """
    lock = SubmissionGradingLock.get_submission_lock(submission_uuid)
    return lock is not None and lock.is_active
