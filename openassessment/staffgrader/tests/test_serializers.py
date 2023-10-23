"""
Tests for serializers used in staff grading
"""
from contextlib import contextmanager, ExitStack
from datetime import datetime, timedelta, timezone
from typing import OrderedDict
from uuid import uuid4

import ddt
from django.test.testcases import TestCase
from freezegun import freeze_time
from mock import Mock, patch

from openassessment.staffgrader.serializers.submission_list import (
    MissingContextException, SubmissionListSerializer, SubmissionListScoreSerializer, TeamSubmissionListSerializer
)
from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock
from openassessment.staffgrader.serializers.submission_lock import SubmissionLockSerializer
from openassessment.test_utils import CacheResetTest


TEST_TIME = datetime(2020, 8, 29, 2, 14, tzinfo=timezone(offset=timedelta(hours=-4)))


@freeze_time(TEST_TIME)
class TestSubmissionLockSerializer(CacheResetTest):
    """ Tests for SubmissionLockSerializer """

    test_user_id_1 = 'Alice'
    test_user_id_2 = 'Bob'

    test_submission_id = str(uuid4())
    test_submission_lock = None

    timestamp = '2020-08-29T02:14:00-04:00'

    def setUp(self):
        super().setUp()

        # create a test lock for test_submission_id by test_user_id_1
        self.test_submission_lock = SubmissionGradingLock.claim_submission_lock(
            self.test_submission_id,
            self.test_user_id_1,
        )

    def test_empty(self):
        """ Serialization with an empty object returns lock_status of 'unlocked' """
        context = {'user_id': self.test_user_id_1}
        expected_output = {'lock_status': 'unlocked'}
        assert SubmissionLockSerializer({}, context=context).data == expected_output

    def test_serialize_inactive_lock(self):
        """ An inactive lock should serialize with lock_status of 'unlocked'. Other fields may or may not be passed """
        self.test_submission_lock.created_at = self.test_submission_lock.created_at - (
            SubmissionGradingLock.TIMEOUT + timedelta(hours=1)
        )
        self.test_submission_lock.save()

        context = {'user_id': self.test_user_id_1}
        output = SubmissionLockSerializer(self.test_submission_lock, context=context).data
        assert output['lock_status'] == 'unlocked'

    def test_serialize_in_progress_lock(self):
        """ Serializing a lock I own returns a lock_status of 'in-progress' """
        context = {'user_id': self.test_user_id_1}
        expected_output = {
            'submission_uuid': self.test_submission_id,
            'owner_id': self.test_user_id_1,
            'created_at': self.timestamp,
            'lock_status': 'in-progress'
        }

        assert SubmissionLockSerializer(self.test_submission_lock, context=context).data == expected_output

    def test_serialize_locked_lock(self):
        """ Serializing a lock owned by another user returns a lock_status of 'locked' """
        context = {'user_id': self.test_user_id_2}
        expected_output = {
            'submission_uuid': self.test_submission_id,
            'owner_id': self.test_user_id_1,
            'created_at': self.timestamp,
            'lock_status': 'locked'
        }

        assert SubmissionLockSerializer(self.test_submission_lock, context=context).data == expected_output


class BaseSerializerTest(TestCase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None


@ddt.ddt
class TestSubmissionListScoreSerializer(BaseSerializerTest):

    @ddt.unpack
    @ddt.data((1, 10), (99, 100), (0, 0))
    def test_serializer(self, earned, possible):
        mock_assessment = Mock(points_earned=earned, points_possible=possible)
        assert SubmissionListScoreSerializer(mock_assessment).data == {
            'pointsEarned': mock_assessment.points_earned,
            'pointsPossible': mock_assessment.points_possible
        }


@ddt.ddt
class TestSubmissionListSerializer(BaseSerializerTest):

    @contextmanager
    def mock_get_gradedBy(self):
        with patch.object(SubmissionListSerializer, 'get_gradedBy', return_value='get_gradedBy'):
            yield

    @contextmanager
    def mock_get_username(self):
        with patch.object(SubmissionListSerializer, 'get_username', return_value='get_username'):
            yield

    @contextmanager
    def mock_get_teamName(self):
        with patch.object(SubmissionListSerializer, 'get_teamName', return_value='get_teamName'):
            yield

    @contextmanager
    def mock_get_score(self):
        with patch.object(SubmissionListSerializer, 'get_score', return_value='get_score'):
            yield

    @contextmanager
    def mock_verify_required_context(self):
        with patch.object(SubmissionListSerializer, '_verify_required_context'):
            yield

    @contextmanager
    def mock_serializer_methods(self, gradedBy=False, username=False, teamName=False, score=False, verify=False):
        with ExitStack() as stack:
            if gradedBy:
                stack.enter_context(self.mock_get_gradedBy())
            if username:
                stack.enter_context(self.mock_get_username())
            if teamName:
                stack.enter_context(self.mock_get_teamName())
            if score:
                stack.enter_context(self.mock_get_score())
            if verify:
                stack.enter_context(self.mock_verify_required_context())
            yield

    def test_serializer(self):
        mock_workflow = Mock()
        with self.mock_serializer_methods(gradedBy=True, username=True, teamName=True, score=True, verify=True):
            result = SubmissionListSerializer(mock_workflow).data
        self.assertDictEqual(
            result,
            {
                'submissionUuid': str(mock_workflow.submission_uuid),
                'dateSubmitted': str(mock_workflow.created_at),
                'dateGraded': str(mock_workflow.grading_completed_at),
                'gradingStatus': str(mock_workflow.grading_status),
                'lockStatus': str(mock_workflow.lock_status),
                'gradedBy': 'get_gradedBy',
                'username': 'get_username',
                'teamName': 'get_teamName',
                'score': 'get_score',
            }
        )

    @ddt.data(True, False)
    def test_get_gradedBy(self, has_scorer_id):
        mock_workflow = Mock()
        scorer_id, scorer_username = 'test_scorer_id', 'test_scorer_username'
        if has_scorer_id:
            mock_workflow.scorer_id = scorer_id
        else:
            mock_workflow.scorer_id = None

        with self.mock_serializer_methods(username=True, score=True, verify=True):
            result = SubmissionListSerializer(
                mock_workflow,
                context={
                    'anonymous_id_to_username': {scorer_id: scorer_username}
                }
            ).data
        if has_scorer_id:
            self.assertEqual(result['gradedBy'], scorer_username)
        else:
            self.assertIsNone(result['gradedBy'])

    @ddt.data(True, False)
    def test_get_score(self, has_assessment):
        mock_workflow = Mock()
        # mock_workflow.identifying_uuid = str(mock_workflow.identifying_uuid)
        mock_assessment = Mock()

        mock_submission_uuid_to_assessment = {}
        if has_assessment:
            mock_submission_uuid_to_assessment[mock_workflow.identifying_uuid] = mock_assessment

        with self.mock_serializer_methods(gradedBy=True, username=True, verify=True):
            with patch(
                'openassessment.staffgrader.serializers.submission_list.SubmissionListScoreSerializer'
            ) as mock_score_serializer:
                result = SubmissionListSerializer(
                    mock_workflow,
                    context={
                        'submission_uuid_to_assessment': mock_submission_uuid_to_assessment
                    }
                ).data

        if has_assessment:
            mock_score_serializer.assert_called_once_with(mock_assessment)
            self.assertEqual(result['score'], mock_score_serializer.return_value.data)
        else:
            self.assertEqual(result['score'], {})

    def test_get_username(self):
        mock_workflow = Mock()
        # mock_workflow.identifying_uuid = str(mock_workflow.identifying_uuid)
        student_id, username = 'test_student_id', 'test_username'

        with self.mock_serializer_methods(gradedBy=True, score=True, verify=True):
            result = SubmissionListSerializer(
                mock_workflow,
                context={
                    'submission_uuid_to_student_id': {mock_workflow.identifying_uuid: student_id},
                    'anonymous_id_to_username': {student_id: username}
                }
            ).data

        self.assertEqual(result['username'], username)

    def test_get_teamName(self):
        mock_workflow = Mock()
        student_id, username = 'test_student_id', 'test_username'

        with self.mock_serializer_methods(gradedBy=True, username=True, score=True, verify=True):
            result = SubmissionListSerializer(
                mock_workflow,
                context={
                    'submission_uuid_to_student_id': {mock_workflow.identifying_uuid: student_id},
                    'anonymous_id_to_username': {student_id: username}
                }
            ).data

        # Team name should always be none for this individual responses
        self.assertEqual(result['teamName'], None)

    def test_integration(self):
        # Make three workflows. The first two have scorer_ids and the third does not
        workflows = [
            Mock(scorer_id='staff_student_id_1'),
            Mock(scorer_id='staff_student_id_2'),
            Mock(scorer_id=None)
        ]

        # Dict from workflow uuids to student_id_{0,1,2}
        submission_uuid_to_student_id = {
            workflow.identifying_uuid: f'student_id_{i}'
            for i, workflow in enumerate(workflows)
        }

        # Simple mapping of student_id_n to username_n
        anonymous_id_to_username = {
            f'student_id_{i}': f'username_{i}'
            for i in range(3)
        }
        # also include usernames for the scorers of the first two workflows
        anonymous_id_to_username[workflows[0].scorer_id] = 'staff_username_1'
        anonymous_id_to_username[workflows[1].scorer_id] = 'staff_username_2'

        # Add assessments for the "scored" workflows
        submission_uuid_to_assessment = {
            workflows[0].identifying_uuid: Mock(points_possible=20, points_earned=10),
            workflows[1].identifying_uuid: Mock(points_possible=20, points_earned=7),
        }

        data = SubmissionListSerializer(
            workflows,
            context={
                'submission_uuid_to_student_id': submission_uuid_to_student_id,
                'anonymous_id_to_username': anonymous_id_to_username,
                'submission_uuid_to_assessment': submission_uuid_to_assessment,
            },
            many=True
        ).data

        expected_data = [
            OrderedDict({
                'submissionUuid': str(workflows[0].submission_uuid),
                'dateSubmitted': str(workflows[0].created_at),
                'dateGraded': str(workflows[0].grading_completed_at),
                'gradingStatus': str(workflows[0].grading_status),
                'lockStatus': str(workflows[0].lock_status),
                'gradedBy': 'staff_username_1',
                'username': 'username_0',
                'teamName': None,
                'score': {
                    'pointsEarned': 10,
                    'pointsPossible': 20,
                },
            }),
            OrderedDict({
                'submissionUuid': str(workflows[1].submission_uuid),
                'dateSubmitted': str(workflows[1].created_at),
                'dateGraded': str(workflows[1].grading_completed_at),
                'gradingStatus': str(workflows[1].grading_status),
                'lockStatus': str(workflows[1].lock_status),
                'gradedBy': 'staff_username_2',
                'username': 'username_1',
                'teamName': None,
                'score': {
                    'pointsEarned': 7,
                    'pointsPossible': 20,
                },
            }),
            OrderedDict({
                'submissionUuid': str(workflows[2].submission_uuid),
                'dateSubmitted': str(workflows[2].created_at),
                'dateGraded': str(workflows[2].grading_completed_at),
                'gradingStatus': str(workflows[2].grading_status),
                'lockStatus': str(workflows[2].lock_status),
                'gradedBy': None,
                'username': 'username_2',
                'teamName': None,
                'score': {},
            })
        ]

        self.assertEqual(data, expected_data)


@ddt.ddt
class TestTeamSubmissionListSerializer(BaseSerializerTest):
    """Tests for serializing a list of team submissions"""

    required_context_keys = TeamSubmissionListSerializer.REQUIRED_CONTEXT_KEYS

    @contextmanager
    def mock_get_gradedBy(self):
        with patch.object(TeamSubmissionListSerializer, 'get_gradedBy', return_value='get_gradedBy'):
            yield

    @contextmanager
    def mock_get_username(self):
        with patch.object(TeamSubmissionListSerializer, 'get_username', return_value='get_username'):
            yield

    @contextmanager
    def mock_get_teamName(self):
        with patch.object(TeamSubmissionListSerializer, 'get_teamName', return_value='get_teamName'):
            yield

    @contextmanager
    def mock_get_score(self):
        with patch.object(TeamSubmissionListSerializer, 'get_score', return_value='get_score'):
            yield

    @contextmanager
    def mock_verify_required_context(self):
        with patch.object(TeamSubmissionListSerializer, '_verify_required_context'):
            yield

    @contextmanager
    def mock_serializer_methods(self, gradedBy=False, username=False, teamName=False, score=False, verify=False):
        with ExitStack() as stack:
            if gradedBy:
                stack.enter_context(self.mock_get_gradedBy())
            if username:
                stack.enter_context(self.mock_get_username())
            if teamName:
                stack.enter_context(self.mock_get_teamName())
            if score:
                stack.enter_context(self.mock_get_score())
            if verify:
                stack.enter_context(self.mock_verify_required_context())
            yield

    @ddt.data(0, 1, 2, 3)
    def test_missing_context(self, key_to_remove):
        """Test that missing context raises an exception"""
        context = {key: {} for key in self.required_context_keys}
        mock_workflow = Mock()

        # Remove a required context item
        context.pop(self.required_context_keys[key_to_remove])

        # Assert that the serializer fails
        with self.assertRaises(ValueError):
            TeamSubmissionListSerializer(mock_workflow)

    def test_serializer(self):
        """Test connections between serializer fields and underlying functions"""
        mock_workflow = Mock()
        with self.mock_serializer_methods(gradedBy=True, username=True, teamName=True, score=True, verify=True):
            result = TeamSubmissionListSerializer(mock_workflow).data
        self.assertDictEqual(
            result,
            {
                'submissionUuid': str(mock_workflow.team_submission_uuid),
                'dateSubmitted': str(mock_workflow.created_at),
                'dateGraded': str(mock_workflow.grading_completed_at),
                'gradingStatus': str(mock_workflow.grading_status),
                'lockStatus': str(mock_workflow.lock_status),
                'gradedBy': 'get_gradedBy',
                'username': 'get_username',
                'teamName': 'get_teamName',
                'score': 'get_score',
            }
        )

    def test_get_username(self):
        mock_workflow = Mock()
        student_id, username = 'test_student_id', 'test_username'

        with self.mock_serializer_methods(teamName=True, gradedBy=True, score=True, verify=True):
            result = TeamSubmissionListSerializer(
                mock_workflow,
                context={
                    'submission_uuid_to_student_id': {mock_workflow.identifying_uuid: student_id},
                    'anonymous_id_to_username': {student_id: username}
                }
            ).data

        # Username should be null for team submissions
        self.assertEqual(result['username'], None)

    def test_get_teamName(self):
        mock_workflow = Mock()
        team_id, team_name = 'test_team_id', 'test_team_name'

        with self.mock_serializer_methods(gradedBy=True, username=True, score=True, verify=True):
            result = TeamSubmissionListSerializer(
                mock_workflow,
                context={
                    'team_submission_uuid_to_team_id': {mock_workflow.identifying_uuid: team_id},
                    'team_id_to_team_name': {team_id: team_name}
                }
            ).data

        self.assertEqual(result['teamName'], team_name)

    def test_get_teamName_missing_context(self):
        mock_workflow = Mock()
        context = {}

        with self.mock_serializer_methods(username=True, gradedBy=True, score=True, verify=True):
            with self.assertRaises(MissingContextException):
                _ = TeamSubmissionListSerializer(mock_workflow, context=context).data

    def test_integration(self):
        """Simple integration test to see that fields map correctly"""
        # Create 3 workflows, 2 have scorers
        workflows = [
            Mock(scorer_id='staff_student_id_1'),
            Mock(scorer_id='staff_student_id_2'),
            Mock(scorer_id=None)
        ]

        # Dict from workflow uuids to team_id_{0,1,2}
        team_submission_uuid_to_team_id = {
            workflow.identifying_uuid: f'team_id_{i}'
            for i, workflow in enumerate(workflows)
        }

        # Add mappings from team ID to team name
        team_id_to_team_name = {
            f'team_id_{i}': f'Team name {i}'
            for i, _ in enumerate(workflows)
        }

        # Anonymous id to username used only for scorer ids
        anonymous_id_to_username = {}
        anonymous_id_to_username[workflows[0].scorer_id] = 'staff_username_1'
        anonymous_id_to_username[workflows[1].scorer_id] = 'staff_username_2'

        # Add assessments for the "scored" workflows
        submission_uuid_to_assessment = {
            workflows[0].identifying_uuid: Mock(points_possible=20, points_earned=10),
            workflows[1].identifying_uuid: Mock(points_possible=20, points_earned=7),
        }

        data = TeamSubmissionListSerializer(
            workflows,
            context={
                'anonymous_id_to_username': anonymous_id_to_username,
                'submission_uuid_to_assessment': submission_uuid_to_assessment,
                'team_submission_uuid_to_team_id': team_submission_uuid_to_team_id,
                'team_id_to_team_name': team_id_to_team_name,
            },
            many=True
        ).data

        expected_data = [
            OrderedDict({
                'submissionUuid': str(workflows[0].team_submission_uuid),
                'dateSubmitted': str(workflows[0].created_at),
                'dateGraded': str(workflows[0].grading_completed_at),
                'gradingStatus': str(workflows[0].grading_status),
                'lockStatus': str(workflows[0].lock_status),
                'gradedBy': 'staff_username_1',
                'username': None,
                'teamName': 'Team name 0',
                'score': {
                    'pointsEarned': 10,
                    'pointsPossible': 20,
                },
            }),
            OrderedDict({
                'submissionUuid': str(workflows[1].team_submission_uuid),
                'dateSubmitted': str(workflows[1].created_at),
                'dateGraded': str(workflows[1].grading_completed_at),
                'gradingStatus': str(workflows[1].grading_status),
                'lockStatus': str(workflows[1].lock_status),
                'gradedBy': 'staff_username_2',
                'username': None,
                'teamName': 'Team name 1',
                'score': {
                    'pointsEarned': 7,
                    'pointsPossible': 20,
                },
            }),
            OrderedDict({
                'submissionUuid': str(workflows[2].team_submission_uuid),
                'dateSubmitted': str(workflows[2].created_at),
                'dateGraded': str(workflows[2].grading_completed_at),
                'gradingStatus': str(workflows[2].grading_status),
                'lockStatus': str(workflows[2].lock_status),
                'gradedBy': None,
                'username': None,
                'teamName': 'Team name 2',
                'score': {},
            })
        ]

        self.assertEqual(data, expected_data)
