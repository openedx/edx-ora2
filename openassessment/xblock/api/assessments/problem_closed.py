from openassessment.assessment.api import self as self_api
from submissions import api as submission_api

from ..data_conversion import (
    create_submission_dict
)
from ..resolve_dates import DISTANT_FUTURE
from .workflow import WorkflowAPI

class ProblemClosedAPI:
    def __init__(self, problem_closed, reason, start_date, due_date):
        self.problem_closed = problem_closed
        self.reason = reason
        self.start_date = start_date
        self.due_date = due_date

    def __repr__(self):
        return {
            "problem_closed": self.problem_closed,
            "reason": self.reason,
            "start_date": self.start_date,
            "due_date": self.due_date,
        }

    def is_due(self):
        return self.due_date < DISTANT_FUTURE

    def is_not_avilable_yet(self):
        return self.problem_closed and self.reason === 'start'

    def is_past_due(self):
        return self.problem_closed and self.reason === 'due'
