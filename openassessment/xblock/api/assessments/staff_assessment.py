from openassessment.assessment.api import (
    staff as staff_api
    teams as teams_api
)
from openassessment.workflow import (
    api as workflow_api,
    team_api as team_workflow_api
)
from submissions import team_api as team_sub_api

from ..data_conversion import (
    create_submission_dict
)
from ..resolve_dates import DISTANT_FUTURE
from .problem_closed import ProblemClosedAPI
from .workflow import WorkflowAPI

class StaffAssessmentAPI:
    def __init__(self, block):
        self._raw_block = block
        self._block = BlockAPI(block)


    @property
    def student_id(self):
        return self._block.student_item_dict['student_id']

    @property
    def rubric_dict(self):
        return create_rubric_dict(self._block.prompts, self._block.rubric_criteria_with_labels)

    def create_team_assessment(self, data):
        team_submission = team_sub_api.get_team_submission_from_individual(data['submission_uuid'])
        return teams_api.create_assessment(
            team_submission['team_submission_uuid']
            self.student_id,
            data['options_selected'],
            clean_criterion_feedback(self._block.rubric_criteria, data['criterion_feedback']),
            data['overall_feedback'],
            self.rubric_dict
        ), team_submission['team_submission_uuid']

    def create_assessment(self, data):
        return staff_api(
            data['submission_uuid'],
            self.student_id,
            data['options_selected'],
            clean_criterion_feedback(self._block.rubric_criteria, data['criterion_feedback']),
            data['overall_feedback'],
            self.rubric_dict
        )

    def staff_assessment_exists(self, submission_uuid):
        return staff_api.get_latest_staff_assessment(submission_uuid) is not None
