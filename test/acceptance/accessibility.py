"""
UI-level acceptance tests for OpenAssessment accessibility.
"""
import os
import unittest
from tests import OpenAssessmentTest, StaffAreaPage, FullWorkflowMixin, MultipleOpenAssessmentMixin
from pages import MultipleAssessmentPage


class OpenAssessmentA11yTest(OpenAssessmentTest):
    """
    UI-level acceptance tests for Open Assessment accessibility.
    """

    def setUp(self, problem_type, staff=False):
        super(OpenAssessmentA11yTest, self).setUp(problem_type, staff=staff)
        self.auto_auth_page.visit()

    def _check_a11y(self, page):
        self._configure_a11y_audit_config(page)
        page.a11y_audit.check_for_accessibility_errors()

    def _configure_a11y_audit_config(self, page):
        page.a11y_audit.config.set_scope(
            exclude=[
                "#footer-edx-v3",  # Links to Facebook, Twitter, etc. Populated in production, but not here.
                ".instructor-info-action",  # Staff Debug Info link (general for all XBlocks)
            ],
        )


class SelfAssessmentA11yTest(OpenAssessmentA11yTest):
    """
    Test the accessibility of the self-assessment flow.
    """

    def setUp(self):
        super(SelfAssessmentA11yTest, self).setUp('self_only')

    def test_self_assessment_a11y(self):
        self.submission_page.visit()
        self._check_a11y(self.submission_page)

        self.submission_page.visit().submit_response(self.SUBMISSION)
        self.self_asmnt_page.wait_for_page().wait_for_response()
        self._check_a11y(self.self_asmnt_page)


class PeerAssessmentA11yTest(OpenAssessmentA11yTest):
    """
    Test the accessibility of the peer-assessment flow.
    """

    def setUp(self):
        super(PeerAssessmentA11yTest, self).setUp('peer_only')

    def test_peer_assessment_a11y(self):
        # Create a submission for one learner.
        self.submission_page.visit()
        self._check_a11y(self.submission_page)
        self.submission_page.visit().submit_response(self.SUBMISSION)

        # Create a submission for a second learner.
        self.auto_auth_page.visit()
        self.submission_page.visit().submit_response(self.SUBMISSION)

        # Check accessibility on the peer assessment page (there should be at least one available).
        self.peer_asmnt_page.visit()
        self._check_a11y(self.peer_asmnt_page)


class StudentTrainingA11yTest(OpenAssessmentA11yTest):
    """
    Test the accessibility of student training (the "learning to assess" step).
    """
    def setUp(self):
        super(StudentTrainingA11yTest, self).setUp('student_training')

    def test_student_training_a11y(self):
        self.submission_page.visit()
        self._check_a11y(self.submission_page)

        # Check accessibility on the training page.
        self.submission_page.visit().submit_response(self.SUBMISSION)
        self.student_training_page.wait_for_page().wait_for_response()
        self._check_a11y(self.student_training_page)


class StaffAreaA11yTest(OpenAssessmentA11yTest):
    """
    Test the accessibility of the staff area.

    This is testing a problem with "staff assessment only".
    """
    def setUp(self):
        super(StaffAreaA11yTest, self).setUp('staff_only', staff=True)
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)

    def test_staff_tools_panel(self):
        """
        Check the accessibility of the "Staff Tools" panel
        """
        self.staff_area_page.visit()
        self.staff_area_page.click_staff_toolbar_button("staff-tools")
        self._check_a11y(self.staff_area_page)

    def test_staff_info_panel(self):
        """
        Check the accessibility of the "Staff Info" panel
        """
        self.staff_area_page.visit()
        self.staff_area_page.click_staff_toolbar_button("staff-info")
        self._check_a11y(self.staff_area_page)

    def test_staff_grading_panel(self):
        """
        Check the accessibility of the "Staff Grading" panel
        """
        self.submission_page.visit().submit_response(self.SUBMISSION)
        self.assertTrue(self.submission_page.has_submitted)

        self.staff_area_page.visit()
        self.staff_area_page.click_staff_toolbar_button("staff-grading")
        self.staff_area_page.expand_staff_grading_section()
        self._check_a11y(self.staff_area_page)

    def test_learner_info(self):
        """
        Check the accessibility of the learner information sections of the "Staff Tools" panel.
        """
        self.auto_auth_page.visit()
        username, _ = self.auto_auth_page.get_username_and_email()

        self.submission_page.visit().submit_response(self.SUBMISSION)
        self.assertTrue(self.submission_page.has_submitted)

        self.staff_area_page.visit()

        # Click on staff tools and search for the user.
        self.staff_area_page.show_learner(username)
        self.staff_area_page.expand_learner_report_sections()

        self._check_a11y(self.staff_area_page)

    def test_staff_grade(self):
        """
        Check the accessibility of the Staff Grade section, as shown to the learner.
        """
        self.submission_page.visit().submit_response(self.SUBMISSION)
        self.assertTrue(self.submission_page.has_submitted)

        self.do_staff_assessment(options_selected=self.STAFF_OVERRIDE_OPTIONS_SELECTED)

        # Refresh the page, then verify accessibility of the Staff Grade section (marked Complete).
        self.browser.refresh()
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS)

        self._check_a11y(self.staff_asmnt_page)


class FullWorkflowA11yTest(OpenAssessmentA11yTest, FullWorkflowMixin):
    """
    Test accessibility at the end of a "full workflow" problem. In particular,
    this verifies the accessibility of the "Your Grade" section and the related
    sections in staff tools when all assessment steps have been completed.
    """

    def setUp(self):
        super(FullWorkflowA11yTest, self).setUp('full_workflow_staff_override', staff=True)
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)

    def test_training_peer_self_staff_override(self):
        """
        """
        # Create a learner with submission, training, and self assessment completed.
        learner, learner_email = self.do_submission_training_self_assessment()

        # Now create a second learner so that learner 1 has someone to assess.
        # The second learner does all the steps as well (submission, training, self assessment, peer assessment).
        self.do_submission_training_self_assessment()
        self.do_peer_assessment(options=self.PEER_ASSESSMENT)

        # Go back to the first learner to complete her workflow.
        self.login_user(learner, learner_email)

        # Learner 1 does peer assessment of learner 2 to complete workflow.
        self.do_peer_assessment(options=self.SUBMITTED_ASSESSMENT)

        # Continue grading by other students if necessary to ensure learner has a peer grade.
        self.verify_submission_has_peer_grade(learner, learner_email)

        # At this point, the learner sees the peer assessment score (0). Verify the accessibility
        # of the "your grade" section.
        self.assertEqual(self.PEER_ASSESSMENT_SCORE, self.grade_page.wait_for_page().score)
        self._check_a11y(self.grade_page)

        # Now do a staff override, changing the score (to 1).
        self.do_staff_override(learner)

        # Refresh and check the accessibility of "your grade" section again.
        self.browser.refresh()
        self.assertEqual(self.STAFF_OVERRIDE_SCORE, self.grade_page.wait_for_page().score)
        self._check_a11y(self.grade_page)

        # Also verify the accessibility of the complete staff area information.
        self.staff_area_page.visit().show_learner(learner)
        self.staff_area_page.expand_learner_report_sections()
        self._check_a11y(self.staff_area_page)


class FullWorkflowRequiredA11yTest(OpenAssessmentA11yTest, FullWorkflowMixin):
    """
    Test accessibility when both staff override and full staff grading rubrics have rendered.
    """

    def setUp(self):
        super(FullWorkflowRequiredA11yTest, self).setUp('full_workflow_staff_required', staff=True)
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)

    def test_multiple_rubrics(self):
        """
        Test accessibility when both the staff override and the full staff grading
        rubric forms have been opened.
        """
        # Create a learner with submission, training, and self assessment completed.
        learner = self.do_train_self_peer(False)

        # Open up the full staff grading form
        self.staff_area_page.visit()
        self.staff_area_page.click_staff_toolbar_button("staff-grading")
        self.staff_area_page.expand_staff_grading_section()

        # Open up the override form
        self.staff_area_page.show_learner(learner)
        self.staff_area_page.expand_learner_report_sections()

        self._check_a11y(self.staff_area_page)


class MultipleOpenAssessmentA11yTest(OpenAssessmentA11yTest, MultipleOpenAssessmentMixin):
    """
    Test accessibility when we have a unit containing multiple ORA blocks.
    """

    def setUp(self):
        super(MultipleOpenAssessmentA11yTest, self).setUp('multiple_ora', staff=True)
        # Staff area page is not present in OpenAssessmentTest base class, so we are adding it here.
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)
        self.multiple_assessment_page = MultipleAssessmentPage(self.browser, self.problem_loc)

    def test_multiple_ora_complete_flow(self):
        """
        Test accessibility when we have a unit containing multiple ORA blocks.
        """
        # Assess entire problem page for potential duplicate IDs among ORA xblocks
        self.multiple_assessment_page.a11y_audit.config.set_scope(['#main'])
        self.multiple_assessment_page.a11y_audit.config.set_rules({
            "apply": [
                "duplicate-id"
            ]
        })
        self.multiple_assessment_page.a11y_audit.check_for_accessibility_errors()

        # Each problem has vertical index assigned and has a `vert-{vertical_index}` top level class.
        # That also means that all pages are being differentiated by their vertical index number that is assigned to
        # each problem type. We are passing vertical index number and setting it by `self.setup_vertical_index` method
        # so as to move to a different problem.

        # Assess first ORA problem, pass the vertical index number
        self.assess_component(0)
        self._check_a11y(self.peer_asmnt_page)

        # Assess second ORA problem, pass the vertical index number
        self.assess_component(1)
        self._check_a11y(self.peer_asmnt_page)


class FileUploadA11yTest(OpenAssessmentA11yTest):

    def setUp(self):
        super(FileUploadA11yTest, self).setUp('file_upload')

    def test_file_upload(self):
        self.auto_auth_page.visit()
        self.submission_page.visit()
        self._check_a11y(self.submission_page)

    def _configure_a11y_audit_config(self, page):
        super(FileUploadA11yTest, self)._configure_a11y_audit_config(page)
        page.a11y_audit.config.set_rules({
            "ignore": [
                "list",  # TODO: TNL-5900
            ]
        })


if __name__ == "__main__":

    # Configure the screenshot directory
    if 'SCREENSHOT_DIR' not in os.environ:
        tests_dir = os.path.dirname(__file__)
        os.environ['SCREENSHOT_DIR'] = os.path.join(tests_dir, 'screenshots')

    unittest.main()
