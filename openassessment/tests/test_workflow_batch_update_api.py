"""
Tests batch ORA workflow update API
"""
import datetime
import logging
from django.utils import timezone
from mock import patch
import pytest

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

    # pylint: disable=protected-access
    def test_add_workflow_update_parameters(self):
        data = {}

        update_api._add_workflow_update_parameters(data, "course_id_1", "item_id_1", "submission_uuid_1", {"k1": "v1"},
                                                   {"k2": "v2"})

        self.assertEqual(data["courses"][0]["course_id"], "course_id_1")
        self.assertEqual(data["courses"][0]["course_settings"], {"k1": "v1"})
        self.assertEqual(data["courses"][0]["assessments"][0]["item_id"], "item_id_1")
        self.assertEqual(data["courses"][0]["assessments"][0]["assessment_requirements"], {"k2": "v2"})
        self.assertEqual(data["courses"][0]["assessments"][0]["submissions"][0]["submission_uuid"], "submission_uuid_1")

        # add another course
        update_api._add_workflow_update_parameters(data, "course_id_2", "item_id_2", "submission_uuid_2",
                                                   {"k21": "v21"},
                                                   {"k22": "v22"})

        # verify existing data was not affected
        self.assertEqual(data["courses"][0]["course_id"], "course_id_1")
        self.assertEqual(data["courses"][0]["course_settings"], {"k1": "v1"})
        self.assertEqual(data["courses"][0]["assessments"][0]["item_id"], "item_id_1")
        self.assertEqual(data["courses"][0]["assessments"][0]["assessment_requirements"], {"k2": "v2"})
        self.assertEqual(data["courses"][0]["assessments"][0]["submissions"][0]["submission_uuid"], "submission_uuid_1")

        # verify new course structure was added
        self.assertEqual(data["courses"][1]["course_id"], "course_id_2")
        self.assertEqual(data["courses"][1]["course_settings"], {"k21": "v21"})
        self.assertEqual(data["courses"][1]["assessments"][0]["item_id"], "item_id_2")
        self.assertEqual(data["courses"][1]["assessments"][0]["assessment_requirements"], {"k22": "v22"})
        self.assertEqual(data["courses"][1]["assessments"][0]["submissions"][0]["submission_uuid"], "submission_uuid_2")

        # add submission uuid
        update_api._add_workflow_update_parameters(data, "course_id_1", "item_id_1", "submission_uuid_12", {"k1": "v1"},
                                                   {"k2": "v2"})

        self.assertEqual(data["courses"][0]["assessments"][0]["submissions"][1]["submission_uuid"],
                         "submission_uuid_12")

    @patch('openassessment.workflow_batch_update_api.modulestore')
    @patch('openassessment.workflow_batch_update_api.UsageKey.from_string')
    def test_get_workflow_update_parameters(self, mocked_from_string, mocked_modulestore):
        mocked_modulestore.return_value = MockModulestore()
        mocked_from_string.side_effect = mock_from_string
        #
        peer_workflows = self.get_peer_workflows_for_test_get_workflow_update_parameters()
        wup = update_api.get_workflow_update_parameters(peer_workflows)

        #
        self.assertEqual(len(wup["courses"]), 2)
        self.assertEqual(wup["courses"][0]["course_id"], "course_id_1")
        self.assertEqual(wup["courses"][0]["assessments"][0]["item_id"], "item_id_1")
        self.assertEqual(wup["courses"][0]["assessments"][1]["item_id"], "item_id_2")
        self.assertEqual(wup["courses"][1]["course_id"], "course_id_2")
        self.assertEqual(wup["courses"][1]["assessments"][0]["item_id"], "item_id_3")

    # pylint: disable=unused-variable
    def get_peer_workflows_for_test_get_workflow_update_parameters(self):
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")
        miles_sub, miles = self._create_student_and_submission("Miles", "Miles's answer")
        pat_sub, pat = self._create_student_and_submission("Pat", "Pat's answer")

        pw_tim = PeerWorkflow.objects.get(student_id=tim["student_id"])
        pw_tim.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_tim.course_id = "course_id_1"
        pw_tim.item_id = "item_id_1"
        pw_miles = PeerWorkflow.objects.get(student_id=miles["student_id"])
        pw_miles.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_miles.course_id = "course_id_1"
        pw_miles.item_id = "item_id_2"
        pw_pat = PeerWorkflow.objects.get(student_id=pat["student_id"])
        pw_pat.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_pat.course_id = "course_id_2"
        pw_pat.item_id = "item_id_3"

        return [pw_tim, pw_miles, pw_pat]

    @patch('openassessment.workflow.api.update_from_assessments')
    def test_update_workflow_for_submission(self, mock_update_from_assessments):
        mock_update_from_assessments.return_value = "workflow"

        workflow = update_api.update_workflow_for_submission("submission_uuid", "assessment_requirements",
                                                             "course_override")
        mock_update_from_assessments.assert_called_once_with("submission_uuid", "assessment_requirements",
                                                             "course_override")
        self.assertEqual(workflow, "workflow")

        # UpdateWorkflowForSubmissionException expected to be raised
        mock_update_from_assessments.side_effect = Exception()
        with pytest.raises(update_api.UpdateWorkflowForSubmissionException):
            update_api.update_workflow_for_submission("submission_uuid", "assessment_requirements",
                                                      "course_override")

    @patch('openassessment.workflow_batch_update_api.get_blocked_peer_workflows_for_ora_block')
    def test_update_workflows_for_ora_block(self, mock_get_blocked_peer_workflows_for_ora_block):
        workflow_update_parameters = {
            "courses": [
                {
                    "course_id": "course_id_11",
                    "course_settings": {"k11": "v11"},
                    "assessments": [
                        {
                            "item_id": "item_id_11",
                            "assessment_requirements": {"k12": "v12"},
                            "submissions": [
                                {"submission_uuid": "submission_uuid_11"}
                            ]
                        },
                        {
                            "item_id": "item_id_12",
                            "assessment_requirements": {"k12": "v12"},
                            "submissions": [
                                {"submission_uuid": "submission_uuid_12"}
                            ]
                        }
                    ]
                }
            ]
        }

        mock_get_blocked_peer_workflows_for_ora_block.return_value = "peer_workflows"
        with patch(
                'openassessment.workflow_batch_update_api.get_workflow_update_parameters') \
                as mock_get_workflow_update_parameters:
            mock_get_workflow_update_parameters.return_value = workflow_update_parameters

            with patch(
                    'openassessment.workflow_batch_update_api.update_workflow_for_submission_task.apply_async') \
                    as mock_update_workflow_for_submission:
                # test scenario when cached data is not passed
                update_api.update_workflows_for_ora_block("item_id_12")

                mock_get_blocked_peer_workflows_for_ora_block.assert_called_once_with("item_id_12")
                mock_get_workflow_update_parameters.assert_called_once_with("peer_workflows")
                mock_update_workflow_for_submission.assert_called_once_with(["submission_uuid_12", {'k12': 'v12'},
                                                                             {'k11': 'v11'}])

                # test scenario when cached data is passed
                workflow_update_parameters["courses"][0]["assessments"][0]["item_id"] = "item_id_0"
                workflow_update_parameters["courses"][0]["assessments"][0]["submissions"][0][
                    "submission_uuid"] = "submission_uuid_0"
                workflow_update_parameters["courses"][0]["course_settings"] = {'k0': 'v0'}
                workflow_update_parameters["courses"][0]["assessments"][0]["assessment_requirements"] = {'k1': 'v1'}
                update_api.update_workflows_for_ora_block("item_id_0")
                mock_update_workflow_for_submission.assert_called_with(["submission_uuid_0",
                                                                        {'k1': 'v1'},
                                                                        {'k0': 'v0'}])

                # UpdateWorkflowsForOraBlockException expected to be raised
                mock_update_workflow_for_submission.side_effect = Exception()
                with pytest.raises(update_api.UpdateWorkflowsForOraBlockException):
                    update_api.update_workflows_for_ora_block("item_id_0")

    @patch('openassessment.workflow_batch_update_api.get_blocked_peer_workflows_for_course')
    def test_update_workflows_for_course(self, mock_get_blocked_peer_workflows_for_course):
        workflow_update_parameters = {
            "courses": [
                {
                    "course_id": "course_id_11",
                    "course_settings": {"k11": "v11"},
                    "assessments": [
                        {
                            "item_id": "item_id_11",
                            "assessment_requirements": {"k12": "v12"},
                            "submissions": [{"submission_uuid": "submission_uuid_11"}]
                        },
                        {
                            "item_id": "item_id_12",
                            "assessment_requirements": {"k12": "v12"},
                            "submissions": [{"submission_uuid": "submission_uuid_12"}]
                        }
                    ]
                }
            ]
        }
        mock_get_blocked_peer_workflows_for_course.return_value = "mock_peer_workflows"
        with patch(
                'openassessment.workflow_batch_update_api.get_workflow_update_parameters') \
                as mock_get_workflow_update_parameters:
            mock_get_workflow_update_parameters.return_value = workflow_update_parameters
            with patch(
                    'openassessment.workflow_batch_update_api.update_workflows_for_ora_block_task.apply_async') \
                    as mock_update_workflows_for_ora_block:
                # test scenario when cached data is not passed
                update_api.update_workflows_for_course("course_id_11")

                mock_get_blocked_peer_workflows_for_course.assert_called_once_with("course_id_11")
                mock_get_workflow_update_parameters.assert_called_once_with("mock_peer_workflows")

                mock_update_workflows_for_ora_block.assert_called_with(["item_id_12", workflow_update_parameters])
                self.assertEqual(mock_update_workflows_for_ora_block.call_count, 2)

                # test scenario when cached data is passed
                workflow_update_parameters["courses"][0]["course_id"] = "course_id_0"
                workflow_update_parameters["courses"][0]["assessments"][0]["item_id"] = "item_id_0"
                workflow_update_parameters["courses"][0]["assessments"][1]["item_id"] = "item_id_01"
                update_api.update_workflows_for_course("course_id_0", workflow_update_parameters)
                mock_update_workflows_for_ora_block.assert_called_with(["item_id_01", workflow_update_parameters])
                self.assertEqual(mock_update_workflows_for_ora_block.call_count, 4)

                # UpdateWorkflowsForCourseException expected to be raised
                mock_update_workflows_for_ora_block.side_effect = Exception()
                with pytest.raises(update_api.UpdateWorkflowsForCourseException):
                    update_api.update_workflows_for_course("course_id_0", workflow_update_parameters)

    @patch('openassessment.workflow_batch_update_api.get_blocked_peer_workflows')
    def test_update_workflows_for_all_blocked_submissions(self, mock_get_blocked_peer_workflows):
        workflow_update_parameters = {
            "courses": [
                {
                    "course_id": "course_id_11",
                    "course_settings": {"k11": "v11"},
                    "assessments": []
                }
            ]
        }
        mock_get_blocked_peer_workflows.return_value = "mock_peer_workflows"
        with patch(
                'openassessment.workflow_batch_update_api.get_workflow_update_parameters') \
                as mock_get_workflow_update_parameters:
            mock_get_workflow_update_parameters.return_value = workflow_update_parameters

            with patch(
                    'openassessment.workflow_batch_update_api.update_workflows_for_course_task.apply_async') \
                    as mock_update_workflows_for_course:
                update_api.update_workflows_for_all_blocked_submissions()
                mock_get_blocked_peer_workflows.assert_called_once()
                mock_get_workflow_update_parameters.assert_called_once_with("mock_peer_workflows")

                mock_update_workflows_for_course.assert_called_once_with(["course_id_11", workflow_update_parameters])

    def test_get_course_object(self):
        workflow_update_parameters = {
            "courses": [
                {
                    "course_id": "course_id_1",
                    "course_settings": {"k1": "v1"},
                    "assessments": []
                }
            ]
        }
        course = update_api._get_course_object(workflow_update_parameters, "course_id_1")
        self.assertEqual(course["course_id"], "course_id_1")

        course = update_api._get_course_object(workflow_update_parameters, "course_id_2")
        self.assertIsNone(course)

    # pylint: disable=protected-access
    def test_get_ora_object(self):
        workflow_update_parameters = {
            "courses": [
                {
                    "course_id": "course_id_11",
                    "course_settings": {
                        "k11": "v11"
                    },
                    "assessments": [
                        {
                            "item_id": "item_id_11",
                            "assessment_requirements": {
                                "k12": "v12"
                            },
                            "submissions": [
                                {
                                    "submission_uuid": "submission_uuid_11"
                                }
                            ]
                        },
                        {
                            "item_id": "item_id_12",
                            "assessment_requirements": {
                                "k12": "v12"
                            },
                            "submissions": [
                                {
                                    "submission_uuid": "submission_uuid_12"
                                },
                                {
                                    "submission_uuid": "submission_uuid_13"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        ora = update_api._get_ora_object(workflow_update_parameters, "item_id_12")
        self.assertEqual(ora["item_id"], "item_id_12")

        ora = update_api._get_ora_object(workflow_update_parameters, "item_id_12")
        self.assertEqual(len(ora["submissions"]), 2)

        ora = update_api._get_ora_object(workflow_update_parameters, "item_id_non_existing")
        self.assertIsNone(ora)

    def test_get_submission_object(self):
        workflow_update_parameters = {
            "courses": [
                {
                    "course_id": "course_id_11",
                    "course_settings": {
                        "k11": "v11"
                    },
                    "assessments": [
                        {
                            "item_id": "item_id_12",
                            "assessment_requirements": {
                                "k12": "v12"
                            },
                            "submissions": [
                                {
                                    "submission_uuid": "submission_uuid_12"
                                },
                                {
                                    "submission_uuid": "submission_uuid_13"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        submission = update_api._get_submission_object(workflow_update_parameters, "submission_uuid_12")
        self.assertEqual(submission["submission_uuid"], "submission_uuid_12")

        submission = update_api._get_submission_object(workflow_update_parameters, "non_existing")
        self.assertIsNone(submission)

    def test_get_course_settings_for_ora(self):
        workflow_update_parameters = {
            "courses": [
                {
                    "course_id": "course_id_11",
                    "course_settings": {"k11": "v11"},
                    "assessments": [
                        {
                            "item_id": "item_id_12",
                            "assessment_requirements": {"k12": "v12"},
                            "submissions": [
                                {"submission_uuid": "submission_uuid_12"},
                                {"submission_uuid": "submission_uuid_13"}
                            ]
                        }
                    ]
                }
            ]
        }
        course_settings = update_api._get_course_settings_for_ora(workflow_update_parameters, "item_id_12")
        self.assertEqual(course_settings, {"k11": "v11"})

        course_settings = update_api._get_course_settings_for_ora(workflow_update_parameters, "non_existing")
        self.assertIsNone(course_settings)

    @staticmethod
    def _create_student_and_submission(student, answer, date=None, steps=None):
        """ Creats a student and submission for tests. """
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student
        submission = sub_api.create_submission(new_student_item, answer, date)
        peer_api.on_start(submission["uuid"])
        workflow_api.create_workflow(submission["uuid"], steps or STEPS)
        return submission, new_student_item


def mock_from_string(*args):
    return args[0]


class MockOraBlock:
    def __init__(self, requirements):
        self.requirements = requirements

    def workflow_requirements(self):
        return self.requirements


class MockCourseBlock:
    def __init__(self, force_on_flexible_peer_openassessments):
        self.force_on_flexible_peer_openassessments = force_on_flexible_peer_openassessments


class MockModulestore:

    def get_item(self, block_key):

        workflow_requirements = {"peer": {
            "must_grade": 2,
            "must_be_graded_by": 3,
            "enable_flexible_grading": False
        }}

        if block_key == "item_id_1":
            return MockOraBlock(workflow_requirements)
        elif block_key == "item_id_2":
            workflow_requirements["peer"]["enable_flexible_grading"] = True
            return MockOraBlock(workflow_requirements)
        elif block_key == "item_id_3":
            workflow_requirements["peer"]["enable_flexible_grading"] = True
            return MockOraBlock(workflow_requirements)
        elif block_key == "course_id_1":
            return MockCourseBlock(True)
        elif block_key == "course_id_2":
            return MockCourseBlock(False)

        return None
