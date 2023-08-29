"""
Actions related to submissions
"""

import json
import logging
import os

from openassessment.fileupload.exceptions import FileUploadError
from openassessment.workflow.errors import AssessmentWorkflowError
from openassessment.xblock.data_conversion import prepare_submission_for_serialization
from openassessment.xblock.submission_mixin import (
    EmptySubmissionError,
    NoTeamToCreateSubmissionForError,
)
from openassessment.xblock.validation import validate_submission

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name



def submit(block_config, submission_info, data):
    """
    Place the submission text into Openassessment system

    Allows submission of new responses.  Performs basic workflow validation
    on any new submission to ensure it is acceptable to receive a new
    response at this time.

    Args:
        data (dict): Data may contain two attributes: submission and
            file_urls. submission is the response from the student which
            should be stored in the Open Assessment system. file_urls is the
            path to a related file for the submission. file_urls is optional.
        suffix (str): Not used in this handler.

    Returns:
        (tuple | [tuple]): Returns the status (boolean) of this request, the
            associated status tag (str), and status text (unicode).
            This becomes an array of similarly structured tuples in the event
            of a team submission, one entry per student entry.
    """
    # Import is placed here to avoid model import at project startup.
    from submissions import api

    if "submission" not in data:
        return (
            False,
            "EBADARGS",
            block_config.translate('"submission" required to submit answer.'),
        )

    status = False
    student_sub_data = data["submission"]
    success, msg = validate_submission(
        student_sub_data, block_config.prompts, block_config.translate, block_config.text_response
    )
    if not success:
        return (False, "EBADARGS", msg)

    student_item_dict = block_config.student_item_dict

    # Short-circuit if no user is defined (as in Studio Preview mode)
    # Since students can't submit, they will never be able to progress in the workflow
    if block_config.in_studio_preview:
        return (
            False,
            "ENOPREVIEW",
            block_config.translate(
                "To submit a response, view this component in Preview or Live mode."
            ),
        )

    status_tag = (
        "ENOMULTI"  # It is an error to submit multiple times for the same item
    )
    status_text = block_config.translate("Multiple submissions are not allowed.")

    if not submission_info.has_submitted:
        try:
            # a submission for a team generates matching submissions for all members
            if block_config.is_team_assignment():
                submission = submission_info.create_team_submission(student_sub_data)
            else:
                submission = submission_info.create_submission(student_sub_data)
            return _create_submission_response(submission)

        except api.SubmissionRequestError as err:
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
                logger.exception(
                    f"Response exceeds maximum allowed size: {student_item_dict}"
                )
                status_tag = "EANSWERLENGTH"
                max_size = f"({int(api.Submission.MAXSIZE / 1024)} KB)"
                base_error = block_config.translate("Response exceeds maximum allowed size.")
                extra_info = block_config.translate(
                    "Note: if you have a spellcheck or grammar check browser extension, "
                    "try disabling, reloading, and reentering your response before submitting."
                )
                status_text = f"{base_error} {max_size} {extra_info}"
            else:
                msg = (
                    "The submissions API reported an invalid request error "
                    "when submitting a response for the user: {student_item}"
                ).format(student_item=student_item_dict)
                logger.exception(msg)
                status_tag = "EBADFORM"
                status_text = msg
        except EmptySubmissionError:
            msg = (
                "Attempted to submit submission for user {student_item}, "
                "but submission contained no content."
            ).format(student_item=student_item_dict)
            logger.exception(msg)
            status_tag = "EEMPTYSUB"
            status_text = block_config.translate(
                "Submission cannot be empty. "
                "Please refresh the page and try again."
            )
        except (
            api.SubmissionError,
            AssessmentWorkflowError,
            NoTeamToCreateSubmissionForError,
        ):
            msg = (
                "An unknown error occurred while submitting "
                "a response for the user: {student_item}"
            ).format(student_item=student_item_dict)
            logger.exception(msg)
            status_tag = "EUNKNOWN"
            status_text = block_config.translate("API returned unclassified exception.")

    # error cases fall through to here
    return status, status_tag, status_text


def save_submission(block_config, submission_info, data):
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
    if "submission" in data:
        student_sub_data = data["submission"]
        success, msg = validate_submission(
            student_sub_data, block_config.prompts, block_config.translate, block_config.text_response
        )
        if not success:
            return {"success": False, "msg": msg}
        try:
            submission_info.saved_response = json.dumps(
                prepare_submission_for_serialization(student_sub_data)
            )
            submission_info.has_saved = True

            # Emit analytics event...
            block_config.publish_event(
                "openassessmentblock.save_submission",
                {"saved_response": submission_info.saved_response},
            )
        except Exception:  # pylint: disable=broad-except
            return {
                "success": False,
                "msg": block_config.translate("Please contact support staff."),
            }
        else:
            return {"success": True, "msg": ""}
    else:
        return {
            "success": False,
            "msg": block_config.translate("Submission data missing. Please contact support staff."),
        }

def _create_submission_response(submission):
    """
    Wrap submission info for return to client

    Returns:
        (tuple): True (indicates success), student item, attempt number
    """
    status = True
    status_tag = submission.get("student_item")
    status_text = submission.get("attempt_number")

    return (status, status_tag, status_text)

### FILE UPLOAD ###

def save_files_descriptions(block_config, submission_info, data):
    """
    Save the metadata for each uploaded file.

    Args:
        block_config (ORAConfigAPI)
        submission_info (SubmissionAPI)
        data (dict): Data should have a single key 'fileMetadata' that contains
            a list of dictionaries with the following keys: 'description','fileName', and 'fileSize'
        each element of the list maps to a single file

    Returns:
        dict: Contains a bool 'success' and unicode string 'msg'.
    """
    failure_response = {
        "success": False,
        "msg": block_config.translate("Files descriptions were not submitted."),
    }

    if "fileMetadata" not in data:
        return failure_response

    if not isinstance(data["fileMetadata"], list):
        return failure_response

    file_data = [
        {
            "description": item["description"],
            "name": item["fileName"],
            "size": item["fileSize"],
        }
        for item in data["fileMetadata"]
    ]

    for new_upload in file_data:
        if not all(
            [
                isinstance(new_upload["description"], str),
                isinstance(new_upload["name"], str),
                isinstance(new_upload["size"], int),
            ]
        ):
            return failure_response

    try:
        submission_info.files.file_manager.append_uploads(*file_data)
        # Emit analytics event...
        block_config.publish_event(
            "openassessmentblock.save_files_descriptions",
            {"saved_response": submission_info.saved_files_descriptions},
        )
    except FileUploadError as exc:
        logger.exception(
            "FileUploadError: file description for data %s failed with error %s",
            data,
            exc,
            exc_info=True,
        )
        return {
            "success": False,
            "msg": block_config._("Files metadata could not be saved."),
        }
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception(
            "FileUploadError: unhandled exception for data %s. Error: %s",
            data,
            exc,
            exc_info=True,
        )
    return {"success": True, "msg": ""}



def upload_url(block_config, submission_info, data):
    """
    Request a URL to be used for uploading content related to this
    submission.

    Returns:
        A URL to be used to upload content associated with this submission.

    """
    if "contentType" not in data or "filename" not in data:
        return {
            "success": False,
            "msg": block_config.translate("There was an error uploading your file."),
        }

    if not block_config.allow_multiple_files:
        # Here we check if there are existing file uploads by checking for
        # an existing download url for any of the upload slots.
        # Note that we can't use self.saved_files_descriptions because that
        # is populated before files are uploaded
        for file_index in range(submission_info.files.max_allowed_uploads):
            file_url = submission_info.files.get_download_url(file_index)
            if file_url:
                return {
                    "success": False,
                    "msg": block_config.translate(
                        "Only a single file upload is allowed for this assessment."
                    ),
                }

    file_num = int(data.get("filenum", 0))

    _, file_ext = os.path.splitext(data["filename"])
    file_ext = file_ext.strip(".") if file_ext else None
    content_type = data["contentType"]

    # Validate that there are no data issues and file type is allowed
    if not submission_info.files.is_supported_upload_type(file_ext, content_type):
        return {
            "success": False,
            "msg": block_config.translate(
                "File upload failed: unsupported file type."
                "Only the supported file types can be uploaded."
                "If you have questions, please reach out to the course team."
            ),
        }

    # Attempt to upload
    file_num = int(data.get("filenum", 0))
    try:
        key = submission_info.files.get_file_key(file_num)
        url = submission_info.files.get_upload_url(key, content_type)
        return {"success": True, "url": url}
    except FileUploadError:
        logger.exception(
            "FileUploadError:Error retrieving upload URL for the data: %s.", data
        )
        return {"success": False, "msg": block_config.translate("Error retrieving upload URL.")}

def download_url(submission_info, data):
    """
    Request a download URL.

    Returns:
        A URL to be used for downloading content related to the submission.
    """
    file_num = int(data.get("filenum", 0))
    return {"success": True, "url": submission_info.files.get_download_url(file_num)}

def remove_uploaded_file(block_config, submission_info, data):
    """
    Removes uploaded user file.
    """
    file_index = data.get("filenum", -1)
    try:
        file_index = int(file_index)
    except ValueError:
        file_index = -1
    student_item_key = submission_info.files.get_file_key(file_index)
    if submission_info.files.can_delete_file(file_index):
        try:
            submission_info.files.delete_uploaded_file(file_index)

            # Emit analytics event...
            block_config.publish_event(
                "openassessmentblock.remove_uploaded_file",
                {"student_item_key": student_item_key},
            )
            logger.debug("Deleted file %s", student_item_key)
            return {"success": True}
        except FileUploadError as exc:
            logger.exception(
                "FileUploadError: Error when deleting file %s : %s",
                student_item_key,
                exc,
                exc_info=True,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "FileUploadError: unhandled exception for data %s. Error: %s",
                data,
                exc,
                exc_info=True,
            )

    return {"success": False}
