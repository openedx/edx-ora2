"""
Serializers are created to ensure models do not have to be accessed outside the
scope of the Tim APIs.
"""
from rest_framework import serializers
from openassessment.peer.models import PeerEvaluation


class PeerAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeerEvaluation
        fields = (
            'submission',
            'points_earned',
            'points_possible',
            'scored_at',
            'scorer_id',
            'score_type',
            'feedback',
        )
