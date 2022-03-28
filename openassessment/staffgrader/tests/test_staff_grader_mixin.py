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

    test_timestamp = "1969-07-20T22:56:00-04:00"

    test_course_id = "course_id"

    staff_user = None
    staff_user_id = 'staff'

    non_staff_user = None
    non_staff_user_id = 'not-staff'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Set up users that will be used (and unmodified) across tests
        cls.staff_user = UserFactory.create()
        cls.staff_user.is_staff = True
        cls.staff_user.save()

        cls.non_staff_user = UserFactory.create()
        cls.non_staff_user.is_staff = False
        cls.non_staff_user.save()

        # Authenticate users - Fun fact, that's a Django typo :shrug:
        cls.staff_user.is_athenticated = True
        cls.non_staff_user.is_athenticated = True

    def setUp(self):
        super().setUp()

        # Create a submission lock
        self.submission_lock = SubmissionGradingLock.objects.create(
            owner_id=self.staff_user_id,
            submission_uuid=self.test_submission_uuid,
        )

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_check_submission_lock_none(self, xblock):
        """ A check for submission lock where there is no lock should return empty dict """
        xblock.xmodule_runtime = Mock(user_is_staff=True)
        request_data = {'submission_uuid': self.test_submission_uuid_unlocked}
        response = self.request(xblock, 'check_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "lock_status": "unlocked",
        })

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_check_submission_lock(self, xblock):
        """ A check for submission lock returns the matching submission lock """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)
        request_data = {'submission_uuid': self.test_submission_uuid}
        response = self.request(xblock, 'check_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "submission_uuid": self.test_submission_uuid,
            "owner_id": self.staff_user_id,
            "created_at": self.test_timestamp,
            "lock_status": "in-progress",
        })

    @patch('openassessment.staffgrader.staff_grader_mixin.get_submission')
    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_claim_submission_lock(self, xblock, _):
        """ A submission lock can be claimed on a submission w/out an active lock """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)

        request_data = {'submission_uuid': self.test_submission_uuid_unlocked}
        response = self.request(xblock, 'claim_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "submission_uuid": self.test_submission_uuid_unlocked,
            "owner_id": self.staff_user_id,
            "created_at": self.test_timestamp,
            "lock_status": "in-progress",
        })

    @patch('openassessment.staffgrader.staff_grader_mixin.get_submission')
    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_reclaim_submission_lock(self, xblock, _):
        """ A lock owner can re-claim a submission lock, updating the timestamp """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)

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
    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_claim_submission_lock_contested(self, xblock, _):
        """ Trying to claim a lock on a submission with an active lock raises an error """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id='other-staff-user-id')

        request_data = {'submission_uuid': self.test_submission_uuid}
        response = self.request(xblock, 'claim_submission_lock', json.dumps(request_data), response_format='response')
        response_body = json.loads(response.body.decode('utf-8'))

        self.assertEqual(response.status_code, 403)
        self.assertDictEqual(response_body, {
            "error": "ERR_LOCK_CONTESTED"
        })

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_delete_submission_lock(self, xblock):
        """ The lock owner can clear a submission lock if it exists """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)

        request_data = {'submission_uuid': self.test_submission_uuid}
        response = self.request(xblock, 'delete_submission_lock', json.dumps(request_data), response_format='json')

        self.assertDictEqual(response, {
            "lock_status": "unlocked"
        })

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_delete_submission_lock_contested(self, xblock):
        """ Users cannot clear a lock owned by another user """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id='other-staff-user-id')

        request_data = {'submission_uuid': self.test_submission_uuid}
        response = self.request(xblock, 'delete_submission_lock', json.dumps(request_data), response_format='response')
        response_body = json.loads(response.body.decode('utf-8'))

        self.assertEqual(response.status_code, 403)
        self.assertDictEqual(response_body, {
            "error": "ERR_LOCK_CONTESTED"
        })

    @patch('openassessment.staffgrader.staff_grader_mixin.get_submission')
    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_submit_staff_assessment(self, xblock, _):
        """Simple connectivity and routing test for submit staff assessment"""
        xblock.xmodule_runtime = Mock(user_is_staff=True)
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
    @scenario('data/team_submission.xml', user_id="staff")
    def test_submit_team_staff_assessment(self, xblock, _):
        """Simple connectivity and routing test for submit team staff assessment"""
        xblock.xmodule_runtime = Mock(user_is_staff=True)
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
