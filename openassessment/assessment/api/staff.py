"""
Public interface for staff grading, used by students/course staff.
"""


import logging

from django.db import DatabaseError, transaction
from django.utils.timezone import now

from submissions import api as submissions_api

from openassessment.assessment.errors import StaffAssessmentInternalError, StaffAssessmentRequestError
from openassessment.assessment.models import Assessment, AssessmentPart, InvalidRubricSelection, StaffWorkflow
from openassessment.assessment.serializers import InvalidRubric, full_assessment_dict, rubric_from_dict
from openassessment.assessment.score_type_constants import STAFF_TYPE


logger = logging.getLogger("openassessment.assessment.api.staff")  # pylint: disable=invalid-name


def submitter_is_finished(submission_uuid, staff_requirements):  # pylint: disable=unused-argument
    """
    Determine if the submitter has finished their requirements for staff
    assessment. Always returns True.

    Args:
        submission_uuid (str): Not used.
        staff_requirements (dict): Not used.

    Returns:
        True

    """
    return True


def assessment_is_finished(submission_uuid, staff_requirements):
    """
    Determine if the staff assessment step of the given submission is completed.
    This checks to see if staff have completed the assessment.

    Args:
        submission_uuid (str): The UUID of the submission being graded.
        staff_requirements (dict): Any variables that may effect this state.

    Returns:
        True if a staff assessment has been completed for this submission or if not required.
    """
    # Requirements of None means we can't make any assumptions about the done-ness of this step
    if staff_requirements is None:
        return False

    if staff_requirements.get('required', False):
        return bool(get_latest_staff_assessment(submission_uuid))

    return True


def on_init(submission_uuid):
    """
    Create a new staff workflow for a student item and submission.

    Creates a unique staff workflow for a student item, associated with a
    submission.

    Note that the staff workflow begins things in on_init() instead of
    on_start(), because staff shoud be able to access the submission
    regardless of which state the workflow is currently in.

    Args:
        submission_uuid (str): The submission associated with this workflow.

    Returns:
        None

    Raises:
        StaffAssessmentInternalError: Raised when there is an internal error
            creating the Workflow.

    """
    try:
        submission = submissions_api.get_submission_and_student(submission_uuid)
        StaffWorkflow.objects.get_or_create(
            course_id=submission['student_item']['course_id'],
            item_id=submission['student_item']['item_id'],
            submission_uuid=submission_uuid
        )
    except DatabaseError as ex:
        error_message = (
            "An internal error occurred while creating a new staff "
            "workflow for submission {}"
            .format(submission_uuid)
        )
        logger.exception(error_message)
        raise StaffAssessmentInternalError(error_message) from ex


def on_cancel(submission_uuid):
    """
    Cancel the staff workflow for submission.

    Sets the cancelled_at field in staff workflow.

    Args:
        submission_uuid (str): The submission UUID associated with this workflow.

    Returns:
        None

    """
    try:
        workflow = StaffWorkflow.objects.get(submission_uuid=submission_uuid)
        workflow.cancelled_at = now()
        workflow.save(update_fields=['cancelled_at'])
    except StaffWorkflow.DoesNotExist:
        # If we can't find a workflow, then we don't have to do anything to
        # cancel it.
        pass
    except DatabaseError as ex:
        error_message = (
            "An internal error occurred while cancelling the staff"
            "workflow for submission {}"
            .format(submission_uuid)
        )
        logger.exception(error_message)
        raise StaffAssessmentInternalError(error_message) from ex


def get_score(submission_uuid, staff_requirements):  # pylint: disable=unused-argument
    """
    Generate a score based on a completed assessment for the given submission.
    If no assessment has been completed for this submission, this will return
    None.

    Args:
        submission_uuid (str): The UUID for the submission to get a score for.
        staff_requirements (dict): Not used.

    Returns:
        A dictionary with the points earned, points possible,
        contributing_assessments, and staff_id information.

    """
    assessment = get_latest_staff_assessment(submission_uuid)
    if not assessment:
        return None

    return {
        "points_earned": assessment["points_earned"],
        "points_possible": assessment["points_possible"],
        "contributing_assessments": [assessment["id"]],
        "staff_id": assessment["scorer_id"],
    }


def get_latest_staff_assessment(submission_uuid):
    """
    Retrieve the latest staff assessment for a submission.

    Args:
        submission_uuid (str): The UUID of the submission being assessed.

    Returns:
        dict: The serialized assessment model
        or None if no assessments are available

    Raises:
        StaffAssessmentInternalError if there are problems connecting to the database.

    Example usage:

    >>> get_latest_staff_assessment('10df7db776686822e501b05f452dc1e4b9141fe5')
    {
        'points_earned': 6,
        'points_possible': 12,
        'scored_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 649284 tzinfo=<UTC>),
        'scorer': u"staff",
        'feedback': u''
    }

    """
    try:
        assessments = Assessment.objects.filter(
            submission_uuid=submission_uuid,
            score_type=STAFF_TYPE,
        )[:1]
    except DatabaseError as ex:
        msg = (
            "An error occurred while retrieving staff assessments "
            "for the submission with UUID {uuid}: {ex}"
        ).format(uuid=submission_uuid, ex=ex)
        logger.exception(msg)
        raise StaffAssessmentInternalError(msg) from ex

    if assessments:
        return full_assessment_dict(assessments[0])

    return None


def get_assessment_scores_by_criteria(submission_uuid):
    """Get the staff score for each rubric criterion

    Args:
        submission_uuid (str): The submission uuid is used to get the
            assessment used to score this submission.

    Returns:
        (dict): A dictionary of rubric criterion names, with a score of
            the staff assessments.

    Raises:
        StaffAssessmentInternalError: If any error occurs while retrieving
            information from the scores, an error is raised.
    """
    try:
        # This will always create a list of length 1
        assessments = list(
            Assessment.objects.filter(
                score_type=STAFF_TYPE, submission_uuid=submission_uuid
            )[:1]
        )
        scores = Assessment.scores_by_criterion(assessments)
        # Since this is only being sent one score, the median score will be the
        # same as the only score.
        return Assessment.get_median_score_dict(scores)
    except DatabaseError as ex:
        error_message = "Error getting staff assessment scores for {}".format(submission_uuid)
        logger.exception(error_message)
        raise StaffAssessmentInternalError(error_message) from ex


def get_submission_to_assess(course_id, item_id, scorer_id):
    """
    Get a submission for staff evaluation.

    Retrieves a submission for assessment for the given staff member.

    Args:
        course_id (str): The course that we would like to fetch submissions from.
        item_id (str): The student_item (problem) that we would like to retrieve submissions for.
        scorer_id (str): The user id of the staff member scoring this submission

    Returns:
        dict: A student submission for assessment. This contains a 'student_item',
            'attempt_number', 'submitted_at', 'created_at', and 'answer' field to be
            used for assessment.

    Raises:
        StaffAssessmentInternalError: Raised when there is an internal error
            retrieving staff workflow information.

    Examples:
        >>> get_submission_to_assess("a_course_id", "an_item_id", "a_scorer_id")
        {
            'student_item': 2,
            'attempt_number': 1,
            'submitted_at': datetime.datetime(2014, 1, 29, 23, 14, 52, 649284, tzinfo=<UTC>),
            'created_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 668850, tzinfo=<UTC>),
            'answer': { ... }
        }

    """
    student_submission_uuid = StaffWorkflow.get_submission_for_review(course_id, item_id, scorer_id)
    if student_submission_uuid:
        try:
            submission_data = submissions_api.get_submission(student_submission_uuid)
            return submission_data
        except submissions_api.SubmissionNotFoundError as ex:
            error_message = (
                "Could not find a submission with the uuid {}"
            ).format(student_submission_uuid)
            logger.exception(error_message)
            raise StaffAssessmentInternalError(error_message) from ex
    else:
        logger.info("No submission found for staff to assess (%s, %s)", course_id, item_id)
        return None


def get_staff_grading_statistics(course_id, item_id):
    """
    Returns the number of graded, ungraded, and in-progress submissions for staff grading.

    Args:
        course_id (str): The course that this problem belongs to
        item_id (str): The student_item (problem) that we want to know statistics about.

    Returns:
        dict: a dictionary that contains the following keys: 'graded', 'ungraded', and 'in-progress'
    """
    return StaffWorkflow.get_workflow_statistics(course_id, item_id)


def create_assessment(
        submission_uuid,
        scorer_id,
        options_selected,
        criterion_feedback,
        overall_feedback,
        rubric_dict,
        scored_at=None
):
    # pylint: disable=unicode-format-string
    """
    Creates an assessment on the given submission.

    Assessments are created based on feedback associated with a particular
    rubric.

    Assumes that the user creating the assessment has the permissions to do so.

    Args:
        submission_uuid (str): The submission uuid for the submission being
            assessed.
        scorer_id (str): The user ID for the user giving this assessment. This
            is required to create an assessment on a submission.
        options_selected (dict): Dictionary mapping criterion names to the
            option names the user selected for that criterion.
        criterion_feedback (dict): Dictionary mapping criterion names to the
            free-form text feedback the user gave for the criterion.
            Since criterion feedback is optional, some criteria may not appear
            in the dictionary.
        overall_feedback (unicode): Free-form text feedback on the submission overall.
        rubric_dict (dict): The rubric model associated with this assessment
        scored_at (datetime): Optional argument to override the time in which
            the assessment took place. If not specified, scored_at is set to
            now.

    Keyword Args:
        scored_at (datetime): Optional argument to override the time in which
            the assessment took place. If not specified, scored_at is set to
            now.

    Returns:
        dict: the Assessment model, serialized as a dict.

    Raises:
        StaffAssessmentRequestError: Raised when the submission_id is invalid, or
            the assessment_dict does not contain the required values to create
            an assessment.
        StaffAssessmentInternalError: Raised when there is an internal error
            while creating a new assessment.

    Examples:
        >>> options_selected = {"clarity": "Very clear", "precision": "Somewhat precise"}
        >>> criterion_feedback = {"clarity": "I thought this essay was very clear."}
        >>> feedback = "Your submission was thrilling."
        >>> create_assessment("Tim", options_selected, criterion_feedback, feedback, rubric_dict)
    """
    try:
        try:
            scorer_workflow = StaffWorkflow.objects.get(submission_uuid=submission_uuid)
        except StaffWorkflow.DoesNotExist:
            scorer_workflow = None

        assessment = _complete_assessment(
            submission_uuid,
            scorer_id,
            options_selected,
            criterion_feedback,
            overall_feedback,
            rubric_dict,
            scored_at,
            scorer_workflow
        )
        return full_assessment_dict(assessment)

    except InvalidRubric as ex:
        error_message = "The rubric definition is not valid."
        logger.exception(error_message)
        raise StaffAssessmentRequestError(error_message) from ex
    except InvalidRubricSelection as ex:
        error_message = "Invalid options were selected in the rubric."
        logger.warning(error_message, exc_info=True)
        raise StaffAssessmentRequestError(error_message) from ex
    except DatabaseError as ex:
        error_message = (
            "An error occurred while creating an assessment by the scorer with this ID: {}"
        ).format(scorer_id)
        logger.exception(error_message)
        raise StaffAssessmentInternalError(error_message) from ex


@transaction.atomic
def _complete_assessment(
        submission_uuid,
        scorer_id,
        options_selected,
        criterion_feedback,
        overall_feedback,
        rubric_dict,
        scored_at,
        scorer_workflow
):
    """
    Internal function for atomic assessment creation. Creates a staff assessment
    in a single transaction.

    Args:
        submission_uuid (str): The submission uuid for the submission being
            assessed.
        scorer_id (str): The user ID for the user giving this assessment. This
            is required to create an assessment on a submission.
        options_selected (dict): Dictionary mapping criterion names to the
            option names the user selected for that criterion.
        criterion_feedback (dict): Dictionary mapping criterion names to the
            free-form text feedback the user gave for the criterion.
            Since criterion feedback is optional, some criteria may not appear
            in the dictionary.
        overall_feedback (unicode): Free-form text feedback on the submission overall.
        rubric_dict (dict): The rubric model associated with this assessment
        scored_at (datetime): Optional argument to override the time in which
            the assessment took place. If not specified, scored_at is set to
            now.

    Returns:
        The Assessment model

    """
    # Get or create the rubric
    rubric = rubric_from_dict(rubric_dict)

    # Create the staff assessment
    assessment = Assessment.create(
        rubric,
        scorer_id,
        submission_uuid,
        STAFF_TYPE,
        scored_at=scored_at,
        feedback=overall_feedback
    )

    # Create assessment parts for each criterion in the rubric
    # This will raise an `InvalidRubricSelection` if the selected options do not
    # match the rubric.
    AssessmentPart.create_from_option_names(assessment, options_selected, feedback=criterion_feedback)

    # Close the active assessment
    if scorer_workflow is not None:
        scorer_workflow.close_active_assessment(assessment, scorer_id)
    return assessment


def bulk_retrieve_workflow_status(course_id, item_id, submission_uuids=None):
    """
    Passthrough method to retrieve bulk states for staff workflows.

    Note that the staff workflow begins things in on_init() instead of
    on_start(), because staff shoud be able to access the submission
    regardless of which state the workflow is currently in.

    Args:
        course_id (str): The course that this problem belongs to.
        item_id (str): The student_item (problem) that we want to retrieve information about.
        submission_uuids list(str): List of submission UUIDs to retrieve status for.

    Returns:
        dict: a dictionary with the submission uuids as keys and their statuses as values.
    """
    return StaffWorkflow.bulk_retrieve_workflow_status(
        course_id, item_id, submission_uuids
    )
