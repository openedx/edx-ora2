"""
Data Conversion utility methods for handling ORA2 XBlock data transformations.

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
        >>>         "answer": "This is my response",
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
                'answer': 'This is my response',
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
        "prompts" : prompts,
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
        if criterion['name'] in criterion_feedback
        and criterion.get('feedback', 'disabled') in ['optional', 'required']
    }


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
