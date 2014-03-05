"""
"""
from django.utils.translation import ugettext as _
from openassessment.assessment.serializers import rubric_from_dict, InvalidRubric
from openassessment.xblock.resolve_dates import resolve_dates, DateValidationError, InvalidDateFormat


def validate_assessments(assessments, enforce_peer_then_self=False):
    """
    Check that the assessment dict is semantically valid.

    Args:
        assessments (list of dict): list of serialized assessment models.

    Kwargs:
        enforce_peer_then_self (bool): If True, enforce the requirement that there
            must be exactly two assessments: first, a peer-assessment, then a self-assessment.

    Returns:
        tuple (is_valid, msg) where
            is_valid is a boolean indicating whether the assessment is semantically valid
            and msg describes any validation errors found.
    """
    if enforce_peer_then_self:
        if len(assessments) != 2:
            return (False, _("Problem must have exactly two assessments"))
        if assessments[0].get('name') != 'peer-assessment':
            return (False, _("The first assessment must be a peer-assessment"))
        if assessments[1].get('name') != 'self-assessment':
            return (False, _("The second assessment must be a self-assessment"))

    if len(assessments) == 0:
        return (False, _("Problem must include at least one assessment"))

    for assessment_dict in assessments:
        # Supported assessment
        if not assessment_dict.get('name') in ['peer-assessment', 'self-assessment']:
            return (False, _("Assessment type is not supported"))

        # Number you need to grade is >= the number of people that need to grade you
        if assessment_dict.get('name') == 'peer-assessment':
            must_grade = assessment_dict.get('must_grade')
            must_be_graded_by = assessment_dict.get('must_be_graded_by')

            if must_grade is None or must_grade < 1:
                return (False, _('"must_grade" must be a positive integer'))

            if must_be_graded_by is None or must_be_graded_by < 1:
                return (False, _('"must_be_graded_by" must be a positive integer'))

            if must_grade < must_be_graded_by:
                return (False, _('"must_grade" should be greater than or equal to "must_be_graded_by"'))

    return (True, u'')


def validate_rubric(rubric_dict):
    """
    Check that the rubric is semantically valid.

    Args:
        rubric_dict (dict): Serialized Rubric model

    Returns:
        tuple (is_valid, msg) where
            is_valid is a boolean indicating whether the assessment is semantically valid
            and msg describes any validation errors found.
    """
    try:
        rubric_from_dict(rubric_dict)
    except InvalidRubric:
        return (False, u'Rubric definition is not valid')
    else:
        return (True, u'')


def validate_dates(start, end, date_ranges):
    """
    Check that start and due dates are valid.

    Args:
        start (str): ISO-formatted date string indicating when the problem opens.
        end (str): ISO-formatted date string indicating when the problem closes.
        date_ranges (list of tuples): List of (start, end) pair for each submission / assessment.

    Returns:
        tuple (is_valid, msg) where
            is_valid is a boolean indicating whether the assessment is semantically valid
            and msg describes any validation errors found.
    """
    try:
        resolve_dates(start, end, date_ranges)
    except (DateValidationError, InvalidDateFormat) as ex:
        return (False, ex.message)
    else:
        return (True, u'')


def validator(start, due):
    """
    Return a validator function configured with the problem's start and end dates.
    This will validate assessments, rubrics, and dates.

    Args:
        start (str): ISO-formatted date string indicating when the problem opens.
        end (str): ISO-formatted date string indicating when the problem closes.

    Returns:
        callable, of a form that can be passed to `update_from_xml`.
    """
    def _inner(rubric_dict, submission_dict, assessments):
        success, msg = validate_assessments(assessments, enforce_peer_then_self=True)
        if not success:
            return (False, msg)

        success, msg = validate_rubric(rubric_dict)
        if not success:
            return (False, msg)

        submission_dates = [(start, submission_dict['due'])]
        assessment_dates = [(asmnt['start'], asmnt['due']) for asmnt in assessments]
        success, msg = validate_dates(start, due, submission_dates + assessment_dates)
        if not success:
            return (False, msg)

        return (True, u'')

    return _inner