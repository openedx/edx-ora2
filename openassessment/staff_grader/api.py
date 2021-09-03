"""
API endpoints for enhanced staff grader
"""
from openassessment.assessment.errors.staff import StaffAssessmentInternalError
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.http.response import HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError, JsonResponse
from django.views.decorators.http import require_http_methods

from openassessment.assessment.models.staff import StaffWorkflow
from openassessment.data import _use_read_replica


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
            got_lock = workflow.claim_lock(anonymous_id)
            data = response_payload(workflow, success=got_lock)

        # DELETE - clear a lock
        elif request.method == "DELETE":
            cleared_lock = workflow.clear_lock(anonymous_id)
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
        "locked": workflow.is_locked,
        "owner": workflow.scorer_id,
        "timestamp": workflow.grading_started_at,
        "success": success
    }

def get_anonymous_id(user_id, course_id):
    """
    Get an anonymous user ID for the user/course

    Returns: String or None
    """
    try:
        user_anon_id = _use_read_replica(
            User.objects.filter(
                anonymoususerid__user_id = user_id,
                anonymoususerid__course_id = course_id
            ).values(
                "anonymoususerid__anonymous_user_id"
            )
        ).get()
        return user_anon_id["anonymoususerid__anonymous_user_id"]
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return None

def has_access(user, course_id, access_level="staff"):
    """
    Determine whether the user has access to the given course.
    i.e. whether they have "staff"-level access
    """
    if user.is_anonymous:
        return False

    access_roles = get_roles(user.id, course_id)

    return access_level in access_roles


def get_roles(user_id, course_id):
    """
    Get access roles for the user in context of the course
    """
    access_roles = _use_read_replica(
        User.objects.filter(
            courseaccessrole__user_id = user_id,
            courseaccessrole__course_id = course_id
        ).values(
            "courseaccessrole__role"
        )
    )

    return [role["courseaccessrole__role"] for role in access_roles]