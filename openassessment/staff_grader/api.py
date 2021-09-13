"""
API endpoints for enhanced staff grader
"""
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError, JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework import serializers

from openassessment.assessment.errors.staff import StaffAssessmentInternalError
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
    serializer = SubmissionLockSerializer(workflow)
    return JsonResponse(serializer.data)


class SubmissionLockSerializer(serializers.ModelSerializer):
    """
    Create response payload with info about the workflow and operation success/failure
    """
    class Meta:
        model = StaffWorkflow
        fields = [
            'submission_uuid',
            'is_being_graded',
            'grading_started_at',
            'grading_completed_at',
            'scorer_id'
        ]

