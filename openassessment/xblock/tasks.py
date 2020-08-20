"""
Celery tasks.
"""
import logging

from celery import task
from celery_utils.logged_task import LoggedTask
from submissions.api import _get_submission_model

from openassessment.xblock.utils import grade_response
from openassessment.xblock.job_sample_grader.job_sample_test_grader import TestGrader

logger = logging.getLogger(__name__)


@task(base=LoggedTask, name="run_and_save_staff_test_cases")
def run_and_save_staff_test_cases(sub_uuid, problem_name):
    """
    Celery task for running staff test cases and updating the submission
    against a given uuid.

    Get the submission against given UUID
    Run the code
    If staff response present, attempt saving it
    If not saved, add a default error response and log the exception
    """
    logger.info("Kicking off run_and_save_staff_test_cases task")
    try:
        submission = _get_submission_model(sub_uuid)
    except Exception:
        logger.exception("Error retrieving submission for problem {} and uuid {}".format(
            problem_name, sub_uuid
        ))
        return

    default_staff_run_error_response = TestGrader.get_error_response('staff', 'Missing Staff Submission')
    answer = submission.answer
    code_submission = answer['submission']
    code_language = answer['language']
    grader_data = {
        'submission': code_submission,
        'language': code_language
    }
    grade_output = grade_response(grader_data, problem_name, add_staff_output=True)

    try:
        staff_run = grade_output[1]
    except KeyError:
        logger.exception("Error retrieving staff submission from grade response")
        staff_run = default_staff_run_error_response

    try:
        submission.answer.update({'staff_run': staff_run})
        submission.save()
    except Exception:
        logger.exception("Error Saving Staff submission in Database, Saving default response")
        submission.answer.update({'staff_run': default_staff_run_error_response})
        submission.save()
