"""
The Peer Assessment Mixin for all Peer Functionality.

"""

import logging

from webob import Response
from xblock.core import XBlock
from openassessment.assessment.errors import (PeerAssessmentInternalError, PeerAssessmentRequestError,
                                              PeerAssessmentWorkflowError)
from openassessment.workflow.errors import AssessmentWorkflowError
from openassessment.xblock.defaults import DEFAULT_RUBRIC_FEEDBACK_TEXT

from .data_conversion import (
    verify_assessment_parameters,
    clean_criterion_feedback,
    create_rubric_dict,
)
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
    PEER_TEMPLATE_PATHS = {
        "unavailable": "openassessmentblock/peer/oa_peer_unavailable.html",
        "cancelled": "openassessmentblock/peer/oa_peer_cancelled.html",
        "complete": "openassessmentblock/peer/oa_peer_complete.html",
        "turbo_mode": "openassessmentblock/peer/oa_peer_turbo_mode.html",
        "turbo_mode_waiting": "openassessmentblock/peer/oa_peer_turbo_mode_waiting.html",
        "closed": "openassessmentblock/peer/oa_peer_closed.html",
        "assessment": "openassessmentblock/peer/oa_peer_assessment.html",
        "waiting": "openassessmentblock/peer/oa_peer_waiting.html",
    }


    @XBlock.json_handler
    @verify_assessment_parameters
    def peer_assess(self, data, suffix=""):  # pylint: disable=unused-argument
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

        step_data = self.peer_data()
        if self.submission_uuid is None:
            return {
                "success": False, "msg": self._("You must submit a response before you can perform a peer assessment.")
            }

        uuid_server, uuid_client = self._get_server_and_client_submission_uuids(step_data, data)
        if uuid_server != uuid_client:
            logger.warning(
                "Irrelevant assessment submission: expected '%s', got '%s'",
                uuid_server,
                uuid_client,
            )
            return {
                "success": False,
                "msg": self._("This feedback has already been submitted or the submission has been cancelled."),
            }

        if step_data.assessment:
            try:
                # Create the assessment
                assessment = peer_api.create_assessment(
                    self.submission_uuid,
                    step_data.student_item["student_id"],
                    data["options_selected"],
                    clean_criterion_feedback(
                        self.config_data.rubric_criteria_with_labels,
                        data["criterion_feedback"]
                    ),
                    data["overall_feedback"],
                    create_rubric_dict(
                        self.config_data.prompts,
                        self.config_data.rubric_criteria_with_labels
                    ),
                    step_data.assessment["must_be_graded_by"]
                )

                # Emit analytics event...
                self.publish_assessment_event("openassessmentblock.peer_assess", assessment)

            except (PeerAssessmentRequestError, PeerAssessmentWorkflowError):
                logger.warning(
                    "Peer API error for submission UUID %s",
                    self.submission_uuid,
                    exc_info=True
                )
                return {"success": False, "msg": self._("Your peer assessment could not be submitted.")}
            except PeerAssessmentInternalError:
                logger.exception(
                    "Peer API internal error for submission UUID: %s",
                    self.submission_uuid
                )
                msg = self._("Your peer assessment could not be submitted.")
                return {"success": False, "msg": msg}

            # Update both the workflow that the submission we"re assessing
            # belongs to, as well as our own (e.g. have we evaluated enough?)
            try:
                if assessment:
                    self.update_workflow_status(submission_uuid=assessment["submission_uuid"])
                self.update_workflow_status()
            except AssessmentWorkflowError:
                logger.exception(
                    "Workflow error occurred when submitting peer assessment "
                    "for submission %s",
                    self.submission_uuid
                )
                msg = self._("Could not update workflow status.")
                return {"success": False, "msg": msg}

            # Temp kludge until we fix JSON serialization for datetime
            assessment["scored_at"] = str(assessment["scored_at"])

            return {"success": True, "msg": ""}

        return {"success": False, "msg": self._("Could not load peer assessment.")}

    @XBlock.handler
    def render_peer_assessment(self, data, suffix=""):  # pylint: disable=unused-argument
        """Renders the Peer Assessment HTML section of the XBlock

        Generates the peer assessment HTML for the first section of an Open
        Assessment XBlock. See OpenAssessmentBlock.render_assessment() for
        more information on rendering XBlock sections.

        Args:
            data (dict): May contain an attribute "continue_grading", which
                allows a student to continue grading peers past the required
                number of assessments.

        """
        if "peer-assessment" not in self.assessment_steps:
            return Response("")
        continue_grading = data.params.get("continue_grading", False)
        path, context_dict = self.peer_path_and_context(continue_grading)

        # For backwards compatibility, if no feedback default text has been
        # set, use the default text
        if "rubric_feedback_default_text" not in context_dict:
            context_dict["rubric_feedback_default_text"] = DEFAULT_RUBRIC_FEEDBACK_TEXT

        return self.render_assessment(path, context_dict)

    def peer_context(self, step_data, peer_sub=None):
        user_preferences = get_user_preferences(self.runtime.service(self, "user"))
        context_dict = {
            "rubric_criteria": self.rubric_criteria_with_labels,
            "allow_multiple_files": self.allow_multiple_files,
            "allow_latex": self.allow_latex,
            "prompts_type": self.prompts_type,
            "user_timezone": user_preferences["user_timezone"],
            "user_language": user_preferences["user_language"],
            "xblock_id": self.get_xblock_id(),
        }

        if self.rubric_feedback_prompt is not None:
            context_dict["rubric_feedback_prompt"] = self.rubric_feedback_prompt

        if self.rubric_feedback_default_text is not None:
            context_dict["rubric_feedback_default_text"] = self.rubric_feedback_default_text

        # We display the due date whether the problem is open or closed.
        # If no date is set, it defaults to the distant future, in which
        # case we don"t display the date.
        if step_data.is_due:
            context_dict["peer_due"] = step_data.due_date

        assessment = step_data.assessment

        if assessment:
            context_dict["must_grade"] = assessment["must_grade"]

            count = step_data.has_finished[1]
            context_dict["graded"] = count
            context_dict["review_num"] = count + 1

            if step_data.continue_grading:
                context_dict["submit_button_text"] = self._(
                    "Submit your assessment and review another response"
                )
            elif assessment["must_grade"] - count == 1:
                context_dict["submit_button_text"] = self._(
                    "Submit your assessment and move to next step"
                )
            else:
                context_dict["submit_button_text"] = self._(
                    "Submit your assessment and move to response #{response_number}"
                ).format(response_number=(count + 2))

        if step_data.is_not_available_yet:
            context_dict["peer_start"] = step_data.start_date

        if (peer_sub):
            context_dict.update({
                "peer_submission": step_data.get_submission_dict(peer_sub),
                # Determine if file upload is supported for this XBlock.
                "file_upload_type": step_data.file_upload_type,
                "peer_file_urls": step_data.get_download_urls(peer_sub),
            })

        return context_dict

    def _peer_path_and_context(self, key, step_data, peer_sub=None):
        return self.PEER_TEMPLATE_PATHS[key], self.peer_context(step_data, peer_sub)

    def peer_path_and_context(self, continue_grading):
        """
        Return the template path and context for rendering the peer assessment step.

        Args:
            continue_grading (bool): If true, the user has chosen to continue grading.

        Returns:
            tuple of (template_path, context_dict)

        """
        # Import is placed here to avoid model import at project startup.
        step_data = self.peer_data(continue_grading)

        if step_data.is_cancelled:
            # Sets the XBlock boolean to signal to Message that it WAS able to grab a submission
            self.no_peers = True
            return self._peer_path_and_context("cancelled", step_data)

        # Once a student has completed a problem, it stays complete,
        # so this condition needs to be first.
        if (step_data.is_complete) and not step_data.continue_grading:
            return self._peer_path_and_context("complete", step_data)

        # Allow continued grading even if the problem due date has passed
        if step_data.continue_grading and step_data.student_item:
            peer_sub = self.get_peer_submission(step_data)
            if peer_sub:
                return self._peer_path_and_context("turbo_mode", step_data, peer_sub)
            else:
                return self._peer_path_and_context("turbo_mode_waiting", step_data)

        if step_data.is_past_due:
            return self._peer_path_and_context("closed", step_data)

        if step_data.is_not_available_yet:
            return self._peer_path_and_context("unavailable", step_data)

        if step_data.is_peer or step_data.is_skipped:
            peer_sub = self.get_peer_submission(step_data)
            if peer_sub:
                # Sets the XBlock boolean to signal to Message that it WAS able to grab a submission
                self.no_peers = False
                return self._peer_path_and_context("assessment", step_data, peer_sub)
            else:
                # Sets the XBlock boolean to signal to Message that it WAS NOT able to grab a submission
                self.no_peers = True
                return self._peer_path_and_context("waiting", step_data)

        return self._peer_path_and_context("unavailable", step_data)

    def get_peer_submission(self, step_data):
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
            peer_submission = step_data.get_peer_submission()
            self.runtime.publish(
                self,
                "openassessmentblock.get_peer_submission",
                step_data.format_submission_for_publish(peer_submission),
            )
        except PeerAssessmentWorkflowError as err:
            logger.exception(err)

        return peer_submission

    def _get_server_and_client_submission_uuids(self, step_data, data={}):  # pylint: disable=dangerous-default-value
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
        submission = self.get_peer_submission(step_data) or {}
        uuid_server = submission.get("uuid", None)
        uuid_client = data.get("submission_uuid", None)
        return uuid_server, uuid_client
