"""
Serializers specific to peer assessment.
"""


from rest_framework import serializers

from openassessment.assessment.models import (AssessmentFeedback, AssessmentFeedbackOption, PeerWorkflow,
                                              PeerWorkflowItem)

from .base import AssessmentSerializer


class AssessmentFeedbackOptionSerializer(serializers.ModelSerializer):
    """
    Serialize an `AssessmentFeedbackOption` model.
    """

    class Meta:
        model = AssessmentFeedbackOption
        fields = ('text',)


class AssessmentFeedbackSerializer(serializers.ModelSerializer):
    """
    Serialize feedback in response to an assessment.
    """
    assessments = AssessmentSerializer(many=True, default=None, required=False)
    options = AssessmentFeedbackOptionSerializer(many=True, default=None, required=False)

    class Meta:
        model = AssessmentFeedback
        fields = ('submission_uuid', 'feedback_text', 'assessments', 'options')


class PeerWorkflowSerializer(serializers.ModelSerializer):
    """Representation of the PeerWorkflow.

    A PeerWorkflow should not be exposed to the front end of any question.  This
    model should only be exposed externally for administrative views, in order
    to visualize the Peer Workflow.

    """

    class Meta:
        model = PeerWorkflow
        fields = (
            'student_id',
            'item_id',
            'course_id',
            'submission_uuid',
            'created_at',
            'completed_at'
        )


class PeerWorkflowItemSerializer(serializers.ModelSerializer):
    """Representation of the PeerWorkflowItem

    As with the PeerWorkflow, this should not be exposed to the front end. This
    should only be used to visualize the Peer Workflow in an administrative
    view.

    """

    class Meta:
        model = PeerWorkflowItem
        fields = (
            'scorer',
            'author',
            'submission_uuid',
            'started_at',
            'assessment',
            'scored'
        )
