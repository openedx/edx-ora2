"""
Contract tests for calling team_workflow_api from team_workflow_mixin
"""

from __future__ import absolute_import
from unittest import TestCase
from mock import patch, Mock
from submissions.errors import TeamSubmissionNotFoundError
from openassessment.xblock.team_workflow_mixin import TeamWorkflowMixin

STUDENT_ITEM_DICT = dict(
    student_id='student_id_1',
    item_id='item1',
    course_id='course1',
    item_type='openassessment'
)

class TestBlock(TeamWorkflowMixin):
    """ Dummy class for testing TeamWorkflowMixin """

    team = Mock()

    def get_student_item_dict(self):
        return STUDENT_ITEM_DICT

    _has_team = True
    def has_team(self):
        return self._has_team



class TestTeamWorkflowMixin(TestCase):
    """
    Class to test the API between team_workflow_mixin and the team_workflow_api
    """

    def setUp(self):
        super().setUp()
        self.test_block = TestBlock()

    @patch('openassessment.xblock.team_workflow_mixin.team_workflow_api')
    def test_get_team_workflow_info(self, api_mock):
        submission_uuid = "sub_uuid"
        self.test_block.get_team_workflow_info(submission_uuid)
        api_mock.get_workflow_for_submission.assert_called_with(submission_uuid)

    @patch('openassessment.xblock.team_workflow_mixin.team_workflow_api')
    def test_create_team_workflow(self, api_mock):
        submission_uuid = "sub_uuid"
        self.test_block.create_team_workflow(submission_uuid)
        api_mock.create_workflow.assert_called_with(submission_uuid)

    @patch('openassessment.xblock.team_workflow_mixin.team_workflow_api')
    def test_get_team_workflow_status_counts(self, api_mock):
        self.test_block.get_team_workflow_status_counts()
        api_mock.get_status_counts.assert_called()

    @patch('openassessment.xblock.team_workflow_mixin.team_sub_api.get_team_submission_for_team')
    def test_get_team_submission_uuid(self, mock_get_team_sub):
        team_submission_uuid =  'this-is-the-uuid'
        mock_get_team_sub.return_value = {'team_submission_uuid': team_submission_uuid}

        self.assertEqual(self.test_block.get_team_submission_uuid(), team_submission_uuid)
        mock_get_team_sub.assert_called_with(
            STUDENT_ITEM_DICT['course_id'],
            STUDENT_ITEM_DICT['item_id'],
            self.test_block.team.team_id
        )

    @patch('openassessment.xblock.team_workflow_mixin.team_sub_api.get_team_submission_for_team')
    def test_get_team_submission_uuid_no_team(self, mock_get_team_sub):
        self.test_block._has_team = False
        self.assertIsNone(self.test_block.get_team_submission_uuid())
        mock_get_team_sub.assert_not_called()

    @patch('openassessment.xblock.team_workflow_mixin.team_sub_api.get_team_submission_for_team')
    def test_get_team_submission_uuid_error(self, mock_get_team_sub):
        mock_get_team_sub.side_effect = TeamSubmissionNotFoundError()
        self.assertIsNone(self.test_block.get_team_submission_uuid())
        mock_get_team_sub.assert_called_with(
            STUDENT_ITEM_DICT['course_id'],
            STUDENT_ITEM_DICT['item_id'],
            self.test_block.team.team_id
        )
