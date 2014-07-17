"""
UI-level acceptance tests for OpenAssessment.
"""
import os
import unittest
from bok_choy.web_app_test import WebAppTest
from bok_choy.promise import EmptyPromise, BrokenPromise
from auto_auth import AutoAuthPage
from pages import (
    SubmissionPage, AssessmentPage, GradePage
)


class OpenAssessmentTest(WebAppTest):
    """
    UI-level acceptance tests for Open Assessment.
    """
    TEST_COURSE_ID = "ora2/1/1"

    PROBLEM_LOCATIONS = {
        'self_only': u'courses/ora2/1/1/courseware/a4dfec19cf9b4a6fb5b18be6ccd9cecc/338a4affb58a45459629e0566291381e/',
        'peer_only': u'courses/ora2/1/1/courseware/a4dfec19cf9b4a6fb5b18be6ccd9cecc/417e47b2663a4f79b62dba20b21628c8/',
    }

    SUBMISSION = u"This is a test submission."
    OPTIONS_SELECTED = [1, 2]
    EXPECTED_SCORE = 6

    def setUp(self, problem_type):
        """
        Configure page objects to test Open Assessment.

        Args:
            problem_type (str): TODO
        """
        super(OpenAssessmentTest, self).setUp()

        problem_loc = self.PROBLEM_LOCATIONS[problem_type]
        self.auto_auth_page = AutoAuthPage(self.browser, course_id=self.TEST_COURSE_ID)
        self.submission_page = SubmissionPage(self.browser, problem_loc)
        self.self_asmnt_page = AssessmentPage('self-assessment', self.browser, problem_loc)
        self.peer_asmnt_page = AssessmentPage('peer-assessment', self.browser, problem_loc)
        self.grade_page = GradePage(self.browser, problem_loc)

class SelfAssessmentTest(OpenAssessmentTest):
    """
    Test the self-assessment flow.
    """

    def setUp(self):
        super(SelfAssessmentTest, self).setUp('self_only')

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


class PeerAssessmentTest(OpenAssessmentTest):
    """
    Test the peer-assessment flow.

    It's complicated to guarantee that a student will both give and
    receive enough assessments to receive a grade, so we stop
    once we've given one peer assessment.
    """

    def setUp(self):
        super(PeerAssessmentTest, self).setUp('peer_only')

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
            EmptyPromise(
                lambda: self.peer_asmnt_page.num_completed > 0,
                "Completed at least one peer assessment."
            ).fulfill()
        except BrokenPromise:
            self.fail("Did not complete at least one peer assessment.")
        else:
            self.assertEqual(self.peer_asmnt_page.num_completed, 1)


if __name__ == "__main__":

    # Configure the screenshot directory
    if 'SCREENSHOT_DIR' not in os.environ:
        tests_dir = os.path.dirname(__file__)
        os.environ['SCREENSHOT_DIR'] = os.path.join(tests_dir, 'screenshots')

    unittest.main()
