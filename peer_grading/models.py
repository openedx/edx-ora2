from django.db import models

MAX_LENGTH = 1028

class PeerGradedEssay(models.Model):
    student_id = models.CharField(max_length=MAX_LENGTH, db_index=True)
    problem_id = models.CharField(max_length=MAX_LENGTH, default="")
    essay_body = models.CharField(max_length=MAX_LENGTH, default="")
    grades = models.CharField(max_length=MAX_LENGTH, default="")
    status = models.CharField(max_length=MAX_LENGTH, default="")


class PeerGradingStatus(models.Model):
    student_id = models.CharField(max_length=MAX_LENGTH, db_index=True)
    problem_id = models.CharField(max_length=MAX_LENGTH, default="")
    grading_status = models.CharField(max_length=MAX_LENGTH, default="")