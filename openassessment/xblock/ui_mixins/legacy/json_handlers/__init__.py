from openassessment.xblock.ui_mixins.legacy.json_handlers.peer_assessment import (
    LegacyPeerAssessmentHandlers,
)
from openassessment.xblock.ui_mixins.legacy.json_handlers.submissions import (
    LegacySubmissionHandlers,
)


class LegacyHandlersMixin(
    LegacySubmissionHandlers,
    LegacyPeerAssessmentHandlers,
):
    pass
