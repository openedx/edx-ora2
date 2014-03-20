"""
Workflow models are intended to track which step the student is in during the
assessment process. The submission state is not explicitly tracked because
the assessment workflow only begins after a submission has been created.

NOTE: We've switched to migrations, so if you make any edits to this file, you
need to then generate a matching migration for it using:

    ./manage.py schemamigration openassessment.workflow --auto

"""
from django.db import models
from django_extensions.db.fields import UUIDField
from model_utils import Choices
from model_utils.models import StatusModel, TimeStampedModel

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
        """Latest score for the submission we're tracking.

        Note that while it is usually the case that we're setting the score,
        that may not always be the case. We may have some course staff override.
        """
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
        from openassessment.assessment import peer_api
        peer_requirements = assessment_requirements["peer"]
        return peer_api.is_complete(self.submission_uuid, peer_requirements)

    def _is_self_complete(self):
        from openassessment.assessment import self_api
        return self_api.is_complete(self.submission_uuid)

    def update_from_assessments(self, assessment_requirements):
        """Query self and peer APIs and change our status if appropriate.

        If the status is done, we do nothing. Once something is done, we never
        move back to any other status.

        By default, an `AssessmentWorkflow` starts with status `peer`.

        If the peer API says that our submitter's requirements are met -- that
        the submitter of the submission we're tracking has assessed the required
        number of other submissions -- then the status will move to `self`.

        If the self API says that the person who created the submission we're
        tracking has assessed themselves, then we move to `waiting`.

        If we're in the `waiting` status, and the peer API says it can score
        this submission (meaning other students have created enough assessments
        of it), then we record the score in the submissions API and move our
        `status` to `done`.

        Args:
            assessment_requirements (dict): Dictionary that currently looks like:
                `{"peer": {"must_grade": <int>, "must_be_graded_by": <int>}}`
                `must_grade` is the number of assessments a student must complete.
                `must_be_graded_by` is the number of assessments a submission must
                receive to be scored. `must_grade` should be greater than
                `must_be_graded_by` to ensure that everyone will get scored.
                The intention is to eventually pass in more assessment sequence
                specific requirements in this dict.

        """
        from openassessment.assessment import peer_api

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
