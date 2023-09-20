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
def update_workflows_for_course(course_id, workflow_update_data=None):
    """
    Updates ORA workflows created for the given course

    Args:
        course_id (str): Course identifier
        workflow_update_data (dict): optional dictionary containing data required to
        update ORA workflow for submission. If not passed, data will be retrieved from DB

        Sample structure (assessment_requirements and course_settings content omitted):
       ```
        {
          "course_id": "value",
          "course_settings": {},
          "assessments": [
            {
              "item_id": "value",
              "assessment_requirements": {},
              "submissions": [
                {
                  "submission_uuid": "value"
                }
              ]
            }
          ]
        }

    ```
    Raises:
        UpdateWorkflowsForCourseException: If batch process fails and cannot continue.
    """
    try:
        if workflow_update_data is None:
            peer_workflows = get_blocked_peer_workflows(course_id=course_id)
            workflow_update_data = _get_workflow_update_data_for_course(peer_workflows, course_id=course_id)

        if workflow_update_data is not None and workflow_update_data.get("assessments") is not None:
            for item in workflow_update_data["assessments"]:
                # execute asynchronously (submit Celery task)
                ora_data = _get_ora_data(course_object=workflow_update_data, item_id=item["item_id"])
                tasks.update_workflows_for_ora_block_task.apply_async([item["item_id"], ora_data])

            return WorkflowUpdateResult(message="Batch workflow tasks submitted successfully for "
                                                "each ORA item_id within course. ",
                                        course_id=course_id,
                                        task_count=len(workflow_update_data["assessments"]))
        else:
            return WorkflowUpdateResult(message="No blocked ORA submissions found for the course."
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
def update_workflows_for_ora_block(item_id, workflow_update_data=None):
    """
    Updates ORA workflows created for the given ORA Block

    Args:
    item_id (str): Identifier for the ORA Block
        e.g. 'block-v1:edX+DemoX+Demo_Course+type@openassessment+block@1676f4b05f0642249ff724e7c07d869e'

    workflow_update_data (dict): optional dictionary containing data required to
        update ORA workflow for submission. If not passed, data will be retrieved from DB

        Sample structure (assessment_requirements and course_settings content omitted):
        ```
            {
              "course_id" = "value",
              "course_settings" = {}
              "item_id": "value",
              "assessment_requirements": {},
              "submissions": [
                {"submission_uuid": "value"}
              ]
            }
    ```

    Raises:
        OraWorkflowBatchUpdateException: If batch process fails and cannot continue, e.g. number of errors
                                        threshold was exceeded, etc.
    """
    try:
        if workflow_update_data is None:
            peer_workflows = get_blocked_peer_workflows(item_id=item_id)
            workflow_update_data = _get_workflow_update_data_for_ora(peer_workflows, item_id)

        if workflow_update_data is not None and workflow_update_data.get('assessment_requirements') is not None:
            assessment_requirements = workflow_update_data['assessment_requirements']
            course_settings = workflow_update_data['course_settings']

            for item in workflow_update_data["submissions"]:
                # execute asynchronously (submit Celery task)
                tasks.update_workflow_for_submission_task.apply_async(
                    [item["submission_uuid"], assessment_requirements, course_settings])

            return WorkflowUpdateResult(message="Batch workflow update for blocked ORA "
                                                "submissions completed successfully. ",
                                        item_id=item_id,
                                        assessment_requirements=assessment_requirements,
                                        course_settings=course_settings,
                                        task_count=len(workflow_update_data["submissions"]))
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
                workflow_update_data = get_workflow_update_data(peer_workflows)
                submission_data = _get_submission_data(workflow_update_data, submission_uuid=submission_uuid)

                # only one course with one ORA item expected for a given submission
                course_settings = submission_data["course_settings"]
                assessment_requirements = submission_data["assessment_requirements"]

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


def is_flexible_peer_grading_on(ora_block, course_block):
    """
    Verify on ORA and Course level if flexible peer grading is "ON"

    Args:
        ora_block (OpenAssessmentBlock): ORA block
        course_block (CourseBlock): Course block

    Returns:
        bool: True if given ORA is configured with flexible peer grading set "ON"
    """
    if ora_block is not None:
        workflow_requirements = ora_block.workflow_requirements()
        if workflow_requirements.get('peer') and workflow_requirements['peer'].get('enable_flexible_grading'):
            return True
    if course_block is not None:
        return course_block.force_on_flexible_peer_openassessments

    return False


def get_blocked_peer_workflows(course_id=None, item_id=None, submission_uuid=None):
    """
    Retrieve ORA peer workflows not completed for >7 days

    Returns:
        list (PeerWorkflow): list of workfows not completed for > 7 days
    """

    filters = {
        'created_at__lte': timezone.now() - datetime.timedelta(days=7),
        'completed_at__isnull': True,
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
          "course_id": "value",
          "course_settings": {},
          "assessments": [
            {
              "item_id": "value",
              "assessment_requirements": {},
              "submissions": [
                {
                  "submission_uuid": "value"
                }
              ]
            }
          ]
        }
      ]
    }
    ```
    """
    workflow_update_data = {}
    store = modulestore()
    cache = set([])
    for peer_workflow in peer_workflows:
        try:
            if peer_workflow.course_id not in cache:
                # retrieve course block
                course_block_key = UsageKey.from_string(peer_workflow.course_id)
                course_block = store.get_item(course_block_key)

                # retrieve openassessment block
                ora_block_key = UsageKey.from_string(peer_workflow.item_id)
                ora_block = store.get_item(ora_block_key)

                if is_flexible_peer_grading_on(ora_block, course_block):
                    # we are interested only in submissions for ORA with flexible peer grading configured
                    course_settings = {
                        'force_on_flexible_peer_openassessments': course_block.force_on_flexible_peer_openassessments}

                    workflow_update_data = _add_course_data(
                        workflow_update_data=workflow_update_data,
                        course_id=peer_workflow.course_id,
                        item_id=peer_workflow.item_id,
                        submission_uuid=peer_workflow.submission_uuid,
                        assessment_requirements=ora_block.workflow_requirements(),
                        course_settings=course_settings)

                cache.add(peer_workflow.course_id)
                cache.add(peer_workflow.item_id)

            elif peer_workflow.item_id not in cache:
                # retrieve openassessment block
                ora_block_key = UsageKey.from_string(peer_workflow.item_id)
                ora_block = store.get_item(ora_block_key)

                workflow_update_data = _add_ora_data(workflow_update_data=workflow_update_data,
                                                     course_id=peer_workflow.course_id,
                                                     item_id=peer_workflow.item_id,
                                                     submission_uuid=peer_workflow.submission_uuid,
                                                     assessment_requirements=ora_block.workflow_requirements())
            else:
                workflow_update_data = _add_submission_data(workflow_update_data,
                                                            course_id=peer_workflow.course_id,
                                                            item_id=peer_workflow.item_id,
                                                            submission_uuid=peer_workflow.submission_uuid)

        except Exception as e:  # pylint: disable=broad-except
            logger.warning(
                "Error occurred while constructing workflow update data"
                "for open assessment: %s  Error:%s",
                peer_workflow.item_id, str(e))

    return workflow_update_data


def _get_workflow_update_data_for_course(peer_workflows, course_id):
    data = get_workflow_update_data(peer_workflows)
    return _get_course_data(data, course_id)


def _get_workflow_update_data_for_ora(peer_workflows, item_id):
    data = get_workflow_update_data(peer_workflows)
    return _get_ora_data(data, item_id)


def _add_course_data(workflow_update_data, course_id, item_id, submission_uuid, course_settings,
                     assessment_requirements):
    """
    Adds course data structure to the provided data cache dictionary
    """
    if workflow_update_data is None or workflow_update_data.get("courses") is None:
        workflow_update_data = {"courses": []}
    workflow_update_data["courses"].append({"course_id": course_id, "course_settings": course_settings, "assessments": [
        {"item_id": item_id, "assessment_requirements": assessment_requirements,
         "submissions": [{"submission_uuid": submission_uuid}]}]})
    return workflow_update_data


def _add_ora_data(workflow_update_data, course_id, item_id, submission_uuid, assessment_requirements):
    """
    Adds ORA data structure to the provided data cache dictionary
    """
    _get_course_data(workflow_update_data, course_id).get("assessments").append(
        {"item_id": item_id, "assessment_requirements": assessment_requirements,
         "submissions": [{"submission_uuid": submission_uuid}]})
    return workflow_update_data


def _add_submission_data(workflow_update_data, course_id, item_id, submission_uuid):
    """
    Adds ORA data structure to the provided data cache dictionary
    """
    course_data = _get_course_data(workflow_update_data, course_id)
    ora_data = _get_ora_data(course_data, item_id)
    ora_data["submissions"].append({"submission_uuid": submission_uuid})
    return workflow_update_data


def _get_course_data(workflow_update_data, course_id):
    """
    Helper function to return `update_workflow_data` dict object structure
    representing specified course.
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
              "submissions": [
                {"submission_uuid": "submission_uuid_1"}
              ]
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
          "submissions": [
            {"submission_uuid": "submission_uuid_1"}
          ]
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


def _get_ora_data(course_object, item_id):
    """
    Helper function to return `update_workflow_data` dict object structure
    representing specified ORA item.
    E.g.  for requested "item_id_1"

        input:

        ```
        {
          "course_id": "course_id_1",
          "course_settings": {},
          "assessments": [
            {
              "item_id": "item_id_1",
              "assessment_requirements": {},
              "submissions": [
                {"submission_uuid": "submission_uuid_1"}
              ]
            }
          ]
        }
        ```

        return value:

        ```
        {
          "item_id": "item_id_1",
          "assessment_requirements": {},
          "submissions": [
            {"submission_uuid": "submission_uuid_1"}
          ]
        }
        ```
    """

    if course_object is not None and course_object.get("assessments"):
        for assessment_object in course_object.get("assessments"):
            if assessment_object["item_id"] == item_id:
                assessment_object["course_id"] = course_object["course_id"]
                assessment_object["course_settings"] = course_object["course_settings"]
                return assessment_object

    return None


def _get_submission_data(workflow_update_data, submission_uuid, course_id=None, item_id=None):
    """
    Helper function to return `update_workflow_data` dict object structure
    representing specified submission.
    To optimize search `course_id` and `item_id` can be provided

    E.g.  for requested "submission_uuid_1"
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
                  "submissions": [
                    {
                    "submission_uuid": "submission_uuid_1"
                    }
                  ]
                }
              ]
            }
          ]
        }
        ```
    return value:
        ```
        {   "course_id": "course_id_1",
            "course_settings": {},
            "item_id": "item_id_1",
            "assessment_requirements": {},
            "submission_uuid": "submission_uuid_1"
        }
        ```
    """

    if workflow_update_data is None or workflow_update_data.get("courses") is None:
        return None

    if item_id is not None and course_id is not None:
        course_object = _get_course_data(workflow_update_data, course_id=course_id)
        ora_object = _get_ora_data(course_object, item_id=item_id)
        for submission_object in ora_object.get("submissions"):
            if submission_object["submission_uuid"] == submission_uuid:
                return {
                    "course_id": course_id,
                    "course_settings": course_object.get("course_settings"),
                    "item_id": item_id,
                    "assessment_requirements": ora_object.get("assessment_requirements"),
                    "submission_uuid": submission_uuid,
                }

    else:
        for course_object in workflow_update_data.get("courses"):
            for ora_object in course_object.get("assessments"):
                for submission_object in ora_object.get("submissions"):
                    if submission_object["submission_uuid"] == submission_uuid:
                        return {
                            "course_id": course_object.get("course_id"),
                            "course_settings": course_object.get("course_settings"),
                            "item_id": ora_object.get("item_id"),
                            "assessment_requirements": ora_object.get("assessment_requirements"),
                            "submission_uuid": submission_uuid,
                        }
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
