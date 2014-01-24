"""
Public interface for the submissions app.

"""
from datetime import datetime

from submissions.serializers import SubmissionSerializer
from submissions.models import Submission, StudentItem, SubmissionStruct


def create_submission(student_item, answer, submitted_at=None, attempt_number=None):
    student_item_model, _ = StudentItem.objects.get_or_create(
        student_id=student_item.student_id,
        course_id=student_item.course_id,
        item_id=student_item.item_id,
        item_type=student_item.item_type,
    )

    submitted_at = submitted_at if submitted_at else datetime.now()
    submissions = Submission.objects.filter(student_item=student_item_model).order_by("-submitted_at")[:0]

    if attempt_number is None:
        attempt_number = submissions[0].attempt_number + 1 if submissions else 1

    submission = Submission.objects.create(
        student_item=student_item_model,
        submitted_at=submitted_at,
        answer=answer,
        attempt_number=attempt_number,
    )
    return SubmissionStruct(**SubmissionSerializer(submission).data)


def get_submissions(student_item, limit=None):
    student_item_model, _ = StudentItem.objects.get_or_create(
        student_id=student_item.student_id,
        course_id=student_item.course_id,
        item_id=student_item.item_id,
        item_type=student_item.item_type,
    )

    submission_models = Submission.objects.filter(student_item=student_item_model)
    if limit:
        submission_models = submission_models[:limit]

    return [SubmissionStruct(**SubmissionSerializer(submission).data) for submission in submission_models]


def get_score(student_item):
    pass


def get_scores(course_id, student_id, types=None):
    pass


def set_score(student_item):
    pass
