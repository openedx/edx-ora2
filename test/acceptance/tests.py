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
from bok_choy.promise import BrokenPromise, EmptyPromise
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
                        raise
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
        'staff_only':
            u'courses/{test_course_id}/courseware/'
            u'61944efb38a349edb140c762c7419b50/415c3ee1b7d04b58a1887a6fe82b31d6/'.format(test_course_id=TEST_COURSE_ID),
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
        'full_workflow_staff_override':
            u'courses/{test_course_id}/courseware/'
            u'676026889c884ac1827688750871c825/181ea9ff144c4766be44eb8cb360e34f/'.format(test_course_id=TEST_COURSE_ID),
        'full_workflow_staff_required':
            u'courses/{test_course_id}/courseware/'
            u'8d9584d242b44343bc270ea5ef04ab03/0b0dcc728abe45138c650732af178afb/'.format(test_course_id=TEST_COURSE_ID),
    }

    SUBMISSION = u"This is a test submission."
    LATEX_SUBMISSION = u"[mathjaxinline]( \int_{0}^{1}xdx \)[/mathjaxinline]"
    OPTIONS_SELECTED = [1, 2]
    STAFF_OVERRIDE_OPTIONS_SELECTED = [0, 1]
    STAFF_OVERRIDE_SCORE = 1
    STAFF_GRADE_EXISTS = "COMPLETE"
    STAFF_OVERRIDE_LEARNER_STEPS_NOT_COMPLETE = "YOU MUST COMPLETE THE STEPS ABOVE TO VIEW YOUR GRADE"
    STAFF_AREA_SCORE = "Final grade: {} out of 8"
    STAFF_OVERRIDE_STAFF_AREA_NOT_COMPLETE = "The problem has not been completed."
    EXPECTED_SCORE = 6
    STUDENT_TRAINING_OPTIONS = [
        [1, 2],
        [0, 2]
    ]

    LEARNER_EMAIL = "learner@foo.com"
    LEARNER_PASSWORD = "learner_password"

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

    def login_user(self, learner, email=LEARNER_EMAIL, password=LEARNER_PASSWORD):
        """
        Logs in an already existing user.

        Args:
            learner (str): the username of the user.
            email (str): email (if not specified, LEARNER_EMAIL is used).
            password (str): password (if not specified, LEARNER_PASSWORD is used).
        """
        auto_auth_page = AutoAuthPage(
            self.browser, email=email, password=password, username=learner,
            course_id=self.TEST_COURSE_ID, staff=True
        )
        auto_auth_page.visit()

    def do_self_assessment(self):
        """
        Creates a user, submits a self assessment, verifies the grade, and returns the username of the
        learner for which the self assessment was submitted.
        """
        self.auto_auth_page.visit()
        username = self.auto_auth_page.get_username()
        self.submission_page.visit().submit_response(self.SUBMISSION)
        self.assertTrue(self.submission_page.has_submitted)

        # Submit a self-assessment
        self.submit_self_assessment(self.OPTIONS_SELECTED)

        # Verify the grade
        self.assertEqual(self.EXPECTED_SCORE, self.grade_page.wait_for_page().score)

        return username

    def submit_self_assessment(self, options=OPTIONS_SELECTED):
        """
        Submit a self assessment for the currently logged in student. Do not verify grade.

        Args:
            options: the options to select for the self assessment
                (will use OPTIONS_SELECTED if not specified)
        """
        self.self_asmnt_page.wait_for_page().wait_for_response()
        self.assertIn(self.SUBMISSION, self.self_asmnt_page.response_text)
        self.self_asmnt_page.assess("self", options).wait_for_complete()
        self.assertTrue(self.self_asmnt_page.is_complete)

    def _verify_staff_grade_section(self, expected_status, expected_message_title):
        """
        Verifies the expected status and message text in the Staff Grade section
        (as shown to the learner).
        """
        self.staff_asmnt_page.wait_for_page()
        self.assertEqual("Staff Grade", self.staff_asmnt_page.label)
        self.staff_asmnt_page.verify_status_value(expected_status)
        self.assertEqual(expected_message_title, self.staff_asmnt_page.message_title)

    def do_training(self):
        """
        Complete two training examples, satisfying the requirements.
        """
        for example_num, options_selected in enumerate(self.STUDENT_TRAINING_OPTIONS):
            if example_num > 0:
                try:
                    self.student_training_page.wait_for_num_completed(example_num)
                except BrokenPromise:
                    msg = "Did not complete at least {num} student training example(s).".format(num=example_num)
                    self.fail(msg)

            self.student_training_page.wait_for_page().wait_for_response().assess("training", options_selected)

        # Check that we've completed student training
        try:
            self.student_training_page.wait_for_complete()
        except BrokenPromise:
            self.fail("Student training was not marked complete.")

    def do_peer_assessment(self, count=1, options=OPTIONS_SELECTED):
        """
        Does the specified number of peer assessments.

        Args:
            count: the number of assessments that must be completed (defaults to 1)
            options: the options to use (defaults to OPTIONS_SELECTED)
        """
        self.peer_asmnt_page.visit()

        for count_assessed in range(1, count + 1):
            self.peer_asmnt_page.wait_for_page().wait_for_response().assess("peer", options)
            self.peer_asmnt_page.wait_for_num_completed(count_assessed)

    def do_staff_override(self, username, final_score=STAFF_AREA_SCORE.format(STAFF_OVERRIDE_SCORE)):
        """
        Complete a staff assessment (grade override).

        Args:
            username: the learner to grade
            final_score: the expected final score as shown in the staff area
                (defaults to the staff override score value)
        """
        self.staff_area_page.visit()
        self.staff_area_page.show_learner(username)
        self.staff_area_page.expand_learner_report_sections()
        self.staff_area_page.staff_assess(self.STAFF_OVERRIDE_OPTIONS_SELECTED, "override")
        self.staff_area_page.verify_learner_final_score(final_score)

    def do_staff_assessment(self, number_to_assess=0, options_selected=OPTIONS_SELECTED):
        """
        Use staff tools to assess available responses.

        Args:
            number_to_assess: the number of submissions to assess. If not provided (or 0),
                will grade all available submissions.
        """
        self.staff_area_page.visit()
        self.staff_area_page.click_staff_toolbar_button("staff-grading")
        # Get the counts before checking out a submission for assessment.
        start_numbers = self.staff_area_page.available_checked_out_numbers
        # Check out a submission.
        self.staff_area_page.expand_staff_grading_section()
        # Checked out number should increase, ungraded decrease.
        ungraded = start_numbers[0]-1
        checked_out = start_numbers[1]+1
        self.staff_area_page.verify_available_checked_out_numbers((ungraded, checked_out))
        assessed = 0
        while number_to_assess == 0 or assessed < number_to_assess:
            continue_after = False if number_to_assess-1 == assessed else ungraded > 0
            self.staff_area_page.staff_assess(options_selected, "full-grade", continue_after)
            assessed += 1
            if not continue_after:
                self.staff_area_page.verify_available_checked_out_numbers((ungraded, checked_out-1))
                break
            else:
                ungraded -=1
                self.staff_area_page.verify_available_checked_out_numbers((ungraded, checked_out))

    def refresh_page(self):
        """
        Helper method that waits for "unsaved changes" warnings to clear before refreshing the page.
        """
        EmptyPromise(
            lambda: self.browser.execute_script("return window.onbeforeunload === null"),
            "Unsubmitted changes exist on page."
        ).fulfill()
        self.browser.refresh()


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


class StaffAssessmentTest(OpenAssessmentTest):
    """
    Test the staff-assessment flow.
    """

    def setUp(self):
        super(StaffAssessmentTest, self).setUp('staff_only', staff=True)

    @retry()
    @attr('acceptance')
    def test_staff_assessment(self):
        # Set up user and navigate to submission page
        self.auto_auth_page.visit()
        username = self.auto_auth_page.get_username()
        self.submission_page.visit()

        # Verify that staff grade step is shown initially
        self._verify_staff_grade_section("NOT AVAILABLE", None)

        # User submits a response
        self.submission_page.submit_response(self.SUBMISSION)
        self.assertTrue(self.submission_page.has_submitted)

        # Verify staff grade section appears as expected
        self._verify_staff_grade_section("NOT AVAILABLE", "WAITING FOR A STAFF GRADE")

        # Perform staff assessment
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)
        self.do_staff_assessment()

        # Verify staff grade section appears as expected
        self.staff_asmnt_page.visit()
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS, None)
        self.assertEqual(self.EXPECTED_SCORE, self.grade_page.wait_for_page().score)

        # Verify that staff scores can be overriden
        self.do_staff_override(username)
        self.refresh_page()
        self.assertEqual(self.STAFF_OVERRIDE_SCORE, self.grade_page.wait_for_page().score)

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
        self.do_peer_assessment()


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
        self.do_staff_override(username, self.STAFF_OVERRIDE_STAFF_AREA_NOT_COMPLETE)

        # Refresh the page so the learner sees the Staff Grade section.
        self.refresh_page()
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS, self.STAFF_OVERRIDE_LEARNER_STEPS_NOT_COMPLETE)

        # Verify no final grade yet.
        self.assertIsNone(self.grade_page.wait_for_page().score)

        # Assess two submissions
        self.do_peer_assessment(count=2)

        # Staff grade section is now marked complete, even though no students have submitted
        # assessments for this particular student (no longer required since staff grade exists).
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS, None)

        # Verify the staff override grade
        self.assertEqual(self.STAFF_OVERRIDE_SCORE, self.grade_page.wait_for_page().score)


class StudentTrainingTest(OpenAssessmentTest):
    """
    Test student training (the "learning to assess" step).
    """
    def setUp(self):
        super(StudentTrainingTest, self).setUp('student_training')

    @retry()
    @attr('acceptance')
    def test_student_training(self):
        # Create a submission so we can get to student training
        self.auto_auth_page.visit()
        self.submission_page.visit().submit_response(self.SUBMISSION)

        self.do_training()


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
        self.staff_area_page.verify_learner_final_score(self.STAFF_AREA_SCORE.format(self.EXPECTED_SCORE))

        # Do staff override and wait for final score to change.
        self.staff_area_page.assess("staff-override", self.STAFF_OVERRIDE_OPTIONS_SELECTED)

        # Verify that the new student score is different from the original one.
        # Unfortunately there is no indication presently that this was a staff override.
        self.staff_area_page.verify_learner_final_score(self.STAFF_AREA_SCORE.format(self.STAFF_OVERRIDE_SCORE))

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
        self.staff_area_page.verify_learner_final_score(self.STAFF_AREA_SCORE.format(self.EXPECTED_SCORE))

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
        self.do_staff_override(username, self.STAFF_OVERRIDE_STAFF_AREA_NOT_COMPLETE)

        # Refresh the page so the learner sees the Staff Grade section.
        self.refresh_page()
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS, self.STAFF_OVERRIDE_LEARNER_STEPS_NOT_COMPLETE)

        # Verify no final grade yet.
        self.assertIsNone(self.grade_page.wait_for_page().score)

        # Verify required staff grading section not available
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)
        self.assertFalse(self.staff_area_page.is_button_visible('staff-grading'))

        # Learner does required self-assessment
        self.self_asmnt_page.wait_for_page().wait_for_response()
        self.assertIn(self.SUBMISSION, self.self_asmnt_page.response_text)
        self.self_asmnt_page.assess("self", self.OPTIONS_SELECTED).wait_for_complete()
        self.assertTrue(self.self_asmnt_page.is_complete)

        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS, None)

        # Verify the staff override grade
        self.assertEqual(self.STAFF_OVERRIDE_SCORE, self.grade_page.wait_for_page().score)

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
        self.do_staff_override(username)

        # And cancel the submission
        self.staff_area_page.expand_learner_report_sections()
        self.staff_area_page.cancel_submission()

        # Refresh the page so the learner sees the Staff Grade section shows the submission has been cancelled.
        self.refresh_page()
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


class FullWorkflowMixin(object):
    """
    Mixin with helper methods and constants for testing a full workflow
    (training, self assessment, peer assessment, staff override).
    """
    PEER_ASSESSMENT = [0, 0]
    STAFF_AREA_PEER_ASSESSMENT = ['Poor', u'', u'0', u'5', u'Poor', u'', u'0', u'3']
    PEER_ASSESSMENT_SCORE = 0
    PEER_ASSESSMENT_STAFF_AREA_SCORE = "Final grade: 0 out of 8"

    SELF_ASSESSMENT = [2, 3]
    STAFF_AREA_SELF_ASSESSMENT = ['Good', u'5', u'5', u'Excellent', u'3', u'3']

    SUBMITTED_ASSESSMENT = [0, 3]
    STAFF_AREA_SUBMITTED = ['Poor', u'', u'0', u'5', u'Excellent', u'', u'3', u'3']

    def do_submission(self, email, password):
        """
        Creates a user and submission.

        Args:
            email (str): email for the new user
            password (str): password for the new user

        Returns:
            str: the username of the newly created user
        """
        auto_auth_page = AutoAuthPage(
            self.browser, email=email, password=password, course_id=self.TEST_COURSE_ID, staff=True
        )
        auto_auth_page.visit()
        username = auto_auth_page.get_username()
        self.submission_page.visit().submit_response(self.SUBMISSION)

        return username

    def do_submission_training_self_assessment(self, email, password):
        """
        Creates a user and then does submission, training, and self assessment.

        Args:
            email (str): email for the new user
            password (str): password for the new user

        Returns:
            str: the username of the newly created user
        """
        username = self.do_submission(email, password)
        self.do_training()
        self.submit_self_assessment(self.SELF_ASSESSMENT)

        return username

    def do_train_self_peer(self, peer_to_grade=True):
        """
        Common functionality for executing training, self, and peer assessment steps.

        Args:
            peer_to_grade: boolean, defaults to True. Set to False to have learner complete their required steps,
                but no peers to submit a grade for learner in return.
        """
        # Create a learner with submission, training, and self assessment completed.
        learner = self.do_submission_training_self_assessment(self.LEARNER_EMAIL, self.LEARNER_PASSWORD)

        # Now create a second learner so that learner 1 has someone to assess.
        # The second learner does all the steps as well (submission, training, self assessment, peer assessment).
        self.do_submission_training_self_assessment("learner2@foo.com", None)
        if peer_to_grade:
            self.do_peer_assessment(options=self.PEER_ASSESSMENT)

        # Go back to the first learner to complete her workflow.
        self.login_user(learner)

        # Learner 1 does peer assessment of learner 2 to complete workflow.
        self.do_peer_assessment(options=self.SUBMITTED_ASSESSMENT)

        # Continue grading by other students if necessary to ensure learner has a peer grade.
        if peer_to_grade:
            self.verify_submission_has_peer_grade(learner)

        return learner

    def verify_staff_area_fields(self, username, peer_assessments, submitted_assessments, self_assessment):
        """
        Verifies the expected entries in the staff area for peer assessments,
        submitted assessments, and self assessment.

        Args:
            username (str): the username of the learner to check
            peer_assessments: the expected fields in the peer assessment section
            submitted_assessments: the expected fields in the submitted assessments section
            self_assessment: the expected fields in the self assessment section
        """
        self.staff_area_page.visit()
        self.staff_area_page.show_learner(username)
        self.staff_area_page.expand_learner_report_sections()
        self.assertEqual(peer_assessments, self.staff_area_page.status_text('peer__assessments'))
        self.assertEqual(submitted_assessments, self.staff_area_page.status_text('submitted__assessments'))
        self.assertEqual(self_assessment, self.staff_area_page.status_text('self__assessment'))

    def verify_submission_has_peer_grade(self, learner, max_attempts=5):
        """
        If learner does not now have a score, it means that "extra" submissions are in the system,
        and more need to be scored. Create additional learners and have them grade until learner has
        a grade (stopping after specified max attempts).

        Args:
            learner: the learner whose grade will be checked
            max_attempts: the maximum number of times an additional peer grading should be done
        """
        def peer_grade_exists():
            self.staff_area_page.visit()
            self.staff_area_page.show_learner(learner)
            return "Peer Assessments for This Learner" in self.staff_area_page.learner_report_sections

        count = 0
        while not peer_grade_exists() and count < max_attempts:
            count += 1
            self.do_submission_training_self_assessment("extra_{}@looping.com".format(count), None)
            self.do_peer_assessment(options=self.PEER_ASSESSMENT)
            self.login_user(learner)

        self.assertTrue(
            peer_grade_exists(),
            "Learner still not graded after {} additional attempts".format(max_attempts)
        )

    def verify_grade_entries(self, expected_entries):
        """
        Verify the grade entries (sources and values) as shown in the
        "Your Grade" section.

        Args:
            expected_entries: array of expected entries, with each entry being an array
               consisting of the data for a particular source. Note that order is important.
        """

        for index, expected_entry in enumerate(expected_entries):
            self.assertEqual(expected_entry[0], self.grade_page.grade_entry(0, index))
            self.assertEqual(expected_entry[1], self.grade_page.grade_entry(1, index))


class FullWorkflowOverrideTest(OpenAssessmentTest, FullWorkflowMixin):
    """
    Tests of complete workflows, combining multiple required steps together.
    """
    def setUp(self):
        super(FullWorkflowOverrideTest, self).setUp("full_workflow_staff_override", staff=True)
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)

    @retry()
    @attr('acceptance')
    def test_staff_override_at_end(self):
        """
        Scenario: complete workflow with staff override at the very end

        Given that I have created a submission, completed training, and done a self assessment
        And a second learner has also created a submission, training, and self assessment
        Then I can assess a learner
        And when another learner assesses me
        Then I see my score based on the peer assessment
        And when a staff member overrides the score
        Then I see the staff override score
        And all fields in the staff area tool are correct
        """
        learner = self.do_train_self_peer()

        # At this point, the learner sees the peer assessment score (0).
        self.assertEqual(self.PEER_ASSESSMENT_SCORE, self.grade_page.wait_for_page().score)
        self.verify_staff_area_fields(
            learner, self.STAFF_AREA_PEER_ASSESSMENT, self.STAFF_AREA_SUBMITTED, self.STAFF_AREA_SELF_ASSESSMENT
        )
        self.staff_area_page.verify_learner_final_score(self.PEER_ASSESSMENT_STAFF_AREA_SCORE)

        self.verify_grade_entries([
            [(u"PEER MEDIAN GRADE - 0 POINTS", u"Poor"), (u"PEER MEDIAN GRADE - 0 POINTS", u"Poor")],
            [(u"YOUR SELF ASSESSMENT", u"Good"), (u"YOUR SELF ASSESSMENT", u"Excellent")]
        ])

        # Now do a staff override, changing the score (to 1).
        self.do_staff_override(learner)

        self.refresh_page()
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS, None)
        self.assertEqual(self.STAFF_OVERRIDE_SCORE, self.grade_page.wait_for_page().score)
        self.verify_staff_area_fields(
            learner, self.STAFF_AREA_PEER_ASSESSMENT, self.STAFF_AREA_SUBMITTED, self.STAFF_AREA_SELF_ASSESSMENT
        )
        self.staff_area_page.verify_learner_final_score(self.STAFF_AREA_SCORE.format(self.STAFF_OVERRIDE_SCORE))

        self.verify_grade_entries([
            [(u"STAFF GRADE - 0 POINTS", u"Poor"), (u"STAFF GRADE - 1 POINT", u"Fair")],
            [(u"PEER MEDIAN GRADE", u"Poor"), (u"PEER MEDIAN GRADE", u"Poor")],
            [(u"YOUR SELF ASSESSMENT", u"Good"), (u"YOUR SELF ASSESSMENT", u"Excellent")]
        ])

    @retry()
    @attr('acceptance')
    def test_staff_override_at_beginning(self):
        """
        Scenario: complete workflow with staff override at the very beginning

        Given that I have created a submission
        Then I see no score yet
        And when a staff member creates a grade override
        Then I see that an override exists, but I cannot see the score
        And when a second learner creates a submission
        Then I can complete my required steps (training, self assessment, peer assesssment)
        And I see my staff override score
        And all fields in the staff area tool are correct
        """
        # Create only the initial submission before doing the staff override.
        learner = self.do_submission(self.LEARNER_EMAIL, self.LEARNER_PASSWORD)

        # Verify no grade present (and no staff grade section), no assessment information in staff area.
        self.assertIsNone(self.grade_page.wait_for_page().score)
        self.assertFalse(self.staff_asmnt_page.is_browser_on_page())
        self.verify_staff_area_fields(learner, [], [], [])
        self.staff_area_page.verify_learner_final_score(self.STAFF_OVERRIDE_STAFF_AREA_NOT_COMPLETE)

        # Do staff override-- score still not shown due to steps not being complete.
        self.do_staff_override(learner, self.STAFF_OVERRIDE_STAFF_AREA_NOT_COMPLETE)

        # Refresh the page so the learner sees the Staff Grade section.
        self.refresh_page()
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS, self.STAFF_OVERRIDE_LEARNER_STEPS_NOT_COMPLETE)

        # Now create a second learner so that "learner" has someone to assess.
        self.do_submission("learner2@foo.com", None)

        # Go back to the original learner to complete her workflow and view score.
        self.login_user(learner)

        # Do training exercise and self assessment
        self.student_training_page.visit()
        self.do_training()
        self.submit_self_assessment(self.SELF_ASSESSMENT)

        # Verify staff grade still not available, as learner has not done peer assessment.
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS, self.STAFF_OVERRIDE_LEARNER_STEPS_NOT_COMPLETE)
        self.assertIsNone(self.grade_page.wait_for_page().score)
        self.verify_staff_area_fields(learner, [], [], self.STAFF_AREA_SELF_ASSESSMENT)
        self.staff_area_page.verify_learner_final_score(self.STAFF_OVERRIDE_STAFF_AREA_NOT_COMPLETE)

        # Now do the final required step-- peer grading.
        self.do_peer_assessment(options=self.SUBMITTED_ASSESSMENT)

        # Grade is now visible to the learner (even though no student has graded the learner).
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS, None)
        self.assertEqual(self.STAFF_OVERRIDE_SCORE, self.grade_page.wait_for_page().score)
        self.verify_staff_area_fields(learner, [], self.STAFF_AREA_SUBMITTED, self.STAFF_AREA_SELF_ASSESSMENT)
        self.staff_area_page.verify_learner_final_score(self.STAFF_AREA_SCORE.format(self.STAFF_OVERRIDE_SCORE))

        self.verify_grade_entries([
            [(u"STAFF GRADE - 0 POINTS", u"Poor"), (u"STAFF GRADE - 1 POINT", u"Fair")],
            [(u"YOUR SELF ASSESSMENT", u"Good"), (u"YOUR SELF ASSESSMENT", u"Excellent")]
        ])


@ddt.ddt
class FullWorkflowRequiredTest(OpenAssessmentTest, FullWorkflowMixin):
    """
    Tests of complete workflows, combining multiple required steps together.
    """
    def setUp(self):
        super(FullWorkflowRequiredTest, self).setUp("full_workflow_staff_required", staff=True)
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)

    @retry()
    @attr('acceptance')
    @ddt.data(True, False)
    def test_train_self_peer_staff(self, peer_grades_me):
        """
        Scenario: complete workflow that included staff required step.

        Given that I have created a submission, completed training, and done a self assessment
        And a second learner has also created a submission, training, and self assessment
        Then I can assess a learner
        And when another learner assesses me
        And a staff member submits a score
        Then I see the staff score
        And all fields in the staff area tool are correct
        """
        # Using ddt booleans to confirm behavior independent of whether I receive a peer score or not
        self.do_train_self_peer(peer_grades_me)

        # Ensure grade is not present, since staff assessment has not been made
        self.assertIsNone(self.grade_page.wait_for_page().score)

        # Now do a staff assessment.
        self.do_staff_assessment(options_selected=self.STAFF_OVERRIDE_OPTIONS_SELECTED)

        # As an add-on, let's make sure that both submissions (the learner's, and the additional one created
        # in do_train_self_peer() above) were assessed using staff-grading's "submit and keep going"
        self.assertEqual(0, self.staff_area_page.available_checked_out_numbers[0])

        # At this point, the learner sees the score (1).
        self.refresh_page()
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS, None)
        self.assertEqual(self.STAFF_OVERRIDE_SCORE, self.grade_page.wait_for_page().score)

        if peer_grades_me:
            self.verify_grade_entries([
                [(u"STAFF GRADE - 0 POINTS", u"Poor"), (u"STAFF GRADE - 1 POINT", u"Fair")],
                [(u"PEER MEDIAN GRADE", u"Poor"), (u"PEER MEDIAN GRADE", u"Poor")],
                [(u"YOUR SELF ASSESSMENT", u"Good"), (u"YOUR SELF ASSESSMENT", u"Excellent")],
            ])
        else:
            self.verify_grade_entries([
                [(u"STAFF GRADE - 0 POINTS", u"Poor"), (u"STAFF GRADE - 1 POINT", u"Fair")],
                [(u"YOUR SELF ASSESSMENT", u"Good"), (u"YOUR SELF ASSESSMENT", u"Excellent")],
            ])


if __name__ == "__main__":

    # Configure the screenshot directory
    if 'SCREENSHOT_DIR' not in os.environ:
        tests_dir = os.path.dirname(__file__)
        os.environ['SCREENSHOT_DIR'] = os.path.join(tests_dir, 'screenshots')

    unittest.main()
