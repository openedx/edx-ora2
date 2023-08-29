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

        self._file_manager = block.file_manager
        self._workflow = block.workflow_data.workflow
        self._file_upload_type = block.file_upload_type
        self._team_id = team_id

    @property
    def max_allowed_uploads(self):
        return self._block.MAX_FILES_COUNT

    @property
    def uploaded_files(self):
        """
        Get files uploaded by users, where file uploads are enabled.

        Returns:
        * List(File descriptors) if ORA supports file uploads, can be empty.
        * None when file uploads not enabled.
        """
        if self._file_upload_type:
            file_urls = self.file_manager.file_descriptors(
                team_id=self._team_id, include_deleted=True
            )
            team_file_urls = self.file_manager.team_file_descriptors(
                team_id=self._team_id
            )
            return {"file_urls": file_urls, "team_file_urls": team_file_urls}
        return None

    def is_supported_upload_type(self, file_ext, content_type):
        """Whether or not a particular file type is allowed for this ORA"""
        return self._block.is_supported_upload_type(file_ext, content_type)

    @property
    def saved_files_descriptions(self):
        return self._block.saved_files_descriptions

    @property
    def file_manager(self):
        return self._file_manager

    def get_file_key(self, file_number):
        student_item_dict = self._block.get_student_item_dict()
        return file_upload_api.get_student_file_key(
            student_item_dict, index=file_number
        )

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
