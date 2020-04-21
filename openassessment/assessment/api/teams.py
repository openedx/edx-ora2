"""
Public interface for staff grading of team assignments, used by students/course staff.
"""
from __future__ import absolute_import

import logging

from django.db import DatabaseError
from django.utils.timezone import now

from openassessment.assessment.api.staff import _complete_assessment
from openassessment.assessment.errors import StaffAssessmentInternalError, StaffAssessmentRequestError
from openassessment.assessment.models import Assessment, TeamStaffWorkflow, InvalidRubricSelection
from openassessment.assessment.serializers import InvalidRubric, full_assessment_dict


from submissions import (
    api as submissions_api,
    team_api as team_submissions_api
)

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

STAFF_TYPE = "ST"


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
            team_submission_uuid=team_submission_uuid
        )
    except DatabaseError:
        error_message = (
            "An internal error occurred while creating a new team staff workflow for team submission {}"
        ).format(team_submission_uuid)
        logger.exception(error_message)
        raise StaffAssessmentInternalError(error_message)


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
    except DatabaseError:
        error_message = (
            "An internal error occurred while cancelling the team staff workflow for submission {}"
        ).format(team_submission_uuid)
        logger.exception(error_message)
        raise StaffAssessmentInternalError(error_message)


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
        # Get the reference submission from a team submission
        team_workflow = TeamStaffWorkflow.objects.filter(
            team_submission_uuid=team_submission_uuid
        ).first()

        if not team_workflow:
            return None

        submission_uuid = team_workflow.submission_uuid

        assessment = Assessment.objects.filter(
            submission_uuid=submission_uuid,
            score_type=STAFF_TYPE,
        ).first()
    except DatabaseError as ex:
        msg = (
            "An error occurred while retrieving staff assessments "
            "for the submission with UUID {uuid}: {ex}"
        ).format(uuid=submission_uuid, ex=ex)
        logger.exception(msg)
        raise StaffAssessmentInternalError(msg)

    if assessment:
        return full_assessment_dict(assessment)

    return None


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

    except InvalidRubric:
        error_message = "The rubric definition is not valid."
        logger.exception(error_message)
        raise StaffAssessmentRequestError(error_message)
    except InvalidRubricSelection:
        error_message = "Invalid options were selected in the rubric."
        logger.warning(error_message, exc_info=True)
        raise StaffAssessmentRequestError(error_message)
    except DatabaseError:
        error_message = (
            "An error occurred while creating an assessment by the scorer with this ID: {}"
        ).format(scorer_id)
        logger.exception(error_message)
        raise StaffAssessmentInternalError(error_message)
