"""
Models for managing staff assessments.
"""
from datetime import timedelta

from django.db import models, DatabaseError
from django.utils.timezone import now

from openassessment.assessment.models.base import Assessment
from openassessment.assessment.errors import StaffAssessmentInternalError


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
    course_id = models.CharField(max_length=40, db_index=True)
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

    @property
    def is_cancelled(self):
        """
        Check if the workflow is cancelled.

        Returns:
            True/False
        """
        return bool(self.cancelled_at)

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
            submission_uuid (str): The submission UUID from the student
                requesting a submission for assessment. This is used to explicitly
                avoid giving the student their own submission, and determines the
                associated Peer Workflow.
            item_id (str): The student_item that we would like to retrieve submissions for.
            scorer_id (str): The user id of the staff member scoring this submission

        Returns:
            submission_uuid (str): The submission_uuid for the submission to review.

        Raises:
            StaffAssessmentInternalError: Raised when there is an error retrieving
                the workflows for this request.

        """
        timeout = (now() - cls.TIME_LIMIT).strftime("%Y-%m-%d %H:%M:%S")
        try:
            # Search for existing submissions that the scorer has worked on.
            staff_workflows = StaffWorkflow.objects.filter(
                course_id=course_id,
                item_id=item_id,
                scorer_id=scorer_id,
                grading_completed_at=None,
                cancelled_at=None,
            )
            # If no existing submissions exist, then get any other
            # available workflows.
            if not staff_workflows:
                staff_workflows = StaffWorkflow.objects.filter(
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
            return workflow.submission_uuid
        except DatabaseError:
            error_message = (
                u"An internal error occurred while retrieving a submission for staff grading"
            )
            logger.exception(error_message)
            raise StaffAssessmentInternalError(error_message)

    def close_active_assessment(self, assessment, scorer_id):
        """
        Assign assessment to workflow, and mark the grading as complete.
        """
        self.assessment = assessment.id
        self.scorer_id = scorer_id
        self.grading_completed_at = now()
        self.save()
