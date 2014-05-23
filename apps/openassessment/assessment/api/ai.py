"""
Public interface for AI training and grading, used by students/course authors.
"""
import logging
from django.db import DatabaseError
from submissions import api as sub_api
from openassessment.assessment.serializers import (
    deserialize_training_examples, InvalidTrainingExample, InvalidRubric,
    full_assessment_dict
)
from openassessment.assessment.errors import (
    AITrainingRequestError, AITrainingInternalError,
    AIGradingRequestError, AIGradingInternalError
)
from openassessment.assessment.models import (
    AITrainingWorkflow, InvalidOptionSelection, NoTrainingExamples,
    Assessment, AITrainingWorkflow, AIGradingWorkflow,
    AIClassifierSet, AI_ASSESSMENT_TYPE
)
from openassessment.assessment.worker import training as training_tasks
from openassessment.assessment.worker import grading as grading_tasks


logger = logging.getLogger(__name__)


def submit(submission_uuid, rubric, algorithm_id):
    """
    Submit a response for AI assessment.
    This will:
        (a) create a workflow (database record) to track the grading task
        (b) if classifiers exist for the rubric, schedule an asynchronous grading task.

    Args:
        submission_uuid (str): The UUID of the submission to assess.
        rubric (dict): Serialized rubric model.
        algorithm_id (unicode): Use only classifiers trained with the specified algorithm.

    Returns:
        grading_workflow_uuid (str): The UUID of the grading workflow.
            Usually the caller of `submit()` won't need this (since the workers
            are parameterized by grading workflow UUID), but it's
            useful for testing.

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    try:
        workflow = AIGradingWorkflow.start_workflow(submission_uuid, rubric, algorithm_id)
    except (sub_api.SubmissionNotFoundError, sub_api.SubmissionRequestError) as ex:
        msg = (
            u"An error occurred while retrieving the "
            u"submission with UUID {uuid}: {ex}"
        ).format(uuid=submission_uuid, ex=ex)
        raise AIGradingRequestError(msg)
    except InvalidRubric as ex:
        msg = (
            u"An error occurred while parsing the serialized "
            u"rubric {rubric}: {ex}"
        ).format(rubric=rubric, ex=ex)
        raise AIGradingRequestError(msg)
    except (sub_api.SubmissionInternalError, DatabaseError) as ex:
        msg = (
            u"An unexpected error occurred while submitting an "
            u"essay for AI grading: {ex}"
        ).format(ex=ex)
        logger.exception(msg)
        raise AIGradingInternalError(msg)

    try:
        classifier_set_candidates = AIClassifierSet.objects.filter(
            rubric=workflow.rubric, algorithm_id=algorithm_id
        ).order_by('-created_at')[:1]

        # If we find classifiers for this rubric/algorithm
        # then associate the classifiers with the workflow
        # and schedule a grading task.
        # Otherwise, the task will need to be scheduled later,
        # once the classifiers have been trained.
        if len(classifier_set_candidates) > 0:
            workflow.classifier_set = classifier_set_candidates[0]
            workflow.save()
            grading_tasks.grade_essay.apply_async(args=[workflow.uuid])
            logger.info((
                u"Scheduled grading task for AI grading workflow with UUID {workflow_uuid} "
                u"(submission UUID = {sub_uuid}, algorithm ID = {algorithm_id})"
            ).format(workflow_uuid=workflow.uuid, sub_uuid=submission_uuid, algorithm_id=algorithm_id))
        else:
            logger.info((
                u"Cannot schedule a grading task for AI grading workflow with UUID {workflow_uuid} "
                u"because no classifiers are available for the rubric associated with submission {sub_uuid} "
                u"for the algorithm {algorithm_id}"
            ).format(workflow_uuid=workflow.uuid, sub_uuid=submission_uuid, algorithm_id=algorithm_id))
        return workflow.uuid
    except Exception as ex:
        msg = (
            u"An unexpected error occurred while scheduling the "
            u"AI grading task for the submission with UUID {uuid}: {ex}"
        ).format(uuid=submission_uuid, ex=ex)
        raise AIGradingInternalError(msg)


def get_latest_assessment(submission_uuid):
    """
    Retrieve the latest AI assessment for a submission.

    Args:
        submission_uuid (str): The UUID of the submission being assessed.

    Returns:
        dict: The serialized assessment model
        or None if no assessments are available

    Raises:
        AIGradingInternalError

    """
    try:
        assessments = Assessment.objects.filter(
            submission_uuid=submission_uuid,
            score_type=AI_ASSESSMENT_TYPE,
        )[:1]
    except DatabaseError as ex:
        msg = (
            u"An error occurred while retrieving AI graded assessments "
            u"for the submission with UUID {uuid}: {ex}"
        ).format(uuid=submission_uuid, ex=ex)
        logger.exception(msg)
        raise AIGradingInternalError(msg)

    if len(assessments) > 0:
        return full_assessment_dict(assessments[0])
    else:
        return None


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
    except NoTrainingExamples as ex:
        raise AITrainingRequestError(ex)
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
        logger.info((
            u"Scheduled training task for the AI training workflow with UUID {workflow_uuid} "
            u"(algorithm ID = {algorithm_id})"
        ).format(workflow_uuid=workflow.uuid, algorithm_id=algorithm_id))
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
