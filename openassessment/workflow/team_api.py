"""
Functions that largely mirror the workflow functions specified
in `workflow.api`, but specifically for handling team submissions.
"""
import logging

from django.db import DatabaseError
from django.db.models import Count

from openassessment.workflow.errors import (
    AssessmentWorkflowError,
    AssessmentWorkflowInternalError,
    AssessmentWorkflowRequestError,
    AssessmentWorkflowNotFoundError
)
from openassessment.workflow.models import (
    TeamAssessmentWorkflow,
    AssessmentWorkflowCancellation
)
from openassessment.workflow.serializers import (
    TeamAssessmentWorkflowSerializer,
    AssessmentWorkflowCancellationSerializer
)


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def create_workflow(team_submission_uuid):
    """
    A team submission should only be assessible by staff.  Therefore, unlike
    the analogous `create_workflow()` method for individual submissions,
    we don't accept `steps` or `on_init_params` as parameters to this function,
    since those are only used to indicate which assessment steps (e.g. "peer", "self")
    are to be included in the workflow.

    Raises:
        AssessmentWorkflowInternalError on error
    """
    try:
        team_workflow = TeamAssessmentWorkflow.start_workflow(team_submission_uuid)
        logger.info(
            "Started team assessment workflow for team submission UUID %s",
            team_submission_uuid
        )
        return team_workflow
    except Exception as ex:
        err_msg = (
            "An unexpected error occurred while creating "
            "the workflow for team submission UUID {uuid}"
        ).format(uuid=team_submission_uuid)
        logger.exception(err_msg)
        raise AssessmentWorkflowInternalError(err_msg) from ex


def get_workflow_for_submission(team_submission_uuid):
    """
    Pass through to update_from_assessments. Returns team assessment workflow information
    """
    return update_from_assessments(team_submission_uuid)


def update_from_assessments(team_submission_uuid, override_submitter_requirements=False):
    """
        Like `api.update_from_assessments`, but for teams.  We don't need
        an analogous `assessment_requirements` parameter, because team submissions
        are only assessible by staff (where requirements like "must_grade" and
        "must_be_graded_by" are not supported).

        We also don't need an analogous `course_settings` parameter because there are
        currently no course settings that impact staff grading.

        Raises:
            AssessmentWorkflowInternalError on error
        """
    # Get the wokflow for this submission
    team_workflow = _get_workflow_model(team_submission_uuid)

    # Update the workflow status based on the underlying assessments
    try:
        team_workflow.update_from_assessments(override_submitter_requirements)
        logger.info(
            "Updated workflow for team submission UUID %s",
            team_submission_uuid
        )
    except Exception as exc:
        err_msg = "Could not update team assessment workflow: %s"
        logger.exception(err_msg, exc)
        raise AssessmentWorkflowInternalError(err_msg % exc) from exc

    # Return serialized workflow object
    return _serialized_with_details(team_workflow)


def _serialized_with_details(team_workflow):
    data_dict = TeamAssessmentWorkflowSerializer(team_workflow).data
    data_dict['status_details'] = team_workflow.status_details()
    return data_dict


def _get_workflow_model(team_submission_uuid):
    """
    Returns the `TeamAssessmentWorkflow` model associated with the
    given `team_submission_uuid`.

    Raises:
        AssessmentWorkflowRequestError for incorrect arguments
        AssessmentWorkflowNotFoundError when workflow not found
        AssessmentWorkflowInternalError on error
    """
    if not isinstance(team_submission_uuid, str):
        raise AssessmentWorkflowRequestError("team_submission_uuid must be a string")

    try:
        team_workflow = TeamAssessmentWorkflow.get_by_team_submission_uuid(team_submission_uuid)
    except Exception as exc:
        err_msg = (
            "Could not get team assessment workflow with team_submission_uuid {uuid} due to error: {exc}"
        ).format(uuid=team_submission_uuid, exc=exc)
        logger.exception(err_msg)
        raise AssessmentWorkflowInternalError(err_msg) from exc

    if team_workflow is None:
        err_msg = (
            "No team assessment workflow matching team_submission_uuid {uuid}"
        ).format(uuid=team_submission_uuid)
        raise AssessmentWorkflowNotFoundError(err_msg)

    return team_workflow


def get_status_counts(course_id, item_id):
    """
    Count how many team workflows have each status, for a given item in a course.
    "staff" is the only allowed step for team submissions, so we don't
    need a `steps` parameter here.

    Keyword Arguments:
        course_id (unicode): The ID of the course.
        item_id (unicode): The ID of the item in the course.

    Returns:
        list of dictionaries with keys "status" (str) and "count" (int)

    Example usage:
        >>> get_status_counts("course-v1:edX+DemoX+Demo_Course", "peer-assessment-problem")
        [
            {"status": "staff", "count": 5},
            {"status": "waiting", "count": 43},
            {"status": "done", "count": 0},
        ]
    """
    statuses = TeamAssessmentWorkflow.STEPS + TeamAssessmentWorkflow.STATUSES

    # Remove AI status, valid for workflow logic but not a valid team/student step
    if 'ai' in statuses:
        statuses.remove('ai')

    queryset = TeamAssessmentWorkflow.objects.filter(
        status__in=statuses,
        course_id=course_id,
        item_id=item_id,
    ).values('status').annotate(count=Count('status')).order_by('-created')

    counts_by_status = {status: 0 for status in statuses}

    for row in queryset:
        counts_by_status[row['status']] = row['count']

    return [
        {'status': status, 'count': count}
        for status, count
        in counts_by_status.items()
    ]


def cancel_workflow(team_submission_uuid, comments, cancelled_by_id):
    """
    Add an entry in AssessmentWorkflowCancellation table for a TeamAssessmentWorkflow.

    An TeamAssessmentWorkflow which has been cancelled is no longer included in the
    staff grading pool.

    Team workflows follow the same cancellation workflow,
    but operate on the reference submission.
    """
    try:
        submission_uuid = _get_workflow_model(team_submission_uuid).submission_uuid
        TeamAssessmentWorkflow.cancel_workflow(
            submission_uuid,
            comments,
            cancelled_by_id,
            TeamAssessmentWorkflow.REQUIREMENTS,
            {}
        )
    except Exception as exc:
        err_msg = (
            "Could not cancel team assessment workflow with team_submission_uuid {uuid} due to error: {exc}"
        ).format(uuid=team_submission_uuid, exc=exc)
        logger.exception(err_msg)
        raise AssessmentWorkflowInternalError(err_msg) from exc


def get_assessment_workflow_cancellation(team_submission_uuid):
    """
    Get cancellation information for a team assessment workflow.
    """
    try:
        workflow = _get_workflow_model(team_submission_uuid)
        workflow_cancellation = AssessmentWorkflowCancellation.get_latest_workflow_cancellation(
            workflow.submission_uuid
        )
        return AssessmentWorkflowCancellationSerializer(workflow_cancellation).data if workflow_cancellation else None
    except DatabaseError as ex:
        error_message = (
            "Error finding team assessment workflow cancellation for team submission UUID {uuid}."
        ).format(uuid=team_submission_uuid)
        logger.exception(error_message)
        raise AssessmentWorkflowInternalError(error_message) from ex
    except Exception as exc:
        err_msg = (
            "Could not get workflow cancellation with team_submission_uuid {uuid} due to error: {exc}"
        ).format(uuid=team_submission_uuid, exc=exc)
        logger.exception(err_msg)
        raise AssessmentWorkflowInternalError(err_msg) from exc


def is_workflow_cancelled(team_submission_uuid):
    """
    Check if the team assessment workflow is cancelled
    """
    try:
        workflow = TeamAssessmentWorkflow.get_by_team_submission_uuid(team_submission_uuid)
        return workflow.is_cancelled if workflow else False
    except AssessmentWorkflowError:
        return False
