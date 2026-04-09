"""
Manual test script for ORA reminder notification flow.
Run from edx-platform Django shell:
    python manage.py lms shell < /path/to/test_ora_reminder_flow.py

Tests:
  1. create_ora_reminder() creates a DB row correctly
  2. Sweeper skips rows when feature is disabled
  3. Sweeper deactivates when workflow step is not peer/self
  4. Sweeper reschedules when no peer submissions are available
  5. Sweeper sends notification and advances schedule (peer step)
  6. Sweeper sends notification for self step (no peer check)
  7. Sweeper deactivates when max count reached
  8. Sweeper deactivates when ORA deadline has passed
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.conf import settings

from openassessment.workflow.models import ORAReminder, AssessmentWorkflow
from openassessment.xblock.utils.ora_reminders import (
    create_ora_reminder,
    _do_sweep,
    _process_single_reminder,
)

User = get_user_model()
NOW = datetime.now(timezone.utc)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"

def check(label, condition):
    print(f"{'✅' if condition else '❌'} {label}: {PASS if condition else FAIL}")
    return condition

def make_reminder(user, submission_uuid=None, next_reminder_at=None, reminder_sent_count=0,
                  is_active=True, ora_due_date=None, course_end_date=None):
    """Create a fresh ORAReminder row for testing."""
    ORAReminder.objects.filter(submission_uuid=submission_uuid or '').delete()
    return ORAReminder.objects.create(
        user=user,
        course_id='course-v1:OpenedX+DemoX+DemoCourse',
        ora_usage_key='block-v1:OpenedX+DemoX+DemoCourse+type@openassessment+block@test',
        ora_name='Test ORA',
        submission_uuid=submission_uuid or str(uuid.uuid4()),
        submission_time=NOW - timedelta(hours=25),
        content_url='http://localhost/courses/test/jump_to/block',
        next_reminder_at=next_reminder_at or (NOW - timedelta(minutes=5)),
        reminder_sent_count=reminder_sent_count,
        is_active=is_active,
        ora_due_date=ora_due_date,
        course_end_date=course_end_date,
    )

user = User.objects.get(username='learner')

print("\n" + "="*60)
print("  ORA REMINDER FLOW — MANUAL TEST SUITE")
print("="*60 + "\n")

# ---------------------------------------------------------------------------
# TEST 1: create_ora_reminder() — feature disabled
# ---------------------------------------------------------------------------
print("── Test 1: create_ora_reminder skips when feature disabled ──")
ORAReminder.objects.all().delete()
sub_uuid = str(uuid.uuid4())

with patch.dict(settings.FEATURES, {'ENABLE_ORA_REMINDERS': False}):
    create_ora_reminder(
        user_id=user.id,
        course_key_str='course-v1:OpenedX+DemoX+DemoCourse',
        ora_usage_key_str='block-v1:OpenedX+DemoX+DemoCourse+type@openassessment+block@test',
        ora_name='Test ORA',
        submission_uuid=sub_uuid,
        submission_time_iso=NOW.isoformat(),
        content_url='http://localhost/test',
    )

check("No row created when ENABLE_ORA_REMINDERS=False", ORAReminder.objects.count() == 0)

# ---------------------------------------------------------------------------
# TEST 2: create_ora_reminder() — feature enabled
# ---------------------------------------------------------------------------
print("\n── Test 2: create_ora_reminder creates row when enabled ──")
sub_uuid = str(uuid.uuid4())

with patch.dict(settings.FEATURES, {'ENABLE_ORA_REMINDERS': True}), \
     patch('openassessment.xblock.utils.ora_reminders._get_ora_due_date', return_value=None), \
     patch('openassessment.xblock.utils.ora_reminders._get_course_end_date', return_value=None):
    create_ora_reminder(
        user_id=user.id,
        course_key_str='course-v1:OpenedX+DemoX+DemoCourse',
        ora_usage_key_str='block-v1:OpenedX+DemoX+DemoCourse+type@openassessment+block@test',
        ora_name='Test ORA',
        submission_uuid=sub_uuid,
        submission_time_iso=NOW.isoformat(),
        content_url='http://localhost/test',
    )

row = ORAReminder.objects.filter(submission_uuid=sub_uuid).first()
check("Row created in DB", row is not None)
check("is_active=True", row and row.is_active)
check("reminder_sent_count=0", row and row.reminder_sent_count == 0)
initial_delay = getattr(settings, 'ORA_REMINDER_INITIAL_DELAY_HOURS', 24)
expected_next = NOW + timedelta(hours=initial_delay)
check(
    f"next_reminder_at ≈ now + {initial_delay}h",
    row and abs((row.next_reminder_at - expected_next).total_seconds()) < 10
)

# ---------------------------------------------------------------------------
# TEST 3: sweep — feature disabled, no rows processed
# ---------------------------------------------------------------------------
print("\n── Test 3: Sweep does nothing when feature disabled ──")
ORAReminder.objects.all().delete()
reminder = make_reminder(user)

notification_mock = MagicMock()
with patch.dict(settings.FEATURES, {'ENABLE_ORA_REMINDERS': False}), \
     patch('openedx_events.learning.signals.USER_NOTIFICATION_REQUESTED.send_event', notification_mock):
    _do_sweep()

reminder.refresh_from_db()
check("No notification sent", notification_mock.call_count == 0)
check("Row untouched (still active, count=0)", reminder.is_active and reminder.reminder_sent_count == 0)

# ---------------------------------------------------------------------------
# TEST 4: sweep — workflow step not peer/self → deactivate
# ---------------------------------------------------------------------------
print("\n── Test 4: Deactivate when workflow step is not peer/self ──")
ORAReminder.objects.all().delete()
reminder = make_reminder(user)

notification_mock = MagicMock()
with patch.dict(settings.FEATURES, {'ENABLE_ORA_REMINDERS': True}), \
     patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='training'), \
     patch('openedx_events.learning.signals.USER_NOTIFICATION_REQUESTED.send_event', notification_mock):
    _do_sweep()

reminder.refresh_from_db()
check("Row deactivated", not reminder.is_active)
check("No notification sent", notification_mock.call_count == 0)

# ---------------------------------------------------------------------------
# TEST 5: sweep — peer step, no peer submissions available → reschedule
# ---------------------------------------------------------------------------
print("\n── Test 5: Reschedule when peer step but no submissions to review ──")
ORAReminder.objects.all().delete()
reminder = make_reminder(user)
original_next = reminder.next_reminder_at

notification_mock = MagicMock()
with patch.dict(settings.FEATURES, {'ENABLE_ORA_REMINDERS': True}), \
     patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer'), \
     patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=False), \
     patch('openedx_events.learning.signals.USER_NOTIFICATION_REQUESTED.send_event', notification_mock):
    _do_sweep()

reminder.refresh_from_db()
check_again = getattr(settings, 'ORA_REMINDER_CHECK_AGAIN_HOURS', 12)
check("Still active (not deactivated)", reminder.is_active)
check("count unchanged at 0", reminder.reminder_sent_count == 0)
check(f"next_reminder_at advanced by {check_again}h", reminder.next_reminder_at > original_next)
check("No notification sent", notification_mock.call_count == 0)

# ---------------------------------------------------------------------------
# TEST 6: sweep — peer step, submissions available → send notification
# ---------------------------------------------------------------------------
print("\n── Test 6: Send notification for peer step (submissions available) ──")
ORAReminder.objects.all().delete()
reminder = make_reminder(user)

notification_mock = MagicMock()
with patch.dict(settings.FEATURES, {'ENABLE_ORA_REMINDERS': True}), \
     patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer'), \
     patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True), \
     patch('openedx_events.learning.signals.USER_NOTIFICATION_REQUESTED.send_event', notification_mock):
    _do_sweep()

reminder.refresh_from_db()
check("Notification sent once", notification_mock.call_count == 1)
check("reminder_sent_count incremented to 1", reminder.reminder_sent_count == 1)
check("Still active (max not reached)", reminder.is_active)

# Verify notification payload
if notification_mock.call_count == 1:
    call_kwargs = notification_mock.call_args[1]
    nd = call_kwargs['notification_data']
    check("notification_type = 'ora_reminder'", nd.notification_type == 'ora_reminder')
    check("pending_step = 'peer reviews'", nd.context.get('pending_step') == 'peer reviews')
    check("ora_name = 'Test ORA'", nd.context.get('ora_name') == 'Test ORA')
    check("user_id is correct", nd.user_ids == [user.id])

# ---------------------------------------------------------------------------
# TEST 7: sweep — self step → send notification (no peer check)
# ---------------------------------------------------------------------------
print("\n── Test 7: Send notification for self step (no peer availability check) ──")
ORAReminder.objects.all().delete()
reminder = make_reminder(user)

notification_mock = MagicMock()
peer_check_mock = MagicMock()
with patch.dict(settings.FEATURES, {'ENABLE_ORA_REMINDERS': True}), \
     patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='self'), \
     patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', peer_check_mock), \
     patch('openedx_events.learning.signals.USER_NOTIFICATION_REQUESTED.send_event', notification_mock):
    _do_sweep()

reminder.refresh_from_db()
check("Notification sent", notification_mock.call_count == 1)
check("Peer availability NOT checked for self step", peer_check_mock.call_count == 0)
if notification_mock.call_count == 1:
    nd = notification_mock.call_args[1]['notification_data']
    check("pending_step = 'self review'", nd.context.get('pending_step') == 'self review')

# ---------------------------------------------------------------------------
# TEST 8: sweep — max count reached → deactivate without sending
# ---------------------------------------------------------------------------
print("\n── Test 8: Deactivate when max count already reached ──")
ORAReminder.objects.all().delete()
max_count = getattr(settings, 'ORA_REMINDER_MAX_COUNT', 3)
reminder = make_reminder(user, reminder_sent_count=max_count)

notification_mock = MagicMock()
with patch.dict(settings.FEATURES, {'ENABLE_ORA_REMINDERS': True}), \
     patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer'), \
     patch('openedx_events.learning.signals.USER_NOTIFICATION_REQUESTED.send_event', notification_mock):
    _do_sweep()

reminder.refresh_from_db()
check("Row deactivated", not reminder.is_active)
check("No notification sent", notification_mock.call_count == 0)

# ---------------------------------------------------------------------------
# TEST 9: sweep — ORA deadline passed → deactivate
# ---------------------------------------------------------------------------
print("\n── Test 9: Deactivate when ORA due date has passed ──")
ORAReminder.objects.all().delete()
reminder = make_reminder(user, ora_due_date=NOW - timedelta(days=1))

notification_mock = MagicMock()
with patch.dict(settings.FEATURES, {'ENABLE_ORA_REMINDERS': True}), \
     patch('openedx_events.learning.signals.USER_NOTIFICATION_REQUESTED.send_event', notification_mock):
    _do_sweep()

reminder.refresh_from_db()
check("Row deactivated (deadline passed)", not reminder.is_active)
check("No notification sent", notification_mock.call_count == 0)

# ---------------------------------------------------------------------------
# TEST 10: sweep — not yet due → skip
# ---------------------------------------------------------------------------
print("\n── Test 10: Skip rows that are not yet due ──")
ORAReminder.objects.all().delete()
reminder = make_reminder(user, next_reminder_at=NOW + timedelta(hours=10))

notification_mock = MagicMock()
with patch.dict(settings.FEATURES, {'ENABLE_ORA_REMINDERS': True}), \
     patch('openedx_events.learning.signals.USER_NOTIFICATION_REQUESTED.send_event', notification_mock):
    _do_sweep()

reminder.refresh_from_db()
check("Row untouched (not yet due)", reminder.is_active and reminder.reminder_sent_count == 0)
check("No notification sent", notification_mock.call_count == 0)

# ---------------------------------------------------------------------------
# TEST 11: Final reminder → deactivate after sending
# ---------------------------------------------------------------------------
print("\n── Test 11: Deactivate after sending the final reminder ──")
ORAReminder.objects.all().delete()
max_count = getattr(settings, 'ORA_REMINDER_MAX_COUNT', 3)
reminder = make_reminder(user, reminder_sent_count=max_count - 1)

notification_mock = MagicMock()
with patch.dict(settings.FEATURES, {'ENABLE_ORA_REMINDERS': True}), \
     patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer'), \
     patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True), \
     patch('openedx_events.learning.signals.USER_NOTIFICATION_REQUESTED.send_event', notification_mock):
    _do_sweep()

reminder.refresh_from_db()
check("Final notification sent", notification_mock.call_count == 1)
check(f"reminder_sent_count = {max_count}", reminder.reminder_sent_count == max_count)
check("Row deactivated after final reminder", not reminder.is_active)

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
ORAReminder.objects.all().delete()

print("\n" + "="*60)
print("  ALL TESTS COMPLETE")
print("="*60 + "\n")
