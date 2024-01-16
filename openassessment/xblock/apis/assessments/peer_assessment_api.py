"""
External API for ORA Peer Assessment data
"""
import logging

from openassessment.assessment.errors import PeerAssessmentWorkflowError
from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.errors.peer import PeerAssessmentInternalError, PeerAssessmentRequestError
from openassessment.assessment.models.peer import PeerWorkflowItem
from openassessment.assessment.serializers.base import serialize_assessments
from openassessment.workflow.errors import AssessmentWorkflowError
from openassessment.xblock.apis.assessments.errors import (
    ReviewerMustHaveSubmittedException,
    ServerClientUUIDMismatchException,
)
from openassessment.xblock.utils.data_conversion import create_submission_dict
from openassessment.xblock.apis.step_data_api import StepDataAPI
from openassessment.xblock.utils.data_conversion import (
    clean_criterion_feedback,
    create_rubric_dict,
)

logger = logging.getLogger(__name__)


class PeerAssessmentAPI(StepDataAPI):
    def __init__(self, block, continue_grading=False):
        super().__init__(block, "peer-assessment")
        self._continue_grading = continue_grading

    @property
    def submission_uuid(self):
        return self.workflow_data.submission_uuid

    @property
    def assessment(self):
        return self.config_data.get_assessment_module("peer-assessment")

    @property
    def assessments(self):
        return peer_api.get_assessments(self.submission_uuid)

    @property
    def scored_assessments(self):
        return serialize_assessments(PeerWorkflowItem.get_scored_assessments(self.submission_uuid))

    @property
    def unscored_assessments(self):
        return serialize_assessments(PeerWorkflowItem.get_unscored_assessments(self.submission_uuid))

    @property
    def peer_grade(self):
        return self._block.grades_data.peer_score

    @property
    def continue_grading(self):
        return self._continue_grading and self.workflow_data.is_peer_complete

    @property
    def file_upload_type(self):
        return self.config_data.file_upload_type

    @property
    def num_completed(self):
        _, count = self.has_finished
        return count

    @property
    def num_received(self):
        """
        Return number of peer assessments this submission has received
        or None if submission not found.
        """
        return peer_api.get_graded_by_count(self.submission_uuid)

    @property
    def waiting_for_submissions_to_assess(self):
        """
        Determine if the student is blocked, waiting on submissions to assess.
        """
        peer_submission = peer_api.get_submission_to_assess(
            self.submission_uuid, self.assessment["must_be_graded_by"],
            peek=True
        )
        return not bool(peer_submission)

    @property
    def has_finished(self):
        finished, count = peer_api.has_finished_required_evaluating(
            self.submission_uuid, self.assessment["must_grade"]
        )
        return finished, count

    @property
    def is_cancelled(self):
        return self.workflow_data.is_cancelled

    @property
    def is_complete(self):
        finished = False
        if self.assessment:
            finished = self.has_finished[0]
        return self.workflow_data.is_done or finished

    @property
    def is_peer(self):
        return self.workflow_data.is_peer

    @property
    def is_skipped(self):
        return self.workflow_data.is_peer_skipped

    @property
    def student_item(self):
        return self.config_data.student_item_dict

    @property
    def must_be_graded_by(self):
        return self.assessment['must_be_graded_by']

    def format_submission_for_publish(self, peer_submission):
        student_item_dict = self.config_data.student_item_dict
        return {
            "requesting_student_id": student_item_dict["student_id"],
            "course_id": student_item_dict["course_id"],
            "item_id": student_item_dict["item_id"],
            "submission_returned_uuid": peer_submission["uuid"] if peer_submission else None,
        }

    def get_submission_dict(self, peer_sub):
        return create_submission_dict(peer_sub, self.config_data.prompts)

    def get_download_urls(self, peer_sub):
        return self._block.get_download_urls_from_submission(peer_sub)

    def get_active_assessment_submission(self):
        try:
            return peer_api.get_active_assessment_submission(
                self.submission_uuid
            )
        except PeerAssessmentWorkflowError as err:
            logger.exception(err)
            return None

    def get_peer_submission(self):
        peer_submission = False
        try:
            peer_submission = peer_api.get_submission_to_assess(
                self.submission_uuid, self.assessment["must_be_graded_by"]
            )
            self.config_data.publish_event(
                "openassessmentblock.get_peer_submission",
                self.format_submission_for_publish(peer_submission),
            )
        except PeerAssessmentWorkflowError as err:
            logger.exception(err)
        return peer_submission

    def assert_assessing_valid_submission(self, uuid_client):
        """
        Validate that the forntend and backend agree on which submission is being assessed
        """
        # Get the current active submission without pulling a new one
        submission = self.get_active_assessment_submission()

        # If there is no active submission (expired or never got one somehow), raise
        if submission is None:
            raise ServerClientUUIDMismatchException()

        if uuid_client is None:
            # If we don't have a uuid from the client, we can't do the next check
            return

        uuid_server = submission.get("uuid", None)

        # If the server and client don't agree, raise
        if uuid_server != uuid_client:
            logger.warning(
                "Irrelevant assessment submission: expected '%s', got '%s'",
                uuid_server,
                uuid_client,
            )
            raise ServerClientUUIDMismatchException()


def peer_assess(
    options_selected,
    overall_feedback,
    criterion_feedback,
    config_data,
    workflow_data,
    peer_step_data,
    assessed_submission_uuid=None,
):
    """Place a peer assessment into OpenAssessment system

    Assess a Peer Submission.  Performs basic workflow validation to ensure
    that an assessment can be performed as this time.

    Args:
        `assessed_submission_uuid` (string): The unique identifier for the submission being assessed.
        `options_selected` (dict): Dictionary mapping criterion names to option values.
        `overall_feedback` (unicode): Written feedback for the submission as a whole.
        `criterion_feedback` (unicode): Written feedback per the criteria for the submission.
        `config_data`: ORA Config Data object
        `workflow_data`: ORA Workflow Data object
        `peer_step_data`: ORA Peer Step Data object

    Returns:
        None

    Raises:
        ReviewerMustHaveSubmittedException
        ServerClientUUIDMismatchException
        PeerAssessmentRequestError
        PeerAssessmentWorkflowError
        PeerAssessmentInternalError
        AssessmentWorkflowError
    """
    scorer_submission_uuid = workflow_data.submission_uuid
    if not workflow_data.has_workflow:
        raise ReviewerMustHaveSubmittedException()

    peer_step_data.assert_assessing_valid_submission(assessed_submission_uuid)

    try:
        assessment = peer_api.create_assessment(
            scorer_submission_uuid,
            config_data.student_item_dict["student_id"],
            options_selected,
            clean_criterion_feedback(
                config_data.rubric_criteria_with_labels,
                criterion_feedback,
            ),
            overall_feedback,
            create_rubric_dict(
                config_data.prompts,
                config_data.rubric_criteria_with_labels,
            ),
            peer_step_data.must_be_graded_by,
        )
        # Emit analytics event...
        config_data.publish_assessment_event("openassessmentblock.peer_assess", assessment)
    except (PeerAssessmentRequestError, PeerAssessmentWorkflowError):
        logger.warning(
            "Peer API error for submission UUID %s",
            scorer_submission_uuid,
            exc_info=True,
        )
        raise
    except PeerAssessmentInternalError:
        logger.exception(
            "Peer API internal error for submission UUID: %s",
            scorer_submission_uuid,
        )
        raise

    # Update both the workflow that the submission we"re assessing
    # belongs to, as well as our own (e.g. have we evaluated enough?)
    try:
        if assessment:
            workflow_data.update_workflow_status(assessment['submission_uuid'])
        workflow_data.update_workflow_status(scorer_submission_uuid)
    except AssessmentWorkflowError:
        logger.exception(
            "Workflow error occurred when submitting peer assessment for submission %s",
            assessed_submission_uuid,
        )
        raise
