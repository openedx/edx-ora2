"""
Serializers are created to ensure models do not have to be accessed outside the
scope of the ORA2 APIs.
"""
from rest_framework import serializers
from openassessment.workflow.models import AssessmentWorkflow, AssessmentWorkflowCancellation


class AssessmentWorkflowSerializer(serializers.ModelSerializer):
    score = serializers.ReadOnlyField(required=False)

    class Meta:
        model = AssessmentWorkflow
        fields = (
            'uuid',
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
