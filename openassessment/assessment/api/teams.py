"""
Public interface for staff grading of team assignments, used by students/course staff.
"""


import logging

from django.db import DatabaseError
from django.utils.timezone import now

from submissions import team_api as team_submissions_api

from openassessment.assessment.api.staff import _complete_assessment
from openassessment.assessment.errors import StaffAssessmentInternalError, StaffAssessmentRequestError
from openassessment.assessment.models import Assessment, TeamStaffWorkflow, InvalidRubricSelection
from openassessment.assessment.serializers import InvalidRubric, full_assessment_dict
from openassessment.assessment.score_type_constants import STAFF_TYPE

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def submitter_is_finished(team_submission_uuid, team_requirements):  # pylint: disable=unused-argument
    """
    Determine if the submitter has finished their requirements for staff
    assessment. Always returns True.

    Args:
        team_submission_uuid (str): Not used.
        team_requirements (dict): Not used.

    Returns:
        True

    """
    return True


def assessment_is_finished(team_submission_uuid, staff_requirements, _):
    """
    Determine if the staff assessment step of the given team submission is completed.
    This checks to see if staff have completed the assessment.

    Args:
        team_submission_uuid (str): The UUID of the submission being graded.
        staff_requirements (dict): Any variables that may effect this state.

    Returns:
        True if a staff assessment has been completed for this team submission or if not required.
    """
    # Requirements of None means we can't make any assumptions about the done-ness of this step
    if staff_requirements is None:
        return False

    if staff_requirements.get('required', False):
        return bool(get_latest_staff_assessment(team_submission_uuid))

    return True


def on_init(team_submission_uuid):
    """
    Create a new team staff workflow for a student item and submission.

    Creates a unique team staff workflow for a student item, associated with a
    team submission.

    Note that the staff workflow begins things in on_init() instead of
    on_start(), because staff shoud be able to access the submission
    regardless of which state the workflow is currently in.

    Args:
        team_submission_uuid (str): The team submission associated with this workflow.

    Returns:
        None

    Raises:
        StaffAssessmentInternalError: Raised when there is an internal error
            creating the Workflow.
    """
    try:
        team_submission = team_submissions_api.get_team_submission(team_submission_uuid)
        TeamStaffWorkflow.objects.get_or_create(
            course_id=team_submission['course_id'],
            item_id=team_submission['item_id'],
            team_submission_uuid=team_submission_uuid,
            # submission_uuid is currently not used in any logic in TeamStaffWorkflow, so we don't
            # realy care which submission is chosen and it doesn't need to match the TeamAssessment Workflow.
            # It must be filled because of the unique constraint on the field (can't have multiple '' values)
            submission_uuid=team_submission['submission_uuids'][0],
        )
    except DatabaseError as ex:
        error_message = (
            "An internal error occurred while creating a new team staff workflow for team submission {}"
        ).format(team_submission_uuid)
        logger.exception(error_message)
        raise StaffAssessmentInternalError(error_message) from ex


def on_cancel(team_submission_uuid):
    """
    Cancel the team staff workflow for submission.

    Sets the cancelled_at field in team staff workflow.

    Args:
        team_submission_uuid (str): The team_submission UUID associated with this workflow.

    Returns:
        None

    """
    try:
        workflow = TeamStaffWorkflow.objects.get(team_submission_uuid=team_submission_uuid)
        workflow.cancelled_at = now()
        workflow.save(update_fields=['cancelled_at'])
    except TeamStaffWorkflow.DoesNotExist:
        # If we can't find a workflow, then we don't have to do anything to
        # cancel it.
        pass
    except DatabaseError as ex:
        error_message = (
            "An internal error occurred while cancelling the team staff workflow for submission {}"
        ).format(team_submission_uuid)
        logger.exception(error_message)
        raise StaffAssessmentInternalError(error_message) from ex


def get_score(team_submission_uuid, staff_requirements, course_settings):  # pylint: disable=unused-argument
    """
    Generate a score based on a completed assessment for the given team submission.
    If no assessment has been completed for this submission, this will return
    None.

    Args:
        team_submission_uuid (str): The UUID for the submission to get a score for.
        staff_requirements (dict): Not used.
        course_settings (dict): Not used.

    Returns:
        A dictionary with the points earned, points possible,
        contributing_assessments, and staff_id information.

    """
    assessment = get_latest_staff_assessment(team_submission_uuid)
    if not assessment:
        return None

    return {
        "points_earned": assessment["points_earned"],
        "points_possible": assessment["points_possible"],
        "contributing_assessments": [assessment["id"]],
        "staff_id": assessment["scorer_id"],
    }


def get_latest_staff_assessment(team_submission_uuid):
    """
    Retrieve the latest staff assessment for a team submission.

    Args:
        team_submission_uuid (str): The UUID of the team submission being assessed.

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
        'scorer': "staff",
        'feedback': ''
    }

    """
    try:
        # Get the reference submissions
        team_submission = team_submissions_api.get_team_submission(team_submission_uuid)

        # Return the most-recently graded assessment for any team member's submisison
        assessment = Assessment.objects.filter(
            submission_uuid__in=team_submission['submission_uuids'],
            score_type=STAFF_TYPE,
        ).first()
    except DatabaseError as ex:
        msg = (
            "An error occurred while retrieving staff assessments "
            "for the submission with UUID {uuid}: {ex}"
        ).format(uuid=team_submission_uuid, ex=ex)
        logger.exception(msg)
        raise StaffAssessmentInternalError(msg) from ex

    if assessment:
        return full_assessment_dict(assessment)

    return None


def get_assessment_scores_by_criteria(team_submission_uuid):
    """Get the staff score for each rubric criterion

    Args:
        team_submission_uuid (str): The team submission uuid is used to get the
            assessment used to score this submission.

    Returns:
        (dict): A dictionary of rubric criterion names, with a score of
            the staff assessments.

    Raises:
        StaffAssessmentInternalError: If any error occurs while retrieving
            information from the scores, an error is raised.
    """
    try:
        # Get most recently graded assessment for a team submission
        team_submission = team_submissions_api.get_team_submission(team_submission_uuid)
        assessments = list(
            Assessment.objects.filter(
                submission_uuid__in=team_submission['submission_uuids'],
                score_type=STAFF_TYPE,
            )[:1]
        )

        scores = Assessment.scores_by_criterion(assessments)
        # Since this is only being sent one score, the median score will be the
        # same as the only score.
        return Assessment.get_median_score_dict(scores)
    except DatabaseError as ex:
        error_message = f"Error getting staff assessment scores for {team_submission_uuid}"
        logger.exception(error_message)
        raise StaffAssessmentInternalError(error_message) from ex


def get_submission_to_assess(course_id, item_id, scorer_id):
    """
    Get a team submission for staff evaluation.

    Retrieves a team submission for assessment for the given staff member.

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
    team_submission_uuid = TeamStaffWorkflow.get_submission_for_review(course_id, item_id, scorer_id)
    if team_submission_uuid:
        try:
            submission_data = team_submissions_api.get_team_submission(team_submission_uuid)
            return submission_data
        except DatabaseError as ex:
            error_message = (
                "Could not find a team submission with the uuid {}"
            ).format(team_submission_uuid)
            logger.exception(error_message)
            raise StaffAssessmentInternalError(error_message) from ex
    else:
        logger.info("No team submission found for staff to assess (%s, %s)", course_id, item_id)
        return None


def get_staff_grading_statistics(course_id, item_id):
    """
    Returns the number of graded, ungraded, and in-progress team submissions for staff grading.

    Args:
        course_id (str): The course that this problem belongs to
        item_id (str): The student_item (problem) that we want to know statistics about.

    Returns:
        dict: a dictionary that contains the following keys: 'graded', 'ungraded', and 'in-progress'
    """
    return TeamStaffWorkflow.get_workflow_statistics(course_id, item_id)


def create_assessment(
        team_submission_uuid,
        scorer_id,
        options_selected,
        criterion_feedback,
        overall_feedback,
        rubric_dict,
        scored_at=None
):
    """
    Creates an assessment for each member of the submitting team.

    Closely mirrors openassessment.assessment.api.staff.py::create_assessment

    Can use _complete_assessment from Staff API as is, but has the side-effect
    of only associating the last graded assessment with the workflow

    Returns:
        dict: the Assessment model, serialized as a dict.
    """
    try:
        try:
            scorer_workflow = TeamStaffWorkflow.objects.get(team_submission_uuid=team_submission_uuid)
        except TeamStaffWorkflow.DoesNotExist:
            scorer_workflow = None

        # Get the submissions for a team
        team_submission = team_submissions_api.get_team_submission(team_submission_uuid)

        assessment_dicts = []
        for submission_uuid in team_submission['submission_uuids']:
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
            assessment_dicts.append(full_assessment_dict(assessment))

        return assessment_dicts

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
