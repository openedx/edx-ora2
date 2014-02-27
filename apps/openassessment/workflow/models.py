"""
Workflow models serve the following functions:

1. Show what evaluation step a student is in for a given problem.
2. To know what the evaluation sequence is. This is canonically stored in the
OpenAssessmentBlock's problem definition, but we have to have a copy of it so
that the Workflow API can interact with things that are not XBlock aware.
3. Once an evaluation step completes, to decide whether to advance to the next
step or (if it's the last step), to determine the score we write for this
StudentItem.
4. Record a history of everything that's happened with this workflow. This is
useful for debugging and research.

Whenever possible, canonical storage of things like scores and whether a student
has completed an evaluation step should be kept with those evaluation apps
(e.g. openassessment.peer, openassessment.self).


things others ask of us:

things we ask/tell others:

workflow_created()
has_score() ?
complete() ?
open() ?




"""
from django.db import models
from django.utils.timezone import now
from django_extensions.db.fields import UUIDField
from model_utils import Choices
from model_utils.models import StatusModel, TimeStampedModel

class AssessmentWorkflow(TimeStampedModel, StatusModel):
    """Tracks the open-ended assessment status of a student submission.

    """
    STATUS = Choices("peer", "self", "done")

    submission_uuid = models.CharField(max_length=255, db_index=True)
    uuid = UUIDField(version=1, db_index=True, unique=True)

    # JSON state field -- initially going to be a list of evaluators like:
    # ["peereval", "selfeval"], but may later have more complex data that
    # determine thresholds for advancing to the next step or specifying how to
    # decide the final score.
    # state = models.TextField()

    class Meta:
        ordering = ["-created"]

    # Also need a non-unique index on (course_id, item_id, status)


# class AssessmentWorkflowEvent(models.Model):
#     workflow = models.ForeignKey(AssessmentWorkflow, related_name="events")
#
#     app = models.CharField(max_length=50)
#     event_type = models.CharField(max_length=255)
#     event_data = models.TextField()
#     description = models.TextField()
#
#     created_at = models.DateTimeField(default=now, db_index=True)
