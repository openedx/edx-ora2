"""
Public interface for AI training and grading, used by workers.
"""
import logging
from django.utils.timezone import now
from django.db import DatabaseError
from openassessment.assessment.models import (
    AITrainingWorkflow, AIClassifierSet,
    ClassifierUploadError, ClassifierSerializeError,
    IncompleteClassifierSet, NoTrainingExamples
)
from openassessment.assessment.errors import (
    AITrainingRequestError, AITrainingInternalError
)


logger = logging.getLogger(__name__)



def get_submission(grading_workflow_uuid):
    """
    Retrieve the submission associated with a particular grading workflow.

    Args:
        grading_workflow_uuid (str): The UUID of the grading workflow.

    Returns:
        submission (JSON-serializable): submission from the student.

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    pass


def get_classifier_set(grading_workflow_uuid):
    """
    Retrieve the classifier set associated with a particular grading workflow.

    Args:
        grading_workflow_uuid (str): The UUID of the grading workflow.

    Returns:
        dict: Maps criterion names to serialized classifiers.
            (binary classifiers are base-64 encoded).

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    pass


def create_assessment(grading_workflow_uuid, assessment):
    """
    Create an AI assessment (complete the AI grading task).

    Args:
        grading_workflow_uuid (str): The UUID of the grading workflow.
        assessment (dict): The serialized assessment.

    Returns:
        None

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    pass


def get_algorithm_id(training_workflow_uuid):
    """
    Retrieve the ID of the algorithm to use.

    Args:
        training_workflow_uuid (str): The UUID of the training workflow.

    Returns:
        unicode: The algorithm ID associated with the training task.

    Raises:
        AITrainingRequestError
        AITrainingInternalError

    """
    try:
        workflow = AITrainingWorkflow.objects.get(uuid=training_workflow_uuid)
        return workflow.algorithm_id
    except AITrainingWorkflow.DoesNotExist:
        msg = (
            u"Could not retrieve AI training workflow with UUID {}"
        ).format(training_workflow_uuid)
        raise AITrainingRequestError(msg)
    except DatabaseError:
        msg = (
            u"An unexpected error occurred while retrieving "
            u"the algorithm ID for training workflow with UUID {}"
        ).format(training_workflow_uuid)
        logger.exception(msg)
        raise AITrainingInternalError(msg)


def get_training_examples(training_workflow_uuid):
    """
    Retrieve the training examples associated with a training task.

    Args:
        training_workflow_uuid (str): The UUID of the training workflow.

    Returns:
        list of dict: Serialized training examples, of the form:

    Raises:
        AITrainingRequestError
        AITrainingInternalError

    Example usage:
        >>> get_training_examples('abcd1234')
        [
            {
                "text": u"Example answer number one",
                "scores": {
                    "vocabulary": 1,
                    "grammar": 2
                }
            },
            {
                "text": u"Example answer number two",
                "scores": {
                    "vocabulary": 3,
                    "grammar": 1
                }
            }
        ]

    """
    try:
        workflow = AITrainingWorkflow.objects.get(uuid=training_workflow_uuid)
        returned_examples = []

        for example in workflow.training_examples.all():
            answer = example.answer
            if isinstance(answer, dict):
                text = answer.get('answer', '')
            else:
                text = answer

            scores = {
                option.criterion.name: option.points
                for option in example.options_selected.all()
            }

            returned_examples.append({
                'text': text,
                'scores': scores
            })

        return returned_examples
    except AITrainingWorkflow.DoesNotExist:
        msg = (
            u"Could not retrieve AI training workflow with UUID {}"
        ).format(training_workflow_uuid)
        raise AITrainingRequestError(msg)
    except DatabaseError:
        msg = (
            u"An unexpected error occurred while retrieving "
            u"training examples for the AI training workflow with UUID {}"
        ).format(training_workflow_uuid)
        logger.exception(msg)
        raise AITrainingInternalError(msg)


def create_classifiers(training_workflow_uuid, classifier_set):
    """
    Upload trained classifiers and mark the workflow complete.

    If grading tasks were submitted before any classifiers were trained,
    this call will automatically reschedule those tasks.

    Args:
        training_workflow_uuid (str): The UUID of the training workflow.
        classifier_set (dict): Mapping of criteria names to serialized classifiers.

    Returns:
        None

    Raises:
        AITrainingRequestError
        AITrainingInternalError

    """
    try:
        workflow = AITrainingWorkflow.objects.get(uuid=training_workflow_uuid)

        # If the task is executed multiple times, the classifier set may already
        # have been created.  If so, log a warning then return immediately.
        if workflow.is_complete:
            msg = u"AI training workflow with UUID {} already has trained classifiers."
            logger.warning(msg)
        else:
            workflow.complete(classifier_set)
    except AITrainingWorkflow.DoesNotExist:
        msg = (
            u"Could not retrieve AI training workflow with UUID {}"
        ).format(training_workflow_uuid)
        raise AITrainingRequestError(msg)
    except NoTrainingExamples as ex:
        logger.exception(ex)
        raise AITrainingInternalError(ex)
    except IncompleteClassifierSet as ex:
        msg = (
            u"An error occurred while creating the classifier set "
            u"for the training workflow with UUID {uuid}: {ex}"
        ).format(uuid=training_workflow_uuid, ex=ex)
        raise AITrainingRequestError(msg)
    except (ClassifierSerializeError, ClassifierUploadError, DatabaseError) as ex:
        msg = (
            u"An unexpected error occurred while creating the classifier "
            u"set for training workflow UUID {uuid}: {ex}"
        ).format(uuid=training_workflow_uuid, ex=ex)
        logger.exception(msg)
        raise AITrainingInternalError(msg)
    except DatabaseError:
        msg = (
            u"An unexpected error occurred while creating the classifier set "
            u"for the AI training workflow with UUID {}"
        ).format(training_workflow_uuid)
        logger.exception(msg)
        raise AITrainingInternalError(msg)
