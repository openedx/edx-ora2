""" A Mixin for Response submissions. """
from __future__ import absolute_import, unicode_literals

import json
import logging

import six
from six.moves import range

from openassessment.fileupload import api as file_upload_api
from openassessment.fileupload.exceptions import FileUploadError
from openassessment.workflow.errors import AssessmentWorkflowError
from xblock.core import XBlock

from .data_conversion import create_submission_dict, prepare_submission_for_serialization
from .resolve_dates import DISTANT_FUTURE
from .user_data import get_user_preferences
from .validation import validate_submission

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def _safe_load_json_list(field):
    """
    Tries to load JSON-ified string,
    returns an empty list if we try to load some non-JSON-encoded string.
    """
    try:
        return json.loads(field)
    except ValueError:
        return []


class SubmissionMixin(object):
    """Submission Mixin introducing all Submission-related functionality.

    Submission Mixin contains all logic and handlers associated with rendering
    the submission section of the front end, as well as making all API calls to
    the middle tier for constructing new submissions, or fetching submissions.

    SubmissionMixin is a Mixin for the OpenAssessmentBlock. Functions in the
    SubmissionMixin call into the OpenAssessmentBlock functions and will not
    work outside the scope of OpenAssessmentBlock.

    """

    ALLOWED_IMAGE_MIME_TYPES = ['image/gif', 'image/jpeg', 'image/pjpeg', 'image/png']

    ALLOWED_FILE_MIME_TYPES = ['application/pdf'] + ALLOWED_IMAGE_MIME_TYPES

    MAX_FILES_COUNT = 20

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
            (tuple): Returns the status (boolean) of this request, the
                associated status tag (str), and status text (unicode).

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
                submission = self.create_submission(student_item_dict, student_sub_data)
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
            except (api.SubmissionError, AssessmentWorkflowError):
                msg = (
                    u"An unknown error occurred while submitting "
                    u"a response for the user: {student_item}"
                ).format(student_item=student_item_dict)
                logger.exception(msg)
                status_tag = 'EUNKNOWN'
                status_text = self._(u'API returned unclassified exception.')
            else:
                status = True
                status_tag = submission.get('student_item')
                status_text = submission.get('attempt_number')

        return status, status_tag, status_text

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

    def get_saved_file_metadata(self):
        """
        Get list of (file_download_url, file_description, file_name, file_size) for all uploaded files.
        Deleted files are represented as (None, None, None, 0)
        """
        saved_file_descriptions, saved_file_names, saved_file_sizes = self.get_safe_normalized_file_metadata()

        file_metadata = []

        if not saved_file_descriptions:
            # This is the old behavior, required for a corner case and should be eventually removed.
            # https://github.com/edx/edx-ora2/pull/1275 closed a loophole that allowed files
            # to be uploaded without descriptions. In that case, saved_file_descriptions would be
            # an empty list. If there are currently users in that state who have files uploaded
            # with no descriptions but have not yet submitted, they will fall here.
            for i in range(self.MAX_FILES_COUNT):
                file_url = self._get_download_url(i)
                file_description = ''
                file_name = ''
                file_size = 0
                if file_url:
                    try:
                        file_description = saved_file_descriptions[i]
                        file_name = saved_file_names[i]
                        file_size = saved_file_sizes[i]
                    except IndexError:
                        pass
                    file_metadata.append((file_url, file_description, file_name, file_size))
                else:
                    break
        else:
            zipped_metadata = zip(saved_file_descriptions, saved_file_names, saved_file_sizes)
            for i, (file_description, file_name, file_size) in enumerate(zipped_metadata):
                if file_description is None:
                    # We are passing Nones to the template because when files are deleted, we still want to
                    # represent them as empty elements in order to preserve the indices and thus urls of the
                    # remaining files.
                    file_metadata.append((None, None, None, 0))
                else:
                    file_url = self._get_download_url(i)
                    file_metadata.append((file_url, file_description, file_name, file_size))
        return file_metadata

    def get_file_descriptions(self):
        return _safe_load_json_list(self.saved_files_descriptions)

    def set_file_descriptions(self, file_description_list):
        self.saved_files_descriptions = json.dumps(file_description_list)

    def get_file_names(self):
        return _safe_load_json_list(self.saved_files_names)

    def set_file_names(self, file_name_list):
        self.saved_files_names = json.dumps(file_name_list)

    def get_file_sizes(self):
        return _safe_load_json_list(self.saved_files_sizes)

    def set_file_sizes(self, file_size_list):
        self.saved_files_sizes = json.dumps(file_size_list)

    def fix_file_names(self, descriptions=None):
        descriptions = descriptions or self.get_file_descriptions()
        if len(self.get_file_names()) != len(descriptions):
            self.set_file_names([None for _ in range(len(descriptions))])
        return self.get_file_names()

    def fix_file_sizes(self, descriptions=None):
        descriptions = descriptions or self.get_file_descriptions()
        if len(self.get_file_sizes()) != len(descriptions):
            self.set_file_sizes([None for _ in range(len(descriptions))])
        return self.get_file_sizes()

    def get_safe_normalized_file_metadata(self):
        descriptions = self.get_file_descriptions()
        names = self.fix_file_names(descriptions)
        sizes = self.fix_file_sizes(descriptions)
        return descriptions, names, sizes

    def append_safe_normalized_file_metadata(self, descriptions_to_add, names_to_add, sizes_to_add):
        """
        Given lists of new file metadata, write the new metadata to our stored file metadata fields

        Args:
            descriptions_to_add: a list of file descriptions
            names_to_add: a list of file names
            sizes_to_add: a list of file sizes as integers

        Returns: newly updated file metadata fields
        """
        if not (len(descriptions_to_add) == len(names_to_add) == len(sizes_to_add)):
            message = (
                'Attempted to append file metadata of differing lengths: '
                'descriptions = {}, names = {}, sizes = {}'
            )
            raise FileUploadError(message.format(descriptions_to_add, names_to_add, sizes_to_add))

        existing_file_descriptions, existing_file_names, existing_file_sizes = self.get_safe_normalized_file_metadata()

        new_descriptions = existing_file_descriptions + descriptions_to_add
        self.set_file_descriptions(new_descriptions)

        new_names = existing_file_names + names_to_add
        self.set_file_names(new_names)

        new_sizes = existing_file_sizes + sizes_to_add
        self.set_file_sizes(new_sizes)

        return new_descriptions, new_names, new_sizes

    def delete_safe_normalized_file_metadata(self, index):
        """
        Given a file index to remove, null out its metadata in our stored file metadata fields

        Args:
            index: file index to remove

        Returns: newly updated file metadata fields
        """
        stored_file_descriptions, stored_file_names, stored_file_sizes = self.get_safe_normalized_file_metadata()

        stored_file_descriptions[index] = None
        self.set_file_descriptions(stored_file_descriptions)

        stored_file_names[index] = None
        self.set_file_names(stored_file_names)

        stored_file_sizes[index] = 0
        self.set_file_sizes(stored_file_sizes)

        return stored_file_descriptions, stored_file_names, stored_file_sizes

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

        file_data = data['fileMetadata']

        if not isinstance(file_data, list):
            return failure_response

        file_descriptions = [desc['description'] for desc in file_data]
        file_names = [desc['fileName'] for desc in file_data]
        file_sizes = [desc['fileSize'] for desc in file_data]

        if not all([
            all([isinstance(description, six.string_types) for description in file_descriptions]),
            all([isinstance(name, six.string_types) for name in file_names]),
            all([isinstance(size, six.integer_types) for size in file_sizes]),
        ]):
            return failure_response

        try:
            self.append_safe_normalized_file_metadata(file_descriptions, file_names, file_sizes)
            # Emit analytics event...
            self.runtime.publish(
                self,
                "openassessmentblock.save_files_descriptions",
                {"saved_response": self.saved_files_descriptions}
            )
        except FileUploadError as exc:
            logger.exception(six.text_type(exc))
            return {'success': False, 'msg': self._(u"Files metadata could not be saved.")}

        return {'success': True, 'msg': u''}

    def create_submission(self, student_item_dict, student_sub_data):
        """ Creates submission for the submitted assessment response. """
        # Import is placed here to avoid model import at project startup.
        from submissions import api

        # Store the student's response text in a JSON-encodable dict
        # so that later we can add additional response fields.
        student_sub_dict = prepare_submission_for_serialization(student_sub_data)

        if self.file_upload_type:
            saved_file_metadata = []
            try:
                saved_file_metadata = self.get_saved_file_metadata()
            except FileUploadError:
                logger.exception(
                    u"FileUploadError for student_item: {student_item_dict}"
                    u" and submission data: {student_sub_data} with file".format(
                        student_item_dict=student_item_dict,
                        student_sub_data=student_sub_data,
                    )
                )

            student_sub_dict['file_keys'] = []
            student_sub_dict['files_descriptions'] = []
            student_sub_dict['files_name'] = []
            student_sub_dict['files_sizes'] = []
            for i, (file_url, file_description, file_name, file_size) in enumerate(saved_file_metadata):
                if not file_url:
                    continue
                key_to_save = self._get_student_item_key(i)
                student_sub_dict['file_keys'].append(key_to_save)
                student_sub_dict['files_descriptions'].append(file_description)
                student_sub_dict['files_name'].append(file_name)
                student_sub_dict['files_sizes'].append(file_size)

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

        removed = file_upload_api.remove_file(self._get_student_item_key(filenum))

        if removed:
            self.delete_safe_normalized_file_metadata(filenum)

        return {'success': removed}

    def _get_download_url(self, file_num=0):
        """
        Internal function for retrieving the download url.

        """
        try:
            return file_upload_api.get_download_url(self._get_student_item_key(file_num))
        except FileUploadError:
            logger.exception("Error retrieving download URL.")
            return ''

    def _get_student_item_key(self, num=0):
        """
        Simple utility method to generate a common file upload key based on
        the student item.

        Returns:
            A string representation of the key.

        """
        student_item_dict = self.get_student_item_dict()
        num = int(num)
        if num > 0:
            student_item_dict['num'] = num
            return u"{student_id}/{course_id}/{item_id}/{num}".format(
                **student_item_dict
            )
        return u"{student_id}/{course_id}/{item_id}".format(
            **student_item_dict
        )

    def _get_url_by_file_key(self, key):
        """
        Return download url for some particular file key.

        """
        url = ''
        try:
            if key:
                url = file_upload_api.get_download_url(key)
        except FileUploadError:
            logger.exception(u"Unable to generate download url for file key {}".format(key))
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
            file_names = submission['answer'].get('files_name', [])
            for idx, key in enumerate(file_keys):
                file_download_url = self._get_url_by_file_key(key)
                if file_download_url:
                    file_description = descriptions[idx].strip() if idx < len(descriptions) else ''
                    file_name = file_names[idx].strip() if idx < len(file_names) else ''
                    urls.append((file_download_url, file_description, file_name))
                else:
                    break
        elif 'file_key' in submission['answer']:
            key = submission['answer'].get('file_key', '')
            file_download_url = self._get_url_by_file_key(key)
            if file_download_url:
                urls.append((file_download_url, '', ''))
        return urls

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
        workflow = self.get_workflow_info()
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
            file_metadata = self.get_saved_file_metadata()
            context['file_urls'] = [
                (file_url, file_description, file_name) for file_url, file_description, file_name, _ in file_metadata
            ]
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
            context["workflow_cancellation"] = self.get_workflow_cancellation_info(self.submission_uuid)
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
