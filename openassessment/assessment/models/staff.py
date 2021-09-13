"""
Models for managing staff assessments.
"""


from datetime import timedelta
import logging

from django.db import DatabaseError, models
from django.utils.timezone import now

from openassessment.assessment.errors import StaffAssessmentInternalError

logger = logging.getLogger("openassessment.assessment.models")  # pylint: disable=invalid-name


class StaffWorkflow(models.Model):
    """
    Internal Model for tracking Staff Assessment Workflow

    This model can be used to determine the following information required
    throughout the Staff Assessment Workflow:

    1) Get next submission that requires assessment.
    2) Does a submission have a staff assessment?
    3) Does this staff member already have a submission open for assessment?
    4) Close open assessments when completed.

    """
    # Amount of time before a lease on a submission expires
    TIME_LIMIT = timedelta(hours=8)

    scorer_id = models.CharField(max_length=40, db_index=True)
    course_id = models.CharField(max_length=255, db_index=True)
    item_id = models.CharField(max_length=128, db_index=True)
    submission_uuid = models.CharField(max_length=128, db_index=True, unique=True)
    created_at = models.DateTimeField(default=now, db_index=True)
    grading_completed_at = models.DateTimeField(null=True, db_index=True)
    grading_started_at = models.DateTimeField(null=True, db_index=True)
    cancelled_at = models.DateTimeField(null=True, db_index=True)
    assessment = models.CharField(max_length=128, db_index=True, null=True)

    class Meta:
        ordering = ["created_at", "id"]
        app_label = "assessment"

    @classmethod
    def get_workflow(cls, submission_uuid, course_id):
        """
        Get the StaffWorkflow for a submission_uuid/course.
        Adding course to the query keeps us from leaking submissions across courses.

        Returns: StaffWorkflow or None if no workflow is found.
        """
        try:
            return cls.objects.get(
                submission_uuid=submission_uuid,
                course_id=course_id
            )
        except cls.DoesNotExist:
            return None

    @property
    def is_cancelled(self):
        """
        Check if the workflow is cancelled.

        Returns:
            True/False
        """
        return bool(self.cancelled_at)

    @property
    def is_being_graded(self):
        """
        Check if the submission for this workflow is actively being graded.
        i.e. someone started grading it recently (within the configured TIME_LIMIT
        in the past).

        Returns:
            True/False
        """
        # If nobody has started grading this submission, it is not locked
        if not self.grading_started_at:
            return False

        # If somebody started grading this but the lock time has passed, it is not locked
        elif now() > self.grading_started_at + self.TIME_LIMIT:
            return False

        else:
            return True

    def claim_for_grading(self, scorer_id):
        """
        Claim a submission to begin grading.

        Returns:
            True/False whether it was successful in claiming or not
        """
        if self.is_being_graded and self.scorer_id != scorer_id:
            return False
        try:
            self.scorer_id = scorer_id
            self.grading_started_at = now()
            self.save()
        except DatabaseError as ex:
            error_message = (
                f'An internal error occurred trying to claim submission for grading: {self.submission_uuid}'
            )
            logger.exception(error_message)
            raise StaffAssessmentInternalError(error_message) from ex
        return True

    def clear_claim_for_grading(self, scorer_id):
        """
        Clear a claim for grading a submission.
        Only the current grader can clear a claim while it is active.

        Returns: True/False whether it was successful in clearing or not
        """
        if self.is_being_graded and self.scorer_id != scorer_id:
            return False
        try:
            self.scorer_id = ""
            self.grading_started_at = None
            self.save()
        except DatabaseError as ex:
            error_message = (f'An internal error occurred trying to clear claim on submission: {self.submission_uuid}')
            logger.exception(error_message)
            raise StaffAssessmentInternalError(error_message) from ex
        return True

    @property
    def identifying_uuid(self):
        """
        Return the 'primary' identifying UUID for the staff workflow.
        (submission_uuid for StaffWorkflow, team_submission_uuid for TeamStaffWorkflow)
        """
        return self.submission_uuid

    @classmethod
    def get_workflow_statistics(cls, course_id, item_id):
        """
        Returns the number of graded, ungraded, and in-progress submissions for staff grading.

        Args:
            course_id (str): The course that this problem belongs to
            item_id (str): The student_item (problem) that we want to know statistics about.

        Returns:
            dict: a dictionary that contains the following keys: 'graded', 'ungraded', and 'in-progress'
        """
        # pylint: disable=unicode-format-string
        timeout = (now() - cls.TIME_LIMIT).strftime("%Y-%m-%d %H:%M:%S")
        ungraded = cls.objects.filter(
            models.Q(grading_started_at=None) | models.Q(grading_started_at__lte=timeout),
            course_id=course_id, item_id=item_id, grading_completed_at=None, cancelled_at=None
        ).count()

        in_progress = cls.objects.filter(
            course_id=course_id, item_id=item_id, grading_completed_at=None, cancelled_at=None,
            grading_started_at__gt=timeout
        ).count()

        graded = cls.objects.filter(
            course_id=course_id, item_id=item_id, cancelled_at=None
        ).exclude(grading_completed_at=None).count()

        return {'ungraded': ungraded, 'in-progress': in_progress, 'graded': graded}

    @classmethod
    def get_submission_for_review(cls, course_id, item_id, scorer_id):
        """
        Find a submission for staff assessment. This function will find the next
        submission that requires assessment, excluding any submission that has been
        completely graded, or is actively being reviewed by other staff members.

        Args:
            course_id (str): The course that we would like to retrieve submissions for,
            item_id (str): The student_item that we would like to retrieve submissions for.
            scorer_id (str): The user id of the staff member scoring this submission

        Returns:
            identifying_uuid (str): The identifying_uuid for the (team or individual) submission to review.

        Raises:
            StaffAssessmentInternalError: Raised when there is an error retrieving
                the workflows for this request.

        """
        # pylint: disable=unicode-format-string
        timeout = (now() - cls.TIME_LIMIT).strftime("%Y-%m-%d %H:%M:%S")
        try:
            # Search for existing submissions that the scorer has worked on.
            staff_workflows = cls.objects.filter(
                course_id=course_id,
                item_id=item_id,
                scorer_id=scorer_id,
                grading_completed_at=None,
                cancelled_at=None,
            )
            # If no existing submissions exist, then get any other
            # available workflows.
            if not staff_workflows:
                staff_workflows = cls.objects.filter(
                    models.Q(scorer_id='') | models.Q(grading_started_at__lte=timeout),
                    course_id=course_id,
                    item_id=item_id,
                    grading_completed_at=None,
                    cancelled_at=None,
                )
            if not staff_workflows:
                return None

            workflow = staff_workflows[0]
            workflow.scorer_id = scorer_id
            workflow.grading_started_at = now()
            workflow.save()
            return workflow.identifying_uuid
        except DatabaseError as ex:
            error_message = (
                "An internal error occurred while retrieving a submission for staff grading"
            )
            logger.exception(error_message)
            raise StaffAssessmentInternalError(error_message) from ex

    @classmethod
    def bulk_retrieve_workflow_status(cls, course_id, item_id, submission_uuids):
        """
        Retrieves a dictionary with the requested submission UUIDs statuses.

        Args:
            course_id (str): The course that this problem belongs to
            item_ids (list of strings): The student_item (problem) that we want to know statistics about.

        Returns:
            dict: a dictionary with the submission uuids as keys and their statuses as values.
                  Example:
                  {
                      "uuid_1": "submitted",
                      "uuid_2": "not_submitted
                  }
        """
        # Retrieve queryed submissions
        steps = cls.objects.filter(
            course_id=course_id,
            item_id=item_id,
            submission_uuid__in=submission_uuids,
        )

        # Parse them to a dict readable format
        assessments_list = {}
        for assessment in steps:
            status = None
            if assessment.grading_completed_at:
                status = 'submitted'
            else:
                status = 'not_submitted'

            assessments_list[assessment.submission_uuid] = status

        return assessments_list

    def close_active_assessment(self, assessment, scorer_id):
        """
        Assign assessment to workflow, and mark the grading as complete.
        """
        self.assessment = assessment.id
        self.scorer_id = scorer_id
        self.grading_completed_at = now()
        self.save()


class TeamStaffWorkflow(StaffWorkflow):
    """
    Extends the StafWorkflow to be used for team based assessments.
    """
    team_submission_uuid = models.CharField(max_length=128, unique=True, null=False)

    @property
    def identifying_uuid(self):
        """
        Return the 'primary' identifying UUID for the staff workflow.
        (submission_uuid for StaffWorkflow, team_submission_uuid for TeamStaffWorkflow)
        """
        return self.team_submission_uuid

    @classmethod
    def get_workflow(cls, team_submission_uuid, course_id):  # pylint: disable=arguments-differ
        """
        Get a the TeamStaffWorkflow for a team_submission_uuid/course.
        Adding course to the query keeps us from leaking submissions across courses.

        Returns: TeamStaffWorkflow or None if no workflow is found.
        """
        try:
            return cls.objects.get(
                team_submission_uuid=team_submission_uuid,
                course_id=course_id
            )
        except cls.DoesNotExist:
            return None
