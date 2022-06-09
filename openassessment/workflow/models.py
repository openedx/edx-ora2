"""
Workflow models are intended to track which step the student is in during the
assessment process. The submission state is not explicitly tracked because
the assessment workflow only begins after a submission has been created.

NOTE: We've switched to migrations, so if you make any edits to this file, you
need to then generate a matching migration for it using:

    ./manage.py schemamigration openassessment.workflow --auto

"""


import importlib
import logging
from uuid import uuid4

from django.conf import settings
from django.db import DatabaseError, models, transaction
from django.dispatch import receiver
from django.utils.timezone import now

from model_utils import Choices
from model_utils.models import StatusModel, TimeStampedModel

from submissions import api as sub_api, team_api as sub_team_api
from openassessment.assessment.errors.base import AssessmentError
from openassessment.assessment.signals import assessment_complete_signal

from .errors import AssessmentApiLoadError, AssessmentWorkflowError, AssessmentWorkflowInternalError

logger = logging.getLogger('openassessment.workflow.models')  # pylint: disable=invalid-name


# To encapsulate the workflow API from the assessment API,
# we use dependency injection.  The Django settings define
# a dictionary mapping assessment step names to the Python module path
# that implements the corresponding assessment API.
# For backwards compatibility, we provide a default configuration as well
DEFAULT_ASSESSMENT_API_DICT = {
    'peer': 'openassessment.assessment.api.peer',
    'self': 'openassessment.assessment.api.self',
    'training': 'openassessment.assessment.api.student_training',
}
ASSESSMENT_API_DICT = getattr(
    settings, 'ORA2_ASSESSMENTS',
    DEFAULT_ASSESSMENT_API_DICT
)


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
    STAFF_STEP_NAME = 'staff'

    STEPS = sorted(ASSESSMENT_API_DICT.keys())

    STATUSES = [
        # User has done all necessary assessment but hasn't been
        # graded yet -- we're waiting for assessments of their
        # submission by others.
        "waiting",
        "done",  # Complete
        "cancelled"  # User submission has been cancelled.
    ]

    STATUS_VALUES = STEPS + STATUSES

    STATUS = Choices(*STATUS_VALUES)  # implicit "status" field

    # For now, we use a simple scoring mechanism:
    # Once a student has completed all assessments,
    # we search assessment APIs
    # in priority order until one of the APIs provides a score.
    # We then use that score as the student's overall score.
    # This Django setting is a list of assessment steps (defined in `settings.ORA2_ASSESSMENTS`)
    # in descending priority order.
    DEFAULT_ASSESSMENT_SCORE_PRIORITY = ['peer', 'self']  # pylint: disable=invalid-name
    ASSESSMENT_SCORE_PRIORITY = getattr(
        settings, 'ORA2_ASSESSMENT_SCORE_PRIORITY',
        DEFAULT_ASSESSMENT_SCORE_PRIORITY
    )

    STAFF_ANNOTATION_TYPE = "staff_defined"

    submission_uuid = models.CharField(max_length=36, db_index=True, unique=True)
    uuid = models.UUIDField(db_index=True, unique=True, default=uuid4)

    # These values are used to find workflows for a particular item
    # in a course without needing to look up the submissions for that item.
    # Because submissions are immutable, we can safely duplicate the values
    # here without violating data integrity.
    course_id = models.CharField(max_length=255, blank=False, db_index=True)
    item_id = models.CharField(max_length=255, blank=False, db_index=True)

    class Meta:
        ordering = ["-created"]
        # TODO: In migration, need a non-unique index on (course_id, item_id, status)
        app_label = "workflow"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'staff' not in AssessmentWorkflow.STEPS:
            new_list = ['staff']
            new_list.extend(AssessmentWorkflow.STEPS)
            AssessmentWorkflow.STEPS = new_list
            AssessmentWorkflow.STATUS_VALUES = AssessmentWorkflow.STEPS + AssessmentWorkflow.STATUSES
            AssessmentWorkflow.STATUS = Choices(*AssessmentWorkflow.STATUS_VALUES)

        if 'staff' not in AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY:
            new_list = ['staff']
            new_list.extend(AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY)
            AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY = new_list

    @classmethod
    @transaction.atomic
    def start_workflow(cls, submission_uuid, step_names, on_init_params):
        """
        Start a new workflow.

        Args:
            submission_uuid (str): The UUID of the submission associated with this workflow.
            step_names (list): The names of the assessment steps in the workflow.
            on_init_params (dict): The parameters to pass to each assessment module
                on init.  Keys are the assessment step names.

        Returns:
            AssessmentWorkflow

        Raises:
            SubmissionNotFoundError
            SubmissionRequestError
            SubmissionInternalError
            DatabaseError
            Assessment-module specific errors
        """
        submission_dict = sub_api.get_submission_and_student(submission_uuid)

        staff_auto_added = False
        if 'staff' not in step_names:
            staff_auto_added = True
            new_list = ['staff']
            new_list.extend(step_names)
            step_names = new_list

        # Create the workflow and step models in the database
        # For now, set the status to waiting; we'll modify it later
        # based on the first step in the workflow.
        workflow = cls.objects.create(
            submission_uuid=submission_uuid,
            status=AssessmentWorkflow.STATUS.waiting,
            course_id=submission_dict['student_item']['course_id'],
            item_id=submission_dict['student_item']['item_id']
        )
        workflow_steps = [
            AssessmentWorkflowStep.objects.create(
                workflow=workflow, name=step, order_num=i
            )
            for i, step in enumerate(step_names)
        ]
        workflow.steps.add(*workflow_steps)

        # Initialize the assessment APIs
        has_started_first_step = False
        for step in workflow_steps:
            api = step.api()

            if api is not None:
                # Initialize the assessment module
                # We do this for every assessment module
                on_init_func = getattr(api, 'on_init', lambda submission_uuid, **params: None)
                on_init_func(submission_uuid, **on_init_params.get(step.name, {}))

                # If we auto-added a staff step, it is optional and should be marked complete immediately
                if step.name == "staff" and staff_auto_added:
                    step.assessment_completed_at = now()
                    step.save()

                # For the first valid step, update the workflow status
                # and notify the assessment module that it's being started
                if not has_started_first_step:
                    # Update the workflow
                    workflow.status = step.name
                    workflow.save()

                    # Notify the assessment module that it's being started
                    on_start_func = getattr(api, 'on_start', lambda submission_uuid: None)
                    on_start_func(submission_uuid)

                    # Remember that we've already started the first step
                    has_started_first_step = True

        # Update the workflow (in case some of the assessment modules are automatically complete)
        # We do NOT pass in requirements, on the assumption that any assessment module
        # that accepts requirements would NOT automatically complete.
        workflow.update_from_assessments(None)

        # Return the newly created workflow
        return workflow

    @property
    def score(self):
        """Latest score for the submission we're tracking.

        Returns:
            score (dict): The latest score for this workflow, or None if the workflow is incomplete.
        """
        score = None
        if self.status == self.STATUS.done:
            score = sub_api.get_latest_score_for_submission(self.submission_uuid)
        return score

    def status_details(self):
        """
        Returns workflow status in the form of a dictionary. Each step in the
        workflow is a key, and each key maps to a dictionary defining whether
        the step is complete (submitter requirements fulfilled) and graded (the
        submission has been assessed).

        For the 'peer' step there will be extra keys in its mapped dictionary:
        - 'peers_graded_count': how many peers the submitter has assessed
        - 'graded_by_count': how many peers the submitter been assessed by
        """
        status_dict = {}
        steps = self._get_steps()
        for step in steps:
            status_dict[step.name] = {
                "complete": step.is_submitter_complete(),
                "graded": step.is_assessment_complete(),
                "skipped": step.skipped
            }
            if step.name == 'peer':
                # the number passed here is arbitrary and ignored
                _, peers_graded_count = step.api().has_finished_required_evaluating(self.submission_uuid, 1)
                graded_by_count = step.api().get_graded_by_count(self.submission_uuid)
                status_dict[step.name]['peers_graded_count'] = peers_graded_count
                status_dict[step.name]['graded_by_count'] = graded_by_count
        return status_dict

    def get_score(self, assessment_requirements, step_for_name):
        """Iterate through the assessment APIs in priority order
         and return the first reported score.

        Args:
            assessment_requirements (dict): Dictionary passed to the assessment API.
                This defines the requirements for each assessment step; the APIs
                can refer to this to decide whether the requirements have been
                met.  Note that the requirements could change if the author
                updates the problem definition.
            step_for_name (dict): a key value pair for step name: step

        Returns:
             score dict.
        """
        score = None
        for assessment_step_name in self.ASSESSMENT_SCORE_PRIORITY:

            # Check if the problem contains this assessment type
            assessment_step = step_for_name.get(assessment_step_name)

            # Query the corresponding assessment API for a score
            # If we find one, then stop looking
            if assessment_step is not None:

                # Check if the assessment API defines a score function at all
                get_score_func = getattr(assessment_step.api(), 'get_score', None)
                if get_score_func is not None:
                    if assessment_requirements is None:
                        step_requirements = None
                    else:
                        step_requirements = assessment_requirements.get(assessment_step_name, {})
                    score = get_score_func(self.identifying_uuid, step_requirements)
                    if not score and assessment_step.is_staff_step():
                        if step_requirements and step_requirements.get('required', False):
                            break  # A staff score was not found, and one is required. Return None
                        continue  # A staff score was not found, but it is not required, so try the next type of score
                    break

        return score

    def update_from_assessments(self, assessment_requirements, override_submitter_requirements=False):
        """Query assessment APIs and change our status if appropriate.

        If the status is done, we do nothing. Once something is done, we never
        move back to any other status.

        If an assessment API says that our submitter's requirements are met, or if
        current assessment step can be skipped, then move to the next assessment.
        For example, in student training, if the submitter we're tracking has completed
        the training, they're allowed to continue. Whereas in peer assessment, it is
        allowed to skip that step so we mark it as started and move to the next assessment.
        So all skippable steps are in progress until completed. But user can complete
        next steps before those skippable ones.

        For every possible assessments, we find out all skippable assessments and mark
        them as skipped and consider that step already started (calling `on_start` for
        that assessmet api). Then choose the next un-skippable step as current step.

        If the submitter has finished all the assessments, then we change
        their status to `waiting`.

        If we're in the `waiting` status, and an assessment API says it can score
        this submission, then we record the score in the submissions API and move our
        `status` to `done`.

        By convention, if `assessment_requirements` is `None`, then assessment
        modules that need requirements should automatically say that they're incomplete.
        This allows us to update the workflow even when we don't know the
        current state of the problem.  For example, if we're updating the workflow
        at the completion of an asynchronous call, we won't necessarily know the
        current state of the problem, but we would still want to update assessments
        that don't have any requirements.

        Args:
            assessment_requirements (dict): Dictionary passed to the assessment API.
                This defines the requirements for each assessment step; the APIs
                can refer to this to decide whether the requirements have been
                met.  Note that the requirements could change if the author
                updates the problem definition.
            override_submitter_requirements (bool): If True, the presence of a new
                staff score will cause all of the submitter's requirements to be
                fulfilled, moving the workflow to DONE and exposing their grade.
        """
        if self.status == self.STATUS.cancelled:
            return

        # Update our AssessmentWorkflowStep models with the latest from our APIs
        steps = self._get_steps()

        step_for_name = {step.name: step for step in steps}

        new_staff_score = self.get_score(
            assessment_requirements,
            {self.STAFF_STEP_NAME: step_for_name.get(self.STAFF_STEP_NAME, None)}
        )
        if new_staff_score:
            # new_staff_score is just the most recent staff score, it may already be recorded in sub_api
            old_score = sub_api.get_latest_score_for_submission(self.submission_uuid)
            if (
                    # Does a prior score exist? Is it a staff score? Do the points earned match?
                    not old_score or self.STAFF_ANNOTATION_TYPE not in [
                        annotation['annotation_type'] for annotation in old_score['annotations']
                    ] or old_score['points_earned'] != new_staff_score['points_earned']
            ):
                # Set the staff score using submissions api, and log that fact
                self.set_staff_score(new_staff_score)
                self.save()
                logger.info(
                    "Workflow for submission UUID %s has updated score using %s assessment.",
                    self.submission_uuid,
                    self.STAFF_STEP_NAME
                )

                # Update the assessment_completed_at field for all steps
                # All steps are considered "assessment complete", as the staff score will override all
                for step in steps:
                    common_now = now()
                    step.assessment_completed_at = common_now
                    if override_submitter_requirements:
                        step.submitter_completed_at = common_now
                    step.save()

        if self.status == self.STATUS.done:
            return

        # Go through each step and update its status.
        for step in steps:
            step.update(self.submission_uuid, assessment_requirements)

        possible_statuses = []
        skipped_statuses = []
        all_statuses = []

        # find which are the next unskippable steps and steps that can be skipped
        for step in steps:
            all_statuses.append(step.name)
            if step.submitter_completed_at is None:
                if step.can_skip(self.submission_uuid, assessment_requirements):
                    skipped_statuses.append(step.name)
                else:
                    possible_statuses.append(step.name)

        # if there is no unskippable steps and only skippable steps left
        # then consider 1st skippable step as unskippable
        if len(possible_statuses) == 0 and len(skipped_statuses) > 0:
            unskip_step = skipped_statuses.pop()
            possible_statuses.append(unskip_step)
            if step_for_name.get(unskip_step):
                step_for_name[unskip_step].unskip()

        # mark skippable step as skipped only if current it's the current step
        # this prevent skipping a step too early
        for step_name in skipped_statuses:
            skip_step = step_for_name.get(step_name)
            if skip_step:
                # skip when its the current status or were before than current status
                if self.status in all_statuses and all_statuses.index(self.status) >= all_statuses.index(step_name):
                    skip_step.skip()
                    # skiping an assessment step should also start it
                    skip_step.start(self.submission_uuid)

        new_status = next(
            iter(possible_statuses),
            self.STATUS.waiting  # if nothing's left to complete, we're waiting
        )

        # If the submitter is beginning the next assessment, notify the
        # appropriate assessment API.
        new_step = step_for_name.get(new_status)
        if new_step is not None:
            new_step.start(self.submission_uuid)

        # If the submitter has done all they need to do, let's check to see if
        # all steps have been fully assessed (i.e. we can score it).
        if new_status == self.STATUS.waiting and all(step.assessment_completed_at for step in steps):
            score = self.get_score(assessment_requirements, step_for_name)
            # If we found a score, then we're done
            if score is not None:
                # Only set the score if it's not a staff score, in which case it will have already been set above
                if score.get("staff_id") is None:
                    self.set_score(score)
                new_status = self.STATUS.done

        # Finally save our changes if the status has changed
        if self.status != new_status:
            self.status = new_status
            self.save()
            logger.info(
                "Workflow for submission UUID %s has updated status to %s",
                self.submission_uuid,
                new_status
            )

    def _get_steps(self):
        """
        Simple helper function for retrieving all the steps in the given
        Workflow.
        """
        # A staff step must always be available, to allow for staff overrides
        try:
            self.steps.get(name=self.STATUS.staff)
        except AssessmentWorkflowStep.DoesNotExist:
            for step in list(self.steps.all()):
                step.order_num += 1
            staff_step, _ = AssessmentWorkflowStep.objects.get_or_create(
                name=self.STATUS.staff,
                order_num=0,
                assessment_completed_at=now(),
                workflow=self,
            )
            self.steps.add(  # pylint: disable=no-member
                staff_step
            )

        # Do not return steps that are not recognized in the AssessmentWorkflow.
        steps = list(self.steps.filter(name__in=AssessmentWorkflow.STEPS))
        if not steps:
            # If no steps exist for this AssessmentWorkflow, assume
            # peer -> self for backwards compatibility, with an optional staff override
            self.steps.add(  # pylint: disable=no-member
                AssessmentWorkflowStep(name=self.STATUS.staff, order_num=0, assessment_completed_at=now()),
                AssessmentWorkflowStep(name=self.STATUS.peer, order_num=1),
                AssessmentWorkflowStep(name=self.STATUS.self, order_num=2)
            )
            steps = list(self.steps.all())

        return steps

    def set_staff_score(self, score, reason=None):
        """
        Set a staff score for the workflow.

        Allows for staff scores to be set on a submission, with annotations to provide an audit trail if needed.
        This method can be used for both required staff grading, and staff overrides.

        Args:
            score (dict): A dict containing 'points_earned', 'points_possible', and 'staff_id'.
            is_override (bool): Optionally True if staff is overriding a previous score.
            reason (string): An optional parameter specifying the reason for the staff grade. A default value
                will be used in the event that this parameter is not provided.

        """
        if reason is None:
            reason = "A staff member has defined the score for this submission"
        sub_dict = sub_api.get_submission_and_student(self.submission_uuid)
        sub_api.reset_score(
            sub_dict['student_item']['student_id'],
            self.course_id,
            self.item_id,
            emit_signal=False
        )
        sub_api.set_score(
            self.submission_uuid,
            score["points_earned"],
            score["points_possible"],
            annotation_creator=score["staff_id"],
            annotation_type=self.STAFF_ANNOTATION_TYPE,
            annotation_reason=reason
        )

    def set_score(self, score):
        """
        Set a score for the workflow.

        Scores are persisted via the Submissions API, separate from the Workflow
        Data. Score is associated with the same submission_uuid as this workflow

        Args:
            score (dict): A dict containing 'points_earned' and
                'points_possible'.

        """
        if not self.staff_score_exists():
            sub_api.set_score(
                self.submission_uuid,
                score["points_earned"],
                score["points_possible"]
            )

    def staff_score_exists(self):
        """
        Check if a staff score exists for this submission.
        """
        steps = self._get_steps()
        step_for_name = {step.name: step for step in steps}
        staff_step = step_for_name.get(self.STAFF_STEP_NAME)
        if staff_step is not None:
            get_latest_func = getattr(staff_step.api(), 'get_latest_assessment', None)
            if get_latest_func is not None:
                staff_assessment = get_latest_func(self.submission_uuid)
                if staff_assessment is not None:
                    return True
        return False

    def cancel(self, assessment_requirements):
        """
        Cancel workflow for all steps.

        Set the points earned to 0 and workflow status to cancelled.

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
        steps = self._get_steps()
        step_for_name = {step.name: step for step in steps}

        # Cancel the workflow for each step.
        for step in steps:
            on_cancel_func = getattr(step.api(), 'on_cancel', None)
            if on_cancel_func is not None:
                on_cancel_func(self.identifying_uuid)

        try:
            score = self.get_score(assessment_requirements, step_for_name)
        except AssessmentError as exc:
            logger.info("TNL-5799, exception in get_score during cancellation. %s", exc)
            score = None

        # Set the points_earned to 0.
        if score is not None:
            score['points_earned'] = 0
            self.set_score(score)

        # Save status if it is not cancelled.
        if self.status != self.STATUS.cancelled:
            self.status = self.STATUS.cancelled
            self.save()
            logger.info(
                "Workflow for submission UUID %s has updated status to %s",
                self.submission_uuid,
                self.STATUS.cancelled
            )

    @classmethod
    def cancel_workflow(cls, submission_uuid, comments, cancelled_by_id, assessment_requirements):
        """
        Add an entry in AssessmentWorkflowCancellation table for a AssessmentWorkflow.

        AssessmentWorkflow which has been cancelled is no longer included in the
        peer grading pool.

        Args:
            submission_uuid (str): The UUID of the workflow's submission.
            comments (str): The reason for cancellation.
            cancelled_by_id (str): The ID of the user who cancelled the peer workflow.
            assessment_requirements (dict): Dictionary that currently looks like:
            `{"peer": {"must_grade": <int>, "must_be_graded_by": <int>}}`
            `must_grade` is the number of assessments a student must complete.
            `must_be_graded_by` is the number of assessments a submission must
            receive to be scored. `must_grade` should be greater than
            `must_be_graded_by` to ensure that everyone will get scored.
            The intention is to eventually pass in more assessment sequence
            specific requirements in this dict.
        """
        try:
            workflow = cls.objects.get(submission_uuid=submission_uuid)
            AssessmentWorkflowCancellation.create(workflow=workflow, comments=comments, cancelled_by_id=cancelled_by_id)
            # Cancel the related step's workflow.
            workflow.cancel(assessment_requirements)
        except (cls.DoesNotExist, cls.MultipleObjectsReturned) as ex:
            error_message = f"Error finding workflow for submission UUID {submission_uuid}."
            logger.exception(error_message)
            raise AssessmentWorkflowError(error_message) from ex
        except DatabaseError as ex:
            error_message = "Error creating assessment workflow cancellation for submission UUID {}.".format(
                submission_uuid)
            logger.exception(error_message)
            raise AssessmentWorkflowInternalError(error_message) from ex

    @classmethod
    def get_by_submission_uuid(cls, submission_uuid):
        """
        Retrieve the Assessment Workflow associated with the given submission UUID.

        Args:
            submission_uuid (str): The string representation of the UUID belonging
                to the associated Assessment Workflow.

        Returns:
            workflow (AssessmentWorkflow): The most recent assessment workflow associated with
                this submission UUID.

        Raises:
            AssessmentWorkflowError: Thrown when no workflow can be found for
                the associated submission UUID. This should always exist before a
                student is allow to request submissions for peer assessment.

        """
        try:
            return cls.objects.get(submission_uuid=submission_uuid)
        except cls.DoesNotExist:
            return None
        except DatabaseError as exc:
            message = f"Error finding workflow for submission UUID {submission_uuid} due to error: {exc}."
            logger.exception(message)
            raise AssessmentWorkflowError(message) from exc

    @property
    def is_cancelled(self):
        """
        Check if assessment workflow is cancelled.

        Returns:
            True/False
        """
        return self.cancellations.exists()

    @property
    def identifying_uuid(self):
        """
        Returns the primary identifying uuid for this workflow.
        Can be overriden by child classes
        """
        return self.submission_uuid


class TeamAssessmentWorkflow(AssessmentWorkflow):
    """
    Extends AssessmentWorkflow to support team based assessments.
    """
    # Only staff assessments are supported for teams
    TEAM_STAFF_STEP_NAME = 'teams'

    STEPS = [TEAM_STAFF_STEP_NAME]
    STATUS_VALUES = STEPS + AssessmentWorkflow.STATUSES
    STATUS = Choices(*STATUS_VALUES)  # implicit "status" field

    ASSESSMENT_SCORE_PRIORITY = [TEAM_STAFF_STEP_NAME]

    REQUIREMENTS = {TEAM_STAFF_STEP_NAME: {"required": True}}

    team_submission_uuid = models.CharField(max_length=128, unique=True, null=False)

    @classmethod
    def get_by_team_submission_uuid(cls, team_submission_uuid):
        """ Given a team submission uuid, return the associated workflow """
        try:
            return cls.objects.get(team_submission_uuid=team_submission_uuid)
        except cls.DoesNotExist:
            return None
        except DatabaseError as exc:
            message = (
                "Error finding workflow for team submission UUID {uuid} due to error: {exc}."
            ).format(uuid=team_submission_uuid, exc=exc)
            logger.exception(message)
            raise AssessmentWorkflowError(message) from exc

    @classmethod
    @transaction.atomic
    def start_workflow(cls, team_submission_uuid):  # pylint: disable=arguments-differ, arguments-renamed
        """ Start a team workflow """
        team_submission_dict = sub_team_api.get_team_submission(team_submission_uuid)
        try:
            referrence_learner_submission_uuid = team_submission_dict['submission_uuids'][0]
        except IndexError as ex:
            msg = f'No individual submission found for team submisison uuid {team_submission_uuid}'
            logger.exception(msg)
            raise AssessmentWorkflowInternalError(msg) from ex

        # Create the workflow in the database
        # For now, set the status to waiting; we'll modify it later
        team_workflow = cls.objects.create(
            team_submission_uuid=team_submission_uuid,
            submission_uuid=referrence_learner_submission_uuid,
            status=TeamAssessmentWorkflow.STATUS.waiting,
            course_id=team_submission_dict['course_id'],
            item_id=team_submission_dict['item_id']
        )
        team_staff_step = AssessmentWorkflowStep.objects.create(
            workflow=team_workflow, name=cls.TEAM_STAFF_STEP_NAME, order_num=0
        )
        team_workflow.steps.add(team_staff_step)

        team_assessment_api = team_staff_step.api()
        team_assessment_api.on_init(team_submission_uuid)

        return team_workflow

    @property
    def _team_staff_step(self):
        return self._get_steps()[0]

    def _get_steps(self):
        """
        Simple helper function for retrieving all the steps in the given
        TeamAssessmentWorkflow. In this case, it's somewhat trivial, since a
        TeamAssessmentWorkflow can only ever have a single 'teams' step.
        """

        if self.steps.count() != 1:
            err_msg = 'Team Assessment Workflow {} should have exactly one single "teams" step: {}'.format(
                self.uuid,
                self.steps.all()
            )
            logger.error(err_msg)
            raise AssessmentWorkflowInternalError(err_msg)
        step = self.steps.first()  # pylint: disable=no-member
        if step.name != TeamAssessmentWorkflow.STATUS.teams:
            err_msg = 'Team Assessment Workflow {} has a "{}" step rather than a teams step'.format(
                self.uuid,
                step.name
            )
            logger.error(err_msg)
            raise AssessmentWorkflowInternalError(err_msg)
        return [step]

    def update_from_assessments(self, override_submitter_requirements=False):
        # pylint: disable=arguments-differ, arguments-renamed
        """
        Update the workflow with potential new scores from assessments.
        """
        if self.status == self.STATUS.cancelled:
            return

        team_staff_step = self._team_staff_step
        team_staff_api = team_staff_step.api()
        new_score = team_staff_api.get_score(self.team_submission_uuid, self.REQUIREMENTS)
        if new_score:
            # new_score is just the most recent team score, it may already be recorded in sub_api
            old_score = sub_api.get_latest_score_for_submission(self.submission_uuid)
            if (
                    # Does a prior score exist?  Do the points earned match?
                    not old_score or self.STAFF_ANNOTATION_TYPE not in [
                        annotation['annotation_type'] for annotation in old_score['annotations']
                    ] or old_score['points_earned'] != new_score['points_earned']
            ):
                # Set the team staff score using team submissions api, and log that fact
                self._set_team_staff_score(new_score)
                self.save()
                logger.info(
                    "Team Workflow for team submission UUID %s has updated score using team staff assessment.",
                    self.team_submission_uuid
                )
                common_now = now()
                team_staff_step.assessment_completed_at = common_now
                team_staff_step.save()

            if override_submitter_requirements:
                team_staff_step.submitter_completed_at = common_now
            team_staff_step.update(self.team_submission_uuid, self.REQUIREMENTS)
            self.status = self.STATUS.done
            self.save()

    def _set_team_staff_score(self, score):
        reason = "A staff member has defined the score for this submission"
        sub_team_api.set_score(
            self.team_submission_uuid,
            score["points_earned"],
            score["points_possible"],
            annotation_creator=score["staff_id"],
            annotation_type=self.STAFF_ANNOTATION_TYPE,
            annotation_reason=reason
        )

    @property
    def identifying_uuid(self):
        """
        Returns the primary identifying uuid for this workflow.
        Overwrites AssessmentWorkflow.identifying_uuid to return team_submission_uuid
        """
        return self.team_submission_uuid


class AssessmentWorkflowStep(models.Model):
    """An individual step in the overall workflow process.

    Similar caveats apply to this class as apply to `AssessmentWorkflow`. What
    we're storing in the database is usually but not always current information.
    In particular, if the problem definition has changed the requirements for a
    particular step in the workflow, then what is in the database will be out of
    sync until someone views this problem again (which will trigger a workflow
    update to occur).

    """
    workflow = models.ForeignKey(AssessmentWorkflow, related_name="steps", on_delete=models.CASCADE)
    name = models.CharField(max_length=20)
    submitter_completed_at = models.DateTimeField(default=None, null=True)
    assessment_completed_at = models.DateTimeField(default=None, null=True)
    order_num = models.PositiveIntegerField()
    skipped = models.BooleanField(default=False, null=True)

    staff_step_types = [AssessmentWorkflow.STAFF_STEP_NAME, TeamAssessmentWorkflow.TEAM_STAFF_STEP_NAME]

    class Meta:
        ordering = ["workflow", "order_num"]
        app_label = "workflow"

    def is_submitter_complete(self):
        """
        Used to determine whether the submitter of the response has completed
        their required actions.
        """
        return self.submitter_completed_at is not None

    def is_assessment_complete(self):
        """
        Used to determine whether the response has been assessed at this step.
        """
        return self.assessment_completed_at is not None

    def is_staff_step(self):
        return self.name in self.staff_step_types

    def can_skip(self, submission_uuid, assessment_requirements):
        if assessment_requirements is None:
            step_reqs = None
        else:
            step_reqs = assessment_requirements.get(self.name)

        can_be_skipped = getattr(self.api(), 'can_be_skipped', lambda sid, reqs: False)
        return can_be_skipped(submission_uuid, step_reqs)

    def skip(self):
        if not self.skipped:
            self.skipped = True
            self.save()

    def start(self, submission_uuid):
        on_start_func = getattr(self.api(), 'on_start', None)
        if on_start_func is not None:
            on_start_func(submission_uuid)

    def unskip(self):
        if self.skipped:
            self.skipped = False
            self.save()

    def api(self):
        """
        Returns an API associated with this workflow step. If no API is
        associated with this workflow step, None is returned.

        This relies on Django settings to map step names to
        the assessment API implementation.
        """
        # We retrieve the settings in-line here (rather than using the
        # top-level constant), so that @override_settings will work
        # in the test suite.
        api_path = getattr(
            settings, 'ORA2_ASSESSMENTS', DEFAULT_ASSESSMENT_API_DICT
        ).get(self.name)
        # Staff APIs should always be available
        if self.is_staff_step() and not api_path:
            if self.name == AssessmentWorkflow.STAFF_STEP_NAME:
                api_path = 'openassessment.assessment.api.staff'
            elif self.name == TeamAssessmentWorkflow.TEAM_STAFF_STEP_NAME:
                api_path = 'openassessment.assessment.api.teams'
            else:
                raise AssessmentWorkflowInternalError(f'Staff step type {self.name} has no associated api')
        if api_path is not None:
            try:
                return importlib.import_module(api_path)
            except (ImportError, ValueError) as ex:
                raise AssessmentApiLoadError(self.name, api_path) from ex
        else:
            # It's possible for the database to contain steps for APIs
            # that are not configured -- for example, if a new assessment
            # type is added, then the code is rolled back.
            msg = (
                "No assessment configured for '{name}'.  "
                "Check the ORA2_ASSESSMENTS Django setting."
            ).format(name=self.name)
            logger.warning(msg)
            return None

    def update(self, submission_uuid, assessment_requirements):
        """
        Updates the AssessmentWorkflowStep models with the requirements
        specified from the Workflow API.

        Intended for internal use by update_from_assessments(). See
        update_from_assessments() documentation for more details.
        """
        # Once a step is completed, it will not be revisited based on updated requirements.
        step_changed = False
        if assessment_requirements is None:
            step_reqs = None
        else:
            step_reqs = assessment_requirements.get(self.name, {})

        def default_finished(*args):
            return True

        submitter_finished = getattr(self.api(), 'submitter_is_finished', default_finished)
        assessment_finished = getattr(self.api(), 'assessment_is_finished', default_finished)

        # Has the user completed their obligations for this step?
        if not self.is_submitter_complete() and submitter_finished(submission_uuid, step_reqs):
            self.submitter_completed_at = now()
            step_changed = True

        # Has the step received a score?
        if not self.is_assessment_complete() and assessment_finished(submission_uuid, step_reqs):
            self.assessment_completed_at = now()
            step_changed = True

        if step_changed:
            self.save()


@receiver(assessment_complete_signal)
def update_workflow_async(sender, **kwargs):  # pylint: disable=unused-argument
    """
    Register a receiver for the update workflow signal
    This allows asynchronous processes to update the workflow

    Args:
        sender (object): Not used

    Keyword Arguments:
        submission_uuid (str): The UUID of the submission associated
            with the workflow being updated.

    Returns:
        None

    """
    submission_uuid = kwargs.get('submission_uuid')
    if submission_uuid is None:
        logger.error("Update workflow signal called without a submission UUID")
        return

    try:
        workflow = AssessmentWorkflow.objects.get(submission_uuid=submission_uuid)
        workflow.update_from_assessments(None)
    except AssessmentWorkflow.DoesNotExist:
        msg = f"Could not retrieve workflow for submission with UUID {submission_uuid}"
        logger.exception(msg)
    except DatabaseError:
        msg = (
            "Database error occurred while updating "
            "the workflow for submission UUID {}"
        ).format(submission_uuid)
        logger.exception(msg)
    except Exception:  # pylint: disable=broad-except
        msg = (
            "Unexpected error occurred while updating the workflow "
            "for submission UUID {}"
        ).format(submission_uuid)
        logger.exception(msg)


class AssessmentWorkflowCancellation(models.Model):
    """Model for tracking cancellations of assessment workflow.

    It is created when a staff member requests removal of a submission
    from the peer grading pool.
    """
    workflow = models.ForeignKey(AssessmentWorkflow, related_name='cancellations', on_delete=models.CASCADE)
    comments = models.TextField(max_length=10000)
    cancelled_by_id = models.CharField(max_length=40, db_index=True)

    created_at = models.DateTimeField(default=now, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]
        app_label = "workflow"

    def __repr__(self):
        return (
            "AssessmentWorkflowCancellation(workflow={0.workflow}, "
            "comments={0.comments}, cancelled_by_id={0.cancelled_by_id}, "
            "created_at={0.created_at})"
        ).format(self)

    def __str__(self):
        return repr(self)

    @classmethod
    def create(cls, workflow, comments, cancelled_by_id):
        """
        Create a new AssessmentWorkflowCancellation object.

        Args:
            workflow (AssessmentWorkflow): The cancelled workflow.
            comments (unicode): The reason for cancellation.
            cancelled_by_id (unicode): The ID of the user who cancelled the workflow.

        Returns:
            AssessmentWorkflowCancellation

        """
        cancellation_params = {
            'workflow': workflow,
            'comments': comments,
            'cancelled_by_id': cancelled_by_id,
        }
        return cls.objects.create(**cancellation_params)

    @classmethod
    def get_latest_workflow_cancellation(cls, submission_uuid):
        """
        Get the latest AssessmentWorkflowCancellation for a submission's workflow.

        Args:
            submission_uuid (str): The UUID of the workflow's submission.

        Returns:
            AssessmentWorkflowCancellation or None
        """
        workflow_cancellations = cls.objects.filter(workflow__submission_uuid=submission_uuid).order_by("-created_at")
        return workflow_cancellations[0] if workflow_cancellations.exists() else None
