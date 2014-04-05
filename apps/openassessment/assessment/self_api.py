"""
Public interface for self-assessment.
"""
import logging
from django.utils.translation import ugettext as _
from dogapi import dog_stats_api

from submissions.api import get_submission_and_student, SubmissionNotFoundError
from openassessment.assessment.serializers import (
    AssessmentSerializer, InvalidRubric,
    full_assessment_dict, rubric_from_dict, serialize_assessments
)
from openassessment.assessment.models import (
    Assessment, AssessmentPart, InvalidOptionSelection
)


# Assessments are tagged as "self-evaluation"
SELF_TYPE = "SE"

logger = logging.getLogger("openassessment.assessment.self_api")


class SelfAssessmentRequestError(Exception):
    """
    There was a problem with the request for a self-assessment.
    """
    pass


def create_assessment(submission_uuid, user_id, options_selected, rubric_dict, scored_at=None):
    """
    Create a self-assessment for a submission.

    Args:
        submission_uuid (str): The unique identifier for the submission being assessed.
        user_id (str): The ID of the user creating the assessment.  This must match the ID of the user who made the submission.
        options_selected (dict): Mapping of rubric criterion names to option values selected.
        rubric_dict (dict): Serialized Rubric model.

    Kwargs:
        scored_at (datetime): The timestamp of the assessment; defaults to the current time.

    Returns:
        dict: serialized Assessment model

    Raises:
        SelfAssessmentRequestError: Could not retrieve a submission that the user is allowed to score.
    """
    # Check that there are not any assessments for this submission
    if Assessment.objects.filter(submission_uuid=submission_uuid, score_type=SELF_TYPE).exists():
        raise SelfAssessmentRequestError(_("You've already completed your self assessment for this response."))

    # Check that the student is allowed to assess this submission
    try:
        submission = get_submission_and_student(submission_uuid)
        if submission['student_item']['student_id'] != user_id:
            raise SelfAssessmentRequestError(_("You can only complete a self assessment on your own response."))
    except SubmissionNotFoundError:
        raise SelfAssessmentRequestError(_("Could not retrieve the response."))

    # Get or create the rubric
    try:
        rubric = rubric_from_dict(rubric_dict)
        option_ids = rubric.options_ids(options_selected)
    except InvalidRubric as ex:
        msg = _("Invalid rubric definition: {errors}").format(errors=ex.errors)
        raise SelfAssessmentRequestError(msg)
    except InvalidOptionSelection:
        msg = _("Selected options do not match the rubric")
        raise SelfAssessmentRequestError(msg)

    # Create the assessment
    # Since we have already retrieved the submission, we can assume that
    # the user who created the submission exists.
    self_assessment = {
        "rubric": rubric.id,
        "scorer_id": user_id,
        "submission_uuid": submission_uuid,
        "score_type": SELF_TYPE,
        "feedback": u"",
    }

    if scored_at is not None:
        self_assessment['scored_at'] = scored_at

    # Serialize the assessment
    serializer = AssessmentSerializer(data=self_assessment)
    if not serializer.is_valid():
        msg = _("Could not create self assessment: {errors}").format(errors=serializer.errors)
        raise SelfAssessmentRequestError(msg)

    assessment = serializer.save()

    # We do this to do a run around django-rest-framework serializer
    # validation, which would otherwise require two DB queries per
    # option to do validation. We already validated these options above.
    AssessmentPart.add_to_assessment(assessment, option_ids)
    assessment_dict = full_assessment_dict(assessment)
    _log_assessment(assessment, submission)


    # Return the serialized assessment
    return assessment_dict


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


def is_complete(submission_uuid):
    """
    Check whether a self-assessment has been completed for a submission.

    Args:
        submission_uuid (str): The unique identifier of the submission.

    Returns:
        bool
    """
    return Assessment.objects.filter(
        score_type=SELF_TYPE, submission_uuid=submission_uuid
    ).exists()


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
        u"Created self-assessment {assessment_id} for student {user} on "
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

    tags = [
        u"course_id:{course_id}".format(course_id=submission['student_item']['course_id']),
        u"item_id:{item_id}".format(item_id=submission['student_item']['item_id']),
        u"type:self"
    ]

    score_percentage = assessment.to_float()
    if score_percentage is not None:
        dog_stats_api.histogram('openassessment.assessment.score_percentage', score_percentage, tags=tags)

    dog_stats_api.increment('openassessment.assessment.count', tags=tags)
