"""
Views for the old-style ORA UI
"""

from xblock.core import XBlock

from .peer_assessments.views import render_peer_assessment
from .self_assessments.views import render_self_assessment
from .student_training.views import render_student_training
from .submissions.views import LegacySubmissionViews


class LegacyViewsMixin:
    @XBlock.handler
    def render_submission(self, data, suffix=""):  # pylint: disable=unused-argument
        """ """
        return LegacySubmissionViews.render_submission(self.config_data, self.submission_data)

    # NOTE - Temporary surfacing for testing / refactoring
    def submission_path_and_context(self):
        return LegacySubmissionViews.submission_path(self.submission_data), LegacySubmissionViews.submission_context(self.config_data, self.submission_data)

    @XBlock.handler
    def render_peer_assessment(self, data):
        continue_grading = data.params.get("continue_grading", False)
        peer_data = self.peer_data(continue_grading)
        if peer_data.is_cancelled:
            self.no_peers = True
        if peer_data.is_peer or peer_data.is_skipped:
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

    @XBlock.handler
    def render_student_training(self):
        return render_student_training(self.api_data)
