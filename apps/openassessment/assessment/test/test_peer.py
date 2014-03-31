# coding=utf-8
import datetime

from django.db import DatabaseError
import pytz

from ddt import ddt, file_data
from mock import patch
from nose.tools import raises

from openassessment.test_utils import CacheResetTest
from openassessment.assessment import peer_api
from openassessment.assessment.models import Assessment, PeerWorkflow, PeerWorkflowItem, AssessmentFeedback
from openassessment.workflow import api as workflow_api
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

# Answers are against RUBRIC_DICT -- this is worth 12 points
ASSESSMENT_DICT_PASS_HUGE = dict(
    feedback=u"这是中国" * Assessment.MAXSIZE,
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
class TestPeerApi(CacheResetTest):
    def test_create_assessment(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob, 1)
        assessment = peer_api.create_assessment(
            sub["uuid"],
            bob["student_id"],
            ASSESSMENT_DICT,
            RUBRIC_DICT,
        )
        self.assertEqual(assessment["points_earned"], 6)
        self.assertEqual(assessment["points_possible"], 14)
        self.assertEqual(assessment["feedback"], ASSESSMENT_DICT["feedback"])

    def test_create_huge_assessment_fails(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob, 1)
        with self.assertRaises(peer_api.PeerAssessmentRequestError):
            peer_api.create_assessment(
                sub["uuid"],
                bob["student_id"],
                ASSESSMENT_DICT_PASS_HUGE,
                RUBRIC_DICT,
            )

    @file_data('valid_assessments.json')
    def test_get_assessments(self, assessment_dict):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob, 3)
        peer_api.create_assessment(
            sub["uuid"],
            bob["student_id"],
            assessment_dict,
            RUBRIC_DICT,
        )
        assessments = peer_api.get_assessments(sub["uuid"], scored_only=False)
        self.assertEqual(1, len(assessments))

    @file_data('valid_assessments.json')
    def test_get_assessments_with_date(self, assessment_dict):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob, 3)
        peer_api.create_assessment(
            sub["uuid"],
            bob["student_id"],
            assessment_dict,
            RUBRIC_DICT,
            MONDAY
        )
        assessments = peer_api.get_assessments(sub["uuid"], scored_only=False)
        self.assertEqual(1, len(assessments))
        self.assertEqual(assessments[0]["scored_at"], MONDAY)

    def test_has_finished_evaluation(self):
        """
        Verify unfinished assessments do not get counted when determining a
        complete workflow.
        """
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob, REQUIRED_GRADED)
        self.assertEqual(sub["uuid"], tim_sub["uuid"])
        finished, count = peer_api.has_finished_required_evaluating(bob, 1)
        self.assertFalse(finished)
        self.assertEqual(count, 0)
        peer_api.create_assessment(
            sub["uuid"], bob["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )
        finished, count = peer_api.has_finished_required_evaluating(bob, 1)
        self.assertTrue(finished)
        self.assertEqual(count, 1)

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
            self.assertEquals((False, i), peer_api.has_finished_required_evaluating(STUDENT_ITEM, REQUIRED_GRADED))
            sub = peer_api.get_submission_to_assess(tim, REQUIRED_GRADED)
            peer_api.create_assessment(
                sub["uuid"], tim["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
            )

        self.assertEquals((True, 5), peer_api.has_finished_required_evaluating(STUDENT_ITEM, REQUIRED_GRADED))

        # Tim should not have a score, because his submission does not have
        # enough assessments.
        self.assertIsNone(sub_api.get_score(STUDENT_ITEM))

        sub = peer_api.get_submission_to_assess(bob, REQUIRED_GRADED)
        self.assertEqual(sub["uuid"], tim_sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], bob["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )

        sub = peer_api.get_submission_to_assess(sally, REQUIRED_GRADED)
        self.assertEqual(sub["uuid"], tim_sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], sally["student_id"], ASSESSMENT_DICT_FAIL, RUBRIC_DICT
        )

        sub = peer_api.get_submission_to_assess(jim, REQUIRED_GRADED)
        self.assertEqual(sub["uuid"], tim_sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], jim["student_id"], ASSESSMENT_DICT_PASS, RUBRIC_DICT
        )

        # Tim has met the critera, and should now be complete.
        requirements = {
            'must_grade': REQUIRED_GRADED,
            'must_be_graded_by': REQUIRED_GRADED_BY
        }
        self.assertTrue(peer_api.is_complete(tim_sub["uuid"], requirements))

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
        angel_sub, angel = self._create_student_and_submission("Angel", "Angel's answer")

        # 2) Angel waits for peers
        sub = peer_api.get_submission_to_assess(angel, REQUIRED_GRADED_BY)
        self.assertIsNone(sub)
        # 3) Bob submits
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob, REQUIRED_GRADED_BY)
        self.assertEquals(angel_sub["uuid"], sub["uuid"])

        # 4) Sally submits
        sally_sub, sally = self._create_student_and_submission("Sally", "Sally's answer")

        # 5) Sally pulls Angel's Submission but never reviews it.
        sub = peer_api.get_submission_to_assess(sally, REQUIRED_GRADED_BY)
        self.assertEquals(angel_sub["uuid"], sub["uuid"])

        # 6) Jim submits
        jim_sub, jim = self._create_student_and_submission("Jim", "Jim's answer")

        # 7) Jim also doesn't care about Angel and does not bother to review.
        sub = peer_api.get_submission_to_assess(jim, REQUIRED_GRADED_BY)
        self.assertEquals(angel_sub["uuid"], sub["uuid"])

        # 8) Buffy comes along and she submits
        buffy_sub, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")

        # 9) Buffy cares about Angel, but she won't get Angel's submission;
        # it's held by Bob, Sally, and Jim.
        sub = peer_api.get_submission_to_assess(buffy, REQUIRED_GRADED_BY)
        self.assertEquals(bob_sub["uuid"], sub["uuid"])

        # 10) Buffy goes on to review Bob, Sally, and Jim, but needs two more.
        peer_api.create_assessment(
            sub["uuid"], buffy["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )
        sub = peer_api.get_submission_to_assess(buffy, REQUIRED_GRADED_BY)
        self.assertEquals(sally_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], buffy["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )
        sub = peer_api.get_submission_to_assess(buffy, REQUIRED_GRADED_BY)
        self.assertEquals(jim_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], buffy["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )
        sub = peer_api.get_submission_to_assess(buffy, REQUIRED_GRADED_BY)
        self.assertIsNone(sub)

        # 11) Xander comes along and submits.
        xander_sub, xander = self._create_student_and_submission("Xander", "Xander's answer")

        # 12) Xander means well, so Xander grades Bob, Sally, and Jim, but gets
        # lazy and doesn't grade Buffy when her submission comes along.
        sub = peer_api.get_submission_to_assess(xander, REQUIRED_GRADED_BY)
        self.assertEquals(bob_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], xander["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )
        sub = peer_api.get_submission_to_assess(xander, REQUIRED_GRADED_BY)
        self.assertEquals(sally_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], xander["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )
        sub = peer_api.get_submission_to_assess(xander, REQUIRED_GRADED_BY)
        self.assertEquals(jim_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], xander["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )

        # Tim has met the critera, and should now have a score.
        # We patch the call to `self_api.is_complete()` simulate having completed a self-assessment.
        # TODO: currently, we need to import `self_api` within the `_is_self_complete` method
        # to avoid circular imports.  This means we can't patch self_api directly.
        from openassessment.workflow.models import AssessmentWorkflow
        with patch.object(AssessmentWorkflow, '_is_self_complete') as mock_complete:
            mock_complete.return_value = True
            score = workflow_api.get_workflow_for_submission(sub["uuid"], requirements)["score"]

        # 13) Buffy is waiting in the wings. She pulls Xander's submission and
        # grades it.
        sub = peer_api.get_submission_to_assess(buffy, REQUIRED_GRADED_BY)
        self.assertEquals(xander_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], buffy["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )

        # 14) Spike submits.
        spike_sub, spike = self._create_student_and_submission("Spike", "Spike's answer")

        # 15) Spike reviews Bob, Sally, Jim, Buffy, and Xander.
        sub = peer_api.get_submission_to_assess(spike, REQUIRED_GRADED_BY)
        self.assertEquals(bob_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], spike["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )
        sub = peer_api.get_submission_to_assess(spike, REQUIRED_GRADED_BY)
        self.assertEquals(sally_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], spike["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )
        sub = peer_api.get_submission_to_assess(spike, REQUIRED_GRADED_BY)
        self.assertEquals(jim_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], spike["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )
        sub = peer_api.get_submission_to_assess(spike, REQUIRED_GRADED_BY)
        self.assertEquals(buffy_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], spike["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )
        sub = peer_api.get_submission_to_assess(spike, REQUIRED_GRADED_BY)
        self.assertEquals(xander_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], spike["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )

        # 16) Buffy reviews Spike
        sub = peer_api.get_submission_to_assess(buffy, REQUIRED_GRADED_BY)
        self.assertEquals(spike_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], buffy["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )

        # 17) Willow comes along and submits
        willow_sub, willow = self._create_student_and_submission("Willow", "Willow's answer")

        # 18) Willow goes to grade, and should get Buffy
        sub = peer_api.get_submission_to_assess(willow, REQUIRED_GRADED_BY)
        self.assertEquals(buffy_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], willow["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )

        # 19) Xander comes back and gets Buffy's submission, and grades it.
        sub = peer_api.get_submission_to_assess(xander, REQUIRED_GRADED_BY)
        self.assertEquals(buffy_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            sub["uuid"], xander["student_id"], ASSESSMENT_DICT, RUBRIC_DICT
        )

        # 20) Buffy should now have a grade.
        requirements = {
            'must_grade': REQUIRED_GRADED,
            'must_be_graded_by': REQUIRED_GRADED_BY
        }
        self.assertTrue(peer_api.is_complete(buffy_sub["uuid"], requirements))

    def test_find_active_assessments(self):
        buffy_answer, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_answer, xander = self._create_student_and_submission("Xander", "Xander's answer")

        # Check for a workflow for Buffy.
        buffy_workflow = peer_api._get_latest_workflow(buffy)
        self.assertIsNotNone(buffy_workflow)

        # Check to see if Buffy is actively reviewing Xander's submission.
        # She isn't so we should get back no uuid.
        submission_uuid = peer_api._find_active_assessments(buffy_workflow)
        self.assertIsNone(submission_uuid)

        # Buffy is going to review Xander's submission, so create a workflow
        # item for Buffy.
        peer_api._create_peer_workflow_item(buffy_workflow, xander_answer["uuid"])

        # Check to see if Buffy is still actively reviewing Xander's submission.
        submission_uuid = peer_api._find_active_assessments(buffy_workflow)
        self.assertEqual(xander_answer["uuid"], submission_uuid)

    def test_get_latest_workflow(self):
        buffy_answer, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")
        self._create_student_and_submission("Xander", "Xander's answer")
        self._create_student_and_submission("Willow", "Willow's answer")
        buffy_answer_two, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")

        workflow = peer_api._get_latest_workflow(buffy)
        self.assertNotEqual(buffy_answer["uuid"], workflow.submission_uuid)
        self.assertEqual(buffy_answer_two["uuid"], workflow.submission_uuid)

    def test_get_submission_for_review(self):
        buffy_answer, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_answer, xander = self._create_student_and_submission("Xander", "Xander's answer")
        self._create_student_and_submission("Willow", "Willow's answer")

        buffy_workflow = peer_api._get_latest_workflow(buffy)

        # Get the next submission for review
        submission_uuid = peer_api._get_submission_for_review(buffy_workflow, 3)
        self.assertEqual(xander_answer["uuid"], submission_uuid)

    def test_get_submission_for_over_grading(self):
        buffy_answer, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_answer, xander = self._create_student_and_submission("Xander", "Xander's answer")
        willow_answer, willow = self._create_student_and_submission("Willow", "Willow's answer")

        buffy_workflow = peer_api._get_latest_workflow(buffy)
        xander_workflow = peer_api._get_latest_workflow(xander)
        willow_workflow = peer_api._get_latest_workflow(willow)

        # Get a bunch of workflow items opened up.
        peer_api._create_peer_workflow_item(buffy_workflow, xander_answer["uuid"])
        peer_api._create_peer_workflow_item(willow_workflow, xander_answer["uuid"])
        peer_api._create_peer_workflow_item(xander_workflow, xander_answer["uuid"])
        peer_api._create_peer_workflow_item(buffy_workflow, willow_answer["uuid"])
        peer_api._create_peer_workflow_item(xander_workflow, willow_answer["uuid"])

        #Get the next submission for review
        submission_uuid = peer_api._get_submission_for_over_grading(xander_workflow)
        self.assertEqual(buffy_answer["uuid"], submission_uuid)

    def test_create_assessment_feedback(self):
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob, 1)
        assessment = peer_api.create_assessment(
            sub["uuid"],
            bob["student_id"],
            ASSESSMENT_DICT,
            RUBRIC_DICT,
        )
        sub = peer_api.get_submission_to_assess(tim, 1)
        peer_api.create_assessment(
            sub["uuid"],
            tim["student_id"],
            ASSESSMENT_DICT,
            RUBRIC_DICT,
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
        buffy_answer, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_answer, xander = self._create_student_and_submission("Xander", "Xander's answer")

        # Create a workflow for Buffy.
        buffy_workflow = peer_api._get_latest_workflow(buffy)

        # Get a workflow item opened up.
        submission = peer_api.get_submission_to_assess(buffy, 3)

        self.assertEqual(xander_answer["uuid"], submission["uuid"])

        assessment_dict = peer_api.create_assessment(
            xander_answer["uuid"], "Buffy", ASSESSMENT_DICT, RUBRIC_DICT
        )
        assessment = Assessment.objects.filter(
            scorer_id=assessment_dict["scorer_id"],
            scored_at=assessment_dict["scored_at"])[0]
        peer_api._close_active_assessment(buffy_workflow, xander_answer["uuid"], assessment)

        item = peer_api._create_peer_workflow_item(buffy_workflow, xander_answer["uuid"])
        self.assertEqual(xander_answer["uuid"], submission["uuid"])
        self.assertIsNotNone(item.assessment)

    @patch.object(PeerWorkflow.objects, 'raw')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_failure_to_get_review_submission(self, mock_filter):
        tim_answer, tim = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        tim_workflow = peer_api._get_latest_workflow(tim)
        mock_filter.side_effect = DatabaseError("Oh no.")
        peer_api._get_submission_for_review(tim_workflow, 3)

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
        tim_answer, tim = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        peer_api.set_assessment_feedback({'submission_uuid': tim_answer['uuid']})

    @patch.object(AssessmentFeedback, 'save')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_set_assessment_feedback_error_on_save(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Oh no.")
        tim_answer, tim = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        peer_api.set_assessment_feedback(
            {
                'submission_uuid': tim_answer['uuid'],
                'feedback_text': 'Boo',
            }
        )

    @patch.object(AssessmentFeedback, 'save')
    @raises(peer_api.PeerAssessmentRequestError)
    def test_set_assessment_feedback_error_on_huge_save(self, mock_filter):
        tim_answer, tim = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        peer_api.set_assessment_feedback(
            {
                'submission_uuid': tim_answer['uuid'],
                'feedback_text': 'Boo'*AssessmentFeedback.MAXSIZE,
            }
        )

    @patch.object(PeerWorkflow.objects, 'filter')
    @raises(peer_api.PeerAssessmentWorkflowError)
    def test_failure_to_get_latest_workflow(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Oh no.")
        tim_answer, tim = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        peer_api._get_latest_workflow(tim)

    @patch.object(PeerWorkflow.objects, 'get_or_create')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_create_workflow_error(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Oh no.")
        self._create_student_and_submission("Tim", "Tim's answer", MONDAY)

    @patch.object(PeerWorkflowItem.objects, 'get_or_create')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_create_workflow_item_error(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Oh no.")
        tim_answer, tim = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        peer_api._create_peer_workflow_item(tim, tim_answer['uuid'])

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

    def test_no_submissions_to_evaluate_for_tim(self):
        self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        submission = peer_api.get_submission_to_assess(STUDENT_ITEM, 3)
        self.assertIsNone(submission)

    def test_get_max_scores(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob, 1)
        assessment = peer_api.create_assessment(
            sub["uuid"],
            bob["student_id"],
            ASSESSMENT_DICT,
            RUBRIC_DICT,
        )
        self.assertEqual(assessment["points_earned"], 6)
        self.assertEqual(assessment["points_possible"], 14)
        self.assertEqual(assessment["feedback"], ASSESSMENT_DICT["feedback"])

        max_scores = peer_api.get_rubric_max_scores(sub["uuid"])
        self.assertEqual(max_scores['secret'], 1)
        self.assertEqual(max_scores['giveup'], 10)

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
            submission["uuid"],
            STUDENT_ITEM["student_id"],
            ASSESSMENT_DICT,
            RUBRIC_DICT,
            MONDAY
        )

    @patch.object(PeerWorkflowItem, 'get_scored_assessments')
    @raises(peer_api.PeerAssessmentInternalError)
    def test_error_on_get_assessment(self, mock_filter):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        sub = peer_api.get_submission_to_assess(bob, 3)
        peer_api.create_assessment(
            sub["uuid"],
            bob["student_id"],
            ASSESSMENT_DICT,
            RUBRIC_DICT,
            MONDAY
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
            ASSESSMENT_DICT,
            RUBRIC_DICT,
            MONDAY
        )

    @staticmethod
    def _create_student_and_submission(student, answer, date=None):
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student
        submission = sub_api.create_submission(new_student_item, answer, date)
        peer_api.create_peer_workflow(submission["uuid"])
        workflow_api.create_workflow(submission["uuid"])
        return submission, new_student_item
