""" Tests for the get_submission_and_assessment_info endpoint """
from contextlib import contextmanager
from uuid import uuid4

from mock import patch, Mock
from submissions import api as sub_api

from openassessment.xblock.test.base import scenario
from openassessment.data import VersionNotFoundException
from openassessment.staffgrader.tests.test_base import StaffGraderMixinTestBase


class GetSubmissionInfoTests(StaffGraderMixinTestBase):
    """ Tests for the get_submission_info handler endpoint """

    handler_name = 'get_submission_info'

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_no_submission_uuid(self, xblock):
        """ How does the endpoint behave when we don't give it a submission_uuid? """
        self.set_staff_user(xblock, 'Bob')
        response = self.request(xblock, {})
        self.assert_response(response, 400, {"error": "Body must contain a submission_uuid"})

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_no_access(self, xblock):
        """ How does the endpoint behave when the requester doesn't have proper permissions? """
        xblock.xmodule_runtime = Mock(user_is_staff=False)
        response = self.request(xblock, {'submission_uuid': 'meaningless-value'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('You do not have permission to access ORA staff grading.', response.body.decode('UTF-8'))

    @contextmanager
    def _mock_parse_submission_raw_answer(self, **kwargs):
        """ Context manager to mock the parsing of a raw answer into an nswer object """
        with patch(
            'openassessment.staffgrader.staff_grader_mixin.OraSubmissionAnswerFactory.parse_submission_raw_answer',
            **kwargs
        ) as mock_parse:
            yield mock_parse

    @contextmanager
    def _mock_get_download_urls(self, **kwargs):
        """ Helper method to mock the get_download_urls_from_submission method """
        with patch("openassessment.data.get_download_url", **kwargs) as mock_get_download_url:
            yield mock_get_download_url

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_get_submission_error(self, xblock):
        """ What happens when there's an exception when we attempt to look up the submission? """
        submission_uuid = str(uuid4())
        err_msg = str(Mock())

        self.set_staff_user(xblock, 'Bob')
        with self._mock_get_submission(side_effect=sub_api.SubmissionError(err_msg)):
            response = self.request(xblock, {'submission_uuid': submission_uuid})

        self.assert_response(response, 500, {"error": "Internal error getting submission info"})

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_answer_version_unknown(self, xblock):
        """ What happens when the raw answer we look up doesn't parse correctly? """
        submission_uuid = str(uuid4())
        mock_submission = Mock()
        mock_exception = VersionNotFoundException("No version found!!!!11")
        self.set_staff_user(xblock, 'Bob')
        with self._mock_get_submission(return_value=mock_submission):
            with self._mock_parse_submission_raw_answer(side_effect=mock_exception):
                response = self.request(xblock, {'submission_uuid': submission_uuid})

        self.assertEqual(response.status_code, 500)
        self.assertIn(str(mock_exception), response.body.decode('UTF-8'))

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_get_submission_info(self, xblock):
        """ Unit test for normal behavior of get_submission_info """
        text_responses = [
            "This is my answer for <b>Prompt One</b>.",
            "This is my answer for <i>Prompt Two</i>",
            "This is my response for <a href='www.edx.org'>Prompt Three</a>"
        ]
        file_uploads = [
            {
                "url": 'A', "description": 'B', "name": 'C', "size": 100
            },
            {
                "url": '1', "description": '2', "name": '3', "size": 300
            },
        ]
        file_responses = [
            {
                "download_url": 'A', "description": 'B', "name": 'C', "size": 100
            },
            {
                "download_url": '1', "description": '2', "name": '3', "size": 300
            },
        ]

        submission_uuid = str(uuid4())
        mock_submission = Mock()
        mock_answer = Mock()
        mock_answer.get_text_responses.return_value = text_responses
        mock_answer.get_file_uploads.return_value = file_uploads
        self.set_staff_user(xblock, 'Bob')
        with self._mock_get_submission(return_value=mock_submission):
            with self._mock_parse_submission_raw_answer(return_value=mock_answer):
                with self._mock_get_download_urls():
                    response = self.request(xblock, {'submission_uuid': submission_uuid})

        self.assert_response(
            response,
            200,
            {
                'text': text_responses,
                'files': file_responses
            }
        )

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_get_submission_info__integration(self, xblock):
        """ Test of full behavior of get_submission_info """
        student_id = 'test-student-id-1010101'
        test_answer = {
            'parts': [
                {'text': "This is my answer for <b>Prompt One</b>."},
                {'text': "This is my answer for <i>Prompt Two</i>"},
                {'text': "This is my response for <a href='www.edx.org'>Prompt Three</a>"},
            ],
            'file_keys': ['key-1', 'key-2', 'key-3'],
            'files_descriptions': ['description-1', 'description-2', 'description-3'],
            'files_names': ['filename-1', 'filename-2', 'filename-3'],
            'files_sizes': [200, 1500, 3000],
        }
        submission, _ = self._create_student_and_submission(student_id, test_answer)

        self.set_staff_user(xblock, 'Bob')
        with self._mock_get_download_url():
            response = self.request(xblock, {'submission_uuid': submission['uuid']})

        expected_submission_info = {
            'text': [
                "This is my answer for <b>Prompt One</b>.",
                "This is my answer for <i>Prompt Two</i>",
                "This is my response for <a href='www.edx.org'>Prompt Three</a>"
            ],
            'files': [
                {
                    'name': 'filename-1',
                    'description': 'description-1',
                    'download_url': 'www.file_url.com/key-1',
                    'size': 200,
                },
                {
                    'name': 'filename-2',
                    'description': 'description-2',
                    'download_url': 'www.file_url.com/key-2',
                    'size': 1500,
                },
                {
                    'name': 'filename-3',
                    'description': 'description-3',
                    'download_url': 'www.file_url.com/key-3',
                    'size': 3000,
                },
            ]
        }

        self.assert_response(response, 200, expected_submission_info)
