""" A Mixin for Response submissions. """
import logging

from django.utils.functional import cached_property

from openassessment.fileupload import api as file_upload_api
from openassessment.fileupload.exceptions import FileUploadError

from openassessment.data import OraSubmissionAnswerFactory

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class FilesMixin:
    """
    Files Mixin introducing all Files-related functionality.
    """

    ALLOWED_IMAGE_MIME_TYPES = ['image/gif', 'image/jpeg', 'image/pjpeg', 'image/png']  # pragma: no cover
    ALLOWED_IMAGE_EXTENSIONS = ['gif', 'jpg', 'jpeg', 'jfif', 'pjpeg', 'pjp', 'png']  # pragma: no cover

    ALLOWED_FILE_MIME_TYPES = ['application/pdf'] + ALLOWED_IMAGE_MIME_TYPES  # pragma: no cover
    ALLOWED_FILE_EXTENSIONS = ['pdf'] + ALLOWED_IMAGE_EXTENSIONS  # pragma: no cover

    MAX_FILES_COUNT = 20  # pragma: no cover

    # taken from http://www.howtogeek.com/137270/50-file-extensions-that-are-potentially-dangerous-on-windows/
    # and http://pcsupport.about.com/od/tipstricks/a/execfileext.htm
    # left out .js and office extensions
    FILE_EXT_BLACK_LIST = [
        'exe', 'msi', 'app', 'dmg', 'com', 'pif', 'application', 'gadget',
        'msp', 'scr', 'hta', 'cpl', 'msc', 'jar', 'bat', 'cmd', 'vb', 'vbs',
        'jse', 'ws', 'wsf', 'wsc', 'wsh', 'scf', 'lnk', 'inf', 'reg', 'ps1',
        'ps1xml', 'ps2', 'ps2xml', 'psc1', 'psc2', 'msh', 'msh1', 'msh2', 'mshxml',
        'msh1xml', 'msh2xml', 'action', 'apk', 'app', 'bin', 'command', 'csh',
        'ins', 'inx', 'ipa', 'isu', 'job', 'mst', 'osx', 'out', 'paf', 'prg',
        'rgs', 'run', 'sct', 'shb', 'shs', 'u3p', 'vbscript', 'vbe', 'workflow',
        'htm', 'html',
    ]

    FILE_UPLOAD_PRESETS = {
        'image': {
            'mime_types': ALLOWED_IMAGE_MIME_TYPES,
            'extensions': ALLOWED_IMAGE_EXTENSIONS
        },
        'pdf-and-image': {
            'mime_types': ALLOWED_FILE_MIME_TYPES,
            'extensions': ALLOWED_FILE_EXTENSIONS,
        },
        'custom': {}
    }

    @cached_property
    def file_manager(self):
        return file_upload_api.FileUploadManager(self)

    # FILE UPLOADS
    @classmethod
    def _get_url_by_file_key(cls, key):
        """
        Return download url for some particular file key.

        """
        url = ''
        try:
            if key:
                url = file_upload_api.get_download_url(key)
        except FileUploadError as exc:
            logger.exception(
                "FileUploadError: Download url for file key %s failed with error %s",
                key,
                exc,
                exc_info=True
            )

        return url

    @classmethod
    def get_download_urls_from_submission(cls, submission):
        """
        Returns a download URLs for retrieving content within a submission.

        Args:
            submission (dict): Dictionary containing an answer and a file_keys.
                The file_keys is used to try and retrieve a download urls
                with related content

        Returns:
            List of FileDescriptor dicts for each file associated with the submission

        """
        urls = []
        raw_answer = submission.get('answer')
        answer = OraSubmissionAnswerFactory.parse_submission_raw_answer(raw_answer)
        for file_upload in answer.get_file_uploads(missing_blank=True):
            file_download_url = cls._get_url_by_file_key(file_upload.key)
            if file_download_url:
                urls.append(
                    file_upload_api.FileDescriptor(
                        download_url=file_download_url,
                        description=file_upload.description,
                        name=file_upload.name,
                        size=file_upload.size,
                        show_delete_button=False
                    )._asdict()
                )
        return urls

    def get_files_info_from_user_state(self, username):
        """
        Returns the files information from the user state for a given username.

        If the files information is present in the user state, return a list of following tuple:
        (file_download_url, file_description, file_name)

        Arguments:
            username(str): user's name whose state is being check for files information.
        Returns:
            List of FileDescriptor dicts, if present, else empty list.
        """

        files_info = []
        user_state = self.get_user_state(username)
        item_dict = self.get_student_item_dict_from_username_or_email(username)
        if 'saved_files_descriptions' in user_state:
            # pylint: disable=protected-access
            files_descriptions = file_upload_api._safe_load_json_list(
                user_state.get('saved_files_descriptions'),
                log_error=True
            )
            files_names = file_upload_api._safe_load_json_list(
                user_state.get('saved_files_names', '[]'),
                log_error=True
            )
            for index, description in enumerate(files_descriptions):
                file_key = file_upload_api.get_student_file_key(item_dict, index)
                download_url = self._get_url_by_file_key(file_key)
                if download_url:
                    file_name = files_names[index] if index < len(files_names) else ''
                    files_info.append(
                        file_upload_api.FileDescriptor(
                            download_url=download_url,
                            description=description,
                            name=file_name,
                            size=None,
                            show_delete_button=False
                        )._asdict()
                    )
                else:
                    # If file has been removed, the URL doesn't exist
                    logger.info(
                        "URLWorkaround: no URL for description %s & key %s for user:%s",
                        description,
                        username,
                        file_key
                    )
                    continue
        return files_info

    def get_all_upload_urls_for_user(self, username_or_email):
        """
        For a particular ORA block, get the download URLs for all the files uploaded and still present.

        Used for an extreme edge case, where the stored files indices are out of sync with
        the uploaded files, this is a last resort to get the download URLs of all the files
        that have been uploaded by a learner in an ORA block(and haven't been deleted from the storage).
        Starting from 0 index to maximum file upload count possible, this checks if a file exists against
        every index. If present, add the info, else repeat it for the next indices.

        Arguments:
            username_or_email(str): username or email of the learner whose files' information is to be obtained.
        Returns:
            List of FileDescriptor dicts
        """
        file_uploads = []
        student_item_dict = self.get_student_item_dict_from_username_or_email(username_or_email)
        for index in range(self.MAX_FILES_COUNT):
            file_key = file_upload_api.get_student_file_key(student_item_dict, index)
            download_url = ''
            try:
                download_url = file_upload_api.get_download_url(file_key)
            except FileUploadError:
                pass

            if download_url:
                logger.info(
                    "Download URL exists for key %s in block %s for user %s",
                    file_key,
                    username_or_email,
                    str(self.location)
                )
                file_uploads.append(
                    file_upload_api.FileDescriptor(
                        download_url=download_url,
                        description='',
                        name='',
                        size=None,
                        show_delete_button=False
                    )._asdict()
                )
            else:
                continue

        return file_uploads

    def get_allowed_file_types_or_preset(self):
        """
        If allowed files are not explicitly set for file uploads, use preset extensions
        """
        if self.white_listed_file_types:
            return self.white_listed_file_types
        elif self.file_upload_type == 'image':
            return self.ALLOWED_IMAGE_EXTENSIONS
        elif self.file_upload_type == 'pdf-and-image':
            return self.ALLOWED_FILE_EXTENSIONS
        return None
