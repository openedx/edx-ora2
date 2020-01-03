"""
Django models specific to peer assessment.

NOTE: We've switched to migrations, so if you make any edits to this file, you
need to then generate a matching migration for it using:

    ./manage.py schemamigration openassessment.assessment --auto

"""
from __future__ import absolute_import, unicode_literals

from datetime import timedelta
import logging
import random

from django.db import DatabaseError, models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now

from openassessment.assessment.errors import PeerAssessmentInternalError, PeerAssessmentWorkflowError
from openassessment.assessment.models.base import Assessment

logger = logging.getLogger("openassessment.assessment.models")  # pylint: disable=invalid-name


@python_2_unicode_compatible
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

    class Meta:
        app_label = "assessment"

    def __str__(self):
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
    feedback_text = models.TextField(max_length=10000, default=u"")
    options = models.ManyToManyField(AssessmentFeedbackOption, related_name='assessment_feedback', default=None)

    class Meta:
        app_label = "assessment"

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
        self.options.add(*options)  # pylint:disable=E1101


@python_2_unicode_compatible
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
    course_id = models.CharField(max_length=255, db_index=True)
    submission_uuid = models.CharField(max_length=128, db_index=True, unique=True)
    created_at = models.DateTimeField(default=now, db_index=True)
    completed_at = models.DateTimeField(null=True, db_index=True)
    grading_completed_at = models.DateTimeField(null=True, db_index=True)
    cancelled_at = models.DateTimeField(null=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]
        app_label = "assessment"

    @property
    def is_cancelled(self):
        """
        Check if workflow is cancelled.

        Returns:
            True/False
        """
        return bool(self.cancelled_at)

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
            error_message = (
                u"Error finding workflow for submission UUID {}. Workflow must be "
                u"created for submission before beginning peer assessment."
            ).format(submission_uuid)
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
            workflow_items = PeerWorkflowItem.objects.filter(
                scorer=scorer_workflow,
                author=peer_workflow,
                submission_uuid=submission_uuid
            )

            if workflow_items:
                item = workflow_items[0]
            else:
                item = PeerWorkflowItem.objects.create(
                    scorer=scorer_workflow,
                    author=peer_workflow,
                    submission_uuid=submission_uuid
                )
            item.started_at = now()
            item.save()
            return item
        except DatabaseError:
            error_message = (
                u"An internal error occurred while creating a new peer workflow "
                u"item for workflow {}"
            ).format(scorer_workflow)
            logger.exception(error_message)
            raise PeerAssessmentInternalError(error_message)

    def find_active_assessments(self):
        """Given a student item, return an active assessment if one is found.

        Before retrieving a new submission for a peer assessor, check to see if that
        assessor already has a submission out for assessment. If an unfinished
        assessment is found that has not expired or has not been cancelled,
        return the associated submission.

        TODO: If a user begins an assessment, then resubmits, this will never find
        the unfinished assessment. Is this OK?

        Args:
            workflow (PeerWorkflow): See if there is an associated active assessment
                for this PeerWorkflow.

        Returns:
            (PeerWorkflowItem) The PeerWorkflowItem for the submission that the
                student has open for active assessment.

        """
        oldest_acceptable = now() - self.TIME_LIMIT
        items = list(self.graded.all().select_related('author').order_by("-started_at", "-id"))
        valid_open_items = []
        completed_sub_uuids = []
        # First, remove all completed items.
        for item in items:
            if item.assessment is not None or item.author.is_cancelled:
                completed_sub_uuids.append(item.submission_uuid)
            else:
                valid_open_items.append(item)

        # Remove any open items which have a submission which has been completed.
        for item in valid_open_items:
            if (item.started_at < oldest_acceptable) or (item.submission_uuid in completed_sub_uuids):
                valid_open_items.remove(item)

        return valid_open_items[0] if valid_open_items else None

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
        #  5) Has not been cancelled.
        try:
            peer_workflows = list(PeerWorkflow.objects.raw(
                "select pw.id, pw.submission_uuid "
                "from assessment_peerworkflow pw "
                "where pw.item_id=%s "
                "and pw.course_id=%s "
                "and pw.student_id<>%s "
                "and pw.grading_completed_at is NULL "
                "and pw.cancelled_at is NULL "
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
            error_message = (
                u"An internal error occurred while retrieving a peer submission "
                u"for learner {}"
            ).format(self)
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
        #  3) Has not been cancelled.
        try:
            query = list(PeerWorkflow.objects.raw(
                "select pw.id, pw.submission_uuid "
                "from assessment_peerworkflow pw "
                "where course_id=%s "
                "and item_id=%s "
                "and student_id<>%s "
                "and pw.cancelled_at is NULL "
                "and pw.id not in ( "
                "select pwi.author_id "
                "from assessment_peerworkflowitem pwi "
                "where pwi.scorer_id=%s"
                "); ",
                [self.course_id, self.item_id, self.student_id, self.id]
            ))
            workflow_count = len(query)
            if workflow_count < 1:
                return None

            random_int = random.randint(0, workflow_count - 1)
            random_workflow = query[random_int]

            return random_workflow.submission_uuid
        except DatabaseError:
            error_message = (
                u"An internal error occurred while retrieving a peer submission "
                u"for learner {}"
            ).format(self)
            logger.exception(error_message)
            raise PeerAssessmentInternalError(error_message)

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
            item_query = self.graded.filter(
                submission_uuid=submission_uuid
            ).order_by("-started_at", "-id")
            items = list(item_query[:1])
            if not items:
                msg = (
                    u"No open assessment was found for learner {} while assessing "
                    u"submission UUID {}."
                ).format(self.student_id, submission_uuid)
                raise PeerAssessmentWorkflowError(msg)
            item = items[0]
            item.assessment = assessment
            item.save()

            if not item.author.grading_completed_at:
                if item.author.graded_by.filter(assessment__isnull=False).count() >= num_required_grades:
                    item.author.grading_completed_at = now()
                    item.author.save()

        except (DatabaseError, PeerWorkflowItem.DoesNotExist):
            error_message = (
                u"An internal error occurred while retrieving a workflow item for "
                u"learner {}. Workflow Items are created when submissions are "
                u"pulled for assessment."
            ).format(self.student_id)
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

    def __str__(self):
        return repr(self)


@python_2_unicode_compatible
class PeerWorkflowItem(models.Model):
    """Represents an assessment associated with a particular workflow

    Created every time a submission is requested for peer assessment. The
    associated workflow represents the scorer of the given submission, and the
    assessment represents the completed assessment for this work item.

    """
    scorer = models.ForeignKey(PeerWorkflow, related_name='graded', on_delete=models.CASCADE)
    author = models.ForeignKey(PeerWorkflow, related_name='graded_by', on_delete=models.CASCADE)
    submission_uuid = models.CharField(max_length=128, db_index=True)
    started_at = models.DateTimeField(default=now, db_index=True)
    assessment = models.ForeignKey(Assessment, null=True, on_delete=models.CASCADE)

    # This WorkflowItem was used to determine the final score for the Workflow.
    scored = models.BooleanField(default=False)

    @classmethod
    def get_scored_assessments(cls, submission_uuid):
        """
        Return all scored assessments for a given submission.

        Args:
            submission_uuid (str): The UUID of the submission.

        Returns:
            QuerySet of Assessment objects.

        """
        return Assessment.objects.filter(
            pk__in=[
                item.assessment.pk for item in PeerWorkflowItem.objects.filter(
                    submission_uuid=submission_uuid, scored=True
                )
            ]
        )

    class Meta:
        ordering = ["started_at", "id"]
        app_label = "assessment"

    def __repr__(self):
        return (
            "PeerWorkflowItem(scorer={0.scorer}, author={0.author}, "
            "submission_uuid={0.submission_uuid}, "
            "started_at={0.started_at}, assessment={0.assessment}, "
            "scored={0.scored})"
        ).format(self)

    def __str__(self):
        return repr(self)
