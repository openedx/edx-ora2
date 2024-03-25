"""This module contains functions that determine if a learner's assessment is eligible for resubmission."""

from datetime import datetime, timedelta
import pytz


def allow_resubmission(config_data, workflow_data, submission_data: dict) -> bool:
    """
    Determines if a learner can reset their submission and try again. A learner
    can resubmit if the following conditions are met:
    - Whether the assignment allows learner resubmissions
    - Whether the submission date has not been exceeded
    - Whether the learner's response has not been graded by peers or staff

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
        has_been_graded(workflow_data)
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

    days = config_data.resubmissions_grace_period_days
    hours, minutes = list(map(int, config_data.resubmissions_grace_period_time.split(":")))
    if not days and not hours and not minutes:
        return False

    current_datetime = datetime.now(pytz.UTC)
    grace_period = timedelta(days=days, hours=hours, minutes=minutes)
    deadline_datetime = submission_data["created_at"] + grace_period
    return current_datetime >= deadline_datetime


def has_been_graded(workflow_data) -> bool:
    """
    Checks if the learner's submission hasn't been graded by peers or staff.

    Args:
        workflow_data (WorkflowAPI): Object containing necessary data for time and workflow status checks.

    Returns:
        bool: True if the learner's response hasn't been graded by peers or staff, False otherwise.
    """
    if workflow_data.status == "waiting":
        return False

    if workflow_data.status in ["done", "cancelled"]:
        return True

    status_details = workflow_data.status_details

    # If the learner has been graded by at least one peer
    graded_by_count = status_details.get("peer", {}).get("graded_by_count")
    if graded_by_count is not None and graded_by_count > 0:
        return True

    return False
