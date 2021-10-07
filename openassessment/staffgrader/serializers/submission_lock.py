"""
Serializers for submission locks
"""
from os import read
from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock
from openassessment.assessment.models.base import Assessment, AssessmentPart
from rest_framework import serializers


class SubmissionLockSerializer(serializers.ModelSerializer):
    """
    Serialized info about a submission lock
    """
    class Meta:
        model = SubmissionGradingLock
        fields = [
            'submission_uuid',
            'owner_id',
            'created_at',
        ]


class SubmissionDetailFileSerilaizer(serializers.Serializer):
    """
    Serialized info about a single file
    """
    download_url = serializers.URLField()
    description = serializers.CharField()
    name = serializers.CharField()


class AssessmentPartSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='criterion.name')
    option = serializers.CharField(source='option.name', default='')

    class Meta:
        model = AssessmentPart
        fields = ['name', 'option', 'feedback']
        read_only_fields = fields


class AssessmentSerializer(serializers.ModelSerializer):
    """
    Serialized info about an assessment
    """
    criteria = AssessmentPartSerializer(source='parts', many=True, read_only=True)

    class Meta:
        model = Assessment
        fields = [
            'feedback',
            'points_earned',
            'points_possible',
            'criteria',
        ]
        read_only_fields = fields
