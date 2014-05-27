"""
Asynchronous tasks for training classifiers from examples.
"""
from collections import defaultdict
from celery import task
from celery.utils.log import get_task_logger
from openassessment.assessment.api import ai_worker as ai_worker_api
from openassessment.assessment.errors import AIError
from .algorithm import AIAlgorithm, AIAlgorithmError


MAX_RETRIES = 2

logger = get_task_logger(__name__)


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


@task(max_retries=MAX_RETRIES)  # pylint: disable=E1102
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
    # Retrieve task parameters
    try:
        params = ai_worker_api.get_training_task_params(workflow_uuid)
        examples = params['training_examples']
        algorithm_id = params['algorithm_id']
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
