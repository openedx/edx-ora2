"""
Test OpenAssessment XBlock validation.
"""

from datetime import datetime as dt
import pytz
import ddt
from django.test import TestCase
from openassessment.xblock.validation import validate_assessments, validate_rubric, validate_dates


@ddt.ddt
class AssessmentValidationTest(TestCase):

    @ddt.file_data('data/valid_assessments.json')
    def test_valid_assessment(self, data):
        success, msg = validate_assessments([data['assessment']])
        self.assertTrue(success)
        self.assertEqual(msg, u'')

    @ddt.file_data('data/invalid_assessments.json')
    def test_invalid_assessment(self, data):
        success, msg = validate_assessments([data['assessment']])
        self.assertFalse(success)
        self.assertGreater(len(msg), 0)

    def test_no_assessments(self):
        success, msg = validate_assessments([])
        self.assertFalse(success)
        self.assertGreater(len(msg), 0)

    # Currently, we enforce the restriction that there must be
    # exactly two assessments, in the order (a) peer, then (b) self.
    # If and when we remove that restriction, this test can be deleted.
    @ddt.file_data('data/assessment_combo.json')
    def test_enforce_peer_then_self(self, data):
        success, msg = validate_assessments(data['assessments'], enforce_peer_then_self=True)
        self.assertEqual(success, data['valid'], msg=msg)

        if not success:
            self.assertGreater(len(msg), 0)


@ddt.ddt
class RubricValidationTest(TestCase):

    @ddt.file_data('data/valid_rubrics.json')
    def test_valid_assessment(self, data):
        success, msg = validate_rubric(data['rubric'])
        self.assertTrue(success)
        self.assertEqual(msg, u'')

    @ddt.file_data('data/invalid_rubrics.json')
    def test_invalid_assessment(self, data):
        success, msg = validate_rubric(data['rubric'])
        self.assertFalse(success)
        self.assertGreater(len(msg), 0)


@ddt.ddt
class DateValidationTest(TestCase):

    def setUp(self):
        self.DATES = {
            (day - 1): dt(2014, 1, day).replace(tzinfo=pytz.UTC).isoformat()
            for day in range(1, 15)
        }
        self.DATES[None] = None

    @ddt.file_data('data/valid_dates.json')
    def test_valid_dates(self, data):

        # Input data dict specifies the index for each date
        date = lambda key: self.DATES[data[key]]

        # This lambda is a convenience to map these dates to (start, due) tuples
        date_range = lambda start_key, due_key: (date(start_key), date(due_key))

        success, msg = validate_dates(
            date('xblock_start'), date('xblock_due'),
            [
                date_range('submission_start', 'submission_due'),
                date_range('peer_start', 'peer_due'),
                date_range('self_start', 'self_due'),
            ]
        )

        self.assertTrue(success, msg=msg)
        self.assertEqual(msg, u'')

    @ddt.file_data('data/invalid_dates.json')
    def test_invalid_dates(self, data):
        # Input data dict specifies the index for each date
        date = lambda key: self.DATES[data[key]]

        # This lambda is a convenience to map these dates to (start, due) tuples
        date_range = lambda start_key, due_key: (date(start_key), date(due_key))

        success, msg = validate_dates(
            date('xblock_start'), date('xblock_due'),
            [
                date_range('submission_start', 'submission_due'),
                date_range('peer_start', 'peer_due'),
                date_range('self_start', 'self_due'),
            ]
        )

        self.assertFalse(success)
        self.assertGreater(len(msg), 0)

    def test_invalid_date_format(self):
        valid = dt(2014, 1, 1).replace(tzinfo=pytz.UTC).isoformat()

        success, _ = validate_dates("invalid", valid, [(valid, valid)])
        self.assertFalse(success)

        success, _ = validate_dates(valid, "invalid", [(valid, valid)])
        self.assertFalse(success)

        success, _ = validate_dates(valid, valid, [("invalid", valid)])
        self.assertFalse(success)

        success, _ = validate_dates(valid, valid, [(valid, "invalid")])
        self.assertFalse(success)
