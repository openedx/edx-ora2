"""
Tests for the staff area.
"""


from collections import namedtuple
import json
import urllib

import ddt
from django.test.utils import override_settings
from mock import MagicMock, Mock, PropertyMock, call, patch
from testfixtures import log_capture

from submissions import api as sub_api
from submissions import team_api as team_sub_api
from submissions.errors import SubmissionNotFoundError

from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.assessment.api import staff as staff_api
from openassessment.assessment.api import teams as teams_api
from openassessment.fileupload.exceptions import FileUploadInternalError
from openassessment.tests.factories import UserFactory
from openassessment.workflow import api as workflow_api
from openassessment.workflow import team_api as team_workflow_api
from openassessment.xblock.utils.data_conversion import prepare_submission_for_serialization
from openassessment.xblock.test.base import XBlockHandlerTestCase, scenario
from openassessment.xblock.test.test_team import (
    MockTeamsService,
    MOCK_TEAM_MEMBER_USERNAMES,
    MOCK_TEAM_MEMBER_USERNAMES_CONV,
    MOCK_TEAM_MEMBER_STUDENT_IDS,
    MOCK_TEAM_NAME,
    MOCK_TEAM_ID
)

FILE_URL = 'www.fileurl.com'
SAVED_FILES_DESCRIPTIONS = ['file1', 'file2']
SAVED_FILES_NAMES = ['file1.txt', 'file2.txt']

STUDENT_ITEM = {
    "student_id": "Bob",
    "course_id": "test_course",
    "item_id": "item_one",
    "item_type": "openassessment",
}

TEAMMATE_ITEM = {
    "student_id": MOCK_TEAM_MEMBER_STUDENT_IDS[0],
    "course_id": "test_course",
    "item_id": "item_one",
    "item_type": "openassessment",
}

ASSESSMENT_DICT = {
    'overall_feedback': "这是中国",
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


class NullUserService:
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


class UserStateService:
    """
    An implementation of `user_state` runtime service, to be utilized by tests.
    """

    def get_state_as_dict(self, username=None, location=None):  # pylint: disable=unused-argument
        """
        Returns a default state regardless of any passed params.
        """
        return {
            'saved_files_descriptions': json.dumps(SAVED_FILES_DESCRIPTIONS),
            'saved_files_names': json.dumps(SAVED_FILES_NAMES)
        }


@ddt.ddt
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
    def test_view_in_studio_button(self, xblock):
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, False, False, "Bob"
        )

        # If we are not course staff,then we should NOT see the studio link
        resp = self.request(xblock, 'render_staff_area', json.dumps({}))
        self.assertNotIn("view ora in studio", resp.decode('utf-8').lower())

        # If we ARE course staff, then we should see the studio link
        xblock.xmodule_runtime.user_is_staff = True
        resp = self.request(xblock, 'render_staff_area', json.dumps({}))
        self.assertIn("view ora in studio", resp.decode('utf-8').lower())

    @override_settings(
        HTTPS='on',
        CMS_BASE="studio",
    )
    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_get_studio_url(self, xblock):
        # Given we are staff viewing an ORA
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )

        # Mock the location of the vertical, returned when we run str(block)
        xblock.parent = 'vertical-location'

        # When I get context for the staff area
        _, context = xblock.get_staff_path_and_context()

        # Then I get the appropriate URL for studio
        expectedUrl = 'https://studio/container/vertical-location'
        self.assertIn('studio_edit_url', context)
        self.assertEqual(expectedUrl, context['studio_edit_url'])

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
        self.assertNotIn('staff-info', xblock_fragment.body_html())

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
        self.assertIn("a response was not found for this learner.", resp.body.decode('utf-8').lower())

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
            ASSESSMENT_DICT['options_selected'], {}, "",
            {'criteria': xblock.rubric_criteria},
            1,
        )

        # Now Bob should be fully populated in the student info view.
        path, context = xblock.get_student_info_path_and_context("Bob")
        self.assertEqual("Bob Answer 1", context['submission']['answer']['parts'][0]['text'])
        self.assertIsNotNone(context['peer_assessments'])
        self.assertIsNone(context['self_assessment'])
        self.assertIsNone(context['staff_assessment'])
        self.assertEqual("openassessmentblock/staff_area/oa_student_info.html", path)

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
        self.assertEqual("Bob Answer 1", context['submission']['answer']['parts'][0]['text'])
        self.assertIsNone(context['peer_assessments'])
        self.assertIsNotNone(context['self_assessment'])
        self.assertIsNone(context['staff_assessment'])
        self.assertEqual("openassessmentblock/staff_area/oa_student_info.html", path)

        grade_details = context['grade_details']
        self.assertEqual(1, len(grade_details['criteria'][0]['assessments']))
        self.assertEqual('Self Assessment Grade', grade_details['criteria'][0]['assessments'][0]['title'])

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

        _, _ = xblock.get_student_info_path_and_context("Bob")
        self.assertIn(
            "Good use of vocabulary!",
            self.request(
                xblock,
                "render_student_info",
                urllib.parse.urlencode({"student_username": "Bob"})
            ).decode('utf-8')
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
        self.assertEqual("Bob Answer 1", context['submission']['answer']['parts'][0]['text'])
        self.assertIsNone(context['peer_assessments'])
        self.assertIsNone(context['self_assessment'])
        self.assertIsNotNone(context['staff_assessment'])
        self.assertEqual("openassessmentblock/staff_area/oa_student_info.html", path)

        grade_details = context['grade_details']
        self.assertEqual(1, len(grade_details['criteria'][0]['assessments']))
        self.assertEqual('Staff Grade', grade_details['criteria'][0]['assessments'][0]['title'])

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
            assessment_requirements=requirements,
            course_settings={},
        )

        path, context = xblock.get_student_info_path_and_context("Bob")
        self.assertEqual("Bob Answer 1", context['submission']['answer']['parts'][0]['text'])
        self.assertIsNotNone(context['workflow_cancellation'])
        self.assertEqual("openassessmentblock/staff_area/oa_student_info.html", path)

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
            assessment_requirements=requirements,
            course_settings={},
        )

        xblock.submission_uuid = submission["uuid"]
        path, _ = xblock.peer_path_and_context(False)
        self.assertEqual("openassessmentblock/peer/oa_peer_cancelled.html", path)

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
            'files_descriptions': ["test_description"],
            'files_name': ["test_fileName"]
        }, ['self'])

        # Mock the file upload API to avoid hitting S3
        with patch("openassessment.xblock.apis.submissions.file_api.file_upload_api.get_download_url") as \
                get_download_url:
            get_download_url.return_value = "http://www.example.com/image.jpeg"

            # also fake a file_upload_type so our patched url gets rendered
            xblock.file_upload_type_raw = 'image'

            __, context = xblock.get_student_info_path_and_context("Bob")

            # Check that the right file key was passed to generate the download url
            get_download_url.assert_called_with("test_key")

            # Check the context passed to the template
            self.assertEqual(
                [{
                    'download_url': 'http://www.example.com/image.jpeg',
                    'description': 'test_description',
                    'name': 'test_fileName',
                    'size': 0,
                    'show_delete_button': False
                }],
                context['staff_file_urls']
            )

            self.assertEqual('image', context['file_upload_type'])

            # Check the fully rendered template
            payload = urllib.parse.urlencode({"student_username": "Bob"})
            resp = self.request(xblock, "render_student_info", payload).decode('utf-8')
            self.assertIn("http://www.example.com/image.jpeg", resp)
            self.assertIn("test_description", resp)

    @scenario('data/self_only_scenario.xml', user_id='Bob')
    def test_staff_area_student_info_many_images_submission(self, xblock):
        """
        Test multiple file uploads support
        """
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        xblock.runtime._services['user'] = NullUserService()  # pylint: disable=protected-access

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id

        file_keys = ["test_key0", "test_key1", "test_key2"]
        files_descriptions = ["test_description0", "test_description1", "test_description2"]
        files_name = ["fname0", "fname1", "fname2"]
        images = ["http://www.example.com/image%d.jpeg" % i for i in range(3)]
        file_keys_with_images = dict(list(zip(file_keys, images)))

        # Create an image submission for Bob, and corresponding workflow.
        self._create_submission(bob_item, {
            'text': "Bob Answer",
            'file_keys': file_keys,
            'files_descriptions': files_descriptions,
            'files_name': files_name
        }, ['self'])

        # Mock the file upload API to avoid hitting S3
        with patch("openassessment.xblock.apis.submissions.file_api.file_upload_api.get_download_url") as \
                get_download_url:
            get_download_url.return_value = Mock()
            get_download_url.side_effect = lambda file_key: file_keys_with_images[file_key]

            # also fake a file_upload_type so our patched url gets rendered
            xblock.file_upload_type_raw = 'image'

            __, context = xblock.get_student_info_path_and_context("Bob")

            # Check that the right file key was passed to generate the download url
            calls = [call("test_key%d" % i) for i in range(3)]
            get_download_url.assert_has_calls(calls)

            # Check the context passed to the template
            self.assertEqual(
                [{
                    "download_url": image,
                    "description": "test_description%d" % i,
                    "name": "fname%d" % i,
                    "size": 0,
                    "show_delete_button": False
                } for i, image in enumerate(images)],
                context['staff_file_urls']
            )
            self.assertEqual('image', context['file_upload_type'])

            # Check the fully rendered template
            payload = urllib.parse.urlencode({"student_username": "Bob"})
            resp = self.request(xblock, "render_student_info", payload).decode('utf-8')
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
            'file_keys': ["test_key"],
            'files_descriptions': []
        }, ['self'])

        # Mock the file upload API to simulate an error
        with patch("openassessment.fileupload.api.get_download_url") as file_api_call:
            file_api_call.side_effect = FileUploadInternalError("Error!")
            __, context = xblock.get_student_info_path_and_context("Bob")

            # Expect that the page still renders, but without the image url
            self.assertIn('submission', context)
            self.assertNotIn('file_url', context['submission'])

            # Check the fully rendered template
            payload = urllib.parse.urlencode({"student_username": "Bob"})
            resp = self.request(xblock, "render_student_info", payload).decode('utf-8')
            self.assertIn("Bob Answer", resp)

    @scenario('data/grade_scenario.xml', user_id='Bob')
    def test_staff_area_student_info_full_workflow(self, xblock):
        # Simulate that we are course staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        xblock.runtime._services['user'] = NullUserService()  # pylint: disable=protected-access

        # Commonly chosen options for assessments
        options_selected = {
            "𝓒𝓸𝓷𝓬𝓲𝓼𝓮": "Ġööḋ",
            "Form": "Poor",
        }

        criterion_feedback = {
            "𝓒𝓸𝓷𝓬𝓲𝓼𝓮": "Dear diary: Lots of creativity from my dream journal last night at 2 AM,",
            "Form": "Not as insightful as I had thought in the wee hours of the morning!"
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
            options_selected, {}, "",
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
        self.assertIn("bob answer", resp.body.decode('utf-8').lower())

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

    @scenario('data/team_submission.xml', user_id='StaffMember')
    def test_cancel_team_submission_submission_not_found(self, xblock):
        # Set up team assignment and submission
        self._setup_xblock_and_create_submission(xblock, anonymous_user_id='StaffMember')
        mock_get_user_submission = Mock()
        xblock.get_user_submission = mock_get_user_submission

        params = {"submission_uuid": 'abc', "comments": "Inappropriate language."}

        # Raise submission not found exception.
        mock_get_user_submission.side_effect = SubmissionNotFoundError()
        resp = self.request(xblock, 'cancel_submission', json.dumps(params), response_format='json')
        self.assertIn("Submission not found", resp['msg'])
        self.assertFalse(resp['success'])

        # get_user_submission returns None
        mock_get_user_submission.side_effect = None
        mock_get_user_submission.return_value = None
        resp = self.request(xblock, 'cancel_submission', json.dumps(params), response_format='json')
        self.assertIn("Submission not found", resp['msg'])
        self.assertFalse(resp['success'])

    @scenario('data/team_submission.xml', user_id='StaffMember')
    def test_cancel_team_submission_no_team_uuid(self, xblock):
        # Set up team assignment and submission
        self._setup_xblock_and_create_submission(xblock, anonymous_user_id='StaffMember')
        xblock.get_user_submission = Mock(return_value={'team_submission_uuid': ''})

        params = {"submission_uuid": 'abc', "comments": "Inappropriate language."}

        # Raise exception since there's no team_submission_uuid.
        resp = self.request(xblock, 'cancel_submission', json.dumps(params), response_format='json')
        self.assertIn("Submission for team assignment has no associated team submission", resp['msg'])
        self.assertFalse(resp['success'])

    @scenario('data/team_submission.xml', user_id='StaffMember')
    def test_cancel_team_submission(self, xblock):
        # Set up team assignment and submission
        team_submission = self._setup_xblock_and_create_submission(xblock, anonymous_user_id='StaffMember')
        xblock.get_user_submission = Mock(
            return_value={
                'team_submission_uuid': team_submission['team_submission_uuid']
            }
        )
        params = {"submission_uuid": 'abc', "comments": "Inappropriate language."}

        # There should be one team submission before cancellation
        status_counts, total_submissions = xblock.get_team_workflow_status_counts()
        self.assertEqual(total_submissions, 1)
        status_counts = self._parse_workflow_status_counts(status_counts)
        self.assertEqual(status_counts['waiting'], 1)

        # The staff area student context should not include a workflow cancellation
        _, context = xblock.get_student_info_path_and_context(MOCK_TEAM_MEMBER_STUDENT_IDS[0])
        self.assertIsNone(context['workflow_cancellation'])

        # Cancel the team submission
        resp = self.request(xblock, 'cancel_submission', json.dumps(params), response_format='json')
        self.assertIn("The team’s submission has been removed from grading.", resp['msg'])
        self.assertTrue(resp['success'])

        # The submission should now be cancelled.
        status_counts, total_submissions = xblock.get_team_workflow_status_counts()
        self.assertEqual(total_submissions, 1)
        status_counts = self._parse_workflow_status_counts(status_counts)
        self.assertEqual(status_counts['cancelled'], 1)

        # The staff area student context will still not include a workflow cancellation
        _, context = xblock.get_student_info_path_and_context(MOCK_TEAM_MEMBER_STUDENT_IDS[0])
        workflow_cancellation = context['workflow_cancellation']
        self.assertIsNotNone(workflow_cancellation)
        self.assertEqual(workflow_cancellation['cancelled_by_id'], 'StaffMember')
        self.assertEqual(workflow_cancellation['comments'], params['comments'])

    @scenario('data/team_submission.xml', user_id='StaffMember')
    def test_staff_area__team_assignment__staff_assessment_with_final_grade(self, xblock):
        """
        If a user has a staff assessment, they should also have a final grade.
        """
        # Set up team assignment and submission. StaffMember is not on any team.
        team_submission = self._setup_xblock_and_create_submission(
            xblock,
            anonymous_user_id='StaffMember',
            has_team=False
        )
        # Assess team submission
        feedback = "Team assignment complete!!!!!"
        teams_api.create_assessment(
            team_submission['team_submission_uuid'],
            "StaffMember",
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            feedback,
            {'criteria': xblock.rubric_criteria},
        )
        _, context = xblock.get_student_info_path_and_context(MOCK_TEAM_MEMBER_STUDENT_IDS[0])

        # Context should contain score and staff assessment
        self.assertIsNotNone(context['staff_assessment'])
        assessment = context['staff_assessment'][0]
        self.assertEqual(assessment['scorer_id'], 'StaffMember')
        self.assertEqual(assessment['feedback'], feedback)
        self.assertIsNotNone(context['score'])
        self.assertEqual(context['score']['annotations'][0]['creator'], 'StaffMember')

    @scenario('data/staff_grade_scenario.xml', user_id='Bob')
    def test_staff_assessment_counts(self, xblock):
        """
        Verify the staff assessment counts (ungraded and checked out)
        as shown in the staff grading tool when staff assessment is required.
        """
        xblock.is_enhanced_staff_grader_enabled = False
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

    @scenario('data/grade_scenario.xml', user_id='Bob')
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
        team_submission_disabled = 'data-team-submission="False"'

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
        self.assertIn(team_submission_disabled, resp)

        self.assert_event_published(xblock, 'openassessmentblock.get_submission_for_staff_grading', {
            'type': 'full-grade',
            'requesting_staff_id': 'Bob',
            'item_id': bob_item['item_id'],
            'submission_returned_uuid': submission['uuid']
        })

    @scenario('data/team_submission.xml', user_id='Bob')
    def test_staff_form_for_team_assessment(self, xblock):
        self._setup_xblock_and_create_submission(xblock)

        team_submission_enabled = 'data-team-submission="True"'
        team_name_query = f'data-team-name="{MOCK_TEAM_NAME}"'
        team_usernames_query = f'data-team-usernames="{MOCK_TEAM_MEMBER_USERNAMES_CONV}"'

        resp = self.request(xblock, 'render_staff_grade_form', json.dumps({})).decode('utf-8')
        self.assertIn(team_submission_enabled, resp)
        self.assertIn(team_name_query, resp)
        self.assertIn(team_usernames_query, resp)

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
        self.assertIn("final grade", resp.body.decode('utf-8').lower())

        # Staff user Bob can clear his own submission
        xblock.clear_student_state('Bob', 'test_course', xblock.scope_ids.usage_id, bob_item['student_id'])

        # Verify that the submission was cleared
        resp = xblock.render_student_info(request)
        self.assertIn("response was not found", resp.body.decode('utf-8').lower())

    @patch('openassessment.xblock.staff_area_mixin.remove_file')
    @scenario('data/self_only_scenario.xml', user_id='Bob')
    def test_staff_delete_student_state_with_files(self, xblock, remove_file_patch):
        # Given we are course staff...
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, 'Bob'
        )
        xblock.runtime._services['user'] = NullUserService()  # pylint: disable=protected-access

        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id

        # and a student has a submission files and corresponding workflow...
        submission = self._create_submission(
            bob_item,
            {
                'text': "Bob Answer",
                'file_keys': SAVED_FILES_NAMES,
                'files_descriptions': SAVED_FILES_DESCRIPTIONS
            },
            ['self']
        )

        # which has already been assessed
        self_api.create_assessment(
            submission['uuid'],
            STUDENT_ITEM["student_id"],
            ASSESSMENT_DICT['options_selected'],
            ASSESSMENT_DICT['criterion_feedback'],
            ASSESSMENT_DICT['overall_feedback'],
            {'criteria': xblock.rubric_criteria},
        )

        # When we clear the student's state
        xblock.clear_student_state('Bob', 'test_course', xblock.scope_ids.usage_id, bob_item['student_id'])

        # Verify that the files were removed
        remove_file_patch.assert_has_calls([call(key) for key in SAVED_FILES_NAMES])

    @scenario('data/team_submission.xml', user_id='Bob')
    def test_staff_delete_student_state_for_team_assessment(self, xblock):
        # Given a team with a submission
        self._setup_xblock_and_create_submission(xblock)
        status_counts, total_submissions = xblock.get_team_workflow_status_counts()
        self.assertEqual(total_submissions, 1)
        status_counts = self._parse_workflow_status_counts(status_counts)
        self.assertEqual(status_counts['waiting'], 1)

        # When I clear the team's state
        xblock.clear_student_state(
            MOCK_TEAM_MEMBER_STUDENT_IDS[0],
            'test_course',
            xblock.scope_ids.usage_id,
            STUDENT_ITEM['student_id']
        )

        # Then the submission goes into cancelled state
        status_counts, total_submissions = xblock.get_team_workflow_status_counts()
        self.assertEqual(total_submissions, 1)
        status_counts = self._parse_workflow_status_counts(status_counts)
        self.assertEqual(status_counts['cancelled'], 1)

        # And the submissions are cleared to allow a new submission workflow
        self.assertEqual(xblock.get_team_workflow_info(), {})

    @patch('openassessment.xblock.staff_area_mixin.delete_shared_files_for_team')
    @scenario('data/team_submission.xml', user_id='Bob')
    def test_staff_clear_team_state_with_submission_clears_files(self, xblock, delete_files_patch):
        # Given we are staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, 'Bob'
        )

        # ... on a team ORA w/ a team submission (which presumably also has files)
        self._setup_xblock_and_create_submission(xblock)

        # When we clear team state
        xblock.clear_student_state(
            MOCK_TEAM_MEMBER_STUDENT_IDS[0],
            'test_course',
            xblock.scope_ids.usage_id,
            STUDENT_ITEM['student_id']
        )

        # Then we delete files for the team
        delete_files_patch.assert_called_with(STUDENT_ITEM['course_id'], xblock.scope_ids.usage_id, MOCK_TEAM_ID)

    @patch('openassessment.xblock.staff_area_mixin.delete_shared_files_for_team')
    @scenario('data/team_submission.xml', user_id='Bob')
    def test_staff_clear_team_state_without_submission(self, xblock, delete_files_patch):
        # Given we are staff
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, False, False, 'Bob'
        )

        # ... on a team ORA w/out a team submission
        xblock.is_team_assignment = Mock(return_value=True)

        # When we clear team state
        xblock.clear_student_state('Bob', 'test_course', xblock.scope_ids.usage_id, STUDENT_ITEM['student_id'])

        # We don't know team info, so don't clear files
        delete_files_patch.assert_not_called()

    def _parse_workflow_status_counts(self, status_counts):
        """ Helper to transform status counts from a list of dicts to a single dict """
        return {
            status['status']: status['count'] for status in status_counts
        }

    @log_capture()
    @patch('openassessment.xblock.config_mixin.ConfigMixin.user_state_upload_data_enabled')
    @scenario('data/file_upload_missing_scenario.xml', user_id='Bob')
    def test_staff_area_student_upload_info_from_user_state(self, xblock, waffle_patch, logger):
        """
        Verify the student upload info is retrieved correctly from the user state.

        Scenario: When the upload info is missing from submission
        And upload is either required or optional
        And user state waffle flag is enabled
        Then user state is used for getting the upload data, if present
        """
        waffle_patch.return_value = True
        self._setup_xblock_and_create_submission(xblock)
        with patch("openassessment.fileupload.api.get_download_url") as get_download_url:
            get_download_url.return_value = FILE_URL
            __, context = xblock.get_student_info_path_and_context('Bob')
            self._verify_user_state_usage_log_present(logger, **{'location': xblock.location})
            staff_urls = context['staff_file_urls']
            for count in range(2):
                self.assertDictEqual(
                    staff_urls[count],
                    {
                        'download_url': FILE_URL,
                        'description': SAVED_FILES_DESCRIPTIONS[count],
                        'name': SAVED_FILES_NAMES[count],
                        'size': None,
                        'show_delete_button': False
                    }
                )

            self._verify_staff_assessment_rendering(
                xblock,
                'openassessmentblock/staff_area/oa_staff_grade_learners_assessment.html',
                context,
                FILE_URL,
            )

    @patch('openassessment.xblock.config_mixin.ConfigMixin.user_state_upload_data_enabled', new_callable=PropertyMock)
    @scenario('data/file_upload_missing_scenario.xml', user_id='Bob')
    def test_staff_area_student_user_state_not_used(self, xblock, waffle_patch):
        """
        Verify the user state isn't used if the waffle flag isn't on.

        Scenario: When the upload info is missing from submission
        And upload is either required or optional
        If the waffle flag is not set
        Then user state is not used for the upload info
        And there is no upload information present
        """
        waffle_patch.return_value = False
        self._setup_xblock_and_create_submission(xblock)
        __, context = xblock.get_student_info_path_and_context('Bob')
        self.assertFalse(any(context['staff_file_urls']))

    @scenario('data/team_submission.xml', user_id='Bob')
    def test_staff_area_has_team_info(self, xblock):
        # Given that we are course staff, managing a team assignment
        self._setup_xblock_and_create_submission(xblock)

        # When I get the staff context
        __, context = xblock.get_staff_path_and_context()

        # Then the context has team assignment info
        self.assertTrue(context['is_team_assignment'])

    @scenario('data/team_submission.xml', user_id='Bob', )
    def test_staff_area_student_info_has_team_info(self, xblock):
        # Given that we are course staff and teams enabled
        student = self._setup_xblock_and_create_submission(xblock)['submitted_by']

        # When I get the student context
        __, context = xblock.get_student_info_path_and_context(student)

        # Then the context has team info
        self.assertTrue(context['is_team_assignment'])
        self.assertEqual(context['team_name'], MOCK_TEAM_NAME)

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_staff_area_has_team_info_individual(self, xblock):
        # Given that we are course staff, managing an individual assignment
        self._setup_xblock_and_create_submission(xblock)

        # When I get the staff context
        __, context = xblock.get_staff_path_and_context()

        # Then the context has team assignment info
        self.assertFalse(context['is_team_assignment'])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_staff_area_student_info_no_team_info(self, xblock):
        # Given that we are course staff and teams are not enabled
        self._setup_xblock_and_create_submission(xblock)

        # When I get the student context
        __, context = xblock.get_student_info_path_and_context("Bob")

        # Then it knows it's not a team assignment
        self.assertFalse(context['is_team_assignment'])
        self.assertIsNone(context['team_name'])

    @patch('openassessment.data.map_anonymized_ids_to_usernames')
    @scenario('data/peer_assessment_scenario.xml', user_id='Bob')
    def test_waiting_step_details_api(self, xblock, username_map_patch):
        """
        Test the waiting step details JSON API response.
        """
        # Set mocks
        xblock.xmodule_runtime = Mock(user_is_staff=True)
        username_map_patch.return_value = {"Bob": "bob_username"}

        # Make a submission, but no peer assessments available
        self._setup_xblock_and_create_submission(xblock)

        # Retrieve waiting step details
        resp = self.request(xblock, 'waiting_step_data', json.dumps({}))
        waiting_step_details = json.loads(resp.decode('utf-8'))

        # Check the response
        self.assertCountEqual(
            waiting_step_details.keys(),
            [
                'display_name',
                'must_grade',
                'must_be_graded_by',
                'student_data',
                'overwritten_count',
                'waiting_count'
            ],
        )
        # Only a single student is waiting
        self.assertEqual(len(waiting_step_details['student_data']), 1)
        self.assertEqual(waiting_step_details['waiting_count'], 1)
        self.assertEqual(waiting_step_details['overwritten_count'], 0)
        # Check the response dict
        self.assertCountEqual(
            waiting_step_details['student_data'][0].keys(),
            [
                'student_id',
                'graded',
                'graded_by',
                'submission_uuid',
                'username',
                'staff_grade_status',
                'workflow_status',
                'created_at',
            ],
        )
        # Check that the username was correctly mapped
        self.assertEqual(
            waiting_step_details['student_data'][0]['username'],
            "bob_username"
        )

    @patch('openassessment.data.map_anonymized_ids_to_usernames')
    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_waiting_step_details_api_no_permission(self, xblock, username_map_patch):
        """
        Check that only staff users can use the waiting step details API.
        """
        username_map_patch.return_value = {}

        # If user is not staff, API is not available
        xblock.xmodule_runtime = Mock(user_is_staff=False)
        resp = self.request(xblock, 'waiting_step_data', json.dumps({}))
        self.assertIn("you do not have permission", resp.decode('utf-8').lower())

        # If it's course staff then display API results
        xblock.xmodule_runtime.user_is_staff = True
        resp = self.request(xblock, 'waiting_step_data', json.dumps({}))
        body = json.loads(resp.decode('utf-8'))

        self.assertCountEqual(
            body.keys(),
            [
                'display_name',
                'must_grade',
                'must_be_graded_by',
                'student_data',
                'overwritten_count',
                'waiting_count'
            ],
        )

    @scenario('data/team_submission.xml', user_id='StaffMember')
    def test_staff_area_student_info__different_team(self, xblock):
        """
        If a user has submitted with a team, and then moved to another team,
        test that a staff member entering their username will be shown their submission
        rather than their new team's submission.
        """
        # Setup the xblock, but don't create team submissions
        self._setup_xblock(xblock, anonymous_user_id='StaffMember')

        # Create a team submission that UserA has already been a part of
        arbitrary_user = UserFactory.create()
        other_team_student_ids = [MOCK_TEAM_MEMBER_STUDENT_IDS[0], 'someother-teammate-studentid', 'a-third-person-id']
        other_team_id = 'this-is-some-other-team-s-team-id'
        other_team_name = 'some-other-team-name'
        self._create_team_submission(
            TEAMMATE_ITEM['course_id'],
            xblock.location,
            other_team_id,
            arbitrary_user.id,
            other_team_student_ids,
            {'text': 'Previously existing team submission answer'}
        )

        # Create a team submission for the test team, excluding UserA
        self._create_team_submission(
            TEAMMATE_ITEM['course_id'],
            xblock.location,
            MOCK_TEAM_ID,
            arbitrary_user.id,
            MOCK_TEAM_MEMBER_STUDENT_IDS[1:],
            {'text': "Test team's submission without User A"}
        )

        mock_team = MagicMock()
        mock_team.configure_mock(name=other_team_name)
        # Ideally we could do a full integration test of this, but asserting that this
        # is called with the desired parameters is still a sound test
        with patch.object(MockTeamsService, 'get_team_by_team_id') as mock_get_team:
            mock_get_team.return_value = mock_team
            _, context = xblock.get_student_info_path_and_context(MOCK_TEAM_MEMBER_USERNAMES[0])
            mock_get_team.assert_called_with(other_team_id)

        self.assertEqual(context['team_name'], other_team_name)
        expected_usernames = list(other_team_student_ids)
        expected_usernames[0] = MOCK_TEAM_MEMBER_USERNAMES[0]
        self.assertEqual(
            set(context['team_usernames']),
            set(expected_usernames)
        )

    @scenario('data/basic_scenario.xml', user_id='Bob')
    @patch(
        'openassessment.xblock.config_mixin.ConfigMixin.is_enhanced_staff_grader_enabled',
        new_callable=PropertyMock
    )
    def test_staff_area_esg_on_staff_assessment_is_not_required(self, xblock, mock_esg_flag):
        """
        When staff_assessment_required is disabled, neither of esg flag
        nor the url should be defined in the context.
        """
        mock_esg_flag.return_value = True
        _, context = xblock.get_staff_path_and_context()

        self._verify_staff_assessment_context(context, False, 0, 0)
        mock_esg_flag.assert_not_called()
        self.assertNotIn('is_enhanced_staff_grader_enabled', context)
        self.assertNotIn('enhanced_staff_grader_url', context)

    @override_settings(
        ORA_GRADING_MICROFRONTEND_URL='ora_url'
    )
    @ddt.data(False, True)
    @patch(
        'openassessment.xblock.config_mixin.ConfigMixin.is_enhanced_staff_grader_enabled',
        new_callable=PropertyMock
    )
    @scenario('data/staff_grade_scenario.xml', user_id='Bob')
    def test_staff_area_esg(self, xblock, is_esg_enabled, mock_esg_flag):
        """
        If there is a staff step, enhanced_staff_grader_url should be
        "ORA_GRADING_MICROFRONTEND_URL/xblock_id" whether or not ESG is enabled
        """
        mock_esg_flag.return_value = is_esg_enabled
        _, context = xblock.get_staff_path_and_context()

        self._verify_staff_assessment_context(context, True, 0, 0)
        mock_esg_flag.assert_called()
        self.assertEqual(context['is_enhanced_staff_grader_enabled'], is_esg_enabled)
        self.assertEqual(context['enhanced_staff_grader_url'], '{esg_url}/{block_id}'.format(
            esg_url='ora_url',
            block_id=context['xblock_id']
        ))

    @log_capture()
    @patch('openassessment.xblock.config_mixin.ConfigMixin.user_state_upload_data_enabled')
    @scenario('data/file_upload_missing_scenario.xml', user_id='Bob')
    def test_student_userstate_not_used_when_upload_info_in_submission(self, xblock, waffle_patch, logger):
        """
        Verify the user state isn't used if the upload info is present in submission.

        Scenario: When the upload info is present in submission
        And upload is either required or optional
        If the waffle flag is set
        Then user state is not used for the upload info
        And user state usage logs aren't present
        """
        waffle_patch.return_value = True
        self._setup_xblock_and_create_submission(xblock, **{
            'file_keys': [FILE_URL, FILE_URL],
            'files_descriptions': [SAVED_FILES_DESCRIPTIONS[1], SAVED_FILES_DESCRIPTIONS[0]],
            'files_names': [SAVED_FILES_NAMES[1], SAVED_FILES_NAMES[0]],
            'files_sizes': [],
        })
        with patch("openassessment.fileupload.api.get_download_url") as get_download_url:
            get_download_url.return_value = FILE_URL
            __, __ = xblock.get_student_info_path_and_context('Bob')  # pylint: disable=redeclared-assigned-name
        with self.assertRaises(AssertionError):
            self._verify_user_state_usage_log_present(logger, **{'location': xblock.location})

    @log_capture()
    @patch("openassessment.fileupload.api.get_download_url")
    @patch('openassessment.xblock.config_mixin.ConfigMixin.is_fetch_all_urls_waffle_enabled')
    @patch('openassessment.xblock.config_mixin.ConfigMixin.user_state_upload_data_enabled')
    @scenario('data/file_upload_missing_scenario.xml', user_id='Bob')
    def test_staff_area_student_all_uploads(self, xblock, user_state_waffle, all_files_waffle, download_url, logger):
        """
        Verify the all files urls are obtained for a user in a given ORA block when staff is
        viewing an individual learner submission.

        Scenario: When the upload info is missing from submission
        And upload is either required or optional
        And user state upload info is not synced with uploaded files' indices
        And user state and all file urls waffle flags are enabled
        Then the URLs for all the uploaded files are obtained
        """
        user_state_waffle.return_value = True
        all_files_waffle.return_value = True
        self._setup_xblock_and_create_submission(xblock)
        # Download URL return value is empty due to indices inconsistency
        download_url.return_value = ""
        __, context = xblock.get_student_info_path_and_context('Bob')
        self._verify_user_state_usage_log_present(logger, **{'location': xblock.location})
        staff_urls = context['staff_file_urls']
        self.assertFalse(any(staff_urls))

        # If state doesn't provide data, it is possible to use all files urls workaround
        self.assertTrue(xblock.should_get_all_files_urls(staff_urls))
        download_url.return_value = FILE_URL

        # Calling this method directly as using `get_student_info_path_and_context`
        # will use user state. This is because we are mocking get_download_url method.
        staff_urls = xblock.get_all_upload_urls_for_user('Bob')
        expected_staff_urls = [{
            'download_url': FILE_URL,
            'description': '',
            'name': '',
            'size': None,
            'show_delete_button': False
        }] * xblock.MAX_FILES_COUNT
        self.assertEqual(staff_urls, expected_staff_urls)

        new_context = dict(context.items())
        new_context['staff_file_urls'] = staff_urls
        self._verify_staff_assessment_rendering(
            xblock,
            'openassessmentblock/staff_area/oa_staff_grade_learners_assessment.html',
            new_context,
            FILE_URL,
        )

    def _verify_staff_assessment_rendering(self, xblock, template_path, context, *expected_strings):
        """
        The file upload template has a hard dependency on the length of the file description tuple,
        so make sure we don't blow up when trying to render it with this context.
        """
        response = xblock.render_assessment(template_path, context_dict=context)
        for expected_string in expected_strings:
            self.assertIn(expected_string, response.body.decode('utf-8'))

    def _verify_staff_assessment_context(self, context, required, ungraded=None, in_progress=None):
        """
        Internal helper for common staff assessment context verification.
        """
        self.assertEqual(required, context['staff_assessment_required'])
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
    ):
        """
        Internal helper to define a mock runtime.
        """
        mock_runtime = Mock(
            course_id='test_course',
            item_id=item_id,
            anonymous_student_id=anonymous_user_id,
            user_is_staff=is_staff,
            user_is_admin=is_admin,
            user_is_beta=user_is_beta,
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

    def _create_team_submission(self, course_id, item_id, team_id, submitting_user_id, team_member_student_ids, answer):
        """
        Create a team submission and initialize a team workflow
        """
        team_submission = team_sub_api.create_submission_for_team(
            course_id,
            item_id,
            team_id,
            submitting_user_id,
            team_member_student_ids,
            answer,
        )
        team_workflow_api.create_workflow(team_submission['team_submission_uuid'])
        return team_submission

    @ddt.data('files_names', 'files_name')
    @scenario('data/self_only_scenario.xml', user_id='Bob')
    def test_file_name_is_rendered_on_template(self, xblock, key):
        """
        This test Validates the file name is visible to staff when viewing individual submission.
        """
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
            'files_descriptions': ["test_description"],
            'files_sizes': [],
            key: ["test_fileName"],
        }, ['self'])

        # Mock the file upload API to avoid hitting S3
        with patch("openassessment.xblock.apis.submissions.file_api.file_upload_api.get_download_url") as \
                get_download_url:
            get_download_url.return_value = "http://www.example.com/image.jpeg"
            # also fake a file_upload_type so our patched url gets rendered
            xblock.file_upload_type_raw = 'image'

            __, context = xblock.get_student_info_path_and_context("Bob")

            # Check that the right file key was passed to generate the download url
            get_download_url.assert_called_with("test_key")

            # Check the context passed to the template
            self.assertEqual(
                [{
                    'download_url': 'http://www.example.com/image.jpeg',
                    'description': 'test_description',
                    'name': 'test_fileName',
                    'size': 0,
                    'show_delete_button': False
                }],
                context['staff_file_urls']
            )

            # Check the rendered template
            payload = urllib.parse.urlencode({"student_username": "Bob"})
            resp = self.request(xblock, "render_student_info", payload).decode('utf-8')
            self.assertIn("http://www.example.com/image.jpeg", resp)

    @ddt.data(
        (False, False),
        (True, False),
        (False, True),
        (True, True),
    )
    @ddt.unpack
    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_show_unavailable_staff_override_section(self, xblock, cancelled_submission, grades_frozen):
        """
        If grades are frozen or a submission is cancelled, we want to show the override dropdown,
        but show a warning rather than the override form
        """
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, "Bob"
        )
        xblock.runtime._services['user'] = NullUserService()  # pylint: disable=protected-access

        # Create a submission
        bob_item = STUDENT_ITEM.copy()
        bob_item["item_id"] = xblock.scope_ids.usage_id
        submission = self._create_submission(bob_item, {'text': "Bob Answer"}, ['staff'])

        if cancelled_submission:
            workflow_api.cancel_workflow(
                submission_uuid=submission["uuid"],
                comments="Inappropriate language",
                cancelled_by_id=bob_item['student_id'],
                assessment_requirements={},
                course_settings={},
            )
        if grades_frozen:
            mock_are_grades_frozen = Mock(return_value=True)
            mock_grade_utils = Mock(are_grades_frozen=mock_are_grades_frozen)
            xblock.runtime._services['grade_utils'] = mock_grade_utils  # pylint: disable=protected-access

        payload = urllib.parse.urlencode({"student_username": "Bob"})
        resp = self.request(xblock, "render_student_info", payload).decode('utf-8')
        self.assertIn("Submit Assessment Grade Override", resp)
        if cancelled_submission:
            self.assertIn("Unable to perform grade override", resp)
            self.assertIn("This submission has been cancelled and cannot recieve a grade", resp)
        if grades_frozen:
            self.assertIn("Unable to perform grade override", resp)
            self.assertIn("Grades are frozen", resp)

    def _setup_xblock_and_create_submission(self, xblock, anonymous_user_id='Bob', has_team=True, **kwargs):
        """
        A shortcut method to setup ORA xblock and add a user submission or a team submission to the block.
        """
        self._setup_xblock(xblock, anonymous_user_id=anonymous_user_id, has_team=has_team)
        if xblock.teams_enabled:
            arbitrary_test_user = UserFactory.create()
            return self._create_team_submission(
                STUDENT_ITEM['course_id'],
                xblock.location,
                MOCK_TEAM_ID,
                arbitrary_test_user.id,
                xblock.get_anonymous_user_ids_for_team(),
                {'parts': [{'text': 'This is a team response'}]}
            )
        else:
            student_item = STUDENT_ITEM.copy()
            student_item["item_id"] = xblock.location
            return self._create_submission(student_item, {
                'text': "Text Answer",
                'file_keys': kwargs.get('file_keys', []),
                'files_descriptions': kwargs.get('files_descriptions', []),
                'files_names': kwargs.get('files_names', []),
                'files_sizes': kwargs.get('files_sizes', [])
            }, ['staff'])

    def _setup_xblock(self, xblock, anonymous_user_id='Bob', has_team=True):
        """
        Setup an xblock for teams / individual testing without creating a submission
        """
        xblock.xmodule_runtime = self._create_mock_runtime(
            xblock.scope_ids.usage_id, True, False, anonymous_user_id
        )
        # pylint: disable=protected-access
        xblock.runtime._services['user'] = NullUserService()
        xblock.runtime._services['user_state'] = UserStateService()
        if xblock.teams_enabled:
            xblock.runtime._services['teams'] = MockTeamsService(has_team)

        usage_id = xblock.scope_ids.usage_id
        xblock.location = usage_id
        xblock.user_state_upload_data_enabled = Mock(return_value=True)
        xblock.is_enhanced_staff_grader_enabled = False
        if xblock.teams_enabled:
            xblock.is_team_assignment = Mock(return_value=True)
            anonymous_user_ids_for_team = MOCK_TEAM_MEMBER_STUDENT_IDS
            xblock.get_anonymous_user_ids_for_team = Mock(return_value=anonymous_user_ids_for_team)

            # For both functions, map values in MOCK_TEAM_MEMBER_STUDENT_IDS to values in MOCK_TEAM_MEMBER_USERNAMES,
            # and if the parameters are not in those, just return the value itself. These are only defined in the
            # team case because otherwise MOCK_TEAM_MEMBER_(STUDENT_IDS|USERNAMES) have no meaning.
            def mock_get_username(student_id):
                if student_id in MOCK_TEAM_MEMBER_STUDENT_IDS:
                    return MOCK_TEAM_MEMBER_USERNAMES[MOCK_TEAM_MEMBER_STUDENT_IDS.index(student_id)]
                return student_id

            def mock_get_anonymous_id(username, _):
                if username in MOCK_TEAM_MEMBER_USERNAMES:
                    return MOCK_TEAM_MEMBER_STUDENT_IDS[MOCK_TEAM_MEMBER_USERNAMES.index(username)]
                return username

            xblock.get_username = Mock(side_effect=mock_get_username)
            xblock.get_anonymous_user_id = Mock(side_effect=mock_get_anonymous_id)

    @staticmethod
    def _verify_user_state_usage_log_present(logger, **kwargs):
        """
        Validates the presence of the logs indicating user state usage for upload info.
        """
        logger.check_present(
            (
                'openassessment.xblock.staff_area_mixin',
                'INFO',
                'Checking student module for upload info for user: {username} in block: {block}'.format(
                    username=kwargs.get('username', 'Bob'),
                    block=kwargs.get('location')
                )
            )
        )
