"""
JSON handlers for the old-style ORA UI
"""


from openassessment.xblock.ui_mixins.legacy.peer_assessments.actions import (
    LegacyPeerAssessmentActions,
)
from openassessment.xblock.ui_mixins.legacy.submissions.actions import (
    LegacySubmissionActions,
)


class LegacyHandlersMixin(LegacySubmissionActions, LegacyPeerAssessmentActions):
    pass
