"""
Tests for Staff Grader mixin
"""
from datetime import datetime
import json
from unittest.mock import Mock
from freezegun import freeze_time

from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock
from openassessment.tests.factories import  UserFactory
from openassessment.xblock.test.base import XBlockHandlerTestCase, scenario


@freeze_time("1969-07-21 02:56:00", tz_offset=0)
class TestSubmissionLockMixin(XBlockHandlerTestCase):
    """ Tests for interacting with submission grading/locking """
    test_submission_uuid = "definitely_a_uuid"
    test_team_submission_uuid = "definitely_team_uuid"
    test_course_id = "definitely_a_course_id"
    test_workflow = None
    test_timestamp = "1969-07-21T02:56:00-04:00"

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
            submission_uuid=self.test_submission_uuid,
            owner_id=self.staff_user_id,
            created_at=datetime.now()
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
