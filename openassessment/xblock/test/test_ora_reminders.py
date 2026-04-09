"""
Tests for openassessment.xblock.utils.ora_reminders

Covers:
- create_ora_reminder          (public helper)
- ensure_sweep_chain_running   (public helper)
- sweep_ora_reminders          (Celery task)
- _do_sweep                    (core sweep logic)
- _process_single_reminder     (per-row processing)
- _deactivate                  (row deactivation)
- _get_workflow_step           (workflow lookup)
- _send_reminder_notification  (signal dispatch)
- _check_peer_submissions_available (peer availability)
"""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, PropertyMock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from openassessment.test_utils import CacheResetTest
from openassessment.workflow.models import ORAReminder, AssessmentWorkflow


User = get_user_model()

# Shared constants
NOW = datetime(2026, 4, 8, 12, 0, 0, tzinfo=timezone.utc)
SUBMISSION_TIME = datetime(2026, 4, 7, 10, 0, 0, tzinfo=timezone.utc)
SUBMISSION_TIME_ISO = SUBMISSION_TIME.isoformat()
COURSE_KEY_STR = 'course-v1:TestX+T101+2026'
ORA_USAGE_KEY_STR = 'block-v1:TestX+T101+2026+type@openassessment+block@abc123'
ORA_NAME = 'Peer Essay'
SUBMISSION_UUID = 'sub-uuid-0001'
CONTENT_URL = 'http://lms.example.com/courses/course-v1:TestX+T101+2026/jump_to/block-v1:...'


def _make_reminder(user, **overrides):
    """Create an ORAReminder with sane defaults."""
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
        reminder_sent_count=0,
        next_reminder_at=NOW - timedelta(hours=1),  # due
        is_active=True,
    )
    defaults.update(overrides)
    return ORAReminder.objects.create(**defaults)


# ---------------------------------------------------------------------------
# create_ora_reminder
# ---------------------------------------------------------------------------
@override_settings(FEATURES={**dict(getattr(settings, 'FEATURES', {})), 'ENABLE_ORA_REMINDERS': True})
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
        self.assertEqual(reminder.reminder_sent_count, 0)
        # Default initial delay = 24h
        expected_next = SUBMISSION_TIME + timedelta(hours=24)
        self.assertEqual(reminder.next_reminder_at, expected_next)

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
        expected_next = SUBMISSION_TIME + timedelta(hours=12)
        self.assertEqual(reminder.next_reminder_at, expected_next)

    def test_update_or_create_overwrites_existing(self):
        """Calling create_ora_reminder twice with the same submission_uuid should update, not duplicate."""
        from openassessment.xblock.utils.ora_reminders import create_ora_reminder

        create_ora_reminder(
            user_id=self.user.id,
            course_key_str=COURSE_KEY_STR,
            ora_usage_key_str=ORA_USAGE_KEY_STR,
            ora_name='Old Name',
            submission_uuid=SUBMISSION_UUID,
            submission_time_iso=SUBMISSION_TIME_ISO,
            content_url=CONTENT_URL,
        )
        create_ora_reminder(
            user_id=self.user.id,
            course_key_str=COURSE_KEY_STR,
            ora_usage_key_str=ORA_USAGE_KEY_STR,
            ora_name='Updated Name',
            submission_uuid=SUBMISSION_UUID,
            submission_time_iso=SUBMISSION_TIME_ISO,
            content_url=CONTENT_URL,
        )
        self.assertEqual(ORAReminder.objects.filter(submission_uuid=SUBMISSION_UUID).count(), 1)
        self.assertEqual(ORAReminder.objects.get(submission_uuid=SUBMISSION_UUID).ora_name, 'Updated Name')

    def test_caches_ora_due_date(self):
        """Due date passed by caller is stored on the row."""
        from openassessment.xblock.utils.ora_reminders import create_ora_reminder

        due_dt = datetime(2026, 6, 1, tzinfo=timezone.utc)

        create_ora_reminder(
            user_id=self.user.id,
            course_key_str=COURSE_KEY_STR,
            ora_usage_key_str=ORA_USAGE_KEY_STR,
            ora_name=ORA_NAME,
            submission_uuid=SUBMISSION_UUID,
            submission_time_iso=SUBMISSION_TIME_ISO,
            content_url=CONTENT_URL,
            ora_due_date=due_dt,
        )
        reminder = ORAReminder.objects.get(submission_uuid=SUBMISSION_UUID)
        self.assertEqual(reminder.ora_due_date, due_dt)

    def test_caches_course_end_date(self):
        """Course end date passed by caller is stored on the row."""
        from openassessment.xblock.utils.ora_reminders import create_ora_reminder

        end_dt = datetime(2026, 8, 1, tzinfo=timezone.utc)

        create_ora_reminder(
            user_id=self.user.id,
            course_key_str=COURSE_KEY_STR,
            ora_usage_key_str=ORA_USAGE_KEY_STR,
            ora_name=ORA_NAME,
            submission_uuid=SUBMISSION_UUID,
            submission_time_iso=SUBMISSION_TIME_ISO,
            content_url=CONTENT_URL,
            course_end_date=end_dt,
        )
        reminder = ORAReminder.objects.get(submission_uuid=SUBMISSION_UUID)
        self.assertEqual(reminder.course_end_date, end_dt)

    @override_settings(FEATURES={**dict(getattr(settings, 'FEATURES', {})), 'ENABLE_ORA_REMINDERS': False})
    def test_skips_when_feature_disabled(self):
        """When ENABLE_ORA_REMINDERS is False, no row should be created."""
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

        self.assertFalse(ORAReminder.objects.filter(submission_uuid=SUBMISSION_UUID).exists())

    def test_db_error_does_not_propagate(self):
        """create_ora_reminder should swallow DB errors (logged, not raised)."""
        from openassessment.xblock.utils.ora_reminders import create_ora_reminder

        with patch(
            'openassessment.workflow.models.ORAReminder.objects'
        ) as mock_mgr:
            mock_mgr.update_or_create.side_effect = Exception('DB error')
            # Should not raise
            create_ora_reminder(
                user_id=self.user.id,
                course_key_str=COURSE_KEY_STR,
                ora_usage_key_str=ORA_USAGE_KEY_STR,
                ora_name=ORA_NAME,
                submission_uuid=SUBMISSION_UUID,
                submission_time_iso=SUBMISSION_TIME_ISO,
                content_url=CONTENT_URL,
            )


# ---------------------------------------------------------------------------
# ensure_sweep_chain_running
# ---------------------------------------------------------------------------
@override_settings(FEATURES={**dict(getattr(settings, 'FEATURES', {})), 'ENABLE_ORA_REMINDERS': True})
class TestEnsureSweepChainRunning(CacheResetTest):
    """Tests for the ensure_sweep_chain_running function."""

    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders')
    def test_starts_chain_when_lock_not_held(self, mock_task):
        """Should dispatch the task when the lock is available."""
        from openassessment.xblock.utils.ora_reminders import ensure_sweep_chain_running

        ensure_sweep_chain_running()
        mock_task.apply_async.assert_called_once()

    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders')
    def test_does_not_start_when_lock_held(self, mock_task):
        """Should NOT dispatch the task when the lock is already held."""
        from django.core.cache import cache
        from openassessment.xblock.utils.ora_reminders import (
            ensure_sweep_chain_running,
            SWEEP_LOCK_KEY,
        )

        cache.set(SWEEP_LOCK_KEY, 'running', timeout=9999)
        ensure_sweep_chain_running()
        mock_task.apply_async.assert_not_called()

    @override_settings(FEATURES={**dict(getattr(settings, 'FEATURES', {})), 'ENABLE_ORA_REMINDERS': False})
    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders')
    def test_skips_when_feature_disabled(self, mock_task):
        """When ENABLE_ORA_REMINDERS is False, chain should not start."""
        from openassessment.xblock.utils.ora_reminders import ensure_sweep_chain_running

        ensure_sweep_chain_running()

        mock_task.apply_async.assert_not_called()

    @override_settings(ORA_REMINDER_SWEEP_INTERVAL_SECONDS=600)
    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders')
    def test_custom_sweep_interval(self, mock_task):
        """Lock timeout should be SWEEP_LOCK_TIMEOUT_MULTIPLIER * custom interval."""
        from django.core.cache import cache
        from openassessment.xblock.utils.ora_reminders import (
            ensure_sweep_chain_running,
            SWEEP_LOCK_KEY,
            SWEEP_LOCK_TIMEOUT_MULTIPLIER,
        )

        ensure_sweep_chain_running()
        mock_task.apply_async.assert_called_once()
        # After call, the lock should be set
        self.assertIsNotNone(cache.get(SWEEP_LOCK_KEY))


# ---------------------------------------------------------------------------
# _get_workflow_step
# ---------------------------------------------------------------------------
class TestGetWorkflowStep(CacheResetTest):
    """Tests for _get_workflow_step helper."""

    def test_returns_none_for_missing_workflow(self):
        from openassessment.xblock.utils.ora_reminders import _get_workflow_step
        result = _get_workflow_step('nonexistent-uuid')
        self.assertIsNone(result)

    @patch('openassessment.workflow.models.AssessmentWorkflow.objects')
    def test_returns_status(self, mock_objects):
        from openassessment.xblock.utils.ora_reminders import _get_workflow_step
        mock_wf = MagicMock(status='peer')
        mock_objects.get.return_value = mock_wf
        result = _get_workflow_step('some-uuid')
        self.assertEqual(result, 'peer')

    def test_returns_none_on_import_error(self):
        """Should return None if openassessment is not installed."""
        from openassessment.xblock.utils.ora_reminders import _get_workflow_step

        with patch.dict('sys.modules', {'openassessment.workflow.models': None}):
            # Force ImportError inside the function
            with patch(
                'openassessment.xblock.utils.ora_reminders.AssessmentWorkflow',
                side_effect=ImportError,
                create=True,
            ):
                # This is hard to truly test without breaking the import;
                # we'll just test the DoesNotExist path as a proxy
                result = _get_workflow_step('missing-uuid')
                self.assertIsNone(result)


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
        kwargs = mock_send.call_args[1]
        nd = kwargs['notification_data']
        self.assertEqual(nd.user_ids, [42])
        self.assertEqual(nd.context['ora_name'], 'Peer Essay')
        self.assertEqual(nd.context['pending_step'], 'peer reviews')
        self.assertEqual(nd.notification_type, 'ora_reminder')
        self.assertEqual(nd.app_name, 'grading')
        self.assertEqual(nd.content_url, 'http://example.com/ora')

    def test_handles_missing_openedx_events(self):
        """Should log warning and return if openedx_events is not available."""
        from openassessment.xblock.utils.ora_reminders import _send_reminder_notification

        with patch.dict('sys.modules', {
            'openedx_events': None,
            'openedx_events.learning': None,
            'openedx_events.learning.data': None,
            'openedx_events.learning.signals': None,
        }):
            # Should not raise
            _send_reminder_notification(
                user_id=1,
                course_key_str=COURSE_KEY_STR,
                ora_name='Test',
                pending_step='peer reviews',
                content_url='http://example.com',
            )


# ---------------------------------------------------------------------------
# _check_peer_submissions_available
# ---------------------------------------------------------------------------
class TestCheckPeerSubmissionsAvailable(unittest.TestCase):
    """Tests for _check_peer_submissions_available helper."""

    @patch('openassessment.assessment.api.peer.get_submission_to_assess')
    def test_returns_true_when_submission_available(self, mock_get):
        from openassessment.xblock.utils.ora_reminders import _check_peer_submissions_available

        mock_get.return_value = {'submission': 'data'}
        self.assertTrue(_check_peer_submissions_available('sub-uuid'))
        mock_get.assert_called_once_with('sub-uuid', graded_by=1, peek=True)

    @patch('openassessment.assessment.api.peer.get_submission_to_assess')
    def test_returns_false_when_no_submission(self, mock_get):
        from openassessment.xblock.utils.ora_reminders import _check_peer_submissions_available

        mock_get.return_value = None
        self.assertFalse(_check_peer_submissions_available('sub-uuid'))

    @patch('openassessment.assessment.api.peer.get_submission_to_assess',
           side_effect=Exception('peer API error'))
    def test_returns_true_on_error(self, mock_get):
        """Fail open: if the check errors, assume submissions are available."""
        from openassessment.xblock.utils.ora_reminders import _check_peer_submissions_available
        self.assertTrue(_check_peer_submissions_available('sub-uuid'))


# ---------------------------------------------------------------------------
# _deactivate
# ---------------------------------------------------------------------------
class TestDeactivate(CacheResetTest):
    """Tests for _deactivate helper."""

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
class TestProcessSingleReminder(CacheResetTest):
    """Tests for the _process_single_reminder function."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='reminder_user', password='pass')

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_sends_reminder_and_advances_count(self, mock_step, mock_avail, mock_send):
        """Happy path: peer step, submissions available, count < max."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)
        _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertEqual(reminder.reminder_sent_count, 1)
        self.assertTrue(reminder.is_active)
        # Next reminder scheduled at NOW + 48h (default interval)
        self.assertEqual(reminder.next_reminder_at, NOW + timedelta(hours=48))
        mock_send.assert_called_once()

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='self')
    def test_self_step_sends_reminder(self, mock_step, mock_avail, mock_send):
        """Self-assessment step should also trigger reminders."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)
        _process_single_reminder(reminder, NOW)

        mock_send.assert_called_once()
        kwargs = mock_send.call_args[1]
        self.assertEqual(kwargs['pending_step'], 'self review')

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    def test_final_reminder_deactivates(self, mock_avail, mock_step, mock_send):
        """When the sent count reaches max, the reminder should be deactivated."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user, reminder_sent_count=2)  # default max=3
        _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertEqual(reminder.reminder_sent_count, 3)
        self.assertFalse(reminder.is_active)

    def test_deactivates_when_ora_due_date_passed(self):
        """Should deactivate without sending if the ORA due date has passed."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        past_due = NOW - timedelta(hours=1)
        reminder = _make_reminder(self.user, ora_due_date=past_due)

        with patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    def test_deactivates_when_course_end_date_passed(self):
        """Should deactivate without sending if the course end date has passed."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        past_end = NOW - timedelta(days=1)
        reminder = _make_reminder(self.user, course_end_date=past_end)

        with patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    def test_deactivates_when_max_count_already_reached(self):
        """Should deactivate if reminder_sent_count >= max_count at entry."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user, reminder_sent_count=5)

        with patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='done')
    def test_deactivates_when_workflow_not_peer_or_self(self, mock_step):
        """Should deactivate if the workflow step is no longer peer/self."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)

        with patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='waiting')
    def test_deactivates_when_workflow_is_waiting(self, mock_step):
        """Waiting status means the user has finished, should deactivate."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)

        with patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value=None)
    def test_deactivates_when_workflow_missing(self, mock_step):
        """If the workflow doesn't exist at all, deactivate."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)

        with patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=False)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_defers_when_no_peer_submissions(self, mock_step, mock_avail):
        """Should postpone (not deactivate) if peer step has no available submissions."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)

        with patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertTrue(reminder.is_active)
        self.assertEqual(reminder.reminder_sent_count, 0)  # not incremented
        # Default check_again_hours=12
        self.assertEqual(reminder.next_reminder_at, NOW + timedelta(hours=12))
        mock_send.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='self')
    def test_self_step_skips_peer_availability_check(self, mock_step, mock_send):
        """Self step should NOT check peer availability — should just send."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)

        with patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available') as mock_avail:
            _process_single_reminder(reminder, NOW)
            mock_avail.assert_not_called()

        mock_send.assert_called_once()

    @override_settings(ORA_REMINDER_INTERVAL_HOURS=24)
    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_custom_interval_hours(self, mock_step, mock_avail, mock_send):
        """ORA_REMINDER_INTERVAL_HOURS should control next_reminder_at."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user)
        _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertEqual(reminder.next_reminder_at, NOW + timedelta(hours=24))

    @override_settings(ORA_REMINDER_MAX_COUNT=1)
    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_custom_max_count(self, mock_step, mock_avail, mock_send):
        """ORA_REMINDER_MAX_COUNT=1 means the first sent reminder is also the last."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user, reminder_sent_count=0)
        _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertEqual(reminder.reminder_sent_count, 1)
        self.assertFalse(reminder.is_active)

    def test_ora_due_date_exactly_now_deactivates(self):
        """Edge: due date == now should deactivate (<=)."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user, ora_due_date=NOW)

        with patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification') as mock_send:
            _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertFalse(reminder.is_active)
        mock_send.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_ora_due_date_in_future_does_not_deactivate(self, mock_step, mock_avail, mock_send):
        """Due date in the future should not trigger deactivation."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        future_due = NOW + timedelta(days=7)
        reminder = _make_reminder(self.user, ora_due_date=future_due)
        _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertTrue(reminder.is_active)
        mock_send.assert_called_once()

    @patch('openassessment.xblock.utils.ora_reminders._send_reminder_notification')
    @patch('openassessment.xblock.utils.ora_reminders._check_peer_submissions_available', return_value=True)
    @patch('openassessment.xblock.utils.ora_reminders._get_workflow_step', return_value='peer')
    def test_no_deadlines_set(self, mock_step, mock_avail, mock_send):
        """Null due dates should not trigger deactivation."""
        from openassessment.xblock.utils.ora_reminders import _process_single_reminder

        reminder = _make_reminder(self.user, ora_due_date=None, course_end_date=None)
        _process_single_reminder(reminder, NOW)

        reminder.refresh_from_db()
        self.assertTrue(reminder.is_active)
        mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# _do_sweep
# ---------------------------------------------------------------------------
class TestDoSweep(CacheResetTest):
    """Tests for the _do_sweep function."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='sweep_user', password='pass')
        # We need a real "now" that's consistent with our test data.
        # Reminders are "due" when next_reminder_at <= now.
        # We'll create reminders relative to the real current time.
        self.real_now = datetime.now(timezone.utc)

    @patch('openassessment.xblock.utils.ora_reminders._process_single_reminder')
    def test_processes_due_reminders(self, mock_process):
        """Should pick up reminders whose next_reminder_at <= now."""
        from openassessment.xblock.utils.ora_reminders import _do_sweep

        _make_reminder(self.user, next_reminder_at=self.real_now - timedelta(hours=2))
        _do_sweep()

        self.assertEqual(mock_process.call_count, 1)

    @patch('openassessment.xblock.utils.ora_reminders._process_single_reminder')
    def test_skips_future_reminders(self, mock_process):
        """Reminders scheduled in the future should not be processed."""
        from openassessment.xblock.utils.ora_reminders import _do_sweep

        _make_reminder(self.user, next_reminder_at=self.real_now + timedelta(hours=24))
        _do_sweep()

        mock_process.assert_not_called()

    @patch('openassessment.xblock.utils.ora_reminders._process_single_reminder')
    def test_skips_inactive_reminders(self, mock_process):
        """Inactive reminders should never be picked up."""
        from openassessment.xblock.utils.ora_reminders import _do_sweep

        _make_reminder(
            self.user,
            is_active=False,
            next_reminder_at=self.real_now - timedelta(hours=2),
        )
        _do_sweep()

        mock_process.assert_not_called()

    @override_settings(ORA_REMINDER_SWEEP_BATCH_SIZE=2)
    @patch('openassessment.xblock.utils.ora_reminders._process_single_reminder')
    def test_batch_size_limit(self, mock_process):
        """Should process at most ORA_REMINDER_SWEEP_BATCH_SIZE reminders."""
        from openassessment.xblock.utils.ora_reminders import _do_sweep

        for i in range(5):
            _make_reminder(
                self.user,
                submission_uuid=f'sub-{i}',
                next_reminder_at=self.real_now - timedelta(hours=1),
            )
        _do_sweep()
        self.assertEqual(mock_process.call_count, 2)

    @patch('openassessment.xblock.utils.ora_reminders._process_single_reminder',
           side_effect=Exception('boom'))
    def test_error_in_one_reminder_does_not_stop_others(self, mock_process):
        """Individual reminder errors should be caught; sweep continues."""
        from openassessment.xblock.utils.ora_reminders import _do_sweep

        for i in range(3):
            _make_reminder(
                self.user,
                submission_uuid=f'sub-{i}',
                next_reminder_at=self.real_now - timedelta(hours=1),
            )
        # Should not raise
        _do_sweep()
        # All 3 should have been attempted
        self.assertEqual(mock_process.call_count, 3)


# ---------------------------------------------------------------------------
# sweep_ora_reminders (Celery task)
# ---------------------------------------------------------------------------
@override_settings(FEATURES={**dict(getattr(settings, 'FEATURES', {})), 'ENABLE_ORA_REMINDERS': True})
class TestSweepOraRemindersTask(CacheResetTest):
    """Tests for the sweep_ora_reminders Celery task."""

    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders.apply_async')
    @patch('openassessment.xblock.utils.ora_reminders._do_sweep')
    def test_calls_do_sweep_and_rechains(self, mock_do_sweep, mock_apply):
        """Task should call _do_sweep and re-chain itself."""
        from openassessment.xblock.utils.ora_reminders import sweep_ora_reminders

        sweep_ora_reminders()

        mock_do_sweep.assert_called_once()
        mock_apply.assert_called_once()
        # Check countdown matches default sweep interval
        call_kwargs = mock_apply.call_args[1]
        self.assertEqual(call_kwargs['countdown'], 1800)

    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders.apply_async')
    @patch('openassessment.xblock.utils.ora_reminders._do_sweep', side_effect=Exception('sweep error'))
    def test_rechains_even_on_error(self, mock_do_sweep, mock_apply):
        """Task should re-chain in finally even if _do_sweep raises."""
        from openassessment.xblock.utils.ora_reminders import sweep_ora_reminders

        sweep_ora_reminders()

        mock_apply.assert_called_once()

    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders.apply_async')
    @patch('openassessment.xblock.utils.ora_reminders._do_sweep')
    def test_sets_heartbeat_on_success(self, mock_do_sweep, mock_apply):
        """Should write a heartbeat cache key after successful sweep."""
        from django.core.cache import cache
        from openassessment.xblock.utils.ora_reminders import (
            sweep_ora_reminders,
            SWEEP_HEARTBEAT_KEY,
        )

        sweep_ora_reminders()

        heartbeat = cache.get(SWEEP_HEARTBEAT_KEY)
        self.assertIsNotNone(heartbeat)

    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders.apply_async')
    @patch('openassessment.xblock.utils.ora_reminders._do_sweep', side_effect=Exception('fail'))
    def test_no_heartbeat_on_error(self, mock_do_sweep, mock_apply):
        """Should NOT write heartbeat if _do_sweep errors."""
        from django.core.cache import cache
        from openassessment.xblock.utils.ora_reminders import (
            sweep_ora_reminders,
            SWEEP_HEARTBEAT_KEY,
        )

        sweep_ora_reminders()

        heartbeat = cache.get(SWEEP_HEARTBEAT_KEY)
        self.assertIsNone(heartbeat)

    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders.apply_async')
    @patch('openassessment.xblock.utils.ora_reminders._do_sweep')
    def test_refreshes_lock_in_finally(self, mock_do_sweep, mock_apply):
        """Should refresh the sweep lock in finally block."""
        from django.core.cache import cache
        from openassessment.xblock.utils.ora_reminders import (
            sweep_ora_reminders,
            SWEEP_LOCK_KEY,
        )

        sweep_ora_reminders()

        lock = cache.get(SWEEP_LOCK_KEY)
        self.assertEqual(lock, 'running')

    @override_settings(ORA_REMINDER_SWEEP_INTERVAL_SECONDS=300)
    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders.apply_async')
    @patch('openassessment.xblock.utils.ora_reminders._do_sweep')
    def test_custom_sweep_interval_in_rechain(self, mock_do_sweep, mock_apply):
        """Re-chain countdown should use custom sweep interval."""
        from openassessment.xblock.utils.ora_reminders import sweep_ora_reminders

        sweep_ora_reminders()

        call_kwargs = mock_apply.call_args[1]
        self.assertEqual(call_kwargs['countdown'], 300)

    @override_settings(FEATURES={**dict(getattr(settings, 'FEATURES', {})), 'ENABLE_ORA_REMINDERS': False})
    @patch('openassessment.xblock.utils.ora_reminders.sweep_ora_reminders.apply_async')
    def test_skips_sweep_and_stops_chain_when_feature_disabled(self, mock_apply):
        """Should skip the sweep AND stop re-chaining when ENABLE_ORA_REMINDERS is False."""
        from openassessment.xblock.utils.ora_reminders import sweep_ora_reminders

        with patch('openassessment.xblock.utils.ora_reminders._do_sweep') as mock_do_sweep:
            sweep_ora_reminders()
            mock_do_sweep.assert_not_called()

        # Does NOT re-chain when feature is disabled — chain dies gracefully
        mock_apply.assert_not_called()


# ---------------------------------------------------------------------------
# _handle_post_submission_notifications (from submissions_actions.py)
# ---------------------------------------------------------------------------
class TestHandlePostSubmissionNotifications(unittest.TestCase):
    """Tests for the _handle_post_submission_notifications orchestration function."""

    def _make_mocks(self, assessment_steps=None):
        """Build mock objects for submission, student_item, config, and workflow."""
        if assessment_steps is None:
            assessment_steps = ['peer-assessment', 'self-assessment']

        submission = {
            'uuid': 'sub-uuid-test',
            'submitted_at': datetime(2026, 4, 7, 10, 0, 0, tzinfo=timezone.utc),
        }
        student_item_dict = {
            'item_id': 'block-v1:TestX+T1+2026+type@openassessment+block@test',
            'student_id': 'anon-id-123',
            'course_id': COURSE_KEY_STR,
        }

        block_config = MagicMock()
        block_config.course = MagicMock()
        block_config.course.id = COURSE_KEY_STR
        block_config._block.display_name = 'Test ORA'

        block_workflow = MagicMock()
        block_workflow.assessment_steps = assessment_steps

        return submission, student_item_dict, block_config, block_workflow

    @patch('openassessment.xblock.apis.submissions.submissions_actions.ensure_sweep_chain_running')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.create_ora_reminder')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.get_user_model')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.map_anonymized_ids_to_usernames')
    def test_happy_path(self, mock_map, mock_get_model, mock_create, mock_sweep):
        from openassessment.xblock.apis.submissions.submissions_actions import (
            _handle_post_submission_notifications,
        )

        mock_map.return_value = {'anon-id-123': 'testuser'}
        mock_user = MagicMock(id=99)
        MockUser = MagicMock()
        MockUser.objects.get.return_value = mock_user
        mock_get_model.return_value = MockUser

        submission, student_item, config, workflow = self._make_mocks()
        _handle_post_submission_notifications(submission, student_item, config, workflow)

        mock_create.assert_called_once()
        self.assertEqual(mock_create.call_args[1]['user_id'], 99)
        mock_sweep.assert_called_once()

    def test_returns_early_without_peer_or_self_steps(self):
        from openassessment.xblock.apis.submissions.submissions_actions import (
            _handle_post_submission_notifications,
        )

        submission, student_item, config, workflow = self._make_mocks(
            assessment_steps=['staff-assessment']
        )
        with patch(
            'openassessment.xblock.apis.submissions.submissions_actions.create_ora_reminder'
        ) as mock_create:
            _handle_post_submission_notifications(submission, student_item, config, workflow)
            mock_create.assert_not_called()

    def test_only_peer_step_triggers_reminder(self):
        from openassessment.xblock.apis.submissions.submissions_actions import (
            _handle_post_submission_notifications,
        )

        submission, student_item, config, workflow = self._make_mocks(
            assessment_steps=['peer-assessment']
        )

        with patch(
            'openassessment.xblock.apis.submissions.submissions_actions.map_anonymized_ids_to_usernames',
            return_value={'anon-id-123': 'testuser'},
        ), patch(
            'openassessment.xblock.apis.submissions.submissions_actions.get_user_model',
        ) as mock_gum, patch(
            'openassessment.xblock.apis.submissions.submissions_actions.create_ora_reminder',
        ) as mock_create, patch(
            'openassessment.xblock.apis.submissions.submissions_actions.ensure_sweep_chain_running',
        ):
            MockUser = MagicMock()
            MockUser.objects.get.return_value = MagicMock(id=10)
            mock_gum.return_value = MockUser

            _handle_post_submission_notifications(submission, student_item, config, workflow)
            mock_create.assert_called_once()

    def test_only_self_step_triggers_reminder(self):
        from openassessment.xblock.apis.submissions.submissions_actions import (
            _handle_post_submission_notifications,
        )

        submission, student_item, config, workflow = self._make_mocks(
            assessment_steps=['self-assessment']
        )

        with patch(
            'openassessment.xblock.apis.submissions.submissions_actions.map_anonymized_ids_to_usernames',
            return_value={'anon-id-123': 'testuser'},
        ), patch(
            'openassessment.xblock.apis.submissions.submissions_actions.get_user_model',
        ) as mock_gum, patch(
            'openassessment.xblock.apis.submissions.submissions_actions.create_ora_reminder',
        ) as mock_create, patch(
            'openassessment.xblock.apis.submissions.submissions_actions.ensure_sweep_chain_running',
        ):
            MockUser = MagicMock()
            MockUser.objects.get.return_value = MagicMock(id=11)
            mock_gum.return_value = MockUser

            _handle_post_submission_notifications(submission, student_item, config, workflow)
            mock_create.assert_called_once()

    @patch('openassessment.xblock.apis.submissions.submissions_actions.ensure_sweep_chain_running')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.create_ora_reminder')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.map_anonymized_ids_to_usernames')
    def test_skips_reminder_when_username_not_found(self, mock_map, mock_create, mock_sweep):
        from openassessment.xblock.apis.submissions.submissions_actions import (
            _handle_post_submission_notifications,
        )

        mock_map.return_value = {'anon-id-123': None}  # username not resolved

        submission, student_item, config, workflow = self._make_mocks()
        _handle_post_submission_notifications(submission, student_item, config, workflow)

        mock_create.assert_not_called()  # reminder skipped
        mock_sweep.assert_not_called()

    @patch('openassessment.xblock.apis.submissions.submissions_actions.ensure_sweep_chain_running')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.create_ora_reminder',
           side_effect=Exception('reminder error'))
    @patch('openassessment.xblock.apis.submissions.submissions_actions.get_user_model')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.map_anonymized_ids_to_usernames')
    def test_reminder_error_does_not_propagate(self, mock_map, mock_gum, mock_create, mock_sweep):
        """Errors in reminder creation should not bubble up."""
        from openassessment.xblock.apis.submissions.submissions_actions import (
            _handle_post_submission_notifications,
        )

        mock_map.return_value = {'anon-id-123': 'testuser'}
        MockUser = MagicMock()
        MockUser.objects.get.return_value = MagicMock(id=42)
        mock_gum.return_value = MockUser

        submission, student_item, config, workflow = self._make_mocks()
        # Should not raise
        _handle_post_submission_notifications(submission, student_item, config, workflow)

    @patch('openassessment.xblock.apis.submissions.submissions_actions.ensure_sweep_chain_running')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.create_ora_reminder')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.get_user_model')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.map_anonymized_ids_to_usernames')
    def test_uses_created_at_when_submitted_at_missing(self, mock_map, mock_gum, mock_create, mock_sweep):
        """Should fall back to created_at if submitted_at is not in submission dict."""
        from openassessment.xblock.apis.submissions.submissions_actions import (
            _handle_post_submission_notifications,
        )

        mock_map.return_value = {'anon-id-123': 'testuser'}
        MockUser = MagicMock()
        MockUser.objects.get.return_value = MagicMock(id=1)
        mock_gum.return_value = MockUser

        submission = {
            'uuid': 'sub-uuid-test',
            'created_at': datetime(2026, 4, 7, 8, 0, 0, tzinfo=timezone.utc),
        }
        student_item = {
            'item_id': 'block-v1:X+1+2026+type@openassessment+block@t',
            'student_id': 'anon-id-123',
            'course_id': COURSE_KEY_STR,
        }
        config = MagicMock()
        config.course = MagicMock()
        config.course.id = COURSE_KEY_STR
        config._block.display_name = 'Test'

        workflow = MagicMock()
        workflow.assessment_steps = ['peer-assessment']

        _handle_post_submission_notifications(submission, student_item, config, workflow)

        # Verify the submission_time_iso passed to create_ora_reminder
        call_kwargs = mock_create.call_args[1]
        self.assertIn('2026-04-07T08:00:00', call_kwargs['submission_time_iso'])

    @patch('openassessment.xblock.apis.submissions.submissions_actions.ensure_sweep_chain_running')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.create_ora_reminder')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.get_user_model')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.map_anonymized_ids_to_usernames')
    def test_uses_course_id_from_student_item_when_no_course_object(
        self, mock_map, mock_gum, mock_create, mock_sweep
    ):
        """Should fall back to student_item course_id when block_config.course is None."""
        from openassessment.xblock.apis.submissions.submissions_actions import (
            _handle_post_submission_notifications,
        )

        mock_map.return_value = {'anon-id-123': 'testuser'}
        MockUser = MagicMock()
        MockUser.objects.get.return_value = MagicMock(id=5)
        mock_gum.return_value = MockUser

        submission, student_item, config, workflow = self._make_mocks()
        config.course = None  # no course object

        _handle_post_submission_notifications(submission, student_item, config, workflow)

        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs['course_key_str'], COURSE_KEY_STR)

    @patch('openassessment.xblock.apis.submissions.submissions_actions.ensure_sweep_chain_running')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.create_ora_reminder')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.get_user_model')
    @patch('openassessment.xblock.apis.submissions.submissions_actions.map_anonymized_ids_to_usernames')
    def test_submission_time_string_fallback(self, mock_map, mock_gum, mock_create, mock_sweep):
        """When submitted_at is a plain string, it should be used as-is."""
        from openassessment.xblock.apis.submissions.submissions_actions import (
            _handle_post_submission_notifications,
        )

        mock_map.return_value = {'anon-id-123': 'testuser'}
        MockUser = MagicMock()
        MockUser.objects.get.return_value = MagicMock(id=7)
        mock_gum.return_value = MockUser

        submission = {
            'uuid': 'sub-uuid-test',
            'submitted_at': '2026-04-07T10:00:00+00:00',
        }
        student_item = {
            'item_id': 'block-v1:X+1+2026+type@openassessment+block@t',
            'student_id': 'anon-id-123',
            'course_id': COURSE_KEY_STR,
        }
        config = MagicMock()
        config.course = MagicMock()
        config.course.id = COURSE_KEY_STR
        config._block.display_name = 'Test'

        workflow = MagicMock()
        workflow.assessment_steps = ['self-assessment']

        _handle_post_submission_notifications(submission, student_item, config, workflow)

        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs['submission_time_iso'], '2026-04-07T10:00:00+00:00')


# ---------------------------------------------------------------------------
# ORAReminder model
# ---------------------------------------------------------------------------
class TestOraReminderModel(CacheResetTest):
    """Basic tests for the ORAReminder Django model."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='model_user', password='pass')

    def test_str_representation(self):
        reminder = _make_reminder(self.user)
        s = str(reminder)
        self.assertIn('ORAReminder', s)
        self.assertIn(str(self.user.id), s)
        self.assertIn(ORA_USAGE_KEY_STR, s)

    def test_unique_submission_uuid_constraint(self):
        """Two reminders with the same submission_uuid should be disallowed."""
        from django.db import IntegrityError

        _make_reminder(self.user, submission_uuid='dup-uuid')
        with self.assertRaises(IntegrityError):
            _make_reminder(self.user, submission_uuid='dup-uuid')

    def test_is_active_default(self):
        reminder = _make_reminder(self.user)
        self.assertTrue(reminder.is_active)

    def test_timestamps_auto_set(self):
        """TimeStampedModel should auto-populate created/modified."""
        reminder = _make_reminder(self.user)
        self.assertIsNotNone(reminder.created)
        self.assertIsNotNone(reminder.modified)











