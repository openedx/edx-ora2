from django.db import DatabaseError

from django.test import TestCase
from mock import patch
from nose.tools import raises
from openassessment.assessment import peer_api

from openassessment.workflow.models import AssessmentWorkflow
from submissions.models import Submission
import openassessment.workflow.api as workflow_api
import submissions.api as sub_api

ITEM_1 = {
    "student_id": "Optimus Prime 001",
    "item_id": "Matrix of Leadership",
    "course_id": "Advanced Auto Mechanics 200",
    "item_type": "openassessment",
}

REQUIREMENTS = {
    "peer": {
        "must_grade": 5,
        "must_be_graded_by": 3,
    }
}

class TestAssessmentWorkflowApi(TestCase):

    def test_create_workflow(self):
        submission = sub_api.create_submission(ITEM_1, "Shoot Hot Rod")
        workflow = workflow_api.create_workflow(submission["uuid"])

        workflow_keys = set(workflow.keys())
        self.assertEqual(
            workflow_keys,
            {
                'submission_uuid', 'uuid', 'status', 'created', 'modified', 'score'
            }
        )
        self.assertEqual(workflow["submission_uuid"], submission["uuid"])
        self.assertEqual(workflow["status"], "peer")

        workflow_from_get = workflow_api.get_workflow_for_submission(
            submission["uuid"], REQUIREMENTS
        )
        del workflow_from_get['status_details']
        self.assertEqual(workflow, workflow_from_get)

    def test_need_valid_submission_uuid(self):
        # submission doesn't exist
        with self.assertRaises(workflow_api.AssessmentWorkflowRequestError):
            workflow = workflow_api.create_workflow("xxxxxxxxxxx")

        # submission_uuid is the wrong type
        with self.assertRaises(workflow_api.AssessmentWorkflowRequestError):
            workflow = workflow_api.create_workflow(123)

    @patch.object(Submission.objects, 'get')
    @raises(workflow_api.AssessmentWorkflowInternalError)
    def test_unexpected_submissions_errors_wrapped(self, mock_get):
        mock_get.side_effect = Exception("Kaboom!")
        workflow_api.create_workflow("zzzzzzzzzzzzzzz")

    @patch.object(AssessmentWorkflow.objects, 'create')
    @raises(workflow_api.AssessmentWorkflowInternalError)
    def test_unexpected_workflow_errors_wrapped(self, mock_create):
        mock_create.side_effect = DatabaseError("Kaboom!")
        submission = sub_api.create_submission(ITEM_1, "Ultra Magnus fumble")
        workflow_api.create_workflow(submission["uuid"])

    def test_get_assessment_workflow_expected_errors(self):
        with self.assertRaises(workflow_api.AssessmentWorkflowNotFoundError):
            workflow_api.get_workflow_for_submission("0000000000000", REQUIREMENTS)
        with self.assertRaises(workflow_api.AssessmentWorkflowRequestError):
            workflow_api.get_workflow_for_submission(123, REQUIREMENTS)

    @patch.object(Submission.objects, 'get')
    @raises(workflow_api.AssessmentWorkflowInternalError)
    def test_unexpected_workflow_get_errors_wrapped(self, mock_get):
        mock_get.side_effect = Exception("Kaboom!")
        submission = sub_api.create_submission(ITEM_1, "We talk TV!")
        workflow = workflow_api.create_workflow(submission["uuid"])
        workflow_api.get_workflow_for_submission(workflow["uuid"], REQUIREMENTS)
