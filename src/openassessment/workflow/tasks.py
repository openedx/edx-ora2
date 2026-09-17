"""
Celery task wrappers to execute batch ORA workflow update and reminder sweeping.
"""

from celery import shared_task
from celery.signals import worker_ready

from edx_django_utils.monitoring import set_code_owner_attribute

# Import sweep_ora_reminders so Celery autodiscovery registers it.
# The task lives in ora_reminders.py to keep sweeper logic self-contained.
from openassessment.xblock.utils.ora_reminders import sweep_ora_reminders  # pylint: disable=unused-import  # noqa: F401


@worker_ready.connect
def on_worker_ready(sender, **kwargs):  # pylint: disable=unused-argument
    """
    Start the ORA reminder sweep chain when a Celery worker comes online.

    Delegates entirely to ``ensure_sweep_chain_running``, which acquires the
    lock atomically with ``cache.add`` and only clears it when the heartbeat is
    stale (older than ``2 * sweep_interval``).

    We deliberately do NOT ``cache.delete`` the lock here.  LMS in production
    runs many workers that restart one-at-a-time during a rolling deploy; an
    unconditional delete on each restart would yank the lock from a chain that
    is still alive (its next run is a countdown task in the broker, not bound to
    this worker), letting the restarted worker start a second, parallel chain —
    duplicate sweeps and duplicate notifications.  The heartbeat-staleness check
    is the single source of truth for "the previous chain actually died", so a
    genuinely dead chain still recovers (within ``2 * sweep_interval``) without
    risking duplicates.
    """
    from openassessment.xblock.utils.ora_reminders import ensure_sweep_chain_running
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
