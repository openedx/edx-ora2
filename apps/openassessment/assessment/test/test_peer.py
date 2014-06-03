# coding=utf-8
import datetime
import pytz

from django.db import DatabaseError, IntegrityError
from django.utils import timezone
from ddt import ddt, file_data
from mock import patch
from nose.tools import raises

from openassessment.test_utils import CacheResetTest
from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.models import (
    Assessment, AssessmentPart, AssessmentFeedback,
    PeerWorkflow, PeerWorkflowItem
)
from openassessment.workflow import api as workflow_api
from submissions import api as sub_api
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
ASSESSMENT_DICT = {
    'overall_feedback': u"这是中国",
    'criterion_feedback': {
        "giveup": u"𝓨𝓸𝓾 𝓼𝓱𝓸𝓾𝓵𝓭𝓷'𝓽 𝓰𝓲𝓿𝓮 𝓾𝓹!"
    },
    'options_selected': {
        "secret": "yes",
        u"ⓢⓐⓕⓔ": "no",
        "giveup": "reluctant",
        "singing": "no",
    },
}

# Answers are against RUBRIC_DICT -- this is worth 0 points
ASSESSMENT_DICT_FAIL = {
    'overall_feedback': u"fail",
    'criterion_feedback': {},
    'options_selected': {
        "secret": "no",
        u"ⓢⓐⓕⓔ": "no",
        "giveup": "unwilling",
        "singing": "yes",
    }
}

# Answers are against RUBRIC_DICT -- this is worth 12 points
ASSESSMENT_DICT_PASS = {
    'overall_feedback': u"这是中国",
    'criterion_feedback': {},
    'options_selected': {
        "secret": "yes",
        u"ⓢⓐⓕⓔ": "yes",
        "giveup": "eager",
        "singing": "no",
    }
}

# Answers are against RUBRIC_DICT -- this is worth 12 points
# Feedback text is one character over the limit.
LONG_FEEDBACK_TEXT = u"是" * Assessment.MAXSIZE + "."
ASSESSMENT_DICT_HUGE = {
    'overall_feedback': LONG_FEEDBACK_TEXT,
    'criterion_feedback': {
        "secret": LONG_FEEDBACK_TEXT,
        u"ⓢⓐⓕⓔ": LONG_FEEDBACK_TEXT,
        "giveup": LONG_FEEDBACK_TEXT,
        "singing": LONG_FEEDBACK_TEXT,
    },
    'options_selected': {
        "secret": "yes",
        u"ⓢⓐⓕⓔ": "yes",
        "giveup": "eager",
        "singing": "no",
    },
}

REQUIRED_GRADED = 5
REQUIRED_GRADED_BY = 3

MONDAY = datetime.datetime(2007, 9, 12, 0, 0, 0, 0, pytz.UTC)
TUESDAY = datetime.datetime(2007, 9, 13, 0, 0, 0, 0, pytz.UTC)
WEDNESDAY = datetime.datetime(2007, 9, 15, 0, 0, 0, 0, pytz.UTC)
THURSDAY = datetime.datetime(2007, 9, 16, 0, 0, 0, 0, pytz.UTC)

STEPS = ['peer', 'self']

@ddt
class TestPeerApi(CacheResetTest):
    """
    Tests for the peer assessment API functions.
    """

    CREATE_ASSESSMENT_NUM_QUERIES = 60

    def test_create_assessment_points(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], 1)

        with self.assertNumQueries(self.CREATE_ASSESSMENT_NUM_QUERIES):
            assessment = peer_api.create_assessment(
                bob_sub["uuid"],
                bob["student_id"],
                ASSESSMENT_DICT['options_selected'], dict(), "",
                RUBRIC_DICT,
                REQUIRED_GRADED_BY,
            )
        self.assertEqual(assessment["points_earned"], 6)
        self.assertEqual(assessment["points_possible"], 14)

    def test_create_assessment_with_feedback(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], 1)

        # Creating feedback per criterion should need one additional query to update
        # for each criterion that has feedback.
        with self.assertNumQueries(self.CREATE_ASSESSMENT_NUM_QUERIES + 1):
            assessment = peer_api.create_assessment(
                bob_sub["uuid"],
                bob["student_id"],
                ASSESSMENT_DICT['options_selected'],
                ASSESSMENT_DICT['criterion_feedback'],
                ASSESSMENT_DICT['overall_feedback'],
                RUBRIC_DICT,
                REQUIRED_GRADED_BY,
            )
        self.assertEqual(assessment["feedback"], ASSESSMENT_DICT["overall_feedback"])

        # The parts are not guaranteed to be in any particular order,
        # so we need to iterate through and check them by name.
        # If we haven't explicitly set feedback for the criterion, expect
        # that it defaults to an empty string.
        for part in assessment['parts']:
            criterion_name = part['option']['criterion']['name']
            expected_feedback = ASSESSMENT_DICT['criterion_feedback'].get(criterion_name, "")
            self.assertEqual(part['feedback'], expected_feedback)

    def test_create_assessment_unknown_criterion_feedback(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], 1)

        # Create an assessment where the criterion feedback uses
        # a criterion name that isn't in the rubric.
        assessment = peer_api.create_assessment(
            bob_sub["uuid"],
            bob["student_id"],
            ASSESSMENT_DICT['options_selected'],
            {'unknown': 'Unknown criterion has feedback!'},
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # The criterion feedback should be ignored
        for part_num in range(3):
            self.assertEqual(assessment["parts"][part_num]["feedback"], "")

    def test_create_huge_overall_feedback_error(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], 1)

        # Huge overall feedback text
        assessment_dict = peer_api.create_assessment(
            bob_sub["uuid"],
            bob["student_id"],
            ASSESSMENT_DICT_HUGE['options_selected'],
            dict(),
            ASSESSMENT_DICT_HUGE['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # The assessment feedback text should be truncated
        self.assertEqual(len(assessment_dict['feedback']), Assessment.MAXSIZE)

        # The length of the feedback text in the database should
        # equal what we got from the API.
        assessment = Assessment.objects.get()
        self.assertEqual(len(assessment.feedback), Assessment.MAXSIZE)

    def test_create_huge_per_criterion_feedback_error(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], 1)

        # Huge per-criterion feedback text
        assessment = peer_api.create_assessment(
            bob_sub["uuid"],
            bob["student_id"],
            ASSESSMENT_DICT_HUGE['options_selected'],
            ASSESSMENT_DICT_HUGE['criterion_feedback'],
            "",
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # Verify that the feedback has been truncated
        for part in assessment['parts']:
            self.assertEqual(len(part['feedback']), Assessment.MAXSIZE)

        # Verify that the feedback in the database matches what we got back from the API
        for part in AssessmentPart.objects.all():
            self.assertEqual(len(part.feedback), Assessment.MAXSIZE)

    @file_data('data/valid_assessments.json')
    def test_get_assessments(self, assessment_dict):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob_sub['uuid'], 3)
        peer_api.create_assessment(
            bob_sub["uuid"],
            bob["student_id"],
            assessment_dict['options_selected'],
            assessment_dict['criterion_feedback'],
            assessment_dict['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        assessments = peer_api.get_assessments(sub["uuid"], scored_only=False)
        self.assertEqual(1, len(assessments))

    @file_data('data/valid_assessments.json')
    def test_get_assessments_with_date(self, assessment_dict):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob_sub['uuid'], 3)
        peer_api.create_assessment(
            bob_sub["uuid"],
            bob["student_id"],
            assessment_dict['options_selected'],
            assessment_dict['criterion_feedback'],
            assessment_dict['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
            MONDAY,
        )
        assessments = peer_api.get_assessments(sub["uuid"], scored_only=False)
        self.assertEqual(1, len(assessments))
        self.assertEqual(assessments[0]["scored_at"], MONDAY)

    def test_has_finished_evaluation(self):
        """
        Verify unfinished assessments do not get counted when determining a
        complete workflow.
        """
        tim_sub, _ = self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob_sub['uuid'], 1)
        self.assertEqual(sub["uuid"], tim_sub["uuid"])
        finished, count = peer_api.has_finished_required_evaluating(bob_sub['uuid'], 1)
        self.assertFalse(finished)
        self.assertEqual(count, 0)
        peer_api.create_assessment(
            bob_sub["uuid"], bob["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            1,
        )
        finished, count = peer_api.has_finished_required_evaluating(bob_sub['uuid'], 1)
        self.assertTrue(finished)
        self.assertEqual(count, 1)

    def test_peer_leases_same_submission(self):
        """
        Tests the scenario where a student pulls a peer's submission for
        assessment, lets the lease expire, then pulls the same peer's submission
        a second time.

        This creates two similar PeerWorkflowItems in the database, and when
        completing the assessment, the latest PeerWorkflowItem should be
        updated.
        """
        yesterday = timezone.now() - datetime.timedelta(days=1)
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")
        self._create_student_and_submission("Bob", "Bob's answer")
        self._create_student_and_submission("Sally", "Sally's answer")
        sub = peer_api.get_submission_to_assess(tim_sub['uuid'], REQUIRED_GRADED)
        self.assertEqual(u"Bob's answer", sub['answer'])

        # And now we cheat; we want to set the clock back such that the lease
        # on this PeerWorkflowItem has expired.
        pwis = PeerWorkflowItem.objects.filter(submission_uuid=sub['uuid'])
        self.assertEqual(len(pwis), 1)
        pwis[0].started_at = yesterday
        pwis[0].save()

        sub = peer_api.get_submission_to_assess(tim_sub['uuid'], REQUIRED_GRADED)
        self.assertEqual(u"Bob's answer", sub['answer'])

        peer_api.create_assessment(
            tim_sub["uuid"], tim["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        pwis = PeerWorkflowItem.objects.filter(submission_uuid=sub['uuid'])
        self.assertEqual(len(pwis), 1)
        self.assertNotEqual(pwis[0].started_at, yesterday)

    def test_peer_workflow_integrity_error(self):
        tim_sub, __ = self._create_student_and_submission("Tim", "Tim's answer")
        with patch.object(PeerWorkflow.objects, "get_or_create") as mock_peer:
            mock_peer.side_effect = IntegrityError("Oh no!")
            # This should not raise an exception
            peer_api.create_peer_workflow(tim_sub["uuid"])

    @raises(peer_api.PeerAssessmentWorkflowError)
    def test_no_submission_found_closing_assessment(self):
        """
        Confirm the appropriate error is raised when no submission is found
        open for assessment, when submitting an assessment.
        """
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        peer_api.create_assessment(
            tim_sub["uuid"], tim["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

    def test_peer_assessment_workflow(self):
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sally_sub, sally = self._create_student_and_submission("Sally", "Sally's answer")
        jim_sub, jim = self._create_student_and_submission("Jim", "Jim's answer")
        self._create_student_and_submission("Buffy", "Buffy's answer")
        self._create_student_and_submission("Xander", "Xander's answer")

        # Tim should not have a score, because he has not evaluated enough
        # peer submissions.
        requirements = {
            "peer": {
                "must_grade": REQUIRED_GRADED,
                "must_be_graded_by": REQUIRED_GRADED_BY,
            }
        }
        score = workflow_api.get_workflow_for_submission(
            tim_sub["uuid"], requirements
        )["score"]
        self.assertIsNone(score)

        for i in range(5):
            self.assertEquals((False, i), peer_api.has_finished_required_evaluating(tim_sub['uuid'], REQUIRED_GRADED))
            sub = peer_api.get_submission_to_assess(tim_sub['uuid'], REQUIRED_GRADED)
            peer_api.create_assessment(
                tim_sub["uuid"], tim["student_id"],
                ASSESSMENT_DICT['options_selected'],
                ASSESSMENT_DICT['criterion_feedback'],
                ASSESSMENT_DICT['overall_feedback'],
                RUBRIC_DICT,
                REQUIRED_GRADED_BY,
            )

        self.assertEquals((True, 5), peer_api.has_finished_required_evaluating(tim_sub['uuid'], REQUIRED_GRADED))

        # Tim should not have a score, because his submission does not have
        # enough assessments.
        self.assertIsNone(sub_api.get_score(STUDENT_ITEM))

        sub = peer_api.get_submission_to_assess(bob_sub['uuid'], REQUIRED_GRADED)
        self.assertEqual(sub["uuid"], tim_sub["uuid"])
        peer_api.create_assessment(
            bob_sub["uuid"], bob["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        sub = peer_api.get_submission_to_assess(sally_sub['uuid'], REQUIRED_GRADED)
        self.assertEqual(sub["uuid"], tim_sub["uuid"])
        peer_api.create_assessment(
            sally_sub["uuid"], sally["student_id"],
            ASSESSMENT_DICT_FAIL['options_selected'],
            ASSESSMENT_DICT_FAIL['criterion_feedback'],
            ASSESSMENT_DICT_FAIL['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        sub = peer_api.get_submission_to_assess(jim_sub['uuid'], REQUIRED_GRADED)
        self.assertEqual(sub["uuid"], tim_sub["uuid"])
        peer_api.create_assessment(
            jim_sub["uuid"], jim["student_id"],
            ASSESSMENT_DICT_PASS['options_selected'],
            ASSESSMENT_DICT_PASS['criterion_feedback'],
            ASSESSMENT_DICT_PASS['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # Tim has met the critera, and should now be complete.
        requirements = {
            'must_grade': REQUIRED_GRADED,
            'must_be_graded_by': REQUIRED_GRADED_BY
        }
        self.assertTrue(peer_api.submitter_is_finished(tim_sub["uuid"], requirements))

    def test_completeness(self):
        """
        Verify that a submission in the peer workflow is only marked complete
        when we intend it to be. Incomplete assessments should never be
        included in a grade.
        """
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sally_sub, sally = self._create_student_and_submission("Sally", "Sally's answer")
        jim_sub, jim = self._create_student_and_submission("Jim", "Jim's answer")
        self._create_student_and_submission("Buffy", "Buffy's answer")
        self._create_student_and_submission("Xander", "Xander's answer")

        # Tim should not have a score, because he has not evaluated enough
        # peer submissions.
        requirements = {
            "peer": {
                "must_grade": REQUIRED_GRADED,
                "must_be_graded_by": REQUIRED_GRADED_BY,
                }
        }
        score = workflow_api.get_workflow_for_submission(
            tim_sub["uuid"], requirements
        )["score"]
        self.assertIsNone(score)

        # Bob and Sally pull Tim's submission for peer assessment, but do not
        # grade him right away.
        sub = peer_api.get_submission_to_assess(bob_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(sub["uuid"], tim_sub["uuid"])

        sub = peer_api.get_submission_to_assess(sally_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(sub["uuid"], tim_sub["uuid"])

        # Jim pulls Tim's submission, then grades it immediately.
        sub = peer_api.get_submission_to_assess(jim_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(sub["uuid"], tim_sub["uuid"])

        peer_api.create_assessment(
            jim_sub["uuid"], jim["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # Tim should have no score.
        score = workflow_api.get_workflow_for_submission(
            tim_sub["uuid"], requirements
        )["score"]
        self.assertIsNone(score)

        # Tim's workflow should not be fully graded
        self.assertIsNone(PeerWorkflow.objects.get(student_id=tim["student_id"]).grading_completed_at)

        peer_api.create_assessment(
            bob_sub["uuid"], bob["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        peer_api.create_assessment(
            sally_sub["uuid"], sally["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # Tim should not have a score since he did not grade peers..
        score = workflow_api.get_workflow_for_submission(
            tim_sub["uuid"], requirements
        )["score"]
        self.assertIsNone(score)

        # Tim's workflow has enough grades.
        self.assertIsNotNone(PeerWorkflow.objects.get(student_id=tim["student_id"]).grading_completed_at)

    def test_complex_peer_assessment_workflow(self):
        """
        Intended to mimic a more complicated scenario where people do not
        necessarily always finish their assessments.

        1) Angel submits
        2) Angel waits for Peer Assessments
        3) Bob submits and pulls Angel's submission but never reviews it.
        4) Sally submits
        5) Sally pulls Angel's Submission but never reviews it.
        6) Jim submits
        7) Jim also doesn't care about Angel and does not bother to review.
        8) Buffy comes along and she submits
        9) Buffy cares about Angel, but she won't get Angel's submission;
            it's held by Bob, Sally, and Jim.
        10) Buffy goes on to review Bob, Sally, and Jim, but needs two more.
        11) Xander comes along and submits.
        12) Xander means well, so Xander grades Bob, Sally, and Jim, but gets
            lazy and doesn't grade Buffy when her submission comes along.
        13) Buffy is waiting in the wings. She pulls Xander's submission and
            grades it.
        14) Spike submits.
        15) Spike reviews Bob, Sally, Jim, Buffy, and Xander.
        16) Buffy reviews Spike
        17) Willow comes along and submits
        18) Willow goes to grade, and should get Xander
        19) Xander comes back and gets Buffy's submission, and grades it.
        20) Buffy should now have a grade.
        """

        # Buffy should not have a score, because she has not evaluated enough
        # peer submissions.
        requirements = {
            "peer": {
                "must_grade": REQUIRED_GRADED,
                "must_be_graded_by": REQUIRED_GRADED_BY,
            }
        }

        # 1) Angel Submits
        angel_sub, _ = self._create_student_and_submission("Angel", "Angel's answer")

        # 2) Angel waits for peers
        sub = peer_api.get_submission_to_assess(angel_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertIsNone(sub)
        # 3) Bob submits
        bob_sub, _ = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(angel_sub["uuid"], sub["uuid"])

        # 4) Sally submits
        sally_sub, _ = self._create_student_and_submission("Sally", "Sally's answer")

        # 5) Sally pulls Angel's Submission but never reviews it.
        sub = peer_api.get_submission_to_assess(sally_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(angel_sub["uuid"], sub["uuid"])

        # 6) Jim submits
        jim_sub, _ = self._create_student_and_submission("Jim", "Jim's answer")

        # 7) Jim also doesn't care about Angel and does not bother to review.
        sub = peer_api.get_submission_to_assess(jim_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(angel_sub["uuid"], sub["uuid"])

        # 8) Buffy comes along and she submits
        buffy_sub, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")

        # 9) Buffy cares about Angel, but she won't get Angel's submission;
        # it's held by Bob, Sally, and Jim.
        sub = peer_api.get_submission_to_assess(buffy_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(bob_sub["uuid"], sub["uuid"])

        # 10) Buffy goes on to review Bob, Sally, and Jim, but needs two more.
        peer_api.create_assessment(
            buffy_sub["uuid"], buffy["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        sub = peer_api.get_submission_to_assess(buffy_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(sally_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            buffy_sub["uuid"], buffy["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        sub = peer_api.get_submission_to_assess(buffy_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(jim_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            buffy_sub["uuid"], buffy["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # 11) Xander comes along and submits.
        xander_sub, xander = self._create_student_and_submission("Xander", "Xander's answer")

        # 12) Xander means well, so Xander grades Bob, Sally, and Jim, but gets
        # lazy and doesn't grade Buffy when her submission comes along.
        sub = peer_api.get_submission_to_assess(xander_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(bob_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            xander_sub["uuid"], xander["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        sub = peer_api.get_submission_to_assess(xander_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(sally_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            xander_sub["uuid"], xander["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        sub = peer_api.get_submission_to_assess(xander_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(jim_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            xander_sub["uuid"], xander["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # 13) Buffy is waiting in the wings. She pulls Xander's submission and
        # grades it.
        sub = peer_api.get_submission_to_assess(buffy_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(xander_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            buffy_sub["uuid"], buffy["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # 14) Spike submits.
        spike_sub, spike = self._create_student_and_submission("Spike", "Spike's answer")

        # 15) Spike reviews Bob, Sally, Jim, Buffy, and Xander.
        sub = peer_api.get_submission_to_assess(spike_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(bob_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            spike_sub["uuid"], spike["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,

        )
        sub = peer_api.get_submission_to_assess(spike_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(sally_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            spike_sub["uuid"], spike["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        sub = peer_api.get_submission_to_assess(spike_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(jim_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            spike_sub["uuid"], spike["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        sub = peer_api.get_submission_to_assess(spike_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(buffy_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            spike_sub["uuid"], spike["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        sub = peer_api.get_submission_to_assess(spike_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(xander_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            spike_sub["uuid"], spike["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # 16) Buffy reviews Spike
        sub = peer_api.get_submission_to_assess(buffy_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(spike_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            buffy_sub["uuid"], buffy["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # 17) Willow comes along and submits
        willow_sub, willow = self._create_student_and_submission("Willow", "Willow's answer")

        # 18) Willow goes to grade, and should get Buffy
        sub = peer_api.get_submission_to_assess(willow_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(buffy_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            willow_sub["uuid"], willow["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # 19) Xander comes back and gets Buffy's submission, and grades it.
        sub = peer_api.get_submission_to_assess(xander_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEquals(buffy_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            xander_sub["uuid"], xander["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # 20) Buffy should now have a grade.
        requirements = {
            'must_grade': REQUIRED_GRADED,
            'must_be_graded_by': REQUIRED_GRADED_BY
        }
        self.assertTrue(peer_api.submitter_is_finished(buffy_sub["uuid"], requirements))

    def test_get_submitted_assessments(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], REQUIRED_GRADED_BY)
        assessment = peer_api.create_assessment(
            bob_sub["uuid"],
            bob["student_id"],
            ASSESSMENT_DICT['options_selected'], dict(), "",
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        self.assertEqual(assessment["points_earned"], 6)
        self.assertEqual(assessment["points_possible"], 14)
        submitted_assessments = peer_api.get_submitted_assessments(bob_sub["uuid"], scored_only=True)
        self.assertEqual(0, len(submitted_assessments))

        submitted_assessments = peer_api.get_submitted_assessments(bob_sub["uuid"], scored_only=False)
        self.assertEqual(1, len(submitted_assessments))

    def test_get_submitted_assessments_with_bad_submission(self):
        submitted_assessments = peer_api.get_submitted_assessments("bad-uuid", scored_only=True)
        self.assertEqual(0, len(submitted_assessments))

    def test_find_active_assessments(self):
        buffy_answer, _ = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_answer, _ = self._create_student_and_submission("Xander", "Xander's answer")

        # Check for a workflow for Buffy.
        buffy_workflow = PeerWorkflow.get_by_submission_uuid(buffy_answer['uuid'])
        self.assertIsNotNone(buffy_workflow)

        # Check to see if Buffy is actively reviewing Xander's submission.
        # She isn't so we should get back no uuid.
        submission_uuid = buffy_workflow.find_active_assessments()
        self.assertIsNone(submission_uuid)

        # Buffy is going to review Xander's submission, so create a workflow
        # item for Buffy.
        PeerWorkflow.create_item(buffy_workflow, xander_answer["uuid"])

        # Check to see if Buffy is still actively reviewing Xander's submission.
        submission_uuid = buffy_workflow.find_active_assessments()
        self.assertEqual(xander_answer["uuid"], submission_uuid)

    def test_get_workflow_by_uuid(self):
        buffy_answer, _ = self._create_student_and_submission("Buffy", "Buffy's answer")
        self._create_student_and_submission("Xander", "Xander's answer")
        self._create_student_and_submission("Willow", "Willow's answer")
        buffy_answer_two, _ = self._create_student_and_submission("Buffy", "Buffy's answer")

        workflow = PeerWorkflow.get_by_submission_uuid(buffy_answer_two['uuid'])
        self.assertNotEqual(buffy_answer["uuid"], workflow.submission_uuid)
        self.assertEqual(buffy_answer_two["uuid"], workflow.submission_uuid)

    def test_get_submission_for_review(self):
        buffy_answer, _ = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_answer, _ = self._create_student_and_submission("Xander", "Xander's answer")
        self._create_student_and_submission("Willow", "Willow's answer")

        buffy_workflow = PeerWorkflow.get_by_submission_uuid(buffy_answer['uuid'])

        # Get the next submission for review
        submission_uuid = buffy_workflow.get_submission_for_review(3)
        self.assertEqual(xander_answer["uuid"], submission_uuid)

    def test_get_submission_for_over_grading(self):
        buffy_answer, _ = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_answer, _ = self._create_student_and_submission("Xander", "Xander's answer")
        willow_answer, _ = self._create_student_and_submission("Willow", "Willow's answer")

        buffy_workflow = PeerWorkflow.get_by_submission_uuid(buffy_answer['uuid'])
        xander_workflow = PeerWorkflow.get_by_submission_uuid(xander_answer['uuid'])
        willow_workflow = PeerWorkflow.get_by_submission_uuid(willow_answer['uuid'])

        # Get a bunch of workflow items opened up.
        PeerWorkflow.create_item(buffy_workflow, xander_answer["uuid"])
        PeerWorkflow.create_item(willow_workflow, xander_answer["uuid"])
        PeerWorkflow.create_item(xander_workflow, xander_answer["uuid"])
        PeerWorkflow.create_item(buffy_workflow, willow_answer["uuid"])
        PeerWorkflow.create_item(xander_workflow, willow_answer["uuid"])

        # Get the next submission for review
        submission_uuid = xander_workflow.get_submission_for_over_grading()

        if not (buffy_answer["uuid"] == submission_uuid or willow_answer["uuid"] == submission_uuid):
            self.fail("Submission was not Buffy or Willow's.")

    def test_create_feedback_on_an_assessment(self):
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], 1)
        assessment = peer_api.create_assessment(
            bob_sub["uuid"],
            bob["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        peer_api.get_submission_to_assess(tim_sub['uuid'], 1)
        peer_api.create_assessment(
            tim_sub["uuid"],
            tim["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        peer_api.get_score(
            tim_sub["uuid"],
            {
                'must_grade': 1,
                'must_be_graded_by': 1
            }
        )
        feedback = peer_api.get_assessment_feedback(tim_sub['uuid'])
        self.assertIsNone(feedback)
        peer_api.set_assessment_feedback(
            {
                'submission_uuid': tim_sub['uuid'],
                'feedback_text': 'Bob is a jerk!',
                'options': [
                    'I disliked this assessment',
                    'I felt this assessment was unfair',
                ]
            }
        )
        saved_feedback = peer_api.get_assessment_feedback(tim_sub['uuid'])
        self.assertIsNot(saved_feedback, None)
        self.assertEquals(saved_feedback['submission_uuid'], assessment['submission_uuid'])
        self.assertEquals(saved_feedback['feedback_text'], 'Bob is a jerk!')
        self.assertItemsEqual(saved_feedback['options'], [
            {'text': 'I disliked this assessment'},
            {'text': 'I felt this assessment was unfair'},
        ])
        self.assertEquals(saved_feedback["assessments"][0]["submission_uuid"], assessment["submission_uuid"])

    def test_close_active_assessment(self):
        buffy_answer, _ = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_answer, _ = self._create_student_and_submission("Xander", "Xander's answer")

        # Create a workflow for Buffy.
        buffy_workflow = PeerWorkflow.get_by_submission_uuid(buffy_answer['uuid'])

        # Get a workflow item opened up.
        submission = peer_api.get_submission_to_assess(buffy_answer['uuid'], 3)

        self.assertEqual(xander_answer["uuid"], submission["uuid"])

        assessment_dict = peer_api.create_assessment(
            buffy_answer["uuid"], "Buffy",
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        assessment = Assessment.objects.filter(
            scorer_id=assessment_dict["scorer_id"],
            scored_at=assessment_dict["scored_at"])[0]
        buffy_workflow.close_active_assessment(xander_answer["uuid"], assessment, REQUIRED_GRADED_BY)

        item = PeerWorkflowItem.objects.get(submission_uuid=xander_answer['uuid'])
        self.assertEqual(xander_answer["uuid"], submission["uuid"])
        self.assertIsNotNone(item.assessment)

    @patch.object(PeerWorkflowItem.objects, "filter")
    @raises(peer_api.PeerAssessmentInternalError)
    def test_get_submitted_assessments_error(self, mock_filter):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], REQUIRED_GRADED_BY)
        mock_filter.side_effect = DatabaseError("Oh no.")
        submitted_assessments = peer_api.get_submitted_assessments(bob_sub["uuid"], scored_only=False)
        self.assertEqual(1, len(submitted_assessments))

    @patch.object(PeerWorkflow.objects, 'raw')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_failure_to_get_review_submission(self, mock_filter):
        tim_answer, _ = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        tim_workflow = PeerWorkflow.get_by_submission_uuid(tim_answer['uuid'])
        mock_filter.side_effect = DatabaseError("Oh no.")
        tim_workflow.get_submission_for_review(3)

    @patch.object(AssessmentFeedback.objects, 'get')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_get_assessment_feedback_error(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Oh no.")
        tim_answer, tim = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        peer_api.get_assessment_feedback(tim_answer['uuid'])

    @patch.object(PeerWorkflowItem, 'get_scored_assessments')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_set_assessment_feedback_error(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Oh no.")
        tim_answer, _ = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        peer_api.set_assessment_feedback({'submission_uuid': tim_answer['uuid']})

    @patch.object(AssessmentFeedback, 'save')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_set_assessment_feedback_error_on_save(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Oh no.")
        tim_answer, _ = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        peer_api.set_assessment_feedback(
            {
                'submission_uuid': tim_answer['uuid'],
                'feedback_text': 'Boo',
            }
        )

    @patch.object(AssessmentFeedback, 'save')
    @raises(peer_api.PeerAssessmentRequestError)
    def test_set_assessment_feedback_error_on_huge_save(self, mock_filter):
        tim_answer, _ = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        peer_api.set_assessment_feedback(
            {
                'submission_uuid': tim_answer['uuid'],
                'feedback_text': 'Boo'*AssessmentFeedback.MAXSIZE,
            }
        )

    @patch.object(PeerWorkflow.objects, 'get')
    @raises(peer_api.PeerAssessmentWorkflowError)
    def test_failure_to_get_latest_workflow(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Oh no.")
        tim_answer, _ = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        PeerWorkflow.get_by_submission_uuid(tim_answer['uuid'])

    @patch.object(PeerWorkflow.objects, 'get_or_create')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_create_workflow_error(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Oh no.")
        self._create_student_and_submission("Tim", "Tim's answer", MONDAY)

    @patch.object(PeerWorkflow.objects, 'get_or_create')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_create_workflow_item_error(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Oh no.")
        tim_answer, tim = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        PeerWorkflow.create_item(tim, tim_answer['uuid'])

    def test_get_submission_to_evaluate(self):
        submission, __ = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        self._create_student_and_submission("Bob", "Bob's answer", TUESDAY)
        self._create_student_and_submission(
            "Sally", "Sally's answer", WEDNESDAY
        )
        self._create_student_and_submission("Jim", "Jim's answer", THURSDAY)

        submission = peer_api.get_submission_to_assess(submission['uuid'], 3)
        self.assertIsNotNone(submission)
        self.assertEqual(submission["answer"], u"Bob's answer")
        self.assertEqual(submission["student_item"], 2)
        self.assertEqual(submission["attempt_number"], 1)

    def test_no_submissions_to_evaluate_for_tim(self):
        submission, __ = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        submission = peer_api.get_submission_to_assess(submission['uuid'], 3)
        self.assertIsNone(submission)

    def test_get_max_scores(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob_sub['uuid'], 1)
        assessment = peer_api.create_assessment(
            bob_sub["uuid"], bob["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            1
        )

        max_scores = peer_api.get_rubric_max_scores(sub["uuid"])
        self.assertEqual(max_scores['secret'], 1)
        self.assertEqual(max_scores['giveup'], 10)

    @raises(peer_api.PeerAssessmentWorkflowError)
    def test_no_open_assessment(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.create_assessment(
            bob_sub['uuid'], bob['student_id'],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            1
        )

    @patch.object(Assessment.objects, 'filter')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_max_score_db_error(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Bad things happened")
        tim, _ = self._create_student_and_submission("Tim", "Tim's answer")
        peer_api.get_rubric_max_scores(tim["uuid"])

    @patch.object(PeerWorkflow.objects, 'get')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_median_score_db_error(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Bad things happened")
        tim, _ = self._create_student_and_submission("Tim", "Tim's answer")
        peer_api.get_assessment_median_scores(tim["uuid"])

    @patch.object(PeerWorkflowItem, 'get_scored_assessments')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_get_assessments_db_error(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Bad things happened")
        tim, _ = self._create_student_and_submission("Tim", "Tim's answer")
        peer_api.get_assessments(tim["uuid"])

    @patch.object(PeerWorkflow.objects, 'get_or_create')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_error_on_assessment_creation(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Bad things happened")
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER_ONE)
        peer_api.create_peer_workflow(submission["uuid"])
        peer_api.create_assessment(
            submission["uuid"], STUDENT_ITEM["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
            MONDAY,
        )

    @patch.object(PeerWorkflowItem, 'get_scored_assessments')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_error_on_get_assessment(self, mock_filter):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob_sub['uuid'], 3)
        peer_api.create_assessment(
            bob_sub["uuid"], bob["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
            MONDAY,
        )
        mock_filter.side_effect = DatabaseError("Bad things happened")
        peer_api.get_assessments(sub["uuid"])

    def test_choose_score(self):
        self.assertEqual(0, Assessment.get_median_score([]))
        self.assertEqual(5, Assessment.get_median_score([5]))
        # average of 5, 6, rounded down.
        self.assertEqual(6, Assessment.get_median_score([5, 6]))
        self.assertEqual(14, Assessment.get_median_score([5, 6, 12, 16, 22, 53]))
        self.assertEqual(14, Assessment.get_median_score([6, 5, 12, 53, 16, 22]))
        self.assertEqual(16, Assessment.get_median_score([5, 6, 12, 16, 22, 53, 102]))
        self.assertEqual(16, Assessment.get_median_score([16, 6, 12, 102, 22, 53, 5]))

    @raises(peer_api.PeerAssessmentWorkflowError)
    def test_assess_before_submitting(self):
        # Create a submission for another student
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER_ONE)

        # Attempt to create the assessment from another student without first making a submission
        peer_api.create_assessment(
            submission["uuid"],
            "another_student",
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
            MONDAY,
        )

    def test_get_submission_to_assess_no_workflow(self):
        # Try to retrieve a submission to assess when the student
        # doing the assessment hasn't yet submitted.
        with self.assertRaises(peer_api.PeerAssessmentWorkflowError):
            peer_api.get_submission_to_assess("no_such_submission", "scorer ID")

    @staticmethod
    def _create_student_and_submission(student, answer, date=None):
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student
        submission = sub_api.create_submission(new_student_item, answer, date)
        peer_api.create_peer_workflow(submission["uuid"])
        workflow_api.create_workflow(submission["uuid"], STEPS)
        return submission, new_student_item
