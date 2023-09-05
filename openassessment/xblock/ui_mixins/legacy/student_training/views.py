"""
Student training step in the OpenAssessment XBlock.
"""
import logging

from webob import Response


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

template_paths = {
    "unavailable": "openassessmentblock/student_training/student_training_unavailable.html",
    "cancelled": "openassessmentblock/student_training/student_training_cancelled.html",
    "complete": "openassessmentblock/student_training/student_training_complete.html",
    "closed": "openassessmentblock/student_training/student_training_closed.html",
    "training": "openassessmentblock/student_training/student_training.html",
    "error": "openassessmentblock/student_training/student_training_error.html",
}


def render_student_training(api_data):
    """
    Render the student training step.

    Args:
        data: Not used.

    Keyword Arguments:
        suffix: Not used.

    Returns:
        unicode: HTML content of the grade step

    """
    if "student-training" not in api_data.config_data.assessment_steps:
        return Response("")

    config_data = api_data.config_data
    try:
        path, context = training_path_and_context(api_data)
    except Exception:  # pylint: disable=broad-except
        submission_uuid = api_data.submission_data.submission_uuid
        msg = f"Could not render Learner Training step for submission {submission_uuid}."
        logger.exception(msg)
        return config_data.render_error(config_data.translate("An unexpected error occurred."))
    else:
        return config_data.render_assessment(path, context)


def training_context(api_data):
    """
    Return the template context used to render the student training step.

    Returns:
        context dict.
    """
    step_data = api_data.student_training_data
    config_data = api_data.config_data

    # Retrieve the status of the workflow.
    # If no submissions have been created yet, the status will be None.
    user_preferences = api_data.config_data.user_preferences

    context = {
        "xblock_id": config_data.get_xblock_id(),
        "allow_multiple_files": config_data.allow_multiple_files,
        "allow_latex": config_data.allow_latex,
        "prompts_type": config_data.prompts_type,
        "user_timezone": user_preferences["user_timezone"],
        "user_language": user_preferences["user_language"],
    }

    if not step_data.has_workflow:
        return context

    if step_data.is_cancelled or step_data.is_complete:
        return context

    # If the problem is closed, then do not allow students to access the training step
    if step_data.is_not_available_yet:
        context["training_start"] = step_data.start_date
        return context
    if step_data.is_past_due:
        context["training_due"] = step_data.due_date
        return context

    if not step_data.training_module:
        return context

    if step_data.is_due:
        context["training_due"] = step_data.due_date

    # Report progress in the student training workflow (completed X out of Y)
    context.update(
        {
            "training_num_available": step_data.num_available,
            "training_num_completed": step_data.num_completed,
            "training_num_current": step_data.num_completed + 1,
        }
    )

    # Retrieve the example essay for the student to submit
    # This will contain the essay text, the rubric, and the options the instructor selected.
    example_context = step_data.example_context
    if not example_context["error_message"]:
        context.update(
            {
                "training_essay": example_context["essay_context"],
                "training_rubric": step_data.example_rubric,
            }
        )

    return context


def training_path_and_context(api_data):
    """
    Return the template path and context used to render the student training step.

    Returns:
        tuple of `(path, context)` where `path` is the path to the template and
            `context` is a dict.

    """
    step_data = api_data.student_training_data

    def path_and_context(path_key):
        return template_paths[path_key], training_context(api_data)

    # Retrieve the status of the workflow.
    # If no submissions have been created yet, the status will be None.
    if not step_data.has_workflow:
        return path_and_context("unavailable")

    # If the student has completed the training step, then show that the step is complete.
    # We put this condition first so that if a student has completed the step, it *always*
    # shows as complete.
    # We're assuming here that the training step always precedes the other assessment steps
    # (peer/self) -- we may need to make this more flexible later.
    if step_data.is_cancelled:
        return path_and_context("cancelled")
    if step_data.is_complete:
        return path_and_context("complete")

    # If the problem is closed, then do not allow students to access the training step
    if step_data.is_not_available_yet:
        return path_and_context("unavailable")
    if step_data.is_past_due:
        return path_and_context("closed")

    # If we're on the training step, show the student an example
    # We do this last so we can avoid querying the student training API if possible.
    if not step_data.training_module:
        return path_and_context("unavailable")

    # Retrieve the example essay for the student to submit
    # This will contain the essay text, the rubric, and the options the instructor selected.
    example_context = step_data.example_context
    if example_context["error_message"]:
        logger.error(example_context["error_message"])
        return path_and_context("error")
    else:
        return path_and_context("training")
