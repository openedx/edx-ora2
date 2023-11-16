"""
External API for ORA Self Assessment data
"""
import logging
from submissions import api as submission_api

from openassessment.assessment.api import self as self_api
from openassessment.assessment.errors.self import SelfAssessmentInternalError, SelfAssessmentRequestError
from openassessment.workflow.errors import AssessmentWorkflowInternalError, AssessmentWorkflowRequestError
from openassessment.xblock.apis.assessments.errors import ReviewerMustHaveSubmittedException
from openassessment.xblock.apis.step_data_api import StepDataAPI
from openassessment.xblock.utils.data_conversion import (
    clean_criterion_feedback,
    create_rubric_dict,
    create_submission_dict,
)


logger = logging.getLogger(__name__)


class SelfAssessmentAPI(StepDataAPI):
    def __init__(self, block):
        super().__init__(block, "self-assessment")

    @property
    def is_self_complete(self):
        return self.workflow_data.is_self_complete

    @property
    def is_cancelled(self):
        return self.workflow_data.is_cancelled

    @property
    def is_self_active(self):
        return self.workflow_data.is_self

    @property
    def assessment(self):
        return self_api.get_assessment(self.workflow_data.workflow.get("submission_uuid"))

    @property
    def submission_uuid(self):
        return self._block.submission_uuid

    @property
    def submission(self):
        if self.submission_uuid:
            return submission_api.get_submission(self.submission_uuid)
        return None

    @property
    def submission_dict(self):
        if self.submission:
            return create_submission_dict(self.submission, self.config_data.prompts)
        return None

    @property
    def file_urls(self):
        if self.submission:
            return self._block.get_download_urls_from_submission(self.submission)
        return None

    @property
    def student_item_dict(self):
        return self.config_data.student_item_dict

    @property
    def rubric_criteria(self):
        return self.config_data.rubric_criteria

    @property
    def rubric_criteria_with_labels(self):
        return self.config_data.rubric_criteria

    @property
    def prompts(self):
        return self.config_data.rubric_criteria


def self_assess(
    options_selected,
    criterion_feedback,
    overall_feedback,
    config_data,
    workflow_data,
    self_step_data
):
    """
    Create a self-assessment for a submission.

    Args:
        `options_selected` (dict): Dictionary mapping criterion names to option values.
        `criterion_feedback` (unicode): Written feedback per the criteria for the submission.
        `overall_feedback` (unicode): Written feedback for the submission as a whole.
        `config_data`: ORA Config Data object
        `workflow_data`: ORA Workflow Data object
        `self_step_data`: ORA Self Step Data object

    Returns: None

    Raises:
        ReviewerMustHaveSubmittedException
        SelfAssessmentRequestError
        AssessmentWorkflowRequestError
        SelfAssessmentInternalError
        AssessmentWorkflowInternalError
    """
    submission_uuid = self_step_data.submission_uuid

    if not workflow_data.has_workflow:
        raise ReviewerMustHaveSubmittedException()

    try:
        assessment = self_api.create_assessment(
            submission_uuid,
            self_step_data.student_item_dict["student_id"],
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
        )
        config_data.publish_assessment_event("openassessmentblock.self_assess", assessment)
        # After we've created the self-assessment, we need to update the workflow.
        workflow_data.update_workflow_status()
    except (
        SelfAssessmentRequestError,
        AssessmentWorkflowRequestError,
        SelfAssessmentInternalError,
        AssessmentWorkflowInternalError
    ):
        logger.warning(
            "An error occurred while submitting a self assessment for the submission %s",
            submission_uuid,
            exc_info=True,
        )
        raise
