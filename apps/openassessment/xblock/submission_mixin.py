from xblock.core import XBlock
from django.utils.translation import ugettext as _
from submissions import api
from openassessment.assessment import peer_api
from openassessment.workflow import api as workflow_api


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
        'ENODATA':  'API returned an empty response',
        'EBADFORM': 'API Submission Request Error',
        'EUNKNOWN': 'API returned unclassified exception',
        'ENOMULTI': 'Multiple submissions are not allowed for this item',
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
        prev_sub = self.get_user_submission(student_item_dict)

        status_tag = 'ENOMULTI'  # It is an error to submit multiple times for the same item
        if not prev_sub:
            status_tag = 'ENODATA'
            try:
                submission = self.create_submission(student_item_dict, student_sub)
            except api.SubmissionRequestError as err:
                status_tag = 'EBADFORM'
                status_text = unicode(err.field_errors)
            except (api.SubmissionError, workflow_api.AssessmentWorkflowError):
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
        submission = api.create_submission(student_item_dict, student_sub)
        workflow = workflow_api.create_workflow(submission["uuid"])
        self.submission_uuid = submission["uuid"]
        return submission

    @staticmethod
    def _get_submission_score(student_item_dict):
        """Return the most recent score, if any, for student item

        Gets the score, if available.

        Args:
            student_item_dict (dict): The student item we want to check for a
                score.

        Returns:
            (dict): Dictionary representing the score for this particular
                question.

        """
        scores = api.get_score(student_item_dict)
        return scores[0] if scores else None

    @staticmethod
    def get_user_submission(student_item_dict):
        """Return the most recent submission by user in student_item_dict

        Given a student item, return the most recent submission.  If no
        submission is available, return None. All submissions are preserved, but
        only the most recent will be returned in this function, since the active
        workflow will only be concerned with the most recent submission.

        Args:
            student_item_dict (dict): The student item we want to get the
                latest submission for.

        Returns:
            (dict): A dictionary representation of a submission to render to
                the front end.

        """
        submissions = []
        try:
            submissions = api.get_submissions(student_item_dict)
        except api.SubmissionRequestError:
            # This error is actually ok.
            pass
        return submissions[0] if submissions else None

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
        # TODO Check if Saved
        student_item = self.get_student_item_dict()
        # Has the student submitted?
        student_submission = self.get_user_submission(student_item)
        # Has it been graded yet?
        student_score = self._get_submission_score(student_item)
        step_status = "Graded" if student_score else "Submitted"
        step_status = step_status if student_submission else "Incomplete"
        assessment_ui_model = self.get_assessment_module('peer-assessment')
        problem_open, date = self.is_open()
        context = {
            "student_submission": student_submission,
            "student_score": student_score,
            "step_status": step_status,
            "saved_response": self.saved_response,
            "save_status": self.save_status
        }

        path = "openassessmentblock/response/oa_response.html"
        if student_score:
            assessments = peer_api.get_assessments(student_submission["uuid"])
            median_scores = peer_api.get_assessment_median_scores(
                student_submission["uuid"],
                assessment_ui_model["must_be_graded_by"]
            )
            context["peer_assessments"] = assessments
            context["rubric_criteria"] = self.rubric_criteria
            for criterion in context["rubric_criteria"]:
                criterion["median_score"] = median_scores[criterion["name"]]

            path = 'openassessmentblock/response/oa_response_graded.html'
        elif student_submission:
            path = 'openassessmentblock/response/oa_response_submitted.html'
        elif not problem_open and date == "due" and not student_submission:
            path = 'openassessmentblock/response/oa_response_closed.html'

        return self.render_assessment(path, context_dict=context)
