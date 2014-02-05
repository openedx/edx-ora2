from ddt import ddt, file_data
from django.db import DatabaseError
import pytz
import datetime

from django.test import TestCase
from nose.tools import raises
from mock import patch

from openassessment.peer import api
from openassessment.peer.models import PeerEvaluation
from submissions.api import create_submission
from submissions.models import Submission
from submissions.tests.test_api import STUDENT_ITEM, ANSWER_ONE

ASSESSMENT_DICT = dict(
    points_earned=[1, 0, 3, 2],
    points_possible=12,
    feedback="Your submission was thrilling.",
)

MONDAY = datetime.datetime(2007, 9, 12, 0, 0, 0, 0, pytz.UTC)
TUESDAY = datetime.datetime(2007, 9, 13, 0, 0, 0, 0, pytz.UTC)
WEDNESDAY = datetime.datetime(2007, 9, 15, 0, 0, 0, 0, pytz.UTC)
THURSDAY = datetime.datetime(2007, 9, 16, 0, 0, 0, 0, pytz.UTC)


@ddt
class TestApi(TestCase):
    def test_create_evaluation(self):
        create_submission(STUDENT_ITEM, ANSWER_ONE)
        evaluation = api.create_evaluation(
            "1",
            STUDENT_ITEM["student_id"],
            ASSESSMENT_DICT
        )
        self._assert_evaluation(evaluation, **ASSESSMENT_DICT)

    @file_data('test_valid_evaluations.json')
    def test_get_evaluations(self, assessment_dict):
        create_submission(STUDENT_ITEM, ANSWER_ONE)
        api.create_evaluation("1", STUDENT_ITEM["student_id"], assessment_dict)
        evaluations = api.get_evaluations("1")
        self.assertEqual(1, len(evaluations))
        self._assert_evaluation(evaluations[0], **assessment_dict)

    @file_data('test_valid_evaluations.json')
    def test_get_evaluations_with_date(self, assessment_dict):
        create_submission(STUDENT_ITEM, ANSWER_ONE)
        api.create_evaluation(
            "1", STUDENT_ITEM["student_id"], assessment_dict, MONDAY
        )
        evaluations = api.get_evaluations("1")
        self.assertEqual(1, len(evaluations))
        self._assert_evaluation(evaluations[0], **assessment_dict)
        self.assertEqual(evaluations[0]["scored_at"], MONDAY)

    def test_student_finished_evaluating(self):
        self._create_student_and_submission("Bob", "Bob's answer")
        self._create_student_and_submission("Sally", "Sally's answer")
        self._create_student_and_submission("Jim", "Jim's answer")

        self.assertFalse(api.has_finished_required_evaluating("Tim", 3))
        api.create_evaluation("1", "Tim", ASSESSMENT_DICT)
        api.create_evaluation("2", "Tim", ASSESSMENT_DICT)
        self.assertFalse(api.has_finished_required_evaluating("Tim", 3))
        api.create_evaluation("3", "Tim", ASSESSMENT_DICT)
        self.assertTrue(api.has_finished_required_evaluating("Tim", 3))

    @raises(api.PeerEvaluationRequestError)
    def test_bad_configuration(self):
        api.has_finished_required_evaluating("Tim", -1)

    def test_get_submission_to_evaluate(self):
        self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        self._create_student_and_submission("Bob", "Bob's answer", TUESDAY)
        self._create_student_and_submission("Sally", "Sally's answer",
                                            WEDNESDAY)
        self._create_student_and_submission("Jim", "Jim's answer", THURSDAY)

        submission = api.get_submission_to_evaluate(STUDENT_ITEM)
        self.assertIsNotNone(submission)
        self.assertEqual(submission["answer"], u"Bob's answer")
        self.assertEqual(submission["student_item"], 2)
        self.assertEqual(submission["attempt_number"], 1)

    @raises(api.PeerEvaluationWorkflowError)
    def test_no_submissions_to_evaluate_for_tim(self):
        self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        api.get_submission_to_evaluate(STUDENT_ITEM)

    """
    Some Error Checking Tests against DB failures.
    """

    @patch.object(Submission.objects, 'get')
    @raises(api.PeerEvaluationInternalError)
    def test_error_on_evaluation_creation(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Bad things happened")
        create_submission(STUDENT_ITEM, ANSWER_ONE)
        api.create_evaluation(
            "1", STUDENT_ITEM["student_id"], ASSESSMENT_DICT, MONDAY
        )

    @patch.object(PeerEvaluation.objects, 'filter')
    @raises(api.PeerEvaluationInternalError)
    def test_error_on_get_evaluation(self, mock_filter):
        create_submission(STUDENT_ITEM, ANSWER_ONE)
        api.create_evaluation("1", STUDENT_ITEM["student_id"], ASSESSMENT_DICT,
                          MONDAY)
        mock_filter.side_effect = DatabaseError("Bad things happened")
        api.get_evaluations("1")

    @staticmethod
    def _create_student_and_submission(student, answer, date=None):
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student
        create_submission(new_student_item, answer, date)

    def _assert_evaluation(self, evaluation, points_earned, points_possible,
                           feedback):
        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation["points_earned"], sum(points_earned))
        self.assertEqual(evaluation["points_possible"], points_possible)
        self.assertEqual(evaluation["feedback"], feedback)