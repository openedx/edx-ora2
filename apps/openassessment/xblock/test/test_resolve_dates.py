"""
Test resolving unspecified dates and date strings to datetimes.
"""

import datetime
import pytz
from django.test import TestCase
import ddt
from openassessment.xblock.resolve_dates import resolve_dates, DISTANT_PAST, DISTANT_FUTURE


@ddt.ddt
class ResolveDatesTest(TestCase):

    def setUp(self):
        # Construct a dictionary of datetimes for our test data to index
        self.DATES = {
            (day - 1): datetime.datetime(2014, 1, day).replace(tzinfo=pytz.UTC)
            for day in range(1, 15)
        }
        self.DATES[-1] = DISTANT_PAST
        self.DATES[99] = DISTANT_FUTURE

        # Construct a dictionary of ISO-formatted date strings for our test data to index
        self.DATE_STRINGS = {key: val.isoformat() for key, val in self.DATES.iteritems()}
        self.DATE_STRINGS[None] = None

    @ddt.file_data('data/resolve_dates.json')
    def test_resolve_dates(self, data):

        # Test data provides indices into our date dictionaries
        resolved_start, resolved_end, resolved_ranges = resolve_dates(
            self.DATE_STRINGS[data['start']],
            self.DATE_STRINGS[data['end']],
            [
                (self.DATE_STRINGS[start], self.DATE_STRINGS[end])
                for start, end in tuple(data['date_ranges'])
            ]
        )
        self.assertEqual(resolved_start, self.DATES[data['resolved_start']])
        self.assertEqual(resolved_end, self.DATES[data['resolved_end']])
        self.assertEqual(
            resolved_ranges,
            [
                (self.DATES[start], self.DATES[end])
                for start, end in tuple(data['resolved_ranges'])
            ]
        )