"""
Celery tasks.
"""
import logging

from celery import task
from celery_utils.logged_task import LoggedTask
from submissions.api import _get_submission_model
from opaque_keys.edx.keys import UsageKey  # pylint: disable=import-error
from openassessment.xblock.signals import CODING_TEST_CASES_EVALUATED
from xmodule.modulestore.django import modulestore  # pylint: disable=import-error

from openassessment.xblock.job_sample_grader.utils import is_design_problem, get_error_response

from lms.djangoapps.courseware.models import StudentModule

logger = logging.getLogger(__name__)


@task(base=LoggedTask, name="run_and_save_test_cases_output")
def run_and_save_test_cases_output(
    block_id: str,
    user_id: int,
    saved_response: dict,
    add_staff_cases: bool = False,
    **kwargs):
    """
    A task that executes a candidates code response. Results are saved
    in StudentModule state.

    Args:
        block_id (str): ORA block usage id.
        user_id (int): Student user id.
        saved_response (dict): A dict of shape (example): 
            {
                'executor_id': 'server_shell-python:3.5.2',
                'submission': 'print("YES")'
            }
        add_staff_cases (bool, optional): Whether or not to run staff test cases.
            Defaults to False.
    """
    try:
        ora_block = modulestore().get_item(UsageKey.from_string(block_id))
    except Exception:
        logger.exception(
            'Error retreiving OpenAssessmentBlock with usage id {}'.format(block_id)
        )
        return

    try:
        grade_output = ora_block.grade_response(
            saved_response,
            ora_block.display_name,
            add_staff_cases,
        )
    except Exception as ex:
        logger.exception(
            'Could not grade response for user {} and block {}. {}'.format(
                user_id, block_id, str(ex)
            ),
            exc_info=ex
        )
        code_execution_results = {
            'success': False,
            'message': 'Error grading the response.',
            'error': str(ex),
            'output': None,
        }
    else:
        if add_staff_cases:
            sample_output, staff_output = grade_output
        else:
            sample_output, staff_output = grade_output, None

        code_execution_results = {
            'success': True,
            'message': '',
            'output': {
                'sample': sample_output,
                'staff': staff_output,
            }
        }

    ora_block.set_code_execution_results(code_execution_results, user_id)


@task(base=LoggedTask, name="run_and_save_staff_test_cases")
def run_and_save_staff_test_cases(block_id, sub_uuid, problem_name, **kwargs):
    """
    Celery task for running staff test cases and updating the submission
    against a given uuid.

    If the problem is not a design-based problem
    Get the submission against given UUID
    Run the code
    If staff response present, attempt saving it
    If not saved, add a default error response and log the exception
    """
    if is_design_problem(problem_name):
        return

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
    executor_id = answer['executor_id']
    grader_data = {
        'submission': code_submission,
        'executor_id': executor_id
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

    CODING_TEST_CASES_EVALUATED.send(
        sender=None,
        block_id=block_id,
        submission_uuid=sub_uuid,
    )
