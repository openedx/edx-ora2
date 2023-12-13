""" Tests Peer Workflow. """

import copy
import datetime
from unittest.mock import patch

from ddt import ddt, file_data, data, unpack
import pytz

from django.db import DatabaseError, IntegrityError
from django.utils import timezone
from pytest import raises

from submissions import api as sub_api
from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.errors.peer import PeerAssessmentWorkflowError
from openassessment.assessment.models import (
    Assessment,
    AssessmentFeedback,
    AssessmentFeedbackOption,
    AssessmentPart,
    PeerWorkflow,
    PeerWorkflowItem
)
from openassessment.workflow.models import AssessmentWorkflow
from openassessment.test_utils import CacheResetTest
from openassessment.workflow import api as workflow_api

STUDENT_ITEM = {
    "student_id": "Tim",
    "course_id": "Demo_Course",
    "item_id": "item_one",
    "item_type": "Peer_Submission",
}

ANSWER_ONE = "this is my answer!"

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
            "name": "ⓢⓐⓕⓔ",
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
    'overall_feedback': "这是中国",
    'criterion_feedback': {
        "giveup": "𝓨𝓸𝓾 𝓼𝓱𝓸𝓾𝓵𝓭𝓷'𝓽 𝓰𝓲𝓿𝓮 𝓾𝓹!"
    },
    'options_selected': {
        "secret": "yes",
        "ⓢⓐⓕⓔ": "no",
        "giveup": "reluctant",
        "singing": "no",
    },
}

# Answers are against RUBRIC_DICT -- this is worth 0 points
ASSESSMENT_DICT_FAIL = {
    'overall_feedback': "fail",
    'criterion_feedback': {},
    'options_selected': {
        "secret": "no",
        "ⓢⓐⓕⓔ": "no",
        "giveup": "unwilling",
        "singing": "yes",
    }
}

# Answers are against RUBRIC_DICT -- this is worth 14 points
ASSESSMENT_DICT_PASS = {
    'overall_feedback': "这是中国",
    'criterion_feedback': {},
    'options_selected': {
        "secret": "yes",
        "ⓢⓐⓕⓔ": "yes",
        "giveup": "eager",
        "singing": "no",
    }
}

# Answers are against RUBRIC_DICT -- this is worth 14 points
# Feedback text is one character over the limit.
LONG_FEEDBACK_TEXT = "是" * Assessment.MAX_FEEDBACK_SIZE + "."
ASSESSMENT_DICT_HUGE = {
    'overall_feedback': LONG_FEEDBACK_TEXT,
    'criterion_feedback': {
        "secret": LONG_FEEDBACK_TEXT,
        "ⓢⓐⓕⓔ": LONG_FEEDBACK_TEXT,
        "giveup": LONG_FEEDBACK_TEXT,
        "singing": LONG_FEEDBACK_TEXT,
    },
    'options_selected': {
        "secret": "yes",
        "ⓢⓐⓕⓔ": "yes",
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

STEP_REQUIREMENTS = {
    "peer": {
        "must_grade": 1,
        "must_be_graded_by": 1
    }
}

COURSE_SETTINGS = {}

COURSE_SETTINGS_FLEXIBLE_ON = {
    'force_on_flexible_peer_openassessments': True
}


@ddt
class TestPeerApi(CacheResetTest):
    """
    Tests for the peer assessment API functions.
    """

    CREATE_ASSESSMENT_NUM_QUERIES = 38

    def test_create_assessment_points(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], 1)

        with self.assertNumQueries(self.CREATE_ASSESSMENT_NUM_QUERIES):
            assessment = peer_api.create_assessment(
                bob_sub["uuid"],
                bob["student_id"],
                ASSESSMENT_DICT['options_selected'], {}, "",
                RUBRIC_DICT,
                REQUIRED_GRADED_BY,
            )
        self.assertEqual(assessment["points_earned"], 6)
        self.assertEqual(assessment["points_possible"], 14)

    def test_create_assessment_with_feedback(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], 1)

        with self.assertNumQueries(self.CREATE_ASSESSMENT_NUM_QUERIES):
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

    def test_get_waiting_step_details(self):
        """
        Test that the waiting step details API returns data for students
        stuck in the waiting step.
        """
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], 1)
        peer_api.create_assessment(
            bob_sub["uuid"],
            bob["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        students_waiting = peer_api.get_waiting_step_details(
            STUDENT_ITEM['course_id'],
            STUDENT_ITEM['item_id'],
            [bob_sub['uuid']],
            must_be_graded_by=1,
        )

        # Check that the API response - Bob is waiting a peer assessment
        self.assertEqual(len(students_waiting), 1)
        # Bob was not graded by anyone and graded Tim
        self.assertEqual(students_waiting[0]['graded_by'], 0)
        self.assertEqual(students_waiting[0]['graded'], 1)

    def test_get_bulk_scored_assessments(self):
        # Create three learners and submissions
        submission_and_learner = [self._create_student_and_submission(f"Learner{i}", f"{i} answer") for i in [0, 1, 2]]

        # Each learner assesses two peers, so everyone scores 2 and is scored by 2
        for submission, learner in submission_and_learner:
            for _ in range(2):
                peer_api.get_submission_to_assess(submission['uuid'], 1)
                peer_api.create_assessment(
                    submission["uuid"],
                    learner["student_id"],
                    ASSESSMENT_DICT['options_selected'],
                    ASSESSMENT_DICT['criterion_feedback'],
                    ASSESSMENT_DICT['overall_feedback'],
                    RUBRIC_DICT,
                    1,
                )

        # call get_score for all three to mark items as 'scored'. Everyone shoulfd have a score because
        # they have at least one peer review and have done at least one review.
        for submission, _ in submission_and_learner:
            peer_score = peer_api.get_score(
                submission['uuid'],
                {'must_be_graded_by': 1, 'must_grade': 1},
                COURSE_SETTINGS
            )
            assert peer_score is not None

        # There should be three "scored" assessments
        scored_assessment_ids = {
            assessment.id for assessment in
            peer_api.get_bulk_scored_assessments(
                [submission['uuid'] for submission, _ in submission_and_learner]
            )
        }
        assert len(scored_assessment_ids) == 3

        # Each learner should have recieved one "scored" and one "unscored" peer assessment
        for submission, _ in submission_and_learner:
            workflow = PeerWorkflow.objects.prefetch_related('graded_by').get(submission_uuid=submission['uuid'])
            unscored = workflow.graded_by.get(scored=False)
            scored = workflow.graded_by.get(scored=True)
            assert unscored.assessment_id not in scored_assessment_ids
            assert scored.assessment_id in scored_assessment_ids

    def test_create_assessment_criterion_with_zero_options(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], 1)

        # Modify the rubric to include a criterion with no options,
        # only written feedback.
        rubric = copy.deepcopy(RUBRIC_DICT)
        rubric["criteria"].append({
            "name": "feedback only",
            "prompt": "feedback only",
            "options": []
        })

        # Provide written feedback for the feedback-only criterion
        feedback = {
            "feedback only": "This is some feedback"
        }
        assessment = peer_api.create_assessment(
            bob_sub["uuid"],
            bob["student_id"],
            ASSESSMENT_DICT['options_selected'],
            feedback, "",
            rubric,
            REQUIRED_GRADED_BY,
        )

        # Verify that the point values are the same
        # (the feedback-only criterion isn't worth any points)
        self.assertEqual(assessment["points_earned"], 6)
        self.assertEqual(assessment["points_possible"], 14)

        # Verify the feedback-only criterion assessment part
        self.assertEqual(assessment["parts"][4]["criterion"]["name"], "feedback only")
        self.assertIs(assessment["parts"][4]["option"], None)
        self.assertEqual(assessment["parts"][4]["feedback"], "This is some feedback")

    def test_create_assessment_unknown_criterion_feedback(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], 1)

        # Create an assessment where the criterion feedback uses
        # a criterion name that isn't in the rubric.
        # An exception should be raised, since this will be interpreted
        # as adding an extra criterion with no options, just feedback.
        with self.assertRaises(peer_api.PeerAssessmentRequestError):
            peer_api.create_assessment(
                bob_sub["uuid"],
                bob["student_id"],
                ASSESSMENT_DICT['options_selected'],
                {'unknown': 'Unknown criterion has feedback!'},
                ASSESSMENT_DICT['overall_feedback'],
                RUBRIC_DICT,
                REQUIRED_GRADED_BY,
            )

    def test_create_huge_overall_feedback_error(self):
        self._create_student_and_submission("Tim", "Tim's answer")
        bob_sub, bob = self._create_student_and_submission("Bob", "Bob's answer")
        peer_api.get_submission_to_assess(bob_sub['uuid'], 1)

        # Huge overall feedback text
        assessment_dict = peer_api.create_assessment(
            bob_sub["uuid"],
            bob["student_id"],
            ASSESSMENT_DICT_HUGE['options_selected'],
            {},
            ASSESSMENT_DICT_HUGE['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )

        # The assessment feedback text should be truncated
        self.assertEqual(len(assessment_dict['feedback']), Assessment.MAX_FEEDBACK_SIZE)

        # The length of the feedback text in the database should
        # equal what we got from the API.
        assessment = Assessment.objects.get()
        self.assertEqual(len(assessment.feedback), Assessment.MAX_FEEDBACK_SIZE)

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
            self.assertEqual(len(part['feedback']), Assessment.MAX_FEEDBACK_SIZE)

        # Verify that the feedback in the database matches what we got back from the API
        for part in AssessmentPart.objects.all():
            self.assertEqual(len(part.feedback), Assessment.MAX_FEEDBACK_SIZE)

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
        assessments = peer_api.get_assessments(sub["uuid"])
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
        assessments = peer_api.get_assessments(sub["uuid"])
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
        self.assertEqual("Bob's answer", sub['answer'])

        # And now we cheat; we want to set the clock back such that the lease
        # on this PeerWorkflowItem has expired.
        pwis = PeerWorkflowItem.objects.filter(submission_uuid=sub['uuid'])
        self.assertEqual(len(pwis), 1)
        pwis[0].started_at = yesterday
        pwis[0].save()

        sub = peer_api.get_submission_to_assess(tim_sub['uuid'], REQUIRED_GRADED)
        self.assertEqual("Bob's answer", sub['answer'])

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
        with patch("openassessment.assessment.models.peer.PeerWorkflow.objects.get_or_create") as mock_peer:
            mock_peer.side_effect = IntegrityError("Oh no!")
            # This should not raise an exception
            peer_api.on_start(tim_sub["uuid"])

    def test_no_submission_found_closing_assessment(self):
        """
        Confirm the appropriate error is raised when no submission is found
        open for assessment, when submitting an assessment.
        """
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
        with raises(peer_api.PeerAssessmentWorkflowError):
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
            tim_sub["uuid"],
            requirements,
            COURSE_SETTINGS,
        )["score"]
        self.assertIsNone(score)

        for i in range(5):
            self.assertEqual((False, i), peer_api.has_finished_required_evaluating(tim_sub['uuid'], REQUIRED_GRADED))
            sub = peer_api.get_submission_to_assess(tim_sub['uuid'], REQUIRED_GRADED)
            peer_api.create_assessment(
                tim_sub["uuid"], tim["student_id"],
                ASSESSMENT_DICT['options_selected'],
                ASSESSMENT_DICT['criterion_feedback'],
                ASSESSMENT_DICT['overall_feedback'],
                RUBRIC_DICT,
                REQUIRED_GRADED_BY,
            )

        self.assertEqual((True, 5), peer_api.has_finished_required_evaluating(tim_sub['uuid'], REQUIRED_GRADED))

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
            tim_sub["uuid"],
            requirements,
            COURSE_SETTINGS,
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
            tim_sub["uuid"],
            requirements,
            COURSE_SETTINGS,
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
            tim_sub["uuid"],
            requirements,
            COURSE_SETTINGS,
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
        self.assertEqual(angel_sub["uuid"], sub["uuid"])

        # 4) Sally submits
        sally_sub, _ = self._create_student_and_submission("Sally", "Sally's answer")

        # 5) Sally pulls Angel's Submission but never reviews it.
        sub = peer_api.get_submission_to_assess(sally_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(angel_sub["uuid"], sub["uuid"])

        # 6) Jim submits
        jim_sub, _ = self._create_student_and_submission("Jim", "Jim's answer")

        # 7) Jim also doesn't care about Angel and does not bother to review.
        sub = peer_api.get_submission_to_assess(jim_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(angel_sub["uuid"], sub["uuid"])

        # 8) Buffy comes along and she submits
        buffy_sub, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")

        # 9) Buffy cares about Angel, but she won't get Angel's submission;
        # it's held by Bob, Sally, and Jim.
        sub = peer_api.get_submission_to_assess(buffy_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(bob_sub["uuid"], sub["uuid"])

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
        self.assertEqual(sally_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            buffy_sub["uuid"], buffy["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        sub = peer_api.get_submission_to_assess(buffy_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(jim_sub["uuid"], sub["uuid"])
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
        self.assertEqual(bob_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            xander_sub["uuid"], xander["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        sub = peer_api.get_submission_to_assess(xander_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(sally_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            xander_sub["uuid"], xander["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        sub = peer_api.get_submission_to_assess(xander_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(jim_sub["uuid"], sub["uuid"])
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
        self.assertEqual(xander_sub["uuid"], sub["uuid"])
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
        self.assertEqual(bob_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            spike_sub["uuid"], spike["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,

        )
        sub = peer_api.get_submission_to_assess(spike_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(sally_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            spike_sub["uuid"], spike["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        sub = peer_api.get_submission_to_assess(spike_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(jim_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            spike_sub["uuid"], spike["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        sub = peer_api.get_submission_to_assess(spike_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(buffy_sub["uuid"], sub["uuid"])
        peer_api.create_assessment(
            spike_sub["uuid"], spike["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        sub = peer_api.get_submission_to_assess(spike_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(xander_sub["uuid"], sub["uuid"])
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
        self.assertEqual(spike_sub["uuid"], sub["uuid"])
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
        self.assertEqual(buffy_sub["uuid"], sub["uuid"])
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
        self.assertEqual(buffy_sub["uuid"], sub["uuid"])
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
            ASSESSMENT_DICT['options_selected'], {}, "",
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
        )
        self.assertEqual(assessment["points_earned"], 6)
        self.assertEqual(assessment["points_possible"], 14)

        submitted_assessments = peer_api.get_submitted_assessments(bob_sub["uuid"])
        self.assertEqual(1, len(submitted_assessments))

    def test_get_submitted_assessments_with_bad_submission(self):
        submitted_assessments = peer_api.get_submitted_assessments("bad-uuid")
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
        item = buffy_workflow.find_active_assessments()
        self.assertEqual(xander_answer["uuid"], item.submission_uuid)

        # Cancel the Xander's submission.
        PeerWorkflow.get_by_submission_uuid(xander_answer['uuid'])
        workflow_api.cancel_workflow(
            submission_uuid=xander_answer["uuid"],
            comments='Cancellation reason',
            cancelled_by_id=_['student_id'],
            assessment_requirements=STEP_REQUIREMENTS,
            course_settings=COURSE_SETTINGS,
        )

        # Check to see if Buffy is actively reviewing Xander's submission.
        # She isn't able to get the submission to assess.
        item = buffy_workflow.find_active_assessments()
        self.assertIsNone(item)

    def test_submission_cancelled_while_being_assessed(self):
        # Test that if student pulls the submission for review and the
        # submission is cancelled their assessment will not be accepted.
        buffy_sub, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_sub, __ = self._create_student_and_submission("Xander", "Xander's answer")

        # Check for a workflow for Buffy.
        buffy_workflow = PeerWorkflow.get_by_submission_uuid(buffy_sub['uuid'])
        self.assertIsNotNone(buffy_workflow)

        # Buffy is going to review Xander's submission, so create a workflow
        # item for Buffy.
        PeerWorkflow.create_item(buffy_workflow, xander_sub["uuid"])

        # Check to see if Buffy is actively reviewing Xander's submission.
        submission = peer_api.get_submission_to_assess(buffy_sub['uuid'], 1)
        self.assertEqual(xander_sub["uuid"], submission['uuid'])

        # Cancel the Xander's submission.
        workflow_api.cancel_workflow(
            submission_uuid=xander_sub['uuid'],
            comments="Inappropriate language",
            cancelled_by_id=buffy['student_id'],
            assessment_requirements=STEP_REQUIREMENTS,
            course_settings=COURSE_SETTINGS,
        )

        # Check to see if Buffy is actively reviewing Xander's submission.
        # She isn't able to get the submission to assess.
        submission = peer_api.get_submission_to_assess(buffy_sub['uuid'], 1)
        self.assertIsNone(submission)

        # Try to assess the cancelled submission
        # This will raise PeerAssessmentWorkflowError
        with self.assertRaises(peer_api.PeerAssessmentWorkflowError):
            peer_api.create_assessment(
                buffy_sub['uuid'],
                buffy["student_id"],
                ASSESSMENT_DICT['options_selected'],
                ASSESSMENT_DICT['criterion_feedback'],
                ASSESSMENT_DICT['overall_feedback'],
                RUBRIC_DICT,
                REQUIRED_GRADED_BY,
            )

    def test_cancelled_submission_peerworkflow_status(self):
        # Test peerworkflow is cancelled.

        buffy_sub, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")

        # Check for a workflow for Buffy.
        buffy_workflow = PeerWorkflow.get_by_submission_uuid(buffy_sub['uuid'])
        self.assertIsNotNone(buffy_workflow)

        # Cancel the buffy's submission (peer workflow and assessment workflow).
        workflow_api.cancel_workflow(
            submission_uuid=buffy_sub['uuid'],
            comments="Inappropriate language",
            cancelled_by_id=buffy['student_id'],
            assessment_requirements=STEP_REQUIREMENTS,
            course_settings=COURSE_SETTINGS,
        )

        workflow = PeerWorkflow.get_by_submission_uuid(buffy_sub["uuid"])
        self.assertTrue(workflow.is_cancelled)

    def test_cancel_submission_when_peerworkflow_does_not_exist(self):
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = "Buffy"

        submission = sub_api.create_submission(new_student_item, "Buffy Answer")

        peer_api.on_cancel(submission['uuid'])
        # Check for a workflow for Buffy.
        # It should be None
        buffy_workflow = PeerWorkflow.get_by_submission_uuid(submission['uuid'])
        self.assertIsNone(buffy_workflow)

    def test_get_workflow_by_uuid(self):
        buffy_answer, _ = self._create_student_and_submission("Buffy", "Buffy's answer")
        self._create_student_and_submission("Xander", "Xander's answer")
        self._create_student_and_submission("Willow", "Willow's answer")
        buffy_answer_two, _ = self._create_student_and_submission("Buffy", "Buffy's answer")

        workflow = PeerWorkflow.get_by_submission_uuid(buffy_answer_two['uuid'])
        self.assertNotEqual(buffy_answer["uuid"], workflow.submission_uuid)
        self.assertEqual(buffy_answer_two["uuid"], workflow.submission_uuid)

    def test_get_submission_for_review(self):
        buffy_answer, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_answer, __ = self._create_student_and_submission("Xander", "Xander's answer")
        self._create_student_and_submission("Willow", "Willow's answer")

        buffy_workflow = PeerWorkflow.get_by_submission_uuid(buffy_answer['uuid'])

        # Get the next submission for review
        submission_uuid = buffy_workflow.get_submission_for_review(3)
        self.assertEqual(xander_answer["uuid"], submission_uuid)

        # Cancel the Xander's submission.
        workflow_api.cancel_workflow(
            submission_uuid=xander_answer['uuid'],
            comments="Inappropriate language",
            cancelled_by_id=buffy['student_id'],
            assessment_requirements=STEP_REQUIREMENTS,
            course_settings=COURSE_SETTINGS,
        )

        # Check to see if Buffy is actively reviewing Xander's submission.
        # She isn't able to get the submission uuid to assess.
        submission_uuid = buffy_workflow.get_submission_for_review(3)
        self.assertNotEqual(xander_answer["uuid"], submission_uuid)

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

        if not (submission_uuid in (buffy_answer['uuid'], willow_answer['uuid'])):
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
            },
            COURSE_SETTINGS
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
        self.assertEqual(saved_feedback['submission_uuid'], assessment['submission_uuid'])
        self.assertEqual(saved_feedback['feedback_text'], 'Bob is a jerk!')
        self.assertCountEqual(saved_feedback['options'], [
            {'text': 'I disliked this assessment'},
            {'text': 'I felt this assessment was unfair'},
        ])
        self.assertEqual(saved_feedback["assessments"][0]["submission_uuid"], assessment["submission_uuid"])

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

    @patch("openassessment.assessment.models.peer.PeerWorkflowItem.objects.filter")
    def test_get_submitted_assessments_error(self, mock_filter):
        with raises(peer_api.PeerAssessmentInternalError):
            self._create_student_and_submission("Tim", "Tim's answer")
            bob_sub, __ = self._create_student_and_submission("Bob", "Bob's answer")
            peer_api.get_submission_to_assess(bob_sub['uuid'], REQUIRED_GRADED_BY)
            mock_filter.side_effect = DatabaseError("Oh no.")
            submitted_assessments = peer_api.get_submitted_assessments(bob_sub["uuid"])
            self.assertEqual(1, len(submitted_assessments))

    @patch('openassessment.assessment.models.peer.PeerWorkflow.objects.raw')
    def test_failure_to_get_review_submission(self, mock_filter):
        with raises(peer_api.PeerAssessmentInternalError):
            tim_answer, _ = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
            tim_workflow = PeerWorkflow.get_by_submission_uuid(tim_answer['uuid'])
            mock_filter.side_effect = DatabaseError("Oh no.")
            tim_workflow.get_submission_for_review(3)

    @patch('openassessment.assessment.models.AssessmentFeedback.objects.get')
    def test_get_assessment_feedback_error(self, mock_filter):
        with raises(peer_api.PeerAssessmentInternalError):
            mock_filter.side_effect = DatabaseError("Oh no.")
            tim_answer, __ = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
            peer_api.get_assessment_feedback(tim_answer['uuid'])

    def test_get_assessments_null(self):
        # Test to fix serialization of incomplete, unscored assessments

        # Tim & Buffy submit
        tim_answer, _ = self._create_student_and_submission("Tim", "Tim's answer")
        buffy_answer, _ = self._create_student_and_submission("Buffy", "Buffy's answer")

        # Buffy starts but does not finish assessing Tim's answer
        peer_api.get_submission_to_assess(buffy_answer['uuid'], REQUIRED_GRADED_BY)

        # Tim gets unscored assessments, this used to throw an error
        PeerWorkflowItem.get_unscored_assessments(tim_answer["uuid"])

    @patch('openassessment.assessment.models.peer.PeerWorkflowItem.get_scored_assessments')
    def test_set_assessment_feedback_error(self, mock_filter):
        with raises(peer_api.PeerAssessmentInternalError):
            mock_filter.side_effect = DatabaseError("Oh no.")
            tim_answer, _ = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
            peer_api.set_assessment_feedback({'submission_uuid': tim_answer['uuid']})

    @patch('openassessment.assessment.models.AssessmentFeedback.save')
    def test_set_assessment_feedback_error_on_save(self, mock_filter):
        with raises(peer_api.PeerAssessmentInternalError):
            mock_filter.side_effect = DatabaseError("Oh no.")
            tim_answer, _ = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
            peer_api.set_assessment_feedback(
                {
                    'submission_uuid': tim_answer['uuid'],
                    'feedback_text': 'Boo',
                }
            )

    @patch('openassessment.assessment.models.AssessmentFeedback.save')
    def test_set_assessment_feedback_error_on_huge_save(self, _):
        with raises(peer_api.PeerAssessmentRequestError):
            tim_answer, _ = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
            peer_api.set_assessment_feedback(
                {
                    'submission_uuid': tim_answer['uuid'],
                    'feedback_text': 'Boo' * AssessmentFeedback.MAXSIZE,
                }
            )

    @patch('openassessment.assessment.models.peer.PeerWorkflow.objects.get')
    def test_failure_to_get_latest_workflow(self, mock_filter):
        with raises(peer_api.PeerAssessmentWorkflowError):
            mock_filter.side_effect = DatabaseError("Oh no.")
            tim_answer, _ = self._create_student_and_submission("Tim", "Tim's answer", MONDAY)
            PeerWorkflow.get_by_submission_uuid(tim_answer['uuid'])

    @patch('openassessment.assessment.models.peer.PeerWorkflow.objects.get_or_create')
    def test_create_workflow_error(self, mock_filter):
        with raises(peer_api.PeerAssessmentInternalError):
            mock_filter.side_effect = DatabaseError("Oh no.")
            self._create_student_and_submission("Tim", "Tim's answer", MONDAY)

    @patch('openassessment.assessment.models.peer.PeerWorkflow.objects.get_or_create')
    def test_create_workflow_item_error(self, mock_filter):
        with raises(peer_api.PeerAssessmentInternalError):
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
        self.assertEqual(submission["answer"], "Bob's answer")
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
        peer_api.create_assessment(
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

    def test_no_open_assessment(self):
        with raises(peer_api.PeerAssessmentWorkflowError):
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

    def test_max_score_db_error(self):
        with raises(peer_api.PeerAssessmentInternalError):
            tim, _ = self._create_student_and_submission("Tim", "Tim's answer")
            with patch('openassessment.assessment.models.Assessment.objects.filter') as mock_filter:
                mock_filter.side_effect = DatabaseError("Bad things happened")
                peer_api.get_rubric_max_scores(tim["uuid"])

    @patch('openassessment.assessment.models.peer.PeerWorkflow.objects.get')
    def test_median_score_db_error(self, mock_filter):
        with raises(peer_api.PeerAssessmentInternalError):
            mock_filter.side_effect = DatabaseError("Bad things happened")
            tim, _ = self._create_student_and_submission("Tim", "Tim's answer")
            peer_api.get_assessment_median_scores(tim["uuid"])

    @patch('openassessment.assessment.models.Assessment.objects.filter')
    def test_get_assessments_db_error(self, mock_filter):
        with raises(peer_api.PeerAssessmentInternalError):
            mock_filter.return_value = Assessment.objects.none()
            tim, _ = self._create_student_and_submission("Tim", "Tim's answer")
            mock_filter.side_effect = DatabaseError("Bad things happened")
            peer_api.get_assessments(tim["uuid"])

    @patch('openassessment.assessment.models.peer.PeerWorkflow.objects.get_or_create')
    def test_error_on_assessment_creation(self, mock_filter):
        with raises(peer_api.PeerAssessmentInternalError):
            mock_filter.side_effect = DatabaseError("Bad things happened")
            submission = sub_api.create_submission(STUDENT_ITEM, ANSWER_ONE)
            peer_api.on_start(submission["uuid"])
            peer_api.create_assessment(
                submission["uuid"], STUDENT_ITEM["student_id"],
                ASSESSMENT_DICT['options_selected'],
                ASSESSMENT_DICT['criterion_feedback'],
                ASSESSMENT_DICT['overall_feedback'],
                RUBRIC_DICT,
                REQUIRED_GRADED_BY,
                MONDAY,
            )

    @patch('openassessment.assessment.models.Assessment.objects.filter')
    def test_error_on_get_assessment(self, mock_filter):
        with raises(peer_api.PeerAssessmentInternalError):
            mock_filter.return_value = Assessment.objects.none()
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

    def test_assess_before_submitting(self):
        with raises(peer_api.PeerAssessmentWorkflowError):
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

    def test_ignore_duplicate_workflow_items(self):
        """
        A race condition may cause two workflow items to be opened for a single
        submission. In this case, we want to be defensive in the API, such that
        no open workflow item is acknowledged if an assessment has already been
        made against the associated submission.

        """
        bob_sub, bob = self._create_student_and_submission('Bob', 'Bob submission')
        tim_sub, __ = self._create_student_and_submission('Tim', 'Tim submission')
        sally_sub, __ = self._create_student_and_submission('Sally', 'Sally submission')
        jane_sub, __ = self._create_student_and_submission('Jane', 'Jane submission')

        # Create two workflow items.
        peer_api.create_peer_workflow_item(bob_sub['uuid'], tim_sub['uuid'])
        peer_api.create_peer_workflow_item(bob_sub['uuid'], tim_sub['uuid'])

        # Assess the submission, then get the next submission.
        peer_api.create_assessment(
            bob_sub['uuid'],
            bob['student_id'],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
            MONDAY
        )

        # Verify the next submission is not Tim again, but Sally.
        next_sub = peer_api.get_submission_to_assess(bob_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(next_sub['uuid'], sally_sub['uuid'])

        # Request another peer submission. Should pick up Sally again.
        next_sub = peer_api.get_submission_to_assess(bob_sub['uuid'], REQUIRED_GRADED_BY)
        self.assertEqual(next_sub['uuid'], sally_sub['uuid'])

        # Ensure that the next assessment made is against Sally, not Tim.
        # Assess the submission, then get the next submission.
        peer_api.create_assessment(
            bob_sub['uuid'],
            bob['student_id'],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            REQUIRED_GRADED_BY,
            MONDAY
        )

        # Make sure Tim has one assessment.
        tim_assessments = peer_api.get_assessments(tim_sub['uuid'])
        self.assertEqual(1, len(tim_assessments))

        # Make sure Sally has one assessment.
        sally_assessments = peer_api.get_assessments(sally_sub['uuid'])
        self.assertEqual(1, len(sally_assessments))

        # Make sure Jane has no assessment.
        jane_assessments = peer_api.get_assessments(jane_sub['uuid'])
        self.assertEqual(0, len(jane_assessments))

    def test_get_submission_to_assess_no_workflow(self):
        # Try to retrieve a submission to assess when the student
        # doing the assessment hasn't yet submitted.
        with self.assertRaises(peer_api.PeerAssessmentWorkflowError):
            peer_api.get_submission_to_assess("no_such_submission", "scorer ID")

    def test_get_submission_to_assess_for_cancelled_submission(self):
        # Test that student will not be able to pull the cancelled
        # submission for review.
        buffy_sub, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_sub, __ = self._create_student_and_submission("Xander", "Xander's answer")

        # Check for a workflow for Buffy.
        buffy_workflow = PeerWorkflow.get_by_submission_uuid(buffy_sub['uuid'])
        self.assertIsNotNone(buffy_workflow)

        # Buffy is going to review Xander's submission, so create a workflow
        # item for Buffy.
        PeerWorkflow.create_item(buffy_workflow, xander_sub["uuid"])

        # Cancel the Xander's submission.
        workflow_api.cancel_workflow(
            submission_uuid=xander_sub['uuid'],
            comments="Inappropriate language",
            cancelled_by_id=buffy['student_id'],
            assessment_requirements=STEP_REQUIREMENTS,
            course_settings=COURSE_SETTINGS,
        )

        # Check to see if Buffy is able to review Xander's submission.
        # She isn't able to get the submission to assess because xander's
        # submission is cancelled.
        item = peer_api.get_submission_to_assess(buffy_sub['uuid'], 1)
        self.assertIsNone(item)

    def test_get_graded_by_count(self):
        self.assertIsNone(peer_api.get_graded_by_count("DOESNOTEXIST"))

        buffy_sub, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_sub, _ = self._create_student_and_submission("Xander", "Xander's answer")

        # buffy peer grades xander
        peer_api.get_submission_to_assess(buffy_sub['uuid'], buffy['student_id'])
        peer_api.create_assessment(
            buffy_sub['uuid'],
            buffy['student_id'],
            ASSESSMENT_DICT_PASS['options_selected'],
            ASSESSMENT_DICT_PASS['criterion_feedback'],
            ASSESSMENT_DICT_PASS['overall_feedback'],
            RUBRIC_DICT,
            2
        )

        # buffy has not been peer graded, but xander has been graded by 1
        self.assertEqual(peer_api.get_graded_by_count(xander_sub["uuid"]), 1)
        self.assertEqual(peer_api.get_graded_by_count(buffy_sub["uuid"]), 0)

    def test_status_details(self):
        buffy_sub, buffy = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_sub, _ = self._create_student_and_submission("Xander", "Xander's answer")

        # buffy peer grades xander
        peer_api.get_submission_to_assess(buffy_sub['uuid'], buffy['student_id'])
        peer_api.create_assessment(
            buffy_sub['uuid'],
            buffy['student_id'],
            ASSESSMENT_DICT_PASS['options_selected'],
            ASSESSMENT_DICT_PASS['criterion_feedback'],
            ASSESSMENT_DICT_PASS['overall_feedback'],
            RUBRIC_DICT,
            2
        )

        buffy_workflow = AssessmentWorkflow.get_by_submission_uuid(buffy_sub['uuid'])
        expected_status = {
            "peer": {
                "peers_graded_count": 1,
                "complete": False,
                "graded_by_count": 0,
                "skipped": False,
                "graded": False,
            },
            "self": {"complete": False, "skipped": False, "graded": False},
            "staff": {"complete": True, "skipped": False, "graded": True},
        }
        self.assertEqual(expected_status, buffy_workflow.status_details())

        xander_workflow = AssessmentWorkflow.get_by_submission_uuid(xander_sub['uuid'])
        expected_status = {
            "peer": {
                "peers_graded_count": 0,
                "complete": False,
                "graded_by_count": 1,
                "skipped": False,
                "graded": False,
            },
            "self": {"complete": False, "skipped": False, "graded": False},
            "staff": {"complete": True, "skipped": False, "graded": True},
        }
        self.assertEqual(expected_status, xander_workflow.status_details())

    def test_get_submission_to_assess_for_student_with_cancelled_submission(self):
        # Test that student with cancelled submission will not be able to
        # review submissions by others.
        buffy_sub, __ = self._create_student_and_submission("Buffy", "Buffy's answer")
        xander_sub, xander = self._create_student_and_submission("Xander", "Xander's answer")

        # Check for a workflow for Buffy.
        buffy_workflow = PeerWorkflow.get_by_submission_uuid(buffy_sub['uuid'])
        self.assertIsNotNone(buffy_workflow)

        # Buffy is going to review Xander's submission, so create a workflow
        # item for Buffy.
        PeerWorkflow.create_item(buffy_workflow, xander_sub["uuid"])

        # Cancel the Buffy's submission.
        workflow_api.cancel_workflow(
            submission_uuid=buffy_sub['uuid'],
            comments="Inappropriate language",
            cancelled_by_id=xander['student_id'],
            assessment_requirements=STEP_REQUIREMENTS,
            course_settings=COURSE_SETTINGS,
        )
        self.assertTrue(peer_api.is_workflow_cancelled(submission_uuid=buffy_sub['uuid']))

        # Check to see if Buffy is able to review Xander's submission.
        # She isn't able to get the submission to assess because it's own
        # submission is cancelled.
        item = peer_api.get_submission_to_assess(buffy_sub['uuid'], 1)
        self.assertIsNone(item)

    def test_too_many_assessments_counted_in_score_bug(self):
        # This bug allowed a score to be calculated using more
        # assessments, than the required number in the problem definition.
        # For the test case, set required number of assessments to one.
        required_graded_by = 1
        requirements = {
            'must_grade': 1,
            'must_be_graded_by': required_graded_by
        }

        # Create some submissions and students
        bob_sub, bob = self._create_student_and_submission('Bob', 'Bob submission')
        tim_sub, tim = self._create_student_and_submission('Tim', 'Tim submission')

        # Bob assesses someone else, satisfying his requirements
        peer_api.get_submission_to_assess(bob_sub['uuid'], bob['student_id'])
        peer_api.create_assessment(
            bob_sub['uuid'],
            bob['student_id'],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            required_graded_by
        )

        # Tim grades Bob, so now Bob has one assessment with a good grade
        peer_api.get_submission_to_assess(tim_sub['uuid'], tim['student_id'])
        peer_api.create_assessment(
            tim_sub['uuid'],
            tim['student_id'],
            ASSESSMENT_DICT_PASS['options_selected'],
            ASSESSMENT_DICT_PASS['criterion_feedback'],
            ASSESSMENT_DICT_PASS['overall_feedback'],
            RUBRIC_DICT,
            required_graded_by
        )

        # Here, the XBlock would update the workflow,
        # which would check the peer API to see if the student has
        # enough assessments.
        # Part of the bug was that this would call `get_score()` which
        # implicitly marked peer workflow items as scored.
        peer_api.assessment_is_finished(bob_sub['uuid'], requirements, COURSE_SETTINGS)

        # Sue creates a submission
        sue_sub, sue = self._create_student_and_submission('Sue', 'Sue submission')

        # Sue grades the only person in the queue, who is Tim because Tim still needs an assessment
        peer_api.get_submission_to_assess(sue_sub['uuid'], sue['student_id'])
        peer_api.create_assessment(
            sue_sub['uuid'],
            sue['student_id'],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            required_graded_by
        )

        # Sue grades the only person she hasn't graded yet (Bob), with a failing grade
        peer_api.get_submission_to_assess(sue_sub['uuid'], sue['student_id'])
        peer_api.create_assessment(
            sue_sub['uuid'],
            sue['student_id'],
            ASSESSMENT_DICT_FAIL['options_selected'],
            ASSESSMENT_DICT_FAIL['criterion_feedback'],
            ASSESSMENT_DICT_FAIL['overall_feedback'],
            RUBRIC_DICT,
            required_graded_by
        )

        # This used to create a second assessment,
        # which was the bug.
        score = peer_api.get_score(bob_sub['uuid'], requirements, COURSE_SETTINGS)

        # Verify that only the first assessment was used to generate the score
        self.assertEqual(score['points_earned'], 14)

    def test_create_assessment_database_error(self):
        with raises(peer_api.PeerAssessmentInternalError):
            self._create_student_and_submission("Bob", "Bob's answer")
            submission, student = self._create_student_and_submission("Jim", "Jim's answer")
            peer_api.get_submission_to_assess(submission['uuid'], 1)

            with patch('openassessment.assessment.models.peer.PeerWorkflow.objects.get') as mock_call:
                mock_call.side_effect = DatabaseError("Kaboom!")
                peer_api.create_assessment(
                    submission['uuid'],
                    student['student_id'],
                    ASSESSMENT_DICT['options_selected'],
                    ASSESSMENT_DICT['criterion_feedback'],
                    ASSESSMENT_DICT['overall_feedback'],
                    RUBRIC_DICT,
                    REQUIRED_GRADED_BY
                )

    def test_create_assessment_invalid_rubric_error(self):
        with raises(peer_api.PeerAssessmentRequestError):
            self._create_student_and_submission("Bob", "Bob's answer")
            submission, student = self._create_student_and_submission("Jim", "Jim's answer")
            peer_api.get_submission_to_assess(submission['uuid'], 1)
            peer_api.create_assessment(
                submission['uuid'],
                student['student_id'],
                ASSESSMENT_DICT['options_selected'],
                ASSESSMENT_DICT['criterion_feedback'],
                ASSESSMENT_DICT['overall_feedback'],
                {"invalid_rubric!": "is invalid"},
                REQUIRED_GRADED_BY
            )

    @data(
        (
            {'must_grade': 1, 'must_be_graded_by': 10, 'enable_flexible_grading': True},
            timezone.now() - datetime.timedelta(days=8),
            True  # Should grade
        ),
        (
            {'must_grade': 1, 'must_be_graded_by': 10},
            timezone.now() - datetime.timedelta(days=8),
            False  # flexible grading not enabled, shouldn't grade
        ),
        (
            {'must_grade': 1, 'must_be_graded_by': 10, 'enable_flexible_grading': True},
            timezone.now() - datetime.timedelta(days=5),
            False  # only 5 days old submission, shouldn't grade
        )
    )
    @unpack
    def test_flexible_peer_grade_averaging(self, requirements, submission_date, is_graded):
        """
        Test if flexible peer grad averaging works.

        Even though required_graded_by is set to 10, as flexible grading enabled,
        if the submission is 7 days old and there is already 3 peer assessment provided,
        it should grade the student submission without any more wait.
        """

        required_graded_by = requirements['must_be_graded_by']

        user_submissions = []

        # create some submission and students
        for i in range(10):
            user_submissions.append(
                self._create_student_and_submission(
                    f'Student{i}',
                    f'Student{i} submission',
                    date=submission_date
                )
            )

        # make workflow date equals to the submission_date.
        # We need this because we depend on workflow.created_at to determine
        # if the submission is min 7 days old
        for i, value in enumerate(user_submissions):
            sub, _ = value
            workflow = PeerWorkflow.get_by_submission_uuid(sub['uuid'])
            workflow.created_at = submission_date
            workflow.save()

        # pylint: disable=inconsistent-return-statements
        def get_submission_index(target_submission):
            for i, value in enumerate(user_submissions):
                submission, _ = value
                if target_submission['uuid'] == submission['uuid']:
                    return i

        # Do peer 3 assessment on 1st submission
        for i in range(4):
            sub, student = user_submissions[i]
            # User 0 can't assess themselves so they assess learner 1 but the next three assess learner 0
            submission_to_assess = peer_api.get_submission_to_assess(sub['uuid'], student['student_id'])
            assert get_submission_index(submission_to_assess) == (1 if i == 0 else 0)

            peer_api.create_assessment(
                sub['uuid'],
                student['student_id'],
                ASSESSMENT_DICT['options_selected'],
                ASSESSMENT_DICT['criterion_feedback'],
                ASSESSMENT_DICT['overall_feedback'],
                RUBRIC_DICT,
                required_graded_by
            )
        # check grade of 1st submission.
        score = peer_api.get_score(user_submissions[0][0]['uuid'], requirements, COURSE_SETTINGS)

        if is_graded:
            assert score is not None
            assert isinstance(score, dict)
        else:
            assert score is None

    def test_flexible_peer_grading__zero_graded(self):
        """
        Test that flexible peer graing won't round someone down to requiring zero assessments
        """
        # create a student with a submission from eight days ago
        submission_date = timezone.now() - datetime.timedelta(days=8)
        submission, _ = self._create_student_and_submission(
            'test-student',
            'student-submission',
            date=submission_date
        )
        # Backdate created_by so that flexible grading kicks in
        workflow = PeerWorkflow.get_by_submission_uuid(submission['uuid'])
        workflow.created_at = submission_date
        workflow.save()

        # The learner has not been graded by anyone, but flexible grading rounds the required 3 to .9 and casts to 0
        # The must_grade = 0 is technically disallowed by validation rules but these api calls don't care
        requirements = {'must_grade': 0, 'must_be_graded_by': 3, 'enable_flexible_grading': True}
        self.assertEqual(1, peer_api.required_peer_grades(submission['uuid'], requirements, COURSE_SETTINGS))
        self.assertIsNone(peer_api.get_score(submission['uuid'], requirements, COURSE_SETTINGS))

    @staticmethod
    def _create_student_and_submission(student, answer, date=None, steps=None):
        """ Creats a student and submission for tests. """
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student
        submission = sub_api.create_submission(new_student_item, answer, date)
        peer_api.on_start(submission["uuid"])
        workflow_api.create_workflow(submission["uuid"], steps or STEPS)
        return submission, new_student_item

    def _assert_assessment_workflow_status(self, uuid, expected_status, step_requirements, course_settings):
        workflow = workflow_api.get_workflow_for_submission(uuid, step_requirements, course_settings)
        self.assertEqual(workflow['status'], expected_status)

    def test_get_waiting_step_details__peer_item_created_not_assessed(self):
        """
        PeerWorkflowItem objects are created when a peer is assigned another peer to grade.
        Make sure that they aren't counted as "recieved peer grades" unless an assessment has
        actually been formed.
        """
        step_requirements = {'peer': {'must_grade': 1, 'must_be_graded_by': 2}}

        # a target student and submission, and some other students and submissions
        target_learner_sub, target_learner = self._create_student_and_submission(
            'TargetLearner',
            'TargetLearner submission',
            steps=['peer']
        )
        other_learner_submissions = [
            self._create_student_and_submission(f'Student{i}', f'Student{i} submission', steps=['peer'])
            for i in range(5)
        ]

        # Have the target student submit her required assessment, they should now be waiting.
        peer_api.get_submission_to_assess(
            target_learner_sub['uuid'],
            target_learner['student_id']
        )
        peer_api.create_assessment(
            target_learner_sub['uuid'],
            target_learner['student_id'],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            step_requirements['peer']['must_be_graded_by']
        )
        self._assert_assessment_workflow_status(
            target_learner_sub['uuid'],
            'waiting',
            step_requirements,
            COURSE_SETTINGS
        )

        # Call get_submission_to_assess once more so that target_learner has an open incomplete peer assessment
        peer_api.get_submission_to_assess(target_learner_sub['uuid'], target_learner['student_id'])

        # Call get_submission_to_assess so all five learners in other_learner_submissions are
        # currently assessing target_learner
        for sub, student in other_learner_submissions:
            chosen_submission = peer_api.get_submission_to_assess(sub['uuid'], student['student_id'])
            self.assertIsNotNone(chosen_submission)
            self.assertEqual(chosen_submission['uuid'], target_learner_sub['uuid'])

        # Make one other learner assess the target learner, just so we're sure the
        # `graded` value at the end is loaded correctly
        peer_api.create_assessment(
            other_learner_submissions[0][0]['uuid'],
            other_learner_submissions[0][1]['student_id'],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            step_requirements['peer']['must_be_graded_by']
        )

        # The target learner is still in waiting and has five items but only one peer grade
        self._assert_assessment_workflow_status(
            target_learner_sub['uuid'],
            'waiting',
            step_requirements,
            COURSE_SETTINGS
        )
        self.assertEqual(PeerWorkflow.get_by_submission_uuid(target_learner_sub['uuid']).graded_by.count(), 5)
        self.assertEqual(peer_api.get_graded_by_count(target_learner_sub['uuid']), 1)

        # The learner is returned from 'get_waiting_step_details'
        students_waiting = peer_api.get_waiting_step_details(
            STUDENT_ITEM['course_id'],
            STUDENT_ITEM['item_id'],
            [target_learner_sub['uuid']] + [sub['uuid'] for sub, _ in other_learner_submissions],
            must_be_graded_by=step_requirements['peer']['must_be_graded_by'],
        )
        students_waiting = {learner['student_id']: learner for learner in students_waiting}
        target_learner_entry = students_waiting.get(target_learner['student_id'])
        self.assertIsNotNone(target_learner_entry)
        self.assertEqual(target_learner_entry['graded'], 1)
        self.assertEqual(target_learner_entry['graded_by'], 1)

    def test_flexible_peer_grading__additional_grades_after_grade(self):
        """
        When flexile grading is enabled and a learner recieves their grades,
        we should accurately record which assessments were actually used in the score.
        """
        peer_requirements = {'must_grade': 1, 'must_be_graded_by': 2, 'enable_flexible_grading': True}
        assessment_requirements = {'peer': peer_requirements}

        # Make some random learners with submissions
        other_learner_submissions = [
            self._create_student_and_submission(f'Student{i}', f'Student{i} submission', steps=['peer'])
            for i in range(3)
        ]

        # create a student with a submission from eight days ago
        submission_date = timezone.now() - datetime.timedelta(days=8)
        submission, learner = self._create_student_and_submission(
            'test-student',
            'student-submission',
            date=submission_date,
            steps=['peer']
        )
        # Backdate created_by so that flexible grading kicks in
        workflow = PeerWorkflow.get_by_submission_uuid(submission['uuid'])
        workflow.created_at = submission_date
        workflow.save()

        # It doesn't yet have a score but only requires one peer grade
        assert peer_api.get_score(submission['uuid'], peer_requirements, COURSE_SETTINGS) is None
        self.assertEqual(1, peer_api.required_peer_grades(submission['uuid'], peer_requirements, COURSE_SETTINGS))

        # The target learner assesses a peer, so they have completed their requirements.
        peer_api.get_submission_to_assess(submission['uuid'], learner['student_id'])
        peer_api.create_assessment(
            submission['uuid'],
            learner['student_id'],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            peer_requirements['must_be_graded_by']
        )

        # Helper function to peer assess until we peer assess the target learner
        def peer_assess_until_we_assess_target_submission(other_learner_index, assessment_dict):
            grading_learner_submission, grading_learner = other_learner_submissions[other_learner_index]
            current_peer_review_uuid = 'None'
            while current_peer_review_uuid != submission['uuid']:
                submission_to_assess = peer_api.get_submission_to_assess(
                    grading_learner_submission['uuid'],
                    grading_learner['student_id']
                )
                current_peer_review_uuid = submission_to_assess['uuid']
                peer_api.create_assessment(
                    grading_learner_submission['uuid'],
                    grading_learner['student_id'],
                    assessment_dict['options_selected'],
                    assessment_dict['criterion_feedback'],
                    assessment_dict['overall_feedback'],
                    RUBRIC_DICT,
                    peer_requirements['must_be_graded_by']
                )

        # One learner reviews the target learner. The target learner has now recieved enough reviews
        # and recieves a grade (0)
        peer_assess_until_we_assess_target_submission(0, ASSESSMENT_DICT_FAIL)
        workflow = workflow_api.update_from_assessments(submission['uuid'], assessment_requirements, COURSE_SETTINGS)
        assert workflow['status'] == 'done'
        assert workflow['score']['points_earned'] == 0
        assert workflow['score']['points_possible'] == 14

        peer_score = peer_api.get_score(submission['uuid'], peer_requirements, COURSE_SETTINGS)
        assessment_1 = Assessment.objects.get(submission_uuid=submission['uuid'])
        assert assessment_1.peerworkflowitem_set.first().scored
        assert peer_score == {
            "points_earned": 0,
            "points_possible": 14,
            "contributing_assessments": [assessment_1.id],
            "staff_id": None,
        }

        # Two more learners peer assess the target learner
        peer_assess_until_we_assess_target_submission(1, ASSESSMENT_DICT_PASS)
        peer_assess_until_we_assess_target_submission(2, ASSESSMENT_DICT_PASS)

        peer_score = peer_api.get_score(submission['uuid'], peer_requirements, COURSE_SETTINGS)
        workflow = workflow_api.update_from_assessments(submission['uuid'], assessment_requirements, COURSE_SETTINGS)
        item_qs = PeerWorkflowItem.objects.filter(author__student_id=learner['student_id'])
        # Get the three PeerWorkflowItems in order. Student 1, 2, 3
        items = [item_qs.get(scorer__student_id=other_learner_submissions[i][1]['student_id']) for i in [0, 1, 2]]
        # Flexible peer grading only includes the first score in the actual grade,
        # so only the first item should be `scored`
        assert items[0].scored and not items[1].scored and not items[2].scored
        # Contributing assessments is still not reflecting "scored" but the points should match the workflow
        assert peer_score == {
            "points_earned": 0,
            "points_possible": 14,
            "contributing_assessments": [item.assessment_id for item in items],
            "staff_id": None,
        }
        # Workflow hasn't changed, the score is still the same
        assert workflow['status'] == 'done'
        assert workflow['score']['points_earned'] == 0
        assert workflow['score']['points_possible'] == 14

        assert peer_score['points_earned'] == workflow['score']['points_earned']

    @unpack
    @data(
        (True, True, True),
        (True, False, True),
        (False, True, True),
        (False, False, False)
    )
    def test_flexible_peer_grading_enabled(self, block_setting, course_override, expected_flexible):
        """ Test for the behavior for flexible_peer_grading_enabled """
        result = peer_api.flexible_peer_grading_enabled(
            {"enable_flexible_grading": block_setting},
            {"force_on_flexible_peer_openassessments": course_override}
        )
        assert result == expected_flexible

    def test_get_active_assessment(self):
        """
        Test for behavior of get_active_assessment
        """
        # Three learners and submissions
        alice_sub, _ = self._create_student_and_submission('alice', 'alice sub', steps=['peer'])
        bob_sub, _ = self._create_student_and_submission('bob', 'bob sub', steps=['peer'])
        carlos_sub, _ = self._create_student_and_submission('carlos', 'carlos sub', steps=['peer'])

        # No one has any active assessment currently
        assert peer_api.get_active_assessment_submission(alice_sub['uuid']) is None
        assert peer_api.get_active_assessment_submission(bob_sub['uuid']) is None
        assert peer_api.get_active_assessment_submission(carlos_sub['uuid']) is None

        # Alice requests a peer to grade and is assigned bob
        sub = peer_api.get_submission_to_assess(alice_sub['uuid'], 3)
        assert sub['uuid'] == bob_sub['uuid']

        # Alice's active assessment is now Bob, and Bob is unaffected
        assert peer_api.get_active_assessment_submission(alice_sub['uuid'])['uuid'] == bob_sub['uuid']
        assert peer_api.get_active_assessment_submission(bob_sub['uuid']) is None

        # Alice assesses Bob and then should have no active assessment
        peer_api.create_assessment(
            alice_sub['uuid'],
            'alice',
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            3
        )
        assert peer_api.get_active_assessment_submission(alice_sub['uuid']) is None

        # Alice requests a new peer to assess and gets Carlos, who is now her active assessment
        sub = peer_api.get_submission_to_assess(alice_sub['uuid'], 3)
        assert sub['uuid'] == carlos_sub['uuid']
        assert peer_api.get_active_assessment_submission(alice_sub['uuid'])['uuid'] == carlos_sub['uuid']

        # Assess Carlos, active assessment is now None
        peer_api.create_assessment(
            alice_sub['uuid'],
            'alice',
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            RUBRIC_DICT,
            3
        )
        assert peer_api.get_active_assessment_submission(alice_sub['uuid']) is None

        # There are no more peers to assess, and the returned None does not affect the active assessment
        assert peer_api.get_submission_to_assess(alice_sub['uuid'], 3) is None
        assert peer_api.get_active_assessment_submission(alice_sub['uuid']) is None

    def test_get_active_assessment_cancelled(self):
        # Two learners and submissions
        alice_sub, _ = self._create_student_and_submission('alice', 'alice sub', steps=['peer'])
        bob_sub, _ = self._create_student_and_submission('bob', 'bob sub', steps=['peer'])

        # Alice requests a peer to grade and is assigned bob
        sub = peer_api.get_submission_to_assess(alice_sub['uuid'], 3)
        assert sub['uuid'] == bob_sub['uuid']

        # Alice is then cancelled, so then her active assessment is None
        workflow_api.cancel_workflow(
            alice_sub['uuid'], "cancel", "1", STEP_REQUIREMENTS, COURSE_SETTINGS
        )
        assert peer_api.get_active_assessment_submission(alice_sub['uuid']) is None

    def test_get_active_assessment_nonexistant(self):
        # If we request the active assessment submission for a nonexistant workflow,
        # raise an error
        with self.assertRaises(PeerAssessmentWorkflowError):
            peer_api.get_active_assessment_submission('nonexistant-uuid')

    def test_get_active_assessment_error(self):
        # Two learners and submissions
        alice_sub, _ = self._create_student_and_submission('alice', 'alice sub', steps=['peer'])
        bob_sub, bob_item = self._create_student_and_submission('bob', 'bob sub', steps=['peer'])

        # Alice requests a peer to grade and is assigned bob
        sub = peer_api.get_submission_to_assess(alice_sub['uuid'], 3)
        assert sub['uuid'] == bob_sub['uuid']

        # Delete bob's submission to induce an error
        sub_api.reset_score(
            bob_item['student_id'],
            bob_item['course_id'],
            bob_item['item_id'],
            clear_state=True,
            emit_signal=False
        )

        # Expected error is raised
        with self.assertRaises(PeerAssessmentWorkflowError):
            peer_api.get_active_assessment_submission(alice_sub['uuid'])


class PeerWorkflowTest(CacheResetTest):
    """
    Tests for the peer workflow model.
    """
    STUDENT_ITEM = {
        'student_id': 'test_student',
        'course_id': 'test_course',
        'item_type': 'openassessment',
        'item_id': 'test_item'
    }

    OTHER_STUDENT = {
        'student_id': 'test_student_2',
        'course_id': 'test_course',
        'item_type': 'openassessment',
        'item_id': 'test_item'
    }

    def test_create_item_multiple_available(self):
        # Bugfix TIM-572
        submitter_sub = sub_api.create_submission(self.STUDENT_ITEM, 'test answer')
        submitter_workflow = PeerWorkflow.objects.create(
            student_id=self.STUDENT_ITEM['student_id'],
            item_id=self.STUDENT_ITEM['item_id'],
            course_id=self.STUDENT_ITEM['course_id'],
            submission_uuid=submitter_sub['uuid']
        )
        scorer_sub = sub_api.create_submission(self.OTHER_STUDENT, 'test answer 2')
        scorer_workflow = PeerWorkflow.objects.create(
            student_id=self.OTHER_STUDENT['student_id'],
            item_id=self.OTHER_STUDENT['item_id'],
            course_id=self.OTHER_STUDENT['course_id'],
            submission_uuid=scorer_sub['uuid']
        )

        for _ in range(2):
            PeerWorkflowItem.objects.create(
                scorer=scorer_workflow,
                author=submitter_workflow,
                submission_uuid=submitter_sub['uuid']
            )

        # This used to cause an error when `get_or_create` returned multiple workflow items
        PeerWorkflow.create_item(scorer_workflow, submitter_sub['uuid'])


class AssessmentFeedbackTest(CacheResetTest):
    """
    Tests for assessment feedback.
    This is feedback that students give in response to the peer assessments they receive.
    """

    def setUp(self):
        super().setUp()
        self.feedback = AssessmentFeedback.objects.create(
            submission_uuid='test_submission',
            feedback_text='test feedback',
        )

    def test_default_options(self):
        self.assertEqual(self.feedback.options.count(), 0)

    def test_add_options_all_new(self):
        # We haven't created any feedback options yet, so these should be created.
        self.feedback.add_options(['I liked my assessment', 'I thought my assessment was unfair'])

        # Check the feedback options
        options = self.feedback.options.all()
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0].text, 'I liked my assessment')
        self.assertEqual(options[1].text, 'I thought my assessment was unfair')

    def test_add_options_some_new(self):
        # Create one feedback option in the database
        AssessmentFeedbackOption.objects.create(text='I liked my assessment')

        # Add feedback options.  The one that's new should be created.
        self.feedback.add_options(['I liked my assessment', 'I thought my assessment was unfair'])

        # Check the feedback options
        options = self.feedback.options.all()
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0].text, 'I liked my assessment')
        self.assertEqual(options[1].text, 'I thought my assessment was unfair')

    def test_add_options_empty(self):
        # No options
        self.feedback.add_options([])
        self.assertEqual(len(self.feedback.options.all()), 0)

        # Add an option
        self.feedback.add_options(['test'])
        self.assertEqual(len(self.feedback.options.all()), 1)

        # Add an empty list of options
        self.feedback.add_options([])
        self.assertEqual(len(self.feedback.options.all()), 1)

    def test_add_options_duplicates(self):

        # Add some options, which will be created
        self.feedback.add_options(['I liked my assessment', 'I thought my assessment was unfair'])

        # Add some more options, one of which is a duplicate
        self.feedback.add_options(['I liked my assessment', 'I disliked my assessment'])

        # There should be three options
        options = self.feedback.options.all()
        self.assertEqual(len(options), 3)
        self.assertEqual(options[0].text, 'I liked my assessment')
        self.assertEqual(options[1].text, 'I thought my assessment was unfair')
        self.assertEqual(options[2].text, 'I disliked my assessment')

        # There should be only three options in the database
        self.assertEqual(AssessmentFeedbackOption.objects.count(), 3)

    def test_add_options_all_old(self):
        # Add some options, which will be created
        self.feedback.add_options(['I liked my assessment', 'I thought my assessment was unfair'])

        # Add some more options, all of which are duplicates
        self.feedback.add_options(['I liked my assessment', 'I thought my assessment was unfair'])

        # There should be two options
        options = self.feedback.options.all()
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0].text, 'I liked my assessment')
        self.assertEqual(options[1].text, 'I thought my assessment was unfair')

        # There should be two options in the database
        self.assertEqual(AssessmentFeedbackOption.objects.count(), 2)

    def test_unicode(self):
        # Create options with unicode
        self.feedback.add_options(['𝓘 𝓵𝓲𝓴𝓮𝓭 𝓶𝔂 𝓪𝓼𝓼𝓮𝓼𝓼𝓶𝓮𝓷𝓽', 'ﾉ ｲんougんｲ ﾶﾘ ﾑ丂丂乇丂丂ﾶ乇刀ｲ wﾑ丂 u刀ｷﾑﾉ尺'])

        # There should be two options in the database
        self.assertEqual(AssessmentFeedbackOption.objects.count(), 2)
