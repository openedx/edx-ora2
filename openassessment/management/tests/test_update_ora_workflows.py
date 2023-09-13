"""tests for the management command to asynchronously batch update ORA workflows"""

from django.test import TestCase
from mock import patch
import pytest
from django.core.management.base import CommandError
from openassessment.management.commands import update_ora_workflows


class UpdateOraWorkflowsTest(TestCase):

    @patch(
        'openassessment.management.commands.update_ora_workflows.tasks.'
        'update_workflows_for_all_blocked_submissions_task.apply_async')
    def test_update_ora_workflows_for_all_blocked_submissions(self, mock_update_workflows):
        command = update_ora_workflows.Command()
        command.handle()
        mock_update_workflows.assert_called()

    @patch('openassessment.management.commands.update_ora_workflows.tasks.'
           'update_workflows_for_course_task.apply_async')
    def test_update_ora_workflows_for_course(self, mock_update_workflows):
        command = update_ora_workflows.Command()
        command.handle(course_id="course_id_1")
        mock_update_workflows.assert_called_with(["course_id_1"])

    @patch(
        'openassessment.management.commands.update_ora_workflows.tasks.'
        'update_workflows_for_ora_block_task.apply_async')
    def test_update_ora_workflows_for_ora_block(self, mock_update_workflows):
        command = update_ora_workflows.Command()
        command.handle(item_id="item_id_1")
        mock_update_workflows.assert_called_with(["item_id_1"])

    def test_update_ora_workflows_arguments_error(self):
        command = update_ora_workflows.Command()
        # CommandError expected to be raised if ambiguous args provided
        with pytest.raises(CommandError):
            command.handle(item_id="item_id_1", course_id="course_id_1")
