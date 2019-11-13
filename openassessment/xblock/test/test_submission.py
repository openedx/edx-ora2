# -*- coding: utf-8 -*-
"""
Test submission to the OpenAssessment XBlock.
"""

from __future__ import absolute_import

import datetime as dt
import json

from mock import Mock, patch
import pytz

from django.test.utils import override_settings

import boto
from boto.s3.key import Key
from moto import mock_s3
from openassessment.fileupload import api
from openassessment.workflow import api as workflow_api
from openassessment.xblock.data_conversion import create_submission_dict, prepare_submission_for_serialization
from openassessment.xblock.openassessmentblock import OpenAssessmentBlock
from openassessment.xblock.workflow_mixin import WorkflowMixin
from submissions import api as sub_api
from submissions.api import SubmissionInternalError, SubmissionRequestError

from .base import XBlockHandlerTestCase, scenario


class SubmissionTest(XBlockHandlerTestCase):
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
        self.assertIsNot(resp[2], None)

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
            course_id='test_course',
            anonymous_student_id='test_student'
        )

        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "ENOPREVIEW")
        self.assertIsNot(resp[2], None)

    def _ability_to_submit_blank_answer(self, xblock):
        """
        Checks ability to submit blank answer if text response is not required

        """
        empty_submission = json.dumps({"submission": [""]})
        resp = self.request(xblock, 'submit', empty_submission, response_format='json')
        self.assertTrue(resp[0])

    @scenario('data/text_response_optional.xml', user_id='Bob')
    def test_ability_to_submit_blank_answer_if_text_response_optional(self, xblock):
        """
        Checks ability to submit blank answer if text response is optional

        """
        self._ability_to_submit_blank_answer(xblock)

    @scenario('data/text_response_none.xml', user_id='Bob')
    def test_ability_to_submit_blank_answer_if_text_response_none(self, xblock):
        """
        Checks ability to submit blank answer if text response is None

        """
        self._ability_to_submit_blank_answer(xblock)

    @scenario('data/over_grade_scenario.xml', user_id='Alice')
    def test_closed_submissions(self, xblock):
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        self.assertIn("Incomplete", resp.decode('utf-8'))

    @scenario('data/line_breaks.xml')
    def test_prompt_line_breaks(self, xblock):
        # Verify that prompts with multiple lines retain line breaks
        # (backward compatibility in case if prompt_type == 'text')
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        expected_prompt = u"<p><br />Line 1</p><p>Line 2</p><p>Line 3<br /></p>"
        self.assertIn(expected_prompt, resp.decode('utf-8'))

    @scenario('data/prompt_html.xml')
    def test_prompt_html_to_text(self, xblock):
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        expected_prompt = u"<code><strong>Question 123</strong></code>"
        self.assertIn(expected_prompt, resp.decode('utf-8'))

        xblock.prompts_type = "text"
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
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
            course_id='test_course',
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
    @scenario('data/file_upload_scenario.xml')
    def test_download_url(self, xblock):
        """ Test generate correct download URL with existing file. should create a file and get the download URL """
        conn = boto.connect_s3()
        bucket = conn.create_bucket('mybucket')
        key = Key(bucket)
        key.key = "submissions_attachments/test_student/test_course/" + xblock.scope_ids.usage_id
        key.set_contents_from_string("How d'ya do?")
        download_url = api.get_download_url("test_student/test_course/" + xblock.scope_ids.usage_id)

        xblock.xmodule_runtime = Mock(
            course_id='test_course',
            anonymous_student_id='test_student',
        )

        resp = self.request(xblock, 'download_url', json.dumps(dict()), response_format='json')

        self.assertTrue(resp['success'])
        self.assertEqual(download_url, resp['url'])

    def _get_student_item_key(self, num, usage_id):
        key = "submissions_attachments/test_student/test_course/" + usage_id
        if num > 0:
            key = key + "/" + str(num)
        return key

    def _create_uploaded_file(self, bucket, file_num, usage_id):
        key = Key(bucket)
        key.key = self._get_student_item_key(file_num, usage_id)
        key.set_contents_from_string("How d'ya do?")

    def _create_uploaded_files(self, num_files, usage_key):
        conn = boto.connect_s3()
        bucket = conn.create_bucket('mybucket')
        for i in range(num_files):
            self._create_uploaded_file(bucket, i, usage_key)

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
        """ Test that after deleting a file, the remaining files are correctly submitted  """
        self._create_uploaded_files(5, xblock.scope_ids.usage_id)
        xblock.xmodule_runtime = Mock(
            course_id='test_course',
            anonymous_student_id='test_student',
        )
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
        with patch('submissions.api.create_submission') as mocked_submit:
            with patch.object(WorkflowMixin, 'create_workflow'):
                mocked_submit.return_value = {
                    "uuid": '1111',
                    "attempt_number": 1,
                    "created_at": dt.datetime.now(),
                    "submitted_at": dt.datetime.now(),
                    "answer": {},
                }
                resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
                mocked_submit.assert_called_once()
                student_sub_dict = mocked_submit.call_args[0][1]
                self.assertEqual(
                    student_sub_dict['files_descriptions'],
                    [meta['description'] for meta in expected_file_metadata]
                )
                self.assertEqual(
                    student_sub_dict['files_name'],
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
        resp = self.request(xblock, 'download_url', json.dumps(dict()), response_format='json')

        self.assertTrue(resp['success'])
        self.assertEqual(u'', resp['url'])

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
            course_id='test_course',
            anonymous_student_id='test_student',
        )
        resp = self.request(xblock, 'upload_url', json.dumps({'contentType': 'filename',
                                                              'filename': 'test.PDF'}), response_format='json')
        self.assertTrue(resp['success'])
        self.assertIn(
            '/submissions_attachments/test_student/test_course/' + xblock.scope_ids.usage_id,
            resp['url']
        )


class SubmissionRenderTest(XBlockHandlerTestCase):
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
            xblock, 'openassessmentblock/response/oa_response_unavailable.html',
            {
                'text_response': 'required',
                'file_upload_response': None,
                'file_upload_type': None,
                'submission_start': dt.datetime(4999, 4, 1).replace(tzinfo=pytz.utc),
                'allow_latex': False,
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': False,
            }
        )

    @scenario('data/submission_unavailable.xml', user_id="Bob")
    def test_unavailable_submitted(self, xblock):
        # If the instructor changes the start date after the problem
        # has opened, it's possible for a student to have made a submission
        # even though the problem is unavailable.
        # In this case, we should continue showing that the student completed
        # the submission.
        submission = xblock.create_submission(
            xblock.get_student_item_dict(),
            ('A man must have a code', 'A man must have an umbrella too.')
        )
        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response_submitted.html',
            {
                'student_submission': create_submission_dict(submission, xblock.prompts),
                'text_response': 'required',
                'file_upload_response': None,
                'file_upload_type': None,
                'peer_incomplete': True,
                'self_incomplete': True,
                'allow_latex': False,
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': False,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_unanswered(self, xblock):
        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response.html',
            {
                'text_response': 'required',
                'file_upload_response': None,
                'file_upload_type': None,
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ("", "")
                    )
                }, xblock.prompts),
                'save_status': 'This response has not been saved.',
                'submit_enabled': False,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'allow_latex': False,
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': True,
            }
        )

    @scenario('data/submission_no_deadline.xml', user_id="Bob")
    def test_open_no_deadline(self, xblock):
        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response.html',
            {
                'text_response': 'required',
                'file_upload_response': None,
                'file_upload_type': None,
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ("", "")
                    )
                }, xblock.prompts),
                'save_status': 'This response has not been saved.',
                'submit_enabled': False,
                'allow_latex': False,
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': True,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_saved_response(self, xblock):
        descriptions = ["whatever.pdf", "anything you want to call it is fine"]
        names = ["whatever.pdf", "anything.pdf"]
        sizes = [200, 400]

        xblock.append_safe_normalized_file_metadata(descriptions, names, sizes)

        # Save a response
        payload = json.dumps({'submission': ('A man must have a code', 'A man must have an umbrella too.')})
        resp = self.request(xblock, 'save_submission', payload, response_format='json')
        self.assertTrue(resp['success'])

        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response.html',
            {
                'text_response': 'required',
                'file_upload_response': None,
                'file_upload_type': None,
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ('A man must have a code', 'A man must have an umbrella too.')
                    )
                }, xblock.prompts),
                'save_status': 'This response has been saved but not submitted.',
                'submit_enabled': True,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'allow_latex': False,
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': True,
            }
        )

        self.assertEqual(descriptions, xblock.get_file_descriptions())
        self.assertEqual(names, xblock.get_file_names())
        self.assertEqual(sizes, xblock.get_file_sizes())

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_saved_response_misaligned_file_data(self, xblock):
        descriptions = ["whatever.pdf", "anything you want to call it is fine"]
        names = []
        sizes = [200]

        xblock.set_file_descriptions(descriptions)
        xblock.set_file_names(names)
        xblock.set_file_sizes(sizes)

        xblock.file_upload_type = 'pdf-and-image'
        xblock.file_upload_response = 'optional'

        # Save a response
        payload = json.dumps({'submission': ('A man must have a code', 'A man must have an umbrella too.')})
        resp = self.request(xblock, 'save_submission', payload, response_format='json')
        self.assertTrue(resp['success'])

        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response.html',
            {
                'text_response': 'required',
                'file_upload_response': 'optional',
                'file_upload_type': 'pdf-and-image',
                'file_urls': [
                    ('', u'whatever.pdf', None),
                    ('', u'anything you want to call it is fine', None)
                ],
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ('A man must have a code', 'A man must have an umbrella too.')
                    )
                }, xblock.prompts),
                'save_status': 'This response has been saved but not submitted.',
                'submit_enabled': True,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'allow_latex': False,
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': True,
            }
        )

        self.assertEqual(["whatever.pdf", "anything you want to call it is fine"], xblock.get_file_descriptions())
        self.assertEqual([None, None], xblock.get_file_names())
        self.assertEqual([None, None], xblock.get_file_sizes())

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_saved_response_old_format(self, xblock):
        # Save a response
        xblock.prompts = [{'description': 'One prompt.'}]
        xblock.saved_response = "An old format response."
        xblock.has_saved = True

        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response.html',
            {
                'text_response': 'required',
                'file_upload_response': None,
                'file_upload_type': None,
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ('An old format response.',)
                    )
                }, xblock.prompts),
                'save_status': 'This response has been saved but not submitted.',
                'submit_enabled': True,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'allow_latex': False,
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': True,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_submitted(self, xblock):
        submission = xblock.create_submission(
            xblock.get_student_item_dict(),
            ('A man must have a code', 'A man must have an umbrella too.')
        )
        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response_submitted.html',
            {
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'student_submission': create_submission_dict(submission, xblock.prompts),
                'text_response': 'required',
                'file_upload_response': None,
                'file_upload_type': None,
                'peer_incomplete': True,
                'self_incomplete': True,
                'allow_latex': False,
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': False,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_cancelled_submission(self, xblock):
        student_item = xblock.get_student_item_dict()
        mock_staff = Mock(name='Bob')
        xblock.get_username = Mock(return_value=mock_staff)
        submission = xblock.create_submission(
            student_item,
            ('A man must have a code', 'A man must have an umbrella too.')
        )
        workflow_api.cancel_workflow(
            submission_uuid=submission['uuid'], comments='Inappropriate language',
            cancelled_by_id='Bob',
            assessment_requirements=xblock.workflow_requirements()
        )

        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response_cancelled.html',
            {
                'text_response': 'required',
                'file_upload_response': None,
                'file_upload_type': None,
                'allow_latex': False,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'student_submission': submission,
                'workflow_cancellation': {
                    'comments': 'Inappropriate language',
                    'cancelled_at': xblock.get_workflow_cancellation_info(submission['uuid']).get('cancelled_at'),
                    'cancelled_by_id': 'Bob',
                    'cancelled_by': mock_staff
                },
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': False,
            }
        )

    @patch.object(OpenAssessmentBlock, 'get_user_submission')
    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_submitted_old_format(self, xblock, mock_get_user_submission):
        xblock.create_submission(
            xblock.get_student_item_dict(),
            ('A man must have a code', 'A man must have an umbrella too.')
        )

        mock_get_user_submission.return_value = {"answer": {"text": "An old format response."}}
        xblock.prompts = [{'description': 'One prompt.'}]

        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response_submitted.html',
            {
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'student_submission': {"answer": {"parts": [
                    {"prompt": {'description': 'One prompt.'}, "text": "An old format response."}
                ]}},
                'text_response': 'required',
                'file_upload_response': None,
                'file_upload_type': None,
                'peer_incomplete': True,
                'self_incomplete': True,
                'allow_latex': False,
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': False,
            }
        )

    @scenario('data/submission_closed.xml', user_id="Bob")
    def test_closed_incomplete(self, xblock):
        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response_closed.html',
            {
                'text_response': 'required',
                'file_upload_response': None,
                'file_upload_type': None,
                'submission_due': dt.datetime(2014, 4, 5).replace(tzinfo=pytz.utc),
                'allow_latex': False,
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': False,
            }
        )

    @scenario('data/submission_closed.xml', user_id="Bob")
    def test_closed_submitted(self, xblock):
        submission = xblock.create_submission(
            xblock.get_student_item_dict(),
            ('A man must have a code', 'A man must have an umbrella too.')
        )
        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response_submitted.html',
            {
                'submission_due': dt.datetime(2014, 4, 5).replace(tzinfo=pytz.utc),
                'student_submission': create_submission_dict(submission, xblock.prompts),
                'text_response': 'required',
                'file_upload_response': None,
                'file_upload_type': None,
                'peer_incomplete': False,
                'self_incomplete': True,
                'allow_latex': False,
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': False,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_graded(self, xblock):
        # Create a submission
        submission = xblock.create_submission(
            xblock.get_student_item_dict(),
            ('A man must have a code', 'A man must have an umbrella too.')
        )

        # Simulate the user receiving a grade
        xblock.get_workflow_info = Mock(return_value={
            'status': 'done',
            'submission_uuid': submission['uuid']
        })

        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response_graded.html',
            {
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'student_submission': create_submission_dict(submission, xblock.prompts),
                'text_response': 'required',
                'file_upload_response': None,
                'file_upload_type': None,
                'allow_latex': False,
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': False,
            }
        )

    @scenario('data/submission_closed.xml', user_id="Bob")
    def test_closed_graded(self, xblock):
        # Create a submission
        submission = xblock.create_submission(
            xblock.get_student_item_dict(),
            ('A man must have a code', 'A man must have an umbrella too.')
        )

        # Simulate the user receiving a grade
        xblock.get_workflow_info = Mock(return_value={
            'status': 'done',
            'submission_uuid': submission['uuid']
        })

        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response_graded.html',
            {
                'submission_due': dt.datetime(2014, 4, 5).replace(tzinfo=pytz.utc),
                'student_submission': create_submission_dict(submission, xblock.prompts),
                'text_response': 'required',
                'file_upload_response': None,
                'file_upload_type': None,
                'allow_latex': False,
                'user_timezone': None,
                'user_language': None,
                'prompts_type': 'text',
                'enable_delete_files': False,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_integration(self, xblock):
        # Expect that the response step is open and displays the deadline
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        self.assertIn('Enter your response to the prompt', resp.decode('utf-8'))
        self.assertIn('2999-05-06T00:00:00+00:00', resp.decode('utf-8'))

        # Create a submission for the user
        xblock.create_submission(
            xblock.get_student_item_dict(),
            (u'Ⱥ mȺn mᵾsŧ ħȺvɇ Ⱥ ȼøđɇ.', u'∀ ɯɐu ɯnsʇ ɥɐʌǝ ɐu nɯqɹǝllɐ ʇoo˙'),
        )

        # Expect that the response step is "submitted"
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        self.assertIn('your response has been submitted', resp.decode('utf-8').lower())

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
        self.assertEqual(context, expected_context)

        # Verify that we render without error
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        self.assertGreater(len(resp), 0)
