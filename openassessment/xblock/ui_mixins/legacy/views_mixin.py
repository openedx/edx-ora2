"""
Views for the old-style ORA UI
"""

from xblock.core import XBlock

from openassessment.xblock.ui_mixins.legacy.peer_assessments.views import (
    render_peer_assessment
)
from openassessment.xblock.ui_mixins.legacy.self_assessments.views import (
    render_self_assessment
)
from openassessment.xblock.ui_mixins.legacy.student_training.views import (
    render_student_training
)
from openassessment.xblock.ui_mixins.legacy.submissions.views import (
    LegacySubmissionViewsMixin,
)


class LegacyViewsMixin(LegacySubmissionViewsMixin):
    @XBlock.handler
    def render_peer_assessment(self, data):
        continue_grading = data.params.get("continue_grading", False)
        peer_data = self.peer_data(continue_grading)
        if peer_data.is_cancelled:
            self.no_peers = True
        if (peer_data.is_peer or peer_data.is_skipped):
            if peer_data.get_peer_submission():
                self.no_peers = False
            else:
                self.no_peers = True
        return render_peer_assessment(self.api_data, continue_grading)

    @XBlock.handler
    def render_self_assessment(self):
        if self.self_data.is_cancelled:
            self.no_peers = True
        return render_self_assessment(self.api_data)

    @XBlock.hander
    def render_student_training(self):
        return render_student_training(self.api_data)
