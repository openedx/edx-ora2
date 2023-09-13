"""
External API for ORA Staff Assessment data
"""
from submissions import team_api as team_sub_api

from openassessment.assessment.api import staff as staff_api, teams as teams_api
from openassessment.xblock.apis.step_data_api import StepDataAPI
from openassessment.xblock.utils.data_conversion import (
    clean_criterion_feedback,
    create_rubric_dict,
)


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

    def create_team_assessment(self, data):
        team_submission = team_sub_api.get_team_submission_from_individual_submission(
            data["submission_uuid"]
        )
        return (
            teams_api.create_assessment(
                team_submission["team_submission_uuid"],
                self.student_id,
                data["options_selected"],
                clean_criterion_feedback(
                    self.config_data.rubric_criteria, data["criterion_feedback"]
                ),
                data["overall_feedback"],
                self.rubric_dict,
            ),
            team_submission["team_submission_uuid"],
        )

    def create_assessment(self, data):
        return staff_api.create_assessment(
            data["submission_uuid"],
            self.student_id,
            data["options_selected"],
            clean_criterion_feedback(
                self.config_data.rubric_criteria, data["criterion_feedback"]
            ),
            data["overall_feedback"],
            self.rubric_dict,
        )

    @staticmethod
    def staff_assessment_exists(submission_uuid):
        return staff_api.get_latest_staff_assessment(submission_uuid) is not None
