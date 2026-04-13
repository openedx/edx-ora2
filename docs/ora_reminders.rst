ORA Reminder Notifications
==========================

ORA reminders send periodic nudges to learners who have submitted a response
but have not yet completed their required **peer** or **self** review steps.

A single platform-wide Celery sweeper task (``sweep_ora_reminders``) runs on a
configurable interval, finds due reminder rows in the database, and fires
``ora_reminder`` notifications through the edx-platform notification system.

Enabling
--------

Set ``ENABLE_ORA_REMINDERS`` to ``True`` in your Django settings:

.. code-block:: python

    ENABLE_ORA_REMINDERS = True

The notification type ``ora_reminder`` must also be registered in edx-platform's
``openedx.core.djangoapps.notifications.base_notification`` (already included
in edx-platform ≥ the version that ships this feature).

Configuration Settings
----------------------

All settings have sensible defaults and only need to be overridden when you
want non-default behaviour.

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Setting
     - Default
     - Description
   * - ``ORA_REMINDER_INITIAL_DELAY_HOURS``
     - ``24``
     - Hours after submission before the **first** reminder is sent. Gives
       learners time to complete reviews on their own before being nudged.
   * - ``ORA_REMINDER_INTERVAL_HOURS``
     - ``48``
     - Hours between consecutive reminders after the first one.
   * - ``ORA_REMINDER_MAX_COUNT``
     - ``3``
     - Maximum number of reminders sent per learner per ORA submission.
       Once this limit is reached the reminder row is deactivated.
   * - ``ORA_REMINDER_SWEEP_INTERVAL_SECONDS``
     - ``1800``
     - How often (in seconds) the sweeper re-schedules itself. Each run
       processes all rows whose ``next_reminder_at`` has passed.
   * - ``ORA_REMINDER_SWEEP_BATCH_SIZE``
     - ``1000``
     - Maximum rows processed per sweep cycle. If more rows are due they
       will be picked up on the next sweep.
   * - ``ORA_REMINDER_CHECK_AGAIN_HOURS``
     - ``12``
     - Hours to wait before re-checking when a peer-step reminder is due
       but no peer submissions are available for the learner to review yet.
       Prevents sending useless reminders to very early submitters.

Example override (in your LMS environment settings):

.. code-block:: python

    ORA_REMINDER_INITIAL_DELAY_HOURS = 48   # wait 2 days before first nudge
    ORA_REMINDER_INTERVAL_HOURS = 72        # then nudge every 3 days
    ORA_REMINDER_MAX_COUNT = 2              # send at most 2 reminders

How It Works
------------

1. When a learner submits an ORA that has peer or self review as a required
   step, an ``ORAReminder`` database row is created with
   ``next_reminder_at = submission_time + ORA_REMINDER_INITIAL_DELAY_HOURS``.

2. The ``sweep_ora_reminders`` Celery task runs every
   ``ORA_REMINDER_SWEEP_INTERVAL_SECONDS`` seconds (self-chaining pattern).
   On each run it queries all active rows whose ``next_reminder_at ≤ now``.

3. For each due row, guards are checked in order:

   - **Time window elapsed** — hours since submission exceed
     ``INITIAL_DELAY + MAX_COUNT × INTERVAL`` → row deactivated.
     This is equivalent to "all X reminders have been sent" without
     tracking a count.
   - **Step completed** — workflow is no longer on a peer/self step (learner
     finished their reviews) → row deactivated.
   - **Deadline passed** — the current step's due date (or ORA-level due
     date as fallback) or course end date has passed → row deactivated,
     no notification sent.
   - **No peers available** (peer step only) — no submissions exist yet for
     the learner to review → ``next_reminder_at`` advanced by
     ``ORA_REMINDER_CHECK_AGAIN_HOURS``, no notification sent.

4. If all guards pass, an ``ora_reminder`` notification is fired and
   ``next_reminder_at`` is advanced by ``ORA_REMINDER_INTERVAL_HOURS``.

Durability
----------

- Reminder state lives in MySQL (``ORAReminder`` table), not in Celery/Redis.
  A Redis restart loses only the pending sweep task, not the schedule data.
- The sweep task re-chains itself inside a ``finally`` block, so even an
  unhandled exception will not kill the chain permanently.
- A cache heartbeat (key ``ora_reminder_sweep_heartbeat``) is written after
  each successful sweep. An external health-check can detect a dead chain and
  restart it by calling ``ensure_sweep_chain_running()``.
- ``cache.add`` is used as a distributed lock to prevent duplicate chains
  from starting simultaneously.

Reminder Failures
-----------------

Errors during reminder creation (at submission time) are caught and logged
but **do not fail the submission**. The learner's submission is always
persisted even if the reminder row cannot be created.

Errors during a sweep cycle are caught per-row; a failure on one reminder
does not stop processing of the remaining rows.
