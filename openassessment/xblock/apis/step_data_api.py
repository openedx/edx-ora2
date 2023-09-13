""" Base class for step data collations """
from openassessment.xblock.utils.resolve_dates import DISTANT_FUTURE


class StepDataAPI:
    def __init__(self, block, step=None):
        self._block = block
        problem_closed, closed_reason, start_date, due_date = block.is_closed(step=step)
        self._problem_closed = problem_closed
        self._closed_reason = closed_reason
        self._start_date = start_date
        self._due_date = due_date

    def __repr__(self):
        return "{0}".format(
            {
                "problem_closed": self.problem_closed,
                "closed_reason": self.closed_reason,
                "start_date": self.start_date,
                "due_date": self.due_date,
            }
        )

    @property
    def config_data(self):
        return self._block.api_data.config_data

    @property
    def workflow_data(self):
        return self._block.api_data.workflow_data

    @property
    def problem_closed(self):
        return self._problem_closed

    @property
    def closed_reason(self):
        return self._closed_reason

    @property
    def start_date(self):
        return self._start_date

    @property
    def due_date(self):
        return self._due_date

    @property
    def is_due(self):
        return self.due_date < DISTANT_FUTURE

    @property
    def is_not_available_yet(self):
        return self.problem_closed and self.closed_reason == "start"

    @property
    def is_past_due(self):
        return self.problem_closed and self.closed_reason == "due"
