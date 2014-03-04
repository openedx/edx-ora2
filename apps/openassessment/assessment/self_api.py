"""
Public interface for self-assessment.
"""
from django.utils.translation import ugettext as _
from submissions.api import (
    get_submission_by_uuid, get_submissions,
    SubmissionNotFoundError, SubmissionRequestError
)
from openassessment.assessment.serializers import (
    rubric_from_dict, AssessmentSerializer, full_assessment_dict, InvalidRubric
)
from openassessment.assessment.models import Assessment, InvalidOptionSelection

# TODO -- remove once Dave's changes land
from submissions.models import Submission


# Assessments are tagged as "self-evaluation"
SELF_TYPE = "SE"


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
    # TODO -- change key lookup for submission UUID once Dave's changes land
    if Assessment.objects.filter(submission__uuid=submission_uuid, score_type=SELF_TYPE).exists():
        raise SelfAssessmentRequestError(_("Self assessment already exists for this submission"))

    # Check that the student is allowed to assess this submission
    try:
        submission = get_submission_by_uuid(submission_uuid)
        if submission is None or submission['student_item']['student_id'] != user_id:
            raise SelfAssessmentRequestError(_("Cannot self-assess this submission"))
    except SubmissionNotFoundError:
        raise SelfAssessmentRequestError(_("Could not retrieve the submission."))

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
        # TODO -- replace once Dave adds submission_uuid as a field on the assessment
        "submission": Submission.objects.get(uuid=submission_uuid).pk,
        "score_type": SELF_TYPE,
        "feedback": u"",
        "parts": [{"option": option_id} for option_id in option_ids],
    }

    if scored_at is not None:
        self_assessment['scored_at'] = scored_at

    # Serialize the assessment
    serializer = AssessmentSerializer(data=self_assessment)
    if not serializer.is_valid():
        msg = _("Could not create self assessment: {errors}").format(errors=serializer.errors)
        raise SelfAssessmentRequestError(msg)

    serializer.save()

    # Return the serialized assessment
    return serializer.data


def get_submission_and_assessment(student_item_dict):
    """
    Retrieve a submission and self-assessment for a student item.

    Args:
        student_item_dict (dict): serialized StudentItem model

    Returns:
        A tuple `(submission, assessment)` where:
            submission (dict) is a serialized Submission model, or None (if the user has not yet made a submission)
            assessment (dict) is a serialized Assessment model, or None (if the user has not yet self-assessed)

        If multiple submissions or self-assessments are found, returns the most recent one.

    Raises:
        SelfAssessmentRequestError: Student item dict was invalid.
    """
    # Look up the most recent submission from the student item
    try:
        submissions = get_submissions(student_item_dict, limit=1)
        if not submissions:
            return (None, None)
    except SubmissionNotFoundError:
        return (None, None)
    except SubmissionRequestError as ex:
        raise SelfAssessmentRequestError(_('Could not retrieve submission'))

    submission_uuid = submissions[0]['uuid']

    # Retrieve assessments for the submission
    # We weakly enforce that number of self-assessments per submission is <= 1,
    # but not at the database level.  Someone could take advantage of the race condition
    # between checking the number of self-assessments and creating a new self-assessment.
    # To be safe, we retrieve just the most recent submission.
    assessments = Assessment.objects.filter(
        score_type=SELF_TYPE, submission__uuid=submission_uuid
    ).order_by('-scored_at')

    if assessments.exists():
        # TODO -- remove once Dave's changes land
        assessment_dict = full_assessment_dict(assessments[0])
        assessment_dict['submission_uuid'] = submission_uuid
        return (submissions[0], assessment_dict)
    else:
        return (submissions[0], None)


# TODO: fill in this stub
def is_complete(submission_uuid):
    return True
