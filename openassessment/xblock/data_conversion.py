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
                if (isinstance(example, dict) and
                    (isinstance(example['answer'], unicode) or isinstance(example['answer'], str))):
                    example['answer'] = {
                        'parts': [
                            {'text': example['answer']}
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
    3. Add prompts to submission['answer']['parts'] to simplify iteration in the template.

    Args:
        submission (dict): Submission dictionary.
        prompts (list of dict): The prompts from the problem definition.

    Returns:
        dict
    """
    parts = [{ 'prompt': prompt, 'text': ''} for prompt in prompts]

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
