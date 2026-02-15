"""ATLAS Observability & Tracing testleri."""

import pytest

from app.core.observability import (
    AlertManager,
    AnomalyDetector,
    DashboardBuilder,
    HealthChecker,
    MetricsCollector,
    ObservabilityOrchestrator,
    SLAMonitor,
    SpanCollector,
    TraceManager,
)
from app.models.observability import (
    AlertRecord,
    AlertSeverity,
    AnomalyType,
    HealthStatus,
    MetricRecord,
    MetricType,
    ObservabilitySnapshot,
    SLALevel,
    TraceRecord,
    TraceStatus,
)


# ===================== Models =====================


class TestObservabilityModels:
    """Model testleri."""

    def test_trace_status_enum(self):
        assert TraceStatus.ACTIVE == "active"
        assert TraceStatus.COMPLETED == "completed"
        assert TraceStatus.ERROR == "error"
        assert TraceStatus.TIMEOUT == "timeout"
        assert TraceStatus.CANCELLED == "cancelled"
        assert TraceStatus.SAMPLED_OUT == "sampled_out"

    def test_metric_type_enum(self):
        assert MetricType.COUNTER == "counter"
        assert MetricType.GAUGE == "gauge"
        assert MetricType.HISTOGRAM == "histogram"
        assert MetricType.SUMMARY == "summary"
        assert MetricType.RATE == "rate"
        assert MetricType.DISTRIBUTION == "distribution"

    def test_health_status_enum(self):
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"
        assert HealthStatus.UNKNOWN == "unknown"
        assert HealthStatus.MAINTENANCE == "maintenance"
        assert HealthStatus.STARTING == "starting"

    def test_alert_severity_enum(self):
        assert AlertSeverity.INFO == "info"
        assert AlertSeverity.WARNING == "warning"
        assert AlertSeverity.ERROR == "error"
        assert AlertSeverity.CRITICAL == "critical"
        assert AlertSeverity.EMERGENCY == "emergency"
        assert AlertSeverity.RESOLVED == "resolved"

    def test_anomaly_type_enum(self):
        assert AnomalyType.SPIKE == "spike"
        assert AnomalyType.DROP == "drop"
        assert AnomalyType.TREND == "trend"
        assert AnomalyType.SEASONAL == "seasonal"
        assert AnomalyType.OUTLIER == "outlier"
        assert AnomalyType.PATTERN_BREAK == "pattern_break"

    def test_sla_level_enum(self):
        assert SLALevel.PLATINUM == "platinum"
        assert SLALevel.GOLD == "gold"
        assert SLALevel.SILVER == "silver"
        assert SLALevel.BRONZE == "bronze"
        assert SLALevel.BASIC == "basic"
        assert SLALevel.CUSTOM == "custom"

    def test_trace_record(self):
        r = TraceRecord(name="api_call")
        assert r.name == "api_call"
        assert r.status == TraceStatus.ACTIVE
        assert r.span_count == 0
        assert len(r.trace_id) == 8

    def test_trace_record_custom(self):
        r = TraceRecord(
            name="db_query",
            status=TraceStatus.COMPLETED,
            span_count=5,
            duration_ms=150.0,
        )
        assert r.status == TraceStatus.COMPLETED
        assert r.span_count == 5
        assert r.duration_ms == 150.0

    def test_metric_record(self):
        r = MetricRecord(name="requests_total")
        assert r.name == "requests_total"
        assert r.metric_type == MetricType.COUNTER
        assert r.value == 0.0
        assert len(r.metric_id) == 8

    def test_metric_record_custom(self):
        r = MetricRecord(
            name="cpu_usage",
            metric_type=MetricType.GAUGE,
            value=75.5,
            labels={"host": "web1"},
        )
        assert r.metric_type == MetricType.GAUGE
        assert r.labels["host"] == "web1"

    def test_alert_record(self):
        r = AlertRecord(name="high_cpu")
        assert r.name == "high_cpu"
        assert r.severity == AlertSeverity.WARNING
        assert r.acknowledged is False
        assert len(r.alert_id) == 8

    def test_alert_record_custom(self):
        r = AlertRecord(
            name="disk_full",
            severity=AlertSeverity.CRITICAL,
            message="Disk %95 dolu",
        )
        assert r.severity == AlertSeverity.CRITICAL
        assert "Disk" in r.message

    def test_observability_snapshot(self):
        s = ObservabilitySnapshot(
            total_traces=100,
            total_metrics=50,
            total_alerts=5,
            health_status=HealthStatus.HEALTHY,
        )
        assert s.total_traces == 100
        assert s.health_status == HealthStatus.HEALTHY
        assert s.sla_compliance == 100.0


# ===================== TraceManager =====================


class TestTraceManager:
    """TraceManager testleri."""

    def test_init(self):
        tm = TraceManager()
        assert tm.active_trace_count == 0
        assert tm.completed_trace_count == 0
        assert tm.sampling_rate == 1.0

    def test_custom_sampling(self):
        tm = TraceManager(sampling_rate=0.5)
        assert tm.sampling_rate == 0.5

    def test_sampling_clamp(self):
        tm = TraceManager(sampling_rate=2.0)
        assert tm.sampling_rate == 1.0
        tm2 = TraceManager(sampling_rate=-1.0)
        assert tm2.sampling_rate == 0.0

    def test_start_trace(self):
        tm = TraceManager()
        r = tm.start_trace("api_call")
        assert r["sampled"] is True
        assert r["trace_id"] != ""
        assert tm.active_trace_count == 1

    def test_end_trace(self):
        tm = TraceManager()
        r = tm.start_trace("api_call")
        tid = r["trace_id"]
        end = tm.end_trace(tid)
        assert end["status"] == "completed"
        assert end["duration_ms"] >= 0
        assert tm.active_trace_count == 0
        assert tm.completed_trace_count == 1

    def test_end_trace_not_found(self):
        tm = TraceManager()
        r = tm.end_trace("missing")
        assert r["status"] == "error"

    def test_start_span(self):
        tm = TraceManager()
        t = tm.start_trace("req")
        tid = t["trace_id"]
        s = tm.start_span(tid, "db_query")
        assert s["span_id"] != ""
        assert s["trace_id"] == tid

    def test_start_span_trace_not_found(self):
        tm = TraceManager()
        r = tm.start_span("missing", "span1")
        assert r["status"] == "error"

    def test_end_span(self):
        tm = TraceManager()
        t = tm.start_trace("req")
        tid = t["trace_id"]
        s = tm.start_span(tid, "op")
        sid = s["span_id"]
        r = tm.end_span(tid, sid)
        assert r["status"] == "ok"
        assert r["duration_ms"] >= 0

    def test_end_span_not_found(self):
        tm = TraceManager()
        t = tm.start_trace("req")
        r = tm.end_span(t["trace_id"], "missing")
        assert r["status"] == "error"

    def test_add_span_event(self):
        tm = TraceManager()
        t = tm.start_trace("req")
        tid = t["trace_id"]
        s = tm.start_span(tid, "op")
        sid = s["span_id"]
        assert tm.add_span_event(tid, sid, "log") is True
        assert tm.add_span_event(tid, "bad", "x") is False

    def test_context(self):
        tm = TraceManager()
        t = tm.start_trace("req")
        tid = t["trace_id"]
        tm.set_context(tid, "user_id", "u123")
        ctx = tm.get_context(tid)
        assert ctx["user_id"] == "u123"

    def test_context_empty(self):
        tm = TraceManager()
        assert tm.get_context("missing") == {}

    def test_correlate(self):
        tm = TraceManager()
        t1 = tm.start_trace("req1")
        t2 = tm.start_trace("req2")
        r = tm.correlate(
            t1["trace_id"], t2["trace_id"],
        )
        assert r["valid"] is True

    def test_correlate_invalid(self):
        tm = TraceManager()
        r = tm.correlate("a", "b")
        assert r["valid"] is False

    def test_get_trace(self):
        tm = TraceManager()
        t = tm.start_trace("req")
        tid = t["trace_id"]
        trace = tm.get_trace(tid)
        assert trace is not None
        assert trace["name"] == "req"

    def test_get_trace_completed(self):
        tm = TraceManager()
        t = tm.start_trace("req")
        tid = t["trace_id"]
        tm.end_trace(tid)
        trace = tm.get_trace(tid)
        assert trace is not None
        assert trace["status"] == "completed"

    def test_get_trace_not_found(self):
        tm = TraceManager()
        assert tm.get_trace("missing") is None

    def test_get_spans(self):
        tm = TraceManager()
        t = tm.start_trace("req")
        tid = t["trace_id"]
        tm.start_span(tid, "s1")
        tm.start_span(tid, "s2")
        spans = tm.get_spans(tid)
        assert len(spans) == 2

    def test_zero_sampling(self):
        tm = TraceManager(sampling_rate=0.0)
        r = tm.start_trace("req")
        assert r["sampled"] is False
        assert r["trace_id"] == ""


# ===================== SpanCollector =====================


class TestSpanCollector:
    """SpanCollector testleri."""

    def test_init(self):
        sc = SpanCollector()
        assert sc.buffer_count == 0
        assert sc.total_collected == 0

    def test_collect(self):
        sc = SpanCollector()
        assert sc.collect({"name": "span1"}) is True
        assert sc.buffer_count == 1
        assert sc.total_collected == 1

    def test_collect_with_filter(self):
        sc = SpanCollector()
        sc.add_filter(lambda s: s.get("name") != "skip")
        assert sc.collect({"name": "keep"}) is True
        assert sc.collect({"name": "skip"}) is False
        assert sc.total_filtered == 1

    def test_collect_with_enricher(self):
        sc = SpanCollector()
        sc.add_enricher(lambda s: {"env": "prod"})
        sc.collect({"name": "span1"})
        buf = sc.get_buffer()
        assert buf[0]["env"] == "prod"

    def test_collect_batch(self):
        sc = SpanCollector()
        r = sc.collect_batch([
            {"name": "s1"},
            {"name": "s2"},
            {"name": "s3"},
        ])
        assert r["accepted"] == 3
        assert r["total"] == 3

    def test_auto_flush(self):
        sc = SpanCollector(buffer_size=3)
        sc.collect({"name": "s1"})
        sc.collect({"name": "s2"})
        sc.collect({"name": "s3"})
        # Buffer otomatik bosaltildi
        assert sc.export_count == 1
        assert sc.buffer_count == 0

    def test_manual_flush(self):
        sc = SpanCollector()
        sc.collect({"name": "s1"})
        r = sc.flush()
        assert r["flushed"] == 1
        assert sc.buffer_count == 0

    def test_flush_empty(self):
        sc = SpanCollector()
        r = sc.flush()
        assert r["flushed"] == 0

    def test_get_exported_batch(self):
        sc = SpanCollector()
        sc.collect({"name": "s1"})
        sc.flush()
        batch = sc.get_exported_batch(0)
        assert batch is not None
        assert len(batch) == 1
        assert sc.get_exported_batch(99) is None

    def test_remove_filters(self):
        sc = SpanCollector()
        sc.add_filter(lambda s: True)
        sc.add_filter(lambda s: True)
        assert sc.remove_filters() == 2

    def test_should_flush(self):
        sc = SpanCollector(buffer_size=2)
        assert sc.should_flush() is False
        sc.collect({"name": "s1"})
        sc.collect({"name": "s2"})
        # After auto-flush, buffer is empty
        assert sc.buffer_count == 0

    def test_get_buffer(self):
        sc = SpanCollector()
        sc.collect({"name": "s1"})
        buf = sc.get_buffer()
        assert len(buf) == 1


# ===================== MetricsCollector =====================


class TestMetricsCollector:
    """MetricsCollector testleri."""

    def test_init(self):
        mc = MetricsCollector()
        assert mc.total_metrics == 0

    def test_increment(self):
        mc = MetricsCollector()
        assert mc.increment("requests") == 1.0
        assert mc.increment("requests") == 2.0
        assert mc.increment("requests", 5) == 7.0

    def test_get_counter(self):
        mc = MetricsCollector()
        mc.increment("req")
        assert mc.get_counter("req") == 1.0
        assert mc.get_counter("missing") == 0.0

    def test_counter_with_labels(self):
        mc = MetricsCollector()
        mc.increment("req", labels={"method": "GET"})
        mc.increment("req", labels={"method": "POST"})
        assert mc.get_counter("req", {"method": "GET"}) == 1.0
        assert mc.get_counter("req", {"method": "POST"}) == 1.0

    def test_set_gauge(self):
        mc = MetricsCollector()
        mc.set_gauge("cpu", 75.5)
        assert mc.get_gauge("cpu") == 75.5

    def test_get_gauge_missing(self):
        mc = MetricsCollector()
        assert mc.get_gauge("missing") is None

    def test_gauge_with_labels(self):
        mc = MetricsCollector()
        mc.set_gauge("cpu", 75.5, {"host": "web1"})
        assert mc.get_gauge("cpu", {"host": "web1"}) == 75.5

    def test_observe(self):
        mc = MetricsCollector()
        mc.observe("latency", 10.0)
        mc.observe("latency", 20.0)
        mc.observe("latency", 30.0)
        h = mc.get_histogram("latency")
        assert h is not None
        assert h["count"] == 3
        assert h["mean"] == 20.0
        assert h["min"] == 10.0
        assert h["max"] == 30.0

    def test_histogram_percentiles(self):
        mc = MetricsCollector()
        for i in range(100):
            mc.observe("lat", float(i))
        h = mc.get_histogram("lat")
        assert h["p50"] == pytest.approx(49.5, abs=1)
        assert h["p95"] >= 90
        assert h["p99"] >= 95

    def test_get_histogram_missing(self):
        mc = MetricsCollector()
        assert mc.get_histogram("missing") is None

    def test_custom_metric(self):
        mc = MetricsCollector()
        mc.set_custom("uptime", 99.99, "percentage")
        assert mc.get_custom("uptime") == 99.99
        assert mc.get_custom("missing") is None

    def test_aggregate(self):
        mc = MetricsCollector()
        mc.increment("req")
        mc.set_gauge("cpu", 50.0)
        mc.observe("lat", 10.0)
        report = mc.aggregate()
        assert "counters" in report
        assert "gauges" in report
        assert "histograms" in report

    def test_export_prometheus(self):
        mc = MetricsCollector()
        mc.increment("requests_total")
        mc.set_gauge("cpu_usage", 75.0)
        output = mc.export_prometheus()
        assert "requests_total" in output
        assert "cpu_usage" in output

    def test_prometheus_with_labels(self):
        mc = MetricsCollector()
        mc.increment("req", labels={"method": "GET"})
        output = mc.export_prometheus()
        assert 'method="GET"' in output

    def test_reset(self):
        mc = MetricsCollector()
        mc.increment("a")
        mc.set_gauge("b", 1.0)
        mc.observe("c", 1.0)
        mc.set_custom("d", 1)
        counts = mc.reset()
        assert counts["counters"] == 1
        assert counts["gauges"] == 1
        assert mc.total_metrics == 0

    def test_counter_count(self):
        mc = MetricsCollector()
        mc.increment("a")
        mc.increment("b")
        assert mc.counter_count == 2

    def test_gauge_count(self):
        mc = MetricsCollector()
        mc.set_gauge("a", 1.0)
        assert mc.gauge_count == 1

    def test_histogram_count(self):
        mc = MetricsCollector()
        mc.observe("a", 1.0)
        assert mc.histogram_count == 1


# ===================== HealthChecker =====================


class TestHealthChecker:
    """HealthChecker testleri."""

    def test_init(self):
        hc = HealthChecker()
        assert hc.check_count == 0

    def test_liveness_check(self):
        hc = HealthChecker()
        hc.add_liveness_check("app", lambda: True)
        r = hc.check_liveness()
        assert r["alive"] is True

    def test_liveness_check_fail(self):
        hc = HealthChecker()
        hc.add_liveness_check("app", lambda: False)
        r = hc.check_liveness()
        assert r["alive"] is False

    def test_liveness_check_exception(self):
        hc = HealthChecker()
        hc.add_liveness_check(
            "app", lambda: 1 / 0,
        )
        r = hc.check_liveness()
        assert r["alive"] is False
        assert r["checks"]["app"]["error"] is not None

    def test_readiness_check(self):
        hc = HealthChecker()
        hc.add_readiness_check("db", lambda: True)
        r = hc.check_readiness()
        assert r["ready"] is True

    def test_readiness_check_fail(self):
        hc = HealthChecker()
        hc.add_readiness_check("db", lambda: False)
        r = hc.check_readiness()
        assert r["ready"] is False

    def test_dependency_check(self):
        hc = HealthChecker()
        hc.add_dependency_check("redis", lambda: True)
        r = hc.check_dependencies()
        assert r["healthy"] is True
        assert r["critical_ok"] is True

    def test_dependency_check_critical_fail(self):
        hc = HealthChecker()
        hc.add_dependency_check(
            "db", lambda: False, critical=True,
        )
        r = hc.check_dependencies()
        assert r["critical_ok"] is False

    def test_dependency_check_non_critical_fail(self):
        hc = HealthChecker()
        hc.add_dependency_check(
            "cache", lambda: False, critical=False,
        )
        r = hc.check_dependencies()
        assert r["healthy"] is False
        assert r["critical_ok"] is True

    def test_custom_check(self):
        hc = HealthChecker()
        hc.add_custom_check(
            "disk", lambda: {"status": "ok", "usage": 50},
        )
        r = hc.check_custom("disk")
        assert r["status"] == "ok"

    def test_custom_check_not_found(self):
        hc = HealthChecker()
        r = hc.check_custom("missing")
        assert r["status"] == "error"

    def test_custom_check_exception(self):
        hc = HealthChecker()
        hc.add_custom_check("bad", lambda: 1 / 0)
        r = hc.check_custom("bad")
        assert r["status"] == "error"

    def test_aggregate_healthy(self):
        hc = HealthChecker()
        hc.add_liveness_check("app", lambda: True)
        hc.add_readiness_check("db", lambda: True)
        hc.add_dependency_check("redis", lambda: True)
        r = hc.get_aggregate_status()
        assert r["status"] == "healthy"

    def test_aggregate_degraded(self):
        hc = HealthChecker()
        hc.add_liveness_check("app", lambda: True)
        hc.add_readiness_check("db", lambda: False)
        r = hc.get_aggregate_status()
        assert r["status"] == "degraded"

    def test_aggregate_unhealthy(self):
        hc = HealthChecker()
        hc.add_liveness_check("app", lambda: False)
        r = hc.get_aggregate_status()
        assert r["status"] == "unhealthy"

    def test_remove_check(self):
        hc = HealthChecker()
        hc.add_liveness_check("app", lambda: True)
        assert hc.remove_check("app") is True
        assert hc.liveness_count == 0
        assert hc.remove_check("missing") is False

    def test_check_counts(self):
        hc = HealthChecker()
        hc.add_liveness_check("a", lambda: True)
        hc.add_readiness_check("b", lambda: True)
        hc.add_dependency_check("c", lambda: True)
        assert hc.liveness_count == 1
        assert hc.readiness_count == 1
        assert hc.dependency_count == 1
        assert hc.check_count == 3


# ===================== AlertManager =====================


class TestAlertManager:
    """AlertManager testleri."""

    def test_init(self):
        am = AlertManager()
        assert am.rule_count == 0
        assert am.alert_count == 0

    def test_add_rule(self):
        am = AlertManager()
        r = am.add_rule(
            "high_cpu", "cpu_usage", "gt", 80.0,
            severity="critical",
        )
        assert r["name"] == "high_cpu"
        assert am.rule_count == 1

    def test_remove_rule(self):
        am = AlertManager()
        am.add_rule("r1", "m1", "gt", 50.0)
        assert am.remove_rule("r1") is True
        assert am.remove_rule("missing") is False

    def test_evaluate_triggers(self):
        am = AlertManager()
        am.add_rule("high_cpu", "cpu", "gt", 80.0)
        alerts = am.evaluate("cpu", 90.0)
        assert len(alerts) == 1
        assert alerts[0]["rule"] == "high_cpu"

    def test_evaluate_no_trigger(self):
        am = AlertManager()
        am.add_rule("high_cpu", "cpu", "gt", 80.0)
        alerts = am.evaluate("cpu", 50.0)
        assert len(alerts) == 0

    def test_evaluate_lt(self):
        am = AlertManager()
        am.add_rule("low_mem", "mem", "lt", 10.0)
        alerts = am.evaluate("mem", 5.0)
        assert len(alerts) == 1

    def test_evaluate_eq(self):
        am = AlertManager()
        am.add_rule("exact", "val", "eq", 42.0)
        assert len(am.evaluate("val", 42.0)) == 1
        assert len(am.evaluate("val", 43.0)) == 0

    def test_evaluate_gte_lte(self):
        am = AlertManager()
        am.add_rule("r1", "m", "gte", 50.0)
        am.add_rule("r2", "m", "lte", 50.0)
        assert len(am.evaluate("m", 50.0)) == 2

    def test_silence(self):
        am = AlertManager()
        am.add_rule("r1", "m", "gt", 50.0)
        am.silence("r1", 3600, "maintenance")
        alerts = am.evaluate("m", 100.0)
        assert len(alerts) == 0
        assert am.silence_count == 1

    def test_unsilence(self):
        am = AlertManager()
        am.silence("r1", 3600)
        assert am.unsilence("r1") is True
        assert am.unsilence("missing") is False

    def test_routing(self):
        am = AlertManager()
        routed = []
        am.add_route("critical", lambda a: routed.append(a))
        am.add_rule("r1", "m", "gt", 50.0, severity="critical")
        am.evaluate("m", 100.0)
        assert len(routed) == 1

    def test_acknowledge(self):
        am = AlertManager()
        am.add_rule("r1", "m", "gt", 50.0)
        am.evaluate("m", 100.0)
        assert am.acknowledge(0) is True
        assert am.acknowledge(99) is False
        active = am.get_active_alerts()
        assert len(active) == 0

    def test_get_active_alerts(self):
        am = AlertManager()
        am.add_rule("r1", "m", "gt", 50.0, severity="warning")
        am.add_rule("r2", "m", "gt", 80.0, severity="critical")
        am.evaluate("m", 100.0)
        assert len(am.get_active_alerts()) == 2
        critical = am.get_active_alerts("critical")
        assert len(critical) == 1

    def test_escalation(self):
        am = AlertManager()
        am.add_escalation("critical", 300, "manager")
        assert len(am._escalation_rules) == 1

    def test_alert_summary(self):
        am = AlertManager()
        am.add_rule("r1", "m", "gt", 50.0, severity="warning")
        am.evaluate("m", 100.0)
        s = am.get_alert_summary()
        assert s["total"] == 1
        assert s["active"] == 1
        assert s["by_severity"]["warning"] == 1

    def test_route_count(self):
        am = AlertManager()
        am.add_route("warning", lambda a: None)
        am.add_route("critical", lambda a: None)
        assert am.route_count == 2


# ===================== DashboardBuilder =====================


class TestDashboardBuilder:
    """DashboardBuilder testleri."""

    def test_init(self):
        db = DashboardBuilder()
        assert db.dashboard_count == 0

    def test_create_dashboard(self):
        db = DashboardBuilder()
        r = db.create_dashboard("sys", title="System")
        assert r["name"] == "sys"
        assert db.dashboard_count == 1

    def test_delete_dashboard(self):
        db = DashboardBuilder()
        db.create_dashboard("sys")
        assert db.delete_dashboard("sys") is True
        assert db.delete_dashboard("missing") is False

    def test_add_widget(self):
        db = DashboardBuilder()
        db.create_dashboard("sys")
        r = db.add_widget(
            "sys", "chart", "CPU Usage",
            data_source="metrics",
        )
        assert r["widget_index"] == 0
        assert db.total_widgets == 1

    def test_add_widget_no_dashboard(self):
        db = DashboardBuilder()
        r = db.add_widget("missing", "chart", "test")
        assert r["status"] == "error"

    def test_remove_widget(self):
        db = DashboardBuilder()
        db.create_dashboard("sys")
        db.add_widget("sys", "chart", "w1")
        db.add_widget("sys", "table", "w2")
        assert db.remove_widget("sys", 0) is True
        assert db.total_widgets == 1

    def test_remove_widget_invalid(self):
        db = DashboardBuilder()
        assert db.remove_widget("missing", 0) is False
        db.create_dashboard("sys")
        assert db.remove_widget("sys", 99) is False

    def test_add_data_source(self):
        db = DashboardBuilder()
        r = db.add_data_source(
            "prometheus", "metrics",
        )
        assert r["name"] == "prometheus"
        assert db.data_source_count == 1

    def test_remove_data_source(self):
        db = DashboardBuilder()
        db.add_data_source("prom", "metrics")
        assert db.remove_data_source("prom") is True
        assert db.remove_data_source("missing") is False

    def test_get_dashboard(self):
        db = DashboardBuilder()
        db.create_dashboard("sys", title="System")
        d = db.get_dashboard("sys")
        assert d is not None
        assert d["title"] == "System"
        assert db.get_dashboard("missing") is None

    def test_list_dashboards(self):
        db = DashboardBuilder()
        db.create_dashboard("a")
        db.create_dashboard("b")
        lst = db.list_dashboards()
        assert len(lst) == 2

    def test_share_dashboard(self):
        db = DashboardBuilder()
        db.create_dashboard("sys")
        r = db.share_dashboard("sys", "user1", "view")
        assert r["shared_with"] == "user1"

    def test_share_dashboard_not_found(self):
        db = DashboardBuilder()
        r = db.share_dashboard("missing", "user1")
        assert r["status"] == "error"

    def test_get_shared_users(self):
        db = DashboardBuilder()
        db.create_dashboard("sys")
        db.share_dashboard("sys", "u1")
        db.share_dashboard("sys", "u2")
        users = db.get_shared_users("sys")
        assert "u1" in users
        assert "u2" in users

    def test_clone_dashboard(self):
        db = DashboardBuilder()
        db.create_dashboard("sys")
        db.add_widget("sys", "chart", "w1")
        r = db.clone_dashboard("sys", "sys_copy")
        assert r["widgets"] == 1
        assert db.dashboard_count == 2

    def test_clone_not_found(self):
        db = DashboardBuilder()
        r = db.clone_dashboard("missing", "new")
        assert r["status"] == "error"


# ===================== AnomalyDetector =====================


class TestAnomalyDetector:
    """AnomalyDetector testleri."""

    def test_init(self):
        ad = AnomalyDetector()
        assert ad.anomaly_count == 0
        assert ad.baseline_count == 0

    def test_add_data_point(self):
        ad = AnomalyDetector()
        r = ad.add_data_point("cpu", 50.0)
        assert r is None  # temel cizgi yok
        assert ad.metric_count == 1

    def test_learn_baseline(self):
        ad = AnomalyDetector()
        for i in range(20):
            ad.add_data_point("cpu", 50.0 + (i % 5))
        r = ad.learn_baseline("cpu")
        assert r["status"] == "learned"
        assert ad.baseline_count == 1

    def test_learn_baseline_insufficient(self):
        ad = AnomalyDetector()
        ad.add_data_point("cpu", 50.0)
        r = ad.learn_baseline("cpu")
        assert r["status"] == "insufficient_data"

    def test_set_baseline(self):
        ad = AnomalyDetector()
        ad.set_baseline("cpu", 50.0, 5.0)
        assert ad.baseline_count == 1

    def test_detect_anomaly_spike(self):
        ad = AnomalyDetector(sensitivity=2.0)
        ad.set_baseline("cpu", 50.0, 5.0)
        r = ad.add_data_point("cpu", 100.0)
        assert r is not None
        assert r["type"] == "spike"

    def test_detect_anomaly_drop(self):
        ad = AnomalyDetector(sensitivity=2.0)
        ad.set_baseline("cpu", 50.0, 5.0)
        r = ad.add_data_point("cpu", 0.0)
        assert r is not None
        assert r["type"] == "drop"

    def test_no_anomaly(self):
        ad = AnomalyDetector(sensitivity=2.0)
        ad.set_baseline("cpu", 50.0, 5.0)
        r = ad.add_data_point("cpu", 52.0)
        assert r is None

    def test_root_cause_hints(self):
        ad = AnomalyDetector()
        ad.add_root_cause_hint("cpu", "Check process list")
        ad.add_root_cause_hint("cpu", "Check cron jobs")
        hints = ad.get_root_cause_hints("cpu")
        assert len(hints) == 2
        assert ad.get_root_cause_hints("missing") == []

    def test_get_anomalies(self):
        ad = AnomalyDetector(sensitivity=2.0)
        ad.set_baseline("cpu", 50.0, 5.0)
        ad.add_data_point("cpu", 100.0)
        ad.add_data_point("cpu", 0.0)
        anomalies = ad.get_anomalies()
        assert len(anomalies) == 2

    def test_get_anomalies_filtered(self):
        ad = AnomalyDetector(sensitivity=2.0)
        ad.set_baseline("cpu", 50.0, 5.0)
        ad.set_baseline("mem", 70.0, 3.0)
        ad.add_data_point("cpu", 100.0)
        ad.add_data_point("mem", 100.0)
        assert len(ad.get_anomalies("cpu")) == 1

    def test_detect_trend_increasing(self):
        ad = AnomalyDetector()
        for i in range(20):
            ad.add_data_point("cpu", float(i))
        r = ad.detect_trend("cpu", window=10)
        assert r["trend"] == "increasing"

    def test_detect_trend_insufficient(self):
        ad = AnomalyDetector()
        ad.add_data_point("cpu", 1.0)
        r = ad.detect_trend("cpu")
        assert r["trend"] == "unknown"

    def test_detect_trend_stable(self):
        ad = AnomalyDetector()
        for _ in range(20):
            ad.add_data_point("cpu", 50.0)
        r = ad.detect_trend("cpu", window=10)
        assert r["trend"] == "stable"

    def test_clear_anomalies(self):
        ad = AnomalyDetector(sensitivity=2.0)
        ad.set_baseline("cpu", 50.0, 5.0)
        ad.add_data_point("cpu", 100.0)
        count = ad.clear_anomalies()
        assert count == 1
        assert ad.anomaly_count == 0

    def test_clear_anomalies_filtered(self):
        ad = AnomalyDetector(sensitivity=2.0)
        ad.set_baseline("cpu", 50.0, 5.0)
        ad.set_baseline("mem", 70.0, 3.0)
        ad.add_data_point("cpu", 100.0)
        ad.add_data_point("mem", 100.0)
        count = ad.clear_anomalies("cpu")
        assert count == 1
        assert ad.anomaly_count == 1

    def test_zero_std_anomaly(self):
        ad = AnomalyDetector()
        ad.set_baseline("val", 50.0, 0.0)
        r = ad.add_data_point("val", 51.0)
        assert r is not None  # farkli deger = anomali


# ===================== SLAMonitor =====================


class TestSLAMonitor:
    """SLAMonitor testleri."""

    def test_init(self):
        sm = SLAMonitor()
        assert sm.slo_count == 0

    def test_define_slo(self):
        sm = SLAMonitor()
        r = sm.define_slo("uptime", 99.9)
        assert r["name"] == "uptime"
        assert r["target"] == 99.9
        assert r["error_budget"] == pytest.approx(0.1)
        assert sm.slo_count == 1

    def test_remove_slo(self):
        sm = SLAMonitor()
        sm.define_slo("uptime", 99.9)
        assert sm.remove_slo("uptime") is True
        assert sm.remove_slo("missing") is False

    def test_record_measurement_ok(self):
        sm = SLAMonitor()
        sm.define_slo("uptime", 99.0)
        r = sm.record_measurement("uptime", 1.0, True)
        assert r["status"] == "ok"
        assert r["compliance"] == 100.0

    def test_record_measurement_not_found(self):
        sm = SLAMonitor()
        r = sm.record_measurement("missing", 1.0)
        assert r["status"] == "error"

    def test_record_measurement_breach(self):
        sm = SLAMonitor()
        sm.define_slo("uptime", 99.0)
        # 1 basarisiz / 1 toplam = %0 basari < %99
        r = sm.record_measurement("uptime", 0.0, False)
        assert r["status"] == "breach"
        assert sm.breach_count >= 1

    def test_get_compliance(self):
        sm = SLAMonitor()
        sm.define_slo("uptime", 99.0)
        for _ in range(99):
            sm.record_measurement("uptime", 1.0, True)
        sm.record_measurement("uptime", 0.0, False)
        c = sm.get_compliance("uptime")
        assert c["actual"] == 99.0
        assert c["compliant"] is True

    def test_get_compliance_not_found(self):
        sm = SLAMonitor()
        r = sm.get_compliance("missing")
        assert r["status"] == "error"

    def test_error_budget(self):
        sm = SLAMonitor()
        sm.define_slo("uptime", 99.0)
        budget = sm.get_error_budget("uptime")
        assert budget is not None
        assert budget["total"] == 1.0
        assert budget["remaining"] == 1.0

    def test_error_budget_consumed(self):
        sm = SLAMonitor()
        sm.define_slo("uptime", 99.0)
        sm.record_measurement("uptime", 0.0, False)
        budget = sm.get_error_budget("uptime")
        assert budget["consumed"] == 1

    def test_get_breaches(self):
        sm = SLAMonitor()
        sm.define_slo("uptime", 99.0)
        sm.record_measurement("uptime", 0.0, False)
        breaches = sm.get_breaches()
        assert len(breaches) >= 1

    def test_get_breaches_filtered(self):
        sm = SLAMonitor()
        sm.define_slo("a", 99.0)
        sm.define_slo("b", 99.0)
        sm.record_measurement("a", 0.0, False)
        sm.record_measurement("b", 0.0, False)
        assert len(sm.get_breaches("a")) >= 1

    def test_get_trend_improving(self):
        sm = SLAMonitor()
        sm.define_slo("uptime", 90.0)
        # Ilk yarisinda basarisiz, ikinci yarisinda basarili
        for _ in range(5):
            sm.record_measurement("uptime", 0.0, False)
        for _ in range(5):
            sm.record_measurement("uptime", 1.0, True)
        r = sm.get_trend("uptime", window=10)
        assert r["trend"] == "improving"

    def test_get_trend_insufficient(self):
        sm = SLAMonitor()
        sm.define_slo("uptime", 99.0)
        r = sm.get_trend("uptime")
        assert r["trend"] == "unknown"

    def test_generate_report(self):
        sm = SLAMonitor()
        sm.define_slo("uptime", 99.0)
        sm.define_slo("latency", 95.0)
        sm.record_measurement("uptime", 1.0, True)
        sm.record_measurement("latency", 1.0, True)
        report = sm.generate_report()
        assert report["total_slos"] == 2
        assert report["compliant"] == 2

    def test_measurement_count(self):
        sm = SLAMonitor()
        sm.define_slo("a", 99.0)
        sm.record_measurement("a", 1.0, True)
        sm.record_measurement("a", 1.0, True)
        assert sm.measurement_count == 2


# ===================== ObservabilityOrchestrator =====================


class TestObservabilityOrchestrator:
    """ObservabilityOrchestrator testleri."""

    def test_init(self):
        oo = ObservabilityOrchestrator()
        assert oo.is_initialized is False

    def test_init_custom(self):
        oo = ObservabilityOrchestrator(
            sampling_rate=0.5, sensitivity=3.0,
        )
        assert oo.traces.sampling_rate == 0.5

    def test_initialize(self):
        oo = ObservabilityOrchestrator()
        r = oo.initialize()
        assert r["status"] == "initialized"
        assert oo.is_initialized is True
        assert oo.dashboards.dashboard_count == 2

    def test_initialize_no_defaults(self):
        oo = ObservabilityOrchestrator()
        r = oo.initialize(default_dashboards=False)
        assert oo.dashboards.dashboard_count == 0

    def test_record_request(self):
        oo = ObservabilityOrchestrator()
        r = oo.record_request(
            "api_call", 150.0, success=True,
        )
        assert r["trace_id"] != ""
        assert r["success"] is True

    def test_record_request_error(self):
        oo = ObservabilityOrchestrator()
        r = oo.record_request(
            "api_call", 500.0, success=False,
        )
        assert r["success"] is False

    def test_record_request_with_alert(self):
        oo = ObservabilityOrchestrator()
        oo.alerts.add_rule(
            "slow", "api_call_duration", "gt", 100.0,
        )
        r = oo.record_request("api_call", 200.0)
        assert r["alerts_triggered"] >= 1

    def test_record_request_with_anomaly(self):
        oo = ObservabilityOrchestrator()
        oo.anomalies.set_baseline(
            "api_call_duration", 50.0, 5.0,
        )
        r = oo.record_request("api_call", 200.0)
        assert r["anomaly_detected"] is True

    def test_check_system_health(self):
        oo = ObservabilityOrchestrator()
        oo.health.add_liveness_check(
            "app", lambda: True,
        )
        r = oo.check_system_health()
        assert r["status"] == "healthy"

    def test_correlate_events(self):
        oo = ObservabilityOrchestrator()
        r = oo.correlate_events(
            {"type": "error"},
            {"type": "spike"},
            "caused_by",
        )
        assert r["relation"] == "caused_by"
        assert oo.correlation_count == 1

    def test_get_unified_view(self):
        oo = ObservabilityOrchestrator()
        oo.initialize()
        view = oo.get_unified_view()
        assert "health" in view
        assert "active_traces" in view
        assert "total_metrics" in view
        assert view["initialized"] is True

    def test_get_analytics(self):
        oo = ObservabilityOrchestrator()
        oo.record_request("test", 10.0)
        analytics = oo.get_analytics()
        assert "traces" in analytics
        assert "metrics" in analytics
        assert "alerts" in analytics
        assert "anomalies" in analytics
        assert "sla" in analytics


# ===================== Config Settings =====================


class TestConfigSettings:
    """Config ayarlari testleri."""

    def test_observability_settings(self):
        from app.config import settings
        assert hasattr(settings, "observability_enabled")
        assert hasattr(settings, "trace_sampling_rate")
        assert hasattr(settings, "metrics_interval")
        assert hasattr(settings, "alert_evaluation_interval")
        assert hasattr(settings, "observability_retention_days")

    def test_observability_defaults(self):
        from app.config import settings
        assert settings.observability_enabled is True
        assert settings.trace_sampling_rate == 1.0
        assert settings.metrics_interval == 60
        assert settings.alert_evaluation_interval == 30
        assert settings.observability_retention_days == 30
