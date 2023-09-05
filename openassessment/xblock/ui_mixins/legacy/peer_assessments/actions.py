"""Collection of JSON handlers for legacy view"""
import logging

from openassessment.assessment.errors import (
    PeerAssessmentInternalError,
    PeerAssessmentRequestError,
    PeerAssessmentWorkflowError,
)
from openassessment.workflow.errors import AssessmentWorkflowError

from openassessment.xblock.utils.data_conversion import (
    clean_criterion_feedback,
    create_rubric_dict,
)

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

messages = {
    "must_submit": "You must submit a response before you can perform a peer assessment.",
    "already_submitted": "This feedback has already been submitted or the submission has been cancelled.",
    "could_not_submit": "Your peer assessment could not be submitted.",
    "could_not_update": "Could not update workflow status.",
    "could_not_load": "Could not load peer assessment.",
}


def create_peer_assessment(api_data, data):
    # Import is placed here to avoid model import at project startup.
    from openassessment.assessment.api import peer as peer_api

    config_data = api_data.config_data
    submission_uuid = api_data.workflow_data.submission_uuid
    peer_assessment_data = api_data.peer_assessment_data()

    # Create the assessment
    assessment = peer_api.create_assessment(
        submission_uuid,
        peer_assessment_data.student_item["student_id"],
        data["options_selected"],
        clean_criterion_feedback(
            config_data.rubric_criteria_with_labels,
            data["criterion_feedback"],
        ),
        data["overall_feedback"],
        create_rubric_dict(
            config_data.prompts,
            config_data.rubric_criteria_with_labels,
        ),
        peer_assessment_data.assessment["must_be_graded_by"],
    )

    return assessment


def peer_assess(api_data, data, suffix=""):  # pylint: disable=unused-argument
    """Place a peer assessment into OpenAssessment system

    Assess a Peer Submission.  Performs basic workflow validation to ensure
    that an assessment can be performed as this time.

    Args:
        data (dict): A dictionary containing information required to create
            a new peer assessment.  This dict should have the following attributes:
            `submission_uuid` (string): The unique identifier for the submission being assessed.
            `options_selected` (dict): Dictionary mapping criterion names to option values.
            `overall_feedback` (unicode): Written feedback for the submission as a whole.
            `criterion_feedback` (unicode): Written feedback per the criteria for the submission.

    Returns:
        Dict with keys "success" (bool) indicating success/failure.
        and "msg" (unicode) containing additional information if an error occurs.

    """
    translate = api_data.config_data.translate
    submission_uuid = api_data.workflow_data.submission_uuid

    def failure_response(reason):
        return {"success": False, "msg": translate(reason)}

    if submission_uuid is None:
        return failure_response(messages["must_submit"])

    step_data = api_data.peer_assessment_data()
    submission = step_data.get_peer_submission() or {}
    uuid_server = submission.get("uuid", None)
    uuid_client = data.get("submission_uuid", None)

    if uuid_server != uuid_client:
        logger.warning(
            "Irrelevant assessment submission: expected '%s', got '%s'",
            uuid_server,
            uuid_client,
        )
        return failure_response(messages["already_submitted"])

    if step_data.assessment:
        try:
            assessment = create_peer_assessment(api_data, data)
            # Emit analytics event...
            api_data.config_data.publish_assessment_event("openassessmentblock.peer_assess", assessment)
        except (PeerAssessmentRequestError, PeerAssessmentWorkflowError):
            logger.warning(
                "Peer API error for submission UUID %s",
                submission_uuid,
                exc_info=True,
            )
            return failure_response(messages["could_not_submit"])
        except PeerAssessmentInternalError:
            logger.exception(
                "Peer API internal error for submission UUID: %s",
                submission_uuid,
            )
            return failure_response(messages["could_not_submit"])

        # Update both the workflow that the submission we"re assessing
        # belongs to, as well as our own (e.g. have we evaluated enough?)
        try:
            update = api_data.workflow_data.update_workflow_status
            if assessment:
                update(submission_uuid=assessment["submission_uuid"])
            update()
        except AssessmentWorkflowError:
            logger.exception(
                "Workflow error occurred when submitting peer assessment for submission %s",
                submission_uuid,
            )
            return failure_response(messages["could_not_update"])

        # Temp kludge until we fix JSON serialization for datetime
        assessment["scored_at"] = str(assessment["scored_at"])

        return {"success": True, "msg": ""}

    return failure_response(messages["could_not_load"])
