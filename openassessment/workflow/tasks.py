"""
Celery task wrappers to execute batch ORA workflow update and reminder sweeping.
"""

from celery import shared_task
from celery.signals import worker_ready

from edx_django_utils.monitoring import set_code_owner_attribute

# Import sweep_ora_reminders so Celery autodiscovery registers it.
# The task lives in ora_reminders.py to keep sweeper logic self-contained.
from openassessment.xblock.utils.ora_reminders import sweep_ora_reminders  # noqa: F401


@worker_ready.connect
def on_worker_ready(sender, **kwargs):  # pylint: disable=unused-argument
    """
    Start the ORA reminder sweep chain when a Celery worker comes online.

    Clears the sweep lock first because pending countdown tasks from a
    previous worker process are lost on restart.  In a multi-worker setup
    ``cache.add`` inside ``ensure_sweep_chain_running`` still prevents
    duplicate chains — only the first worker to re-acquire the lock wins.
    """
    from django.core.cache import cache
    from openassessment.xblock.utils.ora_reminders import ensure_sweep_chain_running, SWEEP_LOCK_KEY
    cache.delete(SWEEP_LOCK_KEY)
    ensure_sweep_chain_running()


@shared_task(bind=True,
             acks_late=True,
             autoretry_for=(Exception,),
             max_retries=3,
             retry_backoff=True,
             retry_backoff_max=500,
             retry_jitter=True)
@set_code_owner_attribute
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
@set_code_owner_attribute
# pylint: disable=unused-argument
def update_workflows_for_course_task(self, course_id, workflow_update_data_for_course=None):
    """
    Async task wrapper
    """
    from openassessment.workflow.workflow_batch_update_api import update_workflows_for_course
    return update_workflows_for_course(course_id, workflow_update_data_for_course)


@shared_task(bind=True,
             acks_late=True,
             autoretry_for=(Exception,),
             max_retries=3,
             retry_backoff=True,
             retry_backoff_max=500,
             retry_jitter=True)
@set_code_owner_attribute
# pylint: disable=unused-argument
def update_workflows_for_ora_block_task(self, item_id, workflow_update_data_for_ora=None, course_settings=None):
    """
    Async task wrapper
    """
    from openassessment.workflow.workflow_batch_update_api import update_workflows_for_ora_block
    return update_workflows_for_ora_block(item_id, workflow_update_data_for_ora, course_settings)


@shared_task(bind=True,
             acks_late=True,
             autoretry_for=(Exception,),
             max_retries=3,
             retry_backoff=True,
             retry_backoff_max=300,
             retry_jitter=True)
@set_code_owner_attribute
# pylint: disable=unused-argument
def update_workflow_for_submission_task(self, submission_uuid, assessment_requirements=None, course_settings=None):
    """
    Async task wrapper
    """
    from openassessment.workflow.workflow_batch_update_api import update_workflow_for_submission
    return update_workflow_for_submission(submission_uuid, assessment_requirements, course_settings)
