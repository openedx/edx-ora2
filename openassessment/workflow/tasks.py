"""
Celery task wrappers to execute batch ORA workflow update
"""

from celery import shared_task


@shared_task(bind=True,
             acks_late=True,
             autoretry_for=(Exception,),
             max_retries=3,
             retry_backoff=True,
             retry_backoff_max=500,
             retry_jitter=True)
def update_workflows_for_all_blocked_submissions_task(self):  # pylint: disable=unused-argument
    """
    Async task wrapper
    """
    from openassessment.workflow.workflow_batch_update_api import update_workflows_for_all_blocked_submissions
    return update_workflows_for_all_blocked_submissions()


@shared_task(bind=True,
             acks_late=True,
             autoretry_for=(Exception,),
             max_retries=3,
             retry_backoff=True,
             retry_backoff_max=500,
             retry_jitter=True)
def update_workflows_for_course_task(self, course_id):  # pylint: disable=unused-argument
    """
    Async task wrapper
    """
    from openassessment.workflow.workflow_batch_update_api import update_workflows_for_course
    return update_workflows_for_course(course_id)


@shared_task(bind=True,
             acks_late=True,
             autoretry_for=(Exception,),
             max_retries=3,
             retry_backoff=True,
             retry_backoff_max=500,
             retry_jitter=True)
def update_workflows_for_ora_block_task(self, item_id):  # pylint: disable=unused-argument
    """
    Async task wrapper
    """
    from openassessment.workflow.workflow_batch_update_api import update_workflows_for_ora_block
    return update_workflows_for_ora_block(item_id)


@shared_task(bind=True,
             acks_late=True,
             autoretry_for=(Exception,),
             max_retries=3,
             retry_backoff=True,
             retry_backoff_max=300,
             retry_jitter=True)
# pylint: disable=unused-argument
def update_workflow_for_submission_task(self, submission_uuid, assessment_requirements=None, course_settings=None):
    """
    Async task wrapper
    """
    from openassessment.workflow.workflow_batch_update_api import update_workflow_for_submission
    return update_workflow_for_submission(submission_uuid, assessment_requirements, course_settings)
