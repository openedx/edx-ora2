# coding=utf-8
"""
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
import random
from datetime import timedelta

from django.core.cache import cache
from django.db import models
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.db import DatabaseError
import math

from openassessment.assessment.errors import PeerAssessmentWorkflowError, PeerAssessmentInternalError

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
    # SHA1 hash
    content_hash = models.CharField(max_length=40, unique=True, db_index=True)

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
            msg = _("Incorrect number of options for this rubric ({actual} instead of {expected})").format(
                actual=len(options_selected), expected=len(rubric_criteria_dict))
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
                msg = _("{criterion}: {option} not found in rubric").format(
                    criterion=criterion_name, option=option_name
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


class AssessmentFeedbackOption(models.Model):
    """
    Option a student can select to provide feedback on the feedback they received.

    `AssessmentFeedback` stands in a one-to-many relationship with `AssessmentFeedbackOption`s:
    a student can select zero or more `AssessmentFeedbackOption`s when providing feedback.

    Over time, we may decide to add, delete, or reword assessment feedback options.
    To preserve data integrity, we will always get-or-create `AssessmentFeedbackOption`s
    based on the option text.
    """
    text = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return u'"{}"'.format(self.text)


class AssessmentFeedback(models.Model):
    """
    Feedback on feedback.  When students receive their grades, they
    can provide feedback on how they were assessed, to be reviewed by course staff.

    This consists of free-form written feedback
    ("Please provide any thoughts or comments on the feedback you received from your peers")
    as well as zero or more feedback options
    ("Please select the statements below that reflect what you think of this peer grading experience")
    """
    MAXSIZE = 1024 * 100     # 100KB

    submission_uuid = models.CharField(max_length=128, unique=True, db_index=True)
    assessments = models.ManyToManyField(Assessment, related_name='assessment_feedback', default=None)
    feedback_text = models.TextField(max_length=10000, default="")
    options = models.ManyToManyField(AssessmentFeedbackOption, related_name='assessment_feedback', default=None)

    def add_options(self, selected_options):
        """
        Select feedback options for this assessment.
        Students can select zero or more options.

        Note: you *must* save the model before calling this method.

        Args:
            option_text_list (list of unicode): List of options that the user selected.

        Raises:
            DatabaseError
        """
        # First, retrieve options that already exist
        options = list(AssessmentFeedbackOption.objects.filter(text__in=selected_options))

        # If there are additional options that do not yet exist, create them
        new_options = [text for text in selected_options if text not in [opt.text for opt in options]]
        for new_option_text in new_options:
            options.append(AssessmentFeedbackOption.objects.create(text=new_option_text))

        # Add all options to the feedback model
        # Note that we've already saved each of the AssessmentFeedbackOption models, so they have primary keys
        # (required for adding to a many-to-many relationship)
        self.options.add(*options)


class PeerWorkflow(models.Model):
    """Internal Model for tracking Peer Assessment Workflow

    This model can be used to determine the following information required
    throughout the Peer Assessment Workflow:

    1) Get next submission that requires assessment.
    2) Does a submission have enough assessments?
    3) Has a student completed enough assessments?
    4) Does a student already have a submission open for assessment?
    5) Close open assessments when completed.
    6) Should 'over grading' be allowed for a submission?

    The student item is the author of the submission.  Peer Workflow Items are
    created for each assessment made by this student.

    """
    # Amount of time before a lease on a submission expires
    TIME_LIMIT = timedelta(hours=8)

    student_id = models.CharField(max_length=40, db_index=True)
    item_id = models.CharField(max_length=128, db_index=True)
    course_id = models.CharField(max_length=40, db_index=True)
    submission_uuid = models.CharField(max_length=128, db_index=True, unique=True)
    created_at = models.DateTimeField(default=now, db_index=True)
    completed_at = models.DateTimeField(null=True, db_index=True)
    grading_completed_at = models.DateTimeField(null=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]

    @classmethod
    def get_by_submission_uuid(cls, submission_uuid):
        """
        Retrieve the Peer Workflow associated with the given submission UUID.

        Args:
            submission_uuid (str): The string representation of the UUID belonging
                to the associated Peer Workflow.

        Returns:
            workflow (PeerWorkflow): The most recent peer workflow associated with
                this submission UUID.

        Raises:
            PeerAssessmentWorkflowError: Thrown when no workflow can be found for
                the associated submission UUID. This should always exist before a
                student is allow to request submissions for peer assessment.

        Examples:
            >>> PeerWorkflow.get_workflow_by_submission_uuid("abc123")
            {
                'student_id': u'Bob',
                'item_id': u'type_one',
                'course_id': u'course_1',
                'submission_uuid': u'1',
                'created_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 668850, tzinfo=<UTC>)
            }

        """
        try:
            return cls.objects.get(submission_uuid=submission_uuid)
        except cls.DoesNotExist:
            return None
        except DatabaseError:
            error_message = _(
                u"Error finding workflow for submission UUID {}. Workflow must be "
                u"created for submission before beginning peer assessment."
                .format(submission_uuid)
            )
            logger.exception(error_message)
            raise PeerAssessmentWorkflowError(error_message)

    @classmethod
    def create_item(cls, scorer_workflow, submission_uuid):
        """
        Create a new peer workflow for a student item and submission.

        Args:
            scorer_workflow (PeerWorkflow): The peer workflow associated with the scorer.
            submission_uuid (str): The submission associated with this workflow.

        Raises:
            PeerAssessmentInternalError: Raised when there is an internal error
                creating the Workflow.
        """
        peer_workflow = cls.get_by_submission_uuid(submission_uuid)

        try:
            workflow_item, __ = PeerWorkflowItem.objects.get_or_create(
                scorer=scorer_workflow,
                author=peer_workflow,
                submission_uuid=submission_uuid
            )
            workflow_item.started_at = now()
            workflow_item.save()
            return workflow_item
        except DatabaseError:
            error_message = _(
                u"An internal error occurred while creating a new peer workflow "
                u"item for workflow {}".format(scorer_workflow)
            )
            logger.exception(error_message)
            raise PeerAssessmentInternalError(error_message)

    def find_active_assessments(self):
        """Given a student item, return an active assessment if one is found.

        Before retrieving a new submission for a peer assessor, check to see if that
        assessor already has a submission out for assessment. If an unfinished
        assessment is found that has not expired, return the associated submission.

        TODO: If a user begins an assessment, then resubmits, this will never find
        the unfinished assessment. Is this OK?

        Args:
            workflow (PeerWorkflow): See if there is an associated active assessment
                for this PeerWorkflow.

        Returns:
            submission_uuid (str): The submission_uuid for the submission that the
                student has open for active assessment.

        """
        oldest_acceptable = now() - self.TIME_LIMIT
        workflows = self.graded.filter(
            assessment__isnull=True,
            started_at__gt=oldest_acceptable
        )
        return workflows[0].submission_uuid if workflows else None

    def get_submission_for_review(self, graded_by):
        """
        Find a submission for peer assessment. This function will find the next
        submission that requires assessment, excluding any submission that has been
        completely graded, or is actively being reviewed by other students.

        Args:
            graded_by (unicode): Student ID of the scorer.

        Returns:
            submission_uuid (str): The submission_uuid for the submission to review.

        Raises:
            PeerAssessmentInternalError: Raised when there is an error retrieving
                the workflows or workflow items for this request.

        """
        timeout = (now() - self.TIME_LIMIT).strftime("%Y-%m-%d %H:%M:%S")
        # The follow query behaves as the Peer Assessment Queue. This will
        # find the next submission (via PeerWorkflow) in this course / question
        # that:
        #  1) Does not belong to you
        #  2) Does not have enough completed assessments
        #  3) Is not something you have already scored.
        #  4) Does not have a combination of completed assessments or open
        #     assessments equal to or more than the requirement.
        try:
            peer_workflows = list(PeerWorkflow.objects.raw(
                "select pw.id, pw.submission_uuid "
                "from assessment_peerworkflow pw "
                "where pw.item_id=%s "
                "and pw.course_id=%s "
                "and pw.student_id<>%s "
                "and pw.grading_completed_at is NULL "
                "and pw.id not in ("
                "   select pwi.author_id "
                "   from assessment_peerworkflowitem pwi "
                "   where pwi.scorer_id=%s "
                "   and pwi.assessment_id is not NULL "
                ") "
                "and ("
                "   select count(pwi.id) as c "
                "   from assessment_peerworkflowitem pwi "
                "   where pwi.author_id=pw.id "
                "   and (pwi.assessment_id is not NULL or pwi.started_at > %s) "
                ") < %s "
                "order by pw.created_at, pw.id "
                "limit 1; ",
                [
                    self.item_id,
                    self.course_id,
                    self.student_id,
                    self.id,
                    timeout,
                    graded_by
                ]
            ))
            if not peer_workflows:
                return None

            return peer_workflows[0].submission_uuid
        except DatabaseError:
            error_message = _(
                u"An internal error occurred while retrieving a peer submission "
                u"for student {}".format(self)
            )
            logger.exception(error_message)
            raise PeerAssessmentInternalError(error_message)

    def get_submission_for_over_grading(self):
        """
        Retrieve the next submission uuid for over grading in peer assessment.
        """
        # The follow query behaves as the Peer Assessment Over Grading Queue. This
        # will find a random submission (via PeerWorkflow) in this course / question
        # that:
        #  1) Does not belong to you
        #  2) Is not something you have already scored
        try:
            query = list(PeerWorkflow.objects.raw(
                "select pw.id, pw.submission_uuid "
                "from assessment_peerworkflow pw "
                "where course_id=%s "
                "and item_id=%s "
                "and student_id<>%s "
                "and pw.id not in ( "
                    "select pwi.author_id "
                    "from assessment_peerworkflowitem pwi "
                    "where pwi.scorer_id=%s); ",
                [self.course_id, self.item_id, self.student_id, self.id]
            ))
            workflow_count = len(query)
            if workflow_count < 1:
                return None

            random_int = random.randint(0, workflow_count - 1)
            random_workflow = query[random_int]

            return random_workflow.submission_uuid
        except DatabaseError:
            error_message = _(
                u"An internal error occurred while retrieving a peer submission "
                u"for student {}".format(self)
            )
            logger.exception(error_message)
            raise PeerAssessmentInternalError(error_message)

    def get_latest_open_workflow_item(self):
        """
        Return the latest open workflow item for this workflow.

        Returns:
            A PeerWorkflowItem that is open for assessment.
            None if no item is found.

        """
        workflow_query = self.graded.filter(
            assessment__isnull=True
        ).order_by("-started_at", "-id")
        items = list(workflow_query[:1])
        return items[0] if items else None

    def close_active_assessment(self, submission_uuid, assessment, num_required_grades):
        """
        Updates a workflow item on the student's workflow with the associated
        assessment. When a workflow item has an assessment, it is considered
        finished.

        Args:
            submission_uuid (str): The submission the scorer is grading.
            assessment (PeerAssessment): The associate assessment for this action.
            graded_by (int): The required number of grades the peer workflow
                requires to be considered complete.

        Returns:
            None

        """
        try:
            item_query = self.graded.filter(submission_uuid=submission_uuid).order_by("-started_at", "-id")
            items = list(item_query[:1])
            if not items:
                raise PeerAssessmentWorkflowError(_(
                    u"No open assessment was found for student {} while assessing "
                    u"submission UUID {}.".format(self.student_id, submission_uuid)
                ))
            item = items[0]
            item.assessment = assessment
            item.save()

            if (not item.author.grading_completed_at
                    and item.author.graded_by.filter(assessment__isnull=False).count() >= num_required_grades):
                item.author.grading_completed_at = now()
                item.author.save()
        except (DatabaseError, PeerWorkflowItem.DoesNotExist):
            error_message = _(
                u"An internal error occurred while retrieving a workflow item for "
                u"student {}. Workflow Items are created when submissions are "
                u"pulled for assessment."
                .format(self.student_id)
            )
            logger.exception(error_message)
            raise PeerAssessmentWorkflowError(error_message)

    def num_peers_graded(self):
        """
        Returns the number of peers the student owning the workflow has graded.

        Returns:
            integer

        """
        return self.graded.filter(assessment__isnull=False).count()

    def __repr__(self):
        return (
            "PeerWorkflow(student_id={0.student_id}, item_id={0.item_id}, "
            "course_id={0.course_id}, submission_uuid={0.submission_uuid}"
            "created_at={0.created_at}, completed_at={0.completed_at})"
        ).format(self)

    def __unicode__(self):
        return repr(self)


class PeerWorkflowItem(models.Model):
    """Represents an assessment associated with a particular workflow

    Created every time a submission is requested for peer assessment. The
    associated workflow represents the scorer of the given submission, and the
    assessment represents the completed assessment for this work item.

    """
    scorer = models.ForeignKey(PeerWorkflow, related_name='graded')
    author = models.ForeignKey(PeerWorkflow, related_name='graded_by')
    submission_uuid = models.CharField(max_length=128, db_index=True)
    started_at = models.DateTimeField(default=now, db_index=True)
    assessment = models.ForeignKey(Assessment, null=True)

    # This WorkflowItem was used to determine the final score for the Workflow.
    scored = models.BooleanField(default=False)

    @classmethod
    def get_scored_assessments(cls, submission_uuid):
        return Assessment.objects.filter(
            pk__in=[
                item.assessment.pk for item in PeerWorkflowItem.objects.filter(
                    submission_uuid=submission_uuid, scored=True
                )
            ]
        )

    class Meta:
        ordering = ["started_at", "id"]

    def __repr__(self):
        return (
            "PeerWorkflowItem(scorer={0.scorer}, author={0.author}, "
            "submission_uuid={0.submission_uuid}, "
            "started_at={0.started_at}, assessment={0.assessment}, "
            "scored={0.scored})"
        ).format(self)

    def __unicode__(self):
        return repr(self)
