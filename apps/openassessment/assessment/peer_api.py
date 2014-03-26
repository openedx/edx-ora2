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
from django.db.models import Q

from openassessment.assessment.models import (
    Assessment, AssessmentFeedback, AssessmentPart,
    InvalidOptionSelection, PeerWorkflow, PeerWorkflowItem,
)
from openassessment.assessment.serializers import (
    AssessmentSerializer, AssessmentFeedbackSerializer, RubricSerializer,
    full_assessment_dict, rubric_from_dict, serialize_assessments,
)
from submissions import api as sub_api
from submissions.api import get_submission_and_student
from submissions.models import Submission, StudentItem
from submissions.serializers import SubmissionSerializer, StudentItemSerializer

logger = logging.getLogger(__name__)

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


def is_complete(submission_uuid, requirements):
    try:
        workflow = PeerWorkflow.objects.get(submission_uuid=submission_uuid)
    except PeerWorkflow.DoesNotExist:
        return False
    return _num_peers_graded(workflow) >= requirements["must_grade"]


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

    workflow.completed_at = timezone.now()
    workflow.save()
    return {
        "points_earned": sum(
            get_assessment_median_scores(submission_uuid).values()
        ),
        "points_possible": items[0].assessment.points_possible,
    }


def create_assessment(
        submission_uuid,
        scorer_id,
        assessment_dict,
        rubric_dict,
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
        assessment_dict (dict): All related information for the assessment. An
            assessment contains points_earned, points_possible, and feedback.

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
        >>> assessment_dict = dict(
        >>>    options_selected={"clarity": "Very clear", "precision": "Somewhat precise"},
        >>>    feedback="Your submission was thrilling.",
        >>> )
        >>> create_assessment("1", "Tim", assessment_dict, rubric_dict)
    """
    try:
        submission = Submission.objects.get(uuid=submission_uuid)
        rubric = rubric_from_dict(rubric_dict)

        # Validate that the selected options matched the rubric
        # and raise an error if this is not the case
        try:
            option_ids = rubric.options_ids(assessment_dict["options_selected"])
        except InvalidOptionSelection as ex:
            msg = _("Selected options do not match the rubric: {error}").format(error=ex.message)
            raise PeerAssessmentRequestError(msg)

        feedback = assessment_dict.get('feedback', u'')
        peer_assessment = {
            "rubric": rubric.id,
            "scorer_id": scorer_id,
            "submission_uuid": submission.uuid,
            "score_type": PEER_TYPE,
            "feedback": feedback,
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
        AssessmentPart.add_to_assessment(assessment, option_ids)

        student_item = submission.student_item
        student_item_dict = StudentItemSerializer(student_item).data

        try:
            scorer_item = StudentItem.objects.get(
                student_id=scorer_id,
                item_id=student_item.item_id,
                course_id=student_item.course_id,
                item_type=student_item.item_type
            )
        except StudentItem.DoesNotExist:
            raise PeerAssessmentWorkflowError(_(
                "You must make a submission before assessing another student."))

        scorer_item_dict = StudentItemSerializer(scorer_item).data
        scorer_workflow = _get_latest_workflow(scorer_item_dict)
        workflow = _get_latest_workflow(student_item_dict)

        if not scorer_workflow:
            raise PeerAssessmentWorkflowError(_(
                "You must make a submission before assessing another student."))
        if not workflow:
            raise PeerAssessmentWorkflowError(_(
                "The submission you reviewed is not in the peer workflow. This "
                "assessment cannot be submitted unless the associated "
                "submission came from the peer workflow."))
        # Close the active assessment
        _close_active_assessment(scorer_workflow, submission_uuid, assessment)

        return full_assessment_dict(assessment)
    except DatabaseError:
        error_message = _(
            u"An error occurred while creating assessment {} for submission: "
            u"{} by: {}"
            .format(assessment_dict, submission_uuid, scorer_id)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)


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
            ).order_by( "-scored_at", "-id").select_related("rubric")[:1]
        )
        if not assessments:
            return None

        assessment = assessments[0]
        rubric_dict = RubricSerializer.serialized_from_cache(assessment.rubric)
        return {
            criterion["name"]: criterion["points_possible"]
            for criterion in rubric_dict["criteria"]
        }
    except Submission.DoesNotExist:
        return None
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


def has_finished_required_evaluating(student_item_dict, required_assessments):
    """Check if a student still needs to evaluate more submissions

    Per the contract of the peer assessment workflow, a student must evaluate a
    number of peers before receiving feedback on their submission.

    Args:
        student_item (dict): The student id is required to determine if the
            student has completed enough assessments, relative to the item id
            and course id available in the student item. This argument is
            required.
        required_assessments (int): The number of assessments a student has to
            submit before receiving the feedback on their submission. This is a
            required argument.

    Returns:
        tuple: True if the student has evaluated enough peer submissions to move
            through the peer assessment workflow. False if the student needs to
            evaluate more peer submissions. The second value is the count of
            assessments completed.

    Raises:
        PeerAssessmentRequestError: Raised when the student_id is invalid, or
            the required_assessments is not a positive integer.
        PeerAssessmentInternalError: Raised when there is an internal error
            while evaluating this workflow rule.

    Examples:
        >>> student_item_dict = dict(
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one",
        >>>    student_id="Bob",
        >>> )
        >>> has_finished_required_evaluating(student_item_dict, 3)
        True, 3

    """
    workflow = _get_latest_workflow(student_item_dict)
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
        student_item_dict,
        graded_by,
        over_grading=False):
    """Get a submission to peer evaluate.

    Retrieves a submission for assessment for the given student_item. This will
    not return a submission submitted by the requesting scorer. Submissions are
    returned based on how many assessments are still required, and if there are
    peers actively assessing a particular submission. If there are no
    submissions requiring assessment, a submission may be returned that will be
    'over graded', and the assessment will not be counted towards the overall
    grade.

    Args:
        student_item_dict (dict): The student item information from the student
            requesting a submission for assessment. The dict contains an
            item_id, course_id, and item_type, used to identify the unique
            question for the review, while the student_id is used to explicitly
            avoid giving the student their own submission.
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
    workflow = _get_latest_workflow(student_item_dict)
    if not workflow:
        raise PeerAssessmentWorkflowError(_(
            u"A Peer Assessment Workflow does not exist for the specified "
            u"student."))
    submission_uuid = _find_active_assessments(workflow)
    # If there is an active assessment for this user, get that submission,
    # otherwise, get the first assessment for review, otherwise, if over grading
    # is turned on, get the first submission available for over grading.
    if submission_uuid is None:
        submission_uuid = _get_submission_for_review(workflow, graded_by)
    if submission_uuid is None and over_grading:
        submission_uuid = _get_submission_for_over_grading(workflow)
    if submission_uuid:
        try:
            submission_data = sub_api.get_submission(submission_uuid)
            _create_peer_workflow_item(workflow, submission_uuid)
            return submission_data
        except sub_api.SubmissionDoesNotExist:
            error_message = _(
                u"Could not find a submission with the uuid {} for student {} "
                u"in the peer workflow."
                .format(submission_uuid, student_item_dict)
            )
            logger.exception(error_message)
            raise PeerAssessmentWorkflowError(error_message)
    else:
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
        PeerAssessmentInternalError: Raised when there is an internal error
            creating the Workflow.

    Examples:
        >>> create_peer_workflow("1")

    """
    try:
        submission = Submission.objects.get(uuid=submission_uuid)
        workflow = PeerWorkflow.objects.get_or_create(
            student_id=submission.student_item.student_id,
            course_id=submission.student_item.course_id,
            item_id=submission.student_item.item_id,
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


def create_peer_workflow_item(scorer, submission_uuid):
    """
    Begin peer-assessing a particular submission.
    Note that this does NOT pick the submission from the prioritized list of available submissions.
    Mainly useful for testing.

    Args:
        scorer (str): The ID of the scoring student.
        submission_uuid (str): The unique identifier of the submission being scored

    Returns:
        None

    Raises:
        PeerAssessmentWorkflowError: Could not find the workflow for the student.
        PeerAssessmentInternalError: Could not create the peer workflow item.
    """
    submission = get_submission_and_student(submission_uuid)
    student_item_dict = copy.copy(submission['student_item'])
    student_item_dict['student_id'] = scorer
    workflow = _get_latest_workflow(student_item_dict)
    _create_peer_workflow_item(workflow, submission_uuid)


def _get_latest_workflow(student_item_dict):
    """Given a student item, return the current workflow for this student.

    Given a student item, get the most recent workflow for the student.

    TODO: API doesn't take in current submission; do we pass that in, or get
    the latest workflow item? Currently using "latest".

    Args:
        student_item_dict (dict): Dictionary representation of a student item.
            The most recent workflow associated with this student item is
            returned.

    Returns:
        workflow (PeerWorkflow): The most recent peer workflow associated with
            this student item.

    Raises:
        PeerAssessmentWorkflowError: Thrown when no workflow can be found for
            the associated student item. This should always exist before a
            student is allow to request submissions for peer assessment.

    Examples:
        >>> student_item_dict = dict(
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one",
        >>>    student_id="Bob",
        >>> )
        >>> workflow = _get_latest_workflow(student_item_dict)
        {
            'student_id': u'Bob',
            'item_id': u'type_one',
            'course_id': u'course_1',
            'submission_uuid': u'1',
            'created_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 668850, tzinfo=<UTC>)
        }

    """
    try:
        workflows = PeerWorkflow.objects.filter(
            student_id=student_item_dict["student_id"],
            item_id=student_item_dict["item_id"],
            course_id=student_item_dict["course_id"]
        ).order_by("-created_at", "-id")
        return workflows[0] if workflows else None
    except DatabaseError:
        error_message = _(
            u"Error finding workflow for student {}. Workflow must be created "
            u"for student before beginning peer assessment."
            .format(student_item_dict)
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
        >>> workflow = _get_latest_workflow(student_item_dict)
        >>> _create_peer_workflow_item(workflow, "1")

    """
    try:
        peer_workflow = PeerWorkflow.objects.get(submission_uuid=submission_uuid)
        workflow_item, __ = PeerWorkflowItem.objects.get_or_create(
            scorer=workflow,
            author=peer_workflow,
            submission_uuid=submission_uuid
        )
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
        >>> workflow = _get_latest_workflow(student_item_dict)
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
    try:
        peer_workflows = list(PeerWorkflow.objects.raw(
            "select pw.id, pw.submission_uuid "
            "from assessment_peerworkflow pw "
            "left join assessment_peerworkflowitem pwi "
            "on pw.id=pwi.author_id "
            "where pw.item_id=%s "
            "and pw.course_id=%s "
            "and pw.student_id<>%s "
            "and pw.graded_count < %s "
            "and pw.id not in (select pwi.author_id from assessment_peerworkflowitem pwi where pwi.scorer_id=%s) "
            "and (pwi.scorer_id is NULL or pwi.assessment_id is not NULL or pwi.started_at > %s) "
            "group by pw.id "
            "having count(pwi.id) < %s "
            "limit 1; ",
            [
                workflow.item_id,
                workflow.course_id,
                workflow.student_id,
                graded_by,
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
    Specifically, this will construct a query that:
    1) selects all the peer workflows for the current course and item,
        excluding the current student
    2) checks all the assessments associated with those workflows, excluding
        the current student's assessments, and any workflows connected to them.
    3) checks to see if any unfinished assessments are expired
    4) Groups all the workflows with their collective assessments
    5) Orders them but their total assessments
    6) Returns the workflow with the fewest assessments.

    """
    try:
        peer_workflows = list(PeerWorkflow.objects.raw(
            "select pw.id, pw.submission_uuid "
            "from assessment_peerworkflow pw "
            "left join assessment_peerworkflowitem pwi "
            "on pw.id=pwi.author_id "
            "where pw.item_id=%s "
            "and pw.course_id=%s "
            "and pw.student_id<>%s "
            "and pw.id not in (select pwi.author_id from assessment_peerworkflowitem pwi where pwi.scorer_id=%s) "
            "group by pw.id "
            "order by count(pwi.id), pw.created_at, pw.id "
            "limit 1; ",
            [
                workflow.item_id,
                workflow.course_id,
                workflow.student_id,
                workflow.id
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


def _get_next_submission(order, workflow, *args):
    """Constructs a raw SQL query for over grading or general peer review

    Refactored function for retrieving the first submission that meets the
    criteria of the query, which is altered based on the parameters passed
    into the function.

    For example, for a general peer assessment query, the following would be
    the generated SQL query:

    select pw.id, pw.submission_uuid , pw.student_id
    from assessment_peerworkflow pw
    where pw.completed_at is NULL
    and pw.item_id='item_one'
    and pw.course_id='Demo_Course'
    and pw.student_id<>'Tim'
    and pw.id not in (select pwi.author_id from assessment_peerworkflowitem pwi where pwi.scorer_id=3159)
    and (select count(pwi.id) from assessment_peerworkflowitem pwi where pwi.scorer_id=3159)
    and (pw.started_at is NULL or pw.graded_count < 3 or (pw.graded_count = 3 and pw.started_at < '2014-03-14 20:09:04'))
    order by pw.created_at, pw.id
    limit 1;

    Args:
        order (str): A piece of the query that is unique to over grading or
            general peer review. This is inserted in the otherwise identical
            query.
        workflow (PeerWorkflow): The workflow associated with the student
            requesting a submission for peer assessment. Used to parametrize
            the query.

    Returns:
        A submission uuid for the submission that should be peer assessed.

    """



def _close_active_assessment(workflow, submission_uuid, assessment):
    """Associate the work item with a complete assessment.

    Updates a workflow item on the student's workflow with the associated
    assessment. When a workflow item has an assessment, it is considered
    finished.

    Args:
        workflow (PeerWorkflow): The scorer's workflow
        submission_uuid (str): The submission the scorer is grading.
        assessment (PeerAssessment): The associate assessment for this action.

    Examples:
        >>> student_item_dict = dict(
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one",
        >>>    student_id="Bob",
        >>> )
        >>> workflow = _get_latest_workflow(student_item_dict)
        >>> assessment = Assessment.objects.all()[0]
        >>> _close_active_assessment(workflow, "1", assessment)

    """
    try:
        item = workflow.graded.get(submission_uuid=submission_uuid)
        item.assessment = assessment
        item.scorer.graded_count += 1
        item.save()
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
        >>> workflow = _get_latest_workflow(student_item_dict)
        >>> _num_peers_graded(workflow, 3)
        True
    """
    return workflow.graded.filter(assessment__isnull=False).count()


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
