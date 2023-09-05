"""
Student training step in the OpenAssessment XBlock.
"""
import logging

from openassessment.assessment.api import student_training
from openassessment.workflow.errors import AssessmentWorkflowError

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

messages = {
    "missing_selected": "Missing options_selected key in request.",
    "selected_must_be_dict": "options_selected must be a dictionary.",
    "could_not_check": "Your scores could not be checked.",
    "unexpected_error": "An unexpected error occurred.",
    "could_not_update": "Could not update workflow status.",
}


def training_assess(api_data, data):
    """
    Compare the scores given by the student with those given by the course author.
    If they match, update the training workflow.  The client can then reload this
    step to view the next essay or the completed step.

    Currently, we return a boolean indicating whether the student assessed correctly
    or not.  However, the student training API provides the exact criteria that the student
    scored incorrectly, as well as the "correct" options for those criteria.
    In the future, we may expose this in the UI to provide more detailed feedback.

    Args:
        data (dict): Must have the following keys:
            options_selected (dict): Dictionary mapping criterion names to option values.

    Returns:
        Dict with keys:
            * "success" (bool) indicating success or error
            * "msg" (unicode) containing additional information if an error occurs.
            * "correct" (bool) indicating whether the student scored the assessment correctly.

    """

    translate = api_data.config_data.translate
    submission_uuid = api_data.workflow_data.submission_uuid

    def failure_response(reason_key):
        return {"success": False, "msg": translate(messages[reason_key])}

    if "options_selected" not in data:
        return failure_response("missing_selected")
    if not isinstance(data["options_selected"], dict):
        return failure_response("selected_must_be_dict")

    # Check the student's scores against the course author's scores.
    # This implicitly updates the student training workflow (which example essay is shown)
    # as well as the assessment workflow (training/peer/self steps).
    try:
        corrections = student_training.assess_training_example(submission_uuid, data["options_selected"])
        api_data.config_data.publish_event(
            "openassessment.student_training_assess_example",
            {
                "submission_uuid": submission_uuid,
                "options_selected": data["options_selected"],
                "corrections": corrections,
            },
        )
    except student_training.StudentTrainingRequestError:
        msg = ("Could not check learner training scores for the learner with submission UUID {uuid}").format(
            uuid=submission_uuid
        )
        logger.warning(msg, exc_info=True)

        return failure_response("could_not_check")
    except student_training.StudentTrainingInternalError:
        return failure_response("could_not_check")
    except Exception:  # pylint: disable=broad-except
        return failure_response("unexpected_error")
    else:
        try:
            api_data.workflow_data.update_workflow_status()
        except AssessmentWorkflowError:
            logger.exception(translate(messages["could_not_update"]))
            return failure_response("could_not_update")
        return {
            "success": True,
            "msg": "",
            "corrections": corrections,
        }
