""" A Mixin for Response submissions. """
import logging

from django.utils.functional import cached_property

from openassessment.fileupload import api as file_upload_api
from openassessment.fileupload.exceptions import FileUploadError

from ..data import OraSubmissionAnswerFactory
from .data_conversion import (
    prepare_submission_for_serialization,
)


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class NoTeamToCreateSubmissionForError(Exception):
    pass


class EmptySubmissionError(Exception):
    pass


class SubmissionMixin:
    """
    Submission Mixin introducing all Submission-related functionality.

    Submission Mixin contains all logic and handlers associated with rendering
    the submission section of the front end, as well as making all API calls to
    the middle tier for constructing new submissions, or fetching submissions.

    SubmissionMixin is a Mixin for the OpenAssessmentBlock. Functions in the
    SubmissionMixin call into the OpenAssessmentBlock functions and will not
    work outside the scope of OpenAssessmentBlock.
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

    def create_team_submission(self, student_sub_data):
        """ A student submitting for a team should generate matching submissions for every member of the team. """
        if not self.has_team():
            msg = "Student {} has no team for course {}".format(
                self.get_student_item_dict()['student_id'],
                self.course_id
            )
            logger.exception(msg)
            raise NoTeamToCreateSubmissionForError(msg)

        # Import is placed here to avoid model import at project startup.
        from submissions import team_api

        team_info = self.get_team_info()
        # Store the student's response text in a JSON-encodable dict
        # so that later we can add additional response fields.
        student_sub_dict = prepare_submission_for_serialization(student_sub_data)

        self._collect_files_for_submission(student_sub_dict)

        self.check_for_empty_submission_and_raise_error(student_sub_dict)

        submitter_anonymous_user_id = self.xmodule_runtime.anonymous_student_id
        user = self.get_real_user(submitter_anonymous_user_id)
        student_item_dict = self.get_student_item_dict(anonymous_user_id=submitter_anonymous_user_id)
        anonymous_student_ids = self.get_anonymous_user_ids_for_team()
        submission = team_api.create_submission_for_team(
            self.course_id,
            student_item_dict['item_id'],
            team_info['team_id'],
            user.id,
            anonymous_student_ids,
            student_sub_dict,
        )

        self.create_team_workflow(submission["team_submission_uuid"])
        # Emit analytics event...
        self.runtime.publish(
            self,
            "openassessmentblock.create_team_submission",
            {
                "submission_uuid": submission["team_submission_uuid"],
                "team_id": team_info["team_id"],
                "attempt_number": submission["attempt_number"],
                "created_at": submission["created_at"],
                "submitted_at": submission["submitted_at"],
                "answer": submission["answer"],
            }
        )
        return submission

    # TODO - Remove, temporarily surfacing to avoid test refactors
    def create_submission(self, student_item_dict, student_sub_data):
        """ Creates submission for the submitted assessment response or a list for a team assessment. """
        return self.submission_data.create_submission(student_item_dict, student_sub_data)

    def check_for_empty_submission_and_raise_error(self, student_sub_dict):
        """
        Check if student_sub_dict has any submission content so that we don't
        create empty submissions.

        If there are no text responses and no file responses, raise an EmptySubmissionError
        """
        has_content = False

        # Does the student_sub_dict have any non-zero-length strings in 'parts'?
        has_content |= any(part.get('text', '') for part in student_sub_dict.get('parts', []))

        # Are there any file_keys in student_sub_dict?
        has_content |= len(student_sub_dict.get('file_keys', [])) > 0

        if not has_content:
            raise EmptySubmissionError

    ### FILE UPLOADS ###

    def _collect_files_for_submission(self, student_sub_dict):
        """ Collect files from CSM for individual submisisons or SharedFileUpload for team submisisons. """

        if not self.file_upload_type:
            return None

        for field in ('file_keys', 'files_descriptions', 'files_names', 'files_sizes'):
            student_sub_dict[field] = []

        team_id = None if not self.has_team() else self.team.team_id
        uploads = self.file_manager.get_uploads(team_id=team_id)
        if self.is_team_assignment():
            uploads += self.file_manager.get_team_uploads(team_id=team_id)

        for upload in uploads:
            student_sub_dict['file_keys'].append(upload.key)
            student_sub_dict['files_descriptions'].append(upload.description)
            student_sub_dict['files_names'].append(upload.name)
            student_sub_dict['files_sizes'].append(upload.size)

        return student_sub_dict

    def _can_delete_file(self, filenum):
        """
        Helper function, wraps `file_upload_api.can_delete_file()`.
        """
        team_id = self.get_team_info().get('team_id')
        key = self._get_student_item_key(filenum)
        current_user_id = self.get_student_item_dict()['student_id']
        return file_upload_api.can_delete_file(current_user_id, self.teams_enabled, key, team_id)

    def _get_download_url(self, file_num=0):
        """
        Internal function for retrieving the download url.

        """
        return self._get_url_by_file_key(self._get_student_item_key(file_num))

    def _get_student_item_key(self, num=0):
        """
        Simple utility method to generate a common file upload key based on
        the student item.

        Returns:
            A string representation of the key.

        """
        return file_upload_api.get_student_file_key(self.get_student_item_dict(), index=num)

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
