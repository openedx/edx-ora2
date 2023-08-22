from openassessment.xblock.ui_mixins.legacy.views.peer_assessment import (
    LegacyPeerAssessmentViewMixin,
)
from openassessment.xblock.ui_mixins.legacy.views.submissions import (
    LegacySubmissionViewsMixin,
)


class LegacyViewMixin(LegacyPeerAssessmentViewMixin, LegacySubmissionViewsMixin):
    pass
