"""
Shared funcitons/logic for staff and team API
"""
from __future__ import absolute_import

import logging

from django.db import DatabaseError, transaction
from django.utils.timezone import now

from openassessment.assessment.errors import StaffAssessmentInternalError
from openassessment.assessment.models import Assessment, AssessmentPart, InvalidRubricSelection, StaffWorkflow
from openassessment.assessment.serializers import InvalidRubric, full_assessment_dict, rubric_from_dict


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

STAFF_TYPE = "ST"


def cancel_workflow(uuid, workflow_model=StaffWorkflow):
    """
    Cancel the workflow for submission.

    Sets the cancelled_at field in team staff workflow.

    Args:
        uuid (str): The UUID associated with this workflow.

    Returns:
        None

    """
    try:
        workflow = workflow_model.get_by_identifying_uuid(uuid)
        workflow.cancelled_at = now()
        workflow.save(update_fields=['cancelled_at'])
    except workflow_model.DoesNotExist:
        # If we can't find a workflow, then we don't have to do anything to cancel it
        pass
    except DatabaseError:
        error_message = (
            "An internal error occurred while cancelling the team/staff workflow for submission {}"
        ).format(uuid)
        logger.exception(error_message)
        raise StaffAssessmentInternalError(error_message)


def get_latest_staff_assessment(submission_uuids):
    """
    Retrieve the latest staff assessment for a submission.

    Args:
        submission_uuids (Array(str)): The UUIDs of the submissions being assessed.

    Returns:
        dict: The serialized assessment model
        or None if no assessments are available

    Raises:
        StaffAssessmentInternalError if there are problems connecting to the database.

    Example usage:

    >>> get_latest_staff_assessment(['10df7db776686822e501b05f452dc1e4b9141fe5'])
    {
        'points_earned': 6,
        'points_possible': 12,
        'scored_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 649284 tzinfo=<UTC>),
        'scorer': "staff",
        'feedback': ''
    }

    """
    try:
        # Return the most-recently graded assessment for any submisison
        assessment = Assessment.objects.filter(
            submission_uuid__in=submission_uuids,
            score_type=STAFF_TYPE,
        ).first()
    except DatabaseError as ex:
        msg = (
            "An error occurred while retrieving staff assessments "
            "for the submission with UUID {uuids}: {ex}"
        ).format(uuids=submission_uuids, ex=ex)
        logger.exception(msg)
        raise StaffAssessmentInternalError(msg)

    return assessment


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
