from openassessment.xblock.resolve_dates import DISTANT_FUTURE


class ProblemClosedAPI:

    def __init__(self, block, step=None):
        self.block = block
        (
            self.problem_closed,
            self.reason,
            self.start_date,
            self.due_date,
        ) = block.is_closed(step=step)

    def __repr__(self):
        return {
            "problem_closed": self.problem_closed,
            "reason": self.reason,
            "start_date": self.start_date,
            "due_date": self.due_date,
        }

    @property
    def is_due(self):
        return self.due_date < DISTANT_FUTURE

    @property
    def is_not_available_yet(self):
        return self.problem_closed and self.reason == "start"

    @property
    def is_past_due(self):
        return self.problem_closed and self.reason == "due"
