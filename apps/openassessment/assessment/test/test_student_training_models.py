"""
Tests for student training models.
"""
import mock
from django.db import IntegrityError
from submissions import api as sub_api
from openassessment.test_utils import CacheResetTest
from openassessment.assessment.models import (
    StudentTrainingWorkflow, StudentTrainingWorkflowItem
)
from .constants import STUDENT_ITEM, ANSWER, EXAMPLES


class StudentTrainingWorkflowTest(CacheResetTest):
    """
    Tests for the student training workflow model.
    """

    @mock.patch.object(StudentTrainingWorkflow.objects, 'get')
    @mock.patch.object(StudentTrainingWorkflow.objects, 'create')
    def test_create_workflow_integrity_error(self, mock_create, mock_get):
        # Simulate a race condition in which someone creates a workflow
        # after we check if it exists.  This will violate the database uniqueness
        # constraints, so we need to handle this case gracefully.
        mock_create.side_effect = IntegrityError

        # The first time we check, we should see that no workflow exists.
        # The second time, we should get the workflow created by someone else
        mock_workflow = mock.MagicMock(StudentTrainingWorkflow)
        mock_get.side_effect = [
            StudentTrainingWorkflow.DoesNotExist,
            mock_workflow
        ]

        # Expect that we retry and retrieve the workflow that someone else created
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER)
        workflow = StudentTrainingWorkflow.get_or_create_workflow(submission['uuid'])
        self.assertEqual(workflow, mock_workflow)

    @mock.patch.object(StudentTrainingWorkflowItem.objects, 'get')
    @mock.patch.object(StudentTrainingWorkflowItem.objects, 'create')
    def test_create_workflow_item_integrity_error(self, mock_create, mock_get):
        # Create a submission and workflow
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER)
        workflow = StudentTrainingWorkflow.get_or_create_workflow(submission['uuid'])

        # Simulate a race condition in which someone creates a workflow item
        # after we check if it exists.
        mock_workflow_item = mock.MagicMock(StudentTrainingWorkflowItem)
        mock_create.side_effect = IntegrityError
        mock_get.return_value = mock_workflow_item

        # Expect that we retry and retrieve the workflow item created by someone else
        self.assertEqual(workflow.next_training_example(EXAMPLES), mock_workflow_item.training_example)
