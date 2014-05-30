"""
Asynchronous tasks for grading essays using text classifiers.
"""

from celery import task
from django.db import DatabaseError
from celery.utils.log import get_task_logger
from openassessment.assessment.api import ai_worker as ai_worker_api
from openassessment.assessment.errors import AIError, AIGradingInternalError, AIGradingRequestError
from .algorithm import AIAlgorithm, AIAlgorithmError
from openassessment.assessment.models.ai import AIClassifierSet, AIGradingWorkflow


MAX_RETRIES = 2

logger = get_task_logger(__name__)


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


@task(max_retries=MAX_RETRIES)  # pylint: disable=E1102
def reschedule_grading_tasks(course_id, item_id):
    """
    Reschedules all incomplete grading workflows with the specified parameters.

    Args:
        course_id (unicode): The course item that we will be rerunning the rescheduling on.
        item_id (unicode): The item that the rescheduling will be running on
    """
    # Finds all incomplete grading workflows
    grading_workflows = AIGradingWorkflow.get_incomplete_workflows(course_id, item_id)

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
            except (AIGradingInternalError, AIGradingRequestError, AIError) as ex:
                msg = (
                    u"An error occurred while try to grade essay with uuid='{id}': {ex}"
                ).format(id=workflow.uuid, ex=ex)
                logger.exception(msg)
                failures += 1

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