""" A Mixin for Response submissions. """


import json
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.utils.functional import cached_property

from xblock.core import XBlock
from xblock.exceptions import NoSuchServiceError
from openassessment.fileupload import api as file_upload_api
from openassessment.fileupload.exceptions import FileUploadError
from openassessment.workflow.errors import AssessmentWorkflowError

from .data_conversion import create_submission_dict, prepare_submission_for_serialization
from .resolve_dates import DISTANT_FUTURE
from .user_data import get_user_preferences
from .validation import validate_submission

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class NoTeamToCreateSubmissionForError(Exception):
    pass


class SubmissionMixin:
    """Submission Mixin introducing all Submission-related functionality.

    Submission Mixin contains all logic and handlers associated with rendering
    the submission section of the front end, as well as making all API calls to
    the middle tier for constructing new submissions, or fetching submissions.

    SubmissionMixin is a Mixin for the OpenAssessmentBlock. Functions in the
    SubmissionMixin call into the OpenAssessmentBlock functions and will not
    work outside the scope of OpenAssessmentBlock.

    """

    ALLOWED_IMAGE_MIME_TYPES = ['image/gif', 'image/jpeg', 'image/pjpeg', 'image/png']  # pragma: no cover

    ALLOWED_FILE_MIME_TYPES = ['application/pdf'] + ALLOWED_IMAGE_MIME_TYPES  # pragma: no cover

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

    @cached_property
    def file_manager(self):
        return file_upload_api.FileUploadManager(self)

    @XBlock.json_handler
    def submit(self, data, suffix=''):  # pylint: disable=unused-argument
        """Place the submission text into Openassessment system

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
                of a team submisison, one entry per student entry.

        """
        # Import is placed here to avoid model import at project startup.
        from submissions import api
        if 'submission' not in data:
            return (
                False,
                'EBADARGS',
                self._(u'"submission" required to submit answer.')
            )

        status = False
        student_sub_data = data['submission']
        success, msg = validate_submission(student_sub_data, self.prompts, self._, self.text_response)
        if not success:
            return (
                False,
                'EBADARGS',
                msg
            )

        student_item_dict = self.get_student_item_dict()

        # Short-circuit if no user is defined (as in Studio Preview mode)
        # Since students can't submit, they will never be able to progress in the workflow
        if self.in_studio_preview:
            return (
                False,
                'ENOPREVIEW',
                self._(u'To submit a response, view this component in Preview or Live mode.')
            )

        workflow = self.get_workflow_info()

        status_tag = 'ENOMULTI'  # It is an error to submit multiple times for the same item
        status_text = self._(u'Multiple submissions are not allowed.')

        if not workflow:
            try:

                # a submission for a team generates matching submissions for all members
                if self.is_team_assignment():
                    submission = self.create_team_submission(student_sub_data)
                else:
                    submission = self.create_submission(student_item_dict, student_sub_data)
                return self._create_submission_response(submission)

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
                    for answer_err in err.field_errors.get('answer', [])
                )
                if answer_too_long:
                    status_tag = 'EANSWERLENGTH'
                else:
                    msg = (
                        u"The submissions API reported an invalid request error "
                        u"when submitting a response for the user: {student_item}"
                    ).format(student_item=student_item_dict)
                    logger.exception(msg)
                    status_tag = 'EBADFORM'
                    status_text = msg
            except (api.SubmissionError, AssessmentWorkflowError, NoTeamToCreateSubmissionForError):
                msg = (
                    u"An unknown error occurred while submitting "
                    u"a response for the user: {student_item}"
                ).format(student_item=student_item_dict)
                logger.exception(msg)
                status_tag = 'EUNKNOWN'
                status_text = self._(u'API returned unclassified exception.')

        # error cases fall through to here
        return status, status_tag, status_text

    def _create_submission_response(self, submission):
        """ Wrap submisison info for return to client

            Returns:
                (tuple): True (indicates success), student item, attempt number
        """
        status = True
        status_tag = submission.get('student_item')
        status_text = submission.get('attempt_number')

        return (status, status_tag, status_text)

    @XBlock.json_handler
    def save_submission(self, data, suffix=''):  # pylint: disable=unused-argument
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
        if 'submission' in data:
            student_sub_data = data['submission']
            success, msg = validate_submission(student_sub_data, self.prompts, self._, self.text_response)
            if not success:
                return {'success': False, 'msg': msg}
            try:
                self.saved_response = json.dumps(
                    prepare_submission_for_serialization(student_sub_data)
                )
                self.has_saved = True

                # Emit analytics event...
                self.runtime.publish(
                    self,
                    "openassessmentblock.save_submission",
                    {"saved_response": self.saved_response}
                )
            except Exception:  # pylint: disable=broad-except
                return {'success': False, 'msg': self._(u"This response could not be saved.")}
            else:
                return {'success': True, 'msg': u''}
        else:
            return {'success': False, 'msg': self._(u"This response was not submitted.")}

    @XBlock.json_handler
    def save_files_descriptions(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Save the metadata for each uploaded file.

        Args:
            data (dict): Data should have a single key 'fileMetadata' that contains
                a list of dictionaries with the following keys: 'description','fileName', and 'fileSize'
            each element of the list maps to a single file
            suffix (str): Not used.

        Returns:
            dict: Contains a bool 'success' and unicode string 'msg'.
        """
        failure_response = {'success': False, 'msg': self._(u"Files descriptions were not submitted.")}

        if 'fileMetadata' not in data:
            return failure_response

        if not isinstance(data['fileMetadata'], list):
            return failure_response

        file_data = [
            {
                'description': item['description'],
                'name': item['fileName'],
                'size': item['fileSize'],
            } for item in data['fileMetadata']
        ]

        for new_upload in file_data:
            if not all([
                isinstance(new_upload['description'], str),
                isinstance(new_upload['name'], str),
                isinstance(new_upload['size'], int),
            ]):
                return failure_response

        try:
            self.file_manager.append_uploads(*file_data)
            # Emit analytics event...
            self.runtime.publish(
                self,
                "openassessmentblock.save_files_descriptions",
                {"saved_response": self.saved_files_descriptions}
            )
        except FileUploadError as exc:
            logger.exception(u"FileUploadError: file description for data {data} failed with error {error}".format(
                data=data,
                error=exc
            ))
            return {'success': False, 'msg': self._(u"Files metadata could not be saved.")}

        return {'success': True, 'msg': u''}

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

    def create_submission(self, student_item_dict, student_sub_data):
        """ Creates submission for the submitted assessment response or a list for a team assessment. """
        # Import is placed here to avoid model import at project startup.
        from submissions import api

        # Store the student's response text in a JSON-encodable dict
        # so that later we can add additional response fields.
        student_sub_dict = prepare_submission_for_serialization(student_sub_data)

        self._collect_files_for_submission(student_sub_dict)

        submission = api.create_submission(student_item_dict, student_sub_dict)
        self.create_workflow(submission["uuid"])
        self.submission_uuid = submission["uuid"]

        # Emit analytics event...
        self.runtime.publish(
            self,
            "openassessmentblock.create_submission",
            {
                "submission_uuid": submission["uuid"],
                "attempt_number": submission["attempt_number"],
                "created_at": submission["created_at"],
                "submitted_at": submission["submitted_at"],
                "answer": submission["answer"],
            }
        )

        return submission

    def _collect_files_for_submission(self, student_sub_dict):
        """ Collect files from CSM for individual submisisons or SharedFileUpload for team submisisons. """

        if not self.file_upload_type:
            return None

        for field in ('file_keys', 'files_descriptions', 'files_names', 'files_sizes'):
            student_sub_dict[field] = []

        uploads = self.file_manager.get_uploads()
        if self.is_team_assignment():
            uploads += self.file_manager.get_team_uploads()

        for upload in uploads:
            student_sub_dict['file_keys'].append(upload.key)
            student_sub_dict['files_descriptions'].append(upload.description)
            student_sub_dict['files_names'].append(upload.name)
            student_sub_dict['files_sizes'].append(upload.size)

        return student_sub_dict

    @XBlock.json_handler
    def get_student_username(self, data, suffix):  # pylint: disable=unused-argument
        """
        Gets the username of the current student for use in team lookup.
        """
        anonymous_id = self.xmodule_runtime.anonymous_student_id
        return {'username': self.get_username(anonymous_id)}

    @XBlock.json_handler
    def upload_url(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Request a URL to be used for uploading content related to this
        submission.

        Returns:
            A URL to be used to upload content associated with this submission.

        """
        if 'contentType' not in data or 'filename' not in data:
            return {'success': False, 'msg': self._(u"There was an error uploading your file.")}
        content_type = data['contentType']
        file_name = data['filename']
        file_name_parts = file_name.split('.')

        file_num = int(data.get('filenum', 0))

        file_ext = file_name_parts[-1] if len(file_name_parts) > 1 else None
        if self.file_upload_type == 'image' and content_type not in self.ALLOWED_IMAGE_MIME_TYPES:
            return {'success': False, 'msg': self._(u"Content type must be GIF, PNG or JPG.")}

        if self.file_upload_type == 'pdf-and-image' and content_type not in self.ALLOWED_FILE_MIME_TYPES:
            return {'success': False, 'msg': self._(u"Content type must be PDF, GIF, PNG or JPG.")}

        if self.file_upload_type == 'custom' and file_ext.lower() not in self.white_listed_file_types:
            return {'success': False, 'msg': self._(u"File type must be one of the following types: {}").format(
                ', '.join(self.white_listed_file_types))}

        if file_ext in self.FILE_EXT_BLACK_LIST:
            return {'success': False, 'msg': self._(u"File type is not allowed.")}
        try:
            key = self._get_student_item_key(file_num)
            url = file_upload_api.get_upload_url(key, content_type)
            return {'success': True, 'url': url}
        except FileUploadError:
            logger.exception(u"FileUploadError:Error retrieving upload URL for the data:{data}.".format(data=data))
            return {'success': False, 'msg': self._(u"Error retrieving upload URL.")}

    @XBlock.json_handler
    def download_url(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Request a download URL.

        Returns:
            A URL to be used for downloading content related to the submission.

        """
        file_num = int(data.get('filenum', 0))
        return {'success': True, 'url': self._get_download_url(file_num)}

    @XBlock.json_handler
    def remove_uploaded_file(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Removes uploaded user file.
        """
        filenum = data.get('filenum', -1)
        try:
            filenum = int(filenum)
        except ValueError:
            filenum = -1
        student_item_key = self._get_student_item_key(num=filenum)
        if self._can_delete_file(filenum):
            try:
                self.file_manager.delete_upload(filenum)
                logger.debug("Deleted file {student_item_key}".format(student_item_key=student_item_key))
                return {'success': True}
            except FileUploadError as exc:
                logger.exception("FileUploadError: Error when deleting file {student_item_key} : {exc}".format(
                    student_item_key=student_item_key,
                    exc=exc
                ))

        return {'success': False}

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

    def _get_url_by_file_key(self, key):
        """
        Return download url for some particular file key.

        """
        url = ''
        try:
            if key:
                url = file_upload_api.get_download_url(key)
        except FileUploadError as exc:
            logger.exception(u"FileUploadError: Download url for file key {key} failed with error {error}".format(
                key=key,
                error=exc
            ))

        return url

    def get_download_urls_from_submission(self, submission):
        """
        Returns a download URLs for retrieving content within a submission.

        Args:
            submission (dict): Dictionary containing an answer and a file_keys.
                The file_keys is used to try and retrieve a download urls
                with related content

        Returns:
            List with URLs to related content. If there is no content related to this
            key, or if there is no key for the submission, returns an empty
            list.

        """
        urls = []
        if 'file_keys' in submission['answer']:
            file_keys = submission['answer'].get('file_keys', [])
            descriptions = submission['answer'].get('files_descriptions', [])
            file_names = submission['answer'].get('files_name', submission['answer'].get('files_names', []))
            for idx, key in enumerate(file_keys):
                file_download_url = self._get_url_by_file_key(key)
                if file_download_url:
                    file_description = descriptions[idx].strip() if idx < len(descriptions) else ''
                    try:
                        file_name = file_names[idx].strip() if idx < len(file_names) else ''
                    except AttributeError:
                        file_name = ''
                        logger.error('descriptions[idx] is None in {}'.format(submission))
                    urls.append((file_download_url, file_description, file_name, False))
        elif 'file_key' in submission['answer']:
            key = submission['answer'].get('file_key', '')
            file_download_url = self._get_url_by_file_key(key)
            if file_download_url:
                urls.append((file_download_url, '', '', False))
        return urls

    def get_files_info_from_user_state(self, username):
        """
        Returns the files information from the user state for a given username.

        If the files information is present in the user state, return a list of following tuple:
        (file_download_url, file_description, file_name)

        Arguments:
            username(str): user's name whose state is being check for files information.
        Returns:
            List of files information tuple, if present, else empty list.
        """

        files_info = []
        user_state = self.get_user_state(username)
        item_dict = self.get_student_item_dict_from_username_or_email(username)
        if u'saved_files_descriptions' in user_state:
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
                    files_info.append((download_url, description, file_name, False))
                else:
                    # If file has been removed, the URL doesn't exist
                    logger.info("URLWorkaround: no URL for description {desc} & key {key} for user:{user}".format(
                        desc=description,
                        user=username,
                        key=file_key
                    ))
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
            List of 3-valued tuples, with first value being file URL and other two values as empty string.
            The other 2 values have to be appended to work properly in the template.
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
                logger.info(u"Download URL exists for key {key} in block {block} for user {user}".format(
                    key=file_key,
                    user=username_or_email,
                    block=str(self.location)
                ))
                file_uploads.append((download_url, '', '', False))
            else:
                continue

        return file_uploads

    @staticmethod
    def get_user_submission(submission_uuid):
        """Return the most recent submission by user in workflow

        Return the most recent submission.  If no submission is available,
        return None. All submissions are preserved, but only the most recent
        will be returned in this function, since the active workflow will only
        be concerned with the most recent submission.

        Args:
            submission_uuid (str): The uuid for the submission to retrieve.

        Returns:
            (dict): A dictionary representation of a submission to render to
                the front end.

        """
        # Import is placed here to avoid model import at project startup.
        from submissions import api
        try:
            return api.get_submission(submission_uuid)
        except api.SubmissionRequestError:
            # This error is actually ok.
            return None

    @property
    def save_status(self):
        """
        Return a string indicating whether the response has been saved.

        Returns:
            unicode
        """
        return self._(u'This response has been saved but not submitted.') if self.has_saved else self._(
            u'This response has not been saved.')

    @XBlock.handler
    def render_submission(self, data, suffix=''):  # pylint: disable=unused-argument
        """Renders the Submission HTML section of the XBlock

        Generates the submission HTML for the first section of an Open
        Assessment XBlock. See OpenAssessmentBlock.render_assessment() for
        more information on rendering XBlock sections.

        Needs to support the following scenarios:
        Unanswered and Open
        Unanswered and Closed
        Saved
        Saved and Closed
        Submitted
        Submitted and Closed
        Submitted, waiting assessment
        Submitted and graded

        """
        path, context = self.submission_path_and_context()
        return self.render_assessment(path, context_dict=context)

    def submission_path_and_context(self):
        """
        Determine the template path and context to use when
        rendering the response (submission) step.

        Returns:
            tuple of `(path, context)`, where `path` (str) is the path to the template,
            and `context` (dict) is the template context.

        """
        workflow = self.get_team_workflow_info() if self.teams_enabled else self.get_workflow_info()
        problem_closed, reason, start_date, due_date = self.is_closed('submission')
        user_preferences = get_user_preferences(self.runtime.service(self, 'user'))

        path = 'openassessmentblock/response/oa_response.html'
        context = {
            'user_timezone': user_preferences['user_timezone'],
            'user_language': user_preferences['user_language'],
            "xblock_id": self.get_xblock_id(),
            "text_response": self.text_response,
            "file_upload_response": self.file_upload_response,
            "prompts_type": self.prompts_type,
            "enable_delete_files": False,
        }

        # Due dates can default to the distant future, in which case
        # there's effectively no due date.
        # If we don't add the date to the context, the template won't display it.
        if due_date < DISTANT_FUTURE:
            context["submission_due"] = due_date

        context['file_upload_type'] = self.file_upload_type
        context['allow_latex'] = self.allow_latex

        file_urls = None

        if self.file_upload_type:
            context['file_urls'] = self.file_manager.file_descriptor_tuples(include_deleted=True)
            context['team_file_urls'] = self.file_manager.team_file_descriptor_tuples()
        if self.file_upload_type == 'custom':
            context['white_listed_file_types'] = self.white_listed_file_types

        if not workflow and problem_closed:
            if reason == 'due':
                path = 'openassessmentblock/response/oa_response_closed.html'
            elif reason == 'start':
                context['submission_start'] = start_date
                path = 'openassessmentblock/response/oa_response_unavailable.html'
        elif not workflow:
            # For backwards compatibility. Initially, problems had only one prompt
            # and a string answer. We convert it to the appropriate dict.
            try:
                json.loads(self.saved_response)
                saved_response = {
                    'answer': json.loads(self.saved_response),
                }
            except ValueError:
                saved_response = {
                    'answer': {
                        'text': self.saved_response,
                    },
                }

            context['saved_response'] = create_submission_dict(saved_response, self.prompts)
            context['save_status'] = self.save_status
            context['enable_delete_files'] = True

            if self.teams_enabled:
                try:
                    team_info = self.get_team_info()
                    if team_info:
                        context.update(team_info)
                except ObjectDoesNotExist:
                    error_msg = '{}: User associated with anonymous_user_id {} can not be found.'
                    logger.error(error_msg.format(
                        str(self.location),
                        self.get_student_item_dict()['student_id'],
                    ))
                except NoSuchServiceError:
                    logger.error('{}: Teams service is unavailable'.format(str(self.location)))

            submit_enabled = True
            if self.text_response == 'required' and not self.saved_response:
                submit_enabled = False
            if self.file_upload_response == 'required' and not file_urls:
                submit_enabled = False
            if self.text_response == 'optional' and self.file_upload_response == 'optional' \
                    and not self.saved_response and not file_urls:
                submit_enabled = False
            context['submit_enabled'] = submit_enabled
            path = "openassessmentblock/response/oa_response.html"
        elif workflow["status"] == "cancelled":
            if self.teams_enabled:
                context["workflow_cancellation"] = self.get_team_workflow_cancellation_info(
                    workflow["team_submission_uuid"])
            else:
                context["workflow_cancellation"] = self.get_workflow_cancellation_info(
                    self.submission_uuid)
            context["student_submission"] = self.get_user_submission(
                workflow["submission_uuid"]
            )
            path = 'openassessmentblock/response/oa_response_cancelled.html'
        elif workflow["status"] == "done":
            student_submission = self.get_user_submission(
                workflow["submission_uuid"]
            )
            context["student_submission"] = create_submission_dict(student_submission, self.prompts)
            path = 'openassessmentblock/response/oa_response_graded.html'
        else:
            student_submission = self.get_user_submission(
                workflow["submission_uuid"]
            )
            peer_in_workflow = "peer" in workflow["status_details"]
            self_in_workflow = "self" in workflow["status_details"]
            context["peer_incomplete"] = peer_in_workflow and not workflow["status_details"]["peer"]["complete"]
            context["self_incomplete"] = self_in_workflow and not workflow["status_details"]["self"]["complete"]
            context["student_submission"] = create_submission_dict(student_submission, self.prompts)
            path = 'openassessmentblock/response/oa_response_submitted.html'

        return path, context
