"""
Provides functionality to batch update ORA workflows for different scopes
"""

import logging
import time
import datetime
from django.utils import timezone

from opaque_keys.edx.keys import UsageKey
from openassessment.runtime_imports.functions import modulestore
from openassessment.assessment.models import PeerWorkflow
from openassessment.workflow import api
from openassessment.workflow import tasks

logger = logging.getLogger(__name__)


def log_task_info(func):
    """
    This decorator logs task info. Expects `WorkflowUpdateResult` as a decorated function return value
    """

    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        log_message = f"function_name={func.__name__} "
        if result is not None:
            log_message += " ".join([f"{str(key)}={str(value)}" for key, value in result.__dict__.items()])
        log_message += f" processing_time={(end - start):.5f} "
        logger.info(log_message)
        return result

    return wrapper


@log_task_info
def update_workflows_for_all_blocked_submissions():
    """
    Updates ORA workflows for submissions meeting following filtering criteria:
     - Flexible Peer Grading ON
     - ungraded submissions that are >7 days old

     Raises:
        OraWorkflowBatchUpdateException: If batch process fails and cannot continue, e.g. number of errors
                                        threshold was exceeded, etc.
    """
    try:
        peer_workflows = get_blocked_peer_workflows()
        workflow_update_data = get_workflow_update_data(peer_workflows)
        if workflow_update_data.get("courses") is not None:
            for course_object in workflow_update_data.get("courses"):
                # execute asynchronously (submit Celery task)
                tasks.update_workflows_for_course_task.apply_async([course_object["course_id"], course_object])

            return WorkflowUpdateResult(message="Batch workflow update tasks submitted "
                                                "successfully for each course id. ",
                                        task_count=len(workflow_update_data["courses"]))
        else:
            return WorkflowUpdateResult(message="No blocked ORA submissions found. "
                                                "Batch workflow update completed without submitting any tasks.",
                                        task_count=0)
    except (UpdateWorkflowsForCourseException, Exception) as e:  # pylint: disable=broad-except
        logger.error(
            "Batch workflow update. Error occurred while updating workflows for all blocked submissions.  Error:%s",
            str(e))
        raise UpdateWorkflowsForAllBlockedSubmissionsException(str(e)) from e


@log_task_info
def update_workflows_for_course(course_id, workflow_update_data_for_course=None):
    """
    Updates ORA workflows created for the given course

    Args:
        course_id (str): Course identifier

        workflow_update_data_for_course (dict): optional dictionary containing data required to
        update ORA workflow for submission. If not passed, data will be retrieved from DB

        Sample structure (assessment_requirements and course_settings content omitted):
       ```
        {
          "course_id": str,
          "course_settings": {},
          "assessments": [
            {
              "item_id": str,
              "assessment_requirements": {},
              "submissions": [str]
            }
          ]
        }
    ```
    Raises:
        UpdateWorkflowsForCourseException: If batch process fails and cannot continue.
    """
    try:
        if workflow_update_data_for_course is None:
            peer_workflows = get_blocked_peer_workflows(course_id=course_id)
            data = get_workflow_update_data(peer_workflows)
            workflow_update_data_for_course = _get_course_data(data, course_id)

        if workflow_update_data_for_course is not None and workflow_update_data_for_course.get(
                "assessments") is not None:
            for assessment in workflow_update_data_for_course["assessments"]:
                # execute asynchronously (submit Celery task)

                tasks.update_workflows_for_ora_block_task.apply_async(
                    [assessment["item_id"], assessment,
                     workflow_update_data_for_course["course_settings"]])

            return WorkflowUpdateResult(message="Batch workflow tasks submitted successfully for "
                                                "each ORA item_id within course. ",
                                        course_id=course_id,
                                        task_count=len(workflow_update_data_for_course["assessments"]))
        else:
            return WorkflowUpdateResult(message="No blocked ORA submissions found for the course. "
                                                "Batch workflow update completed without submitting any tasks.",
                                        course_id=course_id,
                                        task_count=0)

    except (UpdateWorkflowsForOraBlockException, Exception) as e:  # pylint: disable=broad-except
        logger.error(
            "Batch workflow update for course blocked submissions failed. "
            "course_id=%s Error:%s",
            course_id,
            str(e))
        raise UpdateWorkflowsForCourseException(str(e)) from e


@log_task_info
def update_workflows_for_ora_block(item_id, workflow_update_data_for_ora=None, course_settings=None):
    """
    Updates ORA workflows created for the given ORA Block

    Args:
    item_id (str): Identifier for the ORA Block
        e.g. 'block-v1:edX+DemoX+Demo_Course+type@openassessment+block@1676f4b05f0642249ff724e7c07d869e'

    workflow_update_data_for_ora (dict): optional dictionary containing data required to
        update ORA workflow for submission. If not passed, data will be retrieved from DB

        Sample structure (assessment_requirements and course_settings content omitted):
        ```
            {
              "item_id": str,
              "assessment_requirements": {},
              "submissions": [str]
            }
        ```
    course_settings (dict) - course block overrides/settings containing flexible peer grading override flag,
        e.g.
        ```
             {
                'force_on_flexible_peer_openassessments': True
             }
        ```

    Raises:
        OraWorkflowBatchUpdateException: If batch process fails and cannot continue, e.g. number of errors
                                        threshold was exceeded, etc.
    """
    try:
        if workflow_update_data_for_ora is None or course_settings is None:
            peer_workflows = get_blocked_peer_workflows(item_id=item_id)
            workflow_update_data_for_ora, course_settings = \
                _get_workflow_update_data_and_course_settings(peer_workflows, item_id)

        if workflow_update_data_for_ora is not None and workflow_update_data_for_ora.get(
                'assessment_requirements') is not None:
            assessment_requirements = workflow_update_data_for_ora['assessment_requirements']

            for submission_uuid in workflow_update_data_for_ora["submissions"]:
                # execute asynchronously (submit Celery task)
                tasks.update_workflow_for_submission_task.apply_async(
                    [submission_uuid, assessment_requirements, course_settings])

            return WorkflowUpdateResult(message="Batch workflow update for blocked ORA "
                                                "submissions completed successfully. ",
                                        item_id=item_id,
                                        assessment_requirements=assessment_requirements,
                                        course_settings=course_settings,
                                        task_count=len(workflow_update_data_for_ora["submissions"]))
        else:
            return WorkflowUpdateResult(message="No blocked ORA submissions found for the ORA item. "
                                                "Batch workflow update completed without submitting any tasks.",
                                        item_id_id=item_id,
                                        task_count=0)

    except (UpdateWorkflowForSubmissionException, Exception) as e:  # pylint: disable=broad-except
        logger.error(
            "Batch workflow update for ORA block failed. "
            "item_id=%s error_message:%s",
            item_id,
            str(e))
        raise UpdateWorkflowsForOraBlockException(str(e)) from e


@log_task_info
def update_workflow_for_submission(submission_uuid, assessment_requirements=None, course_settings=None):
    """
    Updates ORA workflow created for a given submission
    Wrapper for `workflow.api.update_from_assessments(submission_uuid, assessment_requirements, course_override)`
    """
    try:

        if assessment_requirements is None or course_settings is None:
            peer_workflows = get_blocked_peer_workflows(submission_uuid)
            if peer_workflows is not None:
                course_settings, assessment_requirements = \
                    _get_course_settings_and_assessment_requirements(peer_workflows, submission_uuid)

        api.update_from_assessments(submission_uuid, assessment_requirements, course_settings)

        return WorkflowUpdateResult(message="ORA workflow update for a single blocked submission "
                                            "completed successfully. ",
                                    submission_uuid=submission_uuid)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(
            "ORA workflow update for a single submission failed. "
            "submission_uuid=%s assessment_requirements=%s course_settings=%s. error_message=%s",
            submission_uuid,
            assessment_requirements,
            course_settings,
            str(e))
        raise UpdateWorkflowForSubmissionException(str(e)) from e


def is_flexible_peer_grading_on(assessment_requirements, course_settings):
    """
    Verify on ORA and Course level if flexible peer grading is "ON"

    Args:
        assessment_requirements (dict): retrieved from ORA block
        course_settings (dict): Course overrides retrieved from course block. Must contain flexible peer grading
                                override flag, e.g.
                                ```
                                {'force_on_flexible_peer_openassessments': True}
                                ```

    Returns:
        bool: True if given ORA is configured with flexible peer grading set "ON"
    """

    if assessment_requirements.get('peer') and assessment_requirements['peer'].get('enable_flexible_grading') is True:
        return True
    if course_settings is not None:
        return course_settings.get('force_on_flexible_peer_openassessments')

    return False


def get_blocked_peer_workflows(course_id=None, item_id=None, submission_uuid=None):
    """
    Retrieve ORA peer workflows not completed for >7 days

    Returns:
        list (PeerWorkflow): list of workfows not completed for > 7 days
    """

    filters = {
        'created_at__lte': timezone.now() - datetime.timedelta(days=7),
        'grading_completed_at__isnull': True,
        'completed_at__isnull': False
    }
    if course_id is not None:
        filters['course_id'] = course_id
    if item_id is not None:
        filters['item_id'] = item_id
    if submission_uuid is not None:
        filters['submission_uuid'] = item_id

    return PeerWorkflow.objects.filter(**filters)


def get_workflow_update_data(peer_workflows):
    """
    Generates dictionary containing data required to update ORA workflows for all scopes.
    This data structure is used as a local cache to avoid redundant DB queries during
    batch workflow update process

    Structure:
    ```
    {
      "courses": [
        {
          "course_id": str,
          "course_settings": {},
          "assessments": [
            {
              "item_id": str,
              "assessment_requirements": {},
              "submissions": [str]
            }
          ]
        }
      ]
    }
    ```
    """

    workflow_update_data = {}
    store = modulestore()
    # temp cache to optimize number of DB lookups for course blocks
    course_settings_cache = {}
    # temp cache to optimize number of DB lookups for ora blocks
    assessment_requirements_cache = {}

    submissions_cache = set([])

    for peer_workflow in peer_workflows:

        try:
            if peer_workflow.course_id not in course_settings_cache:
                # retrieve course block from DB
                course_block_key = UsageKey.from_string(peer_workflow.course_id)
                course_block = store.get_item(course_block_key)
                # add course settings to temp cache
                course_settings_cache[peer_workflow.course_id] = {
                    'force_on_flexible_peer_openassessments': course_block.force_on_flexible_peer_openassessments}

            if peer_workflow.item_id not in assessment_requirements_cache:
                # retrieve openassessment block from DB
                ora_block_key = UsageKey.from_string(peer_workflow.item_id)
                ora_block = store.get_item(ora_block_key)
                # add assessment requirements to temp cache
                assessment_requirements_cache[peer_workflow.item_id] = ora_block.workflow_requirements()

            if peer_workflow.submission_uuid not in submissions_cache:
                if is_flexible_peer_grading_on(assessment_requirements_cache.get(peer_workflow.item_id),
                                               course_settings_cache.get(peer_workflow.course_id)):
                    workflow_update_data = _add_data(
                        workflow_update_data=workflow_update_data,
                        course_id=peer_workflow.course_id,
                        item_id=peer_workflow.item_id,
                        submission_uuid=peer_workflow.submission_uuid,
                        assessment_requirements=assessment_requirements_cache.get(peer_workflow.item_id),
                        course_settings=course_settings_cache.get(peer_workflow.course_id))

                submissions_cache.add(peer_workflow.submission_uuid)

        except Exception as e:  # pylint: disable=broad-except
            logger.warning(
                "Error occurred while constructing workflow update data "
                "for open assessment: %s  Error:%s",
                peer_workflow.item_id, str(e))

    return workflow_update_data


def _get_workflow_update_data_and_course_settings(peer_workflows, item_id):
    """
    Helper to provide data required for ora scope workflows update

    Returns:
        openassessment scope data (dict)
        course settings (dict)
    """
    data = get_workflow_update_data(peer_workflows)
    if data is not None and data.get("courses") is not None:
        for course in data.get("courses"):
            for ora in course.get("assessments"):
                if ora.get("item_id") == item_id:
                    return ora, course["course_settings"]
    return None


def _get_course_settings_and_assessment_requirements(peer_workflows, submission_uuid):
    """
    Helper providing data required for a workflow update for a single submission
    Returns:
        course_settings (dict)
        assessment_requirements (dict)

    """
    data = get_workflow_update_data(peer_workflows)
    if data is not None and data.get("courses") is not None:
        for course in data.get("courses"):
            for ora in course.get("assessments"):
                if submission_uuid in ora["submissions"]:
                    return course["course_settings"], ora["assessment_requirements"]
    return None


def _add_data(workflow_update_data, course_id, item_id, submission_uuid, course_settings, assessment_requirements):
    """
    Adds provided data to the data cache dictionary.

    `workflow_update_data` structure:
    ```
       {
      "courses": [
        {
          "course_id": str,
          "course_settings": {},
          "assessments": [
            {
              "item_id": str,
              "assessment_requirements": {},
              "submissions": [str]
            }
          ]
        }
      ]
    }
    ```

    """
    if workflow_update_data is None or workflow_update_data.get("courses") is None:
        workflow_update_data = {"courses": []}
    course_data = _get_course_data(workflow_update_data, course_id)

    if course_data is None:
        course_data = {"course_id": course_id, "course_settings": course_settings, "assessments": [
            {"item_id": item_id, "assessment_requirements": assessment_requirements,
             "submissions": [submission_uuid]}]}
        workflow_update_data["courses"].append(course_data)

    ora_data = None
    for ora_object in course_data.get("assessments"):
        if ora_object["item_id"] == item_id:
            ora_data = ora_object

    if ora_data is None:
        ora_data = {"item_id": item_id,
                    "assessment_requirements": assessment_requirements,
                    "submissions": [submission_uuid]}
        course_data.get("assessments").append(ora_data)

    if submission_uuid in ora_data.get("submissions"):
        return workflow_update_data

    ora_data["submissions"].append(submission_uuid)

    return workflow_update_data


def _get_course_data(workflow_update_data, course_id):
    """
    Helper function to extract dict object structure representing specified course
    from the `update_workflow_data` dictionary
    E.g.  for requested "course_id_1"

    input:
    ```
    {
      "courses": [
        {
          "course_id": "course_id_1",
          "course_settings": {},
          "assessments": [
            {
              "item_id": "item_id_1",
              "assessment_requirements": {},
              "submissions": ["submission_uuid_1"]
            }
          ]
        }
      ]
    }
    ```

    return value:
    ```
    {
      "course_id": "course_id_1",
      "course_settings": {},
      "assessments": [
        {
          "item_id": "item_id_1",
          "assessment_requirements": {},
          "submissions": ["submission_uuid_1"]
        }
      ]
    }
    ```

    """
    if workflow_update_data is not None and workflow_update_data.get("courses"):
        for course_object in workflow_update_data.get("courses"):
            if course_object["course_id"] == course_id:
                return course_object
    return None


class OraWorkflowBatchUpdateException(Exception):
    """Raised when batch ORA workflow process failed"""


class UpdateWorkflowForSubmissionException(Exception):
    """Raised when batch ORA workflow update for a single submission failed"""


class UpdateWorkflowsForOraBlockException(Exception):
    """Raised when batch ORA workflow update for an ORA block (open assessment)  failed"""


class UpdateWorkflowsForCourseException(Exception):
    """Raised when batch ORA workflows update for a course failed"""


class UpdateWorkflowsForAllBlockedSubmissionsException(Exception):
    """Raised when batch ORA workflows update for all blocked submissions failed"""


class WorkflowUpdateResult:
    """
    Used mainly for the purpose of returning data needed to log completed execution.
    All args will be concatenated to the log message as key:value pairs
    """

    def __init__(self, message=None, **kwargs):
        self.message = message
        for key, value in kwargs.items():
            setattr(self, key, value)
