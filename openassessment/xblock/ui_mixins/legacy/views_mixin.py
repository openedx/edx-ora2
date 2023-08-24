"""
Views for the old-style ORA UI
"""


from openassessment.xblock.ui_mixins.legacy.peer_assessments.views import (
    LegacyPeerAssessmentViewsMixin,
)
from openassessment.xblock.ui_mixins.legacy.submissions.views import (
    LegacySubmissionViewsMixin,
)


class LegacyViewsMixin(LegacySubmissionViewsMixin, LegacyPeerAssessmentViewsMixin):
    pass
