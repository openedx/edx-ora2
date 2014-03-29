"""
Validate changes to an XBlock before it is updated.
"""
from django.utils.translation import ugettext as _
from openassessment.assessment.serializers import rubric_from_dict, InvalidRubric
from openassessment.xblock.resolve_dates import resolve_dates, DateValidationError, InvalidDateFormat


def _match_by_order(items, others):
    """
    Given two lists of dictionaries, each containing "order_num" keys,
    return a set of tuples, where the items in the tuple are dictionaries
    with the same "order_num" keys.

    Args:
        items (list of dict): Items to match, each of which must contain a "order_num" key.
        others (list of dict): Items to match, each of which must contain a "order_num" key.

    Returns:
        list of tuples, each containing two dictionaries

    Raises:
        IndexError: A dictionary does no contain a 'order_num' key.
    """
    # Sort each dictionary by its "name" key, then zip them and return
    key_func = lambda x: x['order_num']
    return zip(sorted(items, key=key_func), sorted(others, key=key_func))


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


def validate_rubric(rubric_dict, current_rubric, is_released):
    """
    Check that the rubric is semantically valid.

    Args:
        rubric_dict (dict): Serialized Rubric model representing the updated state of the rubric.
        current_rubric (dict): Serialized Rubric model representing the current state of the rubric.
        is_released (bool): True if and only if the problem has been released.

    Returns:
        tuple (is_valid, msg) where
            is_valid is a boolean indicating whether the assessment is semantically valid
            and msg describes any validation errors found.
    """
    try:
        rubric_from_dict(rubric_dict)
    except InvalidRubric:
        return (False, u'Rubric definition is not valid')

    # After a problem is released, authors are allowed to change text,
    # but nothing that would change the point value of a rubric.
    if is_released:

        # Number of criteria must be the same
        if len(rubric_dict['criteria']) != len(current_rubric['criteria']):
            return (False, u'Number of criteria cannot be changed after a problem is released.')

        # Number of options for each criterion must be the same
        for new_criterion, old_criterion in _match_by_order(rubric_dict['criteria'], current_rubric['criteria']):
            if len(new_criterion['options']) != len(old_criterion['options']):
                return (False, u'Number of options cannot be changed after a problem is released.')

            else:
                for new_option, old_option in _match_by_order(new_criterion['options'], old_criterion['options']):
                    if new_option['points'] != old_option['points']:
                        return (False, u'Point values cannot be changed after a problem is released.')

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


def validator(oa_block, strict_post_release=True):
    """
    Return a validator function configured for the XBlock.
    This will validate assessments, rubrics, and dates.

    Args:
        oa_block (OpenAssessmentBlock): The XBlock being updated.

    Kwargs:
        strict_post_release (bool): If true, restrict what authors can update once
            a problem has been released.

    Returns:
        callable, of a form that can be passed to `update_from_xml`.
    """

    def _inner(rubric_dict, submission_dict, assessments):
        success, msg = validate_assessments(assessments, enforce_peer_then_self=True)
        if not success:
            return (False, msg)

        current_rubric = {
            'prompt': oa_block.prompt,
            'criteria': oa_block.rubric_criteria
        }
        success, msg = validate_rubric(
            rubric_dict, current_rubric,
            strict_post_release and oa_block.is_released()
        )
        if not success:
            return (False, msg)

        submission_dates = [(oa_block.start, submission_dict['due'])]
        assessment_dates = [(asmnt['start'], asmnt['due']) for asmnt in assessments]
        success, msg = validate_dates(oa_block.start, oa_block.due, submission_dates + assessment_dates)
        if not success:
            return (False, msg)

        return (True, u'')

    return _inner