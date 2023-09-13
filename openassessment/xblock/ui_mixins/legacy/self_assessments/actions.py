""" A mixin for self Assessments. """
import logging

from openassessment.assessment.api import self as self_api
from openassessment.workflow import api as workflow_api

from openassessment.xblock.utils.data_conversion import (
    clean_criterion_feedback,
    create_rubric_dict,
)

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

messages = {
    "must_submit": "You must submit a response before you can perform a self-assessment.",
    "could_not_submit": "Your self assessment could not be submitted.",
}


def self_assess(api_data, data, suffix=""):  # pylint: disable=unused-argument
    """
    Create a self-assessment for a submission.

    Args:
        data (dict): Must have the following keys:
            options_selected (dict): Dictionary mapping criterion names to option values.

    Returns:
        Dict with keys "success" (bool) indicating success/failure
        and "msg" (unicode) containing additional information if an error occurs.
    """
    # Import is placed here to avoid model import at project startup.
    translate = api_data.config_data.translate
    submission_uuid = api_data.submission_data.submission_uuid

    def failure_response(reason):
        return {"success": False, "msg": translate(reason)}

    if submission_uuid is None:
        return failure_response(messages["must_submit"])

    step_data = api_data.self_assessment_data
    try:
        assessment = self_api.create_assessment(
            step_data.submission_uuid,
            step_data.student_item_dict["student_id"],
            data["options_selected"],
            clean_criterion_feedback(step_data.rubric_criteria, data["criterion_feedback"]),
            data["overall_feedback"],
            create_rubric_dict(step_data.prompts, step_data.rubric_criteria_with_labels),
        )
        api_data.config_data.publish_assessment_event("openassessmentblock.self_assess", assessment)
        # After we've created the self-assessment, we need to update the workflow.
        api_data.workflow_data.update_workflow_status()
    except (
        self_api.SelfAssessmentRequestError,
        workflow_api.AssessmentWorkflowRequestError,
    ):
        logger.warning(
            "An error occurred while submitting a self assessment for the submission %s",
            submission_uuid,
            exc_info=True,
        )
        return failure_response(messages["could_not_submit"])
    except (
        self_api.SelfAssessmentInternalError,
        workflow_api.AssessmentWorkflowInternalError,
    ):
        logger.exception(
            "An error occurred while submitting a self assessment for the submission %s",
            submission_uuid,
        )
        return failure_response(messages["could_not_submit"])
    else:
        return {"success": True, "msg": ""}
