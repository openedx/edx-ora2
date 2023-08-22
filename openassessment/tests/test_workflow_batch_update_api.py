"""
Tests batch ORA workflow update API
"""
import datetime
import logging
from django.utils import timezone
from mock import patch

from submissions import api as sub_api
from openassessment.test_utils import CacheResetTest
from openassessment.assessment.models import PeerWorkflow
from openassessment.assessment.api import peer as peer_api
from openassessment.workflow import api as workflow_api
from openassessment import workflow_batch_update_api as update_api

logger = logging.getLogger(__name__)

STUDENT_ITEM = {
    "student_id": "Tim",
    "course_id": "Demo_Course",
    "item_id": "item_one",
    "item_type": "Peer_Submission",
}

STEPS = ['peer', 'self']


class TestWorkflowBatchUpdateAPI(CacheResetTest):

    def test_get_blocked_peer_workflows(self):
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")  # pylint: disable=unused-variable
        self._create_student_and_submission("Miles", "Miles's answer")
        pat_sub, pat = self._create_student_and_submission("Pat", "Pat's answer")  # pylint: disable=unused-variable

        blocked = update_api.get_blocked_peer_workflows()
        # we expect 0 blocked submissions as they were just created
        self.assertEqual(len(blocked), 0)

        # set Tim's submission create_at date to >7 days ago
        pw_tim = PeerWorkflow.objects.get(student_id=tim["student_id"])
        pw_tim.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_tim.save()
        blocked = update_api.get_blocked_peer_workflows()
        # we expect 1 blocked submission
        self.assertEqual(len(blocked), 1)

        # set Pat's submission create_at date to >7 days ago and set completed_at date
        pw_pat = PeerWorkflow.objects.get(student_id=pat["student_id"])
        pw_pat.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_pat.completed_at = timezone.now() - datetime.timedelta(days=2)
        pw_pat.save()
        blocked = update_api.get_blocked_peer_workflows()
        # we still expect 1 blocked submission (Tim)
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0].student_id, 'Tim')

    def test_get_blocked_peer_workflows_for_course(self):
        # pylint: disable=unused-variable
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")
        # pylint: disable=unused-variable
        miles_sub, miles = self._create_student_and_submission("Miles", "Miles's answer")
        # pylint: disable=unused-variable
        pat_sub, pat = self._create_student_and_submission("Pat", "Pat's answer")

        blocked = update_api.get_blocked_peer_workflows_for_course("course_1")
        # we expect 0 blocked submissions for "course_1"
        self.assertEqual(len(blocked), 0)

        pw_tim = PeerWorkflow.objects.get(student_id=tim["student_id"])
        pw_tim.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_tim.save()

        pw_pat = PeerWorkflow.objects.get(student_id=pat["student_id"])
        pw_pat.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_pat.course_id = "course_1"
        pw_pat.save()

        blocked = update_api.get_blocked_peer_workflows_for_course("course_1")
        # we expect 1 blocked submission for "course_1"
        self.assertEqual(len(blocked), 1)

        pw_miles = PeerWorkflow.objects.get(student_id=miles["student_id"])
        pw_miles.course_id = "course_2"
        pw_miles.save()

        blocked = update_api.get_blocked_peer_workflows_for_course("course_2")
        # we expect 0 blocked submissions for "course_2"
        self.assertEqual(len(blocked), 0)

    def test_get_blocked_peer_workflows_for_ora_block(self):
        # pylint: disable=unused-variable
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")
        # pylint: disable=unused-variable
        miles_sub, miles = self._create_student_and_submission("Miles", "Miles's answer")
        # pylint: disable=unused-variable
        pat_sub, pat = self._create_student_and_submission("Pat", "Pat's answer")

        blocked = update_api.get_blocked_peer_workflows_for_ora_block("item_1")
        # we expect 0 blocked submissions for "item_1"
        self.assertEqual(len(blocked), 0)

        pw_tim = PeerWorkflow.objects.get(student_id=tim["student_id"])
        pw_tim.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_tim.save()

        pw_pat = PeerWorkflow.objects.get(student_id=pat["student_id"])
        pw_pat.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_pat.item_id = "item_1"
        pw_pat.save()

        blocked = update_api.get_blocked_peer_workflows_for_ora_block("item_1")
        # we expect 1 blocked submission for "item_1"
        self.assertEqual(len(blocked), 1)

        pw_miles = PeerWorkflow.objects.get(student_id=miles["student_id"])
        pw_miles.item_id = "item_2"
        pw_miles.save()

        blocked = update_api.get_blocked_peer_workflows_for_ora_block("item_2")
        # we expect 0 blocked submissions for "item_2"
        self.assertEqual(len(blocked), 0)

    def test_is_flexible_peer_grading_on(self):
        workflow_requirements = {"peer": {
            "must_grade": 2,
            "must_be_graded_by": 3,
            "enable_flexible_grading": True
        }}
        ora_block = MockOraBlock(workflow_requirements)
        self.assertTrue(update_api.is_flexible_peer_grading_on(ora_block))

        ora_block.requirements['peer']['enable_flexible_grading'] = False
        self.assertFalse(update_api.is_flexible_peer_grading_on(ora_block))

        ora_block.requirements['peer']['enable_flexible_grading'] = False
        self.assertFalse(update_api.is_flexible_peer_grading_on(ora_block))

        del (ora_block.requirements['peer']['enable_flexible_grading'])
        self.assertFalse(update_api.is_flexible_peer_grading_on(ora_block))

        del (ora_block.requirements['peer'])
        self.assertFalse(update_api.is_flexible_peer_grading_on(ora_block))

    @patch('openassessment.workflow.api.update_from_assessments')
    def test_update_workflow_for_submission(self, mock_update_from_assessments):
        mock_update_from_assessments.return_value = "workflow"

        workflow = update_api.update_workflow_for_submission("submission_uuid", "assessment_requirements",
                                                             "course_override")
        mock_update_from_assessments.assert_called_once_with("submission_uuid", "assessment_requirements",
                                                             "course_override")
        self.assertEqual(workflow, "workflow")

    @patch('openassessment.workflow_batch_update_api.update_workflow_for_submission')
    def test_update_workflows(self, mock_update_workflow_for_submission):
        update_api.update_workflows({})
        mock_update_workflow_for_submission.assert_not_called()

        update_api.update_workflows(None)
        mock_update_workflow_for_submission.assert_not_called()

        assessment_requirements_dict = {
            "submission_uuid_1": {},
            "submission_uuid_2": {},
        }
        update_api.update_workflows(assessment_requirements_dict)
        mock_update_workflow_for_submission.assert_called_with("submission_uuid_2", {}, None)
        self.assertEqual(mock_update_workflow_for_submission.call_count, 2)

        # exceptions for individual updates should not disrupt batch process:
        try:
            mock_update_workflow_for_submission.side_effect = Exception()
            update_api.update_workflows(assessment_requirements_dict)
        except Exception:  # pylint: disable=broad-except
            self.fail("Exception not expected")

    @patch('openassessment.workflow_batch_update_api.update_workflows')
    @patch('openassessment.workflow_batch_update_api.get_blocked_peer_workflows_for_ora_block')
    @patch('openassessment.workflow_batch_update_api.get_assessment_requirements_for_flex_peer_grading')
    def test_update_workflows_for_ora_block(self, mock_update_workflows,
                                            mock_get_blocked_peer_workflows_for_ora_block,
                                            mock_get_assessment_requirements_for_flex_peer_grading):
        update_api.update_workflows_for_ora_block("some_item_id")
        mock_get_blocked_peer_workflows_for_ora_block.assert_called_once_with("some_item_id")
        mock_get_assessment_requirements_for_flex_peer_grading.assert_called_once()
        mock_update_workflows.assert_called_once()

        # exceptions should not disrupt batch process:
        try:
            mock_get_blocked_peer_workflows_for_ora_block.side_effect = Exception()
            update_api.update_workflows_for_ora_block("some_item_id")
        except Exception:   # pylint: disable=broad-except
            self.fail("Exception not expected")

    @patch('openassessment.workflow_batch_update_api.update_workflows')
    @patch('openassessment.workflow_batch_update_api.get_blocked_peer_workflows_for_course')
    @patch('openassessment.workflow_batch_update_api.get_assessment_requirements_for_flex_peer_grading')
    def test_update_workflows_for_course(self, mock_update_workflows,
                                         mock_get_blocked_peer_workflows_for_course,
                                         mock_get_assessment_requirements_for_flex_peer_grading):
        update_api.update_workflows_for_course("some_course_id")
        mock_get_blocked_peer_workflows_for_course.assert_called_once_with("some_course_id")
        mock_get_assessment_requirements_for_flex_peer_grading.assert_called_once()
        mock_update_workflows.assert_called_once()

        # exceptions should not disrupt batch process:
        try:
            mock_get_blocked_peer_workflows_for_course.side_effect = Exception()
            update_api.update_workflows_for_ora_block("some_item_id")
        except Exception:   # pylint: disable=broad-except
            self.fail("Exception not expected")

    @patch('openassessment.workflow_batch_update_api.update_workflows')
    @patch('openassessment.workflow_batch_update_api.get_blocked_peer_workflows')
    @patch('openassessment.workflow_batch_update_api.get_assessment_requirements_for_flex_peer_grading')
    def test_update_workflows_for_all_blocked_submissions(self, mock_update_workflows,
                                                          mock_get_blocked_peer_workflows,
                                                          mock_get_assessment_requirements_for_flex_peer_grading):
        update_api.update_workflows_for_all_blocked_submissions()
        mock_get_blocked_peer_workflows.assert_called_once()
        mock_get_assessment_requirements_for_flex_peer_grading.assert_called_once()
        mock_update_workflows.assert_called_once()

        # exceptions should not disrupt batch process:
        try:
            mock_get_blocked_peer_workflows.side_effect = Exception()
            update_api.update_workflows_for_all_blocked_submissions()
        except Exception:  # pylint: disable=broad-except
            self.fail("Exception not expected")

    @staticmethod
    def _create_student_and_submission(student, answer, date=None, steps=None):
        """ Creats a student and submission for tests. """
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student
        submission = sub_api.create_submission(new_student_item, answer, date)
        peer_api.on_start(submission["uuid"])
        workflow_api.create_workflow(submission["uuid"], steps or STEPS)
        return submission, new_student_item


class MockOraBlock:
    def __init__(self, requirements):
        self.requirements = requirements

    def workflow_requirements(self):
        return self.requirements
