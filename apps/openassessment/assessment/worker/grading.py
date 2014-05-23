"""
Asynchronous tasks for grading essays using text classifiers.
"""

from celery import task
from celery.utils.log import get_task_logger
from openassessment.assessment.api import ai_worker as ai_worker_api
from openassessment.assessment.errors import AIError
from .algorithm import AIAlgorithm, AIAlgorithmError


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
