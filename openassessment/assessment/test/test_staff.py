# coding=utf-8
import datetime
import pytz
import copy

from django.db import DatabaseError, IntegrityError
from django.utils import timezone
from ddt import ddt, file_data
from mock import patch
from nose.tools import raises

from openassessment.test_utils import CacheResetTest
from openassessment.assessment.api import staff as staff_api
from openassessment.assessment.api.self import create_assessment as self_assess
from openassessment.assessment.models import (
    Assessment, AssessmentPart, AssessmentFeedback, AssessmentFeedbackOption,
    PeerWorkflow, PeerWorkflowItem
)
from openassessment.workflow import api as workflow_api
from submissions import api as sub_api

STUDENT_ITEM = dict(
    student_id="Tim",
    course_id="Demo_Course",
    item_id="item_one",
    item_type="Peer_Submission",
)

ANSWER_ONE = u"this is my answer!"

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

# Answers are against RUBRIC_DICT -- this is worth 14 points
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

# Answers are against RUBRIC_DICT -- this is worth 14 points
# Feedback text is one character over the limit.
LONG_FEEDBACK_TEXT = u"是" * Assessment.MAX_FEEDBACK_SIZE + "."
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



@ddt
class TestStaffOverwrite(CacheResetTest):
    """
    Tests for staff assessments made as overrides, when none is required to exist.
    """

    STEPS = ['self']
    STEP_REQUIREMENTS = {}

    def test_create_assessment_points(self):
        tim_sub, tim = self.create_student_and_submission("Tim", "Tim's answer")

        assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            ASSESSMENT_DICT['options_selected'], dict(), "",
            RUBRIC_DICT,
        )
        self.assertEqual(assessment["points_earned"], 6)
        self.assertEqual(assessment["points_possible"], 14)

        #ensure submission is marked as finished now

    def test_create_assessment_overrides(self):
        tim_sub, tim = self.create_student_and_submission("Tim", "Tim's answer")

        self_assessment = self_assess(
            tim_sub["uuid"],
            tim["student_id"],
            ASSESSMENT_DICT['options_selected'], dict(), "",
            RUBRIC_DICT,
        )
        workflow_api.update_from_assessments(tim_sub["uuid"], self.STEP_REQUIREMENTS)

        self.assertEqual(self_assessment["points_earned"], 6)
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], self.STEP_REQUIREMENTS)
        self.assertEqual(workflow["score"]["points_earned"], 6)

        staff_assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            ASSESSMENT_DICT_PASS['options_selected'], dict(), "",
            RUBRIC_DICT,
        )
        workflow_api.update_from_assessments(tim_sub["uuid"], self.STEP_REQUIREMENTS, force_update_score=True)
        self.assertEqual(staff_assessment["points_earned"], 14)
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], self.STEP_REQUIREMENTS)
        self.assertEqual(workflow["score"]["points_earned"], 14)

    def test_create_assessment_does_not_block(self):
        #create a submission
        tim_sub, tim = self.create_student_and_submission("Tim", "Tim's answer")

        #staff assess it
        staff_assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            ASSESSMENT_DICT_PASS['options_selected'], dict(), "",
            RUBRIC_DICT,
        )
        workflow_api.update_from_assessments(tim_sub["uuid"], self.STEP_REQUIREMENTS, force_update_score=True)

        #ensure points are what we expect
        self.assertEqual(staff_assessment["points_earned"], 14)
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], self.STEP_REQUIREMENTS)
        self.assertEqual(workflow["score"]["points_earned"], 14)

        #self assess it, ensure assessment is recorded
        self_assessment = self_assess(
            tim_sub["uuid"],
            tim["student_id"],
            ASSESSMENT_DICT['options_selected'], dict(), "",
            RUBRIC_DICT,
        )
        self.assertEqual(self_assessment["points_earned"], 6)

        #ensure points are not updated
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], self.STEP_REQUIREMENTS)
        self.assertEqual(workflow["score"]["points_earned"], 14)

    def create_student_and_submission(self, student, answer, date=None):
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student
        submission = sub_api.create_submission(new_student_item, answer, date)
        workflow_api.create_workflow(submission["uuid"], self.STEPS)
        return submission, new_student_item
