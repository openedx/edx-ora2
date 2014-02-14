"""
These Models have to capture not only the state of evaluations made for certain
submissions, but also the state of the specific rubrics at the time those
evaluations were made. This means we have a number of little models, and that
much of this data is immutable once created, so that we don't lose historical
information. This also means that if you change the Rubric in a problem and
this system is seeing that new Rubric for the first time, we're going to be
writing a whole little tree of objects into the database. Fortunately, we only
need to write this when we see a changed problem (rare). Performance concerns
when reading this data is mitigated by the fact that it's easy to cache the
entire tree of objects (since everything is immutable).
"""
from hashlib import sha1
import json

from django.db import models
from django.utils.timezone import now

from submissions.models import Submission


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


class Rubric(models.Model):
    """
    A Rubric
    """
    # SHA1 hash
    content_hash = models.CharField(max_length=40)

    # This is actually the prompt for the whole question, which may be a
    # complex, nested XML structure.
    prompt = models.TextField(max_length=10000)

    def points_possible(self):
        return sum(crit.points_possible() for crit in self.criteria.all())


class Criterion(models.Model):
    # All Rubrics have at least one Criterion
    rubric = models.ForeignKey(Rubric, related_name="criteria")

    # 0-based order in the Rubric
    order_num = models.PositiveIntegerField()

    # What are we asking the reviewer to evaluate in this Criterion?
    prompt = models.TextField(max_length=10000)

    class Meta:
        ordering = ["rubric", "order_num"]


    def points_possible(self):
        return max(option.points for option in self.options.all())


class CriterionOption(models.Model):
    # All Criteria must have at least one CriterionOption.
    criterion = models.ForeignKey(Criterion, related_name="options")

    # 0-based order in Criterion
    order_num = models.PositiveIntegerField()

    # How many points this option is worth. 0 is allowed.
    points = models.PositiveIntegerField()

    # Short name of the option. This is visible to the user.
    # Examples: "Excellent", "Good", "Fair", "Poor"
    name = models.CharField(max_length=100)

    # Longer text describing this option and why you should choose it.
    # Example: "The response makes 3-5 Monty Python references and at least one
    #           original Star Wars trilogy reference. Do not select this option
    #           if the author made any references to the second trilogy."
    explanation = models.TextField(max_length=10000, blank=True)

    class Meta:
        ordering = ["criterion", "order_num"]


    def __repr__(self):
        return (
            "CriterionOption(order_num={0.order_num}, points={0.points}, "
            "name={0.name!r}, explanation={0.explanation!r})"
        ).format(self)

    def __unicode__(self):
        return repr(self)

