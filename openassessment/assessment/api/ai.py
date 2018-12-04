"""
Public interface for ai-assessment.
"""
import logging

from submissions import api as submissions_api

logger = logging.getLogger("openassessment.assessment.api.ai")

AI_TYPE = "AI"


def on_init(submission_uuid):
    """
    Create a new ai workflow for a student item and submission.

    Creates a unique staff workflow for a student item, associated with a
    submission.

    Note that the staff workflow begins things in on_init() instead of
    on_start(), because staff should be able to access the submission
    regardless of which state the workflow is currently in.

    Args:
        submission_uuid (str): The submission associated with this workflow.

    Returns:
        None

    Raises:
        StaffAssessmentInternalError: Raised when there is an internal error
            creating the Workflow.

    """
    # in progress


