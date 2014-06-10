from django.db import DatabaseError
from django.test.utils import override_settings
import ddt
from mock import patch
from nose.tools import raises
from openassessment.assessment.models import PeerWorkflow

from openassessment.test_utils import CacheResetTest

from submissions.models import Submission
import openassessment.workflow.api as workflow_api
from openassessment.assessment.models import StudentTrainingWorkflow
import submissions.api as sub_api
from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.workflow.models import AssessmentWorkflow
from openassessment.workflow.errors import AssessmentWorkflowInternalError


ITEM_1 = {
    "student_id": "Optimus Prime 001",
    "item_id": "Matrix of Leadership",
    "course_id": "Advanced Auto Mechanics 200",
    "item_type": "openassessment",
}


@ddt.ddt
class TestAssessmentWorkflowApi(CacheResetTest):

    @ddt.file_data('data/assessments.json')
    def test_create_workflow(self, data):
        first_step = data["steps"][0] if data["steps"] else "peer"
        submission = sub_api.create_submission(ITEM_1, "Shoot Hot Rod")
        workflow = workflow_api.create_workflow(submission["uuid"], data["steps"])

        workflow_keys = set(workflow.keys())
        self.assertEqual(
            workflow_keys,
            {
                'submission_uuid', 'uuid', 'status', 'created', 'modified', 'score'
            }
        )
        self.assertEqual(workflow["submission_uuid"], submission["uuid"])
        self.assertEqual(workflow["status"], first_step)

        workflow_from_get = workflow_api.get_workflow_for_submission(
            submission["uuid"], data["requirements"]
        )
        del workflow_from_get['status_details']
        self.assertEqual(workflow, workflow_from_get)

        # Test that the Peer Workflow is, or is not created, based on when peer
        # is a step in the workflow.
        if "peer" == first_step:
            peer_workflow = PeerWorkflow.objects.get(submission_uuid=submission["uuid"])
            self.assertIsNotNone(peer_workflow)
        else:
            peer_workflows = list(PeerWorkflow.objects.filter(submission_uuid=submission["uuid"]))
            self.assertFalse(peer_workflows)

    def test_assessment_module_rollback_update_workflow(self):
        """
        Test that updates work when assessment modules roll back

        This test is designed to instantiate a workflow with an installed
        assessment module, then verify the workflow can be updated even when
        the status is set to an uninstalled assessment module.

        """
        requirements = {
            "special": {},
            "peer": {
                "must_grade": 1,
                "must_be_graded_by": 1
            },
            "self": {}
        }

        # We'll cheat to create the workflow with the new 'special' status,
        # otherwise the creation logic will not allow unknown an unknown status
        # to be set.
        real_steps = AssessmentWorkflow.STEPS
        AssessmentWorkflow.STEPS = ["special"] + real_steps
        workflow, submission = self._create_workflow_with_status(
            "user 1",
            "test/1/1",
            "peer-problem",
            "special",
            steps=["special", "peer", "self"])
        AssessmentWorkflow.STEPS = real_steps

        workflow_api.get_workflow_for_submission(
            submission["uuid"], requirements
        )

        peer_workflows = list(PeerWorkflow.objects.filter(submission_uuid=submission["uuid"]))
        self.assertTrue(peer_workflows)


        with patch.object(peer_api, 'submitter_is_finished') as mock_peer_submit:
            mock_peer_submit.return_value = True
            workflow = workflow_api.get_workflow_for_submission(
                submission["uuid"], requirements
            )
        self.assertEquals("self", workflow['status'])

        with patch.object(self_api, 'submitter_is_finished') as mock_self_submit:
            mock_self_submit.return_value = True
            workflow = workflow_api.get_workflow_for_submission(
                submission["uuid"], requirements
            )

        self.assertEquals("waiting", workflow['status'])

    def test_update_peer_workflow(self):
        submission = sub_api.create_submission(ITEM_1, "Shoot Hot Rod")
        workflow = workflow_api.create_workflow(submission["uuid"], ["training", "peer"])
        StudentTrainingWorkflow.create_workflow(submission_uuid=submission["uuid"])
        requirements = {
            "training": {
                "num_required": 2
            },
            "peer": {
                "must_grade": 5,
                "must_be_graded_by": 3
            }
        }
        workflow_keys = set(workflow.keys())
        self.assertEqual(
            workflow_keys,
            {
                'submission_uuid', 'uuid', 'status', 'created', 'modified', 'score'
            }
        )
        self.assertEqual(workflow["submission_uuid"], submission["uuid"])
        self.assertEqual(workflow["status"], "training")

        peer_workflows = list(PeerWorkflow.objects.filter(submission_uuid=submission["uuid"]))
        self.assertFalse(peer_workflows)

        workflow_from_get = workflow_api.get_workflow_for_submission(
            submission["uuid"], requirements
        )

        del workflow_from_get['status_details']
        self.assertEqual(workflow, workflow_from_get)

        requirements["training"]["num_required"] = 0
        workflow = workflow_api.update_from_assessments(submission["uuid"], requirements)

        # New step is Peer, and a Workflow has been created.
        self.assertEqual(workflow["status"], "peer")
        peer_workflow = PeerWorkflow.objects.get(submission_uuid=submission["uuid"])
        self.assertIsNotNone(peer_workflow)

    @ddt.file_data('data/assessments.json')
    def test_need_valid_submission_uuid(self, data):
        # submission doesn't exist
        with self.assertRaises(workflow_api.AssessmentWorkflowRequestError):
            workflow = workflow_api.create_workflow("xxxxxxxxxxx", data["steps"])

        # submission_uuid is the wrong type
        with self.assertRaises(workflow_api.AssessmentWorkflowRequestError):
            workflow = workflow_api.create_workflow(123, data["steps"])

    @patch.object(Submission.objects, 'get')
    @ddt.file_data('data/assessments.json')
    @raises(workflow_api.AssessmentWorkflowInternalError)
    def test_unexpected_submissions_errors_wrapped(self, data, mock_get):
        mock_get.side_effect = Exception("Kaboom!")
        workflow_api.create_workflow("zzzzzzzzzzzzzzz", data["steps"])

    @patch.object(AssessmentWorkflow.objects, 'create')
    @ddt.file_data('data/assessments.json')
    @raises(workflow_api.AssessmentWorkflowInternalError)
    def test_unexpected_workflow_errors_wrapped(self, data, mock_create):
        mock_create.side_effect = DatabaseError("Kaboom!")
        submission = sub_api.create_submission(ITEM_1, "Ultra Magnus fumble")
        workflow_api.create_workflow(submission["uuid"], data["steps"])

    @patch.object(PeerWorkflow.objects, 'get_or_create')
    @raises(workflow_api.AssessmentWorkflowInternalError)
    def test_unexpected_peer_workflow_errors_wrapped(self, mock_create):
        mock_create.side_effect = DatabaseError("Kaboom!")
        submission = sub_api.create_submission(ITEM_1, "Ultra Magnus fumble")
        workflow_api.create_workflow(submission["uuid"], ["peer", "self"])

    @patch.object(AssessmentWorkflow.objects, 'get')
    @ddt.file_data('data/assessments.json')
    @raises(workflow_api.AssessmentWorkflowInternalError)
    def test_unexpected_exception_wrapped(self, data, mock_create):
        mock_create.side_effect = Exception("Kaboom!")
        submission = sub_api.create_submission(ITEM_1, "Ultra Magnus fumble")
        workflow_api.update_from_assessments(submission["uuid"], data["steps"])

    @ddt.file_data('data/assessments.json')
    def test_get_assessment_workflow_expected_errors(self, data):
        with self.assertRaises(workflow_api.AssessmentWorkflowNotFoundError):
            workflow_api.get_workflow_for_submission("0000000000000", data["requirements"])
        with self.assertRaises(workflow_api.AssessmentWorkflowRequestError):
            workflow_api.get_workflow_for_submission(123, data["requirements"])

    @patch.object(Submission.objects, 'get')
    @ddt.file_data('data/assessments.json')
    @raises(workflow_api.AssessmentWorkflowInternalError)
    def test_unexpected_workflow_get_errors_wrapped(self, data, mock_get):
        mock_get.side_effect = Exception("Kaboom!")
        submission = sub_api.create_submission(ITEM_1, "We talk TV!")
        workflow = workflow_api.create_workflow(submission["uuid"], data["steps"])
        workflow_api.get_workflow_for_submission(workflow["uuid"], {})

    def test_get_status_counts(self):
        # Initially, the counts should all be zero
        counts = workflow_api.get_status_counts("test/1/1", "peer-problem", ["peer", "self"])
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
        counts = workflow_api.get_status_counts("test/1/1", "peer-problem", ["peer", "self"])
        self.assertEqual(counts, [
            {"status": "peer", "count": 1},
            {"status": "self", "count": 2},
            {"status": "waiting", "count": 3},
            {"status": "done", "count": 4},
        ])

        # Create a workflow in a different course, same user and item
        # Counts should be the same
        self._create_workflow_with_status("user 1", "other_course", "peer-problem", "peer")
        updated_counts = workflow_api.get_status_counts("test/1/1", "peer-problem", ["peer", "self"])
        self.assertEqual(counts, updated_counts)

        # Create a workflow in the same course, different item
        # Counts should be the same
        self._create_workflow_with_status("user 1", "test/1/1", "other problem", "peer")
        updated_counts = workflow_api.get_status_counts("test/1/1", "peer-problem", ["peer", "self"])
        self.assertEqual(counts, updated_counts)

    @override_settings(ORA2_ASSESSMENTS={'self': 'not.a.module'})
    def test_unable_to_load_api(self):
        submission = sub_api.create_submission({
            "student_id": "test student",
            "course_id": "test course",
            "item_id": "test item",
            "item_type": "openassessment",
        }, "test answer")

        with self.assertRaises(AssessmentWorkflowInternalError):
            workflow_api.create_workflow(submission['uuid'], ['self'])

        with self.assertRaises(AssessmentWorkflowInternalError):
            workflow_api.update_from_assessments(submission['uuid'], {})

    def _create_workflow_with_status(
        self, student_id, course_id, item_id,
        status, answer="answer", steps=None
    ):
        """
        Create a submission and workflow with a given status.

        Args:
            student_id (unicode): Student ID for the submission.
            course_id (unicode): Course ID for the submission.
            item_id (unicode): Item ID for the submission
            status (unicode): One of acceptable status values (e.g. "peer", "self", "waiting", "done")

        Kwargs:
            answer (unicode): Submission answer.
            steps (list): A list of steps to create the workflow with. If not
                specified the default steps are "peer", "self".

        Returns:
            workflow, submission
        """
        if not steps:
            steps = ["peer", "self"]

        submission = sub_api.create_submission({
            "student_id": student_id,
            "course_id": course_id,
            "item_id": item_id,
            "item_type": "openassessment",
        }, answer)

        workflow = workflow_api.create_workflow(submission['uuid'], steps)
        workflow_model = AssessmentWorkflow.objects.get(uuid=workflow['uuid'])
        workflow_model.status = status
        workflow_model.save()
        return workflow, submission
