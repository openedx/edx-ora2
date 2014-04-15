"""
Tests for submission models.
"""

from django.test import TestCase
from submissions.models import Submission, Score, ScoreSummary, StudentItem


class TestScoreSummary(TestCase):
    """
    Test selection of options from a rubric.
    """

    def test_latest(self):
        item = StudentItem.objects.create(
            student_id="score_test_student",
            course_id="score_test_course",
            item_id="i4x://mycourse/class_participation.section_attendance"
        )
        first_score = Score.objects.create(
            student_item=item,
            submission=None,
            points_earned=8,
            points_possible=10,
        )
        second_score = Score.objects.create(
            student_item=item,
            submission=None,
            points_earned=5,
            points_possible=10,
        )
        latest_score = ScoreSummary.objects.get(student_item=item).latest
        self.assertEqual(second_score, latest_score)


    def test_highest(self):
        item = StudentItem.objects.create(
            student_id="score_test_student",
            course_id="score_test_course",
            item_id="i4x://mycourse/special_presentation"
        )

        # Low score is higher than no score...
        low_score = Score.objects.create(
            student_item=item,
            points_earned=0,
            points_possible=0,
        )
        self.assertEqual(
            low_score,
            ScoreSummary.objects.get(student_item=item).highest
        )

        # Medium score should supplant low score
        med_score = Score.objects.create(
            student_item=item,
            points_earned=8,
            points_possible=10,
        )
        self.assertEqual(
            med_score,
            ScoreSummary.objects.get(student_item=item).highest
        )

        # Even though the points_earned is higher in the med_score, high_score
        # should win because it's 4/4 as opposed to 8/10.
        high_score = Score.objects.create(
            student_item=item,
            points_earned=4,
            points_possible=4,
        )
        self.assertEqual(
            high_score,
            ScoreSummary.objects.get(student_item=item).highest
        )

        # Put another medium score to make sure it doesn't get set back down
        med_score2 = Score.objects.create(
            student_item=item,
            points_earned=5,
            points_possible=10,
        )
        self.assertEqual(
            high_score,
            ScoreSummary.objects.get(student_item=item).highest
        )
        self.assertEqual(
            med_score2,
            ScoreSummary.objects.get(student_item=item).latest
        )

    def test_reset_score_highest(self):
        item = StudentItem.objects.create(
            student_id="score_test_student",
            course_id="score_test_course",
            item_id="i4x://mycourse/special_presentation"
        )

        # Reset score with no score
        Score.create_reset_score(item)
        highest = ScoreSummary.objects.get(student_item=item).highest
        self.assertEqual(highest.points_earned, 0)
        self.assertEqual(highest.points_possible, 0)

        # Non-reset score after a reset score
        submission = Submission.objects.create(student_item=item, attempt_number=1)
        Score.objects.create(
            student_item=item,
            submission=submission,
            points_earned=2,
            points_possible=3,
        )
        highest = ScoreSummary.objects.get(student_item=item).highest
        self.assertEqual(highest.points_earned, 2)
        self.assertEqual(highest.points_possible, 3)

        # Reset score after a non-reset score
        Score.create_reset_score(item)
        highest = ScoreSummary.objects.get(student_item=item).highest
        self.assertEqual(highest.points_earned, 0)
        self.assertEqual(highest.points_possible, 0)

    def test_highest_score_hidden(self):
        item = StudentItem.objects.create(
            student_id="score_test_student",
            course_id="score_test_course",
            item_id="i4x://mycourse/special_presentation"
        )

        # Score with points possible set to 0
        # (by convention a "hidden" score)
        submission = Submission.objects.create(student_item=item, attempt_number=1)
        Score.objects.create(
            student_item=item,
            submission=submission,
            points_earned=0,
            points_possible=0,
        )
        highest = ScoreSummary.objects.get(student_item=item).highest
        self.assertEqual(highest.points_earned, 0)
        self.assertEqual(highest.points_possible, 0)

        # Score with points
        submission = Submission.objects.create(student_item=item, attempt_number=1)
        Score.objects.create(
            student_item=item,
            submission=submission,
            points_earned=1,
            points_possible=2,
        )
        highest = ScoreSummary.objects.get(student_item=item).highest
        self.assertEqual(highest.points_earned, 1)
        self.assertEqual(highest.points_possible, 2)

        # Another score with points possible set to 0
        # The previous score should remain the highest score.
        submission = Submission.objects.create(student_item=item, attempt_number=1)
        Score.objects.create(
            student_item=item,
            submission=submission,
            points_earned=0,
            points_possible=0,
        )
        highest = ScoreSummary.objects.get(student_item=item).highest
        self.assertEqual(highest.points_earned, 1)
        self.assertEqual(highest.points_possible, 2)
