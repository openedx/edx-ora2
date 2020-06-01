"""
The Peer Assessment Mixin for all Peer Functionality.

"""

from __future__ import absolute_import

import logging

from webob import Response
from xblock.core import XBlock
from openassessment.assessment.errors import (PeerAssessmentInternalError, PeerAssessmentRequestError,
                                              PeerAssessmentWorkflowError)
from openassessment.workflow.errors import AssessmentWorkflowError
from openassessment.xblock.defaults import DEFAULT_RUBRIC_FEEDBACK_TEXT

from .data_conversion import (clean_criterion_feedback, create_rubric_dict, create_submission_dict,
                              verify_assessment_parameters)
from .resolve_dates import DISTANT_FUTURE
from .user_data import get_user_preferences

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class PeerAssessmentMixin:
    """The Peer Assessment Mixin for all Peer Functionality.

    Abstracts all functionality and handlers associated with Peer Assessment.
    All Peer Assessment API calls should be contained without this Mixin as
    well.

    PeerAssessmentMixin is a Mixin for the OpenAssessmentBlock. Functions in
    the PeerAssessmentMixin call into the OpenAssessmentBlock functions and
    will not work outside of OpenAssessmentBlock

    """

    @XBlock.json_handler
    @verify_assessment_parameters
    def peer_assess(self, data, suffix=''):  # pylint: disable=unused-argument
        """Place a peer assessment into OpenAssessment system

        Assess a Peer Submission.  Performs basic workflow validation to ensure
        that an assessment can be performed as this time.

        Args:
            data (dict): A dictionary containing information required to create
                a new peer assessment.  This dict should have the following attributes:
                `submission_uuid` (string): The unique identifier for the submission being assessed.
                `options_selected` (dict): Dictionary mapping criterion names to option values.
                `overall_feedback` (unicode): Written feedback for the submission as a whole.
                `criterion_feedback` (unicode): Written feedback per the criteria for the submission.

        Returns:
            Dict with keys "success" (bool) indicating success/failure.
            and "msg" (unicode) containing additional information if an error occurs.

        """
        # Import is placed here to avoid model import at project startup.
        from openassessment.assessment.api import peer as peer_api
        if self.submission_uuid is None:
            return {
                'success': False, 'msg': self._('You must submit a response before you can perform a peer assessment.')
            }

        uuid_server, uuid_client = self._get_server_and_client_submission_uuids(data)
        if uuid_server != uuid_client:
            logger.warning(
                u'Irrelevant assessment submission: expected "{uuid_server}", got "{uuid_client}"'.format(
                    uuid_server=uuid_server,
                    uuid_client=uuid_client,
                )
            )
            return {
                'success': False,
                'msg': self._('This feedback has already been submitted or the submission has been cancelled.'),
            }

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
                    create_rubric_dict(self.prompts, self.rubric_criteria_with_labels),
                    assessment_ui_model['must_be_graded_by']
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

        return {'success': False, 'msg': self._('Could not load peer assessment.')}

    @XBlock.handler
    def render_peer_assessment(self, data, suffix=''):  # pylint: disable=unused-argument
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
        # Import is placed here to avoid model import at project startup.
        from openassessment.assessment.api import peer as peer_api
        path = 'openassessmentblock/peer/oa_peer_unavailable.html'
        finished = False
        problem_closed, reason, start_date, due_date = self.is_closed(step="peer-assessment")
        user_preferences = get_user_preferences(self.runtime.service(self, 'user'))

        context_dict = {
            "rubric_criteria": self.rubric_criteria_with_labels,
            "allow_latex": self.allow_latex,
            "prompts_type": self.prompts_type,
            "user_timezone": user_preferences['user_timezone'],
            "user_language": user_preferences['user_language'],
            "xblock_id": self.get_xblock_id(),
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
        workflow_status = workflow.get('status')
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
                    "Submit your assessment and review another response"
                )
            elif assessment["must_grade"] - count == 1:
                context_dict["submit_button_text"] = self._(
                    "Submit your assessment and move to next step"
                )
            else:
                context_dict["submit_button_text"] = self._(
                    u"Submit your assessment and move to response #{response_number}"
                ).format(response_number=(count + 2))

        if workflow_status == "cancelled":
            path = 'openassessmentblock/peer/oa_peer_cancelled.html'
            # Sets the XBlock boolean to signal to Message that it WAS able to grab a submission
            self.no_peers = True

        # Once a student has completed a problem, it stays complete,
        # so this condition needs to be first.
        elif (workflow.get('status') == 'done' or finished) and not continue_grading:
            path = "openassessmentblock/peer/oa_peer_complete.html"

        # Allow continued grading even if the problem due date has passed
        elif continue_grading and student_item:
            peer_sub = self.get_peer_submission(student_item, assessment)
            if peer_sub:
                path = 'openassessmentblock/peer/oa_peer_turbo_mode.html'
                context_dict["peer_submission"] = create_submission_dict(peer_sub, self.prompts)

                # Determine if file upload is supported for this XBlock.
                context_dict["file_upload_type"] = self.file_upload_type
                context_dict["peer_file_urls"] = self.get_download_urls_from_submission(peer_sub)
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
                context_dict["peer_submission"] = create_submission_dict(peer_sub, self.prompts)
                # Determine if file upload is supported for this XBlock.
                context_dict["file_upload_type"] = self.file_upload_type
                context_dict["peer_file_urls"] = self.get_download_urls_from_submission(peer_sub)
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
        # Import is placed here to avoid model import at project startup.
        from openassessment.assessment.api import peer as peer_api
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

    def _get_server_and_client_submission_uuids(self, data={}):  # pylint: disable=dangerous-default-value
        """
        Retrieve the server and client submission_uuids

        Args:
            data (dict): A dictionary containing new peer assessment data
                This dict should have the following attributes:
                - `submission_uuid` (string): Unique identifier for the submission being assessed
                `- options_selected` (dict): Map criterion names to option values
                `- feedback` (unicode): Written feedback for the submission

        Returns:
            tuple: (uuid_server, uuid_client)
        """
        student_item = self.get_student_item_dict()
        assessment = self.get_assessment_module('peer-assessment')
        submission = self.get_peer_submission(student_item, assessment) or {}
        uuid_server = submission.get('uuid', None)
        uuid_client = data.get('submission_uuid', None)
        return uuid_server, uuid_client
