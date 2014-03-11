"""
Resolve unspecified dates and date strings to datetimes.
"""
import datetime as dt
import pytz
from dateutil.parser import parse as parse_date
from django.utils.translation import ugettext as _


class InvalidDateFormat(Exception):
    """
    The date string could not be parsed.
    """
    pass


class DateValidationError(Exception):
    """
    Dates are not semantically valid.
    """
    pass


DISTANT_PAST = dt.datetime(dt.MINYEAR, 1, 1, tzinfo=pytz.utc)
DISTANT_FUTURE = dt.datetime(dt.MAXYEAR, 1, 1, tzinfo=pytz.utc)


def _parse_date(value):
    """
    Parse an ISO formatted datestring into a datetime object with timezone set to UTC.

    Args:
        value (str or datetime): The ISO formatted date string or datetime object.

    Returns:
        datetime.datetime

    Raises:
        InvalidDateFormat: The date string could not be parsed.
    """
    if isinstance(value, dt.datetime):
        return value.replace(tzinfo=pytz.utc)

    elif isinstance(value, basestring):
        try:
            return parse_date(value).replace(tzinfo=pytz.utc)
        except ValueError:
            raise InvalidDateFormat(_("Could not parse date '{date}'").format(date=value))

    else:
        raise InvalidDateFormat(_("'{date}' must be a date string or datetime").format(date=value))


def resolve_dates(start, end, date_ranges):
    """
    Resolve date strings (including "default" dates) to datetimes.
    The basic rules are:

        1) Unset problem start dates default to the distant past.
        2) Unset problem end dates default to the distant future.
        3) Unset start dates default to the start date of the previous assessment/submission.
            (The first submission defaults to the problem start date.)
        4) Unset end dates default to the end date of the following assessment/submission.
            (The last assessment defaults to the problem end date.)

    Example:

        Suppose I have a problem with a submission and two assessments:

        |                                                                               |
        |    |== submission ==|   |== peer-assessessment ==|   |== self-assessment ==|  |
        |                                                                               |

        and I set start/due dates for the submission and self-assessment, but not for peer-assessment.
        Then by default, peer-assessment will "expand":

        |                                                                               |
        |    |== submission ==|                                |== self-assessment ==|  |
        |    |============================ peer-assessment ==========================|  |
        |                                                                               |

        If I then remove the due date for the submission, but add a due date for peer-assessment:

        |                                                                               |
        |    |== submission =============================|  |== self-assessment ==|     |
        |    |============== peer-assessment ============|                              |
        |                                                                               |

        If no dates are set, start dates default to the distant past and end dates default
        to the distant future:

        |                                                    |
        |    |================= submission ==============|   |
        |    |============== self-assessment ============|   |
        |    |============== peer-assessment ============|   |
        |                                                    |


    Args:
        start (str, ISO date format, or datetime): When the problem opens.  A value of None indicates that the problem is always open.
        end (str, ISO date format, or datetime): When the problem closes.  A value of None indicates that the problem never closes.
        date_ranges (list of tuples): list of (start, end) ISO date string tuples indicating
            the start/end timestamps (date string or datetime) of each submission/assessment.

    Returns:
        start (datetime): The resolved start date
        end (datetime): The resolved end date.
        list of (start, end) tuples, where both elements are datetime objects.

    Raises:
        DateValidationError
        InvalidDateFormat
    """
    # Resolve problem start and end dates to minimum and maximum dates
    start = _parse_date(start) if start is not None else DISTANT_PAST
    end = _parse_date(end) if end is not None else DISTANT_FUTURE
    resolved_starts = []
    resolved_ends = []

    # Validate the problem start/end dates
    if start >= end:
        msg = _(u"Problem start date '{start}' cannot be later than the problem due date '{due}'.").format(
            start=start, due=end
        )
        raise DateValidationError(msg)

    # Iterate through the list forwards and backwards simultaneously
    # As we iterate forwards, resolve start dates.
    # As we iterate backwards, resolve end dates.
    prev_start = start
    prev_end = end
    for index in range(len(date_ranges)):
        reverse_index = len(date_ranges) - index - 1

        # Resolve "default" start dates to the previous start date.
        # If I set a start date for peer-assessment, but don't set a start date for the following self-assessment,
        # then the self-assessment should default to the same start date as the peer-assessment.
        step_start, __ = date_ranges[index]
        step_start = _parse_date(step_start) if step_start is not None else prev_start

        # Resolve "default" end dates to the following end date.
        # If I set a due date for self-assessment, but don't set a due date for the previous peer-assessment,
        # then the peer-assessment should default to the same due date as the self-assessment.
        __, step_end = date_ranges[reverse_index]
        step_end = _parse_date(step_end) if step_end is not None else prev_end

        if step_start < prev_start:
            msg = _(u"The start date '{start}' must be after the previous start date '{prev}'.").format(
                start=step_start, prev=prev_start
            )
            raise DateValidationError(msg)

        if step_end > prev_end:
            msg = _(u"The due date '{due}' must be before the following due date '{prev}'.").format(
                due=step_end, prev=prev_end
            )
            raise DateValidationError(msg)

        resolved_starts.append(step_start)
        resolved_ends.insert(0, step_end)
        prev_start = step_start
        prev_end = step_end

    # Combine the resolved dates back into a list of tuples
    resolved_ranges = zip(resolved_starts, resolved_ends)

    # Now that we have resolved both start and end dates, we can safely compare them
    for resolved_start, resolved_end in resolved_ranges:
        if resolved_start >= resolved_end:
            msg = _(u"Start date '{start}' cannot be later than the due date '{due}'").format(
                start=resolved_start, due=resolved_end
            )
            raise DateValidationError(msg)

    return start, end, resolved_ranges