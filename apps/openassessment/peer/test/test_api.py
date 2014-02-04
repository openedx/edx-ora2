from ddt import ddt
from django.test import TestCase
from openassessment.peer.api import create_evaluation, get_evaluations
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

    def test_get_submission_to_evaluate(self):
        pass

    def test_concurrent_evaluators(self):
        pass

    def _assert_evaluation(self, evaluation, points_earned, points_possible, feedback):
        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation["points_earned"], sum(points_earned))
        self.assertEqual(evaluation["points_possible"], points_possible)
        self.assertEqual(evaluation["feedback"], feedback)