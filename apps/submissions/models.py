"""
Submission models hold student responses to problems, scores, and a history of
those scores. It is intended to be a general purpose store that is usable by
different problem types, and is therefore ignorant of ORA workflow.

NOTE: We've switched to migrations, so if you make any edits to this file, you
need to then generate a matching migration for it using:

    ./manage.py schemamigration submissions --auto

"""
import json
import logging

from django.db import models, DatabaseError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now
from django_extensions.db.fields import UUIDField


logger = logging.getLogger(__name__)


class StudentItem(models.Model):
    """Represents a single item for a single course for a single user.

    This is typically an XBlock problem, but could be something more generic
    like class participation.

    """
    # The anonymized Student ID that the XBlock sees, not their real ID.
    student_id = models.CharField(max_length=255, blank=False, db_index=True)

    # Not sure yet whether these are legacy course_ids or new course_ids
    course_id = models.CharField(max_length=255, blank=False, db_index=True)

    # Version independent, course-local content identifier, i.e. the problem
    # This is the block_id for XBlock items.
    item_id = models.CharField(max_length=255, blank=False, db_index=True)

    # What kind of problem is this? The XBlock tag if it's an XBlock
    item_type = models.CharField(max_length=100)

    def __repr__(self):
        return repr(dict(
            student_id=self.student_id,
            course_id=self.course_id,
            item_id=self.item_id,
            item_type=self.item_type,
        ))

    def __unicode__(self):
        return u"({0.student_id}, {0.course_id}, {0.item_type}, {0.item_id})".format(self)

    class Meta:
        unique_together = (
            # For integrity reasons, and looking up all of a student's items
            ("course_id", "student_id", "item_id"),
        )


class Submission(models.Model):
    """A single response by a student for a given problem in a given course.

    A student may have multiple submissions for the same problem. Submissions
    should never be mutated. If the student makes another Submission, or if we
    have to make corrective Submissions to fix bugs, those should be new
    objects. We want to keep Submissions immutable both for audit purposes, and
    because it makes caching trivial.

    """
    MAXSIZE = 1024*100  # 100KB

    uuid = UUIDField(version=1, db_index=True)

    student_item = models.ForeignKey(StudentItem)

    # Which attempt is this? Consecutive Submissions do not necessarily have
    # increasing attempt_number entries -- e.g. re-scoring a buggy problem.
    attempt_number = models.PositiveIntegerField()

    # submitted_at is separate from created_at to support re-scoring and other
    # processes that might create Submission objects for past user actions.
    submitted_at = models.DateTimeField(default=now, db_index=True)

    # When this row was created.
    created_at = models.DateTimeField(editable=False, default=now, db_index=True)

    # The answer (JSON-serialized)
    raw_answer = models.TextField(blank=True)

    def __repr__(self):
        return repr(dict(
            uuid=self.uuid,
            student_item=self.student_item,
            attempt_number=self.attempt_number,
            submitted_at=self.submitted_at,
            created_at=self.created_at,
            raw_answer=self.raw_answer,
        ))

    def __unicode__(self):
        return u"Submission {}".format(self.uuid)

    class Meta:
        ordering = ["-submitted_at", "-id"]


class Score(models.Model):
    """What the user scored for a given StudentItem at a given time.

    Note that while a Score *can* be tied to a Submission, it doesn't *have* to.
    Specifically, if we want to have scores for things that are not a part of
    the courseware (like "class participation"), there would be no corresponding
    Submission.
    """
    student_item = models.ForeignKey(StudentItem)
    submission = models.ForeignKey(Submission, null=True)
    points_earned = models.PositiveIntegerField(default=0)
    points_possible = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(editable=False, default=now, db_index=True)

    # Flag to indicate that this score should reset the current "highest" score
    reset = models.BooleanField(default=False)

    @property
    def submission_uuid(self):
        """
        Retrieve the submission UUID associated with this score.
        If the score isn't associated with a submission (for example, if this is
        a "reset" score or a a non-courseware item like "class participation"),
        then this will return None.

        Returns:
            str or None

        """
        if self.submission is not None:
            return self.submission.uuid
        else:
            return None

    def to_float(self):
        """
        Calculate (points earned) / (points possible).
        If points possible is None (e.g. this is a "hidden" score)
        then return None.

        Returns:
            float or None

        """
        if self.points_possible == 0:
            return None
        return float(self.points_earned) / self.points_possible

    def __repr__(self):
        return repr(dict(
            student_item=self.student_item,
            submission=self.submission,
            created_at=self.created_at,
            points_earned=self.points_earned,
            points_possible=self.points_possible,
        ))

    def is_hidden(self):
        """
        By convention, a score of 0/0 is not displayed to users.
        Hidden scores are filtered by the submissions API.

        Returns:
            bool: Whether the score should be hidden.

        """
        return self.points_possible == 0

    @classmethod
    def create_reset_score(cls, student_item):
        """
        Create a "reset" score (a score with a null submission).

        Only scores created after the most recent "reset" score
        should be used to determine a student's effective score.

        Args:
            student_item (StudentItem): The student item model.

        Returns:
            Score: The newly created "reset" score.

        Raises:
            DatabaseError: An error occurred while creating the score

        """
        # By setting the "reset" flag, we ensure that the "highest"
        # score in the score summary will point to this score.
        # By setting points earned and points possible to 0,
        # we ensure that this score will be hidden from the user.
        return cls.objects.create(
            student_item=student_item,
            submission=None,
            points_earned=0,
            points_possible=0,
            reset=True,
        )

    def __unicode__(self):
        return u"{0.points_earned}/{0.points_possible}".format(self)


class ScoreSummary(models.Model):
    """Running store of the highest and most recent Scores for a StudentItem."""
    student_item = models.ForeignKey(StudentItem, unique=True)

    highest = models.ForeignKey(Score, related_name="+")
    latest = models.ForeignKey(Score, related_name="+")

    class Meta:
        verbose_name_plural = "Score Summaries"

    @receiver(post_save, sender=Score)
    def update_score_summary(sender, **kwargs):
        """
        Listen for new Scores and update the relevant ScoreSummary.

        Args:
            sender: not used

        Kwargs:
            instance (Score): The score model whose save triggered this receiver.

        """
        score = kwargs['instance']
        try:
            score_summary = ScoreSummary.objects.get(
                student_item=score.student_item
            )
            score_summary.latest = score

            # A score with the "reset" flag set will always replace the current highest score
            if score.reset:
                score_summary.highest = score
            # The conversion to a float may return None if points possible is zero
            # In Python, None is always less than an integer, so any score
            # with non-null points possible will take precedence.
            elif score.to_float() > score_summary.highest.to_float():
                score_summary.highest = score
            score_summary.save()
        except ScoreSummary.DoesNotExist:
            ScoreSummary.objects.create(
                student_item=score.student_item,
                highest=score,
                latest=score,
            )
        except DatabaseError as err:
            logger.exception(
                u"Error while updating score summary for student item {}"
                .format(score.student_item)
            )
