"""
UI-level acceptance tests for OpenAssessment.
"""
import unittest
from bok_choy.web_app_test import WebAppTest
from auto_auth import AutoAuthPage
from pages import (
    SubmissionPage, SelfAssessmentPage, GradePage
)


class OpenAssessmentTest(WebAppTest):
    """
    UI-level acceptance tests for Open Assessment.
    """
    TEST_COURSE_ID = "ora2/1/1"

    PROBLEM_LOCATIONS = {
        'self_only': u'courses/ora2/1/1/courseware/a4dfec19cf9b4a6fb5b18be6ccd9cecc/338a4affb58a45459629e0566291381e/',
    }

    SUBMISSION = u"This is a test submission."
    OPTIONS_SELECTED = [1, 2]
    EXPECTED_SCORE = 6

    def setUp(self):
        """
        Create an account registered for the test course and log in.
        """
        super(OpenAssessmentTest, self).setUp()
        AutoAuthPage(self.browser, course_id=self.TEST_COURSE_ID).visit()

    def test_self_assessment(self):
        """
        Test the self-only flow.
        """
        submission_page = SubmissionPage(
            self.browser,
            self.PROBLEM_LOCATIONS['self_only']
        ).visit()
        submission_page.submit_response(self.SUBMISSION)
        self.assertTrue(submission_page.has_submitted)

        self_assessment_page = SelfAssessmentPage(
            self.browser,
            self.PROBLEM_LOCATIONS['self_only']
        ).wait_for_page()
        self.assertIn(self.SUBMISSION, self_assessment_page.response_text)
        self_assessment_page.assess(self.OPTIONS_SELECTED)
        self.assertTrue(self_assessment_page.has_submitted)

        grade_page = GradePage(
            self.browser,
            self.PROBLEM_LOCATIONS['self_only']
        ).wait_for_page()
        self.assertEqual(grade_page.score, self.EXPECTED_SCORE)


if __name__ == "__main__":
    unittest.main()
