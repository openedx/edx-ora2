"""Async API wrapper for API defined in  openassessment.workflow_batch_update_api """

from celery import shared_task
from openassessment import workflow_batch_update_api


@shared_task
def update_workflows_for_all_blocked_submissions():
    return workflow_batch_update_api.update_workflows_for_all_blocked_submissions()

@shared_task
def update_workflows_for_ora_block(item_id):
    return workflow_batch_update_api.update_workflows_for_ora_block(item_id)

@shared_task
def update_workflows_for_course(course_id):
    return workflow_batch_update_api.update_workflows_for_course(course_id)

