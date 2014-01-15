from django.db import models

MAX_LENGTH = 1028

class Essay(models.Model):
    student_id = models.CharField(max_length=MAX_LENGTH, db_index=True)
    location_id = models.CharField(max_length=MAX_LENGTH, default="")
    course_id = models.CharField(max_length=MAX_LENGTH, default="")
    essay_body = models.CharField(max_length=MAX_LENGTH, default="")
    scoring_type = models.CharField(max_length=MAX_LENGTH, default="")
    scores = models.CharField(max_length=MAX_LENGTH, default="")
    submitted_date = models.DateTimeField()


class Scoring(models.Model):
    points_earned = models.PositiveIntegerField(default=0)
    points_possible = models.PositiveIntegerField(default=0)
    feedback = models.CharField(max_length=MAX_LENGTH, default="")  # TODO how to link to feedback keys?
    scored_date = models.DateTimeField()
    student_id = models.CharField(max_length=MAX_LENGTH)
    score_type = models.CharField(max_length=MAX_LENGTH, default="")
    confidence = models.FloatField(default=0.0)
    included = models.BooleanField(default=True)

class Feedback(models.Model):
    text = models.CharField(max_length=MAX_LENGTH, default="")
    scoring = models.CharField(max_length=MAX_LENGTH, default="")  # TODO Link to Scoring keys.
