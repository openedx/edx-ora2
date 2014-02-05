"""
This would hold models related to the peer response workflow. There's going to
be a lot here, like rubrics and such.

"""
from django.db import models
from django.utils.timezone import now

from submissions.models import Submission


#class Rubric(models.model):
#    pass
#
#
#class RubricScore(models.model):
#    description = models.TextField(max_length=255, default="")
#    point_value = models.PositiveIntegerField(default=0)
#    section = models.ForeignKey(RubricScoredSection
#
#
#class RubricScoredSection(models.model):
#    points_earned = models.PositiveIntegerField(default=0)
#    points_possible = models.PositiveIntegerField(default=0)
#    rubric = models.ForeignKey(Rubric)
#

class PeerEvaluation(models.Model):
    submission = models.ForeignKey(Submission)
    points_earned = models.PositiveIntegerField(default=0)
    points_possible = models.PositiveIntegerField(default=0)
    scored_at = models.DateTimeField(default=now, db_index=True)
    scorer_id = models.CharField(max_length=255, db_index=True)
    score_type = models.CharField(max_length=2)
    feedback = models.TextField(max_length=10000, default="")

    def __repr__(self):
        return repr(dict(
            submission=self.submission,
            points_earned=self.points_earned,
            points_possible=self.points_possible,
            scored_at=self.scored_at,
            scorer_id=self.scorer_id,
            score_type=self.score_type,
            feedback=self.feedback,
        ))

    class Meta:
        ordering = ["-scored_at"]
