"""
The Peer Assessment view Mixin
"""
from webob import Response
from openassessment.xblock.utils.defaults import DEFAULT_RUBRIC_FEEDBACK_TEXT

from openassessment.xblock.utils.user_data import get_user_preferences


template_paths = {
    "unavailable": "legacy/peer/oa_peer_unavailable.html",
    "cancelled": "legacy/peer/oa_peer_cancelled.html",
    "complete": "legacy/peer/oa_peer_complete.html",
    "turbo_mode": "legacy/peer/oa_peer_turbo_mode.html",
    "turbo_mode_waiting": "legacy/peer/oa_peer_turbo_mode_waiting.html",
    "closed": "legacy/peer/oa_peer_closed.html",
    "assessment": "legacy/peer/oa_peer_assessment.html",
    "waiting": "legacy/peer/oa_peer_waiting.html",
}


def peer_context(config_data, step_data, self_assessment_data, peer_sub=None):
    user_preferences = get_user_preferences(config_data.user_service)

    is_self = "self-assessment" in config_data.assessment_steps
    is_self_complete = self_assessment_data.is_self_complete
    peer_has_finished = step_data.has_finished[0]
    show_survey = (peer_has_finished and not is_self) or (peer_has_finished and is_self_complete)

    context_dict = {
        "rubric_criteria": config_data.rubric_criteria_with_labels,
        "allow_multiple_files": config_data.allow_multiple_files,
        "allow_latex": config_data.allow_latex,
        "prompts_type": config_data.prompts_type,
        "user_timezone": user_preferences["user_timezone"],
        "user_language": user_preferences["user_language"],
        "xblock_id": config_data.get_xblock_id(),
        "show_survey": show_survey,
    }

    if config_data.rubric_feedback_prompt is not None:
        context_dict["rubric_feedback_prompt"] = config_data.rubric_feedback_prompt

    if config_data.rubric_feedback_default_text is not None:
        context_dict["rubric_feedback_default_text"] = config_data.rubric_feedback_default_text

    # We display the due date whether the problem is open or closed.
    # If no date is set, it defaults to the distant future, in which
    # case we don"t display the date.
    if step_data.is_due:
        context_dict["peer_due"] = step_data.due_date

    assessment = step_data.assessment
    translate = config_data.translate

    if assessment:
        count = step_data.has_finished[1]

        if step_data.continue_grading:
            context_dict["submit_button_text"] = translate("Submit your assessment and review another response")
        elif assessment["must_grade"] - count == 1:
            context_dict["submit_button_text"] = translate("Submit your assessment and move to next step")
        else:
            context_dict["submit_button_text"] = translate(
                "Submit your assessment and move to response #{response_number}"
            ).format(response_number=(count + 2))

        context_dict.update(
            {
                "must_grade": assessment["must_grade"],
                "graded": count,
                "review_num": count + 1,
            }
        )

    if step_data.is_not_available_yet:
        context_dict["peer_start"] = step_data.start_date

    if peer_sub:
        context_dict.update(
            {
                "peer_submission": step_data.get_submission_dict(peer_sub),
                # Determine if file upload is supported for this XBlock.
                "file_upload_type": step_data.file_upload_type,
                "peer_file_urls": step_data.get_download_urls(peer_sub),
            }
        )

    return context_dict


def peer_path_and_context(api_data, continue_grading):
    """
    Return the template path and context for rendering the peer assessment step.

    Args:
        continue_grading (bool): If true, the user has chosen to continue grading.

    Returns:
        tuple of (template_path, context_dict)

    """
    step_data = api_data.peer_assessment_data(continue_grading)

    def path_and_context(path_key, peer_sub=None):
        return (
            template_paths[path_key],
            peer_context(api_data.config_data, step_data, api_data.self_assessment_data, peer_sub),
        )

    if step_data.is_cancelled:
        return path_and_context("cancelled")

    # Once a student has completed a problem, it stays complete,
    # so this condition needs to be first.
    if (step_data.is_complete) and not step_data.continue_grading:
        return path_and_context("complete")

    # Allow continued grading even if the problem due date has passed
    if step_data.continue_grading and step_data.student_item:
        peer_sub = step_data.get_peer_submission()
        if peer_sub:
            return path_and_context("turbo_mode", peer_sub)
        else:
            return path_and_context("turbo_mode_waiting")

    if step_data.is_past_due:
        return path_and_context("closed")

    if step_data.is_not_available_yet:
        return path_and_context("unavailable")

    if step_data.is_peer or step_data.is_skipped:
        peer_sub = step_data.get_peer_submission()
        if peer_sub:
            return path_and_context("assessment", peer_sub)
        else:
            return path_and_context("waiting")

    return path_and_context("unavailable")


def render_peer_assessment(api_data, continue_grading):
    """Renders the Peer Assessment HTML section of the XBlock

    Generates the peer assessment HTML for the first section of an Open
    Assessment XBlock. See OpenAssessmentBlock.render_assessment() for
    more information on rendering XBlock sections.

    Args:
        data (dict): May contain an attribute "continue_grading", which
            allows a student to continue grading peers past the required
            number of assessments.

    """
    if "peer-assessment" not in api_data.config_data.assessment_steps:
        return Response("")

    path, context_dict = peer_path_and_context(api_data, continue_grading)

    # For backwards compatibility, if no feedback default text has been
    # set, use the default text
    if "rubric_feedback_default_text" not in context_dict:
        context_dict["rubric_feedback_default_text"] = DEFAULT_RUBRIC_FEEDBACK_TEXT

    return api_data.config_data.render_assessment(path, context_dict)
