from ddt import ddt, file_data
from django.db import DatabaseError
import pytz
import datetime

from django.test import TestCase
from nose.tools import raises
from mock import patch

from openassessment.peer import api
from openassessment.peer.models import Assessment
from submissions import api as sub_api
from submissions.models import Submission
from submissions.tests.test_api import STUDENT_ITEM, ANSWER_ONE

ASSESSMENT_DICT = dict(
    points_earned=[1, 0, 3, 2],
    points_possible=14,
    feedback="Your submission was thrilling.",
    options_selected={
        "secret": "yes",
        "safe": "no",
        "giveup": "reluctant",
        "singing": "no",
    }
)

RUBRIC_DICT = dict(
    criteria=[
        dict(
            name="secret",
            prompt="Did the writer keep it secret?",
            options=[
                dict(name="no", points="0", explanation=""),
                dict(name="yes", points="1", explanation="")
            ]
        ),
        dict(
            name="safe",
            prompt="Did the writer keep it safe?",
            options=[
                dict(name="no", points="0", explanation=""),
                dict(name="yes", points="1", explanation="")
            ]
        ),
        dict(
            name="giveup",
            prompt="How willing is the writer to give up the ring?",
            options=[
                dict(
                    name="unwilling",
                    points="0",
                    explanation="Likely to use force to keep it."
                ),
                dict(
                    name="reluctant",
                    points="3",
                    explanation="May argue, but will give it up voluntarily."
                ),
                dict(
                    name="eager",
                    points="10",
                    explanation="Happy to give it up."
                )
            ]
        ),
        dict(
            name="singing",
            prompt="Did the writer break into tedious elvish lyrics?",
            options=[
                dict(name="no", points="2", explanation=""),
                dict(name="yes", points="0", explanation="")
            ]
        ),
    ]
)

REQUIRED_GRADED = 5
REQUIRED_GRADED_BY = 3

MONDAY = datetime.datetime(2007, 9, 12, 0, 0, 0, 0, pytz.UTC)
TUESDAY = datetime.datetime(2007, 9, 13, 0, 0, 0, 0, pytz.UTC)
WEDNESDAY = datetime.datetime(2007, 9, 15, 0, 0, 0, 0, pytz.UTC)
THURSDAY = datetime.datetime(2007, 9, 16, 0, 0, 0, 0, pytz.UTC)


@ddt
class TestApi(TestCase):
    def test_create_evaluation(self):
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        evaluation = api.create_assessment(
            submission["uuid"],
            STUDENT_ITEM["student_id"],
            REQUIRED_GRADED,
            REQUIRED_GRADED_BY,
            ASSESSMENT_DICT,
            RUBRIC_DICT,
        )
        self._assert_evaluation(evaluation, **ASSESSMENT_DICT)

    @file_data('test_valid_evaluations.json')
    def test_get_evaluations(self, assessment_dict):
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        api.create_assessment(
            submission["uuid"],
            STUDENT_ITEM["student_id"],
            REQUIRED_GRADED,
            REQUIRED_GRADED_BY,
            assessment_dict,
            RUBRIC_DICT,
        )
        evaluations = api.get_assessments(submission["uuid"])
        self.assertEqual(1, len(evaluations))
        self._assert_evaluation(evaluations[0], **assessment_dict)

    @file_data('test_valid_evaluations.json')
    def test_get_evaluations_with_date(self, assessment_dict):
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        api.create_assessment(
            submission["uuid"],
            STUDENT_ITEM["student_id"],
            REQUIRED_GRADED,
            REQUIRED_GRADED_BY,
            assessment_dict,
            RUBRIC_DICT,
            MONDAY
        )
        evaluations = api.get_assessments(submission["uuid"])
        self.assertEqual(1, len(evaluations))
        self._assert_evaluation(evaluations[0], **assessment_dict)
        self.assertEqual(evaluations[0]["scored_at"], MONDAY)

    def test_peer_evaluation_workflow(self):
        tim = self._create_student_and_submission("Tim", "Tim's answer")
        bob = self._create_student_and_submission("Bob", "Bob's answer")
        sally = self._create_student_and_submission("Sally", "Sally's answer")
        jim = self._create_student_and_submission("Jim", "Jim's answer")
        buffy = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander = self._create_student_and_submission("Xander", "Xander's answer")

        # Tim should not have a score, because he has not evaluated enough
        # peer submissions.
        scores = sub_api.get_score(STUDENT_ITEM)
        self.assertFalse(scores)

        self.assertFalse(api.has_finished_required_evaluating("Tim", REQUIRED_GRADED))
        api.create_assessment(
            bob["uuid"], "Tim", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )
        api.create_assessment(
            sally["uuid"], "Tim", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )
        self.assertFalse(api.has_finished_required_evaluating("Tim", REQUIRED_GRADED))

        api.create_assessment(
            jim["uuid"], "Tim", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )
        self.assertFalse(api.has_finished_required_evaluating("Tim", REQUIRED_GRADED))
        api.create_evaluation(
            buffy["uuid"], "Tim", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )
        self.assertFalse(api.has_finished_required_evaluating("Tim", REQUIRED_GRADED))
        api.create_evaluation(
            xander["uuid"], "Tim", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )
        self.assertTrue(api.has_finished_required_evaluating("Tim", REQUIRED_GRADED))

        # Tim should not have a score, because his submission does not have
        # enough evaluations.
        scores = sub_api.get_score(STUDENT_ITEM)
        self.assertFalse(scores)

        api.create_assessment(
            tim["uuid"], "Bob", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )
        api.create_assessment(
            tim["uuid"], "Sally", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )
        api.create_assessment(
            tim["uuid"], "Jim", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )

        # Tim has met the critera, and should now have a score.
        scores = sub_api.get_score(STUDENT_ITEM)
        self.assertTrue(scores)
        self.assertEqual(6, scores[0]["points_earned"])
        self.assertEqual(12, scores[0]["points_possible"])


    @raises(api.PeerAssessmentRequestError)
    def test_bad_configuration(self):
        api.has_finished_required_evaluating("Tim", -1)

    def test_get_submission_to_evaluate(self):
        self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        self._create_student_and_submission("Bob", "Bob's answer", TUESDAY)
        self._create_student_and_submission(
            "Sally", "Sally's answer", WEDNESDAY
        )
        self._create_student_and_submission("Jim", "Jim's answer", THURSDAY)

        submission = api.get_submission_to_assess(STUDENT_ITEM, 3)
        self.assertIsNotNone(submission)
        self.assertEqual(submission["answer"], u"Bob's answer")
        self.assertEqual(submission["student_item"], 2)
        self.assertEqual(submission["attempt_number"], 1)

    @raises(api.PeerAssessmentWorkflowError)
    def test_no_submissions_to_evaluate_for_tim(self):
        self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        api.get_submission_to_assess(STUDENT_ITEM, 3)

    """
    Some Error Checking Tests against DB failures.
    """

    @patch.object(Submission.objects, 'get')
    @raises(api.PeerAssessmentInternalError)
    def test_error_on_evaluation_creation(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Bad things happened")
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        api.create_assessment(
            submission["uuid"],
            STUDENT_ITEM["student_id"],
            REQUIRED_GRADED,
            REQUIRED_GRADED_BY,
            ASSESSMENT_DICT,
            RUBRIC_DICT,
            MONDAY
        )

    @patch.object(Assessment.objects, 'filter')
    @raises(sub_api.SubmissionInternalError)
    def test_error_on_get_evaluation(self, mock_filter):
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        api.create_assessment(
            submission["uuid"],
            STUDENT_ITEM["student_id"],
            REQUIRED_GRADED,
            REQUIRED_GRADED_BY,
            ASSESSMENT_DICT,
            RUBRIC_DICT,
            MONDAY
        )
        mock_filter.side_effect = DatabaseError("Bad things happened")
        api.get_assessments(submission["uuid"])

    def test_choose_score(self):
        self.assertEqual(0, api._calculate_final_score([]))
        self.assertEqual(5, api._calculate_final_score([5]))
        # average of 5, 6, rounded down.
        self.assertEqual(6, api._calculate_final_score([5, 6]))
        self.assertEqual(14, api._calculate_final_score([5, 6, 12, 16, 22, 53]))
        self.assertEqual(14, api._calculate_final_score([6, 5, 12, 53, 16, 22]))
        self.assertEqual(16, api._calculate_final_score([5, 6, 12, 16, 22, 53, 102]))
        self.assertEqual(16, api._calculate_final_score([16, 6, 12, 102, 22, 53, 5]))


    @staticmethod
    def _create_student_and_submission(student, answer, date=None):
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student
        return sub_api.create_submission(new_student_item, answer, date)

    def _assert_evaluation(self, evaluation, points_earned, points_possible,
                           feedback, options_selected):
        print evaluation

        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation["points_earned"], sum(points_earned))
        self.assertEqual(evaluation["points_possible"], points_possible)
        # self.assertEqual(evaluation["feedback"], feedback)
