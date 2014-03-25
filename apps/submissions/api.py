"""
Public interface for the submissions app.

"""
import copy
import logging

from django.core.cache import cache
from django.conf import settings
from django.db import IntegrityError, DatabaseError
from django.utils.encoding import force_unicode

from submissions.serializers import (
    SubmissionSerializer, StudentItemSerializer, ScoreSerializer, JsonFieldError
)
from submissions.models import Submission, StudentItem, Score, ScoreSummary

logger = logging.getLogger("submissions.api")


class SubmissionError(Exception):
    """An error that occurs during submission actions.

    This error is raised when the submission API cannot perform a requested
    action.

    """
    pass


class SubmissionInternalError(SubmissionError):
    """An error internal to the Submission API has occurred.

    This error is raised when an error occurs that is not caused by incorrect
    use of the API, but rather internal implementation of the underlying
    services.

    """
    pass


class SubmissionNotFoundError(SubmissionError):
    """This error is raised when no submission is found for the request.

    If a state is specified in a call to the API that results in no matching
    Submissions, this error may be raised.

    """
    pass


class SubmissionRequestError(SubmissionError):
    """This error is raised when there was a request-specific error

    This error is reserved for problems specific to the use of the API.

    """

    def __init__(self, field_errors):
        Exception.__init__(self, repr(field_errors))
        self.field_errors = copy.deepcopy(field_errors)


def create_submission(student_item_dict, answer, submitted_at=None,
                      attempt_number=None):
    """Creates a submission for assessment.

    Generic means by which to submit an answer for assessment.

    Args:
        student_item_dict (dict): The student_item this
            submission is associated with. This is used to determine which
            course, student, and location this submission belongs to.
        answer (JSON-serializable): The answer given by the student to be assessed.
        submitted_at (datetime): The date in which this submission was submitted.
            If not specified, defaults to the current date.
        attempt_number (int): A student may be able to submit multiple attempts
            per question. This allows the designated attempt to be overridden.
            If the attempt is not specified, it will take the most recent
            submission, as specified by the submitted_at time, and use its
            attempt_number plus one.

    Returns:
        dict: A representation of the created Submission. The submission
        contains five attributes: student_item, attempt_number, submitted_at,
        created_at, and answer. 'student_item' is the ID of the related student
        item for the submission. 'attempt_number' is the attempt this submission
        represents for this question. 'submitted_at' represents the time this
        submission was submitted, which can be configured, versus the
        'created_at' date, which is when the submission is first created.

    Raises:
        SubmissionRequestError: Raised when there are validation errors for the
            student item or submission. This can be caused by the student item
            missing required values, the submission being too long, the
            attempt_number is negative, or the given submitted_at time is invalid.
        SubmissionInternalError: Raised when submission access causes an
            internal error.

    Examples:
        >>> student_item_dict = dict(
        >>>    student_id="Tim",
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one"
        >>> )
        >>> create_submission(student_item_dict, "The answer is 42.", datetime.utcnow, 1)
        {
            'student_item': 2,
            'attempt_number': 1,
            'submitted_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 649284 tzinfo=<UTC>),
            'created_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 668850, tzinfo=<UTC>),
            'answer': u'The answer is 42.'
        }

    """
    student_item_model = _get_or_create_student_item(student_item_dict)
    if attempt_number is None:
        try:
            submissions = Submission.objects.filter(
                student_item=student_item_model)[:1]
        except DatabaseError:
            error_message = u"An error occurred while filtering submissions for student item: {}".format(
                student_item_dict)
            logger.exception(error_message)
            raise SubmissionInternalError(error_message)
        attempt_number = submissions[0].attempt_number + 1 if submissions else 1

    model_kwargs = {
        "student_item": student_item_model.pk,
        "answer": answer,
        "attempt_number": attempt_number,
    }
    if submitted_at:
        model_kwargs["submitted_at"] = submitted_at

    try:
        submission_serializer = SubmissionSerializer(data=model_kwargs)
        if not submission_serializer.is_valid():
            raise SubmissionRequestError(submission_serializer.errors)
        submission_serializer.save()

        sub_data = submission_serializer.data
        logger.info(
            u"Created submission uuid={submission_uuid} for "
            u"(course_id={course_id}, item_id={item_id}, "
            u"anonymous_student_id={anonymous_student_id})"
            .format(
                submission_uuid=sub_data["uuid"],
                course_id=student_item_dict["course_id"],
                item_id=student_item_dict["item_id"],
                anonymous_student_id=student_item_dict["student_id"]
            )
        )

        return sub_data

    except JsonFieldError:
        error_message = u"Could not serialize JSON field in submission {} for student item {}".format(
            model_kwargs, student_item_dict
        )
        raise SubmissionRequestError(error_message)
    except DatabaseError:
        error_message = u"An error occurred while creating submission {} for student item: {}".format(
            model_kwargs,
            student_item_dict
        )
        logger.exception(error_message)
        raise SubmissionInternalError(error_message)


def get_submission(submission_uuid):
    """Retrieves a single submission by uuid.

    Args:
        submission_uuid (str): Identifier for the submission.

    Raises:
        SubmissionNotFoundError: Raised if the submission does not exist.
        SubmissionRequestError: Raised if the search parameter is not a string.
        SubmissionInternalError: Raised for unknown errors.

    Examples:
        >>> get_submission("20b78e0f32df805d21064fc912f40e9ae5ab260d")
        {
            'student_item': 2,
            'attempt_number': 1,
            'submitted_at': datetime.datetime(2014, 1, 29, 23, 14, 52, 649284, tzinfo=<UTC>),
            'created_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 668850, tzinfo=<UTC>),
            'answer': u'The answer is 42.'
        }

    """
    if not isinstance(submission_uuid, basestring):
        raise SubmissionRequestError(
            "submission_uuid ({!r}) must be a string type".format(submission_uuid)
        )

    cache_key = "submissions.submission.{}".format(submission_uuid)
    cached_submission_data = cache.get(cache_key)
    if cached_submission_data:
        logger.info("Get submission {} (cached)".format(submission_uuid))
        return cached_submission_data

    try:
        submission = Submission.objects.get(uuid=submission_uuid)
        submission_data = SubmissionSerializer(submission).data
        cache.set(cache_key, submission_data)
    except Submission.DoesNotExist:
        logger.error("Submission {} not found.".format(submission_uuid))
        raise SubmissionNotFoundError(
            u"No submission matching uuid {}".format(submission_uuid)
        )
    except Exception as exc:
        # Something very unexpected has just happened (like DB misconfig)
        err_msg = "Could not get submission due to error: {}".format(exc)
        logger.exception(err_msg)
        raise SubmissionInternalError(err_msg)

    logger.info("Get submission {}".format(submission_uuid))
    return submission_data


def get_submission_and_student(uuid):
    """
    Retrieve a submission by its unique identifier, including the associated student item.

    Args:
        uuid (str): the unique identifier of the submission.

    Returns:
        Serialized Submission model (dict) containing a serialized StudentItem model
        If the submission does not exist, return None
    """
    try:
        submission = Submission.objects.get(uuid=uuid)
    except Submission.DoesNotExist:
        return None

    # There is probably a more idiomatic way to do this using the Django REST framework
    try:
        submission_dict = SubmissionSerializer(submission).data
        submission_dict['student_item'] = StudentItemSerializer(submission.student_item).data
    except Exception as ex:
        err_msg = "Could not get submission due to error: {}".format(ex)
        logger.exception(err_msg)
        raise SubmissionInternalError(err_msg)

    return submission_dict


def get_submissions(student_item_dict, limit=None):
    """Retrieves the submissions for the specified student item,
    ordered by most recent submitted date.

    Returns the submissions relative to the specified student item. Exception
    thrown if no submission is found relative to this location.

    Args:
        student_item_dict (dict): The location of the problem this submission is
            associated with, as defined by a course, student, and item.
        limit (int): Optional parameter for limiting the returned number of
            submissions associated with this student item. If not specified, all
            associated submissions are returned.

    Returns:
        List dict: A list of dicts for the associated student item. The submission
        contains five attributes: student_item, attempt_number, submitted_at,
        created_at, and answer. 'student_item' is the ID of the related student
        item for the submission. 'attempt_number' is the attempt this submission
        represents for this question. 'submitted_at' represents the time this
        submission was submitted, which can be configured, versus the
        'created_at' date, which is when the submission is first created.

    Raises:
        SubmissionRequestError: Raised when the associated student item fails
            validation.
        SubmissionNotFoundError: Raised when a submission cannot be found for
            the associated student item.

    Examples:
        >>> student_item_dict = dict(
        >>>    student_id="Tim",
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one"
        >>> )
        >>> get_submissions(student_item_dict, 3)
        [{
            'student_item': 2,
            'attempt_number': 1,
            'submitted_at': datetime.datetime(2014, 1, 29, 23, 14, 52, 649284, tzinfo=<UTC>),
            'created_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 668850, tzinfo=<UTC>),
            'answer': u'The answer is 42.'
        }]

    """
    student_item_model = _get_or_create_student_item(student_item_dict)
    try:
        submission_models = Submission.objects.filter(
            student_item=student_item_model)
    except DatabaseError:
        error_message = (
            u"Error getting submission request for student item {}"
            .format(student_item_dict)
        )
        logger.exception(error_message)
        raise SubmissionNotFoundError(error_message)

    if limit:
        submission_models = submission_models[:limit]

    return SubmissionSerializer(submission_models, many=True).data


def get_score(student_item):
    """Get the score for a particular student item

    Each student item should have a unique score. This function will return the
    score if it is available. A score is only calculated for a student item if
    it has completed the workflow for a particular assessment module.

    Args:
        student_item (dict): The dictionary representation of a student item.
            Function returns the score related to this student item.

    Returns:
        score (dict): The score associated with this student item. None if there
            is no score found.

    Raises:
        SubmissionInternalError: Raised if a score cannot be retrieved because
            of an internal server error.

    Examples:
        >>> student_item = {
        >>>     "student_id":"Tim",
        >>>     "course_id":"TestCourse",
        >>>     "item_id":"u_67",
        >>>     "item_type":"openassessment"
        >>> }
        >>>
        >>> get_score(student_item)
        [{
            'student_item': 2,
            'submission': 2,
            'points_earned': 8,
            'points_possible': 20,
            'created_at': datetime.datetime(2014, 2, 7, 18, 30, 1, 807911, tzinfo=<UTC>)
        }]

    """
    try:
        student_item_model = StudentItem.objects.get(**student_item)
        score = ScoreSummary.objects.get(student_item=student_item_model).latest
    except (ScoreSummary.DoesNotExist, StudentItem.DoesNotExist):
        return None

    return ScoreSerializer(score).data


def get_scores(course_id, student_id):
    """Return a dict mapping item_ids -> (points_earned, points_possible).

    This method would be used by an LMS to find all the scores for a given
    student in a given course.

    Args:
        course_id (str): Course ID, used to do a lookup on the `StudentItem`.
        student_id (str): Student ID, used to do a lookup on the `StudentItem`.

    Returns:
        dict: The keys are `item_id`s (`str`) and the values are tuples of
        `(points_earned, points_possible)`. All points are integer values and
        represent the raw, unweighted scores. Submissions does not have any
        concept of weights. If there are no entries matching the `course_id` or
        `student_id`, we simply return an empty dictionary. This is not
        considered an error because there might be many queries for the progress
        page of a person who has never submitted anything.
    """
    try:
        score_summaries = ScoreSummary.objects.filter(
            student_item__course_id=course_id,
            student_item__student_id=student_id,
        ).select_related('latest', 'student_item')
    except DatabaseError:
        msg = u"Could not fetch scores for course {}, student {}".format(
            course_id, student_id
        )
        logger.exception(msg)
        raise SubmissionInternalError(msg)
    scores = {
        summary.student_item.item_id:
            (summary.latest.points_earned, summary.latest.points_possible)
        for summary in score_summaries
    }
    return scores


def get_latest_score_for_submission(submission_uuid):
    try:
        score = Score.objects.filter(
            submission__uuid=submission_uuid
        ).order_by("-id").select_related("submission")[0]
    except IndexError:
        return None

    return ScoreSerializer(score).data


def set_score(submission_uuid, points_earned, points_possible):
    """Set a score for a particular submission.

    Sets the score for a particular submission. This score is calculated
    externally to the API.

    Args:
        student_item (dict): The student item associated with this score. This
            dictionary must contain a course_id, student_id, and item_id.
        submission_uuid (str): The submission associated with this score.
        submission_uuid (str): UUID for the submission (must exist).
        points_earned (int): The earned points for this submission.
        points_possible (int): The total points possible for this particular
            student item.

    Returns:
        None

    Raises:
        SubmissionInternalError: Thrown if there was an internal error while
            attempting to save the score.
        SubmissionRequestError: Thrown if the given student item or submission
            are not found.

    Examples:
        >>> set_score("a778b933-9fb3-11e3-9c0f-040ccee02800", 11, 12)
        {
            'student_item': 2,
            'submission': 1,
            'points_earned': 11,
            'points_possible': 12,
            'created_at': datetime.datetime(2014, 2, 7, 20, 6, 42, 331156, tzinfo=<UTC>)
        }

    """
    try:
        submission_model = Submission.objects.get(uuid=submission_uuid)
    except Submission.DoesNotExist:
        raise SubmissionNotFoundError(
            u"No submission matching uuid {}".format(submission_uuid)
        )
    except DatabaseError:
        error_msg = u"Could not retrieve student item: {} or submission {}.".format(
            submission_uuid
        )
        logger.exception(error_msg)
        raise SubmissionRequestError(error_msg)

    score = ScoreSerializer(
        data={
            "student_item": submission_model.student_item.pk,
            "submission": submission_model.pk,
            "points_earned": points_earned,
            "points_possible": points_possible,
        }
    )
    if not score.is_valid():
        logger.exception(score.errors)
        raise SubmissionInternalError(score.errors)

    # When we save the score, a score summary will be created if
    # it does not already exist.
    # When the database's isolation level is set to repeatable-read,
    # it's possible for a score summary to exist for this student item,
    # even though we cannot retrieve it.
    # In this case, we assume that someone else has already created
    # a score summary and ignore the error.
    try:
        score.save()
        logger.info(
            "Score of ({}/{}) set for submission {}"
            .format(points_earned, points_possible, submission_uuid)
        )
    except IntegrityError:
        pass


def _get_or_create_student_item(student_item_dict):
    """Gets or creates a Student Item that matches the values specified.

    Attempts to get the specified Student Item. If it does not exist, the
    specified parameters are validated, and a new Student Item is created.

    Args:
        student_item_dict (dict): The dict containing the student_id, item_id,
            course_id, and item_type that uniquely defines a student item.

    Returns:
        StudentItem: The student item that was retrieved or created.

    Raises:
        SubmissionInternalError: Thrown if there was an internal error while
            attempting to create or retrieve the specified student item.
        SubmissionRequestError: Thrown if the given student item parameters fail
            validation.

    Examples:
        >>> student_item_dict = dict(
        >>>    student_id="Tim",
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one"
        >>> )
        >>> _get_or_create_student_item(student_item_dict)
        {'item_id': 'item_1', 'item_type': 'type_one', 'course_id': 'course_1', 'student_id': 'Tim'}

    """
    try:
        try:
            return StudentItem.objects.get(**student_item_dict)
        except StudentItem.DoesNotExist:
            student_item_serializer = StudentItemSerializer(
                data=student_item_dict)
            if not student_item_serializer.is_valid():
                raise SubmissionRequestError(student_item_serializer.errors)
            return student_item_serializer.save()
    except DatabaseError:
        error_message = u"An error occurred creating student item: {}".format(
            student_item_dict)
        logger.exception(error_message)
        raise SubmissionInternalError(error_message)
