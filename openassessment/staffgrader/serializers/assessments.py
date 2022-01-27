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
    size = serializers.IntegerField()


class AssessmentPartSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='criterion.name')
    option = serializers.CharField(source='option.name', default=None)
    points = serializers.IntegerField(source='option.points', default=None)

    class Meta:
        model = AssessmentPart
        fields = ['name', 'option', 'points', 'feedback']
        read_only_fields = fields


class AssessmentScoreSerializer(serializers.ModelSerializer):
    """
    Serializer for pulling score info off the assessment and into a "score" dict
    """
    pointsEarned = serializers.IntegerField(source='points_earned')
    pointsPossible = serializers.IntegerField(source='points_possible')

    class Meta:
        model = Assessment
        fields = [
            'pointsEarned',
            'pointsPossible',
        ]


class AssessmentSerializer(serializers.ModelSerializer):
    """
    Serialized info about an assessment
    """
    criteria = AssessmentPartSerializer(source='parts', many=True, read_only=True)
    score = AssessmentScoreSerializer(source='*')

    class Meta:
        model = Assessment
        fields = [
            'feedback',
            'score',
            'criteria',
        ]
        read_only_fields = fields
