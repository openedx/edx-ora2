"""
Serializers for submission locks
"""
from rest_framework import serializers

from openassessment.assessment.models.staff import StaffWorkflow, TeamStaffWorkflow


class SubmissionLockSerializer(serializers.ModelSerializer):
    """
    Create response payload with info about the workflow and operation success/failure
    """
    class Meta:
        model = StaffWorkflow
        fields = [
            'submission_uuid',
            'is_being_graded',
            'grading_started_at',
            'grading_completed_at',
            'scorer_id'
        ]


class TeamSubmissionLockSerializer(serializers.ModelSerializer):
    """
    Create response payload with info about the workflow and operation success/failure
    """
    class Meta:
        model = TeamStaffWorkflow
        fields = [
            'team_submission_uuid',
            'is_being_graded',
            'grading_started_at',
            'grading_completed_at',
            'scorer_id'
        ]
