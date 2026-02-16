"""ATLAS Health & Uptime Guardian testleri."""

import time

from app.core.guardian.auto_scaler import (
    GuardianAutoScaler,
)
from app.core.guardian.degradation_predictor import (
    DegradationPredictor,
)
from app.core.guardian.guardian_orchestrator import (
    GuardianOrchestrator,
)
from app.core.guardian.incident_responder import (
    IncidentResponder,
)
from app.core.guardian.postmortem_generator import (
    PostmortemGenerator,
)
from app.core.guardian.recovery_automator import (
    RecoveryAutomator,
)
from app.core.guardian.sla_enforcer import (
    SLAEnforcer,
)
from app.core.guardian.system_pulse_checker import (
    SystemPulseChecker,
)
from app.core.guardian.uptime_tracker import (
    UptimeTracker,
)


# ── SystemPulseChecker ──


class TestPulseCheckerInit:
    def test_init(self):
        p = SystemPulseChecker()
        assert p.check_count == 0
        assert p.component_count == 0


class TestRegisterComponent:
    def test_basic(self):
        p = SystemPulseChecker()
        r = p.register_component(
            "api",
            component_type="service",
        )
        assert r["registered"] is True
        assert r["name"] == "api"
        assert p.component_count == 1


class TestCheckHealth:
    def test_healthy(self):
        p = SystemPulseChecker()
        p.register_component("api")
        r = p.check_health(
            "api",
            response_time_ms=100.0,
            is_healthy=True,
        )
        assert r["checked"] is True
        assert r["status"] == "healthy"

    def test_unhealthy(self):
        p = SystemPulseChecker()
        p.register_component("api")
        r = p.check_health(
            "api",
            response_time_ms=100.0,
            is_healthy=False,
        )
        assert r["status"] == "unhealthy"

    def test_not_registered(self):
        p = SystemPulseChecker()
        r = p.check_health("unknown")
        assert r["checked"] is False


class TestGetComponentStatus:
    def test_found(self):
        p = SystemPulseChecker()
        p.register_component("db")
        p.check_health(
            "db",
            response_time_ms=50.0,
            is_healthy=True,
        )
        r = p.get_component_status("db")
        assert r["found"] is True
        assert r["status"] == "healthy"

    def test_not_found(self):
        p = SystemPulseChecker()
        r = p.get_component_status("x")
        assert r["found"] is False


class TestDependencyHealth:
    def test_all_healthy(self):
        p = SystemPulseChecker()
        p.register_component("db")
        p.register_component("redis")
        p.check_health(
            "db", 50.0, True,
        )
        p.check_health(
            "redis", 30.0, True,
        )
        r = p.check_dependency_health(
            "api",
            dependencies=["db", "redis"],
        )
        assert r["all_healthy"] is True
        assert r["health_pct"] == 100.0

    def test_some_unhealthy(self):
        p = SystemPulseChecker()
        p.register_component("db")
        p.check_health(
            "db", 50.0, True,
        )
        r = p.check_dependency_health(
            "api",
            dependencies=["db", "missing"],
        )
        assert r["all_healthy"] is False
        assert "missing" in r["unhealthy"]


class TestMeasureResponseTime:
    def test_fast(self):
        p = SystemPulseChecker()
        p.register_component(
            "api", timeout_ms=1000.0,
        )
        r = p.measure_response_time(
            "api", 200.0,
        )
        assert r["measured"] is True
        assert r["level"] == "fast"

    def test_not_registered(self):
        p = SystemPulseChecker()
        r = p.measure_response_time("x")
        assert r["measured"] is False


class TestCheckResourceUsage:
    def test_normal(self):
        p = SystemPulseChecker()
        r = p.check_resource_usage(
            "api",
            cpu_pct=50.0,
            memory_pct=60.0,
            disk_pct=40.0,
        )
        assert r["level"] == "normal"

    def test_critical(self):
        p = SystemPulseChecker()
        r = p.check_resource_usage(
            "api",
            cpu_pct=95.0,
            memory_pct=95.0,
            disk_pct=95.0,
        )
        assert r["level"] == "critical"


# ── UptimeTracker ──


class TestUptimeTrackerInit:
    def test_init(self):
        u = UptimeTracker()
        assert u.service_count == 0
        assert u.downtime_count == 0


class TestTrackService:
    def test_basic(self):
        u = UptimeTracker()
        r = u.track_service(
            "api", sla_target=99.9,
        )
        assert r["tracked"] is True
        assert u.service_count == 1


class TestCalculateUptime:
    def test_full(self):
        u = UptimeTracker()
        u.track_service("api")
        r = u.calculate_uptime(
            "api", period_hours=24.0,
        )
        assert r["calculated"] is True
        assert r["uptime_pct"] == 100.0

    def test_with_downtime(self):
        u = UptimeTracker()
        u.track_service("api")
        u.log_downtime(
            "api", duration_sec=3600.0,
        )
        r = u.calculate_uptime(
            "api", period_hours=24.0,
        )
        assert r["uptime_pct"] < 100.0

    def test_not_tracked(self):
        u = UptimeTracker()
        r = u.calculate_uptime("x")
        assert r["calculated"] is False


class TestLogDowntime:
    def test_basic(self):
        u = UptimeTracker()
        u.track_service("api")
        r = u.log_downtime(
            "api",
            duration_sec=300.0,
            reason="deployment",
        )
        assert r["logged"] is True
        assert u.downtime_count == 1


class TestCheckSLA:
    def test_compliant(self):
        u = UptimeTracker()
        u.track_service(
            "api", sla_target=99.9,
        )
        r = u.check_sla(
            "api", period_hours=720.0,
        )
        assert r["checked"] is True
        assert r["status"] == "compliant"

    def test_not_tracked(self):
        u = UptimeTracker()
        r = u.check_sla("x")
        assert r["checked"] is False


class TestAvailabilityMetrics:
    def test_found(self):
        u = UptimeTracker()
        u.track_service("api")
        u.log_downtime("api", 60.0)
        r = u.get_availability_metrics("api")
        assert r["found"] is True
        assert r["total_incidents"] == 1

    def test_not_found(self):
        u = UptimeTracker()
        r = u.get_availability_metrics("x")
        assert r["found"] is False


class TestHistoricalTrend:
    def test_found(self):
        u = UptimeTracker()
        u.track_service("api")
        r = u.get_historical_trend("api")
        assert r["found"] is True
        assert r["trend"] == "improving"

    def test_not_found(self):
        u = UptimeTracker()
        r = u.get_historical_trend("x")
        assert r["found"] is False


# ── DegradationPredictor ──


class TestDegradationInit:
    def test_init(self):
        d = DegradationPredictor()
        assert d.prediction_count == 0
        assert d.anomaly_count == 0


class TestRecordMetric:
    def test_basic(self):
        d = DegradationPredictor()
        r = d.record_metric(
            "api", 100.0, "latency",
        )
        assert r["recorded"] is True
        assert r["data_points"] == 1


class TestAnalyzeTrendDeg:
    def test_stable(self):
        d = DegradationPredictor()
        for v in [100, 102, 98, 101, 99]:
            d.record_metric(
                "api", v, "latency",
            )
        r = d.analyze_trend(
            "api", "latency",
        )
        assert r["analyzed"] is True
        assert r["trend"] == "stable"

    def test_insufficient(self):
        d = DegradationPredictor()
        d.record_metric("api", 100.0)
        r = d.analyze_trend("api")
        assert r["analyzed"] is False


class TestDetectAnomaly:
    def test_anomaly(self):
        d = DegradationPredictor()
        for v in [100, 110, 105]:
            d.record_metric("api", v)
        r = d.detect_anomaly(
            "api", 500.0,
        )
        assert r["is_anomaly"] is True

    def test_normal(self):
        d = DegradationPredictor()
        for v in [100, 110, 105]:
            d.record_metric("api", v)
        r = d.detect_anomaly(
            "api", 108.0,
        )
        assert r["is_anomaly"] is False


class TestPredictFailure:
    def test_predicted(self):
        d = DegradationPredictor()
        for v in [100, 105, 110, 150, 200]:
            d.record_metric("api", v)
        r = d.predict_failure("api")
        assert r["predicted"] is True
        assert r["risk"] in (
            "critical", "high",
            "medium", "low", "none",
        )

    def test_insufficient(self):
        d = DegradationPredictor()
        d.record_metric("api", 100.0)
        r = d.predict_failure("api")
        assert r["predicted"] is False


class TestEarlyWarning:
    def test_warning(self):
        d = DegradationPredictor()
        for v in [100, 110, 120, 180, 250]:
            d.record_metric("api", v)
        r = d.generate_early_warning("api")
        assert r["warning"] is True

    def test_no_warning(self):
        d = DegradationPredictor()
        for v in [100, 100, 100, 100, 100]:
            d.record_metric("api", v)
        r = d.generate_early_warning("api")
        assert r["warning"] is False


class TestRiskScore:
    def test_calculated(self):
        d = DegradationPredictor()
        for v in [100, 110, 120]:
            d.record_metric(
                "api", v, "latency",
            )
        r = d.calculate_risk_score("api")
        assert r["calculated"] is True
        assert r["risk_score"] >= 0

    def test_no_data(self):
        d = DegradationPredictor()
        r = d.calculate_risk_score("api")
        assert r["calculated"] is False


# ── GuardianAutoScaler ──


class TestAutoScalerInit:
    def test_init(self):
        s = GuardianAutoScaler()
        assert s.scale_up_count == 0
        assert s.scale_down_count == 0


class TestRegisterScaleService:
    def test_basic(self):
        s = GuardianAutoScaler()
        r = s.register_service(
            "api",
            min_instances=1,
            max_instances=5,
        )
        assert r["registered"] is True


class TestMonitorLoad:
    def test_high(self):
        s = GuardianAutoScaler()
        s.register_service("api")
        r = s.monitor_load(
            "api",
            cpu_pct=95.0,
            memory_pct=95.0,
            request_rate=90.0,
        )
        assert r["monitored"] is True
        assert r["level"] in (
            "critical", "high",
        )

    def test_not_found(self):
        s = GuardianAutoScaler()
        r = s.monitor_load("x")
        assert r["monitored"] is False


class TestCheckScaleTrigger:
    def test_scale_up(self):
        s = GuardianAutoScaler()
        s.register_service(
            "api", max_instances=5,
        )
        s.monitor_load(
            "api", cpu_pct=95.0,
            memory_pct=95.0,
            request_rate=90.0,
        )
        r = s.check_scale_trigger("api")
        assert r["checked"] is True
        assert r["direction"] == "up"

    def test_not_found(self):
        s = GuardianAutoScaler()
        r = s.check_scale_trigger("x")
        assert r["checked"] is False


class TestAdjustResources:
    def test_scale_up(self):
        s = GuardianAutoScaler()
        s.register_service(
            "api",
            current_instances=2,
            max_instances=5,
        )
        r = s.adjust_resources(
            "api", "up", 1,
        )
        assert r["adjusted"] is True
        assert r["current"] == 3

    def test_scale_down(self):
        s = GuardianAutoScaler()
        s.register_service(
            "api",
            current_instances=3,
            min_instances=1,
        )
        r = s.adjust_resources(
            "api", "down", 1,
        )
        assert r["adjusted"] is True
        assert r["current"] == 2

    def test_not_found(self):
        s = GuardianAutoScaler()
        r = s.adjust_resources("x")
        assert r["adjusted"] is False


class TestHandleCooldown:
    def test_checked(self):
        s = GuardianAutoScaler()
        s.register_service("api")
        r = s.handle_cooldown("api")
        assert r["checked"] is True
        assert r["in_cooldown"] is False

    def test_not_found(self):
        s = GuardianAutoScaler()
        r = s.handle_cooldown("x")
        assert r["checked"] is False


class TestOptimizeCost:
    def test_optimized(self):
        s = GuardianAutoScaler()
        s.register_service(
            "api", current_instances=5,
        )
        s.monitor_load(
            "api", cpu_pct=30.0,
            memory_pct=20.0,
        )
        r = s.optimize_cost(
            "api", cost_per_instance=10.0,
        )
        assert r["optimized"] is True
        assert r["savings"] >= 0

    def test_not_found(self):
        s = GuardianAutoScaler()
        r = s.optimize_cost("x")
        assert r["optimized"] is False


# ── IncidentResponder ──


class TestIncidentInit:
    def test_init(self):
        i = IncidentResponder()
        assert i.incident_count == 0
        assert i.remediation_count == 0


class TestDetectIncident:
    def test_basic(self):
        i = IncidentResponder()
        r = i.detect_incident(
            "api",
            severity="high",
            description="Down",
        )
        assert r["detected"] is True
        assert r["status"] == "open"
        assert i.incident_count == 1


class TestAutoRemediate:
    def test_success(self):
        i = IncidentResponder()
        inc = i.detect_incident(
            "api", severity="medium",
        )
        r = i.auto_remediate(
            inc["incident_id"],
            action="restart",
        )
        assert r["remediated"] is True

    def test_critical_blocked(self):
        i = IncidentResponder()
        inc = i.detect_incident(
            "api", severity="critical",
        )
        r = i.auto_remediate(
            inc["incident_id"],
        )
        assert r["remediated"] is False

    def test_not_found(self):
        i = IncidentResponder()
        r = i.auto_remediate("x")
        assert r["remediated"] is False


class TestEscalate:
    def test_basic(self):
        i = IncidentResponder()
        inc = i.detect_incident(
            "api", severity="high",
        )
        r = i.escalate(
            inc["incident_id"],
            level="team_lead",
        )
        assert r["escalated"] is True

    def test_not_found(self):
        i = IncidentResponder()
        r = i.escalate("x")
        assert r["escalated"] is False


class TestSendCommunication:
    def test_basic(self):
        i = IncidentResponder()
        inc = i.detect_incident("api")
        r = i.send_communication(
            inc["incident_id"],
            channel="telegram",
        )
        assert r["sent"] is True

    def test_not_found(self):
        i = IncidentResponder()
        r = i.send_communication("x")
        assert r["sent"] is False


class TestUpdateIncidentStatus:
    def test_basic(self):
        i = IncidentResponder()
        inc = i.detect_incident("api")
        r = i.update_status(
            inc["incident_id"],
            status="resolved",
        )
        assert r["updated"] is True
        assert r["new_status"] == "resolved"

    def test_not_found(self):
        i = IncidentResponder()
        r = i.update_status("x")
        assert r["updated"] is False


# ── PostmortemGenerator ──


class TestPostmortemInit:
    def test_init(self):
        p = PostmortemGenerator()
        assert p.report_count == 0
        assert p.lesson_count == 0


class TestCreateTimeline:
    def test_basic(self):
        p = PostmortemGenerator()
        events = [
            {"event": "detected",
             "timestamp": 1000},
            {"event": "resolved",
             "timestamp": 1300},
        ]
        r = p.create_timeline(
            "inc_1", events=events,
        )
        assert r["created"] is True
        assert r["events"] == 2
        assert r["duration_sec"] == 300.0


class TestAnalyzeRootCause:
    def test_recent_change(self):
        p = PostmortemGenerator()
        r = p.analyze_root_cause(
            "inc_1",
            change_log=["deploy v2.0"],
        )
        assert r["analyzed"] is True
        assert r["root_cause"] == (
            "recent_change"
        )

    def test_unknown(self):
        p = PostmortemGenerator()
        r = p.analyze_root_cause("inc_1")
        assert r["root_cause"] == "unknown"


class TestAssessImpact:
    def test_low(self):
        p = PostmortemGenerator()
        r = p.assess_impact(
            "inc_1",
            affected_users=10,
            downtime_min=5.0,
        )
        assert r["assessed"] is True
        assert r["severity"] == "low"

    def test_high(self):
        p = PostmortemGenerator()
        r = p.assess_impact(
            "inc_1",
            affected_users=5000,
            revenue_impact=50000,
            downtime_min=120,
            affected_services=[
                "api", "web", "db", "cache",
            ],
        )
        assert r["severity"] in (
            "critical", "high",
        )


class TestGenerateActionItems:
    def test_with_cause(self):
        p = PostmortemGenerator()
        r = p.generate_action_items(
            "inc_1",
            root_cause="recent_change",
            severity="high",
        )
        assert r["generated"] is True
        assert r["action_count"] >= 3


class TestCaptureLessons:
    def test_basic(self):
        p = PostmortemGenerator()
        r = p.capture_lessons(
            "inc_1",
            what_worked=["Quick detection"],
            what_failed=["Slow response"],
            improvements=["Add alerts"],
        )
        assert r["captured"] is True
        assert r["worked_count"] == 1
        assert p.lesson_count == 1


class TestGeneratePostmortem:
    def test_basic(self):
        p = PostmortemGenerator()
        r = p.generate_report(
            "inc_1",
            component="api",
            severity="high",
            symptoms=["timeout"],
        )
        assert r["generated"] is True
        assert p.report_count == 1


# ── SLAEnforcer ──


class TestSLAEnforcerInit:
    def test_init(self):
        s = SLAEnforcer()
        assert s.sla_count == 0
        assert s.breach_count == 0


class TestDefineSLA:
    def test_basic(self):
        s = SLAEnforcer()
        r = s.define_sla(
            "api", uptime_target=99.9,
        )
        assert r["defined"] is True
        assert s.sla_count == 1


class TestMonitorCompliance:
    def test_compliant(self):
        s = SLAEnforcer()
        s.define_sla(
            "api",
            uptime_target=99.9,
            response_time_ms=500.0,
            error_rate_pct=0.1,
        )
        r = s.monitor_compliance(
            "api",
            current_uptime=99.95,
            current_response_ms=200.0,
            current_error_rate=0.05,
        )
        assert r["monitored"] is True
        assert r["status"] == "compliant"

    def test_breached(self):
        s = SLAEnforcer()
        s.define_sla("api")
        r = s.monitor_compliance(
            "api",
            current_uptime=95.0,
            current_response_ms=1000.0,
            current_error_rate=5.0,
        )
        assert r["status"] == "breached"

    def test_not_found(self):
        s = SLAEnforcer()
        r = s.monitor_compliance("x")
        assert r["monitored"] is False


class TestDetectBreach:
    def test_breach(self):
        s = SLAEnforcer()
        s.define_sla(
            "api", uptime_target=99.9,
        )
        r = s.detect_breach(
            "api",
            metric="uptime",
            actual_value=98.0,
        )
        assert r["checked"] is True
        assert r["is_breach"] is True
        assert s.breach_count == 1

    def test_no_breach(self):
        s = SLAEnforcer()
        s.define_sla(
            "api", uptime_target=99.9,
        )
        r = s.detect_breach(
            "api",
            metric="uptime",
            actual_value=99.95,
        )
        assert r["is_breach"] is False

    def test_not_found(self):
        s = SLAEnforcer()
        r = s.detect_breach("x")
        assert r["checked"] is False


class TestSLAAlert:
    def test_basic(self):
        s = SLAEnforcer()
        r = s.generate_alert(
            "api", alert_type="breach",
        )
        assert r["generated"] is True


class TestSLAReport:
    def test_generated(self):
        s = SLAEnforcer()
        s.define_sla("api")
        r = s.generate_report("api")
        assert r["generated"] is True

    def test_not_found(self):
        s = SLAEnforcer()
        r = s.generate_report("x")
        assert r["generated"] is False


# ── RecoveryAutomator ──


class TestRecoveryInit:
    def test_init(self):
        r = RecoveryAutomator()
        assert r.recovery_count == 0
        assert r.rollback_count == 0


class TestDefineProcedure:
    def test_basic(self):
        r = RecoveryAutomator()
        res = r.define_procedure(
            "api",
            steps=["restart", "verify"],
        )
        assert res["defined"] is True
        assert res["steps"] == 2


class TestExecuteFix:
    def test_basic(self):
        r = RecoveryAutomator()
        r.define_procedure("api")
        res = r.execute_fix(
            "api", fix_type="restart",
        )
        assert res["executed"] is True
        assert res["status"] == "success"
        assert r.recovery_count == 1


class TestTriggerRollback:
    def test_basic(self):
        r = RecoveryAutomator()
        res = r.trigger_rollback(
            "api", reason="failed deploy",
        )
        assert res["triggered"] is True
        assert res["status"] == "completed"
        assert r.rollback_count == 1


class TestVerifyHealth:
    def test_healthy(self):
        r = RecoveryAutomator()
        res = r.verify_health(
            "api",
            checks={
                "ping": True,
                "db": True,
                "cache": True,
            },
        )
        assert res["healthy"] is True
        assert res["health_pct"] == 100.0

    def test_unhealthy(self):
        r = RecoveryAutomator()
        res = r.verify_health(
            "api",
            checks={
                "ping": True,
                "db": False,
                "cache": False,
                "queue": False,
                "storage": False,
            },
        )
        assert res["healthy"] is False

    def test_no_checks(self):
        r = RecoveryAutomator()
        res = r.verify_health("api")
        assert res["healthy"] is False


class TestConfirmSuccess:
    def test_verified(self):
        r = RecoveryAutomator()
        fix = r.execute_fix("api")
        res = r.confirm_success(
            fix["recovery_id"],
            verified=True,
        )
        assert res["confirmed"] is True
        assert res["status"] == "verified"

    def test_not_found(self):
        r = RecoveryAutomator()
        res = r.confirm_success("x")
        assert res["confirmed"] is False


# ── GuardianOrchestrator ──


class TestGuardianOrchInit:
    def test_init(self):
        g = GuardianOrchestrator()
        assert g.check_count == 0
        assert g.response_count == 0


class TestRunFullHealthCheck:
    def test_healthy(self):
        g = GuardianOrchestrator()
        r = g.run_full_health_check(
            "api",
            response_time_ms=100.0,
            is_healthy=True,
        )
        assert r["check_complete"] is True
        assert r["health_status"] == "healthy"

    def test_unhealthy(self):
        g = GuardianOrchestrator()
        r = g.run_full_health_check(
            "api",
            response_time_ms=100.0,
            is_healthy=False,
        )
        assert r["health_status"] == (
            "unhealthy"
        )


class TestMonitorPredictRespond:
    def test_healthy(self):
        g = GuardianOrchestrator()
        r = g.monitor_predict_respond(
            "api",
            response_time_ms=50.0,
            is_healthy=True,
        )
        assert r["pipeline_complete"] is True
        assert r["incident_created"] is False

    def test_unhealthy(self):
        g = GuardianOrchestrator()
        r = g.monitor_predict_respond(
            "api",
            response_time_ms=100.0,
            is_healthy=False,
        )
        assert r["incident_created"] is True
        assert r["incident_id"] is not None


class TestProtect247:
    def test_basic(self):
        g = GuardianOrchestrator()
        r = g.protect_247(
            services=["api", "db"],
        )
        assert r["protection_active"] is True
        assert r["services_monitored"] == 2


class TestGuardianAnalytics:
    def test_basic(self):
        g = GuardianOrchestrator()
        g.run_full_health_check("api")
        r = g.get_analytics()
        assert r["full_checks"] == 1
        assert r["health_checks"] >= 1

    def test_empty(self):
        g = GuardianOrchestrator()
        r = g.get_analytics()
        assert r["full_checks"] == 0
        assert r["incidents"] == 0


# ── Config ──


class TestGuardianConfig:
    def test_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.guardian_enabled is True
        assert s.health_check_interval == 60
        assert s.auto_remediate is True
        assert s.sla_target == 99.9
        assert (
            s.incident_auto_escalate is True
        )


# ── Imports ──


class TestGuardianImports:
    def test_all_imports(self):
        from app.core.guardian import (
            DegradationPredictor,
            GuardianAutoScaler,
            GuardianOrchestrator,
            IncidentResponder,
            PostmortemGenerator,
            RecoveryAutomator,
            SLAEnforcer,
            SystemPulseChecker,
            UptimeTracker,
        )
        assert SystemPulseChecker
        assert UptimeTracker
        assert DegradationPredictor
        assert GuardianAutoScaler
        assert IncidentResponder
        assert PostmortemGenerator
        assert SLAEnforcer
        assert RecoveryAutomator
        assert GuardianOrchestrator
