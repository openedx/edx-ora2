"""
External API for ORA Staff Assessment data
"""
import logging
from submissions import team_api as team_sub_api
from openassessment.assessment.api import staff as staff_api, teams as teams_api
from openassessment.assessment.errors.staff import StaffAssessmentError
from openassessment.workflow import api as workflow_api, team_api as team_workflow_api
from openassessment.xblock.apis.step_data_api import StepDataAPI
from openassessment.xblock.utils.data_conversion import (
    clean_criterion_feedback,
    create_rubric_dict,
)

logger = logging.getLogger(__name__)


class StaffAssessmentAPI(StepDataAPI):
    @property
    def has_status(self):
        return self.workflow_data.has_status

    @property
    def is_cancelled(self):
        return self.workflow_data.is_cancelled

    @property
    def is_done(self):
        return self.workflow_data.is_done

    @property
    def is_waiting(self):
        return self.workflow_data.is_waiting

    @property
    def student_id(self):
        return self.config_data.student_item_dict["student_id"]

    @property
    def rubric_dict(self):
        return create_rubric_dict(
            self.config_data.prompts, self.config_data.rubric_criteria_with_labels
        )

    @property
    def assessment(self):
        return staff_api.get_assessment(self.workflow_data.workflow.get("submission_uuid"))

    @staticmethod
    def staff_assessment_exists(submission_uuid):
        return staff_api.get_latest_staff_assessment(submission_uuid) is not None


def staff_assess(
    submission_uuid,
    options_selected,
    criterion_feedback,
    overall_feedback,
    assess_type,
    config_data,
    staff_step_data,
):
    """
    Create a staff assessment from a team or individual submission.
    """
    if config_data.is_team_assignment():
        do_assessment_fn = do_team_staff_assessment
    else:
        do_assessment_fn = do_staff_assessment
    do_assessment_fn(
        submission_uuid,
        options_selected,
        criterion_feedback,
        overall_feedback,
        assess_type,
        config_data,
        staff_step_data,
    )


def do_staff_assessment(
    submission_uuid,
    options_selected,
    criterion_feedback,
    overall_feedback,
    assess_type,
    config_data,
    staff_step_data,
):
    """
    Create a staff assessment from a staff submission.
    """
    try:
        assessment = staff_api.create_assessment(
            submission_uuid,
            staff_step_data.student_id,
            options_selected,
            clean_criterion_feedback(
                config_data.rubric_criteria,
                criterion_feedback,
            ),
            overall_feedback,
            staff_step_data.rubric_dict,
        )
        config_data.publish_assessment_event("openassessmentblock.staff_assess", assessment, type=assess_type)
        is_regrade = assess_type == 'regrade'
        workflow_api.update_from_assessments(submission_uuid, None, {}, override_submitter_requirements=is_regrade)
    except StaffAssessmentError:
        logger.warning(
            "An error occurred while submitting a staff assessment for the submission %s",
            submission_uuid,
            exc_info=True,
        )
        raise


# TODO: do_team_staff_assessment_from_individual vs _from_team
def do_team_staff_assessment(
    individual_submission_uuid,
    options_selected,
    criterion_feedback,
    overall_feedback,
    assess_type,
    config_data,
    staff_step_data,
    team_submission_uuid=None,
):
    if team_submission_uuid is None:
        team_submission = team_sub_api.get_team_submission_from_individual_submission(individual_submission_uuid)
        team_submission_uuid = team_submission['team_submission_uuid']
    try:
        assessment = teams_api.create_assessment(
            team_submission_uuid,
            staff_step_data.student_id,
            options_selected,
            clean_criterion_feedback(
                config_data.rubric_criteria, criterion_feedback
            ),
            overall_feedback,
            staff_step_data.rubric_dict,
        )
        config_data.publish_assessment_event("openassessmentblock.staff_assess", assessment[0], type=assess_type)
        is_regrade = assess_type == "regrade"
        team_workflow_api.update_from_assessments(
            team_submission_uuid,
            override_submitter_requirements=is_regrade
        )
    except StaffAssessmentError:
        logger.warning(
            "An error occurred while submitting a team assessment for (%s, %s)",
            individual_submission_uuid,
            team_submission_uuid,
            exc_info=True,
        )
        raise
