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
from openassessment.workflow import api as workflow_api, workflow_batch_update_api as update_api

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
        _tim_sub, _tim = self._create_student_and_submission("Tim", "Tim's answer")
        self._create_student_and_submission("Miles", "Miles's answer")
        _pat_sub, _pat = self._create_student_and_submission("Pat", "Pat's answer")

        blocked = update_api.get_blocked_peer_workflows()
        # we expect 0 blocked submissions as they were just created
        self.assertEqual(len(blocked), 0)

        # set Tim's submission create_at date to >7 days ago
        # set Tim's peer workflow completion at 3 days ago
        pw_tim = PeerWorkflow.objects.get(student_id=_tim["student_id"])
        pw_tim.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_tim.completed_at = timezone.now() - datetime.timedelta(days=3)
        pw_tim.save()
        blocked = update_api.get_blocked_peer_workflows()
        # we expect 1 blocked submission
        self.assertEqual(len(blocked), 1)

        # set Pat's submission create_at date to >7 days ago and set completed_at date
        pw_pat = PeerWorkflow.objects.get(student_id=_pat["student_id"])
        pw_pat.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_pat.grading_completed_at = timezone.now() - datetime.timedelta(days=2)
        pw_pat.save()
        blocked = update_api.get_blocked_peer_workflows()
        # we still expect 1 blocked submission (Tim)
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0].student_id, 'Tim')

    def test_get_blocked_peer_workflows_for_course(self):
        _tim_sub, _tim = self._create_student_and_submission("Tim", "Tim's answer")
        _miles_sub, _miles = self._create_student_and_submission("Miles", "Miles's answer")
        _pat_sub, _pat = self._create_student_and_submission("Pat", "Pat's answer")

        blocked = update_api.get_blocked_peer_workflows(course_id="course_1")
        # we expect 0 blocked submissions for "course_1"
        self.assertEqual(len(blocked), 0)

        pw_tim = PeerWorkflow.objects.get(student_id=_tim["student_id"])
        pw_tim.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_tim.save()

        pw_pat = PeerWorkflow.objects.get(student_id=_pat["student_id"])
        pw_pat.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_pat.completed_at = timezone.now() - datetime.timedelta(days=3)
        pw_pat.course_id = "course_1"
        pw_pat.save()

        blocked = update_api.get_blocked_peer_workflows(course_id="course_1")
        # we expect 1 blocked submission for "course_1"
        self.assertEqual(len(blocked), 1)

        pw_miles = PeerWorkflow.objects.get(student_id=_miles["student_id"])
        pw_miles.course_id = "course_2"
        pw_miles.save()

        blocked = update_api.get_blocked_peer_workflows(course_id="course_2")
        # we expect 0 blocked submissions for "course_2"
        self.assertEqual(len(blocked), 0)

    def test_get_blocked_peer_workflows_for_ora_block(self):
        _tim_sub, _tim = self._create_student_and_submission("Tim", "Tim's answer")
        _miles_sub, _miles = self._create_student_and_submission("Miles", "Miles's answer")
        _pat_sub, _pat = self._create_student_and_submission("Pat", "Pat's answer")

        blocked = update_api.get_blocked_peer_workflows(item_id="item_1")
        # we expect 0 blocked submissions for "item_1"
        self.assertEqual(len(blocked), 0)

        pw_tim = PeerWorkflow.objects.get(student_id=_tim["student_id"])
        pw_tim.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_tim.save()

        pw_pat = PeerWorkflow.objects.get(student_id=_pat["student_id"])
        pw_pat.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_pat.completed_at = timezone.now() - datetime.timedelta(days=3)
        pw_pat.item_id = "item_1"
        pw_pat.save()

        blocked = update_api.get_blocked_peer_workflows(item_id="item_1")
        # we expect 1 blocked submission for "item_1"
        self.assertEqual(len(blocked), 1)

        pw_miles = PeerWorkflow.objects.get(student_id=_miles["student_id"])
        pw_miles.item_id = "item_2"
        pw_miles.save()

        blocked = update_api.get_blocked_peer_workflows(item_id="item_2")
        # we expect 0 blocked submissions for "item_2"
        self.assertEqual(len(blocked), 0)

    def test_is_flexible_peer_grading_on(self):
        assessment_requirements = {"peer": {
            "must_grade": 2,
            "must_be_graded_by": 3,
            "enable_flexible_grading": True
        }}
        course_settings = {
            'force_on_flexible_peer_openassessments': False}
        self.assertTrue(update_api.is_flexible_peer_grading_on(assessment_requirements, course_settings))

        assessment_requirements['peer']['enable_flexible_grading'] = False
        self.assertFalse(update_api.is_flexible_peer_grading_on(assessment_requirements, course_settings))

        assessment_requirements['peer']['enable_flexible_grading'] = False
        self.assertFalse(update_api.is_flexible_peer_grading_on(assessment_requirements, course_settings))

        del (assessment_requirements['peer']['enable_flexible_grading'])
        self.assertFalse(update_api.is_flexible_peer_grading_on(assessment_requirements, course_settings))

        del (assessment_requirements['peer'])
        self.assertFalse(update_api.is_flexible_peer_grading_on(assessment_requirements, course_settings))

        course_settings['force_on_flexible_peer_openassessments'] = True
        self.assertTrue(update_api.is_flexible_peer_grading_on(assessment_requirements, course_settings))

    @patch('openassessment.workflow.workflow_batch_update_api.modulestore')
    @patch('openassessment.workflow.workflow_batch_update_api.UsageKey.from_string')
    def test_get_workflow_update_data(self, mocked_from_string, mocked_modulestore):
        mocked_modulestore.return_value = MockModulestore()
        mocked_from_string.side_effect = mock_from_string

        peer_workflows = self.get_peer_workflows()
        wup = update_api.get_workflow_update_data(peer_workflows)

        self.assertEqual(len(wup["courses"]), 2)
        self.assertEqual(wup["courses"][0]["course_id"], "course_id_1")
        self.assertEqual(wup["courses"][0]["assessments"][0]["item_id"], "item_id_1")
        self.assertEqual(wup["courses"][0]["assessments"][1]["item_id"], "item_id_2")
        self.assertEqual(len(wup["courses"][0]["assessments"][0]["submissions"]), 2)
        self.assertEqual(wup["courses"][1]["course_id"], "course_id_2")
        self.assertEqual(wup["courses"][1]["assessments"][0]["item_id"], "item_id_3")

    def get_peer_workflows(self):
        _tim_sub, _tim = self._create_student_and_submission("Tim", "Tim's answer")
        _miles_sub, _miles = self._create_student_and_submission("Miles", "Miles's answer")
        _pat_sub, _pat = self._create_student_and_submission("Pat", "Pat's answer")
        _wayne_sub, _wayne = self._create_student_and_submission("Wayne", "Wayne's answer")

        pw_tim = PeerWorkflow.objects.get(student_id=_tim["student_id"])
        pw_tim.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_tim.course_id = "course_id_1"
        pw_tim.item_id = "item_id_1"
        pw_miles = PeerWorkflow.objects.get(student_id=_miles["student_id"])
        pw_miles.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_miles.course_id = "course_id_1"
        pw_miles.item_id = "item_id_2"
        pw_pat = PeerWorkflow.objects.get(student_id=_pat["student_id"])
        pw_pat.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_pat.course_id = "course_id_2"
        pw_pat.item_id = "item_id_3"
        pw_wayne = PeerWorkflow.objects.get(student_id=_wayne["student_id"])
        pw_wayne.created_at = timezone.now() - datetime.timedelta(days=8)
        pw_wayne.course_id = "course_id_1"
        pw_wayne.item_id = "item_id_1"

        return [pw_tim, pw_miles, pw_pat, pw_wayne]

    @patch('openassessment.workflow.workflow_batch_update_api._get_course_settings_and_assessment_requirements')
    @patch('openassessment.workflow.workflow_batch_update_api.get_blocked_peer_workflows')
    @patch('openassessment.workflow.api.update_from_assessments')
    def test_update_workflow_for_submission(self, mock_update_from_assessments,
                                            mock_get_blocked_peer_workflows,
                                            mock_get_workflow_update_data_for_submission):
        assessment_requirements = {"assessment_requirements_key": "assessment_requirements_val"}
        course_settings = {"course_settings_key": "course_settings_val"}

        mock_get_blocked_peer_workflows.return_value = "blocked_peer_workflows"
        mock_update_from_assessments.return_value = "workflow"
        mock_get_workflow_update_data_for_submission.return_value = course_settings, assessment_requirements

        update_api.update_workflow_for_submission("submission_uuid_1")
        mock_update_from_assessments.assert_called_once_with("submission_uuid_1",
                                                             assessment_requirements,
                                                             course_settings)

        # test scenario when cached data is passed
        assessment_requirements = {"assessment_requirements_key": "assessment_requirements_val_1"}
        course_settings = {"course_settings_key": "course_settings_val_1"}
        update_api.update_workflow_for_submission("submission_uuid_11", assessment_requirements, course_settings)
        mock_update_from_assessments.assert_called_with("submission_uuid_11", assessment_requirements, course_settings)

        # UpdateWorkflowForSubmissionException expected to be raised
        mock_update_from_assessments.side_effect = Exception()
        with pytest.raises(update_api.UpdateWorkflowForSubmissionException):
            update_api.update_workflow_for_submission("submission_uuid", "assessment_requirements",
                                                      "course_override")

    @patch('openassessment.workflow.workflow_batch_update_api.get_blocked_peer_workflows')
    def test_update_workflows_for_ora_block(self, mock_get_blocked_peer_workflows):
        workflow_update_data_for_ora = {
            "item_id": "item_id_11",
            "assessment_requirements": {"k12": "v12"},
            "submissions": ["submission_uuid_11"]
        }
        course_settings = {"course_setting_key": "course_setting_value"}

        mock_get_blocked_peer_workflows.return_value = "peer_workflows"
        with patch(
                'openassessment.workflow.workflow_batch_update_api._get_workflow_update_data_and_course_settings') \
                as mock_get_workflow_update_data_for_ora:
            mock_get_workflow_update_data_for_ora.return_value = workflow_update_data_for_ora, course_settings

            with patch(
                    'openassessment.workflow.tasks.update_workflow_for_submission_task.apply_async') \
                    as mock_update_workflow_for_submission_async:
                # test scenario when cached data is not passed
                update_api.update_workflows_for_ora_block("item_id_12")

                mock_get_blocked_peer_workflows.assert_called_once_with(item_id="item_id_12")
                mock_get_workflow_update_data_for_ora.assert_called_once_with("peer_workflows", "item_id_12")
                mock_update_workflow_for_submission_async.assert_called_once_with(
                    ["submission_uuid_11", {'k12': 'v12'}, {"course_setting_key": "course_setting_value"}])
                #
                # test scenario when cached data is passed
                workflow_update_data_for_ora["item_id"] = "item_id_0"
                workflow_update_data_for_ora["submissions"][0] = "submission_uuid_0"
                workflow_update_data_for_ora["assessment_requirements"] = {'k1': 'v1'}
                course_settings = {'csk_0': 'csv_0'}
                update_api.update_workflows_for_ora_block("item_id_0", workflow_update_data_for_ora, course_settings)
                mock_update_workflow_for_submission_async.assert_called_with(["submission_uuid_0",
                                                                              {'k1': 'v1'},
                                                                              {'csk_0': 'csv_0'}])

                # UpdateWorkflowsForOraBlockException expected to be raised
                mock_update_workflow_for_submission_async.side_effect = Exception()
                with pytest.raises(update_api.UpdateWorkflowsForOraBlockException):
                    update_api.update_workflows_for_ora_block("item_id_0")

    @patch('openassessment.workflow.workflow_batch_update_api.get_blocked_peer_workflows')
    def test_update_workflows_for_course(self, mock_get_blocked_peer_workflows):
        workflow_update_data = {"courses": [{
            "course_id": "course_id_11",
            "course_settings": {"k11": "v11"},
            "assessments": [
                {
                    "item_id": "item_id_11",
                    "assessment_requirements": {"k12": "v12"},
                    "submissions": ["submission_uuid_11"]
                },
                {
                    "item_id": "item_id_21",
                    "assessment_requirements": {"k21": "v21"},
                    "submissions": ["submission_uuid_21", "submission_uuid_22"]
                }
            ]
        }]}

        mock_get_blocked_peer_workflows.return_value = "mock_peer_workflows"
        with patch(
                'openassessment.workflow.workflow_batch_update_api.get_workflow_update_data') \
                as mock_get_workflow_update_data:
            mock_get_workflow_update_data.return_value = workflow_update_data
            with patch(
                    'openassessment.workflow.tasks.update_workflows_for_ora_block_task.apply_async') \
                    as mock_update_workflows_for_ora_block_async:

                # test scenario when cached data is not passed
                update_api.update_workflows_for_course("course_id_11")

                mock_get_blocked_peer_workflows.assert_called_once_with(course_id="course_id_11")
                mock_get_workflow_update_data.assert_called_once_with("mock_peer_workflows")
                ora_data = workflow_update_data["courses"][0]["assessments"][1]
                course_settings = workflow_update_data["courses"][0]["course_settings"]
                mock_update_workflows_for_ora_block_async.assert_called_with(
                    ["item_id_21", ora_data, course_settings])
                self.assertEqual(mock_update_workflows_for_ora_block_async.call_count, 2)

                # test scenario when cached data is passed
                workflow_update_data["courses"][0]["course_id"] = "course_id_0"
                workflow_update_data["courses"][0]["assessments"][0]["item_id"] = "item_id_0"
                workflow_update_data["courses"][0]["assessments"][1]["item_id"] = "item_id_01"

                update_api.update_workflows_for_course("course_id_0", workflow_update_data["courses"][0])
                mock_update_workflows_for_ora_block_async.assert_called_with(
                    ["item_id_01",
                     ora_data,
                     course_settings])
                self.assertEqual(mock_update_workflows_for_ora_block_async.call_count, 4)

                # UpdateWorkflowsForCourseException expected to be raised
                mock_get_workflow_update_data.side_effect = Exception()
                with pytest.raises(update_api.UpdateWorkflowsForCourseException):
                    update_api.update_workflows_for_course("course_id_0")

    @patch('openassessment.workflow.workflow_batch_update_api.get_blocked_peer_workflows')
    def test_update_workflows_for_all_blocked_submissions(self, mock_get_blocked_peer_workflows):
        workflow_update_data = {
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
                'openassessment.workflow.workflow_batch_update_api.get_workflow_update_data') \
                as mock_get_workflow_update_data:
            mock_get_workflow_update_data.return_value = workflow_update_data

            with patch(
                    'openassessment.workflow.tasks.update_workflows_for_course_task.apply_async') \
                    as mock_update_workflows_for_course:
                update_api.update_workflows_for_all_blocked_submissions()
                mock_get_blocked_peer_workflows.assert_called_once()
                mock_get_workflow_update_data.assert_called_once_with("mock_peer_workflows")

                mock_update_workflows_for_course.assert_called_once_with(["course_id_11", {
                    "course_id": "course_id_11",
                    "course_settings": {"k11": "v11"},
                    "assessments": []
                }])

    # pylint: disable=protected-access
    def test_get_course_data(self):
        workflow_update_data = {
            "courses": [
                {
                    "course_id": "course_id_1",
                    "course_settings": {"k1": "v1"},
                    "assessments": []
                },
                {
                    "course_id": "course_id_12",
                    "course_settings": {"k12": "v12"},
                    "assessments": []
                }
            ]
        }
        course = update_api._get_course_data(workflow_update_data, "course_id_1")
        self.assertEqual(course["course_id"], "course_id_1")

        course = update_api._get_course_data(workflow_update_data, "course_id_2")
        self.assertIsNone(course)
        course = update_api._get_course_data(workflow_update_data, None)
        self.assertIsNone(course)
        course = update_api._get_course_data(None, "course_id_2")
        self.assertIsNone(course)
        course = update_api._get_course_data({}, "course_id_2")
        self.assertIsNone(course)

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
