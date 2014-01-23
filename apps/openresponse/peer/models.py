"""
This would hold models related to the peer response workflow. There's going to
be a lot here, like rubrics and such.

"""
from django.db import models
from django.utils.timezone import now


class PeerEvaluation(models.Model):
    # submission = models.ForeignKey(Submission)
    points_earned = models.PositiveIntegerField(default=0)
    points_possible = models.PositiveIntegerField(default=0)
    scored_at = models.DateTimeField(default=now, db_index=True)
    scorer_id = models.CharField(max_length=255, db_index=True)
    score_type = models.CharField(max_length=2)
    feedback = models.TextField(max_length=10000, default="")

