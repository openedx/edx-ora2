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
    AssessmentSerializer, AssessmentFeedbackSerializer,
    rubric_from_dict, serialize_assessments
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
    return _check_student_done_grading(workflow, requirements["must_grade"])


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

    assessments = Assessment.objects.filter(
        submission_uuid=submission_uuid, score_type=PEER_TYPE
    )[:requirements["must_be_graded_by"]]

    submission_finished = assessments.count() >= requirements["must_be_graded_by"]

    if not submission_finished:
        return None

    PeerWorkflowItem.objects.filter(
        assessment__in=[a.pk for a in assessments]
    ).update(scored=True)

    PeerWorkflow.objects.filter(submission_uuid=submission_uuid).update(
        completed_at=timezone.now()
    )
    return {
        "points_earned": sum(
            get_assessment_median_scores(submission_uuid).values()
        ),
        "points_possible": assessments[0].points_possible,
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
        AssessmentPart.objects.bulk_create([
            AssessmentPart(assessment=assessment, option_id=option_id)
            for option_id in option_ids
        ])

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

        return peer_serializer.data
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
        serialized_assessments = serialize_assessments(
            Assessment.objects.filter(submission_uuid=submission_uuid).order_by( "-scored_at", "-id")[:1]
        )
        if not serialized_assessments:
            return None

        assessment = serialized_assessments[0]
        return {
            criterion["name"]: criterion["points_possible"]
            for criterion in assessment["rubric"]["criteria"]
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
        assessments = PeerWorkflowItem.get_scored_assessments(submission_uuid)
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
    count = 0
    if workflow:
        done = _check_student_done_grading(workflow, required_assessments)
        count = workflow.items.all().exclude(assessment=-1).count()
    return done, count


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


def create_peer_workflow_item(scorer_id, submission_uuid):
    """
    Begin peer-assessing a particular submission.
    Note that this does NOT pick the submission from the prioritized list of available submissions.
    Mainly useful for testing.

    Args:
        scorer_id (str): The ID of the scoring student.
        submission_uuid (str): The unique identifier of the submission being scored

    Returns:
        None

    Raises:
        PeerAssessmentWorkflowError: Could not find the workflow for the student.
        PeerAssessmentInternalError: Could not create the peer workflow item.
    """
    submission = get_submission_and_student(submission_uuid)
    student_item_dict = copy.copy(submission['student_item'])
    student_item_dict['student_id'] = scorer_id
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
        workflow_item, __ = PeerWorkflowItem.objects.get_or_create(
            scorer_id=workflow,
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
    workflows = workflow.items.filter(
        assessment=-1,
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
    order = " having count(pwi.id) < %s order by pw.created_at, pw.id "
    timeout = (timezone.now() - TIME_LIMIT).strftime("%Y-%m-%d %H:%M:%S")
    sub = _get_next_submission(
        order,
        workflow,
        workflow.item_id,
        workflow.course_id,
        workflow.student_id,
        timeout,
        graded_by
    )
    return sub


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
    order = " order by c, pw.created_at, pw.id "
    timeout = (timezone.now() - TIME_LIMIT).strftime("%Y-%m-%d %H:%M:%S")
    return _get_next_submission(
        order,
        workflow,
        workflow.item_id,
        workflow.course_id,
        workflow.student_id,
        timeout
    )


def _get_next_submission(order, workflow, *args):
    """Constructs a raw SQL query for over grading or general peer review

    Refactored function for retrieving the first submission that meets the
    criteria of the query, which is altered based on the parameters passed
    into the function.

    For example, for a general peer assessment query, the following would be
    the generated SQL query:

    select pw.id, pw.submission_uuid , count(pwi.id) as c
    from assessment_peerworkflow pw
    left join assessment_peerworkflowitem pwi
    on pw.submission_uuid=pwi.submission_uuid
    where pw.item_id='item_one'
    and pw.course_id='Demo_Course'
    and pw.student_id<>'Buffy1'
    and pw.submission_uuid<>'bc164f09-eb14-4b1d-9ba8-bb2c1c924fba'
    and pw.submission_uuid<>'7c5e7db4-e82d-45e1-8fda-79c5deaa16d5'
    and pw.submission_uuid<>'9ba64ff5-f18e-4794-b45b-cee26248a0a0'
    and pw.submission_uuid<>'cdd6cf7a-2787-43ec-8d31-62fdb14d4e09'
    and pw.submission_uuid<>'ebc7d4e1-1577-4443-ab58-2caad9a10837'
    and (pwi.scorer_id_id is NULL or pwi.assessment<>-1 or pwi.started_at > '2014-03-04 20:09:04')
    group by pw.submission_uuid having count(pwi.id) < 3
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
    try:

        exclude = ""
        for item in workflow.items.all():
            exclude += "and pw.submission_uuid<>'{}' ".format(item.submission_uuid)
        raw_query = (
            "select pw.id, pw.submission_uuid, pwi.scorer_id_id, count(pwi.id) as c "
            "from assessment_peerworkflow pw "
            "left join assessment_peerworkflowitem pwi "
            "on pw.submission_uuid=pwi.submission_uuid "
            "where pw.item_id=%s "
            "and pw.course_id=%s "
            "and pw.student_id<>%s "
            "{} "
            " and (pwi.scorer_id_id is NULL or pwi.assessment<>-1 or pwi.started_at > %s) "
            "group by pw.submission_uuid "
            "{} "
            "limit 1; "
        )

        query = raw_query.format(exclude, order)
        peer_workflows = PeerWorkflow.objects.raw(query, args)
        if len(list(peer_workflows)) == 0:
            return None

        return peer_workflows[0].submission_uuid
    except DatabaseError:
        error_message = _(
            u"An internal error occurred while retrieving a peer submission "
            u"for student {}".format(workflow)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)


def _assessors_count(peer_workflow):
    return PeerWorkflowItem.objects.filter(
        ~Q(assessment=-1) |
        Q(assessment=-1, started_at__gt=timezone.now() - TIME_LIMIT),
        submission_uuid=peer_workflow.submission_uuid).count()


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
        item = workflow.items.get(submission_uuid=submission_uuid)
        item.assessment = assessment.id
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


def _check_student_done_grading(workflow, must_grade):
    """Checks if the student has graded enough peers.

    Determines if the student has graded enough peers.

    Args:
        workflow (PeerWorkflow): The workflow associated with the current
            student.
        must_grade (int): The number of submissions the student has to peer
            assess before they are finished.

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
        >>> _check_student_done_grading(workflow, 3)
        True
    """
    return workflow.items.all().exclude(assessment=-1).count() >= must_grade


def get_assessment_feedback(submission_uuid):
    """Retrieve a feedback object for an assessment whether it exists or not.

    Gets or creates a new Assessment Feedback model for the given submission.

    Args:
        submission_uuid: The submission we want to create assessment feedback
            for.
    Returns:
        The assessment feedback object that exists, or a newly created model.
    Raises:
        PeerAssessmentInternalError: Raised when the AssessmentFeedback cannot
            be created or retrieved because of internal exceptions.

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
    """Set a feedback object for an assessment to have some new values.

    Sets or updates the assessment feedback with the given values in the
    dict.

    Args:
        feedback_dict (dict): A dictionary of all the values to update or create
            a new assessment feedback.
    Returns:
        The modified or created feedback.
    """
    submission_uuid = feedback_dict.get('submission_uuid')
    if not submission_uuid:
        error_message = u"An error occurred creating assessment feedback: bad or missing submission_uuid."
        logger.error(error_message)
        raise PeerAssessmentRequestError(error_message)
    try:
        assessments = PeerWorkflowItem.get_scored_assessments(submission_uuid)
    except DatabaseError:
        error_message = (
            u"An error occurred getting database state to set assessment feedback for {}."
            .format(submission_uuid)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)
    feedback = AssessmentFeedbackSerializer(data=feedback_dict)
    if not feedback.is_valid():
        raise PeerAssessmentRequestError(feedback.errors)

    try:
        feedback_model = feedback.save()
        # Assessments associated with feedback must be saved after the row is
        # committed to the database in order to associated the PKs across both
        # tables.
        feedback_model.assessments.add(*assessments)
    except DatabaseError:
        error_message = (
            u"An error occurred saving assessment feedback for {}."
            .format(submission_uuid)
        )
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message)
    return feedback.data
