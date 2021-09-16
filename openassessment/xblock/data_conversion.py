"""
Data Conversion utility methods for handling ORA2 XBlock data transformations and validation.

"""
import json


def convert_training_examples_list_to_dict(examples_list):
    """
    Convert of options selected we store in the problem def,
    which is ordered, to the unordered dictionary of options
    selected that the student training API expects.

    Args:
        examples_list (list): A list of options selected against a rubric.

    Returns:
        A dictionary of the given examples in the list.

    Example:
        >>> examples = [
        >>>     {
        >>>         "answer": {
        >>>             "parts": {
        >>>                 [
        >>>                     {"text:" "Answer part 1"},
        >>>                     {"text:" "Answer part 2"},
        >>>                     {"text:" "Answer part 3"}
        >>>                 ]
        >>>             }
        >>>         },
        >>>         "options_selected": [
        >>>             {
        >>>                 "criterion": "Ideas",
        >>>                 "option": "Fair"
        >>>             },
        >>>             {
        >>>                 "criterion": "Content",
        >>>                 "option": "Good"
        >>>             }
        >>>         ]
        >>>     }
        >>> ]
        >>> convert_training_examples_list_to_dict(examples)
        [
            {
                'answer': {
                    'parts': {
                        [
                            {'text:' 'Answer part 1'},
                            {'text:' 'Answer part 2'},
                            {'text:' 'Answer part 3'}
                        ]
                    }
                 },
                'options_selected': {
                    'Ideas': 'Fair',
                    'Content': 'Good'
                }
            }
        ]

    """
    return [
        {
            'answer': ex['answer'],
            'options_selected': {
                select_dict['criterion']: select_dict['option']
                for select_dict in ex['options_selected']
            }
        }
        for ex in examples_list
    ]


def list_to_conversational_format(str_list):
    """
    String list render method, displaying a list of string values in conversational language.
    ['a'] => 'a';  ['a', 'b'] => 'a and b';  ['a', 'b', 'c'] => 'a, b, and c'

    Args:
        str_list (str[]): List of strings to return in comma-joined/conversational form.

    Returns:
        Combined string.
    """
    if str_list is None:
        return ''
    if len(str_list) < 3:
        return ' and '.join(str_list)
    return '{}, and {}'.format(', '.join(str_list[:-1]), str_list[-1])


def update_assessments_format(assessments):
    """
    For each example update 'answer' to newer format.

    Args:
        assessments (list): list of assessments
    Returns:
        list of dict
    """
    for assessment in assessments:
        if 'examples' in assessment and assessment['examples']:
            for example in assessment['examples']:
                if isinstance(example, dict) and isinstance(example['answer'], str):
                    example['answer'] = {
                        'parts': [
                            {'text': example['answer']}
                        ]
                    }
                if isinstance(example, dict) and isinstance(example['answer'], list) and example['answer']:
                    example['answer'] = {
                        'parts': [
                            {'text': example_answer} for example_answer in example['answer']
                        ]
                    }
    return assessments


def create_prompts_list(prompt_or_serialized_prompts):
    """
    Construct a list of prompts.

    Initially a block had a single prompt which was saved as a simple string.
    In that case a new prompt dict is constructed from it.

    Args:
        prompt_or_serialized_prompts (unicode): A string which can either
        be a single prompt text or json for a list of prompts.

    Returns:
        list of dict
    """

    if prompt_or_serialized_prompts is None:
        prompt_or_serialized_prompts = ''

    try:
        prompts = json.loads(prompt_or_serialized_prompts)
    except ValueError:
        prompts = [
            {
                'description': prompt_or_serialized_prompts,
            }
        ]
    return prompts


def create_rubric_dict(prompts, criteria):
    """
    Construct a serialized rubric model in the format expected
    by the assessments app.

    Args:
        prompts (list of dict): The rubric prompts.
        criteria (list of dict): The serialized rubric criteria.

    Returns:
        dict

    """
    return {
        "prompts": prompts,
        "criteria": criteria
    }


def clean_criterion_feedback(rubric_criteria, criterion_feedback):
    """
    Remove per-criterion feedback for criteria with feedback disabled
    in the rubric.

    Args:
        rubric_criteria (list): The rubric criteria from the problem definition.
        criterion_feedback (dict): Mapping of criterion names to feedback text.

    Returns:
        dict

    """
    return {
        criterion['name']: criterion_feedback[criterion['name']]
        for criterion in rubric_criteria
        if criterion['name'] in criterion_feedback and criterion.get(
            'feedback', 'disabled'
        ) in ['optional', 'required']
    }


def prepare_submission_for_serialization(submission_data):
    """
    Convert a list of answers into the right format dict for serialization.

    Args:
        submission_data (list of unicode): The answers.

    Returns:
        dict
    """
    return {
        'parts': [{'text': text} for text in submission_data],
    }


def create_submission_dict(submission, prompts):
    """
    1. Convert from legacy format.
    2. Add prompts to submission['answer']['parts'] to simplify iteration in the template.

    Args:
        submission (dict): Submission dictionary.
        prompts (list of dict): The prompts from the problem definition.

    Returns:
        dict
    """
    parts = [{'prompt': prompt, 'text': ''} for prompt in prompts]

    if 'text' in submission['answer']:
        parts[0]['text'] = submission['answer'].pop('text')
    else:
        for index, part in enumerate(submission['answer'].pop('parts')):
            parts[index]['text'] = part['text']

    submission['answer']['parts'] = parts

    return submission


def make_django_template_key(key):
    """
    Django templates access dictionary items using dot notation,
    which means that dictionary keys with hyphens don't work.
    This function sanitizes a key for use in Django templates
    by replacing hyphens with underscores.

    Args:
        key (basestring): The key to sanitize.

    Returns:
        basestring
    """
    return key.replace('-', '_')


def _verify_assessment_data(_, data):
    if not isinstance(data, dict):
        return _('Assessment data must be a dictionary/object')

    if 'options_selected' not in data:
        return _('You must provide options selected in the assessment.')

    if 'overall_feedback' not in data:
        return _('You must provide overall feedback in the assessment.')

    if 'criterion_feedback' not in data:
        return _('You must provide feedback for criteria in the assessment.')

    return None


def verify_assessment_parameters(func):
    """
    Verify that the wrapped function receives the required parameters.

    Used for the staff_assess, self_assess, peer_assess functions and uses their data types.

    Args:
        func - the function to be modified

    Returns:
        the modified function
    """
    def verify_and_call(instance, data, suffix):
        """ Inner Method. """
        # Validate the request
        msg = _verify_assessment_data(instance._, data)
        if msg:
            return {'success': False, 'msg': msg}

        return func(instance, data, suffix)
    return verify_and_call


def verify_multiple_assessment_parameters(func):
    """
    Verify that the wrapped function receives the required parameters.

    Used for bulk_staff_assess.

    Args:
        func - the function to be modified

    Returns:
        the modified function
    """
    def verify_and_call(instance, data, suffix):
        """ Inner Method. """
        if not isinstance(data, list):
            return {'success': False, 'msg': instance._('This view takes only a list as a parameter')}
        errors = {}
        for assessment_index, assessment in enumerate(data):
            msg = _verify_assessment_data(instance._, assessment)
            if msg:
                errors[assessment_index] = msg

        if errors:
            return {
                'success': False,
                'msg': 'One or more of the submitted assessments is missing required fields',
                'errors': errors,
            }

        return func(instance, data, suffix)
    return verify_and_call
