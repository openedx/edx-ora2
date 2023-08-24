"""
Collection of JSON handlers for legacy view

"""
import logging

from xblock.core import XBlock
from openassessment.assessment.errors import (
    PeerAssessmentInternalError,
    PeerAssessmentRequestError,
    PeerAssessmentWorkflowError,
)
from openassessment.workflow.errors import AssessmentWorkflowError

from openassessment.xblock.data_conversion import (
    verify_assessment_parameters,
    clean_criterion_feedback,
    create_rubric_dict,
)
from openassessment.xblock.user_data import get_user_preferences

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class LegacyPeerAssessmentActions:
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
                "success": False,
                "msg": self._(
                    "You must submit a response before you can perform a peer assessment."
                ),
            }

        uuid_server, uuid_client = self._get_server_and_client_submission_uuids(
            step_data, data
        )
        if uuid_server != uuid_client:
            logger.warning(
                "Irrelevant assessment submission: expected '%s', got '%s'",
                uuid_server,
                uuid_client,
            )
            return {
                "success": False,
                "msg": self._(
                    "This feedback has already been submitted or the submission has been cancelled."
                ),
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
                        data["criterion_feedback"],
                    ),
                    data["overall_feedback"],
                    create_rubric_dict(
                        self.config_data.prompts,
                        self.config_data.rubric_criteria_with_labels,
                    ),
                    step_data.assessment["must_be_graded_by"],
                )

                # Emit analytics event...
                self.publish_assessment_event(
                    "openassessmentblock.peer_assess", assessment
                )

            except (PeerAssessmentRequestError, PeerAssessmentWorkflowError):
                logger.warning(
                    "Peer API error for submission UUID %s",
                    self.submission_uuid,
                    exc_info=True,
                )
                return {
                    "success": False,
                    "msg": self._("Your peer assessment could not be submitted."),
                }
            except PeerAssessmentInternalError:
                logger.exception(
                    "Peer API internal error for submission UUID: %s",
                    self.submission_uuid,
                )
                msg = self._("Your peer assessment could not be submitted.")
                return {"success": False, "msg": msg}

            # Update both the workflow that the submission we"re assessing
            # belongs to, as well as our own (e.g. have we evaluated enough?)
            try:
                if assessment:
                    self.update_workflow_status(
                        submission_uuid=assessment["submission_uuid"]
                    )
                self.update_workflow_status()
            except AssessmentWorkflowError:
                logger.exception(
                    "Workflow error occurred when submitting peer assessment "
                    "for submission %s",
                    self.submission_uuid,
                )
                msg = self._("Could not update workflow status.")
                return {"success": False, "msg": msg}

            # Temp kludge until we fix JSON serialization for datetime
            assessment["scored_at"] = str(assessment["scored_at"])

            return {"success": True, "msg": ""}

        return {"success": False, "msg": self._("Could not load peer assessment.")}
