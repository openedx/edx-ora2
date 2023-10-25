"""
Tests for Staff Grader mixin
"""
import copy
from datetime import timedelta
import json
from unittest.mock import Mock, patch
from uuid import uuid4

from freezegun import freeze_time
from openassessment.assessment.errors.staff import StaffAssessmentError

from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock
from openassessment.tests.factories import UserFactory
from openassessment.xblock.test.base import XBlockHandlerTestCase, scenario, STAFF_GOOD_ASSESSMENT


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

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_batch_delete_submission_locks_no_id(self, xblock):
        """ If, somehow, the runtime fails to give us a user ID, break """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=None)

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

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_batch_delete_submission_locks_no_param(self, xblock):
        """ Batch delete fails if submission_uuids not supplied """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)

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

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_batch_delete_submission_locks_empty(self, xblock):
        """ An empty list of submisison UUIDs is silly, but should pass """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)

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
    def test_batch_delete_submission_locks_bad_param(self, xblock):
        """ Batch delete fails if submission_uuids is not a list """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)

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

    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_batch_delete_submission_locks(self, xblock):
        """ Batch delete clears submission locks we own """
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)

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
    @patch('openassessment.staffgrader.staff_grader_mixin.do_staff_assessment')
    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_submit_staff_assessment(self, xblock, mock_do_assessment, _):
        """Simple connectivity and routing test for submit staff assessment"""
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)
        xblock.is_team_assignment = Mock(return_value=False)

        request_data = copy.deepcopy(STAFF_GOOD_ASSESSMENT)
        request_data['submission_uuid'] = self.test_submission_uuid
        response = self.request(xblock, 'submit_staff_assessment', json.dumps(request_data), response_format='json')

        mock_do_assessment.assert_called_once()
        assert len(mock_do_assessment.call_args.args) == 7
        assert mock_do_assessment.call_args.args[0:5] == (
            self.test_submission_uuid,
            request_data['options_selected'],
            request_data['criterion_feedback'],
            request_data['overall_feedback'],
            request_data['assess_type'],
        )
        assert not mock_do_assessment.call_args.kwargs

        self.assertDictEqual(response, {
            'success': True,
            'msg': ''
        })

    @patch('openassessment.staffgrader.staff_grader_mixin.get_team_submission')
    @patch('openassessment.staffgrader.staff_grader_mixin.do_team_staff_assessment')
    @scenario('data/team_submission.xml', user_id="staff")
    def test_submit_team_staff_assessment(self, xblock, mock_do_assessment, _):
        """Simple connectivity and routing test for submit team staff assessment"""
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)
        xblock.is_team_assignment = Mock(return_value=True)

        request_data = copy.deepcopy(STAFF_GOOD_ASSESSMENT)
        request_data['submission_uuid'] = self.test_team_submission_uuid
        response = self.request(xblock, 'submit_staff_assessment', json.dumps(request_data), response_format='json')

        mock_do_assessment.assert_called_once()
        assert len(mock_do_assessment.call_args.args) == 7
        assert mock_do_assessment.call_args.args[0:5] == (
            self.test_team_submission_uuid,
            request_data['options_selected'],
            request_data['criterion_feedback'],
            request_data['overall_feedback'],
            request_data['assess_type'],
        )
        assert mock_do_assessment.call_args.kwargs['team_submission_uuid'] == self.test_team_submission_uuid

        self.assertDictEqual(response, {
            'success': True,
            'msg': ''
        })

    @patch('openassessment.staffgrader.staff_grader_mixin.get_submission')
    @patch('openassessment.staffgrader.staff_grader_mixin.do_staff_assessment')
    @scenario('data/basic_scenario.xml', user_id="staff")
    def test_submit_staff_assessment__error(self, xblock, mock_do_assessment, _):
        """Error case for submit_staff_assessment"""
        xblock.xmodule_runtime = Mock(user_is_staff=True, anonymous_student_id=self.staff_user_id)
        xblock.is_team_assignment = Mock(return_value=False)
        mock_do_assessment.side_effect = StaffAssessmentError()

        request_data = copy.deepcopy(STAFF_GOOD_ASSESSMENT)
        request_data['submission_uuid'] = self.test_submission_uuid
        response = self.request(xblock, 'submit_staff_assessment', json.dumps(request_data), response_format='json')
        self.assertDictEqual(response, {
            'success': False,
            'msg': 'Your team assessment could not be submitted.'
        })
