"""
Serializers for the training assessment type.
"""


from django.core.cache import cache
from django.db import IntegrityError, transaction

from openassessment.assessment.data_conversion import update_training_example_answer_format
from openassessment.assessment.models import TrainingExample

from .base import RubricSerializer, rubric_from_dict


class InvalidTrainingExample(Exception):
    """
    The training example could not be deserialized.
    """


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
        errors.append("Training example must be a dictionary")

    if 'answer' not in example:
        errors.append('Training example must contain an "answer" field.')

    if 'options_selected' not in example:
        errors.append('Training example must contain an "options_selected" field.')

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
    # Since training examples are immutable, we can safely cache them
    cache_key = example.cache_key_serialized()
    example_dict = cache.get(cache_key)
    if example_dict is None:
        example_dict = {
            'answer': update_training_example_answer_format(example.answer),
            'options_selected': example.options_selected_dict,
            'rubric': RubricSerializer.serialized_from_cache(example.rubric),
        }
        cache.set(cache_key, example_dict)
    return example_dict


@transaction.atomic
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
        InvalidRubricSelection
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
        >>>     "prompts": [
        >>>         {"description": "Prompt 1"}
        >>>         {"description": "Prompt 2"}
        >>>         {"description": "Prompt 3"}
        >>>     ],
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
        >>>         'answer': {
        >>>             'parts': {
        >>>                 [
        >>>                     {'text:' 'Answer part 1'},
        >>>                     {'text:' 'Answer part 2'},
        >>>                     {'text:' 'Answer part 3'}
        >>>                 ]
        >>>             }
        >>>         },
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
        # Try to retrieve the example from the cache
        cache_key, content_hash = TrainingExample.cache_key(
            example_dict['answer'],
            example_dict['options_selected'],
            rubric
        )
        example = cache.get(cache_key)

        # If we couldn't retrieve the example from the cache, create it
        if example is None:
            # Validate the training example
            is_valid, errors = validate_training_example_format(example_dict)
            if not is_valid:
                raise InvalidTrainingExample("; ".join(errors))

            # Get or create the training example
            try:
                example = TrainingExample.objects.get(content_hash=content_hash)
            except TrainingExample.DoesNotExist:
                try:
                    with transaction.atomic():
                        example = TrainingExample.create_example(
                            example_dict['answer'], example_dict['options_selected'], rubric
                        )
                except IntegrityError:
                    example = TrainingExample.objects.get(content_hash=content_hash)

            # Add the example to the cache
            cache.set(cache_key, example)

        created_examples.append(example)

    return created_examples
