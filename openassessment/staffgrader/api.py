"""
API endpoints for enhanced staff grader
"""
from openassessment.staffgrader.serializers.submission_lock import SubmissionLockSerializer, TeamSubmissionLockSerializer
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError, JsonResponse
from django.views.decorators.http import require_http_methods

from openassessment.assessment.errors.staff import StaffAssessmentInternalError
from openassessment.assessment.models.staff import StaffWorkflow, TeamStaffWorkflow
from openassessment.staff_grader.utils import has_access, get_anonymous_id


@login_required()
@require_http_methods(["GET", "POST", "DELETE"])
def locks_view(request):
    """
    Actions to interact with submission locks, blocking other staff from grading assignments while
    grading is in progress.
    """
    # Unpack / validate request
    submission_uuid = request.GET.get('submissionid')
    team_submission_uuid = request.GET.get('teamsubmissionid')

    if not (submission_uuid or team_submission_uuid):
        return HttpResponseBadRequest("Request must contain either a submissionid or teamsubmissionid query param")
    elif submission_uuid and team_submission_uuid:
        return HttpResponseBadRequest("Request cannot contain both a submissionid and teamsubmissionid query param")

    # Get the workflow for this submission
    if team_submission_uuid:
        workflow = TeamStaffWorkflow.get_workflow(team_submission_uuid)
    else:
        workflow = StaffWorkflow.get_workflow(submission_uuid)

    if not workflow:
        return HttpResponseNotFound()

    course_id = workflow.course_id

    # Requires staff permission for the course
    if not has_access(request.user, course_id):
        return HttpResponseForbidden()

    anonymous_id = get_anonymous_id(request.user.id, course_id)
    if not anonymous_id:
        return HttpResponseForbidden()

    try:
        # GET - get lock info, already done implicitly
        if request.method == "GET":
            pass

        # POST - attempt to claim a lock
        elif request.method == "POST":
            got_lock = workflow.claim_for_grading(anonymous_id)
            if not got_lock:
                return HttpResponseForbidden("Failed to claim lock")

        # DELETE - clear a lock
        elif request.method == "DELETE":
            cleared_lock = workflow.clear_claim_for_grading(anonymous_id)
            if not cleared_lock:
                return HttpResponseForbidden("Failed to clear lock")

    except StaffAssessmentInternalError as ex:
        return HttpResponseServerError(ex)

    # We return workflow info on success
    if team_submission_uuid:
        serializer = TeamSubmissionLockSerializer(workflow)
    else:
        serializer = SubmissionLockSerializer(workflow)

    return JsonResponse(serializer.data)
