# coding=utf-8
"""
Django models shared by all assessment types.

These models have to capture not only the state of assessments made for certain
submissions, but also the state of the rubrics at the time those assessments
were made.

NOTE: We've switched to migrations, so if you make any edits to this file, you
need to then generate a matching migration for it using:

    ./manage.py schemamigration openassessment.assessment --auto

"""
from collections import defaultdict
from copy import deepcopy
from hashlib import sha1
import json

from django.core.cache import cache
from django.db import models
from django.utils.timezone import now
import math

import logging
logger = logging.getLogger("openassessment.assessment.models")


class InvalidOptionSelection(Exception):
    """
    The user selected options that do not match the rubric.
    """
    pass


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
    # SHA1 hash, including prompts and explanations
    content_hash = models.CharField(max_length=40, unique=True, db_index=True)

    # SHA1 hash of just the rubric structure (criteria / options / points)
    structure_hash = models.CharField(max_length=40, db_index=True)

    class Meta:
        app_label = "assessment"

    @property
    def points_possible(self):
        """The total number of points that could be earned in this Rubric."""
        criteria_points = [crit.points_possible for crit in self.criteria.all()]
        return sum(criteria_points) if criteria_points else 0

    @staticmethod
    def content_hash_from_dict(rubric_dict):
        """Given a dict of rubric information, return a unique hash.

        This is a static method because we want to provide the `content_hash`
        when we create the rubric -- i.e. before the Rubric object could know or
        access its child criteria or options. In Django, when you add child
        elements to a model object using a foreign key relation, it will
        immediately persist to the database. But in order to persist to the
        database, the child object needs to have the ID of the parent, meaning
        that Rubric would have to have already been created and persisted.
        """
        rubric_dict = deepcopy(rubric_dict)

        # Neither "id" nor "content_hash" would count towards calculating the
        # content_hash.
        rubric_dict.pop("id", None)
        rubric_dict.pop("content_hash", None)

        canonical_form = json.dumps(rubric_dict, sort_keys=True)
        return sha1(canonical_form).hexdigest()

    @staticmethod
    def structure_hash_from_dict(rubric_dict):
        """
        Generate a hash of the rubric that includes only structural information:
            * Criteria names and order
            * Option names / points / order number

        We do NOT include prompt text or option explanations.

        NOTE: currently, we use the criterion and option names as unique identifiers,
        so we include them in the structure.  In the future, we plan to assign
        criteria/options unique IDs -- when we do that, we will need to update
        this method and create a data migration for existing rubrics.
        """
        structure = [
            {
                "criterion_name": criterion.get('name'),
                "criterion_order": criterion.get('order_num'),
                "options": [
                    {
                        "option_name": option.get('name'),
                        "option_points": option.get('points'),
                        "option_order": option.get('order_num')
                    }
                    for option in criterion.get('options', [])
                ]
            }
            for criterion in rubric_dict.get('criteria', [])
        ]
        canonical_form = json.dumps(structure, sort_keys=True)
        return sha1(canonical_form).hexdigest()

    def options_ids(self, options_selected):
        """Given a mapping of selected options, return the option IDs.

        We use this to map user selection during assessment to the
        :class:`CriterionOption` IDs that are in our database. These IDs are
        never shown to the user.

        Args:
            options_selected (dict): Mapping of criteria names to the names of
                the option that was selected for that criterion.

        Returns:
            set of option ids

        Examples:
            >>> options_selected = {"secret": "yes", "safe": "no"}
            >>> rubric.options_ids(options_selected)
            [10, 12]

        Raises:
            InvalidOptionSelection: the selected options do not match the rubric.

        """
        # Cache based on the content_hash, not the id. It's slightly safer, and
        # we don't have to worry about invalidation of the cache while running
        # tests.
        rubric_criteria_dict_cache_key = (
            "assessment.rubric_criteria_dict.{}".format(self.content_hash)
        )

        # Create a dict of dicts that maps:
        # criterion names --> option names --> option ids
        #
        # If we've already generated one of these for this rubric, grab it from
        # the cache instead of hitting the database again.
        rubric_criteria_dict = cache.get(rubric_criteria_dict_cache_key)

        if not rubric_criteria_dict:
            rubric_criteria_dict = defaultdict(dict)

            # Select all criteria and options for this rubric
            # We use `select_related()` to minimize the number of database queries
            rubric_options = CriterionOption.objects.filter(
                criterion__rubric=self
            ).select_related()

            # Construct dictionaries for each option in the rubric
            for option in rubric_options:
                rubric_criteria_dict[option.criterion.name][option.name] = option.id

            # Save it in our cache
            cache.set(rubric_criteria_dict_cache_key, rubric_criteria_dict)

        # Validate: are options selected for each criterion in the rubric?
        if len(options_selected) != len(rubric_criteria_dict):
            msg = (
                u"Incorrect number of options for this rubric "
                u"({actual} instead of {expected})"
            ).format(
                actual=len(options_selected),
                expected=len(rubric_criteria_dict)
            )
            raise InvalidOptionSelection(msg)

        # Look up each selected option
        option_id_set = set()
        for criterion_name, option_name in options_selected.iteritems():
            if (criterion_name in rubric_criteria_dict and
                option_name in rubric_criteria_dict[criterion_name]
            ):
                option_id = rubric_criteria_dict[criterion_name][option_name]
                option_id_set.add(option_id)
            else:
                msg = (
                    "{criterion}: {option} not found in rubric"
                ).format(criterion=criterion_name, option=option_name)
                raise InvalidOptionSelection(msg)

        return option_id_set

    def options_ids_for_points(self, criterion_points):
        """
        Given a mapping of selected point values, return the option IDs.
        If there are multiple options with the same point value,
        this will return the first one (lower order number).

        Args:
            criterion_points (dict): Mapping of criteria names to point values.

        Returns:
            list of option IDs

        Raises:
            InvalidOptionSelection

        """
        # Retrieve the mapping of criterion names/points to option IDs
        # from the cache, if it's available
        cache_key = "assessment.rubric_points_dict.{}".format(self.content_hash)
        rubric_points_dict = cache.get(cache_key)

        # Otherwise, create the dict by querying the database
        if not rubric_points_dict:
            rubric_options = CriterionOption.objects.filter(
                criterion__rubric=self
            ).select_related()

            rubric_points_dict = defaultdict(dict)
            for option in rubric_options:
                if option.points not in rubric_points_dict[option.criterion.name]:
                    rubric_points_dict[option.criterion.name][option.points] = option.id

            # Store the dict in the cache
            cache.set(cache_key, rubric_points_dict)

        # Find the IDs for the options matching the specified point value
        option_id_set = set()
        for criterion_name, option_points in criterion_points.iteritems():
            if (criterion_name in rubric_points_dict and option_points in rubric_points_dict[criterion_name]):
                option_id = rubric_points_dict[criterion_name][option_points]
                option_id_set.add(option_id)
            else:
                msg = u"{criterion} option with point value {points} not found in rubric".format(
                    criterion=criterion_name, points=option_points
                )
                raise InvalidOptionSelection(msg)

        return option_id_set


class Criterion(models.Model):
    """A single aspect of a submission that needs assessment.

    As an example, an essay might be assessed separately for accuracy, brevity,
    and clarity. Each of those would be separate criteria.

    All Rubrics have at least one Criterion.
    """
    rubric = models.ForeignKey(Rubric, related_name="criteria")

    name = models.CharField(max_length=100, blank=False)

    # 0-based order in the Rubric
    order_num = models.PositiveIntegerField()

    # What are we asking the reviewer to evaluate in this Criterion?
    prompt = models.TextField(max_length=10000)

    class Meta:
        ordering = ["rubric", "order_num"]
        app_label = "assessment"

    @property
    def points_possible(self):
        """The total number of points that could be earned in this Criterion."""
        return max(option.points for option in self.options.all())


class CriterionOption(models.Model):
    """What an assessor chooses when assessing against a Criteria.

    CriterionOptions have a name, point value, and explanation associated with
    them. When you have to select between "Excellent", "Good", "Fair", "Bad" --
    those are options.

    Note that this is the representation of the choice itself, *not* a
    representation of a particular assessor's choice for a particular
    Assessment. That state is stored in :class:`AssessmentPart`.
    """
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
        app_label = "assessment"

    def __repr__(self):
        return (
            "CriterionOption(order_num={0.order_num}, points={0.points}, "
            "name={0.name!r}, explanation={0.explanation!r})"
        ).format(self)

    def __unicode__(self):
        return repr(self)


class Assessment(models.Model):
    """An evaluation made against a particular Submission and Rubric.

    This is student state information and is created when a student completes
    an assessment of some submission. It is composed of :class:`AssessmentPart`
    objects that map to each :class:`Criterion` in the :class:`Rubric` we're
    assessing against.
    """
    MAXSIZE = 1024 * 100     # 100KB

    submission_uuid = models.CharField(max_length=128, db_index=True)
    rubric = models.ForeignKey(Rubric)

    scored_at = models.DateTimeField(default=now, db_index=True)
    scorer_id = models.CharField(max_length=40, db_index=True)
    score_type = models.CharField(max_length=2)

    feedback = models.TextField(max_length=10000, default="", blank=True)

    class Meta:
        ordering = ["-scored_at", "-id"]
        app_label = "assessment"

    @property
    def points_earned(self):
        parts = [part.points_earned for part in self.parts.all()]
        return sum(parts) if parts else 0

    @property
    def points_possible(self):
        return self.rubric.points_possible

    def to_float(self):
        """
        Calculate the score percentage (points earned / points possible).

        Returns:
            float or None

        """
        if self.points_possible == 0:
            return None
        else:
            return float(self.points_earned) / self.points_possible

    def __unicode__(self):
        return u"Assessment {}".format(self.id)

    @classmethod
    def get_median_score_dict(cls, scores_dict):
        """Determine the median score in a dictionary of lists of scores

        For a dictionary of lists, where each list contains a set of scores,
        determine the median value in each list.

        Args:
            scores_dict (dict): A dictionary of lists of int values. These int
                values are reduced to a single value that represents the median.

        Returns:
            (dict): A dictionary with criterion name keys and median score
                values.

        Examples:
            >>> scores = {
            >>>     "foo": [1, 2, 3, 4, 5],
            >>>     "bar": [6, 7, 8, 9, 10]
            >>> }
            >>> Assessment.get_median_score_dict(scores)
            {"foo": 3, "bar": 8}

        """
        median_scores = {}
        for criterion, criterion_scores in scores_dict.iteritems():
            criterion_score = Assessment.get_median_score(criterion_scores)
            median_scores[criterion] = criterion_score
        return median_scores

    @staticmethod
    def get_median_score(scores):
        """Determine the median score in a list of scores

        Determine the median value in the list.

        Args:
            scores (list): A list of int values. These int values
                are reduced to a single value that represents the median.

        Returns:
            (int): The median score.

        Examples:
            >>> scores = 1, 2, 3, 4, 5]
            >>> Assessment.get_median_score(scores)
            3

        """
        total_criterion_scores = len(scores)
        sorted_scores = sorted(scores)
        median = int(math.ceil(total_criterion_scores / float(2)))
        if total_criterion_scores == 0:
            median_score = 0
        elif total_criterion_scores % 2:
            median_score = sorted_scores[median-1]
        else:
            median_score = int(
                math.ceil(
                    sum(sorted_scores[median-1:median+1])/float(2)
                )
            )
        return median_score

    @classmethod
    def scores_by_criterion(cls, assessments):
        """Create a dictionary of lists for scores associated with criterion

        Create a key value in a dict with a list of values, for every criterion
        found in an assessment.

        Iterate over every part of every assessment. Each part is associated with
        a criterion name, which becomes a key in the score dictionary, with a list
        of scores.

        Args:
            assessments (list): List of assessments to sort scores by their
                associated criteria.

        Examples:
            >>> assessments = Assessment.objects.all()
            >>> Assessment.scores_by_criterion(assessments)
            {
                "foo": [1, 2, 3],
                "bar": [6, 7, 8]
            }
        """
        assessments = list(assessments)  # Force us to read it all
        if not assessments:
            return []

        # Generate a cache key that represents all the assessments we're being
        # asked to grab scores from (comma separated list of assessment IDs)
        cache_key = "assessments.scores_by_criterion.{}".format(
            ",".join(str(assessment.id) for assessment in assessments)
        )
        scores = cache.get(cache_key)
        if scores:
            return scores

        scores = defaultdict(list)
        for assessment in assessments:
            for part in assessment.parts.all().select_related("option__criterion"):
                criterion_name = part.option.criterion.name
                scores[criterion_name].append(part.option.points)

        cache.set(cache_key, scores)
        return scores


class AssessmentPart(models.Model):
    """Part of an Assessment corresponding to a particular Criterion.

    This is student state -- `AssessmentPart` represents what the student
    assessed a submission with for a given `Criterion`. So an example would be::

      5 pts: "Excellent"

    It's implemented as a foreign key to the `CriterionOption` that was chosen
    by this assessor for this `Criterion`. So basically, think of this class
    as :class:`CriterionOption` + student state.
    """
    MAX_FEEDBACK_SIZE = 1024 * 100

    assessment = models.ForeignKey(Assessment, related_name='parts')
    option = models.ForeignKey(CriterionOption, related_name="+")

    # Free-form text feedback for the specific criterion
    # Note that the `Assessment` model also has a feedback field,
    # which is feedback on the submission as a whole.
    feedback = models.TextField(default="", blank=True)

    class Meta:
        app_label = "assessment"

    @property
    def points_earned(self):
        return self.option.points

    @property
    def points_possible(self):
        return self.option.criterion.points_possible

    @classmethod
    def add_to_assessment(cls, assessment, option_ids, criterion_feedback=None):
        """
        Creates AssessmentParts and adds them to `assessment`.

        Args:
            assessment (Assessment): The assessment model we're adding parts to.
            option_ids (list of int): List of primary keys for options the user selected.

        Kwargs:
            criterion_feedback (dict): Dictionary mapping criterion names
                to free-form text feedback on the criterion.
                You don't need to include all the rubric criteria,
                and keys that don't match any criterion will be ignored.

        Returns:
            None

        """
        cls.objects.bulk_create([
            cls(assessment=assessment, option_id=option_id)
            for option_id in option_ids
        ])

        if criterion_feedback is not None:
            for criterion_name, feedback in criterion_feedback.iteritems():
                feedback = feedback[0:cls.MAX_FEEDBACK_SIZE]
                assessment.parts.filter(
                    option__criterion__name=criterion_name
                ).update(feedback=feedback)
