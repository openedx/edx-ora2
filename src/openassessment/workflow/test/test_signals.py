"""
Tests for Django signals and receivers defined by the workflow API.
"""
from unittest import mock

import ddt
from django.db import DatabaseError

from submissions import api as sub_api
from openassessment.assessment.signals import assessment_complete_signal
from openassessment.test_utils import CacheResetTest
from openassessment.workflow import api as workflow_api
from openassessment.workflow.models import AssessmentWorkflow


@ddt.ddt
class UpdateWorkflowSignalTest(CacheResetTest):
    """
    Test for the update workflow signal.
    """
    STUDENT_ITEM = {
        "student_id": "test student",
        "item_id": "test item",
        "course_id": "test course",
        "item_type": "openassessment",
    }

    def setUp(self):
        """
        Create a submission.
        """
        super().setUp()
        submission = sub_api.create_submission(self.STUDENT_ITEM, "test answer")
        self.submission_uuid = submission['uuid']

    def test_update_signal_no_workflow(self):
        # Without defining a workflow, send the signal
        # The receiver should catch and log the exception
        assessment_complete_signal.send(sender=None, submission_uuid=self.submission_uuid)

    def test_update_signal_no_submission_uuid(self):
        # Try to send the signal without specifying a submission UUID
        # The receiver should catch and log the exception
        assessment_complete_signal.send(sender=None)

    def test_update_signal_updates_workflow(self):
        # Start a workflow for the submission
        workflow_api.create_workflow(self.submission_uuid, ['self'])

        # Spy on the workflow update call
        with mock.patch.object(AssessmentWorkflow, 'update_from_assessments') as mock_update:

            # Send a signal to update the workflow
            assessment_complete_signal.send(sender=None, submission_uuid=self.submission_uuid)

            # Verify that the workflow model update was called
            mock_update.assert_called_once_with(None, {})

    @ddt.data(DatabaseError, IOError)
    @mock.patch('openassessment.workflow.models.AssessmentWorkflow.objects.get')
    def test_errors(self, error, mock_call):
        # Start a workflow for the submission
        workflow_api.create_workflow(self.submission_uuid, ['self'])

        # The receiver should catch and log the error
        mock_call.side_effect = error("OH NO!")
        assessment_complete_signal.send(sender=None, submission_uuid=self.submission_uuid)
