import datetime
import copy

from ddt import ddt, file_data
from django.db import DatabaseError
from django.core.cache import cache
from django.test import TestCase
from nose.tools import raises
from mock import patch
import pytz

from submissions import api as api
from submissions.models import ScoreSummary, Submission, StudentItem
from submissions.serializers import StudentItemSerializer

STUDENT_ITEM = dict(
    student_id="Tim",
    course_id="Demo_Course",
    item_id="item_one",
    item_type="Peer_Submission",
)

SECOND_STUDENT_ITEM = dict(
    student_id="Alice",
    course_id="Demo_Course",
    item_id="item_one",
    item_type="Peer_Submission",
)

ANSWER_ONE = u"this is my answer!"
ANSWER_TWO = u"this is my other answer!"
ANSWER_THREE = u'' + 'c' * (Submission.MAXSIZE + 1)


@ddt
class TestSubmissionsApi(TestCase):
    """
    Testing Submissions
    """

    def setUp(self):
        """
        Clear the cache.
        """
        cache.clear()

    def test_create_submission(self):
        submission = api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        student_item = self._get_student_item(STUDENT_ITEM)
        self._assert_submission(submission, ANSWER_ONE, student_item.pk, 1)

    def test_create_huge_submission_fails(self):
        with self.assertRaises(api.SubmissionRequestError):
            api.create_submission(STUDENT_ITEM, ANSWER_THREE)

    def test_get_submission_and_student(self):
        submission = api.create_submission(STUDENT_ITEM, ANSWER_ONE)

        # Retrieve the submission by its uuid
        retrieved = api.get_submission_and_student(submission['uuid'])
        self.assertItemsEqual(submission, retrieved)

        # Should raise an exception if the student item does not exist
        with self.assertRaises(api.SubmissionNotFoundError):
            api.get_submission_and_student(u'no such uuid')

    def test_get_submissions(self):
        api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        api.create_submission(STUDENT_ITEM, ANSWER_TWO)
        submissions = api.get_submissions(STUDENT_ITEM)

        student_item = self._get_student_item(STUDENT_ITEM)
        self._assert_submission(submissions[1], ANSWER_ONE, student_item.pk, 1)
        self._assert_submission(submissions[0], ANSWER_TWO, student_item.pk, 2)

    def test_get_submission(self):
        # Test base case that we can create a submission and get it back
        sub_dict1 = api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        sub_dict2 = api.get_submission(sub_dict1["uuid"])
        self.assertEqual(sub_dict1, sub_dict2)

        # Test invalid inputs
        with self.assertRaises(api.SubmissionRequestError):
            api.get_submission(20)
        with self.assertRaises(api.SubmissionRequestError):
            api.get_submission({})

        # Test not found
        with self.assertRaises(api.SubmissionNotFoundError):
            api.get_submission("notarealuuid")
        with self.assertRaises(api.SubmissionNotFoundError):
            api.get_submission("0" * 50)  # This is bigger than our field size

    @patch.object(Submission.objects, 'get')
    @raises(api.SubmissionInternalError)
    def test_get_submission_deep_error(self, mock_get):
        # Test deep explosions are wrapped
        mock_get.side_effect = DatabaseError("Kaboom!")
        api.get_submission("000000000000000")


    def test_two_students(self):
        api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        api.create_submission(SECOND_STUDENT_ITEM, ANSWER_TWO)

        submissions = api.get_submissions(STUDENT_ITEM)
        self.assertEqual(1, len(submissions))
        student_item = self._get_student_item(STUDENT_ITEM)
        self._assert_submission(submissions[0], ANSWER_ONE, student_item.pk, 1)

        submissions = api.get_submissions(SECOND_STUDENT_ITEM)
        self.assertEqual(1, len(submissions))
        student_item = self._get_student_item(SECOND_STUDENT_ITEM)
        self._assert_submission(submissions[0], ANSWER_TWO, student_item.pk, 1)


    @file_data('data/valid_student_items.json')
    def test_various_student_items(self, valid_student_item):
        api.create_submission(valid_student_item, ANSWER_ONE)
        student_item = self._get_student_item(valid_student_item)
        submission = api.get_submissions(valid_student_item)[0]
        self._assert_submission(submission, ANSWER_ONE, student_item.pk, 1)

    def test_get_latest_submission(self):
        past_date = datetime.datetime(2007, 9, 12, 0, 0, 0, 0, pytz.UTC)
        more_recent_date = datetime.datetime(2007, 9, 13, 0, 0, 0, 0, pytz.UTC)
        api.create_submission(STUDENT_ITEM, ANSWER_ONE, more_recent_date)
        api.create_submission(STUDENT_ITEM, ANSWER_TWO, past_date)

        # Test a limit on the submissions
        submissions = api.get_submissions(STUDENT_ITEM, 1)
        self.assertEqual(1, len(submissions))
        self.assertEqual(ANSWER_ONE, submissions[0]["answer"])
        self.assertEqual(more_recent_date.year,
                         submissions[0]["submitted_at"].year)

    def test_set_attempt_number(self):
        api.create_submission(STUDENT_ITEM, ANSWER_ONE, None, 2)
        submissions = api.get_submissions(STUDENT_ITEM)
        student_item = self._get_student_item(STUDENT_ITEM)
        self._assert_submission(submissions[0], ANSWER_ONE, student_item.pk, 2)

    @raises(api.SubmissionRequestError)
    @file_data('data/bad_student_items.json')
    def test_error_checking(self, bad_student_item):
        api.create_submission(bad_student_item, -100)

    @raises(api.SubmissionRequestError)
    def test_error_checking_submissions(self):
        api.create_submission(STUDENT_ITEM, ANSWER_ONE, None, -1)

    @patch.object(Submission.objects, 'filter')
    @raises(api.SubmissionInternalError)
    def test_error_on_submission_creation(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Bad things happened")
        api.create_submission(STUDENT_ITEM, ANSWER_ONE)

    def test_create_non_json_answer(self):
        with self.assertRaises(api.SubmissionRequestError):
            api.create_submission(STUDENT_ITEM, datetime.datetime.now())

    def test_load_non_json_answer(self):
        # This should never happen, if folks are using the public API.
        # Create a submission with a raw answer that is NOT valid JSON
        submission = api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        sub_model = Submission.objects.get(uuid=submission['uuid'])
        sub_model.raw_answer = ''
        sub_model.save()

        with self.assertRaises(api.SubmissionInternalError):
            api.get_submission(sub_model.uuid)

        with self.assertRaises(api.SubmissionInternalError):
            api.get_submission_and_student(sub_model.uuid)

    @patch.object(StudentItemSerializer, 'save')
    @raises(api.SubmissionInternalError)
    def test_create_student_item_validation(self, mock_save):
        mock_save.side_effect = DatabaseError("Bad things happened")
        api.create_submission(STUDENT_ITEM, ANSWER_ONE)

    def test_unicode_enforcement(self):
        api.create_submission(STUDENT_ITEM, "Testing unicode answers.")
        submissions = api.get_submissions(STUDENT_ITEM, 1)
        self.assertEqual(u"Testing unicode answers.", submissions[0]["answer"])

    def _assert_submission(self, submission, expected_answer, expected_item,
                           expected_attempt):
        self.assertIsNotNone(submission)
        self.assertEqual(submission["answer"], expected_answer)
        self.assertEqual(submission["student_item"], expected_item)
        self.assertEqual(submission["attempt_number"], expected_attempt)

    def _get_student_item(self, student_item):
        return StudentItem.objects.get(
            student_id=student_item["student_id"],
            course_id=student_item["course_id"],
            item_id=student_item["item_id"]
        )

    def test_caching(self):
        sub = api.create_submission(STUDENT_ITEM, "Hello World!")

        # The first request to get the submission hits the database...
        with self.assertNumQueries(1):
            db_sub = api.get_submission(sub["uuid"])

        # The next one hits the cache only...
        with self.assertNumQueries(0):
            cached_sub = api.get_submission(sub["uuid"])

        # The data that gets passed back matches the original in both cases
        self.assertEqual(sub, db_sub)
        self.assertEqual(sub, cached_sub)

    """
    Testing Scores
    """

    def test_create_score(self):
        submission = api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        student_item = self._get_student_item(STUDENT_ITEM)
        self._assert_submission(submission, ANSWER_ONE, student_item.pk, 1)

        api.set_score(submission["uuid"], 11, 12)
        score = api.get_latest_score_for_submission(submission["uuid"])
        self._assert_score(score, 11, 12)

    def test_get_score(self):
        submission = api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        api.set_score(submission["uuid"], 11, 12)
        score = api.get_score(STUDENT_ITEM)
        self._assert_score(score, 11, 12)
        self.assertEqual(score['submission_uuid'], submission['uuid'])

    def test_get_score_for_submission_hidden_score(self):
        # Create a "hidden" score for the submission
        # (by convention, a score with points possible set to 0)
        submission = api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        api.set_score(submission["uuid"], 0, 0)

        # Expect that the retrieved score is None
        score = api.get_latest_score_for_submission(submission['uuid'])
        self.assertIs(score, None)

    def test_get_score_no_student_id(self):
        student_item = copy.deepcopy(STUDENT_ITEM)
        student_item['student_id'] = None
        self.assertIs(api.get_score(student_item), None)

    def test_get_scores(self):
        student_item = copy.deepcopy(STUDENT_ITEM)
        student_item["course_id"] = "get_scores_course"

        student_item["item_id"] = "i4x://a/b/c/s1"
        s1 = api.create_submission(student_item, "Hello World")

        student_item["item_id"] = "i4x://a/b/c/s2"
        s2 = api.create_submission(student_item, "Hello World")

        student_item["item_id"] = "i4x://a/b/c/s3"
        s3 = api.create_submission(student_item, "Hello World")

        api.set_score(s1['uuid'], 3, 5)
        api.set_score(s1['uuid'], 4, 5)
        api.set_score(s1['uuid'], 2, 5)  # Should overwrite previous lines

        api.set_score(s2['uuid'], 0, 10)
        api.set_score(s3['uuid'], 4, 4)

        # Getting the scores for a user should never take more than one query
        with self.assertNumQueries(1):
            scores = api.get_scores(
                student_item["course_id"], student_item["student_id"]
            )
            self.assertEqual(
                scores,
                {
                    u"i4x://a/b/c/s1": (2, 5),
                    u"i4x://a/b/c/s2": (0, 10),
                    u"i4x://a/b/c/s3": (4, 4),
                }
            )

    @patch.object(ScoreSummary.objects, 'filter')
    @raises(api.SubmissionInternalError)
    def test_error_on_get_scores(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Bad things happened")
        api.get_scores("some_course", "some_student")

    def _assert_score(
            self,
            score,
            expected_points_earned,
            expected_points_possible):
        self.assertIsNotNone(score)
        self.assertEqual(score["points_earned"], expected_points_earned)
        self.assertEqual(score["points_possible"], expected_points_possible)
