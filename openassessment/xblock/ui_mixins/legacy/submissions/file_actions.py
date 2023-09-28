"""
Actions for file management
"""
import logging
import os
from openassessment.fileupload.exceptions import FileUploadError

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


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
                    "msg": block_config.translate("Only a single file upload is allowed for this assessment."),
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
        logger.exception("FileUploadError:Error retrieving upload URL for the data: %s.", data)
        return {
            "success": False,
            "msg": block_config.translate("Error retrieving upload URL."),
        }


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
