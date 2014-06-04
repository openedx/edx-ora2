# coding=utf-8
from collections import namedtuple
import pytz
import json
from mock import Mock, patch
from django.test.utils import override_settings
from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.assessment.api import ai as ai_api
from openassessment.workflow import api as workflow_api
from openassessment.assessment.errors.ai import AIError, AIGradingInternalError, AITrainingInternalError
from submissions import api as sub_api
from openassessment.xblock.test.base import scenario, XBlockHandlerTestCase
# Test dependency on Stub AI Algorithm configuration
from openassessment.assessment.test.test_ai import (
    ALGORITHM_ID, AI_ALGORITHMS, train_classifiers
)

STUDENT_ITEM = dict(
    student_id="Bob",
    course_id="test_course",
    item_id="item_one",
    item_type="openassessment",
)

ASSESSMENT_DICT = {
    'overall_feedback': u"这是中国",
    'options_selected': {
        "Concise": "Robert Heinlein",
        "Clear-headed": "Yogi Berra",
        "Form": "Reddit",
    },
}

EXAMPLE_BASED_ASSESSMENT = {
    "name": "example-based-assessment",
    "algorithm_id": "1",
    "examples": [
        {
            "answer": "Foo",
            "options_selected": [
                {
                    "criterion": "Ideas",
                    "option": "Fair"
                },
                {
                    "criterion": "Content",
                    "option": "Good"
                }
            ]
        },
        {
            "answer": "Bar",
            "options_selected": [
                {
                    "criterion": "Ideas",
                    "option": "Poor"
                },
                {
                    "criterion": "Content",
                    "option": "Good"
                }
            ]
        }
    ]
}

# Rubric-specific classifier score override
CLASSIFIER_SCORE_OVERRIDES = {
    u"Ideas": {'score_override': 1},
    u"Content": {'score_override': 2}
}


class TestCourseStaff(XBlockHandlerTestCase):
    """
    Tests for course staff debug panel.
    """

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_is_course_staff(self, xblock):
        # By default, we shouldn't be course staff
        self.assertFalse(xblock.is_course_staff)

        # If the LMS runtime tells us we're not course staff,
        # we shouldn't be course staff.
        xblock.xmodule_runtime = Mock(user_is_staff=False)
        self.assertFalse(xblock.is_course_staff)

        # If the LMS runtime tells us that we ARE course staff,
        # then we're course staff.
        xblock.xmodule_runtime.user_is_staff = True
        self.assertTrue(xblock.is_course_staff)

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_course_staff_debug_info(self, xblock):
        # If we're not course staff, we shouldn't see the debug info
        xblock.xmodule_runtime =  self._create_mock_runtime(
            xblock.scope_ids.usage_id, False, False, "Bob"
        )
        resp = self.request(xblock, 'render_staff_info', json.dumps({}))
        self.assertNotIn("course staff information", resp.decode('utf-8').lower())

        # If we ARE course staff, then we should see the debug info
        xblock.xmodule_runtime.user_is_staff = True
        resp = self.request(xblock, 'render_staff_info', json.dumps({}))
        self.assertIn("course staff information", resp.decode('utf-8').lower())

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_course_student_debug_info(self, xblock):
        # If we're not course staff, we shouldn't see the debug info
        xblock.xmodule_runtime =  self._create_mock_runtime(
            xblock.scope_ids.usage_id, False, False, "Bob"
        )
        resp = self.request(xblock, 'render_student_info', json.dumps({}))
        self.assertIn("you do not have permission", resp.decode('utf-8').lower())

        # If we ARE course staff, then we should see the debug info
        xblock.xmodule_runtime.user_is_staff = True
        resp = self.request(xblock, 'render_student_info', json.dumps({}))
        self.assertIn("couldn\'t find a response for this student.", resp.decode('utf-8').lower())

    @scenario('data/basic_scenario.xml')
    def test_hide_course_staff_debug_info_in_studio_preview(self, xblock):
        # If we are in Studio preview mode, don't show the staff debug info
        # In this case, the runtime will tell us that we're staff,
        # but no user ID will be set.
        xblock.xmodule_runtime =  self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        # If the client requests the staff info directly, they should get an error
        resp = self.request(xblock, 'render_staff_info', json.dumps({}))
        self.assertNotIn("course staff information", resp.decode('utf-8').lower())
        self.assertIn("do not have permission", resp.decode('utf-8').lower())

        # The container page should not contain a staff info section at all
        xblock_fragment = self.runtime.render(xblock, 'student_view')
        self.assertNotIn(u'staff-info', xblock_fragment.body_html())

    @scenario('data/staff_dates_scenario.xml', user_id='Bob')
    def test_staff_debug_dates_table(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime =  self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        # Verify that we can render without error
        resp = self.request(xblock, 'render_staff_info', json.dumps({}))
        decoded_response = resp.decode('utf-8').lower()
        self.assertIn("course staff information", decoded_response)

        # Confirm example-based-assessment does not show up; it is not date
        # driven so its start / due dates are not relevant
        self.assertNotIn("example-based-assessment", decoded_response)
        # Check all release dates.
        self.assertIn("march 1, 2014", decoded_response)
        self.assertIn("jan. 2, 2015", decoded_response)
        self.assertIn("jan. 2, 2016", decoded_response)

        # Check all due dates.
        self.assertIn("april 1, 2014", decoded_response)
        self.assertIn("april 1, 2015", decoded_response)
        self.assertIn("april 1, 2016", decoded_response)

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_staff_debug_dates_distant_past_and_future(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime =  self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        # Verify that we can render without error
        resp = self.request(xblock, 'render_staff_info', json.dumps({}))
        self.assertIn("course staff information", resp.decode('utf-8').lower())
        self.assertIn("n/a", resp.decode('utf-8').lower())

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_staff_debug_student_info_no_submission(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime =  self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        request = namedtuple('Request', 'params')
        request.params = {"student_id": "test_student"}
        # Verify that we can render without error
        resp = xblock.render_student_info(request)
        self.assertIn("couldn\'t find a response for this student.", resp.body.lower())

    @scenario('data/peer_only_scenario.xml', user_id='Bob')
    def test_staff_debug_student_info_peer_only(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime =  self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        # Create a submission for Bob, and corresponding workflow.
        submission = sub_api.create_submission(bob_item, {'text':"Bob Answer"})
        peer_api.create_peer_workflow(submission["uuid"])
        workflow_api.create_workflow(submission["uuid"], ['peer'])

        # Create a submission for Tim, and corresponding workflow.
        tim_item = bob_item.copy()
        tim_item["student_id"] = "Tim"
        tim_sub = sub_api.create_submission(tim_item, "Tim Answer")
        peer_api.create_peer_workflow(tim_sub["uuid"])
        workflow_api.create_workflow(tim_sub["uuid"], ['peer', 'self'])

        # Bob assesses Tim.
        peer_api.get_submission_to_assess(submission['uuid'], 1)
        peer_api.create_assessment(
            submission["uuid"],
            STUDENT_ITEM["student_id"],
            ASSESSMENT_DICT['options_selected'], dict(), "",
            {'criteria': xblock.rubric_criteria},
            1,
        )

        # Now Bob should be fully populated in the student info view.
        request = namedtuple('Request', 'params')
        request.params = {"student_id": "Bob"}
        # Verify that we can render without error
        path, context = xblock.get_student_info_path_and_context(request)
        self.assertEquals("Bob Answer", context['submission']['answer']['text'])
        self.assertIsNone(context['self_assessment'])
        self.assertEquals("openassessmentblock/staff_debug/student_info.html", path)

    @scenario('data/self_only_scenario.xml', user_id='Bob')
    def test_staff_debug_student_info_self_only(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime =  self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        # Create a submission for Bob, and corresponding workflow.
        submission = sub_api.create_submission(bob_item, {'text':"Bob Answer"})
        peer_api.create_peer_workflow(submission["uuid"])
        workflow_api.create_workflow(submission["uuid"], ['self'])

        # Bob assesses himself.
        self_api.create_assessment(
            submission['uuid'],
            STUDENT_ITEM["student_id"],
            ASSESSMENT_DICT['options_selected'],
            {'criteria': xblock.rubric_criteria},
        )

        # Now Bob should be fully populated in the student info view.
        request = namedtuple('Request', 'params')
        request.params = {"student_id": "Bob"}
        # Verify that we can render without error
        path, context = xblock.get_student_info_path_and_context(request)
        self.assertEquals("Bob Answer", context['submission']['answer']['text'])
        self.assertEquals([], context['peer_assessments'])
        self.assertEquals("openassessmentblock/staff_debug/student_info.html", path)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_staff_debug_student_info_full_workflow(self, xblock):
        # Train classifiers.
        example_based_assessment = xblock.get_assessment_module('example-based-assessment')
        example_based_assessment['algorithm_id'] = ALGORITHM_ID
        train_classifiers({'criteria': xblock.rubric_criteria}, CLASSIFIER_SCORE_OVERRIDES)

        # Commonly chosen options for assessments
        options_selected = {
            "Ideas": "Good",
            "Content": "Poor",
        }

        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        # Create a submission for Bob, and corresponding workflow.
        submission = sub_api.create_submission(bob_item, {'text':"Bob Answer"})
        peer_api.create_peer_workflow(submission["uuid"])
        workflow_api.create_workflow(submission["uuid"], ['peer', 'self'])

        # Create a submission for Tim, and corresponding workflow.
        tim_item = bob_item.copy()
        tim_item["student_id"] = "Tim"
        tim_sub = sub_api.create_submission(tim_item, "Tim Answer")
        peer_api.create_peer_workflow(tim_sub["uuid"])
        workflow_api.create_workflow(tim_sub["uuid"], ['peer', 'self'])

        # Bob assesses Tim.
        peer_api.get_submission_to_assess(submission['uuid'], 1)
        peer_api.create_assessment(
            submission["uuid"],
            STUDENT_ITEM["student_id"],
            options_selected, dict(), "",
            {'criteria': xblock.rubric_criteria},
            1,
        )

        # Bob assesses himself.
        self_api.create_assessment(
            submission['uuid'],
            STUDENT_ITEM["student_id"],
            options_selected,
            {'criteria': xblock.rubric_criteria},
        )

        # Now Bob should be fully populated in the student info view.
        request = namedtuple('Request', 'params')
        request.params = {"student_id": "Bob"}
        # Verify that we can render without error
        resp = xblock.render_student_info(request)
        self.assertIn("bob answer", resp.body.lower())

    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_display_schedule_training(self, xblock):
        xblock.rubric_assessments.append(EXAMPLE_BASED_ASSESSMENT)
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )
        path, context = xblock.get_staff_path_and_context()
        self.assertEquals('openassessmentblock/staff_debug/staff_debug.html', path)
        self.assertTrue(context['display_schedule_training'])

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_schedule_training(self, xblock):
        example_based_assessment = xblock.get_assessment_module('example-based-assessment')
        example_based_assessment['algorithm_id'] = ALGORITHM_ID
        train_classifiers({'criteria': xblock.rubric_criteria}, CLASSIFIER_SCORE_OVERRIDES)
        xblock.rubric_assessments.append(EXAMPLE_BASED_ASSESSMENT)
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )
        response = self.request(xblock, 'schedule_training', json.dumps({}), response_format='json')
        self.assertTrue(response['success'], msg=response.get('msg'))
        self.assertTrue('workflow_uuid' in response)

    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_not_displaying_schedule_training(self, xblock):
        xblock.rubric_assessments.append(EXAMPLE_BASED_ASSESSMENT)
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        path, context = xblock.get_staff_path_and_context()
        self.assertEquals('openassessmentblock/staff_debug/staff_debug.html', path)
        self.assertFalse(context['display_schedule_training'])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_admin_schedule_training_no_permissions(self, xblock):
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        response = self.request(xblock, 'schedule_training', json.dumps({}), response_format='json')
        self.assertFalse(response['success'])
        self.assertTrue('permission' in response['msg'])

    @patch.object(ai_api, "train_classifiers")
    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_admin_schedule_training_error(self, xblock, mock_api):
        mock_api.side_effect = AIError("Oh no!")
        xblock.rubric_assessments.append(EXAMPLE_BASED_ASSESSMENT)
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )
        response = self.request(xblock, 'schedule_training', json.dumps({}), response_format='json')
        self.assertFalse(response['success'])
        self.assertTrue('error' in response['msg'])

    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_display_reschedule_unfinished_grading_tasks(self, xblock):
        xblock.rubric_assessments.append(EXAMPLE_BASED_ASSESSMENT)
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )
        path, context = xblock.get_staff_path_and_context()
        self.assertEquals('openassessmentblock/staff_debug/staff_debug.html', path)
        self.assertTrue(context['display_reschedule_unfinished_tasks'])

    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_reschedule_unfinished_grading_tasks_no_permissions(self, xblock):
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        response = self.request(xblock, 'reschedule_unfinished_tasks', json.dumps({}), response_format='json')
        self.assertFalse(response['success'])
        self.assertTrue('permission' in response['msg'])

    @patch.object(ai_api, "reschedule_unfinished_tasks")
    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_reschedule_unfinished_grading_tasks_success(self, xblock, mock_api):
        mock_api.side_effect = Mock()
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )
        response = self.request(xblock, 'reschedule_unfinished_tasks', json.dumps({}), response_format='json')
        self.assertTrue(response['success'])
        self.assertTrue(u'All' in response['msg'])
        mock_api.assert_called_with(
            course_id=unicode(STUDENT_ITEM.get('course_id')), item_id=unicode(xblock.scope_ids.usage_id),
            task_type=u"grade"
        )

    @patch.object(ai_api, "reschedule_unfinished_tasks")
    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_reschedule_unfinished_grading_tasks_error(self, xblock, mock_api):
        mock_api.side_effect = AIGradingInternalError("Oh Noooo!")
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )
        response = self.request(xblock, 'reschedule_unfinished_tasks', json.dumps({}), response_format='json')
        self.assertFalse(response['success'])
        self.assertTrue('error' in response['msg'])

    @scenario('data/peer_only_scenario.xml', user_id='Bob')
    def test_no_example_based_assessment(self, xblock):
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )
        response = self.request(xblock, 'schedule_training', json.dumps({}), response_format='json')
        self.assertFalse(response['success'])
        self.assertTrue('not configured' in response['msg'])

    def _create_mock_runtime(self, item_id, is_staff, is_admin, anonymous_user_id):
        mock_runtime = Mock(
            course_id='test_course',
            item_id=item_id,
            anonymous_student_id='Bob',
            user_is_staff=is_staff,
            user_is_admin=is_admin,
            service=lambda self, service: Mock(
                get_anonymous_student_id=lambda user_id, course_id: anonymous_user_id
            )
        )
        return mock_runtime
