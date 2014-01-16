from django.db import models

MAX_LENGTH = 1028
ESSAY_BODY_MAX_LENGTH = 8192
GRADING_TYPES = (
    ('PE', 'Peer Assessment'),
)


class Submission(models.Model):
    student_id = models.CharField(max_length=MAX_LENGTH, db_index=True)
    location_id = models.CharField(max_length=MAX_LENGTH, default="")
    course_id = models.CharField(max_length=MAX_LENGTH, default="")
    essay_body = models.CharField(max_length=ESSAY_BODY_MAX_LENGTH, default="")
    preferred_grading = models.CharField(max_length=2, choices=GRADING_TYPES)
    submitted_date = models.DateTimeField()


class Scoring(models.Model):
    points_earned = models.PositiveIntegerField(default=0)
    points_possible = models.PositiveIntegerField(default=0)
    scored_date = models.DateTimeField()
    student_id = models.CharField(max_length=MAX_LENGTH)
    score_type = models.CharField(max_length=2, choices=GRADING_TYPES)
    confidence = models.FloatField(default=0.0)
    included = models.BooleanField(default=True)
    submission = models.ForeignKey(Submission)


class Feedback(models.Model):
    text = models.CharField(max_length=MAX_LENGTH, default="")
    score = models.ForeignKey(Scoring)
