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
        "training", # User needs to practice grading using example essays
    ]

    STATUSES = [
        "waiting",  # User has done all necessary assessment but hasn't been
                    # graded yet -- we're waiting for assessments of their
                    # submission by others.
        "done",  # Complete
    ]

    STATUS_VALUES = STEPS + STATUSES

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
        status_dict = {}
        steps = self._get_steps()
        for step in steps:
            status_dict[step.name] = {
                "complete": step.api().submitter_is_finished(
                    self.submission_uuid,
                    assessment_requirements.get(step.name, {})
                )
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
        from openassessment.assessment.api import peer as peer_api
        from openassessment.assessment.api import self as self_api

        # If we're done, we're done -- it doesn't matter if requirements have
        # changed because we've already written a score.
        if self.status == self.STATUS.done:
            return

        # Update our AssessmentWorkflowStep models with the latest from our APIs
        steps = self._get_steps()

        # Go through each step and update its status.
        for step in steps:
            step.update(self.submission_uuid, assessment_requirements)

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

    def _get_steps(self):
        """
        Simple helper function for retrieving all the steps in the given
        Workflow.
        """
        steps = list(self.steps.all())
        if not steps:
            # If no steps exist for this AssessmentWorkflow, assume
            # peer -> self for backwards compatibility
            self.steps.add(
                AssessmentWorkflowStep(name=self.STATUS.peer, order_num=0),
                AssessmentWorkflowStep(name=self.STATUS.self, order_num=1)
            )
            steps = list(self.steps.all())
        return steps

    def set_score(self, score):
        """
        Set a score for the workflow.

        Scores are persisted via the Submissions API, separate from the Workflow
        Data. Score is associated with the same submission_uuid as this workflow

        Args:
            score (dict): A dict containing 'points_earned' and
                'points_possible'.

        """
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

    class Meta:
        ordering = ["workflow", "order_num"]

    def is_submitter_complete(self):
        return self.submitter_completed_at is not None

    def is_assessment_complete(self):
        return self.assessment_completed_at is not None

    def api(self):
        """
        Returns an API associated with this workflow step. If no API is
        associated with this workflow step, None is returned.
        """
        from openassessment.assessment.api import peer as peer_api
        from openassessment.assessment.api import self as self_api
        from openassessment.assessment.api import student_training as student_training
        api = None
        if self.name == AssessmentWorkflow.STATUS.self:
            api = self_api
        elif self.name == AssessmentWorkflow.STATUS.peer:
            api = peer_api
        elif self.name == AssessmentWorkflow.STATUS.training:
            api = student_training
        return api

    def update(self, submission_uuid, assessment_requirements):
        """
        Updates the AssessmentWorkflowStep models with the requirements
        specified from the Workflow API.

        Intended for internal use by update_from_assessments(). See
        update_from_assessments() documentation for more details.
        """
        # Once a step is completed, it will not be revisited based on updated
        # requirements.
        step_changed = False
        step_reqs = assessment_requirements.get(self.name, {})

        # Has the user completed their obligations for this step?
        if (not self.is_submitter_complete() and
                self.api().submitter_is_finished(submission_uuid, step_reqs)):
            self.submitter_completed_at = now()
            step_changed = True

        # Has the step received a score?
        if (not self.is_assessment_complete() and
                self.api().assessment_is_finished(submission_uuid, step_reqs)):
            self.assessment_completed_at = now()
            step_changed = True

        if step_changed:
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
