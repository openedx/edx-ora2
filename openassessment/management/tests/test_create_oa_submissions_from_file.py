""" Tests for the create_oa_submissions_from_file management command """
from os.path import join
from contextlib import contextmanager
import tempfile
import json
from mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from submissions import api as sub_api

from openassessment.assessment.api import staff as staff_api
from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock
from openassessment.workflow import api as workflow_api
from openassessment.management.commands.create_oa_submissions_from_file import Command, SUPERUSER_USERNAME
from openassessment.tests.factories import UserFactory

USERNAME_1 = 'user1'
USERNAME_2 = 'user2'
STAFF_USER_1 = 'staffuser1'
STAFF_USER_2 = 'staffuser2'
COURSE_ID = 'course-v1:edX+Test1+1T2021'

DISPLAY_NAME_1 = 'ORA 1'

CRITERION_GRAMMAR = {
    'label': 'Grammar',
    'prompt': 'Grammar good or am grammar bad',
    'feedback': 'required',
    'options': [
        {
            'label': 'Bad',
            'points': 0,
            'explanation': 'Bad',
            'name': 'Bad',
            'order_num': 0
        },
        {
            'label': 'Good',
            'points': 1,
            'explanation': 'Good',
            'name': 'Good',
            'order_num': 1
        },
    ],
    'name': 'Grammar',
    'order_num': 0
}

MOCK_BLOCK_KWARGS = {
    'display_name': DISPLAY_NAME_1,
    'prompts': ['This is the prompt'],
    'rubric_criteria_with_labels': [CRITERION_GRAMMAR],
    'location': 'block-v1@testX+thistest+atest@openassessment-lkasjdflakdslsjfldfjlfajksf'
}

SUBMISSION_CONFIG_1 = {
    "username": USERNAME_1,
    "lockOwner": STAFF_USER_1,
    "gradeData": {
        "gradedBy": STAFF_USER_2,
        "overallFeedback": 'overallfeedback',
        "criteria": [
            {
                "label": CRITERION_GRAMMAR['label'],
                "selectedOption": CRITERION_GRAMMAR['options'][1]['label'],
                "feedback": 'it is good',
            },
        ]
    }
}


SUBMISSION_CONFIG_2 = {
    "username": USERNAME_2,
    'lockOwner': None,
    "gradeData": {}
}

CONFIG_1 = [{
    "displayName": DISPLAY_NAME_1,
    "submissions": [
        SUBMISSION_CONFIG_1,
        SUBMISSION_CONFIG_2,
    ]
}]


def anonymous_user_id(username):
    return username + "_anonymous_id"


def student_item(username, location):
    return {
        'student_id': anonymous_user_id(username),
        'course_id': COURSE_ID,
        'item_id': location,
        'item_type': 'openassessment'
    }


USERNAME_TO_ANONYMOUS_ID = {
    username: anonymous_user_id(username) for username in [
        USERNAME_1,
        USERNAME_2,
        STAFF_USER_1,
        STAFF_USER_2,
        SUPERUSER_USERNAME
    ]
}


class CreateSubmissionsFromFileTest(TestCase):
    """ Tests for create_oa_submissions_from_file """

    def setUp(self):
        super().setUp()
        self.cmd = Command()
        self.cmd.CONFIG_FILE_LOCATION_BASE = ''

        self.cmd.username_to_anonymous_user_id = USERNAME_TO_ANONYMOUS_ID
        self.mock_block = Mock(**MOCK_BLOCK_KWARGS)
        self.cmd.display_name_to_block = {DISPLAY_NAME_1: self.mock_block}

    def test_get_display_names__duplicate(self):
        """ Error behavior when a duplicate display name is provided """
        display_names = ['ora_A', 'ora_B', 'ora_B']
        config = [
            {'displayName': display_name, 'submissions': []} for display_name in display_names
        ]
        with self.assertRaisesMessage(CommandError, 'Duplicate ORA display name found in configuration file: ora_B'):
            self.cmd.get_display_names(config)

    @contextmanager
    def _test_config_file(self, content):
        """ Helper context handler to write and delete a temp file """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_file_path = join(tmpdir, 'submission_config.json')
            with open(tmp_file_path, 'w') as f:
                f.write(content)
            yield tmpdir, tmp_file_path

    def test_read_config_file(self):
        """ Test for reading a config file """
        with self._test_config_file(json.dumps(CONFIG_1)) as (_, tmp_file_path):
            read_config = self.cmd.read_config_file(tmp_file_path)
            assert read_config == CONFIG_1

    def test_read_config_file__not_found(self):
        """ Test for error behavior when test file cannot be found"""
        with self._test_config_file(json.dumps(CONFIG_1)) as (tmpdir, _):
            nonexistant_path = join(tmpdir, 'some_other_file.json')
            with self.assertRaisesMessage(CommandError, f'File {nonexistant_path} not found.'):
                self.cmd.read_config_file(nonexistant_path)

    def test_read_config_file__error(self):
        """ Test for error behavior when test file cannot be read successfuly """
        invalid_json = '{ this ] aint ( valid " json :( /'
        with self._test_config_file(invalid_json) as (_, config_path):
            with self.assertRaisesRegex(CommandError, f'Unable to parse file {config_path}'):
                self.cmd.read_config_file(config_path)

    def test_load_ora_blocks__multiple_blocks(self):
        """
        Test for error behavior when we attempt to look up a block
        in a course that multiple blocks with that display name
        """
        mock_blocks = [
            Mock(display_name='ORA A', location=1),
            Mock(display_name='ORA B', location=2),
            Mock(display_name='ORA A', location=3),
        ]
        expected_error_message = (
            "The ORA 'ORA A' is specified in the input file. "
            "The course contains more than one ORA with that display name. "
            "First two found:  [1, 3]"
        )
        with patch.object(self.cmd, '_load_ora_blocks_from_modulestore') as mock_modulestore:
            mock_modulestore.return_value = mock_blocks
            with self.assertRaisesMessage(CommandError, expected_error_message):
                self.cmd.load_ora_blocks(COURSE_ID, ['ORA A', 'ORA B'])

    def test_load_ora_blocks__missing(self):
        """
        Test for error behavior when we are unable to find a block of
        a given display name
        """
        mock_blocks = [
            Mock(display_name='ORA A', location=1),
            Mock(display_name='ORA B', location=2),
            Mock(display_name='ORA C', location=3),
        ]
        expected_error_message = f'The following Display Name(s) were not found in {COURSE_ID}'
        with patch.object(self.cmd, '_load_ora_blocks_from_modulestore') as mock_modulestore:
            mock_modulestore.return_value = mock_blocks
            with self.assertRaisesMessage(CommandError, expected_error_message) as err:
                self.cmd.load_ora_blocks(COURSE_ID, ['ORA A', 'ORA B', 'ORA F', 'ORA Z'])
            error_message = str(err.exception)
            assert 'ORA F' in error_message
            assert 'ORA Z' in error_message

    def test_load_anonymous_user_ids__missing(self):
        """ Test for when we are unable to find an anonymous_user_id for a username """

        def mock_anonymous_id_for_user(user, course_id):  # pylint: disable=unused-argument
            return user.username + "_anonymous"

        for username in [USERNAME_1, USERNAME_2, STAFF_USER_1, STAFF_USER_2, SUPERUSER_USERNAME]:
            UserFactory.create(username=username)

        expected_error = 'Unable to load anonymous id for user(s) user_not_found'
        with patch(
            'openassessment.management.commands.create_oa_submissions_from_file.anonymous_id_for_user',
            return_value=mock_anonymous_id_for_user
        ):
            with self.assertRaisesMessage(CommandError, expected_error):
                self.cmd.load_anonymous_user_ids(COURSE_ID, {USERNAME_1, USERNAME_2, 'user_not_found'})

    def test_init_ora_test_data(self):
        """ Test for behavior of the init step """
        mock_path = 'openassessment.management.commands.create_oa_submissions_from_file.call_command'
        with patch(mock_path) as mock_call_command:
            self.cmd.init_ora_test_data(COURSE_ID, CONFIG_1)

        def assert_create_test_users_call(call, users, course_staff):
            """ Helper to assert create_test_users was called with the expected (kw)arguments """
            assert call.args[0] == 'create_test_users'
            assert set(call.args[1:]) == users
            assert call.kwargs['course'] == COURSE_ID
            assert call.kwargs.get('course_staff', False) == course_staff

        assert mock_call_command.call_count == 2
        assert_create_test_users_call(mock_call_command.call_args_list[0], {USERNAME_1, USERNAME_2}, False)
        assert_create_test_users_call(mock_call_command.call_args_list[1], {STAFF_USER_1, STAFF_USER_2}, True)

    def test_submit_ora_test_data(self):
        """ Test for behavior of the submit step """
        self.cmd.submit_ora_test_data(COURSE_ID, CONFIG_1)

        # User 1 should have a submission, their workflow should be 'done', they should have a staff grade
        # and they should be locked.
        user_1_submission = sub_api.get_submissions(student_item(USERNAME_1, self.mock_block.location))[0]
        user_1_workflow = workflow_api.get_workflow_for_submission(user_1_submission['uuid'], None, {})
        assert user_1_workflow['status'] == 'done'
        user_1_assessment = staff_api.get_latest_staff_assessment(user_1_submission['uuid'])
        assert user_1_assessment['points_earned'] == 1
        assert user_1_assessment['scorer_id'] == anonymous_user_id(STAFF_USER_2)
        assert user_1_assessment['feedback'] == SUBMISSION_CONFIG_1['gradeData']['overallFeedback']
        user_1_lock_owner = SubmissionGradingLock.get_submission_lock(user_1_submission['uuid']).owner_id
        assert user_1_lock_owner == anonymous_user_id(STAFF_USER_1)

        # User 2 should have a submission, their workflow should be 'waiting', they should not have a
        # staff grade and they should not be locked
        user_2_submission = sub_api.get_submissions(student_item(USERNAME_2, self.mock_block.location))[0]
        user_2_workflow = workflow_api.get_workflow_for_submission(user_2_submission['uuid'], None, {})
        assert user_2_workflow['status'] == 'waiting'
        user_2_assessment = staff_api.get_latest_staff_assessment(user_2_submission['uuid'])
        assert user_2_assessment is None
        assert SubmissionGradingLock.get_submission_lock(user_2_submission['uuid']) is None

    def test_reset_ora_test_data(self):
        """ Test for behavior of the reset step"""
        self.cmd.reset_ora_test_data(COURSE_ID, CONFIG_1)
        assert self.mock_block.clear_student_state.call_count == 2

        for reset_user in [USERNAME_1, USERNAME_2]:
            self.mock_block.clear_student_state.assert_any_call(
                anonymous_user_id(reset_user),
                COURSE_ID,
                str(self.mock_block.location),
                anonymous_user_id(SUPERUSER_USERNAME)
            )


class CreateSubmissionsFromFileCallCommandTest(TestCase):

    def setUp(self):
        super().setUp()
        for username in [USERNAME_1, USERNAME_2, STAFF_USER_1, STAFF_USER_2, SUPERUSER_USERNAME]:
            UserFactory.create(username=username)

        self.mock_block = Mock(**MOCK_BLOCK_KWARGS)

        def mock_anonymous_id_for_user(user, course_id):  # pylint: disable=unused-argument
            return anonymous_user_id(user.username)

        read_config_patcher = patch.object(
            Command,
            'read_config_file',
            return_value=CONFIG_1
        )
        anonymous_id_for_user_patcher = patch(
            'openassessment.management.commands.create_oa_submissions_from_file.anonymous_id_for_user',
            side_effect=mock_anonymous_id_for_user
        )
        self.mock_store = Mock()
        self.mock_store.get_items.return_value = [self.mock_block]
        modulestore_patcher = patch(
            'openassessment.management.commands.create_oa_submissions_from_file.modulestore',
            return_value=self.mock_store
        )
        call_command_patcher = patch(
            'openassessment.management.commands.create_oa_submissions_from_file.call_command'
        )
        self.patchers = [
            read_config_patcher,
            anonymous_id_for_user_patcher,
            modulestore_patcher,
            call_command_patcher
        ]
        self.read_config_mock = read_config_patcher.start()
        self.anonymous_id_for_user_mock = anonymous_id_for_user_patcher.start()
        self.modulestore_mock = modulestore_patcher.start()
        self.call_command_mock = call_command_patcher.start()

    def tearDown(self):
        super().tearDown()
        for patcher in self.patchers:
            patcher.stop()

    def test_init(self):
        call_command('create_oa_submissions_from_file', COURSE_ID, 'filepath', '--init')
        self.assert_init_called()
        self.assert_submission_created(USERNAME_1, STAFF_USER_2, STAFF_USER_1)
        self.assert_submission_created(USERNAME_2, None, None)

    def test_submit(self):
        call_command('create_oa_submissions_from_file', COURSE_ID, 'filepath', '--submit')
        self.assert_submission_created(USERNAME_1, STAFF_USER_2, STAFF_USER_1)
        self.assert_submission_created(USERNAME_2, None, None)

    def test_reset(self):
        call_command('create_oa_submissions_from_file', COURSE_ID, 'filepath', '--reset')
        self.assert_reset_called(2)

    def assert_init_called(self):
        assert self.call_command_mock.call_count == 2
        assert self.call_command_mock.call_args_list[0].args[0] == 'create_test_users'
        assert self.call_command_mock.call_args_list[1].args[0] == 'create_test_users'

    def assert_submission_created(self, user, expected_graded_by, expected_locked_by):
        submission = sub_api.get_submissions(student_item(user, self.mock_block.location))[0]
        workflow = workflow_api.get_workflow_for_submission(submission['uuid'], None, {})
        assessment = staff_api.get_latest_staff_assessment(submission['uuid'])
        lock = SubmissionGradingLock.get_submission_lock(submission['uuid'])

        if expected_graded_by:
            assert workflow['status'] == 'done'
            assert assessment['scorer_id'] == anonymous_user_id(expected_graded_by)
        else:
            assert workflow['status'] == 'waiting'
            assert assessment is None

        if expected_locked_by:
            assert lock is not None
            assert lock.owner_id == anonymous_user_id(STAFF_USER_1)

    def assert_reset_called(self, expected_calls):
        assert self.mock_block.clear_student_state.call_count == expected_calls
