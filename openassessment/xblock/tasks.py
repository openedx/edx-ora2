"""
Celery tasks.
"""
import logging

from celery import task
from celery_utils.logged_task import LoggedTask
from submissions.api import _get_submission_model
from opaque_keys.edx.keys import UsageKey  # pylint: disable=import-error
from xmodule.modulestore.django import modulestore  # pylint: disable=import-error

from openassessment.xblock.job_sample_grader.utils import is_design_problem,get_error_response

logger = logging.getLogger(__name__)


@task(base=LoggedTask, name="run_and_save_staff_test_cases")
def run_and_save_staff_test_cases(block_id, sub_uuid, problem_name):
    """
    Celery task for running staff test cases and updating the submission
    against a given uuid.

    If the problem is not a design-based problem
    Get the submission against given UUID
    Run the code
    If staff response present, attempt saving it
    If not saved, add a default error response and log the exception
    """
    if not is_design_problem(problem_name):
        logger.info(
            "Kicking off run_and_save_staff_test_cases task against sub ID {} and problem {}".format(
                sub_uuid, problem_name
            )
        )
        try:
            submission = _get_submission_model(sub_uuid)
        except Exception:
            logger.exception("Error retrieving submission for problem {} and uuid {}".format(
                problem_name, sub_uuid
            ))
            return

        default_staff_run_error_response = get_error_response('staff', 'Missing Staff Submission')
        answer = submission.answer
        code_submission = answer['submission']
        code_language = answer['language']
        grader_data = {
            'submission': code_submission,
            'language': code_language
        }
        try:
            ora_block = modulestore().get_item(UsageKey.from_string(block_id))
        except Exception:
            logger.exception(
                "Error retreiving OpenAssessmentBlock with usage id {} for problem {} and uuid {}."
                .format(
                    block_id,
                    problem_name,
                    sub_uuid
                )
            )
            return

        grade_output = ora_block.grade_response(grader_data, problem_name, add_staff_output=True)

        try:
            staff_run = grade_output[1]
        except IndexError:
            logger.exception(
                "Error retrieving staff submission from UUID {} from grade response for problem {}".format(
                    sub_uuid, problem_name
                )
            )
            staff_run = default_staff_run_error_response

        try:
            submission.answer.update({'staff_run': staff_run})
            submission.save()
        except Exception:
            logger.exception("Error Saving Staff submission in Database, Saving default response")
            submission.answer.update({'staff_run': default_staff_run_error_response})
            submission.save()
