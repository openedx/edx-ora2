"""
Tests for SubmissionLock model
"""
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from django.test import TestCase
from freezegun import freeze_time

from openassessment.staffgrader.errors.submission_lock import SubmissionLockContestedError
from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock


@freeze_time("1969-07-21 02:56:00", tz_offset=0)
class TestSubmissionLockModel(TestCase):
    """ Tests for interacting with submission grading/locking """

    existing_submission_lock = None
    locked_submission_uuid = str(uuid4())

    expired_submission_lock = None
    expired_locked_submission_uuid = str(uuid4())

    unlocked_submission_uuid = str(uuid4())

    user_id = "foo"
    other_user_id = "bar"

    def setUp(self):
        super().setUp()
        self.existing_submission_lock = SubmissionGradingLock.objects.create(
            submission_uuid=self.locked_submission_uuid,
            owner_id=self.user_id,
            created_at=datetime.now(tz=timezone.utc)
        )

        self.expired_submission_lock = SubmissionGradingLock.objects.create(
            submission_uuid=self.expired_locked_submission_uuid,
            owner_id=self.user_id,
            created_at=datetime.now(tz=timezone.utc) - (SubmissionGradingLock.TIMEOUT + timedelta(hours=1))
        )

    def test_lock_active(self):
        # A lock created within the TIMEOUT is considered active
        assert self.existing_submission_lock.is_active is True

    def test_lock_inactive(self):
        # A lock created and left for more than TIMEOUT is considered inactive
        assert self.expired_submission_lock.is_active is False

    def test_get_submission_lock(self):
        # Can get an existing submission lock by submission ID
        assert SubmissionGradingLock.get_submission_lock(self.locked_submission_uuid) == self.existing_submission_lock

    def test_get_submisison_lock_none(self):
        # Getting info about a non-existing submission lock returns None
        assert SubmissionGradingLock.get_submission_lock(self.unlocked_submission_uuid) is None

    def test_claim_submission_lock(self):
        # Can claim a lock on a submission without an existing lock
        assert SubmissionGradingLock.get_submission_lock(self.unlocked_submission_uuid) is None
        new_lock = SubmissionGradingLock.claim_submission_lock(
            self.unlocked_submission_uuid,
            self.user_id
        )

        assert new_lock is not None
        assert SubmissionGradingLock.get_submission_lock(self.unlocked_submission_uuid) == new_lock

    def test_claim_submission_lock_contested(self):
        # Trying to claim a lock when someone else has a lock raises a SubmissionLockContestedError
        assert SubmissionGradingLock.get_submission_lock(self.locked_submission_uuid) == self.existing_submission_lock
        with self.assertRaises(SubmissionLockContestedError):
            SubmissionGradingLock.claim_submission_lock(self.locked_submission_uuid, self.other_user_id)

    def test_claim_submission_lock_stale(self):
        # When a submission lock has become inactive (older than TIMEOUT), it can be claimed by a new user
        new_lock = SubmissionGradingLock.claim_submission_lock(
            self.expired_locked_submission_uuid,
            self.other_user_id
        )

        assert new_lock is not None
        assert SubmissionGradingLock.get_submission_lock(self.expired_locked_submission_uuid) == new_lock

    def test_clear_submission_lock(self):
        # clear_submission_lock removes the existing lock
        assert SubmissionGradingLock.get_submission_lock(self.locked_submission_uuid) == self.existing_submission_lock
        SubmissionGradingLock.clear_submission_lock(self.locked_submission_uuid, self.user_id)
        assert SubmissionGradingLock.get_submission_lock(self.locked_submission_uuid) is None

    def test_clear_submission_lock_contested(self):
        # clear_submission_lock blocks you from clearing a lock owned by another user
        assert SubmissionGradingLock.get_submission_lock(self.locked_submission_uuid) == self.existing_submission_lock
        with self.assertRaises(SubmissionLockContestedError):
            SubmissionGradingLock.clear_submission_lock(self.locked_submission_uuid, self.other_user_id)
