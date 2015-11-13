"""
Public interface for staff grading, used by students/course staff.
"""
import logging
from django.db import DatabaseError, IntegrityError, transaction
from dogapi import dog_stats_api

from openassessment.assessment.models import (
    Assessment, AssessmentFeedback, AssessmentPart,
    InvalidRubricSelection
)
from openassessment.assessment.serializers import (
    AssessmentFeedbackSerializer, RubricSerializer,
    full_assessment_dict, rubric_from_dict, serialize_assessments,
    InvalidRubric
)
from openassessment.assessment.errors import (
    StaffAssessmentRequestError, StaffAssessmentInternalError
)
from submissions import api as sub_api

logger = logging.getLogger("openassessment.assessment.api.peer")


STAFF_TYPE = "ST"


def submitter_is_finished(submission_uuid, requirements):
    """
    Determine if the submitter has finished their requirements for staff
    assessment. Always returns True.

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
    checks to see if staff have completed the assessment.

    Args:
        submission_uuid (str): The UUID of the submission being graded.
        requirements (dict): Any variables that may effect this state.

    Returns:
        True if the assessment has been completed for this submission.

    """
    required = requirements.get('staff', {}).get('required', False)
    if required:
        return bool(get_latest_assessment(submission_uuid))
    return True


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


def get_latest_assessment(submission_uuid):
    """
    Retrieve the latest staff assessment for a submission.

    Args:
        submission_uuid (str): The UUID of the submission being assessed.

    Returns:
        dict: The serialized assessment model
        or None if no assessments are available

    Raises:
        StaffAssessmentInternalError

    Example usage:

    >>> get_latest_assessment('10df7db776686822e501b05f452dc1e4b9141fe5')
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
            u"An error occurred while retrieving staff assessments "
            u"for the submission with UUID {uuid}: {ex}"
        ).format(uuid=submission_uuid, ex=ex)
        logger.exception(msg)
        raise StaffAssessmentInternalError(msg)

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
            the staff assessments.

    Raises:
        StaffAssessmentInternalError: If any error occurs while retrieving
            information from the scores, an error is raised.
    """
    try:
        assessments = list(
            Assessment.objects.filter(
                score_type=STAFF_TYPE, submission_uuid=submission_uuid
            )[:1]
        )
        scores = Assessment.scores_by_criterion(assessments)
        return Assessment.get_median_score_dict(scores)
    except DatabaseError:
        error_message = u"Error getting staff assessment scores for {}".format(submission_uuid)
        logger.exception(error_message)
        raise StaffAssessmentInternalError(error_message)


def create_assessment(
    submission_uuid,
    scorer_id,
    options_selected,
    criterion_feedback,
    overall_feedback,
    rubric_dict,
    scored_at=None
):
    """Creates an assessment on the given submission.

    Assessments are created based on feedback associated with a particular
    rubric.

    Args:
        scorer_id (str): The user ID for the user giving this assessment. This
            is required to create an assessment on a submission.
        options_selected (dict): Dictionary mapping criterion names to the
            option names the user selected for that criterion.
        criterion_feedback (dict): Dictionary mapping criterion names to the
            free-form text feedback the user gave for the criterion.
            Since criterion feedback is optional, some criteria may not appear
            in the dictionary.
        overall_feedback (unicode): Free-form text feedback on the submission overall.

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
        # TODO: check if staff has access etc.
        assessment = _complete_assessment(
            submission_uuid,
            scorer_id,
            options_selected,
            criterion_feedback,
            overall_feedback,
            rubric_dict,
            scored_at
        )
        return full_assessment_dict(assessment)

    except InvalidRubric:
        msg = u"Rubric definition was not valid"
        logger.exception(msg)
        raise StaffAssessmentRequestError(msg)
    except InvalidRubricSelection:
        msg = u"Invalid options selected in the rubric"
        logger.warning(msg, exc_info=True)
        raise StaffAssessmentRequestError(msg)
    except DatabaseError:
        error_message = (
            u"An error occurred while creating assessment by scorer with ID: {}"
        ).format(scorer_id)
        logger.exception(error_message)
        raise StaffAssessmentInternalError(error_message)


@transaction.commit_on_success
def _complete_assessment(
        submission_uuid,
        scorer_id,
        options_selected,
        criterion_feedback,
        overall_feedback,
        rubric_dict,
        scored_at
):
    """
    Internal function for atomic assessment creation. Creates a staff assessment
    in a single transaction.

    Args:
        rubric_dict (dict): The rubric model associated with this assessment
        scorer_id (str): The user ID for the user giving this assessment. This
            is required to create an assessment on a submission.
        submission_uuid (str): The submission uuid for the submission being
            assessed.
        options_selected (dict): Dictionary mapping criterion names to the
            option names the user selected for that criterion.
        criterion_feedback (dict): Dictionary mapping criterion names to the
            free-form text feedback the user gave for the criterion.
            Since criterion feedback is optional, some criteria may not appear
            in the dictionary.
        overall_feedback (unicode): Free-form text feedback on the submission overall.
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

    return assessment
