"""
Functions that largely mirror the workflow functions specified
in `workflow.api`, but specifically for handling team submissions.
"""

def create_workflow(team_submission_uuid):
    """
    A team submission should only be assessible by staff.  Therefore, unlike
    the analogous `create_workflow()` method for individual submissions,
    we don't accept `steps` or `on_init_params` as parameters to this function,
    since those are only used to indicate which assessment steps (e.g. "peer", "self")
    are to be included in the workflow.
    """
    # TODO: try to invoke `TeamAssessmentWorkflow.start_workflow(team_submission_uuid)`
    # and catch any errors that might occur.
    raise NotImplementedError


def get_workflow_for_submission(team_submission_uuid):
    """
    Like `api.get_workflow_for_submission`, but for teams.  We don't need
    an analogous `assessment_requirements` parameter, because team submissions
    are only assessible by staff (where requirements like "must_grade" and
    "must_be_graded_by" are not supported).
    """
    # TODO: call `update_from_assessments(team_submission_uuid)`
    # Also, decide if you really need both `get_workflow_for_submission()`
    # and `update_from_assessments()`, when the former only calls/returns
    # the result of the latter.
    raise NotImplementedError


def update_from_assessments(team_submission_uuid):
    """
    Should update the workflow status based on the status of the underlying
    assessments.
    """
    # TODO: get the `TeamAssessmentWorkflow` model for the given
    # `team_submission_uuid` and invoke it's `update_from_assessments()` method.
    # Return a serialized version of its results (see `_serialized_with_details()`)
    raise NotImplementedError


def _get_workflow_model(team_submission_uuid):
    """
    Returns the `TeamAssessmentWorkflow` model associated with the
    given `team_submission_uuid`.
    """
    raise NotImplementedError


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
            {"status": "done", "count": 12},
        ]
    """
    # TODO: return the results of a query against `TeamAssessmentWorkflow`,
    # filtered by (course_id, item_id) and grouped by `status`.
    raise NotImplementedError


def cancel_workflow(team_submission_uuid, comments, cancelled_by_id):
    """
    Add an entry in AssessmentWorkflowCancellation table for a AssessmentWorkflow.

    An AssessmentWorkflow which has been cancelled is no longer included in the
    staff grading pool.
    """
    # TODO: Call `TeamAssessmentWorkflow.cancel_workflow(team_submission_uuid, comments, cancelled_by_id)`
    raise NotImplementedError


def get_assessment_workflow_cancellation(team_submission_uuid):
    """
    Get cancellation information for a team assessment workflow.
    """
    # TODO: Return the serialized results of
    # `AssessmentWorkflowCancellation.get_latest_workflow_cancellation(submission_uuid)`.
    raise NotImplementedError


def is_workflow_cancelled(team_submission_uuid):
    """
    """
    raise NotImplementedError
