"""
Public interface for AI training and grading, used by students/course authors.
"""
import logging
from openassessment.assessment.serializers import (
    deserialize_training_examples, InvalidTrainingExample, InvalidRubric
)
from openassessment.assessment.errors import (
    AITrainingRequestError, AITrainingInternalError
)
from openassessment.assessment.models import AITrainingWorkflow, InvalidOptionSelection
from openassessment.assessment.worker import training as training_tasks


logger = logging.getLogger(__name__)


def submit(submission_uuid, rubric):
    """
    Submit a response for AI assessment.
    This will:
        (a) create a workflow (database record) to track the grading task
        (b) if classifiers exist for the rubric, schedule an asynchronous grading task.

    Args:
        submission_uuid (str): The UUID of the submission to assess.
        rubric (dict): Serialized rubric model.

    Returns:
        grading_workflow_uuid (str): The UUID of the grading workflow.
            Usually the caller of `submit()` won't need this (since the workers
            are parameterized by grading workflow UUID), but it's
            useful for testing.

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    pass


def get_latest_assessment(submission_uuid):
    """
    Retrieve the latest AI assessment for a submission.

    Args:
        submission_uuid (str): The UUID of the submission being assessed.

    Returns:
        dict: The serialized assessment model

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    pass


def train_classifiers(rubric_dict, examples, algorithm_id):
    """
    Schedule a task to train classifiers.
    All training examples must match the rubric!

    Args:
        rubric_dict (dict): The rubric used to assess the classifiers.
        examples (list of dict): Serialized training examples.
        algorithm_id (unicode): The ID of the algorithm used to train the classifiers.

    Returns:
        training_workflow_uuid (str): The UUID of the training workflow.
            Usually the caller will not need this (since the workers
            are parametrized by training workflow UUID), but it's
            useful for testing.

    Raises:
        AITrainingRequestError
        AITrainingInternalError

    """
    # Get or create the rubric and training examples
    try:
        examples = deserialize_training_examples(examples, rubric_dict)
    except (InvalidRubric, InvalidTrainingExample, InvalidOptionSelection) as ex:
        msg = u"Could not parse rubric and/or training examples: {ex}".format(ex=ex)
        raise AITrainingRequestError(msg)

    # Create the workflow model
    try:
        workflow = AITrainingWorkflow.start_workflow(examples, algorithm_id)
    except:
        msg = (
            u"An unexpected error occurred while creating "
            u"the AI training workflow"
        )
        logger.exception(msg)
        raise AITrainingInternalError(msg)

    # Schedule the task, parametrized by the workflow UUID
    try:
        training_tasks.train_classifiers.apply_async(args=[workflow.uuid])
    except:
        msg = (
            u"An unexpected error occurred while scheduling "
            u"the task for training workflow with UUID {}"
        ).format(workflow.uuid)
        logger.exception(msg)
        raise AITrainingInternalError(msg)

    # Return the workflow UUID
    return workflow.uuid


def reschedule_unfinished_tasks(course_id=None, item_id=None, task_type=None):
    """
    Check for unfinished tasks (both grading and training) and reschedule them.
    Optionally restrict by course/item ID and task type.

    Kwargs:
        course_id (unicode): Restrict to unfinished tasks in a particular course.
        item_id (unicode): Restrict to unfinished tasks for a particular item in a course.
            NOTE: if you specify the item ID, you must also specify the course ID.
        task_type (unicode): Either "grade" or "train".  Restrict to unfinished tasks of this type.

    Raises:
        AIError

    """
    pass
