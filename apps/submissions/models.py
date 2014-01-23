"""
This holds generic submissions and scores information. Is is ignorant of
workflows, ORA, etc. So the flow is this:

Student submission:

* XBlock creates a Submission
* submissions app sends a general notification that a submission has happened
* openresponse can listen for that signal if it wants, or query itself on demand
* when openresponse is satistifed that it has collected enough information to
  score the student, it will push that score information back to this app.
* when the LMS wants to know what raw scores a student has, it calls this app.

Things to consider probably aren't worth the extra effort/complexity in the MVP:
* Many to Many relations for students-submissions, evaluations-submissions
* Version ID (this doesn't work until split-mongostore comes into being)

"""
from django.db import models
from django.utils.timezone import now

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

    class Meta:
        unique_together = (
            # For integrity reasons, and looking up all of a student's items
            ("course_id", "student_id", "item_id"),

            # Composite index for getting information across a course
            ("course_id", "item_id"),
        )


class Submission(models.Model):
    """A single response by a student for a given problem in a given course.

    A student may have multiple submissions for the same problem.

    """
    student_item = models.ForeignKey(StudentItem)

    # Which attempt is this? Consecutive Submissions do not necessarily have
    # increasing attempt_number entries -- e.g. re-scoring a buggy problem.
    attempt_number = models.PositiveIntegerField()

    # submitted_at is separate from created_at to support re-scoring and other
    # processes that might create Submission objects for past user actions.
    submitted_at = models.DateTimeField(default=now, db_index=True)

    # When this row was created.
    created_at = models.DateTimeField(editable=False, default=now, db_index=True)

    # The actual answer, assumed to be a JSON string
    answer = models.TextField(blank=True)


class Score(models.Model):
    """What the user scored for a given StudentItem.

    TODO: Make a ScoreHistory that has more detailed log information so that we
          can reconstruct what the state was at a given point in time and debug
          more easily.
    """
    student_item = models.ForeignKey(StudentItem)
    submission = models.ForeignKey(Submission, null=True)
    points_earned = models.PositiveIntegerField(default=0)
    points_possible = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(editable=False, default=now, db_index=True)

