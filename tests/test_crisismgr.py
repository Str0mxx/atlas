"""ATLAS Disaster & Crisis Management testleri.

CrisisMgrDetector, EscalationProtocol,
CrisisCommunicationTemplate, StakeholderNotifier,
CrisisActionPlanGenerator, PostCrisisAnalyzer,
CrisisSimulationRunner, CrisisRecoveryTracker,
CrisisMgrOrchestrator testleri.
"""

import pytest

from app.core.crisismgr.action_plan_generator import (
    CrisisActionPlanGenerator,
)
from app.core.crisismgr.communication_template import (
    CrisisCommunicationTemplate,
)
from app.core.crisismgr.crisis_detector import (
    CrisisMgrDetector,
)
from app.core.crisismgr.crisismgr_orchestrator import (
    CrisisMgrOrchestrator,
)
from app.core.crisismgr.escalation_protocol import (
    EscalationProtocol,
)
from app.core.crisismgr.post_crisis_analyzer import (
    PostCrisisAnalyzer,
)
from app.core.crisismgr.recovery_tracker import (
    CrisisRecoveryTracker,
)
from app.core.crisismgr.simulation_runner import (
    CrisisSimulationRunner,
)
from app.core.crisismgr.stakeholder_notifier import (
    StakeholderNotifier,
)
from app.models.crisismgr_models import (
    ActionPlanRecord,
    CrisisLevel,
    CrisisRecord,
    CrisisStatus,
    EscalationRecord,
    EscalationTier,
    NotificationChannel,
    RecoveryPhase,
    RecoveryRecord,
    SimulationType,
)


# ── CrisisMgrDetector ───────────────────


class TestDetectAnomaly:
    """detect_anomaly testleri."""

    def test_anomaly(self):
        d = CrisisMgrDetector()
        r = d.detect_anomaly(
            "error_rate",
            current_value=10.0,
            baseline=2.0,
            std_dev=1.0,
        )
        assert r["detected"] is True
        assert r["is_anomaly"] is True
        assert d.anomaly_count == 1

    def test_normal(self):
        d = CrisisMgrDetector()
        r = d.detect_anomaly(
            "error_rate",
            current_value=2.5,
            baseline=2.0,
            std_dev=1.0,
        )
        assert r["is_anomaly"] is False

    def test_critical_severity(self):
        d = CrisisMgrDetector()
        r = d.detect_anomaly(
            "cpu",
            current_value=100.0,
            baseline=20.0,
            std_dev=5.0,
        )
        assert r["severity"] == "critical"


class TestMonitorThreshold:
    """monitor_threshold testleri."""

    def test_critical(self):
        d = CrisisMgrDetector()
        r = d.monitor_threshold(
            "cpu", value=95.0,
            warn_threshold=80.0,
            critical_threshold=90.0,
        )
        assert r["status"] == "critical"

    def test_warning(self):
        d = CrisisMgrDetector()
        r = d.monitor_threshold(
            "cpu", value=85.0,
            warn_threshold=80.0,
            critical_threshold=90.0,
        )
        assert r["status"] == "warning"

    def test_normal(self):
        d = CrisisMgrDetector()
        r = d.monitor_threshold(
            "cpu", value=50.0,
            warn_threshold=80.0,
            critical_threshold=90.0,
        )
        assert r["status"] == "normal"


class TestRecognizePattern:
    """recognize_pattern testleri."""

    def test_spike(self):
        d = CrisisMgrDetector()
        events = [
            {"value": 1}, {"value": 2},
            {"value": 100},
        ]
        r = d.recognize_pattern(
            events, "spike",
        )
        assert r["matched"] is True

    def test_trend_up(self):
        d = CrisisMgrDetector()
        events = [
            {"value": 1}, {"value": 3},
            {"value": 7},
        ]
        r = d.recognize_pattern(
            events, "trend_up",
        )
        assert r["matched"] is True

    def test_empty(self):
        d = CrisisMgrDetector()
        r = d.recognize_pattern([], "spike")
        assert r["matched"] is False


class TestFuseSignals:
    """fuse_signals testleri."""

    def test_critical(self):
        d = CrisisMgrDetector()
        signals = [
            {"severity": "critical"},
            {"severity": "high"},
        ]
        r = d.fuse_signals(signals)
        assert r["fused"] is True
        assert r["crisis_level"] in [
            "critical", "high",
        ]

    def test_low(self):
        d = CrisisMgrDetector()
        signals = [
            {"severity": "low"},
        ]
        r = d.fuse_signals(signals)
        assert r["crisis_level"] == "low"

    def test_empty(self):
        d = CrisisMgrDetector()
        r = d.fuse_signals([])
        assert r["crisis_level"] == "low"


class TestIssueEarlyWarning:
    """issue_early_warning testleri."""

    def test_basic(self):
        d = CrisisMgrDetector()
        r = d.issue_early_warning(
            "outage", confidence=0.85,
        )
        assert r["issued"] is True
        assert d.warning_count == 1


# ── EscalationProtocol ──────────────────


class TestDefineLevels:
    """define_levels testleri."""

    def test_default(self):
        e = EscalationProtocol()
        r = e.define_levels("crisis_1")
        assert r["defined"] is True
        assert r["level_count"] == 4


class TestSetContactChain:
    """set_contact_chain testleri."""

    def test_basic(self):
        e = EscalationProtocol()
        r = e.set_contact_chain(
            "crisis_1",
            contacts=[
                {"name": "A", "tier": "tier1"},
            ],
        )
        assert r["set_ok"] is True


class TestGetResponseTime:
    """get_response_time testleri."""

    def test_tier1(self):
        e = EscalationProtocol()
        r = e.get_response_time("tier1")
        assert r["retrieved"] is True
        assert r["max_response_seconds"] == 300


class TestAutoEscalate:
    """auto_escalate testleri."""

    def test_escalate(self):
        e = EscalationProtocol()
        r = e.auto_escalate(
            "crisis_1",
            current_tier="tier1",
            elapsed_seconds=600,
        )
        assert r["escalated"] is True
        assert r["to_tier"] == "tier2"
        assert e.escalation_count == 1

    def test_no_escalate(self):
        e = EscalationProtocol()
        r = e.auto_escalate(
            "crisis_1",
            current_tier="tier1",
            elapsed_seconds=100,
        )
        assert r["escalated"] is False


class TestOverride:
    """override testleri."""

    def test_basic(self):
        e = EscalationProtocol()
        r = e.override(
            "crisis_1",
            target_tier="executive",
            reason="CEO request",
        )
        assert r["overridden"] is True
        assert e.override_count == 1


# ── CrisisCommunicationTemplate ─────────


class TestCreateCrisisTemplate:
    """create_template testleri."""

    def test_basic(self):
        c = CrisisCommunicationTemplate()
        r = c.create_template(
            "outage_notice",
            body="System {{system}} is down",
        )
        assert r["created"] is True
        assert c.template_count == 1


class TestTargetAudience:
    """target_audience testleri."""

    def test_basic(self):
        c = CrisisCommunicationTemplate()
        c.create_template("notice")
        r = c.target_audience(
            "notice", "external",
        )
        assert r["targeted"] is True

    def test_not_found(self):
        c = CrisisCommunicationTemplate()
        r = c.target_audience("xxx")
        assert r["found"] is False


class TestAdaptTone:
    """adapt_tone testleri."""

    def test_critical(self):
        c = CrisisCommunicationTemplate()
        c.create_template("notice")
        r = c.adapt_tone(
            "notice", crisis_level="critical",
        )
        assert r["tone"] == "urgent"


class TestGenerateCrisisMessage:
    """generate_message testleri."""

    def test_basic(self):
        c = CrisisCommunicationTemplate()
        c.create_template(
            "notice",
            body="Alert: {{issue}}",
        )
        r = c.generate_message(
            "notice",
            variables={"issue": "Outage"},
        )
        assert r["generated"] is True
        assert "Outage" in r["message"]
        assert c.message_count == 1

    def test_not_found(self):
        c = CrisisCommunicationTemplate()
        r = c.generate_message("xxx")
        assert r["found"] is False


class TestUpdateCrisisVersion:
    """update_version testleri."""

    def test_basic(self):
        c = CrisisCommunicationTemplate()
        c.create_template("notice")
        r = c.update_version(
            "notice", new_body="Updated",
        )
        assert r["updated"] is True
        assert r["version"] == 2


# ── StakeholderNotifier ─────────────────


class TestRouteNotification:
    """route_notification testleri."""

    def test_basic(self):
        n = StakeholderNotifier()
        r = n.route_notification(
            "crisis_1",
            stakeholder="fatih",
            message="Alert!",
        )
        assert r["sent"] is True
        assert n.notification_count == 1


class TestHandlePriority:
    """handle_priority testleri."""

    def test_critical(self):
        n = StakeholderNotifier()
        r = n.handle_priority(
            "crisis_1", "critical",
        )
        assert "phone" in r["channels"]

    def test_low(self):
        n = StakeholderNotifier()
        r = n.handle_priority(
            "crisis_1", "low",
        )
        assert r["channels"] == ["email"]


class TestTrackConfirmation:
    """track_confirmation testleri."""

    def test_confirmed(self):
        n = StakeholderNotifier()
        r = n.track_confirmation(
            "ntf_1", confirmed=True,
        )
        assert r["tracked"] is True
        assert r["confirmed"] is True


class TestEscalateNoResponse:
    """escalate_no_response testleri."""

    def test_escalate(self):
        n = StakeholderNotifier()
        r = n.escalate_no_response(
            "ntf_1",
            timeout_seconds=300,
            elapsed_seconds=600,
        )
        assert r["should_escalate"] is True
        assert n.escalation_count == 1

    def test_no_escalate(self):
        n = StakeholderNotifier()
        n.track_confirmation(
            "ntf_1", confirmed=True,
        )
        r = n.escalate_no_response(
            "ntf_1",
            elapsed_seconds=600,
        )
        assert r["should_escalate"] is False


class TestGetAuditLog:
    """get_audit_log testleri."""

    def test_basic(self):
        n = StakeholderNotifier()
        n.route_notification(
            "crisis_1", "fatih",
        )
        r = n.get_audit_log()
        assert r["count"] >= 1


# ── CrisisActionPlanGenerator ───────────


class TestGeneratePlan:
    """generate_plan testleri."""

    def test_general(self):
        p = CrisisActionPlanGenerator()
        r = p.generate_plan("crisis_1")
        assert r["generated"] is True
        assert r["step_count"] >= 3
        assert p.plan_count == 1

    def test_outage(self):
        p = CrisisActionPlanGenerator()
        r = p.generate_plan(
            "crisis_1", crisis_type="outage",
        )
        assert "Restore service" in r["steps"]


class TestAssignTask:
    """assign_task testleri."""

    def test_basic(self):
        p = CrisisActionPlanGenerator()
        r = p.assign_task(
            "crisis_1",
            "Investigate root cause",
            assignee="fatih",
        )
        assert r["assigned"] is True
        assert p.task_count == 1


class TestCreateTimeline:
    """create_timeline testleri."""

    def test_basic(self):
        p = CrisisActionPlanGenerator()
        p.generate_plan("crisis_1")
        r = p.create_timeline("crisis_1")
        assert r["created"] is True
        assert r["total_minutes"] > 0

    def test_not_found(self):
        p = CrisisActionPlanGenerator()
        r = p.create_timeline("xxx")
        assert r["found"] is False


class TestAllocateResources:
    """allocate_resources testleri."""

    def test_basic(self):
        p = CrisisActionPlanGenerator()
        r = p.allocate_resources(
            "crisis_1",
            resources={"engineers": 3},
        )
        assert r["allocated"] is True
        assert r["total_units"] == 3


class TestAddDependency:
    """add_dependency testleri."""

    def test_basic(self):
        p = CrisisActionPlanGenerator()
        t1 = p.assign_task(
            "crisis_1", "Task A",
        )
        t2 = p.assign_task(
            "crisis_1", "Task B",
        )
        r = p.add_dependency(
            "crisis_1",
            t2["task_id"],
            t1["task_id"],
        )
        assert r["added"] is True


# ── PostCrisisAnalyzer ──────────────────


class TestRootCauseAnalysis:
    """root_cause_analysis testleri."""

    def test_basic(self):
        a = PostCrisisAnalyzer()
        r = a.root_cause_analysis(
            "crisis_1",
            symptoms=["high latency"],
            contributing_factors=[
                "DB overload",
            ],
        )
        assert r["analyzed"] is True
        assert r["root_cause"] == "DB overload"
        assert a.analysis_count == 1


class TestReconstructTimeline:
    """reconstruct_timeline testleri."""

    def test_basic(self):
        a = PostCrisisAnalyzer()
        events = [
            {"event": "alert", "timestamp": 100},
            {"event": "fix", "timestamp": 200},
        ]
        r = a.reconstruct_timeline(
            "crisis_1", events,
        )
        assert r["reconstructed"] is True
        assert r["duration_seconds"] == 100


class TestAssessImpact:
    """assess_impact testleri."""

    def test_high(self):
        a = PostCrisisAnalyzer()
        r = a.assess_impact(
            "crisis_1",
            financial_impact=50000,
            affected_users=5000,
        )
        assert r["assessed"] is True
        assert r["overall_impact"] in [
            "critical", "high",
        ]

    def test_low(self):
        a = PostCrisisAnalyzer()
        r = a.assess_impact(
            "crisis_1",
            financial_impact=0,
            affected_users=5,
        )
        assert r["overall_impact"] in [
            "low", "moderate",
        ]


class TestExtractLessons:
    """extract_lessons testleri."""

    def test_basic(self):
        a = PostCrisisAnalyzer()
        r = a.extract_lessons(
            "crisis_1",
            lessons=["Add monitoring"],
        )
        assert r["extracted"] is True
        assert a.lesson_count == 1


class TestRecommendImprovements:
    """recommend_improvements testleri."""

    def test_with_factors(self):
        a = PostCrisisAnalyzer()
        a.root_cause_analysis(
            "crisis_1",
            contributing_factors=[
                "Lack of monitoring",
            ],
        )
        r = a.recommend_improvements(
            "crisis_1",
        )
        assert r["recommended"] is True
        assert r["count"] >= 1

    def test_no_analysis(self):
        a = PostCrisisAnalyzer()
        r = a.recommend_improvements("xxx")
        assert r["count"] >= 1


# ── CrisisSimulationRunner ──────────────


class TestExecuteDrill:
    """execute_drill testleri."""

    def test_basic(self):
        s = CrisisSimulationRunner()
        r = s.execute_drill(
            "Annual Drill",
            participants=["fatih", "ali"],
        )
        assert r["executed"] is True
        assert r["participant_count"] == 2
        assert s.drill_count == 1


class TestTestScenario:
    """test_scenario testleri."""

    def test_basic(self):
        s = CrisisSimulationRunner()
        r = s.test_scenario(
            "DB Failure",
            crisis_type="outage",
        )
        assert r["tested"] is True
        assert r["passed"] is True


class TestMeasureResponseTime:
    """measure_response_time testleri."""

    def test_within_target(self):
        s = CrisisSimulationRunner()
        drill = s.execute_drill("Test")
        r = s.measure_response_time(
            drill["simulation_id"],
            "fatih",
            response_seconds=120,
        )
        assert r["within_target"] is True

    def test_not_found(self):
        s = CrisisSimulationRunner()
        r = s.measure_response_time(
            "xxx", "fatih",
        )
        assert r["found"] is False


class TestIdentifyGaps:
    """identify_gaps testleri."""

    def test_slow_response(self):
        s = CrisisSimulationRunner()
        drill = s.execute_drill("Test")
        s.measure_response_time(
            drill["simulation_id"],
            "slow_person",
            response_seconds=600,
        )
        r = s.identify_gaps(
            drill["simulation_id"],
        )
        assert r["identified"] is True
        assert r["gap_count"] >= 1


class TestGenerateTraining:
    """generate_training testleri."""

    def test_basic(self):
        s = CrisisSimulationRunner()
        r = s.generate_training(
            "slow_response",
        )
        assert r["generated"] is True
        assert "Training" in r["module"]


# ── CrisisRecoveryTracker ───────────────


class TestTrackProgress:
    """track_progress testleri."""

    def test_basic(self):
        t = CrisisRecoveryTracker()
        r = t.track_progress(
            "crisis_1",
            phase="containment",
            progress_pct=25.0,
        )
        assert r["tracked"] is True
        assert t.recovery_count == 1

    def test_update(self):
        t = CrisisRecoveryTracker()
        t.track_progress(
            "crisis_1", progress_pct=25.0,
        )
        r = t.track_progress(
            "crisis_1", progress_pct=75.0,
        )
        assert r["progress_pct"] == 75.0


class TestAddMilestone:
    """add_milestone testleri."""

    def test_basic(self):
        t = CrisisRecoveryTracker()
        r = t.add_milestone(
            "crisis_1",
            "Service restored",
            target_hours=4,
        )
        assert r["added"] is True


class TestCompleteMilestone:
    """complete_milestone testleri."""

    def test_basic(self):
        t = CrisisRecoveryTracker()
        t.add_milestone(
            "crisis_1", "Restored",
        )
        r = t.complete_milestone(
            "crisis_1", "Restored",
        )
        assert r["completed"] is True
        assert t.milestone_count == 1

    def test_not_found(self):
        t = CrisisRecoveryTracker()
        r = t.complete_milestone(
            "crisis_1", "xxx",
        )
        assert r["found"] is False


class TestMonitorResources:
    """monitor_resources testleri."""

    def test_all_available(self):
        t = CrisisRecoveryTracker()
        t.track_progress("crisis_1")
        r = t.monitor_resources(
            "crisis_1",
            resources={"engineers": 5},
        )
        assert r["all_available"] is True

    def test_depleted(self):
        t = CrisisRecoveryTracker()
        t.track_progress("crisis_1")
        r = t.monitor_resources(
            "crisis_1",
            resources={"budget": 0},
        )
        assert r["all_available"] is False


class TestReportStatus:
    """report_status testleri."""

    def test_basic(self):
        t = CrisisRecoveryTracker()
        t.track_progress(
            "crisis_1", progress_pct=50.0,
        )
        r = t.report_status("crisis_1")
        assert r["reported"] is True
        assert r["progress_pct"] == 50.0

    def test_not_found(self):
        t = CrisisRecoveryTracker()
        r = t.report_status("xxx")
        assert r["found"] is False


class TestVerifyCompletion:
    """verify_completion testleri."""

    def test_complete(self):
        t = CrisisRecoveryTracker()
        t.track_progress(
            "crisis_1", progress_pct=100.0,
        )
        t.add_milestone(
            "crisis_1", "Done",
        )
        t.complete_milestone(
            "crisis_1", "Done",
        )
        r = t.verify_completion("crisis_1")
        assert r["is_complete"] is True

    def test_incomplete(self):
        t = CrisisRecoveryTracker()
        t.track_progress(
            "crisis_1", progress_pct=50.0,
        )
        r = t.verify_completion("crisis_1")
        assert r["is_complete"] is False


# ── CrisisMgrOrchestrator ──────────────


class TestHandleCrisis:
    """handle_crisis testleri."""

    def test_anomaly(self):
        o = CrisisMgrOrchestrator()
        r = o.handle_crisis(
            "crisis_1",
            metric_name="error_rate",
            current_value=10.0,
            baseline=2.0,
            std_dev=1.0,
        )
        assert r["pipeline_complete"] is True
        assert r["is_anomaly"] is True
        assert r["notified"] is True
        assert r["recovery_started"] is True
        assert o.pipeline_count == 1

    def test_normal(self):
        o = CrisisMgrOrchestrator()
        r = o.handle_crisis(
            "crisis_2",
            current_value=2.0,
            baseline=2.0,
            std_dev=1.0,
        )
        assert r["is_anomaly"] is False


class TestPostCrisisReview:
    """post_crisis_review testleri."""

    def test_basic(self):
        o = CrisisMgrOrchestrator()
        r = o.post_crisis_review(
            "crisis_1",
            symptoms=["high latency"],
            factors=["DB overload"],
            lessons=["Add redundancy"],
        )
        assert r["reviewed"] is True
        assert r["root_cause"] == "DB overload"
        assert r["lessons_count"] == 1


class TestGetCrisisAnalytics:
    """get_analytics testleri."""

    def test_basic(self):
        o = CrisisMgrOrchestrator()
        o.handle_crisis(
            "crisis_1",
            current_value=10.0,
            baseline=2.0,
            std_dev=1.0,
        )
        r = o.get_analytics()
        assert r["pipelines_run"] == 1
        assert r["crises_managed"] == 1
        assert r["notifications_sent"] >= 1


# ── Models ──────────────────────────────


class TestCrisisModels:
    """Model testleri."""

    def test_crisis_level(self):
        assert CrisisLevel.LOW == "low"
        assert CrisisLevel.CRITICAL == "critical"

    def test_crisis_status(self):
        assert CrisisStatus.DETECTED == "detected"
        assert CrisisStatus.ACTIVE == "active"

    def test_escalation_tier(self):
        assert EscalationTier.TIER1 == "tier1"
        assert EscalationTier.EXECUTIVE == "executive"

    def test_notification_channel(self):
        assert NotificationChannel.TELEGRAM == "telegram"
        assert NotificationChannel.EMAIL == "email"

    def test_recovery_phase(self):
        assert RecoveryPhase.CONTAINMENT == "containment"
        assert RecoveryPhase.VERIFICATION == "verification"

    def test_simulation_type(self):
        assert SimulationType.DRILL == "drill"
        assert SimulationType.FULL_SCALE == "full_scale"

    def test_crisis_record(self):
        r = CrisisRecord(title="Outage")
        assert r.title == "Outage"
        assert r.crisis_id

    def test_escalation_record(self):
        r = EscalationRecord(tier="tier2")
        assert r.tier == "tier2"

    def test_action_plan_record(self):
        r = ActionPlanRecord(task_count=5)
        assert r.task_count == 5

    def test_recovery_record(self):
        r = RecoveryRecord(
            phase="mitigation",
        )
        assert r.phase == "mitigation"
