"""Public interface managing the workflow for peer assessments.

The Peer Assessment Workflow API exposes all public actions required to complete
the workflow for a given submission.

"""


import logging

from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone

from submissions import api as sub_api
from openassessment.assessment.errors import (PeerAssessmentInternalError, PeerAssessmentRequestError,
                                              PeerAssessmentWorkflowError)
from openassessment.assessment.models import (Assessment, AssessmentFeedback, AssessmentPart, InvalidRubricSelection,
                                              PeerWorkflow, PeerWorkflowItem)
from openassessment.assessment.serializers import (AssessmentFeedbackSerializer, InvalidRubric, RubricSerializer,
                                                   full_assessment_dict, rubric_from_dict, serialize_assessments)

logger = logging.getLogger("openassessment.assessment.api.peer")  # pylint: disable=invalid-name

PEER_TYPE = "PE"

FLEXIBLE_PEER_GRADING_REQUIRED_SUBMISSION_AGE_IN_DAYS = 7
FLEXIBLE_PEER_GRADING_GRADED_BY_PERCENTAGE = 30


def required_peer_grades(submission_uuid, peer_requirements):
    """
    Given a submission id, finds how many peer assessment required.

    Args:
        submission_uuid (str): The UUID of the submission being tracked.
        peer_requirements (dict): Dictionary with the key "must_grade" indicating
            the required number of submissions the student must grade
            and "enable_flexible_grading" indicating if flexible grading enabled.

    Returns:
        int
    """

    submission = sub_api.get_submission(submission_uuid)

    must_grade = peer_requirements["must_be_graded_by"]

    if peer_requirements.get("enable_flexible_grading"):

        # find how many days elapsed since subimitted
        days_elapsed = (timezone.now().date() - submission['submitted_at'].date()).days

        # check if flexible grading applies. if it does, then update must_grade
        if days_elapsed >= FLEXIBLE_PEER_GRADING_REQUIRED_SUBMISSION_AGE_IN_DAYS:
            must_grade = int(must_grade * FLEXIBLE_PEER_GRADING_GRADED_BY_PERCENTAGE / 100)
            if must_grade == 0:
                must_grade = 1

    return must_grade


def can_be_skipped(submission_uuid, peer_requirements):  # pylint: disable=unused-argument
    """
    Peer workflow step can be always skipped.

    Args:
        submission_uuid (str): The UUID of the submission being tracked.
        peer_requirements (dict): Dictionary with the key "must_grade" indicating
            the required number of submissions the student must grade.

    Returns:
        bool
    """
    return peer_requirements is not None


def submitter_is_finished(submission_uuid, peer_requirements):
    """
    Check whether the submitter has made the required number of assessments.

    If the requirements dict is None (because we're being updated
    asynchronously or when the workflow is first created),
    then automatically return False.

    Args:
        submission_uuid (str): The UUID of the submission being tracked.
        peer_requirements (dict): Dictionary with the key "must_grade" indicating
            the required number of submissions the student must grade.

    Returns:
        bool

    """
    if peer_requirements is None:
        return False

    try:
        workflow = PeerWorkflow.objects.get(submission_uuid=submission_uuid)
        if workflow.completed_at is not None:
            return True
        elif workflow.num_peers_graded() >= peer_requirements["must_grade"]:
            workflow.completed_at = timezone.now()
            workflow.save()
            return True
        return False
    except PeerWorkflow.DoesNotExist:
        return False
    except KeyError as ex:
        raise PeerAssessmentRequestError('Requirements dict must contain "must_grade" key') from ex


def get_graded_by_count(submission_uuid):
    """
    Retrieve the number of peer assessments the submitter has received.
    Returns None if no submission with this ID.
    """
    workflow = PeerWorkflow.get_by_submission_uuid(submission_uuid)
    if workflow is None:
        return None

    scored_items = workflow.graded_by.filter(
        assessment__submission_uuid=submission_uuid,
        assessment__score_type=PEER_TYPE
    )
    return scored_items.count()


def assessment_is_finished(submission_uuid, peer_requirements):
    """
    Check whether the submitter has received enough assessments
    to get a score.

    If the requirements dict is None (because we're being updated
    asynchronously or when the workflow is first created),
    then automatically return False.

    Args:
        submission_uuid (str): The UUID of the submission being tracked.
        peer_requirements (dict): Dictionary with the key "must_be_graded_by"
            indicating the required number of assessments the student
            must receive to get a score.

    Returns:

        bool
    """
    if not peer_requirements:
        return False

    count = get_graded_by_count(submission_uuid)
    if count is None:
        return False

    return count >= required_peer_grades(submission_uuid, peer_requirements)


def on_start(submission_uuid):
    """Create a new peer workflow for a student item and submission.

    Creates a unique peer workflow for a student item, associated with a
    submission.

    Args:
        submission_uuid (str): The submission associated with this workflow.

    Returns:
        None

    Raises:
        SubmissionError: There was an error retrieving the submission.
        PeerAssessmentInternalError: Raised when there is an internal error
            creating the Workflow.

    """
    try:
        with transaction.atomic():
            submission = sub_api.get_submission_and_student(submission_uuid)
            workflow, __ = PeerWorkflow.objects.get_or_create(
                student_id=submission['student_item']['student_id'],
                course_id=submission['student_item']['course_id'],
                item_id=submission['student_item']['item_id'],
                submission_uuid=submission_uuid
            )
            workflow.save()
    except IntegrityError:
        # If we get an integrity error, it means someone else has already
        # created a workflow for this submission, so we don't need to do anything.
        pass
    except DatabaseError as ex:
        error_message = (
            "An internal error occurred while creating a new peer "
            "workflow for submission {}"
            .format(submission_uuid)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message) from ex


def get_score(submission_uuid, peer_requirements):
    """
    Retrieve a score for a submission if requirements have been satisfied.

    Args:
        submission_uuid (str): The UUID of the submission.
        requirements (dict): Dictionary with the key "must_be_graded_by"
            indicating the required number of assessments the student
            must receive to get a score.

    Returns:
        A dictionary with the points earned, points possible, and
        contributing_assessments information, along with a None staff_id.

    """

    if peer_requirements is None:
        return None

    # User hasn't completed their own submission yet
    if not submitter_is_finished(submission_uuid, peer_requirements):
        return None

    workflow = PeerWorkflow.get_by_submission_uuid(submission_uuid)

    if workflow is None:
        return None

    # Retrieve the assessments in ascending order by score date,
    # because we want to use the *first* one(s) for the score.
    items = workflow.graded_by.filter(
        assessment__submission_uuid=submission_uuid,
        assessment__score_type=PEER_TYPE
    ).order_by('-assessment')

    # Check if enough peers have graded this submission
    if items.count() < required_peer_grades(submission_uuid, peer_requirements):
        return None

    # Unfortunately, we cannot use update() after taking a slice,
    # so we need to update the and save the items individually.
    # One might be tempted to first query for the first n assessments,
    # then select items that have those assessments.
    # However, this generates a SQL query with a LIMIT in a subquery,
    # which is not supported by some versions of MySQL.
    # Although this approach generates more database queries, the number is likely to
    # be relatively small (at least 1 and very likely less than 5).
    for scored_item in items[:peer_requirements["must_be_graded_by"]]:
        scored_item.scored = True
        scored_item.save()
    assessments = [item.assessment for item in items]

    return {
        "points_earned": sum(
            get_assessment_median_scores(submission_uuid).values()
        ),
        "points_possible": assessments[0].points_possible,
        "contributing_assessments": [assessment.id for assessment in assessments],
        "staff_id": None,
    }


def create_assessment(
        scorer_submission_uuid,
        scorer_id,
        options_selected,
        criterion_feedback,
        overall_feedback,
        rubric_dict,
        num_required_grades,
        scored_at=None
):
    # pylint: disable=unicode-format-string
    """
    Creates an assessment on the given submission.

    Assessments are created based on feedback associated with a particular
    rubric.

    Args:
        scorer_submission_uuid (str): The submission uuid for the Scorer's
            workflow. The submission being assessed can be determined via the
            peer workflow of the grading student.
        scorer_id (str): The user ID for the user giving this assessment. This
            is required to create an assessment on a submission.
        options_selected (dict): Dictionary mapping criterion names to the
            option names the user selected for that criterion.
        criterion_feedback (dict): Dictionary mapping criterion names to the
            free-form text feedback the user gave for the criterion.
            Since criterion feedback is optional, some criteria may not appear
            in the dictionary.
        overall_feedback (unicode): Free-form text feedback on the submission overall.
        num_required_grades (int): The required number of assessments a
            submission requires before it is completed. If this number of
            assessments is reached, the grading_completed_at timestamp is set
            for the Workflow.

    Keyword Args:
        scored_at (datetime): Optional argument to override the time in which
            the assessment took place. If not specified, scored_at is set to
            now.

    Returns:
        dict: the Assessment model, serialized as a dict.

    Raises:
        PeerAssessmentRequestError: Raised when the submission_id is invalid, or
            the assessment_dict does not contain the required values to create
            an assessment.
        PeerAssessmentInternalError: Raised when there is an internal error
            while creating a new assessment.

    Examples:
        >>> options_selected = {"clarity": "Very clear", "precision": "Somewhat precise"}
        >>> criterion_feedback = {"clarity": "I thought this essay was very clear."}
        >>> feedback = "Your submission was thrilling."
        >>> create_assessment("1", "Tim", options_selected, criterion_feedback, feedback, rubric_dict)
    """
    try:
        # Retrieve workflow information
        scorer_workflow = PeerWorkflow.objects.get(submission_uuid=scorer_submission_uuid)
        peer_workflow_item = scorer_workflow.find_active_assessments()
        if peer_workflow_item is None:
            message = (
                "There are no open assessments associated with the scorer's "
                "submission UUID {}."
            ).format(scorer_submission_uuid)
            logger.warning(message)
            raise PeerAssessmentWorkflowError(message)
        peer_submission_uuid = peer_workflow_item.submission_uuid

        assessment = _complete_assessment(
            rubric_dict,
            scorer_id,
            peer_submission_uuid,
            options_selected,
            criterion_feedback,
            scorer_workflow,
            overall_feedback,
            num_required_grades,
            scored_at
        )

        _log_assessment(assessment, scorer_workflow)
        return full_assessment_dict(assessment)
    except PeerWorkflow.DoesNotExist as ex:
        message = (
            "There is no Peer Workflow associated with the given "
            "submission UUID {}."
        ).format(scorer_submission_uuid)
        logger.exception(message)
        raise PeerAssessmentWorkflowError(message) from ex
    except InvalidRubric as ex:
        msg = "The rubric definition is not valid."
        logger.exception(msg)
        raise PeerAssessmentRequestError(msg) from ex
    except InvalidRubricSelection as ex:
        msg = "Invalid options were selected in the rubric."
        logger.warning(msg, exc_info=True)
        raise PeerAssessmentRequestError(msg) from ex
    except DatabaseError as ex:
        error_message = (
            "An error occurred while creating an assessment by the scorer with this ID: {}"
        ).format(scorer_id)
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message) from ex


@transaction.atomic
def _complete_assessment(
        rubric_dict,
        scorer_id,
        peer_submission_uuid,
        options_selected,
        criterion_feedback,
        scorer_workflow,
        overall_feedback,
        num_required_grades,
        scored_at
):
    """
    Internal function for atomic assessment creation. Creates a peer assessment
    and closes the associated peer workflow item in a single transaction.

    Args:
        rubric_dict (dict): The rubric model associated with this assessment
        scorer_id (str): The user ID for the user giving this assessment. This
            is required to create an assessment on a submission.
        peer_submission_uuid (str): The submission uuid for the submission being
            assessed.
        options_selected (dict): Dictionary mapping criterion names to the
            option names the user selected for that criterion.
        criterion_feedback (dict): Dictionary mapping criterion names to the
            free-form text feedback the user gave for the criterion.
            Since criterion feedback is optional, some criteria may not appear
            in the dictionary.
        scorer_workflow (PeerWorkflow): The PeerWorkflow associated with the
            scorer. Updates the workflow item associated with this assessment.
        overall_feedback (unicode): Free-form text feedback on the submission overall.
        num_required_grades (int): The required number of assessments a
            submission requires before it is completed. If this number of
            assessments is reached, the grading_completed_at timestamp is set
            for the Workflow.
        scored_at (datetime): Optional argument to override the time in which
            the assessment took place. If not specified, scored_at is set to
            now.

    Returns:
        The Assessment model

    """
    # Get or create the rubric
    rubric = rubric_from_dict(rubric_dict)

    # Create the peer assessment
    assessment = Assessment.create(
        rubric,
        scorer_id,
        peer_submission_uuid,
        PEER_TYPE,
        scored_at=scored_at,
        feedback=overall_feedback
    )

    # Create assessment parts for each criterion in the rubric
    # This will raise an `InvalidRubricSelection` if the selected options do not
    # match the rubric.
    AssessmentPart.create_from_option_names(assessment, options_selected, feedback=criterion_feedback)

    # Close the active assessment
    scorer_workflow.close_active_assessment(peer_submission_uuid, assessment, num_required_grades)
    return assessment


def get_rubric_max_scores(submission_uuid):
    """Gets the maximum possible value for each criterion option

    Iterates over the rubric used to grade the given submission, and creates a
    dictionary of maximum possible values.

    Args:
        submission_uuid: The submission to get the associated rubric max scores.
    Returns:
        A dictionary of max scores for this rubric's criteria options. Returns
            None if no assessments are found for this submission.
    Raises:
        PeerAssessmentInternalError: Raised when there is an error retrieving
            the submission, or its associated rubric.
    """
    try:
        assessments = list(
            Assessment.objects.filter(
                submission_uuid=submission_uuid
            ).order_by("-scored_at", "-id").select_related("rubric")[:1]
        )
        if not assessments:
            return None

        assessment = assessments[0]
        rubric_dict = RubricSerializer.serialized_from_cache(assessment.rubric)
        return {
            criterion["name"]: criterion["points_possible"]
            for criterion in rubric_dict["criteria"]
        }
    except DatabaseError as ex:
        error_message = (
            "Error getting rubric options max scores for submission uuid {uuid}"
        ).format(uuid=submission_uuid)
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message) from ex


def get_assessment_median_scores(submission_uuid):
    """Get the median score for each rubric criterion

    For a given assessment, collect the median score for each criterion on the
    rubric. This set can be used to determine the overall score, as well as each
    part of the individual rubric scores.

    If there is a true median score, it is returned. If there are two median
    values, the average of those two values is returned, rounded up to the
    greatest integer value.

    Args:
        submission_uuid (str): The submission uuid is used to get the
            assessments used to score this submission, and generate the
            appropriate median score.

    Returns:
        dict: A dictionary of rubric criterion names,
        with a median score of the peer assessments.

    Raises:
        PeerAssessmentInternalError: If any error occurs while retrieving
            information to form the median scores, an error is raised.
    """
    try:
        workflow = PeerWorkflow.objects.get(submission_uuid=submission_uuid)
        items = workflow.graded_by.filter(scored=True)
        assessments = [item.assessment for item in items]
        scores = Assessment.scores_by_criterion(assessments)
        return Assessment.get_median_score_dict(scores)
    except PeerWorkflow.DoesNotExist:
        return {}
    except DatabaseError as ex:
        error_message = (
            "Error getting assessment median scores for submission {uuid}"
        ).format(uuid=submission_uuid)
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message) from ex


def has_finished_required_evaluating(submission_uuid, required_assessments):
    """Check if a student still needs to evaluate more submissions

    Per the contract of the peer assessment workflow, a student must evaluate a
    number of peers before receiving feedback on their submission.

    Args:
        submission_uuid (str): The submission UUID is required to determine if
            the associated student has completed enough assessments. This
            argument is required.
        required_assessments (int): The number of assessments a student has to
            submit before receiving the feedback on their submission. This is a
            required argument.

    Returns:
        tuple: True if the student has evaluated enough peer submissions to move
            through the peer assessment workflow. False if the student needs to
            evaluate more peer submissions. The second value is the count of
            assessments completed.

    Raises:
        PeerAssessmentRequestError: Raised when the submission UUID is invalid,
            or the required_assessments is not a positive integer.
        PeerAssessmentInternalError: Raised when there is an internal error
            while evaluating this workflow rule.

    Examples:
        >>> has_finished_required_evaluating("abc123", 3)
        True, 3

    """
    workflow = PeerWorkflow.get_by_submission_uuid(submission_uuid)
    done = False
    peers_graded = 0
    if workflow:
        peers_graded = workflow.num_peers_graded()
        done = (peers_graded >= required_assessments)
    return done, peers_graded


def get_assessments(submission_uuid, limit=None):
    """Retrieve the assessments for a submission.

    Retrieves all the assessments for a submissions. This API returns related
    feedback without making any assumptions about grading. Any outstanding
    assessments associated with this submission will not be returned.

    Args:
        submission_uuid (str): The submission all the requested assessments are
            associated with. Required.

    Keyword Arguments:
        limit (int): Limit the returned assessments. If None, returns all.


    Returns:
        list: A list of dictionaries, where each dictionary represents a
            separate assessment. Each assessment contains points earned, points
            possible, time scored, scorer id, score type, and feedback.


    Raises:
        PeerAssessmentRequestError: Raised when the submission_id is invalid.
        PeerAssessmentInternalError: Raised when there is an internal error
            while retrieving the assessments associated with this submission.

    Examples:
        >>> get_assessments("1", limit=2)
        [
            {
                'points_earned': 6,
                'points_possible': 12,
                'scored_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 649284 tzinfo=<UTC>),
                'scorer': u"Tim",
                'feedback': u'Your submission was thrilling.'
            },
            {
                'points_earned': 11,
                'points_possible': 12,
                'scored_at': datetime.datetime(2014, 1, 31, 14, 10, 17, 544214 tzinfo=<UTC>),
                'scorer': u"Bob",
                'feedback': u'Great submission.'
            }
        ]

    """
    try:
        assessments = Assessment.objects.filter(
            submission_uuid=submission_uuid,
            score_type=PEER_TYPE
        )[:limit]
        return serialize_assessments(assessments)
    except DatabaseError as ex:
        error_message = (
            "Error getting assessments for submission {uuid}"
        ).format(uuid=submission_uuid)
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message) from ex


def get_submitted_assessments(submission_uuid, limit=None):
    """Retrieve the assessments created by the given submission's author.

    Retrieves all the assessments created by the given submission's author. This
    API returns related feedback without making any assumptions about grading.
    Any outstanding assessments associated with this submission will not be
    returned.

    Args:
        submission_uuid (str): The submission of the student whose assessments
        we are requesting. Required.

    Keyword Arguments:
        limit (int): Limit the returned assessments. If None, returns all.

    Returns:
        list(dict): A list of dictionaries, where each dictionary represents a
            separate assessment. Each assessment contains points earned, points
            possible, time scored, scorer id, score type, and feedback. If no
            workflow is found associated with the given submission_uuid, returns
            an empty list.

    Raises:
        PeerAssessmentRequestError: Raised when the submission_id is invalid.
        PeerAssessmentInternalError: Raised when there is an internal error
            while retrieving the assessments associated with this submission.

    Examples:
        >>> get_submitted_assessments("1", limit=2)
        [
            {
                'points_earned': 6,
                'points_possible': 12,
                'scored_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 649284 tzinfo=<UTC>),
                'scorer': u"Tim",
                'feedback': u'Your submission was thrilling.'
            },
            {
                'points_earned': 11,
                'points_possible': 12,
                'scored_at': datetime.datetime(2014, 1, 31, 14, 10, 17, 544214 tzinfo=<UTC>),
                'scorer': u"Tim",
                'feedback': u'Great submission.'
            }
        ]

    """
    try:
        # If no workflow is found associated with the uuid, this returns None,
        # and an empty set of assessments will be returned.
        workflow = PeerWorkflow.get_by_submission_uuid(submission_uuid)
        items = PeerWorkflowItem.objects.filter(
            scorer=workflow,
            assessment__isnull=False
        )
        assessments = Assessment.objects.filter(
            pk__in=[item.assessment.pk for item in items])[:limit]
        return serialize_assessments(assessments)
    except DatabaseError as ex:
        error_message = (
            "Couldn't retrieve the assessments completed by the student with submission {uuid}"
        ).format(uuid=submission_uuid)
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message) from ex


def get_submission_to_assess(submission_uuid, graded_by):
    """Get a submission to peer evaluate.

    Retrieves a submission for assessment for the given student. This will
    not return a submission submitted by the requesting scorer. Submissions are
    returned based on how many assessments are still required, and if there are
    peers actively assessing a particular submission. If there are no
    submissions requiring assessment, a submission may be returned that will be
    'over graded', and the assessment will not be counted towards the overall
    grade.

    Args:
        submission_uuid (str): The submission UUID from the student
            requesting a submission for assessment. This is used to explicitly
            avoid giving the student their own submission, and determines the
            associated Peer Workflow.
        graded_by (int): The number of assessments a submission
            requires before it has completed the peer assessment process.

    Returns:
        dict: A peer submission for assessment. This contains a 'student_item',
            'attempt_number', 'submitted_at', 'created_at', and 'answer' field to be
            used for assessment.

    Raises:
        PeerAssessmentRequestError: Raised when the request parameters are
            invalid for the request.
        PeerAssessmentInternalError: Raised when there is an internal error
            retrieving peer workflow information.
        PeerAssessmentWorkflowError: Raised when an error occurs because this
            function, or the student item, is not in the proper workflow state
            to retrieve a peer submission.

    Examples:
        >>> get_submission_to_assess("abc123", 3)
        {
            'student_item': 2,
            'attempt_number': 1,
            'submitted_at': datetime.datetime(2014, 1, 29, 23, 14, 52, 649284, tzinfo=<UTC>),
            'created_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 668850, tzinfo=<UTC>),
            'answer': u'The answer is 42.'
        }

    """
    workflow = PeerWorkflow.get_by_submission_uuid(submission_uuid)

    if not workflow:
        raise PeerAssessmentWorkflowError(
            "A Peer Assessment Workflow does not exist for the student "
            "with submission UUID {}".format(submission_uuid)
        )

    if workflow.is_cancelled:
        return None

    open_item = workflow.find_active_assessments()
    peer_submission_uuid = open_item.submission_uuid if open_item else None
    # If there is an active assessment for this user, get that submission,
    # otherwise, get the first assessment for review, otherwise,
    # get the first submission available for over grading ("over-grading").
    if peer_submission_uuid is None:
        peer_submission_uuid = workflow.get_submission_for_review(graded_by)
    if peer_submission_uuid is None:
        peer_submission_uuid = workflow.get_submission_for_over_grading()
    if peer_submission_uuid:
        try:
            submission_data = sub_api.get_submission(peer_submission_uuid)
            PeerWorkflow.create_item(workflow, peer_submission_uuid)
            _log_workflow(peer_submission_uuid, workflow)
            return submission_data
        except sub_api.SubmissionNotFoundError as ex:
            error_message = "Could not find a submission with the uuid %s for student %s in the peer workflow."
            error_meesage_args = (peer_submission_uuid, workflow.student_id)
            logger.exception(error_message, error_meesage_args[0], error_meesage_args[1])
            raise PeerAssessmentWorkflowError(error_message % error_meesage_args) from ex
    else:
        logger.info(
            "No submission found for %s to assess (%s, %s)",
            workflow.student_id,
            workflow.course_id,
            workflow.item_id
        )
        return None


def create_peer_workflow(submission_uuid):
    """Create a new peer workflow for a student item and submission.

    Creates a unique peer workflow for a student item, associated with a
    submission.

    Args:
        submission_uuid (str): The submission associated with this workflow.

    Returns:
        None

    Raises:
        SubmissionError: There was an error retrieving the submission.
        PeerAssessmentInternalError: Raised when there is an internal error
            creating the Workflow.

    Examples:
        >>> create_peer_workflow("1")

    """
    try:
        with transaction.atomic():
            submission = sub_api.get_submission_and_student(submission_uuid)
            workflow, __ = PeerWorkflow.objects.get_or_create(
                student_id=submission['student_item']['student_id'],
                course_id=submission['student_item']['course_id'],
                item_id=submission['student_item']['item_id'],
                submission_uuid=submission_uuid
            )
            workflow.save()
    except IntegrityError:
        # If we get an integrity error, it means someone else has already
        # created a workflow for this submission, so we don't need to do anything.
        pass
    except DatabaseError as ex:
        error_message = (
            "An internal error occurred while creating a new peer "
            "workflow for submission {}"
        ).format(submission_uuid)
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message) from ex


def create_peer_workflow_item(scorer_submission_uuid, submission_uuid):
    """
    Begin peer-assessing a particular submission.
    Note that this does NOT pick the submission from the prioritized list of available submissions.
    Mainly useful for testing.

    Args:
        scorer_submission_uuid (str): The ID of the scoring student.
        submission_uuid (str): The unique identifier of the submission being scored

    Returns:
        None

    Raises:
        PeerAssessmentWorkflowError: Could not find the workflow for the student.
        PeerAssessmentInternalError: Could not create the peer workflow item.
    """
    workflow = PeerWorkflow.get_by_submission_uuid(scorer_submission_uuid)
    PeerWorkflow.create_item(workflow, submission_uuid)


def get_assessment_feedback(submission_uuid):
    """
    Retrieve a feedback on an assessment.

    Args:
        submission_uuid: The submission we want to retrieve assessment feedback for.

    Returns:
        dict or None

    Raises:
        PeerAssessmentInternalError: Error occurred while retrieving the feedback.
    """
    try:
        feedback = AssessmentFeedback.objects.get(
            submission_uuid=submission_uuid
        )
        return AssessmentFeedbackSerializer(feedback).data
    except AssessmentFeedback.DoesNotExist:
        return None
    except DatabaseError as ex:
        error_message = (
            "An error occurred retrieving assessment feedback for {}."
            .format(submission_uuid)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message) from ex


def set_assessment_feedback(feedback_dict):
    """
    Set a feedback object for an assessment to have some new values.

    Sets or updates the assessment feedback with the given values in the dict.

    Args:
        feedback_dict (dict): A dictionary of all the values to update or create
            a new assessment feedback.

    Returns:
        None

    Raises:
        PeerAssessmentRequestError
        PeerAssessmentInternalError
    """
    submission_uuid = feedback_dict.get('submission_uuid')
    feedback_text = feedback_dict.get('feedback_text')
    selected_options = feedback_dict.get('options', list())

    if feedback_text and len(feedback_text) > AssessmentFeedback.MAXSIZE:
        error_message = "Assessment feedback too large."
        raise PeerAssessmentRequestError(error_message)

    try:
        # Get or create the assessment model for this submission
        # If we receive an integrity error, assume that someone else is trying to create
        # another feedback model for this submission, and raise an exception.
        if submission_uuid:
            feedback, created = AssessmentFeedback.objects.get_or_create(submission_uuid=submission_uuid)
        else:
            error_message = "An error occurred creating assessment feedback: bad or missing submission_uuid."
            logger.error(error_message)
            raise PeerAssessmentRequestError(error_message)

        # Update the feedback text
        if feedback_text is not None:
            feedback.feedback_text = feedback_text

        # Save the feedback model.  We need to do this before setting m2m relations.
        if created or feedback_text is not None:
            feedback.save()

        # Associate the feedback with selected options
        feedback.add_options(selected_options)

        # Associate the feedback with scored assessments
        assessments = PeerWorkflowItem.get_scored_assessments(submission_uuid)
        feedback.assessments.add(*assessments)
    except DatabaseError as ex:
        msg = f"Error occurred while creating or updating feedback on assessment: {feedback_dict}"
        logger.exception(msg)
        raise PeerAssessmentInternalError(msg) from ex


def _log_assessment(assessment, scorer_workflow):
    """
    Log the creation of a peer assessment.

    Args:
        assessment (Assessment): The assessment model that was created.
        scorer_workflow (dict): A dictionary representation of the Workflow
            belonging to the scorer of this assessment.

    Returns:
        None

    """
    logger.info(
        "Created peer-assessment %s for submission %s, course %s, item %s with rubric %s; scored by %s",
        assessment.id,
        assessment.submission_uuid,
        scorer_workflow.course_id,
        scorer_workflow.item_id,
        assessment.rubric.content_hash,
        scorer_workflow.student_id,
    )


def _log_workflow(submission_uuid, workflow):
    """
    Log the creation of a peer-assessment workflow.

    Args:
        submission_uuid (str): The UUID of the submission being assessed.
        workflow (PeerWorkflow): The Peer Workflow of the student making the
            assessment.
    """
    logger.info(
        "Retrieved submission %s (%s, %s) to be assessed by %s",
        submission_uuid,
        workflow.course_id,
        workflow.item_id,
        workflow.student_id,
    )


def is_workflow_cancelled(submission_uuid):
    """
    Check if workflow submission is cancelled.

    Args:
        submission_uuid (str): The UUID of the workflow's submission.

    Returns:
        True/False
    """
    if submission_uuid is None:
        return False
    try:
        workflow = PeerWorkflow.get_by_submission_uuid(submission_uuid)
        return workflow.is_cancelled if workflow else False
    except PeerAssessmentWorkflowError:
        return False


def on_cancel(submission_uuid):
    """Cancel the peer workflow for submission.

    Sets the cancelled_at field in peer workflow.

    Args:
        submission_uuid (str): The submission UUID associated with this workflow.

    Returns:
        None

    """
    try:
        workflow = PeerWorkflow.get_by_submission_uuid(submission_uuid)
        if workflow:
            workflow.cancelled_at = timezone.now()
            workflow.save()
    except (PeerAssessmentWorkflowError, DatabaseError) as ex:
        error_message = (
            "An internal error occurred while cancelling the peer"
            "workflow for submission {}"
            .format(submission_uuid)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message) from ex


def get_waiting_step_details(
    course_id,
    item_id,
    submission_uuids,
    must_be_graded_by
):
    """
    Proxy method to `get_waiting_step_details` model method.
    Retrieves information about users in the waiting step (waiting for peer reviews).

    Args:
        course_id (str): The course that this problem belongs to.
        item_id (str): The student_item (problem) that we want to know statistics about.
        submission_uuids (list): A list of submission UUIDs to filter the results for,
                                    if None is given, this will return all students which
                                    the peer step is not complete.
        must_be_graded_by (int): number of required peer reviews for this problem.

    Returns:
        dict: a dictionary that contains information about students in the waiting step.
              The dictionary includes the following information: `student_id`, `created_at` (
              timestamp of when the step was created), `graded` (how many peers the student
              graded) and `graded_by` (how many peers graded this student).
    """
    return PeerWorkflow.get_waiting_step_details(
        course_id,
        item_id,
        submission_uuids,
        must_be_graded_by
    )
