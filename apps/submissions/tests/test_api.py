import datetime

from ddt import ddt, file_data
from django.db import DatabaseError
from django.test import TestCase
from nose.tools import raises
from mock import patch

from submissions.api import create_submission, get_submissions, SubmissionRequestError, SubmissionInternalError
from submissions.models import Submission
from submissions.serializers import StudentItemSerializer

STUDENT_ITEM = dict(
    student_id="Tim",
    course_id="Demo_Course",
    item_id="item_one",
    item_type="Peer_Submission",
)

SECOND_STUDENT_ITEM = dict(
    student_id="Bob",
    course_id="Demo_Course",
    item_id="item_one",
    item_type="Peer_Submission",
)

ANSWER_ONE = u"this is my answer!"
ANSWER_TWO = u"this is my other answer!"


@ddt
class TestApi(TestCase):
    def test_create_submission(self):
        submission = create_submission(STUDENT_ITEM, ANSWER_ONE)
        self._assert_submission(submission, ANSWER_ONE, 1, 1)

    def test_get_submissions(self):
        create_submission(STUDENT_ITEM, ANSWER_ONE)
        create_submission(STUDENT_ITEM, ANSWER_TWO)
        submissions = get_submissions(STUDENT_ITEM)

        self._assert_submission(submissions[1], ANSWER_ONE, 1, 1)
        self._assert_submission(submissions[0], ANSWER_TWO, 1, 2)

    def test_two_students(self):
        create_submission(STUDENT_ITEM, ANSWER_ONE)
        create_submission(SECOND_STUDENT_ITEM, ANSWER_TWO)

        submissions = get_submissions(STUDENT_ITEM)
        self.assertEqual(1, len(submissions))
        self._assert_submission(submissions[0], ANSWER_ONE, 1, 1)

        submissions = get_submissions(SECOND_STUDENT_ITEM)
        self.assertEqual(1, len(submissions))
        self._assert_submission(submissions[0], ANSWER_TWO, 2, 1)


    @file_data('test_valid_student_items.json')
    def test_various_student_items(self, valid_student_item):
        create_submission(valid_student_item, ANSWER_ONE)
        submission = get_submissions(valid_student_item)[0]
        self._assert_submission(submission, ANSWER_ONE, 1, 1)

    def test_get_latest_submission(self):
        past_date = datetime.date(2007, 11, 23)
        more_recent_date = datetime.date(2011, 10, 15)
        create_submission(STUDENT_ITEM, ANSWER_ONE, more_recent_date)
        create_submission(STUDENT_ITEM, ANSWER_TWO, past_date)

        # Test a limit on the submissions
        submissions = get_submissions(STUDENT_ITEM, 1)
        self.assertEqual(1, len(submissions))
        self.assertEqual(ANSWER_ONE, submissions[0]["answer"])
        self.assertEqual(more_recent_date.year,
                         submissions[0]["submitted_at"].year)

    def test_set_attempt_number(self):
        create_submission(STUDENT_ITEM, ANSWER_ONE, None, 2)
        submissions = get_submissions(STUDENT_ITEM)
        self._assert_submission(submissions[0], ANSWER_ONE, 1, 2)

    @raises(SubmissionRequestError)
    @file_data('test_bad_student_items.json')
    def test_error_checking(self, bad_student_item):
        create_submission(bad_student_item, -100)

    @raises(SubmissionRequestError)
    def test_error_checking_submissions(self):
        create_submission(STUDENT_ITEM, ANSWER_ONE, None, -1)

    @patch.object(Submission.objects, 'filter')
    @raises(SubmissionInternalError)
    def test_error_on_submission_creation(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Bad things happened")
        create_submission(STUDENT_ITEM, ANSWER_ONE)

    @patch.object(StudentItemSerializer, 'save')
    @raises(SubmissionInternalError)
    def test_create_student_item_validation(self, mock_save):
        mock_save.side_effect = DatabaseError("Bad things happened")
        create_submission(STUDENT_ITEM, ANSWER_ONE)

    def test_unicode_enforcement(self):
        create_submission(STUDENT_ITEM, "Testing unicode answers.")
        submissions = get_submissions(STUDENT_ITEM, 1)
        self.assertEqual(u"Testing unicode answers.", submissions[0]["answer"])

    def _assert_submission(self, submission, expected_answer, expected_item,
                           expected_attempt):
        self.assertIsNotNone(submission)
        self.assertEqual(submission["answer"], expected_answer)
        self.assertEqual(submission["student_item"], expected_item)
        self.assertEqual(submission["attempt_number"], expected_attempt)