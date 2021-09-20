from datetime import datetime
import json

from unittest.mock import patch

from django.http import HttpRequest
from django.test import TestCase
from freezegun import freeze_time

from openassessment.staffgrader.staff_grader_mixin import StaffGraderMixin
from openassessment.tests.factories import  UserFactory


@freeze_time("1969-07-21 02:56:00", tz_offset=0)
class TestSubmissionLockMixin(TestCase):
    """ Tests for interacting with submission grading/locking """
    test_submission_uuid = "definitely_a_uuid"
    test_team_submission_uuid = "definitely_team_uuid"
    test_course_id = "definitely_a_course_id"
    test_workflow = None
    test_timestamp = "1969-07-20T22:56:00-04:00"

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

        return super().setUp()

    # @patch("openassessment.staff_grader.api.has_access")
    # def test_no_access(self, mock_access):
    #     # Given a user without valid access
    #     mock_access.return_value = False

    #     request = HttpRequest()
    #     request.method = "GET"
    #     request.GET = {'submissionid': self.test_submission_uuid}
    #     request.user = self.non_staff_user

    #     # When I try to hit any endpoint
    #     result = locks_view(request)

    #     # Then I get an empty HTTP Forbidden response
    #     assert result.status_code == 403

    # @patch("openassessment.staff_grader.api.has_access")
    # @patch("openassessment.staff_grader.api.get_anonymous_id")
    # def test_not_found(self, mock_get_anon_id, mock_access):
    #     # Given a user with valid access
    #     mock_access.return_value = True
    #     mock_get_anon_id.return_value = self.staff_user_id

    #     # ... trying to access an invalid submission
    #     request = HttpRequest()
    #     request.method = "GET"
    #     request.user = self.staff_user
    #     request.GET = {'submissionid': 'not-a-real-submission'}

    #     # When I hit any of the endpoints
    #     result = locks_view(request)

    #     # Then I get a Not Found error
    #     assert result.status_code == 404

    def test_missing_params(self):
        # Given a badly formed request (missing submission/team submission IDs)
        request = HttpRequest()
        request.method = "GET"
        request.user = self.staff_user
        request.GET = {}

        # When I hit any of the endpoints
        result = locks_view(request)

        # Then I get a bad request error
        assert result.status_code == 400

    # def test_double_params(self):
    #     # Given a badly formed request (both submission/team submission IDs)
    #     request = HttpRequest()
    #     request.method = "GET"
    #     request.user = self.staff_user
    #     request.GET = {
    #         'submissionid': self.test_submission_uuid,
    #         'teamsubmissionid': self.test_team_submission_uuid
    #     }

    #     # When I hit any of the endpoints
    #     result = locks_view(request)

    #     # Then I get a bad request error
    #     assert result.status_code == 400

    # @patch("openassessment.staff_grader.api.has_access")
    # @patch("openassessment.staff_grader.api.get_anonymous_id")
    # def test_get(self, mock_get_anon_id, mock_access):
    #     # Given a user with valid access
    #     mock_access.return_value = True
    #     mock_get_anon_id.return_value = self.staff_user_id

    #     # ... trying to access a valid submission
    #     request = HttpRequest()
    #     request.method = "GET"
    #     request.user = self.staff_user
    #     request.GET = {'submissionid': self.test_submission_uuid}

    #     # When I GET submission lock info
    #     result = locks_view(request)
    #     result_data = json.loads(result.getvalue())

    #     # Then I successfully get workflow data back
    #     assert result.status_code == 200
    #     assert result_data == {
    #         'submission_uuid': self.test_submission_uuid,
    #         'is_being_graded': False,
    #         'grading_started_at': None,
    #         'grading_completed_at': None,
    #         'scorer_id': '',
    #     }

    # @patch("openassessment.staff_grader.api.has_access")
    # @patch("openassessment.staff_grader.api.get_anonymous_id")
    # def test_get_team(self, mock_get_anon_id, mock_access):
    #     # Given a user with valid access
    #     mock_access.return_value = True
    #     mock_get_anon_id.return_value = self.staff_user_id

    #     # ... trying to access a valid team submission
    #     request = HttpRequest()
    #     request.method = "GET"
    #     request.user = self.staff_user
    #     request.GET = {'teamsubmissionid': self.test_team_submission_uuid}

    #     # When I GET submission lock info
    #     result = locks_view(request)
    #     result_data = json.loads(result.getvalue())

    #     # Then I successfully get workflow data back
    #     assert result.status_code == 200
    #     assert result_data == {
    #         'team_submission_uuid': self.test_team_submission_uuid,
    #         'is_being_graded': False,
    #         'grading_started_at': None,
    #         'grading_completed_at': None,
    #         'scorer_id': '',
    #     }

    # @patch("openassessment.staff_grader.api.has_access")
    # @patch("openassessment.staff_grader.api.get_anonymous_id")
    # def test_post(self, mock_get_anon_id, mock_access):
    #     # Given a user with valid access
    #     mock_access.return_value = True
    #     mock_get_anon_id.return_value = self.staff_user_id

    #     # ... trying to access a valid submission
    #     request = HttpRequest()
    #     request.method = "POST"
    #     request.user = self.staff_user
    #     request.GET = {'submissionid': self.test_submission_uuid}

    #     # When I POST submission lock info
    #     result = locks_view(request)
    #     result_data = json.loads(result.getvalue())

    #     # Then I successfully claim access to a submission and it begins grading
    #     assert result.status_code == 200
    #     assert result_data == {
    #         'submission_uuid': self.test_submission_uuid,
    #         'is_being_graded': True,
    #         'grading_started_at': self.test_timestamp,
    #         'grading_completed_at': None,
    #         'scorer_id': self.staff_user_id,
    #     }

    # @patch("openassessment.staff_grader.api.has_access")
    # @patch("openassessment.staff_grader.api.get_anonymous_id")
    # def test_delete(self, mock_get_anon_id, mock_access):
    #     # Given a user with valid access
    #     mock_access.return_value = True
    #     mock_get_anon_id.return_value = self.staff_user_id

    #     # ... trying to access an in-grading-progress submisison
    #     self.test_workflow.grading_started_at = datetime.now()
    #     self.test_workflow.scorer_id = self.staff_user_id
    #     self.test_workflow.save()

    #     request = HttpRequest()
    #     request.method = "DELETE"
    #     request.user = self.staff_user
    #     request.GET = {'submissionid': self.test_submission_uuid}

    #     # When I DELETE submission lock info
    #     result = locks_view(request)
    #     result_data = json.loads(result.getvalue())

    #     # Then I release my claim to it, it goes back into ungraded
    #     assert result.status_code == 200
    #     assert result_data == {
    #         'submission_uuid': self.test_submission_uuid,
    #         'is_being_graded': False,
    #         'grading_started_at': None,
    #         'grading_completed_at': None,
    #         'scorer_id': '',
    #     }


    # @scenario('data/grade_scenario.xml', user_id='Greggs')
    # def test_submit_feedback(self, xblock):
    #     # Create submissions and assessments
    #     self.create_submission_and_assessments(
    #         xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT
    #     )

    #     # Submit feedback on the assessments
    #     payload = json.dumps({
    #         'feedback_text': 'I disliked my assessment',
    #         'feedback_options': ['Option 1', 'Option 2'],
    #     })
    #     resp = self.request(xblock, 'submit_feedback', payload, response_format='json')
    #     self.assertTrue(resp['success'])

    #     # Verify that the feedback was created in the database
    #     feedback = peer_api.get_assessment_feedback(xblock.submission_uuid)
    #     self.assertIsNot(feedback, None)
    #     self.assertEqual(feedback['feedback_text'], 'I disliked my assessment')
    #     self.assertCountEqual(
    #         feedback['options'], [{'text': 'Option 1'}, {'text': 'Option 2'}]
    #     )
