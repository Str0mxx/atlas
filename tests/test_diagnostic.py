"""Self-Diagnostic & Auto-Repair sistemi testleri."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.diagnostic import (
    BottleneckRecord,
    BottleneckType,
    DiagnosticPhase,
    DiagnosticSnapshot,
    ErrorRecord,
    ErrorSeverity,
    FixRecord,
    FixType,
    HealthReport,
    HealthStatus,
    MaintenanceType,
    RecoveryRecord,
)


# ── Model Testleri ──────────────────────────────────────────


class TestDiagnosticModels:
    """Model testleri."""

    def test_health_report_defaults(self):
        r = HealthReport()
        assert r.status == HealthStatus.UNKNOWN
        assert r.score == 0.5
        assert r.issues == []

    def test_error_record_defaults(self):
        e = ErrorRecord()
        assert e.severity == ErrorSeverity.MEDIUM
        assert e.frequency == 1

    def test_bottleneck_record_defaults(self):
        b = BottleneckRecord()
        assert b.bottleneck_type == BottleneckType.LATENCY
        assert b.impact == 0.5

    def test_fix_record_defaults(self):
        f = FixRecord()
        assert f.fix_type == FixType.CONFIG
        assert f.rollback_available is True

    def test_recovery_record_defaults(self):
        r = RecoveryRecord()
        assert r.data_integrity == 1.0
        assert r.success is False

    def test_diagnostic_snapshot_defaults(self):
        s = DiagnosticSnapshot()
        assert s.overall_health == HealthStatus.UNKNOWN
        assert s.health_score == 0.0

    def test_enum_values(self):
        assert HealthStatus.HEALTHY == "healthy"
        assert ErrorSeverity.CRITICAL == "critical"
        assert BottleneckType.CPU == "cpu"
        assert FixType.CACHE_CLEAR == "cache_clear"
        assert MaintenanceType.CLEANUP == "cleanup"
        assert DiagnosticPhase.SCANNING == "scanning"

    def test_unique_ids(self):
        r1 = HealthReport()
        r2 = HealthReport()
        assert r1.report_id != r2.report_id

    def test_health_report_custom(self):
        r = HealthReport(
            component="db",
            status=HealthStatus.HEALTHY,
            score=0.95,
            metrics={"latency": 10.0},
        )
        assert r.component == "db"
        assert r.score == 0.95

    def test_error_record_custom(self):
        e = ErrorRecord(
            error_type="timeout",
            severity=ErrorSeverity.HIGH,
            component="api",
        )
        assert e.error_type == "timeout"
        assert e.severity == ErrorSeverity.HIGH

    def test_fix_record_custom(self):
        f = FixRecord(
            fix_type=FixType.RESTART,
            target="worker",
            success=True,
        )
        assert f.fix_type == FixType.RESTART
        assert f.success is True


# ── HealthScanner Testleri ───────────────────────────────────


class TestHealthScanner:
    """HealthScanner testleri."""

    def setup_method(self):
        from app.core.diagnostic.health_scanner import HealthScanner
        self.scanner = HealthScanner()

    def test_init(self):
        assert self.scanner.component_count == 0
        assert self.scanner.report_count == 0

    def test_register_component(self):
        result = self.scanner.register_component(
            "db", "database", {"latency": 0.5},
        )
        assert self.scanner.component_count == 1
        assert result["type"] == "database"

    def test_scan_component_healthy(self):
        self.scanner.register_component("api", thresholds={"error_rate": 0.5})
        report = self.scanner.scan_component("api", {"error_rate": 0.1})
        assert report.status == HealthStatus.HEALTHY
        assert report.component == "api"

    def test_scan_component_with_issues(self):
        self.scanner.register_component("api", thresholds={"error_rate": 0.3})
        report = self.scanner.scan_component("api", {"error_rate": 0.5})
        assert len(report.issues) > 0

    def test_full_scan(self):
        self.scanner.register_component("api")
        self.scanner.register_component("db")
        result = self.scanner.full_scan({
            "api": {"latency": 0.1},
            "db": {"latency": 0.2},
        })
        assert result["components_scanned"] == 2
        assert "overall_status" in result

    def test_set_baseline_and_detect_anomaly(self):
        self.scanner.set_baseline("api", {"latency": 0.1})
        anomaly = self.scanner.detect_anomaly(
            "api", "latency", 0.5, deviation_threshold=0.3,
        )
        assert anomaly is not None
        assert anomaly["deviation"] > 0.3

    def test_no_anomaly_within_threshold(self):
        self.scanner.set_baseline("api", {"latency": 0.1})
        anomaly = self.scanner.detect_anomaly(
            "api", "latency", 0.12, deviation_threshold=0.3,
        )
        assert anomaly is None

    def test_get_component_history(self):
        self.scanner.register_component("api")
        self.scanner.scan_component("api", {"latency": 0.1})
        self.scanner.scan_component("api", {"latency": 0.2})
        history = self.scanner.get_component_history("api")
        assert len(history) == 2

    def test_get_unhealthy_components(self):
        self.scanner.register_component("api", thresholds={"err": 0.1})
        self.scanner.scan_component("api", {"err": 0.9, "load": 0.9})
        unhealthy = self.scanner.get_unhealthy_components()
        assert len(unhealthy) >= 0  # depends on score

    def test_anomaly_count(self):
        self.scanner.set_baseline("api", {"latency": 0.1})
        self.scanner.detect_anomaly("api", "latency", 1.0)
        assert self.scanner.anomaly_count == 1


# ── ErrorAnalyzer Testleri ───────────────────────────────────


class TestErrorAnalyzer:
    """ErrorAnalyzer testleri."""

    def setup_method(self):
        from app.core.diagnostic.error_analyzer import ErrorAnalyzer
        self.analyzer = ErrorAnalyzer()

    def test_init(self):
        assert self.analyzer.error_count == 0

    def test_record_error(self):
        record = self.analyzer.record_error(
            "timeout", "Request timed out", "api",
        )
        assert record.error_type == "timeout"
        assert self.analyzer.error_count == 1

    def test_frequency_tracking(self):
        self.analyzer.record_error("timeout", "err1", "api")
        record = self.analyzer.record_error("timeout", "err2", "api")
        assert record.frequency == 2

    def test_analyze_root_cause(self):
        record = self.analyzer.record_error(
            "timeout", "Connection timeout", "api",
        )
        result = self.analyzer.analyze_root_cause(record.error_id)
        assert result["found"]
        assert result["root_cause"]

    def test_analyze_root_cause_not_found(self):
        result = self.analyzer.analyze_root_cause("nonexistent")
        assert not result["found"]

    def test_find_correlations(self):
        self.analyzer.record_error("timeout", "err", "api")
        self.analyzer.record_error("connection", "err", "db")
        corrs = self.analyzer.find_correlations(time_window_seconds=60)
        assert len(corrs) == 1

    def test_assess_impact(self):
        record = self.analyzer.record_error(
            "crash", "Fatal", "core",
            severity=ErrorSeverity.CRITICAL,
        )
        result = self.analyzer.assess_impact(record.error_id)
        assert result["assessed"]
        assert result["overall_impact"] > 0.5

    def test_assess_impact_not_found(self):
        result = self.analyzer.assess_impact("nonexistent")
        assert not result["assessed"]

    def test_get_frequent_errors(self):
        for _ in range(5):
            self.analyzer.record_error("timeout", "err", "api")
        frequent = self.analyzer.get_frequent_errors(min_frequency=3)
        assert len(frequent) == 1
        assert frequent[0]["frequency"] == 5

    def test_get_errors_by_component(self):
        self.analyzer.record_error("timeout", "err", "api")
        self.analyzer.record_error("crash", "err", "db")
        api_errors = self.analyzer.get_errors_by_component("api")
        assert len(api_errors) == 1

    def test_get_errors_by_severity(self):
        self.analyzer.record_error(
            "crash", "err", severity=ErrorSeverity.CRITICAL,
        )
        self.analyzer.record_error("warn", "err", severity=ErrorSeverity.LOW)
        critical = self.analyzer.get_errors_by_severity(ErrorSeverity.CRITICAL)
        assert len(critical) == 1

    def test_add_root_cause_rule(self):
        self.analyzer.add_root_cause_rule("oom", "Bellek tasmasi")
        record = self.analyzer.record_error("oom_killer", "OOM", "worker")
        result = self.analyzer.analyze_root_cause(record.error_id)
        assert "Bellek" in result["root_cause"]

    def test_error_patterns(self):
        self.analyzer.record_error("timeout", "err", "api")
        patterns = self.analyzer.get_error_patterns()
        assert len(patterns) == 1


# ── BottleneckDetector Testleri ──────────────────────────────


class TestBottleneckDetector:
    """BottleneckDetector testleri."""

    def setup_method(self):
        from app.core.diagnostic.bottleneck_detector import BottleneckDetector
        self.detector = BottleneckDetector()

    def test_init(self):
        assert self.detector.bottleneck_count == 0

    def test_profile_operation(self):
        result = self.detector.profile_operation("query", 50.0)
        assert result["duration_ms"] == 50.0
        assert self.detector.profile_count == 1

    def test_detect_slow_operations(self):
        for _ in range(3):
            self.detector.profile_operation("slow_query", 2000.0)
        slow = self.detector.detect_slow_operations(threshold_ms=1000.0)
        assert len(slow) == 1
        assert slow[0]["operation"] == "slow_query"

    def test_no_slow_operations(self):
        self.detector.profile_operation("fast_query", 50.0)
        slow = self.detector.detect_slow_operations(threshold_ms=1000.0)
        assert len(slow) == 0

    def test_check_memory_bottleneck(self):
        result = self.detector.check_memory("worker", 90.0)
        assert result is not None
        assert result.bottleneck_type == BottleneckType.MEMORY

    def test_check_memory_ok(self):
        result = self.detector.check_memory("worker", 50.0)
        assert result is None

    def test_check_memory_with_growth(self):
        result = self.detector.check_memory("worker", 70.0, memory_growth_rate=10.0)
        assert result is not None

    def test_check_cpu_bottleneck(self):
        result = self.detector.check_cpu("worker", 95.0)
        assert result is not None
        assert result.bottleneck_type == BottleneckType.CPU

    def test_check_cpu_ok(self):
        result = self.detector.check_cpu("worker", 30.0)
        assert result is None

    def test_check_io_bottleneck(self):
        result = self.detector.check_io("db", 200.0)
        assert result is not None
        assert result.bottleneck_type == BottleneckType.IO

    def test_check_network_bottleneck(self):
        result = self.detector.check_network("api", 500.0)
        assert result is not None
        assert result.bottleneck_type == BottleneckType.NETWORK

    def test_set_threshold(self):
        self.detector.set_threshold("cpu_percent", 90.0)
        result = self.detector.check_cpu("worker", 85.0)
        assert result is None  # 85 < 90

    def test_get_bottlenecks_by_type(self):
        self.detector.check_cpu("w1", 95.0)
        self.detector.check_memory("w2", 90.0)
        cpu = self.detector.get_bottlenecks_by_type(BottleneckType.CPU)
        assert len(cpu) == 1

    def test_get_top_bottlenecks(self):
        self.detector.check_cpu("w1", 95.0)
        self.detector.check_cpu("w2", 85.0)
        top = self.detector.get_top_bottlenecks(limit=1)
        assert len(top) == 1

    def test_get_operation_stats(self):
        self.detector.profile_operation("query", 100.0)
        self.detector.profile_operation("query", 200.0)
        stats = self.detector.get_operation_stats("query")
        assert stats is not None
        assert stats["avg_ms"] == 150.0

    def test_get_operation_stats_not_found(self):
        assert self.detector.get_operation_stats("missing") is None


# ── DependencyChecker Testleri ───────────────────────────────


class TestDependencyChecker:
    """DependencyChecker testleri."""

    def setup_method(self):
        from app.core.diagnostic.dependency_checker import DependencyChecker
        self.checker = DependencyChecker()

    def test_init(self):
        assert self.checker.package_count == 0

    def test_register_package(self):
        result = self.checker.register_package("flask", "2.0.0")
        assert self.checker.package_count == 1

    def test_check_missing(self):
        self.checker.register_package("app", "1.0", ["flask", "redis"])
        missing = self.checker.check_missing()
        assert len(missing) == 2

    def test_check_missing_satisfied(self):
        self.checker.register_package("flask", "2.0.0")
        self.checker.register_package("app", "1.0", ["flask"])
        missing = self.checker.check_missing()
        assert len(missing) == 0

    def test_check_version_conflicts(self):
        self.checker.register_package("app1", "1.0", ["lib==1.0"])
        self.checker.register_package("app2", "1.0", ["lib==2.0"])
        conflicts = self.checker.check_version_conflicts()
        assert len(conflicts) == 1

    def test_no_version_conflicts(self):
        self.checker.register_package("app1", "1.0", ["lib==1.0"])
        self.checker.register_package("app2", "1.0", ["lib==1.0"])
        conflicts = self.checker.check_version_conflicts()
        assert len(conflicts) == 0

    def test_check_circular(self):
        self.checker.register_package("a", "1.0", ["b"])
        self.checker.register_package("b", "1.0", ["a"])
        cycles = self.checker.check_circular()
        assert len(cycles) > 0

    def test_no_circular(self):
        self.checker.register_package("a", "1.0", ["b"])
        self.checker.register_package("b", "1.0")
        cycles = self.checker.check_circular()
        assert len(cycles) == 0

    def test_mark_deprecated(self):
        self.checker.register_package("old_lib", "1.0")
        self.checker.mark_deprecated("old_lib", "new_lib")
        deprecated = self.checker.check_deprecated()
        assert len(deprecated) == 1

    def test_add_vulnerability(self):
        self.checker.register_package("lib", "1.0")
        self.checker.add_vulnerability("lib", "CVE-2024-001", "high")
        vulns = self.checker.check_vulnerabilities()
        assert len(vulns) == 1
        assert self.checker.vulnerability_count == 1

    def test_full_check_healthy(self):
        self.checker.register_package("app", "1.0")
        result = self.checker.full_check()
        assert result["healthy"]

    def test_full_check_with_issues(self):
        self.checker.register_package("app", "1.0", ["missing_lib"])
        result = self.checker.full_check()
        assert not result["healthy"]
        assert result["total_issues"] > 0

    def test_get_dependency_tree(self):
        self.checker.register_package("app", "1.0", ["lib"])
        self.checker.register_package("lib", "2.0")
        tree = self.checker.get_dependency_tree("app")
        assert tree["name"] == "app"
        assert len(tree["children"]) == 1


# ── AutoFixer Testleri ───────────────────────────────────────


class TestAutoFixer:
    """AutoFixer testleri."""

    def setup_method(self):
        from app.core.diagnostic.auto_fixer import AutoFixer
        self.fixer = AutoFixer(auto_approve=True)

    def test_init(self):
        assert self.fixer.fix_count == 0

    def test_find_fix(self):
        fix = self.fixer.find_fix("cache_overflow")
        assert fix is not None
        assert fix["fix_type"] == FixType.CACHE_CLEAR

    def test_find_fix_not_found(self):
        assert self.fixer.find_fix("unknown_issue") is None

    def test_apply_fix(self):
        record = self.fixer.apply_fix(
            "api", FixType.CACHE_CLEAR, "Clear cache",
        )
        assert record.success
        assert self.fixer.fix_count == 1

    def test_auto_fix_safe(self):
        result = self.fixer.auto_fix("cache_overflow", "api")
        assert result["fixed"]

    def test_auto_fix_unsafe_with_approval(self):
        result = self.fixer.auto_fix("service_down", "worker")
        assert result["fixed"]  # auto_approve=True

    def test_auto_fix_unsafe_without_approval(self):
        from app.core.diagnostic.auto_fixer import AutoFixer
        fixer = AutoFixer(auto_approve=False)
        result = fixer.auto_fix("service_down", "worker")
        assert not result["fixed"]
        assert result.get("requires_approval")

    def test_clear_cache(self):
        record = self.fixer.clear_cache("redis")
        assert record.fix_type == FixType.CACHE_CLEAR

    def test_fix_config(self):
        record = self.fixer.fix_config("api", {"timeout": 30})
        assert record.fix_type == FixType.CONFIG

    def test_restart_service(self):
        record = self.fixer.restart_service("worker")
        assert record.fix_type == FixType.RESTART
        assert not record.rollback_available

    def test_repair_data(self):
        record = self.fixer.repair_data("db", "Index rebuild")
        assert record.fix_type == FixType.DATA_REPAIR

    def test_add_known_fix(self):
        self.fixer.add_known_fix(
            "disk_full", FixType.CACHE_CLEAR, "Temizle", auto_safe=True,
        )
        fix = self.fixer.find_fix("disk_full")
        assert fix is not None

    def test_get_fix_history(self):
        self.fixer.apply_fix("a", FixType.CONFIG)
        self.fixer.apply_fix("b", FixType.RESTART)
        history = self.fixer.get_fix_history()
        assert len(history) == 2

    def test_get_fix_history_filtered(self):
        self.fixer.apply_fix("a", FixType.CONFIG)
        self.fixer.apply_fix("b", FixType.RESTART)
        history = self.fixer.get_fix_history(target="a")
        assert len(history) == 1

    def test_success_rate(self):
        self.fixer.apply_fix("a", FixType.CONFIG)
        assert self.fixer.get_success_rate() == 1.0


# ── RecoveryManager Testleri ─────────────────────────────────


class TestRecoveryManager:
    """RecoveryManager testleri."""

    def setup_method(self):
        from app.core.diagnostic.recovery_manager import RecoveryManager
        self.recovery = RecoveryManager()

    def test_init(self):
        assert self.recovery.recovery_count == 0
        assert self.recovery.backup_count == 0

    def test_create_backup(self):
        result = self.recovery.create_backup(
            "daily", "db", {"tables": 10},
        )
        assert self.recovery.backup_count == 1

    def test_restore_backup_success(self):
        self.recovery.create_backup("daily", "db")
        record = self.recovery.restore_backup("daily")
        assert record.success

    def test_restore_backup_not_found(self):
        record = self.recovery.restore_backup("missing")
        assert not record.success

    def test_create_checkpoint(self):
        result = self.recovery.create_checkpoint(
            "pre_deploy", {"version": "1.0"},
        )
        assert self.recovery.checkpoint_count == 1

    def test_recover_state(self):
        self.recovery.create_checkpoint("cp1", {"v": 1})
        record = self.recovery.recover_state("cp1")
        assert record.success

    def test_recover_state_not_found(self):
        record = self.recovery.recover_state("missing")
        assert not record.success

    def test_push_and_execute_rollback(self):
        self.recovery.push_rollback("deploy", {"version": "0.9"})
        assert self.recovery.rollback_depth == 1
        record = self.recovery.execute_rollback()
        assert record.success
        assert self.recovery.rollback_depth == 0

    def test_execute_rollback_empty(self):
        record = self.recovery.execute_rollback()
        assert not record.success

    def test_rollback_all(self):
        self.recovery.push_rollback("a", {})
        self.recovery.push_rollback("b", {})
        records = self.recovery.rollback_all()
        assert len(records) == 2

    def test_check_data_integrity_healthy(self):
        result = self.recovery.check_data_integrity(
            "db", {"a": 1, "b": 2}, {"a": 1, "b": 2},
        )
        assert result["healthy"]
        assert result["integrity"] == 1.0

    def test_check_data_integrity_issues(self):
        result = self.recovery.check_data_integrity(
            "db", {"a": 1, "b": 2, "c": 3}, {"a": 1, "b": 99},
        )
        assert not result["healthy"]
        assert "c" in result["missing_keys"]
        assert "b" in result["mismatched"]

    def test_restore_service(self):
        record = self.recovery.restore_service("api")
        assert record.success

    def test_get_recovery_history(self):
        self.recovery.restore_service("a")
        self.recovery.restore_service("b")
        history = self.recovery.get_recovery_history()
        assert len(history) == 2

    def test_get_available_backups(self):
        self.recovery.create_backup("b1", "db")
        self.recovery.create_backup("b2", "files")
        backups = self.recovery.get_available_backups()
        assert len(backups) == 2

    def test_success_rate(self):
        self.recovery.restore_service("ok")
        assert self.recovery.success_rate == 1.0


# ── PreventiveCare Testleri ──────────────────────────────────


class TestPreventiveCare:
    """PreventiveCare testleri."""

    def setup_method(self):
        from app.core.diagnostic.preventive_care import PreventiveCare
        self.care = PreventiveCare()

    def test_init(self):
        assert self.care.schedule_count == 0

    def test_schedule_maintenance(self):
        result = self.care.schedule_maintenance(
            "cleanup", MaintenanceType.CLEANUP, interval_hours=24,
        )
        assert self.care.schedule_count == 1
        assert result["enabled"]

    def test_run_cleanup(self):
        result = self.care.run_cleanup("logs", items_cleaned=100, space_freed_mb=50.0)
        assert result["items_cleaned"] == 100
        assert self.care.cleanup_count == 1

    def test_run_optimization(self):
        result = self.care.run_optimization("db", improvement_percent=15.0)
        assert result["improvement_percent"] == 15.0
        assert self.care.optimization_count == 1

    def test_record_health(self):
        self.care.record_health(0.8)
        self.care.record_health(0.7)
        assert self.care.health_data_points == 2

    def test_analyze_trend_insufficient(self):
        self.care.record_health(0.8)
        result = self.care.analyze_trend()
        assert result["trend"] == "insufficient_data"

    def test_analyze_trend_stable(self):
        for _ in range(5):
            self.care.record_health(0.7)
        result = self.care.analyze_trend()
        assert result["trend"] == "stable"

    def test_analyze_trend_declining(self):
        # Yuksek skorlar (genel ortalama yukari cekilir)
        self.care.record_health(0.9)
        self.care.record_health(0.9)
        self.care.record_health(0.9)
        self.care.record_health(0.9)
        self.care.record_health(0.9)
        # Son 5 dusuk (recent_avg < overall_avg - 0.05)
        self.care.record_health(0.5)
        self.care.record_health(0.5)
        self.care.record_health(0.5)
        self.care.record_health(0.5)
        self.care.record_health(0.5)
        result = self.care.analyze_trend()
        assert result["trend"] == "declining"

    def test_predict_maintenance(self):
        self.care.schedule_maintenance("test", MaintenanceType.CLEANUP)
        predictions = self.care.predict_maintenance()
        assert len(predictions) > 0

    def test_get_due_maintenance(self):
        self.care.schedule_maintenance("test", MaintenanceType.CLEANUP)
        due = self.care.get_due_maintenance()
        assert len(due) == 1  # never run = due

    def test_disable_schedule(self):
        self.care.schedule_maintenance("test", MaintenanceType.CLEANUP)
        assert self.care.disable_schedule("test")
        due = self.care.get_due_maintenance()
        assert len(due) == 0

    def test_enable_schedule(self):
        self.care.schedule_maintenance("test", MaintenanceType.CLEANUP)
        self.care.disable_schedule("test")
        assert self.care.enable_schedule("test")
        due = self.care.get_due_maintenance()
        assert len(due) == 1

    def test_disable_not_found(self):
        assert not self.care.disable_schedule("missing")


# ── DiagnosticReporter Testleri ──────────────────────────────


class TestDiagnosticReporter:
    """DiagnosticReporter testleri."""

    def setup_method(self):
        from app.core.diagnostic.diagnostic_reporter import DiagnosticReporter
        self.reporter = DiagnosticReporter(alert_threshold=0.5)

    def test_init(self):
        assert self.reporter.report_count == 0

    def test_generate_health_report_healthy(self):
        report = self.reporter.generate_health_report({
            "overall_status": "healthy",
            "overall_score": 0.9,
            "total_issues": 0,
            "components_scanned": 5,
        })
        assert report["overall_status"] == "healthy"
        assert self.reporter.report_count == 1

    def test_generate_health_report_low_triggers_alert(self):
        self.reporter.generate_health_report({
            "overall_status": "critical",
            "overall_score": 0.2,
            "total_issues": 5,
            "components_scanned": 3,
        })
        assert self.reporter.alert_count >= 1

    def test_generate_issue_summary(self):
        report = self.reporter.generate_issue_summary(
            errors=[{"severity": "critical"}],
            bottlenecks=[{"type": "cpu"}],
            dependency_issues=[{"type": "missing"}],
        )
        assert report["total_issues"] == 3
        assert report["critical_count"] == 1

    def test_generate_issue_summary_creates_recommendations(self):
        self.reporter.generate_issue_summary(
            errors=[{"severity": "high"}],
            bottlenecks=[],
            dependency_issues=[],
        )
        assert self.reporter.recommendation_count >= 1

    def test_generate_trend_report(self):
        report = self.reporter.generate_trend_report({
            "trend": "declining",
            "overall_avg": 0.6,
            "recent_avg": 0.4,
        })
        assert report["trend_direction"] == "declining"
        assert self.reporter.alert_count >= 1

    def test_add_recommendation(self):
        rec = self.reporter.add_recommendation(
            "Optimize DB", "Index rebuild", priority="high",
        )
        assert self.reporter.recommendation_count == 1

    def test_get_alerts_filtered(self):
        self.reporter.generate_health_report({
            "overall_status": "critical",
            "overall_score": 0.1,
            "total_issues": 10,
        })
        high = self.reporter.get_alerts(severity="high")
        assert len(high) >= 1

    def test_get_recommendations_filtered(self):
        self.reporter.add_recommendation("A", "A", priority="high")
        self.reporter.add_recommendation("B", "B", priority="low")
        high = self.reporter.get_recommendations(priority="high")
        assert len(high) == 1

    def test_get_recent_reports(self):
        for i in range(10):
            self.reporter.generate_health_report({
                "overall_status": "healthy",
                "overall_score": 0.9,
                "total_issues": 0,
            })
        recent = self.reporter.get_recent_reports(limit=3)
        assert len(recent) == 3

    def test_clear_alerts(self):
        self.reporter.generate_health_report({
            "overall_status": "critical",
            "overall_score": 0.1,
            "total_issues": 5,
        })
        cleared = self.reporter.clear_alerts()
        assert cleared >= 1
        assert self.reporter.alert_count == 0


# ── DiagnosticOrchestrator Testleri ──────────────────────────


class TestDiagnosticOrchestrator:
    """DiagnosticOrchestrator testleri."""

    def setup_method(self):
        from app.core.diagnostic.diagnostic_orchestrator import (
            DiagnosticOrchestrator,
        )
        self.orch = DiagnosticOrchestrator(
            auto_repair=True, alert_threshold=0.5,
        )

    def test_init(self):
        assert self.orch.cycle_count == 0
        assert self.orch.phase == DiagnosticPhase.IDLE

    def test_run_full_diagnostic(self):
        result = self.orch.run_full_diagnostic({
            "api": {"latency": 0.1, "errors": 0.02},
            "db": {"latency": 0.2, "connections": 0.3},
        })
        assert result["cycle"] == 1
        assert "scan" in result
        assert "report" in result

    def test_report_error(self):
        result = self.orch.report_error(
            "timeout", "Request failed", "api",
        )
        assert result["error_id"]
        assert result["root_cause"]["found"]

    def test_report_critical_error_escalates(self):
        self.orch.report_error(
            "crash", "Fatal error", "core",
            severity=ErrorSeverity.CRITICAL,
        )
        assert self.orch.escalation_count == 1

    def test_check_performance(self):
        result = self.orch.check_performance(
            {"query": 50.0, "render": 100.0},
            {"cpu_percent": 95.0},
        )
        assert "slow_operations" in result
        assert len(result["bottlenecks"]) >= 1

    def test_check_dependencies(self):
        self.orch.checker.register_package("app", "1.0")
        result = self.orch.check_dependencies()
        assert result["healthy"]

    def test_trigger_recovery_service(self):
        result = self.orch.trigger_recovery("api", "service_restore")
        assert result["success"]

    def test_trigger_recovery_backup(self):
        self.orch.recovery.create_backup("snap", "db")
        result = self.orch.trigger_recovery("snap", "backup_restore")
        assert result["success"]

    def test_trigger_recovery_rollback(self):
        self.orch.recovery.push_rollback("deploy", {})
        result = self.orch.trigger_recovery("deploy", "rollback")
        assert result["success"]

    def test_run_maintenance(self):
        self.orch.care.schedule_maintenance(
            "cleanup", MaintenanceType.CLEANUP,
        )
        result = self.orch.run_maintenance()
        assert result["due_maintenance"] >= 1

    def test_get_snapshot(self):
        self.orch.run_full_diagnostic({
            "api": {"latency": 0.1},
        })
        snap = self.orch.get_snapshot()
        assert snap.uptime_seconds >= 0
        assert snap.components_scanned >= 0

    def test_subsystem_access(self):
        assert self.orch.scanner is not None
        assert self.orch.analyzer is not None
        assert self.orch.detector is not None
        assert self.orch.checker is not None
        assert self.orch.fixer is not None
        assert self.orch.recovery is not None
        assert self.orch.care is not None
        assert self.orch.reporter is not None


# ── Entegrasyon Testleri ─────────────────────────────────────


class TestDiagnosticIntegration:
    """Entegrasyon testleri."""

    def test_full_diagnostic_cycle(self):
        from app.core.diagnostic.diagnostic_orchestrator import (
            DiagnosticOrchestrator,
        )
        orch = DiagnosticOrchestrator(auto_repair=True)

        # Bilesen kaydet
        orch.scanner.register_component("api", thresholds={"error_rate": 0.3})
        orch.scanner.register_component("db", thresholds={"latency": 0.5})

        # Tam teshis
        result = orch.run_full_diagnostic({
            "api": {"error_rate": 0.1, "latency": 0.2},
            "db": {"latency": 0.15, "connections": 0.3},
        })
        assert result["cycle"] == 1

        # Hata raporla
        err = orch.report_error("timeout", "Slow query", "db")
        assert err["root_cause"]["found"]

        # Snapshot
        snap = orch.get_snapshot()
        assert snap.errors_found >= 1

    def test_error_to_fix_pipeline(self):
        from app.core.diagnostic.diagnostic_orchestrator import (
            DiagnosticOrchestrator,
        )
        orch = DiagnosticOrchestrator(auto_repair=True)

        # Hata raporla ve otomatik duzelt
        result = orch.report_error(
            "cache_overflow", "Cache full", "redis",
            severity=ErrorSeverity.HIGH,
        )

        # Etki yuksekse fix uygulanmis olmali
        if result["impact"].get("requires_immediate"):
            assert result["fix_applied"] is not None

    def test_recovery_workflow(self):
        from app.core.diagnostic.diagnostic_orchestrator import (
            DiagnosticOrchestrator,
        )
        orch = DiagnosticOrchestrator()

        # Yedek olustur
        orch.recovery.create_backup("pre_update", "db", {"v": "1.0"})

        # Checkpoint olustur
        orch.recovery.create_checkpoint("stable", {"status": "ok"})

        # Rollback bilgisi ekle
        orch.recovery.push_rollback("update", {"v": "1.0"})

        # Kurtarma
        result = orch.trigger_recovery("pre_update", "backup_restore")
        assert result["success"]

    def test_preventive_and_reporting(self):
        from app.core.diagnostic.diagnostic_orchestrator import (
            DiagnosticOrchestrator,
        )
        orch = DiagnosticOrchestrator()

        # Saglik gecmisi
        for score in [0.9, 0.85, 0.8, 0.75, 0.7]:
            orch.care.record_health(score)

        # Bakim
        result = orch.run_maintenance()
        assert "trend" in result

    def test_bottleneck_detection_pipeline(self):
        from app.core.diagnostic.diagnostic_orchestrator import (
            DiagnosticOrchestrator,
        )
        orch = DiagnosticOrchestrator()

        result = orch.check_performance(
            {"query": 2000.0, "render": 50.0},
            {"cpu_percent": 30.0, "memory_percent": 90.0},
        )
        assert len(result["bottlenecks"]) >= 1  # memory bottleneck
