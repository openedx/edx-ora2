"""
Schema for validating and sanitizing data received from the JavaScript client.
"""

from __future__ import absolute_import

import dateutil
from pytz import utc
import six

from voluptuous import (
    All,
    Any,
    In,
    Invalid,
    Optional,
    Range,
    Required,
    Schema,
)


def utf8_validator(value):
    """Validate and sanitize unicode strings.
    If we're given a bytestring, assume that the encoding is UTF-8

    Args:
        value: The value to validate

    Returns:
        unicode

    Raises:
        Invalid

    """
    try:
        if isinstance(value, bytes):
            return value.decode('utf-8')
        return six.text_type(value)
    except (ValueError, TypeError):
        raise Invalid(u"Could not load unicode from value \"{val}\"".format(val=value))


def datetime_validator(value):
    """Validate and sanitize a datetime string in ISO format.

    Args:
        value: The value to validate

    Returns:
        unicode: ISO-formatted datetime string

    Raises:
        Invalid

    """
    try:
        # The dateutil parser defaults empty values to the current day,
        # which is NOT what we want.
        if value is None or value == '':
            raise Invalid(u"Datetime value cannot be \"{val}\"".format(val=value))

        # Parse the date and interpret it as UTC
        value = dateutil.parser.parse(value).replace(tzinfo=utc)
        return six.text_type(value.isoformat())
    except (ValueError, TypeError):
        raise Invalid(u"Could not parse datetime from value \"{val}\"".format(val=value))


PROMPTS_TYPES = [
    u'text',
    u'html',
]


NECESSITY_OPTIONS = [
    u'required',
    u'optional',
    u''
]


VALID_ASSESSMENT_TYPES = [
    u'peer-assessment',
    u'self-assessment',
    u'student-training',
    u'staff-assessment',
]

VALID_UPLOAD_FILE_TYPES = [
    u'image',
    u'pdf-and-image',
    u'custom'
]

# Schema definition for an update from the Studio JavaScript editor.
EDITOR_UPDATE_SCHEMA = Schema({
    Required('prompts'): [
        Schema({
            Required('description'): utf8_validator,
        })
    ],
    Required('prompts_type', default='text'): Any(All(utf8_validator, In(PROMPTS_TYPES)), None),
    Required('title'): utf8_validator,
    Required('feedback_prompt'): utf8_validator,
    Required('feedback_default_text'): utf8_validator,
    Required('submission_start'): Any(datetime_validator, None),
    Required('submission_due'): Any(datetime_validator, None),
    Required('text_response', default='required'): Any(All(utf8_validator, In(NECESSITY_OPTIONS)), None),
    Required('file_upload_response', default=None): Any(All(utf8_validator, In(NECESSITY_OPTIONS)), None),
    'allow_file_upload': bool,  # Backwards compatibility.
    Required('file_upload_type', default=None): Any(All(utf8_validator, In(VALID_UPLOAD_FILE_TYPES)), None),
    'white_listed_file_types': utf8_validator,
    Required('allow_latex'): bool,
    Required('leaderboard_show'): int,
    Optional('teams_enabled'): bool,
    Optional('selected_teamset_id'): utf8_validator,
    Required('assessments'): [
        Schema({
            Required('name'): All(utf8_validator, In(VALID_ASSESSMENT_TYPES)),
            Required('start', default=None): Any(datetime_validator, None),
            Required('due', default=None): Any(datetime_validator, None),
            'required': bool,
            'must_grade': All(int, Range(min=0)),
            'must_be_graded_by': All(int, Range(min=0)),
            'examples': [
                Schema({
                    Required('answer'): [utf8_validator],
                    Required('options_selected'): [
                        Schema({
                            Required('criterion'): utf8_validator,
                            Required('option'): utf8_validator
                        })
                    ]
                })
            ],
            'examples_xml': utf8_validator,
        })
    ],
    Required('editor_assessments_order'): [
        All(utf8_validator, In(VALID_ASSESSMENT_TYPES))
    ],
    Required('feedbackprompt', default=u""): utf8_validator,
    Required('criteria'): [
        Schema({
            Required('order_num'): All(int, Range(min=0)),
            Required('name'): utf8_validator,
            Required('label'): utf8_validator,
            Required('prompt'): utf8_validator,
            Required('feedback'): All(
                utf8_validator,
                In([
                    'disabled',
                    'optional',
                    'required',
                ])
            ),
            Required('options'): [
                Schema({
                    Required('order_num'): All(int, Range(min=0)),
                    Required('name'): utf8_validator,
                    Required('label'): utf8_validator,
                    Required('explanation'): utf8_validator,
                    Required('points'): All(int, Range(min=0)),
                })
            ]
        })
    ]
})
