import copy
import dateutil
import logging

from django.utils.translation import ugettext as _
from xblock.core import XBlock

from submissions import api
from openassessment.assessment import peer_api
from openassessment.workflow import api as workflow_api


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
        # Studio Preview provides an anonymous student ID, so we need to check the scope ids directly
        # to check that we are in preview mode.
        if self.scope_ids.user_id is None:
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
                logger.exception("Error occurred while submitting.")
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
            except:
                return {'success': False, 'msg': _(u"Could not save response submission")}
            else:
                return {'success': True, 'msg': u''}
        else:
            return {'success': False, 'msg': _(u"Missing required key 'submission'")}

    def create_submission(self, student_item_dict, student_sub):

        # Store the student's response text in a JSON-encodable dict
        # so that later we can add additional response fields.
        student_sub_dict = {'text': student_sub}

        submission = api.create_submission(student_item_dict, student_sub_dict)
        workflow_api.create_workflow(submission["uuid"])
        self.submission_uuid = submission["uuid"]
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
        return _(u'Saved but not submitted') if self.has_saved else _(u'Not saved')

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
        problem_open, date = self.is_open()
        sub_due = None
        if self.submission_due is not None:
            submission_deadline = dateutil.parser.parse(self.submission_due)
            sub_due = submission_deadline.strftime("%A, %B %d, %Y %X")
        context = {
            "saved_response": self.saved_response,
            "save_status": self.save_status,
            "submission_due": sub_due,
        }

        if not workflow and not problem_open:
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
