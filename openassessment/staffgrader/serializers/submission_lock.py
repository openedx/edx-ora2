"""
Serializers for submission locks
"""
from rest_framework import serializers
from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock


class SubmissionLockSerializer(serializers.ModelSerializer):
    """
    Serialized info about a submission lock.

    Notes:
    - Passing an empty dict returns ony the locked status, useful for frontend which needs to know locked status.
    - Need to provide context={'user_id': <anon-user-id>} for proper "lock_status" serialization.
    """
    requires_context = True

    submission_uuid = serializers.CharField(required=False)
    owner_id = serializers.CharField(required=False)
    created_at = serializers.DateTimeField(required=False)
    lock_status = serializers.SerializerMethodField()

    def get_lock_status(self, instance):
        """
        Get the lock status, one of:
        - "in-progress" - querying user has the active lock
        - "locked" - a lock is owned by another user
        - "unlocked" - no lock exists for this submission

        NOTE: context={'user_id': <anon-user-id>} must be provided to serializer fo this to be accurate
        """
        if not instance or (not instance.is_active):
            return "unlocked"
        elif instance.owner_id == self.context.get('user_id'):
            return "in-progress"
        else:
            return "locked"

    class Meta:
        model = SubmissionGradingLock
        fields = [
            'submission_uuid',
            'owner_id',
            'created_at',
            'lock_status',
        ]
        read_only_fields = fields
