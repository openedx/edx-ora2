"""
Test reset scores.
"""

import copy
from mock import patch
from django.test import TestCase
import ddt
from django.core.cache import cache
from django.db import DatabaseError
from submissions import api as sub_api
from submissions.models import ScoreSummary


@ddt.ddt
class TestResetScore(TestCase):
    """
    Test resetting scores for a specific student on a specific problem.
    """

    STUDENT_ITEM = {
        'student_id': 'Test student',
        'course_id': 'Test course',
        'item_id': 'Test item',
        'item_type': 'Test item type',
    }

    def setUp(self):
        """
        Clear the cache.
        """
        cache.clear()

    def test_reset_with_no_scores(self):
        sub_api.reset_scores(
            self.STUDENT_ITEM['course_id'],
            self.STUDENT_ITEM['student_id'],
            self.STUDENT_ITEM['item_id'],
        )
        self.assertIs(sub_api.get_score(self.STUDENT_ITEM), None)

        scores = sub_api.get_scores(self.STUDENT_ITEM['course_id'], self.STUDENT_ITEM['student_id'])
        self.assertEqual(len(scores), 0)

    def test_reset_with_one_score(self):
        # Create a submission for the student and score it
        submission = sub_api.create_submission(self.STUDENT_ITEM, 'test answer')
        sub_api.set_score(submission['uuid'], 1, 2)

        # Reset scores
        sub_api.reset_scores(
            self.STUDENT_ITEM['course_id'],
            self.STUDENT_ITEM['student_id'],
            self.STUDENT_ITEM['item_id'],
        )

        # Expect that no scores are available for the student
        self.assertIs(sub_api.get_score(self.STUDENT_ITEM), None)
        scores = sub_api.get_scores(self.STUDENT_ITEM['course_id'], self.STUDENT_ITEM['student_id'])
        self.assertEqual(len(scores), 0)

    def test_reset_with_multiple_scores(self):
        # Create a submission for the student and score it
        submission = sub_api.create_submission(self.STUDENT_ITEM, 'test answer')
        sub_api.set_score(submission['uuid'], 1, 2)
        sub_api.set_score(submission['uuid'], 2, 2)

        # Reset scores
        sub_api.reset_scores(
            self.STUDENT_ITEM['course_id'],
            self.STUDENT_ITEM['student_id'],
            self.STUDENT_ITEM['item_id'],
        )

        # Expect that no scores are available for the student
        self.assertIs(sub_api.get_score(self.STUDENT_ITEM), None)
        scores = sub_api.get_scores(self.STUDENT_ITEM['course_id'], self.STUDENT_ITEM['student_id'])
        self.assertEqual(len(scores), 0)

    @ddt.data(
        {'student_id': 'other student'},
        {'course_id': 'other course'},
        {'item_id': 'other item'},
    )
    def test_reset_different_student_item(self, changed):
        # Create a submissions for two students
        submission = sub_api.create_submission(self.STUDENT_ITEM, 'test answer')
        sub_api.set_score(submission['uuid'], 1, 2)

        other_student = copy.copy(self.STUDENT_ITEM)
        other_student.update(changed)
        submission = sub_api.create_submission(other_student, 'other test answer')
        sub_api.set_score(submission['uuid'], 3, 4)

        # Reset the score for the first student
        sub_api.reset_scores(
            self.STUDENT_ITEM['course_id'],
            self.STUDENT_ITEM['student_id'],
            self.STUDENT_ITEM['item_id'],
        )

        # The first student's scores should be reset
        self.assertIs(sub_api.get_score(self.STUDENT_ITEM), None)
        scores = sub_api.get_scores(self.STUDENT_ITEM['course_id'], self.STUDENT_ITEM['student_id'])
        self.assertNotIn(self.STUDENT_ITEM['item_id'], scores)

        # But the second student should still have a score
        score = sub_api.get_score(other_student)
        self.assertEqual(score['points_earned'], 3)
        self.assertEqual(score['points_possible'], 4)
        scores = sub_api.get_scores(other_student['course_id'], other_student['student_id'])
        self.assertIn(other_student['item_id'], scores)

    def test_reset_then_add_score(self):
        # Create a submission for the student and score it
        submission = sub_api.create_submission(self.STUDENT_ITEM, 'test answer')
        sub_api.set_score(submission['uuid'], 1, 2)

        # Reset scores
        sub_api.reset_scores(
            self.STUDENT_ITEM['course_id'],
            self.STUDENT_ITEM['student_id'],
            self.STUDENT_ITEM['item_id'],
        )

        # Score the student again
        sub_api.set_score(submission['uuid'], 3, 4)

        # Expect that the new score is available
        score = sub_api.get_score(self.STUDENT_ITEM)
        self.assertEqual(score['points_earned'], 3)
        self.assertEqual(score['points_possible'], 4)

        scores = sub_api.get_scores(self.STUDENT_ITEM['course_id'], self.STUDENT_ITEM['student_id'])
        self.assertIn(self.STUDENT_ITEM['item_id'], scores)
        self.assertEqual(scores[self.STUDENT_ITEM['item_id']], (3, 4))

    def test_reset_then_get_score_for_submission(self):
        # Create a submission for the student and score it
        submission = sub_api.create_submission(self.STUDENT_ITEM, 'test answer')
        sub_api.set_score(submission['uuid'], 1, 2)

        # Reset scores
        sub_api.reset_scores(
            self.STUDENT_ITEM['course_id'],
            self.STUDENT_ITEM['student_id'],
            self.STUDENT_ITEM['item_id'],
        )

        # If we're retrieving the score for a particular submission,
        # instead of a student item, then we should STILL get a score.
        self.assertIsNot(sub_api.get_latest_score_for_submission(submission['uuid']), None)

    @patch.object(ScoreSummary.objects, 'filter')
    def test_database_error(self, filter_mock):
        filter_mock.side_effect = DatabaseError("Test error")
        with self.assertRaises(sub_api.SubmissionInternalError):
            sub_api.reset_scores(
                self.STUDENT_ITEM['course_id'],
                self.STUDENT_ITEM['student_id'],
                self.STUDENT_ITEM['item_id'],
            )
