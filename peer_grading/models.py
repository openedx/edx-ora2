from django.db import models
from common_grading.models import MAX_LENGTH


class Status(models.Model):
    student_id = models.CharField(max_length=MAX_LENGTH, db_index=True)
    problem_id = models.CharField(max_length=MAX_LENGTH, default="")
    grading_status = models.CharField(max_length=MAX_LENGTH, default="")