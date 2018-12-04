"""
Django models specific to ai assessment.

NOTE: We've switched to migrations, so if you make any edits to this file, you
need to then generate a matching migration for it using:

    ./manage.py schemamigration openassessment.assessment --auto

"""
from datetime import timedelta
import logging

from django.db import DatabaseError, models
from django.utils.timezone import now

from openassessment.assessment.errors import AIAssessmentWorkflowError

logger = logging.getLogger("openassessment.assessment.models")


class AIWorkflow(models.Model):
    """Internal Model for tracking AI Assessment Workflow

    This model can be used to determine the following information required
    throughout the AI Assessment Workflow:

    1) Get next submission that requires assessment.
    2) Does a submission have a ai assessment?
    4) Does a student already have a submission open for assessment?
    5) Close open assessments when completed.

    """
    # Amount of time before a lease on a submission expires
    TIME_LIMIT = timedelta(hours=8)

    student_id = models.CharField(max_length=40, db_index=True)
    course_id = models.CharField(max_length=255, db_index=True)
    submission_uuid = models.CharField(max_length=128, db_index=True, unique=True)
    created_at = models.DateTimeField(default=now, db_index=True)
    completed_at = models.DateTimeField(null=True, db_index=True)
    grading_completed_at = models.DateTimeField(null=True, db_index=True)
    cancelled_at = models.DateTimeField(null=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]
        app_label = "assessment"

    @property
    def is_cancelled(self):
        """
        Check if workflow is cancelled.

        Returns:
            True/False
        """
        return bool(self.cancelled_at)

    @classmethod
    def get_by_submission_uuid(cls, submission_uuid):
        """
        Retrieve the AI Workflow associated with the given submission UUID.

        Args:
            submission_uuid (str): The string representation of the UUID belonging
                to the associated Peer Workflow.

        Returns:
            workflow (AIWorkflow): The most recent AI workflow associated with
                this submission UUID.

        Raises:
            AIAssessmentWorkflowError: Thrown when no workflow can be found for
                the associated submission UUID.

        Examples:
            >>> AIWorkflow.get_by_submission_uuid("abc123")
            {
                'course_id': u'course_1',
                'submission_uuid': u'1',
                'created_at': datetime.datetime(2014, 1, 29, 17, 14, 52, 668850, tzinfo=<UTC>)
            }

        """
        try:
            return cls.objects.get(submission_uuid=submission_uuid)
        except cls.DoesNotExist:
            return None
        except DatabaseError:
            error_message = (
                u"Error finding workflow for submission UUID {}. Workflow must be "
                u"created for submission before beginning ai assessment."
            ).format(submission_uuid)
            logger.exception(error_message)
            raise AIAssessmentWorkflowError(error_message)

    def close_active_assessment(self, assessment):
        """
        Assign assessment to workflow, and mark the grading as complete.
        """
        self.assessment = assessment.id
        self.grading_completed_at = now()
        self.save()

    def __repr__(self):
        return (
            "AIWorkflow(student_id={0.student_id}, course_id={0.course_id}, "
            "submission_uuid={0.submission_uuid} created_at={0.created_at}, "
            "completed_at={0.completed_at})"
        ).format(self)

    def __unicode__(self):
        return repr(self)
