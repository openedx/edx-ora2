"""
Views related to submissions
"""
import logging

from django.core.exceptions import ObjectDoesNotExist
from xblock.exceptions import NoSuchServiceError

from openassessment.xblock.utils.data_conversion import (
    create_submission_dict,
    list_to_conversational_format,
)
from openassessment.xblock.utils.user_data import get_user_preferences


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def render_submission(config, submission_info):
    """
    Renders the Submission HTML section of the XBlock

    Generates the submission HTML for the first section of an Open
    Assessment XBlock. See OpenAssessmentBlock.render_assessment() for
    more information on rendering XBlock sections.

    Needs to support the following scenarios:
    - Unanswered and Open
    - Unanswered and Closed
    - Saved
    - Saved and Closed
    - Submitted
    - Submitted and Closed
    - Submitted, waiting assessment
    - Submitted and graded
    """
    context = get_submission_context(config, submission_info)
    path = get_submission_path(submission_info)

    return config.render_assessment(path, context_dict=context)


def get_submission_path(submission_info):
    """
    Given info about the submission, return the appropriate template path

    Returns:
    - path (String) to the template
    """

    # Template Paths
    template_dir = "openassessmentblock/response"
    submission_template_paths = {
        "default": "oa_response",
        "closed": "oa_response_closed",
        "unavailable": "oa_response_unavailable",
        "team_already_submitted": "oa_response_team_already_submitted",
        "cancelled": "oa_response_cancelled",
        "graded": "oa_response_graded",
        "submitted": "oa_response_submitted",
    }
    full_paths = {k: f"{template_dir}/{path}.html" for (k, path) in submission_template_paths.items()}

    # Response is unavailable (not yet open or past due date)
    if not submission_info.has_submitted and submission_info.problem_is_inaccessible:
        if submission_info.is_past_due:
            return full_paths["closed"]
        if submission_info.is_not_available_yet:
            return full_paths["unavailable"]

    # Response is unavailable (team assignment where user hasn't submitted and is not on a team)
    elif submission_info.is_team_assignment and submission_info.team_id is None:
        return full_paths["unavailable"]

    # Response not yet submitted
    elif not submission_info.has_submitted:
        if submission_info.is_team_assignment and submission_info.team_previously_submitted_without_student:
            return full_paths["team_already_submitted"]

    # Cancelled: Instructor has cancelled this response
    elif submission_info.has_been_cancelled:
        return full_paths["cancelled"]

    # Done: Submitted and received final grade
    elif submission_info.has_received_final_grade:
        return full_paths["graded"]

    # Submitted and waiting for a grade
    else:
        return full_paths["submitted"]

    return full_paths["default"]


def get_team_submission_context(config):
    """
    Populate the passed context object with team info, including a set of students on
    the team with submissions to the current item from another team, under the key
    `team_members_with_external_submissions`.

    Args:
        config: Access to ORA config API
    Returns
        (dict): context with team-related fields
    """
    from submissions import team_api

    team_context = {}

    try:
        team_info = config.get_team_info()
        if team_info:
            team_context = team_info
            if config.is_course_staff:
                return team_context
            student_item_dict = config.get_student_item_dict()
            external_submissions = team_api.get_teammates_with_submissions_from_other_teams(
                config.course_id,
                student_item_dict["item_id"],
                team_info["team_id"],
                config.get_anonymous_user_ids_for_team(),
            )

            team_context["team_members_with_external_submissions"] = list_to_conversational_format(
                [config.get_username(submission["student_id"]) for submission in external_submissions]
            )
    except ObjectDoesNotExist:
        logger.error(
            "%s: User associated with anonymous_user_id %s can not be found.",
            str(config.location),
            config.get_student_item_dict()["student_id"],
        )
    except NoSuchServiceError:
        logger.error("%s: Teams service is unavailable", str(config.location))

    return team_context


def save_status(config, submission_info):
    """
    Return a string indicating whether the response has been saved.

    Returns:
        unicode
    """
    return config.translate("Draft saved!") if submission_info.has_saved else config.translate("Response not started.")


def get_submission_context(config, submission_info):
    """
    Determine the context needed when rendering the response (submission) step.

    Returns:
    * Context (dict) - Context used for rendering the submission
    """
    # Get ORA Metadata
    block_metadata = {
        "xblock_id": config.get_xblock_id(),
        "base_asset_url": config.base_asset_url,
    }

    # Get response config
    response_config = submission_info.response_config

    # Get user info / preferences
    user_preferences = get_user_preferences(config.user_service)
    user_config = {
        "has_real_user": config.has_real_user,
        "user_language": user_preferences["user_language"],
        "user_timezone": user_preferences["user_timezone"],
    }

    # Below here we determine submission status and template
    submission_context = {}
    team_submission_context = {}
    file_urls = submission_info.files.uploaded_files
    if file_urls:
        submission_context.update(file_urls)

    # Get access information (whether problem is closed) and reasons
    workflow_context = {}
    if submission_info.due_date:
        workflow_context["submission_due"] = submission_info.due_date

    # Response is unavailable (not yet open or past due date)
    if not submission_info.has_submitted and submission_info.problem_is_inaccessible:
        if submission_info.is_not_available_yet:
            workflow_context["submission_start"] = submission_info.start_date

    # Response not yet submitted: Get the saved response
    elif not submission_info.has_submitted:
        # Load the user/team saved response
        saved_response = submission_info.saved_response
        submission_context["saved_response"] = create_submission_dict(saved_response, config.prompts)

        if submission_info.is_team_assignment:
            team_context = get_team_submission_context(config)
            submission_context.update(team_context)

        # Determine UI states
        submission_context["save_status"] = save_status(config, submission_info)
        submission_context["enable_delete_files"] = True

    # Cancelled: Instructor has cancelled this response
    elif submission_info.has_been_cancelled:
        # Load user/team submission
        submission_context["student_submission"] = submission_info.student_submission

        # Get cancellation information
        workflow_context["workflow_cancellation"] = submission_info.cancellation_info

    # Done: Submitted and received final grade
    elif submission_info.has_received_final_grade:
        student_submission = submission_info.student_submission
        submission_context["student_submission"] = create_submission_dict(student_submission, config.prompts)

    # Submitted and waiting for a grade
    else:
        # Load user/team submission
        student_submission = submission_info.student_submission
        submission_context["student_submission"] = create_submission_dict(student_submission, config.prompts)

        # Get workflow context
        workflow_context["peer_incomplete"] = submission_info.peer_step_incomplete
        workflow_context["self_incomplete"] = submission_info.self_step_incomplete

    # Assemble context
    context = {
        **block_metadata,
        **response_config,
        **user_config,
        **workflow_context,
        **submission_context,
        **team_submission_context,
    }

    return context
