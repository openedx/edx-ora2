"""
UI-level acceptance tests for OpenAssessment.
"""
import ddt
import os
import unittest
import time
from functools import wraps

from nose.plugins.attrib import attr
from bok_choy.web_app_test import WebAppTest
from bok_choy.promise import BrokenPromise
from auto_auth import AutoAuthPage
from pages import (
    SubmissionPage, AssessmentPage, GradePage, StaffAreaPage
)


def retry(tries=4, delay=3, backoff=2):
    """
    Retry decorator with exponential backoff.

    Kwargs:
        tries (int): Maximum number of times to execute the function.
        delay (int): Starting delay between retries.
        backoff (int): Multiplier applied to the delay.

    """
    def _decorator(func):
        @wraps(func)
        def _inner(*args, **kwargs):
            _delay = delay
            for attempt_num in range(tries):
                try:
                    return func(*args, **kwargs)
                except (BrokenPromise, AssertionError) as ex:
                    if attempt_num >= (tries - 1):
                        raise ex
                    else:
                        print "Test failed with {err}, retrying in {sec} seconds...".format(err=ex, sec=_delay)
                        time.sleep(_delay)
                        _delay *= backoff
        return _inner
    return _decorator


class OpenAssessmentTest(WebAppTest):
    """
    UI-level acceptance tests for Open Assessment.
    """
    TEST_COURSE_ID = "course-v1:edx+ORA203+course"

    PROBLEM_LOCATIONS = {
        'self_only':
            u'courses/{test_course_id}/courseware/'
            u'a4dfec19cf9b4a6fb5b18be6ccd9cecc/338a4affb58a45459629e0566291381e/'.format(test_course_id=TEST_COURSE_ID),
        'peer_only':
            u'courses/{test_course_id}/courseware/'
            u'a4dfec19cf9b4a6fb5b18be6ccd9cecc/417e47b2663a4f79b62dba20b21628c8/'.format(test_course_id=TEST_COURSE_ID),
        'student_training':
            u'courses/{test_course_id}/courseware/'
            u'676026889c884ac1827688750871c825/5663e9b038434636977a4226d668fe02/'.format(test_course_id=TEST_COURSE_ID),
        'file_upload':
            u'courses/{test_course_id}/courseware/'
            u'57a3f9d51d424f6cb922f0d69cba868d/bb563abc989340d8806920902f267ca3/'.format(test_course_id=TEST_COURSE_ID),
    }

    SUBMISSION = u"This is a test submission."
    LATEX_SUBMISSION = u"[mathjaxinline]( \int_{0}^{1}xdx \)[/mathjaxinline]"
    OPTIONS_SELECTED = [1, 2]
    STAFF_OVERRIDE_OPTIONS_SELECTED = [0, 1]
    EXPECTED_SCORE = 6

    def setUp(self, problem_type, staff=False):
        """
        Configure page objects to test Open Assessment.

        Args:
            problem_type (str): The type of problem being tested,
              used to choose which part of the course to load.
            staff (bool): If True, runs the test with a staff user (defaults to False).

        """
        super(OpenAssessmentTest, self).setUp()

        self.problem_loc = self.PROBLEM_LOCATIONS[problem_type]
        self.auto_auth_page = AutoAuthPage(self.browser, course_id=self.TEST_COURSE_ID, staff=staff)
        self.submission_page = SubmissionPage(self.browser, self.problem_loc)
        self.self_asmnt_page = AssessmentPage('self-assessment', self.browser, self.problem_loc)
        self.peer_asmnt_page = AssessmentPage('peer-assessment', self.browser, self.problem_loc)
        self.student_training_page = AssessmentPage('student-training', self.browser, self.problem_loc)
        self.staff_asmnt_page = AssessmentPage('staff-assessment', self.browser, self.problem_loc)
        self.grade_page = GradePage(self.browser, self.problem_loc)

    def do_self_assessment(self):
        """
        Submits a self assessment, verifies the grade, and returns the username of the student
        for which the self assessment was submitted.
        """
        self.auto_auth_page.visit()
        username = self.auto_auth_page.get_username()
        self.submission_page.visit().submit_response(self.SUBMISSION)
        self.assertTrue(self.submission_page.has_submitted)

        # Submit a self-assessment
        self.self_asmnt_page.wait_for_page().wait_for_response()
        self.assertIn(self.SUBMISSION, self.self_asmnt_page.response_text)
        self.self_asmnt_page.assess("self", self.OPTIONS_SELECTED).wait_for_complete()
        self.assertTrue(self.self_asmnt_page.is_complete)

        # Verify the grade
        self.assertEqual(self.grade_page.wait_for_page().score, self.EXPECTED_SCORE)

        return username

    def _verify_staff_grade_section(self, expected_status, expected_message_title):
        self.staff_asmnt_page.wait_for_page()
        self.assertEqual("Staff Grade", self.staff_asmnt_page.label)
        self.staff_asmnt_page.verify_status_value(expected_status)
        self.assertEqual(expected_message_title, self.staff_asmnt_page.message_title)


class SelfAssessmentTest(OpenAssessmentTest):
    """
    Test the self-assessment flow.
    """

    def setUp(self):
        super(SelfAssessmentTest, self).setUp('self_only')

    @retry()
    @attr('acceptance')
    def test_self_assessment(self):
        # Submit a response
        self.do_self_assessment()

        # Check browser scrolled back to top of assessment
        self.assertTrue(self.self_asmnt_page.is_on_top)

    @retry()
    @attr('acceptance')
    def test_latex(self):
        self.auto_auth_page.visit()
        self.submission_page.visit()
        # 'Preview in Latex' button should be disabled at the page load
        self.assertTrue(self.submission_page.latex_preview_button_is_disabled)

        # Fill latex expression, & Verify if 'Preview in Latex is enabled'
        self.submission_page.visit().fill_latex(self.LATEX_SUBMISSION)
        self.assertFalse(self.submission_page.latex_preview_button_is_disabled)

        # Click 'Preview in Latex' button & Verify if it was rendered
        self.submission_page.preview_latex()


class PeerAssessmentTest(OpenAssessmentTest):
    """
    Test the peer-assessment flow.

    It's complicated to guarantee that a student will both give and
    receive enough assessments to receive a grade, so we stop
    once we've given one peer assessment.
    """

    def setUp(self):
        super(PeerAssessmentTest, self).setUp('peer_only')

    @retry()
    @attr('acceptance')
    def test_peer_assessment(self):
        # Create a submission for the first student, so there's
        # at least one submission to assess.
        self.auto_auth_page.visit()
        self.submission_page.visit().submit_response(self.SUBMISSION)

        # Create a submission for the second student
        self.auto_auth_page.visit()
        self.submission_page.visit().submit_response(self.SUBMISSION)

        # Assess the submission (there should be at least one available)
        self.peer_asmnt_page.wait_for_page().wait_for_response().assess("peer", self.OPTIONS_SELECTED)

        # Check that the status indicates we've assessed one submission
        try:
            self.peer_asmnt_page.wait_for_num_completed(1)
        except BrokenPromise:
            self.fail("Did not complete at least one peer assessment.")


class PeerAssessmentTestStaffOverride(OpenAssessmentTest):
    """
    Test setting a staff override on a problem which requires peer assessment.
    """

    def setUp(self):
        super(PeerAssessmentTestStaffOverride, self).setUp('peer_only', staff=True)
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)

    @retry()
    @attr('acceptance')
    def test_staff_override(self):
        """
        Scenario: staff can override a learner's grade

        Given I am viewing a new peer assessment problem as a learner
        And if I create a response to the problem
        Then there is no Staff Grade section present
        And if a staff member creates a grade override
        Then when I refresh the page, I see that a staff override exists
        And the message says that I must complete my steps to view the grade
        And if I submit required peer assessments
        Then the Staff Grade section is marked complete with no message
        And I can see my final grade, even though no peers have assessed me
        """
        # Create two students with a submission each so that there are 2 submissions to assess.
        for _ in range(0, 2):
            self.auto_auth_page.visit()
            self.submission_page.visit().submit_response(self.SUBMISSION)

        # Create a submission for the third student (used for the remainder of the test).
        self.auto_auth_page.visit()
        username = self.auto_auth_page.get_username()
        self.submission_page.visit().submit_response(self.SUBMISSION)
        # Staff Grade field should not be visible yet.
        self.assertFalse(self.staff_asmnt_page.is_browser_on_page())

        # Submit a staff override.
        self.staff_area_page.visit()
        self.staff_area_page.show_learner(username)
        self.staff_area_page.expand_learner_report_sections()
        self.staff_area_page.assess("staff", self.STAFF_OVERRIDE_OPTIONS_SELECTED)

        # Refresh the page so the learner sees the Staff Grade section.
        self.browser.refresh()
        self._verify_staff_grade_section("COMPLETE", "YOU MUST COMPLETE THE STEPS ABOVE TO VIEW YOUR GRADE")

        # Verify no final grade yet.
        self.assertIsNone(self.grade_page.wait_for_page().score)

        # Assess two submissions
        for count_assessed in range(1, 3):
            self.peer_asmnt_page.wait_for_page().wait_for_response().assess("peer", self.OPTIONS_SELECTED)
            self.peer_asmnt_page.wait_for_num_completed(count_assessed)

        # Staff grade section is now marked complete, even though no students have submitted
        # assessments for this particular student (no longer required since staff grade exists).
        self._verify_staff_grade_section("COMPLETE", None)

        # Verify the staff override grade
        self.assertEqual(self.grade_page.wait_for_page().score, 1)


class StudentTrainingTest(OpenAssessmentTest):
    """
    Test student training (the "learning to assess" step).
    """

    # Select options that are correct so we can complete the flow.
    STUDENT_TRAINING_OPTIONS = [
        [1, 2],
        [0, 2]
    ]

    def setUp(self):
        super(StudentTrainingTest, self).setUp('student_training')

    @retry()
    @attr('acceptance')
    def test_student_training(self):
        # Create a submission so we can get to student training
        self.auto_auth_page.visit()
        self.submission_page.visit().submit_response(self.SUBMISSION)

        # Complete two training examples, satisfying the requirements
        for example_num, options_selected in enumerate(self.STUDENT_TRAINING_OPTIONS):
            try:
                self.student_training_page.wait_for_num_completed(example_num)
            except BrokenPromise:
                msg = "Did not complete at least {num} student training example(s).".format(num=example_num)
                self.fail(msg)

            self.student_training_page.wait_for_page().wait_for_response().assess("training", options_selected)

            # Check browser scrolled back to top only on first example

            # TODO: Disabling assertion. Scrolling is showing inconsistent behavior.
            # self.assertEqual(self.self_asmnt_page.is_on_top, example_num == 0)

        # Check that we've completed student training
        try:
            self.student_training_page.wait_for_complete()
        except BrokenPromise:
            self.fail("Student training was not marked complete.")


@ddt.ddt
class StaffAreaTest(OpenAssessmentTest):
    """
    Test the staff area.

    This is testing a problem with "self assessment only".
    """

    def setUp(self):
        super(StaffAreaTest, self).setUp('self_only', staff=True)
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)

    @retry()
    @attr('acceptance')
    def test_staff_area_buttons(self):
        """
        Scenario: the staff area buttons should behave correctly

        Given I am viewing the staff area of an ORA problem
        Then none of the buttons should be active
        When I click the "Manage Individual Learners" button
        Then only the "Manage Individual Learners" button should be active
        When I click the "View Assignment Statistics" button
        Then only the "View Assignment Statistics" button should be active
        When I click the "Staff Info" button again
        Then none of the buttons should be active
        """
        self.auto_auth_page.visit()
        self.staff_area_page.visit()
        self.assertEqual(self.staff_area_page.selected_button_names, [])
        self.staff_area_page.click_staff_toolbar_button("staff-tools")
        self.assertEqual(self.staff_area_page.selected_button_names, ["MANAGE INDIVIDUAL LEARNERS"])
        self.staff_area_page.click_staff_toolbar_button("staff-info")
        self.assertEqual(self.staff_area_page.selected_button_names, ["VIEW ASSIGNMENT STATISTICS"])
        self.staff_area_page.click_staff_toolbar_button("staff-info")
        self.assertEqual(self.staff_area_page.selected_button_names, [])

    @retry()
    @attr('acceptance')
    @ddt.data(
        ("staff-tools", "MANAGE INDIVIDUAL LEARNERS"),
        ("staff-info", "VIEW ASSIGNMENT STATISTICS"),
    )
    @ddt.unpack
    def test_staff_area_panel(self, panel_name, button_label):
        """
        Scenario: the staff area panels should be shown correctly

        Given I am viewing the staff area of an ORA problem
        Then none of the panels should be shown
        When I click a staff button
        Then only the related panel should be shown
        When I click the close button in the panel
        Then none of the panels should be shown
        """
        self.auto_auth_page.visit()
        self.staff_area_page.visit()

        # Verify that there is no selected panel initially
        self.assertEqual(self.staff_area_page.selected_button_names, [])
        self.assertEqual(self.staff_area_page.visible_staff_panels, [])

        # Click on the button and verify that the panel has opened
        self.staff_area_page.click_staff_toolbar_button(panel_name)
        self.assertEqual(self.staff_area_page.selected_button_names, [button_label])
        self.assertIn(
            u'openassessment__{button_name}'.format(button_name=panel_name),
            self.staff_area_page.visible_staff_panels[0]
        )

        # Click 'Close' and verify that the panel has been closed
        self.staff_area_page.click_staff_panel_close_button(panel_name)
        self.assertEqual(self.staff_area_page.selected_button_names, [])
        self.assertEqual(self.staff_area_page.visible_staff_panels, [])

    @retry()
    @attr('acceptance')
    def test_student_info(self):
        """
        Scenario: staff tools shows learner response information

        Given I am viewing the staff area of an ORA problem
        When I search for a learner in staff tools
        And the learner has submitted a response to an ORA problem with self-assessment
        Then I see the correct learner information sections
        """
        username = self.do_self_assessment()

        self.staff_area_page.visit()

        # Click on staff tools and search for user
        self.staff_area_page.show_learner(username)
        self.assertEqual(
            [u"Learner's Response", u"Learner's Self Assessment", u"Learner's Final Grade",
             u"Submit Assessment Grade Override", u"Remove Submission From Peer Grading"],
            self.staff_area_page.learner_report_sections
        )

        self.assertNotIn('A response was not found for this learner', self.staff_area_page.learner_report_text)

    @retry()
    @attr('acceptance')
    def test_student_info_no_submission(self):
        """
        Scenario: staff tools indicates if no submission has been received for a given learner

        Given I am viewing the staff area of an ORA problem
        When I search for a learner in staff tools
        And the learner has not submitted a response to the ORA problem
        Then I see a message indicating that the learner has not submitted a response
        And there are no student information sections displayed
        """
        self.auto_auth_page.visit()
        self.staff_area_page.visit()

        # Click on staff tools and search for user
        self.staff_area_page.show_learner('no-submission-learner')
        self.staff_area_page.verify_learner_report_text('A response was not found for this learner.')

    @retry()
    @attr('acceptance')
    def test_staff_override(self):
        """
        Scenario: staff can override a learner's grade

        Given I am viewing the staff area of an ORA problem
        When I search for a learner in staff tools
        And the learner has submitted a response to an ORA problem with self-assessment
        Then I can submit a staff override of the self-assessment
        And I see the updated final score
        """
        username = self.do_self_assessment()

        self.staff_area_page.visit()

        # Click on staff tools and search for user
        self.staff_area_page.show_learner(username)

        # Check the learner's current score.
        self.staff_area_page.expand_learner_report_sections()
        self.staff_area_page.verify_learner_final_score("Final grade: 6 out of 8")

        # Do staff override and wait for final score to change.
        self.staff_area_page.assess("staff", self.STAFF_OVERRIDE_OPTIONS_SELECTED)

        # Verify that the new student score is different from the original one.
        # Unfortunately there is no indication presently that this was a staff override.
        self.staff_area_page.verify_learner_final_score("Final grade: 1 out of 8")

    @retry()
    @attr('acceptance')
    def test_cancel_submission(self):
        """
        Scenario: staff can cancel a learner's submission

        Given I am viewing the staff area of an ORA problem
        When I search for a learner in staff tools
        And the learner has submitted a response to an ORA problem with self-assessment
        Then I can cancel the learner's submission
        And I see an updated message indicating that the submission has been canceled.
        """
        username = self.do_self_assessment()

        self.staff_area_page.visit()

        # Click on staff tools and search for user
        self.staff_area_page.show_learner(username)

        # Check the learner's current score.
        self.staff_area_page.expand_learner_report_sections()
        self.staff_area_page.verify_learner_final_score("Final grade: 6 out of 8")

        # Cancel the student submission
        self.staff_area_page.cancel_submission()

        self.staff_area_page.verify_learner_final_score(
            "The learner's submission has been removed from peer assessment. "
            "The learner receives a grade of zero unless you delete the learner's state for the "
            "problem to allow them to resubmit a response."
        )

        # Verify that the staff override and submission removal sections are now gone.
        self.assertEqual(
            [u"Learner's Response", u"Learner's Self Assessment", u"Learner's Final Grade"],
            self.staff_area_page.learner_report_sections
        )

        # Verify that the Learner Response has been replaced with a message about the removal
        self.staff_area_page.expand_learner_report_sections()
        self.assertIn("Learner submission removed", self.staff_area_page.learner_response)

    @retry()
    @attr('acceptance')
    def test_staff_grade_override(self):
        """
        Scenario: the staff grade section displays correctly

        Given I am viewing a new self assessment problem as a learner
        Then there is no Staff Grade section present
        And if I create a response to the problem
        Then there is no Staff Grade section present
        And if a staff member creates a grade override
        Then when I refresh the page, I see that a staff override exists
        And the message says that I must complete my steps to view the grade
        And if I submit my self-assessment
        Then the Staff Grade section is marked complete with no message
        And I can see my final grade
        """
        # View the problem-- no Staff Grade area.
        self.auto_auth_page.visit()
        username = self.auto_auth_page.get_username()
        self.submission_page.visit()
        self.assertFalse(self.staff_asmnt_page.is_browser_on_page())

        self.submission_page.submit_response(self.SUBMISSION)
        self.assertTrue(self.submission_page.has_submitted)
        self.assertFalse(self.staff_asmnt_page.is_browser_on_page())

        # Submit a staff override
        self.staff_area_page.visit()
        self.staff_area_page.show_learner(username)
        self.staff_area_page.expand_learner_report_sections()
        self.staff_area_page.assess("staff", self.STAFF_OVERRIDE_OPTIONS_SELECTED)

        # Refresh the page so the learner sees the Staff Grade section.
        self.browser.refresh()
        self._verify_staff_grade_section("COMPLETE", "YOU MUST COMPLETE THE STEPS ABOVE TO VIEW YOUR GRADE")

        # Verify no final grade yet.
        self.assertIsNone(self.grade_page.wait_for_page().score)

        # Learner does required self-assessment
        self.self_asmnt_page.wait_for_page().wait_for_response()
        self.assertIn(self.SUBMISSION, self.self_asmnt_page.response_text)
        self.self_asmnt_page.assess("self", self.OPTIONS_SELECTED).wait_for_complete()
        self.assertTrue(self.self_asmnt_page.is_complete)

        self._verify_staff_grade_section("COMPLETE", None)

        # Verify the staff override grade
        self.assertEqual(self.grade_page.wait_for_page().score, 1)

    @retry()
    @attr('acceptance')
    def test_staff_grade_override_cancelled(self):
        """
        Scenario: the staff grade section displays cancelled when the submission is cancelled

        Given I have created a response and a self-assessment
        And a staff member creates a grade override and then cancels my submission
        Then when I refresh the page, the Staff Grade section is marked cancelled
        And I have no final grade
        """
        username = self.do_self_assessment()

        # Submit a staff override
        self.staff_area_page.visit()
        self.staff_area_page.show_learner(username)
        self.staff_area_page.expand_learner_report_sections()

        # Do staff override.
        self.staff_area_page.assess("staff", self.STAFF_OVERRIDE_OPTIONS_SELECTED)
        # And cancel the submission
        self.staff_area_page.expand_learner_report_sections()
        self.staff_area_page.cancel_submission()

        # Refresh the page so the learner sees the Staff Grade section shows the submission has been cancelled.
        self.browser.refresh()
        self._verify_staff_grade_section("CANCELLED", None)
        self.assertIsNone(self.grade_page.wait_for_page().score)


class FileUploadTest(OpenAssessmentTest):
    """
    Test file upload
    """

    def setUp(self):
        super(FileUploadTest, self).setUp('file_upload')

    @retry()
    @attr('acceptance')
    def test_file_upload(self):
        self.auto_auth_page.visit()
        # trying to upload a unacceptable file
        self.submission_page.visit()
        # hide django debug tool, otherwise, it will cover the button on the right side,
        # which will cause the button non-clickable and tests to fail
        self.submission_page.hide_django_debug_tool()
        self.submission_page.select_file(os.path.dirname(os.path.realpath(__file__)) + '/__init__.py')
        self.assertTrue(self.submission_page.has_file_error)

        # trying to upload a acceptable file
        self.submission_page.visit().select_file(os.path.dirname(os.path.realpath(__file__)) + '/README.rst')
        self.assertFalse(self.submission_page.has_file_error)
        self.submission_page.upload_file()
        self.assertTrue(self.submission_page.has_file_uploaded)


if __name__ == "__main__":

    # Configure the screenshot directory
    if 'SCREENSHOT_DIR' not in os.environ:
        tests_dir = os.path.dirname(__file__)
        os.environ['SCREENSHOT_DIR'] = os.path.join(tests_dir, 'screenshots')

    unittest.main()
