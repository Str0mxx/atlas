"""Time & Schedule Management sistemi testleri."""

import time

import pytest

from app.models.scheduler import (
    CalendarEvent,
    DeadlinePriority,
    DeadlineRecord,
    ReminderChannel,
    ReminderRecord,
    ScheduledTask,
    ScheduleStatus,
    ScheduleType,
    SchedulerSnapshot,
    TimeEntryType,
    WorkloadStatus,
)

from app.core.scheduler import (
    CalendarManager,
    DeadlineTracker,
    ReminderSystem,
    ScheduleOptimizer,
    SchedulerOrchestrator,
    TaskScheduler,
    TimeEstimator,
    TimeTracker,
    WorkloadBalancer,
)


# ── Model Testleri ──────────────────────────────────


class TestSchedulerModels:
    """Model testleri."""

    def test_schedule_type_enum(self):
        assert ScheduleType.ONE_TIME == "one_time"
        assert ScheduleType.RECURRING == "recurring"
        assert ScheduleType.CRON == "cron"

    def test_schedule_status_enum(self):
        assert ScheduleStatus.PENDING == "pending"
        assert ScheduleStatus.ACTIVE == "active"
        assert ScheduleStatus.OVERDUE == "overdue"

    def test_reminder_channel_enum(self):
        assert ReminderChannel.TELEGRAM == "telegram"
        assert ReminderChannel.EMAIL == "email"

    def test_deadline_priority_enum(self):
        assert DeadlinePriority.LOW == "low"
        assert DeadlinePriority.CRITICAL == "critical"

    def test_workload_status_enum(self):
        assert WorkloadStatus.IDLE == "idle"
        assert WorkloadStatus.OVERLOADED == "overloaded"

    def test_time_entry_type_enum(self):
        assert TimeEntryType.WORK == "work"
        assert TimeEntryType.MEETING == "meeting"

    def test_scheduled_task_defaults(self):
        task = ScheduledTask()
        assert task.task_id
        assert task.status == ScheduleStatus.PENDING
        assert task.priority == 5

    def test_calendar_event_defaults(self):
        event = CalendarEvent()
        assert event.event_id
        assert event.timezone == "UTC"
        assert event.tags == []

    def test_reminder_record_defaults(self):
        rec = ReminderRecord()
        assert rec.reminder_id
        assert rec.sent is False
        assert rec.snoozed == 0

    def test_deadline_record_defaults(self):
        rec = DeadlineRecord()
        assert rec.deadline_id
        assert rec.priority == DeadlinePriority.MEDIUM
        assert rec.extensions == 0

    def test_scheduler_snapshot_defaults(self):
        snap = SchedulerSnapshot()
        assert snap.total_tasks == 0
        assert snap.workload_status == WorkloadStatus.NORMAL
        assert snap.tracked_hours == 0.0


# ── TaskScheduler Testleri ──────────────────────────


class TestTaskScheduler:
    """TaskScheduler testleri."""

    def test_init(self):
        ts = TaskScheduler()
        assert ts.task_count == 0
        assert ts.active_count == 0

    def test_schedule_once(self):
        ts = TaskScheduler()
        task = ts.schedule_once("test-task", priority=3)
        assert task.name == "test-task"
        assert task.schedule_type == ScheduleType.ONE_TIME
        assert task.status == ScheduleStatus.PENDING
        assert task.priority == 3
        assert ts.task_count == 1

    def test_schedule_recurring(self):
        ts = TaskScheduler()
        task = ts.schedule_recurring("recurring", 60)
        assert task.schedule_type == ScheduleType.RECURRING
        assert task.status == ScheduleStatus.ACTIVE
        assert task.interval_seconds == 60

    def test_schedule_cron(self):
        ts = TaskScheduler()
        task = ts.schedule_cron("cron-task", "*/5 * * * *")
        assert task.schedule_type == ScheduleType.CRON
        assert task.cron_expr == "*/5 * * * *"

    def test_priority_clamped(self):
        ts = TaskScheduler()
        t1 = ts.schedule_once("low", priority=0)
        t2 = ts.schedule_once("high", priority=15)
        assert t1.priority == 1
        assert t2.priority == 10

    def test_pause_task(self):
        ts = TaskScheduler()
        task = ts.schedule_recurring("t", 60)
        assert ts.pause_task(task.task_id)
        assert task.status == ScheduleStatus.PAUSED

    def test_pause_completed_fails(self):
        ts = TaskScheduler()
        task = ts.schedule_once("t")
        ts.complete_task(task.task_id)
        assert not ts.pause_task(task.task_id)

    def test_resume_task(self):
        ts = TaskScheduler()
        task = ts.schedule_recurring("t", 60)
        ts.pause_task(task.task_id)
        assert ts.resume_task(task.task_id)
        assert task.status == ScheduleStatus.ACTIVE

    def test_resume_non_paused_fails(self):
        ts = TaskScheduler()
        task = ts.schedule_recurring("t", 60)
        assert not ts.resume_task(task.task_id)

    def test_cancel_task(self):
        ts = TaskScheduler()
        task = ts.schedule_once("t")
        assert ts.cancel_task(task.task_id)
        assert task.status == ScheduleStatus.CANCELLED

    def test_cancel_nonexistent(self):
        ts = TaskScheduler()
        assert not ts.cancel_task("nope")

    def test_complete_task(self):
        ts = TaskScheduler()
        task = ts.schedule_once("t")
        assert ts.complete_task(task.task_id)
        assert task.status == ScheduleStatus.COMPLETED
        assert ts.history_count == 1

    def test_get_pending(self):
        ts = TaskScheduler()
        ts.schedule_once("a", priority=5)
        ts.schedule_once("b", priority=1)
        pending = ts.get_pending()
        assert len(pending) == 2
        assert pending[0].priority <= pending[1].priority

    def test_get_by_priority(self):
        ts = TaskScheduler()
        ts.schedule_once("lo", priority=2)
        ts.schedule_once("hi", priority=8)
        result = ts.get_by_priority(min_priority=5)
        assert len(result) == 1
        assert result[0].name == "hi"

    def test_get_task(self):
        ts = TaskScheduler()
        task = ts.schedule_once("t")
        assert ts.get_task(task.task_id) is task
        assert ts.get_task("nope") is None

    def test_active_count(self):
        ts = TaskScheduler()
        ts.schedule_once("a")
        ts.schedule_recurring("b", 60)
        t3 = ts.schedule_once("c")
        ts.complete_task(t3.task_id)
        assert ts.active_count == 2


# ── CalendarManager Testleri ────────────────────────


class TestCalendarManager:
    """CalendarManager testleri."""

    def test_init(self):
        cm = CalendarManager()
        assert cm.event_count == 0
        assert cm.holiday_count == 0

    def test_add_event(self):
        cm = CalendarManager()
        event = cm.add_event("Meeting", tags=["work"])
        assert event.title == "Meeting"
        assert "work" in event.tags
        assert cm.event_count == 1

    def test_remove_event(self):
        cm = CalendarManager()
        event = cm.add_event("Meeting")
        assert cm.remove_event(event.event_id)
        assert cm.event_count == 0

    def test_remove_nonexistent(self):
        cm = CalendarManager()
        assert not cm.remove_event("nope")

    def test_get_event(self):
        cm = CalendarManager()
        event = cm.add_event("Meeting")
        assert cm.get_event(event.event_id) is event
        assert cm.get_event("nope") is None

    def test_get_events_in_range(self):
        from datetime import datetime, timedelta, timezone
        cm = CalendarManager()
        now = datetime.now(timezone.utc)
        cm.add_event("e1", start_time=now)
        cm.add_event(
            "e2",
            start_time=now + timedelta(hours=2),
        )
        cm.add_event(
            "e3",
            start_time=now + timedelta(days=5),
        )
        result = cm.get_events_in_range(
            now - timedelta(hours=1),
            now + timedelta(hours=3),
        )
        assert len(result) == 2

    def test_detect_conflicts(self):
        from datetime import datetime, timedelta, timezone
        cm = CalendarManager()
        now = datetime.now(timezone.utc)
        cm.add_event(
            "e1",
            start_time=now,
            end_time=now + timedelta(hours=2),
        )
        new_event = CalendarEvent(
            title="e2",
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=3),
        )
        conflicts = cm.detect_conflicts(new_event)
        assert len(conflicts) == 1

    def test_no_conflict_no_overlap(self):
        from datetime import datetime, timedelta, timezone
        cm = CalendarManager()
        now = datetime.now(timezone.utc)
        cm.add_event(
            "e1",
            start_time=now,
            end_time=now + timedelta(hours=1),
        )
        new_event = CalendarEvent(
            title="e2",
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=3),
        )
        assert len(cm.detect_conflicts(new_event)) == 0

    def test_check_availability(self):
        from datetime import datetime, timedelta, timezone
        cm = CalendarManager()
        now = datetime.now(timezone.utc)
        cm.add_event(
            "busy",
            start_time=now,
            end_time=now + timedelta(hours=2),
        )
        assert not cm.check_availability(
            now + timedelta(minutes=30),
            now + timedelta(hours=1),
        )
        assert cm.check_availability(
            now + timedelta(hours=3),
            now + timedelta(hours=4),
        )

    def test_holidays(self):
        cm = CalendarManager()
        cm.add_holiday("2026-01-01", "Yilbasi")
        assert cm.is_holiday("2026-01-01")
        assert not cm.is_holiday("2026-01-02")
        assert cm.holiday_count == 1

    def test_is_working_hours(self):
        cm = CalendarManager(
            workday_start="09:00",
            workday_end="18:00",
        )
        assert cm.is_working_hours(10)
        assert cm.is_working_hours(9)
        assert not cm.is_working_hours(8)
        assert not cm.is_working_hours(18)

    def test_get_events_by_tag(self):
        cm = CalendarManager()
        cm.add_event("e1", tags=["work"])
        cm.add_event("e2", tags=["personal"])
        cm.add_event("e3", tags=["work", "urgent"])
        result = cm.get_events_by_tag("work")
        assert len(result) == 2


# ── ReminderSystem Testleri ─────────────────────────


class TestReminderSystem:
    """ReminderSystem testleri."""

    def test_init(self):
        rs = ReminderSystem()
        assert rs.reminder_count == 0

    def test_create_reminder(self):
        rs = ReminderSystem()
        rem = rs.create_reminder("Test hatirlatma")
        assert rem.message == "Test hatirlatma"
        assert not rem.sent
        assert rs.reminder_count == 1

    def test_create_with_channel(self):
        rs = ReminderSystem()
        rem = rs.create_reminder(
            "Test", channel=ReminderChannel.TELEGRAM,
        )
        assert rem.channel == ReminderChannel.TELEGRAM

    def test_send_reminder(self):
        rs = ReminderSystem()
        rem = rs.create_reminder("Test")
        assert rs.send_reminder(rem.reminder_id)
        assert rem.sent
        assert rs.delivery_count == 1

    def test_send_already_sent(self):
        rs = ReminderSystem()
        rem = rs.create_reminder("Test")
        rs.send_reminder(rem.reminder_id)
        assert not rs.send_reminder(rem.reminder_id)

    def test_send_nonexistent(self):
        rs = ReminderSystem()
        assert not rs.send_reminder("nope")

    def test_snooze_reminder(self):
        rs = ReminderSystem()
        rem = rs.create_reminder("Test")
        rs.send_reminder(rem.reminder_id)
        assert rs.snooze_reminder(rem.reminder_id, 10)
        assert rem.snoozed == 1
        assert not rem.sent  # Reset edilmis

    def test_snooze_completed_fails(self):
        rs = ReminderSystem()
        rem = rs.create_reminder("Test")
        rs.complete_reminder(rem.reminder_id)
        assert not rs.snooze_reminder(rem.reminder_id)

    def test_complete_reminder(self):
        rs = ReminderSystem()
        rem = rs.create_reminder("Test")
        assert rs.complete_reminder(rem.reminder_id)
        assert rem.completed

    def test_complete_nonexistent(self):
        rs = ReminderSystem()
        assert not rs.complete_reminder("nope")

    def test_escalation_rule(self):
        rs = ReminderSystem()
        rule = rs.add_escalation_rule(
            3, ReminderChannel.TELEGRAM,
        )
        assert rule["max_snooze"] == 3

    def test_check_escalation_triggered(self):
        rs = ReminderSystem()
        rem = rs.create_reminder("Test")
        rs.add_escalation_rule(2, ReminderChannel.TELEGRAM)
        rs.snooze_reminder(rem.reminder_id)
        rs.snooze_reminder(rem.reminder_id)
        result = rs.check_escalation(rem.reminder_id)
        assert result is not None
        assert result["escalate_to"] == "telegram"

    def test_check_escalation_not_triggered(self):
        rs = ReminderSystem()
        rem = rs.create_reminder("Test")
        rs.add_escalation_rule(5, ReminderChannel.TELEGRAM)
        result = rs.check_escalation(rem.reminder_id)
        assert result is None

    def test_get_pending(self):
        rs = ReminderSystem()
        rs.create_reminder("a")
        r2 = rs.create_reminder("b")
        rs.send_reminder(r2.reminder_id)
        pending = rs.get_pending()
        assert len(pending) == 1

    def test_pending_count(self):
        rs = ReminderSystem()
        rs.create_reminder("a")
        rs.create_reminder("b")
        assert rs.pending_count == 2

    def test_get_reminder(self):
        rs = ReminderSystem()
        rem = rs.create_reminder("Test")
        assert rs.get_reminder(rem.reminder_id) is rem
        assert rs.get_reminder("nope") is None


# ── DeadlineTracker Testleri ────────────────────────


class TestDeadlineTracker:
    """DeadlineTracker testleri."""

    def test_init(self):
        dt = DeadlineTracker()
        assert dt.deadline_count == 0
        assert dt.overdue_count == 0

    def test_add_deadline(self):
        dt = DeadlineTracker()
        dl = dt.add_deadline(
            "task1",
            time.time() + 86400,
        )
        assert dl.task_name == "task1"
        assert dt.deadline_count == 1

    def test_add_with_priority(self):
        dt = DeadlineTracker()
        dl = dt.add_deadline(
            "task1",
            time.time() + 86400,
            priority=DeadlinePriority.CRITICAL,
        )
        assert dl.priority == DeadlinePriority.CRITICAL

    def test_check_deadlines_on_track(self):
        dt = DeadlineTracker(warning_hours=24)
        dt.add_deadline(
            "future",
            time.time() + 100000,
        )
        result = dt.check_deadlines()
        assert len(result["on_track"]) == 1
        assert len(result["overdue"]) == 0

    def test_check_deadlines_overdue(self):
        dt = DeadlineTracker()
        dt.add_deadline(
            "past",
            time.time() - 3600,
        )
        result = dt.check_deadlines()
        assert len(result["overdue"]) == 1
        assert dt.overdue_count == 1

    def test_check_deadlines_warning(self):
        dt = DeadlineTracker(warning_hours=48)
        dt.add_deadline(
            "soon",
            time.time() + 3600,  # 1 saat sonra
        )
        result = dt.check_deadlines()
        assert len(result["warning"]) == 1

    def test_complete_deadline(self):
        dt = DeadlineTracker()
        dl = dt.add_deadline("t", time.time() + 86400)
        assert dt.complete_deadline(dl.deadline_id)
        assert dl.completed

    def test_complete_nonexistent(self):
        dt = DeadlineTracker()
        assert not dt.complete_deadline("nope")

    def test_extend_deadline(self):
        dt = DeadlineTracker()
        dl = dt.add_deadline("t", time.time() + 3600)
        original_due = dl.due_at
        assert dt.extend_deadline(dl.deadline_id, 24)
        assert dl.due_at > original_due
        assert dl.extensions == 1
        assert dt.extension_count == 1

    def test_extend_completed_fails(self):
        dt = DeadlineTracker()
        dl = dt.add_deadline("t", time.time() + 3600)
        dt.complete_deadline(dl.deadline_id)
        assert not dt.extend_deadline(dl.deadline_id, 24)

    def test_adjust_priority(self):
        dt = DeadlineTracker()
        dl = dt.add_deadline("t", time.time() + 86400)
        assert dt.adjust_priority(
            dl.deadline_id, DeadlinePriority.CRITICAL,
        )
        assert dl.priority == DeadlinePriority.CRITICAL

    def test_adjust_nonexistent(self):
        dt = DeadlineTracker()
        assert not dt.adjust_priority(
            "nope", DeadlinePriority.HIGH,
        )

    def test_get_overdue(self):
        dt = DeadlineTracker()
        dt.add_deadline("past", time.time() - 3600)
        dt.add_deadline("future", time.time() + 86400)
        dt.check_deadlines()
        overdue = dt.get_overdue()
        assert len(overdue) == 1

    def test_get_by_priority(self):
        dt = DeadlineTracker()
        dt.add_deadline(
            "lo", time.time() + 86400,
            priority=DeadlinePriority.LOW,
        )
        dt.add_deadline(
            "hi", time.time() + 86400,
            priority=DeadlinePriority.HIGH,
        )
        result = dt.get_by_priority(DeadlinePriority.HIGH)
        assert len(result) == 1

    def test_get_deadline(self):
        dt = DeadlineTracker()
        dl = dt.add_deadline("t", time.time() + 86400)
        assert dt.get_deadline(dl.deadline_id) is dl
        assert dt.get_deadline("nope") is None


# ── TimeEstimator Testleri ──────────────────────────


class TestTimeEstimator:
    """TimeEstimator testleri."""

    def test_init(self):
        te = TimeEstimator()
        assert te.estimate_count == 0
        assert te.actual_count == 0

    def test_estimate_basic(self):
        te = TimeEstimator()
        est = te.estimate("t1", base_hours=2.0)
        assert est["base_hours"] == 2.0
        assert est["adjusted_hours"] > 0
        assert est["total_hours"] > est["adjusted_hours"]
        assert est["confidence"] == 0.3

    def test_estimate_with_history(self):
        te = TimeEstimator()
        te.record_actual("x1", 3.0, "dev")
        te.record_actual("x2", 4.0, "dev")
        te.record_actual("x3", 3.5, "dev")
        est = te.estimate("t1", "dev", base_hours=2.0)
        assert est["confidence"] == 0.3
        assert est["adjusted_hours"] != est["base_hours"]

    def test_record_actual_with_estimate(self):
        te = TimeEstimator()
        te.estimate("t1", base_hours=2.0)
        result = te.record_actual("t1", 2.5)
        assert result["actual"] == 2.5
        assert result["variance"] is not None
        assert result["accuracy"] is not None

    def test_record_actual_without_estimate(self):
        te = TimeEstimator()
        result = te.record_actual("t1", 3.0)
        assert result["estimated"] is None
        assert result["variance"] is None

    def test_confidence_interval(self):
        te = TimeEstimator()
        te.record_actual("a", 2.0, "dev")
        te.record_actual("b", 3.0, "dev")
        te.record_actual("c", 2.5, "dev")
        ci = te.get_confidence_interval("dev")
        assert ci["samples"] == 3
        assert ci["mean"] > 0
        assert ci["lower"] < ci["upper"]

    def test_confidence_interval_empty(self):
        te = TimeEstimator()
        ci = te.get_confidence_interval("empty")
        assert ci["samples"] == 0
        assert ci["mean"] == 0.0

    def test_confidence_interval_single(self):
        te = TimeEstimator()
        te.record_actual("a", 5.0, "single")
        ci = te.get_confidence_interval("single")
        assert ci["samples"] == 1
        assert ci["mean"] == 5.0

    def test_accuracy_stats(self):
        te = TimeEstimator()
        te.estimate("t1", base_hours=2.0)
        te.record_actual("t1", 2.2)
        stats = te.get_accuracy_stats()
        assert stats["avg_accuracy"] > 0
        assert stats["total_estimates"] == 1
        assert stats["total_actuals"] == 1

    def test_accuracy_stats_empty(self):
        te = TimeEstimator()
        stats = te.get_accuracy_stats()
        assert stats["avg_accuracy"] == 0.0

    def test_category_count(self):
        te = TimeEstimator()
        te.record_actual("a", 1.0, "dev")
        te.record_actual("b", 2.0, "ops")
        assert te.category_count == 2

    def test_buffer_clamped(self):
        te = TimeEstimator(default_buffer=5.0)
        assert te._default_buffer == 1.0
        te2 = TimeEstimator(default_buffer=-1.0)
        assert te2._default_buffer == 0.0


# ── WorkloadBalancer Testleri ───────────────────────


class TestWorkloadBalancer:
    """WorkloadBalancer testleri."""

    def test_init(self):
        wb = WorkloadBalancer()
        assert wb.agent_count == 0
        assert wb.assignment_count == 0

    def test_register_agent(self):
        wb = WorkloadBalancer()
        agent = wb.register_agent("a1", capacity=1.0)
        assert agent["agent_id"] == "a1"
        assert wb.agent_count == 1

    def test_assign_task_auto(self):
        wb = WorkloadBalancer()
        wb.register_agent("a1")
        result = wb.assign_task("t1", load=0.2)
        assert result["assigned"]
        assert result["agent_id"] == "a1"
        assert wb.assignment_count == 1

    def test_assign_task_specific(self):
        wb = WorkloadBalancer()
        wb.register_agent("a1")
        wb.register_agent("a2")
        result = wb.assign_task(
            "t1", load=0.2, agent_id="a2",
        )
        assert result["agent_id"] == "a2"

    def test_assign_no_agent(self):
        wb = WorkloadBalancer()
        result = wb.assign_task("t1", load=0.2)
        assert not result["assigned"]

    def test_release_task(self):
        wb = WorkloadBalancer()
        wb.register_agent("a1")
        wb.assign_task("t1", load=0.2)
        assert wb.release_task("t1")
        assert wb.assignment_count == 0

    def test_release_nonexistent(self):
        wb = WorkloadBalancer()
        assert not wb.release_task("nope")

    def test_get_status_idle(self):
        wb = WorkloadBalancer()
        wb.register_agent("a1")
        assert wb.get_status("a1") == WorkloadStatus.IDLE

    def test_get_status_light(self):
        wb = WorkloadBalancer()
        wb.register_agent("a1", capacity=1.0)
        wb.assign_task("t1", load=0.3, agent_id="a1")
        assert wb.get_status("a1") == WorkloadStatus.LIGHT

    def test_get_status_normal(self):
        wb = WorkloadBalancer()
        wb.register_agent("a1", capacity=1.0)
        wb.assign_task("t1", load=0.6, agent_id="a1")
        assert wb.get_status("a1") == WorkloadStatus.NORMAL

    def test_get_status_heavy(self):
        wb = WorkloadBalancer()
        wb.register_agent("a1", capacity=1.0)
        wb.assign_task("t1", load=0.9, agent_id="a1")
        assert wb.get_status("a1") == WorkloadStatus.HEAVY

    def test_get_status_overloaded(self):
        wb = WorkloadBalancer()
        wb.register_agent("a1", capacity=1.0)
        wb.assign_task("t1", load=0.96, agent_id="a1")
        assert wb.get_status("a1") == WorkloadStatus.OVERLOADED

    def test_get_status_nonexistent(self):
        wb = WorkloadBalancer()
        assert wb.get_status("nope") == WorkloadStatus.IDLE

    def test_load_distribution(self):
        wb = WorkloadBalancer()
        wb.register_agent("a1", capacity=1.0)
        wb.register_agent("a2", capacity=1.0)
        wb.assign_task("t1", load=0.5, agent_id="a1")
        dist = wb.get_load_distribution()
        assert dist["a1"] == 0.5
        assert dist["a2"] == 0.0

    def test_detect_overloaded(self):
        wb = WorkloadBalancer()
        wb.register_agent("a1", capacity=1.0)
        wb.register_agent("a2", capacity=1.0)
        wb.assign_task("t1", load=0.9, agent_id="a1")
        overloaded = wb.detect_overloaded()
        assert "a1" in overloaded
        assert "a2" not in overloaded

    def test_rebalance(self):
        wb = WorkloadBalancer()
        wb.register_agent("a1", capacity=1.0)
        wb.register_agent("a2", capacity=1.0)
        wb.assign_task("t1", load=0.8, agent_id="a1")
        result = wb.rebalance()
        assert result["rebalanced"]
        assert result["moves"] == 2

    def test_rebalance_empty(self):
        wb = WorkloadBalancer()
        result = wb.rebalance()
        assert not result["rebalanced"]

    def test_auto_assign_best_agent(self):
        wb = WorkloadBalancer()
        wb.register_agent("a1", capacity=1.0)
        wb.register_agent("a2", capacity=1.0)
        wb.assign_task("t1", load=0.7, agent_id="a1")
        result = wb.assign_task("t2", load=0.2)
        assert result["agent_id"] == "a2"


# ── TimeTracker Testleri ────────────────────────────


class TestTimeTracker:
    """TimeTracker testleri."""

    def test_init(self):
        tt = TimeTracker()
        assert tt.entry_count == 0
        assert tt.total_hours == 0.0
        assert not tt.is_tracking

    def test_start_stop_timer(self):
        tt = TimeTracker()
        tt.start_timer("t1")
        assert tt.is_tracking
        entry = tt.stop_timer()
        assert entry is not None
        assert entry["task_id"] == "t1"
        assert not tt.is_tracking
        assert tt.entry_count == 1

    def test_stop_without_start(self):
        tt = TimeTracker()
        assert tt.stop_timer() is None

    def test_start_stops_previous(self):
        tt = TimeTracker()
        tt.start_timer("t1")
        tt.start_timer("t2")
        assert tt.entry_count == 1  # t1 durduruldu
        assert tt.is_tracking

    def test_log_time(self):
        tt = TimeTracker()
        entry = tt.log_time("t1", 2.5)
        assert entry["duration_hours"] == 2.5
        assert entry["manual"]
        assert tt.entry_count == 1

    def test_log_with_type(self):
        tt = TimeTracker()
        entry = tt.log_time(
            "t1", 1.0, TimeEntryType.MEETING,
        )
        assert entry["type"] == "meeting"

    def test_set_billing_rate(self):
        tt = TimeTracker()
        tt.set_billing_rate("work", 50.0)
        assert tt._billing_rates["work"] == 50.0

    def test_calculate_billing(self):
        tt = TimeTracker()
        tt.set_billing_rate("work", 50.0)
        tt.log_time("t1", 2.0)
        result = tt.calculate_billing("t1")
        assert result["total_hours"] == 2.0
        assert result["total_cost"] == 100.0

    def test_calculate_billing_all(self):
        tt = TimeTracker()
        tt.set_billing_rate("work", 50.0)
        tt.log_time("t1", 2.0)
        tt.log_time("t2", 3.0)
        result = tt.calculate_billing()
        assert result["total_hours"] == 5.0

    def test_productivity_metrics(self):
        tt = TimeTracker()
        tt.log_time("t1", 4.0, TimeEntryType.WORK)
        tt.log_time("t2", 1.0, TimeEntryType.BREAK)
        metrics = tt.get_productivity_metrics()
        assert metrics["work_hours"] == 4.0
        assert metrics["break_hours"] == 1.0
        assert metrics["total_hours"] == 5.0
        assert metrics["work_ratio"] == 0.8

    def test_report_by_type(self):
        tt = TimeTracker()
        tt.log_time("t1", 2.0, TimeEntryType.WORK)
        tt.log_time("t2", 1.0, TimeEntryType.MEETING)
        report = tt.get_report("type")
        assert "work" in report["breakdown"]
        assert "meeting" in report["breakdown"]

    def test_report_by_task(self):
        tt = TimeTracker()
        tt.log_time("t1", 2.0)
        tt.log_time("t1", 3.0)
        tt.log_time("t2", 1.0)
        report = tt.get_report("task")
        assert report["breakdown"]["t1"] == 5.0
        assert report["breakdown"]["t2"] == 1.0

    def test_total_hours(self):
        tt = TimeTracker()
        tt.log_time("t1", 2.5)
        tt.log_time("t2", 1.5)
        assert tt.total_hours == 4.0


# ── ScheduleOptimizer Testleri ──────────────────────


class TestScheduleOptimizer:
    """ScheduleOptimizer testleri."""

    def test_init(self):
        so = ScheduleOptimizer()
        assert so.item_count == 0
        assert so.optimization_count == 0

    def test_add_item(self):
        so = ScheduleOptimizer()
        item = so.add_item("i1", 1000.0, 2.0)
        assert item["item_id"] == "i1"
        assert item["duration"] == 2.0
        assert so.item_count == 1

    def test_find_gaps(self):
        so = ScheduleOptimizer()
        so.add_item("i1", 1000.0, 1.0)  # 1000 - 4600
        so.add_item("i2", 10000.0, 1.0)  # 10000 - 13600
        gaps = so.find_gaps()
        assert len(gaps) == 1
        assert gaps[0]["gap_hours"] > 0

    def test_find_gaps_no_gap(self):
        so = ScheduleOptimizer()
        so.add_item("i1", 1000.0, 1.0)  # 1000 - 4600
        so.add_item("i2", 4600.0, 1.0)  # 4600 - 8200
        gaps = so.find_gaps()
        assert len(gaps) == 0

    def test_find_gaps_too_few(self):
        so = ScheduleOptimizer()
        so.add_item("i1", 1000.0, 1.0)
        assert len(so.find_gaps()) == 0

    def test_fill_gap(self):
        so = ScheduleOptimizer()
        so.add_item("i1", 1000.0, 1.0)
        so.add_item("i2", 10000.0, 1.0)
        assert so.fill_gap("i3", 0)
        assert so.item_count == 3

    def test_fill_gap_invalid(self):
        so = ScheduleOptimizer()
        assert not so.fill_gap("i1", 0)

    def test_batch_schedule(self):
        so = ScheduleOptimizer()
        items = [
            {"item_id": "a", "priority": 3, "duration": 1.0},
            {"item_id": "b", "priority": 1, "duration": 2.0},
        ]
        result = so.batch_schedule(items)
        assert len(result) == 2
        assert so.item_count == 2

    def test_level_resources(self):
        so = ScheduleOptimizer()
        so.add_item("i1", 1000.0, 2.0, priority=1)
        so.add_item("i2", 1000.0, 2.0, priority=2)
        so.add_item("i3", 1000.0, 2.0, priority=3)
        result = so.level_resources(max_concurrent=1)
        assert result["adjustments"] > 0

    def test_what_if(self):
        so = ScheduleOptimizer()
        so.add_item("i1", 1000.0, 1.0)
        so.add_item("i2", 5000.0, 1.0)
        result = so.what_if("remove_one", {
            "remove": ["i1"],
        })
        assert result["affected_items"] == 1
        assert result["impact"] in ("low", "medium", "high")
        assert so.scenario_count == 1

    def test_what_if_delay(self):
        so = ScheduleOptimizer()
        so.add_item("i1", 1000.0, 1.0)
        result = so.what_if("delay_all", {
            "delay_hours": 2,
        })
        assert result["impact"] == "high"

    def test_optimize(self):
        so = ScheduleOptimizer()
        so.add_item("i1", 1000.0, 1.0)
        so.add_item("i2", 10000.0, 1.0)
        result = so.optimize()
        assert result["total_items"] == 2
        assert so.optimization_count >= 1


# ── SchedulerOrchestrator Testleri ──────────────────


class TestSchedulerOrchestrator:
    """SchedulerOrchestrator testleri."""

    def test_init(self):
        so = SchedulerOrchestrator()
        assert so.scheduler.task_count == 0
        assert so.calendar.event_count == 0
        assert so.notification_count == 0

    def test_schedule_task(self):
        so = SchedulerOrchestrator()
        result = so.schedule_task(
            "test-gorev",
            priority=7,
            estimated_hours=3.0,
        )
        assert result["task_id"]
        assert result["name"] == "test-gorev"
        assert result["estimated_hours"] > 0
        assert result["reminder_id"]

    def test_schedule_task_with_deadline(self):
        so = SchedulerOrchestrator()
        result = so.schedule_task(
            "urgent",
            deadline_epoch=time.time() + 86400,
            priority=8,
        )
        assert result["deadline_id"] is not None

    def test_complete_task(self):
        so = SchedulerOrchestrator()
        r = so.schedule_task("t")
        result = so.complete_task(
            r["task_id"], actual_hours=2.0,
        )
        assert result["completed"]
        assert result["comparison"] is not None

    def test_complete_without_actual(self):
        so = SchedulerOrchestrator()
        r = so.schedule_task("t")
        result = so.complete_task(r["task_id"])
        assert result["completed"]
        assert result["comparison"] is None

    def test_check_all_deadlines(self):
        so = SchedulerOrchestrator()
        so.deadlines.add_deadline(
            "past", time.time() - 3600,
        )
        result = so.check_all_deadlines()
        assert len(result["overdue"]) == 1
        assert so.notification_count >= 1

    def test_get_analytics(self):
        so = SchedulerOrchestrator()
        so.schedule_task("t1")
        analytics = so.get_analytics()
        assert "productivity" in analytics
        assert "estimation_accuracy" in analytics
        assert analytics["total_scheduled"] == 1

    def test_preferences(self):
        so = SchedulerOrchestrator()
        so.set_preference("theme", "dark")
        assert so.get_preference("theme") == "dark"
        assert so.get_preference("missing", "def") == "def"
        assert so.preference_count == 1

    def test_get_snapshot(self):
        so = SchedulerOrchestrator()
        so.schedule_task("t1")
        snap = so.get_snapshot()
        assert isinstance(snap, SchedulerSnapshot)
        assert snap.total_tasks == 1
        assert snap.active_tasks == 1
        assert snap.pending_reminders >= 0

    def test_all_components_accessible(self):
        so = SchedulerOrchestrator()
        assert so.scheduler is not None
        assert so.calendar is not None
        assert so.reminders is not None
        assert so.deadlines is not None
        assert so.estimator is not None
        assert so.workload is not None
        assert so.tracker is not None
        assert so.optimizer is not None


# ── Entegrasyon Testleri ────────────────────────────


class TestSchedulerIntegration:
    """Entegrasyon testleri."""

    def test_full_task_lifecycle(self):
        so = SchedulerOrchestrator()
        # Zamanla
        r = so.schedule_task(
            "feature-dev",
            deadline_epoch=time.time() + 86400,
            estimated_hours=4.0,
            category="dev",
        )
        # Zaman takibi basla
        so.tracker.start_timer(r["task_id"])
        so.tracker.stop_timer()
        # Tamamla
        result = so.complete_task(
            r["task_id"],
            actual_hours=3.5,
            category="dev",
        )
        assert result["completed"]

    def test_workload_with_scheduling(self):
        so = SchedulerOrchestrator()
        so.workload.register_agent("agent1")
        so.workload.register_agent("agent2")
        so.workload.assign_task("t1", 0.5, "agent1")
        so.workload.assign_task("t2", 0.3, "agent2")
        overloaded = so.workload.detect_overloaded()
        assert len(overloaded) == 0

    def test_calendar_with_reminders(self):
        from datetime import datetime, timedelta, timezone
        so = SchedulerOrchestrator()
        now = datetime.now(timezone.utc)
        so.calendar.add_event(
            "Meeting",
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
        )
        so.reminders.create_reminder(
            "Meeting reminder",
            channel=ReminderChannel.TELEGRAM,
        )
        assert so.calendar.event_count == 1
        assert so.reminders.reminder_count == 1

    def test_deadline_with_estimation(self):
        so = SchedulerOrchestrator()
        est = so.estimator.estimate(
            "t1", "testing", base_hours=2.0,
        )
        so.deadlines.add_deadline(
            "testing-task",
            time.time() + est["total_hours"] * 3600,
        )
        so.estimator.record_actual("t1", 2.5, "testing")
        stats = so.estimator.get_accuracy_stats()
        assert stats["total_actuals"] == 1

    def test_optimizer_with_tasks(self):
        so = SchedulerOrchestrator()
        now = time.time()
        so.optimizer.add_item("task1", now, 1.0)
        so.optimizer.add_item(
            "task2", now + 7200, 1.0,
        )
        result = so.optimizer.optimize()
        assert result["total_items"] == 2
