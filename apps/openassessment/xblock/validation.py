"""
Validate changes to an XBlock before it is updated.
"""
from collections import Counter
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


def _duplicates(items):
    """
    Given an iterable of items, return a set of duplicate items in the list.

    Args:
        items (list): The list of items, which may contain duplicates.

    Returns:
        set: The set of duplicate items in the list.

    """
    counts = Counter(items)
    return set(x for x in items if counts[x] > 1)


def validate_assessments(assessments):
    """
    Check that the assessment dict is semantically valid.

    Valid assessment steps are currently:
    * peer, then self
    * self only

    Args:
        assessments (list of dict): list of serialized assessment models.

    Returns:
        tuple (is_valid, msg) where
            is_valid is a boolean indicating whether the assessment is semantically valid
            and msg describes any validation errors found.
    """
    def _self_only(assessments):
        return len(assessments) == 1 and assessments[0].get('name') == 'self-assessment'

    def _peer_then_self(assessments):
        return (
            len(assessments) == 2 and
            assessments[0].get('name') == 'peer-assessment' and
            assessments[1].get('name') == 'self-assessment'
        )

    # Right now, there are two allowed scenarios: (peer -> self) and (self)
    if not (_self_only(assessments) or _peer_then_self(assessments)):
        return (
            False,
            _("The only supported assessment flows are (peer, self) or (self).")
        )

    if len(assessments) == 0:
        return (False, _("This problem must include at least one assessment."))

    for assessment_dict in assessments:
        # Supported assessment
        if not assessment_dict.get('name') in ['peer-assessment', 'self-assessment']:
            return (False, _('The "name" value must be "peer-assessment" or "self-assessment".'))

        # Number you need to grade is >= the number of people that need to grade you
        if assessment_dict.get('name') == 'peer-assessment':
            must_grade = assessment_dict.get('must_grade')
            must_be_graded_by = assessment_dict.get('must_be_graded_by')

            if must_grade is None or must_grade < 1:
                return (False, _('The "must_grade" value must be a positive integer.'))

            if must_be_graded_by is None or must_be_graded_by < 1:
                return (False, _('The "must_be_graded_by" value must be a positive integer.'))

            if must_grade < must_be_graded_by:
                return (False, _('The "must_grade" value must be greater than or equal to the "must_be_graded_by" value.'))

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
        return (False, u'This rubric definition is not valid.')

    # No duplicate criteria names
    duplicates = _duplicates([criterion['name'] for criterion in rubric_dict['criteria']])
    if len(duplicates) > 0:
        msg = u"Criteria duplicate name(s): {duplicates}".format(
            duplicates=", ".join(duplicates)
        )
        return (False, msg)

    # No duplicate option names within a criterion
    for criterion in rubric_dict['criteria']:
        duplicates = _duplicates([option['name'] for option in criterion['options']])
        if len(duplicates) > 0:
            msg = u"Options in '{criterion}' have duplicate name(s): {duplicates}".format(
                criterion=criterion['name'], duplicates=", ".join(duplicates)
            )
            return (False, msg)

    # After a problem is released, authors are allowed to change text,
    # but nothing that would change the point value of a rubric.
    if is_released:

        # Number of criteria must be the same
        if len(rubric_dict['criteria']) != len(current_rubric['criteria']):
            return (False, u'The number of criteria cannot be changed after a problem is released.')

        # Number of options for each criterion must be the same
        for new_criterion, old_criterion in _match_by_order(rubric_dict['criteria'], current_rubric['criteria']):
            if len(new_criterion['options']) != len(old_criterion['options']):
                return (False, u'The number of options cannot be changed after a problem is released.')

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
        success, msg = validate_assessments(assessments)
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
