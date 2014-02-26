"""
Public interface for the submissions app.

"""
import copy
import logging

from django.db import DatabaseError
from django.utils.encoding import force_unicode

from submissions.serializers import SubmissionSerializer, StudentItemSerializer, ScoreSerializer
from submissions.models import Submission, StudentItem, Score


logger = logging.getLogger(__name__)


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
        answer (str): The answer given by the student to be assessed.
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

    try:
        answer = force_unicode(answer)
    except UnicodeDecodeError:
        raise SubmissionRequestError(
            u"Submission answer could not be properly decoded to unicode.")

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
        return submission_serializer.data
    except DatabaseError:
        error_message = u"An error occurred while creating submission {} for student item: {}".format(
            model_kwargs,
            student_item_dict
        )
        logger.exception(error_message)
        raise SubmissionInternalError(error_message)


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
    student_item_model = StudentItem.objects.get(**student_item)
    scores = Score.objects.filter(student_item=student_item_model)
    return ScoreSerializer(scores, many=True).data


def get_scores(course_id, student_id, types=None):
    pass


def set_score(student_item, submission, score, points_possible):
    """Set a score for a particular student item, submission pair.

    Sets the score for a particular student item and submission pair. This score
    is calculated externally to the API.

    Args:
        student_item (dict): The student item associated with this score. This
            dictionary must contain a course_id, student_id, and item_id.
        submission (dict): The submission associated with this score. This
            dictionary must contain all submission fields to properly get a
            unique submission item.
        score (int): The score to associate with the given submission and
            student item.
        points_possible (int): The total points possible for this particular
            student item.

    Returns:
        (dict): The dictionary representation of the saved score.

    Raises:
        SubmissionInternalError: Thrown if there was an internal error while
            attempting to save the score.
        SubmissionRequestError: Thrown if the given student item or submission
            are not found.

    Examples:
        >>> student_item_dict = dict(
        >>>    student_id="Tim",
        >>>    item_id="item_1",
        >>>    course_id="course_1",
        >>>    item_type="type_one"
        >>> )
        >>>
        >>> submission_dict = dict(
        >>>    student_item=2,
        >>>    attempt_number=1,
        >>>    submitted_at=datetime.datetime(2014, 1, 29, 23, 14, 52, 649284, tzinfo=<UTC>),
        >>>    created_at=datetime.datetime(2014, 1, 29, 17, 14, 52, 668850, tzinfo=<UTC>),
        >>>    answer=u'The answer is 42.'
        >>> )
        >>> set_score(student_item_dict, submission_dict, 11, 12)
        {
            'student_item': 2,
            'submission': 1,
            'points_earned': 11,
            'points_possible': 12,
            'created_at': datetime.datetime(2014, 2, 7, 20, 6, 42, 331156, tzinfo=<UTC>)
        }

    """
    try:
        student_item_model = StudentItem.objects.get(**student_item)
        submission_model = Submission.objects.get(**submission)
    except DatabaseError:
        error_msg = u"Could not retrieve student item: {} or submission {}.".format(
            student_item, submission
        )
        logger.exception(error_msg)
        raise SubmissionRequestError(error_msg)

    score = ScoreSerializer(
        data={
            "student_item": student_item_model.pk,
            "submission": submission_model.pk,
            "points_earned": score,
            "points_possible": points_possible,
        }
    )
    if not score.is_valid():
        logger.exception(score.errors)
        raise SubmissionInternalError(score.errors)
    score.save()
    return score.data


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
