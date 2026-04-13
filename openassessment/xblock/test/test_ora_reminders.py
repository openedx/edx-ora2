"""
Tests for openassessment.xblock.utils.ora_reminders

Covers:
- create_ora_reminder               (public helper)
- ensure_sweep_chain_running        (public helper)
- sweep_ora_reminders               (Celery task)
- _do_sweep                         (core sweep logic)
- _process_single_reminder          (per-row processing)
- _deactivate                       (row deactivation)
- _get_workflow_step                (workflow lookup)
- _send_reminder_notification       (signal dispatch)
- _check_peer_submissions_available (peer availability)
"""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from openassessment.test_utils import CacheResetTest
from openassessment.workflow.models import ORAReminder, AssessmentWorkflow


User = get_user_model()

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------
NOW = datetime(2026, 4, 8, 12, 0, 0, tzinfo=timezone.utc)
SUBMISSION_TIME = datetime(2026, 4, 7, 10, 0, 0, tzinfo=timezone.utc)
SUBMISSION_TIME_ISO = SUBMISSION_TIME.isoformat()
COURSE_KEY_STR = 'course-v1:TestX+T101+2026'
ORA_USAGE_KEY_STR = 'block-v1:TestX+T101+2026+type@openassessment+block@abc123'
ORA_NAME = 'Peer Essay'
SUBMISSION_UUID = 'sub-uuid-0001'
CONTENT_URL = 'http://lms.example.com/courses/course-v1:TestX+T101+2026/jump_to/block-v1:...'

# Default settings used across tests (Z=0, Y=48, X=3 → window = 144 h)
INITIAL_DELAY = 0
INTERVAL = 48
MAX_COUNT = 3
WINDOW = INITIAL_DELAY + MAX_COUNT * INTERVAL  # 144 h


def _make_reminder(user, **overrides):
    """Create an ORAReminder with sane defaults (submission_time=SUBMISSION_TIME, due in 1 h)."""
    defaults = dict(
        user=user,
        course_id=COURSE_KEY_STR,
        ora_usage_key=ORA_USAGE_KEY_STR,
        ora_name=ORA_NAME,
        submission_uuid=SUBMISSION_UUID,
        submission_time=SUBMISSION_TIME,
        content_url=CONTENT_URL,
        ora_due_date=None,
        course_end_date=None,
        peer_assessment_due=None,
        self_assessment_due=None,
        next_reminder_at=NOW - timedelta(hours=1),  # already due
        is_active=True,
    )
    defaults.update(overrides)
    return ORAReminder.objects.create(**defaults)


# ---------------------------------------------------------------------------
# create_ora_reminder
# ---------------------------------------------------------------------------
@override_settings(
    ENABLE_ORA_REMINDERS=True,
    ORA_REMINDER_INITIAL_DELAY_HOURS=INITIAL_DELAY,
    ORA_REMINDER_INTERVAL_HOURS=INTERVAL,
    ORA_REMINDER_MAX_COUNT=MAX_COUNT,
)
class TestCreateOraReminder(CacheResetTest):
    """Tests for the create_ora_reminder public helper."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='testlearner', password='pass')

    def test_creates_reminder_row(self):
        """A reminder row should be persisted with correct defaults."""
        from openassessment.xblock.utils.ora_reminders import create_ora_reminder

        create_ora_reminder(
            user_id=self.user.id,
            course_key_str=COURSE_KEY_STR,
            ora_usage_key_str=ORA_USAGE_KEY_STR,
            ora_name=ORA_NAME,
            submission_uuid=SUBMISSION_UUID,
            submission_time_iso=SUBMISSION_TIME_ISO,
            content_url=CONTENT_URL,
        )

        reminder = ORAReminder.objects.get(submission_uuid=SUBMISSION_UUID)
        self.assertEqual(reminder.user_id, self.user.id)
        self.assertEqual(reminder.course_id, COURSE_KEY_STR)
        self.assertEqual(reminder.ora_usage_key, ORA_USAGE_KEY_STR)
        self.assertEqual(reminder.ora_name, ORA_NAME)
        self.assertTrue(reminder.is_active)
        # With INITIAL_DELAY=0, next_reminder_at == submission_time
        self.assertEqual(reminder.next_reminder_at, SUBMISSION_TIME)

    @override_settings(ORA_REMINDER_INITIAL_DELAY_HOURS=12)
    def test_custom_initial_delay(self):
        """ORA_REMINDER_INITIAL_DELAY_HOURS should control next_reminder_at."""
        from openassessment.xblock.utils.ora_reminders import create_ora_reminder

        create_ora_reminder(
            user_id=self.user.id,
            course_key_str=COURSE_KEY_STR,
            ora_usage_key_str=ORA_USAGE_KEY_STR,
            ora_name=ORA_NAME,
            submission_uuid=SUBMISSION_UUID,
            submission_time_iso=SUBMISSION_TIME_ISO,
            content_url=CONTENT_URL,
        )
        reminder = ORAReminder.objects.get(submission_uuid=SUBMISSION_UUID)
        self.assertEqual(reminder.next_reminder_at, SUBMISSION_TIME + timedelta(hours=12))

    def test_update_or_create_overwrites_existing(self):
        """Calling create_ora_reminder twice with the same submission_uuid should update."""
        from openassessment.xblock.utils.ora_reminders import create_ora_reminder

        create_ora_reminder(
            user_id=self.user.id, course_key_str=COURSE_KEY_STR,
            ora_usage_key_str=ORA_USAGE_KEY_STR, ora_name='Old Name',
            submission_uuid=SUBMISSION_UUID, submission_time_iso=SUBMISSION_TIME_ISO,
            content_url=CONTENT_URL,
        )
        create_ora_reminder(
            user_id=self.user.id, course_key_str=COURSE_KEY_STR,
            ora_usage_key_str=ORA_USAGE_KEY_STR, ora_name='Updated Name',
            submission_uuid=SUBMISSION_UUID, submission_time_iso=SUBMISSION_TIME_ISO,
            content_url=CONTENT_URL,
        )
        self.assertEqual(ORAReminder.objects.filter(submission_uuid=SUBMISSION_UUID).count(), 1)
        self.assertEqual(ORAReminder.objects.get(submission_uuid=SUBMISSION_UUID).ora_name, 'Updated Name')

    def test_caches_step_due_dates(self):
        """Step-level due dates passed by caller are stored on the row."""
        from openassessment.xblock.utils.ora_reminders import create_ora_reminder

        peer_due = datetime(2026, 5, 1, tzinfo=timezone.utc)
        self_due = datetime(2026, 6, 1, tzinfo=timezone.utc)

        create_ora_reminder(
            user_id=self.user.id, course_key_str=COURSE_KEY_STR,
            ora_usage_key_str=ORA_USAGE_KEY_STR, ora_name=ORA_NAME,
            submission_uuid=SUBMISSION_UUID, submission_time_iso=SUBMISSION_TIME_ISO,
            content_url=CONTENT_URL,
            peer_assessment_due=peer_due,
            self_assessment_due=self_due,
        )
        reminder = ORAReminder.objects.get(submission_uuid=SUBMISSION_UUID)
        self.assertEqual(reminder.peer_assessment_due, peer_due)
        self.assertEqual(reminder.self_assessment_due, self_due)

    def test_caches_course_end_date(self):
        """Course end date passed by caller is stored on the row."""
        from openassessment.xblock.utils.ora_reminders import create_ora_reminder

        end_dt = datetime(2026, 8, 1, tzinfo=timezone.utc)
        create_ora_reminder(
            user_id=self.user.id, course_key_str=COURSE_KEY_STR,
            ora_usage_key_str=ORA_USAGE_KEY_STR, ora_name=ORA_NAME,
            submission_uuid=SUBMISSION_UUID, submission_time_iso=SUBMISSION_TIME_ISO,
            content_url=CONTENT_URL, course_end_date=end_dt,
        )
        reminder = ORAReminder.objects.get(submission_uuid=SUBMISSION_UUID)
        self.assertEqual(reminder.course_end_date, end_dt)

    @override_settings(ENABLE_ORA_REMINDERS=False)
    def test_skips_when_feature_disabled(self):
        """When ENABLE_ORA_REMINDERS is False, no row should be created."""
        from openassessment.xblock.utils.ora_reminders import create_ora_reminder

        create_ora_reminder(
            user_id=self.user.id, course_key_str=COURSE_KEY_STR,
            ora_usage_key_str=ORA_USAGE_KEY_STR, ora_name=ORA_NAME,
            submission_uuid=SUBMISSION_UUID, submission_time_iso=SUBMISSION_TIME_ISO,
            content_url=CONTENT_URL,
        )
        self.assertFalse(ORAReminder.objects.filter(submission_uuid=SUBMISSION_UUID).exists())

    def test_db_error_does_not_propagate(self):
        """create_ora_reminder should swallow DB errors (logged, not raised)."""
        from openassessment.xblock.utils.ora_reminders import create_ora_reminder

        with patch('openassessment.workflow.models.ORAReminder.objects') as mock_mgr:
            mock_mgr.update_or_create.side_effect = Exception('DB error')
            create_ora_reminder(
                user_id=self.user.id, course_key_str=COURSE_KEY_STR,
                ora_usage_key_str=ORA_USAGE_KEY_STR, ora_name=ORA_NAME,
                submission_uuid=SUBMISSION_UUID, submission_time_iso=SUBMISSION_TIME_ISO,
                content_url=CONTENT_URL,
            )


# ---------------------------------------------------------------------------
# ensure_sweep_chain_running
# ---------------------------------------------------------------------------
@override_settings(ENABLE_ORA_REMINDERS=True)
class TestEnsureSweepChainRunning(CacheResetTest):
    """Tests for the ensure_sweep_chain_running function."""

    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders')
    def test_starts_chain_when_lock_not_held(self, mock_task):
        from openassessment.xblock.utils.ora_reminders import ensure_sweep_chain_running
        ensure_sweep_chain_running()
        mock_task.apply_async.assert_called_once()

    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders')
    def test_does_not_start_when_lock_held(self, mock_task):
        from django.core.cache import cache
        from openassessment.xblock.utils.ora_reminders import ensure_sweep_chain_running, SWEEP_LOCK_KEY
        cache.set(SWEEP_LOCK_KEY, 'running', timeout=9999)
        ensure_sweep_chain_running()
        mock_task.apply_async.assert_not_called()

    @override_settings(ENABLE_ORA_REMINDERS=False)
    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders')
    def test_skips_when_feature_disabled(self, mock_task):
        from openassessment.xblock.utils.ora_reminders import ensure_sweep_chain_running
        ensure_sweep_chain_running()
        mock_task.apply_async.assert_not_called()

    @override_settings(CELERY_ALWAYS_EAGER=True)
    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders')
    def test_skips_when_always_eager(self, mock_task):
        """Should not start chain when CELERY_ALWAYS_EAGER=True (avoids infinite recursion)."""
        from openassessment.xblock.utils.ora_reminders import ensure_sweep_chain_running
        ensure_sweep_chain_running()
        mock_task.apply_async.assert_not_called()

    @override_settings(ORA_REMINDER_SWEEP_INTERVAL_SECONDS=600)
    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders')
    def test_custom_sweep_interval(self, mock_task):
        from django.core.cache import cache
        from openassessment.xblock.utils.ora_reminders import (
            ensure_sweep_chain_running, SWEEP_LOCK_KEY,
        )
        ensure_sweep_chain_running()
        mock_task.apply_async.assert_called_once()
        self.assertIsNotNone(cache.get(SWEEP_LOCK_KEY))

    @override_settings(ORA_REMINDER_SWEEP_INTERVAL_SECONDS=600)
    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders')
    def test_clears_lock_when_heartbeat_stale(self, mock_task):
        """A stale heartbeat indicates a dead chain — lock should be cleared and chain restarted."""
        from django.core.cache import cache
        from openassessment.xblock.utils.ora_reminders import (
            ensure_sweep_chain_running, SWEEP_LOCK_KEY, SWEEP_HEARTBEAT_KEY,
        )
        # Simulate a lock held with a stale heartbeat (old enough to be considered dead)
        cache.set(SWEEP_LOCK_KEY, 'running', timeout=9999)
        stale_time = (NOW - timedelta(seconds=600 * 3)).isoformat()
        cache.set(SWEEP_HEARTBEAT_KEY, stale_time, timeout=9999)

        with patch('openassessment.xblock.utils.ora_reminders.datetime') as mock_dt:
            mock_dt.now.return_value = NOW
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            ensure_sweep_chain_running()

        mock_task.apply_async.assert_called_once()

    @override_settings(ORA_REMINDER_SWEEP_INTERVAL_SECONDS=600)
    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders')
    def test_does_not_clear_lock_when_heartbeat_fresh(self, mock_task):
        """A fresh heartbeat means the chain is alive — lock should NOT be cleared."""
        from django.core.cache import cache
        from openassessment.xblock.utils.ora_reminders import (
            ensure_sweep_chain_running, SWEEP_LOCK_KEY, SWEEP_HEARTBEAT_KEY,
        )
        cache.set(SWEEP_LOCK_KEY, 'running', timeout=9999)
        fresh_time = (NOW - timedelta(seconds=60)).isoformat()
        cache.set(SWEEP_HEARTBEAT_KEY, fresh_time, timeout=9999)

        with patch('openassessment.xblock.utils.ora_reminders.datetime') as mock_dt:
            mock_dt.now.return_value = NOW
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            ensure_sweep_chain_running()

        mock_task.apply_async.assert_not_called()


# ---------------------------------------------------------------------------
# _get_workflow_step
# ---------------------------------------------------------------------------
class TestGetWorkflowStep(CacheResetTest):
    """Tests for _get_workflow_step helper."""

    def test_returns_none_for_missing_workflow(self):
        from openassessment.xblock.utils.ora_reminders import _get_workflow_step
        self.assertIsNone(_get_workflow_step('nonexistent-uuid'))

    @patch('openassessment.workflow.models.AssessmentWorkflow.objects')
    def test_returns_status(self, mock_objects):
        from openassessment.xblock.utils.ora_reminders import _get_workflow_step
        mock_wf = MagicMock(status='peer')
        mock_objects.get.return_value = mock_wf
        self.assertEqual(_get_workflow_step('some-uuid'), 'peer')


# ---------------------------------------------------------------------------
# _send_reminder_notification
# ---------------------------------------------------------------------------
class TestSendReminderNotification(unittest.TestCase):
    """Tests for _send_reminder_notification helper."""

    @patch('openedx_events.learning.signals.USER_NOTIFICATION_REQUESTED.send_event')
    def test_sends_notification_with_correct_data(self, mock_send):
        from openassessment.xblock.utils.ora_reminders import _send_reminder_notification

        _send_reminder_notification(
            user_id=42,
            course_key_str=COURSE_KEY_STR,
            ora_name='Peer Essay',
            pending_step='peer reviews',
            content_url='http://example.com/ora',
        )

        mock_send.assert_called_once()
        nd = mock_send.call_args[1]['notification_data']
        self.assertEqual(nd.user_ids, [42])
        self.assertEqual(nd.context['ora_name'], 'Peer Essay')
        self.assertEqual(nd.context['pending_step'], 'peer reviews')
        self.assertEqual(nd.notification_type, 'ora_reminder')
        self.assertEqual(nd.app_name, 'grading')
        self.assertEqual(nd.content_url, 'http://example.com/ora')


# ---------------------------------------------------------------------------
# _check_peer_submissions_available
# ---------------------------------------------------------------------------
class TestCheckPeerSubmissionsAvailable(unittest.TestCase):

    @patch('openassessment.assessment.api.peer.get_submission_to_assess')
    def test_returns_true_when_submission_available(self, mock_get):
        from openassessment.xblock.utils.ora_reminders import _check_peer_submissions_available
        mock_get.return_value = {'submission': 'data'}
        self.assertTrue(_check_peer_submissions_available('sub-uuid'))

    @patch('openassessment.assessment.api.peer.get_submission_to_assess')
    def test_returns_false_when_no_submission(self, mock_get):
        from openassessment.xblock.utils.ora_reminders import _check_peer_submissions_available
        mock_get.return_value = None
        self.assertFalse(_check_peer_submissions_available('sub-uuid'))

    @patch('openassessment.assessment.api.peer.get_submission_to_assess', side_effect=Exception('err'))
    def test_returns_true_on_error(self, _mock):
        from openassessment.xblock.utils.ora_reminders import _check_peer_submissions_available
        self.assertTrue(_check_peer_submissions_available('sub-uuid'))


# ---------------------------------------------------------------------------
# _deactivate
# ---------------------------------------------------------------------------
class TestDeactivate(CacheResetTest):

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='deactivate_user', password='pass')

    def test_sets_inactive_and_saves(self):
        from openassessment.xblock.utils.ora_reminders import _deactivate
        reminder = _make_reminder(self.user)
        self.assertTrue(reminder.is_active)
        _deactivate(reminder, 'test reason')
        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)


# ---------------------------------------------------------------------------
# _process_single_reminder
# ---------------------------------------------------------------------------
@override_settings(
    ORA_REMINDER_INITIAL_DELAY_HOURS=INITIAL_DELAY,
    ORA_REMINDER_INTERVAL_HOURS=INTERVAL,
    ORA_REMINDER_MAX_COUNT=MAX_COUNT,
    ORA_REMINDER_CHECK_AGAIN_HOURS=12,
)
class TestProcessSingleReminder(CacheResetTest):
    """Tests for _process_single_reminder."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='reminder_user', password='pass')

    # --- Happy paths ---

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_sends_reminder_and_advances_schedule(self, _step, _avail, mock_send):
        """Happy path: sends notification and advances next_reminder_at by INTERVAL."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)
        _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertTrue(reminder.is_active)
        self.assertEqual(reminder.next_reminder_at, NOW + timedelta(hours=INTERVAL))
        mock_send.assert_called_once()

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='self')
    def test_self_step_sends_reminder(self, _step, _avail, mock_send):
        """Self-assessment step triggers a reminder with the correct pending_step label."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)
        _process_single_reminder(reminder, NOW)

        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args[1]['pending_step'], 'self review')

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='self')
    def test_self_step_skips_peer_availability_check(self, _step, mock_send):
        """Self step must NOT check peer availability — it is irrelevant."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)
        with patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available') as mock_avail:
            _process_single_reminder(reminder, NOW)
            mock_avail.assert_not_called()
        mock_send.assert_called_once()

    # --- Time-based termination (spec §3) ---

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_deactivates_when_window_elapsed(self, _step, mock_send):
        """No notification when now >= submission_time + Z + X*Y."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        # now = exactly at the window boundary
        at_cutoff = SUBMISSION_TIME + timedelta(hours=WINDOW)
        reminder = _make_reminder(self.user, next_reminder_at=at_cutoff)
        _process_single_reminder(reminder, at_cutoff)

        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_final_reminder_deactivates_after_send(self, _step, _avail, mock_send):
        """When next_at after sending would exceed the window, row is deactivated."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        # NOW is one interval before the window end, so next_at = NOW + INTERVAL = window end
        # which triggers deactivation.
        at_last = SUBMISSION_TIME + timedelta(hours=WINDOW - INTERVAL)
        reminder = _make_reminder(self.user, next_reminder_at=at_last)
        _process_single_reminder(reminder, at_last)

        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        self.assertIsNone(reminder.next_reminder_at)
        mock_send.assert_called_once()

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_sends_all_x_reminders_then_stops(self, _step, _avail, mock_send):
        """Exactly MAX_COUNT reminders are sent across the full window, then deactivated."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user, next_reminder_at=SUBMISSION_TIME)
        send_count = 0
        now = SUBMISSION_TIME

        for _ in range(MAX_COUNT + 1):  # one extra iteration to confirm deactivation
            reminder.refresh_from_db()
            if not reminder.is_active:
                break
            _process_single_reminder(reminder, now)
            send_count += 1
            now = now + timedelta(hours=INTERVAL)

        self.assertEqual(mock_send.call_count, MAX_COUNT)
        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)

    # --- Step-level due dates ---

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_deactivates_when_peer_step_due_passed(self, _step, mock_send):
        """Deactivate without sending if peer_assessment_due has passed."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        past_peer_due = NOW - timedelta(hours=1)
        reminder = _make_reminder(self.user, peer_assessment_due=past_peer_due)
        _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='self')
    def test_deactivates_when_self_step_due_passed(self, _step, mock_send):
        """Deactivate without sending if self_assessment_due has passed."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        past_self_due = NOW - timedelta(hours=1)
        reminder = _make_reminder(self.user, self_assessment_due=past_self_due)
        _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_future_peer_due_does_not_block_reminder(self, _step, _avail, mock_send):
        """A future peer_assessment_due should not block sending."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        future_due = NOW + timedelta(days=10)
        reminder = _make_reminder(self.user, peer_assessment_due=future_due)
        _process_single_reminder(reminder, NOW)
        mock_send.assert_called_once()

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_peer_due_does_not_affect_self_step(self, _step, _avail, mock_send):
        """Expired peer_assessment_due should NOT deactivate a reminder on the self step."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        # Override step to 'self' but pass an expired peer due — should still send.
        with patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='self'):
            past_peer_due = NOW - timedelta(hours=1)
            reminder = _make_reminder(self.user, peer_assessment_due=past_peer_due)
            _process_single_reminder(reminder, NOW)
        mock_send.assert_called_once()

    # --- ORA due date fallback ---

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_deactivates_when_ora_due_date_passed_and_no_step_due(self, _step, mock_send):
        """When step-level due dates are None, ora_due_date should act as fallback guard."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        past_ora_due = NOW - timedelta(hours=1)
        reminder = _make_reminder(
            self.user,
            peer_assessment_due=None,
            self_assessment_due=None,
            ora_due_date=past_ora_due,
        )
        _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_step_due_takes_precedence_over_ora_due(self, _step, _avail, mock_send):
        """Step-level due date should be used when present, even if ora_due_date is also set."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        # ORA due date passed, but step due date is in the future — should still send.
        reminder = _make_reminder(
            self.user,
            peer_assessment_due=NOW + timedelta(days=5),
            ora_due_date=NOW - timedelta(hours=1),
        )
        _process_single_reminder(reminder, NOW)
        mock_send.assert_called_once()

    # --- Course end date ---

    def test_deactivates_when_course_end_date_passed(self):
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        with patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer'), \
             patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            reminder = _make_reminder(self.user, course_end_date=NOW - timedelta(days=1))
            _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    # --- Workflow step guards ---

    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='done')
    def test_deactivates_when_workflow_not_peer_or_self(self, _step):
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)
        with patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            _process_single_reminder(reminder, NOW)
        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='training')
    def test_deactivates_when_workflow_is_training(self, _step):
        """training step (e.g. student-training first ORA) should deactivate."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)
        with patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            _process_single_reminder(reminder, NOW)
        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='waiting')
    def test_deactivates_when_workflow_is_waiting(self, _step):
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)
        with patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            _process_single_reminder(reminder, NOW)
        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value=None)
    def test_deactivates_when_workflow_missing(self, _step):
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)
        with patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            _process_single_reminder(reminder, NOW)
        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    # --- Peer availability deferral ---

    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=False)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_defers_when_no_peer_submissions(self, _step, _avail):
        """Should postpone (not deactivate) when peer step has no available submissions."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)
        with patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertTrue(reminder.is_active)
        self.assertEqual(reminder.next_reminder_at, NOW + timedelta(hours=12))
        mock_send.assert_not_called()

    @override_settings(ORA_REMINDER_INTERVAL_HOURS=24)
    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_custom_interval_hours(self, _step, _avail, mock_send):
        """next_reminder_at should advance by the custom interval."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)
        _process_single_reminder(reminder, NOW)
        reminder.refresh_from_db()
        self.assertEqual(reminder.next_reminder_at, NOW + timedelta(hours=24))


# ---------------------------------------------------------------------------
# sweep_ora_reminders (Celery task)
# ---------------------------------------------------------------------------
@override_settings(
    ENABLE_ORA_REMINDERS=True,
    CELERY_ALWAYS_EAGER=False,
    ORA_REMINDER_INITIAL_DELAY_HOURS=INITIAL_DELAY,
    ORA_REMINDER_INTERVAL_HOURS=INTERVAL,
    ORA_REMINDER_MAX_COUNT=MAX_COUNT,
)
class TestSweepOraReminders(CacheResetTest):
    """Tests for the sweep_ora_reminders Celery task."""

    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders.apply_async')
    @patch('openassessment.xblock.utils.ora_reminders._do_sweep')
    def test_runs_sweep_and_rechains(self, mock_sweep, mock_async):
        from openassessment.xblock.utils.ora_reminders import sweep_ora_reminders
        sweep_ora_reminders()
        mock_sweep.assert_called_once()
        mock_async.assert_called_once()

    @override_settings(ENABLE_ORA_REMINDERS=False)
    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders.apply_async')
    @patch('openassessment.xblock.utils.ora_reminders._do_sweep')
    def test_stops_rechain_when_disabled(self, mock_sweep, mock_async):
        from openassessment.xblock.utils.ora_reminders import sweep_ora_reminders
        sweep_ora_reminders()
        mock_sweep.assert_not_called()
        mock_async.assert_not_called()

    @override_settings(CELERY_ALWAYS_EAGER=True)
    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders.apply_async')
    @patch('openassessment.xblock.utils.ora_reminders._do_sweep')
    def test_no_rechain_when_always_eager(self, mock_sweep, mock_async):
        """should_rechain=False when CELERY_ALWAYS_EAGER — avoids infinite recursion."""
        from openassessment.xblock.utils.ora_reminders import sweep_ora_reminders
        sweep_ora_reminders()
        mock_sweep.assert_called_once()   # sweep still runs
        mock_async.assert_not_called()   # but does NOT re-chain


# ---------------------------------------------------------------------------
# _do_sweep integration
# ---------------------------------------------------------------------------
@override_settings(
    ENABLE_ORA_REMINDERS=True,
    ORA_REMINDER_INITIAL_DELAY_HOURS=INITIAL_DELAY,
    ORA_REMINDER_INTERVAL_HOURS=INTERVAL,
    ORA_REMINDER_MAX_COUNT=MAX_COUNT,
    ORA_REMINDER_SWEEP_BATCH_SIZE=100,
)
class TestDoSweep(CacheResetTest):

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='sweep_user', password='pass')

    @patch('openassessment.xblock.utils.ora_reminders._process_single_reminder')
    def test_processes_due_reminders_only(self, mock_process):
        from openassessment.xblock.utils.ora_reminders import _do_sweep

        due = _make_reminder(self.user, next_reminder_at=NOW - timedelta(hours=1))
        _make_reminder(
            self.user,
            submission_uuid='future-sub',
            next_reminder_at=NOW + timedelta(hours=10),
        )

        _do_sweep.__wrapped__(NOW) if hasattr(_do_sweep, '__wrapped__') else None
        with patch('openassessment.xblock.utils.ora_reminders.datetime') as mock_dt:
            mock_dt.now.return_value = NOW
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            from openassessment.xblock.utils.ora_reminders import _do_sweep as real_sweep
            real_sweep()

        # Only the due reminder should be processed
        processed_ids = [call.args[0].id for call in mock_process.call_args_list]
        self.assertIn(due.id, processed_ids)
        self.assertEqual(len(processed_ids), 1)
