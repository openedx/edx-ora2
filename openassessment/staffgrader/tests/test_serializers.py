"""
Tests for serializers used in staff grading
"""
from datetime import datetime, timedelta, timezone, tzinfo
from uuid import uuid4
from freezegun import freeze_time

from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock
from openassessment.staffgrader.serializers.submission_lock import SubmissionLockSerializer
from openassessment.test_utils import CacheResetTest


TEST_TIME = datetime(2020, 8, 29, 2, 14, tzinfo=timezone(offset=timedelta(hours=-4)))


@freeze_time(TEST_TIME, tz_offset=-4)
class TestSubmissionLockSerializer(CacheResetTest):
    """ Tests for SubmissionLockSerializer """

    test_user_id_1 = 'Alice'
    test_user_id_2 = 'Bob'

    test_submission_id = str(uuid4())
    test_submission_lock = None

    timestamp = '2020-08-29T02:14:00-04:00'

    def setUp(self):
        super().setUp()

        # create a test lock for test_submission_id by test_user_id_1
        self.test_submission_lock = SubmissionGradingLock.claim_submission_lock(
            self.test_submission_id,
            self.test_user_id_1,
        )

    def test_empty(self):
        """ Serialization with an empty object returns lock_status of 'unlocked' """
        context = {'user_id': self.test_user_id_1, 'submission_uuid': self.test_submission_id}
        expected_output = {'lock_status': 'unlocked'}
        assert SubmissionLockSerializer({}, context=context).data == expected_output

    def test_serialize_inactive_lock(self):
        """ An inactive lock should serialize with lock_status of 'unlocked'. Other fields may or may not be passed """
        self.test_submission_lock.created_at = self.test_submission_lock.created_at - (
            SubmissionGradingLock.TIMEOUT + timedelta(hours=1)
        )
        self.test_submission_lock.save()

        context = {'user_id': self.test_user_id_1, 'submission_uuid': self.test_submission_id}
        output = SubmissionLockSerializer(self.test_submission_lock, context=context).data
        assert output['lock_status'] == 'unlocked'

    def test_serialize_in_progress_lock(self):
        """ Serializing a lock I own returns a lock_status of 'in-progress' """
        context = {'user_id': self.test_user_id_1, 'submission_uuid': self.test_submission_id}
        expected_output = {
            'submission_uuid': self.test_submission_id,
            'owner_id': self.test_user_id_1,
            'created_at': self.timestamp,
            'lock_status': 'in-progress'
        }

        assert SubmissionLockSerializer(self.test_submission_lock, context=context).data == expected_output


    def test_serialize_locked_lock(self):
        """ Serializing a lock owned by another user returns a lock_status of 'locked' """
        context = {'user_id': self.test_user_id_2, 'submission_uuid': self.test_submission_id}
        expected_output = {
            'submission_uuid': self.test_submission_id,
            'owner_id': self.test_user_id_1,
            'created_at': self.timestamp,
            'lock_status': 'locked'
        }

        assert SubmissionLockSerializer(self.test_submission_lock, context=context).data == expected_output
