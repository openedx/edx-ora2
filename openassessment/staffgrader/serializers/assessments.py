"""
Serializers for assessment details for the ESG app
"""

from rest_framework import serializers
from openassessment.assessment.models.base import Assessment, AssessmentPart


# pylint: disable=abstract-method
class SubmissionDetailFileSerilaizer(serializers.Serializer):
    """
    Serialized info about a single file
    """
    download_url = serializers.URLField()
    description = serializers.CharField()
    name = serializers.CharField()


class AssessmentPartSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='criterion.name')
    option = serializers.CharField(source='option.name', default=None)

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
