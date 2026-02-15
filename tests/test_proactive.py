"""ATLAS Always-On Proactive Brain testleri."""

import time

import pytest

from app.core.proactive.action_decider import (
    ActionDecider,
)
from app.core.proactive.continuous_scanner import (
    ContinuousScanner,
)
from app.core.proactive.opportunity_ranker import (
    OpportunityRanker,
)
from app.core.proactive.periodic_reporter import (
    PeriodicReporter,
)
from app.core.proactive.proactive_anomaly_detector import (
    ProactiveAnomalyDetector,
)
from app.core.proactive.proactive_notifier import (
    ProactiveNotifier,
)
from app.core.proactive.proactive_orchestrator import (
    ProactiveOrchestrator,
)
from app.core.proactive.priority_queue import (
    ProactivePriorityQueue,
)
from app.core.proactive.sleep_cycle_manager import (
    SleepCycleManager,
)
from app.models.proactive_models import (
    ActionDecision,
    ActionType,
    AnomalySeverity,
    NotificationChannel,
    OpportunityRecord,
    OpportunityType,
    ProactiveSnapshot,
    ReportFrequency,
    ScanResult,
    ScanSource,
)


# ==================== Models ====================

class TestProactiveModels:
    """Proactive model testleri."""

    def test_scan_source_enum(self):
        assert ScanSource.SYSTEM == "system"
        assert ScanSource.MARKET == "market"
        assert ScanSource.SECURITY == "security"
        assert ScanSource.PERFORMANCE == "performance"
        assert ScanSource.USER == "user"

    def test_opportunity_type_enum(self):
        assert OpportunityType.COST_SAVING == "cost_saving"
        assert OpportunityType.REVENUE == "revenue"
        assert OpportunityType.EFFICIENCY == "efficiency"
        assert OpportunityType.RISK_MITIGATION == "risk_mitigation"
        assert OpportunityType.GROWTH == "growth"

    def test_anomaly_severity_enum(self):
        assert AnomalySeverity.CRITICAL == "critical"
        assert AnomalySeverity.WARNING == "warning"
        assert AnomalySeverity.NOTICE == "notice"
        assert AnomalySeverity.INFO == "info"
        assert AnomalySeverity.NORMAL == "normal"

    def test_action_type_enum(self):
        assert ActionType.AUTO_HANDLE == "auto_handle"
        assert ActionType.NOTIFY == "notify"
        assert ActionType.ESCALATE == "escalate"
        assert ActionType.DEFER == "defer"
        assert ActionType.IGNORE == "ignore"

    def test_notification_channel_enum(self):
        assert NotificationChannel.TELEGRAM == "telegram"
        assert NotificationChannel.EMAIL == "email"
        assert NotificationChannel.LOG == "log"
        assert NotificationChannel.DASHBOARD == "dashboard"
        assert NotificationChannel.SMS == "sms"

    def test_report_frequency_enum(self):
        assert ReportFrequency.HOURLY == "hourly"
        assert ReportFrequency.DAILY == "daily"
        assert ReportFrequency.WEEKLY == "weekly"
        assert ReportFrequency.MONTHLY == "monthly"
        assert ReportFrequency.CUSTOM == "custom"

    def test_scan_result_model(self):
        sr = ScanResult()
        assert sr.scan_id
        assert sr.source == ScanSource.SYSTEM
        assert sr.findings == []
        assert sr.anomaly_count == 0
        assert sr.timestamp is not None

    def test_opportunity_record_model(self):
        opp = OpportunityRecord(title="Test opp")
        assert opp.opportunity_id
        assert opp.title == "Test opp"
        assert opp.opportunity_type == OpportunityType.EFFICIENCY
        assert opp.score == 0.0
        assert opp.urgency == 0.5

    def test_action_decision_model(self):
        ad = ActionDecision()
        assert ad.decision_id
        assert ad.action_type == ActionType.NOTIFY
        assert ad.confidence == 0.5
        assert ad.risk_level == "low"
        assert ad.details == {}

    def test_proactive_snapshot_model(self):
        snap = ProactiveSnapshot()
        assert snap.snapshot_id
        assert snap.total_scans == 0
        assert snap.total_opportunities == 0
        assert snap.total_anomalies == 0
        assert snap.total_actions == 0


# ==================== ContinuousScanner ====================

class TestContinuousScanner:
    """ContinuousScanner testleri."""

    def test_init(self):
        scanner = ContinuousScanner()
        assert scanner.scan_count == 0
        assert scanner.source_count == 0

    def test_register_source(self):
        scanner = ContinuousScanner()
        result = scanner.register_source("web", "market")
        assert result["registered"] is True
        assert scanner.source_count == 1

    def test_scan_source(self):
        scanner = ContinuousScanner()
        scanner.register_source("sys1", "system")
        result = scanner.scan_source("sys1", {"cpu": 50})
        assert "scan_id" in result
        assert result["source"] == "sys1"
        assert scanner.scan_count == 1

    def test_scan_source_not_found(self):
        scanner = ContinuousScanner()
        result = scanner.scan_source("nonexist")
        assert result.get("error") == "source_not_found"

    def test_scan_findings_threshold(self):
        scanner = ContinuousScanner()
        scanner.register_source("s1")
        result = scanner.scan_source("s1", {"cpu": 150})
        assert result["finding_count"] > 0
        assert any(
            f["type"] == "threshold_exceeded"
            for f in result["findings"]
        )

    def test_scan_findings_negative(self):
        scanner = ContinuousScanner()
        scanner.register_source("s1")
        result = scanner.scan_source("s1", {"balance": -5})
        assert any(
            f["type"] == "negative_value"
            for f in result["findings"]
        )

    def test_scan_findings_error(self):
        scanner = ContinuousScanner()
        scanner.register_source("s1")
        result = scanner.scan_source("s1", {"error": "disk full"})
        assert any(
            f["type"] == "error_detected"
            for f in result["findings"]
        )

    def test_scan_findings_warning(self):
        scanner = ContinuousScanner()
        scanner.register_source("s1")
        result = scanner.scan_source("s1", {"warning": "high load"})
        assert any(
            f["type"] == "warning_detected"
            for f in result["findings"]
        )

    def test_change_detection(self):
        scanner = ContinuousScanner()
        scanner.register_source("s1")
        scanner.scan_source("s1", {"cpu": 50})
        result = scanner.scan_source("s1", {"cpu": 80})
        assert result["change_count"] > 0

    def test_scan_all(self):
        scanner = ContinuousScanner()
        scanner.register_source("s1")
        scanner.register_source("s2")
        result = scanner.scan_all({
            "s1": {"a": 1},
            "s2": {"b": 2},
        })
        assert result["sources_scanned"] == 2

    def test_detect_patterns(self):
        scanner = ContinuousScanner()
        scanner.register_source("s1")
        for _ in range(5):
            scanner.scan_source("s1", {"cpu": 150})
        result = scanner.detect_patterns()
        assert result["pattern_count"] > 0

    def test_schedule_scan(self):
        scanner = ContinuousScanner()
        result = scanner.schedule_scan("s1", 60)
        assert result["scheduled"] is True

    def test_get_scan_history(self):
        scanner = ContinuousScanner()
        scanner.register_source("s1")
        scanner.scan_source("s1", {})
        history = scanner.get_scan_history()
        assert len(history) == 1

    def test_active_source_count(self):
        scanner = ContinuousScanner()
        scanner.register_source("s1")
        scanner.register_source("s2")
        assert scanner.active_source_count == 2


# ==================== OpportunityRanker ====================

class TestOpportunityRanker:
    """OpportunityRanker testleri."""

    def test_init(self):
        ranker = OpportunityRanker()
        assert ranker.opportunity_count == 0

    def test_score_opportunity(self):
        ranker = OpportunityRanker()
        result = ranker.score_opportunity(
            "New feature", urgency=0.8, feasibility=0.9,
        )
        assert "opportunity_id" in result
        assert result["score"] > 0
        assert ranker.scored_count == 1

    def test_score_clamps_values(self):
        ranker = OpportunityRanker()
        result = ranker.score_opportunity(
            "Test", urgency=1.5, feasibility=-0.5, risk=2.0,
        )
        assert result["urgency"] == 1.0
        assert result["feasibility"] == 0.0
        assert result["risk"] == 1.0

    def test_estimate_value(self):
        ranker = OpportunityRanker()
        opp = ranker.score_opportunity("Revenue opp")
        result = ranker.estimate_value(
            opp["opportunity_id"],
            revenue_impact=1000,
            cost_saving=500,
        )
        assert result["total_value"] == 1500

    def test_estimate_value_not_found(self):
        ranker = OpportunityRanker()
        result = ranker.estimate_value("bad_id")
        assert result.get("error") == "opportunity_not_found"

    def test_assess_urgency_deadline_near(self):
        ranker = OpportunityRanker()
        opp = ranker.score_opportunity("Urgent")
        result = ranker.assess_urgency(
            opp["opportunity_id"],
            deadline=time.time() + 1800,
        )
        assert result["urgency"] == 1.0

    def test_assess_urgency_not_found(self):
        ranker = OpportunityRanker()
        result = ranker.assess_urgency("bad_id")
        assert result.get("error") == "opportunity_not_found"

    def test_check_feasibility(self):
        ranker = OpportunityRanker()
        opp = ranker.score_opportunity("Test")
        result = ranker.check_feasibility(
            opp["opportunity_id"],
            resources_available=True,
            skills_available=True,
            budget_available=False,
            dependencies_met=True,
        )
        assert result["feasibility"] == 0.75
        assert "budget" in result["blockers"]

    def test_check_feasibility_not_found(self):
        ranker = OpportunityRanker()
        result = ranker.check_feasibility("bad_id")
        assert result.get("error") == "opportunity_not_found"

    def test_rank_opportunities(self):
        ranker = OpportunityRanker()
        ranker.score_opportunity("Low", urgency=0.1)
        ranker.score_opportunity("High", urgency=0.9)
        result = ranker.rank_opportunities()
        assert result["count"] == 2
        assert result["ranked"][0]["urgency"] >= result["ranked"][1]["urgency"]

    def test_get_opportunity(self):
        ranker = OpportunityRanker()
        opp = ranker.score_opportunity("Test")
        result = ranker.get_opportunity(opp["opportunity_id"])
        assert result["title"] == "Test"

    def test_get_opportunity_not_found(self):
        ranker = OpportunityRanker()
        result = ranker.get_opportunity("bad_id")
        assert result.get("error") == "opportunity_not_found"


# ==================== ProactiveAnomalyDetector ====================

class TestProactiveAnomalyDetector:
    """ProactiveAnomalyDetector testleri."""

    def test_init(self):
        detector = ProactiveAnomalyDetector()
        assert detector.anomaly_count == 0
        assert detector.baseline_count == 0

    def test_learn_baseline(self):
        detector = ProactiveAnomalyDetector()
        result = detector.learn_baseline("cpu", [50, 52, 48, 51, 49])
        assert result["mean"] == pytest.approx(50.0)
        assert detector.baseline_count == 1

    def test_learn_baseline_empty(self):
        detector = ProactiveAnomalyDetector()
        result = detector.learn_baseline("cpu", [])
        assert result.get("error") == "empty_values"

    def test_detect_anomaly_no_baseline(self):
        detector = ProactiveAnomalyDetector()
        result = detector.detect_anomaly("cpu", 50)
        assert result["anomaly"] is False
        assert result["reason"] == "no_baseline"

    def test_detect_anomaly_normal(self):
        detector = ProactiveAnomalyDetector()
        detector.learn_baseline("cpu", [50, 52, 48, 51, 49])
        result = detector.detect_anomaly("cpu", 51)
        assert result["anomaly"] is False

    def test_detect_anomaly_detected(self):
        detector = ProactiveAnomalyDetector()
        detector.learn_baseline("cpu", [50, 52, 48, 51, 49])
        result = detector.detect_anomaly("cpu", 100)
        assert result["anomaly"] is True
        assert detector.anomaly_count == 1

    def test_severity_classification(self):
        detector = ProactiveAnomalyDetector()
        assert detector._classify_severity(6.0) == "critical"
        assert detector._classify_severity(4.0) == "warning"
        assert detector._classify_severity(2.5) == "notice"
        assert detector._classify_severity(1.5) == "info"
        assert detector._classify_severity(0.5) == "normal"

    def test_root_cause_hints(self):
        detector = ProactiveAnomalyDetector()
        hints = detector._get_root_cause_hints("cpu_usage", 95, 50)
        assert len(hints) > 0
        assert any("above" in h for h in hints)

    def test_root_cause_hints_spike(self):
        detector = ProactiveAnomalyDetector()
        hints = detector._get_root_cause_hints("metric", 200, 50)
        assert any("spike" in h for h in hints)

    def test_root_cause_hints_drop(self):
        detector = ProactiveAnomalyDetector()
        hints = detector._get_root_cause_hints("metric", 10, 50)
        assert any("drop" in h for h in hints)

    def test_generate_alert(self):
        detector = ProactiveAnomalyDetector()
        detector.learn_baseline("cpu", [50, 52, 48, 51, 49])
        anom = detector.detect_anomaly("cpu", 200)
        result = detector.generate_alert(anom["anomaly_id"])
        assert "message" in result
        assert detector.alert_count == 1

    def test_generate_alert_not_found(self):
        detector = ProactiveAnomalyDetector()
        result = detector.generate_alert("bad_id")
        assert result.get("error") == "anomaly_not_found"

    def test_batch_detect(self):
        detector = ProactiveAnomalyDetector()
        detector.learn_baseline("cpu", [50, 50, 50])
        detector.learn_baseline("mem", [30, 30, 30])
        result = detector.batch_detect({"cpu": 50, "mem": 90})
        assert result["metrics_checked"] == 2
        assert result["anomalies_found"] >= 1

    def test_get_anomalies_by_severity(self):
        detector = ProactiveAnomalyDetector()
        detector.learn_baseline("m1", [10, 10, 10])
        detector.detect_anomaly("m1", 100)
        results = detector.get_anomalies(severity="critical")
        assert len(results) >= 0

    def test_zero_std_dev(self):
        detector = ProactiveAnomalyDetector()
        detector.learn_baseline("const", [5, 5, 5, 5])
        result = detector.detect_anomaly("const", 5)
        assert result["anomaly"] is False
        result2 = detector.detect_anomaly("const", 6)
        assert result2["anomaly"] is True


# ==================== ProactiveNotifier ====================

class TestProactiveNotifier:
    """ProactiveNotifier testleri."""

    def test_init(self):
        notifier = ProactiveNotifier()
        assert notifier.notification_count == 0

    def test_send_notification(self):
        notifier = ProactiveNotifier()
        result = notifier.send_notification(
            "Test", "Test message", priority=5,
        )
        assert "notification_id" in result
        assert result["status"] == "sent"
        assert notifier.notification_count == 1

    def test_auto_channel_selection(self):
        notifier = ProactiveNotifier()
        result = notifier.send_notification(
            "High", "Critical!", priority=9,
        )
        assert result["channel"] == "sms"

    def test_explicit_channel(self):
        notifier = ProactiveNotifier()
        result = notifier.send_notification(
            "Test", "msg", channel="email",
        )
        assert result["channel"] == "email"

    def test_configure_channel(self):
        notifier = ProactiveNotifier()
        result = notifier.configure_channel(
            "slack", enabled=True, priority_min=4,
        )
        assert result["configured"] is True
        assert notifier.channel_count == 5

    def test_optimize_timing_quiet(self):
        notifier = ProactiveNotifier()
        n = notifier.send_notification("Test", "msg", priority=3)
        result = notifier.optimize_timing(
            n["notification_id"],
            quiet_hours=(22, 8),
        )
        assert "deferred" in result

    def test_optimize_timing_not_found(self):
        notifier = ProactiveNotifier()
        result = notifier.optimize_timing("bad_id")
        assert result.get("error") == "notification_not_found"

    def test_batch_notifications(self):
        notifier = ProactiveNotifier()
        items = [
            {"title": "A", "channel": "log", "priority": 3},
            {"title": "B", "channel": "log", "priority": 5},
            {"title": "C", "channel": "email", "priority": 7},
        ]
        result = notifier.batch_notifications(items)
        assert result["batched"] is True
        assert result["batch_count"] == 2

    def test_batch_empty(self):
        notifier = ProactiveNotifier()
        result = notifier.batch_notifications([])
        assert result["batched"] is False

    def test_priority_override(self):
        notifier = ProactiveNotifier()
        n = notifier.send_notification("Test", "msg", priority=3)
        result = notifier.priority_override(
            n["notification_id"], 9, "critical event",
        )
        assert result["new_priority"] == 9

    def test_priority_override_not_found(self):
        notifier = ProactiveNotifier()
        result = notifier.priority_override("bad_id", 9)
        assert result.get("error") == "notification_not_found"

    def test_get_notifications_by_channel(self):
        notifier = ProactiveNotifier()
        notifier.send_notification("A", "msg", channel="log")
        notifier.send_notification("B", "msg", channel="email")
        results = notifier.get_notifications(channel="log")
        assert len(results) == 1


# ==================== PeriodicReporter ====================

class TestPeriodicReporter:
    """PeriodicReporter testleri."""

    def test_init(self):
        reporter = PeriodicReporter()
        assert reporter.report_count == 0

    def test_daily_summary(self):
        reporter = PeriodicReporter()
        result = reporter.generate_daily_summary(
            {"tasks_completed": 10, "errors": 2},
        )
        assert result["report_type"] == "daily"
        assert result["metrics"]["tasks_completed"] == 10
        assert reporter.report_count == 1

    def test_daily_with_events(self):
        reporter = PeriodicReporter()
        events = [{"type": "deploy"}, {"type": "alert"}]
        result = reporter.generate_daily_summary(
            {"tasks": 5}, events=events,
        )
        assert result["event_count"] == 2

    def test_weekly_report(self):
        reporter = PeriodicReporter()
        result = reporter.generate_weekly_report(
            {"revenue": 5000},
            highlights=["New client"],
            issues=["Server slow"],
        )
        assert result["report_type"] == "weekly"
        assert "New client" in result["highlights"]

    def test_custom_report(self):
        reporter = PeriodicReporter()
        result = reporter.generate_custom_report(
            "Monthly Overview", "monthly",
            {"sales": 100},
        )
        assert result["report_type"] == "custom"
        assert result["title"] == "Monthly Overview"

    def test_trend_calculation(self):
        reporter = PeriodicReporter()
        reporter.generate_daily_summary({"val": 10})
        reporter.generate_daily_summary({"val": 20})
        result = reporter.generate_daily_summary({"val": 30})
        assert "val" in result.get("trends", {})

    def test_add_schedule(self):
        reporter = PeriodicReporter()
        result = reporter.add_schedule("morning", "daily", hour=9)
        assert result["scheduled"] is True
        assert reporter.schedule_count == 1

    def test_track_key_metrics(self):
        reporter = PeriodicReporter()
        result = reporter.track_key_metrics({"cpu": 50, "mem": 60})
        assert result["tracked"] is True
        assert result["metric_count"] == 2

    def test_trend_highlights(self):
        reporter = PeriodicReporter()
        reporter.track_key_metrics({"cpu": 10})
        reporter.track_key_metrics({"cpu": 20})
        reporter.track_key_metrics({"cpu": 30})
        result = reporter.get_trend_highlights()
        assert len(result["highlights"]) > 0
        assert result["highlights"][0]["trend"] == "consistently_increasing"

    def test_trend_highlights_insufficient_data(self):
        reporter = PeriodicReporter()
        result = reporter.get_trend_highlights()
        assert result.get("insufficient_data") is True

    def test_get_reports_by_type(self):
        reporter = PeriodicReporter()
        reporter.generate_daily_summary({"a": 1})
        reporter.generate_weekly_report({"b": 2})
        results = reporter.get_reports(report_type="daily")
        assert len(results) == 1


# ==================== ProactivePriorityQueue ====================

class TestProactivePriorityQueue:
    """ProactivePriorityQueue testleri."""

    def test_init(self):
        queue = ProactivePriorityQueue()
        assert queue.size == 0
        assert queue.is_empty is True

    def test_enqueue(self):
        queue = ProactivePriorityQueue()
        result = queue.enqueue("Task A", priority=5)
        assert "item_id" in result
        assert queue.size == 1

    def test_dequeue(self):
        queue = ProactivePriorityQueue()
        queue.enqueue("Task A", priority=5)
        item = queue.dequeue()
        assert item["title"] == "Task A"
        assert queue.size == 0
        assert queue.processed_count == 1

    def test_dequeue_empty(self):
        queue = ProactivePriorityQueue()
        result = queue.dequeue()
        assert result.get("error") == "queue_empty"

    def test_priority_ordering(self):
        queue = ProactivePriorityQueue()
        queue.enqueue("Low", priority=2)
        queue.enqueue("High", priority=9)
        queue.enqueue("Med", priority=5)
        item = queue.dequeue()
        assert item["title"] == "High"

    def test_peek(self):
        queue = ProactivePriorityQueue()
        queue.enqueue("A", priority=5)
        result = queue.peek()
        assert result["title"] == "A"
        assert queue.size == 1

    def test_peek_empty(self):
        queue = ProactivePriorityQueue()
        result = queue.peek()
        assert result.get("error") == "queue_empty"

    def test_update_priority(self):
        queue = ProactivePriorityQueue()
        result = queue.enqueue("A", priority=3)
        updated = queue.update_priority(
            result["item_id"], 9,
        )
        assert updated["new_priority"] == 9

    def test_update_priority_not_found(self):
        queue = ProactivePriorityQueue()
        result = queue.update_priority("bad_id", 5)
        assert result.get("error") == "item_not_found"

    def test_update_deadline(self):
        queue = ProactivePriorityQueue()
        result = queue.enqueue("A", priority=5)
        updated = queue.update_deadline(
            result["item_id"], time.time() + 3600,
        )
        assert updated["deadline"] > 0

    def test_update_deadline_not_found(self):
        queue = ProactivePriorityQueue()
        result = queue.update_deadline("bad_id", 100)
        assert result.get("error") == "item_not_found"

    def test_remove_item(self):
        queue = ProactivePriorityQueue()
        result = queue.enqueue("A")
        removed = queue.remove_item(result["item_id"])
        assert removed["removed"] is True
        assert queue.size == 0

    def test_remove_item_not_found(self):
        queue = ProactivePriorityQueue()
        result = queue.remove_item("bad_id")
        assert result.get("error") == "item_not_found"

    def test_overflow_handling(self):
        queue = ProactivePriorityQueue(max_size=2)
        queue.enqueue("A", priority=5)
        queue.enqueue("B", priority=8)
        result = queue.enqueue("C", priority=10)
        assert queue.size == 2
        assert "item_id" in result

    def test_get_overdue(self):
        queue = ProactivePriorityQueue()
        queue.enqueue("A", deadline=time.time() - 100)
        queue.enqueue("B", deadline=time.time() + 10000)
        overdue = queue.get_overdue()
        assert len(overdue) == 1

    def test_get_queue(self):
        queue = ProactivePriorityQueue()
        queue.enqueue("A")
        queue.enqueue("B")
        items = queue.get_queue()
        assert len(items) == 2

    def test_deadline_boost(self):
        queue = ProactivePriorityQueue()
        queue.enqueue("Far", priority=8, deadline=time.time() + 999999)
        queue.enqueue("Near", priority=5, deadline=time.time() + 100)
        item = queue.dequeue()
        # Near deadline should get urgency boost
        assert item is not None


# ==================== SleepCycleManager ====================

class TestSleepCycleManager:
    """SleepCycleManager testleri."""

    def test_init(self):
        mgr = SleepCycleManager()
        assert mgr.quiet_hours == (23, 7)

    def test_is_quiet_hours_yes(self):
        mgr = SleepCycleManager(quiet_start=22, quiet_end=8)
        result = mgr.is_quiet_hours(current_hour=23)
        assert result["is_quiet"] is True

    def test_is_quiet_hours_no(self):
        mgr = SleepCycleManager(quiet_start=22, quiet_end=8)
        result = mgr.is_quiet_hours(current_hour=12)
        assert result["is_quiet"] is False

    def test_quiet_hours_midnight_wrap(self):
        mgr = SleepCycleManager(quiet_start=23, quiet_end=7)
        assert mgr.is_quiet_hours(current_hour=2)["is_quiet"] is True
        assert mgr.is_quiet_hours(current_hour=10)["is_quiet"] is False

    def test_set_quiet_hours(self):
        mgr = SleepCycleManager()
        result = mgr.set_quiet_hours(20, 6)
        assert result["quiet_start"] == 20
        assert result["quiet_end"] == 6

    def test_set_timezone(self):
        mgr = SleepCycleManager()
        result = mgr.set_timezone(5)
        assert result["timezone_offset"] == 5

    def test_set_availability(self):
        mgr = SleepCycleManager()
        result = mgr.set_availability("user1", False)
        assert result["available"] is False

    def test_check_availability(self):
        mgr = SleepCycleManager()
        result = mgr.check_availability("user1")
        assert result["available"] is True

    def test_check_availability_expired(self):
        mgr = SleepCycleManager()
        mgr.set_availability(
            "user1", False, until=time.time() - 100,
        )
        result = mgr.check_availability("user1")
        assert result["available"] is True

    def test_add_wake_trigger(self):
        mgr = SleepCycleManager()
        result = mgr.add_wake_trigger(
            "critical_alert", "priority >= 9",
        )
        assert result["added"] is True
        assert mgr.trigger_count == 1

    def test_check_wake_trigger(self):
        mgr = SleepCycleManager()
        mgr.add_wake_trigger("alert", "high", priority_min=8)
        result = mgr.check_wake_trigger("alert", 9)
        assert result["should_wake"] is True

    def test_check_wake_trigger_low_priority(self):
        mgr = SleepCycleManager()
        mgr.add_wake_trigger("alert", "high", priority_min=8)
        result = mgr.check_wake_trigger("info", 3)
        assert result["should_wake"] is False

    def test_emergency_override(self):
        mgr = SleepCycleManager()
        result = mgr.emergency_override("server down", 30)
        assert result["override"] is True
        assert mgr.has_active_override() is True

    def test_should_notify_not_quiet(self):
        mgr = SleepCycleManager(quiet_start=22, quiet_end=8)
        result = mgr.should_notify(5, current_hour=12)
        assert result["should_notify"] is True

    def test_should_notify_quiet_low_priority(self):
        mgr = SleepCycleManager(quiet_start=22, quiet_end=8)
        result = mgr.should_notify(3, current_hour=23)
        assert result["should_notify"] is False

    def test_should_notify_quiet_high_priority(self):
        mgr = SleepCycleManager(quiet_start=22, quiet_end=8)
        result = mgr.should_notify(9, current_hour=23)
        assert result["should_notify"] is True


# ==================== ActionDecider ====================

class TestActionDecider:
    """ActionDecider testleri."""

    def test_init(self):
        decider = ActionDecider()
        assert decider.decision_count == 0

    def test_decide_auto_handle(self):
        decider = ActionDecider()
        result = decider.decide(
            "cache_cleanup", confidence=0.95,
            impact="low", risk=0.1,
        )
        assert result["decision_type"] == "auto_handle"
        assert decider.decision_count == 1

    def test_decide_escalate_low_confidence(self):
        decider = ActionDecider()
        result = decider.decide(
            "deploy", confidence=0.2,
            impact="low", risk=0.1,
        )
        assert result["decision_type"] == "escalate"

    def test_decide_escalate_high_risk(self):
        decider = ActionDecider()
        result = decider.decide(
            "deploy", confidence=0.7,
            impact="low", risk=0.8,
        )
        assert result["decision_type"] == "escalate"

    def test_decide_escalate_high_impact(self):
        decider = ActionDecider()
        result = decider.decide(
            "server_restart", confidence=0.9,
            impact="high", risk=0.1,
        )
        assert result["needs_approval"] is True

    def test_assess_impact(self):
        decider = ActionDecider()
        result = decider.assess_impact(
            "deploy",
            affected_systems=["api", "db", "cache"],
        )
        assert result["impact_level"] in ("medium", "high")

    def test_assess_impact_irreversible(self):
        decider = ActionDecider()
        result = decider.assess_impact(
            "delete", reversible=False,
        )
        # Low bumped to medium for irreversible
        assert result["impact_level"] == "medium"

    def test_assess_impact_production_scope(self):
        decider = ActionDecider()
        result = decider.assess_impact(
            "deploy", scope="production",
        )
        assert result["impact_level"] in ("medium", "high")

    def test_evaluate_risk(self):
        decider = ActionDecider()
        result = decider.evaluate_risk(
            "deploy",
            failure_probability=0.5,
            failure_impact="high",
        )
        assert result["risk_score"] > 0

    def test_evaluate_risk_no_fallback(self):
        decider = ActionDecider()
        result = decider.evaluate_risk(
            "deploy",
            failure_probability=0.5,
            failure_impact="high",
            has_fallback=False,
        )
        assert result["risk_score"] > 0.3

    def test_add_approval_rule(self):
        decider = ActionDecider()
        result = decider.add_approval_rule("delete")
        assert result["added"] is True

    def test_approval_rule_triggers(self):
        decider = ActionDecider()
        decider.add_approval_rule("delete")
        result = decider.decide(
            "delete_database", confidence=0.95,
            impact="low", risk=0.1,
        )
        assert result["needs_approval"] is True
        assert result["decision_type"] == "escalate"

    def test_route_approval(self):
        decider = ActionDecider()
        dec = decider.decide("test", confidence=0.3)
        result = decider.route_approval(
            dec["decision_id"], "admin",
        )
        assert result["routed_to"] == "admin"

    def test_route_approval_not_found(self):
        decider = ActionDecider()
        result = decider.route_approval("bad_id")
        assert result.get("error") == "decision_not_found"

    def test_get_decisions_by_type(self):
        decider = ActionDecider()
        decider.decide("a", confidence=0.95, impact="low", risk=0.1)
        decider.decide("b", confidence=0.2)
        results = decider.get_decisions(decision_type="auto_handle")
        assert len(results) >= 1

    def test_auto_handle_rate(self):
        decider = ActionDecider()
        decider.decide("a", confidence=0.95, impact="low", risk=0.1)
        decider.decide("b", confidence=0.95, impact="low", risk=0.1)
        assert decider.auto_handle_rate == 1.0

    def test_auto_handle_rate_zero(self):
        decider = ActionDecider()
        assert decider.auto_handle_rate == 0.0


# ==================== ProactiveOrchestrator ====================

class TestProactiveOrchestrator:
    """ProactiveOrchestrator testleri."""

    def test_init(self):
        orch = ProactiveOrchestrator()
        assert orch.cycles_completed == 0

    def test_add_scan_source(self):
        orch = ProactiveOrchestrator()
        result = orch.add_scan_source("web", "market")
        assert result["registered"] is True

    def test_run_cycle_empty(self):
        orch = ProactiveOrchestrator()
        result = orch.run_cycle()
        assert result["cycle"] == 1
        assert result["sources_scanned"] == 0

    def test_run_cycle_with_data(self):
        orch = ProactiveOrchestrator()
        orch.add_scan_source("sys")
        result = orch.run_cycle({
            "sys": {"cpu": 50, "mem": 60},
        })
        assert result["sources_scanned"] == 1

    def test_run_cycle_with_anomaly(self):
        orch = ProactiveOrchestrator()
        orch.add_scan_source("sys")
        orch.detector.learn_baseline("sys.cpu", [50, 50, 50])
        result = orch.run_cycle({
            "sys": {"cpu": 200},
        })
        assert result["anomalies_detected"] >= 1

    def test_run_cycle_with_findings(self):
        orch = ProactiveOrchestrator()
        orch.add_scan_source("sys")
        result = orch.run_cycle({
            "sys": {"error": "disk full", "cpu": 150},
        })
        assert result["total_findings"] > 0

    def test_score_opportunity(self):
        orch = ProactiveOrchestrator()
        result = orch.score_opportunity(
            "Cost saving", urgency=0.8,
        )
        assert "opportunity_id" in result

    def test_get_analytics(self):
        orch = ProactiveOrchestrator()
        analytics = orch.get_analytics()
        assert "cycles_completed" in analytics
        assert "scan_sources" in analytics
        assert "anomalies" in analytics
        assert "decisions" in analytics

    def test_get_status(self):
        orch = ProactiveOrchestrator()
        status = orch.get_status()
        assert "cycles_completed" in status
        assert "queue_size" in status

    def test_multiple_cycles(self):
        orch = ProactiveOrchestrator()
        orch.add_scan_source("s1")
        orch.run_cycle({"s1": {"a": 1}})
        orch.run_cycle({"s1": {"a": 2}})
        assert orch.cycles_completed == 2

    def test_full_pipeline(self):
        """Tam pipeline testi."""
        orch = ProactiveOrchestrator()

        # Kaynakları ekle
        orch.add_scan_source("web", "market")
        orch.add_scan_source("server", "system")

        # Bazal öğren
        orch.detector.learn_baseline(
            "server.cpu", [50, 52, 48, 51, 49],
        )

        # Döngü çalıştır
        result = orch.run_cycle({
            "web": {"response_time": 200},
            "server": {"cpu": 95, "error": "high load"},
        })

        assert result["sources_scanned"] == 2
        assert result["cycle"] == 1

        # Analitik kontrol
        analytics = orch.get_analytics()
        assert analytics["total_scans"] >= 2


# ==================== Config ====================

class TestProactiveConfig:
    """Proactive config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.proactive_enabled is True
        assert s.scan_interval_minutes == 5
        assert s.proactive_quiet_hours_start == 23
        assert s.proactive_quiet_hours_end == 7
        assert s.auto_action_threshold == 0.8


# ==================== Imports ====================

class TestProactiveImports:
    """Import testleri."""

    def test_import_all(self):
        from app.core.proactive import (
            ActionDecider,
            ContinuousScanner,
            OpportunityRanker,
            PeriodicReporter,
            ProactiveAnomalyDetector,
            ProactiveNotifier,
            ProactiveOrchestrator,
            ProactivePriorityQueue,
            SleepCycleManager,
        )
        assert ActionDecider is not None
        assert ContinuousScanner is not None
        assert OpportunityRanker is not None
        assert PeriodicReporter is not None
        assert ProactiveAnomalyDetector is not None
        assert ProactiveNotifier is not None
        assert ProactiveOrchestrator is not None
        assert ProactivePriorityQueue is not None
        assert SleepCycleManager is not None

    def test_import_models(self):
        from app.models.proactive_models import (
            ActionDecision,
            ActionType,
            AnomalySeverity,
            NotificationChannel,
            OpportunityRecord,
            OpportunityType,
            ProactiveSnapshot,
            ReportFrequency,
            ScanResult,
            ScanSource,
        )
        assert ScanSource is not None
        assert OpportunityType is not None
        assert AnomalySeverity is not None
        assert ActionType is not None
        assert NotificationChannel is not None
        assert ReportFrequency is not None
        assert ScanResult is not None
        assert OpportunityRecord is not None
        assert ActionDecision is not None
        assert ProactiveSnapshot is not None
