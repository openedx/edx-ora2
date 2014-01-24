"""
Serializers are created to ensure models do not have to be accessed outside the scope of the Tim APIs.
"""
from rest_framework import serializers
from submissions.models import StudentItem, Submission, Score


class StudentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentItem
        fields = ('student_id', 'course_id', 'item_id', 'item_type')


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ('student_item', 'attempt_number', 'submitted_at', 'created_at', 'answer')


class ScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Score
        fields = ('student_item', 'submission', 'points_earned', 'points_possible', 'created_at')
