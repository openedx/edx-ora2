"""
RESTful interface for all Peer Grading Workflow. Covers all requests made for Peer Grading.
"""
import logging
import util

log = logging.getLogger(__name__)

_INTERFACE_VERSION = 0


def submit_peer_essay(request):
    """
    The Peer Grading XModule will push submissions to this interface.

    request - dict with keys header and body
    header needs submission_id,submission_key,queue_name
    body needs grader_payload, student_info, student_response, max_score
    grader_payload needs location, course_id,problem_id,grader
    student_info needs anonymous_student_id, submission_time

    Output:
    Returns status code indicating success (0) or failure (1) and message
    """
    if request.method != 'POST':
        return util._error_response("'submit' must use HTTP POST", _INTERFACE_VERSION)

    #Minimal parsing of reply
    reply_is_valid, header, body = _is_valid_reply(request.POST.copy())

    if not reply_is_valid:
        log.error("Invalid xqueue object added: request_ip: {0} request.POST: {1}".format(
            util.get_request_ip(request),
            request.POST,
        ))
        return util._error_response('Incorrect format', _INTERFACE_VERSION)

    #Retrieve individual values from xqueue body and header.
    prompt = util._value_or_default(body['grader_payload']['prompt'], "")
    rubric = util._value_or_default(body['grader_payload']['rubric'], "")
    student_id = util._value_or_default(body['student_info']['anonymous_student_id'])
    location = util._value_or_default(body['grader_payload']['location'])
    course_id = util._value_or_default(body['grader_payload']['course_id'])
    problem_id = util._value_or_default(body['grader_payload']['problem_id'], location)
    grader_settings = util._value_or_default(body['grader_payload']['grader_settings'], "")
    student_response = util._value_or_default(body['student_response'])
    student_response = util.sanitize_html(student_response)
    xqueue_submission_id = util._value_or_default(header['submission_id'])
    xqueue_submission_key = util._value_or_default(header['submission_key'])
    state_code = SubmissionState.waiting_to_be_graded
    xqueue_queue_name = util._value_or_default(header["queue_name"])
    max_score = util._value_or_default(body['max_score'])

    submission_time_string = util._value_or_default(body['student_info']['submission_time'])
    student_submission_time = datetime.strptime(submission_time_string, "%Y%m%d%H%M%S")

    control_fields = json.loads(body['grader_payload'].get('control', {}))


    skip_basic_checks = util._value_or_default(body['grader_payload']['skip_basic_checks'], False)
    if isinstance(skip_basic_checks, basestring):
        skip_basic_checks = (skip_basic_checks.lower() == "true")

    #TODO: find a better way to do this
    #Need to set rubric to whatever the first submission for this location had
    #as its rubric.  If the rubric is changed in the course XML, it will break things.
    try:
        first_sub_for_location = Submission.objects.filter(location=location).order_by('date_created')[0]
        rubric = first_sub_for_location.rubric
    except Exception:
        error_message = "Could not find an existing submission in location.  rubric is original."
        log.info(error_message)

    initial_display = ""
    if 'initial_display' in body['grader_payload'].keys():
        initial_display = util._value_or_default(body['grader_payload']['initial_display'], "")
    answer = ""
    if 'answer' in body['grader_payload'].keys():
        answer = util._value_or_default(body['grader_payload']['answer'], "")

    #Without this, sometimes a race condition creates duplicate submissions
    sub_count = Submission.objects.filter(
        prompt=prompt,
        rubric=rubric,
        student_id=student_id,
        problem_id=problem_id,
        student_submission_time=student_submission_time,
        xqueue_submission_id=xqueue_submission_id,
        xqueue_submission_key=xqueue_submission_key,
        xqueue_queue_name=xqueue_queue_name,
        location=location,
        course_id=course_id,
        grader_settings=grader_settings,
    ).count()

    if sub_count > 0:
        return util._error_response('Submission already exists.', _INTERFACE_VERSION)

    #Create submission object
    sub, created = Submission.objects.get_or_create(
        prompt=prompt,
        rubric=rubric,
        student_id=student_id,
        problem_id=problem_id,
        state=state_code,
        student_response=student_response,
        student_submission_time=student_submission_time,
        xqueue_submission_id=xqueue_submission_id,
        xqueue_submission_key=xqueue_submission_key,
        xqueue_queue_name=xqueue_queue_name,
        location=location,
        course_id=course_id,
        max_score=max_score,
        grader_settings=grader_settings,
        initial_display=initial_display,
        answer=answer,
        skip_basic_checks=skip_basic_checks,
        control_fields=json.dumps(control_fields)
    )

    if not created:
        return util._error_response('Submission already exists.', _INTERFACE_VERSION)

    #Handle submission and write to db
    success = handle_submission(sub)
    if not success:
        return util._error_response("Failed to handle submission.", _INTERFACE_VERSION)

    util.log_connection_data()
    return util._success_response({'message': "Saved successfully."}, _INTERFACE_VERSION)
