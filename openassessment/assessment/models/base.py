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
import logging
import math

from django.core.cache import cache
from django.db import models
from django.utils.functional import cached_property
from django.utils.timezone import now

from simple_history.models import HistoricalRecords

from model_utils.models import TimeStampedModel

from lazy import lazy

logger = logging.getLogger("openassessment.assessment.models")  # pylint: disable=invalid-name

KEY_SEPARATOR = '/'


class InvalidRubricSelection(Exception):
    """
    The specified criterion/option do not exist in the rubric.
    """


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

    @lazy
    def index(self):
        """
        Load the rubric's data and return an index that allows
        the user to query for specific criteria/options.

        Returns:
            RubricIndex

        """
        return RubricIndex(self)

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
        return sha1(canonical_form.encode('utf-8')).hexdigest()

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
        return sha1(canonical_form.encode('utf-8')).hexdigest()


class Criterion(models.Model):
    """A single aspect of a submission that needs assessment.

    As an example, an essay might be assessed separately for accuracy, brevity,
    and clarity. Each of those would be separate criteria.

    All Rubrics have at least one Criterion.
    """
    rubric = models.ForeignKey(Rubric, related_name="criteria", on_delete=models.CASCADE)

    # Backwards compatibility: The "name" field was formerly
    # used both as a display name and as a unique identifier.
    # Now we're using it only as a unique identifier.
    # We include the "label" (which is displayed to the user)
    # in the data model so we can include it in analytics data packages.
    name = models.CharField(max_length=100, blank=False)
    label = models.CharField(max_length=100, blank=True)

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
        # By convention, criteria with 0 options (only feedback) have 0 points possible
        option_points = [option.points for option in self.options.all()]
        return max(option_points) if option_points else 0


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
    criterion = models.ForeignKey(Criterion, related_name="options", on_delete=models.CASCADE)

    # 0-based order in Criterion
    order_num = models.PositiveIntegerField()

    # How many points this option is worth. 0 is allowed.
    points = models.PositiveIntegerField()

    # Backwards compatibility: The "name" field was formerly
    # used both as a display name and as a unique identifier.
    # Now we're using it only as a unique identifier.
    # We include the "label" (which is displayed to the user)
    # in the data model so we can include it in analytics data packages.
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=100, blank=True)

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

    def __str__(self):
        return repr(self)


class RubricIndex:
    """
    Loads a rubric's criteria and options into memory so that they
    can be repeatedly queried without hitting the database.
    """

    def __init__(self, rubric):
        """
        Load the rubric's data.

        Args:
            rubric (Rubric): The Rubric model to load.

        Returns:
            RubricIndex

        """
        self.rubric = rubric

        # Load the rubric's criteria and options from the database
        criteria = Criterion.objects.select_related().filter(rubric=rubric)
        options = CriterionOption.objects.select_related().filter(
            criterion__rubric=rubric
        ).order_by("-order_num")

        # Create dictionaries indexing the criteria/options
        self._criteria_index = {
            criterion.name: criterion
            for criterion in criteria
        }

        # Finds the set of all criteria which have options by traversing through the options, and adding all of
        # the options' associated criteria to an expanding set.
        criteria_with_options = set()
        option_index = {}
        for option in options:
            option_index[(option.criterion.name, option.name)] = option
            criteria_with_options.add(option.criterion)

        # Anything not in the above mentioned set is a zero option criteria, and we save it here for future reference.
        self._criteria_without_options = set(self._criteria_index.values()) - criteria_with_options

        self._option_index = option_index

        # By convention, if multiple options in the same criterion have the
        # same point value, we return the *first* option.
        # Since the options are in descending order by order number,
        # the option with the lowest order number takes precedence.
        self._option_points_index = {
            (option.criterion.name, option.points): option
            for option in options
        }

    def find_criterion(self, criterion_name):
        """
        Find a criterion by its name.

        Args:
            criterion_name (unicode): The name of the criterion to retrieve.

        Returns:
            Criterion

        Raises:
            InvalidRubricSelection

        """
        if criterion_name not in self._criteria_index:
            msg = (
                "Could not find criterion named \"{criterion}\" "
                "in the rubric with content hash \"{rubric_hash}\""
            ).format(
                criterion=criterion_name,
                rubric_hash=self.rubric.content_hash
            )
            raise InvalidRubricSelection(msg)
        return self._criteria_index[criterion_name]

    def find_option(self, criterion_name, option_name):
        """
        Find a rubric option by criterion name and option name.

        Args:
            criterion_name (unicode): The name of the criterion containing the option.
            option_name (unicode): The name of the option to retrieve.

        Returns:
            CriterionOption

        Raises:
            InvalidRubricSelection

        """
        key = (criterion_name, option_name)
        if key not in self._option_index:
            msg = (
                "Option \"{option}\" not found in rubric "
                "with hash {rubric_hash} for criterion \"{criterion}\""
            ).format(
                option=option_name,
                criterion=criterion_name,
                rubric_hash=self.rubric.content_hash
            )
            raise InvalidRubricSelection(msg)
        return self._option_index[key]

    def find_option_for_points(self, criterion_name, option_points):
        """
        Find a rubric option by criterion name and option point value.
        If multiple options in a criterion have the same point value,
        return the first one (based on order number).

        Args:
            criterion_name (unicode): The name of the criterion containing the option.
            option_points (int): The point value of the option.

        Returns:
            CriterionOption

        Raises:
            InvalidRubricSelection

        """
        key = (criterion_name, option_points)
        if key not in self._option_points_index:
            msg = (
                "Option with points {option_points} not found in rubric "
                "with hash {rubric_hash} for criterion {criterion}"
            ).format(
                option_points=option_points,
                criterion=criterion_name,
                rubric_hash=self.rubric.content_hash
            )
            raise InvalidRubricSelection(msg)
        # Assume that we gave priority to options with lower
        # order numbers when we created the index.
        return self._option_points_index[key]

    @property
    def criteria_names(self):
        """
        Return a list of all criteria names in the rubric.

        Returns:
            set of unicode

        """
        return set(self._criteria_index.keys())

    def find_missing_criteria(self, criteria_names):
        """
        Return a set of criteria names in the rubric that
        are not in the provided list.

        Args:
            criteria_names (list of unicode): The criteria names to check.

        Returns:
            set of unicode: The missing criteria

        """
        return set(self.criteria_names) - set(criteria_names)

    def find_criteria_without_options(self):
        """
        Return a set of `Criterion` models that do not have options.
        (only written feedback).

        Returns:
            set of `Criterion`

        """
        return self._criteria_without_options


class Assessment(models.Model):
    """An evaluation made against a particular Submission and Rubric.

    This is student state information and is created when a student completes
    an assessment of some submission. It is composed of :class:`AssessmentPart`
    objects that map to each :class:`Criterion` in the :class:`Rubric` we're
    assessing against.
    """
    MAX_FEEDBACK_SIZE = 1024 * 100

    submission_uuid = models.CharField(max_length=128, db_index=True)
    rubric = models.ForeignKey(Rubric, on_delete=models.CASCADE)

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
        return float(self.points_earned) / self.points_possible

    def __str__(self):
        return f"Assessment {self.id}"

    @classmethod
    def create(cls, rubric, scorer_id, submission_uuid, score_type, feedback=None, scored_at=None):
        """
        Create a new assessment.

        Args:
            rubric (Rubric): The rubric associated with this assessment.
            scorer_id (unicode): The ID of the scorer.
            submission_uuid (str): The UUID of the submission being assessed.
            score_type (unicode): The type of assessment (e.g. peer, self, or AI)

        Keyword Arguments:
            feedback (unicode): Overall feedback on the submission.
            scored_at (datetime): The time the assessment was created.  Defaults to the current time.

        Returns:
            Assessment

        """
        assessment_params = {
            'rubric': rubric,
            'scorer_id': scorer_id,
            'submission_uuid': submission_uuid,
            'score_type': score_type,
        }

        if scored_at is not None:
            assessment_params['scored_at'] = scored_at

        # Truncate the feedback if it exceeds the maximum size
        if feedback is not None:
            assessment_params['feedback'] = feedback[0:cls.MAX_FEEDBACK_SIZE]

        return cls.objects.create(**assessment_params)

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
        for criterion, criterion_scores in scores_dict.items():
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
            median_score = sorted_scores[median - 1]
        else:
            median_score = int(
                math.ceil(
                    sum(sorted_scores[median - 1:median + 1]) / float(2)
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
            return {}

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
            for part in assessment.parts.all().select_related():
                criterion_name = part.criterion.name
                scores[criterion_name].append(part.points_earned)

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

    assessment = models.ForeignKey(Assessment, related_name='parts', on_delete=models.CASCADE)

    # Assessment parts are usually associated with an option
    # (representing the point value selected for a particular criterion)
    # It's possible, however, for an assessment part to contain
    # only written feedback, with no point value.
    # In this case, the assessment part is associated with a criterion,
    # but not with any option (the `option` field is set to null).
    criterion = models.ForeignKey(Criterion, related_name="+", on_delete=models.CASCADE)
    option = models.ForeignKey(CriterionOption, null=True, related_name="+", on_delete=models.CASCADE)

    # Free-form text feedback for the specific criterion
    # Note that the `Assessment` model also has a feedback field,
    # which is feedback on the submission as a whole.
    feedback = models.TextField(default="", blank=True)

    class Meta:
        app_label = "assessment"

    @property
    def points_earned(self):
        # By convention, an assessment with no options (only feedback) earns 0 points.
        return self.option.points if self.option is not None else 0

    @property
    def points_possible(self):
        return self.criterion.points_possible

    @classmethod
    def create_from_option_names(cls, assessment, selected, feedback=None):
        """
        Create new assessment parts and add them to an assessment.

        Args:
            assessment (Assessment): The assessment we're adding parts to.
            selected (dict): A dictionary mapping criterion names to option names.

        Keyword Arguments:
            feedback (dict): A dictionary mapping criterion names to written
                feedback for the criterion.

        Returns:
            list of `AssessmentPart`s

        Raises:
            InvalidRubricSelection
            DatabaseError

        """
        # Use the rubric index so we can retrieve options/criteria
        # without repeatedly hitting the database.
        # This will also validate our selections against the rubric.
        rubric_index = assessment.rubric.index

        # If the assessment type doesn't explicitly provide feedback,
        # then fill in feedback-only criteria with an empty string for feedback.
        if feedback is None:
            feedback = {
                criterion.name: ""
                for criterion in rubric_index.find_criteria_without_options()
            }

        # Validate that we have selections for all criteria
        # This will raise an exception if we're missing any selections/feedback required for criteria
        cls._check_all_criteria_assessed(rubric_index, list(selected.keys()), list(feedback.keys()))

        # Retrieve the criteria/option/feedback for criteria that have options.
        # Since we're using the rubric's index, we'll get an `InvalidRubricSelection` error
        # if we select an invalid criterion/option.
        assessment_parts = [
            {
                'criterion': rubric_index.find_criterion(criterion_name),
                'option': rubric_index.find_option(criterion_name, option_name),
                'feedback': feedback.get(criterion_name, "")[0:cls.MAX_FEEDBACK_SIZE],
            }
            for criterion_name, option_name in selected.items()
        ]

        # Some criteria may have feedback but no options, only feedback.
        # For these, we set `option` to None, indicating that the assessment part
        # is not associated with any option, only a criterion.
        for criterion_name, feedback_text in feedback.items():
            if criterion_name not in selected:
                assessment_parts.append({
                    'criterion': rubric_index.find_criterion(criterion_name),
                    'option': None,
                    'feedback': feedback_text[0:cls.MAX_FEEDBACK_SIZE]
                })

        # Create assessment parts for each criterion and associate them with the assessment
        # We use the dictionary we created earlier, which may have null options
        # for feedback-only assessment parts.
        return cls.objects.bulk_create([
            cls(
                assessment=assessment,
                criterion=assessment_part['criterion'],
                option=assessment_part['option'],
                feedback=assessment_part['feedback']
            )
            for assessment_part in assessment_parts
        ])

    @classmethod
    def create_from_option_points(cls, assessment, selected):
        """
        Create new assessment parts and add them to an assessment.

        Args:
            assessment (Assessment): The assessment we're adding parts to.
            selected (dict): A dictionary mapping criterion names to option point values.

        Keyword Arguments:
            feedback (dict): A dictionary mapping criterion names to written
                feedback for the criterion.

        Returns:
            list of `AssessmentPart`s

        Raises:
            InvalidRubricSelection
            DatabaseError

        """
        rubric_index = assessment.rubric.index

        # Retrieve the criteria/option/feedback for criteria that have options.
        # Since we're using the rubric's index, we'll get an `InvalidRubricSelection` error
        # if we select an invalid criterion/option.
        assessment_parts = [
            {
                'criterion': rubric_index.find_criterion(criterion_name),
                'option': rubric_index.find_option_for_points(criterion_name, option_points),
            }
            for criterion_name, option_points in selected.items()
        ]

        # Add in feedback-only criteria
        # (criteria that have 0 options)
        for criterion in rubric_index.find_criteria_without_options():
            assessment_parts.append({
                'criterion': criterion,
                'option': None
            })

        # Validate that we have selections for all criteria
        # This will raise an exception if we're missing any criteria
        cls._check_has_all_criteria(rubric_index, {
            part['criterion'].name for part in assessment_parts
        })

        # Create assessment parts for each criterion and associate them with the assessment
        # Since we're not accepting written feedback, set all feedback to an empty string.
        return cls.objects.bulk_create([
            cls(
                assessment=assessment,
                criterion=assessment_part['criterion'],
                option=assessment_part['option'],
                feedback=""
            )
            for assessment_part in assessment_parts
        ])

    @classmethod
    def _check_has_all_criteria(cls, rubric_index, selected_criteria):
        """
        Verify that we've selected options for all criteria in the rubric.

        Args:
            rubric_index (RubricIndex): The index of the rubric's data.
            selected_criteria (list): list of criterion names

        Returns:
            None

        Raises:
            InvalidRubricSelection
        """
        missing_criteria = rubric_index.find_missing_criteria(selected_criteria)
        if missing_criteria:
            msg = f"Missing selections for criteria: {missing_criteria}"
            raise InvalidRubricSelection(msg)

    @classmethod
    def _check_all_criteria_assessed(cls, rubric_index, selected_criteria, criteria_feedback):
        """
        Verify that we've selected options OR have feedback for all criteria in the rubric.

        Verifies the predicate for all criteria (X) in the rubric:
            has-an-option-selected(X) OR (has-zero-options(X) AND has-criterion-feedback(X))

        Args:
            rubric_index (RubricIndex): The index of the rubric's data.
            selected_criteria (list): list of criterion names that have an option selected
            criteria_feedback (list): list of criterion names that have feedback on them

        Returns:
            None

        Raises:
            InvalidRubricSelection
        """
        missing_option_selections = rubric_index.find_missing_criteria(selected_criteria)
        zero_option_criteria = {c.name for c in rubric_index.find_criteria_without_options()}
        # pylint: disable=invalid-name
        zero_option_criteria_missing_feedback = zero_option_criteria - set(criteria_feedback)
        # pylint: disable=invalid-name
        optioned_criteria_missing_selection = missing_option_selections - zero_option_criteria

        missing_criteria = zero_option_criteria_missing_feedback | optioned_criteria_missing_selection

        if missing_criteria:
            msg = "Missing selections for criteria: {missing}".format(missing=', '.join(missing_criteria))
            raise InvalidRubricSelection(msg)


class SharedFileUpload(TimeStampedModel):
    """
    Define a single file uploaded by a student when attached to a team.

    """
    team_id = models.CharField(max_length=255, db_index=True)
    course_id = models.CharField(max_length=255, db_index=True)
    item_id = models.CharField(max_length=255, db_index=True)
    owner_id = models.CharField(max_length=255, db_index=True)
    file_key = models.CharField(max_length=255, unique=True)
    history = HistoricalRecords()
    description = models.TextField(default="", blank=True)
    size = models.BigIntegerField(default=0, blank=True)
    name = models.CharField(max_length=255, default="")

    def __str__(self):
        return f"SharedFileUpload {self.file_key}"

    @cached_property
    def index(self):
        """
        Relies on the definition of fileupload.api.get_student_file_key,
        namely, that ``file_key`` will be composed of either 3 or 4 parts,
        and if 4, then the string after the last slash is the index of the file.
        If there are only 3 parts, the index is 0 by convention.
        """
        key_parts = self.file_key.split(KEY_SEPARATOR)
        if len(key_parts) == 4:
            return int(key_parts[3])
        return 0

    @classmethod
    def by_key(cls, key):
        try:
            return cls.objects.get(file_key=key)
        except cls.DoesNotExist as exc:
            logger.exception(exc)
            raise

    @classmethod
    def by_team_course_item(cls, team_id, course_id, item_id, **kwargs):  # pylint: disable=unused-argument
        return cls.objects.filter(team_id=team_id, course_id=course_id, item_id=item_id)

    @classmethod
    def by_student_course_item(cls, student_id, course_id, item_id, **kwargs):  # pylint: disable=unused-argument
        return cls.objects.filter(owner_id=student_id, course_id=course_id, item_id=item_id)
