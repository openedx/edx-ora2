"""
Public interface for AI training and grading, used by students/course authors.
"""
import logging
from django.db import DatabaseError
from submissions import api as sub_api
from openassessment.assessment.serializers import (
    deserialize_training_examples, InvalidTrainingExample, InvalidRubric, full_assessment_dict
)
from openassessment.assessment.errors import (
    AITrainingRequestError, AITrainingInternalError,
    AIGradingRequestError, AIGradingInternalError, AIError
)
from openassessment.assessment.models import (
    Assessment, AITrainingWorkflow, AIGradingWorkflow,
    InvalidOptionSelection, NoTrainingExamples,
    AI_ASSESSMENT_TYPE
)
from openassessment.assessment.worker import training as training_tasks
from openassessment.assessment.worker import grading as grading_tasks


logger = logging.getLogger(__name__)


def submitter_is_finished(submission_uuid, requirements):
    """
    Determine if the submitter has finished their requirements for Example
    Based Assessment. Always returns True.

    Args:
        submission_uuid (str): Not used.
        requirements (dict): Not used.

    Returns:
        True

    """
    return True


def assessment_is_finished(submission_uuid, requirements):
    """
    Determine if the assessment of the given submission is completed. This
    checks to see if the AI has completed the assessment.

    Args:
        submission_uuid (str): The UUID of the submission being graded.
        requirements (dict): Not used.

    Returns:
        True if the assessment has been completed for this submission.

    """
    return bool(get_latest_assessment(submission_uuid))


def get_score(submission_uuid, requirements):
    """
    Generate a score based on a completed assessment for the given submission.
    If no assessment has been completed for this submission, this will return
    None.

    Args:
        submission_uuid (str): The UUID for the submission to get a score for.
        requirements (dict): Not used.

    Returns:
        A dictionary with the points earned and points possible.

    """
    assessment = get_latest_assessment(submission_uuid)
    if not assessment:
        return None

    return {
        "points_earned": assessment["points_earned"],
        "points_possible": assessment["points_possible"]
    }


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

    Example usage:
    >>> submit('74a9d63e8a5fea369fd391d07befbd86ae4dc6e2', rubric, 'ease')
    '10df7db776686822e501b05f452dc1e4b9141fe5'

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
        # Schedule the grading task only if the workflow has a classifier set
        if workflow.classifier_set is not None:
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

    Examle usage:
    >>> get_latest_assessment('10df7db776686822e501b05f452dc1e4b9141fe5')
    {
        'points_earned': 6,
        'points_possible': 12,
        'scored_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 649284 tzinfo=<UTC>),
        'scorer': u"ease",
        'feedback': u''
    }

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


def get_assessment_scores_by_criteria(submission_uuid):
    """Get the score for each rubric criterion

    Args:
        submission_uuid (str): The submission uuid is used to get the
            assessment used to score this submission.

    Returns:
        (dict): A dictionary of rubric criterion names, with a score of
            the example based assessments.

    Raises:
        AIGradingInternalError: If any error occurs while retrieving
            information from the scores, an error is raised.
    """
    try:
        assessments = list(
            Assessment.objects.filter(
                score_type=AI_ASSESSMENT_TYPE, submission_uuid=submission_uuid
            ).order_by('-scored_at')[:1]
        )
        scores = Assessment.scores_by_criterion(assessments)
        return Assessment.get_median_score_dict(scores)
    except DatabaseError:
        error_message = u"Error getting example-based assessment scores for {}".format(submission_uuid)
        logger.exception(error_message)
        raise AIGradingInternalError(error_message)


def train_classifiers(rubric_dict, examples, course_id, item_id, algorithm_id):
    """
    Schedule a task to train classifiers.
    All training examples must match the rubric!
    After training of classifiers completes successfully, all AIGradingWorkflows that are incomplete will be
    automatically rescheduled to complete.

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
        AIGradingInternalError

    Example usage:
    >>> train_classifiers(rubric, examples, 'ease')
    '10df7db776686822e501b05f452dc1e4b9141fe5'

    """
    # Get or create the rubric and training examples
    try:
        examples = deserialize_training_examples(examples, rubric_dict)
    except (InvalidRubric, InvalidTrainingExample, InvalidOptionSelection) as ex:
        msg = u"Could not parse rubric and/or training examples: {ex}".format(ex=ex)
        raise AITrainingRequestError(msg)

    # Create the workflow model
    try:
        workflow = AITrainingWorkflow.start_workflow(examples, course_id, item_id, algorithm_id)
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
    except (AITrainingInternalError, AITrainingRequestError):
        msg = (
            u"An unexpected error occurred while scheduling "
            u"the task for training workflow with UUID {}"
        ).format(workflow.uuid)
        logger.exception(msg)
        raise AITrainingInternalError(msg)
    except AIGradingInternalError:
        # If we have an error that is coming from the rescheduled grading after successful completion:
        msg = (
            u"An unexpected error occurred while scheduling incomplete grading workflows after "
            u"the training task was completed successfully. The course_id and item_id for the failed "
            u"grading workflows are course_id={cid}, item_id={iid}."
        ).format(cid=course_id, iid=item_id)
        logger.exception(msg)
        raise AIGradingInternalError(msg)

    # Return the workflow UUID
    return workflow.uuid


def reschedule_unfinished_tasks(course_id=None, item_id=None, task_type=u"grade"):
    """
    Check for unfinished tasks (both grading and training) and reschedule them.
    Optionally restrict by course/item ID and task type. Default use case is to
    only reschedule the unfinished grade tasks. Applied use case (with button in
    staff mixin) is to call without argument, and to reschedule grades only.

    Kwargs:
        course_id (unicode): Restrict to unfinished tasks in a particular course.
        item_id (unicode): Restrict to unfinished tasks for a particular item in a course.
            NOTE: if you specify the item ID, you must also specify the course ID.
        task_type (unicode): Either "grade" or "train".  Restrict to unfinished tasks of this type.
            if task_type is specified as None, both training and grading will be rescheduled, in that order.

    Raises:
        AIGradingInternalError
        AITrainingInternalError
        AIError
    """

    if course_id is None or item_id is None:
        msg = u"Rescheduling tasks was not possible because the course_id / item_id was not assigned."
        logger.exception(msg)
        raise AIError

    # Reschedules all of the training tasks
    if task_type == u"train" or task_type is None:
        try:
            training_tasks.reschedule_training_tasks.apply_async(args=[course_id, item_id])
        except Exception as ex:
            msg = (
                u"Rescheduling training tasks for course {cid} and item {iid} failed with exception: {ex}"
            ).format(cid=course_id, iid=item_id, ex=ex)
            logger.exception(msg)
            raise AITrainingInternalError(ex)

    # Reschedules all of the grading tasks
    if task_type == u"grade" or task_type is None:
        try:
            grading_tasks.reschedule_grading_tasks.apply_async(args=[course_id, item_id])
        except Exception as ex:
            msg = (
                u"Rescheduling grading tasks for course {cid} and item {iid} failed with exception: {ex}"
            ).format(cid=course_id, iid=item_id, ex=ex)
            logger.exception(msg)
            raise AIGradingInternalError(ex)
