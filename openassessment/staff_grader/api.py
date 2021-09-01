"""
API endpoints for enhanced staff grader
"""
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.http.response import HttpResponseForbidden, HttpResponseNotFound, JsonResponse
from django.views.decorators.http import require_http_methods


from opaque_keys.edx.keys import CourseKey
from openassessment.assessment.models.staff import StaffWorkflow
from openassessment.data import _use_read_replica

@login_required()
@require_http_methods(["GET", "POST", "DELETE"])
def locks_view(request, course_id, submission_uuid):
    """
    Actions to interact with submission locks, blocking other staff from grading assignments while
    grading is in progress.
    """

    # TODO - update staff permission check to limit by course
    # course_key = CourseKey.from_string(course_id)
    # request.user.has_perm("instructor.email", course_key)

    # Requires staff permission
    if not request.user.is_staff:
        return HttpResponseForbidden()

    anonymous_id = get_anonymous_id(request.user.id, course_id)
    if not anonymous_id:
        return HttpResponseForbidden()

    # Get the workflow for this submission
    workflow = StaffWorkflow.get_workflow(submission_uuid)
    if not workflow:
        return HttpResponseNotFound()

    data = {}
    status = 200

    # GET - get lock info
    if request.method == "GET":
        data = get_lock_info(workflow)

    # POST - attempt to claim a lock
    elif request.method == "POST":
        got_lock = workflow.claim_lock(anonymous_id)
        data = { "success": got_lock }
        status = 200 if got_lock else 500

    # DELETE - clear a lock
    elif request.method == "DELETE":
        cleared_lock = workflow.clear_lock()
        data = { "success": cleared_lock }
        status = 200 if cleared_lock else 500

    return JsonResponse(data, status=status)


def get_lock_info(workflow):
    """
    Given a workflow, get data about if it's locked

    Returns: Object
    """
    return {
        "submission_uuid": workflow.submission_uuid,
        "locked": workflow.is_locked,
        "owner": workflow.scorer_id,
        "timestamp": workflow.grading_started_at,
    }

def get_anonymous_id(user_id, course_id):
    """
    Get an anonymous user ID for the user/course

    Returns: String or None
    """
    try:
        return _use_read_replica(
            User.objects.filter(
                anonymoususerid__user_id = user_id,
                anonymoususerid__course_id = course_id
            ).values(
                "anonymoususerid__anonymous_user_id"
            ).get()["anonymoususerid__anonymous_user_id"]
        )
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return None
