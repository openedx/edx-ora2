"""Public interface managing the workflow for peer assessments.

The Peer Evaluation Workflow API exposes all public actions required to complete
the workflow for a given submission.

"""
import copy
import logging

from django.db import DatabaseError
import math
from openassessment.peer.models import PeerEvaluation

from openassessment.peer.serializers import PeerEvaluationSerializer
from submissions import api as submission_api
from submissions.models import Submission, StudentItem, Score
from submissions.serializers import SubmissionSerializer, StudentItemSerializer

logger = logging.getLogger(__name__)

PEER_TYPE = "PE"


class PeerEvaluationError(Exception):
    """Generic Peer Evaluation Error

    Raised when an error occurs while processing a request related to the
    Peer Evaluation Workflow.

    """
    pass


class PeerEvaluationRequestError(PeerEvaluationError):
    """Error indicating insufficient or incorrect parameters in the request.

    Raised when the request does not contain enough information, or incorrect
    information which does not allow the request to be processed.

    """

    def __init__(self, field_errors):
        Exception.__init__(self, repr(field_errors))
        self.field_errors = copy.deepcopy(field_errors)


class PeerEvaluationWorkflowError(PeerEvaluationError):
    """Error indicating a step in the workflow cannot be completed,

    Raised when the action taken cannot be completed in the workflow. This can
    occur based on parameters specific to the Submission, User, or Peer Scorers.

    """
    pass


class PeerEvaluationInternalError(PeerEvaluationError):
    """Error indicating an internal problem independent of API use.

    Raised when an internal error has occurred. This should be independent of
    the actions or parameters given to the API.

    """
    pass


def create_evaluation(
        submission_uuid,
        scorer_id,
        required_evaluations_for_student,
        required_evaluations_for_submission,
        assessment_dict,
        scored_at=None):
    """Creates an evaluation on the given submission.

    Evaluations are created based on feedback associated with a particular
    rubric.

    Args:
        submission_uuid (str): The submission uuid this assessment is associated
            with. The submission uuid is required and must already exist in the
            Submission model.
        scorer_id (str): The user ID for the user giving this assessment. This
            is required to create an assessment on a submission.
        required_evaluations_for_student (int): The number of evaluations
            required for the student to receive a score for their submission.
        required_evaluations_for_submission (int): The number of evaluations
            required on the submission for it to be scored.
        assessment_dict (dict): All related information for the assessment. An
            assessment contains points_earned, points_possible, and feedback.
        scored_at (datetime): Optional argument to override the time in which
            the evaluation took place. If not specified, scored_at is set to
            now.

    Returns:
        dict: The dictionary representing the evaluation. This includes the
            points earned, points possible, time scored, scorer id, score type,
            and feedback.

    Raises:
        PeerEvaluationRequestError: Raised when the submission_id is invalid, or
            the assessment_dict does not contain the required values to create
            an assessment.
        PeerEvaluationInternalError: Raised when there is an internal error
            while creating a new evaluation.

    Examples:
        >>> assessment_dict = dict(
        >>>    points_earned=[1, 0, 3, 2],
        >>>    points_possible=12,
        >>>    feedback="Your submission was thrilling.",
        >>> )
        >>> create_evaluation("1", "Tim", assessment_dict)
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
        peer_evaluation = {
            "scorer_id": scorer_id,
            "submission": submission.pk,
            "points_earned": sum(assessment_dict["points_earned"]),
            "points_possible": assessment_dict["points_possible"],
            "score_type": PEER_TYPE,
            "feedback": assessment_dict["feedback"],
        }
        if scored_at:
            peer_evaluation["scored_at"] = scored_at

        peer_serializer = PeerEvaluationSerializer(data=peer_evaluation)
        if not peer_serializer.is_valid():
            raise PeerEvaluationRequestError(peer_serializer.errors)
        peer_serializer.save()

        # Check if the submission is finished and its Author has graded enough.
        student_item = submission.student_item
        _check_if_finished_and_create_score(
            student_item,
            submission,
            required_evaluations_for_student,
            required_evaluations_for_submission
        )

        # Check if the grader is finished and has enough evaluations
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
            required_evaluations_for_student,
            required_evaluations_for_submission
        )

        return peer_serializer.data
    except DatabaseError:
        error_message = u"An error occurred while creating evaluation {} for submission: {} by: {}".format(
            assessment_dict,
            submission_uuid,
            scorer_id
        )
        logger.exception(error_message)
        raise PeerEvaluationInternalError(error_message)


def _check_if_finished_and_create_score(student_item,
                                        submission,
                                        required_evaluations_for_student,
                                        required_evaluations_for_submission):
    """Basic function for checking if a student is finished with peer workflow.

    Checks if the student is finished with the peer evaluation workflow. If the
    student already has a final grade calculated, there is no need to proceed.
    If they do not have a grade, the student has a final grade calculated.

    """
    if Score.objects.filter(student_item=student_item):
        return

    finished_evaluating = has_finished_required_evaluating(
        student_item.student_id,
        required_evaluations_for_student
    )
    evaluations = PeerEvaluation.objects.filter(submission=submission)
    submission_finished = evaluations.count() >= required_evaluations_for_submission
    scores = []
    for evaluation in evaluations:
        scores.append(evaluation.points_earned)
    if finished_evaluating and submission_finished:
        submission_api.set_score(
            StudentItemSerializer(student_item).data,
            SubmissionSerializer(submission).data,
            _calculate_final_score(scores),
            evaluations[0].points_possible
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


def has_finished_required_evaluating(student_id, required_evaluations):
    """Check if a student still needs to evaluate more submissions

    Per the contract of the peer assessment workflow, a student must evaluate a
    number of peers before receiving feedback on their submission.

    Args:
        student_id (str): The student in the peer grading workflow to check for
            peer workflow criteria. This argument is required.
        required_evaluations (int): The number of evaluations a student has to
            submit before receiving the feedback on their submission. This is a
            required argument.

    Returns:
        bool: True if the student has evaluated enough peer submissions to move
            through the peer assessment workflow. False if the student needs to
            evaluate more peer submissions.

    Raises:
        PeerEvaluationRequestError: Raised when the student_id is invalid, or
            the required_evaluations is not a positive integer.
        PeerEvaluationInternalError: Raised when there is an internal error
            while evaluating this workflow rule.

    Examples:
        >>> has_finished_required_evaluating("Tim", 3)
        True

    """
    if required_evaluations < 0:
        raise PeerEvaluationRequestError(
            "Required Evaluation count must be a positive integer.")
    return PeerEvaluation.objects.filter(
        scorer_id=student_id
    ).count() >= required_evaluations


def get_evaluations(submission_id):
    """Retrieve the evaluations for a submission.

    Retrieves all the evaluations for a submissions. This API returns related
    feedback without making any assumptions about grading. Any outstanding
    evaluations associated with this submission will not be returned.

    Args:
        submission_id (str): The submission all the requested evaluations are
            associated with. Required.

    Returns:
        list(dict): A list of dictionaries, where each dictionary represents a
            separate evaluation. Each evaluation contains points earned, points
            possible, time scored, scorer id, score type, and feedback.

    Raises:
        PeerEvaluationRequestError: Raised when the submission_id is invalid.
        PeerEvaluationInternalError: Raised when there is an internal error
            while retrieving the evaluations associated with this submission.

    Examples:
        >>> get_evaluations("1")
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
        evaluations = PeerEvaluation.objects.filter(submission=submission)
        serializer = PeerEvaluationSerializer(evaluations, many=True)
        return serializer.data
    except DatabaseError:
        error_message = (
            u"Error getting evaluations for submission {}".format(submission_id)
        )
        logger.exception(error_message)
        raise PeerEvaluationInternalError(error_message)


def get_submission_to_evaluate(student_item_dict, required_num_evaluations):
    """Get a submission to peer evaluate.

    Retrieves a submission for evaluation for the given student_item. This will
    not return a submission submitted by the requesting scorer. The submission
    returned (TODO: will be) is based on a priority queue. Submissions with the
    fewest evaluations and the most active students will be prioritized over
    submissions from students who are not as active in the evaluation process.

    Args:
        student_item_dict (dict): The student item information from the student
            requesting a submission for evaluation. The dict contains an
            item_id, course_id, and item_type, used to identify the unique
            question for the review, while the student_id is used to explicitly
            avoid giving the student their own submission.
        required_num_evaluations (int): The number of evaluations a submission
            requires before it has completed the peer evaluation process.

    Returns:
        dict: A peer submission for evaluation. This contains a 'student_item',
            'attempt_number', 'submitted_at', 'created_at', and 'answer' field to be
            used for evaluation.

    Raises:
        PeerEvaluationRequestError: Raised when the request parameters are
            invalid for the request.
        PeerEvaluationInternalError:
        PeerEvaluationWorkflowError:

    Examples:
        >>> student_item_dict = dict(
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one",
        >>>    student_id="Bob",
        >>> )
        >>> get_submission_to_evaluate(student_item_dict, 3)
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
        required_num_evaluations
    )
    if not submission:
        raise PeerEvaluationWorkflowError(
            "There are no submissions available for evaluation."
        )
    return SubmissionSerializer(submission).data


def _get_first_submission_not_evaluated(student_items, student_id, required_num_evaluations):
    # TODO: We need a priority queue.
    submissions = Submission.objects.filter(student_item__in=student_items).order_by(
        "submitted_at",
        "-attempt_number"
    )
    for submission in submissions:
        evaluations = PeerEvaluation.objects.filter(submission=submission)
        if evaluations.count() < required_num_evaluations:
            already_evaluated = False
            for evaluation in evaluations:
                already_evaluated = already_evaluated or evaluation.scorer_id == student_id
            if not already_evaluated:
                return submission