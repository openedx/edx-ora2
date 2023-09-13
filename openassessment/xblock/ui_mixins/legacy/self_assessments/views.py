""" A mixin for self Assessments. """

import logging

from webob import Response

from openassessment.xblock.utils.user_data import get_user_preferences

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

template_paths = {
    "unavailable": "openassessmentblock/self/oa_self_unavailable.html",
    "cancelled": "openassessmentblock/self/oa_self_cancelled.html",
    "complete": "openassessmentblock/self/oa_self_complete.html",
    "closed": "openassessmentblock/self/oa_self_closed.html",
    "assessment": "openassessmentblock/self/oa_self_assessment.html",
}


def render_self_assessment(api_data):
    if "self-assessment" not in api_data.config_data.assessment_steps:
        return Response("")

    submission_uuid = api_data.submission_data.submission_uuid
    translate = api_data.config_data.translate
    try:
        path, context = self_path_and_context(api_data)
    except Exception:  # pylint: disable=broad-except
        msg = f"Could not retrieve self assessment for submission {submission_uuid}"
        logger.exception(msg)
        return api_data.config_data.render_error(translate("An unexpected error occurred."))
    else:
        return api_data.config_data.render_assessment(path, context)


def self_context(api_data, with_sub=False):
    config_data = api_data.config_data
    user_preferences = get_user_preferences(config_data.user_service)
    context = {
        "allow_multiple_files": config_data.allow_multiple_files,
        "allow_latex": config_data.allow_latex,
        "prompts_type": config_data.prompts_type,
        "xblock_id": config_data.get_xblock_id(),
        "user_timezone": user_preferences["user_timezone"],
        "user_language": user_preferences["user_language"],
    }

    step_data = api_data.self_assessment_data
    # We display the due date whether the problem is open or closed.
    # If no date is set, it defaults to the distant future, in which
    # case we don't display the date.
    if step_data.is_due:
        context["self_due"] = step_data.due_date

    if step_data.is_not_available_yet:
        context["self_start"] = step_data.start_date

    if with_sub and step_data.submission:
        context["rubric_criteria"] = config_data.rubric_criteria_with_labels
        context["self_submission"] = step_data.submission_dict
        if config_data.rubric_feedback_prompt is not None:
            context["rubric_feedback_prompt"] = config_data.rubric_feedback_prompt

        if config_data.rubric_feedback_default_text is not None:
            context["rubric_feedback_default_text"] = config_data.rubric_feedback_default_text

        # Determine if file upload is supported for this XBlock and what kind of files can be uploaded.
        context["file_upload_type"] = config_data.file_upload_type
        context["self_file_urls"] = step_data.file_urls
    return context


def self_path_and_context(api_data):
    """
    Determine the template path and context to use when rendering the self-assessment step.

    Returns:
        tuple of `(path, context)`, where `path` (str) is the path to the template,
        and `context` (dict) is the template context.

    Raises:
        SubmissionError: Error occurred while retrieving the current submission.
        SelfAssessmentRequestError: Error occurred while checking if we had a self-assessment.
    """
    # Import is placed here to avoid model import at project startup.
    step_data = api_data.self_assessment_data

    def path_and_context(path_key, with_sub=False):
        return (template_paths[path_key], self_context(api_data, with_sub))

    if step_data.is_cancelled:
        return path_and_context("cancelled")
    elif step_data.is_self_complete:
        return path_and_context("complete")
    elif step_data.is_self_active or step_data.problem_closed:
        if step_data.assessment is not None:
            return path_and_context("complete")
        elif step_data.problem_closed:
            if step_data.is_not_available_yet:
                return path_and_context("unavailable")
            elif step_data.is_past_due:
                return path_and_context("closed")
        else:
            return path_and_context("assessment", with_sub=True)
    return path_and_context("unavailable", with_sub=True)
