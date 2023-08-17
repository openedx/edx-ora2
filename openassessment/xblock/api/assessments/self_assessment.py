from openassessment.assessment.api import self as self_api
from submissions import api as submission_api

from openassessment.xblock.data_conversion import (
    clean_criterion_feedback,
    create_rubric_dict,
    create_submission_dict
)
from openassessment.xblock.resolve_dates import DISTANT_FUTURE
from openassessment.xblock.api.workflow import WorkflowAPI
from openassessment.xblock.api.block import BlockAPI
from .problem_closed import ProblemClosedAPI

class SelfAssessmentAPI:
    def __init__(self, block):
        self._block = block
        self._block_api = BlockAPI(block)
        self._is_closed = ProblemClosedAPI(block, step="self-assessment")
        self._workflow = WorkflowAPI(block)

    @property
    def is_self_complete(self):
        return self._workflow.is_self_complete

    @property
    def is_cancelled(self):
        return self._workflow.is_cancelled

    @property
    def is_self_active(self):
        return self._workflow.is_self

    @property
    def problem_closed(self):
        return self._is_closed.problem_closed

    @property
    def due_date(self):
        return self._is_closed.due_date

    @property
    def start_date(self):
        return self._is_closed.start_date

    @property
    def is_due(self):
        return self._is_closed.is_due

    @property
    def is_past_due(self):
        return self._is_closed.is_past_due

    @property
    def is_not_available_yet(self):
        return self._is_closed.is_not_available_yet

    @property
    def assessment(self):
        return self_api.get_assessment(self._workflow.workflow.get('submission_uuid'))

    @property
    def submission(self):
        if (self._block.submission_uuid):
            return submission_api.get_submission(self._block.submission_uuid)
        return None

    @property
    def submission_dict(self):
        if (self.submission):
            return create_submission_dict(self.submission, self._block_api.prompts)
        return None

    @property
    def file_urls(self):
        if (self.submission):
            return self._block.get_download_urls_from_submission(self.submission)
        return None


    def create_assessment(self, data):
        return self_api.create_assessment(
            self._block.submission_uuid,
            self._block_api.student_item_dict['student_id'],
            data['options_selected'],
            clean_criterion_feedback(self._block_api.rubric_criteria, data['criterion_feedback']),
            data['overall_feedback'],
            create_rubric_dict(self._block_api.prompts, self._block.rubric_criteria_with_labels)
        )
