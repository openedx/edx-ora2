"""
Serializers specific to peer assessment.
"""
from rest_framework import serializers

from openassessment.assessment.models import AIWorkflow


class AIWorkflowSerializer(serializers.ModelSerializer):
    """Representation of the PeerWorkflow.

    A PeerWorkflow should not be exposed to the front end of any question.  This
    model should only be exposed externally for administrative views, in order
    to visualize the Peer Workflow.

    """

    class Meta:
        model = AIWorkflow
        fields = (
            'student_id',
            'course_id',
            'submission_uuid',
            'created_at',
            'grading_completed_at',
            'completed_at'
        )
