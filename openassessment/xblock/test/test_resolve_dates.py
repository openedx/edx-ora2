"""
Test resolving unspecified dates and date strings to datetimes.
"""

import datetime
from django.test import TestCase
import ddt
from mock import MagicMock
from openassessment.xblock.resolve_dates import resolve_dates, DISTANT_PAST, DISTANT_FUTURE, get_current_time_zone
import pytz
from workbench.runtime import WorkBenchUserService


STUB_I18N = lambda x: x


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
            ],
            STUB_I18N
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

    def test_min_start_date(self):
        # Start date should resolve to the min of all start dates
        # See the detailed comment in the docstring of `resolve_dates`
        # for the reasoning behind this.
        resolved_start, __, __ = resolve_dates(
            "2013-01-01", None,
            [
                ("1999-01-01", "1999-02-03"),
                ("2003-01-01", "2003-02-03"),
                ("3234-01-01", "3234-02-03"),
            ],
            STUB_I18N
        )

        # Should default to the min of all specified start dates
        self.assertEqual(
            resolved_start,
            datetime.datetime(1999, 1, 1).replace(tzinfo=pytz.UTC)
        )

    def test_max_due_date(self):
        # End date should resolve to the max of all end dates
        # See the detailed comment in the docstring of `resolve_dates`
        # for the reasoning behind this.
        __, resolved_end, __ = resolve_dates(
            None, "2013-01-01",
            [
                ("1999-01-01", "1999-02-03"),
                ("2003-01-01", "2003-02-03"),
                ("3234-01-01", "3234-02-03"),
            ],
            STUB_I18N
        )

        # Should default to the max of all specified end dates
        self.assertEqual(
            resolved_end,
            datetime.datetime(3234, 2, 3).replace(tzinfo=pytz.UTC)
        )

    def test_start_greater_than_end(self):
        # Handle the special case in which the problem's release
        # date is after the problem's start date, and we've
        # specified only one deadline.
        resolve_dates(
            "2040-01-01", "2013-01-02",
            [
                (None, "2014-08-01"),
                (None, None),
                (None, None)
            ],
            STUB_I18N
        )

    def test_start_after_step_due(self):
        # Bugfix: this should not raise a validation error
        resolve_dates(
            "2040-01-01", None,
            [
                (None, "2014-08-01"),
                (None, None),
                (None, None)
            ],
            STUB_I18N
        )

    def test_due_before_step_start(self):
        # Bugfix: this should not raise a validation error
        resolve_dates(
            None, "2001-01-01",
            [
                (None, None),
                ("2014-02-03", None),
                (None, None)
            ],
            STUB_I18N
        )

    @ddt.data(({}, pytz.utc),
              ({'pref-lang': 'en', 'time_zone': 'America/Los_Angeles'}, pytz.timezone('America/Los_Angeles')))
    @ddt.unpack
    def test_get_current_time_zone(self, user_preferences, expected_time_zone):
        """Verify get_current_time_zone returns correct time zone or UTC"""
        user_service = WorkBenchUserService(3)
        user_service.get_current_user().opt_attrs['edx-platform.user_preferences'] = user_preferences

        time_zone = get_current_time_zone(user_service)
        self.assertEqual(expected_time_zone, time_zone)
