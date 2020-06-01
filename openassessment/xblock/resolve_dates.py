"""
Resolve unspecified dates and date strings to datetimes.
"""


import datetime as dt

from dateutil.parser import parse as parse_date
import pytz


class InvalidDateFormat(Exception):
    """
    The date string could not be parsed.
    """


class DateValidationError(Exception):
    """
    Dates are not semantically valid.
    """


DISTANT_PAST = dt.datetime(dt.MINYEAR, 1, 1, tzinfo=pytz.utc)
DISTANT_FUTURE = dt.datetime(dt.MAXYEAR, 1, 1, tzinfo=pytz.utc)


def _parse_date(value, _):
    """
    Parse an ISO formatted datestring into a datetime object with timezone set to UTC.

    Args:
        value (str or datetime): The ISO formatted date string or datetime object.
        _ (function): The i18n service function used to get the appropriate
            text for a message.

    Returns:
        datetime.datetime

    Raises:
        InvalidDateFormat: The date string could not be parsed.
    """
    if isinstance(value, dt.datetime):
        return value.replace(tzinfo=pytz.utc)

    elif isinstance(value, str):
        try:
            return parse_date(value).replace(tzinfo=pytz.utc)
        except ValueError:
            raise InvalidDateFormat(
                _(
                    u"'{date}' is an invalid date format. Make sure the date is formatted as YYYY-MM-DDTHH:MM:SS."
                ).format(date=value)
            )

    else:
        raise InvalidDateFormat(_(u"'{date}' must be a date string or datetime").format(date=value))


def parse_date_value(date, _):
    """ Public method for _parse_date """
    return _parse_date(date, _)


def resolve_dates(start, end, date_ranges, _):
    """
    Resolve date strings (including "default" dates) to datetimes.
    The basic rules are:

        1) Unset problem start dates default to the distant past.
        2) Unset problem end dates default to the distant future.
        3) Unset start dates default to the start date of the previous assessment/submission.
            (The first submission defaults to the problem start date.)
        4) Unset end dates default to the end date of the following assessment/submission.
            (The last assessment defaults to the problem end date.)
        5) `start` resolves to the earliest start date.
        6) `end` resolves to the latest end date.
        7) Ensure that `start` is before `end`.
        8) Ensure that `start` is before the earliest due date.
        9) Ensure that `end` is after the latest start date.

    Overriding start/end dates:

        * Rules 5-9 may seem strange, but they're necessary.  Unlike `date_ranges`,
          the `start` and `end` values are inherited by the XBlock from the LMS.
          This means that you can set `start` and `end` in Studio, effectively bypassing
          our validation rules.

        * On the other hand, we *need* the start/due dates so we can resolve unspecified
          date ranges to an actual date.  For example,
          if the problem closes on April 15th, 2014, but the course author hasn't specified
          a due date for a submission, we need ensure the submission closes on April 15th.

        * For this reason, we use `start` and `end` only if they satisfy our validation
          rules.  If not (because a course author has changed them to something invalid in Studio),
          we use the dates that the course author specified in the problem definition,
          which (a) MUST satisfy our ordering constraints, and (b) are probably
          what the author intended.

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
        start (str, ISO date format, or datetime): When the problem opens.
            A value of None indicates that the problem is always open.
        end (str, ISO date format, or datetime): When the problem closes.
            A value of None indicates that the problem never closes.
        date_ranges (list of tuples): list of (start, end) ISO date string tuples indicating
            the start/end timestamps (date string or datetime) of each submission/assessment.
        _ (function): An i18n service function to use for retrieving the
            proper text.

    Returns:
        start (datetime): The resolved start date
        end (datetime): The resolved end date.
        list of (start, end) tuples, where both elements are datetime objects.

    Raises:
        DateValidationError
        InvalidDateFormat
    """
    # Resolve problem start and end dates to minimum and maximum dates
    start = _parse_date(start, _) if start is not None else DISTANT_PAST
    end = _parse_date(end, _) if end is not None else DISTANT_FUTURE
    resolved_starts = []
    resolved_ends = []

    # Amazingly, Studio allows the release date to be after the due date!
    # This can cause a problem if the course author has configured:
    #
    # 1) Problem start >= problem due, and
    # 2) Start/due dates that resolve to the problem start/due date.
    #
    # In this case, all submission/assessment start dates
    # could default to the problem start while
    # due dates default to the problem due date, violating
    # the constraint that start dates always precede due dates.
    # If we detect that the author has done this,
    # we set the start date to just before
    # the due date, so we (just barely) satify the validation rules.
    if start >= end:
        start = end - dt.timedelta(milliseconds=1)

    # Override start/end dates if they fail to satisfy our validation rules
    # These are the only parameters a course author can change in Studio
    # without triggering our validation rules, so we need to use sensible
    # defaults.  See the docstring above for a more detailed justification.
    for step_start, step_end in date_ranges:
        if step_start is not None:
            parsed_start = _parse_date(step_start, _)
            start = min(start, parsed_start)
            end = max(end, parsed_start + dt.timedelta(milliseconds=1))
        if step_end is not None:
            parsed_end = _parse_date(step_end, _)
            end = max(end, parsed_end)
            start = min(start, parsed_end - dt.timedelta(milliseconds=1))

    # Iterate through the list forwards and backwards simultaneously
    # As we iterate forwards, resolve start dates.
    # As we iterate backwards, resolve end dates.
    prev_start = start
    prev_end = end
    for index in range(len(date_ranges)):  # pylint: disable=consider-using-enumerate
        reverse_index = len(date_ranges) - index - 1

        # Resolve "default" start dates to the previous start date.
        # If I set a start date for peer-assessment, but don't set a start date for the following self-assessment,
        # then the self-assessment should default to the same start date as the peer-assessment.
        step_start, __ = date_ranges[index]
        step_start = _parse_date(step_start, _) if step_start is not None else prev_start

        # Resolve "default" end dates to the following end date.
        # If I set a due date for self-assessment, but don't set a due date for the previous peer-assessment,
        # then the peer-assessment should default to the same due date as the self-assessment.
        __, step_end = date_ranges[reverse_index]
        step_end = _parse_date(step_end, _) if step_end is not None else prev_end

        if step_start < prev_start:
            msg = _(
                u"This step's start date '{start}' cannot be earlier than the previous step's start date '{prev}'."
            ).format(
                start=step_start,
                prev=prev_start,
            )
            raise DateValidationError(msg)

        if step_end > prev_end:
            msg = _(u"This step's due date '{due}' cannot be later than the next step's due date '{prev}'.").format(
                due=step_end, prev=prev_end
            )
            raise DateValidationError(msg)

        resolved_starts.append(step_start)
        resolved_ends.insert(0, step_end)
        prev_start = step_start
        prev_end = step_end

    # Combine the resolved dates back into a list of tuples
    resolved_ranges = list(zip(resolved_starts, resolved_ends))

    # Now that we have resolved both start and end dates, we can safely compare them
    for resolved_start, resolved_end in resolved_ranges:
        if resolved_start >= resolved_end:
            msg = _(u"The start date '{start}' cannot be later than the due date '{due}'").format(
                start=resolved_start, due=resolved_end
            )
            raise DateValidationError(msg)

    return start, end, resolved_ranges
