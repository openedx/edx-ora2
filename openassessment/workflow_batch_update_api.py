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


@shared_task
def update_workflows_for_ora_block(item_id):
    """
    Updates ORA workflows created for the given ORA Block

    Args:
    item_id (str): Identifier for the ORA Block
        e.g. 'block-v1:edX+DemoX+Demo_Course+type@openassessment+block@1676f4b05f0642249ff724e7c07d869e'

    Raises:
        OraWorkflowBatchUpdateException: If batch process fails and cannot continue, e.g. number of errors
                                        threshold was exceeded, etc.
    """
    try:
        start = time.time()

        peer_workflows = get_blocked_peer_workflows_for_ora_block(item_id)
        assessment_requirements_dict = get_assessment_requirements_for_flex_peer_grading(peer_workflows)
        update_workflows(assessment_requirements_dict)

        end = time.time()
        logger.info(
            "Batch workflow update for ORA block submissions completed successfully; item_id=%s ;  processing_time=%s",
            item_id,
            str(end - start))

    except (OraWorkflowBatchUpdateErrorThresholdException, Exception) as e:  # pylint: disable=broad-except
        logger.error(
            "Batch workflow update failed. Error occurred while updating workflows for ORA block submissions. "
            "item_id=%s  Error:%s",
            item_id,
            str(e))
        raise OraWorkflowBatchUpdateException(str(e)) from e


@shared_task
def update_workflows_for_course(course_id):
    """
    Updates ORA workflows created for the given course

    Args:
        course_id (str): Course identifier

    Raises:
        OraWorkflowBatchUpdateException: If batch process fails and cannot continue, e.g. number of errors
                                        threshold was exceeded, etc.
    """
    try:
        start = time.time()

        peer_workflows = get_blocked_peer_workflows_for_course(course_id)
        assessment_requirements_dict = get_assessment_requirements_for_flex_peer_grading(peer_workflows)
        update_workflows(assessment_requirements_dict)

        end = time.time()
        logger.info(
            "Batch workflow update for course submissions completed successfully; course_id=%s ;  processing_time=%s",
            course_id,
            str(end - start))

    except (OraWorkflowBatchUpdateErrorThresholdException, Exception) as e:  # pylint: disable=broad-except
        logger.error(
            "Batch ORA workflow update failed. Error occurred while updating workflows for all blocked submissions. "
            "course_id=%s Error:%s",
            course_id,
            str(e))
        raise OraWorkflowBatchUpdateException(str(e)) from e


@shared_task
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
        assessment_requirements_dict = get_assessment_requirements_for_flex_peer_grading(peer_workflows)
        update_workflows(assessment_requirements_dict)

        end = time.time()
        logger.info(
            "Batch workflow update for all blocked submissions completed successfully; processing_time=%s",
            str(end - start))

    except (OraWorkflowBatchUpdateErrorThresholdException, Exception) as e:  # pylint: disable=broad-except
        logger.error(
            "Batch workflow update. Error occurred while updating workflows for all blocked submissions.  Error:%s",
            str(e))
        raise OraWorkflowBatchUpdateException(str(e)) from e


def update_workflows(assessment_requirements_dict, error_threshold=10):
    """
    Updates ORA workflows for the provided submission uuids provides in dictionary

    Args:
        assessment_requirements_dict (dict): <submission_uuid>:<assessment_requirements>
        error_threshold (int): If the number of single ORA workflow update errors exceeds `error_threshold` value,
                               batch process stops and `OraWorkflowBatchUpdateErrorThresholdException` is raised
    Raises:
        OraWorkflowBatchUpdateErrorThresholdException: if error threshold is exceeded
    """

    if assessment_requirements_dict is not None:
        error_count = 0
        for submission_uuid, assessment_requirements in assessment_requirements_dict.items():
            try:
                update_workflow_for_submission(submission_uuid, assessment_requirements, None)
            except Exception as e:  # pylint: disable=broad-except
                logger.warning(
                    "Batch workflow update. Error occurred while updating workflow for "
                    "submission_uuid=%s assessment_requirements=%s   Error:%s",
                    submission_uuid, assessment_requirements, str(e))
                error_count += 1
                if error_count > error_threshold:
                    # pylint: disable=raise-missing-from
                    raise OraWorkflowBatchUpdateErrorThresholdException(
                        "Number of errors exceeded {}.".format(error_threshold))


def update_workflow_for_submission(submission_uuid, assessment_requirements, course_override):
    """
    Wrapper for `workflow.api.update_from_assessments(submission_uuid, assessment_requirements, course_override)`
    """
    start = time.time()
    workflow = api.update_from_assessments(submission_uuid, assessment_requirements, course_override)
    end = time.time()
    logger.info(
        "Update_workflow_for_submission completed successfully; "
        "submission_uuid=%s assessment_requirements=%s course_setttings=%s processing_time=%s",
        submission_uuid,
        assessment_requirements,
        course_override,
        str(end - start))
    return workflow


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


def get_blocked_peer_workflows():
    """
    Retrieve ORA peer workflows not completed for >7 days

    Returns:
        list (PeerWorkflow): list of workfows not completed for > 7 days
    """

    peer_workflows = PeerWorkflow.objects.filter(
        created_at__lte=(timezone.now() - datetime.timedelta(days=7))
    ).exclude(
        completed_at__isnull=False
    )
    return peer_workflows


def get_blocked_peer_workflows_for_course(course_id):
    """
    Retrieve ORA peer workflows not completed for >7 days for a given course

    Args:
        course_id (str): course identifier

    Returns:
        list (PeerWorkflow): list of workfows not completed for > 7 days
    """
    peer_workflows = PeerWorkflow.objects.filter(
        created_at__lte=(timezone.now() - datetime.timedelta(days=7)),
        course_id__exact=course_id
    ).exclude(
        completed_at__isnull=False
    )
    return peer_workflows


def get_blocked_peer_workflows_for_ora_block(item_id):
    """
    Retrieve ORA peer workflows not completed for >7 days for a given ORA block id

    Args:
        item_id (str): Identifier of the ORA Block
            e.g. 'block-v1:edX+DemoX+Demo_Course+type@openassessment+block@1676f4b05f0642249ff724e7c07d869e'

    Returns:
        list (PeerWorkflow): list of workfows not completed for > 7 days
    """

    peer_workflows = PeerWorkflow.objects.filter(
        created_at__lte=(timezone.now() - datetime.timedelta(days=7)),
        item_id__exact=item_id
    ).exclude(
        completed_at__isnull=False
    )
    return peer_workflows


def get_assessment_requirements_for_flex_peer_grading(peer_workflows):
    """
    Returns assessment requirements for each provided peer workflow that was created
    for ORA with flexible peer grading configured (ON) .

    Args:
        peer_workflows (list): list of `PeerWorkflow` objects

    Returns:
        assessment_requirements_dict (dict): Dictionary:  <submission_uuid>:<assessment_requirements>
    """
    # dictionary <submission_uuid>:<workflow_requirements>
    workflow_requirements = {}
    store = modulestore()

    for peer_workflow in peer_workflows:
        try:
            block_key = UsageKey.from_string(peer_workflow.item_id)
            ora_block = store.get_item(block_key)

            if is_flexible_peer_grading_on(ora_block):
                workflow_requirements[peer_workflow.submission_uuid] = ora_block.workflow_requirements()
        except Exception as e:  # pylint: disable=broad-except
            logger.warning(
                "Batch workflow update. Error occurred while retrieving workflow requirements "
                "for open assessment: %s  Error:%s",
                peer_workflow.item_id, str(e))

    return workflow_requirements


class OraWorkflowBatchUpdateException(Exception):
    """Raised when batch ORA workflow process failed"""


class OraWorkflowBatchUpdateErrorThresholdException(Exception):
    """Raised when number of individual ORA workflow updates errors exceeds set threshold"""
