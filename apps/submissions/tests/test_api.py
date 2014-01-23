from django.test import TestCase
from submissions.models import StudentItem, StudentItemStruct
from submissions.api import create_submission, get_submissions

STUDENT_ITEM = StudentItemStruct(
    student_id="Tim",
    course_id="Demo_Course",
    item_id="item_one",
    item_type="Peer_Submission"
)

class TestApi(TestCase):

    def setUp(self):
        StudentItem.objects.create(
            student_id=STUDENT_ITEM.student_id,
            course_id=STUDENT_ITEM.course_id,
            item_id=STUDENT_ITEM.item_id,
            item_type=STUDENT_ITEM.student_id
        )

    def test_create_submission(self):
        submission = create_submission(STUDENT_ITEM, "this is my answer!")
        self._assert_submission(submission, "this is my answer!", 1, 1)

    def test_get_submission(self):
        create_submission(STUDENT_ITEM, "this is my answer!")
        create_submission(STUDENT_ITEM, "this is my other answer!")
        submissions = get_submissions(STUDENT_ITEM)

        self._assert_submission(submissions[0], "this is my answer!", 1, 1)
        self._assert_submission(submissions[1], "this is my other answer!", 1, 1)

        # Test a limit on the submissions
        submissions = get_submissions(STUDENT_ITEM, 1)
        self.assertEqual(1, len(submissions))

    def _assert_submission(self, submission, expected_answer, expected_item, expected_attempt):
        self.assertIsNotNone(submission)
        self.assertEqual(submission.answer, expected_answer)
        self.assertEqual(submission.student_item, expected_item)
        self.assertEqual(submission.attempt_number, expected_attempt)