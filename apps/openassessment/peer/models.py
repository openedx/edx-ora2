# coding=utf-8
"""
These models have to capture not only the state of assessments made for certain
submissions, but also the state of the rubrics at the time those assessments
were made.
"""
from copy import deepcopy
from hashlib import sha1
import json

from django.db import models
from django.utils.timezone import now

from submissions.models import Submission


class Rubric(models.Model):
    """A Rubric contains the guidelines on how to assess a submission.

    Rubrics are composed of :class:`Criterion` objects which are in turn
    composed of :class:`CriterionOption` objects.

    This model is a bit unusual in that it is the representation of the rubric
    that an assessment was made with *at the time of assessment*. The source
    rubric data lives in the problem definition, which is in the
    :class:`OpenAssessmentBlock`. When an assessment is made, the XBlock passes
    that rubric information along as well. When this Django app records the
    :class:`Assessment`, we do a lookup to see if the Rubric model object
    already exists (using hashing). If the Rubric is not found, we create a new
    one with the information OpenAssessmentBlock has passed in.

    .. warning::
       Never change Rubric model data after it's written!

    The little tree of objects that compose a Rubric is meant to be immutable —
    once created, they're never updated. When the problem changes, we end up
    creating a new Rubric instead. This makes it easy to cache and do hash-based
    lookups.
    """
    # SHA1 hash
    content_hash = models.CharField(max_length=40)

    @property
    def points_possible(self):
        criteria_points = [crit.points_possible for crit in self.criteria.all()]
        return sum(criteria_points) if criteria_points else 0

    @staticmethod
    def content_hash_for_rubric_dict(rubric_dict):
        """

        """
        rubric_dict = deepcopy(rubric_dict)
        # Neither "id" nor "content_hash" would count towards calculating the
        # content_hash.
        rubric_dict.pop("id", None)
        rubric_dict.pop("content_hash", None)

        canonical_form = json.dumps(rubric_dict, sort_keys=True)
        return sha1(canonical_form).hexdigest()


    def options_ids(self, crit_to_opt_names):
        """
        """
        # Cache this
        crit_to_all_opts = {
            crit.name : {
                option.name: option.id for option in crit.options.all()
            }
            for crit in self.criteria.all()
        }

        return [
            crit_to_all_opts[crit][opt]
            for crit, opt in crit_to_opt_names.items()
        ]


class Criterion(models.Model):
    # All Rubrics have at least one Criterion
    rubric = models.ForeignKey(Rubric, related_name="criteria")

    name = models.CharField(max_length=100, blank=False)

    # 0-based order in the Rubric
    order_num = models.PositiveIntegerField()

    # What are we asking the reviewer to evaluate in this Criterion?
    prompt = models.TextField(max_length=10000)

    class Meta:
        ordering = ["rubric", "order_num"]


    @property
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


class Assessment(models.Model):
    submission = models.ForeignKey(Submission)
    rubric = models.ForeignKey(Rubric)

    scored_at = models.DateTimeField(default=now, db_index=True)
    scorer_id = models.CharField(max_length=40, db_index=True)
    score_type = models.CharField(max_length=2)

    # TODO: move this to its own model
    feedback = models.TextField(max_length=10000, default="")

    class Meta:
        ordering = ["-scored_at"]

    @property
    def points_earned(self):
        parts = [part.points_earned for part in self.parts.all()]
        return sum(parts) if parts else 0

    @property
    def points_possible(self):
        return self.rubric.points_possible

    @property
    def submission_uuid(self):
        return self.submission.uuid


class AssessmentPart(models.Model):
    assessment = models.ForeignKey(Assessment, related_name='parts')

    # criterion = models.ForeignKey(Criterion)
    option = models.ForeignKey(CriterionOption) # TODO: no reverse

    @property
    def points_earned(self):
        return self.option.points

    @property
    def points_possible(self):
        return self.option.criterion.points_possible
