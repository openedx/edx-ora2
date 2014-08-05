import logging

from webob import Response
from xblock.core import XBlock

from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.errors import (
    PeerAssessmentRequestError, PeerAssessmentInternalError, PeerAssessmentWorkflowError
)
from openassessment.workflow.errors import AssessmentWorkflowError
from openassessment.xblock.defaults import DEFAULT_RUBRIC_FEEDBACK_TEXT
from .data_conversion import create_rubric_dict
from .resolve_dates import DISTANT_FUTURE
from .data_conversion import clean_criterion_feedback

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
        if 'options_selected' not in data:
            return {'success': False, 'msg': self._('Must provide options selected in the assessment')}

        if 'overall_feedback' not in data:
            return {'success': False, 'msg': self._('Must provide overall feedback in the assessment')}

        if 'criterion_feedback' not in data:
            return {'success': False, 'msg': self._('Must provide feedback for criteria in the assessment')}

        if self.submission_uuid is None:
            return {'success': False, 'msg': self._('You must submit a response before you can peer-assess.')}

        assessment_ui_model = self.get_assessment_module('peer-assessment')
        if assessment_ui_model:
            try:
                # Create the assessment
                assessment = peer_api.create_assessment(
                    self.submission_uuid,
                    self.get_student_item_dict()["student_id"],
                    data['options_selected'],
                    clean_criterion_feedback(self.rubric_criteria_with_labels, data['criterion_feedback']),
                    data['overall_feedback'],
                    create_rubric_dict(self.prompt, self.rubric_criteria_with_labels),
                    assessment_ui_model['must_be_graded_by'],
                    track_changes_edits=data.get('track_changes_edits', ''),
                )

                # Emit analytics event...
                self.publish_assessment_event("openassessmentblock.peer_assess", assessment)

            except (PeerAssessmentRequestError, PeerAssessmentWorkflowError):
                logger.warning(
                    u"Peer API error for submission UUID {}".format(self.submission_uuid),
                    exc_info=True
                )
                return {'success': False, 'msg': self._(u"Your peer assessment could not be submitted.")}
            except PeerAssessmentInternalError:
                logger.exception(
                    u"Peer API internal error for submission UUID: {}".format(self.submission_uuid)
                )
                msg = self._("Your peer assessment could not be submitted.")
                return {'success': False, 'msg': msg}

            # Update both the workflow that the submission we're assessing
            # belongs to, as well as our own (e.g. have we evaluated enough?)
            try:
                if assessment:
                    self.update_workflow_status(submission_uuid=assessment['submission_uuid'])
                self.update_workflow_status()
            except AssessmentWorkflowError:
                logger.exception(
                    u"Workflow error occurred when submitting peer assessment "
                    u"for submission {}".format(self.submission_uuid)
                )
                msg = self._('Could not update workflow status.')
                return {'success': False, 'msg': msg}

            # Temp kludge until we fix JSON serialization for datetime
            assessment["scored_at"] = str(assessment["scored_at"])

            return {'success': True, 'msg': u''}

        else:
            return {'success': False, 'msg': self._('Could not load peer assessment.')}

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
        if "peer-assessment" not in self.assessment_steps:
            return Response(u"")
        continue_grading = data.params.get('continue_grading', False)
        path, context_dict = self.peer_path_and_context(continue_grading)

        # For backwards compatibility, if no feedback default text has been
        # set, use the default text
        if 'rubric_feedback_default_text' not in context_dict:
            context_dict['rubric_feedback_default_text'] = DEFAULT_RUBRIC_FEEDBACK_TEXT

        return self.render_assessment(path, context_dict)

    def peer_path_and_context(self, continue_grading):
        """
        Return the template path and context for rendering the peer assessment step.

        Args:
            continue_grading (bool): If true, the user has chosen to continue grading.

        Returns:
            tuple of (template_path, context_dict)

        """
        path = 'openassessmentblock/peer/oa_peer_unavailable.html'
        finished = False
        problem_closed, reason, start_date, due_date = self.is_closed(step="peer-assessment")

        context_dict = {
            "rubric_criteria": self.rubric_criteria_with_labels,
            "estimated_time": "20 minutes",  # TODO: Need to configure this.
            "allow_latex": self.allow_latex,
        }

        if self.rubric_feedback_prompt is not None:
            context_dict["rubric_feedback_prompt"] = self.rubric_feedback_prompt

        if self.rubric_feedback_default_text is not None:
            context_dict['rubric_feedback_default_text'] = self.rubric_feedback_default_text

        # We display the due date whether the problem is open or closed.
        # If no date is set, it defaults to the distant future, in which
        # case we don't display the date.
        if due_date < DISTANT_FUTURE:
            context_dict['peer_due'] = due_date

        workflow = self.get_workflow_info()
        peer_complete = workflow.get('status_details', {}).get('peer', {}).get('complete', False)
        continue_grading = continue_grading and peer_complete

        student_item = self.get_student_item_dict()
        assessment = self.get_assessment_module('peer-assessment')
        if assessment:
            context_dict["must_grade"] = assessment["must_grade"]
            finished, count = peer_api.has_finished_required_evaluating(
                self.submission_uuid,
                assessment["must_grade"]
            )
            context_dict["graded"] = count
            context_dict["review_num"] = count + 1

            if continue_grading:
                context_dict["submit_button_text"] = self._(
                    "Submit your assessment & review another response"
                )
            elif assessment["must_grade"] - count == 1:
                context_dict["submit_button_text"] = self._(
                    "Submit your assessment & move onto next step"
                )
            else:
                context_dict["submit_button_text"] = self._(
                    "Submit your assessment & move to response #{response_number}"
                ).format(response_number=(count + 2))

            context_dict['track_changes'] = assessment.get('track_changes', '')

        # Once a student has completed a problem, it stays complete,
        # so this condition needs to be first.
        if (workflow.get('status') == 'done' or finished) and not continue_grading:
            path = "openassessmentblock/peer/oa_peer_complete.html"

        # Allow continued grading even if the problem due date has passed
        elif continue_grading and student_item:
            peer_sub = self.get_peer_submission(student_item, assessment)
            if peer_sub:
                path = 'openassessmentblock/peer/oa_peer_turbo_mode.html'
                context_dict["peer_submission"] = peer_sub

                # Determine if file upload is supported for this XBlock.
                context_dict["allow_file_upload"] = self.allow_file_upload
                context_dict["peer_file_url"] = self.get_download_url_from_submission(peer_sub)
            else:
                path = 'openassessmentblock/peer/oa_peer_turbo_mode_waiting.html'
        elif reason == 'due' and problem_closed:
            path = 'openassessmentblock/peer/oa_peer_closed.html'
        elif reason == 'start' and problem_closed:
            context_dict["peer_start"] = start_date
            path = 'openassessmentblock/peer/oa_peer_unavailable.html'
        elif workflow.get("status") == "peer":
            peer_sub = self.get_peer_submission(student_item, assessment)
            if peer_sub:
                path = 'openassessmentblock/peer/oa_peer_assessment.html'
                context_dict["peer_submission"] = peer_sub
                # Determine if file upload is supported for this XBlock.
                context_dict["allow_file_upload"] = self.allow_file_upload
                context_dict["peer_file_url"] = self.get_download_url_from_submission(peer_sub)
                # Sets the XBlock boolean to signal to Message that it WAS NOT able to grab a submission
                self.no_peers = False
            else:
                path = 'openassessmentblock/peer/oa_peer_waiting.html'
                # Sets the XBlock boolean to signal to Message that it WAS able to grab a submission
                self.no_peers = True

        return path, context_dict

    def get_peer_submission(self, student_item_dict, assessment):
        """
        Retrieve a submission to peer-assess.

        Args:
            student_item_dict (dict): The student item for the student creating the submission.
            assessment (dict): A dict describing the requirements for grading.

        Returns:
            dict: The serialized submission model.

        """
        peer_submission = False
        try:
            peer_submission = peer_api.get_submission_to_assess(
                self.submission_uuid,
                assessment["must_be_graded_by"]
            )
            self.runtime.publish(
                self,
                "openassessmentblock.get_peer_submission",
                {
                    "requesting_student_id": student_item_dict["student_id"],
                    "course_id": student_item_dict["course_id"],
                    "item_id": student_item_dict["item_id"],
                    "submission_returned_uuid": (
                        peer_submission["uuid"] if peer_submission else None
                    )
                }
            )
        except PeerAssessmentWorkflowError as err:
            logger.exception(err)

        return peer_submission
