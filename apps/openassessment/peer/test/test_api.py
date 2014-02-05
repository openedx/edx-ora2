from ddt import ddt
import pytz
import datetime
from django.test import TestCase
from nose.tools import raises
from openassessment.peer.api import create_evaluation, get_evaluations, has_finished_required_evaluating, PeerEvaluationRequestError, get_submission_to_evaluate
from submissions.api import create_submission
from submissions.tests.test_api import STUDENT_ITEM, ANSWER_ONE

ASSESSMENT_DICT = dict(
    points_earned=[1, 0, 3, 2],
    points_possible=12,
    feedback="Your submission was thrilling.",
)

@ddt
class TestApi(TestCase):

    def test_create_evaluation(self):
        create_submission(STUDENT_ITEM, ANSWER_ONE)
        evaluation = create_evaluation(
            "1",
            STUDENT_ITEM["student_id"],
            ASSESSMENT_DICT
        )
        self._assert_evaluation(evaluation, **ASSESSMENT_DICT)

    def test_get_evaluations(self):
        create_submission(STUDENT_ITEM, ANSWER_ONE)
        create_evaluation("1", STUDENT_ITEM["student_id"], ASSESSMENT_DICT)
        evaluations = get_evaluations("1")
        self.assertEqual(1, len(evaluations))
        self._assert_evaluation(evaluations[0], **ASSESSMENT_DICT)

    def test_student_finished_evaluating(self):
        self._create_student_and_submission("Bob", "Bob's answer")
        self._create_student_and_submission("Sally", "Sally's answer")
        self._create_student_and_submission("Jim", "Jim's answer")

        self.assertFalse(has_finished_required_evaluating("Tim", 3))
        create_evaluation("1", "Tim", ASSESSMENT_DICT)
        create_evaluation("2", "Tim", ASSESSMENT_DICT)
        self.assertFalse(has_finished_required_evaluating("Tim", 3))
        create_evaluation("3", "Tim", ASSESSMENT_DICT)
        self.assertTrue(has_finished_required_evaluating("Tim", 3))

    @raises(PeerEvaluationRequestError)
    def test_bad_configuration(self):
        has_finished_required_evaluating("Tim", -1)

    def test_get_submission_to_evaluate(self):
        monday = datetime.datetime(2007, 9, 12, 0, 0, 0, 0, pytz.UTC)
        tuesday = datetime.datetime(2007, 9, 13, 0, 0, 0, 0, pytz.UTC)
        wednesday = datetime.datetime(2007, 9, 15, 0, 0, 0, 0, pytz.UTC)
        thursday = datetime.datetime(2007, 9, 16, 0, 0, 0, 0, pytz.UTC)

        self._create_student_and_submission("Tim", "Tim's answer", monday)
        self._create_student_and_submission("Bob", "Bob's answer", tuesday)
        self._create_student_and_submission("Sally", "Sally's answer", wednesday)
        self._create_student_and_submission("Jim", "Jim's answer", thursday)

        submission = get_submission_to_evaluate(STUDENT_ITEM)
        self.assertIsNotNone(submission)
        self.assertEqual(submission["answer"], u"Bob's answer")
        self.assertEqual(submission["student_item"], 2)
        self.assertEqual(submission["attempt_number"], 1)

    @staticmethod
    def _create_student_and_submission(student, answer, date=None):
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student
        create_submission(new_student_item, answer, date)

    def _assert_evaluation(self, evaluation, points_earned, points_possible, feedback):
        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation["points_earned"], sum(points_earned))
        self.assertEqual(evaluation["points_possible"], points_possible)
        self.assertEqual(evaluation["feedback"], feedback)