"""
Contract tests for calling team_workflow_api from team_workflow_mixin
"""

from __future__ import absolute_import
from unittest import TestCase
from mock import patch
from openassessment.xblock.team_workflow_mixin import TeamWorkflowMixin


class TestTeamWorkflowMixin(TestCase):
    """
    Class to test the API between team_workflow_mixin and the team_workflow_api
    """

    def setUp(self):
        super().setUp()
        self.team_mixin = TeamWorkflowMixin()

    @patch('openassessment.xblock.team_workflow_mixin.team_workflow_api')
    def test_get_team_workflow_info(self, api_mock):
        submission_uuid = "sub_uuid"
        self.team_mixin.get_team_workflow_info(submission_uuid)
        api_mock.get_workflow_for_submission.assert_called_with(submission_uuid)

    @patch('openassessment.xblock.team_workflow_mixin.team_workflow_api')
    def test_create_team_workflow(self, api_mock):
        submission_uuid = "sub_uuid"
        self.team_mixin.create_team_workflow(submission_uuid)
        api_mock.create_workflow.assert_called_with(submission_uuid)

    @patch('openassessment.xblock.team_workflow_mixin.team_workflow_api')
    def test_get_team_workflow_status_counts(self, api_mock):
        with patch.object(TeamWorkflowMixin, 'get_student_item_dict', create=True) as mock:
            student_item_dict = dict(
                student_id='student_id_1',
                item_id='item1',
                course_id='course1',
                item_type='openassessment'
            )
            mock.return_value = student_item_dict
            self.team_mixin.get_team_workflow_status_counts()
            api_mock.get_status_counts.assert_called()
