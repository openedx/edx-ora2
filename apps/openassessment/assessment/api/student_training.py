"""
Public interface for student training:

* Staff can create assessments for example responses.
* Students assess an example response, then compare the scores
    they gave to to the instructor's assessment.

"""
import logging
from django.db import DatabaseError
from django.utils.translation import ugettext as _
from submissions import api as sub_api
from openassessment.assessment.models import StudentTrainingWorkflow
from openassessment.assessment.serializers import (
    deserialize_training_examples, serialize_training_example,
    validate_training_example_format,
    InvalidTrainingExample, InvalidRubric
)
from openassessment.assessment.errors import (
    StudentTrainingRequestError, StudentTrainingInternalError
)


logger = logging.getLogger(__name__)


def submitter_is_finished(submission_uuid, requirements):   # pylint:disable=W0613
    """
    Check whether the student has correctly assessed
    all the training example responses.

    Args:
        submission_uuid (str): The UUID of the student's submission.
        requirements (dict): Not used.

    Returns:
        bool

    """
    try:
        workflow = StudentTrainingWorkflow.objects.get(submission_uuid=submission_uuid)
    except StudentTrainingWorkflow.DoesNotExist:
        return False
    else:
        return workflow.is_complete


def assessment_is_finished(submission_uuid, requirements):  # pylint:disable=W0613
    """
    Since the student is not being assessed by others,
    this always returns true.
    """
    return True


def get_score(submission_uuid, requirements):   # pylint:disable=W0613
    """
    Training is either complete or incomplete; there is no score.
    """
    return None


def validate_training_examples(rubric, examples):
    """
    Validate that the training examples match the rubric.

    Args:
        rubric (dict): Serialized rubric model.
        examples (list): List of serialized training examples.

    Returns:
        list of errors (unicode)

    Raises:
        StudentTrainingRequestError
        StudentTrainingInternalError

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
        >>> errors = validate_training_examples(rubric, examples)

    """
    errors = []

    # Construct a list of valid options for each criterion
    try:
        criteria_options = {
            unicode(criterion['name']): [
                unicode(option['name'])
                for option in criterion['options']
            ]
            for criterion in rubric['criteria']
        }
    except (ValueError, KeyError):
        msg = _(u"Could not parse serialized rubric")
        return [msg]

    # Check each example
    for order_num, example_dict in enumerate(examples, start=1):

        # Check the structure of the example dict
        is_format_valid, format_errors = validate_training_example_format(example_dict)
        if not is_format_valid:
            format_errors = [
                _(u"Example {} has a validation error: {}").format(order_num, error)
                for error in format_errors
            ]
            errors.extend(format_errors)
        else:
            # Check each selected option in the example (one per criterion)
            options_selected = example_dict['options_selected']
            for criterion_name, option_name in options_selected.iteritems():
                if criterion_name in criteria_options:
                    valid_options = criteria_options[criterion_name]
                    if option_name not in valid_options:
                        msg = u"Example {} has an invalid option for \"{}\": \"{}\"".format(
                            order_num, criterion_name, option_name
                        )
                        errors.append(msg)
                else:
                    msg = _(u"Example {} has an extra option for \"{}\"").format(
                        order_num, criterion_name
                    )
                    errors.append(msg)

            # Check for missing criteria
            for missing_criterion in set(criteria_options.keys()) - set(options_selected.keys()):
                msg = _(u"Example {} is missing an option for \"{}\"").format(
                    order_num, missing_criterion
                )
                errors.append(msg)

    return errors


def create_training_workflow(submission_uuid, rubric, examples):
    """
    Start the training workflow.

    Args:
        submission_uuid (str): The UUID of the student's submission.
        rubric (dict): Serialized rubric model.
        examples (list): The serialized training examples the student will need to assess.

    Returns:
        None

    Raises:
        StudentTrainingRequestError
        StudentTrainingInternalError

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
        >>> create_training_workflow("5443ebbbe2297b30f503736e26be84f6c7303c57", rubric, examples)

    """
    try:
        # Check that examples were provided
        if len(examples) == 0:
            msg = (
                u"No examples provided for student training workflow "
                u"(attempted to create workflow for student with submission UUID {})"
            ).format(submission_uuid)
            raise StudentTrainingRequestError(msg)

        # Ensure that a workflow doesn't already exist for this submission
        already_exists = StudentTrainingWorkflow.objects.filter(
            submission_uuid=submission_uuid
        ).exists()

        if already_exists:
            msg = (
                u"Student training workflow already exists for the student "
                u"associated with submission UUID {}"
            ).format(submission_uuid)
            raise StudentTrainingRequestError(msg)

        # Create the training examples
        try:
            examples = deserialize_training_examples(examples, rubric)
        except (InvalidRubric, InvalidTrainingExample) as ex:
            logger.exception(
                "Could not deserialize training examples for submission UUID {}".format(submission_uuid)
            )
            raise StudentTrainingRequestError(ex.message)

        # Create the workflow
        try:
            StudentTrainingWorkflow.create_workflow(submission_uuid, examples)
        except sub_api.SubmissionNotFoundError as ex:
            raise StudentTrainingRequestError(ex.message)
    except DatabaseError:
        msg = (
            u"Could not create student training workflow "
            u"with submission UUID {}"
        ).format(submission_uuid)
        logger.exception(msg)
        raise StudentTrainingInternalError(msg)


def get_workflow_status(submission_uuid):
    """
    Get the student's position in the training workflow.

    Args:
        submission_uuid (str): The UUID of the student's submission.

    Returns:
        dict: Serialized TrainingStatus

    Raises:
        StudentTrainingRequestError
        StudentTrainingInternalError

    Example usage:
        >>> get_workflow_status("5443ebbbe2297b30f503736e26be84f6c7303c57")
        {
            'num_items_completed': 1,
            'num_items_available': 3
        }

    """
    try:
        try:
            workflow = StudentTrainingWorkflow.objects.get(submission_uuid=submission_uuid)
        except StudentTrainingWorkflow.DoesNotExist:
            msg = u"Student training workflow does not exist for submission UUID {}".format(submission_uuid)
            raise StudentTrainingRequestError(msg)

        num_completed, num_total = workflow.status
        return {
            "num_completed": num_completed,
            "num_total": num_total
        }
    except DatabaseError:
        msg = (
            u"An unexpected error occurred while "
            u"retrieving the student training workflow status for submission UUID {}"
        ).format(submission_uuid)
        logger.exception(msg)
        raise StudentTrainingInternalError(msg)


def get_training_example(submission_uuid):
    """
    Retrieve a training example for the student to assess.

    Args:
        submission_uuid (str): The UUID of the student's submission.

    Returns:
        dict: The training example with keys "answer", "rubric", and "options_selected".
        If no training examples are available (the student has already assessed every example,
            or no examples are defined), returns None.

    Raises:
        StudentTrainingInternalError

    Example usage:

        >>> examples = [
        >>>     {
        >>>         'answer': u'Doler',
        >>>         'options_selected': {
        >>>             'vocabulary': 'good',
        >>>             'grammar': 'poor'
        >>>         }
        >>>     }
        >>> ]
        >>>
        >>> get_training_example("5443ebbbe2297b30f503736e26be84f6c7303c57")
        {
            'answer': u'Lorem ipsum',
            'rubric': {
                "prompt": "Write an essay!",
                "criteria": [
                    {
                        "order_num": 0,
                        "name": "vocabulary",
                        "prompt": "How varied is the vocabulary?",
                        "options": options
                    },
                    {
                        "order_num": 1,
                        "name": "grammar",
                        "prompt": "How correct is the grammar?",
                        "options": options
                    }
                ],
            },
            'options_selected': {
                'vocabulary': 'good',
                'grammar': 'excellent'
            }
        }

    """
    # Find a workflow for the student
    try:
        workflow = StudentTrainingWorkflow.objects.get(submission_uuid=submission_uuid)

        # Find the next incomplete item in the workflow
        item = workflow.next_incomplete_item
        if item is None:
            return None
        else:
            return serialize_training_example(item.training_example)
    except StudentTrainingWorkflow.DoesNotExist:
        msg = (
            u"No student training workflow exists for the student "
            u"associated with submission UUID {}"
        ).format(submission_uuid)
        raise StudentTrainingRequestError(msg)
    except DatabaseError:
        msg = (
            u"Could not retrieve next item in"
            u" student training workflow with submission UUID {}"
        ).format(submission_uuid)
        logger.exception(msg)
        raise StudentTrainingInternalError(msg)


def assess_training_example(submission_uuid, options_selected, update_workflow=True):
    """
    Assess a training example and update the workflow.

    Args:
        submission_uuid (str): The UUID of the student's submission.
        options_selected (dict): The options the student selected.

    Kwargs:
        update_workflow (bool): If true, mark the current item complete
            if the student has assessed the example correctly.

    Returns:
        corrections (dict): Dictionary containing the correct
            options for criteria the student scored incorrectly.

    Raises:
        StudentTrainingRequestError
        StudentTrainingInternalError

    Example usage:

        >>> options_selected = {
        >>>     'vocabulary': 'good',
        >>>     'grammar': 'excellent'
        >>> }
        >>> assess_training_example("5443ebbbe2297b30f503736e26be84f6c7303c57", options_selected)
        {'grammar': 'poor'}

    """
    # Find a workflow for the student
    try:
        workflow = StudentTrainingWorkflow.objects.get(submission_uuid=submission_uuid)

        # Find the next incomplete item in the workflow
        item = workflow.next_incomplete_item
        if item is None:
            msg = (
                u"No items are available in the student training workflow associated with "
                u"submission UUID {}"
            ).format(submission_uuid)
            raise StudentTrainingRequestError(msg)

        # Check the student's scores against the staff's scores.
        corrections = item.check(options_selected)

        # Mark the item as complete if the student's selection
        # matches the instructor's selection
        if update_workflow and len(corrections) == 0:
            item.mark_complete()
        return corrections
    except StudentTrainingWorkflow.DoesNotExist:
        msg = u"Could not find student training workflow for submission UUID {}".format(submission_uuid)
        raise StudentTrainingRequestError(msg)
    except DatabaseError:
        msg = (
            u"An error occurred while comparing the student's assessment "
            u"to the training example.  The submission UUID for the student is {}"
        ).format(submission_uuid)
        logger.exception(msg)
        raise StudentTrainingInternalError(msg)
