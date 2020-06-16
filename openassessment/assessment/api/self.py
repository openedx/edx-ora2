"""
Public interface for self-assessment.
"""


import logging

from django.db import DatabaseError, transaction

from submissions.api import SubmissionNotFoundError, get_submission_and_student
from openassessment.assessment.errors import SelfAssessmentInternalError, SelfAssessmentRequestError
from openassessment.assessment.models import Assessment, AssessmentPart, InvalidRubricSelection
from openassessment.assessment.serializers import (InvalidRubric, full_assessment_dict, rubric_from_dict,
                                                   serialize_assessments)

# Assessments are tagged as "self-evaluation"
SELF_TYPE = "SE"

logger = logging.getLogger("openassessment.assessment.api.self")  # pylint: disable=invalid-name


def submitter_is_finished(submission_uuid, self_requirements):  # pylint: disable=unused-argument
    """
    Check whether a self-assessment has been completed for a submission.

    Args:
        submission_uuid (str): The unique identifier of the submission.
        self_requirements (dict): Any attributes of the assessment module required
            to determine if this assessment is complete. There are currently
            no requirements for a self-assessment.
    Returns:
        True if the submitter has assessed their answer
    Examples:
        >>> submitter_is_finished('222bdf3d-a88e-11e3-859e-040ccee02800', {})
        True
    """
    return Assessment.objects.filter(
        score_type=SELF_TYPE, submission_uuid=submission_uuid
    ).exists()


def assessment_is_finished(submission_uuid, self_requirements):
    """
    Check whether a self-assessment has been completed. For self-assessment,
    this function is synonymous with submitter_is_finished.

    Args:
        submission_uuid (str): The unique identifier of the submission.
        self_requirements (dict): Any attributes of the assessment module required
            to determine if this assessment is complete. There are currently
            no requirements for a self-assessment.
    Returns:
        True if the assessment is complete.
    Examples:
        >>> assessment_is_finished('222bdf3d-a88e-11e3-859e-040ccee02800', {})
        True
    """
    return submitter_is_finished(submission_uuid, self_requirements)


def get_score(submission_uuid, self_requirements):  # pylint: disable=unused-argument
    """
    Get the score for this particular assessment.

    Args:
        submission_uuid (str): The unique identifier for the submission
        self_requirements (dict): Not used.
    Returns:
        A dictionary with the points earned, points possible, and
        contributing_assessments information, along with a None staff_id.
    Examples:
        >>> get_score('222bdf3d-a88e-11e3-859e-040ccee02800', {})
        {
            'points_earned': 5,
            'points_possible': 10
        }
    """
    assessment = get_assessment(submission_uuid)
    if not assessment:
        return None

    return {
        "points_earned": assessment["points_earned"],
        "points_possible": assessment["points_possible"],
        "contributing_assessments": [assessment["id"]],
        "staff_id": None,
    }


def create_assessment(
        submission_uuid,
        user_id,
        options_selected,
        criterion_feedback,
        overall_feedback,
        rubric_dict,
        scored_at=None
):
    """
    Create a self-assessment for a submission.

    Args:
        submission_uuid (str): The unique identifier for the submission being assessed.
        user_id (str): The ID of the user creating the assessment.
                       This must match the ID of the user who made the submission.
        options_selected (dict): Mapping of rubric criterion names to option values selected.
        criterion_feedback (dict): Dictionary mapping criterion names to the
            free-form text feedback the user gave for the criterion.
            Since criterion feedback is optional, some criteria may not appear
            in the dictionary.
        overall_feedback (unicode): Free-form text feedback on the submission overall.
        rubric_dict (dict): Serialized Rubric model.

    Keyword Arguments:
        scored_at (datetime): The timestamp of the assessment; defaults to the current time.

    Returns:
        dict: serialized Assessment model

    Raises:
        SelfAssessmentRequestError: Could not retrieve a submission that the user is allowed to score.
    """
    # Check that there are not any assessments for this submission
    if Assessment.objects.filter(submission_uuid=submission_uuid, score_type=SELF_TYPE).exists():
        msg = (
            u"Cannot submit a self-assessment for the submission {uuid} "
            "because another self-assessment already exists for that submission."
        ).format(uuid=submission_uuid)
        raise SelfAssessmentRequestError(msg)

    # Check that the student is allowed to assess this submission
    try:
        submission = get_submission_and_student(submission_uuid)
        if submission['student_item']['student_id'] != user_id:
            msg = (
                u"Cannot submit a self-assessment for the submission {uuid} "
                u"because it was created by another learner "
                u"(submission learner ID {student_id} does not match your "
                u"learner id {other_id})"
            ).format(
                uuid=submission_uuid,
                student_id=submission['student_item']['student_id'],
                other_id=user_id
            )
            raise SelfAssessmentRequestError(msg)
    except SubmissionNotFoundError:
        msg = (
            u"Could not submit a self-assessment because no submission exists with UUID {uuid}"
        ).format(uuid=submission_uuid)
        raise SelfAssessmentRequestError()

    try:
        assessment = _complete_assessment(
            submission_uuid,
            user_id,
            options_selected,
            criterion_feedback,
            overall_feedback,
            rubric_dict,
            scored_at
        )
        _log_assessment(assessment, submission)
    except InvalidRubric as ex:
        msg = "Invalid rubric definition: " + str(ex)
        logger.warning(msg, exc_info=True)
        raise SelfAssessmentRequestError(msg)
    except InvalidRubricSelection as ex:
        msg = "Selected options do not match the rubric: " + str(ex)
        logger.warning(msg, exc_info=True)
        raise SelfAssessmentRequestError(msg)
    except DatabaseError:
        error_message = (
            u"Error creating self assessment for submission {}"
        ).format(submission_uuid)
        logger.exception(error_message)
        raise SelfAssessmentInternalError(error_message)

    # Return the serialized assessment
    return full_assessment_dict(assessment)


@transaction.atomic
def _complete_assessment(
        submission_uuid,
        user_id,
        options_selected,
        criterion_feedback,
        overall_feedback,
        rubric_dict,
        scored_at
):
    """
    Internal function for creating an assessment and its parts atomically.

    Args:
        submission_uuid (str): The unique identifier for the submission being
            assessed.
        user_id (str): The ID of the user creating the assessment. This must
            match the ID of the user who made the submission.
        options_selected (dict): Mapping of rubric criterion names to option
            values selected.
        criterion_feedback (dict): Dictionary mapping criterion names to the
            free-form text feedback the user gave for the criterion.
            Since criterion feedback is optional, some criteria may not appear
            in the dictionary.
        overall_feedback (unicode): Free-form text feedback on the submission overall.
        rubric_dict (dict): Serialized Rubric model.
        scored_at (datetime): The timestamp of the assessment.

    Returns:
        Assessment model

    """
    # Get or create the rubric
    rubric = rubric_from_dict(rubric_dict)

    # Create the self assessment
    assessment = Assessment.create(
        rubric,
        user_id,
        submission_uuid,
        SELF_TYPE,
        scored_at=scored_at,
        feedback=overall_feedback
    )

    # This will raise an `InvalidRubricSelection` if the selected options do not match the rubric.
    AssessmentPart.create_from_option_names(assessment, options_selected, feedback=criterion_feedback)
    return assessment


def get_assessment(submission_uuid):
    """
    Retrieve a self-assessment for a submission_uuid.

    Args:
        submission_uuid (str): The submission UUID for we want information for
            regarding self assessment.

    Returns:
        assessment (dict) is a serialized Assessment model, or None (if the user has not yet self-assessed)
        If multiple submissions or self-assessments are found, returns the most recent one.

    Raises:
        SelfAssessmentRequestError: submission_uuid was invalid.
    """
    # Retrieve assessments for the submission UUID
    # We weakly enforce that number of self-assessments per submission is <= 1,
    # but not at the database level.  Someone could take advantage of the race condition
    # between checking the number of self-assessments and creating a new self-assessment.
    # To be safe, we retrieve just the most recent submission.
    serialized_assessments = serialize_assessments(Assessment.objects.filter(
        score_type=SELF_TYPE, submission_uuid=submission_uuid
    ).order_by('-scored_at')[:1])

    if not serialized_assessments:
        logger.info(
            u"No self-assessment found for submission {}".format(submission_uuid)
        )
        return None

    serialized_assessment = serialized_assessments[0]
    logger.info(u"Retrieved self-assessment for submission {}".format(submission_uuid))

    return serialized_assessment


def get_assessment_scores_by_criteria(submission_uuid):
    """Get the median score for each rubric criterion

    Args:
        submission_uuid (str): The submission uuid is used to get the
            assessments used to score this submission, and generate the
            appropriate median score.

    Returns:
        (dict): A dictionary of rubric criterion names, with a median score of
            the peer assessments.

    Raises:
        SelfAssessmentInternalError: If any error occurs while retrieving
            information to form the median scores, an error is raised.
    """
    try:
        # This will always create a list of length 1
        assessments = list(
            Assessment.objects.filter(
                score_type=SELF_TYPE, submission_uuid=submission_uuid
            ).order_by('-scored_at')[:1]
        )
        scores = Assessment.scores_by_criterion(assessments)
        # Since this is only being sent one score, the median score will be the
        # same as the only score.
        return Assessment.get_median_score_dict(scores)
    except DatabaseError:
        error_message = (
            u"Error getting self assessment scores for submission {}"
        ).format(submission_uuid)
        logger.exception(error_message)
        raise SelfAssessmentInternalError(error_message)


def _log_assessment(assessment, submission):
    """
    Log the creation of a self-assessment.

    Args:
        assessment (Assessment): The assessment model.
        submission (dict): The serialized submission model.

    Returns:
        None

    """
    logger.info(
        u"Created self-assessment {assessment_id} for learner {user} on "
        u"submission {submission_uuid}, course {course_id}, item {item_id} "
        u"with rubric {rubric_content_hash}"
        .format(
            assessment_id=assessment.id,
            user=submission['student_item']['student_id'],
            submission_uuid=submission['uuid'],
            course_id=submission['student_item']['course_id'],
            item_id=submission['student_item']['item_id'],
            rubric_content_hash=assessment.rubric.content_hash
        )
    )
