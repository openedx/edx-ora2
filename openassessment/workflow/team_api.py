"""
Functions that largely mirror the workflow functions specified
in `workflow.api`, but specifically for handling team submissions.
"""
import logging

from django.db.models import Count

from openassessment.workflow.errors import (
    AssessmentWorkflowInternalError,
    AssessmentWorkflowRequestError,
    AssessmentWorkflowNotFoundError
)
from openassessment.workflow.models import TeamAssessmentWorkflow
from openassessment.workflow.serializers import TeamAssessmentWorkflowSerializer


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
        logger.info((
            "Started team assessment workflow for "
            "team submission UUID {uuid}"
        ).format(uuid=team_submission_uuid))
        return team_workflow
    except Exception:
        err_msg = (
            "An unexpected error occurred while creating "
            "the workflow for team submission UUID {uuid}"
        ).format(uuid=team_submission_uuid)
        logger.exception(err_msg)
        raise AssessmentWorkflowInternalError(err_msg)


def get_workflow_for_submission(team_submission_uuid):
    """
    Like `api.get_workflow_for_submission`, but for teams.  We don't need
    an analogous `assessment_requirements` parameter, because team submissions
    are only assessible by staff (where requirements like "must_grade" and
    "must_be_graded_by" are not supported).

    Raises:
        AssessmentWorkflowInternalError on error
    """
    # Get the wokflow for this submission
    team_workflow = _get_workflow_model(team_submission_uuid)

    # Update the workflow status based on the underlying assessments
    try:
        team_workflow.update_from_assessments()
        logger.info((
            "Updated workflow for team submission UUID {uuid} "
        ).format(uuid=team_submission_uuid))
    except Exception as exc:
        err_msg = (
            "Could not update team assessment workflow: {exc}"
        ).format(exc=exc)
        logger.exception(err_msg)
        raise AssessmentWorkflowInternalError(err_msg)

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
        raise AssessmentWorkflowInternalError(err_msg)

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
