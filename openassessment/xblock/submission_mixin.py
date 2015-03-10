import json
import logging

from xblock.core import XBlock

from submissions import api
from openassessment.fileupload import api as file_upload_api
from openassessment.fileupload.exceptions import FileUploadError
from openassessment.workflow import api as workflow_api
from openassessment.workflow.errors import AssessmentWorkflowError
from .resolve_dates import DISTANT_FUTURE

from data_conversion import create_submission_dict, prepare_submission_for_serialization
from validation import validate_submission

logger = logging.getLogger(__name__)


class SubmissionMixin(object):
    """Submission Mixin introducing all Submission-related functionality.

    Submission Mixin contains all logic and handlers associated with rendering
    the submission section of the front end, as well as making all API calls to
    the middle tier for constructing new submissions, or fetching submissions.

    SubmissionMixin is a Mixin for the OpenAssessmentBlock. Functions in the
    SubmissionMixin call into the OpenAssessmentBlock functions and will not
    work outside the scope of OpenAssessmentBlock.

    """

    @XBlock.json_handler
    def submit(self, data, suffix=''):
        """Place the submission text into Openassessment system

        Allows submission of new responses.  Performs basic workflow validation
        on any new submission to ensure it is acceptable to receive a new
        response at this time.

        Args:
            data (dict): Data may contain two attributes: submission and
                file_url. submission is the response from the student which
                should be stored in the Open Assessment system. file_url is the
                path to a related file for the submission. file_url is optional.
            suffix (str): Not used in this handler.

        Returns:
            (tuple): Returns the status (boolean) of this request, the
                associated status tag (str), and status text (unicode).

        """
        if 'submission' not in data:
            return (
                False,
                'EBADARGS',
                self._(u'"submission" required to submit answer.')
            )

        status = False
        student_sub_data = data['submission']
        success, msg = validate_submission(student_sub_data, self.prompts, self._)
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
                submission = self.create_submission(
                    student_item_dict,
                    student_sub_data
                )
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
    def save_submission(self, data, suffix=''):
        """
        Save the current student's response submission.
        If the student already has a response saved, this will overwrite it.

        Args:
            data (dict): Data should have a single key 'submission' that contains
                the text of the student's response. Optionally, the data could
                have a 'file_url' key that is the path to an associated file for
                this submission.
            suffix (str): Not used.

        Returns:
            dict: Contains a bool 'success' and unicode string 'msg'.
        """
        if 'submission' in data:
            student_sub_data = data['submission']
            success, msg = validate_submission(student_sub_data, self.prompts, self._)
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
            except:
                return {'success': False, 'msg': self._(u"This response could not be saved.")}
            else:
                return {'success': True, 'msg': u''}
        else:
            return {'success': False, 'msg': self._(u"This response was not submitted.")}

    def create_submission(self, student_item_dict, student_sub_data):

        # Store the student's response text in a JSON-encodable dict
        # so that later we can add additional response fields.
        student_sub_dict = prepare_submission_for_serialization(student_sub_data)

        if self.allow_file_upload:
            student_sub_dict['file_key'] = self._get_student_item_key()
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
    def upload_url(self, data, suffix=''):
        """
        Request a URL to be used for uploading content related to this
        submission.

        Returns:
            A URL to be used to upload content associated with this submission.

        """
        if "contentType" not in data:
            return {'success': False, 'msg': self._(u"Must specify contentType.")}
        content_type = data['contentType']

        if not content_type.startswith('image/'):
            return {'success': False, 'msg': self._(u"contentType must be an image.")}

        try:
            key = self._get_student_item_key()
            url = file_upload_api.get_upload_url(key, content_type)
            return {'success': True, 'url': url}
        except FileUploadError:
            logger.exception("Error retrieving upload URL.")
            return {'success': False, 'msg': self._(u"Error retrieving upload URL.")}

    @XBlock.json_handler
    def download_url(self, data, suffix=''):
        """
        Request a download URL.

        Returns:
            A URL to be used for downloading content related to the submission.

        """
        return {'success': True, 'url': self._get_download_url()}

    def _get_download_url(self):
        """
        Internal function for retrieving the download url.

        """
        try:
            return file_upload_api.get_download_url(self._get_student_item_key())
        except FileUploadError:
            logger.exception("Error retrieving download URL.")
            return ''

    def _get_student_item_key(self):
        """
        Simple utility method to generate a common file upload key based on
        the student item.

        Returns:
            A string representation of the key.

        """
        return u"{student_id}/{course_id}/{item_id}".format(
            **self.get_student_item_dict()
        )

    def get_download_url_from_submission(self, submission):
        """
        Returns a download URL for retrieving content within a submission.

        Args:
            submission (dict): Dictionary containing an answer and a file_key.
                The file_key is used to try and retrieve a download url
                with related content

        Returns:
            A URL to related content. If there is no content related to this
            key, or if there is no key for the submission, returns an empty
            string.

        """
        url = ""
        key = submission['answer'].get('file_key', '')
        try:
            if key:
                url = file_upload_api.get_download_url(key)
        except FileUploadError:
            logger.exception("Unable to generate download url for file key {}".format(key))
        return url

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
        return self._(u'This response has been saved but not submitted.') if self.has_saved else self._(u'This response has not been saved.')

    @XBlock.handler
    def render_submission(self, data, suffix=''):
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

        path = 'openassessmentblock/response/oa_response.html'
        context = {}

        # Due dates can default to the distant future, in which case
        # there's effectively no due date.
        # If we don't add the date to the context, the template won't display it.
        if due_date < DISTANT_FUTURE:
            context["submission_due"] = due_date

        context['allow_file_upload'] = self.allow_file_upload
        context['allow_latex'] = self.allow_latex
        context['has_peer'] = 'peer-assessment' in self.assessment_steps
        context['has_self'] = 'self-assessment' in self.assessment_steps

        if self.allow_file_upload:
            context['file_url'] = self._get_download_url()

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
            context['submit_enabled'] = self.saved_response != ''
            path = "openassessmentblock/response/oa_response.html"

        elif workflow["status"] == "cancelled":
            workflow_cancellation = workflow_api.get_assessment_workflow_cancellation(self.submission_uuid)
            if workflow_cancellation:
                workflow_cancellation['cancelled_by'] = self.get_username(workflow_cancellation['cancelled_by_id'])

            context['workflow_cancellation'] = workflow_cancellation
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
            context["student_submission"] = create_submission_dict(student_submission, self.prompts)
            path = 'openassessmentblock/response/oa_response_submitted.html'

        return path, context
