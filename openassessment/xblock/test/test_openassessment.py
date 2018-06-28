"""
Tests the Open Assessment XBlock functionality.
"""
from StringIO import StringIO
from collections import namedtuple
import datetime as dt
import json

import ddt
from freezegun import freeze_time
from lxml import etree
from mock import MagicMock, Mock, PropertyMock, patch
import pytz

from openassessment.workflow.errors import AssessmentWorkflowError
from openassessment.xblock import openassessmentblock
from openassessment.xblock.resolve_dates import DISTANT_FUTURE, DISTANT_PAST

from .base import XBlockHandlerTestCase, scenario


@ddt.ddt
class TestOpenAssessment(XBlockHandlerTestCase):
    """Test Open Asessessment Xblock functionality"""

    TIME_ZONE_FN_PATH = 'openassessment.xblock.user_data.get_user_preferences'

    @scenario('data/basic_scenario.xml')
    def test_load_student_view(self, xblock):
        """OA XBlock returns some HTML to the user.

        View basic test for verifying we're returned some HTML about the
        Open Assessment XBlock. We don't want to match too heavily against the
        contents.
        """
        xblock_fragment = self.runtime.render(xblock, "student_view")
        self.assertIn("OpenAssessmentBlock", xblock_fragment.body_html())

        # Validate Submission Rendering.
        submission_response = xblock.render_submission({})
        self.assertIsNotNone(submission_response)
        self.assertIn("step--response", submission_response.body)

        # Validate Peer Rendering.
        request = namedtuple('Request', 'params')
        request.params = {}
        peer_response = xblock.render_peer_assessment(request)
        self.assertIsNotNone(peer_response)
        self.assertIn("step--peer-assessment", peer_response.body)

        # Validate Self Rendering.
        self_response = xblock.render_self_assessment(request)
        self.assertIsNotNone(self_response)
        self.assertIn("step--self-assessment", self_response.body)

        # Validate Staff Grade.
        staff_response = xblock.render_staff_assessment(request)
        self.assertIsNotNone(self_response)
        self.assertIn("step--staff-assessment", staff_response.body)

        # Validate Grading.
        grade_response = xblock.render_grade({})
        self.assertIsNotNone(grade_response)
        self.assertIn("step--grade", grade_response.body)

    def _staff_assessment_view_helper(self, xblock):
        """
        Helper for "staff_assessment_view" tests

        """
        xblock_fragment = self.runtime.render(xblock, "grade_available_responses_view")
        body_html = xblock_fragment.body_html()
        self.assertIn("StaffAssessmentBlock", body_html)
        self.assertIn("openassessment__title", body_html)
        return body_html

    @scenario('data/staff_grade_scenario.xml')
    def test_staff_assessment_view(self, xblock):
        """OA XBlock returns some HTML for case if Staff Assessment is configured.

        View basic test for verifying auxiliary view which displays the staff grading area.
        """
        body_html = self._staff_assessment_view_helper(xblock)
        self.assertIn("openassessment__staff-area", body_html)
        self.assertIn("ui-staff__content", body_html)
        self.assertNotIn("openassessment__staff-area-unavailable", body_html)

    @scenario('data/basic_scenario.xml')
    def test_staff_assessment_view_staff_assessment_not_configured(self, xblock):
        """OA XBlock returns some HTML for case if Staff Assessment is not configured.

        View basic test for verifying auxiliary view which displays the staff grading area.
        """
        body_html = self._staff_assessment_view_helper(xblock)
        self.assertNotIn("ui-staff__content", body_html)
        self.assertIn("openassessment__staff-area-unavailable", body_html)

    @scenario('data/basic_scenario.xml')
    def test_ora_blocks_listing_view(self, xblock):
        """
        Test view for listing all courses OA blocks.

        """
        xblock_fragment = self.runtime.render(xblock, "ora_blocks_listing_view")
        body_html = xblock_fragment.body_html()

        self.assertIn("CourseOpenResponsesListingBlock", body_html)

        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(body_html), parser)

        xpath_query_to_get_main_section = "//section[contains(@class, 'open-response-assessment-block')]"
        xpath_query_to_get_course_items = "//script[contains(@id, 'open-response-assessment-items')]"

        sections = tree.xpath(xpath_query_to_get_main_section)
        self.assertEqual(len(sections), 1)
        self.assertEquals(sections[0].get('data-item-view-enabled'), '0')

        scripts = tree.xpath(xpath_query_to_get_course_items)
        self.assertEqual(len(scripts), 1)
        self.assertEqual(scripts[0].text, '[]')

        defined_ora_items = [{'id': 'test-id1', 'val': 'test-val1'},
                             {'id': 'test-id2', 'val': 'test-val2'}]

        xblock_fragment = self.runtime.render(xblock, "ora_blocks_listing_view", context={
            'ora_items': defined_ora_items,
            'ora_item_view_enabled': True
        })
        body_html = xblock_fragment.body_html()

        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(body_html), parser)

        sections = tree.xpath(xpath_query_to_get_main_section)
        self.assertEqual(len(sections), 1)
        self.assertEquals(sections[0].get('data-item-view-enabled'), '1')

        scripts = tree.xpath(xpath_query_to_get_course_items)
        self.assertEqual(len(scripts), 1)

        items = json.loads(scripts[0].text)
        self.assertEqual(items, defined_ora_items)

    @scenario('data/empty_prompt.xml')
    def test_prompt_intentionally_empty(self, xblock):
        # Verify that prompts intentionally left empty don't create DOM elements
        xblock_fragment = self.runtime.render(xblock, "student_view")
        body_html = xblock_fragment.body_html()
        present_prompt_text = "you'll provide a response to the prompt"
        missing_article = u'<article class="submission__answer__part__prompt'
        self.assertIn(present_prompt_text, body_html)
        self.assertNotIn(missing_article, body_html)

    @scenario('data/basic_scenario.xml')
    def test_page_load_updates_workflow(self, xblock):

        # No submission made, so don't update the workflow
        with patch('openassessment.xblock.workflow_mixin.workflow_api') as mock_api:
            self.runtime.render(xblock, "student_view")
            self.assertEqual(mock_api.update_from_assessments.call_count, 0)

        # Simulate one submission made (we have a submission ID)
        xblock.submission_uuid = 'test_submission'

        # Now that we have a submission, the workflow should get updated
        with patch('openassessment.xblock.workflow_mixin.workflow_api') as mock_api:
            self.runtime.render(xblock, "student_view")
            expected_reqs = {
                "peer": {"must_grade": 5, "must_be_graded_by": 3}
            }
            mock_api.update_from_assessments.assert_called_once_with('test_submission', expected_reqs)

    @scenario('data/basic_scenario.xml')
    def test_student_view_workflow_error(self, xblock):

        # Simulate an error from updating the workflow
        xblock.submission_uuid = 'test_submission'
        with patch('openassessment.xblock.workflow_mixin.workflow_api') as mock_api:
            mock_api.update_from_assessments.side_effect = AssessmentWorkflowError
            xblock_fragment = self.runtime.render(xblock, "student_view")

        # Expect that the page renders even if the update fails
        self.assertIn("OpenAssessmentBlock", xblock_fragment.body_html())

    @ddt.data(('utc', '04/01/2014 midnight'),
              ('America/Los_Angeles', '04/01/2014 midnight'))
    @ddt.unpack
    def test_load_student_view_with_dates(self, time_zone, expected_date):
        """OA XBlock returns some HTML to the user.

        View basic test for verifying we're returned some HTML about the
        Open Assessment XBlock. We don't want to match too heavily against the
        contents.
        """
        with patch('openassessment.xblock.user_data.get_user_preferences') as time_zone_fn:
            time_zone_fn.return_value['user_timezone'] = pytz.timezone(time_zone)

            xblock = self.load_scenario('data/dates_scenario.xml')
            xblock_fragment = self.runtime.render(xblock, "student_view")
            self.assertIn("OpenAssessmentBlock", xblock_fragment.body_html())

            # Validate Submission Rendering.
            submission_response = xblock.render_submission({})
            self.assertIsNotNone(submission_response)
            self.assertIn("step--response", submission_response.body)
            self.assertIn(expected_date, submission_response.body)

    def _set_up_start_date(self, start_date):
        """
        Helper function to set up start date for xblocks
        """
        xblock = self.load_scenario('data/basic_scenario.xml')
        xblock.start = start_date
        return xblock

    def _set_up_days_early_for_beta(self, xblock, days_early):
        """
        Helper function to set up start date early for beta testers
        """
        xblock.xmodule_runtime = Mock(
            course_id='test_course',
            anonymous_student_id='test_student',
            days_early_for_beta=days_early,
            user_is_staff=False,
            user_is_beta_tester=True
        )

    def _set_up_end_date(self, end_date):
        """
        Helper function to set up end date for xblocks
        """
        xblock = self.load_scenario('data/basic_scenario.xml')
        xblock.due = end_date
        return xblock

    def _render_xblock(self, xblock):
        """
        Helper function to render xblock
        """
        request = namedtuple('Request', 'params')
        request.params = {}
        return xblock.render_peer_assessment(request)

    @ddt.data(('utc', '2014-04-01T01:01:01+00:00'),
              ('America/Los_Angeles', '2014-04-01T01:01:01+00:00'))
    @ddt.unpack
    @freeze_time("2014-01-01")
    def test_formatted_start_dates(self, time_zone, expected_start_date):
        """Test start dates correctly formatted"""
        with patch(self.TIME_ZONE_FN_PATH) as time_zone_fn:
            time_zone_fn.return_value['user_timezone'] = pytz.timezone(time_zone)

            xblock = self._set_up_start_date(dt.datetime(2014, 4, 1, 1, 1, 1))
            resp = self._render_xblock(xblock)
            self.assertIn(expected_start_date, resp.body)

    @ddt.data(('utc', '2014-05-01T00:00:00+00:00'),
              ('America/Los_Angeles', '2014-05-01T00:00:00+00:00'))
    @ddt.unpack
    def test_formatted_end_dates(self, time_zone, expected_end_date):
        """Test end dates correctly formatted"""
        with patch(self.TIME_ZONE_FN_PATH) as time_zone_fn:
            time_zone_fn.return_value['user_timezone'] = time_zone

            # Set due dates'
            xblock = self._set_up_end_date(dt.datetime(2014, 5, 1))
            resp = self._render_xblock(xblock)
            self.assertIn(expected_end_date, resp.body)

    @ddt.data(('utc', '2014-04-01T01:01:01+00:00'),
              ('America/Los_Angeles', '2014-04-01T01:01:01+00:00'))
    @ddt.unpack
    @freeze_time("2014-01-01")
    def test_formatted_start_dates_for_beta_tester_with_days_early(self, time_zone, expected_start_date):
        """Test start dates for beta tester with days early"""
        with patch(self.TIME_ZONE_FN_PATH) as time_zone_fn:
            time_zone_fn.return_value['user_timezone'] = pytz.timezone(time_zone)

            # Set start dates
            xblock = self._set_up_start_date(dt.datetime(2014, 4, 6, 1, 1, 1))
            self._set_up_days_early_for_beta(xblock, 5)
            self.assertEqual(xblock.xmodule_runtime.days_early_for_beta, 5)

            resp = self._render_xblock(xblock)
            self.assertIn(expected_start_date, resp.body)

    @ddt.data(('utc', '2014-05-01T00:00:00+00:00'),
              ('America/Los_Angeles', '2014-05-01T00:00:00+00:00'))
    @ddt.unpack
    def test_formatted_end_dates_for_beta_tester_with_days_early(self, time_zone, expected_end_date):
        """Test end dates for beta tester with days early"""
        with patch(self.TIME_ZONE_FN_PATH) as time_zone_fn:
            time_zone_fn.return_value['user_timezone'] = pytz.timezone(time_zone)

            # Set due dates
            xblock = self._set_up_start_date(dt.datetime(2014, 4, 6, 1, 1, 1))
            xblock.due = dt.datetime(2014, 5, 1)
            self._set_up_days_early_for_beta(xblock, 5)
            self.assertEqual(xblock.xmodule_runtime.days_early_for_beta, 5)
            resp = self._render_xblock(xblock)
            self.assertIn(expected_end_date, resp.body)

    @ddt.data(('utc', '2014-04-06T01:01:01+00:00'),
              ('America/Los_Angeles', '2014-04-06T01:01:01+00:00'))
    @ddt.unpack
    @freeze_time("2014-01-01")
    @patch.object(openassessmentblock.OpenAssessmentBlock, 'is_beta_tester', new_callable=PropertyMock)
    def test_formatted_start_dates_for_beta_tester_without_days_early(
            self,
            time_zone,
            expected_start_date,
            mock_is_beta_tester
    ):
        """Test start dates for beta tester without days early"""
        with patch(self.TIME_ZONE_FN_PATH) as time_zone_fn:
            time_zone_fn.return_value['user_timezone'] = pytz.timezone(time_zone)
            mock_is_beta_tester.return_value = True

            # Set start dates
            xblock = self._set_up_start_date(dt.datetime(2014, 4, 6, 1, 1, 1))
            resp = self._render_xblock(xblock)
            self.assertIn(expected_start_date, resp.body)

    @ddt.data(('utc', '2014-05-01T00:00:00+00:00'),
              ('America/Los_Angeles', '2014-05-01T00:00:00+00:00'))
    @ddt.unpack
    @patch.object(openassessmentblock.OpenAssessmentBlock, 'is_beta_tester', new_callable=PropertyMock)
    def test_formatted_end_dates_for_beta_tester_without_days_early(
            self,
            time_zone,
            expected_end_date,
            mock_is_beta_tester
    ):
        """Test end dates for beta tester without days early"""
        with patch(self.TIME_ZONE_FN_PATH) as time_zone_fn:
            time_zone_fn.return_value['user_timezone'] = pytz.timezone(time_zone)
            mock_is_beta_tester.return_value = True

            # Set due dates
            xblock = self._set_up_end_date(dt.datetime(2014, 5, 1))
            resp = self._render_xblock(xblock)
            self.assertIn(expected_end_date, resp.body)

    @ddt.data(('utc', '2014-04-06T01:01:01+00:00'),
              ('America/Los_Angeles', '2014-04-06T01:01:01+00:00'))
    @ddt.unpack
    @freeze_time("2014-01-01")
    def test_formatted_start_dates_for_beta_tester_with_nonetype_days_early(self, time_zone, expected_start_date):
        """Test start dates for beta tester with NoneType days early"""
        with patch(self.TIME_ZONE_FN_PATH) as time_zone_fn:
            time_zone_fn.return_value = pytz.timezone(time_zone)

            # Set start dates
            xblock = self._set_up_start_date(dt.datetime(2014, 4, 6, 1, 1, 1))
            self._set_up_days_early_for_beta(xblock, None)
            self.assertEqual(xblock.xmodule_runtime.days_early_for_beta, None)

            resp = self._render_xblock(xblock)
            self.assertIn(expected_start_date, resp.body)

    @ddt.data(('utc', '2014-05-01T00:00:00+00:00'),
              ('America/Los_Angeles', '2014-05-01T00:00:00+00:00'))
    @ddt.unpack
    def test_formatted_end_dates_for_beta_tester_with_nonetype_days_early(self, time_zone, expected_end_date):
        """Test end dates for beta tester with NoneType days early"""
        with patch(self.TIME_ZONE_FN_PATH) as time_zone_fn:
            time_zone_fn.return_value = pytz.timezone(time_zone)

            # Set due dates
            xblock = self._set_up_end_date(dt.datetime(2014, 5, 1))
            self._set_up_days_early_for_beta(xblock, None)
            self.assertEqual(xblock.xmodule_runtime.days_early_for_beta, None)

            resp = self._render_xblock(xblock)
            self.assertIn(expected_end_date, resp.body)

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_default_fields(self, xblock):

        # Reset all fields in the XBlock to their default values
        for field_name, field in xblock.fields.iteritems():
            setattr(xblock, field_name, field.default)

        # Validate Submission Rendering.
        student_view = xblock.student_view({})
        self.assertIsNotNone(student_view)

    @scenario('data/basic_scenario.xml', user_id=2)
    def test_numeric_scope_ids(self, xblock):
        # Even if we're passed a numeric user ID, we should store it as a string
        # because that's what our models expect.
        student_item = xblock.get_student_item_dict()
        self.assertEqual(student_item['student_id'], '2')
        self.assertIsInstance(student_item['item_id'], unicode)

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_use_xmodule_runtime(self, xblock):
        # Prefer course ID and student ID provided by the XModule runtime
        xblock.xmodule_runtime = Mock(
            course_id='test_course',
            anonymous_student_id='test_student'
        )

        student_item = xblock.get_student_item_dict()
        self.assertEqual(student_item['course_id'], 'test_course')
        self.assertEqual(student_item['student_id'], 'test_student')

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_ignore_unknown_assessment_types(self, xblock):
        # If the XBlock contains an unknown assessment type
        # (perhaps after a roll-back), it should ignore it.
        xblock.rubric_assessments.append({'name': 'unknown'})

        # Check that the name is excluded from valid assessments
        self.assertNotIn({'name': 'unknown'}, xblock.valid_assessments)
        self.assertNotIn('unknown', xblock.assessment_steps)

        # Check that we can render the student view without error
        self.runtime.render(xblock, 'student_view')

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_prompts_fields(self, xblock):

        self.assertEqual(xblock.prompts, [
            {
                'description': (u'Given the state of the world today, what do you think should be done to '
                                u'combat poverty? Please answer in a short essay of 200-300 words.')
            },
            {
                'description': (u'Given the state of the world today, what do you think should be done to '
                                u'combat pollution?')
            }
        ])

        xblock.prompt = None
        self.assertEqual(xblock.prompts, [{'description': ''}])

        xblock.prompt = 'Prompt.'
        self.assertEqual(xblock.prompts, [{'description': 'Prompt.'}])

        xblock.prompt = '[{"description": "Prompt 1."}, {"description": "Prompt 2."}, {"description": "Prompt 3."}]'
        self.assertEqual(xblock.prompts, [
            {'description': 'Prompt 1.'}, {'description': 'Prompt 2.'}, {'description': 'Prompt 3.'}
        ])

        xblock.prompts = None
        self.assertEqual(xblock.prompt, None)

        xblock.prompts = [{'description': 'Prompt.'}]
        self.assertEqual(xblock.prompt, 'Prompt.')

        xblock.prompts = [{'description': 'Prompt 4.'}, {'description': 'Prompt 5.'}]
        self.assertEqual(xblock.prompt, '[{"description": "Prompt 4."}, {"description": "Prompt 5."}]')

    @scenario('data/neither_response_type.xml')
    def test_no_response_type(self, xblock):
        """
        Ensure that legacy courses will still load properly.
        """
        self.assertEqual(xblock.text_response, 'required')


class TestDates(XBlockHandlerTestCase):

    @scenario('data/basic_scenario.xml')
    def test_start_end_date_checks(self, xblock):
        xblock.start = dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc)
        xblock.due = dt.datetime(2014, 3, 5).replace(tzinfo=pytz.utc)

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 2, 28, 23, 59, 59),
            None, True, "start", xblock.start, xblock.due,
            released=False
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 1, 1, 1, 1),
            None, False, None, xblock.start, xblock.due,
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 4, 23, 59, 59),
            None, False, None, xblock.start, xblock.due,
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 5, 1, 1, 1),
            None, True, "due", xblock.start, xblock.due,
            released=True
        )

    @scenario('data/dates_scenario.xml')
    def test_submission_dates(self, xblock):
        # Scenario defines submission due at 2014-04-01
        xblock.start = dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc).isoformat()
        xblock.due = None

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 2, 28, 23, 59, 59).replace(tzinfo=pytz.utc),
            "submission", True, "start",
            dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc),
            dt.datetime(2014, 4, 1).replace(tzinfo=pytz.utc),
            released=False
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "submission", False, None,
            dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc),
            dt.datetime(2014, 4, 1).replace(tzinfo=pytz.utc),
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 31, 23, 59, 59).replace(tzinfo=pytz.utc),
            "submission", False, None,
            dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc),
            dt.datetime(2014, 4, 1).replace(tzinfo=pytz.utc),
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 4, 1, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "submission", True, "due",
            dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc),
            dt.datetime(2014, 4, 1).replace(tzinfo=pytz.utc),
            released=True
        )

    @scenario('data/dates_scenario.xml')
    def test_peer_assessment_dates(self, xblock):
        # Scenario defines peer assessment open from 2015-01-02 to 2015-04-01
        xblock.start = None
        xblock.due = None

        self.assert_is_closed(
            xblock,
            dt.datetime(2015, 1, 1, 23, 59, 59).replace(tzinfo=pytz.utc),
            "peer-assessment", True, "start",
            dt.datetime(2015, 1, 2).replace(tzinfo=pytz.utc),
            dt.datetime(2015, 4, 1).replace(tzinfo=pytz.utc),
            released=False
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2015, 1, 2, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", False, None,
            dt.datetime(2015, 1, 2).replace(tzinfo=pytz.utc),
            dt.datetime(2015, 4, 1).replace(tzinfo=pytz.utc),
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2015, 3, 31, 23, 59, 59).replace(tzinfo=pytz.utc),
            "peer-assessment", False, None,
            dt.datetime(2015, 1, 2).replace(tzinfo=pytz.utc),
            dt.datetime(2015, 4, 1).replace(tzinfo=pytz.utc),
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2015, 4, 1, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", True, "due",
            dt.datetime(2015, 1, 2).replace(tzinfo=pytz.utc),
            dt.datetime(2015, 4, 1).replace(tzinfo=pytz.utc),
            released=True
        )

    @scenario('data/dates_scenario.xml')
    def test_self_assessment_dates(self, xblock):
        # Scenario defines peer assessment open from 2016-01-02 to 2016-04-01
        xblock.start = None
        xblock.due = None

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 1, 1, 23, 59, 59).replace(tzinfo=pytz.utc),
            "self-assessment", True, "start",
            dt.datetime(2016, 1, 2).replace(tzinfo=pytz.utc),
            dt.datetime(2016, 4, 1).replace(tzinfo=pytz.utc),
            released=False
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 1, 2, 1, 1, 1).replace(tzinfo=pytz.utc),
            "self-assessment", False, None,
            dt.datetime(2016, 1, 2).replace(tzinfo=pytz.utc),
            dt.datetime(2016, 4, 1).replace(tzinfo=pytz.utc),
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 3, 31, 23, 59, 59).replace(tzinfo=pytz.utc),
            "self-assessment", False, None,
            dt.datetime(2016, 1, 2).replace(tzinfo=pytz.utc),
            dt.datetime(2016, 4, 1).replace(tzinfo=pytz.utc),
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 4, 1, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "self-assessment", True, "due",
            dt.datetime(2016, 1, 2).replace(tzinfo=pytz.utc),
            dt.datetime(2016, 4, 1).replace(tzinfo=pytz.utc),
            released=True
        )

    @scenario('data/resolve_dates_scenario.xml')
    def test_resolve_dates(self, xblock):
        # Peer-assessment does not have dates specified, so it should resolve
        # to the previous start (problem start time)
        # and following due date (self-assessment, at 2016-05-02)
        xblock.start = dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc).isoformat()
        xblock.due = None

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 2, 28, 23, 59, 59).replace(tzinfo=pytz.utc),
            "peer-assessment", True, "start",
            dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc),
            dt.datetime(2016, 5, 2).replace(tzinfo=pytz.utc),
            released=False
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", False, None,
            dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc),
            dt.datetime(2016, 5, 2).replace(tzinfo=pytz.utc),
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 5, 1, 23, 59, 59).replace(tzinfo=pytz.utc),
            "peer-assessment", False, None,
            dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc),
            dt.datetime(2016, 5, 2).replace(tzinfo=pytz.utc),
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 5, 2, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", True, "due",
            dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc),
            dt.datetime(2016, 5, 2).replace(tzinfo=pytz.utc),
            released=True
        )

    @scenario('data/basic_scenario.xml')
    def test_is_closed_uses_utc(self, xblock):
        # No dates are set in the basic scenario
        # so we can safely set the release date to one minute in the past (in UTC)
        xblock.start = dt.datetime.utcnow().replace(tzinfo=pytz.utc) - dt.timedelta(minutes=1)

        # Since the start date is in the past, the problem should be available
        is_closed, __, __, __ = xblock.is_closed()
        self.assertFalse(is_closed)

        # Set the start date one hour in the future (in UTC)
        xblock.start = dt.datetime.utcnow().replace(tzinfo=pytz.utc) + dt.timedelta(hours=1)

        # Now the problem should be open
        is_closed, __, __, __ = xblock.is_closed()
        self.assertTrue(is_closed)

    @scenario('data/basic_scenario.xml')
    def test_is_released_unpublished(self, xblock):
        # The scenario doesn't provide a start date, so `is_released()`
        # should be controlled only by the published state.
        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = False
        self.assertFalse(xblock.is_released())

    @scenario('data/basic_scenario.xml')
    def test_is_released_published(self, xblock):
        # The scenario doesn't provide a start date, so `is_released()`
        # should be controlled only by the published state which defaults to True
        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = True
        self.assertTrue(xblock.is_released())

    @scenario('data/basic_scenario.xml')
    def test_is_released_published_scheduled(self, xblock):
        # The scenario doesn't provide a start date, so `is_released()`
        # should be controlled only by the published state which defaults to True
        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = True

        # Set the start date one day ahead in the future (in UTC)
        xblock.start = dt.datetime.utcnow().replace(tzinfo=pytz.utc) + dt.timedelta(days=1)

        # Check that it is not yet released
        self.assertFalse(xblock.is_released())

    @scenario('data/basic_scenario.xml')
    def test_is_released_no_ms(self, xblock):
        self.assertTrue(xblock.is_released())

    @scenario('data/basic_scenario.xml')
    def test_is_released_course_staff(self, xblock):
        # Simulate being course staff
        xblock.xmodule_runtime = Mock(user_is_staff=True)

        # Published, should be released
        self.assertTrue(xblock.is_released())

        # Not published, should be not released
        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = False
        self.assertFalse(xblock.is_released())

    @scenario('data/staff_dates_scenario.xml')
    def test_course_staff_dates(self, xblock):

        xblock.start = None
        xblock.due = None

        # The problem should always be open for course staff
        # The following assertions check before/during/after dates
        # for submission/peer/self
        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 2, 28, 23, 59, 59).replace(tzinfo=pytz.utc),
            "submission", False, None,
            DISTANT_PAST, DISTANT_FUTURE,
            course_staff=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "submission", False, None,
            DISTANT_PAST, DISTANT_FUTURE,
            course_staff=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 31, 23, 59, 59).replace(tzinfo=pytz.utc),
            "submission", False, None,
            DISTANT_PAST, DISTANT_FUTURE,
            course_staff=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 4, 1, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "submission", False, None,
            DISTANT_PAST, DISTANT_FUTURE,
            course_staff=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2015, 1, 1, 23, 59, 59).replace(tzinfo=pytz.utc),
            "peer-assessment", False, None,
            DISTANT_PAST, DISTANT_FUTURE,
            course_staff=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2015, 1, 2, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", False, None,
            DISTANT_PAST, DISTANT_FUTURE,
            course_staff=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2015, 3, 31, 23, 59, 59).replace(tzinfo=pytz.utc),
            "peer-assessment", False, None,
            DISTANT_PAST, DISTANT_FUTURE,
            course_staff=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2015, 4, 1, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", False, None,
            DISTANT_PAST, DISTANT_FUTURE,
            course_staff=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 1, 1, 23, 59, 59).replace(tzinfo=pytz.utc),
            "self-assessment", False, None,
            DISTANT_PAST, DISTANT_FUTURE,
            course_staff=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 1, 2, 1, 1, 1).replace(tzinfo=pytz.utc),
            "self-assessment", False, None,
            DISTANT_PAST, DISTANT_FUTURE,
            course_staff=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 3, 31, 23, 59, 59).replace(tzinfo=pytz.utc),
            "self-assessment", False, None,
            DISTANT_PAST, DISTANT_FUTURE,
            course_staff=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 4, 1, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "self-assessment", False, None,
            DISTANT_PAST, DISTANT_FUTURE,
            course_staff=True
        )

    def assert_is_closed(
        self, xblock, now, step, expected_is_closed, expected_reason,
        expected_start, expected_due, released=None, course_staff=False,
    ):
        """
        Assert whether the XBlock step is open/closed.

        Args:
            xblock (OpenAssessmentBlock): The xblock under test.
            now (datetime): Time to patch for the xblock's call to datetime.now()
            step (str): The step in the workflow (e.g. "submission", "self-assessment")
            expected_is_closed (bool): Do we expect the step to be open or closed?
            expected_reason (str): Either "start", "due", or None.
            expected_start (datetime): Expected start date.
            expected_due (datetime): Expected due date.

        Keyword Arguments:
            released (bool): If set, check whether the XBlock has been released.
            course_staff (bool): Whether to treat the user as course staff.

        Raises:
            AssertionError
        """
        # Need some non-conventional setup to patch datetime because it's a C module.
        # http://nedbatchelder.com/blog/201209/mocking_datetimetoday.html
        # Thanks Ned!
        datetime_patcher = patch.object(openassessmentblock, 'dt', Mock(wraps=dt))
        mocked_datetime = datetime_patcher.start()
        self.addCleanup(datetime_patcher.stop)
        mocked_datetime.datetime.utcnow.return_value = now

        is_closed, reason, start, due = xblock.is_closed(step=step, course_staff=course_staff)
        self.assertEqual(is_closed, expected_is_closed)
        self.assertEqual(reason, expected_reason)
        self.assertEqual(start, expected_start)
        self.assertEqual(due, expected_due)

        if released is not None:
            self.assertEqual(xblock.is_released(step=step), released)

    @scenario('data/basic_scenario.xml')
    def test_get_username(self, xblock):
        user = MagicMock()
        user.username = "Bob"

        xblock.xmodule_runtime = MagicMock()
        xblock.xmodule_runtime.get_real_user.return_value = user

        self.assertEqual('Bob', xblock.get_username('anon_id'))

    @scenario('data/basic_scenario.xml')
    def test_get_username_unknown_id(self, xblock):
        xblock.xmodule_runtime = MagicMock()
        xblock.xmodule_runtime.get_real_user.return_value = None

        self.assertIsNone(xblock.get_username('unknown_id'))
