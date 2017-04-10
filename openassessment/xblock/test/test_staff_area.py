# coding=utf-8
"""
Tests for the staff area.
"""
from collections import namedtuple
import json
import datetime
import urllib
from mock import MagicMock, Mock, call, patch
from django.test.utils import override_settings

from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.assessment.api import staff as staff_api
from openassessment.assessment.api import ai as ai_api
from openassessment.workflow import api as workflow_api
from openassessment.assessment.errors.ai import AIError, AIGradingInternalError
from openassessment.fileupload.exceptions import FileUploadInternalError
from submissions import api as sub_api

from openassessment.xblock.data_conversion import prepare_submission_for_serialization
from openassessment.xblock.test.base import scenario, XBlockHandlerTestCase

ALGORITHM_ID = 'fake'

AI_ALGORITHMS = {
    'fake': 'openassessment.assessment.worker.algorithm.FakeAIAlgorithm'
}

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
    'criterion_feedback': {
        "Concise": "Not very.",
        "Clear-headed": "Indubitably",
        "Form": "s ka tter ed"
    }

}


class NullUserService(object):
    """
    A simple implementation of the runtime "user" service.
    """
    @staticmethod
    def get_anonymous_user_id(username, _):
        """
        A convenience method.
        """
        return username

    @staticmethod
    def get_current_user():
        """
        A convenience method.
        """
        return MagicMock(opt_attrs={})


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
    def test_course_staff_area(self, xblock):
        # If we're not course staff, we shouldn't see the staff area
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, False, False, "Bob"
        )
        resp = self.request(xblock, 'render_staff_area', json.dumps({}))
        self.assertNotIn("view assignment statistics", resp.decode('utf-8').lower())

        # If we ARE course staff, then we should see the debug info
        xblock.xmodule_runtime.user_is_staff = True
        resp = self.request(xblock, 'render_staff_area', json.dumps({}))
        self.assertIn("view assignment statistics", resp.decode('utf-8').lower())

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_course_student_debug_info(self, xblock):
        # If we're not course staff, we shouldn't see the debug info
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, False, False, "Bob"
        )
        resp = self.request(xblock, 'render_student_info', json.dumps({}))
        self.assertIn("you do not have permission", resp.decode('utf-8').lower())

        # If we ARE course staff, then we should see the debug info
        xblock.xmodule_runtime.user_is_staff = True
        resp = self.request(xblock, 'render_student_info', json.dumps({}))
        self.assertIn("a response was not found for this learner.", resp.decode('utf-8').lower())

    @scenario('data/basic_scenario.xml')
    def test_hide_course_staff_area_in_studio_preview(self, xblock):
        # If we are in Studio preview mode, don't show the staff area.
        # In this case, the runtime will tell us that we're staff,
        # but no user ID will be set.
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        # If the client requests the staff info directly, they should get an error
        resp = self.request(xblock, 'render_staff_area', json.dumps({}))
        self.assertNotIn("view assignment statistics", resp.decode('utf-8').lower())
        self.assertIn("do not have permission", resp.decode('utf-8').lower())

        # The container page should not contain a staff info section at all
        xblock_fragment = self.runtime.render(xblock, 'student_view')
        self.assertNotIn(u'staff-info', xblock_fragment.body_html())

    @scenario('data/staff_dates_scenario.xml', user_id='Bob')
    def test_staff_area_dates_table(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        # Verify that we can render without error
        resp = self.request(xblock, 'render_staff_area', json.dumps({}))
        decoded_response = resp.decode('utf-8').lower()
        self.assertIn("view assignment statistics", decoded_response)

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
    def test_staff_area_dates_distant_past_and_future(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        # Verify that we can render without error
        resp = self.request(xblock, 'render_staff_area', json.dumps({}))
        self.assertIn("view assignment statistics", resp.decode('utf-8').lower())
        self.assertIn("n/a", resp.decode('utf-8').lower())

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_staff_area_student_info_no_submission(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        request = namedtuple('Request', 'params')
        request.params = {"student_id": "test_student"}
        # Verify that we can render without error
        resp = xblock.render_student_info(request)
        self.assertIn("a response was not found for this learner.", resp.body.lower())

    @scenario('data/peer_only_scenario.xml', user_id='Bob')
    def test_staff_area_student_info_peer_only(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        xblock.runtime._services['user'] = NullUserService()  # pylint: disable=protected-access

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        # Create a submission for Bob, and corresponding workflow.
        submission = self._create_submission(
            bob_item, prepare_submission_for_serialization(("Bob Answer 1", "Bob Answer 2")), ['peer']
        )

        # Create a submission for Tim, and corresponding workflow.
        tim_item = bob_item.copy()
        tim_item["student_id"] = "Tim"
        self._create_submission(tim_item, "Tim Answer", ['peer', 'self'])

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
        path, context = xblock.get_student_info_path_and_context("Bob")
        self.assertEquals("Bob Answer 1", context['submission']['answer']['parts'][0]['text'])
        self.assertIsNotNone(context['peer_assessments'])
        self.assertIsNone(context['self_assessment'])
        self.assertIsNone(context['staff_assessment'])
        self.assertEquals("openassessmentblock/staff_area/oa_student_info.html", path)

        # Bob still needs to assess other learners
        self.assertIsNone(context['grade_details'])

    @scenario('data/self_only_scenario.xml', user_id='Bob')
    def test_staff_area_student_info_self_only(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        xblock.runtime._services['user'] = NullUserService()  # pylint: disable=protected-access
        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        # Create a submission for Bob, and corresponding workflow.
        submission = self._create_submission(
            bob_item, prepare_submission_for_serialization(("Bob Answer 1", "Bob Answer 2")), ['self']
        )

        # Bob assesses himself.
        self_api.create_assessment(
            submission['uuid'],
            STUDENT_ITEM["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            {'criteria': xblock.rubric_criteria},
        )

        path, context = xblock.get_student_info_path_and_context("Bob")
        self.assertEquals("Bob Answer 1", context['submission']['answer']['parts'][0]['text'])
        self.assertIsNone(context['peer_assessments'])
        self.assertIsNotNone(context['self_assessment'])
        self.assertIsNone(context['staff_assessment'])
        self.assertEquals("openassessmentblock/staff_area/oa_student_info.html", path)

        grade_details = context['grade_details']
        self.assertEquals(1, len(grade_details['criteria'][0]['assessments']))
        self.assertEquals('Self Assessment Grade', grade_details['criteria'][0]['assessments'][0]['title'])

    @scenario('data/feedback_only_criterion_staff.xml', user_id='Bob')
    def test_staff_area_student_info_staff_only_no_options(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        xblock.runtime._services['user'] = NullUserService()  # pylint: disable=protected-access
        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        # Create a submission for Bob, and corresponding workflow.
        submission = self._create_submission(
            bob_item, prepare_submission_for_serialization(("Bob Answer 1", "Bob Answer 2")), ['staff']
        )

        # Bob assesses himself as staff.
        staff_api.create_assessment(
            submission['uuid'],
            STUDENT_ITEM["student_id"],
            {},  # no options available
            {"vocabulary": "Good use of vocabulary!"},
            ASSESSMENT_DICT['overall_feedback'],
            {'criteria': xblock.rubric_criteria},
        )

        _, _ = xblock.get_student_info_path_and_context("Bob")  # pylint: disable=protected-access
        self.assertIn(
            "Good use of vocabulary!",
            self.request(
                xblock,
                "render_student_info",
                urllib.urlencode({"student_username": "Bob"})
            )
        )

    @scenario('data/staff_grade_scenario.xml', user_id='Bob')
    def test_staff_area_student_info_staff_only(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        xblock.runtime._services['user'] = NullUserService()  # pylint: disable=protected-access
        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        # Create a submission for Bob, and corresponding workflow.
        submission = self._create_submission(
            bob_item, prepare_submission_for_serialization(("Bob Answer 1", "Bob Answer 2")), ['staff']
        )

        # Bob assesses himself.
        staff_api.create_assessment(
            submission['uuid'],
            STUDENT_ITEM["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            {'criteria': xblock.rubric_criteria},
        )

        path, context = xblock.get_student_info_path_and_context("Bob")
        self.assertEquals("Bob Answer 1", context['submission']['answer']['parts'][0]['text'])
        self.assertIsNone(context['peer_assessments'])
        self.assertIsNone(context['self_assessment'])
        self.assertIsNotNone(context['staff_assessment'])
        self.assertEquals("openassessmentblock/staff_area/oa_student_info.html", path)

        grade_details = context['grade_details']
        self.assertEquals(1, len(grade_details['criteria'][0]['assessments']))
        self.assertEquals('Staff Grade', grade_details['criteria'][0]['assessments'][0]['title'])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_staff_area_student_info_with_cancelled_submission(self, xblock):
        requirements = {
            "peer": {
                "must_grade": 1,
                "must_be_graded_by": 1
            },
        }

        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        xblock.runtime._services['user'] = NullUserService()  # pylint: disable=protected-access

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        # Create a submission for Bob, and corresponding workflow.
        submission = self._create_submission(
            bob_item, prepare_submission_for_serialization(("Bob Answer 1", "Bob Answer 2")), ['peer']
        )

        workflow_api.cancel_workflow(
            submission_uuid=submission["uuid"],
            comments="Inappropriate language",
            cancelled_by_id=bob_item['student_id'],
            assessment_requirements=requirements
        )

        path, context = xblock.get_student_info_path_and_context("Bob")
        self.assertEquals("Bob Answer 1", context['submission']['answer']['parts'][0]['text'])
        self.assertIsNotNone(context['workflow_cancellation'])
        self.assertEquals("openassessmentblock/staff_area/oa_student_info.html", path)

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_cancelled_submission_peer_assessment_render_path(self, xblock):
        # Test that peer assessment path should be oa_peer_cancelled.html for a cancelled submission.
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        # Create a submission for Bob, and corresponding workflow.
        submission = self._create_submission(bob_item, {'text': "Bob Answer"}, ['peer'])

        requirements = {
            "peer": {
                "must_grade": 1,
                "must_be_graded_by": 1
            },
        }

        workflow_api.cancel_workflow(
            submission_uuid=submission['uuid'],
            comments="Inappropriate language",
            cancelled_by_id=bob_item['student_id'],
            assessment_requirements=requirements
        )

        xblock.submission_uuid = submission["uuid"]
        path, _ = xblock.peer_path_and_context(False)
        self.assertEquals("openassessmentblock/peer/oa_peer_cancelled.html", path)

    @scenario('data/self_only_scenario.xml', user_id='Bob')
    def test_staff_area_student_info_image_submission(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        xblock.runtime._services['user'] = NullUserService()  # pylint: disable=protected-access

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id

        # Create an image submission for Bob, and corresponding workflow.
        self._create_submission(bob_item, {
            'text': "Bob Answer",
            'file_keys': ["test_key"],
            'files_descriptions': ["test_description"]
        }, ['self'])

        # Mock the file upload API to avoid hitting S3
        with patch("openassessment.xblock.submission_mixin.file_upload_api") as file_api:
            file_api.get_download_url.return_value = "http://www.example.com/image.jpeg"
            # also fake a file_upload_type so our patched url gets rendered
            xblock.file_upload_type_raw = 'image'

            __, context = xblock.get_student_info_path_and_context("Bob")

            # Check that the right file key was passed to generate the download url
            file_api.get_download_url.assert_called_with("test_key")

            # Check the context passed to the template
            self.assertEquals([('http://www.example.com/image.jpeg', 'test_description')], context['staff_file_urls'])
            self.assertEquals('image', context['file_upload_type'])

            # Check the fully rendered template
            payload = urllib.urlencode({"student_username": "Bob"})
            resp = self.request(xblock, "render_student_info", payload)
            self.assertIn("http://www.example.com/image.jpeg", resp)

    @scenario('data/self_only_scenario.xml', user_id='Bob')
    def test_staff_area_student_info_many_images_submission(self, xblock):
        """
        Test multiple file uploads support
        """
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        xblock.runtime._services['user'] = NullUserService()

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id

        file_keys = ["test_key0", "test_key1", "test_key2"]
        files_descriptions = ["test_description0", "test_description1", "test_description2"]
        images = ["http://www.example.com/image%d.jpeg" % i for i in range(3)]
        file_keys_with_images = dict(zip(file_keys, images))

        # Create an image submission for Bob, and corresponding workflow.
        self._create_submission(bob_item, {
            'text': "Bob Answer",
            'file_keys': file_keys,
            'files_descriptions': files_descriptions
        }, ['self'])

        # Mock the file upload API to avoid hitting S3
        with patch("openassessment.xblock.submission_mixin.file_upload_api") as file_api:
            file_api.get_download_url.return_value = Mock()
            file_api.get_download_url.side_effect = lambda file_key: file_keys_with_images[file_key]

            # also fake a file_upload_type so our patched url gets rendered
            xblock.file_upload_type_raw = 'image'

            __, context = xblock.get_student_info_path_and_context("Bob")

            # Check that the right file key was passed to generate the download url
            calls = [call("test_key%d" % i) for i in range(3)]
            file_api.get_download_url.assert_has_calls(calls)

            # Check the context passed to the template
            self.assertEquals([(image, "test_description%d" % i) for i, image in enumerate(images)],
                              context['staff_file_urls'])
            self.assertEquals('image', context['file_upload_type'])

            # Check the fully rendered template
            payload = urllib.urlencode({"student_username": "Bob"})
            resp = self.request(xblock, "render_student_info", payload)
            for i in range(3):
                self.assertIn("http://www.example.com/image%d.jpeg" % i, resp)
                self.assertIn("test_description%d" % i, resp)

    @scenario('data/self_only_scenario.xml', user_id='Bob')
    def test_staff_area_student_info_file_download_url_error(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        xblock.runtime._services['user'] = NullUserService()  # pylint: disable=protected-access

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id

        # Create an image submission for Bob, and corresponding workflow.
        self._create_submission(bob_item, {
            'text': "Bob Answer",
            'file_keys': ["test_key"]
        }, ['self'])

        # Mock the file upload API to simulate an error
        with patch("openassessment.fileupload.api.get_download_url") as file_api_call:
            file_api_call.side_effect = FileUploadInternalError("Error!")
            __, context = xblock.get_student_info_path_and_context("Bob")

            # Expect that the page still renders, but without the image url
            self.assertIn('submission', context)
            self.assertNotIn('file_url', context['submission'])

            # Check the fully rendered template
            payload = urllib.urlencode({"student_username": "Bob"})
            resp = self.request(xblock, "render_student_info", payload)
            self.assertIn("Bob Answer", resp)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_staff_area_student_info_full_workflow(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        xblock.runtime._services['user'] = NullUserService()  # pylint: disable=protected-access

        # Commonly chosen options for assessments
        options_selected = {
            "Ideas": "Good",
            "Content": "Poor",
        }

        criterion_feedback = {
            "Ideas": "Dear diary: Lots of creativity from my dream journal last night at 2 AM,",
            "Content": "Not as insightful as I had thought in the wee hours of the morning!"
        }

        overall_feedback = "I think I should tell more people about how important worms are for the ecosystem."

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id

        # Create a submission for Bob, and corresponding workflow.
        submission = self._create_submission(bob_item, {'text': "Bob Answer"}, ['peer', 'self'])

        # Create a submission for Tim, and corresponding workflow.
        tim_item = bob_item.copy()
        tim_item["student_id"] = "Tim"
        self._create_submission(tim_item, "Tim Answer", ['peer', 'self'])

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
            criterion_feedback,
            overall_feedback,
            {'criteria': xblock.rubric_criteria},
        )

        # Now Bob should be fully populated in the student info view.
        request = namedtuple('Request', 'params')
        request.params = {"student_username": "Bob"}
        # Verify that we can render without error
        resp = xblock.render_student_info(request)
        self.assertIn("bob answer", resp.body.lower())

    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_display_schedule_training(self, xblock):
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )
        path, context = xblock.get_staff_path_and_context()
        self.assertEquals('openassessmentblock/staff_area/oa_staff_area.html', path)
        self.assertTrue(context['display_schedule_training'])

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_schedule_training(self, xblock):
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )

        # Schedule training
        response = self.request(xblock, 'schedule_training', json.dumps({}), response_format='json')
        self.assertTrue(response['success'], msg=response.get('msg'))
        self.assertIn('workflow_uuid', response)

    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_not_displaying_schedule_training(self, xblock):
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        path, context = xblock.get_staff_path_and_context()
        self.assertEquals('openassessmentblock/staff_area/oa_staff_area.html', path)
        self.assertFalse(context['display_schedule_training'])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_admin_schedule_training_no_permissions(self, xblock):
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        response = self.request(xblock, 'schedule_training', json.dumps({}), response_format='json')
        self.assertFalse(response['success'])
        self.assertIn('permission', response['msg'])

    @patch.object(ai_api, "train_classifiers")
    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_admin_schedule_training_error(self, xblock, mock_api):
        mock_api.side_effect = AIError("Oh no!")
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )
        response = self.request(xblock, 'schedule_training', json.dumps({}), response_format='json')
        self.assertFalse(response['success'])
        self.assertIn('error', response['msg'])

    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_display_reschedule_unfinished_grading_tasks(self, xblock):
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )
        path, context = xblock.get_staff_path_and_context()
        self.assertEquals('openassessmentblock/staff_area/oa_staff_area.html', path)
        self.assertTrue(context['display_reschedule_unfinished_tasks'])

    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_reschedule_unfinished_grading_tasks_no_permissions(self, xblock):
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        response = self.request(xblock, 'reschedule_unfinished_tasks', json.dumps({}), response_format='json')
        self.assertFalse(response['success'])
        self.assertIn('permission', response['msg'])

    @patch.object(ai_api, "reschedule_unfinished_tasks")
    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_reschedule_unfinished_grading_tasks_success(self, xblock, mock_api):
        mock_api.side_effect = Mock()
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )
        response = self.request(xblock, 'reschedule_unfinished_tasks', json.dumps({}), response_format='json')
        self.assertTrue(response['success'])
        self.assertIn(u'All', response['msg'])
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
        self.assertIn('error', response['msg'])

    @scenario('data/peer_only_scenario.xml', user_id='Bob')
    def test_no_example_based_assessment(self, xblock):
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )
        response = self.request(xblock, 'schedule_training', json.dumps({}), response_format='json')
        self.assertFalse(response['success'])
        self.assertIn('not configured', response['msg'])

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_classifier_set_info(self, xblock):
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )

        # Initially, there should be no classifier set info
        # because we haven't trained any classifiers for this problem
        __, context = xblock.get_staff_path_and_context()
        self.assertIn('classifierset', context)
        self.assertIs(context['classifierset'], None)

        # Schedule a training task, which should create classifiers
        response = self.request(xblock, 'schedule_training', json.dumps({}), response_format='json')
        self.assertTrue(response['success'], msg=response.get('msg'))

        # Now classifier info should be available in the context
        __, context = xblock.get_staff_path_and_context()
        self.assertIn('classifierset', context)
        self.assertTrue(isinstance(context['classifierset']['created_at'], datetime.datetime))
        self.assertEqual(context['classifierset']['algorithm_id'], ALGORITHM_ID)
        self.assertEqual(context['classifierset']['course_id'], xblock.get_student_item_dict()['course_id'])
        self.assertEqual(context['classifierset']['item_id'], xblock.get_student_item_dict()['item_id'])

        # Verify that the classifier set appears in the rendered template
        resp = self.request(xblock, 'render_staff_area', json.dumps({}))
        self.assertIn("classifier set", resp.decode('utf-8').lower())
        self.assertIn(ALGORITHM_ID, resp.decode('utf-8'))

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_classifier_set_info_hidden_for_course_staff(self, xblock):
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        __, context = xblock.get_staff_path_and_context()
        self.assertNotIn('classifierset', context)

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_cancel_submission_without_reason(self, xblock):
        # If we're not course staff, we shouldn't be able to see the
        # cancel submission option
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, False, False, "Bob"
        )

        resp = self.request(xblock, 'cancel_submission', json.dumps({}))
        self.assertIn("you do not have permission", resp.decode('utf-8').lower())

        # If we ARE course staff, then we should see the cancel submission option
        # with valid error message.
        xblock.xmodule_runtime.user_is_staff = True
        resp = self.request(xblock, 'cancel_submission', json.dumps({}), response_format='json')
        self.assertIn("Please enter valid reason", resp['msg'])
        self.assertEqual(False, resp['success'])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_cancel_submission_full_flow(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        # Create a submission for Bob, and corresponding workflow.
        submission = self._create_submission(bob_item, {'text': "Bob Answer"}, ['peer'])

        incorrect_submission_uuid = 'abc'
        params = {"submission_uuid": incorrect_submission_uuid, "comments": "Inappropriate language."}
        # Raise flow not found exception.
        resp = self.request(xblock, 'cancel_submission', json.dumps(params), response_format='json')
        self.assertIn("Error finding workflow", resp['msg'])
        self.assertEqual(False, resp['success'])

        # Verify that we can render without error
        params = {"submission_uuid": submission["uuid"], "comments": "Inappropriate language."}
        resp = self.request(xblock, 'cancel_submission', json.dumps(params), response_format='json')
        self.assertIn("The learner submission has been removed from peer", resp['msg'])
        self.assertEqual(True, resp['success'])

    @scenario('data/staff_grade_scenario.xml', user_id='Bob')
    def test_staff_assessment_counts(self, xblock):
        """
        Verify the staff assessment counts (ungraded and checked out)
        as shown in the staff grading tool when staff assessment is required.
        """
        _, context = xblock.get_staff_path_and_context()
        self._verify_staff_assessment_context(context, True, 0, 0)

        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        # Create a submission for Bob, and corresponding workflow.
        self._create_submission(bob_item, {'text': "Bob Answer"}, [])

        # Verify the count as shown in the staff grading tool.
        _, context = xblock.get_staff_path_and_context()
        self._verify_staff_assessment_context(context, True, 1, 0)

        # Check out the assessment for grading and ensure that the count changes.
        self.request(xblock, 'render_staff_grade_form', json.dumps({}))
        _, context = xblock.get_staff_path_and_context()
        self._verify_staff_assessment_context(context, True, 0, 1)

    @scenario('data/example_based_assessment.xml', user_id='Bob')
    def test_staff_assessment_counts_not_required(self, xblock):
        """
        Verify the staff assessment counts (ungraded and checked out) are
        not present in the context when staff assessment is not required.
        """
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, True, "Bob"
        )
        _, context = xblock.get_staff_path_and_context()
        self._verify_staff_assessment_context(context, False)

    @scenario('data/staff_grade_scenario.xml', user_id='Bob')
    def test_staff_assessment_form(self, xblock):
        """
        Smoke test that the staff assessment form renders when staff assessment
        is required.
        """
        permission_denied = "You do not have permission to access ORA staff grading."
        no_submissions_available = "No other learner responses are available for grading at this time."
        submission_text = "Grade me, please!"

        resp = self.request(xblock, 'render_staff_grade_form', json.dumps({})).decode('utf-8')
        self.assertIn(permission_denied, resp)
        self.assertNotIn(no_submissions_available, resp)

        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        resp = self.request(xblock, 'render_staff_grade_form', json.dumps({})).decode('utf-8')
        self.assertNotIn(permission_denied, resp)
        self.assertIn(no_submissions_available, resp)
        self.assertNotIn(submission_text, resp)

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        # Create a submission for Bob, and corresponding workflow.
        submission = self._create_submission(bob_item, {'text': submission_text}, [])

        resp = self.request(xblock, 'render_staff_grade_form', json.dumps({})).decode('utf-8')
        self.assertNotIn(no_submissions_available, resp)
        self.assertIn(submission_text, resp)

        self.assert_event_published(xblock, 'openassessmentblock.get_submission_for_staff_grading', {
            'type': 'full-grade',
            'requesting_staff_id': 'Bob',
            'item_id': bob_item['item_id'],
            'submission_returned_uuid': submission['uuid']
        })

    @scenario('data/self_only_scenario.xml', user_id='Bob')
    def test_staff_delete_student_state(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, 'Bob'
        )
        xblock.runtime._services['user'] = NullUserService()  # pylint: disable=protected-access

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        # Create a submission for Bob, and corresponding workflow.
        submission = self._create_submission(bob_item, {'text': "Bob Answer"}, ['self'])

        # Bob assesses himself.
        self_api.create_assessment(
            submission['uuid'],
            STUDENT_ITEM["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            {'criteria': xblock.rubric_criteria},
        )

        request = namedtuple('Request', 'params')
        request.params = {"student_username": 'Bob'}
        # Verify that we can see the student's grade
        resp = xblock.render_student_info(request)
        self.assertIn("final grade", resp.body.lower())

        # Staff user Bob can clear his own submission
        xblock.clear_student_state('Bob', 'test_course', xblock.scope_ids.usage_id, bob_item['student_id'])

        # Verify that the submission was cleared
        resp = xblock.render_student_info(request)
        self.assertIn("response was not found", resp.body.lower())

    def _verify_staff_assessment_context(self, context, required, ungraded=None, in_progress=None):
        """
        Internal helper for common staff assessment context verification.
        """
        self.assertEquals(required, context['staff_assessment_required'])
        if not required:
            self.assertNotIn('staff_assessment_ungraded', context)
            self.assertNotIn('staff_assessment_in_progress', context)
        else:
            self.assertEqual(ungraded, context['staff_assessment_ungraded'])
            self.assertEqual(in_progress, context['staff_assessment_in_progress'])

    @staticmethod
    def _create_mock_runtime(
            item_id,
            is_staff,
            is_admin,
            anonymous_user_id,
            user_is_beta=False,
            days_early_for_beta=0
    ):
        """
        Internal helper to define a mock runtime.
        """
        mock_runtime = Mock(
            course_id='test_course',
            item_id=item_id,
            anonymous_student_id='Bob',
            user_is_staff=is_staff,
            user_is_admin=is_admin,
            user_is_beta=user_is_beta,
            days_early_for_beta=days_early_for_beta,
            service=lambda self, service: Mock(
                get_anonymous_student_id=lambda user_id, course_id: anonymous_user_id
            )
        )
        return mock_runtime

    @staticmethod
    def _create_submission(item, values, types):
        """ Create a submission and corresponding workflow. """
        submission = sub_api.create_submission(item, values)

        peer_api.on_start(submission["uuid"])
        workflow_api.create_workflow(submission["uuid"], types)
        return submission
