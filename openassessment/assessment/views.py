""" Assessment Views. """
from __future__ import absolute_import

import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response

from submissions.api import SubmissionRequestError, get_submissions
from openassessment.assessment.api.peer import get_assessments

log = logging.getLogger(__name__)


@login_required()
def get_evaluations_for_student_item(request, course_id, student_id, item_id):  # pylint: disable=unused-argument
    """Retrieve all evaluations associated with the given student item.

    Developer utility for accessing all the evaluations associated with a
    student item. The student item is specified by the unique combination of
    course, student, and item.

    Args:
        request (dict): The request.
        course_id (str): The course id for this student item.
        student_id (str): The student id for this student item.
        item_id (str): The item id for this student item.

    Returns:
        HttpResponse: The response object for this request. Renders a simple
            development page with all the evaluations related to the specified
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
        evaluations = []
        for submission in submissions:
            submission_evaluations = get_assessments(submission["uuid"])
            for evaluation in submission_evaluations:
                evaluation["submission_uuid"] = submission["uuid"]
                evaluations.append(evaluation)

        context["evaluations"] = evaluations

    except SubmissionRequestError:
        context["error"] = "The specified student item was not found."

    return render_to_response('evaluations.html', context)
