# -*- coding: utf-8 -*-
"""
Test submission to the OpenAssessment XBlock.
"""

import json
import datetime as dt
import boto
from boto.s3.key import Key
from django.test.utils import override_settings
from mock import patch, Mock
from moto import mock_s3
import pytz

from submissions import api as sub_api
from submissions.api import SubmissionRequestError, SubmissionInternalError
from openassessment.fileupload import api

from openassessment.workflow import api as workflow_api
from openassessment.xblock.openassessmentblock import OpenAssessmentBlock
from openassessment.xblock.data_conversion import create_submission_dict, prepare_submission_for_serialization

from .base import XBlockHandlerTestCase, scenario


class SubmissionTest(XBlockHandlerTestCase):
    SUBMISSION = json.dumps({
        "submission": ["This is my answer to the first question!", "This is my answer to the second question!"]
    })

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_submit_submission(self, xblock):
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertTrue(resp[0])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_submit_answer_too_long(self, xblock):
        # Maximum answer length is 100K, once the answer has been JSON-encoded
        long_submission = json.dumps({
            "submission": ["This is my answer to the first question!" * 100000,
                           "This is my answer to the second question!"]
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
    def test_submission_API_failure(self, xblock, mock_submit):
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

    @scenario('data/over_grade_scenario.xml', user_id='Alice')
    def test_closed_submissions(self, xblock):
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        self.assertIn("Incomplete", resp)

    @scenario('data/line_breaks.xml')
    def test_prompt_line_breaks(self, xblock):
        # Verify that prompts with multiple lines retain line breaks
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        expected_prompt = u"<p><br />Line 1</p><p>Line 2</p><p>Line 3<br /></p>"
        self.assertIn(expected_prompt, resp)

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
        self.assertTrue(resp['url'].startswith(
            'https://mybucket.s3.amazonaws.com/submissions_attachments/test_student/test_course/' + xblock.scope_ids.usage_id
        ))

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

    @mock_s3
    @override_settings(
        AWS_ACCESS_KEY_ID='foobar',
        AWS_SECRET_ACCESS_KEY='bizbaz',
        FILE_UPLOAD_STORAGE_BUCKET_NAME="mybucket"
    )
    @scenario('data/file_upload_scenario.xml')
    def test_download_url_non_existing_file(self, xblock):
        """ Test generate a download URL for non-existing file, should return empty string """
        resp = self.request(xblock, 'download_url', json.dumps(dict()), response_format='json')

        self.assertTrue(resp['success'])
        self.assertEqual(u'', resp['url'])


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
                'file_upload_type': None,
                'submission_start': dt.datetime(4999, 4, 1).replace(tzinfo=pytz.utc),
                'has_peer': True,
                'has_self': True,
                'allow_latex': False,
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
                'file_upload_type': None,
                'has_peer': True,
                'has_self': True,
                'allow_latex': False,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_unanswered(self, xblock):
        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response.html',
            {
                'file_upload_type': None,
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ("", "")
                    )
                }, xblock.prompts),
                'save_status': 'This response has not been saved.',
                'submit_enabled': False,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'has_peer': True,
                'has_self': True,
                'allow_latex': False,
            }
        )

    @scenario('data/submission_no_deadline.xml', user_id="Bob")
    def test_open_no_deadline(self, xblock):
        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response.html',
            {
                'file_upload_type': None,
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ("", "")
                    )
                }, xblock.prompts),
                'save_status': 'This response has not been saved.',
                'submit_enabled': False,
                'has_peer': True,
                'has_self': False,
                'allow_latex': False,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_saved_response(self, xblock):
        # Save a response
        payload = json.dumps({'submission': ('A man must have a code', 'A man must have an umbrella too.')})
        resp = self.request(xblock, 'save_submission', payload, response_format='json')
        self.assertTrue(resp['success'])

        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response.html',
            {
                'file_upload_type': None,
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ('A man must have a code', 'A man must have an umbrella too.')
                    )
                }, xblock.prompts),
                'save_status': 'This response has been saved but not submitted.',
                'submit_enabled': True,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'has_peer': True,
                'has_self': True,
                'allow_latex': False,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_saved_response_old_format(self, xblock):
        # Save a response
        xblock.prompts = [{'description': 'One prompt.'}]
        xblock.saved_response = "An old format response."
        xblock.has_saved = True

        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response.html',
            {
                'file_upload_type': None,
                'saved_response': create_submission_dict({
                    'answer': prepare_submission_for_serialization(
                        ('An old format response.',)
                    )
                }, xblock.prompts),
                'save_status': 'This response has been saved but not submitted.',
                'submit_enabled': True,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'has_peer': True,
                'has_self': True,
                'allow_latex': False,
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
                'file_upload_type': None,
                'has_peer': True,
                'has_self': True,
                'allow_latex': False,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_cancelled_submission(self, xblock):
        student_item = xblock.get_student_item_dict()
        submission = xblock.create_submission(
            student_item,
            ('A man must have a code', 'A man must have an umbrella too.')
        )
        xblock.get_workflow_info = Mock(return_value={
            'status': 'cancelled',
            'submission_uuid': submission['uuid']
        })

        xblock.get_username = Mock(return_value='Bob')

        workflow_api.get_assessment_workflow_cancellation = Mock(return_value={
            'comments': 'Inappropriate language',
            'cancelled_by_id': 'Bob',
            'created_at': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
            'cancelled_by': 'Bob'
        })

        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response_cancelled.html',
            {
                'file_upload_type': None,
                'allow_latex': False,
                'has_peer': True,
                'has_self': True,
                'submission_due': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                'student_submission': submission,
                'workflow_cancellation': {
                    'comments': 'Inappropriate language',
                    'cancelled_by_id': 'Bob',
                    'created_at': dt.datetime(2999, 5, 6).replace(tzinfo=pytz.utc),
                    'cancelled_by': 'Bob'
                }
            }
        )

    @patch.object(OpenAssessmentBlock, 'get_user_submission')
    @scenario('data/submission_open.xml', user_id="Bob")
    def test_open_submitted_old_format(self, xblock, mock_get_user_submission):
        submission = xblock.create_submission(
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
                'file_upload_type': None,
                'has_peer': True,
                'has_self': True,
                'allow_latex': False,
            }
        )

    @scenario('data/submission_closed.xml', user_id="Bob")
    def test_closed_incomplete(self, xblock):
        self._assert_path_and_context(
            xblock, 'openassessmentblock/response/oa_response_closed.html',
            {
                'file_upload_type': None,
                'submission_due': dt.datetime(2014, 4, 5).replace(tzinfo=pytz.utc),
                'has_peer': False,
                'has_self': True,
                'allow_latex': False,
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
                'file_upload_type': None,
                'has_peer': False,
                'has_self': True,
                'allow_latex': False,
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
                'file_upload_type': None,
                'has_peer': True,
                'has_self': True,
                'allow_latex': False,
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
                'file_upload_type': None,
                'has_peer': False,
                'has_self': True,
                'allow_latex': False,
            }
        )

    @scenario('data/submission_open.xml', user_id="Bob")
    def test_integration(self, xblock):
        # Expect that the response step is open and displays the deadline
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        self.assertIn('Enter your response to the question', resp)
        self.assertIn('Monday, May 6, 2999 00:00 UTC', resp)

        # Create a submission for the user
        xblock.create_submission(
            xblock.get_student_item_dict(),
            (u'Ⱥ mȺn mᵾsŧ ħȺvɇ Ⱥ ȼøđɇ.', u'∀ ɯɐu ɯnsʇ ɥɐʌǝ ɐu nɯqɹǝllɐ ʇoo˙'),
        )

        # Expect that the response step is "submitted"
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        self.assertIn('your response has been submitted', resp.lower())

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
        path, context = xblock.submission_path_and_context()
        self.assertEqual(path, expected_path)
        self.assertEqual(context, expected_context)

        # Verify that we render without error
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        self.assertGreater(len(resp), 0)
