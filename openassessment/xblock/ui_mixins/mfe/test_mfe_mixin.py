"""
Tests for XBlock handlers for the ORA MFE BFF
"""
from collections import namedtuple
from contextlib import contextmanager
import copy
import json
from unittest.mock import Mock, PropertyMock, patch

import ddt
from django.contrib.auth import get_user_model
from mock import MagicMock
from submissions import api as submission_api
from submissions import team_api as submission_team_api

from openassessment.assessment.errors.base import AssessmentError
from openassessment.xblock.apis.assessments.peer_assessment_api import PeerAssessmentAPI
from openassessment.xblock.apis.workflow_api import WorkflowAPI
from openassessment.fileupload.api import FileUpload
from openassessment.fileupload.exceptions import FileUploadError
from openassessment.tests.factories import SharedFileUploadFactory, UserFactory
from openassessment.workflow import api as workflow_api
from openassessment.workflow import team_api as team_workflow_api
from openassessment.xblock.apis.submissions.errors import (
    AnswerTooLongException,
    DeleteNotAllowed,
    DraftSaveException,
    EmptySubmissionError,
    MultipleSubmissionsException,
    OnlyOneFileAllowedException,
    StudioPreviewException,
    SubmissionValidationException,
    SubmitInternalError,
    UnsupportedFileTypeException
)
from openassessment.xblock.apis.submissions.file_api import FileAPI
from openassessment.xblock.test.base import SubmissionTestMixin, XBlockHandlerTestCase, scenario
from openassessment.xblock.test.test_staff_area import NullUserService, UserStateService
from openassessment.xblock.test.test_submission import COURSE_ID, setup_mock_team
from openassessment.xblock.test.test_team import MOCK_TEAM_ID, MockTeamsService
from openassessment.xblock.ui_mixins.mfe.mixin import MFE_STEP_TO_WORKFLOW_MAPPINGS
from openassessment.xblock.ui_mixins.mfe.constants import error_codes, handler_suffixes
from openassessment.xblock.ui_mixins.mfe.submission_serializers import DraftResponseSerializer, SubmissionSerializer


class MockSerializer(MagicMock):
    """ Hack to get JSON-serializable response from serializer """

    @property
    def data(self):
        return {}


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

    DEFAULT_DRAFT_VALUE = {'response': {'textResponses': ['hi']}}
    DEFAULT_SUBMIT_VALUE = {'submission': {'textResponses': ['Hello World', 'Goodbye World']}}
    DEFAULT_DELETE_FILE_VALUE = {'fileIndex': 1}

    DEFAULT_ASSESSMENT_SUBMIT_VALUE = {
        "criteria": [
            {
                "selectedOption": 2,
                "feedback": "rawr!",
            },
            {
                "selectedOption": 0,
                "feedback": ":)",
            },
            {
                "selectedOption": 1,
                "feedback": "i prefer lead",
            }
        ],
        "overallFeedback": "i have no strong feelings",
    }

    def request_create_submission(self, xblock, payload=None):
        if payload is None:
            payload = self.DEFAULT_SUBMIT_VALUE
        return super().request(
            xblock,
            'submission',
            json.dumps(payload),
            suffix=handler_suffixes.SUBMISSION_SUBMIT,
            response_format='response'
        )

    def request_get_learner_data(self, xblock, suffix=None):
        return super().request(
            xblock,
            'get_learner_data',
            "{}",
            request_method="POST",
            response_format='response',
            suffix=suffix,
        )

    def request_save_draft(self, xblock, payload=None):
        if payload is None:
            payload = self.DEFAULT_DRAFT_VALUE
        return super().request(
            xblock,
            'submission',
            json.dumps(payload),
            suffix=handler_suffixes.SUBMISSION_DRAFT,
            response_format='response'
        )

    def request_upload_files(self, xblock, payload):
        return super().request(
            xblock,
            'file',
            json.dumps(payload),
            suffix=handler_suffixes.FILE_ADD,
            response_format='response'
        )

    def request_delete_file(self, xblock, payload=None):
        if payload is None:
            payload = self.DEFAULT_DELETE_FILE_VALUE
        return super().request(
            xblock,
            'file',
            json.dumps(payload),
            suffix=handler_suffixes.FILE_DELETE,
            response_format='response'
        )

    def request_file_callback(self, xblock, payload):
        return super().request(
            xblock,
            'file',
            json.dumps(payload),
            suffix=handler_suffixes.FILE_UPLOAD_CALLBACK,
            response_format='response'
        )

    def request_assessment_submit(self, xblock, step=None, payload=None):
        if payload is None:
            payload = self.DEFAULT_ASSESSMENT_SUBMIT_VALUE
        if step is not None:
            payload['step'] = step
        return super().request(
            xblock,
            'assessment',
            json.dumps(payload),
            suffix=handler_suffixes.ASSESSMENT_SUBMIT,
            response_format='response'
        )


def assert_error_response(response, status_code, error_code, context=''):
    assert response.status_code == status_code
    assert response.json['error'] == {
        'errorCode': error_code,
        'errorContext': context
    }


def create_student_and_submission(student, course, item, answer, xblock=None):
    """ Creates a student and submission for tests. """
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


@ddt.ddt
class GetLearnerDataRoutingTest(MFEHandlersTestBase, SubmissionTestMixin):
    """ Tests for routing / validation on get_learner_data """

    @patch("openassessment.xblock.ui_mixins.mfe.mixin.PageDataSerializer")
    @scenario("data/basic_scenario.xml")
    def test_no_requested_step(self, xblock, mock_serializer):
        # Given we don't pass an active step
        mock_serializer.return_value = MockSerializer()

        # When I ask for learner data
        _ = self.request_get_learner_data(xblock)

        # Then I call serialization without an active step
        expected_context = {
            "requested_step": None,
            "current_workflow_step": "submission",
        }
        mock_serializer.assert_called_once_with(xblock, context={**expected_context})

    @patch("openassessment.xblock.ui_mixins.mfe.mixin.PageDataSerializer")
    @scenario("data/basic_scenario.xml")
    def test_start_submission(self, xblock, mock_serializer):
        # Given we haven't started a submission
        mock_serializer.return_value = MockSerializer()

        # When I ask for learner data
        _ = self.request_get_learner_data(xblock, suffix="submission")

        # Then I get submission
        expected_context = {
            "requested_step": "submission",
            "current_workflow_step": "submission",
        }
        mock_serializer.assert_called_once_with(xblock, context={**expected_context})

    @patch("openassessment.xblock.ui_mixins.mfe.mixin.PageDataSerializer")
    @scenario("data/basic_scenario.xml")
    def test_bad_jump_step(self, xblock, mock_serializer):
        # Given any state
        mock_serializer.return_value = MockSerializer()

        # When I try to jump to a bad step
        response = self.request_get_learner_data(xblock, suffix="asdf")

        # Then I get an error and don't return data
        mock_serializer.assert_not_called()

        expected_context = "Invalid step name: asdf"
        assert_error_response(response, 400, error_codes.INCORRECT_PARAMETERS, context=expected_context)

    @ddt.data("peer", "done")
    @patch("openassessment.xblock.ui_mixins.mfe.mixin.PageDataSerializer")
    @scenario("data/basic_scenario.xml")
    def test_jump_to_inaccessible_step(self, xblock, inaccessible_step, mock_serializer):
        # Given I'm on an early step
        mock_serializer.return_value = MockSerializer()

        # When I try to jump to a step I can't access
        response = self.request_get_learner_data(xblock, suffix=inaccessible_step)

        # Then I get an error and don't return data
        mock_serializer.assert_not_called()

        expected_status = 400
        self.assertEqual(expected_status, response.status_code)

        expected_body = {
            'error': {
                'errorCode': 'ERR_INACCESSIBLE_STEP',
                'errorContext': f'Inaccessible step: {inaccessible_step}'
            }
        }
        self.assertDictEqual(expected_body, json.loads(response.body))

    @patch("openassessment.xblock.ui_mixins.mfe.mixin.PageDataSerializer")
    @scenario("data/basic_scenario.xml", user_id="Alice")
    def test_assessment_step(self, xblock, mock_serializer):
        # Given I've completed my submission
        self.create_test_submission(xblock)
        mock_serializer.return_value = MockSerializer()

        # When I try to load my data
        _ = self.request_get_learner_data(xblock, suffix=None)

        # Then I am routed to the correct assessment step
        expected_context = {
            "requested_step": None,
            "current_workflow_step": "self",
        }
        mock_serializer.assert_called_once_with(xblock, context={**expected_context})

    @patch("openassessment.xblock.ui_mixins.mfe.mixin.PageDataSerializer")
    @scenario("data/basic_scenario.xml", user_id="Alice")
    def test_jump_back_to_submission_step(self, xblock, mock_serializer):
        # Given I've completed my submission
        # xblock.get_student_item
        self.create_test_submission(xblock)
        mock_serializer.return_value = MockSerializer()

        # When I try to jump back to submission
        _ = self.request_get_learner_data(xblock, suffix="submission")

        # Then I am routed to the correct view
        expected_context = {
            "requested_step": "submission",
            "current_workflow_step": "self",
        }
        mock_serializer.assert_called_once_with(xblock, context={**expected_context})


class GetLearnerSubmissionDataIndividualSubmissionTest(MFEHandlersTestBase):

    maxDiff = None

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
            data = DraftResponseSerializer(learner_submission_data).data
        assert data == {
            'textResponses': ['', ''],
            'uploadedFiles': [],
            'teamUploadedFiles': [],
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
            data = DraftResponseSerializer(learner_submission_data).data
        assert data == {
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
            ],
            'teamUploadedFiles': [],
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
            data = SubmissionSerializer(learner_submission_data).data
        assert data == {
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
            ],
            'teamUploadedFiles': None,
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
            data = DraftResponseSerializer(learner_submission_data).data
        assert data == {
            'textResponses': ['', ''],
            'uploadedFiles': [],
            'teamUploadedFiles': [],
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
            data = DraftResponseSerializer(learner_submission_data).data
        assert data == {
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
            ],
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
            data = SubmissionSerializer(learner_submission_data).data
        assert data == {
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
            ],
            'teamUploadedFiles': None,
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
        assert_error_response(resp, 400, error_codes.INCORRECT_PARAMETERS)

    @scenario("data/basic_scenario.xml")
    def test_submission_validation_error(self, xblock):
        with self._mock_save_submission_draft(side_effect=SubmissionValidationException()):
            resp = self.request_save_draft(xblock)
        assert_error_response(resp, 400, error_codes.INVALID_RESPONSE_SHAPE)

    @scenario("data/basic_scenario.xml")
    def test_draft_save_exception(self, xblock):
        with self._mock_save_submission_draft(side_effect=DraftSaveException()):
            resp = self.request_save_draft(xblock)
        assert_error_response(resp, 500, error_codes.INTERNAL_EXCEPTION)

    @scenario("data/basic_scenario.xml")
    def test_draft_save(self, xblock):
        with self._mock_save_submission_draft() as mock_draft:
            resp = self.request_save_draft(xblock)
            assert resp.status_code == 200
            assert_called_once_with_helper(mock_draft, self.DEFAULT_DRAFT_VALUE['response']['textResponses'], 2)


class SubmissionCreateTest(MFEHandlersTestBase):

    @contextmanager
    def _mock_create_submission(self, **kwargs):
        with patch('openassessment.xblock.ui_mixins.mfe.mixin.submissions_actions') as mock_submission_actions:
            mock_submission_actions.submit.configure_mock(**kwargs)
            yield mock_submission_actions.submit

    @scenario("data/basic_scenario.xml")
    def test_incorrect_params(self, xblock):
        resp = self.request_create_submission(xblock, {})
        assert_error_response(resp, 400, error_codes.INCORRECT_PARAMETERS)

    @scenario("data/basic_scenario.xml")
    def test_submission_validation_exception(self, xblock):
        err_msg = 'some error message'
        with self._mock_create_submission(side_effect=SubmissionValidationException(err_msg)):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, error_codes.INVALID_RESPONSE_SHAPE, err_msg)

    @scenario("data/basic_scenario.xml")
    def test_in_studio_preview(self, xblock):
        with self._mock_create_submission(side_effect=StudioPreviewException()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, error_codes.IN_STUDIO_PREVIEW)

    @scenario("data/basic_scenario.xml")
    def test_multiple_submissions(self, xblock):
        with self._mock_create_submission(side_effect=MultipleSubmissionsException()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, error_codes.MULTIPLE_SUBMISSIONS)

    @scenario("data/basic_scenario.xml")
    def test_answer_too_long(self, xblock):
        with self._mock_create_submission(side_effect=AnswerTooLongException()):
            resp = self.request_create_submission(xblock)
        assert_error_response(
            resp,
            400,
            error_codes.SUBMISSION_TOO_LONG,
            {'maxsize': submission_api.Submission.MAXSIZE}
        )

    @scenario("data/basic_scenario.xml")
    def test_submission_error(self, xblock):
        mock_error = submission_api.SubmissionRequestError(
            'there was a problem',
            {'answer': 'invalid format'},
        )
        with self._mock_create_submission(side_effect=mock_error):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, error_codes.SUBMISSION_API_ERROR, str(mock_error))

    @scenario("data/basic_scenario.xml")
    def test_empty_submission(self, xblock):
        with self._mock_create_submission(side_effect=EmptySubmissionError()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 400, error_codes.EMPTY_ANSWER)

    @scenario("data/basic_scenario.xml")
    def test_internal_error(self, xblock):
        with self._mock_create_submission(side_effect=SubmitInternalError()):
            resp = self.request_create_submission(xblock)
        assert_error_response(resp, 500, error_codes.UNKNOWN_ERROR)

    @scenario("data/basic_scenario.xml")
    def test_create_submission(self, xblock):
        with self._mock_create_submission() as mock_submit:
            resp = self.request_create_submission(xblock)
            assert resp.status_code == 200
            assert_called_once_with_helper(mock_submit, self.DEFAULT_SUBMIT_VALUE["submission"]["textResponses"], 3)

    @patch("openassessment.xblock.ui_mixins.mfe.mixin.MfeMixin.is_step_open")
    @scenario("data/basic_scenario.xml")
    def test_blocks_submit_when_step_closed(self, xblock, mock_is_step_open):
        mock_is_step_open.return_value = False
        with self._mock_create_submission():
            resp = self.request_create_submission(xblock)
            assert_error_response(resp, 400, error_codes.INACCESSIBLE_STEP)


@ddt.ddt
class FileUploadTest(MFEHandlersTestBase):
    VALID_FILE_UPLOAD_PAYLOAD = {
        'fileDescription': 'd1',
        'fileName': 'n1',
        'fileSize': 100,
        'contentType': 'text/csv',
    }
    VALID_FILE_UPLOAD_OBJ = FileUpload(
        name=VALID_FILE_UPLOAD_PAYLOAD['fileName'],
        description=VALID_FILE_UPLOAD_PAYLOAD['fileDescription'],
        size=VALID_FILE_UPLOAD_PAYLOAD['fileSize'],
        index=5,
        student_id='student-1234132',
        course_id='course-v1:edX+Demo+asdfasdf',
        item_id='item4',
    )

    @contextmanager
    def _mock_submissions_actions(self, **kwargs):
        with patch(
            'openassessment.xblock.ui_mixins.mfe.mixin.submissions_actions',
            **kwargs
        ) as mock_submission_actions:
            yield mock_submission_actions

    @contextmanager
    def _mock_delete_uploaded_file(self, **kwargs):
        with patch.object(FileAPI, 'delete_uploaded_file', **kwargs) as mock_delete_file:
            yield mock_delete_file

    @ddt.data(
        {},
        ["one", "two"],
        {'fileDescription': 'only description'},
        {
            'fileDescription': 'd1',
            'fileName': 'n1',
            'fileSize': 'safsdfasd',
            'contentType': 'text',
        },
        {
            'fileDescription': 'd1',
            'fileName': 'n1',
            'fileSize': -1,
            'contentType': 'text',
        },
    )
    @scenario("data/basic_scenario.xml")
    def test_bad_inputs(self, xblock, payload):
        resp = self.request_upload_files(xblock, payload)
        assert resp.status_code == 400
        assert resp.json['error']['errorCode'] == error_codes.INCORRECT_PARAMETERS

    @scenario("data/basic_scenario.xml")
    def test_file_upload_error(self, xblock):
        error = FileUploadError('oh no!!!!')
        with self._mock_submissions_actions(**{'append_file_data.side_effect': error}):
            resp = self.request_upload_files(xblock, self.VALID_FILE_UPLOAD_PAYLOAD)
        assert_error_response(resp, 500, error_codes.INTERNAL_EXCEPTION, str(error))

    @scenario("data/basic_scenario.xml")
    def test_file_not_added_error(self, xblock):
        with self._mock_submissions_actions(**{'append_file_data.return_value': []}):
            resp = self.request_upload_files(xblock, self.VALID_FILE_UPLOAD_PAYLOAD)
        assert_error_response(resp, 500, error_codes.INTERNAL_EXCEPTION)

    @scenario("data/basic_scenario.xml")
    @ddt.data(
        ({'get_upload_url.return_value': None}, 500, error_codes.UNABLE_TO_GENERATE_UPLOAD_URL),
        ({'get_upload_url.side_effect': OnlyOneFileAllowedException()}, 400, error_codes.TOO_MANY_UPLOADS),
        (
            {'get_upload_url.side_effect': UnsupportedFileTypeException('.exe')},
            400,
            error_codes.UNSUPPORTED_FILETYPE,
            '.exe'
        ),
        ({'get_upload_url.side_effect': FileUploadError(':(')}, 500, error_codes.UNABLE_TO_GENERATE_UPLOAD_URL, ':('),
    )
    @ddt.unpack
    def test_upload_url_error(
        self,
        xblock,
        mock_url_behavior,
        expected_status,
        expected_code,
        expected_context=''
    ):
        """
        Test that raising certain errors in the Upload URL Generation code will
        result in returning the expected error code
        """
        mock_args = {
            **mock_url_behavior,
            'append_file_data.return_value': [self.VALID_FILE_UPLOAD_OBJ],
        }
        with self._mock_submissions_actions(**mock_args):
            with self._mock_delete_uploaded_file() as mock_delete_file:
                resp = self.request_upload_files(xblock, self.VALID_FILE_UPLOAD_PAYLOAD)
        assert_error_response(resp, expected_status, expected_code, expected_context)
        mock_delete_file.assert_called_once_with(self.VALID_FILE_UPLOAD_OBJ.index)

    @ddt.data(False, True)
    @scenario("data/basic_scenario.xml")
    def test_upload_files(self, xblock, blank_content_type):
        """ Test for file upload happy path"""
        url = 'www.someurl.xyz/fileUpload'
        mock_args = {
            'get_upload_url.return_value': url,
            'append_file_data.return_value': [self.VALID_FILE_UPLOAD_OBJ],
        }

        payload = copy.deepcopy(self.VALID_FILE_UPLOAD_PAYLOAD)
        if blank_content_type:
            payload['contentType'] = ''

        with self._mock_submissions_actions(**mock_args):
            resp = self.request_upload_files(xblock, payload)
        assert resp.status_code == 200
        assert resp.json == {
            'fileUrl': url,
            'fileIndex': self.VALID_FILE_UPLOAD_OBJ.index,
        }


@ddt.ddt
class FileDeleteTest(MFEHandlersTestBase):

    @contextmanager
    def _mock_remove_uploaded_file(self, **kwargs):
        with patch('openassessment.xblock.ui_mixins.mfe.mixin.submissions_actions') as mock_submission_actions:
            mock_submission_actions.remove_uploaded_file.configure_mock(**kwargs)
            yield mock_submission_actions.remove_uploaded_file

    @ddt.data({}, {'fileIndex': 'hello'})
    @scenario("data/basic_scenario.xml")
    def test_invalid_parameters(self, xblock, payload):
        resp = self.request_delete_file(xblock, payload)
        assert_error_response(resp, 400, error_codes.INCORRECT_PARAMETERS)

    @scenario("data/basic_scenario.xml")
    def test_cannot_delete_file(self, xblock):
        with self._mock_remove_uploaded_file(side_effect=DeleteNotAllowed()):
            resp = self.request_delete_file(xblock)
        assert_error_response(resp, 400, error_codes.DELETE_NOT_ALLOWED)

    @scenario("data/basic_scenario.xml")
    def test_file_upload_error(self, xblock):
        error = FileUploadError('oh no!!!!')
        with self._mock_remove_uploaded_file(side_effect=error):
            resp = self.request_delete_file(xblock)
        assert_error_response(resp, 500, error_codes.INTERNAL_EXCEPTION, str(error))

    @scenario("data/basic_scenario.xml")
    def test_delete_file(self, xblock):
        with self._mock_remove_uploaded_file() as mock_remove_file:
            resp = self.request_delete_file(xblock)
        assert resp.status_code == 200
        assert_called_once_with_helper(mock_remove_file, 1, 2)


@ddt.ddt
class FileCallbackTests(MFEHandlersTestBase):

    @contextmanager
    def _mock_delete_uploaded_file(self):
        with patch.object(FileAPI, 'delete_uploaded_file') as mock_delete_file:
            yield mock_delete_file

    @contextmanager
    def _mock_get_download_url(self, **kwargs):
        with patch.object(FileAPI, 'get_download_url', **kwargs) as mock_get_url:
            yield mock_get_url

    @ddt.data(
        {},
        {'fileIndex': 1},
        {'success': False},
        {
            'success': True,
            'fileIndex': -30
        }
    )
    @scenario("data/basic_scenario.xml")
    def test_bad_params(self, xblock, payload):
        resp = self.request_file_callback(xblock, payload)
        assert resp.status_code == 400
        assert resp.json['error']['errorCode'] == error_codes.INCORRECT_PARAMETERS

    @scenario("data/basic_scenario.xml")
    def test_success(self, xblock):
        test_url = 'www.xyz-123/file123423452'
        with self._mock_get_download_url(return_value=test_url):
            with self._mock_delete_uploaded_file() as mock_delete_file:
                resp = self.request_file_callback(xblock, {'success': True, 'fileIndex': 1})
        assert resp.status_code == 200
        assert resp.json == {'downloadUrl': test_url}
        mock_delete_file.assert_not_called()

    @scenario("data/basic_scenario.xml")
    def test_success_file_not_found(self, xblock):
        with self._mock_get_download_url(return_value=None):
            with self._mock_delete_uploaded_file() as mock_delete_file:
                resp = self.request_file_callback(xblock, {'success': True, 'fileIndex': 6})
        assert_error_response(resp, 404, error_codes.FILE_NOT_FOUND)
        mock_delete_file.assert_called_once_with(6)

    @scenario("data/basic_scenario.xml")
    def test_faliure(self, xblock):
        with self._mock_get_download_url() as mock_get_download_url:
            with self._mock_delete_uploaded_file() as mock_delete_file:
                resp = self.request_file_callback(xblock, {'success': False, 'fileIndex': 4})
        assert resp.status_code == 200
        mock_get_download_url.assert_not_called()
        mock_delete_file.assert_called_once_with(4)


AssessMocks = namedtuple('AssessMocks', ['self', 'training', 'peer'])


@ddt.ddt
class AssessmentSubmitTest(MFEHandlersTestBase):

    STATUSES = ['cancelled', 'done', 'waiting', 'self', 'training', 'peer']

    @contextmanager
    def mock_workflow_status(self, return_value):
        with patch.object(WorkflowAPI, 'status', new_callable=PropertyMock) as m:
            m.return_value = return_value
            yield m

    @contextmanager
    def mock_continue_grading(self, return_value):
        with patch.object(PeerAssessmentAPI, 'continue_grading', new_callable=PropertyMock) as m:
            m.return_value = return_value
            yield m

    @contextmanager
    def mock_assess_functions(self, self_kwargs=None, training_kwargs=None, peer_kwargs=None):
        self_kwargs = self_kwargs or {}
        training_kwargs = training_kwargs or {'return_value': None}
        peer_kwargs = peer_kwargs or {}

        base_path = 'openassessment.xblock.ui_mixins.mfe.mixin.'
        with patch(base_path + 'self_assess', **self_kwargs) as mock_self:
            with patch(base_path + 'training_assess', **training_kwargs) as mock_training:
                with patch(base_path + 'peer_assess', **peer_kwargs) as mock_peer:
                    yield AssessMocks(mock_self, mock_training, mock_peer)

    @ddt.data(
        {},
        {
            'criterionFeedback': {},
            'overallFeedback': '',
            'step': 'peer'
        },
        {
            'optionsSelected': ['this is a list'],
            'criterionFeedback': 67,
            'overallFeedback': '',
        }
    )
    @scenario("data/basic_scenario.xml")
    def test_incorrect_params(self, xblock, payload):
        resp = self.request_assessment_submit(xblock, payload)
        assert resp.status_code == 400
        assert resp.json['error']['errorCode'] == error_codes.INCORRECT_PARAMETERS

    @ddt.data("self", "peer", "studentTraining")
    @scenario("data/basic_scenario.xml")
    def test_not_allowed_to_assess_when_cancelled(self, xblock, step):
        with self.mock_workflow_status("cancelled"):
            resp = self.request_assessment_submit(xblock, step=step)
        assert resp.status_code == 400
        assert resp.json['error']['errorCode'] == error_codes.INVALID_STATE_TO_ASSESS

    @ddt.unpack
    @ddt.data(
        ('self', True, False, False),
        ('studentTraining', False, True, False),
        ('peer', False, False, True)
    )
    @scenario("data/basic_scenario.xml")
    def test_assess(self, xblock, mfe_step, expect_self, expect_training, expect_peer):
        workflow_step = MFE_STEP_TO_WORKFLOW_MAPPINGS[mfe_step]
        with self.mock_workflow_status(workflow_step):
            with self.mock_assess_functions() as assess_mocks:
                resp = self.request_assessment_submit(xblock, step=mfe_step)
        assert resp.status_code == 200
        assert assess_mocks.self.called == expect_self
        assert assess_mocks.training.called == expect_training
        assert assess_mocks.peer.called == expect_peer

    @ddt.data(None, 'waiting', 'self', 'training', 'done')
    @scenario("data/basic_scenario.xml")
    def test_peer_assess_when_not_in_peer(self, xblock, step):
        with self.mock_assess_functions() as assess_mocks:
            with self.mock_workflow_status(step):
                resp = self.request_assessment_submit(xblock, step="peer")

        assert resp.status_code == 200
        assess_mocks.self.assert_not_called()
        assess_mocks.training.assert_not_called()
        assess_mocks.peer.assert_called()

    @ddt.data('self', 'studentTraining', 'peer')
    @scenario("data/basic_scenario.xml")
    def test_assess_error(self, xblock, mfe_step):
        error = AssessmentError("there was a problem")
        workflow_step = MFE_STEP_TO_WORKFLOW_MAPPINGS[mfe_step]
        with self.mock_workflow_status(workflow_step):
            with self.mock_assess_functions(**{workflow_step + '_kwargs': {'side_effect': error}}):
                resp = self.request_assessment_submit(xblock, step=mfe_step)
        assert_error_response(resp, 500, error_codes.INTERNAL_EXCEPTION, str(error))

    @scenario("data/basic_scenario.xml")
    def test_cant_submit_when_cancelled(self, xblock):
        with self.mock_workflow_status('cancelled'):
            resp = self.request_assessment_submit(xblock, step="peer")
        assert resp.status_code == 400
        assert resp.json['error']['errorCode'] == error_codes.INVALID_STATE_TO_ASSESS

    @scenario("data/basic_scenario.xml")
    def test_training_assess_corrections(self, xblock):
        corrections = {'ferocity': 'sublime', 'element': 'hydrogen'}
        with self.mock_workflow_status('training'):
            with self.mock_assess_functions(training_kwargs={'return_value': corrections}):
                resp = self.request_assessment_submit(xblock, step='studentTraining')

        assert_error_response(resp, 400, error_codes.TRAINING_ANSWER_INCORRECT, corrections)

    @patch("openassessment.xblock.ui_mixins.mfe.mixin.MfeMixin.is_step_open")
    @ddt.data('self', 'studentTraining', 'peer')
    @scenario("data/basic_scenario.xml")
    def test_blocks_assess_when_step_closed(self, xblock, mfe_step, mock_is_step_open):
        mock_is_step_open.return_value = False
        with self.mock_assess_functions() as assess_mocks:
            with self.mock_workflow_status(mfe_step):
                resp = self.request_assessment_submit(xblock, step=mfe_step)

        assert_error_response(resp, 400, error_codes.INACCESSIBLE_STEP, f"Inaccessible step: {mfe_step}")
        assess_mocks.self.assert_not_called()
        assess_mocks.training.assert_not_called()
        assess_mocks.peer.assert_not_called()
