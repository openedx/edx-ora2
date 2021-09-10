"""
API endpoints for enhanced staff grader
"""
from openassessment.assessment.errors.staff import StaffAssessmentInternalError
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError, JsonResponse
from django.views.decorators.http import require_http_methods

from openassessment.assessment.models.staff import StaffWorkflow
from openassessment.staff_grader.utils import has_access, get_anonymous_id


@login_required()
@require_http_methods(["GET", "POST", "DELETE"])
def locks_view(request, course_id, submission_uuid):
    """
    Actions to interact with submission locks, blocking other staff from grading assignments while
    grading is in progress.
    """
    # Requires staff permission for the course
    if not has_access(request.user, course_id):
        return HttpResponseForbidden()

    anonymous_id = get_anonymous_id(request.user.id, course_id)
    if not anonymous_id:
        return HttpResponseForbidden()

    # Get the workflow for this submission
    workflow = StaffWorkflow.get_workflow(submission_uuid, course_id)
    if not workflow:
        return HttpResponseNotFound()

    data = {}

    try:
        # GET - get lock info, already done implicitly
        if request.method == "GET":
            data = response_payload(workflow)

        # POST - attempt to claim a lock
        elif request.method == "POST":
            got_lock = workflow.claim_for_grading(anonymous_id)
            data = response_payload(workflow, success=got_lock)

        # DELETE - clear a lock
        elif request.method == "DELETE":
            cleared_lock = workflow.clear_claim_for_grading(anonymous_id)
            data = response_payload(workflow, success=cleared_lock)

    except StaffAssessmentInternalError as ex:
        return HttpResponseServerError(ex)

    return JsonResponse(data)


def response_payload(workflow, success=True):
    """
    Create response payload with info about the workflow and operation success/failure
    """
    return {
        "submission_uuid": workflow.submission_uuid,
        "is_being_graded": workflow.is_being_graded,
        "owner": workflow.scorer_id,
        "timestamp": workflow.grading_started_at,
        "success": success
    }
