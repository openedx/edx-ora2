"""
UI-level acceptance tests for OpenAssessment accessibility.
"""
import os
import unittest
from tests import OpenAssessmentTest


class OpenAssessmentAxsTest(OpenAssessmentTest):
    """
    UI-level acceptance tests for Open Assessment accessibility.
    """

    def _check_axs(self):
        self.auto_auth_page.visit()
        self.submission_page.visit()
        self.submission_page.a11y_audit.config.set_rules({
            "ignore": [
                "aria-valid-attr",  # TODO: AC-199
                "color-contrast",  # TODO: AC-198
                "empty-heading",  # TODO: AC-197
                "link-name",  # TODO: AC-196
            ]
        })
        report = self.submission_page.a11y_audit.check_for_accessibility_errors()


class SelfAssessmentAxsTest(OpenAssessmentAxsTest):
    """
    Test the accessibility of the self-assessment flow.
    """

    def setUp(self):
        super(SelfAssessmentAxsTest, self).setUp('self_only')

    def test_self_assessment_axs(self):
        self._check_axs()


class PeerAssessmentAxsTest(OpenAssessmentAxsTest):
    """
    Test the accessibility of the peer-assessment flow.
    """

    def setUp(self):
        super(PeerAssessmentAxsTest, self).setUp('peer_only')

    def test_peer_assessment_axs(self):
        self._check_axs()


class StudentTrainingAxsTest(OpenAssessmentAxsTest):
    """
    Test the accessibility of student training (the "learning to assess" step).
    """
    def setUp(self):
        super(StudentTrainingAxsTest, self).setUp('student_training')

    def test_student_training_axs(self):
        self._check_axs()


if __name__ == "__main__":

    # Configure the screenshot directory
    if 'SCREENSHOT_DIR' not in os.environ:
        tests_dir = os.path.dirname(__file__)
        os.environ['SCREENSHOT_DIR'] = os.path.join(tests_dir, 'screenshots')

    unittest.main()
