"""
Data Conversion utility methods for handling ORA2 XBlock data transformations.

"""


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


def create_rubric_dict(prompt, criteria):
    """
    Construct a serialized rubric model in the format expected
    by the assessments app.

    Args:
        prompt (unicode): The rubric prompt.
        criteria (list of dict): The serialized rubric criteria.

    Returns:
        dict

    """
    return {
        "prompt": prompt,
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
