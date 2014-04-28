"""Public interface managing the workflow for peer assessments.

The Peer Assessment Workflow API exposes all public actions required to complete
the workflow for a given submission.

"""
import copy
import logging
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.db import DatabaseError
from dogapi import dog_stats_api
import random

from openassessment.assessment.models import (
    Assessment, AssessmentFeedback, AssessmentPart,
    InvalidOptionSelection, PeerWorkflow, PeerWorkflowItem,
)
from openassessment.assessment.serializers import (
    AssessmentSerializer, AssessmentFeedbackSerializer, RubricSerializer,
    full_assessment_dict, rubric_from_dict, serialize_assessments,
)
from submissions import api as sub_api

logger = logging.getLogger("openassessment.assessment.peer_api")

PEER_TYPE = "PE"
TIME_LIMIT = timedelta(hours=8)


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


def submitter_is_finished(submission_uuid, requirements):
    """Temporary bridge method."""
    return is_complete(submission_uuid, requirements)


def is_complete(submission_uuid, requirements):
    try:
        workflow = PeerWorkflow.objects.get(submission_uuid=submission_uuid)
        if workflow.completed_at is not None:
            return True
        elif _num_peers_graded(workflow) >= requirements["must_grade"]:
            workflow.completed_at = timezone.now()
            workflow.save()
            return True
        return False
    except PeerWorkflow.DoesNotExist:
        return False


def get_score(submission_uuid, requirements):
    """
    Retrieve a score for a submission if requirements have been satisfied.

    Args:
        submission_uuid (str): The UUID of the submission.
        requirements (dict): Description of requirements for receiving a score,
            specific to the particular kind of submission (e.g. self or peer).

    Returns:
        dict with keys "points_earned" and "points_possible".
    """
    # User hasn't completed their own submission yet
    if not is_complete(submission_uuid, requirements):
        return None

    workflow = PeerWorkflow.objects.get(submission_uuid=submission_uuid)

    # This query will use the ordering defined by the assessment model
    # (descending scored_at, then descending id)
    items = workflow.graded_by.filter(
        assessment__submission_uuid=submission_uuid,
        assessment__score_type=PEER_TYPE
    ).order_by('assessment')

    submission_finished = items.count() >= requirements["must_be_graded_by"]
    if not submission_finished:
        return None

    # Unfortunately, we cannot use update() after taking a slice,
    # so we need to update the and save the items individually.
    # One might be tempted to first query for the first n assessments,
    # then select items that have those assessments.
    # However, this generates a SQL query with a LIMIT in a subquery,
    # which is not supported by some versions of MySQL.
    # Although this approach generates more database queries, the number is likely to
    # be relatively small (at least 1 and very likely less than 5).
    for scored_item in items[:requirements["must_be_graded_by"]]:
        scored_item.scored = True
        scored_item.save()

    return {
        "points_earned": sum(
            get_assessment_median_scores(submission_uuid).values()
        ),
        "points_possible": items[0].assessment.points_possible,
    }

def assessment_is_finished(submission_uuid, requirements):
    return bool(get_score(submission_uuid, requirements))


def create_assessment(
        scorer_submission_uuid,
        scorer_id,
        options_selected,
        criterion_feedback,
        overall_feedback,
        rubric_dict,
        num_required_grades,
        scored_at=None):
    """Creates an assessment on the given submission.

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

    Kwargs:
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
        rubric = rubric_from_dict(rubric_dict)

        # Validate that the selected options matched the rubric
        # and raise an error if this is not the case
        try:
            option_ids = rubric.options_ids(options_selected)
        except InvalidOptionSelection as ex:
            msg = _("Selected options do not match the rubric: {error}").format(error=ex.message)
            raise PeerAssessmentRequestError(msg)

        scorer_workflow = PeerWorkflow.objects.get(submission_uuid=scorer_submission_uuid)

        peer_workflow_item = _get_latest_open_workflow_item(scorer_workflow)
        if peer_workflow_item is None:
            message = _(
                u"There are no open assessments associated with the scorer's "
                u"submission UUID {}.".format(scorer_submission_uuid)
            )
            logger.error(message)
            raise PeerAssessmentWorkflowError(message)

        peer_submission_uuid = peer_workflow_item.author.submission_uuid
        peer_assessment = {
            "rubric": rubric.id,
            "scorer_id": scorer_id,
            "submission_uuid": peer_submission_uuid,
            "score_type": PEER_TYPE,
            "feedback": overall_feedback[0:Assessment.MAXSIZE],
        }

        if scored_at is not None:
            peer_assessment["scored_at"] = scored_at

        peer_serializer = AssessmentSerializer(data=peer_assessment)

        if not peer_serializer.is_valid():
            raise PeerAssessmentRequestError(peer_serializer.errors)

        assessment = peer_serializer.save()

        # We do this to do a run around django-rest-framework serializer
        # validation, which would otherwise require two DB queries per
        # option to do validation. We already validated these options above.
        AssessmentPart.add_to_assessment(assessment, option_ids, criterion_feedback=criterion_feedback)

        # Close the active assessment
        _close_active_assessment(scorer_workflow, peer_submission_uuid, assessment, num_required_grades)
        assessment_dict = full_assessment_dict(assessment)
        _log_assessment(assessment, scorer_workflow)

        return assessment_dict
    except DatabaseError:
        error_message = _(
            u"An error occurred while creating assessment {} by: {}"
            .format(assessment_dict, scorer_id)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)
    except PeerWorkflow.DoesNotExist:
        message = _(
            u"There is no Peer Workflow associated with the given "
            u"submission UUID {}.".format(scorer_submission_uuid)
        )
        logger.error(message)
        raise PeerAssessmentWorkflowError(message)


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
    except DatabaseError:
        error_message = _(
            u"Error getting rubric options max scores for submission uuid "
            u"[{}]".format(submission_uuid)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)


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
        (dict): A dictionary of rubric criterion names, with a median score of
            the peer assessments.

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
    except DatabaseError:
        error_message = _(u"Error getting assessment median scores {}".format(submission_uuid))
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)


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
    workflow = _get_workflow_by_submission_uuid(submission_uuid)
    done = False
    peers_graded = 0
    if workflow:
        peers_graded = _num_peers_graded(workflow)
        done = (peers_graded >= required_assessments)
    return done, peers_graded


def get_assessments(submission_uuid, scored_only=True, limit=None):
    """Retrieve the assessments for a submission.

    Retrieves all the assessments for a submissions. This API returns related
    feedback without making any assumptions about grading. Any outstanding
    assessments associated with this submission will not be returned.

    Args:
        submission_uuid (str): The submission all the requested assessments are
            associated with. Required.

    Kwargs:
        scored (boolean): Only retrieve the assessments used to generate a score
            for this submission.
        limit (int): Limit the returned assessments. If None, returns all.

    Returns:
        list(dict): A list of dictionaries, where each dictionary represents a
            separate assessment. Each assessment contains points earned, points
            possible, time scored, scorer id, score type, and feedback.

    Raises:
        PeerAssessmentRequestError: Raised when the submission_id is invalid.
        PeerAssessmentInternalError: Raised when there is an internal error
            while retrieving the assessments associated with this submission.

    Examples:
        >>> get_assessments("1", scored_only=True, limit=2)
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
        if scored_only:
            assessments = PeerWorkflowItem.get_scored_assessments(
                submission_uuid
            )[:limit]
        else:
            assessments = Assessment.objects.filter(
                submission_uuid=submission_uuid,
                score_type=PEER_TYPE
            )[:limit]
        return serialize_assessments(assessments)
    except DatabaseError:
        error_message = _(
            u"Error getting assessments for submission {}".format(submission_uuid)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)


def get_submission_to_assess(
        submission_uuid,
        graded_by,
        over_grading=False):
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
        over_grading (bool): Allows over grading to be performed if no submission
            requires assessments. Over grading should only occur if the deadline
            for submissions has passed, but there is still a window for peer
            assessment. Defaults to False.

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
    workflow = _get_workflow_by_submission_uuid(submission_uuid)
    if not workflow:
        raise PeerAssessmentWorkflowError(_(
            u"A Peer Assessment Workflow does not exist for the specified "
            u"student."))
    peer_submission_uuid = _find_active_assessments(workflow)
    # If there is an active assessment for this user, get that submission,
    # otherwise, get the first assessment for review, otherwise, if over grading
    # is turned on, get the first submission available for over grading.
    if peer_submission_uuid is None:
        peer_submission_uuid = _get_submission_for_review(workflow, graded_by)
    if peer_submission_uuid is None and over_grading:
        peer_submission_uuid = _get_submission_for_over_grading(workflow)
    if peer_submission_uuid:
        try:
            submission_data = sub_api.get_submission(peer_submission_uuid)
            _create_peer_workflow_item(workflow, peer_submission_uuid)
            _log_workflow(peer_submission_uuid, workflow, over_grading)
            return submission_data
        except sub_api.SubmissionNotFoundError:
            error_message = _(
                u"Could not find a submission with the uuid {} for student {} "
                u"in the peer workflow."
                .format(peer_submission_uuid, workflow.student_id)
            )
            logger.exception(error_message)
            raise PeerAssessmentWorkflowError(error_message)
    else:
        logger.info(
            u"No submission found for {} to assess ({}, {})"
            .format(
                workflow.student_id,
                workflow.course_id,
                workflow.item_id,
            )
        )
        return None


def create_peer_workflow(submission_uuid):
    """Create a new peer workflow for a student item and submission.

    Creates a unique peer workflow for a student item, associated with a
    submission.

    Args:
        submission_uuid (str): The submission associated with this workflow.

    Returns:
        Workflow (PeerWorkflow): A PeerWorkflow item created based on the given
            student item and submission.

    Raises:
        SubmissionError: There was an error retrieving the submission.
        PeerAssessmentInternalError: Raised when there is an internal error
            creating the Workflow.

    Examples:
        >>> create_peer_workflow("1")

    """
    try:
        submission = sub_api.get_submission_and_student(submission_uuid)
        workflow = PeerWorkflow.objects.get_or_create(
            student_id=submission['student_item']['student_id'],
            course_id=submission['student_item']['course_id'],
            item_id=submission['student_item']['item_id'],
            submission_uuid=submission_uuid
        )
        return workflow
    except DatabaseError:
        error_message = _(
            u"An internal error occurred while creating a new peer "
            u"workflow for submission {}"
            .format(submission_uuid)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)


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
    workflow = _get_workflow_by_submission_uuid(scorer_submission_uuid)
    _create_peer_workflow_item(workflow, submission_uuid)


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
    except DatabaseError:
        error_message = (
            u"An error occurred retrieving assessment feedback for {}."
            .format(submission_uuid)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)


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
        error_message = u"Assessment feedback too large."
        raise PeerAssessmentRequestError(error_message)

    try:
        # Get or create the assessment model for this submission
        # If we receive an integrity error, assume that someone else is trying to create
        # another feedback model for this submission, and raise an exception.
        if submission_uuid:
            feedback, created = AssessmentFeedback.objects.get_or_create(submission_uuid=submission_uuid)
        else:
            error_message = u"An error occurred creating assessment feedback: bad or missing submission_uuid."
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
    except DatabaseError:
        msg = u"Error occurred while creating or updating feedback on assessment: {}".format(feedback_dict)
        logger.exception(msg)
        raise PeerAssessmentInternalError(msg)


def _get_workflow_by_submission_uuid(submission_uuid):
    """Get the Peer Workflow associated with the given submission UUID.

    If available, returns the Peer Workflow associated with the given
    submission UUID.

    Args:
        submission_uuid (str): The string representation of the UUID belonging
            to the associated Peer Workflow.

    Returns:
        workflow (PeerWorkflow): The most recent peer workflow associated with
            this submission UUID.

    Raises:
        PeerAssessmentWorkflowError: Thrown when no workflow can be found for
            the associated submission UUID. This should always exist before a
            student is allow to request submissions for peer assessment.

    Examples:
        >>> workflow = _get_workflow_by_submission_uuid("abc123")
        {
            'student_id': u'Bob',
            'item_id': u'type_one',
            'course_id': u'course_1',
            'submission_uuid': u'1',
            'created_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 668850, tzinfo=<UTC>)
        }

    """
    try:
        return PeerWorkflow.objects.get(submission_uuid=submission_uuid)
    except PeerWorkflow.DoesNotExist:
        return None
    except DatabaseError:
        error_message = _(
            u"Error finding workflow for submission UUID {}. Workflow must be "
            u"created for submission before beginning peer assessment."
            .format(submission_uuid)
        )
        logger.exception(error_message)
        raise PeerAssessmentWorkflowError(error_message)


def _create_peer_workflow_item(workflow, submission_uuid):
    """Create a new peer workflow for a student item and submission.

    Creates a unique peer workflow for a student item, associated with a
    submission.

    Args:
        workflow (PeerWorkflow): The peer workflow associated with the scorer.
        submission_uuid (str): The submission associated with this workflow.

    Raises:
        PeerAssessmentInternalError: Raised when there is an internal error
            creating the Workflow.

    Examples:
        >>> student_item_dict = dict(
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one",
        >>>    student_id="Bob",
        >>> )
        >>> workflow = _get_workflow_by_submission_uuid(student_item_dict)
        >>> _create_peer_workflow_item(workflow, "1")

    """
    try:
        peer_workflow = PeerWorkflow.objects.get(submission_uuid=submission_uuid)

        workflow_item, __ = PeerWorkflowItem.objects.get_or_create(
            scorer=workflow,
            author=peer_workflow,
            submission_uuid=submission_uuid
        )
        workflow_item.started_at = timezone.now()
        workflow_item.save()
        return workflow_item
    except DatabaseError:
        error_message = _(
            u"An internal error occurred while creating a new peer workflow "
            u"item for workflow {}".format(workflow)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)


def _find_active_assessments(workflow):
    """Given a student item, return an active assessment if one is found.

    Before retrieving a new submission for a peer assessor, check to see if that
    assessor already has a submission out for assessment. If an unfinished
    assessment is found that has not expired, return the associated submission.

    TODO: If a user begins an assessment, then resubmits, this will never find
    the unfinished assessment. Is this OK?

    Args:
        workflow (PeerWorkflow): See if there is an associated active assessment
            for this PeerWorkflow.

    Returns:
        submission_uuid (str): The submission_uuid for the submission that the
            student has open for active assessment.

    Examples:
        >>> student_item_dict = dict(
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one",
        >>>    student_id="Bob",
        >>> )
        >>> workflow = _get_workflow_by_submission_uuid(student_item_dict)
        >>> _find_active_assessments(student_item_dict)
        "1"

    """
    workflows = workflow.graded.filter(
        assessment__isnull=True,
        started_at__gt=timezone.now() - TIME_LIMIT
    )
    return workflows[0].submission_uuid if workflows else None


def _get_submission_for_review(workflow, graded_by, over_grading=False):
    """Get the next submission for peer assessment

    Find a submission for peer assessment. This function will find the next
    submission that requires assessment, excluding any submission that has been
    completely graded, or is actively being reviewed by other students.

    Args:
        workflow (PeerWorkflow): Used to determine the next submission to get
            for peer assessment. Iterates over all workflows that have the same
            course_id and item_id as the student_item_dict, excluding any
            workflow which has the same student_id.

    Returns:
        submission_uuid (str): The submission_uuid for the submission to review.

    Raises:
        PeerAssessmentInternalError: Raised when there is an error retrieving
            the workflows or workflow items for this request.

    Examples:
        >>> student_item_dict = dict(
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one",
        >>>    student_id="Bob",
        >>> )
        >>> _find_active_assessments(student_item_dict)
        "1"

    """
    timeout = (timezone.now() - TIME_LIMIT).strftime("%Y-%m-%d %H:%M:%S")
    # The follow query behaves as the Peer Assessment Queue. This will
    # find the next submission (via PeerWorkflow) in this course / question
    # that:
    #  1) Does not belong to you
    #  2) Does not have enough completed assessments
    #  3) Is not something you have already scored.
    #  4) Does not have a combination of completed assessments or open
    #     assessments equal to or more than the requirement.
    try:
        peer_workflows = list(PeerWorkflow.objects.raw(
            "select pw.id, pw.submission_uuid "
            "from assessment_peerworkflow pw "
            "where pw.item_id=%s "
            "and pw.course_id=%s "
            "and pw.student_id<>%s "
            "and pw.grading_completed_at is NULL "
            "and pw.id not in ("
            "   select pwi.author_id "
            "   from assessment_peerworkflowitem pwi "
            "   where pwi.scorer_id=%s "
            "   and pwi.assessment_id is not NULL "
            ") "
            "and ("
            "   select count(pwi.id) as c "
            "   from assessment_peerworkflowitem pwi "
            "   where pwi.author_id=pw.id "
            "   and (pwi.assessment_id is not NULL or pwi.started_at > %s) "
            ") < %s "
            "order by pw.created_at, pw.id "
            "limit 1; ",
            [
                workflow.item_id,
                workflow.course_id,
                workflow.student_id,
                workflow.id,
                timeout,
                graded_by
            ]
        ))
        if not peer_workflows:
            return None

        return peer_workflows[0].submission_uuid
    except DatabaseError:
        error_message = _(
            u"An internal error occurred while retrieving a peer submission "
            u"for student {}".format(workflow)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)


def _get_submission_for_over_grading(workflow):
    """Retrieve the next submission uuid for over grading

    Gets the next submission uuid for over grading in peer assessment.

    """
    # The follow query behaves as the Peer Assessment Over Grading Queue. This
    # will find a random submission (via PeerWorkflow) in this course / question
    # that:
    #  1) Does not belong to you
    #  2) Is not something you have already scored
    try:
        query = list(PeerWorkflow.objects.raw(
            "select pw.id, pw.submission_uuid "
            "from assessment_peerworkflow pw "
            "where course_id=%s "
            "and item_id=%s "
            "and student_id<>%s "
            "and pw.id not in ( "
                "select pwi.author_id "
                "from assessment_peerworkflowitem pwi "
                "where pwi.scorer_id=%s); ",
            [workflow.course_id, workflow.item_id, workflow.student_id, workflow.id]
        ))
        workflow_count = len(query)
        if workflow_count < 1:
            return None

        random_int = random.randint(0, workflow_count - 1)
        random_workflow = query[random_int]

        return random_workflow.submission_uuid
    except DatabaseError:
        error_message = _(
            u"An internal error occurred while retrieving a peer submission "
            u"for student {}".format(workflow)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)


def _get_latest_open_workflow_item(workflow):
    """Gets the latest open workflow item for a given workflow.

    If there is an open workflow item for the given workflow, return this item.

    Args:
        workflow (PeerWorkflow): The scorer's workflow.

    Returns:
        A PeerWorkflowItem that is open for assessment. None if no item is
        found.

    Examples:
        >>> workflow = _get_workflow_by_submission_uuid("abc123")
        >>> _get_latest_open_workflow_item(workflow)
        {
            'student_id': u'Bob',
            'item_id': u'type_one',
            'course_id': u'course_1',
            'submission_uuid': u'1',
            'created_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 668850, tzinfo=<UTC>)
        }
    """
    workflow_query = workflow.graded.filter(
        assessment__isnull=True).order_by("-started_at", "-id")
    items = list(workflow_query[:1])
    return items[0] if items else None


def _close_active_assessment(
        workflow,
        submission_uuid,
        assessment,
        num_required_grades
):
    """Associate the work item with a complete assessment.

    Updates a workflow item on the student's workflow with the associated
    assessment. When a workflow item has an assessment, it is considered
    finished.

    Args:
        workflow (PeerWorkflow): The scorer's workflow
        submission_uuid (str): The submission the scorer is grading.
        assessment (PeerAssessment): The associate assessment for this action.
        graded_by (int): The required number of grades the peer workflow
            requires to be considered complete.

    Examples:
        >>> workflow = _get_workflow_by_submission_uuid("abc123")
        >>> assessment = Assessment.objects.all()[0]
        >>> _close_active_assessment(workflow, "1", assessment, 3)

    """
    try:
        item_query = workflow.graded.filter(submission_uuid=submission_uuid).order_by("-started_at", "-id")
        items = list(item_query[:1])
        if not items:
            raise PeerAssessmentWorkflowError(_(
                u"No open assessment was found for student {} while assessing "
                u"submission UUID {}.".format(workflow.student_id, submission_uuid)
            ))
        item = items[0]
        item.assessment = assessment
        item.save()

        if (not item.author.grading_completed_at
                and item.author.graded_by.filter(assessment__isnull=False).count() >= num_required_grades):
            item.author.grading_completed_at = timezone.now()
            item.author.save()
    except (DatabaseError, PeerWorkflowItem.DoesNotExist):
        error_message = _(
            u"An internal error occurred while retrieving a workflow item for "
            u"student {}. Workflow Items are created when submissions are "
            u"pulled for assessment."
            .format(workflow.student_id)
        )
        logger.exception(error_message)
        raise PeerAssessmentWorkflowError(error_message)


def _num_peers_graded(workflow):
    """Returns the number of peers the student owning the workflow has graded.

    Determines if the student has graded enough peers.

    Args:
        workflow (PeerWorkflow): The workflow associated with the current
            student.

    Returns:
        True if the student is done peer assessing, False if not.

    Examples:
        >>> student_item_dict = dict(
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one",
        >>>    student_id="Bob",
        >>> )
        >>> workflow = _get_workflow_by_submission_uuid(student_item_dict)
        >>> _num_peers_graded(workflow, 3)
        True
    """
    return workflow.graded.filter(assessment__isnull=False).count()


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
        u"Created peer-assessment {assessment_id} for submission "
        u"{submission_uuid}, course {course_id}, item {item_id} "
        u"with rubric {rubric_content_hash}; scored by {scorer}"
        .format(
            assessment_id=assessment.id,
            submission_uuid=assessment.submission_uuid,
            course_id=scorer_workflow.course_id,
            item_id=scorer_workflow.item_id,
            rubric_content_hash=assessment.rubric.content_hash,
            scorer=scorer_workflow.student_id,
        )
    )

    tags = [
        u"course_id:{course_id}".format(course_id=scorer_workflow.course_id),
        u"item_id:{item_id}".format(item_id=scorer_workflow.item_id),
        u"type:peer",
    ]

    score_percentage = assessment.to_float()
    if score_percentage is not None:
        dog_stats_api.histogram('openassessment.assessment.score_percentage', score_percentage, tags=tags)

    # Calculate the time spent assessing
    # This is the time from when the scorer retrieved the submission
    # (created the peer workflow item) to when they completed an assessment.
    # By this point, the assessment *should* have an associated peer workflow item,
    # but if not, we simply skip the event.
    try:
        workflow_item = assessment.peerworkflowitem_set.get()
    except (
        PeerWorkflowItem.DoesNotExist,
        PeerWorkflowItem.MultipleObjectsReturned,
        DatabaseError
    ):
        msg = u"Could not retrieve peer workflow item for assessment: {assessment}".format(
            assessment=assessment.id
        )
        logger.exception(msg)
        workflow_item = None

    if workflow_item is not None:
        time_delta = assessment.scored_at - workflow_item.started_at
        dog_stats_api.histogram(
            'openassessment.assessment.seconds_spent_assessing',
            time_delta.total_seconds(),
            tags=tags
        )

    dog_stats_api.increment('openassessment.assessment.count', tags=tags)


def _log_workflow(submission_uuid, workflow, over_grading):
    """
    Log the creation of a peer-assessment workflow.

    Args:
        submission_uuid (str): The UUID of the submission being assessed.
        workflow (PeerWorkflow): The Peer Workflow of the student making the
            assessment.
        over_grading (bool): Whether over-grading is enabled.
    """
    logger.info(
        u"Retrieved submission {} ({}, {}) to be assessed by {}"
        .format(
            submission_uuid,
            workflow.course_id,
            workflow.item_id,
            workflow.student_id,
        )
    )

    tags = [
        u"course_id:{course_id}".format(course_id=workflow.course_id),
        u"item_id:{item_id}".format(item_id=workflow.item_id),
        u"type:peer"
    ]

    if over_grading:
        tags.append(u"overgrading")

    dog_stats_api.increment('openassessment.assessment.peer_workflow.count', tags=tags)
