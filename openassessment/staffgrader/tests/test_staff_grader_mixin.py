"""
Tests for Staff Grader mixin
"""
from datetime import timedelta
import json
from unittest.mock import Mock, patch
from uuid import uuid4

from freezegun import freeze_time

from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock
from openassessment.tests.factories import UserFactory
from openassessment.xblock.test.base import XBlockHandlerTestCase, scenario


@freeze_time("1969-07-20T22:56:00-04:00")
class TestStaffGraderMixin(XBlockHandlerTestCase):
    """ Tests for interacting with submission grading/locking """
    test_submission_uuid = str(uuid4())
    test_submission_uuid_unlocked = str(uuid4())
    test_team_submission_uuid = str(uuid4())
    test_other_submission_uuid = str(uuid4())

    test_timestamp = "1969-07-20T22:56:00-04:00"

    test_course_id = "course_id"

    staff_user = None
    staff_user_id = 'staff'

    other_staff_user = None
    other_staff_user_id = 'other-staff'

    non_staff_user = None
    non_staff_user_id = 'not-staff'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Set up users that will be used (and unmodified) across tests
        cls.staff_user = UserFactory.create()
        cls.staff_user.is_staff = True
        cls.staff_user.save()

        cls.other_staff_user = UserFactory.create()
        cls.other_staff_user.is_staff = True
        cls.other_staff_user.save()

        cls.non_staff_user = UserFactory.create()
        cls.non_staff_user.is_staff = False
        cls.non_staff_user.save()

        # Authenticate users - Fun fact, that's a Django typo :shrug:
        cls.staff_user.is_athenticated = True
        cls.other_staff_user.is_athenticated = True
        cls.non_staff_user.is_athenticated = True

    def setUp(self):
        super().setUp()

        # Create a submission lock
        self.submission_lock = SubmissionGradingLock.objects.create(
            owner_id=self.staff_user_id,
            submission_uuid=self.test_submission_uuid,
        )

        # Create a submission lock owned by another user
        self.other_submission_lock = SubmissionGradingLock.objects.create(
            owner_id=self.other_staff_user_id,
            submission_uuid=self.test_other_submission_uuid,
        )

    @scenario('data/basic_scenario.xml', user_id="staff", is_staff=True)
    def test_check_submission_lock_none(self, xblock):
        """ A check for submission lock where there is no lock should return empty dict """
        request_data = {'submission_uuid': self.test_submission_uuid_unlocked}
        response = self.request(xblock, 'check_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "lock_status": "unlocked",
        })

    @scenario('data/basic_scenario.xml', user_id="staff", is_staff=True)
    def test_check_submission_lock(self, xblock):
        """ A check for submission lock returns the matching submission lock """
        request_data = {'submission_uuid': self.test_submission_uuid}
        response = self.request(xblock, 'check_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "submission_uuid": self.test_submission_uuid,
            "owner_id": self.staff_user_id,
            "created_at": self.test_timestamp,
            "lock_status": "in-progress",
        })

    @patch('openassessment.staffgrader.staff_grader_mixin.get_submission')
    @scenario('data/basic_scenario.xml', user_id="staff", is_staff=True)
    def test_claim_submission_lock(self, xblock, _):
        """ A submission lock can be claimed on a submission w/out an active lock """
        request_data = {'submission_uuid': self.test_submission_uuid_unlocked}
        response = self.request(xblock, 'claim_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "submission_uuid": self.test_submission_uuid_unlocked,
            "owner_id": self.staff_user_id,
            "created_at": self.test_timestamp,
            "lock_status": "in-progress",
        })

    @patch('openassessment.staffgrader.staff_grader_mixin.get_submission')
    @scenario('data/basic_scenario.xml', user_id="staff", is_staff=True)
    def test_reclaim_submission_lock(self, xblock, _):
        """ A lock owner can re-claim a submission lock, updating the timestamp """
        # Modify the original timestamp for testing
        lock = SubmissionGradingLock.objects.get(submission_uuid=self.test_submission_uuid)
        lock.created_at = lock.created_at - timedelta(hours=2)
        lock.save()

        request_data = {'submission_uuid': self.test_submission_uuid}
        response = self.request(xblock, 'claim_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "submission_uuid": self.test_submission_uuid,
            "owner_id": self.staff_user_id,
            "created_at": self.test_timestamp,
            "lock_status": "in-progress",
        })

    @patch('openassessment.staffgrader.staff_grader_mixin.get_submission')
    @scenario('data/basic_scenario.xml', user_id="other-staff-user-id", is_staff=True)
    def test_claim_submission_lock_contested(self, xblock, _):
        """ Trying to claim a lock on a submission with an active lock raises an error """
        request_data = {'submission_uuid': self.test_submission_uuid}
        response = self.request(xblock, 'claim_submission_lock', json.dumps(request_data), response_format='response')
        response_body = json.loads(response.body.decode('utf-8'))

        self.assertEqual(response.status_code, 403)
        self.assertDictEqual(response_body, {
            "error": "ERR_LOCK_CONTESTED"
        })

    @scenario('data/basic_scenario.xml', user_id="staff", is_staff=True)
    def test_delete_submission_lock(self, xblock):
        """ The lock owner can clear a submission lock if it exists """
        request_data = {'submission_uuid': self.test_submission_uuid}
        response = self.request(xblock, 'delete_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "lock_status": "unlocked"
        })

    @scenario('data/basic_scenario.xml', user_id="other-staff-user-id", is_staff=True)
    def test_delete_submission_lock_contested(self, xblock):
        """ Users cannot clear a lock owned by another user """
        request_data = {'submission_uuid': self.test_submission_uuid}
        response = self.request(xblock, 'delete_submission_lock', json.dumps(request_data), response_format='response')
        response_body = json.loads(response.body.decode('utf-8'))

        self.assertEqual(response.status_code, 403)
        self.assertDictEqual(response_body, {
            "error": "ERR_LOCK_CONTESTED"
        })

    @scenario('data/basic_scenario.xml', user_id=None, is_staff=True)
    def test_batch_delete_submission_locks_no_id(self, xblock):
        """ If, somehow, the user service fails to give us a user ID, break """
        request_data = {'submission_uuids': ['foo']}
        response = self.request(
            xblock,
            'batch_delete_submission_lock',
            json.dumps(request_data),
            response_format='response',
        )
        response_body = json.loads(response.body.decode('utf-8'))

        self.assertEqual(response.status_code, 500)
        self.assertDictEqual(response_body, {
            "error": "Failed to get anonymous user ID",
        })

    @scenario('data/basic_scenario.xml', user_id="staff", is_staff=True)
    def test_batch_delete_submission_locks_no_param(self, xblock):
        """ Batch delete fails if submission_uuids not supplied """
        request_data = {}
        response = self.request(
            xblock,
            'batch_delete_submission_lock',
            json.dumps(request_data),
            response_format='response',
        )
        response_body = json.loads(response.body.decode('utf-8'))

        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response_body, {
            "error": "Body must contain a submission_uuids list"
        })

    @scenario('data/basic_scenario.xml', user_id="staff", is_staff=True)
    def test_batch_delete_submission_locks_empty(self, xblock):
        """ An empty list of submisison UUIDs is silly, but should pass """
        request_data = {'submission_uuids': []}
        response = self.request(
            xblock,
            'batch_delete_submission_lock',
            json.dumps(request_data),
            response_format='response',
        )
        response_body = json.loads(response.body.decode('utf-8'))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response_body)

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_batch_delete_submission_locks_bad_param(self, xblock, is_staff=True):
        """ Batch delete fails if submission_uuids is not a list """
        request_data = {'submission_uuids': 'foo'}
        response = self.request(
            xblock,
            'batch_delete_submission_lock',
            json.dumps(request_data),
            response_format='response',
        )
        response_body = json.loads(response.body.decode('utf-8'))

        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response_body, {
            "error": "Body must contain a submission_uuids list"
        })

    @scenario('data/basic_scenario.xml', user_id="staff", is_staff=True)
    def test_batch_delete_submission_locks(self, xblock):
        """ Batch delete clears submission locks we own """
        request_data = {'submission_uuids': [self.test_submission_uuid, self.test_other_submission_uuid]}
        response = self.request(
            xblock,
            'batch_delete_submission_lock',
            json.dumps(request_data),
            response_format='json',
        )

        # Response should be empty on success
        self.assertIsNone(response)

        # Assert our lock was cleared and other individual's lock was not
        assert not SubmissionGradingLock.objects.filter(
            submission_uuid=self.test_submission_uuid
        ).exists()
        assert SubmissionGradingLock.objects.filter(
            submission_uuid=self.test_other_submission_uuid
        ).exists()

    @patch('openassessment.staffgrader.staff_grader_mixin.get_submission')
    @scenario('data/basic_scenario.xml', user_id="staff", is_staff=True)
    def test_submit_staff_assessment(self, xblock, _):
        """Simple connectivity and routing test for submit staff assessment"""
        xblock.is_team_assignment = Mock(return_value=False)
        xblock.do_staff_assessment = Mock(return_value=(True, ''))

        request_data = {'submission_uuid': self.test_submission_uuid, 'foo': 'bar'}
        response = self.request(xblock, 'submit_staff_assessment', json.dumps(request_data), response_format='json')

        xblock.do_staff_assessment.assert_called_once_with(request_data)
        self.assertDictEqual(response, {
            'success': True,
            'msg': ''
        })

    @patch('openassessment.staffgrader.staff_grader_mixin.get_team_submission')
    @scenario('data/team_submission.xml', user_id="staff", is_staff=True)
    def test_submit_team_staff_assessment(self, xblock, _):
        """Simple connectivity and routing test for submit team staff assessment"""
        xblock.is_team_assignment = Mock(return_value=True)
        xblock.do_team_staff_assessment = Mock(return_value=(True, ''))

        request_data = {'submission_uuid': self.test_team_submission_uuid, 'foo': 'bar'}
        response = self.request(xblock, 'submit_staff_assessment', json.dumps(request_data), response_format='json')

        xblock.do_team_staff_assessment.assert_called_once_with(
            request_data, team_submission_uuid=self.test_team_submission_uuid
        )
        self.assertDictEqual(response, {
            'success': True,
            'msg': ''
        })
