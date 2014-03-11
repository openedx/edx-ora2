"""
Tests the Open Assessment XBlock functionality.
"""
import json
import datetime as dt
import pytz

from mock import Mock, patch

from openassessment.xblock import openassessmentblock
from openassessment.xblock.submission_mixin import SubmissionMixin
from submissions import api as sub_api
from submissions.api import SubmissionRequestError, SubmissionInternalError

from .base import XBlockHandlerTestCase, scenario


class TestOpenAssessment(XBlockHandlerTestCase):

    SUBMISSION = json.dumps({"submission": "This is my answer to this test question!"})

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_submit_submission(self, xblock):
        """XBlock accepts response, returns true on success"""
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertTrue(resp[0])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_submission_multisubmit_failure(self, xblock):
        """XBlock returns true on first, false on second submission"""

        # We don't care about return value of first one
        self.request(xblock, 'submit', self.SUBMISSION, response_format='json')

        # This one should fail because we're not allowed to submit multiple times
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "ENOMULTI")
        self.assertEqual(resp[2], xblock.submit_errors["ENOMULTI"])

    @scenario('data/basic_scenario.xml')
    @patch.object(sub_api, 'create_submission')
    def test_submission_general_failure(self, xblock, mock_submit):
        """Internal errors return some code for submission failure."""
        mock_submit.side_effect = SubmissionInternalError("Cat on fire.")
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "EUNKNOWN")
        self.assertEqual(resp[2], SubmissionMixin().submit_errors["EUNKNOWN"])

    @scenario('data/basic_scenario.xml')
    @patch.object(sub_api, 'create_submission')
    def test_submission_API_failure(self, xblock, mock_submit):
        """API usage errors return code and meaningful message."""
        mock_submit.side_effect = SubmissionRequestError("Cat on fire.")
        resp = self.request(xblock, 'submit', self.SUBMISSION, response_format='json')
        self.assertFalse(resp[0])
        self.assertEqual(resp[1], "EBADFORM")
        self.assertEqual(resp[2], "Cat on fire.")

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
        peer_response = xblock.render_peer_assessment({})
        self.assertIsNotNone(peer_response)
        self.assertTrue(peer_response.body.find("openassessment__peer-assessment"))

        # Validate Self Rendering.
        self_response = xblock.render_self_assessment({})
        self.assertIsNotNone(self_response)
        self.assertTrue(self_response.body.find("openassessment__peer-assessment"))

        # Validate Grading.
        grade_response = xblock.render_grade({})
        self.assertIsNotNone(grade_response)
        self.assertTrue(grade_response.body.find("openassessment__grade"))

    @scenario('data/basic_scenario.xml')
    def test_course_id_from_runtime(self, xblock):

        # Check the default course ID (runtime does not support it)
        self.assertEqual('not supported', xblock.get_student_item_dict()['course_id'])

        # Simulate a runtime that supports course IDs
        xblock.runtime.course_id = 'Test Course'
        self.assertEqual('Test Course', xblock.get_student_item_dict()['course_id'])

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_default_fields(self, xblock):

        # Reset all fields in the XBlock to their default values
        for field_name, field in xblock.fields.iteritems():
            setattr(xblock, field_name, field.default)

        # Validate Submission Rendering.
        student_view = xblock.student_view({})
        self.assertIsNotNone(student_view)


class TestDates(XBlockHandlerTestCase):

    @scenario('data/basic_scenario.xml')
    def test_start_end_date_checks(self, xblock):
        xblock.start = dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc).isoformat()
        xblock.due = dt.datetime(2014, 3, 5).replace(tzinfo=pytz.utc).isoformat()

        self.assert_is_open(
            xblock,
            dt.datetime(2014, 2, 28, 23, 59, 59),
            None, False, "start"
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2014, 3, 1, 1, 1, 1),
            None, True, None
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2014, 3, 4, 23, 59, 59),
            None, True, None
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2014, 3, 5, 1, 1, 1),
            None, False, "due"
        )

    @scenario('data/dates_scenario.xml')
    def test_submission_dates(self, xblock):
        # Scenario defines submission due at 2014-04-01
        xblock.start = dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc).isoformat()
        xblock.due = None

        self.assert_is_open(
            xblock,
            dt.datetime(2014, 2, 28, 23, 59, 59).replace(tzinfo=pytz.utc),
            "submission", False, "start"
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2014, 3, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "submission", True, None
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2014, 3, 31, 23, 59, 59).replace(tzinfo=pytz.utc),
            "submission", True, None
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2014, 4, 1, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "submission", False, "due"
        )

    @scenario('data/dates_scenario.xml')
    def test_peer_assessment_dates(self, xblock):
        # Scenario defines peer assessment open from 2015-01-02 to 2015-04-01
        xblock.start = None
        xblock.due = None

        self.assert_is_open(
            xblock,
            dt.datetime(2015, 1, 1, 23, 59, 59).replace(tzinfo=pytz.utc),
            "peer-assessment", False, "start"
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2015, 1, 2, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", True, None
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2015, 3, 31, 23, 59, 59).replace(tzinfo=pytz.utc),
            "peer-assessment", True, None
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2015, 4, 1, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", False, "due"
        )

    @scenario('data/dates_scenario.xml')
    def test_self_assessment_dates(self, xblock):
        # Scenario defines peer assessment open from 2016-01-02 to 2016-04-01
        xblock.start = None
        xblock.due = None

        self.assert_is_open(
            xblock,
            dt.datetime(2016, 1, 1, 23, 59, 59).replace(tzinfo=pytz.utc),
            "self-assessment", False, "start"
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2016, 1, 2, 1, 1, 1).replace(tzinfo=pytz.utc),
            "self-assessment", True, None
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2016, 3, 31, 23, 59, 59).replace(tzinfo=pytz.utc),
            "self-assessment", True, None
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2016, 4, 1, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "self-assessment", False, "due"
        )

    @scenario('data/resolve_dates_scenario.xml')
    def test_resolve_dates(self, xblock):
        # Peer-assessment does not have dates specified, so it should resolve
        # to the previous start (problem start time)
        # and following due date (self-assessment, at 2016-05-02)
        xblock.start = dt.datetime(2014, 3, 1).replace(tzinfo=pytz.utc).isoformat()
        xblock.due = None

        self.assert_is_open(
            xblock,
            dt.datetime(2014, 2, 28, 23, 59, 59).replace(tzinfo=pytz.utc),
            "peer-assessment", False, "start"
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2014, 3, 1, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", True, None
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2016, 5, 1, 23, 59, 59).replace(tzinfo=pytz.utc),
            "peer-assessment", True, None
        )

        self.assert_is_open(
            xblock,
            dt.datetime(2016, 5, 2, 1, 1, 1).replace(tzinfo=pytz.utc),
            "peer-assessment", False, "due"
        )

    def assert_is_open(self, xblock, now, step, expected_is_open, expected_reason):
        """
        Assert whether the XBlock step is open/closed.

        Args:
            xblock (OpenAssessmentBlock): The xblock under test.
            now (datetime): Time to patch for the xblock's call to datetime.now()
            step (str): The step in the workflow (e.g. "submission", "self-assessment")
            expected_is_open (bool): Do we expect the step to be open or closed?
            expecetd_reason (str): Either "start", "due", or None.

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

        is_open, reason = xblock.is_open(step=step)
        self.assertEqual(is_open, expected_is_open)
        self.assertEqual(reason, expected_reason)