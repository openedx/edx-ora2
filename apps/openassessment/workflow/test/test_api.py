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

    def test_get_status_counts(self):
        # Initially, the counts should all be zero
        counts = workflow_api.get_status_counts()
        self.assertEqual(counts, [
            {"status": "peer", "count": 0},
            {"status": "self", "count": 0},
            {"status": "waiting", "count": 0},
            {"status": "done", "count": 0},
        ])

        # Create assessments with each status
        # We're going to cheat a little bit by using the model objects
        # directly, since the API does not provide access to the status directly.
        self._create_workflow_with_status("user 1", "test/1/1", "peer-problem", "peer")
        self._create_workflow_with_status("user 2", "test/1/1", "peer-problem", "self")
        self._create_workflow_with_status("user 3", "test/1/1", "peer-problem", "self")
        self._create_workflow_with_status("user 4", "test/1/1", "peer-problem", "waiting")
        self._create_workflow_with_status("user 5", "test/1/1", "peer-problem", "waiting")
        self._create_workflow_with_status("user 6", "test/1/1", "peer-problem", "waiting")
        self._create_workflow_with_status("user 7", "test/1/1", "peer-problem", "done")
        self._create_workflow_with_status("user 8", "test/1/1", "peer-problem", "done")
        self._create_workflow_with_status("user 9", "test/1/1", "peer-problem", "done")
        self._create_workflow_with_status("user 10", "test/1/1", "peer-problem", "done")

        # Now the counts should be updated
        counts = workflow_api.get_status_counts()
        self.assertEqual(counts, [
            {"status": "peer", "count": 1},
            {"status": "self", "count": 2},
            {"status": "waiting", "count": 3},
            {"status": "done", "count": 4},
        ])

    def _create_workflow_with_status(
        self, student_id, course_id, item_id, status,
        item_type="openassessment", answer="answer"
    ):
        """
        Create a submission and workflow with a given status.

        Args:
            student_id (unicode): Student ID for the submission.
            course_id (unicode): Course ID for the submission.
            item_id (unicode): Item ID for the submission
            status (unicode): One of acceptable status values (e.g. "peer", "self", "waiting", "done")

        Kwargs:
            item_type (unicode): Type of item for the submission.
            answer (unicode): Submission answer.

        Returns:
            None
        """
        submission = sub_api.create_submission({
            "student_id": student_id,
            "course_id": course_id,
            "item_id": item_id,
            "item_type": item_type
        }, answer)

        AssessmentWorkflow.objects.create(
            submission_uuid=submission['uuid'],
            status=status
        )
