"""
Serializers are created to ensure models do not have to be accessed outside the
scope of the Tim APIs.
"""
from rest_framework import serializers
from openassessment.workflow.models import AssessmentWorkflow


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
