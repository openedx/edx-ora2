"""
UI-level acceptance tests for OpenAssessment accessibility.
"""
import os
import unittest
from tests import OpenAssessmentTest, StaffAreaPage


class OpenAssessmentA11yTest(OpenAssessmentTest):
    """
    UI-level acceptance tests for Open Assessment accessibility.
    """

    def setUp(self, problem_type, staff=False):
        super(OpenAssessmentA11yTest, self).setUp(problem_type, staff=staff)
        self.auto_auth_page.visit()

    def _check_a11y(self, page):
        page.a11y_audit.config.set_scope(
            exclude=[
                ".container-footer",
                ".nav-skip",
                "#global-navigation",
            ],
        )
        page.a11y_audit.config.set_rules({
            "ignore": [
                "aria-valid-attr",  # TODO: AC-199
                "color-contrast",  # TODO: AC-198
                "empty-heading",  # TODO: AC-197
                "link-href",  # TODO: AC-199
                "link-name",  # TODO: AC-196
                "skip-link",  # TODO: AC-179
            ]
        })
        page.a11y_audit.check_for_accessibility_errors()


class SelfAssessmentA11yTest(OpenAssessmentA11yTest):
    """
    Test the accessibility of the self-assessment flow.
    """

    def setUp(self):
        super(SelfAssessmentA11yTest, self).setUp('self_only')

    def test_self_assessment_a11y(self):
        self.submission_page.visit()
        self._check_a11y(self.submission_page)


class PeerAssessmentA11yTest(OpenAssessmentA11yTest):
    """
    Test the accessibility of the peer-assessment flow.
    """

    def setUp(self):
        super(PeerAssessmentA11yTest, self).setUp('peer_only')

    def test_peer_assessment_a11y(self):
        self.submission_page.visit()
        self._check_a11y(self.submission_page)


class StudentTrainingA11yTest(OpenAssessmentA11yTest):
    """
    Test the accessibility of student training (the "learning to assess" step).
    """
    def setUp(self):
        super(StudentTrainingA11yTest, self).setUp('student_training')

    def test_student_training_a11y(self):
        self.submission_page.visit()
        self._check_a11y(self.submission_page)


class StaffAreaA11yTest(OpenAssessmentA11yTest):
    """
    Test the accessibility of the staff area.
    """
    def setUp(self):
        super(StaffAreaA11yTest, self).setUp('peer_only', staff=True)
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)

    def test_staff_tools_panel_a11y(self):
        """
        Check the accessibility of the "Staff Tools" panel
        """
        self.staff_area_page.visit()
        self.staff_area_page.click_staff_toolbar_button("staff-tools")
        self._check_a11y(self.staff_area_page)

    def test_staff_info_panel_a11y(self):
        """
        Check the accessibility of the "Staff Info" panel
        """
        self.staff_area_page.visit()
        self.staff_area_page.click_staff_toolbar_button("staff-info")
        self._check_a11y(self.staff_area_page)


if __name__ == "__main__":

    # Configure the screenshot directory
    if 'SCREENSHOT_DIR' not in os.environ:
        tests_dir = os.path.dirname(__file__)
        os.environ['SCREENSHOT_DIR'] = os.path.join(tests_dir, 'screenshots')

    unittest.main()
