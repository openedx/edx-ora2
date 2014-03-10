"""
Workflow models are intended to track which step the student is in during the
assessment process. The submission state is not explicitly tracked because
the assessment workflow only begins after a submission has been created.
"""
from django.db import models
from django_extensions.db.fields import UUIDField
from model_utils import Choices
from model_utils.models import StatusModel, TimeStampedModel

from openassessment.assessment import peer_api, self_api
from submissions import api as sub_api


class AssessmentWorkflow(TimeStampedModel, StatusModel):
    """Tracks the open-ended assessment status of a student submission.

    It's important to note that although we track the status as an explicit
    field here, it is not the canonical status. This is because the
    determination of what we need to do in order to be "done" is specified by
    the OpenAssessmentBlock problem definition and can change. So every time
    we are asked where the student is, we have to query the peer, self, and
    later other assessment APIs with the latest requirements (e.g. "number of
    submissions you have to assess = 5"). The "status" field on this model is
    an after the fact recording of the last known state of that information so
    we can search easily.
    """
    STATUS = Choices(  # implicit "status" field
        "peer",  # User needs to assess peer submissions
        "self",  # User needs to assess themselves
        "waiting",  # User has done all necessary assessment but hasn't been
                    # graded yet -- we're waiting for assessments of their
                    # submission by others.
        "done",  # Complete
    )

    submission_uuid = models.CharField(max_length=36, db_index=True, unique=True)
    uuid = UUIDField(version=1, db_index=True, unique=True)

    class Meta:
        ordering = ["-created"]
        # TODO: In migration, need a non-unique index on (course_id, item_id, status)

    @property
    def score(self):
        return sub_api.get_latest_score_for_submission(self.submission_uuid)

    def status_details(self, assessment_requirements):
        return {
            "peer": {
                "complete": self._is_peer_complete(assessment_requirements),
            },
            "self": {
                "complete": self._is_self_complete(),
            },
        }

    def _is_peer_complete(self, assessment_requirements):
        peer_requirements = assessment_requirements["peer"]
        return peer_api.is_complete(self.submission_uuid, peer_requirements)

    def _is_self_complete(self):
        return self_api.is_complete(self.submission_uuid)

    def update_from_assessments(self, assessment_requirements):
        # If we're done, we're done -- it doesn't matter if requirements have
        # changed because we've already written a score.
        if self.status == self.STATUS.done:
            return

        # Have they completed the peer and self steps?
        peer_complete = self._is_peer_complete(assessment_requirements)
        self_complete = self._is_self_complete()

        if peer_complete and self_complete:
            # If they've completed both, they're at least waiting, possibly done
            new_status = self.STATUS.waiting
        elif peer_complete:
            # If they haven't done self assessment yet, that's their status
            new_status = self.STATUS.self
        else:
            # Default starting status is peer
            new_status = self.STATUS.peer
            peer_api.create_peer_workflow(self.submission_uuid)

        # If we're at least waiting, let's check if we have a peer score and
        # can move all the way to done
        if new_status == self.STATUS.waiting:
            score = peer_api.get_score(
                self.submission_uuid, assessment_requirements["peer"]
            )
            if score:
                sub_api.set_score(
                    self.submission_uuid,
                    score["points_earned"],
                    score["points_possible"]
                )
                new_status = self.STATUS.done

        # Finally save our changes if the status has changed
        if self.status != new_status:
            self.status = new_status
            self.save()



# Just here to record thoughts for later:
#
# class AssessmentWorkflowEvent(models.Model):
#     workflow = models.ForeignKey(AssessmentWorkflow, related_name="events")
#     app = models.CharField(max_length=50)
#     event_type = models.CharField(max_length=255)
#     event_data = models.TextField()
#     description = models.TextField()
#     created_at = models.DateTimeField(default=now, db_index=True)
