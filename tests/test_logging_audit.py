"""ATLAS Logging & Audit Trail testleri."""

import time

import pytest

from app.models.logging_models import (
    LogLevel,
    LogFormat,
    AuditAction,
    ComplianceStandard,
    ExportTarget,
    RetentionPolicy,
    LogRecord,
    AuditRecord,
    ComplianceRecord,
    LoggingSnapshot,
)
from app.core.logging import (
    LogManager,
    LogFormatter,
    LogAggregator,
    AuditRecorder,
    LogSearcher,
    LogAnalyzer,
    ComplianceReporter,
    LogExporter,
    LoggingOrchestrator,
)


# ==================== Model Testleri ====================


class TestLoggingModels:
    """Model testleri."""

    def test_log_level_enum(self):
        assert LogLevel.DEBUG == "debug"
        assert LogLevel.INFO == "info"
        assert LogLevel.ERROR == "error"
        assert LogLevel.CRITICAL == "critical"

    def test_log_format_enum(self):
        assert LogFormat.JSON == "json"
        assert LogFormat.PLAIN == "plain"
        assert LogFormat.SYSLOG == "syslog"

    def test_audit_action_enum(self):
        assert AuditAction.CREATE == "create"
        assert AuditAction.DELETE == "delete"
        assert AuditAction.LOGIN == "login"

    def test_compliance_standard_enum(self):
        assert ComplianceStandard.GDPR == "gdpr"
        assert ComplianceStandard.SOC2 == "soc2"
        assert ComplianceStandard.HIPAA == "hipaa"

    def test_export_target_enum(self):
        assert ExportTarget.FILE == "file"
        assert ExportTarget.CLOUD == "cloud"
        assert ExportTarget.SIEM == "siem"

    def test_retention_policy_enum(self):
        assert RetentionPolicy.SHORT == "short"
        assert RetentionPolicy.PERMANENT == "permanent"

    def test_log_record_defaults(self):
        r = LogRecord(message="test")
        assert r.log_id
        assert r.level == LogLevel.INFO

    def test_audit_record_defaults(self):
        r = AuditRecord(actor="admin")
        assert r.audit_id
        assert r.action == AuditAction.READ

    def test_compliance_record_defaults(self):
        r = ComplianceRecord()
        assert r.record_id
        assert r.status == "compliant"

    def test_logging_snapshot_defaults(self):
        s = LoggingSnapshot()
        assert s.snapshot_id
        assert s.total_logs == 0


# ==================== LogManager Testleri ====================


class TestLogManager:
    """LogManager testleri."""

    def test_log_info(self):
        m = LogManager()
        r = m.log(LogLevel.INFO, "hello")
        assert r is not None
        assert r["level"] == "info"
        assert m.log_count == 1

    def test_log_filtered_by_level(self):
        m = LogManager(level=LogLevel.WARNING)
        r = m.log(LogLevel.DEBUG, "debug msg")
        assert r is None
        assert m.log_count == 0

    def test_shorthand_methods(self):
        m = LogManager(level=LogLevel.DEBUG)
        m.debug("d")
        m.info("i")
        m.warning("w")
        m.error("e")
        m.critical("c")
        assert m.log_count == 5

    def test_context_injection(self):
        m = LogManager()
        m.set_context("app", "atlas")
        r = m.info("test")
        assert r["context"]["app"] == "atlas"

    def test_clear_context(self):
        m = LogManager()
        m.set_context("k", "v")
        m.clear_context()
        r = m.info("test")
        assert "k" not in r["context"]

    def test_local_context_merge(self):
        m = LogManager()
        m.set_context("global", "yes")
        r = m.info("test", context={"local": "yes"})
        assert r["context"]["global"] == "yes"
        assert r["context"]["local"] == "yes"

    def test_set_level(self):
        m = LogManager(level=LogLevel.INFO)
        m.set_level(LogLevel.DEBUG)
        assert m.current_level == LogLevel.DEBUG

    def test_add_handler(self):
        m = LogManager()
        m.add_handler("file")
        m.add_handler("console")
        assert m.handler_count == 2

    def test_add_handler_dedup(self):
        m = LogManager()
        m.add_handler("file")
        m.add_handler("file")
        assert m.handler_count == 1

    def test_rotation(self):
        m = LogManager(max_size=10)
        for i in range(15):
            m.info(f"msg {i}")
        assert m.log_count <= 10
        assert m.rotation_count >= 1

    def test_get_logs_all(self):
        m = LogManager()
        m.info("a")
        m.error("b")
        logs = m.get_logs()
        assert len(logs) == 2

    def test_get_logs_by_level(self):
        m = LogManager()
        m.info("a")
        m.error("b")
        logs = m.get_logs(level=LogLevel.ERROR)
        assert len(logs) == 1

    def test_get_logs_by_source(self):
        m = LogManager()
        m.info("a", source="app")
        m.info("b", source="db")
        logs = m.get_logs(source="app")
        assert len(logs) == 1

    def test_clear(self):
        m = LogManager()
        m.info("a")
        m.info("b")
        count = m.clear()
        assert count == 2
        assert m.log_count == 0


# ==================== LogFormatter Testleri ====================


class TestLogFormatter:
    """LogFormatter testleri."""

    def test_format_json(self):
        f = LogFormatter()
        r = f.format_json({"level": "info", "message": "hi", "timestamp": time.time()})
        assert '"level"' in r
        assert '"message"' in r
        assert f.formatted_count == 1

    def test_format_plain(self):
        f = LogFormatter()
        r = f.format_plain({"level": "info", "message": "hello", "source": "app", "timestamp": time.time()})
        assert "[INFO]" in r
        assert "hello" in r
        assert "[app]" in r

    def test_format_csv(self):
        f = LogFormatter()
        r = f.format_csv({"level": "error", "message": "bad", "source": "db", "timestamp": time.time()})
        assert "error" in r
        assert "bad" in r

    def test_format_dispatch(self):
        f = LogFormatter(default_format="plain")
        r = f.format({"level": "info", "message": "test", "timestamp": time.time()})
        assert "[INFO]" in r

    def test_format_explicit_type(self):
        f = LogFormatter()
        r = f.format({"level": "info", "message": "x", "timestamp": time.time()}, fmt="json")
        assert '"level"' in r

    def test_register_custom_format(self):
        f = LogFormatter()
        f.register_format("simple", "{level}: {message}")
        r = f.format({"level": "info", "message": "hi"}, fmt="simple")
        assert r == "info: hi"
        assert f.custom_format_count == 1

    def test_get_color(self):
        f = LogFormatter()
        assert f.get_color("error") == "red"
        assert f.get_color("info") == "green"

    def test_set_color(self):
        f = LogFormatter()
        f.set_color("info", "blue")
        assert f.get_color("info") == "blue"

    def test_get_color_unknown(self):
        f = LogFormatter()
        assert f.get_color("unknown") == "default"

    def test_format_batch(self):
        f = LogFormatter()
        records = [
            {"level": "info", "message": "a", "timestamp": time.time()},
            {"level": "error", "message": "b", "timestamp": time.time()},
        ]
        results = f.format_batch(records, "json")
        assert len(results) == 2

    def test_no_timestamp(self):
        f = LogFormatter(include_timestamp=False)
        r = f.format_plain({"level": "info", "message": "hi"})
        assert "[INFO]" in r


# ==================== LogAggregator Testleri ====================


class TestLogAggregator:
    """LogAggregator testleri."""

    def test_register_source(self):
        a = LogAggregator()
        s = a.register_source("app", "application")
        assert s["name"] == "app"
        assert a.source_count == 1

    def test_collect(self):
        a = LogAggregator()
        a.register_source("app")
        r = a.collect("app", {"level": "info", "message": "hi"})
        assert r is True
        assert a.total_collected == 1

    def test_deduplication(self):
        a = LogAggregator(dedup_window=60)
        record = {"level": "info", "message": "same", "source": "app"}
        a.collect("app", record)
        r = a.collect("app", record)
        assert r is False
        assert a.duplicates_skipped == 1

    def test_flush(self):
        a = LogAggregator(buffer_size=100)
        a.collect("app", {"level": "info", "message": "a"})
        a.collect("app", {"level": "info", "message": "b"})
        batch = a.flush()
        assert len(batch) == 2
        assert a.buffer_count == 0
        assert a.forwarded_count == 2

    def test_auto_flush_on_full(self):
        a = LogAggregator(buffer_size=2)
        a.collect("app", {"level": "info", "message": "a"})
        a.collect("x", {"level": "info", "message": "b"})
        assert a.forwarded_count >= 2

    def test_merge_logs(self):
        a = LogAggregator()
        list1 = [{"timestamp": 2, "message": "b"}]
        list2 = [{"timestamp": 1, "message": "a"}]
        merged = a.merge_logs(list1, list2)
        assert merged[0]["message"] == "a"
        assert merged[1]["message"] == "b"

    def test_get_buffer(self):
        a = LogAggregator()
        a.collect("app", {"level": "info", "message": "x"})
        buf = a.get_buffer()
        assert len(buf) == 1

    def test_get_source_stats(self):
        a = LogAggregator()
        a.register_source("app")
        a.collect("app", {"level": "info", "message": "x"})
        stats = a.get_source_stats()
        assert stats["app"]["log_count"] == 1

    def test_cleanup_hashes(self):
        a = LogAggregator()
        a.collect("app", {"level": "info", "message": "old"})
        # Manipulate to make hash old
        for k in list(a._seen_hashes.keys()):
            a._seen_hashes[k] = time.time() - 400
        cleaned = a.cleanup_hashes(max_age=300)
        assert cleaned >= 1


# ==================== AuditRecorder Testleri ====================


class TestAuditRecorder:
    """AuditRecorder testleri."""

    def test_record(self):
        a = AuditRecorder()
        r = a.record("create", "admin", "user:1")
        assert r["action"] == "create"
        assert r["actor"] == "admin"
        assert r["hash"]
        assert a.record_count == 1

    def test_record_with_states(self):
        a = AuditRecorder()
        r = a.record(
            "update", "admin", "user:1",
            before={"name": "old"},
            after={"name": "new"},
        )
        assert r["before"]["name"] == "old"
        assert r["after"]["name"] == "new"

    def test_chain_integrity(self):
        a = AuditRecorder()
        a.record("create", "u1", "r1")
        a.record("update", "u1", "r1")
        a.record("delete", "u2", "r2")
        result = a.verify_chain()
        assert result["valid"] is True
        assert result["count"] == 3

    def test_get_records_all(self):
        a = AuditRecorder()
        a.record("create", "u1", "r1")
        a.record("read", "u2", "r2")
        recs = a.get_records()
        assert len(recs) == 2

    def test_get_records_by_actor(self):
        a = AuditRecorder()
        a.record("create", "u1", "r1")
        a.record("create", "u2", "r2")
        recs = a.get_records(actor="u1")
        assert len(recs) == 1

    def test_get_records_by_action(self):
        a = AuditRecorder()
        a.record("create", "u1", "r1")
        a.record("delete", "u1", "r2")
        recs = a.get_records(action="delete")
        assert len(recs) == 1

    def test_get_records_by_resource(self):
        a = AuditRecorder()
        a.record("create", "u1", "user:1")
        a.record("create", "u1", "user:2")
        recs = a.get_records(resource="user:1")
        assert len(recs) == 1

    def test_get_actor_summary(self):
        a = AuditRecorder()
        a.record("create", "admin", "r1")
        a.record("update", "admin", "r1")
        a.record("read", "user", "r1")
        summary = a.get_actor_summary()
        assert summary["admin"] == 2
        assert summary["user"] == 1

    def test_get_changes(self):
        a = AuditRecorder()
        a.record("create", "u1", "doc:1", after={"title": "new"})
        a.record("update", "u1", "doc:1", before={"title": "new"}, after={"title": "updated"})
        changes = a.get_changes("doc:1")
        assert len(changes) == 2

    def test_get_timeline(self):
        a = AuditRecorder()
        a.record("create", "u1", "r1")
        a.record("read", "u1", "r1")
        now = time.time()
        tl = a.get_timeline(start=now - 10)
        assert len(tl) == 2

    def test_actor_count(self):
        a = AuditRecorder()
        a.record("create", "u1", "r1")
        a.record("create", "u2", "r2")
        assert a.actor_count == 2

    def test_chain_valid_property(self):
        a = AuditRecorder()
        a.record("create", "u1", "r1")
        assert a.chain_valid is True


# ==================== LogSearcher Testleri ====================


class TestLogSearcher:
    """LogSearcher testleri."""

    def test_index_and_search(self):
        s = LogSearcher()
        s.index_logs([
            {"message": "user login", "level": "info"},
            {"message": "database error", "level": "error"},
        ])
        results = s.search("login")
        assert len(results) == 1
        assert s.indexed_count == 2

    def test_search_case_insensitive(self):
        s = LogSearcher()
        s.index_logs([{"message": "Hello World"}])
        results = s.search("hello")
        assert len(results) == 1

    def test_search_case_sensitive(self):
        s = LogSearcher()
        s.index_logs([{"message": "Hello World"}])
        results = s.search("hello", case_sensitive=True)
        assert len(results) == 0

    def test_filter_by_level(self):
        s = LogSearcher()
        s.index_logs([
            {"level": "info", "message": "a"},
            {"level": "error", "message": "b"},
        ])
        results = s.filter_by_level("error")
        assert len(results) == 1

    def test_filter_by_time(self):
        s = LogSearcher()
        now = time.time()
        s.index_logs([
            {"timestamp": now - 100, "message": "old"},
            {"timestamp": now, "message": "new"},
        ])
        results = s.filter_by_time(start=now - 50)
        assert len(results) == 1

    def test_filter_by_source(self):
        s = LogSearcher()
        s.index_logs([
            {"source": "app", "message": "a"},
            {"source": "db", "message": "b"},
        ])
        results = s.filter_by_source("db")
        assert len(results) == 1

    def test_regex_search(self):
        s = LogSearcher()
        s.index_logs([
            {"message": "error code 404"},
            {"message": "error code 500"},
            {"message": "success"},
        ])
        results = s.regex_search(r"error code \d{3}")
        assert len(results) == 2

    def test_regex_search_invalid(self):
        s = LogSearcher()
        s.index_logs([{"message": "test"}])
        results = s.regex_search("[invalid")
        assert results == []

    def test_combined_search(self):
        s = LogSearcher()
        s.index_logs([
            {"level": "error", "source": "app", "message": "fail"},
            {"level": "info", "source": "app", "message": "ok"},
            {"level": "error", "source": "db", "message": "fail"},
        ])
        results = s.combined_search(
            query="fail", level="error", source="app",
        )
        assert len(results) == 1

    def test_clear_index(self):
        s = LogSearcher()
        s.index_logs([{"message": "x"}])
        count = s.clear_index()
        assert count == 1
        assert s.indexed_count == 0

    def test_search_count(self):
        s = LogSearcher()
        s.index_logs([{"message": "x"}])
        s.search("x")
        s.filter_by_level("info")
        assert s.search_count == 2


# ==================== LogAnalyzer Testleri ====================


class TestLogAnalyzer:
    """LogAnalyzer testleri."""

    def test_detect_patterns(self):
        a = LogAnalyzer()
        logs = [
            {"message": "connect"},
            {"message": "connect"},
            {"message": "connect"},
            {"message": "disconnect"},
        ]
        patterns = a.detect_patterns(logs)
        assert len(patterns) >= 1
        assert patterns[0]["message"] == "connect"
        assert patterns[0]["count"] == 3

    def test_detect_patterns_min_freq(self):
        a = LogAnalyzer()
        logs = [{"message": "a"}, {"message": "b"}]
        patterns = a.detect_patterns(logs, min_frequency=3)
        assert len(patterns) == 0

    def test_detect_anomalies(self):
        a = LogAnalyzer(anomaly_threshold=1.5)
        logs = (
            [{"level": "error"}] * 20
            + [{"level": "info"}] * 2
        )
        anomalies = a.detect_anomalies(logs)
        assert len(anomalies) >= 1
        assert a.anomaly_count >= 1

    def test_detect_anomalies_empty(self):
        a = LogAnalyzer()
        assert a.detect_anomalies([]) == []

    def test_detect_error_spike(self):
        a = LogAnalyzer()
        logs = (
            [{"level": "error"}] * 8
            + [{"level": "info"}] * 2
        )
        anomalies = a.detect_anomalies(logs)
        types = [an["type"] for an in anomalies]
        assert "error_spike" in types

    def test_cluster_errors(self):
        a = LogAnalyzer()
        logs = [
            {"level": "error", "message": "timeout connecting to db", "source": "app", "timestamp": 1},
            {"level": "error", "message": "timeout connecting to db", "source": "app", "timestamp": 2},
            {"level": "error", "message": "auth failed for user", "source": "auth", "timestamp": 3},
        ]
        clusters = a.cluster_errors(logs)
        assert len(clusters) == 2
        assert clusters[0]["count"] == 2

    def test_cluster_errors_empty(self):
        a = LogAnalyzer()
        assert a.cluster_errors([]) == []

    def test_cluster_errors_no_errors(self):
        a = LogAnalyzer()
        logs = [{"level": "info", "message": "ok"}]
        assert a.cluster_errors(logs) == []

    def test_analyze_trends(self):
        a = LogAnalyzer()
        now = time.time()
        logs = [
            {"timestamp": now - 120},
            {"timestamp": now - 60},
            {"timestamp": now},
        ]
        t = a.analyze_trends(logs, bucket_size=60)
        assert t["total_logs"] == 3
        assert t["trend"] in ("stable", "increasing", "decreasing")

    def test_analyze_trends_empty(self):
        a = LogAnalyzer()
        t = a.analyze_trends([])
        assert t["trend"] == "stable"

    def test_suggest_root_cause(self):
        a = LogAnalyzer()
        logs = [
            {"message": "timeout connecting to service"},
            {"message": "timeout on database query"},
        ]
        hints = a.suggest_root_cause(logs)
        keywords = [h["keyword"] for h in hints]
        assert "timeout" in keywords

    def test_suggest_root_cause_concentrated(self):
        a = LogAnalyzer()
        logs = [
            {"message": "error", "source": "db"},
            {"message": "error", "source": "db"},
            {"message": "error", "source": "db"},
        ]
        hints = a.suggest_root_cause(logs)
        keywords = [h["keyword"] for h in hints]
        assert "concentrated_source" in keywords

    def test_suggest_root_cause_empty(self):
        a = LogAnalyzer()
        assert a.suggest_root_cause([]) == []

    def test_analysis_count(self):
        a = LogAnalyzer()
        a.detect_patterns([])
        a.detect_anomalies([])
        assert a.analysis_count == 2


# ==================== ComplianceReporter Testleri ====================


class TestComplianceReporter:
    """ComplianceReporter testleri."""

    def test_check_gdpr_compliant(self):
        c = ComplianceReporter()
        r = c.check_compliance("gdpr", {
            "data_encryption": True,
            "access_logging": True,
            "data_retention": True,
        })
        assert r["status"] == "compliant"
        assert r["compliance_pct"] == 100.0
        assert c.report_count == 1

    def test_check_gdpr_non_compliant(self):
        c = ComplianceReporter()
        r = c.check_compliance("gdpr", {
            "data_encryption": True,
            "access_logging": False,
        })
        assert r["status"] == "non_compliant"
        assert r["non_compliant"] >= 1

    def test_check_soc2(self):
        c = ComplianceReporter()
        r = c.check_compliance("soc2", {
            "access_control": True,
            "audit_trail": True,
            "change_management": True,
        })
        assert r["status"] == "compliant"

    def test_log_access(self):
        c = ComplianceReporter()
        r = c.log_access("admin", "user_data", "read")
        assert r["actor"] == "admin"
        assert r["authorized"] is True
        assert c.access_log_count == 1

    def test_log_unauthorized_access(self):
        c = ComplianceReporter()
        c.log_access("hacker", "secrets", "read", authorized=False)
        summary = c.get_access_summary()
        assert summary["unauthorized"] == 1

    def test_set_retention_policy(self):
        c = ComplianceReporter()
        p = c.set_retention_policy("logs", 90, "log_data")
        assert p["retention_days"] == 90
        assert c.policy_count == 1

    def test_get_policy(self):
        c = ComplianceReporter()
        c.set_retention_policy("logs", 90)
        p = c.get_policy("logs")
        assert p is not None
        assert p["retention_days"] == 90

    def test_get_policy_none(self):
        c = ComplianceReporter()
        assert c.get_policy("nope") is None

    def test_generate_audit_report(self):
        c = ComplianceReporter()
        records = [
            {"action": "create", "actor": "admin"},
            {"action": "read", "actor": "user"},
            {"action": "create", "actor": "admin"},
        ]
        r = c.generate_audit_report(records)
        assert r["total_records"] == 3
        assert r["unique_actors"] == 2

    def test_get_access_summary(self):
        c = ComplianceReporter()
        c.log_access("u1", "r1")
        c.log_access("u2", "r1")
        c.log_access("u3", "r2", authorized=False)
        s = c.get_access_summary()
        assert s["total_access"] == 3
        assert s["unique_actors"] == 3
        assert s["unauthorized"] == 1

    def test_add_rule(self):
        c = ComplianceReporter()
        c.add_rule("custom", "c1", "my_rule", "desc")
        r = c.check_compliance("custom", {"my_rule": True})
        assert r["compliance_pct"] == 100.0


# ==================== LogExporter Testleri ====================


class TestLogExporter:
    """LogExporter testleri."""

    def test_register_target(self):
        e = LogExporter()
        t = e.register_target("s3", "cloud")
        assert t["name"] == "s3"
        assert e.target_count == 1

    def test_export_to_file_json(self):
        e = LogExporter()
        logs = [{"level": "info", "message": "hi"}]
        r = e.export_to_file(logs, "out.json", "json")
        assert r["type"] == "file"
        assert r["record_count"] == 1
        assert e.export_count == 1

    def test_export_to_file_csv(self):
        e = LogExporter()
        logs = [{"timestamp": "t", "level": "info", "source": "app", "message": "test"}]
        r = e.export_to_file(logs, "out.csv", "csv")
        assert r["format"] == "csv"

    def test_export_to_cloud(self):
        e = LogExporter()
        e.register_target("s3", "cloud")
        logs = [{"message": "hi"}]
        r = e.export_to_cloud(logs, "s3")
        assert r["success"] is True

    def test_export_to_cloud_no_target(self):
        e = LogExporter()
        r = e.export_to_cloud([], "nope")
        assert r["success"] is False

    def test_export_to_siem(self):
        e = LogExporter()
        e.register_target("splunk", "siem")
        logs = [{"level": "error", "message": "bad"}]
        r = e.export_to_siem(logs, "splunk")
        assert r["success"] is True
        assert r["formatted_count"] == 1

    def test_export_to_siem_no_target(self):
        e = LogExporter()
        r = e.export_to_siem([], "nope")
        assert r["success"] is False

    def test_archive(self):
        e = LogExporter()
        logs = [{"level": "info", "message": "test"}]
        r = e.archive(logs, "arc1")
        assert r["name"] == "arc1"
        assert r["compressed"] is True
        assert r["compression_ratio"] > 0
        assert e.archive_count == 1

    def test_archive_no_compress(self):
        e = LogExporter()
        logs = [{"message": "x"}]
        r = e.archive(logs, compress=False)
        assert r["compressed"] is False

    def test_get_export_history(self):
        e = LogExporter()
        e.export_to_file([], "a.json")
        e.archive([])
        history = e.get_export_history()
        assert len(history) == 2

    def test_get_export_history_filtered(self):
        e = LogExporter()
        e.export_to_file([], "a.json")
        e.archive([])
        history = e.get_export_history("file")
        assert len(history) == 1

    def test_get_archive(self):
        e = LogExporter()
        e.archive([], "test_arc")
        a = e.get_archive("test_arc")
        assert a is not None

    def test_get_archive_none(self):
        e = LogExporter()
        assert e.get_archive("nope") is None


# ==================== LoggingOrchestrator Testleri ====================


class TestLoggingOrch:
    """LoggingOrchestrator testleri."""

    def test_init(self):
        o = LoggingOrchestrator()
        assert o.manager is not None
        assert o.audit is not None

    def test_log(self):
        o = LoggingOrchestrator()
        r = o.log(LogLevel.INFO, "test", source="app")
        assert r is not None
        assert r["level"] == "info"

    def test_log_indexes(self):
        o = LoggingOrchestrator()
        o.log(LogLevel.INFO, "indexed")
        assert o.searcher.indexed_count == 1

    def test_log_error_alert(self):
        o = LoggingOrchestrator()
        o.log(LogLevel.ERROR, "error!")
        assert o.alert_count == 1

    def test_log_critical_alert(self):
        o = LoggingOrchestrator()
        o.log(LogLevel.CRITICAL, "critical!")
        assert o.alert_count == 1

    def test_audit_action(self):
        o = LoggingOrchestrator()
        r = o.audit_action("create", "admin", "doc:1")
        assert r["action"] == "create"
        assert o.audit.record_count == 1
        assert o.compliance.access_log_count == 1

    def test_search_logs(self):
        o = LoggingOrchestrator()
        o.log(LogLevel.INFO, "user login")
        o.log(LogLevel.ERROR, "db error")
        results = o.search_logs(query="login")
        assert len(results) == 1

    def test_analyze(self):
        o = LoggingOrchestrator()
        o.log(LogLevel.INFO, "a")
        o.log(LogLevel.INFO, "a")
        o.log(LogLevel.ERROR, "b")
        r = o.analyze()
        assert r["total_logs"] >= 3

    def test_get_analytics(self):
        o = LoggingOrchestrator()
        o.log(LogLevel.INFO, "x")
        o.audit_action("read", "u1", "r1")
        a = o.get_analytics()
        assert a["total_logs"] == 1
        assert a["total_audits"] == 1

    def test_snapshot(self):
        o = LoggingOrchestrator()
        o.log(LogLevel.INFO, "x")
        s = o.snapshot()
        assert s["logs"] == 1
        assert s["chain_valid"] is True
        assert s["uptime"] >= 0


# ==================== Config Testleri ====================


class TestLoggingConfig:
    """Config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.logging_enabled is True
        assert s.log_level == "info"
        assert s.log_retention_days == 90
        assert s.audit_enabled is True
        assert s.export_format == "json"
