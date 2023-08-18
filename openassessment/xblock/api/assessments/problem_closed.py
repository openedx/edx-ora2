from openassessment.xblock.resolve_dates import DISTANT_FUTURE

class ProblemClosedAPI:
    def __init__(self, block, step=None):
        self.block = block
        problem_closed, reason, start_date, due_date = block.is_closed(step=step)
        self._problem_closed = problem_closed
        self._reason = reason
        self._start_date = start_date
        self._due_date = due_date

    def __repr__(self):
        return "{0}".format({
            "problem_closed": self.problem_closed,
            "reason": self.reason,
            "start_date": self.start_date,
            "due_date": self.due_date,
        })

    @property
    def problem_closed(self):
        return self._problem_closed

    @property
    def reason(self):
        return self._reason

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
        return self.problem_closed and self.reason == "start"

    @property
    def is_past_due(self):
        return self.problem_closed and self.reason == "due"
