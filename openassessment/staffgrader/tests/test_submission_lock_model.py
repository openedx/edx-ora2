from datetime import datetime, timedelta, timezone
from openassessment.staffgrader.errors.submission_lock import SubmissionLockContestedError

from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock

from django.test import TestCase
from freezegun import freeze_time


@freeze_time("1969-07-21 02:56:00", tz_offset=0)
class TestSubmissionLockModel(TestCase):
    """ Tests for interacting with submission grading/locking """
    existing_submission_lock = None

    test_submission_uuid = "currently_locked"
    test_user_id_1 = "foo"
    test_user_id_2 = "bar"
    test_timestamp = "1969-07-20T22:56:00-04:00"

    test_submission_uuid_without_lock = "not_currently_locked"

    def setUp(self):
        self.existing_submission_lock = SubmissionGradingLock.objects.create(
            submission_uuid=self.test_submission_uuid,
            owner_id=self.test_user_id_1,
            created_at=datetime.now(tz=timezone.utc)
        )

    def test_lock_active(self):
        # A lock created within the TIMEOUT is considered active
        assert self.existing_submission_lock.is_active is True

    def test_lock_inactive(self):
        # A lock created and left for more than TIMEOUT is considered inactive
        self.existing_submission_lock.created_at = self.existing_submission_lock.created_at - timedelta(hours=12)
        self.existing_submission_lock.save()
        assert self.existing_submission_lock.is_active is False

    def test_get_submission_lock(self):
        # Can get an existing submission lock by submission ID
        assert SubmissionGradingLock.get_submission_lock(self.test_submission_uuid) == self.existing_submission_lock

    def test_get_submisison_lock_none(self):
        # Getting info about a non-existing submission lock returns None
        assert SubmissionGradingLock.get_submission_lock(self.test_submission_uuid_without_lock) is None

    def test_claim_submission_lock(self):
        # Can claim a lock on a submission without an existing lock
        assert SubmissionGradingLock.get_submission_lock(self.test_submission_uuid_without_lock) is None
        new_lock = SubmissionGradingLock.claim_submission_lock(
            self.test_submission_uuid_without_lock,
            self.test_user_id_1
        )

        assert new_lock is not None
        assert SubmissionGradingLock.get_submission_lock(self.test_submission_uuid_without_lock) == new_lock

    def test_claim_submission_lock_contested(self):
        # Trying to claim a lock when someone else has a lock raises a SubmissionLockContestedError
        assert SubmissionGradingLock.get_submission_lock(self.test_submission_uuid) == self.existing_submission_lock
        with self.assertRaises(SubmissionLockContestedError):
            SubmissionGradingLock.claim_submission_lock(self.test_submission_uuid, self.test_user_id_2)

    def test_clear_submission_lock(self):
        # clear_submission_lock removes the existing lock
        assert SubmissionGradingLock.get_submission_lock(self.test_submission_uuid) == self.existing_submission_lock
        SubmissionGradingLock.clear_submission_lock(self.test_submission_uuid, self.test_user_id_1)
        assert SubmissionGradingLock.get_submission_lock(self.test_submission_uuid) is None

    def test_clear_submission_lock_contested(self):
        # clear_submission_lock blocks you from clearing a lock owned by another user
        assert SubmissionGradingLock.get_submission_lock(self.test_submission_uuid) == self.existing_submission_lock
        with self.assertRaises(SubmissionLockContestedError):
            SubmissionGradingLock.clear_submission_lock(self.test_submission_uuid, self.test_user_id_2)
