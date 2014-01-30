import logging
from django.contrib.auth.decorators import login_required

from django.shortcuts import render_to_response
from submissions.api import SubmissionRequestError, get_submissions

log = logging.getLogger(__name__)


@login_required()
def get_submissions_for_student_item(request, course_id, student_id, item_id):
    """Retrieve all submissions associated with the given student item.

    Developer utility for accessing all the submissions associated with a
    student item. The student item is specified by the unique combination of
    course, student, and item.

    Args:
        request (dict): The request.
        course_id (str): The course id for this student item.
        student_id (str): The student id for this student item.
        item_id (str): The item id for this student item.

    Returns:
        HttpResponse: The response object for this request. Renders a simple
            development page with all the submissions related to the specified
            student item.

    """
    student_item_dict = dict(
        course_id=course_id,
        student_id=student_id,
        item_id=item_id,
    )
    context = dict(**student_item_dict)
    try:
        submissions = get_submissions(student_item_dict)
        context["submissions"] = submissions
    except SubmissionRequestError:
        context["error"] = "The specified student item was not found."

    return render_to_response('submissions.html', context)
