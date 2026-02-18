"""System Health Dashboard testleri."""

import pytest

from app.models.healthdash_models import (
    SystemStatus,
    ResourceType,
    AlertSeverity,
    HeatmapColor,
    RiskLevel,
    TrendDirection,
    SystemRecord,
    HeatmapCell,
    ResourceReading,
    QuotaRecord,
    LatencyRecord,
    UptimeRecord,
    AlertRecord,
    PredictionRecord,
)
from app.core.healthdash.system_status_map import (
    SystemStatusMap,
)
from app.core.healthdash.health_heatmap import (
    HealthHeatmap,
)
from app.core.healthdash.resource_gauge import (
    ResourceGauge,
)
from app.core.healthdash.api_quota_tracker import (
    APIQuotaTracker,
)
from app.core.healthdash.latency_monitor import (
    LatencyMonitor,
)
from app.core.healthdash.uptime_chart import (
    UptimeChart,
)
from app.core.healthdash.alert_timeline import (
    AlertTimeline,
)
from app.core.healthdash.health_degradation_predictor import (
    HealthDegradationPredictor,
)
from app.core.healthdash.healthdash_orchestrator import (
    HealthDashOrchestrator,
)


# ── Model Testleri ──


class TestHealthDashModels:
    """Model testleri."""

    def test_system_status_values(self):
        assert SystemStatus.healthy == "healthy"
        assert SystemStatus.degraded == "degraded"
        assert SystemStatus.down == "down"
        assert SystemStatus.maintenance == "maintenance"
        assert SystemStatus.unknown == "unknown"

    def test_resource_type_values(self):
        assert ResourceType.cpu == "cpu"
        assert ResourceType.memory == "memory"
        assert ResourceType.disk == "disk"
        assert ResourceType.network == "network"
        assert ResourceType.gpu == "gpu"

    def test_alert_severity_values(self):
        assert AlertSeverity.info == "info"
        assert AlertSeverity.warning == "warning"
        assert AlertSeverity.critical == "critical"
        assert AlertSeverity.emergency == "emergency"

    def test_heatmap_color_values(self):
        assert HeatmapColor.green == "green"
        assert HeatmapColor.yellow == "yellow"
        assert HeatmapColor.orange == "orange"
        assert HeatmapColor.red == "red"

    def test_risk_level_values(self):
        assert RiskLevel.low == "low"
        assert RiskLevel.medium == "medium"
        assert RiskLevel.high == "high"
        assert RiskLevel.critical == "critical"

    def test_trend_direction_values(self):
        assert TrendDirection.improving == "improving"
        assert TrendDirection.stable == "stable"
        assert TrendDirection.declining == "declining"
        assert TrendDirection.volatile == "volatile"

    def test_system_record(self):
        r = SystemRecord(
            name="Master Agent",
            category="core",
        )
        assert r.name == "Master Agent"
        assert r.category == "core"
        assert r.status == "healthy"
        assert r.health_score == 100.0
        assert r.system_id

    def test_heatmap_cell(self):
        r = HeatmapCell(
            system_name="API",
            metric_name="health",
            value=85.0,
            color="yellow",
        )
        assert r.system_name == "API"
        assert r.value == 85.0
        assert r.color == "yellow"
        assert r.cell_id

    def test_resource_reading(self):
        r = ResourceReading(
            resource_type="cpu",
            value=65.0,
            status="normal",
        )
        assert r.resource_type == "cpu"
        assert r.value == 65.0
        assert r.status == "normal"

    def test_quota_record(self):
        r = QuotaRecord(
            api_name="Claude",
            daily_limit=1000,
        )
        assert r.api_name == "Claude"
        assert r.daily_limit == 1000
        assert r.daily_used == 0

    def test_latency_record(self):
        r = LatencyRecord(
            endpoint_name="/api/tasks",
            response_ms=120.0,
        )
        assert r.endpoint_name == "/api/tasks"
        assert r.response_ms == 120.0

    def test_uptime_record(self):
        r = UptimeRecord(
            name="Web Server",
            uptime_percent=99.95,
        )
        assert r.name == "Web Server"
        assert r.uptime_percent == 99.95
        assert r.sla_met is True

    def test_alert_record(self):
        r = AlertRecord(
            source="CPU",
            message="High usage",
            severity="warning",
        )
        assert r.source == "CPU"
        assert r.severity == "warning"
        assert r.status == "active"

    def test_prediction_record(self):
        r = PredictionRecord(
            system_name="DB",
            risk_level="medium",
            risk_score=45.0,
        )
        assert r.system_name == "DB"
        assert r.risk_level == "medium"
        assert r.risk_score == 45.0


# ── SystemStatusMap Testleri ──


class TestSystemStatusMap:
    """SystemStatusMap testleri."""

    def test_init(self):
        m = SystemStatusMap()
        assert m.system_count == 0

    def test_register_system(self):
        m = SystemStatusMap()
        r = m.register_system(
            name="Core",
            category="core",
            components=["agent", "memory"],
        )
        assert r["registered"] is True
        assert r["name"] == "Core"
        assert r["component_count"] == 2
        assert m.system_count == 1

    def test_get_overview_empty(self):
        m = SystemStatusMap()
        r = m.get_overview()
        assert r["retrieved"] is True
        assert r["total_systems"] == 0

    def test_get_overview_healthy(self):
        m = SystemStatusMap()
        m.register_system(name="A")
        m.register_system(name="B")
        r = m.get_overview()
        assert r["healthy"] == 2
        assert r["overall_health"] == 100.0
        assert r["overall_status"] == "healthy"

    def test_update_status(self):
        m = SystemStatusMap()
        reg = m.register_system(name="X")
        sid = reg["system_id"]
        r = m.update_status(
            system_id=sid,
            status="degraded",
            health_score=60.0,
        )
        assert r["updated"] is True
        assert r["status"] == "degraded"
        assert r["status_changed"] is True

    def test_update_status_not_found(self):
        m = SystemStatusMap()
        r = m.update_status(
            system_id="invalid",
        )
        assert r["updated"] is False

    def test_map_dependency(self):
        m = SystemStatusMap()
        a = m.register_system(name="A")
        b = m.register_system(name="B")
        r = m.map_dependency(
            source_id=a["system_id"],
            target_id=b["system_id"],
        )
        assert r["mapped"] is True

    def test_map_dependency_not_found(self):
        m = SystemStatusMap()
        r = m.map_dependency(
            source_id="x",
            target_id="y",
        )
        assert r["mapped"] is False

    def test_drill_down(self):
        m = SystemStatusMap()
        reg = m.register_system(
            name="Core",
            components=["a", "b"],
        )
        r = m.drill_down(
            system_id=reg["system_id"],
        )
        assert r["drilled"] is True
        assert r["name"] == "Core"
        assert len(r["components"]) == 2

    def test_drill_down_not_found(self):
        m = SystemStatusMap()
        r = m.drill_down(system_id="x")
        assert r["drilled"] is False

    def test_navigate(self):
        m = SystemStatusMap()
        m.register_system(
            name="A", category="core"
        )
        m.register_system(
            name="B", category="tools"
        )
        r = m.navigate(category="core")
        assert r["navigated"] is True
        assert r["count"] == 1

    def test_navigate_by_status(self):
        m = SystemStatusMap()
        m.register_system(name="A")
        r = m.navigate(
            status_filter="healthy"
        )
        assert r["count"] == 1

    def test_overview_degraded(self):
        m = SystemStatusMap()
        a = m.register_system(name="A")
        b = m.register_system(name="B")
        m.register_system(name="C")
        m.update_status(
            system_id=a["system_id"],
            status="down",
            health_score=0.0,
        )
        r = m.get_overview()
        assert r["down"] == 1
        assert r["healthy"] == 2


# ── HealthHeatmap Testleri ──


class TestHealthHeatmap:
    """HealthHeatmap testleri."""

    def test_init(self):
        h = HealthHeatmap()
        assert h.cell_count == 0

    def test_add_cell_green(self):
        h = HealthHeatmap()
        r = h.add_cell(
            system_name="API",
            value=95.0,
        )
        assert r["added"] is True
        assert r["color"] == "green"

    def test_add_cell_yellow(self):
        h = HealthHeatmap()
        r = h.add_cell(
            system_name="API",
            value=75.0,
        )
        assert r["color"] == "yellow"

    def test_add_cell_orange(self):
        h = HealthHeatmap()
        r = h.add_cell(
            system_name="API",
            value=55.0,
        )
        assert r["color"] == "orange"

    def test_add_cell_red(self):
        h = HealthHeatmap()
        r = h.add_cell(
            system_name="API",
            value=30.0,
        )
        assert r["color"] == "red"

    def test_generate_heatmap(self):
        h = HealthHeatmap()
        h.add_cell(
            system_name="A", value=90.0
        )
        h.add_cell(
            system_name="A", value=95.0
        )
        h.add_cell(
            system_name="B", value=40.0
        )
        r = h.generate_heatmap()
        assert r["generated"] is True
        assert r["systems"] == 2

    def test_get_time_view(self):
        h = HealthHeatmap()
        for v in [90, 85, 80, 75, 70]:
            h.add_cell(
                system_name="X",
                value=float(v),
            )
        r = h.get_time_view(
            system_name="X", periods=3,
        )
        assert r["retrieved"] is True
        assert r["trend"] == "declining"

    def test_get_time_view_improving(self):
        h = HealthHeatmap()
        for v in [70, 75, 80, 85, 90]:
            h.add_cell(
                system_name="Y",
                value=float(v),
            )
        r = h.get_time_view(
            system_name="Y", periods=4,
        )
        assert r["trend"] == "improving"

    def test_detect_patterns(self):
        h = HealthHeatmap()
        for v in [90, 30, 85, 25, 80]:
            h.add_cell(
                system_name="Z",
                value=float(v),
            )
        r = h.detect_patterns()
        assert r["detected"] is True

    def test_identify_hotspots(self):
        h = HealthHeatmap()
        h.add_cell(
            system_name="A", value=30.0
        )
        h.add_cell(
            system_name="B", value=90.0
        )
        r = h.identify_hotspots(threshold=50.0)
        assert r["identified"] is True
        assert r["hotspot_count"] == 1

    def test_identify_hotspots_critical(self):
        h = HealthHeatmap()
        h.add_cell(
            system_name="C", value=20.0
        )
        r = h.identify_hotspots()
        assert r["hotspots"][0]["severity"] == "critical"


# ── ResourceGauge Testleri ──


class TestResourceGauge:
    """ResourceGauge testleri."""

    def test_init(self):
        g = ResourceGauge()
        assert g.gauge_count == 0

    def test_create_gauge(self):
        g = ResourceGauge()
        r = g.create_gauge(
            resource_type="cpu",
            label="CPU",
        )
        assert r["created"] is True
        assert r["resource_type"] == "cpu"
        assert g.gauge_count == 1

    def test_update_reading_normal(self):
        g = ResourceGauge()
        cr = g.create_gauge()
        r = g.update_reading(
            gauge_id=cr["gauge_id"],
            value=50.0,
        )
        assert r["updated"] is True
        assert r["status"] == "normal"

    def test_update_reading_warning(self):
        g = ResourceGauge()
        cr = g.create_gauge()
        r = g.update_reading(
            gauge_id=cr["gauge_id"],
            value=75.0,
        )
        assert r["status"] == "warning"

    def test_update_reading_critical(self):
        g = ResourceGauge()
        cr = g.create_gauge()
        r = g.update_reading(
            gauge_id=cr["gauge_id"],
            value=95.0,
        )
        assert r["status"] == "critical"
        assert r["alert_triggered"] is True

    def test_update_reading_not_found(self):
        g = ResourceGauge()
        r = g.update_reading(
            gauge_id="invalid",
        )
        assert r["updated"] is False

    def test_monitor_cpu(self):
        g = ResourceGauge()
        r = g.monitor_cpu(
            usage_percent=65.0, cores=8,
        )
        assert r["monitored"] is True
        assert r["status"] == "normal"

    def test_monitor_cpu_critical(self):
        g = ResourceGauge()
        r = g.monitor_cpu(
            usage_percent=95.0,
        )
        assert r["status"] == "critical"

    def test_monitor_memory(self):
        g = ResourceGauge()
        r = g.monitor_memory(
            used_mb=4096.0,
            total_mb=8192.0,
        )
        assert r["monitored"] is True
        assert r["usage_percent"] == 50.0
        assert r["status"] == "normal"

    def test_monitor_memory_warning(self):
        g = ResourceGauge()
        r = g.monitor_memory(
            used_mb=6000.0,
            total_mb=8192.0,
        )
        assert r["status"] == "warning"

    def test_monitor_disk(self):
        g = ResourceGauge()
        r = g.monitor_disk(
            used_gb=50.0,
            total_gb=100.0,
        )
        assert r["monitored"] is True
        assert r["usage_percent"] == 50.0

    def test_monitor_disk_critical(self):
        g = ResourceGauge()
        r = g.monitor_disk(
            used_gb=95.0,
            total_gb=100.0,
        )
        assert r["status"] == "critical"

    def test_monitor_network(self):
        g = ResourceGauge()
        r = g.monitor_network(
            bandwidth_mbps=500.0,
            max_bandwidth_mbps=1000.0,
        )
        assert r["monitored"] is True
        assert r["usage_percent"] == 50.0

    def test_check_thresholds(self):
        g = ResourceGauge()
        cr = g.create_gauge()
        g.update_reading(
            gauge_id=cr["gauge_id"],
            value=95.0,
        )
        r = g.check_thresholds()
        assert r["checked"] is True
        assert r["alert_count"] == 1


# ── APIQuotaTracker Testleri ──


class TestAPIQuotaTracker:
    """APIQuotaTracker testleri."""

    def test_init(self):
        t = APIQuotaTracker()
        assert t.quota_count == 0

    def test_register_quota(self):
        t = APIQuotaTracker()
        r = t.register_quota(
            api_name="Claude",
            daily_limit=1000,
        )
        assert r["registered"] is True
        assert r["api_name"] == "Claude"

    def test_track_usage(self):
        t = APIQuotaTracker()
        reg = t.register_quota(
            api_name="Claude",
            daily_limit=100,
        )
        r = t.track_usage(
            quota_id=reg["quota_id"],
            calls=10,
        )
        assert r["tracked"] is True
        assert r["daily_used"] == 10
        assert r["daily_remaining"] == 90

    def test_track_usage_overage(self):
        t = APIQuotaTracker()
        reg = t.register_quota(
            daily_limit=10,
            monthly_limit=100,
        )
        r = t.track_usage(
            quota_id=reg["quota_id"],
            calls=15,
        )
        assert r["overage"] is True

    def test_track_usage_not_found(self):
        t = APIQuotaTracker()
        r = t.track_usage(
            quota_id="invalid",
        )
        assert r["tracked"] is False

    def test_check_reset_timing(self):
        t = APIQuotaTracker()
        reg = t.register_quota(
            api_name="Claude",
            daily_limit=100,
        )
        t.track_usage(
            quota_id=reg["quota_id"],
            calls=50,
        )
        r = t.check_reset_timing(
            quota_id=reg["quota_id"],
            hours_until_daily=12,
        )
        assert r["checked"] is True

    def test_check_reset_not_found(self):
        t = APIQuotaTracker()
        r = t.check_reset_timing(
            quota_id="x",
        )
        assert r["checked"] is False

    def test_check_overage(self):
        t = APIQuotaTracker()
        reg = t.register_quota(
            daily_limit=10,
            monthly_limit=100,
        )
        t.track_usage(
            quota_id=reg["quota_id"],
            calls=15,
        )
        r = t.check_overage()
        assert r["checked"] is True
        assert r["overage_count"] >= 1

    def test_check_overage_warning(self):
        t = APIQuotaTracker()
        reg = t.register_quota(
            daily_limit=100,
            monthly_limit=1000,
        )
        t.track_usage(
            quota_id=reg["quota_id"],
            calls=85,
        )
        r = t.check_overage()
        assert r["warning_count"] >= 1

    def test_get_usage_history(self):
        t = APIQuotaTracker()
        reg = t.register_quota()
        t.track_usage(
            quota_id=reg["quota_id"],
            calls=5,
        )
        r = t.get_usage_history()
        assert r["retrieved"] is True
        assert r["entries"] >= 1

    def test_get_usage_history_filtered(self):
        t = APIQuotaTracker()
        reg = t.register_quota()
        t.track_usage(
            quota_id=reg["quota_id"],
            calls=3,
        )
        r = t.get_usage_history(
            quota_id=reg["quota_id"],
        )
        assert r["entries"] >= 1

    def test_reset_daily(self):
        t = APIQuotaTracker()
        reg = t.register_quota(
            daily_limit=100,
        )
        t.track_usage(
            quota_id=reg["quota_id"],
            calls=50,
        )
        r = t.reset_daily()
        assert r["reset"] is True
        assert r["reset_count"] >= 1

    def test_cost_tracking(self):
        t = APIQuotaTracker()
        reg = t.register_quota(
            cost_per_call=0.01,
            daily_limit=1000,
        )
        r = t.track_usage(
            quota_id=reg["quota_id"],
            calls=100,
        )
        assert r["cost"] == 1.0


# ── LatencyMonitor Testleri ──


class TestLatencyMonitor:
    """LatencyMonitor testleri."""

    def test_init(self):
        m = LatencyMonitor()
        assert m.endpoint_count == 0

    def test_track_endpoint(self):
        m = LatencyMonitor()
        r = m.track_endpoint(
            name="health",
            path="/health",
            baseline_ms=50.0,
        )
        assert r["tracked"] is True

    def test_record_response_time(self):
        m = LatencyMonitor()
        m.track_endpoint(
            name="health",
            baseline_ms=50.0,
        )
        r = m.record_response_time(
            endpoint_name="health",
            response_ms=30.0,
        )
        assert r["recorded"] is True
        assert r["performance"] == "fast"

    def test_record_slow_response(self):
        m = LatencyMonitor()
        m.track_endpoint(
            name="api",
            baseline_ms=100.0,
        )
        r = m.record_response_time(
            endpoint_name="api",
            response_ms=350.0,
        )
        assert r["performance"] == "very_slow"

    def test_record_not_found(self):
        m = LatencyMonitor()
        r = m.record_response_time(
            endpoint_name="x",
        )
        assert r["recorded"] is False

    def test_get_percentiles(self):
        m = LatencyMonitor()
        m.track_endpoint(name="api")
        for ms in [
            10, 20, 30, 40, 50,
            60, 70, 80, 90, 100,
        ]:
            m.record_response_time(
                endpoint_name="api",
                response_ms=float(ms),
            )
        r = m.get_percentiles(
            endpoint_name="api",
        )
        assert r["calculated"] is True
        assert r["sample_count"] == 10
        assert r["p50"] > 0
        assert r["p95"] > r["p50"]

    def test_get_percentiles_empty(self):
        m = LatencyMonitor()
        m.track_endpoint(name="empty")
        r = m.get_percentiles(
            endpoint_name="empty",
        )
        assert r["sample_count"] == 0

    def test_get_percentiles_not_found(self):
        m = LatencyMonitor()
        r = m.get_percentiles(
            endpoint_name="x",
        )
        assert r["calculated"] is False

    def test_find_slow_endpoints(self):
        m = LatencyMonitor()
        m.track_endpoint(name="fast")
        m.track_endpoint(name="slow")
        m.record_response_time(
            endpoint_name="fast",
            response_ms=50.0,
        )
        m.record_response_time(
            endpoint_name="slow",
            response_ms=600.0,
        )
        r = m.find_slow_endpoints(
            threshold_ms=500.0,
        )
        assert r["found"] is True
        assert r["slow_count"] == 1

    def test_analyze_trend_stable(self):
        m = LatencyMonitor()
        m.track_endpoint(name="api")
        for ms in [100, 102, 98, 101, 99]:
            m.record_response_time(
                endpoint_name="api",
                response_ms=float(ms),
            )
        r = m.analyze_trend(
            endpoint_name="api",
        )
        assert r["analyzed"] is True
        assert r["trend"] == "stable"

    def test_analyze_trend_degrading(self):
        m = LatencyMonitor()
        m.track_endpoint(name="api")
        for ms in [100, 150, 200, 250, 300]:
            m.record_response_time(
                endpoint_name="api",
                response_ms=float(ms),
            )
        r = m.analyze_trend(
            endpoint_name="api",
        )
        assert r["trend"] == "degrading"

    def test_analyze_trend_not_found(self):
        m = LatencyMonitor()
        r = m.analyze_trend(
            endpoint_name="x",
        )
        assert r["analyzed"] is False

    def test_compare_baseline(self):
        m = LatencyMonitor()
        m.track_endpoint(
            name="api",
            baseline_ms=100.0,
        )
        m.record_response_time(
            endpoint_name="api",
            response_ms=80.0,
        )
        r = m.compare_baseline(
            endpoint_name="api",
        )
        assert r["compared"] is True
        assert r["verdict"] == "better"

    def test_compare_baseline_worse(self):
        m = LatencyMonitor()
        m.track_endpoint(
            name="api",
            baseline_ms=100.0,
        )
        m.record_response_time(
            endpoint_name="api",
            response_ms=200.0,
        )
        r = m.compare_baseline(
            endpoint_name="api",
        )
        assert r["verdict"] == "significantly_worse"

    def test_compare_baseline_not_found(self):
        m = LatencyMonitor()
        r = m.compare_baseline(
            endpoint_name="x",
        )
        assert r["compared"] is False


# ── UptimeChart Testleri ──


class TestUptimeChart:
    """UptimeChart testleri."""

    def test_init(self):
        u = UptimeChart()
        assert u.service_count == 0

    def test_track_service(self):
        u = UptimeChart()
        r = u.track_service(
            name="Web",
            sla_target=99.9,
        )
        assert r["tracked"] is True

    def test_record_uptime(self):
        u = UptimeChart()
        reg = u.track_service(name="Web")
        r = u.record_uptime(
            service_id=reg["service_id"],
            minutes=60,
        )
        assert r["recorded"] is True
        assert r["uptime_percent"] == 100.0

    def test_record_uptime_not_found(self):
        u = UptimeChart()
        r = u.record_uptime(
            service_id="x",
        )
        assert r["recorded"] is False

    def test_log_downtime(self):
        u = UptimeChart()
        reg = u.track_service(name="Web")
        u.record_uptime(
            service_id=reg["service_id"],
            minutes=1440,
        )
        r = u.log_downtime(
            service_id=reg["service_id"],
            minutes=5,
            reason="Deploy",
        )
        assert r["logged"] is True

    def test_log_downtime_not_found(self):
        u = UptimeChart()
        r = u.log_downtime(
            service_id="x",
        )
        assert r["logged"] is False

    def test_get_sla_status_met(self):
        u = UptimeChart()
        reg = u.track_service(
            name="Web", sla_target=99.0,
        )
        u.record_uptime(
            service_id=reg["service_id"],
            minutes=9950,
        )
        u.log_downtime(
            service_id=reg["service_id"],
            minutes=50,
        )
        r = u.get_sla_status(
            service_id=reg["service_id"],
        )
        assert r["retrieved"] is True
        assert r["sla_met"] is True

    def test_get_sla_status_not_met(self):
        u = UptimeChart()
        reg = u.track_service(
            name="Web", sla_target=99.9,
        )
        u.record_uptime(
            service_id=reg["service_id"],
            minutes=900,
        )
        u.log_downtime(
            service_id=reg["service_id"],
            minutes=100,
        )
        r = u.get_sla_status(
            service_id=reg["service_id"],
        )
        assert r["sla_met"] is False

    def test_get_sla_status_not_found(self):
        u = UptimeChart()
        r = u.get_sla_status(
            service_id="x",
        )
        assert r["retrieved"] is False

    def test_get_history(self):
        u = UptimeChart()
        reg = u.track_service(name="Web")
        u.log_downtime(
            service_id=reg["service_id"],
            minutes=5,
            reason="Deploy",
        )
        r = u.get_history()
        assert r["retrieved"] is True
        assert r["incident_count"] >= 1

    def test_add_incident_marker(self):
        u = UptimeChart()
        r = u.add_incident_marker(
            service_id="sv_1",
            marker_type="deployment",
            description="v2.0 release",
            severity="low",
        )
        assert r["added"] is True


# ── AlertTimeline Testleri ──


class TestAlertTimeline:
    """AlertTimeline testleri."""

    def test_init(self):
        t = AlertTimeline()
        assert t.alert_count == 0

    def test_record_alert(self):
        t = AlertTimeline()
        r = t.record_alert(
            source="CPU",
            message="High usage",
            severity="warning",
        )
        assert r["recorded"] is True
        assert t.alert_count == 1

    def test_get_timeline(self):
        t = AlertTimeline()
        t.record_alert(source="A")
        t.record_alert(source="B")
        r = t.get_timeline()
        assert r["retrieved"] is True
        assert r["total"] == 2

    def test_filter_by_severity(self):
        t = AlertTimeline()
        t.record_alert(
            source="A", severity="warning",
        )
        t.record_alert(
            source="B", severity="critical",
        )
        r = t.filter_by_severity(
            severity="critical",
        )
        assert r["filtered"] is True
        assert r["count"] == 1

    def test_resolve_alert(self):
        t = AlertTimeline()
        rec = t.record_alert(source="X")
        r = t.resolve_alert(
            alert_id=rec["alert_id"],
            resolution="Fixed config",
        )
        assert r["resolved"] is True

    def test_resolve_alert_not_found(self):
        t = AlertTimeline()
        r = t.resolve_alert(
            alert_id="invalid",
        )
        assert r["resolved"] is False

    def test_track_resolution(self):
        t = AlertTimeline()
        rec = t.record_alert(source="A")
        t.record_alert(source="B")
        t.resolve_alert(
            alert_id=rec["alert_id"],
            resolution="Fixed",
        )
        r = t.track_resolution()
        assert r["tracked"] is True
        assert r["resolved"] == 1
        assert r["active"] == 1
        assert r["resolution_rate"] == 50.0

    def test_analyze_patterns(self):
        t = AlertTimeline()
        t.record_alert(
            source="CPU",
            category="resource",
        )
        t.record_alert(
            source="CPU",
            category="resource",
        )
        t.record_alert(
            source="Disk",
            category="resource",
        )
        r = t.analyze_patterns()
        assert r["analyzed"] is True
        assert r["unique_sources"] == 2

    def test_find_correlations(self):
        t = AlertTimeline()
        t.record_alert(source="CPU")
        t.record_alert(source="Memory")
        t.record_alert(source="CPU")
        t.record_alert(source="Memory")
        r = t.find_correlations()
        assert r["found"] is True


# ── HealthDegradationPredictor Testleri ──


class TestHealthDegradationPredictor:
    """HealthDegradationPredictor testleri."""

    def test_init(self):
        p = HealthDegradationPredictor()
        assert p.prediction_count == 0

    def test_add_data_point(self):
        p = HealthDegradationPredictor()
        r = p.add_data_point(
            system_name="Core",
            value=85.0,
        )
        assert r["added"] is True

    def test_predict_degradation(self):
        p = HealthDegradationPredictor()
        for v in [90, 85, 80, 75, 70]:
            p.add_data_point(
                system_name="Core",
                value=float(v),
            )
        r = p.predict_degradation(
            system_name="Core",
        )
        assert r["predicted"] is True
        assert r["avg_change_per_period"] < 0

    def test_predict_insufficient_data(self):
        p = HealthDegradationPredictor()
        p.add_data_point(
            system_name="X", value=90.0,
        )
        r = p.predict_degradation(
            system_name="X",
        )
        assert (
            r["prediction"]
            == "insufficient_data"
        )

    def test_predict_will_degrade(self):
        p = HealthDegradationPredictor()
        for v in [70, 60, 50, 40]:
            p.add_data_point(
                system_name="Failing",
                value=float(v),
            )
        r = p.predict_degradation(
            system_name="Failing",
            horizon_periods=5,
        )
        assert r["will_degrade"] is True

    def test_get_early_warnings(self):
        p = HealthDegradationPredictor()
        for v in [60, 55, 50, 45]:
            p.add_data_point(
                system_name="Weak",
                value=float(v),
            )
        r = p.get_early_warnings(
            threshold=70.0,
        )
        assert r["retrieved"] is True
        assert r["warning_count"] >= 1

    def test_project_trend(self):
        p = HealthDegradationPredictor()
        for v in [90, 85, 80, 75, 70]:
            p.add_data_point(
                system_name="T",
                value=float(v),
            )
        r = p.project_trend(
            system_name="T",
            periods=5,
        )
        assert r["projected"] is True
        assert r["direction"] == "declining"

    def test_project_trend_improving(self):
        p = HealthDegradationPredictor()
        for v in [70, 75, 80, 85, 90]:
            p.add_data_point(
                system_name="Up",
                value=float(v),
            )
        r = p.project_trend(
            system_name="Up",
        )
        assert r["direction"] == "improving"

    def test_project_trend_insufficient(self):
        p = HealthDegradationPredictor()
        p.add_data_point(
            system_name="X", value=90.0,
        )
        r = p.project_trend(
            system_name="X",
        )
        assert (
            r["trend"] == "insufficient_data"
        )

    def test_score_risk_low(self):
        p = HealthDegradationPredictor()
        for v in [95, 96, 97]:
            p.add_data_point(
                system_name="Safe",
                value=float(v),
            )
        r = p.score_risk(
            system_name="Safe",
        )
        assert r["scored"] is True
        assert r["risk_level"] == "low"

    def test_score_risk_high(self):
        p = HealthDegradationPredictor()
        for v in [60, 50, 40, 30]:
            p.add_data_point(
                system_name="Risky",
                value=float(v),
            )
        r = p.score_risk(
            system_name="Risky",
        )
        assert r["risk_level"] in [
            "high", "critical"
        ]

    def test_score_risk_empty(self):
        p = HealthDegradationPredictor()
        r = p.score_risk(
            system_name="Empty",
        )
        assert r["risk_score"] == 0.0

    def test_get_recommendations_healthy(self):
        p = HealthDegradationPredictor()
        p.add_data_point(
            system_name="OK", value=95.0,
        )
        r = p.get_recommendations(
            system_name="OK",
        )
        assert r["retrieved"] is True
        assert (
            r["recommendations"][0]["action"]
            == "continue_monitoring"
        )

    def test_get_recommendations_critical(self):
        p = HealthDegradationPredictor()
        p.add_data_point(
            system_name="Crit", value=20.0,
        )
        r = p.get_recommendations(
            system_name="Crit",
        )
        assert (
            r["recommendations"][0]["priority"]
            == "critical"
        )

    def test_get_recommendations_empty(self):
        p = HealthDegradationPredictor()
        r = p.get_recommendations(
            system_name="None",
        )
        assert r["recommendations"] == []

    def test_get_recommendations_declining(self):
        p = HealthDegradationPredictor()
        for v in [80, 75, 70]:
            p.add_data_point(
                system_name="Dec",
                value=float(v),
            )
        r = p.get_recommendations(
            system_name="Dec",
        )
        assert any(
            rec["action"]
            == "investigate_decline"
            for rec in r["recommendations"]
        )


# ── HealthDashOrchestrator Testleri ──


class TestHealthDashOrchestrator:
    """HealthDashOrchestrator testleri."""

    def test_init(self):
        o = HealthDashOrchestrator()
        assert o is not None

    def test_full_health_check_normal(self):
        o = HealthDashOrchestrator()
        r = o.full_health_check(
            cpu_percent=45.0,
            memory_used_mb=4096.0,
            memory_total_mb=8192.0,
            disk_used_gb=50.0,
            disk_total_gb=100.0,
        )
        assert r["completed"] is True
        assert r["overall_status"] == "healthy"
        assert r["resource_issues"] == 0

    def test_full_health_check_warning(self):
        o = HealthDashOrchestrator()
        r = o.full_health_check(
            cpu_percent=85.0,
            memory_used_mb=4096.0,
            memory_total_mb=8192.0,
        )
        assert r["overall_status"] == "warning"

    def test_full_health_check_critical(self):
        o = HealthDashOrchestrator()
        r = o.full_health_check(
            cpu_percent=95.0,
            memory_used_mb=7800.0,
            memory_total_mb=8192.0,
        )
        assert r["overall_status"] == "critical"

    def test_register_and_check_systems(self):
        o = HealthDashOrchestrator()
        r = o.register_and_check_systems()
        assert r["completed"] is True
        assert r["registered_count"] == 4

    def test_register_custom_systems(self):
        o = HealthDashOrchestrator()
        r = o.register_and_check_systems(
            systems=[
                {
                    "name": "CustomSys",
                    "category": "test",
                },
            ]
        )
        assert r["registered_count"] == 1

    def test_monitor_and_predict(self):
        o = HealthDashOrchestrator()
        r = o.monitor_and_predict(
            system_name="Core",
            health_values=[
                95.0, 90.0, 85.0, 80.0, 75.0,
            ],
        )
        assert r["completed"] is True
        assert r["data_points"] == 5
        assert "prediction" in r
        assert "risk" in r

    def test_monitor_and_predict_default(self):
        o = HealthDashOrchestrator()
        r = o.monitor_and_predict(
            system_name="Default",
        )
        assert r["completed"] is True

    def test_get_analytics(self):
        o = HealthDashOrchestrator()
        r = o.get_analytics()
        assert r["retrieved"] is True
        assert r["components"] == 8
        assert "systems" in r
        assert "alerts" in r
        assert "predictions" in r

    def test_full_pipeline(self):
        o = HealthDashOrchestrator()
        o.register_and_check_systems()
        o.full_health_check()
        o.monitor_and_predict(
            system_name="Master Agent",
        )
        r = o.get_analytics()
        assert r["retrieved"] is True
        assert r["systems"] >= 4
