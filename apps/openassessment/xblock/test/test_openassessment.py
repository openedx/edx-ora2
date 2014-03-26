"""
Tests the Open Assessment XBlock functionality.
"""
from collections import namedtuple
import datetime as dt
import pytz
from mock import Mock, patch

from openassessment.xblock import openassessmentblock
from openassessment.workflow import api as workflow_api
from .base import XBlockHandlerTestCase, scenario


class TestOpenAssessment(XBlockHandlerTestCase):

    @scenario('data/basic_scenario.xml')
    def test_load_student_view(self, xblock):
        """OA XBlock returns some HTML to the user.

        View basic test for verifying we're returned some HTML about the
        Open Assessment XBlock. We don't want to match too heavily against the
        contents.
        """
        xblock_fragment = self.runtime.render(xblock, "student_view")
        self.assertTrue(xblock_fragment.body_html().find("Openassessmentblock"))

        # Validate Submission Rendering.
        submission_response = xblock.render_submission({})
        self.assertIsNotNone(submission_response)
        self.assertTrue(submission_response.body.find("openassessment__response"))

        # Validate Peer Rendering.
        request = namedtuple('Request', 'params')
        request.params = {}
        peer_response = xblock.render_peer_assessment(request)
        self.assertIsNotNone(peer_response)
        self.assertTrue(peer_response.body.find("openassessment__peer-assessment"))

        # Validate Self Rendering.
        self_response = xblock.render_self_assessment(request)
        self.assertIsNotNone(self_response)
        self.assertTrue(self_response.body.find("openassessment__peer-assessment"))

        # Validate Grading.
        grade_response = xblock.render_grade({})
        self.assertIsNotNone(grade_response)
        self.assertTrue(grade_response.body.find("openassessment__grade"))

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
                "peer": { "must_grade": 5, "must_be_graded_by": 3 }
            }
            mock_api.update_from_assessments.assert_called_once_with('test_submission', expected_reqs)

    @scenario('data/basic_scenario.xml')
    def test_student_view_workflow_error(self, xblock):

        # Simulate an error from updating the workflow
        xblock.submission_uuid = 'test_submission'
        with patch('openassessment.xblock.workflow_mixin.workflow_api') as mock_api:
            mock_api.update_from_assessments.side_effect = workflow_api.AssessmentWorkflowError
            xblock_fragment = self.runtime.render(xblock, "student_view")

        # Expect that the page renders even if the update fails
        self.assertTrue(xblock_fragment.body_html().find("Openassessmentblock"))

    @scenario('data/dates_scenario.xml')
    def test_load_student_view_with_dates(self, xblock):
        """OA XBlock returns some HTML to the user.

        View basic test for verifying we're returned some HTML about the
        Open Assessment XBlock. We don't want to match too heavily against the
        contents.
        """
        xblock_fragment = self.runtime.render(xblock, "student_view")
        self.assertTrue(xblock_fragment.body_html().find("Openassessmentblock"))

        # Validate Submission Rendering.
        submission_response = xblock.render_submission({})
        self.assertIsNotNone(submission_response)
        self.assertTrue(submission_response.body.find("openassessment__response"))
        self.assertTrue(submission_response.body.find("April"))

    @scenario('data/basic_scenario.xml')
    def test_formatted_dates(self, xblock):

        # Set start/due dates
        xblock.start = dt.datetime(2014, 4, 1, 1, 1, 1)
        xblock.due = dt.datetime(2014, 5, 1)

        request = namedtuple('Request', 'params')
        request.params = {}
        resp = xblock.render_peer_assessment(request)
        self.assertTrue(resp.body.find('Tuesday, April 01, 2014'))
        self.assertTrue(resp.body.find('Thursday, May 01, 2014'))

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


class TestDates(XBlockHandlerTestCase):

    @scenario('data/basic_scenario.xml')
    def test_start_end_date_checks(self, xblock):
        xblock.start = dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc).isoformat()
        xblock.due = dt.datetime(2014, 3, 5).replace(tzinfo=pytz.utc).isoformat()

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 2, 28, 23, 59, 59),
            None, True, "start",
            released=False
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 1, 1, 1, 1),
            None, False, None,
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 4, 23, 59, 59),
            None, False, None,
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 5, 1, 1, 1),
            None, True, "due",
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
            released=False
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "submission", False, None,
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 31, 23, 59, 59).replace(tzinfo=pytz.utc),
            "submission", False, None,
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 4, 1, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "submission", True, "due",
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
            released=False
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2015, 1, 2, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", False, None,
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2015, 3, 31, 23, 59, 59).replace(tzinfo=pytz.utc),
            "peer-assessment", False, None,
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2015, 4, 1, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", True, "due",
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
            released=False
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 1, 2, 1, 1, 1).replace(tzinfo=pytz.utc),
            "self-assessment", False, None,
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 3, 31, 23, 59, 59).replace(tzinfo=pytz.utc),
            "self-assessment", False, None,
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 4, 1, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "self-assessment", True, "due",
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
            released=False
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2014, 3, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", False, None,
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 5, 1, 23, 59, 59).replace(tzinfo=pytz.utc),
            "peer-assessment", False, None,
            released=True
        )

        self.assert_is_closed(
            xblock,
            dt.datetime(2016, 5, 2, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", True, "due",
            released=True
        )

    @scenario('data/basic_scenario.xml')
    def test_is_released_unpublished(self, xblock):
        # Simulate the runtime published_date mixin field
        # The scenario doesn't provide a start date, so `is_released()`
        # should be controlled only by the published date.
        xblock.published_date = None
        self.assertFalse(xblock.is_released())

    @scenario('data/basic_scenario.xml')
    def test_is_released_published(self, xblock):
        # Simulate the runtime published_date mixin field
        # The scenario doesn't provide a start date, so `is_released()`
        # should be controlled only by the published date.
        xblock.published_date = dt.datetime(2013, 1, 1).replace(tzinfo=pytz.utc)
        self.assertTrue(xblock.is_released())

    @scenario('data/basic_scenario.xml')
    def test_is_released_no_published_date_field(self, xblock):
        # If the runtime doesn't provide a published_date field, assume we've been published
        self.assertTrue(xblock.is_released())

    def assert_is_closed(self, xblock, now, step, expected_is_closed, expected_reason, released=None):
        """
        Assert whether the XBlock step is open/closed.

        Args:
            xblock (OpenAssessmentBlock): The xblock under test.
            now (datetime): Time to patch for the xblock's call to datetime.now()
            step (str): The step in the workflow (e.g. "submission", "self-assessment")
            expected_is_open (bool): Do we expect the step to be open or closed?
            expecetd_reason (str): Either "start", "due", or None.

        Kwargs:
            released (bool): If set, check whether the XBlock has been released.

        Raises:
            AssertionError
        """
        # Need some non-conventional setup to patch datetime because it's a C module.
        # http://nedbatchelder.com/blog/201209/mocking_datetimetoday.html
        # Thanks Ned!
        datetime_patcher = patch.object(openassessmentblock, 'dt', Mock(wraps=dt))
        mocked_datetime = datetime_patcher.start()
        self.addCleanup(datetime_patcher.stop)
        mocked_datetime.datetime.now.return_value = now

        is_closed, reason = xblock.is_closed(step=step)
        self.assertEqual(is_closed, expected_is_closed)
        self.assertEqual(reason, expected_reason)

        if released is not None:
            self.assertEqual(xblock.is_released(step=step), released)
