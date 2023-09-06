"""
Views for the old-style ORA UI
"""

from xblock.core import XBlock

from .peer_assessments.views import render_peer_assessment, peer_path_and_context
from .self_assessments.views import render_self_assessment, self_path_and_context
from .staff_assessments.views import render_staff_assessment, staff_path_and_context
from .student_training.views import render_student_training, training_path_and_context
from .submissions.views import render_submission, get_submission_path, get_submission_context


class LegacyViewsMixin:
    @XBlock.handler
    def render_submission(self, data, suffix=""):  # pylint: disable=unused-argument
        return render_submission(self.config_data, self.submission_data)

    # NOTE - Temporary surfacing for testing / refactoring
    def submission_path_and_context(self):
        return get_submission_path(self.submission_data), get_submission_context(self.config_data, self.submission_data)

    @XBlock.handler
    def render_peer_assessment(self, data, suffix=""):  # pylint: disable=unused-argument
        continue_grading = data.params.get("continue_grading", False)
        peer_assessment_data = self.peer_assessment_data(continue_grading)
        if peer_assessment_data.is_cancelled:
            self.no_peers = True
        if peer_assessment_data.is_peer or peer_assessment_data.is_skipped:
            if peer_assessment_data.get_peer_submission():
                self.no_peers = False
            else:
                self.no_peers = True
        return render_peer_assessment(self.api_data, continue_grading)

    # NOTE - Temporary surfacing for testing / refactoring
    def peer_path_and_context(self, continue_grading=False):
        return peer_path_and_context(self.api_data, continue_grading)

    # NOTE - Temporary surfacing for testing / refactoring
    def self_path_and_context(self):
        return self_path_and_context(self.api_data)

    # NOTE - Temporary surfacing for testing / refactoring
    def staff_path_and_context(self):
        return staff_path_and_context(self.api_data)

    # NOTE - Temporary surfacing for testing / refactoring
    def training_path_and_context(self):
        return training_path_and_context(self.api_data)

    @XBlock.handler
    def render_self_assessment(self, data, suffix=""):  # pylint: disable=unused-argument
        step_data = self.api_data.self_assessment_data
        if step_data.is_cancelled:
            self.no_peers = True
        return render_self_assessment(self.api_data)

    @XBlock.handler
    def render_staff_assessment(self, data, suffix=""):  # pylint: disable=unused-argument
        return render_staff_assessment(self.api_data)

    @XBlock.handler
    def render_student_training(self, data, suffix=""):  # pylint: disable=unused-argument
        return render_student_training(self.api_data)
