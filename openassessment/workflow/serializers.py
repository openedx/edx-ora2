"""
Serializers are created to ensure models do not have to be accessed outside the
scope of the Tim APIs.
"""
from rest_framework import serializers
from openassessment.workflow.models import AssessmentWorkflow, AssessmentWorkflowCancellation


class AssessmentWorkflowSerializer(serializers.ModelSerializer):
    score = serializers.Field(source='score')

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

# Not implemented yet:
#
# class AssessmentWorkflowHistorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = AssessmentWorkflowHistory
#         fields = (
#             'workflow',
#             'app',
#             'event_type',
#             'event_data',
#             'description',
#             'created_at'
#         )


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
