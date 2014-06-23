"""
Asynchronous tasks for training classifiers from examples.
"""
import datetime
from collections import defaultdict
from celery import task
from celery.utils.log import get_task_logger
from dogapi import dog_stats_api
from django.conf import settings
from django.db import DatabaseError
from openassessment.assessment.api import ai_worker as ai_worker_api
from openassessment.assessment.errors import AIError, ANTICIPATED_CELERY_ERRORS
from .algorithm import AIAlgorithm, AIAlgorithmError
from .grading import reschedule_grading_tasks
from openassessment.assessment.errors.ai import AIGradingInternalError
from openassessment.assessment.models.ai import AITrainingWorkflow

MAX_RETRIES = 2

logger = get_task_logger(__name__)

# If the Django settings define a low-priority queue, use that.
# Otherwise, use the default queue.
TRAINING_TASK_QUEUE = getattr(settings, 'LOW_PRIORITY_QUEUE', None)
RESCHEDULE_TASK_QUEUE = getattr(settings, 'LOW_PRIORITY_QUEUE', None)


class InvalidExample(Exception):
    """
    The example retrieved from the AI API had an invalid format.
    """
    def __init__(self, example_dict, msg):
        err_msg = u"Training example \"{example}\" is not valid: {msg}".format(
            example=example_dict,
            msg=msg
        )
        super(InvalidExample, self).__init__(err_msg)


@task(queue=TRAINING_TASK_QUEUE, max_retries=MAX_RETRIES)  # pylint: disable=E1102
@dog_stats_api.timed('openassessment.assessment.ai.train_classifiers.time')
def train_classifiers(workflow_uuid):
    """
    Asynchronous task to train classifiers for AI grading.
    This task uses the AI API to retrieve task parameters
    (algorithm ID and training examples) and upload
    the trained classifiers.

    If the task could not be completed successfully,
    it is retried a few times.  If it continues to fail,
    it is left incomplete.  Since the AI API tracks all
    training tasks in the database, incomplete tasks
    can always be rescheduled manually later.

    Args:
        workflow_uuid (str): The UUID of the workflow associated
            with this training task.

    Returns:
        None

    Raises:
        AIError: An error occurred during a request to the AI API.
        AIAlgorithmError: An error occurred while training the AI classifiers.
        InvalidExample: The training examples provided by the AI API were not valid.

    """
    # Short-circuit if the workflow is already marked complete
    # This is an optimization, but training tasks could still
    # execute multiple times depending on when they get picked
    # up by workers and marked complete.
    try:
        if ai_worker_api.is_training_workflow_complete(workflow_uuid):
            return
    except AIError:
        msg = (
            u"An unexpected error occurred while checking the "
            u"completion of training workflow with UUID {uuid}"
        ).format(uuid=workflow_uuid)
        logger.exception(msg)
        raise train_classifiers.retry()

    # Retrieve task parameters
    try:
        params = ai_worker_api.get_training_task_params(workflow_uuid)
        examples = params['training_examples']
        algorithm_id = params['algorithm_id']
        course_id = params['course_id']
        item_id = params['item_id']
    except (AIError, KeyError):
        msg = (
            u"An error occurred while retrieving AI training "
            u"task parameters for the workflow with UUID {}"
        ).format(workflow_uuid)
        logger.exception(msg)
        raise train_classifiers.retry()

    # Retrieve the ML algorithm to use for training
    # (based on task params and worker configuration)
    try:
        algorithm = AIAlgorithm.algorithm_for_id(algorithm_id)
    except AIAlgorithmError:
        msg = (
            u"An error occurred while loading the "
            u"AI algorithm (training workflow UUID {})"
        ).format(workflow_uuid)
        logger.exception(msg)
        raise train_classifiers.retry()
    except AIError:
        msg = (
            u"An error occurred while retrieving "
            u"the algorithm ID (training workflow UUID {})"
        ).format(workflow_uuid)
        logger.exception(msg)
        raise train_classifiers.retry()

    # Train a classifier for each criterion
    # The AIAlgorithm subclass is responsible for ensuring that
    # the trained classifiers are JSON-serializable.
    try:
        classifier_set = {
            criterion_name: algorithm.train_classifier(examples_dict)
            for criterion_name, examples_dict
            in _examples_by_criterion(examples).iteritems()
        }
    except InvalidExample:
        msg = (
            u"Training example format was not valid "
            u"(training workflow UUID {})"
        ).format(workflow_uuid)
        logger.exception(msg)
        raise train_classifiers.retry()
    except AIAlgorithmError:
        msg = (
            u"An error occurred while training AI classifiers "
            u"(training workflow UUID {})"
        ).format(workflow_uuid)
        logger.exception(msg)
        raise train_classifiers.retry()

    # Upload the classifiers
    # (implicitly marks the workflow complete)
    try:
        ai_worker_api.create_classifiers(workflow_uuid, classifier_set)
    except AIError:
        msg = (
            u"An error occurred while uploading trained classifiers "
            u"(training workflow UUID {})"
        ).format(workflow_uuid)
        logger.exception(msg)
        raise train_classifiers.retry()

    # Upon successful completion of the creation of classifiers, we will try to automatically schedule any
    # grading tasks for the same item.
    try:
        reschedule_grading_tasks.apply_async(args=[course_id, item_id])
    except AIGradingInternalError as ex:
        msg = (
            u"An error occured while trying to regrade all ungraded assignments"
            u"after classifiers were trained successfully: {}"
        ).format(ex)
        logger.exception(msg)
        # Here we don't retry, because they will already retry once in the grading task.
        raise


@task(queue=RESCHEDULE_TASK_QUEUE, max_retries=MAX_RETRIES) #pylint: disable=E1102
@dog_stats_api.timed('openassessment.assessment.ai.reschedule_training_tasks.time')
def reschedule_training_tasks(course_id, item_id):
    """
    Reschedules all incomplete training tasks

    Args:
        course_id (unicode): The course that we are going to search for unfinished training workflows
        item_id (unicode): The specific item within that course that we will reschedule unfinished workflows for

    Raises:
        AIReschedulingInternalError
        DatabaseError
    """
    # Starts logging the details of the rescheduling
    _log_start_reschedule_training(course_id=course_id, item_id=item_id)
    start_time = datetime.datetime.now()

    # Run a query to find the incomplete training workflows
    try:
        training_workflows = AITrainingWorkflow.get_incomplete_workflows(course_id, item_id)
    except (DatabaseError, AITrainingWorkflow.DoesNotExist) as ex:
        msg = (
            u"An unexpected error occurred while retrieving all incomplete "
            u"training tasks for course_id: {cid} and item_id: {iid}: {ex}"
        ).format(cid=course_id, iid=item_id, ex=ex)
        logger.exception(msg)
        raise reschedule_training_tasks.retry()

    # Tries to train every workflow that has not completed.
    for target_workflow in training_workflows:
        try:
            train_classifiers.apply_async(args=[target_workflow.uuid])
            logger.info(
                u"Rescheduling of training was successful for workflow with uuid{}".format(target_workflow.uuid)
            )
        except ANTICIPATED_CELERY_ERRORS as ex:
            msg = (
                u"An unexpected error occurred while scheduling the task for training workflow with UUID {id}: {ex}"
            ).format(id=target_workflow.uuid, ex=ex)
            logger.exception(msg)

            time_delta = datetime.datetime.now() - start_time
            _log_complete_reschedule_training(
                course_id=course_id, item_id=item_id, seconds=time_delta.total_seconds(), success=False
            )
            raise reschedule_training_tasks.retry()

    # Logs the total time to reschedule all training of classifiers if not logged beforehand by exception.
    time_delta = datetime.datetime.now() - start_time
    _log_complete_reschedule_training(
        course_id=course_id, item_id=item_id, seconds=time_delta.total_seconds(), success=True
    )

def _examples_by_criterion(examples):
    """
    Transform the examples returned by the AI API into our internal format.

    Args:
        examples (list): Training examples of the form returned by the AI API.
            Each element of the list should be a dictionary with keys
            'text' (the essay text) and 'scores' (a dictionary mapping
            criterion names to numeric scores).

    Returns:
        dict: keys are the criteria names, and each value is list of `AIAlgorithm.ExampleEssay`s

    Raises:
        InvalidExample: The provided training examples are not in a valid format.

    """
    internal_examples = defaultdict(list)
    prev_criteria = None

    for example_dict in examples:
        # Check that the example contains the expected keys
        try:
            scores_dict = example_dict['scores']
            text = unicode(example_dict['text'])
        except KeyError:
            raise InvalidExample(example_dict, u'Example dict must have keys "scores" and "text"')

        # Check that the criteria names are consistent across examples
        if prev_criteria is None:
            prev_criteria = set(scores_dict.keys())
        else:
            if prev_criteria != set(scores_dict.keys()):
                msg = (
                    u"Example criteria do not match "
                    u"the previous example: {criteria}"
                ).format(criteria=prev_criteria)
                raise InvalidExample(example_dict, msg)

        for criterion_name, score in scores_dict.iteritems():
            try:
                score = int(score)
            except ValueError:
                raise InvalidExample(example_dict, u"Example score is not an integer")
            else:
                internal_ex = AIAlgorithm.ExampleEssay(text, score)
                internal_examples[criterion_name].append(internal_ex)
    return internal_examples


def _log_start_reschedule_training(course_id=None, item_id=None):
    """
    Sends data about the rescheduling_training task to datadog

    Args:
        course_id (unicode): the course id to associate with the log start
        item_id (unicode): the item id to tag with the log start
    """
    tags = [
        u"course_id:{}".format(course_id),
        u"item_id:{}".format(item_id),
    ]
    dog_stats_api.increment('openassessment.assessment.ai_task.AIRescheduleTraining.scheduled_count', tags)

    msg = u"Rescheduling of incomplete training tasks began for course_id={cid} and item_id={iid}"
    logger.info(msg.format(cid=course_id, iid=item_id))


def _log_complete_reschedule_training(course_id=None, item_id=None, seconds=-1, success=False):
    """
    Sends the total time the rescheduling of training tasks took to datadog
    Note that this function may be invoked multiple times per call to reschedule_training_tasks,
    because the time for EACH ATTEMPT is taken (i.e. if we fail (by error) to schedule training once,
    we log the time elapsed before trying again.)

    Args:
        course_id (unicode): the course_id to tag the task with
        item_id (unicode): the item_id to tag the task with
        seconds (int): the number of seconds that elapsed during the rescheduling task.
        success (bool): indicates whether or not all attempts to reschedule were successful
    """
    tags = [
        u"course_id:{}".format(course_id),
        u"item_id:{}".format(item_id),
        u"success:{}".format(success)
    ]

    dog_stats_api.histogram('openassessment.assessment.ai_task.AIRescheduleTraining.turnaround_time', seconds,tags)
    dog_stats_api.increment('openassessment.assessment.ai_task.AIRescheduleTraining.completed_count', tags)

    msg = u"Rescheduling of incomplete training tasks for course_id={cid} and item_id={iid} completed in {s} seconds."
    if not success:
        msg += u" At least one rescheduling task failed due to internal error."
    msg.format(cid=course_id, iid=item_id, s=seconds)
    logger.info(msg)
