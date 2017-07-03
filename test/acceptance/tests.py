"""
UI-level acceptance tests for OpenAssessment.
"""
from __future__ import absolute_import

import ddt
import os
import unittest
import time
from functools import wraps
from pyinstrument import Profiler

from acceptance.auto_auth import AutoAuthPage
from acceptance.pages import (
    SubmissionPage, AssessmentPage, GradePage, StaffAreaPage
)
from bok_choy.web_app_test import WebAppTest
from bok_choy.promise import BrokenPromise, EmptyPromise
from nose.plugins.attrib import attr

# This value is generally used in jenkins, but not locally
PROFILING_ENABLED = os.environ.get('ORA_PROFILING_ENABLED', False)

def retry(tries=2, delay=4, backoff=2):
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
        'feedback_only':
            u'courses/{test_course_id}/courseware/'
            u'8d9584d242b44343bc270ea5ef04ab03/a2875e0db1454d0b94728b9a7b28000b/'.format(test_course_id=TEST_COURSE_ID),
        'multiple_ora':
            u'courses/{test_course_id}/courseware/'
            u'3b9aa6e06d8f48818ff6f364b5586f38/b79abd43bb11445486cd1874e6c71a64/'.format(test_course_id=TEST_COURSE_ID),
    }

    SUBMISSION = u"This is a test submission."
    LATEX_SUBMISSION = u"[mathjaxinline]( \int_{0}^{1}xdx )[/mathjaxinline]"
    OPTIONS_SELECTED = [1, 2]
    STAFF_OVERRIDE_OPTIONS_SELECTED = [0, 1]
    STAFF_OVERRIDE_SCORE = 1
    STAFF_GRADE_EXISTS = "COMPLETE"
    STAFF_AREA_SCORE = "Final grade: {} out of 8"
    STAFF_OVERRIDE_STAFF_AREA_NOT_COMPLETE = "The problem has not been completed."
    EXPECTED_SCORE = 6
    STUDENT_TRAINING_OPTIONS = [
        [1, 2],
        [0, 2]
    ]

    TEST_PASSWORD = "test_password"

    def setUp(self, problem_type, staff=False):
        """
        Configure page objects to test Open Assessment.

        Args:
            problem_type (str): The type of problem being tested,
              used to choose which part of the course to load.
            staff (bool): If True, runs the test with a staff user (defaults to False).

        """
        super(OpenAssessmentTest, self).setUp()

        if PROFILING_ENABLED:
            self.profiler = Profiler(use_signal=False)
            self.profiler.start()

        self.problem_loc = self.PROBLEM_LOCATIONS[problem_type]
        self.auto_auth_page = AutoAuthPage(self.browser, course_id=self.TEST_COURSE_ID, staff=staff)
        self.submission_page = SubmissionPage(self.browser, self.problem_loc)
        self.self_asmnt_page = AssessmentPage('self-assessment', self.browser, self.problem_loc)
        self.peer_asmnt_page = AssessmentPage('peer-assessment', self.browser, self.problem_loc)
        self.student_training_page = AssessmentPage('student-training', self.browser, self.problem_loc)
        self.staff_asmnt_page = AssessmentPage('staff-assessment', self.browser, self.problem_loc)
        self.grade_page = GradePage(self.browser, self.problem_loc)

    def log_to_file(self):
        with open('{}-profile.log'.format(self.id()), 'w') as f:
            f.write(self.profiler.output_text())

    def tearDown(self):
        if PROFILING_ENABLED:
            self.profiler.stop()
            self.log_to_file()

    def login_user(self, learner, email):
        """
        Logs in an already existing user.

        Args:
            learner (str): the username of the user.
            email (str): email address of the user.
        """
        auto_auth_page = AutoAuthPage(
            self.browser, email=email, password=self.TEST_PASSWORD, username=learner,
            course_id=self.TEST_COURSE_ID, staff=True
        )
        auto_auth_page.visit()

    def do_self_assessment(self):
        """
        Creates a user, submits a self assessment, verifies the grade, and returns the username of the
        learner for which the self assessment was submitted.
        """
        self.auto_auth_page.visit()
        username, _ = self.auto_auth_page.get_username_and_email()
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
        self.self_asmnt_page.assess(options).wait_for_complete()
        self.assertTrue(self.self_asmnt_page.is_complete)

    def _verify_staff_grade_section(self, expected_status):
        """
        Verifies the expected status and message text in the Staff Grade section
        (as shown to the learner).
        """
        self.staff_asmnt_page.wait_for_page()
        self.assertEqual("Staff Grade", self.staff_asmnt_page.label)
        self.staff_asmnt_page.verify_status_value(expected_status)

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

            self.student_training_page.wait_for_page().wait_for_response().assess(options_selected)

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
            self.peer_asmnt_page.wait_for_page().wait_for_response().assess(options)
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
        self.staff_area_page.staff_assess(self.STAFF_OVERRIDE_OPTIONS_SELECTED)
        self.staff_area_page.verify_learner_final_score(final_score)

    def do_staff_assessment(self, number_to_assess=0, options_selected=OPTIONS_SELECTED, feedback=None):
        """
        Use staff tools to assess available responses.

        Args:
            number_to_assess: the number of submissions to assess. If not provided (or 0),
                will grade all available submissions.
            options_selected (dict): the options to choose when grading. Defaults to OPTIONS_SELECTED.
            feedback (function(feedback_type)): if feedback is set, it will be used as a function that takes one
                parameter to generate a feedback string.
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
            if feedback:
                self.staff_area_page.provide_criterion_feedback(feedback("criterion"))
                self.staff_area_page.provide_overall_feedback(feedback("overall"))
            if options_selected:
                self.staff_area_page.staff_assess(options_selected, continue_after)
            assessed += 1
            if not continue_after:
                self.staff_area_page.verify_available_checked_out_numbers((ungraded, checked_out-1))
                break
            else:
                ungraded -= 1
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
        username, _ = self.auto_auth_page.get_username_and_email()
        self.submission_page.visit()

        # Verify that staff grade step is shown initially
        self._verify_staff_grade_section("NOT AVAILABLE")

        # User submits a response
        self.submission_page.submit_response(self.SUBMISSION)
        self.assertTrue(self.submission_page.has_submitted)

        # Verify staff grade section appears as expected
        self._verify_staff_grade_section("NOT AVAILABLE")
        message_title = self.staff_asmnt_page.open_step().message_title
        self.assertEqual("Waiting for a Staff Grade", message_title)

        # Perform staff assessment
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)
        self.do_staff_assessment()

        # Verify staff grade section appears as expected
        self.staff_asmnt_page.visit()
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS)
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


class StaffOverrideTest(OpenAssessmentTest):
    """
    Test setting a staff override on a problem which requires peer or self assessment.

    This is used as a base class, as the problem type defined by subclasses must be known in setUp().
    """
    def __init__(self, *args, **kwargs):
        super(StaffOverrideTest, self).__init__(*args, **kwargs)
        self.problem_type = None

    def setUp(self):
        if self.problem_type is None:
            self.fail("Please define self.problem_type in a sub-class")
        super(StaffOverrideTest, self).setUp(self.problem_type, staff=True)
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)

    @retry()
    @attr('acceptance')
    def _test_staff_override(self):
        """
        Scenario: staff can override a learner's grade

        Given I am viewing a new peer assessment problem as a learner
        And if I create a response to the problem
        Then there is no Staff Grade section present
        And if a staff member creates a grade override
        Then I can see my final grade, even though no peers have assessed me
        """
        # Create a submission
        self.auto_auth_page.visit()
        username, _ = self.auto_auth_page.get_username_and_email()
        self.submission_page.visit().submit_response(self.SUBMISSION)

        # Staff Grade field should not be visible yet.
        self.assertFalse(self.staff_asmnt_page.is_browser_on_page())

        # Submit a staff override.
        self.do_staff_override(username)

        # Refresh the page so the learner sees the Staff Grade section.
        self.refresh_page()
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS)

        # Verify the staff override grade
        self.assertEqual(self.STAFF_OVERRIDE_SCORE, self.grade_page.wait_for_page().score)


class StaffOverrideSelfTest(StaffOverrideTest):
    """
    Subclass of StaffOverrideTest for a 'self_only' problem.
    """
    def __init__(self, *args, **kwargs):
        super(StaffOverrideSelfTest, self).__init__(*args, **kwargs)
        self.problem_type = 'self_only'

    @retry()
    @attr('acceptance')
    def test_staff_override(self):
        super(StaffOverrideSelfTest, self)._test_staff_override()


class StaffOverridePeerTest(StaffOverrideTest):
    """
    Subclass of StaffOverrideTest for a 'peer_only' problem.
    """
    def __init__(self, *args, **kwargs):
        super(StaffOverridePeerTest, self).__init__(*args, **kwargs)
        self.problem_type = 'peer_only'

    @retry()
    @attr('acceptance')
    def test_staff_override(self):
        super(StaffOverridePeerTest, self)._test_staff_override()


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
    def test_staff_area_panel(self):
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

        for panel_name, button_label in [
                ("staff-tools", "MANAGE INDIVIDUAL LEARNERS"),
                ("staff-info", "VIEW ASSIGNMENT STATISTICS"),
        ]:
            # Click on the button and verify that the panel has opened
            self.staff_area_page.click_staff_toolbar_button(panel_name)
            self.assertEqual(self.staff_area_page.selected_button_names, [button_label])
            visible_panels = self.staff_area_page.visible_staff_panels
            self.assertEqual(1, len(visible_panels))
            self.assertIn(u'openassessment__{button_name}'.format(button_name=panel_name), visible_panels[0])

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
        And I've made a staff override assessment of the learner
        Then I see the correct learner information sections
        """
        username = self.do_self_assessment()
        self.do_staff_override(username)

        self.staff_area_page.visit()

        # Click on staff tools and search for user
        self.staff_area_page.show_learner(username)
        self.assertEqual(
            [u"Learner's Response", u"Learner's Self Assessment", u"Staff Assessment for This Learner",
             u"Learner's Final Grade", u"Submit Assessment Grade Override", u"Remove Submission From Peer Grading"],
            self.staff_area_page.learner_report_sections
        )

        self.assertNotIn('A response was not found for this learner', self.staff_area_page.learner_report_text)

    @retry()
    @attr('acceptance')
    def test_student_info_no_submission(self):
        """
        Scenario: staff tools indicates if no submission has been received for a given learner

        Given I am viewing the staff area of an ORA problem
        And I myself have submitted a response with self-assessment
        When I search for a learner in staff tools
        And the learner has not submitted a response to the ORA problem
        Then I see a message indicating that the learner has not submitted a response
        And there are no student information sections displayed
        """
        self.auto_auth_page.visit()

        # This is to catch a bug that existed when the user viewing staff tools had submitted an assessment,
        # and had a grade stored (TNL-4060).
        self.do_self_assessment()

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
        self.assertEquals(
            ['CRITERION', 'SELF ASSESSMENT GRADE'],
            self.staff_area_page.learner_final_score_table_headers
        )
        self.assertEquals(
            ['Fair - 3 points', 'Good - 3 points'], self.staff_area_page.learner_final_score_table_values
        )

        # Do staff override and wait for final score to change.
        self.staff_area_page.assess(self.STAFF_OVERRIDE_OPTIONS_SELECTED)

        # Verify that the new student score is different from the original one.
        self.staff_area_page.verify_learner_final_score(self.STAFF_AREA_SCORE.format(self.STAFF_OVERRIDE_SCORE))
        self.assertEquals(
            ['CRITERION', 'STAFF GRADE', 'SELF ASSESSMENT GRADE'],
            self.staff_area_page.learner_final_score_table_headers
        )
        self.assertEquals(
            ['Poor - 0 points', 'Fair',
             'Fair - 1 point', 'Good'],
            self.staff_area_page.learner_final_score_table_values
        )

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
        self._verify_staff_grade_section("CANCELLED")
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
        readme = os.path.dirname(os.path.realpath(__file__)) + '/README.rst'
        self.submission_page.visit().select_file(readme)
        self.assertFalse(self.submission_page.has_file_error)
        self.assertTrue(self.submission_page.upload_file_button_is_disabled)

        self.submission_page.add_file_description(0, 'file description 1')
        self.assertTrue(self.submission_page.upload_file_button_is_enabled)

        self.submission_page.upload_file()
        self.assertTrue(self.submission_page.have_files_uploaded)


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
    STAFF_AREA_SELF_ASSESSMENT = ['Good', u'', u'5', u'5', u'Excellent', u'', u'3', u'3']

    SUBMITTED_ASSESSMENT = [0, 3]
    STAFF_AREA_SUBMITTED = ['Poor', u'', u'0', u'5', u'Excellent', u'', u'3', u'3']

    def do_submission(self):
        """
        Creates a user and submission.

        Returns:
            (str, str): the username and email of the newly created user
        """
        auto_auth_page = AutoAuthPage(
            self.browser, password=self.TEST_PASSWORD, course_id=self.TEST_COURSE_ID, staff=True
        )
        auto_auth_page.visit()

        username_email = auto_auth_page.get_username_and_email()
        self.submission_page.visit().submit_response(self.SUBMISSION)
        EmptyPromise(self.submission_page.button(".step--student-training").is_focused(),
                     "Student training button should be focused")

        return username_email

    def do_submission_training_self_assessment(self):
        """
        Creates a user and then does submission, training, and self assessment.

        Returns:
            (str, str): the username and password of the newly created user
        """
        username, email = self.do_submission()
        EmptyPromise(self.submission_page.button(".step--student-training").is_focused(),
                     "Student training button should be focused")
        self.submission_page.confirm_feedback_text('Your Response Complete')
        self.submission_page.confirm_feedback_text('Learn to Assess Responses In Progress (1 of 2)')

        self.do_training()
        EmptyPromise(self.submission_page.button(".step--self-assessment").is_focused(),
                     "Self assessment button should be focused")
        self.submission_page.confirm_feedback_text('Learn to Assess Responses Complete')
        self.submission_page.confirm_feedback_text('Assess Your Response In Progress')

        self.submit_self_assessment(self.SELF_ASSESSMENT)
        EmptyPromise(self.submission_page.button(".step--grade").is_focused(),
                     "Grade button should be focused")
        self.submission_page.confirm_feedback_text('Assess Your Response Complete')
        self.submission_page.confirm_feedback_text('Assess Peers In Progress (1 of 1)')

        return username, email

    def do_train_self_peer(self, peer_to_grade=True):
        """
        Common functionality for executing training, self, and peer assessment steps.

        Args:
            peer_to_grade: boolean, defaults to True. Set to False to have learner complete their required steps,
                but no peers to submit a grade for learner in return.
        """
        # Create a learner with submission, training, and self assessment completed.
        learner, learner_email = self.do_submission_training_self_assessment()

        # Now create a second learner so that learner 1 has someone to assess.
        # The second learner does all the steps as well (submission, training, self assessment, peer assessment).
        self.do_submission_training_self_assessment()
        if peer_to_grade:
            self.do_peer_assessment(options=self.PEER_ASSESSMENT)

        # Go back to the first learner to complete her workflow.
        self.login_user(learner, learner_email)

        # Learner 1 does peer assessment of learner 2 to complete workflow.
        self.do_peer_assessment(options=self.SUBMITTED_ASSESSMENT)

        # Continue grading by other students if necessary to ensure learner has a peer grade.
        if peer_to_grade:
            self.verify_submission_has_peer_grade(learner, learner_email)

        return learner

    def staff_assessment(self, peer_grades_me=True):
        """ Do staff assessment workflow """

        # Ensure grade is not present, since staff assessment has not been made
        self.assertIsNone(self.grade_page.wait_for_page().score)

        # Now do a staff assessment.
        self.do_staff_assessment(options_selected=self.STAFF_OVERRIDE_OPTIONS_SELECTED)

        # As an add-on, let's make sure that both submissions (the learner's, and the additional one created
        # in do_train_self_peer() above) were assessed using staff-grading's "submit and keep going"
        self.assertEqual(0, self.staff_area_page.available_checked_out_numbers[0])

        # At this point, the learner sees the score (1).
        self.refresh_page()
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS)
        self.assertEqual(self.STAFF_OVERRIDE_SCORE, self.grade_page.wait_for_page().score)
        if peer_grades_me:
            self.verify_grade_entries(
                [(u"STAFF GRADE - 0 POINTS", u"Poor", u"PEER MEDIAN GRADE", u"Poor", u"PEER 1", u"- POOR",
                  u"YOUR SELF ASSESSMENT", u"Good"),
                 (u"STAFF GRADE - 1 POINT", u"Fair", u"PEER MEDIAN GRADE", u"Poor", u"PEER 1", u"- POOR",
                 u"YOUR SELF ASSESSMENT", u"Excellent")]
            )
        else:
            self.verify_grade_entries(
                [(u"STAFF GRADE - 0 POINTS", u"Poor", u'PEER MEDIAN GRADE',
                  u'Waiting for peer reviews', u"YOUR SELF ASSESSMENT", u"Good"),
                 (u"STAFF GRADE - 1 POINT", u"Fair", u'PEER MEDIAN GRADE',
                  u'Waiting for peer reviews', u"YOUR SELF ASSESSMENT", u"Excellent")
                 ]
            )

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
        self.assertEqual(self_assessment, self.staff_area_page.status_text('self__assessments'))

    def verify_submission_has_peer_grade(self, learner, learner_email, max_attempts=5):
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
            self.do_submission_training_self_assessment()
            self.do_peer_assessment(options=self.PEER_ASSESSMENT)
            self.login_user(learner, learner_email)

        self.assertTrue(
            peer_grade_exists(),
            "Learner still not graded after {} additional attempts".format(max_attempts)
        )

    def verify_grade_entries(self, expected_entries):
        """
        Verify the grade entries as shown in the "Your Grade" section.

        Args:
            expected_entries: array of expected entries, with each entry being an tuple
               consisting of the data for a particular question. Note that order is important.
        """
        for index, expected_entry in enumerate(expected_entries):
            self.assertEqual(expected_entry, self.grade_page.grade_entry(index))


class MultipleOpenAssessmentMixin(FullWorkflowMixin):
    """
    A Multiple ORA assessment mixin with helper methods and constants for testing a full workflow
    (training, self assessment, peer assessment, staff override).
    """

    def setup_vertical_index(self, vertical_index):
        """
        Set the vertical index on the page.
        Each problem has vertical index assigned and has a `vert-{vertical_index}` top level class.
        Set up vertical index on the page so as to move to a different problem.
        """
        self.submission_page.vertical_index = vertical_index
        self.self_asmnt_page.vertical_index = vertical_index
        self.peer_asmnt_page.vertical_index = vertical_index
        self.student_training_page.vertical_index = vertical_index
        self.staff_asmnt_page.vertical_index = vertical_index
        self.grade_page.vertical_index = vertical_index
        self.staff_area_page.vertical_index = vertical_index

    def assess_component(self, vertical_index, peer_grades_me=True):
        """ Assess the complete flow of an open assessment."""
        self.setup_vertical_index(vertical_index)
        self.do_train_self_peer(peer_grades_me)
        self.staff_assessment(peer_grades_me)


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
        self.assertEquals(
            ['CRITERION', 'PEER MEDIAN GRADE', 'SELF ASSESSMENT GRADE'],
            self.staff_area_page.learner_final_score_table_headers
        )
        self.assertEquals(
            ['Poor - 0 points\nPeer 1 - Poor', 'Good',
             'Poor - 0 points\nPeer 1 - Poor', 'Excellent'],
            self.staff_area_page.learner_final_score_table_values
        )

        self.verify_grade_entries(
            [(u"PEER MEDIAN GRADE - 0 POINTS", u"Poor", u"PEER 1", u"- POOR", u"YOUR SELF ASSESSMENT", u"Good"),
             (u"PEER MEDIAN GRADE - 0 POINTS", u"Poor", u"PEER 1", u"- POOR", u"YOUR SELF ASSESSMENT", u"Excellent")]
        )

        # Now do a staff override, changing the score (to 1).
        self.do_staff_override(learner)

        self.refresh_page()
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS)
        self.assertEqual(self.STAFF_OVERRIDE_SCORE, self.grade_page.wait_for_page().score)
        self.verify_staff_area_fields(
            learner, self.STAFF_AREA_PEER_ASSESSMENT, self.STAFF_AREA_SUBMITTED, self.STAFF_AREA_SELF_ASSESSMENT
        )
        self.staff_area_page.verify_learner_final_score(self.STAFF_AREA_SCORE.format(self.STAFF_OVERRIDE_SCORE))
        self.assertEquals(
            ['CRITERION', 'STAFF GRADE', 'PEER MEDIAN GRADE', 'SELF ASSESSMENT GRADE'],
            self.staff_area_page.learner_final_score_table_headers
        )
        self.assertEquals(
            ['Poor - 0 points', 'Peer 1 - Poor', 'Good',
             'Fair - 1 point', 'Peer 1 - Poor', 'Excellent'],
            self.staff_area_page.learner_final_score_table_values
        )
        self.verify_grade_entries(
            [(u"STAFF GRADE - 0 POINTS", u"Poor", u"PEER MEDIAN GRADE", u"Poor",
              u"PEER 1", u"- POOR", u"YOUR SELF ASSESSMENT", u"Good"),
             (u"STAFF GRADE - 1 POINT", u"Fair", u"PEER MEDIAN GRADE",
              u"Poor", u"PEER 1", u"- POOR", u"YOUR SELF ASSESSMENT", u"Excellent")
             ]
        )

    @retry()
    @attr('acceptance')
    def test_staff_override_at_beginning(self):
        """
        Scenario: complete workflow with staff override at the very beginning

        Given that I have created a submission
        Then I see no score yet
        And when a staff member creates a grade override
        Then I see my staff override score
        And all fields in the staff area tool are correct
        """
        # Create only the initial submission before doing the staff override.
        learner, learner_email = self.do_submission()

        # Verify no grade present (and no staff grade section), no assessment information in staff area.
        self.assertIsNone(self.grade_page.wait_for_page().score)
        self.assertFalse(self.staff_asmnt_page.is_browser_on_page())
        self.verify_staff_area_fields(learner, [], [], [])
        self.staff_area_page.verify_learner_final_score(self.STAFF_OVERRIDE_STAFF_AREA_NOT_COMPLETE)

        # Do staff override
        self.do_staff_override(learner)

        # Refresh the page so the learner sees the Staff Grade section.
        self.refresh_page()
        self._verify_staff_grade_section(self.STAFF_GRADE_EXISTS)

        # Grade is now visible to the learner despite not having made any assessments
        self.assertEqual(self.STAFF_OVERRIDE_SCORE, self.grade_page.wait_for_page().score)
        self.verify_staff_area_fields(learner, [], [], [])
        self.staff_area_page.verify_learner_final_score(self.STAFF_AREA_SCORE.format(self.STAFF_OVERRIDE_SCORE))
        self.assertEquals(
            ['CRITERION', 'STAFF GRADE', 'PEER MEDIAN GRADE'],
            self.staff_area_page.learner_final_score_table_headers
        )
        self.assertEquals(
            ['Poor - 0 points', 'Waiting for peer reviews',
             'Fair - 1 point', 'Waiting for peer reviews'],
            self.staff_area_page.learner_final_score_table_values
        )
        self.verify_grade_entries(
            [(u"STAFF GRADE - 0 POINTS", u"Poor", u'PEER MEDIAN GRADE', u'Waiting for peer reviews'),
             (u"STAFF GRADE - 1 POINT", u"Fair", u'PEER MEDIAN GRADE', u'Waiting for peer reviews')
             ]
        )


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

        # Do staff assessment step
        self.staff_assessment(peer_grades_me)


@ddt.ddt
class FeedbackOnlyTest(OpenAssessmentTest, FullWorkflowMixin):
    """
    Test for a problem that containing a criterion that only accepts feedback. Will make and verify self and staff
    assessments.
    """
    def setUp(self):
        super(FeedbackOnlyTest, self).setUp("feedback_only", staff=True)
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)

    def generate_feedback(self, assessment_type, feedback_type):
        return "{}: {} feedback".format(assessment_type, feedback_type)

    def assess_feedback(self, self_or_peer=""):
        if self_or_peer != "self" and self_or_peer != "peer":
            raise AssertionError("assert_feedback only works for self or peer assessments")
        page = self.self_asmnt_page if self_or_peer == "self" else self.peer_asmnt_page
        page.wait_for_page()
        page.submit_assessment()

    @retry()
    @attr('acceptance')
    def test_feedback_only(self):
        # Make submission
        user, pwd = self.do_submission()

        # Make self assessment
        self.self_asmnt_page.visit()
        self.self_asmnt_page.wait_for_page()
        self.self_asmnt_page.provide_criterion_feedback(self.generate_feedback("self", "criterion"))
        self.self_asmnt_page.provide_overall_feedback(self.generate_feedback("self", "overall"))
        self.self_asmnt_page.assess([0])
        self.self_asmnt_page.wait_for_complete()
        self.assertTrue(self.self_asmnt_page.is_complete)

        # Staff assess all available submissions
        self.do_staff_assessment(
            options_selected=[0],  # Select the 0-th option (Yes) on the single scored criterion
            feedback=lambda feedback_type: self.generate_feedback("staff", feedback_type)
        )

        # Verify student-viewable grade report
        self.refresh_page()
        self.grade_page.wait_for_page()
        self.verify_grade_entries(
            [(u'STAFF GRADE - 1 POINT', u'Yes', u'YOUR SELF ASSESSMENT', u'Yes')]
        )
        for i, assessment_type in enumerate(["staff", "self"]):
            # Criterion feedback first
            expected = self.generate_feedback(assessment_type, "criterion")
            actual = self.grade_page.feedback_entry(1, i)
            self.assertEqual(actual, expected)  # Reported answers 3 and 4
            # Then overall
            expected = self.generate_feedback(assessment_type, "overall")
            actual = self.grade_page.feedback_entry("feedback", i)
            self.assertEqual(actual, expected)  # Reported answers 5 and 6
        # Verify that no reported answers other than the 6 we already verified are present
        self.assertEqual(self.grade_page.total_reported_answers, 6)
        # Verify that the feedback-only criterion has no score
        self.assertEqual(self.grade_page.number_scored_criteria, 1)

        # Verify feedback appears from all assessments in staff tools
        self.staff_area_page.show_learner(user)
        self.staff_area_page.expand_learner_report_sections()
        self.assertEqual(
            self.staff_area_page.learner_final_score_table_headers,
            [u'CRITERION', u'STAFF GRADE', u'SELF ASSESSMENT GRADE']
        )
        self.assertEqual(
            self.staff_area_page.learner_final_score_table_values,
            [u'Yes - 1 point', u'Yes', u'Feedback Recorded', u'Feedback Recorded']
        )
        self.assertEqual(
            self.staff_area_page.status_text('staff__assessments')[5],
            self.generate_feedback("staff", "criterion")
        )
        self.assertEqual(
            self.staff_area_page.overall_feedback('staff__assessments'),
            self.generate_feedback("staff", "overall")
        )
        self.assertEqual(
            self.staff_area_page.status_text('self__assessments')[5],
            self.generate_feedback("self", "criterion")
        )
        self.assertEqual(
            self.staff_area_page.overall_feedback('self__assessments'),
            self.generate_feedback("self", "overall")
        )
        # Verify correct score is shown
        self.staff_area_page.verify_learner_final_score("Final grade: 1 out of 1")


class MultipleOpenAssessmentTest(OpenAssessmentTest, MultipleOpenAssessmentMixin):
    """
    Test the multiple peer-assessment flow.
    """

    def setUp(self):
        super(MultipleOpenAssessmentTest, self).setUp('multiple_ora')
        # Staff area page is not present in OpenAssessmentTest base class, so we are adding it here.
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)

    @retry()
    @attr('acceptance')
    def test_multiple_ora_complete_flow(self):
        """
        Scenario: complete workflow on a unit containing multiple ORA blocks.
        """
        # Each problem has vertical index assigned and has a `vert-{vertical_index}` top level class.
        # That also means that all pages are being differentiated by their vertical index number that is assigned to
        # each problem type. We are passing vertical index number and setting it by `self.setup_vertical_index` method
        # so as to move to a different problem.

        # Assess first ORA problem, pass the vertical index number
        self.assess_component(0)

        # Assess second ORA problem, pass the vertical index number
        self.assess_component(1)


if __name__ == "__main__":

    # Configure the screenshot directory
    if 'SCREENSHOT_DIR' not in os.environ:
        tests_dir = os.path.dirname(__file__)
        os.environ['SCREENSHOT_DIR'] = os.path.join(tests_dir, 'screenshots')

    unittest.main()
