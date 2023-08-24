"""
JSON handlers for the old-style ORA UI
"""


from xblock.core import XBlock
from openassessment.xblock.ui_mixins.legacy.peer_assessments.actions import (
    LegacyPeerAssessmentActions,
)
from openassessment.xblock.ui_mixins.legacy.submissions.actions import (
    LegacySubmissionActions,
)


class LegacyHandlersMixin(LegacySubmissionActions, LegacyPeerAssessmentActions):
    """
    Exposes actions (@XBlock.json_handlers) used in our legacy ORA UI
    """

    @XBlock.json_handler
    def submit(self, data, suffix=""):  # pylint: disable=unused-argument
        return LegacySubmissionActions.submit(
            self.config_data, self.submission_data, data
        )
