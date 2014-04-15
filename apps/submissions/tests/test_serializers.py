"""
Tests for submissions serializers.
"""
from django.test import TestCase
from submissions.models import Score, StudentItem
from submissions.serializers import ScoreSerializer


class ScoreSerializerTest(TestCase):
    """
    Tests for the score serializer.
    """

    def test_score_with_null_submission(self):
        item = StudentItem.objects.create(
            student_id="score_test_student",
            course_id="score_test_course",
            item_id="i4x://mycourse/special_presentation"
        )

        # Create a score with a null submission
        score = Score.objects.create(
            student_item=item,
            submission=None,
            points_earned=2,
            points_possible=6
        )
        score_dict = ScoreSerializer(score).data

        self.assertIs(score_dict['submission_uuid'], None)
        self.assertEqual(score_dict['points_earned'], 2)
        self.assertEqual(score_dict['points_possible'], 6)
