"""
Base stateless API actions for acting upon learner submissions
"""

import json
import logging
import os
from submissions.api import Submission, SubmissionError, SubmissionRequestError

from openassessment.fileupload.exceptions import FileUploadError
from openassessment.workflow.errors import AssessmentWorkflowError
from openassessment.xblock.apis.submissions.errors import (
    DeleteNotAllowed,
    EmptySubmissionError,
    NoTeamToCreateSubmissionForError,
    DraftSaveException,
    OnlyOneFileAllowedException,
    SubmissionValidationException,
    AnswerTooLongException,
    StudioPreviewException,
    MultipleSubmissionsException,
    SubmitInternalError,
    UnsupportedFileTypeException
)

from openassessment.xblock.utils.validation import validate_submission
from openassessment.xblock.utils.data_conversion import (
    format_files_for_submission,
    prepare_submission_for_serialization,
)
logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def submit(text_responses, block_config_data, block_submission_data, block_workflow_data):
    """
    Submit response for a student.

    Args:
    * text_responses - List of text responses for submission
    * block_config_data - ORAConfigAPI
    * block_submission_data - SubmissionAPI
    * block_workflow_data - WorkflowAPI
    """
    success, msg = validate_submission(
        text_responses,
        block_config_data.prompts,
        block_config_data.translate,
        block_config_data.text_response,
    )
    if not success:
        raise SubmissionValidationException(msg)

    student_item_dict = block_config_data.student_item_dict

    # Short-circuit if no user is defined (as in Studio Preview mode)
    # Since students can't submit, they will never be able to progress in the workflow
    if block_config_data.in_studio_preview:
        raise StudioPreviewException()

    if block_submission_data.has_submitted:
        raise MultipleSubmissionsException()

    try:
        # a submission for a team generates matching submissions for all members
        if block_config_data.is_team_assignment():
            return create_team_submission(
                student_item_dict,
                text_responses,
                block_config_data,
                block_submission_data,
                block_workflow_data
            )
        else:
            return create_submission(
                student_item_dict,
                text_responses,
                block_config_data,
                block_submission_data,
                block_workflow_data
            )
    except SubmissionRequestError as err:
        # Handle the case of an answer that's too long as a special case,
        # so we can display a more specific error message.
        # Although we limit the number of characters the user can
        # enter on the client side, the submissions API uses the JSON-serialized
        # submission to calculate length.  If each character submitted
        # by the user takes more than 1 byte to encode (for example, double-escaped
        # newline characters or non-ASCII unicode), then the user might
        # exceed the limits set by the submissions API.  In that case,
        # we display an error message indicating that the answer is too long.
        answer_too_long = any(
            "maximum answer size exceeded" in answer_err.lower()
            for answer_err in err.field_errors.get("answer", [])
        )
        if answer_too_long:
            logger.exception(f"Response exceeds maximum allowed size: {student_item_dict}")
            max_size = f"({int(Submission.MAXSIZE / 1024)} KB)"
            base_error = block_config_data.translate("Response exceeds maximum allowed size.")
            extra_info = block_config_data.translate(
                "Note: if you have a spellcheck or grammar check browser extension, "
                "try disabling, reloading, and reentering your response before submitting."
            )
            raise AnswerTooLongException(f"{base_error} {max_size} {extra_info}") from err
        msg = (
            "The submissions API reported an invalid request error "
            "when submitting a response for the user: {student_item}"
        ).format(student_item=student_item_dict)
        logger.exception(msg)
        raise
    except EmptySubmissionError:
        msg = (
            "Attempted to submit submission for user {student_item}, "
            "but submission contained no content."
        ).format(student_item=student_item_dict)
        logger.exception(msg)
        raise
    except (
        SubmissionError,
        AssessmentWorkflowError,
        NoTeamToCreateSubmissionForError,
    ) as e:
        msg = (
            "An unknown error occurred while submitting "
            "a response for the user: {student_item}"
        ).format(
            student_item=student_item_dict
        )
        logger.exception(msg)
        raise SubmitInternalError from e


def create_submission(
    student_item_dict,
    submission_data,
    block_config_data,
    block_submission_data,
    block_workflow_data
):
    """Creates submission for the submitted assessment response or a list for a team assessment."""
    # Import is placed here to avoid model import at project startup.
    from submissions import api

    # Serialize the submission
    submission_dict = prepare_submission_for_serialization(submission_data)

    # Add files
    uploaded_files = block_submission_data.files.get_uploads_for_submission()
    submission_dict.update(format_files_for_submission(uploaded_files))

    # Validate
    if block_submission_data.submission_is_empty(submission_dict):
        raise EmptySubmissionError

    # Create submission
    submission = api.create_submission(student_item_dict, submission_dict)
    block_workflow_data.create_workflow(submission["uuid"])

    # Set student submission_uuid
    block_config_data._block.submission_uuid = submission["uuid"]  # pylint: disable=protected-access

    # Emit analytics event...
    block_config_data.publish_event(
        "openassessmentblock.create_submission",
        {
            "submission_uuid": submission["uuid"],
            "attempt_number": submission["attempt_number"],
            "created_at": submission["created_at"],
            "submitted_at": submission["submitted_at"],
            "answer": submission["answer"],
        },
    )

    return submission


def create_team_submission(
    student_item_dict,
    submission_data,
    block_config_data,
    block_submission_data,
    block_workflow_data
):
    """A student submitting for a team should generate matching submissions for every member of the team."""

    if not block_config_data.has_team:
        student_id = student_item_dict["student_id"]
        course_id = block_config_data.course_id
        msg = f"Student {student_id} has no team for course {course_id}"
        logger.exception(msg)
        raise NoTeamToCreateSubmissionForError(msg)

    # Import is placed here to avoid model import at project startup.
    from submissions import team_api

    team_info = block_config_data.get_team_info()

    # Serialize the submission
    submission_dict = prepare_submission_for_serialization(submission_data)

    # Add files
    uploaded_files = block_submission_data.files.get_uploads_for_submission()
    submission_dict.update(format_files_for_submission(uploaded_files))

    # Validate
    if block_submission_data.submission_is_empty(submission_dict):
        raise EmptySubmissionError

    submitter_anonymous_user_id = block_config_data.get_anonymous_user_id_from_xmodule_runtime()
    user = block_config_data.get_real_user(submitter_anonymous_user_id)

    anonymous_student_ids = block_config_data.get_anonymous_user_ids_for_team()
    submission = team_api.create_submission_for_team(
        block_config_data.course_id,
        student_item_dict["item_id"],
        team_info["team_id"],
        user.id,
        anonymous_student_ids,
        submission_dict,
    )

    block_workflow_data.create_team_workflow(submission["team_submission_uuid"])

    # Emit analytics event...
    block_config_data.publish_event(
        "openassessmentblock.create_team_submission",
        {
            "submission_uuid": submission["team_submission_uuid"],
            "team_id": team_info["team_id"],
            "attempt_number": submission["attempt_number"],
            "created_at": submission["created_at"],
            "submitted_at": submission["submitted_at"],
            "answer": submission["answer"],
        },
    )
    return submission


def save_submission_draft(student_submission_data, block_config_data, block_submission_data):
    """
    Save the current student's response submission.
    If the student already has a response saved, this will overwrite it.

    Args:
        data (dict): Data should have a single key 'submission' that contains
            the text of the student's response. Optionally, the data could
            have a 'file_urls' key that is the path to an associated file for
            this submission.
        suffix (str): Not used.

    Returns:
        dict: Contains a bool 'success' and unicode string 'msg'.
    """
    success, msg = validate_submission(
        student_submission_data,
        block_config_data.prompts,
        block_config_data.translate,
        block_config_data.text_response,
    )
    if not success:
        raise SubmissionValidationException(msg)
    try:
        block_submission_data.saved_response = json.dumps(prepare_submission_for_serialization(student_submission_data))
        block_submission_data.has_saved = True

        # Emit analytics event...
        block_config_data.publish_event(
            "openassessmentblock.save_submission",
            {"saved_response": block_submission_data.saved_response},
        )
    except Exception as e:  # pylint: disable=broad-except
        raise DraftSaveException from e


def append_file_data(file_data, block_config, submission_info):
    """
    Appends a list of file data to the current block state

    Args:
        block_config (ORAConfigAPI)
        submission_info (SubmissionAPI)
        files_to_append (list of {
            'description': (str)
            'name': (str)
            'size': (int)
        })
    """
    try:
        new_files = submission_info.files.file_manager.append_uploads(*file_data)
    except FileUploadError as exc:
        logger.exception(
            "append_file_data: file description for data %s failed with error %s", file_data, exc, exc_info=True
        )
        raise
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception(
            "append_file_data: unhandled exception for data %s. Error: %s", file_data, exc, exc_info=True
        )
        raise FileUploadError(exc) from exc

    # Emit analytics event...
    block_config.publish_event(
        "openassessmentblock.save_files_descriptions",
        {"saved_response": submission_info.files.saved_files_descriptions},
    )
    return new_files


def remove_uploaded_file(file_index, block_config, submission_info):
    """
    Removes uploaded user file.
    """
    file_key = submission_info.files.get_file_key(file_index)
    if not submission_info.files.can_delete_file(file_index):
        raise DeleteNotAllowed()
    try:
        submission_info.files.delete_uploaded_file(file_index)
        # Emit analytics event...
        block_config.publish_event(
            "openassessmentblock.remove_uploaded_file",
            {"student_item_key": file_key},
        )
        logger.debug("Deleted file %s", file_key)
    except FileUploadError as exc:
        logger.exception(
            "FileUploadError: Error when deleting file %s : %s",
            file_key,
            exc,
            exc_info=True,
        )
        raise
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception(
            "FileUploadError: unhandled exception for %s. Error: %s",
            file_key,
            exc,
            exc_info=True,
        )
        raise FileUploadError(exc) from exc


def get_upload_url(content_type, file_name, file_index, block_config, submission_info):
    """
    Request a URL to be used for uploading content for a given file

    Returns:
        A URL to be used to upload content associated with this submission.

    """
    if not block_config.allow_multiple_files:
        if submission_info.files.has_any_file_in_upload_space():
            raise OnlyOneFileAllowedException()

    _, file_ext = os.path.splitext(file_name)
    file_ext = file_ext.strip(".") if file_ext else None

    # Validate that there are no data issues and file type is allowed
    if not submission_info.files.is_supported_upload_type(file_ext, content_type):
        raise UnsupportedFileTypeException(file_ext)

    # Attempt to upload
    try:
        key = submission_info.files.get_file_key(file_index)
        url = submission_info.files.get_upload_url(key, content_type)
        return url
    except FileUploadError:
        logger.exception("FileUploadError:Error retrieving upload URL")
        raise
