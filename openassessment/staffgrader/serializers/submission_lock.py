"""
Serializers for submission locks
"""
from rest_framework import serializers
from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock


class SubmissionLockSerializer(serializers.ModelSerializer):
    """
    Serialized info about a submission lock
    """
    class Meta:
        model = SubmissionGradingLock
        fields = [
            'submission_uuid',
            'owner_id',
            'created_at',
        ]
