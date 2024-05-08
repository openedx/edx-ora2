"""
Test submission to the OpenAssessment XBlock.
"""

import datetime as dt
import json
from unittest.mock import ANY, Mock, call, patch
from testfixtures import LogCapture
import pytz

import boto3
import ddt
from moto import mock_s3
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.test.utils import override_settings
from freezegun import freeze_time
from openedx_filters import PipelineStep
from openedx_filters.learning.filters import ORASubmissionViewRenderStarted

from xblock.exceptions import NoSuchServiceError
from submissions import api as sub_api
from submissions import team_api as team_sub_api
from submissions.api import SubmissionInternalError, SubmissionRequestError
from submissions.models import TeamSubmission
from openassessment.fileupload import api
from openassessment.workflow import (
    api as workflow_api,
    team_api as team_workflow_api
)
from openassessment.xblock.apis.submissions import submissions_actions
from openassessment.xblock.utils.data_conversion import create_submission_dict, prepare_submission_for_serialization
from openassessment.xblock.openassessmentblock import OpenAssessmentBlock
from openassessment.xblock.ui_mixins.legacy.views.submission import get_team_submission_context, render_submission
from openassessment.xblock.ui_mixins.legacy.handlers_mixin import LegacyHandlersMixin
from openassessment.xblock.workflow_mixin import WorkflowMixin
from openassessment.xblock.test.test_team import MockTeamsService, MOCK_TEAM_ID

from .base import SubmissionTestMixin, XBlockHandlerTestCase, scenario
from .test_staff_area import NullUserService, UserStateService

COURSE_ID = 'test_course'


def setup_mock_team(xblock):
    """ Enable teams and configure a mock team to be returned from the teams service

        Returns:
            the mock team for use in test validation
    """

    xblock.xmodule_runtime = Mock(
        user_is_staff=False,
        user_is_beta_tester=False,
        course_id=COURSE_ID,
        anonymous_student_id='r5'
    )

    mock_team = {
        'team_id': MOCK_TEAM_ID,
        'team_name': 'Red Squadron',
        'team_usernames': ['Red Leader', 'Red Two', 'Red Five'],
        'team_url': 'rebel_alliance.org'
    }

    xblock.teams_enabled = True
    xblock.team_submissions_enabled = True

    xblock.has_team = Mock(return_value=True)
    xblock.get_team_info = Mock(return_value=mock_team)
    xblock.get_anonymous_user_ids_for_team = Mock(return_value=['rl', 'r5', 'r2'])
    password = 'password'
    user = get_user_model().objects.create_user(username='Red Five', password=password)
    xblock.get_real_user = Mock(return_value=user)

    return mock_team


class SubmissionXBlockHandlerTestCase(XBlockHandlerTestCase):
    @staticmethod
    def setup_mock_team(xblock):
        return setup_mock_team(xblock)


class TestRenderInvalidTemplate(PipelineStep):
    """
    Utility class used when getting steps for pipeline.
    """

    def run_filter(self, context, template_name):  # pylint: disable=arguments-differ
        """
        Pipeline step that stops the course about render process.
        """
        raise ORASubmissionViewRenderStarted.RenderInvalidTemplate(
            "Invalid template.",
            context={"context": "current_context"},
            template_name="current/path/template.html",
        )


@ddt.ddt
class SubmissionTest(SubmissionXBlockHandlerTestCase, SubmissionTestMixin):
    """ Test Submissions Api for Open Assessments. """
    SUBMISSION = json.dumps({
        "submission": ["This is my answer to the first prompt!", "This is my answer to the second prompt!"]
    })

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_submit_submission(self, xblock):
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertTrue(resp[0])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_submit_answer_too_long(self, xblock):
        # Maximum answer length is 100K, once the answer has been JSON-encoded
        long_submission = json.dumps({
            "submission": ["This is my answer to the first prompt!" * 100000,
                           "This is my answer to the second prompt!"]
        })
        resp = self.request(xblock, 'submit', long_submission, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "EANSWERLENGTH")
        expected_message = (
            "Response exceeds maximum allowed size. (100 KB) "
            "Note: if you have a spellcheck or grammar check browser extension, "
            "try disabling, reloading, and reentering your response before submitting."
        )
        self.assertEqual(resp[2], expected_message)

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_submission_multisubmit_failure(self, xblock):
        # We don't care about return value of first one
        self.request(xblock, 'submit', self.SUBMISSION, response_format='json')

        # This one should fail because we're not allowed to submit multiple times
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "ENOMULTI")
        self.assertIsNotNone(resp[2])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    @patch.object(sub_api, 'create_submission')
    def test_submission_general_failure(self, xblock, mock_submit):
        mock_submit.side_effect = SubmissionInternalError("Cat on fire.")
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "EUNKNOWN")
        self.assertIsNotNone(resp[2])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    @patch.object(sub_api, 'create_submission')
    def test_submission_API_failure(self, xblock, mock_submit):  # pylint: disable=invalid-name
        mock_submit.side_effect = SubmissionRequestError(msg="Cat on fire.")
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "EBADFORM")
        self.assertIsNotNone(resp[2])

    # In Studio preview mode, the runtime sets the user ID to None
    @scenario('data/basic_scenario.xml', user_id=None)
    def test_cannot_submit_in_preview_mode(self, xblock):
        # The Studio runtime apparently provides an anonymous student ID,
        # even though we're running in Preview mode.  We should check the scope id
        # to determine whether we're in Preview mode or not.
        xblock.xmodule_runtime = Mock(
            course_id=COURSE_ID,
            anonymous_student_id='test_student'
        )

        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "ENOPREVIEW")
        self.assertIsNot(resp[2], None)

    @patch("openassessment.xblock.openassessmentblock.allow_resubmission")
    @patch("openassessment.xblock.openassessmentblock.import_student_module")
    @patch("openassessment.xblock.openassessmentblock.reset_student_attempts")
    @patch("openassessment.xblock.openassessmentblock.get_user_by_username_or_email")
    @scenario("data/basic_scenario.xml", user_id="Bob")
    def test_reset_submission(
        self, xblock, mock_user: Mock, mock_reset: Mock, mock_student_module: Mock, mock_allow_resubmission: Mock
    ):
        xblock.xmodule_runtime = Mock(course_id=COURSE_ID)
        mock_user.return_value = "test-user"
        mock_reset.return_value = True
        mock_allow_resubmission.return_value = True
        mock_student_module.return_value = "test-student-module"

        resp = self.request(xblock, "reset_submission", json.dumps({}), response_format="json")

        self.assertTrue(resp["success"])
        self.assertEqual(resp["msg"], "Submission reset successfully.")

    @patch("openassessment.xblock.openassessmentblock.allow_resubmission")
    @scenario("data/basic_scenario.xml", user_id="Bob")
    def test_reset_submission_not_allow_resubmission(self, xblock, mock_allow_resubmission: Mock):
        mock_allow_resubmission.return_value = False

        resp = self.request(xblock, "reset_submission", json.dumps({}), response_format="json")

        self.assertFalse(resp["success"])
        self.assertEqual(resp["msg"], "You can't reset your submission.")

    @patch("openassessment.xblock.openassessmentblock.allow_resubmission")
    @patch("openassessment.xblock.openassessmentblock.import_student_module")
    @patch("openassessment.xblock.openassessmentblock.get_user_by_username_or_email")
    @scenario("data/basic_scenario.xml", user_id="Bob")
    def test_reset_submission_user_not_found_error(
        self, xblock, mock_user: Mock, mock_student_module: Mock, mock_allow_resubmission: Mock
    ):
        mock_allow_resubmission.return_value = True
        mock_student_module.return_value = "test-student-module"
        mock_user.side_effect = get_user_model().DoesNotExist

        resp = self.request(xblock, "reset_submission", json.dumps({}), response_format="json")

        self.assertFalse(resp["success"])
        self.assertEqual(resp["msg"], "The user does not exist.")

    @patch("openassessment.xblock.openassessmentblock.allow_resubmission")
    @patch("openassessment.xblock.openassessmentblock.import_student_module")
    @patch("openassessment.xblock.openassessmentblock.reset_student_attempts")
    @patch("openassessment.xblock.openassessmentblock.get_user_by_username_or_email")
    @scenario("data/basic_scenario.xml", user_id="Bob")
    def test_reset_submission_submission_not_found_error(
        self, xblock, mock_user: Mock, mock_reset: Mock, mock_student_module: Mock, mock_allow_resubmission: Mock
    ):
        xblock.xmodule_runtime = Mock(course_id=COURSE_ID)
        mock_user.side_effect = "test-user"
        error_mock = Mock()
        error_mock.DoesNotExist = ObjectDoesNotExist
        mock_allow_resubmission.return_value = True
        mock_student_module.return_value = error_mock
        mock_reset.side_effect = ObjectDoesNotExist

        resp = self.request(xblock, "reset_submission", json.dumps({}), response_format="json")

        self.assertFalse(resp["success"])
        self.assertEqual(resp["msg"], "There is no submission to reset.")

    @scenario('data/over_grade_scenario.xml', user_id='Alice')
    def test_closed_submissions(self, xblock):
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        self.assertIn("Incomplete", resp.decode('utf-8'))

    @scenario('data/line_breaks.xml')
    def test_prompt_line_breaks(self, xblock):
        # Verify that prompts with multiple lines retain line breaks
        # (backward compatibility in case if prompt_type == 'text')
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        expected_prompt = "<p><br>Line 1</p><p>Line 2</p><p>Line 3<br></p>"
        self.assertIn(expected_prompt, resp.decode('utf-8'))

    @scenario('data/prompt_html.xml')
    def test_prompt_html_to_text(self, xblock):
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        expected_prompt = "<code><strong>Question 123</strong></code>"
        self.assertIn(expected_prompt, resp.decode('utf-8'))

        xblock.prompts_type = "text"
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        expected_prompt = "&lt;code&gt;&lt;strong&gt;Question 123&lt;/strong&gt;&lt;/code&gt;"
        self.assertIn(expected_prompt, resp.decode('utf-8'))

    @mock_s3
    @override_settings(
        AWS_ACCESS_KEY_ID='foobar',
        AWS_SECRET_ACCESS_KEY='bizbaz',
        FILE_UPLOAD_STORAGE_BUCKET_NAME="mybucket"
    )
    @scenario('data/file_upload_scenario.xml')
    def test_upload_url(self, xblock):
        """ Test generate correct upload URL """
        xblock.xmodule_runtime = Mock(
            course_id=COURSE_ID,
            anonymous_student_id='test_student',
        )
        resp = self.request(xblock, 'upload_url', json.dumps({"contentType": "image/jpeg",
                                                              "filename": "test.jpg"}), response_format='json')
        self.assertTrue(resp['success'])
        self.assertIn(
            '/submissions_attachments/test_student/test_course/' + xblock.scope_ids.usage_id,
            resp['url']
        )

    @mock_s3
    @override_settings(
        AWS_ACCESS_KEY_ID='foobar',
        AWS_SECRET_ACCESS_KEY='bizbaz',
        FILE_UPLOAD_STORAGE_BUCKET_NAME="mybucket"
    )
    @scenario('data/single_file_upload_scenario.xml')
    @patch('openassessment.xblock.apis.submissions.file_api.file_upload_api.get_download_url')
    def test_upload_url_single_file(self, xblock, mock_download_url):
        """ Test generate correct upload URL """
        xblock.xmodule_runtime = Mock(
            course_id='test_course',
            anonymous_student_id='test_student',
        )

        # Simulate a file already uploaded
        mock_download_url.return_value = "https://example.com/url"
        resp = self.request(xblock, 'upload_url', json.dumps({"contentType": "image/jpeg",
                                                              "filename": "test.jpg"}), response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn('Only a single file upload is allowed', resp['msg'])

        # Now test that we can upload a file if no existing upload.
        mock_download_url.return_value = None
        resp = self.request(xblock, 'upload_url', json.dumps({"contentType": "image/jpeg",
                                                              "filename": "test.jpg"}), response_format='json')
        self.assertTrue(resp['success'])
        self.assertIn(
            '/submissions_attachments/test_student/test_course/' + xblock.scope_ids.usage_id,
            resp['url']
        )

    @freeze_time('2023-10-17 12:00:01')
    @mock_s3
    @override_settings(
        AWS_ACCESS_KEY_ID='foobar',
        AWS_SECRET_ACCESS_KEY='bizbaz',
        FILE_UPLOAD_STORAGE_BUCKET_NAME="mybucket"
    )
    @scenario('data/file_upload_scenario.xml')
    def test_download_url(self, xblock):
        """ Test generate correct download URL with existing file. should create a file and get the download URL """
        conn = boto3.client("s3")
        conn.create_bucket(Bucket="mybucket")
        key = "submissions_attachments/test_student/test_course/" + xblock.scope_ids.usage_id
        conn.put_object(
            Bucket="mybucket",
            Key=key,
            Body=b"How d'ya do?"
        )
        download_url = api.get_download_url("test_student/test_course/" + xblock.scope_ids.usage_id)

        xblock.xmodule_runtime = Mock(
            course_id=COURSE_ID,
            anonymous_student_id='test_student',
        )

        resp = self.request(xblock, 'download_url', json.dumps({}), response_format='json')

        self.assertTrue(resp['success'])
        self.assertEqual(str(download_url), str(resp['url']))

    def _get_student_item_key(self, num, usage_id):
        key = "submissions_attachments/test_student/test_course/" + usage_id
        if num > 0:
            key = key + "/" + str(num)
        return key

    def _create_uploaded_files(self, num_files, usage_key):
        conn = boto3.client("s3")
        conn.create_bucket(Bucket="mybucket")
        for file_num in range(num_files):
            key = self._get_student_item_key(file_num, usage_key)
            conn.put_object(
                Bucket="mybucket",
                Key=key,
                Body=b"How d'ya do?",
            )

    def _create_entry(self, description, name, size):
        return {
            'description': description,
            'fileName': name,
            'fileSize': size,
        }

    @mock_s3
    @override_settings(
        AWS_ACCESS_KEY_ID='foobar',
        AWS_SECRET_ACCESS_KEY='bizbaz',
        FILE_UPLOAD_STORAGE_BUCKET_NAME="mybucket"
    )
    @scenario('data/file_upload_scenario.xml', user_id='bob')
    def test_delete_and_submit(self, xblock):
        """
        Test that after deleting a file, the remaining files are correctly submitted.
        """
        self._create_uploaded_files(5, xblock.scope_ids.usage_id)
        xblock.xmodule_runtime = Mock(
            course_id=COURSE_ID,
            anonymous_student_id='test_student',
        )

        # Mock away any calls to the teams service
        xblock.submission_data.files.can_delete_file = Mock(return_value=True)
        xblock.has_team = Mock(return_value=False)

        file_metadata = [
            self._create_entry('File Number ' + str(i), 'file_' + str(i), 1000) for i in range(5)
        ]
        file_index_to_remove = 2
        expected_file_metadata = list(file_metadata)
        expected_file_metadata.pop(file_index_to_remove)

        data = {'fileMetadata': file_metadata, 'itsamee': 'magrio'}
        resp = self.request(
            xblock,
            'save_files_descriptions',
            json.dumps(data),
            response_format='json'
        )
        self.assertTrue(resp['success'])

        resp = self.request(
            xblock,
            'remove_uploaded_file',
            json.dumps({'filenum': file_index_to_remove}),
            response_format='json'
        )
        self.assertTrue(resp['success'])

        student_item_key = api.get_student_file_key(
            xblock.get_student_item_dict(),
            index=file_index_to_remove
        )
        self.assert_event_published(
            xblock,
            'openassessmentblock.remove_uploaded_file',
            {
                "student_item_key": student_item_key
            }
        )

        with patch('submissions.api.create_submission') as mocked_submit:
            with patch.object(WorkflowMixin, 'create_workflow'):
                with patch.object(LegacyHandlersMixin, 'send_ora_submission_created_event') as mock_send_event:
                    mocked_submit.return_value = {
                        "uuid": '1111',
                        "attempt_number": 1,
                        "created_at": dt.datetime.now(),
                        "submitted_at": dt.datetime.now(),
                        "answer": {},
                    }
                    resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
                    mock_send_event.assert_called_once()
                    mocked_submit.assert_called_once()
                    student_sub_dict = mocked_submit.call_args[0][1]
                    self.assertEqual(
                        student_sub_dict['files_descriptions'],
                        [meta['description'] for meta in expected_file_metadata]
                    )
                    self.assertEqual(
                        student_sub_dict['files_names'],
                        [meta['fileName'] for meta in expected_file_metadata]
                    )
                    self.assertEqual(
                        student_sub_dict['files_sizes'],
                        [meta['fileSize'] for meta in expected_file_metadata]
                    )

    @mock_s3
    @override_settings(
        AWS_ACCESS_KEY_ID='foobar',
        AWS_SECRET_ACCESS_KEY='bizbaz',
        FILE_UPLOAD_STORAGE_BUCKET_NAME="mybucket"
    )
    @scenario('data/file_upload_scenario.xml')
    def test_download_url_non_existing_file(self, xblock):
        """ For non-existing file, a valid url will be returned, but it will 404 when followed. """
        resp = self.request(xblock, 'download_url', json.dumps({}), response_format='json')

        self.assertTrue(resp['success'])
        self.assertEqual('', resp['url'])

    @mock_s3
    @override_settings(
        AWS_ACCESS_KEY_ID='foobar',
        AWS_SECRET_ACCESS_KEY='bizbaz',
        FILE_UPLOAD_STORAGE_BUCKET_NAME="mybucket"
    )
    @scenario('data/custom_file_upload.xml')
    def test_upload_files_with_uppercase_ext(self, xblock):
        """
        Tests that files with upper case extention uploaded successfully
        """
        xblock.xmodule_runtime = Mock(
            course_id=COURSE_ID,
            anonymous_student_id='test_student',
        )
        resp = self.request(xblock, 'upload_url', json.dumps({'contentType': 'filename',
                                                              'filename': 'test.PDF'}), response_format='json')
        self.assertTrue(resp['success'])
        self.assertIn(
            '/submissions_attachments/test_student/test_course/' + xblock.scope_ids.usage_id,
            resp['url']
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_descriptionless_files(self, xblock):
        """
        Tests the old corner-case of a user being able to save files
        without descriptions.
        """
        with patch('openassessment.fileupload.api.get_download_url') as mock_download_url:
            # Pretend there are two uploaded files for this XBlock.
            mock_download_url.side_effect = [
                Mock(),
                Mock(),
                None,
            ]

            student_item_dict = xblock.get_student_item_dict()
            key_1 = api.get_student_file_key(student_item_dict, index=0)
            key_2 = api.get_student_file_key(student_item_dict, index=1)

            actual_keys = [upload.key for upload in xblock.file_manager.get_uploads()]
            self.assertEqual([key_1, key_2], actual_keys)

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_get_student_username(self, xblock):
        mock_user = Mock(
            username='UserName1'
        )
        xblock.xmodule_runtime = Mock(
            course_id=COURSE_ID,
            anonymous_student_id='test_student',
            get_real_user=lambda _: mock_user
        )
        resp = self.request(xblock, 'get_student_username', json.dumps({}))
        resp = json.loads(resp.decode('utf-8'))
        self.assertEqual(resp['username'], 'UserName1')

    @scenario('data/basic_scenario.xml', user_id='Red Five')
    def test_team_submission(self, xblock):
        """ If teams are enabled, a submission by any member should submit for each member of the team """

        # when the learner submits an open assessment response
        response = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')

        self.assertTrue(response[0])

    @scenario('data/basic_scenario.xml', user_id='Red Five')
    @patch.object(sub_api, 'create_submission')
    def test_team_submission_partial_failure(self, xblock, mock_submit):
        """ If a team submission encounters an issue with one of the submissions...
            easiest behavior is to return a failure, leaving the result a partial success
        """

        # given a learner is on a team
        self.setup_mock_team(xblock)

        xblock.get_workflow_info = Mock(return_value=None)

        # ... but there's an issue when submitting
        mock_submit.side_effect = SubmissionRequestError(msg="I can't shake him!")

        # when the learner submits an open assessment response
        response = self.request(
            xblock, 'submit', self.SUBMISSION, response_format='json')

        # then the submission returns a failure
        self.assertFalse(response[0])

    @scenario('data/basic_scenario.xml', user_id='Red Five')
    def test_team_file_submission(self, xblock):
        """ If teams are enabled, a submission by any member should submit for each member of the team """

        # given a learner is on a team and file uploads are enabled
        mock_team = self.setup_mock_team(xblock)
        xblock.runtime._services['teams'] = MockTeamsService(True)  # pylint: disable=protected-access
        xblock.file_upload_type = 'pdf-and-image'

        xblock.file_manager.get_uploads = Mock(side_effect=lambda team_id: [
            api.FileUpload(
                description='file-1',
                name='file-1.pdf',
                size=100,
                student_id='Lucy',
                course_id='edX/Enchantment_101/April_1',
                item_id='item-a',
                descriptionless=False,
            ),
        ])

        xblock.file_manager.get_team_uploads = Mock(side_effect=lambda team_id: [
            api.FileUpload(
                description='file-5',
                name='file-5.pdf',
                size=500,
                student_id='Bob',
                course_id='edX/Enchantment_101/April_1',
                item_id='item-a',
                descriptionless=False,
            ),
        ])

        xblock.get_workflow_info = Mock(return_value=None)

        # when the learner submits an open assessment response
        response = self.request(
            xblock, 'submit', self.SUBMISSION, response_format='json'
        )

        # then the submission is successful for all members of a team
        self.assertEqual(len(mock_team['team_usernames']), len(response))

        self.assertTrue(response[0])
        self.assertEqual(1, response[2])

        all_submissions = sub_api.get_all_submissions(
            course_id=xblock.course_id,
            item_id=str(xblock.scope_ids.usage_id),
            item_type='openassessment',
        )

        submission_user_ids = set()
        # assert that the content of each teammate's submission is identical.
        for submission in all_submissions:
            submission_user_ids.add(submission['student_id'])
            answer = submission['answer']
            self.assertEqual(['file-1', 'file-5'], answer['files_descriptions'])
            self.assertEqual(['file-1.pdf', 'file-5.pdf'], answer['files_names'])
            self.assertEqual([100, 500], answer['files_sizes'])
            self.assertEqual([
                {'text': 'This is my answer to the first prompt!'},
                {'text': 'This is my answer to the second prompt!'},
            ], answer['parts'])

        self.assertEqual(submission_user_ids, {'rl', 'r5', 'r2'})

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_get_download_urls_from_submission(self, xblock):
        mock_submission = {
            'answer': {
                'parts': [],
                'file_keys': ['key-1', 'key-2', 'key-3'],
                'files_descriptions': ['desc-1', None, 'desc-3'],
                'files_names': ['name-1', None, 'name-3'],
                'files_sizes': []
            },
        }
        with patch('openassessment.data.get_download_url') as mock_download_url:
            # Pretend there are two uploaded files for this XBlock.
            mock_download_url.side_effect = [
                'download-url-1',
                '',
                'download-url-3',
            ]

            actual_urls = xblock.get_download_urls_from_submission(mock_submission)
            # Even though one of the keys had no good download URL, we should
            # still return data for keys that came after it.
            expected_urls = [
                {
                    'download_url': 'download-url-1',
                    'description': 'desc-1',
                    'name': 'name-1',
                    'size': 0,
                    'show_delete_button': False
                },
                {
                    'download_url': 'download-url-3',
                    'description': 'desc-3',
                    'name': 'name-3',
                    'size': 0,
                    'show_delete_button': False
                },
            ]
            self.assertEqual(expected_urls, actual_urls)

            mock_download_url.assert_has_calls([
                call('key-1'), call('key-2'), call('key-3')
            ])

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_get_download_urls_from_submission_single_key(self, xblock):
        mock_submission = {
            'answer': {
                'parts': [],
                'file_key': 'key-1',
            },
        }
        with patch('openassessment.data.get_download_url') as mock_download_url:
            # Pretend there are two uploaded files for this XBlock.
            mock_download_url.side_effect = [
                'download-url-1',
            ]

            actual_urls = xblock.get_download_urls_from_submission(mock_submission)
            expected_urls = [
                {
                    'download_url': 'download-url-1',
                    'description': '',
                    'name': '',
                    'size': 0,
                    'show_delete_button': False
                }
            ]
            self.assertEqual(expected_urls, actual_urls)

            mock_download_url.assert_has_calls([call('key-1')])

    @scenario('data/submission_open.xml', user_id="Red Five")
    def test_get_team_context_exceptions(self, xblock):
        """
        Unit tests for error behavior in get_team_submission_context
        """
        xblock.location = 'some-uuid'
        self.setup_mock_team(xblock)

        # If there's no teams config, just return without adding anyting to the context, but log an error
        with LogCapture() as logger:
            xblock.get_team_info = Mock(side_effect=NoSuchServiceError)
            context = get_team_submission_context(xblock.config_data)
            self.assertEqual(context, {})
            logger.check_present(
                (
                    'openassessment.xblock.ui_mixins.legacy.views.submission',
                    'ERROR',
                    '{}: Teams service is unavailable'.format(
                        xblock.location,
                    )
                )
            )

        # If we can't resolve the anonymous_id to a real user, again just don't do anything but log
        with LogCapture() as logger:
            xblock.get_team_info = Mock(side_effect=ObjectDoesNotExist)
            context = get_team_submission_context(xblock.config_data)
            self.assertEqual(context, {})
            logger.check_present(
                (
                    'openassessment.xblock.ui_mixins.legacy.views.submission',
                    'ERROR',
                    '{}: User associated with anonymous_user_id {} can not be found.'.format(
                        xblock.location,
                        xblock.xmodule_runtime.anonymous_student_id
                    )
                )
            )

    @scenario('data/submission_open.xml', user_id="Red Five")
    @ddt.data(
        (['', ''], None, True),
        (['', ''], [], True),
        (['abc', ''], None, False),
        (['', 'abc'], [], False),
        (['', '', ''], ['file_1_key'], False),
    )
    @ddt.unpack
    def test_submission_is_empty(self, xblock, parts, file_keys, expect_is_empty):
        """
        Unit tests for submission_is_empty
        """
        submission_dict = {'parts': [{'text': part} for part in parts]}
        if file_keys is not None:
            submission_dict['file_keys'] = file_keys

        is_empty = xblock.submission_data.submission_is_empty(submission_dict)
        self.assertEqual(expect_is_empty, is_empty)

    @scenario('data/basic_scenario.xml', user_id='Red Five')
    @ddt.data(False, True)
    def test_empty_submission_error(self, xblock, team_assignment):
        """
        Test that if users try to create an empty submission, an error will be raised
        and no submission is created
        """
        xblock.file_upload_type = 'pdf-and-image'
        if team_assignment:
            self.setup_mock_team(xblock)
            xblock.runtime._services['teams'] = MockTeamsService(True)  # pylint: disable=protected-access

        empty_submission = json.dumps({"submission": ["", ""]})
        response = self.request(
            xblock, 'submit', empty_submission, response_format='json'
        )
        self.assertFalse(response[0])
        self.assertEqual(response[1], "EEMPTYSUB")
        self.assertIsNotNone(response[2])


class SubmissionRenderTest(SubmissionXBlockHandlerTestCase, SubmissionTestMixin):
    """
    Test rendering of the submission step.
    To cover all states in a maintainable way, we mostly check the
    template context/path without actually checking the rendered template
    (although we do verify that it renders without an exception).
    We then include one integration test that renders the template
    to verify that everything is hooked up correctly.
    """

    @scenario('data/submission_unavailable.xml', user_id="Bob")
    def test_unavailable(self, xblock):
        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response_unavailable.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'enable_delete_files': False,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': False,
                'prompts_type': 'text',
                'show_rubric_during_response': False,
                'submission_start': dt.datetime(4999, 4, 1).replace(tzinfo=pytz.utc),
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
            }
        )

    @scenario('data/submission_unavailable.xml', user_id="Bob")
    def test_unavailable_submitted(self, xblock):
        # If the instructor changes the start date after the problem
        # has opened, it's possible for a student to have made a submission
        # even though the problem is unavailable.
        # In this case, we should continue showing that the student completed
        # the submission.
        submission = self.create_test_submission(xblock)
        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response_submitted.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'enable_delete_files': False,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': False,
                'peer_incomplete': True,
                'prompts_type': 'text',
                'self_incomplete': True,
                'show_rubric_during_response': False,
                'student_submission': create_submission_dict(submission, xblock.prompts),
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_unanswered(self, xblock):
        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'date_config_type': 'manual',
                'enable_delete_files': True,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': False,
                'prompts_type': 'text',
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ("", "")
                    )
                }, xblock.prompts),
                'save_status': 'Response not started.',
                'show_rubric_during_response': False,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_timezone': None,
                'user_language': None,
            }
        )

    @scenario('data/submission_open.xml', user_id="Red Five")
    def test_team_open_unanswered(self, xblock):
        mock_team = SubmissionTest.setup_mock_team(xblock)

        # pylint: disable=protected-access
        xblock.runtime._services['user'] = NullUserService()
        xblock.runtime._services['user_state'] = UserStateService()
        xblock.runtime._services['teams'] = MockTeamsService(True)

        xblock.user_state_upload_data_enabled = Mock(return_value=True)
        xblock.is_team_assignment = Mock(return_value=True)
        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'date_config_type': 'manual',
                'enable_delete_files': True,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': True,
                'prompts_type': 'text',
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ("", "")
                    )
                }, xblock.prompts),
                'save_status': 'Response not started.',
                'show_rubric_during_response': False,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'team_id': mock_team['team_id'],
                'team_members_with_external_submissions': '',
                'team_name': mock_team['team_name'],
                'team_url': mock_team['team_url'],
                'team_usernames': mock_team['team_usernames'],
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
            }
        )

    @patch('openassessment.xblock.ui_mixins.legacy.views.submission.get_submission_path')
    @patch.object(OpenAssessmentBlock, "render_assessment")
    @patch.object(ORASubmissionViewRenderStarted, "run_filter")
    @scenario('data/submission_open.xml', user_id="Red Five")
    def test_render_submission_no_run_filter(
        self,
        xblock,
        mock_run_filter: Mock,
        mock_render_assessment: Mock,
        mock_get_submission_path: Mock
    ):
        """
        Test for `render_submission` when the `run_filter` method is not called.
        """
        mock_get_submission_path.return_value = "another/path/template.html"

        render_submission(xblock.config_data, xblock.submission_data)

        mock_run_filter.assert_not_called()
        mock_render_assessment.assert_called_once()

    @patch.object(OpenAssessmentBlock, "render_assessment")
    @patch.object(ORASubmissionViewRenderStarted, "run_filter")
    @scenario('data/submission_open.xml', user_id="Red Five")
    def test_render_submission_run_filter(
        self, xblock, mock_run_filter: Mock, mock_render_assessment: Mock
    ):
        """
        Test for `render_submission` when the `run_filter` method is called.
        """
        expected_context = {"context": "new_context"}
        expected_path = "new/path/template.html"
        mock_run_filter.return_value = (expected_context, expected_path)

        render_submission(xblock.config_data, xblock.submission_data)

        mock_run_filter.assert_called_once()
        mock_render_assessment.assert_called_once_with(expected_path, expected_context)

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            "org.openedx.learning.ora.submission_view.render.started.v1": {
                "fail_silently": False,
                "pipeline": [
                    "openassessment.xblock.test.test_submission.TestRenderInvalidTemplate"
                ]
            }
        }
    )
    @patch.object(OpenAssessmentBlock, "render_assessment")
    @scenario('data/submission_open.xml', user_id="Red Five")
    def test_render_submission_run_filter_exception(self, xblock, mock_render_assessment: Mock):
        """
        Test for `render_submission` when the `run_filter` method raises an exception.
        """
        expected_context = {"context": "current_context"}
        expected_path = "current/path/template.html"

        render_submission(xblock.config_data, xblock.submission_data)

        mock_render_assessment.assert_called_once_with(expected_path, expected_context)

    @patch('submissions.team_api.get_teammates_with_submissions_from_other_teams')
    @scenario('data/submission_open.xml', user_id="Red Five")
    def test_get_team_submission_context(
        self,
        xblock,
        mock_external_team_submissions,
    ):
        team_info = {
            'team_id': MOCK_TEAM_ID,
            'team_info_extra': 'more team info'
        }
        usage_id = xblock.scope_ids.usage_id
        student_item_dict = {
            'item_id': usage_id
        }
        student_ids = ['11111111111111', '222222222222222', '333333333333']
        student_usernames = ['User 1', 'User 2', 'User 3']
        external_submissions = [
            {
                'student_id': student_ids[0],
                'team_id': 'other team'
            },
            {
                'student_id': student_ids[1],
                'team_id': 'still another team',
            },
            {
                'student_id': student_ids[2],
                'team_id': 'final team',
            }
        ]

        mock_external_team_submissions.return_value = external_submissions

        xblock.get_team_info = Mock(return_value=team_info)
        xblock.xmodule_runtime = Mock(
            course_id=COURSE_ID,
            anonymous_student_id="Red Five",
            user_is_staff=False
        )
        xblock.get_student_item_dict = Mock(return_value=student_item_dict)
        xblock.get_username = Mock(
            side_effect=lambda student_id: student_usernames[student_ids.index(student_id)]
        )

        xblock.get_anonymous_user_ids_for_team = Mock(return_value=student_ids)
        expected_names = f"{student_usernames[0]}, {student_usernames[1]}, and {student_usernames[2]}"
        expected_context = {
            "team_members_with_external_submissions": expected_names,
            "team_id": MOCK_TEAM_ID,
            "team_info_extra": "more team info",
        }
        context = get_team_submission_context(xblock.config_data)
        mock_external_team_submissions.assert_called_with(
            COURSE_ID,
            usage_id,
            MOCK_TEAM_ID,
            student_ids
        )
        self.assertEqual(context, expected_context)

    @scenario('data/submission_open.xml', user_id="Red Five")
    def test_get_team_submission_context__no_team(self, xblock):
        team_info = None
        xblock.xmodule_runtime = Mock(
            user_is_staff=False
        )
        xblock.get_team_info = Mock(return_value=team_info)
        context = get_team_submission_context(xblock.config_data)
        self.assertEqual(context, {})

    @scenario('data/submission_open.xml', user_id="Red Five")
    def test_get_team_submission_context__staff_view(self, xblock):
        # In staff view, team info is available, but not submission info.
        # verify that the team info is loaded into context, and nothing else,
        # and that no exceptions are thrown
        team_info = {
            'team_id': MOCK_TEAM_ID,
            'team_info_extra': 'more team info'
        }
        xblock.xmodule_runtime = Mock(
            user_is_staff=True
        )
        xblock.get_team_info = Mock(return_value=team_info)
        context = get_team_submission_context(xblock.config_data)
        self.assertEqual(context, team_info)

    @scenario('data/submission_no_deadline.xml', user_id="Bob")
    def test_open_no_deadline(self, xblock):
        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'enable_delete_files': True,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': False,
                'prompts_type': 'text',
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ("", "")
                    )
                }, xblock.prompts),
                'save_status': 'Response not started.',
                'show_rubric_during_response': False,
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_timezone': None,
                'user_language': None,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_saved_response(self, xblock):
        file_uploads = [
            {'description': 'file-1', 'name': 'file-1.pdf', 'size': 200},
            {'description': 'file-2', 'name': 'file-2.pdf', 'size': 400},
        ]

        xblock.file_manager.append_uploads(*file_uploads)

        # Save a response
        payload = json.dumps({'submission': ('A man must have a code', 'A man must have an umbrella too.')})
        resp = self.request(xblock, 'save_submission', payload, response_format='json')
        self.assertTrue(resp['success'])
        del xblock.location  # self.request() inserts dummy location

        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'date_config_type': 'manual',
                'enable_delete_files': True,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': False,
                'prompts_type': 'text',
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ('A man must have a code', 'A man must have an umbrella too.')
                    )
                }, xblock.prompts),
                'save_status': 'Draft saved!',
                'show_rubric_during_response': False,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
            }
        )

        # pylint: disable=protected-access
        actual_file_uploads = [upload._to_dict() for upload in xblock.file_manager.get_uploads()]
        expected_file_uploads = [
            api.FileUpload(
                description='file-1',
                name='file-1.pdf',
                size=200,
                student_id='Bob',
                course_id='edX/Enchantment_101/April_1',
                item_id=ANY,
                descriptionless=False,
            )._to_dict(),
            api.FileUpload(
                description='file-2',
                name='file-2.pdf',
                size=400,
                student_id='Bob',
                course_id='edX/Enchantment_101/April_1',
                item_id=ANY,
                descriptionless=False,
            )._to_dict(),
        ]

        for expected, actual in zip(expected_file_uploads, actual_file_uploads):
            # We can't consistently determine the values of an XBlock's item_id
            expected.pop('item_id')
            actual.pop('item_id')

        self.assertEqual(expected_file_uploads, actual_file_uploads)

    @scenario('data/save_scenario.xml', user_id="Valchek")
    def test_open_saved_response_deleted_file_uploads(self, xblock):
        """
        Test that we generate the correct file indexes even when
        some of the saved files have been deleted
        """
        file_uploads = [
            {'description': 'file-1', 'name': 'file-1.pdf', 'size': 200},
            {'description': 'file-2', 'name': 'file-2.pdf', 'size': 400},
            {'description': 'file-3', 'name': 'file-3.pdf', 'size': 1600},
        ]

        xblock.file_manager.append_uploads(*file_uploads)

        xblock.xmodule_runtime = Mock(
            user_is_staff=False,
            user_is_beta_tester=False,
            course_id='test_course',
            anonymous_student_id='Pmn'
        )

        # delete file-2
        with patch('openassessment.fileupload.api.remove_file'):
            xblock.file_manager.delete_upload(1)

        payload = json.dumps({'submission': ('A man must have a code', 'A man must have an umbrella too.')})
        resp = self.request(xblock, 'save_submission', payload, response_format='json')
        self.assertTrue(resp['success'])

        expected_file_uploads = [
            api.FileUpload(
                description='file-1',
                name='file-1.pdf',
                size=200,
                student_id='Valchek',
                course_id='edX/Enchantment_101/April_1',
                item_id=ANY,
                descriptionless=False,
            ),
            api.FileUpload(
                description=None,
                name=None,
                size=0,
                student_id='Valchek',
                course_id='edX/Enchantment_101/April_1',
                item_id=ANY,
                descriptionless=False,
            ),
            api.FileUpload(
                description='file-3',
                name='file-3.pdf',
                size=1600,
                student_id='Valchek',
                course_id='edX/Enchantment_101/April_1',
                item_id=ANY,
                descriptionless=False,
            ),
        ]
        # pylint: disable=protected-access
        actual_file_upload_dicts = [
            upload._to_dict() for upload in xblock.file_manager.get_uploads(include_deleted=True)
        ]
        expected_file_upload_dicts = [upload._to_dict() for upload in expected_file_uploads]

        for expected, actual in zip(expected_file_upload_dicts, actual_file_upload_dicts):
            # We can't consistently determine the values of an XBlock's item_id
            expected.pop('item_id')
            actual.pop('item_id')

        self.assertEqual(expected_file_upload_dicts, actual_file_upload_dicts)

        # assert that there's an entry with the correct index in the rendered HTML
        # we should have an index for all files ever uploaded, even the deleted one
        resp = self.request(xblock, 'render_submission', json.dumps({})).decode('utf-8')

        self.assertIn('"submission__answer__file__block submission__answer__file__block__1"  deleted', resp)
        for index in range(len(file_uploads)):
            self.assertIn(
                f'"submission__answer__file__block submission__answer__file__block__{index}"',
                resp
            )

    @scenario('data/file_upload_scenario.xml', user_id="Bob")
    def test_open_saved_response_misaligned_file_data(self, xblock):
        """
        Test the case where the XBlock user state contains a different number of
        file descriptions from file sizes and names.  After rendering the block,
        the list of file names and sizes should be coerced to lists that are of the
        same length as the file descriptions.
        """
        xblock.saved_files_descriptions = json.dumps(["file-1", "file-2"])
        xblock.saved_files_names = json.dumps([])
        xblock.saved_files_sizes = json.dumps([200])

        xblock.file_upload_response = 'optional'

        xblock.get_team_info = Mock(return_value={})

        # Save a response
        payload = json.dumps({'submission': ('A man must have a code', 'A man must have an umbrella too.')})
        resp = self.request(xblock, 'save_submission', payload, response_format='json')
        self.assertTrue(resp['success'])
        del xblock.location  # self.request() inserts dummy location

        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'enable_delete_files': True,
                'file_upload_response': 'optional',
                'file_upload_type': 'pdf-and-image',
                'file_urls': [
                    {
                        'download_url': '',
                        'description': 'file-1',
                        'name': None,
                        'size': None,
                        'show_delete_button': True
                    },
                    {
                        'download_url': '',
                        'description': 'file-2',
                        'name': None,
                        'size': None,
                        'show_delete_button': True
                    }
                ],
                'has_real_user': False,
                'prompts_type': 'text',
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ('A man must have a code', 'A man must have an umbrella too.')
                    )
                }, xblock.prompts),
                'save_status': 'Draft saved!',
                'show_rubric_during_response': False,
                'team_file_urls': [],
                'text_response': None,
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
                'white_listed_file_types': ['.pdf', '.gif', '.jpg', '.jpeg', '.jfif', '.pjpeg', '.pjp', '.png']
            }
        )

        # pylint: disable=protected-access
        actual_file_uploads = [upload._to_dict() for upload in xblock.file_manager.get_uploads()]

        # When file names/sizes are of different cardinality of file descriptions,
        # they are coerced to lists of nulls of the same cardinality of the descriptions,
        # hence, name and size attributes below are null.
        expected_file_uploads = [
            api.FileUpload(
                description='file-1',
                name=None,
                size=None,
                student_id='Bob',
                course_id='edX/Enchantment_101/April_1',
                item_id=ANY,
                descriptionless=False,
            )._to_dict(),
            api.FileUpload(
                description='file-2',
                name=None,
                size=None,
                student_id='Bob',
                course_id='edX/Enchantment_101/April_1',
                item_id=ANY,
                descriptionless=False,
            )._to_dict(),
        ]
        for expected, actual in zip(expected_file_uploads, actual_file_uploads):
            # We can't consistently determine the values of an XBlock's item_id
            expected.pop('item_id')
            actual.pop('item_id')

        self.assertEqual(expected_file_uploads, actual_file_uploads)

    @patch('openassessment.fileupload.api.get_download_url')
    @scenario('data/save_scenario.xml', user_id="Valchek")
    def test_render_shared_files(self, xblock, mock_get_download_url):
        """
        Test that we render files owned by Valchek and
        their teammates when files are shared with a team.
        """
        xblock.file_manager.get_uploads = Mock(return_value=[
            api.FileUpload(
                description='file 1 description',
                name='file-1.pdf',
                size=200,
                student_id='Valchek',
                course_id='edX/Enchantment_101/April_1',
                item_id='item-a',
                descriptionless=False,
            ),
            api.FileUpload(  # just for fun, add a file that's been deleted
                description=None,
                name=None,
                size=0,
                student_id='Valchek',
                course_id='edX/Enchantment_101/April_1',
                item_id=ANY,
                descriptionless=False,
            ),
        ])

        xblock.file_manager.get_team_uploads = Mock(return_value=[
            api.FileUpload(
                description='file 5 description',
                name='file-5.pdf',
                size=500,
                student_id='Bob',
                course_id='edX/Enchantment_101/April_1',
                item_id='item-a',
                descriptionless=False,
            ),
        ])

        mock_get_download_url.side_effect = ['file-1-url', 'file-5-url']

        xblock.xmodule_runtime = Mock(
            user_is_staff=False,
            user_is_beta_tester=False,
            course_id='test_course',
            anonymous_student_id='Pmn'
        )

        # assert that there's an entry with the correct index in the rendered HTML
        # we should have an index for all files ever uploaded, even the deleted one
        resp = self.request(xblock, 'render_submission', json.dumps({})).decode('utf-8')

        expected_strings = [
            '"submission__answer__file__block submission__answer__file__block__0"',
            '"submission__answer__file__block submission__answer__file__block__1"  deleted',
            '"submission__answer__team__file__block submission__answer__team__file__block__0"',
            'file-1.pdf',
            'file-5.pdf',
            'file-1-url',
            'file-5-url',
            'file 1 description',
            'file 5 description',
        ]

        for expected_string in expected_strings:
            self.assertIn(expected_string, resp)

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_saved_response_old_format(self, xblock):
        # Save a response
        xblock.prompts = [{'description': 'One prompt.'}]
        xblock.saved_response = "An old format response."
        xblock.has_saved = True

        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'date_config_type': 'manual',
                'enable_delete_files': True,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': False,
                'prompts_type': 'text',
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ('An old format response.',)
                    )
                }, xblock.prompts),
                'save_status': 'Draft saved!',
                'show_rubric_during_response': False,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
            }
        )

    @scenario('data/team_submission.xml', user_id="Red Five")
    def test_team_open_submitted(self, xblock):
        """ When a submission is created for a team, we create identical submissions for each learner.
            Since we can't save submission info to other learners state, we need to query the database
            on page load to see if a submisison has been created by a team member.
        """
        SubmissionTest.setup_mock_team(xblock)
        student_item_dict = xblock.get_student_item_dict()
        submissions_actions.create_team_submission(
            student_item_dict,
            ('A man must have a code', 'A man must have an umbrella too.'),
            xblock.config_data,
            xblock.submission_data,
            xblock.workflow_data,
        )

        ts = TeamSubmission.objects.all()
        self.assertEqual(len(ts), 1)
        self.assertEqual(ts[0].submitted_by.username, 'Red Five')
        # TODO this work also depends on https://openedx.atlassian.net/browse/EDUCATOR-4986
        # Once that ticket is complete, reinstate original assert via path_and_context

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_submitted(self, xblock):
        submission = self.create_test_submission(xblock)
        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response_submitted.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'date_config_type': 'manual',
                'enable_delete_files': False,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': False,
                'peer_incomplete': True,
                'prompts_type': 'text',
                'self_incomplete': True,
                'show_rubric_during_response': False,
                'student_submission': create_submission_dict(submission, xblock.prompts),
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_cancelled_submission(self, xblock):
        mock_staff = Mock(name='Bob')
        xblock.get_username = Mock(return_value=mock_staff)
        submission = self.create_test_submission(xblock)
        workflow_api.cancel_workflow(
            submission_uuid=submission['uuid'], comments='Inappropriate language',
            cancelled_by_id='Bob',
            assessment_requirements=xblock.workflow_requirements(),
            course_settings={},
        )

        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response_cancelled.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'date_config_type': 'manual',
                'enable_delete_files': False,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': False,
                'prompts_type': 'text',
                'show_rubric_during_response': False,
                'student_submission': submission,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
                'workflow_cancellation': {
                    'comments': 'Inappropriate language',
                    'cancelled_at': xblock.get_workflow_cancellation_info(
                        submission['uuid']).get('cancelled_at'),
                    'cancelled_by_id': 'Bob',
                    'cancelled_by': mock_staff
                },
            }
        )

    @scenario('data/team_submission.xml', user_id="Red Five")
    def test_cancelled_team_submission(self, xblock):
        self.setup_mock_team(xblock)

        # pylint: disable=protected-access
        xblock.runtime._services['user'] = NullUserService()
        xblock.runtime._services['user_state'] = UserStateService()
        xblock.runtime._services['teams'] = MockTeamsService(True)

        xblock.user_state_upload_data_enabled = Mock(return_value=True)
        xblock.is_team_assignment = Mock(return_value=True)

        student_item_dict = xblock.get_student_item_dict()
        team_submission = submissions_actions.create_team_submission(
            student_item_dict,
            ('a man must have a code', 'a man must also have a towel'),
            xblock.config_data,
            xblock.submission_data,
            xblock.workflow_data,
        )

        workflow = xblock.get_workflow_info()
        student_submission = sub_api.get_submission(workflow['submission_uuid'])

        comments = "Cancelled by staff"
        staff_id = "Andy"
        mock_staff = Mock(name=staff_id)
        xblock.get_username = Mock(return_value=mock_staff)

        team_workflow_api.cancel_workflow(
            team_submission_uuid=team_submission['team_submission_uuid'],
            comments=comments,
            cancelled_by_id=staff_id
        )

        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response_cancelled.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'date_config_type': 'manual',
                'enable_delete_files': False,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': True,
                'prompts_type': 'text',
                'show_rubric_during_response': False,
                'student_submission': student_submission,
                # date listed in xml scenario.
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
                'workflow_cancellation': {
                    'comments': comments,
                    'cancelled_at': xblock.get_team_workflow_cancellation_info(
                        team_submission['team_submission_uuid']).get('cancelled_at'),
                    'cancelled_by_id': staff_id,
                    'cancelled_by': mock_staff
                },
            }
        )

    @patch.object(OpenAssessmentBlock, 'get_user_submission')
    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_submitted_old_format(self, xblock, mock_get_user_submission):
        self.create_test_submission(xblock)

        mock_get_user_submission.return_value = {"answer": {"text": "An old format response."}}
        xblock.prompts = [{'description': 'One prompt.'}]

        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response_submitted.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'date_config_type': 'manual',
                'enable_delete_files': False,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': False,
                'peer_incomplete': True,
                'prompts_type': 'text',
                'self_incomplete': True,
                'show_rubric_during_response': False,
                'student_submission': {"answer": {"parts": [
                    {"prompt": {'description': 'One prompt.'}, "text": "An old format response."}
                ]}},
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
            }
        )

    @scenario('data/submission_closed.xml', user_id="Bob")
    def test_closed_incomplete(self, xblock):
        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response_closed.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'date_config_type': 'manual',
                'enable_delete_files': False,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': False,
                'prompts_type': 'text',
                'show_rubric_during_response': False,
                'submission_due': dt.datetime(2014, 4, 5).replace(tzinfo=pytz.utc),
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
            }
        )

    @scenario('data/submission_closed.xml', user_id="Bob")
    def test_closed_submitted(self, xblock):
        submission = self.create_test_submission(xblock)
        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response_submitted.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'date_config_type': 'manual',
                'enable_delete_files': False,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': False,
                'peer_incomplete': False,
                'prompts_type': 'text',
                'self_incomplete': True,
                'show_rubric_during_response': False,
                'student_submission': create_submission_dict(submission, xblock.prompts),
                'submission_due': dt.datetime(2014, 4, 5).replace(tzinfo=pytz.utc),
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_graded(self, xblock):
        # Create a submission
        submission = self.create_test_submission(xblock)

        # Simulate the user receiving a grade
        xblock.get_workflow_info = Mock(return_value={
            'status': 'done',
            'submission_uuid': submission['uuid']
        })

        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response_graded.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'date_config_type': 'manual',
                'enable_delete_files': False,
                'file_upload_response': None,
                'file_upload_type': None,
                'has_real_user': False,
                'prompts_type': 'text',
                'show_rubric_during_response': False,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'student_submission': create_submission_dict(submission, xblock.prompts),
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
            }
        )

    @scenario('data/submission_closed.xml', user_id="Bob")
    def test_closed_graded(self, xblock):
        # Create a submission
        submission = self.create_test_submission(xblock)

        # Simulate the user receiving a grade
        xblock.get_workflow_info = Mock(return_value={
            'status': 'done',
            'submission_uuid': submission['uuid']
        })

        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response_graded.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'date_config_type': 'manual',
                'enable_delete_files': False,
                'has_real_user': False,
                'file_upload_response': None,
                'file_upload_type': None,
                'prompts_type': 'text',
                'show_rubric_during_response': False,
                'student_submission': create_submission_dict(submission, xblock.prompts),
                'submission_due': dt.datetime(2014, 4, 5).replace(tzinfo=pytz.utc),
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_integration(self, xblock):
        # Expect that the response step is open and displays the deadline
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        self.assertIn('Enter your response to the prompt', resp.decode('utf-8'))
        self.assertIn('2999-05-06T00:00:00+00:00', resp.decode('utf-8'))

        # Create a submission for the user
        self.create_test_submission(xblock)

        # Expect that the response step is "submitted"
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        self.assertIn('your response has been submitted', resp.decode('utf-8').lower())

    @patch('openassessment.xblock.apis.submissions.file_api.file_upload_api', autospec=True)
    @scenario('data/submission_open.xml', user_id="Bob")
    def test_can_delete_file(self, xblock, mock_file_api):
        xblock.get_team_info = Mock(return_value={'team_id': 'my-team-id'})
        xblock.is_team_assignment = Mock(return_value=True)

        mock_can_delete_file = mock_file_api.can_delete_file
        mock_get_student_file_key = mock_file_api.get_student_file_key

        self.assertEqual(
            mock_file_api.can_delete_file.return_value,
            xblock.submission_data.files.can_delete_file(5)
        )
        mock_get_student_file_key.assert_called_once_with(xblock.get_student_item_dict(), index=5)
        mock_can_delete_file.assert_called_once_with('Bob', True, mock_get_student_file_key.return_value, 'my-team-id')

    @patch('openassessment.xblock.apis.submissions.file_api.file_upload_api', autospec=True)
    @scenario('data/submission_open.xml', user_id="Bob")
    def test_can_delete_file_no_team_info(self, xblock, mock_file_api):
        xblock.get_team_info = Mock(return_value={})
        xblock.is_team_assignment = Mock(return_value=True)

        mock_can_delete_file = mock_file_api.can_delete_file
        mock_get_student_file_key = mock_file_api.get_student_file_key

        self.assertEqual(
            mock_can_delete_file.return_value,
            xblock.submission_data.files.can_delete_file(5)
        )
        mock_get_student_file_key.assert_called_once_with(xblock.get_student_item_dict(), index=5)
        mock_can_delete_file.assert_called_once_with('Bob', True, mock_get_student_file_key.return_value, None)

    @scenario('data/team_submission.xml', user_id="Red Five")
    def test_change_team_with_submission(self, xblock):
        """
        Test that if a user submits with one team, then joins another team, they will see their original submission

        The user was originally part of TeamA, which was where they submitted their submission,
        then joined TestTeam
        """
        self.setup_mock_team(xblock)

        # pylint: disable=protected-access
        xblock.runtime._services['user'] = NullUserService()
        xblock.runtime._services['user_state'] = UserStateService()
        xblock.runtime._services['teams'] = MockTeamsService(True)

        # Assert that Red Five is on our test team
        self.assertEqual(xblock.team.name, "TeamName")

        # Create Red Five's existing submission with some other team
        arbitrary_user = get_user_model().objects.create_user(username='someuser', password='asdfasdfasf')
        _, team_workflow = self._create_team_submission_and_workflow(
            'test_course',
            xblock.scope_ids.usage_id,
            'TeamA',
            arbitrary_user.id,
            ['r5', 'tA1', 'tA2', 'tA3'],
            {'text': 'This is the answer'},
        )
        individual_submission = sub_api.get_submission(team_workflow.submission_uuid)

        # Assert that the xblock will render Red Five's existing submission rather that
        # no submission (because TestTeam does not yet have a submission)
        path, context = xblock.submission_path_and_context()
        self.assertEqual(path, 'legacy/response/oa_response_submitted.html')
        self.assertEqual(context['student_submission'], create_submission_dict(individual_submission, xblock.prompts))

    @scenario('data/team_submission.xml', user_id="Red Five")
    def test_leave_team_with_submission(self, xblock):
        """
        If a user was on a team that submitted, but leaves the team in the future. They will still
        see their original submission.
        """
        self.setup_mock_team(xblock)

        # pylint: disable=protected-access
        xblock.runtime._services['user'] = NullUserService()
        xblock.runtime._services['user_state'] = UserStateService()
        xblock.runtime._services['teams'] = MockTeamsService(True)

        # Assert that Red Five is on our test team
        self.assertEqual(xblock.team.name, "TeamName")

        # Create Red Five's existing submission with some other team
        arbitrary_user = get_user_model().objects.create_user(username='someuser', password='asdfasdfasf')
        _, team_workflow = self._create_team_submission_and_workflow(
            'test_course',
            xblock.scope_ids.usage_id,
            'TeamA',
            arbitrary_user.id,
            ['r5', 'tA1', 'tA2', 'tA3'],
            {'text': 'This is the answer'},
        )
        individual_submission = sub_api.get_submission(team_workflow.submission_uuid)

        # Red Five leaves the team
        xblock.has_team = Mock(return_value=False)

        # Assert that the xblock will render Red Five's existing submission rather that no submission
        path, context = xblock.submission_path_and_context()
        self.assertEqual(path, 'legacy/response/oa_response_submitted.html')
        self.assertEqual(context['student_submission'], create_submission_dict(individual_submission, xblock.prompts))

    @scenario('data/team_submission.xml', user_id="Red Five")
    def test_get_submission_context_no_team(self, xblock):
        """
        A student who tries to view a team assignment w/out being on a team will see the "response unavialable" view
        """
        # Set up a team assignment, but remove the user from the team
        self.setup_mock_team(xblock)
        xblock.has_team = Mock(return_value=False)
        xblock.get_team_info = Mock(return_value={})

        # pylint: disable=protected-access
        xblock.runtime._services['user'] = NullUserService()
        xblock.runtime._services['user_state'] = UserStateService()
        xblock.runtime._services['teams'] = MockTeamsService(True)

        # Assert that the xblock renders an unavailable submission
        path, _ = xblock.submission_path_and_context()
        self.assertEqual(path, 'legacy/response/oa_response_unavailable.html')

    @scenario('data/team_submission.xml', user_id="Red Five")
    def test_team_has_already_submitted(self, xblock):
        """
        Test that if a user is on a team hat has already submitted, but they themself have not submitted,
        the correct page is rendered.
        """
        self.setup_mock_team(xblock)

        # pylint: disable=protected-access
        xblock.runtime._services['user'] = NullUserService()
        xblock.runtime._services['user_state'] = UserStateService()
        xblock.runtime._services['teams'] = MockTeamsService(True)

        # Create a submission for the team, but without r5.
        arbitrary_user = get_user_model().objects.create_user(username='someuser', password='asdfasdfasf')
        self._create_team_submission_and_workflow(
            'test_course',
            xblock.scope_ids.usage_id,
            MOCK_TEAM_ID,
            arbitrary_user.id,
            ['rl', 'r2'],
            {'text': 'This is the answer'},
        )

        # Assert that we return the 'team already submitted' path
        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response_team_already_submitted.html',
            {
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ("", "")
                    )
                }, xblock.prompts),
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'date_config_type': 'manual',
                'enable_delete_files': True,
                'has_real_user': True,
                'file_upload_response': None,
                'file_upload_type': None,
                'prompts_type': 'text',
                'save_status': 'Response not started.',
                'show_rubric_during_response': False,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'team_id': MOCK_TEAM_ID,
                'team_name': 'Red Squadron',
                'team_members_with_external_submissions': '',
                'team_url': 'rebel_alliance.org',
                'team_usernames': ['Red Leader', 'Red Two', 'Red Five'],
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_language': None,
                'user_timezone': None,
            }
        )

    @scenario('data/file_upload_scenario.xml', user_id="Bob")
    def test_load_file_extension_presets(self, xblock):
        """
        Loading an ORA w/ a file upload preset (e.g. pdf-and-image) will load the list of allowed extensions into
        the context. This allows us to show what files types are allowed for any upload configuration.
        """
        self._assert_path_and_context(
            xblock, 'legacy/response/oa_response.html',
            {
                'allow_latex': False,
                'allow_learner_resubmissions': False,
                'allow_multiple_files': True,
                'base_asset_url': None,
                'enable_delete_files': True,
                'file_upload_response': 'optional',
                'file_upload_type': 'pdf-and-image',
                'file_urls': [],
                'has_real_user': False,
                'prompts_type': 'text',
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ("", "")
                    )
                }, xblock.prompts),
                'save_status': 'Response not started.',
                'show_rubric_during_response': False,
                'team_file_urls': [],
                'text_response': 'required',
                'text_response_editor': 'text',
                'user_timezone': None,
                'user_language': None,
                'white_listed_file_types': ['.pdf', '.gif', '.jpg', '.jpeg', '.jfif', '.pjpeg', '.pjp', '.png'],
            }
        )

    def _create_team_submission_and_workflow(
        self, course_id, item_id, team_id, submitter_id, team_member_student_ids, answer
    ):
        """ Create a team submission and team workflow with the given info """
        team_submission = team_sub_api.create_submission_for_team(
            course_id,
            item_id,
            team_id,
            submitter_id,
            team_member_student_ids,
            answer
        )
        team_workflow = team_workflow_api.create_workflow(team_submission['team_submission_uuid'])
        return team_submission, team_workflow

    def _assert_path_and_context(self, xblock, expected_path, expected_context):
        """
        Render the submission step and verify that the correct template
        and context were used.  Also verify that the template rendered
        without error.

        Args:
            xblock (OpenAssessmentBlock): The XBlock under test.
            expected_path (str): The expected template path.
            expected_context (dict): The expected template context.

        Returns:
            None

        Raises:
            AssertionError: An assertion failed.

        """
        expected_context['xblock_id'] = xblock.scope_ids.usage_id
        path, context = xblock.submission_path_and_context()
        self.maxDiff = None  # pylint: disable=invalid-name

        self.assertEqual(path, expected_path)
        self.assertDictEqual(context, expected_context)

        # Verify that we render without error
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        self.assertGreater(len(resp), 0)
