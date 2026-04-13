"""
Self-chaining sweeper for ORA reminder notifications.

Instead of one Celery chain per user, a **single** Celery task
(``sweep_ora_reminders``) runs periodically, queries the pending peer/self review
submissions for users whose reminder is due, and sends reminder notifications.

Feature is enabled via ``ENABLE_ORA_REMINDERS = True`` in Django settings.
See ``docs/ora_reminders.rst`` for full configuration reference.

This module is responsible for:
- Creating ORAReminder DB rows when submissions are created
- Ensuring the sweeper chain is running
- The sweeper logic that processes reminders

Termination condition (per spec):
  A reminder row is deactivated once:
    now >= submission_time + INITIAL_DELAY_HOURS + MAX_COUNT * INTERVAL_HOURS
  This is equivalent to "all X reminders have been sent" without tracking count.
"""
import logging
import random
from datetime import datetime, timedelta, timezone

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from edx_django_utils.monitoring import set_code_owner_attribute
from opaque_keys.edx.keys import CourseKey
from openedx_events.learning.data import UserNotificationData
from openedx_events.learning.signals import USER_NOTIFICATION_REQUESTED
from openassessment.assessment.api import peer as peer_api

from openassessment.workflow.models import ORAReminder, AssessmentWorkflow

logger = logging.getLogger(__name__)

# ORA workflow steps that should trigger reminders.
PENDING_REMINDER_STEPS = {'peer', 'self'}

STEP_DISPLAY_NAMES = {
    'peer': 'peer reviews',
    'self': 'self review',
}

# Cache keys
SWEEP_LOCK_KEY = 'ora_reminder_sweep_lock'
SWEEP_HEARTBEAT_KEY = 'ora_reminder_sweep_heartbeat'

# The lock timeout must be larger than the sweep interval so the lock doesn't
# expire while the next countdown is still pending.
SWEEP_LOCK_TIMEOUT_MULTIPLIER = 3


def create_ora_reminder(
        user_id,
        course_key_str,
        ora_usage_key_str,
        ora_name,
        submission_uuid,
        submission_time_iso,
        content_url,
        course_end_date=None,
        ora_due_date=None,
        peer_assessment_due=None,
        self_assessment_due=None,
):
    """
    Persist an ``ORAReminder`` row so the sweeper can pick it up later.

    Called from submissions_actions._handle_post_submission_notifications when a
    learner submits an ORA whose immediate next workflow step is peer or self review.

    All deadline fields are passed in by the caller (which has xblock context)
    and cached on the row so the sweeper never needs to touch the modulestore.

    Args:
        user_id (int): The user ID of the submitting learner
        course_key_str (str): The course key string
        ora_usage_key_str (str): The ORA block usage key string
        ora_name (str): The display name of the ORA block
        submission_uuid (str): The UUID of the submission
        submission_time_iso (str): The submission timestamp in ISO 8601 format
        content_url (str): The URL to the ORA block
        course_end_date (datetime, optional): Course end date
        ora_due_date (datetime, optional): ORA block-level due date
        peer_assessment_due (datetime, optional): Peer assessment step due date
        self_assessment_due (datetime, optional): Self assessment step due date
    """
    if not getattr(settings, 'ENABLE_ORA_REMINDERS', False):
        logger.debug('ora_reminders: ENABLE_ORA_REMINDERS is disabled, skipping reminder creation')
        return

    initial_delay_hours = getattr(settings, 'ORA_REMINDER_INITIAL_DELAY_HOURS', 24)
    submission_time = datetime.fromisoformat(submission_time_iso)
    if submission_time.tzinfo is None:
        submission_time = submission_time.replace(tzinfo=timezone.utc)
    next_reminder_at = submission_time + timedelta(hours=initial_delay_hours)

    try:
        ORAReminder.objects.update_or_create(
            submission_uuid=submission_uuid,
            defaults={
                'user_id': user_id,
                'course_id': course_key_str,
                'ora_usage_key': ora_usage_key_str,
                'ora_name': ora_name,
                'submission_time': submission_time,
                'content_url': content_url,
                'ora_due_date': ora_due_date,
                'course_end_date': course_end_date,
                'peer_assessment_due': peer_assessment_due,
                'self_assessment_due': self_assessment_due,
                'next_reminder_at': next_reminder_at,
                'is_active': True,
            },
        )
        logger.info(
            'ora_reminders: Created reminder row for user %s, ORA %s (next_at=%s).',
            user_id, ora_usage_key_str, next_reminder_at,
        )
    except Exception:  # pylint: disable=broad-except
        logger.exception(
            'ora_reminders: Failed to create reminder row for user %s, submission %s.',
            user_id, submission_uuid,
        )


def ensure_sweep_chain_running():
    """
    Start the sweeper chain if one is not already running.

    Uses ``cache.add`` as a distributed lock: only the first caller wins.
    The lock TTL is set to ``SWEEP_LOCK_TIMEOUT_MULTIPLIER * sweep_interval``
    so the lock auto-expires if the chain truly dies.

    If the lock exists but the heartbeat is stale (older than
    ``2 * sweep_interval``), the chain is assumed dead and the lock is
    cleared so a new chain can start immediately.
    """
    if not getattr(settings, 'ENABLE_ORA_REMINDERS', False):
        logger.debug('ora_reminders: ENABLE_ORA_REMINDERS is disabled, not starting sweeper')
        return

    if getattr(settings, 'CELERY_ALWAYS_EAGER', False):
        logger.debug('ora_reminders: CELERY_ALWAYS_EAGER is True, not starting self-chaining sweeper')
        return

    sweep_interval = getattr(settings, 'ORA_REMINDER_SWEEP_INTERVAL_SECONDS', 1800)
    lock_timeout = sweep_interval * SWEEP_LOCK_TIMEOUT_MULTIPLIER

    # If the lock exists, check whether the chain is actually alive by
    # inspecting the heartbeat.  A stale heartbeat means the old chain
    # died (e.g. worker restart) but the lock hasn't expired yet.
    if cache.get(SWEEP_LOCK_KEY):
        heartbeat_iso = cache.get(SWEEP_HEARTBEAT_KEY)
        if heartbeat_iso:
            try:
                last_beat = datetime.fromisoformat(heartbeat_iso)
                stale_threshold = datetime.now(timezone.utc) - timedelta(seconds=sweep_interval * 2)
                if last_beat < stale_threshold:
                    logger.warning(
                        'ora_reminders: Heartbeat stale (last=%s). Clearing lock to restart chain.',
                        heartbeat_iso,
                    )
                    cache.delete(SWEEP_LOCK_KEY)
            except (ValueError, TypeError):
                pass

    acquired = cache.add(SWEEP_LOCK_KEY, 'running', timeout=lock_timeout)
    if acquired:
        jitter = random.randint(0, 60)
        sweep_ora_reminders.apply_async(countdown=jitter)
        logger.info('ora_reminders: Started sweeper chain (jitter=%ss).', jitter)
    else:
        logger.debug('ora_reminders: Sweeper chain already running; skipping start.')


@shared_task(ignore_result=True)
@set_code_owner_attribute
def sweep_ora_reminders():
    """
    ORA reminder notification sweeper.

    1. Query ``ORAReminder`` rows where ``is_active=True`` and
       ``next_reminder_at <= now``.
    2. For each row, check guards (deadline, workflow step, time window).
    3. Send notification or deactivate.
    4. Re-chain self with ``countdown=SWEEP_INTERVAL``.

    The re-chain lives in a ``finally`` block so the chain survives errors.
    When the feature is disabled the task stops re-chaining so the chain dies
    gracefully rather than continuing to enqueue no-op tasks.
    """
    sweep_interval = getattr(settings, 'ORA_REMINDER_SWEEP_INTERVAL_SECONDS', 1800)
    lock_timeout = sweep_interval * SWEEP_LOCK_TIMEOUT_MULTIPLIER
    # Never self-chain when tasks run eagerly (CELERY_ALWAYS_EAGER=True) — it causes infinite recursion.
    should_rechain = not getattr(settings, 'CELERY_ALWAYS_EAGER', False)

    try:
        if not getattr(settings, 'ENABLE_ORA_REMINDERS', False):
            logger.info('ora_reminders: ENABLE_ORA_REMINDERS is disabled. Sweeper stopping.')
            should_rechain = False
            return

        _do_sweep()

        now_utc = datetime.now(timezone.utc)
        cache.set(SWEEP_HEARTBEAT_KEY, now_utc.isoformat(), timeout=lock_timeout)

    except Exception:  # pylint: disable=broad-except
        logger.exception('ora_reminders: Sweeper encountered an error during sweep.')
    finally:
        if should_rechain:
            # Delete-then-add ensures only ONE of potentially parallel sweep
            # tasks wins the right to re-chain.  Parallel chains arise when a
            # worker restart leaves stale countdown tasks in Redis.
            cache.delete(SWEEP_LOCK_KEY)
            acquired = cache.add(SWEEP_LOCK_KEY, 'running', timeout=lock_timeout)
            if acquired:
                sweep_ora_reminders.apply_async(countdown=sweep_interval)
                logger.debug('ora_reminders: Re-chained sweeper in %s seconds.', sweep_interval)
            else:
                logger.info('ora_reminders: Another chain already re-acquired the lock; not re-chaining.')


def _do_sweep():
    """
    Core sweep logic — find due reminders and process each one.
    """
    now = datetime.now(timezone.utc)
    batch_size = getattr(settings, 'ORA_REMINDER_SWEEP_BATCH_SIZE', 1000)

    due_reminders = (
        ORAReminder.objects
        .filter(is_active=True, next_reminder_at__lte=now)
        .select_related('user')
        .order_by('next_reminder_at')[:batch_size]
    )

    processed = 0
    for reminder in due_reminders:
        try:
            _process_single_reminder(reminder, now)
            processed += 1
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                'ora_reminders: Error processing reminder id=%s (user=%s, ora=%s).',
                reminder.id, reminder.user_id, reminder.ora_usage_key,
            )

    if processed:
        logger.info('ora_reminders: Sweep processed %s reminder(s).', processed)


def _process_single_reminder(reminder, now):
    """
    Process one ``ORAReminder`` row.

    Guard order (spec §3):
    1. Time window elapsed  — now >= submission_time + Z + X*Y  → deactivate
    2. Step-level deadline   — current step due date has passed  → deactivate
    3. Course end date       — course has ended                  → deactivate
    4. Workflow step         — no longer peer or self            → deactivate
    5. Peer availability     — no peer submissions yet (peer only) → defer
    6. Send notification & advance schedule.
    """
    max_count = getattr(settings, 'ORA_REMINDER_MAX_COUNT', 3)
    interval_hours = getattr(settings, 'ORA_REMINDER_INTERVAL_HOURS', 48)
    initial_delay_hours = getattr(settings, 'ORA_REMINDER_INITIAL_DELAY_HOURS', 24)
    check_again_hours = getattr(settings, 'ORA_REMINDER_CHECK_AGAIN_HOURS', 12)

    # ---- Guard 1: time-based window (spec: "hours elapsed > X*Y+Z") ----
    reminder_window_end = reminder.submission_time + timedelta(
        hours=initial_delay_hours + max_count * interval_hours
    )
    if now >= reminder_window_end:
        _deactivate(reminder, f'Reminder window elapsed (cutoff={reminder_window_end})')
        return

    # ---- Guard 2 & 3: deadline checks ----
    # Get current step first so we can use the step-specific due date.
    current_step = _get_workflow_step(reminder.submission_uuid)
    if current_step not in PENDING_REMINDER_STEPS:
        _deactivate(reminder, f'Workflow step is "{current_step}" (not peer/self)')
        return

    step_due = (
        reminder.peer_assessment_due if current_step == 'peer'
        else reminder.self_assessment_due
    )
    # Fall back to ORA-level due date when no step-specific date was captured.
    effective_due = step_due or reminder.ora_due_date
    if effective_due and effective_due <= now:
        _deactivate(reminder, f'{current_step} step due date passed ({effective_due})')
        return

    if reminder.course_end_date and reminder.course_end_date <= now:
        _deactivate(reminder, 'Course end date passed')
        return

    # ---- Guard 4: peer availability ----
    if current_step == 'peer':
        has_available = _check_peer_submissions_available(reminder.submission_uuid)
        if not has_available:
            reminder.next_reminder_at = now + timedelta(hours=check_again_hours)
            reminder.save(update_fields=['next_reminder_at', 'modified'])
            logger.info(
                'ora_reminders: No peer submissions available yet for user %s, ORA %s. '
                'Will check again in %s hours.',
                reminder.user_id, reminder.ora_usage_key, check_again_hours,
            )
            return

    # ---- Send the notification ----
    pending_step = STEP_DISPLAY_NAMES.get(current_step, current_step)
    _send_reminder_notification(
        user_id=reminder.user_id,
        course_key_str=str(reminder.course_id),
        ora_name=reminder.ora_name,
        pending_step=pending_step,
        content_url=reminder.content_url,
    )

    # ---- Advance schedule ----
    next_at = now + timedelta(hours=interval_hours)
    if next_at >= reminder_window_end:
        # Final reminder sent — no more will be due within the window.
        reminder.is_active = False
        reminder.next_reminder_at = None
        logger.info(
            'ora_reminders: Final reminder sent for user %s, ORA %s (window closed at %s).',
            reminder.user_id, reminder.ora_usage_key, reminder_window_end,
        )
    else:
        reminder.next_reminder_at = next_at
        logger.info(
            'ora_reminders: Reminder sent for user %s, ORA %s. Next at %s.',
            reminder.user_id, reminder.ora_usage_key, next_at,
        )
    reminder.save(update_fields=['next_reminder_at', 'is_active', 'modified'])


def _deactivate(reminder, reason):
    """
    Mark a reminder row as inactive with a log message.
    """
    reminder.is_active = False
    reminder.save(update_fields=['is_active', 'modified'])
    logger.info(
        'ora_reminders: Deactivated reminder for user %s, ORA %s. Reason: %s',
        reminder.user_id, reminder.ora_usage_key, reason,
    )


def _get_workflow_step(submission_uuid):
    """
    Return the current workflow step for the given submission, or None.
    """
    try:
        workflow = AssessmentWorkflow.objects.get(submission_uuid=submission_uuid)
    except AssessmentWorkflow.DoesNotExist:
        return None

    return workflow.status


def _send_reminder_notification(user_id, course_key_str, ora_name, pending_step, content_url):
    """
    Fire the USER_NOTIFICATION_REQUESTED signal to create the ``ora_reminder`` notification.

    Args:
        user_id (int): The user ID of the learner who needs to complete their review
        course_key_str (str): The course key string
        ora_name (str): The display name of the ORA block
        pending_step (str): Human-readable pending step (e.g. "peer reviews")
        content_url (str): The URL to the ORA block
    """
    course_key = CourseKey.from_string(course_key_str)

    notification_data = UserNotificationData(
        user_ids=[int(user_id)],
        context={
            'ora_name': ora_name,
            'pending_step': pending_step,
        },
        notification_type='ora_reminder',
        content_url=content_url,
        app_name='grading',
        course_key=course_key,
    )
    USER_NOTIFICATION_REQUESTED.send_event(notification_data=notification_data)
    logger.info(
        'ora_reminders: Sent reminder notification for user %s, ORA %s (step=%s)',
        user_id, ora_name, pending_step,
    )


def _check_peer_submissions_available(submission_uuid):
    """
    Check if there are peer submissions available for the user to review.

    Prevents sending reminders to users (especially first submitters) when no
    other submissions exist for them to review yet.

    Args:
        submission_uuid (str): The UUID of the user's submission

    Returns:
        bool: True if peer submissions are available, False if waiting for peers
    """
    try:
        peer_submission = peer_api.get_submission_to_assess(
            submission_uuid,
            graded_by=1,
            peek=True,
        )
        return peer_submission is not None

    except Exception:  # pylint: disable=broad-except
        logger.exception(
            'ora_reminders: Error checking peer submission availability for %s',
            submission_uuid,
        )
        # Fail open — don't block reminders if the check itself errors
        return True
