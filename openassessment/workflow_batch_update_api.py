"""
Provides functionality to batch update ORA workflows for different scopes
"""

import logging
import time
import datetime
from django.utils import timezone
from celery import shared_task

from opaque_keys.edx.keys import UsageKey
from openassessment.runtime_imports.functions import modulestore
from openassessment.assessment.models import PeerWorkflow
from openassessment.workflow import api

logger = logging.getLogger(__name__)


@shared_task(bind=True,
             acks_late=True,
             autoretry_for=(Exception,),
             max_retries=5,
             retry_backoff=True,
             retry_backoff_max=500,
             retry_jitter=True)
def update_workflows_for_all_blocked_submissions_task(self):  # pylint: disable=unused-argument
    """
    Async task wrapper
    """
    return update_workflows_for_all_blocked_submissions()


@shared_task(bind=True,
             acks_late=True,
             autoretry_for=(Exception,),
             max_retries=5,
             retry_backoff=True,
             retry_backoff_max=500,
             retry_jitter=True)
def update_workflows_for_course_task(self, course_id):  # pylint: disable=unused-argument
    """
    Async task wrapper
    """
    return update_workflows_for_course(course_id)


@shared_task(bind=True,
             acks_late=True,
             autoretry_for=(Exception,),
             max_retries=5,
             retry_backoff=True,
             retry_backoff_max=500,
             retry_jitter=True)
def update_workflows_for_ora_block_task(self, item_id):  # pylint: disable=unused-argument
    """
    Async task wrapper
    """
    return update_workflows_for_ora_block(item_id)


@shared_task(bind=True,
             acks_late=True,
             autoretry_for=(Exception,),
             max_retries=5,
             retry_backoff=True,
             retry_backoff_max=500,
             retry_jitter=True)
# pylint: disable=unused-argument
def update_workflow_for_submission_task(self, submission_uuid, assessment_requirements, course_settings):
    """
    Async task wrapper
    """
    return update_workflow_for_submission(submission_uuid, assessment_requirements, course_settings)


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
        start = time.time()

        peer_workflows = get_blocked_peer_workflows()
        workflow_update_parameters = get_workflow_update_parameters(peer_workflows)
        if workflow_update_parameters.get("courses") is not None:
            for course_object in workflow_update_parameters.get("courses"):
                # execute asynchronously (submit Celery task)
                update_workflows_for_course_task.apply_async([course_object["course_id"], workflow_update_parameters])

            end = time.time()
            logger.info(
                "Batch workflow update tasks submitted successfully for each course id. "
                "task_count=%s processing_time=%s",
                len(workflow_update_parameters["courses"]),
                str(end - start))
        else:
            logger.info("No blocked ORA submissions found. "
                        "Batch workflow update completed without submitting any tasks.")

    except (UpdateWorkflowsForCourseException, Exception) as e:  # pylint: disable=broad-except
        logger.error(
            "Batch workflow update. Error occurred while updating workflows for all blocked submissions.  Error:%s",
            str(e))
        raise UpdateWorkflowsForAllBlockedSubmissionsException(str(e)) from e


def update_workflows_for_course(course_id, workflow_update_parameters=None):
    """
    Updates ORA workflows created for the given course

    Args:
        course_id (str): Course identifier
        workflow_update_parameters (dict): optional dictionary containing data required to
        update ORA workflow for submission. If not passed, data will be retrieved from DB

        Sample structure (assessment_requirements and course_settings content omitted):
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
    Raises:
        UpdateWorkflowsForCourseException: If batch process fails and cannot continue.
    """
    try:
        start = time.time()

        if workflow_update_parameters is None:
            peer_workflows = get_blocked_peer_workflows(course_id=course_id)
            workflow_update_parameters = get_workflow_update_parameters(peer_workflows)

        course_data = _get_course_object(workflow_update_parameters, course_id)

        if course_data is not None and course_data.get("assessments") is not None:
            for item in course_data["assessments"]:
                # execute asynchronously (submit Celery task)
                update_workflows_for_ora_block_task.apply_async([item["item_id"], workflow_update_parameters])

            end = time.time()
            logger.info(
                "Batch workflow tasks submitted successfully for each ORA item_id within course. "
                "course_id=%s task_count=%s processing_time=%s",
                course_id,
                len(course_data["assessments"]),
                str(end - start))
        else:
            logger.info("No blocked ORA submissions found for the course_id=%s . "
                        "Batch workflow update completed without submitting any tasks.",
                        course_id)

    except (UpdateWorkflowsForOraBlockException, Exception) as e:  # pylint: disable=broad-except
        logger.error(
            "Batch workflow update for course blocked submissions failed. "
            "course_id=%s Error:%s",
            course_id,
            str(e))
        raise UpdateWorkflowsForCourseException(str(e)) from e


def update_workflows_for_ora_block(item_id, workflow_update_parameters=None):
    """
    Updates ORA workflows created for the given ORA Block

    Args:
    item_id (str): Identifier for the ORA Block
        e.g. 'block-v1:edX+DemoX+Demo_Course+type@openassessment+block@1676f4b05f0642249ff724e7c07d869e'

    workflow_update_parameters (dict): optional dictionary containing data required to
        update ORA workflow for submission. If not passed, data will be retrieved from DB

        Sample structure (assessment_requirements and course_settings content omitted):
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

    Raises:
        OraWorkflowBatchUpdateException: If batch process fails and cannot continue, e.g. number of errors
                                        threshold was exceeded, etc.
    """
    try:
        start = time.time()

        if workflow_update_parameters is None:
            peer_workflows = get_blocked_peer_workflows(item_id=item_id)
            workflow_update_parameters = get_workflow_update_parameters(peer_workflows)

        course_settings = _get_course_settings_for_ora(workflow_update_parameters, item_id)
        workflow_update_parameters_for_ora = _get_ora_object(workflow_update_parameters, item_id)

        if workflow_update_parameters_for_ora is not None and workflow_update_parameters_for_ora.get(
                'assessment_requirements') is not None:
            assessment_requirements = workflow_update_parameters_for_ora['assessment_requirements']

            for item in workflow_update_parameters_for_ora["submissions"]:
                # execute asynchronously (submit Celery task)
                update_workflow_for_submission_task.apply_async(
                    [item["submission_uuid"], assessment_requirements, course_settings])

            end = time.time()
            logger.info(
                "Batch workflow update for blocked ORA submissions completed successfully. "
                "item_id=%s assessment_requirements=%s course_settings=%s submissions=%s processing_time=%s",
                item_id,
                assessment_requirements,
                course_settings,
                workflow_update_parameters_for_ora["submissions"],
                str(end - start))
        else:
            logger.info("No blocked ORA submissions found for the ORA item_id=%s . "
                        "Batch workflow update completed without submitting any tasks.",
                        item_id)

    except (UpdateWorkflowForSubmissionException, Exception) as e:  # pylint: disable=broad-except
        logger.error(
            "Batch workflow update for ORA block failed. "
            "item_id=%s error_message:%s",
            item_id,
            str(e))
        raise UpdateWorkflowsForOraBlockException(str(e)) from e


def update_workflow_for_submission(submission_uuid, assessment_requirements, course_settings):
    """
    Wrapper for `workflow.api.update_from_assessments(submission_uuid, assessment_requirements, course_override)`
    """
    try:
        start = time.time()
        workflow = api.update_from_assessments(submission_uuid, assessment_requirements, course_settings)
        end = time.time()
        logger.info(
            "ORA workflow update for a single blocked submission completed successfully. "
            "submission_uuid=%s assessment_requirements=%s course_settings=%s processing_time=%s",
            submission_uuid,
            assessment_requirements,
            course_settings,
            str(end - start))
        return workflow
    except Exception as e:  # pylint: disable=broad-except
        logger.error(
            "ORA workflow update for a single submission failed. "
            "submission_uuid=%s assessment_requirements=%s course_settings=%s. error_message=%s",
            submission_uuid,
            assessment_requirements,
            course_settings,
            str(e))
        raise UpdateWorkflowForSubmissionException(str(e)) from e


def is_flexible_peer_grading_on(openassessmentblock):
    """
    Is flexible peer grading set "ON" for provided ORA block

    Args:
        openassessmentblock (OpenAssessmentBlock): ORA block

    Returns:
        bool: True if given ORA is configured with flexible peer grading set "ON"
    """
    workflow_requirements = openassessmentblock.workflow_requirements()
    if workflow_requirements.get('peer') and workflow_requirements['peer'].get('enable_flexible_grading'):
        return True

    return False


def get_blocked_peer_workflows(course_id=None, item_id=None):
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

    return PeerWorkflow.objects.filter(**filters)


def get_workflow_update_parameters(peer_workflows):
    """
    Generates dictionary containing data required to update ORA workflows for different scopes.
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
    workflow_update_parameters_dict = {}
    store = modulestore()
    for peer_workflow in peer_workflows:
        try:
            # retrieve openassessment block
            ora_block_key = UsageKey.from_string(peer_workflow.item_id)
            ora_block = store.get_item(ora_block_key)

            # retrieve course block
            course_block_key = UsageKey.from_string(peer_workflow.course_id)
            course_block = store.get_item(course_block_key)

            if is_flexible_peer_grading_on(ora_block) or course_block.force_on_flexible_peer_openassessments:
                # we are interested only in submissions for ORA with flexible peer grading configured
                course_settings = {
                    'force_on_flexible_peer_openassessments': course_block.force_on_flexible_peer_openassessments}
                _add_workflow_update_parameters(workflow_update_parameters_dict,
                                                peer_workflow.course_id,
                                                peer_workflow.item_id,
                                                peer_workflow.submission_uuid,
                                                ora_block.workflow_requirements(),
                                                course_settings)

        except Exception as e:  # pylint: disable=broad-except
            logger.warning(
                "Error occurred while constructing workflow update parameters"
                "for open assessment: %s  Error:%s",
                peer_workflow.item_id, str(e))

    return workflow_update_parameters_dict


def _add_workflow_update_parameters(data, course_id, item_id, submission_id, course_settings, assessment_requirements):
    """
    Helper method used in workflow update cache data generation process.
    Adds course node to the provided dictionary.
    Following structure will be created based on provided args:

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
    """
    if data.get('courses') is None:
        data.update({"courses": []})

    if _get_course_object(data, course_id) is None:
        data["courses"].append({"course_id": course_id, "course_settings": course_settings, "assessments": [
            {"item_id": item_id, "assessment_requirements": assessment_requirements,
             "submissions": [{"submission_uuid": submission_id}]}]})
    else:
        _get_course_object(data, course_id)["course_settings"] = course_settings

    if _get_ora_object(data, item_id) is None:
        # add new ORA object
        _get_course_object(data, course_id).get("assessments").append(
            {"item_id": item_id, "assessment_requirements": assessment_requirements,
             "submissions": []})
    else:  # update assessment requirements
        _get_ora_object(data, item_id)["assessment_requirements"] = assessment_requirements

    if _get_submission_object(data, submission_id) is None:
        # add submission uuid
        _get_ora_object(data, item_id).get("submissions").append({"submission_uuid": submission_id})

    return data


def _get_course_object(workflow_update_parameters, course_id):
    """
    Helper function to return `update_workflow_parameters` dict object structure
    representing specified course.
    E.g.  for requested "course_id_1"

    ```
    {
      "courses": [
        {                               ### this object will be returned
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
    """
    if workflow_update_parameters.get("courses"):
        for course_object in workflow_update_parameters.get("courses"):
            if course_object["course_id"] == course_id:
                return course_object
    return None


def _get_course_settings_for_ora(workflow_update_parameters, item_id):
    """
    Helper function to search workflow_update_parameters dict structure
    and return `course_settings` dict object for a given item_id

    E.g.  for requested "item_id_1"

    ```
    {
      "courses": [
        {
          "course_id": "course_id_1",
          "course_settings": {  ### this object will be returned
          },
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
    """
    if workflow_update_parameters.get("courses"):
        for course_object in workflow_update_parameters.get("courses"):
            for assessment_object in course_object.get("assessments"):
                if assessment_object["item_id"] == item_id:
                    return course_object["course_settings"]
    return None


def _get_ora_object(workflow_update_parameters, item_id):
    """
    Helper function to return `update_workflow_parameters` dict object structure
    representing specified ORA item.
    E.g.  for requested "item_id_1"

    ```
    {
      "courses": [
        {
          "course_id": "course_id_1",
          "course_settings": {},
          "assessments": [
            {                           ### this object will be returned
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
    """
    if workflow_update_parameters.get("courses"):
        for course_object in workflow_update_parameters.get("courses"):
            for assessment_object in course_object.get("assessments"):
                if assessment_object["item_id"] == item_id:
                    return assessment_object
    return None


def _get_submission_object(workflow_update_parameters, submission_uuid):
    """
    Helper function to return `update_workflow_parameters` dict object structure
    representing specified submission.
    E.g.  for requested "submission_uuid_1"

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
                {                                       ### this object will be returned
                "submission_uuid": "submission_uuid_1"
                }
              ]
            }
          ]
        }
      ]
    }
    ```
    """
    if workflow_update_parameters.get("courses"):
        for course_object in workflow_update_parameters.get("courses"):
            for assessment_object in course_object.get("assessments"):
                for submission_object in assessment_object.get("submissions"):
                    if submission_object["submission_uuid"] == submission_uuid:
                        return submission_object
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
