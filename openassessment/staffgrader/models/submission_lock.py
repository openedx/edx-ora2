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
    owner_id = models.CharField(max_length=40, db_index=True)
    created_at = models.DateTimeField(db_index=True)

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
        if current_lock and current_lock.is_active:
            raise SubmissionLockContestedError(f"Submission already locked")

        # Otherwise, create a new lock
        new_lock, created = cls.objects.update_or_create(
            owner_id=user_id,
            created_at=now(),
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
            raise SubmissionLockContestedError(f"Unable to clear submission lock")

        current_lock.delete()
