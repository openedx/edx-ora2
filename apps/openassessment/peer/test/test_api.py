# coding=utf-8
import datetime

from django.db import DatabaseError
from django.test import TestCase
import pytz

from ddt import ddt, file_data
from mock import patch
from nose.tools import raises

from openassessment.peer import api as peer_api
from openassessment.peer.models import Assessment
from submissions import api as sub_api
from submissions.models import Submission
from submissions.tests.test_api import STUDENT_ITEM, ANSWER_ONE

# Possible points: 14
RUBRIC_DICT = {
    "criteria": [
        {
            "name": "secret",
            "prompt": "Did the writer keep it secret?",
            "options": [
                {"name": "no", "points": "0", "explanation": ""},
                {"name": "yes", "points": "1", "explanation": ""},
            ]
        },
        {
            "name": u"ⓢⓐⓕⓔ",
            "prompt": "Did the writer keep it safe?",
            "options": [
                {"name": "no", "points": "0", "explanation": ""},
                {"name": "yes", "points": "1", "explanation": ""},
            ]
        },
        {
            "name": "giveup",
            "prompt": "How willing is the writer to give up the ring?",
            "options": [
                {
                    "name": "unwilling",
                    "points": "0",
                    "explanation": "Likely to use force to keep it."
                },
                {
                    "name": "reluctant",
                    "points": "3",
                    "explanation": "May argue, but will give it up voluntarily."
                },
                {
                    "name": "eager",
                    "points": "10",
                    "explanation": "Happy to give it up."
                }
            ]
        },
        {
            "name": "singing",
            "prompt": "Did the writer break into tedious elvish lyrics?",
            "options": [
                {"name": "no", "points": "2", "explanation": ""},
                {"name": "yes", "points": "0", "explanation": ""}
            ]
        },
    ]
}

# Answers are against RUBRIC_DICT -- this is worth 6 points
ASSESSMENT_DICT = dict(
    feedback=u"这是中国",
    options_selected={
        "secret": "yes",
        u"ⓢⓐⓕⓔ": "no",
        "giveup": "reluctant",
        "singing": "no",
    }
)

# Answers are against RUBRIC_DICT -- this is worth 0 points
ASSESSMENT_DICT_FAIL = dict(
    feedback=u"fail",
    options_selected={
        "secret": "no",
        u"ⓢⓐⓕⓔ": "no",
        "giveup": "unwilling",
        "singing": "yes",
    }
)

# Answers are against RUBRIC_DICT -- this is worth 12 points
ASSESSMENT_DICT_PASS = dict(
    feedback=u"这是中国",
    options_selected={
        "secret": "yes",
        u"ⓢⓐⓕⓔ": "yes",
        "giveup": "eager",
        "singing": "no",
    }
)

REQUIRED_GRADED = 5
REQUIRED_GRADED_BY = 3

MONDAY = datetime.datetime(2007, 9, 12, 0, 0, 0, 0, pytz.UTC)
TUESDAY = datetime.datetime(2007, 9, 13, 0, 0, 0, 0, pytz.UTC)
WEDNESDAY = datetime.datetime(2007, 9, 15, 0, 0, 0, 0, pytz.UTC)
THURSDAY = datetime.datetime(2007, 9, 16, 0, 0, 0, 0, pytz.UTC)


@ddt
class TestApi(TestCase):
    def test_create_assessment(self):
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        assessment = peer_api.create_assessment(
            submission["uuid"],
            STUDENT_ITEM["student_id"],
            REQUIRED_GRADED,
            REQUIRED_GRADED_BY,
            ASSESSMENT_DICT,
            RUBRIC_DICT,
        )
        self.assertEqual(assessment["points_earned"], 6)
        self.assertEqual(assessment["points_possible"], 14)

    @file_data('valid_assessments.json')
    def test_get_assessments(self, assessment_dict):
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        peer_api.create_assessment(
            submission["uuid"],
            STUDENT_ITEM["student_id"],
            REQUIRED_GRADED,
            REQUIRED_GRADED_BY,
            assessment_dict,
            RUBRIC_DICT,
        )
        assessments = peer_api.get_assessments(submission["uuid"])
        self.assertEqual(1, len(assessments))

    @file_data('valid_assessments.json')
    def test_get_assessments_with_date(self, assessment_dict):
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        peer_api.create_assessment(
            submission["uuid"],
            STUDENT_ITEM["student_id"],
            REQUIRED_GRADED,
            REQUIRED_GRADED_BY,
            assessment_dict,
            RUBRIC_DICT,
            MONDAY
        )
        assessments = peer_api.get_assessments(submission["uuid"])
        self.assertEqual(1, len(assessments))
        self.assertEqual(assessments[0]["scored_at"], MONDAY)

    def test_peer_assessment_workflow(self):
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

        self.assertEquals((False, 0), peer_api.has_finished_required_evaluating(STUDENT_ITEM, REQUIRED_GRADED))
        peer_api.create_assessment(
            bob["uuid"], "Tim", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )
        peer_api.create_assessment(
            sally["uuid"], "Tim", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )
        self.assertEquals((False, 2), peer_api.has_finished_required_evaluating(STUDENT_ITEM, REQUIRED_GRADED))

        peer_api.create_assessment(
            jim["uuid"], "Tim", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )
        self.assertEquals((False, 3), peer_api.has_finished_required_evaluating(STUDENT_ITEM, REQUIRED_GRADED))
        peer_api.create_assessment(
            buffy["uuid"], "Tim", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )
        self.assertEquals((False, 4), peer_api.has_finished_required_evaluating(STUDENT_ITEM, REQUIRED_GRADED))
        peer_api.create_assessment(
            xander["uuid"], "Tim", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )
        self.assertEquals((True, 5), peer_api.has_finished_required_evaluating(STUDENT_ITEM, REQUIRED_GRADED))

        # Tim should not have a score, because his submission does not have
        # enough assessments.
        scores = sub_api.get_score(STUDENT_ITEM)
        self.assertFalse(scores)

        peer_api.create_assessment(
            tim["uuid"], "Bob", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT, RUBRIC_DICT
        )
        peer_api.create_assessment(
            tim["uuid"], "Sally", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT_FAIL, RUBRIC_DICT
        )
        peer_api.create_assessment(
            tim["uuid"], "Jim", REQUIRED_GRADED, REQUIRED_GRADED_BY, ASSESSMENT_DICT_PASS, RUBRIC_DICT
        )

        # Tim has met the critera, and should now have a score.
        scores = sub_api.get_score(STUDENT_ITEM)
        self.assertTrue(scores)
        self.assertEqual(6, scores[0]["points_earned"])
        self.assertEqual(14, scores[0]["points_possible"])


    @raises(peer_api.PeerAssessmentRequestError)
    def test_bad_configuration(self):
        peer_api.has_finished_required_evaluating(STUDENT_ITEM, -1)

    def test_get_submission_to_evaluate(self):
        self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        self._create_student_and_submission("Bob", "Bob's answer", TUESDAY)
        self._create_student_and_submission(
            "Sally", "Sally's answer", WEDNESDAY
        )
        self._create_student_and_submission("Jim", "Jim's answer", THURSDAY)

        submission = peer_api.get_submission_to_assess(STUDENT_ITEM, 3)
        self.assertIsNotNone(submission)
        self.assertEqual(submission["answer"], u"Bob's answer")
        self.assertEqual(submission["student_item"], 2)
        self.assertEqual(submission["attempt_number"], 1)

    @raises(peer_api.PeerAssessmentWorkflowError)
    def test_no_submissions_to_evaluate_for_tim(self):
        self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        peer_api.get_submission_to_assess(STUDENT_ITEM, 3)

    @patch.object(Assessment.objects, 'filter')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_median_score_db_error(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Bad things happened")
        tim = self._create_student_and_submission("Tim", "Tim's answer")
        peer_api.get_assessment_median_scores(tim["uuid"], 3)

    @patch.object(Assessment.objects, 'filter')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_get_assessments_db_error(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Bad things happened")
        tim = self._create_student_and_submission("Tim", "Tim's answer")
        peer_api.get_assessments(tim["uuid"])

    @patch.object(Submission.objects, 'get')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_error_on_assessment_creation(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Bad things happened")
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        peer_api.create_assessment(
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
    def test_error_on_get_assessment(self, mock_filter):
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        peer_api.create_assessment(
            submission["uuid"],
            STUDENT_ITEM["student_id"],
            REQUIRED_GRADED,
            REQUIRED_GRADED_BY,
            ASSESSMENT_DICT,
            RUBRIC_DICT,
            MONDAY
        )
        mock_filter.side_effect = DatabaseError("Bad things happened")
        peer_api.get_assessments(submission["uuid"])

    def test_choose_score(self):
        self.assertEqual(0, Assessment.get_median_score([]))
        self.assertEqual(5, Assessment.get_median_score([5]))
        # average of 5, 6, rounded down.
        self.assertEqual(6, Assessment.get_median_score([5, 6]))
        self.assertEqual(14, Assessment.get_median_score([5, 6, 12, 16, 22, 53]))
        self.assertEqual(14, Assessment.get_median_score([6, 5, 12, 53, 16, 22]))
        self.assertEqual(16, Assessment.get_median_score([5, 6, 12, 16, 22, 53, 102]))
        self.assertEqual(16, Assessment.get_median_score([16, 6, 12, 102, 22, 53, 5]))

    @staticmethod
    def _create_student_and_submission(student, answer, date=None):
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student
        return sub_api.create_submission(new_student_item, answer, date)
