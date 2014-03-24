import logging
from django.utils.translation import ugettext as _
from xblock.core import XBlock
from openassessment.assessment import peer_api
from openassessment.assessment.peer_api import (
    PeerAssessmentInternalError, PeerAssessmentRequestError,
    PeerAssessmentWorkflowError
)
import openassessment.workflow.api as workflow_api

logger = logging.getLogger(__name__)


class PeerAssessmentMixin(object):
    """The Peer Assessment Mixin for all Peer Functionality.

    Abstracts all functionality and handlers associated with Peer Assessment.
    All Peer Assessment API calls should be contained without this Mixin as
    well.

    PeerAssessmentMixin is a Mixin for the OpenAssessmentBlock. Functions in
    the PeerAssessmentMixin call into the OpenAssessmentBlock functions and
    will not work outside of OpenAssessmentBlock

    """

    @XBlock.json_handler
    def peer_assess(self, data, suffix=''):
        """Place a peer assessment into OpenAssessment system

        Assess a Peer Submission.  Performs basic workflow validation to ensure
        that an assessment can be performed as this time.

        Args:
            data (dict): A dictionary containing information required to create
                a new peer assessment.  This dict should have the following attributes:
                `submission_uuid` (string): The unique identifier for the submission being assessed.
                `options_selected` (dict): Dictionary mapping criterion names to option values.
                `feedback` (unicode): Written feedback for the submission.

        Returns:
            Dict with keys "success" (bool) indicating success/failure.
            and "msg" (unicode) containing additional information if an error occurs.

        """
        # Validate the request
        if 'feedback' not in data:
            return {'success': False, 'msg': _('Must provide feedback in the assessment')}

        if 'options_selected' not in data:
            return {'success': False, 'msg': _('Must provide options selected in the assessment')}

        if 'submission_uuid' not in data:
            return {'success': False, 'msg': _('Must provide submission uuid for the assessment')}

        assessment_ui_model = self.get_assessment_module('peer-assessment')
        if assessment_ui_model:
            rubric_dict = {
                'criteria': self.rubric_criteria
            }
            assessment_dict = {
                "feedback": data['feedback'],
                "options_selected": data["options_selected"],
            }

            try:
                assessment = peer_api.create_assessment(
                    data["submission_uuid"],
                    self.get_student_item_dict()["student_id"],
                    assessment_dict,
                    rubric_dict,
                )
            except PeerAssessmentRequestError as ex:
                return {'success': False, 'msg': ex.message}
            except PeerAssessmentInternalError as ex:
                msg = _("Internal error occurred while creating the assessment")
                logger.exception(msg)
                return {'success': False, 'msg': msg}

            # Update both the workflow that the submission we're assessing
            # belongs to, as well as our own (e.g. have we evaluated enough?)
            try:
                self.update_workflow_status(submission_uuid=data["submission_uuid"])
                self.update_workflow_status()
            except workflow_api.AssessmentWorkflowError:
                msg = _('Could not update workflow status.')
                logger.exception(msg)
                return {'success': False, 'msg': msg}

            # Temp kludge until we fix JSON serialization for datetime
            assessment["scored_at"] = str(assessment["scored_at"])

            return {'success': True, 'msg': u''}

        else:
            return {'success': False, 'msg': _('Could not load peer assessment.')}

    @XBlock.handler
    def render_peer_assessment(self, data, suffix=''):
        """Renders the Peer Assessment HTML section of the XBlock

        Generates the peer assessment HTML for the first section of an Open
        Assessment XBlock. See OpenAssessmentBlock.render_assessment() for
        more information on rendering XBlock sections.

        Args:
            data (dict): May contain an attribute 'continue_grading', which
                allows a student to continue grading peers past the required
                number of assessments.

        """
        path = 'openassessmentblock/peer/oa_peer_unavailable.html'
        finished = False

        problem_open, date = self.is_open(step="peer")
        context_dict = {
            "rubric_criteria": self.rubric_criteria,
            "estimated_time": "20 minutes"  # TODO: Need to configure this.
        }

        submissions_open, __ = self.is_open(step="submission")
        over_grading = not submissions_open

        workflow = self.get_workflow_info()
        if workflow is None:
            return self.render_assessment(path, context_dict)
        continue_grading = (
            data.params.get('continue_grading', False)
            and workflow["status_details"]["peer"]["complete"]
            and over_grading
        )

        student_item = self.get_student_item_dict()
        assessment = self.get_assessment_module('peer-assessment')
        if assessment:
            context_dict["must_grade"] = assessment["must_grade"]
            finished, count = peer_api.has_finished_required_evaluating(
                student_item,
                assessment["must_grade"]
            )
            context_dict["graded"] = count
            context_dict["review_num"] = count + 1

            if continue_grading:
                context_dict["submit_button_text"] = (
                    "Submit your assessment & review another response"
                )
            elif assessment["must_grade"] - count == 1:
                context_dict["submit_button_text"] = (
                    "Submit your assessment & move onto next step"
                )
            else:
                context_dict["submit_button_text"] = (
                    "Submit your assessment & move to response #{}"
                ).format(count + 2)
            if assessment.get('due'):
                context_dict["peer_due"] = self.format_datetime_string(assessment["due"])


        if date == "due" and not problem_open:
            path = 'openassessmentblock/peer/oa_peer_closed.html'
        elif workflow.get("status") == "peer":
            peer_sub = self.get_peer_submission(student_item, assessment, over_grading)
            if peer_sub:
                path = 'openassessmentblock/peer/oa_peer_assessment.html'
                context_dict["peer_submission"] = peer_sub
            else:
                path = 'openassessmentblock/peer/oa_peer_waiting.html'
        elif continue_grading and student_item:
            peer_sub = self.get_peer_submission(student_item, assessment, continue_grading)
            if peer_sub:
                path = 'openassessmentblock/peer/oa_peer_turbo_mode.html'
                context_dict["peer_submission"] = peer_sub
            else:
                path = 'openassessmentblock/peer/oa_peer_turbo_mode_waiting.html'
        elif workflow.get("status") == "done" or finished:
            path = "openassessmentblock/peer/oa_peer_complete.html"

        return self.render_assessment(path, context_dict)

    def get_peer_submission(
            self,
            student_item_dict,
            assessment,
            over_grading=False
    ):
        peer_submission = False
        try:
            peer_submission = peer_api.get_submission_to_assess(
                student_item_dict,
                assessment["must_be_graded_by"],
                over_grading
            )
        except PeerAssessmentWorkflowError as err:
            logger.exception(err)
        return peer_submission
