"""
A mixin for staff grading.
"""

import logging

from openassessment.assessment.api import (
    staff as staff_api,
)

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def staff_assessment_exists(submission_uuid):
    """
    Returns True if there exists a staff assessment for the given uuid. False otherwise.
    """
    return staff_api.get_latest_staff_assessment(submission_uuid) is not None


def staff_path_and_context(api_data):
    """
    Retrieve the correct template path and template context for the handler to render.
    """
    return "openassessmentblock/staff/oa_staff_grade.html", staff_context(api_data)


def render_staff_assessment(api_data):
    """
    Renders the Staff Assessment HTML section of the XBlock
    Generates the staff assessment HTML for the Open
    Assessment XBlock. See OpenAssessmentBlock.render_assessment() for
    more information on rendering XBlock sections.
    """
    path, context_dict = staff_path_and_context(api_data)
    return api_data.config_data.render_assessment(path, context_dict)


def staff_context(api_data):
    """
    Retrieve the correct template path and template context for the handler to render.
    """
    step_data = api_data.staff_assessment_data
    translate = api_data.config_data.translate

    not_available_context = {
        "status_value": translate("Not Available"),
        "button_active": "disabled=disabled aria-expanded=false",
        "step_classes": "is--unavailable",
    }

    if step_data.is_cancelled:
        context = {
            "status_value": translate("Cancelled"),
            "icon_class": "fa-exclamation-triangle",
            "step_classes": "is--unavailable",
            "button_active": "disabled=disabled aria-expanded=false",
        }
    elif step_data.is_done:  # Staff grade exists and all steps completed.
        context = {
            "status_value": translate("Complete"),
            "icon_class": "fa-check",
            "step_classes": "is--complete is--empty",
            "button_active": "disabled=disabled aria-expanded=false",
        }
    elif step_data.is_waiting:
        # If we are in the 'waiting' workflow, this means that a staff grade cannot exist
        # (because if a staff grade did exist, we would be in 'done' regardless of whether other
        # peers have assessed). Therefore we show that we are waiting on staff to provide a grade.
        context = {
            "status_value": translate("Not Available"),
            "message_title": translate("Waiting for a Staff Grade"),
            "message_content": translate(
                "Check back later to see if a course staff member has assessed "
                "your response. You will receive your grade after the assessment "
                "is complete."
            ),
            "step_classes": "is--showing",
            "button_active": "aria-expanded=true",
        }
    elif not step_data.has_status:
        context = not_available_context
    else:  # status is 'self' or 'peer', indicating that the student still has work to do.
        if staff_assessment_exists(api_data.workflow_data.submission_uuid):
            context = {
                "status_value": translate("Complete"),
                "icon_class": "fa-check",
                "message_title": translate("You Must Complete the Steps Above to View Your Grade"),
                "message_content": translate(
                    "Although a course staff member has assessed your response, "
                    "you will receive your grade only after you have completed "
                    "all the required steps of this problem."
                ),
                "step_classes": "is--initially--collapsed",
                "button_active": "aria-expanded=false",
            }
        else:  # Both student and staff still have work to do, just show "Not Available".
            context = not_available_context

    context["xblock_id"] = api_data.config_data.get_xblock_id()
    return context
