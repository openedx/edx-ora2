"""
Models for locking Submissions for exclusive grading.
Part of Enhanced Staff Grader (ESG).
"""
from django.db import models
from django.utils.timezone import now

from openassessment.assessment.models.staff import StaffWorkflow
from openassessment.staffgrader.errors.submission_lock import SubmissionLockContestedError


class SubmissionGradingLock(models.Model):
    """
    Internal model for locking a submission for exclusive grading
    """
    TIMEOUT = StaffWorkflow.TIME_LIMIT

    # NOTE - submission_uuid can refer to either the team or individual submission
    submission_uuid = models.CharField(max_length=128, db_index=True, unique=True)
    owner_id = models.CharField(max_length=40)
    created_at = models.DateTimeField(default=now)

    class Meta:
        app_label = "staffgrader"
        ordering = ["created_at", "id"]

    @property
    def is_active(self):
        """
        Check if lock is still active (has not timed out)
        """
        return now() < self.created_at + self.TIMEOUT

    @classmethod
    def currently_active(cls):
        """
        Returns a SubmissionGradingLock queryset filtered to only entries that are currently
        'active' (that were created less than SubmissionGradingLock.TIMEOUT ago)
        """
        timeout_threshold = now() - cls.TIMEOUT
        return cls.objects.filter(created_at__gt=timeout_threshold)

    @classmethod
    def get_submission_lock(cls, submission_uuid):
        """
        Get info about a submission grading lock

        Returns: SubmissionGradingLock info or None
        """
        return cls.objects.filter(submission_uuid=submission_uuid).first()

    @classmethod
    def claim_submission_lock(cls, submission_uuid, user_id):
        """
        Try to claim a submission grading lock

        Returns: SubmissionGradingLock or raises Error
        """
        # See if there's already a lock
        current_lock = cls.get_submission_lock(submission_uuid)

        # If there's already an active lock, raise an error
        # Unless the lock owner is trying to reacquire a lock, which is allowed
        if current_lock and current_lock.is_active and current_lock.owner_id != user_id:
            raise SubmissionLockContestedError

        # Otherwise, delete the lock. This is needed so we don't violate the unique submission_uuid constraint
        if current_lock:
            current_lock.delete()

        # Create a new lock
        new_lock = cls.objects.create(
            owner_id=user_id,
            submission_uuid=submission_uuid,
        )

        return new_lock

    @classmethod
    def clear_submission_lock(cls, submission_uuid, user_id):
        """
        Clear an existing lock. Locks can only be cleared by the lock owner

        Returns: None or raises Error
        """
        # Get the current lock, assuming it exists
        current_lock = cls.get_submission_lock(submission_uuid)
        if not current_lock:
            return

        # Only the owner can clear the lock
        if current_lock.owner_id != user_id:
            raise SubmissionLockContestedError

        current_lock.delete()

    @classmethod
    def batch_clear_submission_locks(cls, submission_uuids, user_id):
        """
        For a list of submission locks to try to clear, clear those that we own.

        Returns: Number of submission locks cleared
        """
        return cls.objects.filter(
            submission_uuid__in=submission_uuids, owner_id=user_id
        ).delete()[0]
