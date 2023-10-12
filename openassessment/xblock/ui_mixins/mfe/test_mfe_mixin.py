"""
Tests for XBlock handlers for the ORA MFE BFF
"""
from contextlib import contextmanager
import json
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from submissions import api as submission_api
from submissions import team_api as submission_team_api

from openassessment.tests.factories import SharedFileUploadFactory, UserFactory
from openassessment.workflow import api as workflow_api
from openassessment.workflow import team_api as team_workflow_api
from openassessment.xblock.apis.submissions.errors import (
    AnswerTooLongException,
    DraftSaveException,
    EmptySubmissionError,
    MultipleSubmissionsException,
    StudioPreviewException,
    SubmissionValidationException,
    SubmitInternalError
)
from openassessment.xblock.test.base import XBlockHandlerTestCase, scenario
from openassessment.xblock.test.test_staff_area import NullUserService, UserStateService
from openassessment.xblock.test.test_submission import COURSE_ID, setup_mock_team
from openassessment.xblock.test.test_team import MOCK_TEAM_ID, MockTeamsService
from openassessment.xblock.ui_mixins.mfe.constants import ErrorCodes
from openassessment.xblock.ui_mixins.mfe.submission_serializers import PageDataSubmissionSerializer


class MFEHandlersTestBase(XBlockHandlerTestCase):

    def setUp(self):
        super().setUp()
        self.expected_file_urls = {}

    @contextmanager
    def mock_get_url(self, expected_file_urls=None):
        if expected_file_urls is None:
            expected_file_urls = {}
        base_url = 'www.downloadfiles.xyz/'
        with patch("openassessment.fileupload.api.get_download_url") as mock_unsubmitted_urls:
            with patch("openassessment.data.get_download_url") as mock_submitted_urls:
                mock_submitted_urls.side_effect = lambda file_key: base_url + file_key
                mock_unsubmitted_urls.side_effect = expected_file_urls.get
                yield

    DEFAULT_DRAFT_VALUE = {'response': {'text_responses': ['hi']}}
    DEFAULT_SUBMIT_VALUE = {'response': {'text_responses': ['Hello World', 'Goodbye World']}}

    def request_create_submission(self, xblock, payload=None):
        if payload is None:
            payload = self.DEFAULT_SUBMIT_VALUE
        return super().request(
            xblock,
            'submission',
            json.dumps(payload),
            suffix='create',
            response_format='response'
        )

    def request_learner_submission_info(self, xblock):
        return super().request(
            xblock,
            'get_block_learner_submission_data',
            '',
            response_format='response'
        )

    def request_save_draft(self, xblock, payload=None):
        if payload is None:
            payload = self.DEFAULT_DRAFT_VALUE
        return super().request(
            xblock,
            'submission',
            json.dumps(payload),
            suffix='draft',
            response_format='response'
        )


def assert_error_response(response, status_code, error_code, context=''):
    assert response.status_code == status_code
    assert response.json['error'] == {
        'error_code': error_code,
        'error_context': context
    }


def create_student_and_submission(student, course, item, answer, xblock=None):
    """ Creats a student and submission for tests. """
    submission = submission_api.create_submission(
        {
            'student_id': student,
            'course_id': course,
            'item_id': item,
            'item_type': 'openassessment',
        },
        answer,
        None
    )
    workflow_api.create_workflow(submission["uuid"], ['staff'])
    if xblock is not None:
        xblock.submission_uuid = submission["uuid"]
    return submission


def assert_called_once_with_helper(mock, expected_first_arg, expected_additional_args_count):
    """
    The API objects are not singletons and are sometimes recreated, so we can't check actual
    equality. This just checks the first arg, and that it's called with the expected # of args
    """
    mock.assert_called_once()
    assert mock.call_args.args[0] == expected_first_arg
    assert len(mock.call_args.args) == expected_additional_args_count + 1
    assert not mock.call_args.kwargs


class GetLearnerSubmissionDataIndividualSubmissionTest(MFEHandlersTestBase):

    def setup_xblock(self, xblock):
        xblock.xmodule_runtime = Mock(
            user_is_staff=False,
            user_is_beta_tester=False,
            course_id=COURSE_ID,
            anonymous_student_id='r5'
        )

    @scenario("data/file_upload_scenario.xml", user_id='r5')
    def test_nothing(self, xblock):
        with self.mock_get_url():
            learner_submission_data = xblock.get_learner_submission_data()
            data = PageDataSubmissionSerializer(learner_submission_data).data
        assert data == {
            'hasSubmitted': False,
            'hasCancelled': False,
            'hasRecievedGrade': False,
            'teamInfo': {},
            'response': {
                'textResponses': ['', ''],
                'uploadedFiles': []
            }
        }

    @scenario("data/file_upload_scenario.xml", user_id='r5')
    def test_not_yet_submitted(self, xblock):
        self.setup_xblock(xblock)
        xblock.saved_response = json.dumps({'parts': [{'text': 'hello world'}, {'text': 'goodnight moon'}]})
        xblock.file_manager.append_uploads(
            {'description': 'my presentation', 'name': 'file1.ppt', 'size': 2},
            {'description': 'video of presentation', 'name': 'file3.mp4', 'size': 3},
        )
        student_item = xblock.get_student_item_dict()
        base_key = f'{student_item["student_id"]}/{student_item["course_id"]}/{student_item["item_id"]}'
        with self.mock_get_url({
            base_key: 'www.downloadfiles.xyz/0',
            base_key + '/1': 'www.downloadfiles.xyz/1'
        }):
            learner_submission_data = xblock.get_learner_submission_data()
            data = PageDataSubmissionSerializer(learner_submission_data).data
        assert data == {
            'hasSubmitted': False,
            'hasCancelled': False,
            'hasRecievedGrade': False,
            'teamInfo': {},
            'response': {
                'textResponses': ['hello world', 'goodnight moon'],
                'uploadedFiles': [
                    {
                        'fileUrl': 'www.downloadfiles.xyz/0',
                        'fileName': 'file1.ppt',
                        'fileDescription': 'my presentation',
                        'fileSize': 2,
                        'fileIndex': 0,
                    },
                    {
                        'fileUrl': 'www.downloadfiles.xyz/1',
                        'fileName': 'file3.mp4',
                        'fileDescription': 'video of presentation',
                        'fileSize': 3,
                        'fileIndex': 1,
                    },
                ]
            }
        }

    @scenario("data/file_upload_scenario.xml", user_id='r5')
    def test_submitted(self, xblock):
        self.setup_xblock(xblock)
        create_student_and_submission(
            'bob',
            xblock.course_id,
            str(xblock.scope_ids.usage_id),
            {
                'parts': [{'text': 'hello world'}, {'text': 'goodnight world'}],
                'file_keys': ['f1', 'f2'],
                'files_descriptions': ['file1', 'file2'],
                'files_names': ['f1.txt', 'f2.pdf'],
                'files_sizes': [10, 300],
            },
            xblock
        )

        with self.mock_get_url():
            learner_submission_data = xblock.get_learner_submission_data()
            data = PageDataSubmissionSerializer(learner_submission_data).data
        assert data == {
            'hasSubmitted': True,
            'hasCancelled': False,
            'hasRecievedGrade': False,
            'teamInfo': {},
            'response': {
                'textResponses': ['hello world', 'goodnight world'],
                'uploadedFiles': [
                    {
                        'fileUrl': 'www.downloadfiles.xyz/f1',
                        'fileName': 'f1.txt',
                        'fileDescription': 'file1',
                        'fileSize': 10,
                        'fileIndex': 0,
                    },
                    {
                        'fileUrl': 'www.downloadfiles.xyz/f2',
                        'fileName': 'f2.pdf',
                        'fileDescription': 'file2',
                        'fileSize': 300,
                        'fileIndex': 1,
                    },
                ]
            }
        }


class PageDataSubmissionSerializerTest(MFEHandlersTestBase):
    def setup_xblock(self, xblock):
        setup_mock_team(xblock)
        # pylint: disable=protected-access
        xblock.runtime._services['user'] = NullUserService()
        xblock.runtime._services['user_state'] = UserStateService()
        xblock.runtime._services['teams'] = MockTeamsService(True)

        xblock.user_state_upload_data_enabled = Mock(return_value=True)
        xblock.is_team_assignment = Mock(return_value=True)

    @scenario("data/team_submission_file_scenario.xml", user_id='r5')
    def test_nothing(self, xblock):
        self.setup_xblock(xblock)
        with self.mock_get_url():
            learner_submission_data = xblock.get_learner_submission_data()
            data = PageDataSubmissionSerializer(learner_submission_data).data
        assert data == {
            'hasSubmitted': False,
            'hasCancelled': False,
            'hasRecievedGrade': False,
            'teamInfo': {
                'teamName': 'Red Squadron',
                'teamUsernames': ['Red Leader', 'Red Two', 'Red Five'],
                'previousTeamName': None,
                'hasSubmitted': False,
                'teamUploadedFiles': [],
            },
            'response': {
                'textResponses': ['', ''],
                'uploadedFiles': []
            },
        }

    @scenario("data/team_submission_file_scenario.xml", user_id='r5')
    def test_not_yet_submitted(self, xblock):
        self.setup_xblock(xblock)
        xblock.saved_response = json.dumps({'parts': [{'text': 'hello world'}, {'text': 'goodnight moon'}]})
        xblock.file_manager.append_uploads(
            {'description': 'my presentation', 'name': 'file1.ppt', 'size': 2},
            {'description': 'video of presentation', 'name': 'file3.mp4', 'size': 3},
        )
        student_item = xblock.get_student_item_dict()

        r1 = UserFactory()
        r2 = UserFactory()
        username_map = {
            str(r1.id): r1.username,
            str(r2.id): r2.username,
            'r5': 'Red Five'
        }
        xblock.get_username = Mock(side_effect=username_map.get)

        shared_file_kwargs = {
            'course_id': student_item['course_id'],
            'item_id': student_item['item_id'],
            'team_id': MOCK_TEAM_ID,
        }
        shared_file_1 = SharedFileUploadFactory.create(**{**shared_file_kwargs, 'owner_id': r1.id})
        shared_file_2 = SharedFileUploadFactory.create(**{**shared_file_kwargs, 'owner_id': r2.id})
        base_key = f'{student_item["student_id"]}/{student_item["course_id"]}/{student_item["item_id"]}'
        shared_file_1_key = f'{r1.id}/{student_item["course_id"]}/{student_item["item_id"]}'
        shared_file_2_key = f'{r2.id}/{student_item["course_id"]}/{student_item["item_id"]}'
        with self.mock_get_url({
            base_key: 'www.downloadfiles.xyz/0',
            base_key + '/1': 'www.downloadfiles.xyz/1',
            shared_file_1_key: 'www.downloadfiles.xyz/shared1',
            shared_file_2_key: 'www.downloadfiles.xyz/shared2',
        }):
            learner_submission_data = xblock.get_learner_submission_data()
            data = PageDataSubmissionSerializer(learner_submission_data).data
        assert data == {
            'hasSubmitted': False,
            'hasCancelled': False,
            'hasRecievedGrade': False,
            'teamInfo': {
                'teamName': 'Red Squadron',
                'teamUsernames': ['Red Leader', 'Red Two', 'Red Five'],
                'previousTeamName': None,
                'hasSubmitted': False,
                'teamUploadedFiles': [
                    {
                        'fileUrl': 'www.downloadfiles.xyz/shared1',
                        'fileName': shared_file_1.name,
                        'fileDescription': shared_file_1.description,
                        'fileSize': shared_file_1.size,
                        'uploadedBy': r1.username,
                    },
                    {
                        'fileUrl': 'www.downloadfiles.xyz/shared2',
                        'fileName': shared_file_2.name,
                        'fileDescription': shared_file_2.description,
                        'fileSize': shared_file_2.size,
                        'uploadedBy': r2.username,
                    },
                ],
            },
            'response': {
                'textResponses': ['hello world', 'goodnight moon'],
                'uploadedFiles': [
                    {
                        'fileUrl': 'www.downloadfiles.xyz/0',
                        'fileName': 'file1.ppt',
                        'fileDescription': 'my presentation',
                        'fileSize': 2,
                        'fileIndex': 0,
                    },
                    {
                        'fileUrl': 'www.downloadfiles.xyz/1',
                        'fileName': 'file3.mp4',
                        'fileDescription': 'video of presentation',
                        'fileSize': 3,
                        'fileIndex': 1,
                    },
                ]
            }
        }

    @scenario("data/team_submission_file_scenario.xml", user_id='r5')
    def test_submitted(self, xblock):
        self.setup_xblock(xblock)
        arbitrary_user = get_user_model().objects.create_user(username='someuser', password='asdfasdfasf')
        self._create_team_submission_and_workflow(
            'test_course',
            xblock.scope_ids.usage_id,
            MOCK_TEAM_ID,
            arbitrary_user.id,
            ['rl', 'r2', 'r5'],
            {
                'parts': [{'text': 'This is the answer'}],
                'file_keys': ['k1', 'k2', 'k3'],
                'files_names': ['1.txt', '2.txt', '3.txt'],
                'files_descriptions': ['1', '2', '3'],
                'files_sizes': [12, 1, 56]
            }
        )
        with self.mock_get_url():
            learner_submission_data = xblock.get_learner_submission_data()
            data = PageDataSubmissionSerializer(learner_submission_data).data
        assert data == {
            'hasSubmitted': True,
            'hasCancelled': False,
            'hasRecievedGrade': False,
            'teamInfo': {
                'teamName': 'Red Squadron',
                'teamUsernames': ['Red Leader', 'Red Two', 'Red Five'],
                'previousTeamName': None,
                'hasSubmitted': True,
            },
            'response': {
                'textResponses': ['This is the answer'],
                'uploadedFiles': [
                    {
                        'fileUrl': 'www.downloadfiles.xyz/k1',
                        'fileName': '1.txt',
                        'fileDescription': '1',
                        'fileSize': 12,
                        'fileIndex': 0,
                    },
                    {
                        'fileUrl': 'www.downloadfiles.xyz/k2',
                        'fileName': '2.txt',
                        'fileDescription': '2',
                        'fileSize': 1,
                        'fileIndex': 1,
                    },
                    {
                        'fileUrl': 'www.downloadfiles.xyz/k3',
                        'fileName': '3.txt',
                        'fileDescription': '3',
                        'fileSize': 56,
                        'fileIndex': 2,
                    },
                ]
            }
        }

    def _create_team_submission_and_workflow(
        self, course_id, item_id, team_id, submitter_id, team_member_student_ids, answer
    ):
        """ Create a team submission and team workflow with the given info """
        team_submission = submission_team_api.create_submission_for_team(
            course_id,
            item_id,
            team_id,
            submitter_id,
            team_member_student_ids,
            answer
        )
        team_workflow = team_workflow_api.create_workflow(team_submission['team_submission_uuid'])
        return team_submission, team_workflow


class SubmissionDraftTest(MFEHandlersTestBase):

    @contextmanager
    def _mock_save_submission_draft(self, **kwargs):
        with patch('openassessment.xblock.ui_mixins.mfe.mixin.submissions_actions') as mock_submission_actions:
            mock_submission_actions.save_submission_draft.configure_mock(**kwargs)
            yield mock_submission_actions.save_submission_draft

    @scenario("data/basic_scenario.xml")
    def test_incorrect_params(self, xblock):
        resp = self.request_save_draft(xblock, {})
        assert_error_response(resp, 400, ErrorCodes.INCORRECT_PARAMETERS)

    @scenario("data/basic_scenario.xml")
    def test_submission_validation_error(self, xblock):
        with self._mock_save_submission_draft(side_effect=SubmissionValidationException()):
            resp = self.request_save_draft(xblock)
        assert_error_response(resp, 400, ErrorCodes.INVALID_RESPONSE_SHAPE)

    @scenario("data/basic_scenario.xml")
    def test_draft_save_exception(self, xblock):
        with self._mock_save_submission_draft(side_effect=DraftSaveException()):
            resp = self.request_save_draft(xblock)
        assert_error_response(resp, 500, ErrorCodes.INTERNAL_EXCEPTION)

    @scenario("data/basic_scenario.xml")
    def test_draft_save(self, xblock):
        with self._mock_save_submission_draft() as mock_draft:
            resp = self.request_save_draft(xblock)
            assert resp.status_code == 200
            assert_called_once_with_helper(mock_draft, self.DEFAULT_DRAFT_VALUE['response']['text_responses'], 2)


class SubmissionCreateTest(MFEHandlersTestBase):

    @contextmanager
    def _mock_create_submission(self, **kwargs):
        with patch('openassessment.xblock.ui_mixins.mfe.mixin.submissions_actions') as mock_submission_actions:
            mock_submission_actions.submit.configure_mock(**kwargs)
            yield mock_submission_actions.submit

    @scenario("data/basic_scenario.xml")
    def test_incorrect_params(self, xblock):
        resp = self.request_create_submission(xblock, {})
        assert_error_response(resp, 400, ErrorCodes.INCORRECT_PARAMETERS)

    @scenario("data/basic_scenario.xml")
    def test_submission_validation_exception(self, xblock):
        err_msg = 'some error message'
        with self._mock_create_submission(side_effect=SubmissionValidationException(err_msg)):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, ErrorCodes.INVALID_RESPONSE_SHAPE, err_msg)

    @scenario("data/basic_scenario.xml")
    def test_in_studio_preview(self, xblock):
        with self._mock_create_submission(side_effect=StudioPreviewException()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, ErrorCodes.IN_STUDIO_PREVIEW)

    @scenario("data/basic_scenario.xml")
    def test_multiple_submissions(self, xblock):
        with self._mock_create_submission(side_effect=MultipleSubmissionsException()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, ErrorCodes.MULTIPLE_SUBMISSIONS)

    @scenario("data/basic_scenario.xml")
    def test_answer_too_long(self, xblock):
        with self._mock_create_submission(side_effect=AnswerTooLongException()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, ErrorCodes.SUBMISSION_TOO_LONG, {'maxsize': submission_api.Submission.MAXSIZE})

    @scenario("data/basic_scenario.xml")
    def test_submission_error(self, xblock):
        mock_error = submission_api.SubmissionRequestError(
            'there was a problem',
            {'answer': 'invalid format'},
        )
        with self._mock_create_submission(side_effect=mock_error):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, ErrorCodes.SUBMISSION_API_ERROR, str(mock_error))

    @scenario("data/basic_scenario.xml")
    def test_empty_submission(self, xblock):
        with self._mock_create_submission(side_effect=EmptySubmissionError()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, ErrorCodes.EMPTY_ANSWER)

    @scenario("data/basic_scenario.xml")
    def test_internal_error(self, xblock):
        with self._mock_create_submission(side_effect=SubmitInternalError()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 500, ErrorCodes.UNKNOWN_ERROR)

    @scenario("data/basic_scenario.xml")
    def test_create_submission(self, xblock):
        with self._mock_create_submission() as mock_submit:
            resp = self.request_create_submission(xblock)
            assert resp.status_code == 200
            assert_called_once_with_helper(mock_submit, self.DEFAULT_SUBMIT_VALUE, 3)
