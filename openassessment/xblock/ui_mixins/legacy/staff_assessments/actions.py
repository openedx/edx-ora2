"""
A mixin for staff grading.
"""


import logging

from openassessment.assessment.errors import (
    StaffAssessmentInternalError,
    StaffAssessmentRequestError,
)
from openassessment.workflow import api as workflow_api, team_api as team_workflow_api

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def do_staff_assessment(api_data, data):
    """
    Create a staff assessment from a staff submission.
    """
    config_data = api_data.config_data
    translate = config_data.translate
    step_data = api_data.staff_assessment_data
    if "submission_uuid" not in data:
        return False, translate("The submission ID of the submission being assessed was not found.")
    try:
        assessment = step_data.create_assessment(data)
        assess_type = data.get("assess_type", "regrade")
        config_data.publish_assessment_event("openassessmentblock.staff_assess", assessment, type=assess_type)
        workflow_api.update_from_assessments(
            assessment["submission_uuid"],
            None,
            {},
            override_submitter_requirements=(assess_type == "regrade"),
        )
    except StaffAssessmentRequestError:
        logger.warning(
            "An error occurred while submitting a staff assessment for the submission %s",
            data["submission_uuid"],
            exc_info=True,
        )
        msg = translate("Your staff assessment could not be submitted.")
        return False, msg
    except StaffAssessmentInternalError:
        logger.exception(
            "An error occurred while submitting a staff assessment for the submission %s",
            data["submission_uuid"],
        )
        msg = translate("Your staff assessment could not be submitted.")
        return False, msg
    return True, ""


def do_team_staff_assessment(api_data, data, team_submission_uuid=None):
    """
    Teams version of do_staff_assessment.
    Providing the team_submission_uuid removes lookup of team submission from individual submission_uuid.
    """
    config_data = api_data.config_data
    translate = config_data.translate
    step_data = api_data.staff_assessment_data
    if "submission_uuid" not in data and team_submission_uuid is None:
        return False, translate("The submission ID of the submission being assessed was not found.")
    try:
        assessment, team_submission_uuid = step_data.create_team_assessment(data)
        assess_type = data.get("assess_type", "regrade")
        config_data.publish_assessment_event("openassessmentblock.staff_assess", assessment[0], type=assess_type)
        team_workflow_api.update_from_assessments(
            team_submission_uuid,
            override_submitter_requirements=(assess_type == "regrade"),
        )

    except StaffAssessmentRequestError:
        logger.warning(
            "An error occurred while submitting a team assessment for the submission %s",
            data["submission_uuid"],
            exc_info=True,
        )
        msg = translate("Your team assessment could not be submitted.")
        return False, msg
    except StaffAssessmentInternalError:
        logger.exception(
            "An error occurred while submitting a team assessment for the submission %s",
            data["submission_uuid"],
        )
        msg = translate("Your team assessment could not be submitted.")
        return False, msg

    return True, ""


def staff_assess(api_data, data, suffix=""):  # pylint: disable=unused-argument
    """
    Create a staff assessment from a team or individual submission.
    """
    if api_data.config_data.is_team_assignment():
        success, err_msg = do_team_staff_assessment(api_data, data)
    else:
        success, err_msg = do_staff_assessment(api_data, data)

    return {"success": success, "msg": err_msg}
