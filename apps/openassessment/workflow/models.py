"""
Workflow models are intended to track which step the student is in during the
assessment process. The submission state is not explicitly tracked because
the assessment workflow only begins after a submission has been created.

NOTE: We've switched to migrations, so if you make any edits to this file, you
need to then generate a matching migration for it using:

    ./manage.py schemamigration openassessment.workflow --auto

"""
from datetime import datetime
import logging
import importlib

from django.conf import settings
from django.db import models
from django_extensions.db.fields import UUIDField
from django.utils.timezone import now
from model_utils import Choices
from model_utils.models import StatusModel, TimeStampedModel

from submissions import api as sub_api

logger = logging.getLogger('openassessment.workflow.models')

# This will (hopefully soon) be replaced with calls to the event-tracking API:
#   https://github.com/edx/event-tracking
if hasattr(settings, "EDX_ORA2") and "EVENT_LOGGER" in settings.EDX_ORA2:
    func_path = settings.EDX_ORA2["EVENT_LOGGER"]
    module_name, func_name = func_path.rsplit('.', 1)
    emit_event = getattr(importlib.import_module(module_name), func_name)
else:
    emit_event = lambda event: logger.info("Event: " + unicode(event))


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
    STEPS = [
        "peer",  # User needs to assess peer submissions
        "self",  # User needs to assess themselves
    ]

    STATUS_VALUES = STEPS + [
        "waiting",  # User has done all necessary assessment but hasn't been
                    # graded yet -- we're waiting for assessments of their
                    # submission by others.
        "done",  # Complete
    ]

    STATUS = Choices(*STATUS_VALUES)  # implicit "status" field

    submission_uuid = models.CharField(max_length=36, db_index=True, unique=True)
    uuid = UUIDField(version=1, db_index=True, unique=True)

    # These values are used to find workflows for a particular item
    # in a course without needing to look up the submissions for that item.
    # Because submissions are immutable, we can safely duplicate the values
    # here without violating data integrity.
    course_id = models.CharField(max_length=255, blank=False, db_index=True)
    item_id = models.CharField(max_length=255, blank=False, db_index=True)

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
        from openassessment.assessment import peer_api, self_api

        status_dict = {}

        if "peer" in assessment_requirements:
            status_dict["peer"] = {
                "complete": peer_api.submitter_is_finished(
                    self.submission_uuid,
                    assessment_requirements["peer"]
                )
            }
        if "self" in assessment_requirements:
            status_dict["self"] = {
                "complete": self_api.submitter_is_finished(self.submission_uuid, {})
            }

        return status_dict

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
        from openassessment.assessment import peer_api, self_api

        # If we're done, we're done -- it doesn't matter if requirements have
        # changed because we've already written a score.
        if self.status == self.STATUS.done:
            return

        # Update our AssessmentWorkflowStep models with the latest from our APIs
        steps = self.update_steps(assessment_requirements)

        # Fetch name of the first step that the submitter hasn't yet completed.
        new_status = next(
            (step.name for step in steps if step.submitter_completed_at is None),
            self.STATUS.waiting  # if nothing's left to complete, we're waiting
        )

        # If the submitter has done all they need to do, let's check to see if
        # all steps have been fully assessed (i.e. we can score it).
        if (new_status == self.STATUS.waiting and
            all(step.assessment_completed_at for step in steps)):

            # At this point, we're trying to give a score. We currently have a
            # very simple rule for this -- if it has a peer step, use that for
            # scoring. If not, use the self step. Later on, we may put more
            # interesting rules here.
            step_names = [step.name for step in steps]
            score = None
            if self.STATUS.peer in step_names:
                score = peer_api.get_score(
                    self.submission_uuid,
                    assessment_requirements[self.STATUS.peer]
                )
            elif self.STATUS.self in step_names:
                score = self_api.get_score(self.submission_uuid, {})

            if score:
                self.set_score(score)
                new_status = self.STATUS.done

        # Finally save our changes if the status has changed
        if self.status != new_status:
            self.status = new_status
            self.save()


    def update_steps(self, assessment_requirements):
        from openassessment.assessment import peer_api, self_api

        steps = list(self.steps.all())
        if not steps:
            # If no steps exist for this AssessmentWorkflow, assume
            # peer -> self for backwards compatibility
            self.steps.add(
                AssessmentWorkflowStep(name=self.STATUS.peer, order_num=0),
                AssessmentWorkflowStep(name=self.STATUS.self, order_num=1)
            )
            steps = list(self.steps.all())

        # Mapping of step names to the APIs that power them
        steps_to_apis = {
            self.STATUS.self: self_api,
            self.STATUS.peer: peer_api
        }

        # Go through each step and update its status. Note that because we take
        # the philosophy that once you're done, you're done. That means
        for step in steps:
            step_changed = False
            step_api = steps_to_apis[step.name]
            step_reqs = assessment_requirements.get(step.name, {})

            # Has the user completed their obligations for this step?
            if (step.submitter_completed_at is None and
                step_api.submitter_is_finished(self.submission_uuid, step_reqs)):
                step.submitter_completed_at = now()
                step_changed = True

            # Has the step received a score?
            if (step.assessment_completed_at is None and
                step_api.assessment_is_finished(self.submission_uuid, step_reqs)):
                step.assessment_completed_at = now()
                step_changed = True

            if step_changed:
                step.save()

        return steps


    def set_score(self, score):
        sub_api.set_score(
            self.submission_uuid,
            score["points_earned"],
            score["points_possible"]
        )

        # This should be replaced by using the event tracking API, but
        # that's not quite ready yet. So we're making this temp hack.
        emit_event({
            "context": {
                "course_id": self.course_id
            },
            "event": {
                "submission_uuid": self.submission_uuid,
                "points_earned": score["points_earned"],
                "points_possible": score["points_possible"],
            },
            "event_source": "server",
            "event_type": "openassessment.workflow.score",
            "time": datetime.utcnow(),
        })


class AssessmentWorkflowStep(models.Model):
    """An individual step in the overall workflow process.

    Similar caveats apply to this class as apply to `AssessmentWorkflow`. What
    we're storing in the database is usually but not always current information.
    In particular, if the problem definition has changed the requirements for a
    particular step in the workflow, then what is in the database will be out of
    sync until someone views this problem again (which will trigger a workflow
    update to occur).

    """
    workflow = models.ForeignKey(AssessmentWorkflow, related_name="steps")
    name = models.CharField(max_length=20)
    submitter_completed_at = models.DateTimeField(default=None, null=True)
    assessment_completed_at = models.DateTimeField(default=None, null=True)
    order_num = models.PositiveIntegerField()

    # Store the score for this step as well?
    class Meta:
        ordering = ["workflow", "order_num"]


# Just here to record thoughts for later:
#
# class AssessmentWorkflowEvent(models.Model):
#     workflow = models.ForeignKey(AssessmentWorkflow, related_name="events")
#     app = models.CharField(max_length=50)
#     event_type = models.CharField(max_length=255)
#     event_data = models.TextField()
#     description = models.TextField()
#     created_at = models.DateTimeField(default=now, db_index=True)
