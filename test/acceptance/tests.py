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
        self.grade_page = GradePage(self.browser, self.problem_loc)


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
        self.auto_auth_page.visit()
        self.submission_page.visit().submit_response(self.SUBMISSION)
        self.assertTrue(self.submission_page.has_submitted)

        # Submit a self-assessment
        self.self_asmnt_page.wait_for_page().wait_for_response()
        self.assertIn(self.SUBMISSION, self.self_asmnt_page.response_text)
        self.self_asmnt_page.assess(self.OPTIONS_SELECTED).wait_for_complete()
        self.assertTrue(self.self_asmnt_page.is_complete)

        # Verify the grade
        self.assertEqual(self.grade_page.wait_for_page().score, self.EXPECTED_SCORE)

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
        self.peer_asmnt_page.wait_for_page().wait_for_response().assess(self.OPTIONS_SELECTED)

        # Check that the status indicates we've assessed one submission
        try:
            self.peer_asmnt_page.wait_for_num_completed(1)
        except BrokenPromise:
            self.fail("Did not complete at least one peer assessment.")


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

            self.student_training_page.wait_for_page().wait_for_response().assess(options_selected)

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
    """

    def setUp(self):
        super(StaffAreaTest, self).setUp('peer_only', staff=True)
        self.staff_area_page = StaffAreaPage(self.browser, self.problem_loc)

    @retry()
    @attr('acceptance')
    def test_staff_area_buttons(self):
        """
        Scenario: the staff area buttons should behave correctly

        Given I am viewing the staff area of an ORA problem
        Then none of the buttons should be active
        When I click the "Staff Tools" button
        Then only the "Staff Tools" button should be active
        When I click the "Staff Info" button
        Then only the "Staff Info" button should be active
        When I click the "Staff Info" button again
        Then none of the buttons should be active
        """
        self.auto_auth_page.visit()
        self.staff_area_page.visit()
        self.assertEqual(self.staff_area_page.selected_button_names, [])
        self.staff_area_page.click_staff_toolbar_button("staff-tools")
        self.assertEqual(self.staff_area_page.selected_button_names, ["STAFF TOOLS"])
        self.staff_area_page.click_staff_toolbar_button("staff-info")
        self.assertEqual(self.staff_area_page.selected_button_names, ["STAFF INFO"])
        self.staff_area_page.click_staff_toolbar_button("staff-info")
        self.assertEqual(self.staff_area_page.selected_button_names, [])

    @retry()
    @attr('acceptance')
    @ddt.data(
        ("staff-tools", "STAFF TOOLS"),
        ("staff-info", "STAFF INFO"),
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
        self.assertEqual(
            self.staff_area_page.visible_staff_panels,
            [u'openassessment__{button_name}'.format(button_name=panel_name)]
        )

        # Click 'Close' and verify that the panel has been closed
        self.staff_area_page.click_staff_panel_close_button(panel_name)
        self.assertEqual(self.staff_area_page.selected_button_names, [])
        self.assertEqual(self.staff_area_page.visible_staff_panels, [])


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
