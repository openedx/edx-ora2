"""
Serializers are created to ensure models do not have to be accessed outside the
scope of the ORA2 APIs.
"""
from __future__ import absolute_import

from rest_framework import serializers

from openassessment.workflow.models import AssessmentWorkflow, AssessmentWorkflowCancellation, TeamAssessmentWorkflow


class AssessmentWorkflowSerializer(serializers.ModelSerializer):
    """
    Serialize a AssessmentWorkflow' model.
    """
    score = serializers.ReadOnlyField(required=False)

    class Meta:
        model = AssessmentWorkflow
        fields = (
            'submission_uuid',
            'status',
            'created',
            'modified',

            # Computed
            'score'
        )


class TeamAssessmentWorkflowSerializer(serializers.ModelSerializer):
    """
    Serialize a TeamAssessmentWorkflow model.
    """
    score = serializers.ReadOnlyField(required=False)

    class Meta:
        model = TeamAssessmentWorkflow
        fields = (
            'team_submission_uuid',
            'submission_uuid',
            'status',
            'created',
            'modified',

            # Computed
            'score'
        )


class AssessmentWorkflowCancellationSerializer(serializers.ModelSerializer):
    """
    Serialize a `AssessmentWorkflowCancellation` model.
    """

    class Meta:
        model = AssessmentWorkflowCancellation
        fields = (
            'comments',
            'cancelled_by_id',
            'created_at',
        )
