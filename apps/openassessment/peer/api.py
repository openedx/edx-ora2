"""Public interface managing the workflow for peer assessments.

The Peer Assessment Workflow API exposes all public actions required to complete
the workflow for a given submission.

"""
import copy
import logging
import math

from django.db import DatabaseError

from openassessment.peer.models import Assessment
from openassessment.peer.serializers import AssessmentSerializer
from submissions import api as submission_api
from submissions.models import Submission, StudentItem, Score
from submissions.serializers import SubmissionSerializer, StudentItemSerializer

logger = logging.getLogger(__name__)

PEER_TYPE = "PE"


class PeerAssessmentError(Exception):
    """Generic Peer Assessment Error

    Raised when an error occurs while processing a request related to the
    Peer Assessment Workflow.

    """
    pass


class PeerAssessmentRequestError(PeerAssessmentError):
    """Error indicating insufficient or incorrect parameters in the request.

    Raised when the request does not contain enough information, or incorrect
    information which does not allow the request to be processed.

    """

    def __init__(self, field_errors):
        Exception.__init__(self, repr(field_errors))
        self.field_errors = copy.deepcopy(field_errors)


class PeerAssessmentWorkflowError(PeerAssessmentError):
    """Error indicating a step in the workflow cannot be completed,

    Raised when the action taken cannot be completed in the workflow. This can
    occur based on parameters specific to the Submission, User, or Peer Scorers.

    """
    pass


class PeerAssessmentInternalError(PeerAssessmentError):
    """Error indicating an internal problem independent of API use.

    Raised when an internal error has occurred. This should be independent of
    the actions or parameters given to the API.

    """
    pass


def create_assessment(
        submission_uuid,
        scorer_id,
        required_assessments_for_student,
        required_assessments_for_submission,
        assessment_dict,
 #       rubric_dict,
        scored_at=None):
    """Creates an assessment on the given submission.

    Assessments are created based on feedback associated with a particular
    rubric.

    Args:
        submission_uuid (str): The submission uuid this assessment is associated
            with. The submission uuid is required and must already exist in the
            Submission model.
        scorer_id (str): The user ID for the user giving this assessment. This
            is required to create an assessment on a submission.
        required_assessments_for_student (int): The number of assessments
            required for the student to receive a score for their submission.
        required_assessments_for_submission (int): The number of assessments
            required on the submission for it to be scored.
        assessment_dict (dict): All related information for the assessment. An
            assessment contains points_earned, points_possible, and feedback.
        scored_at (datetime): Optional argument to override the time in which
            the assessment took place. If not specified, scored_at is set to
            now.

    Returns:
        dict: The dictionary representing the assessment. This includes the
            points earned, points possible, time scored, scorer id, score type,
            and feedback.

    Raises:
        PeerAssessmentRequestError: Raised when the submission_id is invalid, or
            the assessment_dict does not contain the required values to create
            an assessment.
        PeerAssessmentInternalError: Raised when there is an internal error
            while creating a new assessment.

    Examples:
        >>> assessment_dict = dict(
        >>>    points_earned=[1, 0, 3, 2],
        >>>    points_possible=12,
        >>>    feedback="Your submission was thrilling.",
        >>> )
        >>> create_assessment("1", "Tim", assessment_dict)
        {
            'points_earned': 6,
            'points_possible': 12,
            'scored_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 649284 tzinfo=<UTC>),
            'scorer_id': u"Tim",
            'feedback': u'Your submission was thrilling.'
        }

    """
    try:
        submission = Submission.objects.get(uuid=submission_uuid)
        peer_assessment = {
            "scorer_id": scorer_id,
            "submission": submission.pk,
            "points_earned": sum(assessment_dict["points_earned"]),
            "points_possible": assessment_dict["points_possible"],
            "score_type": PEER_TYPE,
            "feedback": assessment_dict["feedback"],
        }
        if scored_at:
            peer_assessment["scored_at"] = scored_at

        peer_serializer = AssessmentSerializer(data=peer_evaluation)

        if not peer_serializer.is_valid():
            raise PeerAssessmentRequestError(peer_serializer.errors)
        peer_serializer.save()

        # Check if the submission is finished and its Author has graded enough.
        student_item = submission.student_item
        _check_if_finished_and_create_score(
            student_item,
            submission,
            required_assessments_for_student,
            required_assessments_for_submission
        )

        # Check if the grader is finished and has enough assessments
        scorer_item = StudentItem.objects.get(
            student_id=scorer_id,
            item_id=student_item.item_id,
            course_id=student_item.course_id,
            item_type=student_item.item_type
        )

        scorer_submissions = Submission.objects.filter(
            student_item=scorer_item
        ).order_by("-attempt_number")

        _check_if_finished_and_create_score(
            scorer_item,
            scorer_submissions[0],
            required_assessments_for_student,
            required_assessments_for_submission
        )

        return peer_serializer.data
    except DatabaseError:
        error_message = u"An error occurred while creating assessment {} for submission: {} by: {}".format(
            assessment_dict,
            submission_uuid,
            scorer_id
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)


def _check_if_finished_and_create_score(student_item,
                                        submission,
                                        required_assessments_for_student,
                                        required_assessments_for_submission):
    """Basic function for checking if a student is finished with peer workflow.

    Checks if the student is finished with the peer assessment workflow. If the
    student already has a final grade calculated, there is no need to proceed.
    If they do not have a grade, the student has a final grade calculated.

    """
    if Score.objects.filter(student_item=student_item):
        return

    finished_evaluating = has_finished_required_evaluating(
        student_item.student_id,
        required_assessments_for_student
    )
    assessments = Assessment.objects.filter(submission=submission)
    submission_finished = assessments.count() >= required_assessments_for_submission
    scores = []
    for assessment in assessments:
        scores.append(assessment.points_earned)
    if finished_evaluating and submission_finished:
        submission_api.set_score(
            StudentItemSerializer(student_item).data,
            SubmissionSerializer(submission).data,
            _calculate_final_score(scores),
            assessments[0].points_possible
        )


def _calculate_final_score(scores):
    """Final grade is calculated using integer values, rounding up.

    If there is a true median score, it is returned. If there are two median
    values, the average of those two values is returned, rounded up to the
    greatest integer value.

    """
    total_scores = len(scores)
    scores = sorted(scores)
    median = int(math.ceil(total_scores / float(2)))
    if total_scores == 0:
        return 0
    elif total_scores % 2:
        return scores[median-1]
    else:
        return int(math.ceil(sum(scores[median-1:median+1])/float(2)))


def has_finished_required_evaluating(student_id, required_assessments):
    """Check if a student still needs to evaluate more submissions

    Per the contract of the peer assessment workflow, a student must evaluate a
    number of peers before receiving feedback on their submission.

    Args:
        student_id (str): The student in the peer grading workflow to check for
            peer workflow criteria. This argument is required.
        required_assessments (int): The number of assessments a student has to
            submit before receiving the feedback on their submission. This is a
            required argument.

    Returns:
        bool: True if the student has evaluated enough peer submissions to move
            through the peer assessment workflow. False if the student needs to
            evaluate more peer submissions.

    Raises:
        PeerAssessmentRequestError: Raised when the student_id is invalid, or
            the required_assessments is not a positive integer.
        PeerAssessmentInternalError: Raised when there is an internal error
            while evaluating this workflow rule.

    Examples:
        >>> has_finished_required_evaluating("Tim", 3)
        True

    """
    if required_assessments < 0:
        raise PeerAssessmentRequestError(
            "Required Assessment count must be a positive integer.")
    return Assessment.objects.filter(
        scorer_id=student_id
    ).count() >= required_assessments


def get_assessments(submission_id):
    """Retrieve the assessments for a submission.

    Retrieves all the assessments for a submissions. This API returns related
    feedback without making any assumptions about grading. Any outstanding
    assessments associated with this submission will not be returned.

    Args:
        submission_id (str): The submission all the requested assessments are
            associated with. Required.

    Returns:
        list(dict): A list of dictionaries, where each dictionary represents a
            separate assessment. Each assessment contains points earned, points
            possible, time scored, scorer id, score type, and feedback.

    Raises:
        PeerAssessmentRequestError: Raised when the submission_id is invalid.
        PeerAssessmentInternalError: Raised when there is an internal error
            while retrieving the assessments associated with this submission.

    Examples:
        >>> get_assessments("1")
        [
            {
                'points_earned': 6,
                'points_possible': 12,
                'scored_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 649284 tzinfo=<UTC>),
                'scorer_id': u"Tim",
                'feedback': u'Your submission was thrilling.'
            },
            {
                'points_earned': 11,
                'points_possible': 12,
                'scored_at': datetime.datetime(2014, 1, 31, 14, 10, 17, 544214 tzinfo=<UTC>),
                'scorer_id': u"Bob",
                'feedback': u'Great submission.'
            }
        ]

    """
    try:
        submission = Submission.objects.get(uuid=submission_id)
        assessments = Assessment.objects.filter(submission=submission)
        serializer = AssessmentSerializer(assessments, many=True)
        return serializer.data
    except DatabaseError:
        error_message = (
            u"Error getting assessments for submission {}".format(submission_id)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)


def get_submission_to_assess(student_item_dict, required_num_assessments):
    """Get a submission to peer evaluate.

    Retrieves a submission for assessment for the given student_item. This will
    not return a submission submitted by the requesting scorer. The submission
    returned (TODO: will be) is based on a priority queue. Submissions with the
    fewest assessments and the most active students will be prioritized over
    submissions from students who are not as active in the assessment process.

    Args:
        student_item_dict (dict): The student item information from the student
            requesting a submission for assessment. The dict contains an
            item_id, course_id, and item_type, used to identify the unique
            question for the review, while the student_id is used to explicitly
            avoid giving the student their own submission.
        required_num_assessments (int): The number of assessments a submission
            requires before it has completed the peer assessment process.

    Returns:
        dict: A peer submission for assessment. This contains a 'student_item',
            'attempt_number', 'submitted_at', 'created_at', and 'answer' field to be
            used for assessment.

    Raises:
        PeerAssessmentRequestError: Raised when the request parameters are
            invalid for the request.
        PeerAssessmentInternalError:
        PeerAssessmentWorkflowError:

    Examples:
        >>> student_item_dict = dict(
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one",
        >>>    student_id="Bob",
        >>> )
        >>> get_submission_to_assess(student_item_dict, 3)
        {
            'student_item': 2,
            'attempt_number': 1,
            'submitted_at': datetime.datetime(2014, 1, 29, 23, 14, 52, 649284, tzinfo=<UTC>),
            'created_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 668850, tzinfo=<UTC>),
            'answer': u'The answer is 42.'
        }



    """
    student_items = StudentItem.objects.filter(
        course_id=student_item_dict["course_id"],
        item_id=student_item_dict["item_id"],
    ).exclude(student_id=student_item_dict["student_id"])

    submission = _get_first_submission_not_evaluated(
        student_items,
        student_item_dict["student_id"],
        required_num_assessments
    )
    if not submission:
        raise PeerAssessmentWorkflowError(
            "There are no submissions available for assessment."
        )
    return SubmissionSerializer(submission).data


def _get_first_submission_not_evaluated(student_items, student_id, required_num_assessments):
    # TODO: We need a priority queue.
    submissions = Submission.objects.filter(student_item__in=student_items).order_by(
        "submitted_at",
        "-attempt_number"
    )
    for submission in submissions:
        assessments = Assessment.objects.filter(submission=submission)
        if assessments.count() < required_num_assessments:
            already_evaluated = False
            for assessment in assessments:
                already_evaluated = already_evaluated or assessment.scorer_id == student_id
            if not already_evaluated:
                return submission
