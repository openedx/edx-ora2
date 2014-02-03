"""Public interface managing the workflow for peer assessments.

The Peer Evaluation Workflow API exposes all public actions required to complete
the workflow for a given submission.

"""


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
    pass


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


def create_evaluation(submission_id, scorer_id, assessment_dict, scored_at=None):
    """Creates an evaluation on the given submission.

    Evaluations are created based on feedback associated with a particular
    rubric.

    Args:
        submission_id (str): The submission id this assessment is associated
            with. The submission_id is required and must already exist in the
            Submission model.
        scorer_id (str): The user ID for the user giving this assessment. This
            is required to create an assessment on a submission.
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
        >>> create_evaluation("submission_one", "Tim", assessment_dict)
        {
            'points_earned': 6,
            'points_possible': 12,
            'scored_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 649284 tzinfo=<UTC>),
            'scorer_id': u"Tim",
            'feedback': u'Your submission was thrilling.'
        }

    """
    pass


def has_finished_required_evaluating(student_id):
    """Check if a student still needs to evaluate more submissions

    Per the contract of the peer assessment workflow, a student must evaluate a
    number of peers before receiving feedback on their submission.

    Args:
        student_id (str): The student in the peer grading workflow to check for
            peer workflow criteria. This argument is required.

    Returns:
        bool: True if the student has evaluated enough peer submissions to move
            through the peer assessment workflow. False if the student needs to
            evaluate more peer submissions.

    Raises:
        PeerEvaluationRequestError: Raised when the student_id is invalid
        PeerEvaluationInternalError: Raised when there is an internal error
            while evaluating this workflow rule.

    Examples:
        >>> has_finished_required_evaluating("Tim")
        True

    """
    pass


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
        >>> get_evaluations("submission_one")
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
    pass


def get_submission_to_evaluate(student_item, scorer_id):
    """Get a submission to peer evaluate.

    Retrieves a submission for evaluation for the given student_item. This will
    not return a submission submitted by the requesting scorer. The submission
    returned (TODO: will be) is based on a priority queue. Submissions with the
    fewest evaluations and the most active students will be prioritized over
    submissions from students who are not as active in the evaluation process.

    Args:
        student_item (dict):
        scorer_id (str):

    Returns:
        dict:

    Raises:
        PeerEvaluationRequestError:
        PeerEvaluationInternalError:
        PeerEvaluationWorkflowError:

    Examples:
        >>> student_item_dict = dict(
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one"
        >>> )
        >>> get_submission_to_evaluate(student_item_dict, "Bob")
        {
            'student_item': 2,
            'attempt_number': 1,
            'submitted_at': datetime.datetime(2014, 1, 29, 23, 14, 52, 649284, tzinfo=<UTC>),
            'created_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 668850, tzinfo=<UTC>),
            'answer': u'The answer is 42.'
        }



    """
    pass
