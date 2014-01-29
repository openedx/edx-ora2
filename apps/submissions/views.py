import logging

from django.shortcuts import render_to_response
from submissions import api

log = logging.getLogger(__name__)


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
        HttpResponse: The response object for this request.

    """
    student_item_dict = dict(
        course_id=course_id,
        student_id=student_id,
        item_id=item_id,
    )
    submissions = api.get_submissions(student_item_dict)

    context = dict(
        submissions=submissions,
        **student_item_dict
    )

    return render_to_response('submissions.html', context)
