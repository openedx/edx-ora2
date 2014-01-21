from django.db import models

MAX_LENGTH = 255
ESSAY_BODY_MAX_LENGTH = 10000
GRADING_TYPES = (
    ('PE', 'Peer Assessment'),
)


class Submission(models.Model):
    """A response to a question submitted for evaluation.

    The Submission is a uniform object representing some response that may be evaluated by any number of evaluation
    modules. Each Submission should represent a unique response to a question.  Multiple responses to a question from
    the same student should be represented with a unique Submission.

    Evaluation of a submission by any means will result in a number of associated Scorings.

    """
    student_id = models.CharField(max_length=MAX_LENGTH, db_index=True)
    location_id = models.CharField(max_length=MAX_LENGTH, default="")
    course_id = models.CharField(max_length=MAX_LENGTH, default="")
    essay_body = models.TextField(max_length=ESSAY_BODY_MAX_LENGTH, default="")
    preferred_grading = models.CharField(max_length=2, choices=GRADING_TYPES)
    submitted_date = models.DateTimeField(auto_now_add=True)


class Scoring(models.Model):
    """A particular evaluation for a Submission.

    This model represents a single evaluation of a Submission. Any evaluation module may create a number of Scorings
    for a particular Submission based on the internal workflow.

    Any number of Feedback objects may be associated with a single Scoring.

    """
    points_earned = models.PositiveIntegerField(default=0)
    points_possible = models.PositiveIntegerField(default=0)
    scored_date = models.DateTimeField()
    student_id = models.CharField(max_length=MAX_LENGTH)
    score_type = models.CharField(max_length=2, choices=GRADING_TYPES)
    confidence = models.FloatField(default=0.0)
    included = models.BooleanField(default=True)
    submission = models.ForeignKey(Submission)


class Feedback(models.Model):
    """A particular amount of Feedback associated with a Scoring for a Submission.

    Represents the smallest variable data for an evaluation of a Submission. All Feedback for a particular Submission
    is collected in a Scoring, which is associated with a single evaluator.

    """
    text = models.TextField(max_length=MAX_LENGTH, default="")
    score = models.ForeignKey(Scoring)
