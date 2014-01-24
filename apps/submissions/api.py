"""
Public interface for the submissions app.

"""
from django.db import DatabaseError
from django.utils.encoding import force_unicode

from submissions.serializers import SubmissionSerializer
from submissions.models import Submission, StudentItem, SubmissionStruct


class SubmissionAccessError(Exception):
    pass

class SubmissionNotFoundError(Exception):
    pass


def create_submission(student_item_struct, answer, submitted_at=None,
                      attempt_number=None):
    """Creates a submission for evaluation.

    Generic means by which to submit an answer for evaluation.

    Args:
        student_item_struct (StudentItemStruct): The student_item this
            submission is associated with. This is used to determine which
            course, student, and location this submission belongs to.
        answer (str): The answer given by the student to be evaluated.
        submitted_at (date): The date in which this submission was submitted.
            If not specified, defaults to the current date.
        attempt_number (int): A student may be able to submit multiple attempts
            per question. This allows the designated attempt to be overridden.
            If the attempt is not specified, it will be incremented by the
            number of submissions associated with this student_item.

    Returns:
        SubmissionStruct: A representation of the created Submission.

    Raises:
        SubmissionAccessError: Raised when information regarding the student
            item cannot be accessed or the submission cannot be saved.

    """
    try:
        student_item_model, _ = StudentItem.objects.get_or_create(
            student_item_struct._asdict())
    except DatabaseError as err:
        raise SubmissionAccessError(err)


    if attempt_number is None:
        try:
            submissions = Submission.objects.filter(
                student_item=student_item_model)[:0]
        except DatabaseError as err:
            raise SubmissionAccessError(err)
        attempt_number = submissions[0].attempt_number + 1 if submissions else 1

    model_kwargs = {
        "student_item": student_item_model,
        "answer": force_unicode(answer),
        "attempt_number": attempt_number,
    }
    if submitted_at:
        model_kwargs["submitted_at"] = submitted_at

    try:
        submission = Submission.objects.create(**model_kwargs)
    except DatabaseError as err:
        raise SubmissionAccessError(err)
    return SubmissionStruct(**SubmissionSerializer(submission).data)


def get_submissions(student_item_struct, limit=None):
    """Retrieves the submissions for the specified student item,
    ordered by most recent submitted date.

    Returns the submissions relative to the specified student item. Exception
    thrown if no submission is found relative to this location.

    Args:
        student_item_struct (StudentItemStruct): The location of the problem
            this submission is associated with, as defined by a course, student,
            and item.
        limit (int): Optional parameter for limiting the returned number of
            submissions associated with this student item. If not specified, all
            associated submissions are returned.

    Returns:
        List SubmissionStruct: A list of SubmissionStruct for the associated
            student item.

    Raises:
        SubmissionAccessError: Raised when the associated student item cannot
            be accessed.
        SubmissionNotFoundError: Raised when a submission cannot be found for
            the associated student item.

    """
    try:
        student_item_model, _ = StudentItem.objects.get_or_create(
            student_item_struct._asdict())
    except DatabaseError as err:
        raise SubmissionAccessError(err)

    try:
        submission_models = Submission.objects.filter(
            student_item=student_item_model)
    except DatabaseError:
        raise SubmissionNotFoundError()

    if limit:
        submission_models = submission_models[:limit]

    return [SubmissionStruct(**SubmissionSerializer(submission).data) for
            submission in submission_models]


def get_score(student_item):
    pass


def get_scores(course_id, student_id, types=None):
    pass


def set_score(student_item):
    pass
