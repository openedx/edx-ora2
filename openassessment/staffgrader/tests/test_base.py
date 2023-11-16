""" Base class for esg-related tests, with common setup and utility methods """
from contextlib import contextmanager
import json
from mock import patch, Mock
from submissions import api as sub_api

from openassessment.xblock.test.base import XBlockHandlerTestCase
from openassessment.workflow import api as workflow_api


class StaffGraderMixinTestBase(XBlockHandlerTestCase):
    """ Base class for esg-related tests, with common setup and utility methods """

    handler_name = None

    def setUp(self):
        super().setUp()
        # Lots of large dict comparisons in this file so display full diff
        self.maxDiff = None

    @contextmanager
    def _mock_get_download_url(self):
        with patch('openassessment.data.get_download_url') as mock_get_url:
            mock_get_url.side_effect = lambda file_key: f"www.file_url.com/{file_key}"
            yield mock_get_url

    @contextmanager
    def _mock_get_submission(self, **kwargs):
        """ Context manager to mock the fetching of a submission """
        with patch(
            'openassessment.staffgrader.staff_grader_mixin.get_submission',
            **kwargs
        ) as mock_get:
            yield mock_get

    def set_staff_user(self, xblock, staff_id, course_id=None, item_id=None):
        """
        Mock the runtime to say that the current user is course staff and is logged in as the given user.
        Additionally, mock the xblock's get_student_item_dict to return the value we want,
        rather than the values that are mocked upstream by "handle"
        """
        xblock.xmodule_runtime = Mock(user_is_staff=True)
        xblock.xmodule_runtime.anonymous_student_id = staff_id
        xblock.get_student_item_dict = Mock(
            return_value=self._student_item_dict(staff_id, course_id=course_id, item_id=item_id)
        )

    def request(self, xblock, payload):  # pylint: disable=arguments-differ
        """ Helper to candle calling the `get_submission_and_assessment_info` handler """
        assert self.handler_name is not None, "Subclass must specify handler_name"
        return super().request(
            xblock,
            self.handler_name,
            json.dumps(payload),
            response_format='response'
        )

    def json_parse_response(self, response):
        return json.loads(response.body.decode('utf-8'))

    def assert_status_code_and_parse_json(self, response, expected_code):
        assert expected_code == response.status_code
        return self.json_parse_response(response)

    def assert_response(self, response, expected_status, expected_body):
        assert expected_status == response.status_code
        response_body = self.json_parse_response(response)
        self.assertDictEqual(response_body, expected_body)

    @staticmethod
    def _student_item_dict(student_id, course_id=None, item_id=None):
        """ Generate a student_item_dict given a student_id """
        return {
            'course_id': course_id or 'TestCourseId',
            'item_id': item_id or 'TestItemId',
            'student_id': student_id,
            'item_type': 'openassessment'
        }

    @staticmethod
    def _create_student_and_submission(student, answer):
        """
        Helper method to create a student and submission for use in tests.
        """
        new_student_item = StaffGraderMixinTestBase._student_item_dict(student)
        submission = sub_api.create_submission(new_student_item, answer)
        workflow_api.create_workflow(submission["uuid"], ['staff'])
        return submission, new_student_item

    def submit_staff_assessment(
        self, xblock, submission_uuid, grader, option, option_2=None, criterion_feedback=None, overall_feedback=None
    ):
        """
        Helper method to submit a staff assessment
        Params:
            - xblock: (XBlock) xblock
            - student: (TestUser) the student_id whose submission we're assessing
            - grader: (TestUser) the course staff student_id who is submitting the assessment
            - option: (String) The name of the first option chosen
            - option_2: [Optional] (String) The name of the second option.
                        If not specified, use the first option again.

        Return:
            - None
        """
        assessment = {
            'options_selected': {'Criterion 1': option, 'Criterion 2': option_2 or option},
            'criterion_feedback': criterion_feedback or {},
            'overall_feedback': overall_feedback or '',
            'assess_type': 'full-grade',
            'submission_uuid': submission_uuid
        }
        self.set_staff_user(xblock, grader)
        resp = super().request(xblock, 'submit_staff_assessment', json.dumps(assessment), response_format='json')
        self.assertTrue(resp['success'])
