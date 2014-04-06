import dateutil
import logging

from django.utils.translation import ugettext as _
from xblock.core import XBlock

from submissions import api
from openassessment.workflow import api as workflow_api
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
    }

    @XBlock.json_handler
    def submit(self, data, suffix=''):
        """Place the submission text into Openassessment system

        Allows submission of new responses.  Performs basic workflow validation
        on any new submission to ensure it is acceptable to receive a new
        response at this time.

        Args:
            data (dict): Data should contain one attribute: submission. This is
                the response from the student which should be stored in the
                Open Assessment system.
            suffix (str): Not used in this handler.

        Returns:
            (tuple): Returns the status (boolean) of this request, the
                associated status tag (str), and status text (unicode).

        """
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
                submission = self.create_submission(student_item_dict, student_sub)
            except api.SubmissionRequestError as err:
                status_tag = 'EBADFORM'
                status_text = unicode(err.field_errors)
            except (api.SubmissionError, workflow_api.AssessmentWorkflowError):
                logger.exception("An error occurred while submitting.")
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
                the text of the student's response.
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

        submission = api.create_submission(student_item_dict, student_sub_dict)
        workflow_api.create_workflow(submission["uuid"])
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
        workflow = self.get_workflow_info()
        problem_closed, __, __, due_date = self.is_closed('submission')

        context = {
            "saved_response": self.saved_response,
            "save_status": self.save_status,
            "submit_enabled": self.saved_response != '',
        }

        # Due dates can default to the distant future, in which case
        # there's effectively no due date.
        # If we don't add the date to the context, the template won't display it.
        if due_date < DISTANT_FUTURE:
            context["submission_due"] = due_date.strftime("%A, %B %d, %Y %X")

        if not workflow and problem_closed:
            path = 'openassessmentblock/response/oa_response_closed.html'
        elif not workflow:
            path = "openassessmentblock/response/oa_response.html"
        elif workflow["status"] == "done":
            student_submission = self.get_user_submission(
                workflow["submission_uuid"]
            )
            context["student_submission"] = student_submission
            path = 'openassessmentblock/response/oa_response_graded.html'
        else:
            context["student_submission"] = self.get_user_submission(
                workflow["submission_uuid"]
            )
            path = 'openassessmentblock/response/oa_response_submitted.html'

        return self.render_assessment(path, context_dict=context)
