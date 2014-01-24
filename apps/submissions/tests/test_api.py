import datetime

from django.test import TestCase

from submissions.models import StudentItem, StudentItemStruct
from submissions.api import create_submission, get_submissions

STUDENT_ITEM = StudentItemStruct(
    student_id="Tim",
    course_id="Demo_Course",
    item_id="item_one",
    item_type="Peer_Submission"
)

ANSWER_ONE = "this is my answer!"
ANSWER_TWO = "this is my other answer!"


class TestApi(TestCase):

    def test_create_submission(self):
        submission = create_submission(STUDENT_ITEM, ANSWER_ONE)
        self._assert_submission(submission, ANSWER_ONE, 1, 1)

    def test_get_submissions(self):
        create_submission(STUDENT_ITEM, ANSWER_ONE)
        create_submission(STUDENT_ITEM, ANSWER_TWO)
        submissions = get_submissions(STUDENT_ITEM)

        self._assert_submission(submissions[1], ANSWER_ONE, 1, 1)
        self._assert_submission(submissions[0], ANSWER_TWO, 1, 1)

    def test_get_latest_submission(self):
        past_date = datetime.date(2007, 11, 23)
        more_recent_date = datetime.date(2011, 10, 15)
        create_submission(STUDENT_ITEM, ANSWER_ONE, more_recent_date)
        create_submission(STUDENT_ITEM, ANSWER_TWO, past_date)

        # Test a limit on the submissions
        submissions = get_submissions(STUDENT_ITEM, 1)
        self.assertEqual(1, len(submissions))
        self.assertEqual(ANSWER_ONE, submissions[0].answer)
        self.assertEqual(more_recent_date.year, submissions[0].submitted_at.year)

    def test_set_attempt_number(self):
        create_submission(STUDENT_ITEM, ANSWER_ONE, None, 2)
        submissions = get_submissions(STUDENT_ITEM)
        self._assert_submission(submissions[0], ANSWER_ONE, 1, 2)

    def test_error_checking(self):
        create_submission(STUDENT_ITEM, -100)

    def _assert_submission(self, submission, expected_answer, expected_item,
                           expected_attempt):
        self.assertIsNotNone(submission)
        self.assertEqual(submission.answer, expected_answer)
        self.assertEqual(submission.student_item, expected_item)
        self.assertEqual(submission.attempt_number, expected_attempt)