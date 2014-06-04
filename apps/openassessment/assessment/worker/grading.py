"""
Asynchronous tasks for grading essays using text classifiers.
"""

import datetime
from celery import task
from django.db import DatabaseError
from django.conf import settings
from celery.utils.log import get_task_logger
from dogapi import dog_stats_api
from openassessment.assessment.api import ai_worker as ai_worker_api
from openassessment.assessment.errors import (
    AIError, AIGradingInternalError, AIGradingRequestError, AIReschedulingInternalError, ANTICIPATED_CELERY_ERRORS
)
from .algorithm import AIAlgorithm, AIAlgorithmError
from openassessment.assessment.models.ai import AIClassifierSet, AIGradingWorkflow

MAX_RETRIES = 2

logger = get_task_logger(__name__)

# If the Django settings define a low-priority queue, use that.
# Otherwise, use the default queue.
RESCHEDULE_TASK_QUEUE = getattr(settings, 'LOW_PRIORITY_QUEUE', None)


@task(max_retries=MAX_RETRIES)  # pylint: disable=E1102
def grade_essay(workflow_uuid):
    """
    Asynchronous task to grade an essay using a text classifier
    (trained using a supervised ML algorithm).

    If the task could not be completed successfully,
    it will be retried a few times; if it continues to fail,
    it is left incomplete.  Incomplate tasks can be rescheduled
    manually through the AI API.

    Args:
        workflow_uuid (str): The UUID of the workflow associated
            with this grading task.

    Returns:
        None

    Raises:
        AIError: An error occurred while making an AI worker API call.
        AIAlgorithmError: An error occurred while retrieving or using an AI algorithm.

    """
    # Retrieve the task parameters
    try:
        params = ai_worker_api.get_grading_task_params(workflow_uuid)
        essay_text = params['essay_text']
        classifier_set = params['classifier_set']
        algorithm_id = params['algorithm_id']
    except (AIError, KeyError):
        msg = (
            u"An error occurred while retrieving the AI grading task "
            u"parameters for the workflow with UUID {}"
        ).format(workflow_uuid)
        logger.exception(msg)
        raise grade_essay.retry()

    # Retrieve the AI algorithm
    try:
        algorithm = AIAlgorithm.algorithm_for_id(algorithm_id)
    except AIAlgorithmError:
        msg = (
            u"An error occurred while retrieving "
            u"the algorithm ID (grading workflow UUID {})"
        ).format(workflow_uuid)
        logger.exception(msg)
        raise grade_essay.retry()

    # Use the algorithm to evaluate the essay for each criterion
    try:
        scores_by_criterion = {
            criterion_name: algorithm.score(essay_text, classifier)
            for criterion_name, classifier in classifier_set.iteritems()
        }
    except AIAlgorithmError:
        msg = (
            u"An error occurred while scoring essays using "
            u"an AI algorithm (worker workflow UUID {})"
        ).format(workflow_uuid)
        logger.exception(msg)
        raise grade_essay.retry()

    # Create the assessment and mark the workflow complete
    try:
        ai_worker_api.create_assessment(workflow_uuid, scores_by_criterion)
    except AIError:
        msg = (
            u"An error occurred while creating assessments "
            u"for the AI grading workflow with UUID {uuid}. "
            u"The assessment scores were: {scores}"
        ).format(uuid=workflow_uuid, scores=scores_by_criterion)
        logger.exception(msg)
        raise grade_essay.retry()


@task(queue=RESCHEDULE_TASK_QUEUE, max_retries=MAX_RETRIES)  # pylint: disable=E1102
def reschedule_grading_tasks(course_id, item_id):
    """
    Reschedules all incomplete grading workflows with the specified parameters.

    Args:
        course_id (unicode): The course item that we will be rerunning the rescheduling on.
        item_id (unicode): The item that the rescheduling will be running on

    Raises:
        AIReschedulingInternalError
        AIGradingInternalError
    """

    # Logs the start of the rescheduling process and records the start time so that total time can be calculated later.
    _log_start_reschedule_grading(course_id=course_id, item_id=item_id)
    start_time = datetime.datetime.now()

    # Finds all incomplete grading workflows
    try:
        grading_workflows = AIGradingWorkflow.get_incomplete_workflows(course_id, item_id)
    except (DatabaseError, AIGradingWorkflow.DoesNotExist) as ex:
        msg = (
            u"An unexpected error occurred while retrieving all incomplete "
            u"grading tasks for course_id: {cid} and item_id: {iid}: {ex}"
        ).format(cid=course_id, iid=item_id, ex=ex)
        logger.exception(msg)
        raise AIReschedulingInternalError(msg)

    # Notes whether or not one or more operations failed. If they did, the process of rescheduling will be retried.
    failures = 0

    # A dictionary mapping tuples of (rubric, algorithm_id) to completed classifier sets. Used to avoid repeated
    # queries which will return the same value. This loop implements a memoization of the the query.
    maintained_classifiers = {}

    # Try to grade all incomplete grading workflows
    for workflow in grading_workflows:

        # We will always go through the process of finding the most recent set of classifiers for an
        # incomplete grading workflow. The rationale for this is that if we are ever rescheduling
        # grading, we likely had classifiers which were not working. This way, we always take the last
        # completed set.

        # Note that this solution will lead to failure if "Train Classifiers" and "Refinish Grading Tasks"
        # are called in rapid succession. This is part of the reason this button is in the admin view.

        # Tries to find a set of classifiers that are already defined in our maintained_classifiers based on a
        # description of the workflow in the form of a tuple (rubric, algorithm_id)
        workflow_description = (workflow.rubric, workflow.algorithm_id)
        found_classifiers = maintained_classifiers.get(workflow_description)

        # If no set of classifiers is found, we perform the query to try to find them. We take the most recent
        # and add it to our dictionary of maintained classifiers for future reference.
        if found_classifiers is None:
            try:
                classifier_set_candidates = AIClassifierSet.objects.filter(
                    rubric=workflow.rubric, algorithm_id=workflow.algorithm_id
                ).order_by('-created_at')[:1]
                found_classifiers = classifier_set_candidates[0]
                maintained_classifiers[workflow_description] = found_classifiers
            except IndexError:
                msg = u"No classifiers yet exist for essay with uuid='{}'".format(workflow.uuid)
                logger.log(msg)
            except DatabaseError as ex:
                msg = (
                    u"A Database error occurred while trying to assign classifiers to an essay with uuid='{id}'"
                ).format(id=workflow.uuid)
                logger.exception(msg)

        if found_classifiers is not None:

            workflow.classifier_set = found_classifiers
            try:
                workflow.save()
                logger.info(
                    (
                        u"Classifiers were successfully assigned to grading workflow with uuid={}"
                    ).format(workflow.uuid)
                )
            except DatabaseError as ex:
                msg = (
                    u"A Database error occurred while trying to save classifiers to an essay with uuid='{id}'"
                ).format(id=workflow.uuid)
                logger.exception(msg)

            # Now we should (unless we had an exception above) have a classifier set.
            # Try to schedule the grading
            try:
                grade_essay.apply_async(args=[workflow.uuid])
                logger.info(
                    u"Rescheduling of grading was successful for grading workflow with uuid='{}'".format(workflow.uuid)
                )
            except ANTICIPATED_CELERY_ERRORS as ex:
                msg = (
                    u"An error occurred while try to grade essay with uuid='{id}': {ex}"
                ).format(id=workflow.uuid, ex=ex)
                logger.exception(msg)
                failures += 1

        # If we couldn't assign classifiers, we failed.
        else:
            failures += 1

    # Logs the data from our rescheduling attempt
    time_delta = datetime.datetime.now() - start_time
    _log_complete_reschedule_grading(
        course_id=course_id, item_id=item_id, seconds=time_delta.total_seconds(), success=(failures == 0)
    )

    # If one or more of these failed, we want to retry rescheduling.  Note that this retry is executed in such a way
    # that if it fails, an AIGradingInternalError will be raised with the number of failures on the last attempt (i.e.
    # the total number of workflows matching these critera that still have left to be graded).
    if failures > 0:
        try:
            raise AIGradingInternalError(
                u"In an attempt to reschedule grading workflows, there were {} failures.".format(failures)
            )
        except AIGradingInternalError as ex:
            raise reschedule_grading_tasks.retry()


def _log_start_reschedule_grading(course_id=None, item_id=None):
    """
    Sends data about the rescheduling_grading task to datadog

    Args:
        course_id (unicode): the course id to associate with the log start
        item_id (unicode): the item id to tag with the log start
    """
    tags = [
        u"course_id:{}".format(course_id),
        u"item_id:{}".format(item_id),
    ]
    dog_stats_api.increment('openassessment.assessment.ai_task.AIRescheduleGrading.scheduled_count', tags)

    msg = u"Rescheduling of incomplete grading tasks began for course_id={cid} and item_id={iid}"
    logger.info(msg.format(cid=course_id, iid=item_id))


def _log_complete_reschedule_grading(course_id=None, item_id=None, seconds=-1, success=False):
    """
    Sends the total time the rescheduling of grading tasks took to datadog
    (Just the time taken to reschedule tasks, not the time nescessary to complete them)
    Note that this function may be invoked multiple times per call to reschedule_grading_tasks,
    because the time for EACH ATTEMPT is taken (i.e. if we fail (by error) to schedule grading once,
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

    dog_stats_api.histogram('openassessment.assessment.ai_task.AIRescheduleGrading.turnaround_time', seconds,tags)
    dog_stats_api.increment('openassessment.assessment.ai_task.AIRescheduleGrading.completed_count', tags)

    msg = u"Rescheduling of incomplete grading tasks for course_id={cid} and item_id={iid} completed in {s} seconds."
    if not success:
        msg += u" At least one grading task failed due to internal error."
    msg.format(cid=course_id, iid=item_id, s=seconds)
    logger.info(msg)
