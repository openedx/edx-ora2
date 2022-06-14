"""
Validate changes to an XBlock before it is updated.
"""

from collections import Counter

from openassessment.assessment.api.student_training import validate_training_examples
from openassessment.assessment.serializers import InvalidRubric, rubric_from_dict
from openassessment.xblock.data_conversion import convert_training_examples_list_to_dict
from openassessment.xblock.resolve_dates import DateValidationError, InvalidDateFormat, resolve_dates


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
    def key_func(x):
        return x['order_num']
    return list(zip(sorted(items, key=key_func), sorted(others, key=key_func)))


def _duplicates(items):
    """
    Given an iterable of items, return a set of duplicate items in the list.

    Args:
        items (list): The list of items, which may contain duplicates.

    Returns:
        set: The set of duplicate items in the list.

    """
    counts = Counter(items)
    return {x for x in items if counts[x] > 1}


def _is_valid_assessment_sequence(assessments):
    """
    Check whether the sequence of assessments is valid. The rules enforced are:
        -must have one of staff-, peer-, or self- listed
        -in addition to those, only student-training is a valid entry
        -no duplicate entries
        -if staff-assessment is present, it must come last
        -if student-training is present, it must be followed at some point by peer-assessment

    Args:
        assessments (list of dict): List of assessment dictionaries.

    Returns:
        bool

    """
    sequence = [asmnt.get('name') for asmnt in assessments]
    required = ['staff-assessment', 'peer-assessment', 'self-assessment']
    optional = ['student-training']

    # at least one of required?
    if not any(name in required for name in sequence):
        return False

    # nothing except what appears in required or optional
    if any(name not in required + optional for name in sequence):
        return False

    # no duplicates
    if any(sequence.count(name) > 1 for name in sequence):
        return False

    # if using staff-assessment, it must come last
    if 'staff-assessment' in sequence and sequence[-1] != 'staff-assessment':
        return False

    # if using training, must be followed by peer at some point
    if 'student-training' in sequence:
        train_index = sequence.index('student-training')
        if 'peer-assessment' not in sequence[train_index:]:
            return False

    return True


def validate_assessments(assessments, current_assessments, is_released, _):
    """
    Check that the assessment dict is semantically valid. See _is_valid_assessment_sequence()
    above for a description of valid assessment sequences. In addition, enforces validation
    of several assessment-specific settings.

    If a question has been released, the type and number of assessment steps
    cannot be changed.

    Args:
        assessments (list of dict): list of serialized assessment models.
        current_assessments (list of dict): list of the current serialized
            assessment models. Used to determine if the assessment configuration
            has changed since the question had been released.
        is_released (boolean) : True if the question has been released.
        _ (function): The service function used to get the appropriate i18n text

    Returns:
        tuple (is_valid, msg) where
            is_valid is a boolean indicating whether the assessment is semantically valid
            and msg describes any validation errors found.
    """
    if not assessments:
        return False, _("This problem must include at least one assessment.")

    # Ensure that we support this sequence of assessments.
    if not _is_valid_assessment_sequence(assessments):
        msg = _("The assessment order you selected is invalid.")
        return False, msg

    for assessment_dict in assessments:
        # Number you need to grade is >= the number of people that need to grade you
        if assessment_dict.get('name') == 'peer-assessment':
            must_grade = assessment_dict.get('must_grade')
            must_be_graded_by = assessment_dict.get('must_be_graded_by')

            if must_grade is None or must_grade < 1:
                return False, _('In peer assessment, the "Must Grade" value must be a positive integer.')

            if must_be_graded_by is None or must_be_graded_by < 1:
                return False, _('In peer assessment, the "Graded By" value must be a positive integer.')

            if must_grade < must_be_graded_by:
                return False, _(
                    'In peer assessment, the "Must Grade" value must be greater than or equal to the "Graded By" value.'
                )

        # Student Training must have at least one example, and all
        # examples must have unique answers.
        if assessment_dict.get('name') == 'student-training':
            answers = []
            examples = assessment_dict.get('examples')
            if not examples:
                return False, _('You must provide at least one example response for learner training.')
            for example in examples:
                if example.get('answer') in answers:
                    return False, _('Each example response for learner training must be unique.')
                answers.append(example.get('answer'))

        # Staff grading must be required if it is the only step
        if assessment_dict.get('name') == 'staff-assessment' and len(assessments) == 1:
            required = assessment_dict.get('required')
            if not required:  # Captures both None and explicit False cases, both are invalid
                return False, _('The "required" value must be true if staff assessment is the only step.')

    if is_released:
        if len(assessments) != len(current_assessments):
            return False, _("The number of assessments cannot be changed after the problem has been released.")

        names = [assessment.get('name') for assessment in assessments]
        current_names = [assessment.get('name') for assessment in current_assessments]
        if names != current_names:
            return False, _("The assessment type cannot be changed after the problem has been released.")

    return True, ''


def validate_rubric(rubric_dict, current_rubric, is_released, _):
    """
    Check that the rubric is semantically valid.

    Args:
        rubric_dict (dict): Serialized Rubric model representing the updated state of the rubric.
        current_rubric (dict): Serialized Rubric model representing the current state of the rubric.
        is_released (bool): True if and only if the problem has been released.
        _ (function): The service function used to get the appropriate i18n text

    Returns:
        tuple (is_valid, msg) where
            is_valid is a boolean indicating whether the assessment is semantically valid
            and msg describes any validation errors found.
    """
    try:
        rubric_from_dict(rubric_dict)
    except InvalidRubric:
        return False, _('This rubric definition is not valid.')

    for criterion in rubric_dict['criteria']:
        # No duplicate option names within a criterion
        duplicates = _duplicates([option['name'] for option in criterion['options']])
        if duplicates:
            msg = _("Options in '{criterion}' have duplicate name(s): {duplicates}").format(
                criterion=criterion['name'], duplicates=", ".join(duplicates)
            )
            return False, msg

        # Some criteria may have no options, just written feedback.
        # In this case, written feedback must be required (not optional or disabled).
        if not criterion['options'] and criterion.get('feedback', 'disabled') != 'required':
            msg = _('Criteria with no options must require written feedback.')
            return False, msg

    # After a problem is released, authors are allowed to change text,
    # but nothing that would change the point value of a rubric.
    if is_released:

        # Number of prompts must be the same
        if len(rubric_dict['prompts']) != len(current_rubric['prompts']):
            return False, _('Prompts cannot be created or deleted after a problem is released.')

        # Number of criteria must be the same
        if len(rubric_dict['criteria']) != len(current_rubric['criteria']):
            return False, _('The number of criteria cannot be changed after a problem is released.')

        # Criteria names must be the same
        # We use criteria names as unique identifiers (unfortunately)
        # throughout the system.  Changing them mid-flight can cause
        # the grade page, for example, to raise 500 errors.
        # When we implement non-XML authoring, we might be able to fix this
        # the right way by assigning unique identifiers for criteria;
        # but for now, this is the safest way to avoid breaking problems
        # post-release.
        current_criterion_names = {criterion.get('name') for criterion in current_rubric['criteria']}
        new_criterion_names = {criterion.get('name') for criterion in rubric_dict['criteria']}
        if current_criterion_names != new_criterion_names:
            return False, _('Criteria names cannot be changed after a problem is released')

        # Number of options for each criterion must be the same
        for new_criterion, old_criterion in _match_by_order(rubric_dict['criteria'], current_rubric['criteria']):
            if len(new_criterion['options']) != len(old_criterion['options']):
                return False, _('The number of options cannot be changed after a problem is released.')

            else:
                for new_option, old_option in _match_by_order(new_criterion['options'], old_criterion['options']):
                    if new_option['points'] != old_option['points']:
                        return False, _('Point values cannot be changed after a problem is released.')

    return True, ''


def validate_dates(start, end, date_ranges, _):
    """
    Check that start and due dates are valid.

    Args:
        start (str): ISO-formatted date string indicating when the problem opens.
        end (str): ISO-formatted date string indicating when the problem closes.
        date_ranges (list of tuples): List of (start, end) pair for each submission / assessment.
        _ (function): The service function used to get the appropriate i18n text

    Returns:
        tuple (is_valid, msg) where
            is_valid is a boolean indicating whether the assessment is semantically valid
            and msg describes any validation errors found.
    """
    try:
        resolve_dates(start, end, date_ranges, _)
    except (DateValidationError, InvalidDateFormat) as ex:
        return False, str(ex)
    else:
        return True, ''


def validate_assessment_examples(rubric_dict, assessments, _):
    """
    Validate assessment training examples.

    Args:
        rubric_dict (dict): The serialized rubric model.
        assessments (list of dict): List of assessment dictionaries.
        _ (function): The service function used to get the appropriate i18n text

    Returns:
        tuple (is_valid, msg) where
            is_valid is a boolean indicating whether the assessment is semantically valid
            and msg describes any validation errors found.

    """
    for asmnt in assessments:
        if asmnt['name'] == 'student-training':

            examples = convert_training_examples_list_to_dict(asmnt['examples'])

            # Must have at least one training example
            if not examples:
                return False, _(
                    "Learner training must have at least one training example."
                )

            # Delegate to the student training API to validate the
            # examples against the rubric.
            errors = validate_training_examples(rubric_dict, examples)
            if errors:
                return False, "; ".join(errors)

    return True, ''


def validator(oa_block, _, strict_post_release=True):
    """
    Return a validator function configured for the XBlock.
    This will validate assessments, rubrics, and dates.

    Args:
        oa_block (OpenAssessmentBlock): The XBlock being updated.
        _ (function): The service function used to get the appropriate i18n text

    Keyword Arguments:
        strict_post_release (bool): If true, restrict what authors can update once
            a problem has been released.

    Returns:
        callable, of a form that can be passed to `update_from_xml`.
    """
    # Import is placed here to avoid model import at project startup.
    from submissions.api import MAX_TOP_SUBMISSIONS

    def _inner(rubric_dict, assessments, leaderboard_show=0, submission_start=None, submission_due=None):
        """ Validator method. """

        is_released = strict_post_release and oa_block.is_released()

        # Assessments
        current_assessments = oa_block.rubric_assessments
        success, msg = validate_assessments(assessments, current_assessments, is_released, _)
        if not success:
            return False, msg

        # Rubric
        current_rubric = {
            'prompts': oa_block.prompts,
            'criteria': oa_block.rubric_criteria
        }
        success, msg = validate_rubric(rubric_dict, current_rubric, is_released, _)
        if not success:
            return False, msg

        # Training examples
        success, msg = validate_assessment_examples(rubric_dict, assessments, _)
        if not success:
            return False, msg

        # Dates
        submission_dates = [(submission_start, submission_due)]
        assessment_dates = [(asmnt.get('start'), asmnt.get('due')) for asmnt in assessments]
        success, msg = validate_dates(oa_block.start, oa_block.due, submission_dates + assessment_dates, _)
        if not success:
            return False, msg

        # Leaderboard
        if leaderboard_show < 0 or leaderboard_show > MAX_TOP_SUBMISSIONS:
            return False, _("Leaderboard number is invalid.")

        # Success!
        return True, ''

    return _inner


def validate_submission(submission, prompts, _, text_response='required'):
    """
    Validate submission dict.

    Args:
        submission (list of unicode): Responses for the prompts.
        prompts (list of dict): The prompts from the problem definition.
        _ (function): The service function used to get the appropriate i18n text.

    Returns:
        tuple (is_valid, msg) where
            is_valid is a boolean indicating whether the submission is semantically valid
            and msg describes any validation errors found.
    """

    message = _("The submission format is invalid.")

    if not isinstance(submission, list):
        return False, message

    if text_response == 'required' and len(submission) != len(prompts):
        return False, message

    for submission_part in submission:
        if not isinstance(submission_part, str):
            return False, message

    return True, ''
