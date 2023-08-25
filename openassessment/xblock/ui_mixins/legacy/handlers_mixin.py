"""
JSON handlers for the old-style ORA UI
"""


from xblock.core import XBlock
from openassessment.xblock.ui_mixins.legacy.peer_assessments.actions import peer_assess
from openassessment.xblock.ui_mixins.legacy.submissions.actions import (
    LegacySubmissionActions,
)


class LegacyHandlersMixin(LegacySubmissionActions):
    """
    Exposes actions (@XBlock.json_handlers) used in our legacy ORA UI
    """

    @XBlock.json_handler
    def submit(self, data, suffix=""):  # pylint: disable=unused-argument
        """ Submit a response for the student provided in data['submission'] """
        return LegacySubmissionActions.submit(
            self.config_data, self.submission_data, data
        )

    @XBlock.json_handler
    def save_submission(self, data, suffix=""):  # pylint: disable=unused-argument
        """ Save a draft response for the student under data['submission'] """
        return LegacySubmissionActions.save_submission(self.config_data, self.submission_data, data)

    @XBlock.json_handler
    def peer_assess(self, data):
        return peer_assess(self.api_data, data)
