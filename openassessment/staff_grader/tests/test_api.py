import json

from unittest.mock import patch

from django.http import HttpRequest
from django.test import TestCase
from django.utils.timezone import now
from freezegun import freeze_time

from openassessment.staff_grader.api import locks_view
from openassessment.tests.factories import StaffWorkflowFactory, UserFactory


@freeze_time("1969-07-21 02:56:00", tz_offset=0)
class TestSubmissionLockView(TestCase):
    """ Tests for interacting with submission grading/locking """
    test_submission_uuid = "definitely_a_uuid"
    test_course_id = "definitely_a_course_id"
    test_workflow = None
    test_timestamp = "1969-07-21T02:56:00Z"

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

        self.test_workflow = StaffWorkflowFactory.create(
            submission_uuid=self.test_submission_uuid,
            course_id=self.test_course_id
        )

        return super().setUp()

    @patch("openassessment.staff_grader.api.has_access")
    def test_no_access(self, mock_access):
        # Given a user without valid access
        mock_access.return_value = False

        request = HttpRequest()
        request.method = "GET"
        request.user = self.non_staff_user
        course_id = self.test_course_id
        submission_uuid = self.test_submission_uuid

        # When I try to hit any endpoint
        result = locks_view(request, course_id, submission_uuid)

        # Then I get an empty HTTP Forbidden response
        assert result.status_code == 403

    @patch("openassessment.staff_grader.api.has_access")
    @patch("openassessment.staff_grader.api.get_anonymous_id")
    def test_not_found(self, mock_get_anon_id, mock_access):
        # Given a user with valid access
        mock_access.return_value = True
        mock_get_anon_id.return_value = self.staff_user_id

        # ... trying to access an invalid submission
        request = HttpRequest()
        request.method = "GET"
        request.user = self.staff_user
        course_id = self.test_course_id
        submission_uuid = 'not-a-real-submission'

        # When I hit any of the endpoints
        result = locks_view(request, course_id, submission_uuid)

        # Then I get a Not Found error
        assert result.status_code == 404

    @patch("openassessment.staff_grader.api.has_access")
    @patch("openassessment.staff_grader.api.get_anonymous_id")
    def test_get(self, mock_get_anon_id, mock_access):
        # Given a user with valid access
        mock_access.return_value = True
        mock_get_anon_id.return_value = self.staff_user_id

        # ... trying to access a valid submission
        request = HttpRequest()
        request.method = "GET"
        request.user = self.staff_user
        course_id = self.test_course_id
        submission_uuid = self.test_submission_uuid

        # When I GET submission lock info
        result = locks_view(request, course_id, submission_uuid)
        result_data = json.loads(result.getvalue())

        # Then I successfully get workflow data back
        assert result.status_code == 200
        assert result_data == {
            'submission_uuid': self.test_submission_uuid,
            'is_being_graded': False,
            'owner': '',
            'timestamp': None,
            'success': True
        }

    @patch("openassessment.staff_grader.api.has_access")
    @patch("openassessment.staff_grader.api.get_anonymous_id")
    def test_post(self, mock_get_anon_id, mock_access):
        # Given a user with valid access
        mock_access.return_value = True
        mock_get_anon_id.return_value = self.staff_user_id

        # ... trying to access a valid submission
        request = HttpRequest()
        request.method = "POST"
        request.user = self.staff_user
        course_id = self.test_course_id
        submission_uuid = self.test_submission_uuid

        # When I POST submission lock info
        result = locks_view(request, course_id, submission_uuid)
        result_data = json.loads(result.getvalue())

        # Then I successfully claim access to a submission and it begins grading
        assert result.status_code == 200
        assert result_data == {
            'submission_uuid': self.test_submission_uuid,
            'is_being_graded': True,
            'owner': self.staff_user_id,
            'timestamp': self.test_timestamp,
            'success': True
        }

    @patch("openassessment.staff_grader.api.has_access")
    @patch("openassessment.staff_grader.api.get_anonymous_id")
    def test_delete(self, mock_get_anon_id, mock_access):
        # Given a user with valid access
        mock_access.return_value = True
        mock_get_anon_id.return_value = self.staff_user_id

        # ... trying to access an in-grading-progress submisison
        self.test_workflow.grading_started_at = now()
        self.test_workflow.scorer_id = self.staff_user_id
        self.test_workflow.save()

        request = HttpRequest()
        request.method = "DELETE"
        request.user = self.staff_user
        course_id = self.test_course_id
        submission_uuid = self.test_submission_uuid

        # When I DELETE submission lock info
        result = locks_view(request, course_id, submission_uuid)
        result_data = json.loads(result.getvalue())

        # Then I release my claim to it, it goes back into ungraded
        assert result.status_code == 200
        assert result_data == {
            'submission_uuid': self.test_submission_uuid,
            'is_being_graded': False,
            'owner': '',
            'timestamp': None,
            'success': True
        }
