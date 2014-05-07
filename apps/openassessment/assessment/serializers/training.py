"""
Serializers for the training assessment type.
"""
import json
from django.db import transaction, IntegrityError
from openassessment.assessment.models import TrainingExample
from .base import rubric_from_dict, RubricSerializer


class InvalidTrainingExample(Exception):
    """
    The training example could not be deserialized.
    """
    pass


def validate_training_example_format(example):
    """
    Check whether the serialized training example dict
    has the correct structure.

    Args:
        example (dict): The serialized training example.

    Returns:
        tuple of (is_valid, errors), where `is_valid` is a bool
        and `errors` is a list of error messages.

    """
    errors = []

    if not isinstance(example, dict):
        errors.append(u"Training example must be a dictionary")

    if 'answer' not in example:
        errors.append(u'Training example must contain an "answer" field.')

    if 'options_selected' not in example:
        errors.append(u'Training example must contain an "options_selected" field.')

    is_valid = (len(errors) == 0)
    return is_valid, errors


def serialize_training_example(example):
    """
    Serialize a training example to a dictionary.

    Args:
        example (TrainingExample): The training example to serialize.

    Returns:
        dict

    """
    return {
        'answer': example.answer,
        'options_selected': example.options_selected_dict,
        'rubric': RubricSerializer.serialized_from_cache(example.rubric),
    }


@transaction.commit_on_success
def deserialize_training_examples(examples, rubric_dict):
    """
    Deserialize training examples to Django models.

    Args:
        examples (list of dict): The serialized training examples.
        rubric_dict (dict): The serialized rubric.

    Returns:
        list of TrainingExamples

    Raises:
        InvalidRubric
        InvalidTrainingExample

    Example usage:

        >>> options = [
        >>>     {
        >>>         "order_num": 0,
        >>>         "name": "poor",
        >>>         "explanation": "Poor job!",
        >>>         "points": 0,
        >>>     },
        >>>     {
        >>>         "order_num": 1,
        >>>         "name": "good",
        >>>         "explanation": "Good job!",
        >>>         "points": 1,
        >>>     },
        >>>     {
        >>>         "order_num": 2,
        >>>         "name": "excellent",
        >>>         "explanation": "Excellent job!",
        >>>         "points": 2,
        >>>     },
        >>> ]
        >>>
        >>> rubric = {
        >>>     "prompt": "Write an essay!",
        >>>     "criteria": [
        >>>         {
        >>>             "order_num": 0,
        >>>             "name": "vocabulary",
        >>>             "prompt": "How varied is the vocabulary?",
        >>>             "options": options
        >>>         },
        >>>         {
        >>>             "order_num": 1,
        >>>             "name": "grammar",
        >>>             "prompt": "How correct is the grammar?",
        >>>             "options": options
        >>>         }
        >>>     ]
        >>> }
        >>>
        >>> examples = [
        >>>     {
        >>>         'answer': u'Lorem ipsum',
        >>>         'options_selected': {
        >>>             'vocabulary': 'good',
        >>>             'grammar': 'excellent'
        >>>         }
        >>>     },
        >>>     {
        >>>         'answer': u'Doler',
        >>>         'options_selected': {
        >>>             'vocabulary': 'good',
        >>>             'grammar': 'poor'
        >>>         }
        >>>     }
        >>> ]
        >>>
        >>> examples = deserialize_training_examples(examples, rubric)

    """
    # Parse the rubric
    # This will raise an exception if the serialized rubric is invalid.
    rubric = rubric_from_dict(rubric_dict)

    # Parse each example
    created_examples = []
    for example_dict in examples:
        is_valid, errors = validate_training_example_format(example_dict)
        if not is_valid:
            raise InvalidTrainingExample("; ".join(errors))

        options_ids = rubric.options_ids(example_dict['options_selected'])

        # Calculate the content hash to look up the example
        content_hash = TrainingExample.calculate_hash(example_dict['answer'], options_ids, rubric)

        try:
            example = TrainingExample.objects.get(content_hash=content_hash)
        except TrainingExample.DoesNotExist:
            try:
                example = TrainingExample.create_example(
                    example_dict['answer'], options_ids, rubric
                )
            except IntegrityError:
                example = TrainingExample.objects.get(content_hash=content_hash)

        created_examples.append(example)

    return created_examples
