"""
Public interface for AI training and grading, used by workers.
"""
import logging
from httplib import HTTPException
from django.db import DatabaseError
from dogapi import dog_stats_api
from openassessment.assessment.models import (
    essay_text_from_submission,
    AITrainingWorkflow, AIGradingWorkflow,
    ClassifierUploadError, ClassifierSerializeError,
    IncompleteClassifierSet, NoTrainingExamples,
    InvalidRubricSelection
)
from openassessment.assessment.errors import (
    AITrainingRequestError, AITrainingInternalError,
    AIGradingRequestError, AIGradingInternalError
)


logger = logging.getLogger(__name__)


@dog_stats_api.timed('openassessment.assessment.ai.get_grading_task_params')
def get_grading_task_params(grading_workflow_uuid):
    """
    Retrieve the classifier set and algorithm ID
    associated with a particular grading workflow.

    Args:
        grading_workflow_uuid (str): The UUID of the grading workflow.

    Returns:
        dict with keys:
            * essay_text (unicode): The text of the essay submission.
            * classifier_set (dict): Maps criterion names to serialized classifiers.
            * valid_scores (dict): Maps criterion names to a list of valid scores for that criterion.
            * algorithm_id (unicode): ID of the algorithm used to perform training.

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    try:
        workflow = AIGradingWorkflow.objects.get(uuid=grading_workflow_uuid)
    except AIGradingWorkflow.DoesNotExist:
        msg = (
            u"Could not retrieve the AI grading workflow with uuid {}"
        ).format(grading_workflow_uuid)
        raise AIGradingRequestError(msg)
    except DatabaseError as ex:
        msg = (
            u"An unexpected error occurred while retrieving the "
            u"AI grading workflow with uuid {uuid}: {ex}"
        ).format(uuid=grading_workflow_uuid, ex=ex)
        logger.exception(msg)
        raise AIGradingInternalError(msg)

    classifier_set = workflow.classifier_set
    # Though tasks shouldn't be scheduled until classifer set(s) exist, off of the happy path this is a likely
    # occurrence.  Our response is to log this lack of compliance to dependency as an exception, and then thrown
    # an error with the purpose of killing the celery task running this code.
    if classifier_set is None:
        msg = (
            u"AI grading workflow with UUID {} has no classifier set, but was scheduled for grading"
        ).format(grading_workflow_uuid)
        logger.exception(msg)
        raise AIGradingInternalError(msg)

    try:
        return {
            'essay_text': workflow.essay_text,
            'classifier_set': workflow.classifier_set.classifier_data_by_criterion,
            'algorithm_id': workflow.algorithm_id,
            'valid_scores': workflow.classifier_set.valid_scores_by_criterion,
        }
    except (
        DatabaseError, ClassifierSerializeError, IncompleteClassifierSet,
        ValueError, IOError, HTTPException
    ) as ex:
        msg = (
            u"An unexpected error occurred while retrieving "
            u"classifiers for the grading workflow with UUID {uuid}: {ex}"
        ).format(uuid=grading_workflow_uuid, ex=ex)
        logger.exception(msg)
        raise AIGradingInternalError(msg)


@dog_stats_api.timed('openassessment.assessment.ai.create_assessment')
def create_assessment(grading_workflow_uuid, criterion_scores):
    """
    Create an AI assessment (complete the AI grading task).

    Args:
        grading_workflow_uuid (str): The UUID of the grading workflow.
        criterion_scores (dict): Dictionary mapping criteria names to integer scores.

    Returns:
        None

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    try:
        workflow = AIGradingWorkflow.objects.get(uuid=grading_workflow_uuid)
    except AIGradingWorkflow.DoesNotExist:
        msg = (
            u"Could not retrieve the AI grading workflow with uuid {}"
        ).format(grading_workflow_uuid)
        raise AIGradingRequestError(msg)
    except DatabaseError as ex:
        msg = (
            u"An unexpected error occurred while retrieving the "
            u"AI grading workflow with uuid {uuid}: {ex}"
        ).format(uuid=grading_workflow_uuid, ex=ex)
        logger.exception(msg)
        raise AIGradingInternalError(msg)

    # Optimization: if the workflow has already been marked complete
    # (perhaps the task was picked up by multiple workers),
    # then we don't need to do anything.
    # Otherwise, create the assessment mark the workflow complete.
    try:
        if not workflow.is_complete:
            workflow.complete(criterion_scores)
            logger.info((
                u"Created assessment for AI grading workflow with UUID {workflow_uuid} "
                u"(algorithm ID {algorithm_id})"
            ).format(workflow_uuid=workflow.uuid, algorithm_id=workflow.algorithm_id))
        else:
            msg = u"Grading workflow with UUID {} is already marked complete".format(workflow.uuid)
            logger.info(msg)
    except DatabaseError as ex:
        msg = (
            u"An unexpected error occurred while creating the assessment "
            u"for AI grading workflow with uuid {uuid}: {ex}"
        ).format(uuid=grading_workflow_uuid, ex=ex)
        logger.exception(msg)
        raise AIGradingInternalError(msg)

    # Fire a signal to update the workflow API
    # This will allow students to receive a score if they're
    # waiting on an AI assessment.
    # The signal receiver is responsible for catching and logging
    # all exceptions that may occur when updating the workflow.
    from openassessment.assessment.signals import assessment_complete_signal
    assessment_complete_signal.send(sender=None, submission_uuid=workflow.submission_uuid)


@dog_stats_api.timed('openassessment.assessment.ai.get_training_task_params')
def get_training_task_params(training_workflow_uuid):
    """
    Retrieve the training examples and algorithm ID
    associated with a training task.

    Args:
        training_workflow_uuid (str): The UUID of the training workflow.

    Returns:
        dict with keys:
            * training_examples (list of dict): The examples used to train the classifiers.
            * course_id (unicode): The course ID that the training task is associated with.
            * item_id (unicode): Identifies the item that the AI will be training to grade.
            * algorithm_id (unicode): The ID of the algorithm to use for training.

    Raises:
        AITrainingRequestError
        AITrainingInternalError

    Example usage:
        >>> params = get_training_task_params('abcd1234')
        >>> params['algorithm_id']
        u'ease'
        >>> params['training_examples']
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
            scores = {
                option.criterion.name: option.points
                for option in example.options_selected.all()
            }

            returned_examples.append({
                'text': essay_text_from_submission({'answer': example.answer}),
                'scores': scores
            })

        return {
            'training_examples': returned_examples,
            'algorithm_id': workflow.algorithm_id,
            'course_id': workflow.course_id,
            'item_id': workflow.item_id
        }
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


@dog_stats_api.timed('openassessment.assessment.ai.create_classifiers')
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
        # have been created.  If so, log it, then return immediately.
        if workflow.is_complete:
            msg = u"AI training workflow with UUID {} already has trained classifiers.".format(workflow.uuid)
            logger.info(msg)
        else:
            workflow.complete(classifier_set)
            logger.info((
                u"Created trained classifiers for the AI training workflow with UUID {workflow_uuid} "
                u"(using algorithm ID {algorithm_id})"
            ).format(workflow_uuid=workflow.uuid, algorithm_id=workflow.algorithm_id))
    except AITrainingWorkflow.DoesNotExist:
        msg = (
            u"Could not retrieve AI training workflow with UUID {}"
        ).format(training_workflow_uuid)
        raise AITrainingRequestError(msg)
    except NoTrainingExamples as ex:
        logger.exception(ex)
        raise AITrainingInternalError(ex)
    except (IncompleteClassifierSet, InvalidRubricSelection) as ex:
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


def is_training_workflow_complete(workflow_uuid):
    """
    Check whether the training workflow is complete.

    Args:
        workflow_uuid (str): The UUID of the training workflow

    Returns:
        bool

    Raises:
        AITrainingRequestError
        AITrainingInternalError

    """
    try:
        return AITrainingWorkflow.is_workflow_complete(workflow_uuid)
    except AITrainingWorkflow.DoesNotExist:
        msg = (
            u"Could not retrieve training workflow "
            u"with uuid {uuid} to check whether it's complete."
        ).format(uuid=workflow_uuid)
        raise AITrainingRequestError(msg)
    except DatabaseError:
        msg = (
            u"An unexpected error occurred while checking "
            u"the training workflow with uuid {uuid} for completeness"
        ).format(uuid=workflow_uuid)
        raise AITrainingInternalError(msg)


def is_grading_workflow_complete(workflow_uuid):
    """
    Check whether the grading workflow is complete.

    Args:
        workflow_uuid (str): The UUID of the grading workflow

    Returns:
        bool

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    try:
        return AIGradingWorkflow.is_workflow_complete(workflow_uuid)
    except AIGradingWorkflow.DoesNotExist:
        msg = (
            u"Could not retrieve grading workflow "
            u"with uuid {uuid} to check whether it's complete."
        ).format(uuid=workflow_uuid)
        raise AIGradingRequestError(msg)
    except DatabaseError:
        msg = (
            u"An unexpected error occurred while checking "
            u"the grading workflow with uuid {uuid} for completeness"
        ).format(uuid=workflow_uuid)
        raise AIGradingInternalError(msg)
