"""
API to encapsulate file CRUD behavior in submissions
"""
import logging

from openassessment.fileupload import api as file_upload_api
from openassessment.fileupload.exceptions import FileUploadError

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class FileAPI:
    def __init__(self, block, team_id):
        self._block = block
        self.team_id = team_id
        self._config_data = block.api_data.config_data

    # Config

    @property
    def max_allowed_uploads(self):
        return self._block.MAX_FILES_COUNT

    @property
    def file_upload_type(self):
        return self._block.file_upload_type

    @property
    def file_manager(self):
        return self._block.file_manager

    # File Uploads
    @property
    def uploaded_files(self):
        """
        Get files uploaded by users, where file uploads are enabled.

        Returns:
        * file_urls (List of File descriptors): files uploaded by user,
          can be empty
        * team_file_urls (List of File descriptors): files uploaded by team,
          can be empty.
        * None when file uploads not enabled.
        """
        if self.file_upload_type:
            file_urls = self.file_manager.file_descriptors(team_id=self.team_id, include_deleted=True)
            team_file_urls = self.file_manager.team_file_descriptors(team_id=self.team_id)
            return {"file_urls": file_urls, "team_file_urls": team_file_urls}
        return None

    # TODO - Determine if we can combine this and uploaded_files
    def get_uploads_for_submission(self):
        """Get a list of uploads for a submission"""
        uploads = self.file_manager.get_uploads(team_id=self.team_id)

        if self._block.is_team_assignment():
            uploads += self.file_manager.get_team_uploads(team_id=self.team_id)

        return uploads

    @property
    def saved_files_descriptions(self):
        return self._config_data.saved_files_descriptions

    # Utils / Actions

    def can_delete_file(self, file_index):
        """
        Is a user allowed to delete this file?

        i.e. are they the uploader and still a member of the team that
        uploaded the file?
        """
        team_id = self.team_id
        key = self.get_file_key(file_index)
        current_user_id = self._block.get_student_item_dict()["student_id"]
        teams_enabled = self._block.is_team_assignment()
        return file_upload_api.can_delete_file(current_user_id, teams_enabled, key, team_id)

    def is_supported_upload_type(self, file_ext, content_type):
        """
        Determine if the uploaded file type/extension is allowed for the
        configured file upload configuration.

        Returns:
            True/False if file type is supported/unsupported
        """
        if self.file_upload_type == "image" and content_type not in self._block.ALLOWED_IMAGE_MIME_TYPES:
            return False

        elif self.file_upload_type == "pdf-and-image" and content_type not in self._block.ALLOWED_FILE_MIME_TYPES:
            return False

        elif self.file_upload_type == "custom" and file_ext.lower() not in self._block.white_listed_file_types:
            return False

        elif file_ext in self._block.FILE_EXT_BLACK_LIST:
            return False

        return True

    def get_file_key(self, file_number):
        """Get file key for {file_number} for current student"""
        student_item_dict = self._block.get_student_item_dict()
        return file_upload_api.get_student_file_key(student_item_dict, index=file_number)

    def get_upload_url(self, key, content_type):
        """Returns key, potentially signed, to upload a file to the file backend"""
        return file_upload_api.get_upload_url(key, content_type)

    def get_download_url(self, file_number):
        """
        Get download URL for a given file number

        Returns
        * URL (string)

        Raises:
        * FileUploadError: when failing to get a download URL
        """
        file_key = self.get_file_key(file_number)
        url = ""
        try:
            if file_key:
                url = file_upload_api.get_download_url(file_key)
        except FileUploadError as exc:
            logger.exception(
                "FileUploadError: Download url for file key %s failed with error %s",
                file_key,
                exc,
                exc_info=True,
            )

        return url

    def delete_uploaded_file(self, file_index):
        self.file_manager.delete_upload(file_index)

    def get_download_urls_from_submission(self, submission):
        return self._block.get_download_urls_from_submission(submission)

    def get_files_info_from_user_state(self, username):
        return self._block.get_files_info_from_user_state(username)

    def get_all_upload_urls_for_user(self, username_or_email):
        return self._block.get_all_upload_urls_for_user(username_or_email)

    def get_allowed_file_types_or_preset(self):
        return self._block.get_allowed_file_types_or_preset
