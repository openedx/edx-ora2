import logging

from django.utils.translation import ugettext as _
from xblock.core import XBlock

from submissions import api
from openassessment.fileupload import api as file_upload_api
from openassessment.fileupload.api import FileUploadError
from openassessment.workflow.errors import AssessmentWorkflowError
from .resolve_dates import DISTANT_FUTURE


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

    submit_errors = {
        # Reported to user sometimes, and useful in tests
        'ENODATA':  _(u'API returned an empty response.'),
        'EBADFORM': _(u'API Submission Request Error.'),
        'EUNKNOWN': _(u'API returned unclassified exception.'),
        'ENOMULTI': _(u'Multiple submissions are not allowed.'),
        'ENOPREVIEW': _(u'To submit a response, view this component in Preview or Live mode.'),
        'EBADARGS': _(u'"submission" required to submit answer.')
    }

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
            return False, 'EBADARGS', self.submit_errors['EBADARGS']

        status = False
        status_text = None
        student_sub = data['submission']
        student_item_dict = self.get_student_item_dict()

        # Short-circuit if no user is defined (as in Studio Preview mode)
        # Since students can't submit, they will never be able to progress in the workflow
        if self.in_studio_preview:
            return False, 'ENOPREVIEW', self.submit_errors['ENOPREVIEW']

        workflow = self.get_workflow_info()

        status_tag = 'ENOMULTI'  # It is an error to submit multiple times for the same item
        if not workflow:
            status_tag = 'ENODATA'
            try:
                submission = self.create_submission(
                    student_item_dict,
                    student_sub
                )
            except api.SubmissionRequestError as err:
                status_tag = 'EBADFORM'
                status_text = unicode(err.field_errors)
            except (api.SubmissionError, AssessmentWorkflowError):
                logger.exception("This response was not submitted.")
                status_tag = 'EUNKNOWN'
            else:
                status = True
                status_tag = submission.get('student_item')
                status_text = submission.get('attempt_number')

        # relies on success being orthogonal to errors
        status_text = status_text if status_text else self.submit_errors[status_tag]
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
            try:
                self.saved_response = unicode(data['submission'])
                self.has_saved = True

                # Emit analytics event...
                self.runtime.publish(
                    self,
                    "openassessmentblock.save_submission",
                    {"saved_response": self.saved_response}
                )
            except:
                return {'success': False, 'msg': _(u"This response could not be saved.")}
            else:
                return {'success': True, 'msg': u''}
        else:
            return {'success': False, 'msg': _(u"This response was not submitted.")}

    def create_submission(self, student_item_dict, student_sub):

        # Store the student's response text in a JSON-encodable dict
        # so that later we can add additional response fields.
        student_sub_dict = {'text': student_sub}

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
            return {'success': False, 'msg': _(u"Must specify contentType.")}
        content_type = data['contentType']

        if not content_type.startswith('image/'):
            return {'success': False, 'msg': _(u"contentType must be an image.")}

        try:
            key = self._get_student_item_key()
            url = file_upload_api.get_upload_url(key, content_type)
            return {'success': True, 'url': url}
        except FileUploadError:
            logger.exception("Error retrieving upload URL.")
            return {'success': False, 'msg': _(u"Error retrieving upload URL.")}

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
        return _(u'This response has been saved but not submitted.') if self.has_saved else _(u'This response has not been saved.')

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

        if not workflow and problem_closed:
            if reason == 'due':
                path = 'openassessmentblock/response/oa_response_closed.html'
            elif reason == 'start':
                context['submission_start'] = start_date
                path = 'openassessmentblock/response/oa_response_unavailable.html'
        elif not workflow:
            context['saved_response'] = self.saved_response
            context['allow_file_upload'] = self.allow_file_upload
            context['file_url'] = self._get_download_url()
            context['save_status'] = self.save_status
            context['submit_enabled'] = self.saved_response != ''
            path = "openassessmentblock/response/oa_response.html"
        elif workflow["status"] == "done":
            student_submission = self.get_user_submission(
                workflow["submission_uuid"]
            )
            context["student_submission"] = student_submission
            context['allow_file_upload'] = self.allow_file_upload
            context['file_url'] = self._get_download_url()
            path = 'openassessmentblock/response/oa_response_graded.html'
        else:
            context["student_submission"] = self.get_user_submission(
                workflow["submission_uuid"]
            )
            context['allow_file_upload'] = self.allow_file_upload
            context['file_url'] = self._get_download_url()
            path = 'openassessmentblock/response/oa_response_submitted.html'

        return path, context
