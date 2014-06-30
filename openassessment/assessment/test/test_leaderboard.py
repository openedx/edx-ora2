# -*- coding: utf-8 -*-
"""
Tests for leaderboard handler in Open Assessment XBlock.
"""
import datetime
import pytz
from openassessment.test_utils import CacheResetTest
from submissions.api import create_submission
from openassessment.assessment.api.leaderboard import (
    get_leaderboard
)
from openassessment.assessment.api.self import (
    create_assessment
)

class TestLeaderboardApi(CacheResetTest):

    STUDENT_ITEM_1 = {
        'student_id': '432432423432',
        'item_id': 'test_item',
        'course_id': 'test_course',
        'item_type': 'test_type'
    }

    STUDENT_GRADE_1 = '8'

    STUDENT_ANSWER_1 = "Test answer"

    OPTIONS_SELECTED_1 = {
        "clarity": "clear",
        "accuracy": "very accurate",
    }

    STUDENT_ITEM_2 = {
        'student_id': '32894032',
        'item_id': 'test_item',
        'course_id': 'test_course',
        'item_type': 'test_type'
    }

    STUDENT_GRADE_2 = '4'

    STUDENT_ANSWER_2 = "Test answer two"

    OPTIONS_SELECTED_2 = {
        "clarity": "somewhat clear",
        "accuracy": "accurate",
    }

    RUBRIC = {
        "criteria": [
            {
                "name": "clarity",
                "prompt": "How clear was it?",
                "options": [
                    {"name": "somewhat clear", "points": 1, "explanation": ""},
                    {"name": "clear", "points": 3, "explanation": ""},
                    {"name": "very clear", "points": 5, "explanation": ""},
                ]
            },
            {
                "name": "accuracy",
                "prompt": "How accurate was the content?",
                "options": [
                    {"name": "somewhat accurate", "points": 1, "explanation": ""},
                    {"name": "accurate", "points": 3, "explanation": ""},
                    {"name": "very accurate", "points": 5, "explanation": ""},
                ]
            },
        ]
    }

    def test_get_leaderboard(self):
        # Initially, the leaderboard should be an empty array
        self.assertEqual(get_leaderboard(''), [])

        # Create a submission to self-assess for student 1
        submission = create_submission(self.STUDENT_ITEM_1, self.STUDENT_ANSWER_1)

        # Create a self-assessment for the submission for student 1
        create_assessment(
            submission['uuid'], self.STUDENT_ITEM_1['student_id'],
            self.OPTIONS_SELECTED_1, self.RUBRIC,
            scored_at=datetime.datetime(2014, 4, 1).replace(tzinfo=pytz.utc)
        )

        leaderboard = get_leaderboard(submission['uuid'])

        self.assertEqual(len(leaderboard), 1)
        self.assertEqual(leaderboard[0]['content'], self.STUDENT_ANSWER_1)
        self.assertEqual(leaderboard[0]['score'], self.STUDENT_GRADE_1)

        # Create a submission to self-assess for student 1
        submission = create_submission(self.STUDENT_ITEM_2, self.STUDENT_ANSWER_2)

        # Create a self-assessment for the submission for student 1
        create_assessment(
            submission['uuid'], self.STUDENT_ITEM_2['student_id'],
            self.OPTIONS_SELECTED_2, self.RUBRIC,
            scored_at=datetime.datetime(2014, 4, 1).replace(tzinfo=pytz.utc)
        )

        leaderboard = get_leaderboard(submission['uuid'])

        self.assertEqual(len(leaderboard), 2)
        self.assertEqual(leaderboard[1]['content'], self.STUDENT_ANSWER_2)
        self.assertEqual(leaderboard[1]['score'], self.STUDENT_GRADE_2)
        self.assertEqual(leaderboard[0]['content'], self.STUDENT_ANSWER_1)
        self.assertEqual(leaderboard[0]['score'], self.STUDENT_GRADE_1)