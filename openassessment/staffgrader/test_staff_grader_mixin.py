"""
Tests for Staff Grader mixin
"""
from datetime import timedelta
import json
from unittest.mock import Mock

from django.utils.timezone import now
from freezegun import freeze_time

from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock
from openassessment.tests.factories import UserFactory
from openassessment.xblock.test.base import XBlockHandlerTestCase, scenario


@freeze_time("1969-07-20T22:56:00-04:00")
class TestSubmissionLockMixin(XBlockHandlerTestCase):
    """ Tests for interacting with submission grading/locking """
    test_submission_uuid = "locked_submission_uuid"
    test_submission_uuid_unlocked = "unlocked_submission_uuid"

    test_timestamp = "1969-07-20T22:56:00-04:00"

    test_course_id = "course_id"

    staff_user = None
    staff_user_id = 'staff'

    non_staff_user = None
    non_staff_user_id = 'not-staff'

    def setUp(self):
        self.staff_user = UserFactory.create()
        self.staff_user.is_staff = True
        self.staff_user.save()

        self.non_staff_user = UserFactory.create()
        self.non_staff_user.is_staff = False
        self.non_staff_user.save()

        # Authenticate users - Fun fact, that's a Django typo :shrug:
        self.staff_user.is_athenticated = True
        self.non_staff_user.is_athenticated = True

        # Create a submission lock
        self.submission_lock = SubmissionGradingLock.objects.create(
            owner_id=self.staff_user_id,
            submission_uuid=self.test_submission_uuid,
        )

        return super().setUp()

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_check_submission_lock_none(self, xblock):
        """ A check for submission lock where there is no lock should return empty dict """
        xblock.xmodule_runtime = Mock(user_is_staff=True)
        request_data = {'submission_id': 'submission-without-lock'}
        response = self.request(xblock, 'check_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {})

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_check_submission_lock(self, xblock):
        """ A check for submission lock returns the matching submission lock """
        xblock.xmodule_runtime = Mock(user_is_staff=True)
        request_data = {'submission_id': self.test_submission_uuid}
        response = self.request(xblock, 'check_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "submission_uuid": self.test_submission_uuid,
            "owner_id": self.staff_user_id,
            "created_at": self.test_timestamp,
        })

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_claim_submission_lock(self, xblock):
        """ A submission lock can be claimed on a submission w/out an active lock """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)

        request_data = {'submission_id': self.test_submission_uuid_unlocked}
        response = self.request(xblock, 'claim_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "submission_uuid": self.test_submission_uuid_unlocked,
            "owner_id": self.staff_user_id,
            "created_at": self.test_timestamp,
        })

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_reclaim_submission_lock(self, xblock):
        """ A lock owner can re-claim a submission lock, updating the timestamp """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)

        # Modify the original timestamp for testing
        lock = SubmissionGradingLock.objects.get(submission_uuid=self.test_submission_uuid)
        lock.created_at = lock.created_at - timedelta(hours=2)
        lock.save()

        request_data = {'submission_id': self.test_submission_uuid}
        response = self.request(xblock, 'claim_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "submission_uuid": self.test_submission_uuid,
            "owner_id": self.staff_user_id,
            "created_at": self.test_timestamp,
        })

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_claim_submission_lock_contested(self, xblock):
        """ Trying to claim a lock on a submission with an active lock raises an error """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id='other-staff-user-id')

        request_data = {'submission_id': self.test_submission_uuid}
        response = self.request(xblock, 'claim_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "error": "Submission already locked"
        })

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_delete_submission_lock(self, xblock):
        """ The lock owner can clear a submission lock if it exists """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)

        request_data = {'submission_id': self.test_submission_uuid}
        response = self.request(xblock, 'delete_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {})

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_delete_submission_lock_contested(self, xblock):
        """ Users cannot clear a lock owned by another user """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id='other-staff-user-id')

        request_data = {'submission_id': self.test_submission_uuid}
        response = self.request(xblock, 'delete_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "error": "Unable to clear submission lock"
        })
