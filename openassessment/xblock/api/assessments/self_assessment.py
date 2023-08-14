from openassessment.assessment.api import self as self_api
from submissions import api as submission_api

from ..data_conversion import (
    create_submission_dict
)
from ..resolve_dates import DISTANT_FUTURE
from .problem_closed import ProblemClosedAPI
from .workflow import WorkflowAPI

class SelfAssessmentAPI:
    def __init__(self, block):
        self.block = block;
        self._is_closed = ProblemClosedAPI(block.is_closed(step="self-assessment"))
        self._workflow = WorkflowAPI(block);

    @property
    def problem_closed(self):
        return self._is_closed.problem_closed

    @property
    def closed_reason(self):
        return self._is_closed.reason

    @property
    def due_date(self):
        return self._is_closed.due_date

    @property
    def start_date(self):
        return self._is_closed.start_date

    @property
    def is_due(self):
        return self.is_closed.due_date < DISTANT_FUTURE

    @property
    def assessment(self):
        return self_api.get_assessment(workflow.get('submission_uuid'))

    @property
    def submission(self):
        return submission_api.get_submission(self.block.submission_uuid)

    @property
    def submission_dict(self):
        return create_submission_dict(self.submission, self.block.prompts)

    @property
    def file_urls(self):
        return self.block.get_download_urls_from_submission(self.submission)

    def create_assessment(self, data):
        return self_api.create_assessment(
            self.block.submission_uuid,
            self.block.get_student_item_dict()['student_id'],
            data['options_selected'],
            clean_criterion_feedback(self.block.rubric_criteria, data['criterion_feedback']),
            data['overall_feedback'],
            create_rubric_dict(self.prompts, self.rubric_criteria_with_labels)
        )
