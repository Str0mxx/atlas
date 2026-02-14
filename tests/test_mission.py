"""ATLAS Mission Control testleri."""

import pytest

from app.models.mission import (
    AlertSeverity,
    ContingencyPlan,
    ContingencyType,
    MilestoneDefinition,
    MilestoneState,
    MissionAlert,
    MissionDefinition,
    MissionReport,
    MissionSnapshot,
    MissionState,
    PhaseDefinition,
    PhaseState,
    ReportType,
    ResourceAssignment,
)
from app.core.mission.mission_definer import MissionDefiner
from app.core.mission.mission_planner import MissionPlanner
from app.core.mission.phase_controller import PhaseController
from app.core.mission.resource_commander import ResourceCommander
from app.core.mission.progress_tracker import ProgressTracker
from app.core.mission.situation_room import SituationRoom
from app.core.mission.contingency_manager import ContingencyManager
from app.core.mission.mission_reporter import MissionReporter
from app.core.mission.mission_control import MissionControl


# ============================================================
# Model Testleri
# ============================================================

class TestMissionModels:
    """Model testleri."""

    def test_mission_state_enum(self):
        assert MissionState.DRAFT == "draft"
        assert MissionState.ACTIVE == "active"
        assert MissionState.COMPLETED == "completed"
        assert MissionState.ABORTED == "aborted"

    def test_phase_state_enum(self):
        assert PhaseState.PENDING == "pending"
        assert PhaseState.ACTIVE == "active"
        assert PhaseState.PASSED == "passed"
        assert PhaseState.ROLLED_BACK == "rolled_back"

    def test_milestone_state_enum(self):
        assert MilestoneState.PENDING == "pending"
        assert MilestoneState.COMPLETED == "completed"
        assert MilestoneState.DEFERRED == "deferred"

    def test_alert_severity_enum(self):
        assert AlertSeverity.INFO == "info"
        assert AlertSeverity.CRITICAL == "critical"
        assert AlertSeverity.EMERGENCY == "emergency"

    def test_contingency_type_enum(self):
        assert ContingencyType.PLAN_B == "plan_b"
        assert ContingencyType.ABORT == "abort"
        assert ContingencyType.DEGRADATION == "degradation"

    def test_report_type_enum(self):
        assert ReportType.STATUS == "status"
        assert ReportType.EXECUTIVE == "executive"
        assert ReportType.POST_MISSION == "post_mission"

    def test_mission_definition_defaults(self):
        m = MissionDefinition()
        assert len(m.mission_id) == 8
        assert m.state == MissionState.DRAFT
        assert m.priority == 5
        assert m.budget == 0.0

    def test_mission_definition_fields(self):
        m = MissionDefinition(
            name="Test", goal="Hedef", priority=8, budget=1000.0,
        )
        assert m.name == "Test"
        assert m.goal == "Hedef"
        assert m.priority == 8
        assert m.budget == 1000.0

    def test_phase_definition_defaults(self):
        p = PhaseDefinition()
        assert p.state == PhaseState.PENDING
        assert p.parallel is False
        assert p.progress == 0.0

    def test_milestone_definition(self):
        m = MilestoneDefinition(name="MS-1")
        assert m.name == "MS-1"
        assert m.state == MilestoneState.PENDING

    def test_resource_assignment(self):
        r = ResourceAssignment(resource_id="agent-1", resource_type="agent")
        assert r.resource_id == "agent-1"
        assert r.utilization == 0.0

    def test_mission_alert(self):
        a = MissionAlert(message="Test", severity=AlertSeverity.WARNING)
        assert a.message == "Test"
        assert a.acknowledged is False

    def test_contingency_plan(self):
        c = ContingencyPlan(
            contingency_type=ContingencyType.PLAN_B,
            actions=["A", "B"],
        )
        assert c.activated is False
        assert len(c.actions) == 2

    def test_mission_report(self):
        r = MissionReport(report_type=ReportType.STATUS, title="Test")
        assert r.title == "Test"

    def test_mission_snapshot(self):
        s = MissionSnapshot(total_missions=3, active_missions=1)
        assert s.total_missions == 3
        assert s.health_score == 1.0


# ============================================================
# MissionDefiner Testleri
# ============================================================

class TestMissionDefiner:
    """Gorev tanimlayici testleri."""

    def setup_method(self):
        self.definer = MissionDefiner()

    def test_define_mission(self):
        m = self.definer.define_mission("Test", "Hedef")
        assert m.name == "Test"
        assert m.goal == "Hedef"
        assert m.state == MissionState.DRAFT

    def test_define_with_params(self):
        m = self.definer.define_mission(
            "Test", "Hedef", priority=9, budget=5000.0,
            timeline_hours=24.0, tags=["urgent"],
        )
        assert m.priority == 9
        assert m.budget == 5000.0
        assert m.timeline_hours == 24.0
        assert "urgent" in m.tags

    def test_priority_clamping(self):
        m = self.definer.define_mission("T", "G", priority=15)
        assert m.priority == 10

        m2 = self.definer.define_mission("T", "G", priority=-5)
        assert m2.priority == 1

    def test_set_success_criteria(self):
        m = self.definer.define_mission("T", "G")
        assert self.definer.set_success_criteria(
            m.mission_id, ["kriter1", "kriter2"],
        )
        assert len(m.success_criteria) == 2

    def test_set_constraints(self):
        m = self.definer.define_mission("T", "G")
        assert self.definer.set_constraints(m.mission_id, ["k1"])
        assert len(m.constraints) == 1

    def test_set_timeline(self):
        m = self.definer.define_mission("T", "G")
        assert self.definer.set_timeline(m.mission_id, 48.0)
        assert m.timeline_hours == 48.0

    def test_set_timeline_invalid(self):
        m = self.definer.define_mission("T", "G")
        assert not self.definer.set_timeline(m.mission_id, -1)
        assert not self.definer.set_timeline("nonexistent", 10)

    def test_set_budget(self):
        m = self.definer.define_mission("T", "G")
        assert self.definer.set_budget(m.mission_id, 1000.0)
        assert m.budget == 1000.0

    def test_spend_budget(self):
        m = self.definer.define_mission("T", "G", budget=100.0)
        assert self.definer.spend_budget(m.mission_id, 50.0)
        assert m.budget_used == 50.0

    def test_spend_budget_over_limit(self):
        m = self.definer.define_mission("T", "G", budget=100.0)
        assert not self.definer.spend_budget(m.mission_id, 150.0)

    def test_register_template(self):
        self.definer.register_template("web_project", "Web sitesi", 7, 40.0)
        m = self.definer.define_from_template("web_project", "MyWeb")
        assert m is not None
        assert m.name == "MyWeb"
        assert m.priority == 7

    def test_template_overrides(self):
        self.definer.register_template("base", "Temel", 5)
        m = self.definer.define_from_template(
            "base", "Custom", {"priority": 9},
        )
        assert m.priority == 9

    def test_template_not_found(self):
        result = self.definer.define_from_template("nonexistent", "T")
        assert result is None

    def test_activate_mission(self):
        m = self.definer.define_mission("T", "G")
        assert self.definer.activate_mission(m.mission_id)
        assert m.state == MissionState.PLANNING

    def test_get_budget_status(self):
        m = self.definer.define_mission("T", "G", budget=1000.0)
        self.definer.spend_budget(m.mission_id, 250.0)
        status = self.definer.get_budget_status(m.mission_id)
        assert status["budget"] == 1000.0
        assert status["used"] == 250.0
        assert status["remaining"] == 750.0
        assert status["usage_percent"] == 25.0

    def test_total_missions(self):
        self.definer.define_mission("A", "G1")
        self.definer.define_mission("B", "G2")
        assert self.definer.total_missions == 2


# ============================================================
# MissionPlanner Testleri
# ============================================================

class TestMissionPlanner:
    """Gorev planlayici testleri."""

    def setup_method(self):
        self.planner = MissionPlanner()

    def test_create_phase(self):
        p = self.planner.create_phase("m1", "Design", order=0)
        assert p.name == "Design"
        assert p.mission_id == "m1"
        assert p.state == PhaseState.PENDING

    def test_create_phase_with_deps(self):
        p1 = self.planner.create_phase("m1", "Design", order=0)
        p2 = self.planner.create_phase(
            "m1", "Build", order=1,
            dependencies=[p1.phase_id],
        )
        assert p1.phase_id in p2.dependencies

    def test_get_phases_ordered(self):
        self.planner.create_phase("m1", "C", order=2)
        self.planner.create_phase("m1", "A", order=0)
        self.planner.create_phase("m1", "B", order=1)
        phases = self.planner.get_phases("m1")
        assert [p.name for p in phases] == ["A", "B", "C"]

    def test_create_milestone(self):
        p = self.planner.create_phase("m1", "Design")
        ms = self.planner.create_milestone("m1", p.phase_id, "MVP")
        assert ms.name == "MVP"
        assert ms.phase_id == p.phase_id

    def test_get_milestones(self):
        p = self.planner.create_phase("m1", "Design")
        self.planner.create_milestone("m1", p.phase_id, "MS1")
        self.planner.create_milestone("m1", p.phase_id, "MS2")
        ms = self.planner.get_milestones("m1")
        assert len(ms) == 2

    def test_get_milestones_by_phase(self):
        p1 = self.planner.create_phase("m1", "Design")
        p2 = self.planner.create_phase("m1", "Build")
        self.planner.create_milestone("m1", p1.phase_id, "MS1")
        self.planner.create_milestone("m1", p2.phase_id, "MS2")
        ms = self.planner.get_milestones("m1", p1.phase_id)
        assert len(ms) == 1

    def test_critical_path_simple(self):
        p1 = self.planner.create_phase("m1", "A", order=0)
        p2 = self.planner.create_phase(
            "m1", "B", order=1, dependencies=[p1.phase_id],
        )
        p3 = self.planner.create_phase(
            "m1", "C", order=2, dependencies=[p2.phase_id],
        )
        path = self.planner.get_critical_path("m1")
        assert len(path) == 3
        assert path[-1] == p3.phase_id

    def test_critical_path_empty(self):
        assert self.planner.get_critical_path("nonexistent") == []

    def test_dependency_map(self):
        p1 = self.planner.create_phase("m1", "A", order=0)
        p2 = self.planner.create_phase(
            "m1", "B", order=1, dependencies=[p1.phase_id],
        )
        dep_map = self.planner.get_dependency_map("m1")
        assert p1.phase_id in dep_map
        assert p1.phase_id in dep_map[p2.phase_id]

    def test_identify_risks_no_criteria(self):
        self.planner.create_phase("m1", "Design", order=0)
        risks = self.planner.identify_risks("m1")
        types = [r["type"] for r in risks]
        assert "no_gate_criteria" in types

    def test_identify_risks_no_agents(self):
        self.planner.create_phase("m1", "Build", order=0)
        risks = self.planner.identify_risks("m1")
        types = [r["type"] for r in risks]
        assert "no_agents_assigned" in types

    def test_complete_milestone(self):
        p = self.planner.create_phase("m1", "Design")
        ms = self.planner.create_milestone("m1", p.phase_id, "MS1")
        assert self.planner.complete_milestone(ms.milestone_id)
        assert ms.state == MilestoneState.COMPLETED

    def test_is_phase_ready_no_deps(self):
        p = self.planner.create_phase("m1", "A", order=0)
        assert self.planner.is_phase_ready(p.phase_id)

    def test_is_phase_ready_deps_not_met(self):
        p1 = self.planner.create_phase("m1", "A", order=0)
        p2 = self.planner.create_phase(
            "m1", "B", order=1, dependencies=[p1.phase_id],
        )
        assert not self.planner.is_phase_ready(p2.phase_id)

    def test_is_phase_ready_deps_met(self):
        p1 = self.planner.create_phase("m1", "A", order=0)
        p1.state = PhaseState.PASSED
        p2 = self.planner.create_phase(
            "m1", "B", order=1, dependencies=[p1.phase_id],
        )
        assert self.planner.is_phase_ready(p2.phase_id)


# ============================================================
# PhaseController Testleri
# ============================================================

class TestPhaseController:
    """Faz kontrolcusu testleri."""

    def setup_method(self):
        self.ctrl = PhaseController()

    def _make_phase(self, name="Test", mission_id="m1"):
        phase = PhaseDefinition(name=name, mission_id=mission_id)
        self.ctrl.register_phase(phase)
        return phase

    def test_register_and_get(self):
        p = self._make_phase()
        assert self.ctrl.get_phase(p.phase_id) is not None

    def test_ready_phase(self):
        p = self._make_phase()
        assert self.ctrl.ready_phase(p.phase_id)
        assert p.state == PhaseState.READY

    def test_start_phase(self):
        p = self._make_phase()
        self.ctrl.ready_phase(p.phase_id)
        assert self.ctrl.start_phase(p.phase_id)
        assert p.state == PhaseState.ACTIVE
        assert p.started_at is not None

    def test_submit_for_review(self):
        p = self._make_phase()
        self.ctrl.ready_phase(p.phase_id)
        self.ctrl.start_phase(p.phase_id)
        assert self.ctrl.submit_for_review(p.phase_id)
        assert p.state == PhaseState.REVIEW

    def test_gate_review_pass(self):
        p = self._make_phase()
        self.ctrl.ready_phase(p.phase_id)
        self.ctrl.start_phase(p.phase_id)
        self.ctrl.submit_for_review(p.phase_id)
        result = self.ctrl.gate_review(
            p.phase_id, {"k1": True, "k2": True},
        )
        assert result["passed"]
        assert p.state == PhaseState.PASSED

    def test_gate_review_fail(self):
        p = self._make_phase()
        self.ctrl.ready_phase(p.phase_id)
        self.ctrl.start_phase(p.phase_id)
        self.ctrl.submit_for_review(p.phase_id)
        result = self.ctrl.gate_review(
            p.phase_id, {"k1": True, "k2": False},
        )
        assert not result["passed"]
        assert p.state == PhaseState.ACTIVE

    def test_go_no_go(self):
        p = self._make_phase()
        self.ctrl.ready_phase(p.phase_id)
        self.ctrl.start_phase(p.phase_id)
        self.ctrl.submit_for_review(p.phase_id)
        self.ctrl.gate_review(p.phase_id, {"k1": True})
        assert self.ctrl.go_no_go(p.phase_id)

    def test_rollback_phase(self):
        p = self._make_phase()
        self.ctrl.ready_phase(p.phase_id)
        self.ctrl.start_phase(p.phase_id)
        # Active -> Failed
        self.ctrl.transition(p.phase_id, PhaseState.FAILED)
        assert self.ctrl.rollback_phase(p.phase_id)
        assert p.state == PhaseState.ROLLED_BACK
        assert p.progress == 0.0

    def test_skip_phase(self):
        p = self._make_phase()
        assert self.ctrl.skip_phase(p.phase_id)
        assert p.state == PhaseState.SKIPPED

    def test_update_progress(self):
        p = self._make_phase()
        self.ctrl.ready_phase(p.phase_id)
        self.ctrl.start_phase(p.phase_id)
        assert self.ctrl.update_progress(p.phase_id, 0.7)
        assert p.progress == 0.7

    def test_invalid_transition(self):
        p = self._make_phase()
        assert not self.ctrl.transition(p.phase_id, PhaseState.PASSED)

    def test_parallel_phases(self):
        p1 = PhaseDefinition(name="P1", mission_id="m1", parallel=True)
        p2 = PhaseDefinition(name="P2", mission_id="m1", parallel=False)
        self.ctrl.register_phase(p1)
        self.ctrl.register_phase(p2)
        parallel = self.ctrl.get_parallel_phases("m1")
        assert len(parallel) == 1

    def test_active_phases(self):
        p = self._make_phase()
        self.ctrl.ready_phase(p.phase_id)
        self.ctrl.start_phase(p.phase_id)
        active = self.ctrl.get_active_phases("m1")
        assert len(active) == 1

    def test_passed_count(self):
        p = self._make_phase()
        self.ctrl.ready_phase(p.phase_id)
        self.ctrl.start_phase(p.phase_id)
        self.ctrl.submit_for_review(p.phase_id)
        self.ctrl.gate_review(p.phase_id, {"k1": True})
        assert self.ctrl.passed_count == 1


# ============================================================
# ResourceCommander Testleri
# ============================================================

class TestResourceCommander:
    """Kaynak komutani testleri."""

    def setup_method(self):
        self.cmd = ResourceCommander()
        self.cmd.register_agent("a1")
        self.cmd.register_agent("a2")
        self.cmd.register_tool("t1")

    def test_assign_agent(self):
        a = self.cmd.assign_agent("m1", "a1")
        assert a is not None
        assert a.resource_type == "agent"

    def test_assign_agent_not_registered(self):
        assert self.cmd.assign_agent("m1", "a99") is None

    def test_assign_agent_already_assigned(self):
        self.cmd.assign_agent("m1", "a1")
        assert self.cmd.assign_agent("m2", "a1") is None

    def test_assign_tool(self):
        a = self.cmd.assign_tool("m1", "t1")
        assert a is not None
        assert a.resource_type == "tool"

    def test_release_agent(self):
        self.cmd.assign_agent("m1", "a1")
        assert self.cmd.release_agent("a1")
        # Tekrar atanabilir
        assert self.cmd.assign_agent("m2", "a1") is not None

    def test_release_tool(self):
        self.cmd.assign_tool("m1", "t1")
        assert self.cmd.release_tool("t1")

    def test_reallocate_agent(self):
        self.cmd.assign_agent("m1", "a1")
        assert self.cmd.reallocate_agent("a1", "m2")

    def test_budget_tracking(self):
        self.cmd.set_budget("m1", 1000.0)
        assert self.cmd.spend("m1", 300.0)
        status = self.cmd.get_budget_status("m1")
        assert status["spent"] == 300.0
        assert status["remaining"] == 700.0

    def test_budget_exceeded(self):
        self.cmd.set_budget("m1", 100.0)
        assert not self.cmd.spend("m1", 150.0)

    def test_detect_conflicts(self):
        self.cmd.set_budget("m1", 100.0)
        self.cmd._spent["m1"] = 150.0  # Simulate overspend
        conflicts = self.cmd.detect_conflicts()
        assert len(conflicts) == 1
        assert conflicts[0]["type"] == "budget_exceeded"

    def test_get_mission_resources(self):
        self.cmd.assign_agent("m1", "a1")
        self.cmd.assign_tool("m1", "t1")
        res = self.cmd.get_mission_resources("m1")
        assert "a1" in res["agents"]
        assert "t1" in res["tools"]

    def test_get_free_agents(self):
        self.cmd.assign_agent("m1", "a1")
        free = self.cmd.get_free_agents()
        assert "a2" in free
        assert "a1" not in free

    def test_properties(self):
        assert self.cmd.total_agents == 2
        self.cmd.assign_agent("m1", "a1")
        assert self.cmd.assigned_agent_count == 1


# ============================================================
# ProgressTracker Testleri
# ============================================================

class TestProgressTracker:
    """Ilerleme takipci testleri."""

    def setup_method(self):
        self.tracker = ProgressTracker()
        self.tracker.init_mission("m1", ["p1", "p2", "p3"])

    def test_init_mission(self):
        assert self.tracker.get_progress("m1") == 0.0
        assert self.tracker.tracked_missions == 1

    def test_update_phase_progress(self):
        assert self.tracker.update_phase_progress("m1", "p1", 0.5)
        phases = self.tracker.get_phase_progress("m1")
        assert phases["p1"] == 0.5

    def test_mission_progress_calculation(self):
        self.tracker.update_phase_progress("m1", "p1", 1.0)
        self.tracker.update_phase_progress("m1", "p2", 0.5)
        # (1.0 + 0.5 + 0.0) / 3 = 0.5
        progress = self.tracker.get_progress("m1")
        assert progress == 0.5

    def test_add_and_complete_milestone(self):
        self.tracker.add_milestone("m1", "ms1")
        assert self.tracker.complete_milestone("m1", "ms1")
        status = self.tracker.get_milestone_status("m1")
        assert status["completed"] == 1
        assert status["total"] == 1

    def test_add_blocker(self):
        bid = self.tracker.add_blocker("m1", "Bug found", "p1")
        assert bid.startswith("blk-")
        blockers = self.tracker.get_blockers("m1")
        assert len(blockers) == 1

    def test_resolve_blocker(self):
        bid = self.tracker.add_blocker("m1", "Bug")
        assert self.tracker.resolve_blocker("m1", bid)
        active = self.tracker.get_blockers("m1", active_only=True)
        assert len(active) == 0

    def test_get_all_blockers(self):
        self.tracker.add_blocker("m1", "B1")
        bid = self.tracker.add_blocker("m1", "B2")
        self.tracker.resolve_blocker("m1", bid)
        all_blockers = self.tracker.get_blockers("m1", active_only=False)
        assert len(all_blockers) == 2

    def test_burndown(self):
        self.tracker.update_phase_progress("m1", "p1", 0.5)
        self.tracker.update_phase_progress("m1", "p1", 1.0)
        burndown = self.tracker.get_burndown("m1")
        assert len(burndown) == 2

    def test_eta_calculation(self):
        # Baslangicta 0 ilerleme -> 0 eta
        eta = self.tracker.calculate_eta("m1")
        assert eta == 0.0

    def test_get_status(self):
        status = self.tracker.get_status("m1")
        assert "progress" in status
        assert "phases" in status
        assert "milestones" in status

    def test_update_invalid_phase(self):
        assert not self.tracker.update_phase_progress("m1", "invalid", 0.5)

    def test_complete_invalid_milestone(self):
        assert not self.tracker.complete_milestone("m1", "invalid")


# ============================================================
# SituationRoom Testleri
# ============================================================

class TestSituationRoom:
    """Durum odasi testleri."""

    def setup_method(self):
        self.room = SituationRoom()

    def test_raise_alert(self):
        alert = self.room.raise_alert("m1", "Test alert")
        assert alert.message == "Test alert"
        assert alert.severity == AlertSeverity.INFO

    def test_raise_critical_alert(self):
        self.room.raise_alert(
            "m1", "Critical", AlertSeverity.CRITICAL,
        )
        assert self.room.critical_alert_count == 1

    def test_acknowledge_alert(self):
        alert = self.room.raise_alert("m1", "Test")
        assert self.room.acknowledge_alert(alert.alert_id)
        assert self.room.active_alert_count == 0

    def test_get_alerts_filtered(self):
        self.room.raise_alert("m1", "A1", AlertSeverity.INFO)
        self.room.raise_alert("m1", "A2", AlertSeverity.CRITICAL)
        self.room.raise_alert("m2", "A3", AlertSeverity.WARNING)

        m1_alerts = self.room.get_alerts(mission_id="m1")
        assert len(m1_alerts) == 2

        critical = self.room.get_alerts(severity=AlertSeverity.CRITICAL)
        assert len(critical) == 1

    def test_update_dashboard(self):
        self.room.update_dashboard("m1", {"progress": 0.5})
        self.room.update_dashboard("m1", {"alerts": 2})
        dashboard = self.room.get_dashboard("m1")
        assert dashboard["progress"] == 0.5
        assert dashboard["alerts"] == 2
        assert "last_updated" in dashboard

    def test_record_decision(self):
        d = self.room.record_decision(
            "m1", "Devam et", "Risk dusuk", "fatih",
        )
        assert d["decision"] == "Devam et"
        decisions = self.room.get_decisions("m1")
        assert len(decisions) == 1

    def test_what_if_analysis(self):
        self.room.update_dashboard("m1", {"progress": 0.5})
        result = self.room.what_if_analysis(
            "m1", "Agent kaybedersek",
            {"progress_change": -0.1, "risk_level": "high", "delay_hours": 5},
        )
        assert result["projected_progress"] == 0.4
        assert result["recommendation"] == "review"

    def test_stakeholder_update(self):
        update = self.room.send_stakeholder_update(
            "m1", "50% tamamlandi", ["fatih"],
        )
        assert update["summary"] == "50% tamamlandi"
        updates = self.room.get_stakeholder_updates("m1")
        assert len(updates) == 1

    def test_total_alerts(self):
        self.room.raise_alert("m1", "A")
        self.room.raise_alert("m1", "B")
        assert self.room.total_alerts == 2


# ============================================================
# ContingencyManager Testleri
# ============================================================

class TestContingencyManager:
    """Olasilik yoneticisi testleri."""

    def setup_method(self):
        self.mgr = ContingencyManager()

    def test_create_plan(self):
        plan = self.mgr.create_plan(
            "m1", ContingencyType.PLAN_B,
            "Progress < 0.3", ["reassess", "reallocate"],
        )
        assert plan.contingency_type == ContingencyType.PLAN_B
        assert not plan.activated

    def test_activate_plan(self):
        plan = self.mgr.create_plan(
            "m1", ContingencyType.PLAN_B, "cond", ["a"],
        )
        assert self.mgr.activate_plan(plan.plan_id)
        assert plan.activated
        assert plan.activated_at is not None

    def test_activate_already_active(self):
        plan = self.mgr.create_plan(
            "m1", ContingencyType.PLAN_B, "c", ["a"],
        )
        self.mgr.activate_plan(plan.plan_id)
        assert not self.mgr.activate_plan(plan.plan_id)

    def test_deactivate_plan(self):
        plan = self.mgr.create_plan(
            "m1", ContingencyType.RECOVERY, "c", ["a"],
        )
        self.mgr.activate_plan(plan.plan_id)
        assert self.mgr.deactivate_plan(plan.plan_id)
        assert not plan.activated

    def test_get_plans_filtered(self):
        self.mgr.create_plan("m1", ContingencyType.PLAN_B, "c", ["a"])
        self.mgr.create_plan("m1", ContingencyType.ABORT, "c", ["a"])
        plans = self.mgr.get_plans("m1", ContingencyType.PLAN_B)
        assert len(plans) == 1

    def test_activate_plan_b(self):
        self.mgr.create_plan("m1", ContingencyType.PLAN_B, "c", ["a"])
        plan = self.mgr.activate_plan_b("m1")
        assert plan is not None
        assert plan.activated

    def test_initiate_recovery(self):
        self.mgr.create_plan(
            "m1", ContingencyType.RECOVERY, "c", ["restore"],
        )
        result = self.mgr.initiate_recovery(
            "m1", "DB failure", ["restore_backup", "verify"],
        )
        assert result["plan_activated"] != ""

    def test_abort_mission(self):
        self.mgr.create_plan(
            "m1", ContingencyType.ABORT, "c", ["cleanup"],
        )
        result = self.mgr.abort_mission("m1", "Budget exceeded", "fatih")
        assert result["reason"] == "Budget exceeded"
        assert len(self.mgr.get_abort_log()) == 1

    def test_graceful_degradation(self):
        self.mgr.create_plan(
            "m1", ContingencyType.DEGRADATION, "c", ["reduce"],
        )
        result = self.mgr.graceful_degradation(
            "m1", ["voice_support", "real_time"],
        )
        assert len(result["activated_plans"]) == 1

    def test_record_lesson(self):
        self.mgr.record_lesson("m1", "Always backup", "planning")
        lessons = self.mgr.get_lessons("m1")
        assert len(lessons) == 1
        assert lessons[0]["lesson"] == "Always backup"

    def test_get_lessons_filtered(self):
        self.mgr.record_lesson("m1", "L1", "planning")
        self.mgr.record_lesson("m1", "L2", "execution")
        assert len(self.mgr.get_lessons("m1", "planning")) == 1

    def test_properties(self):
        self.mgr.create_plan("m1", ContingencyType.PLAN_B, "c", ["a"])
        assert self.mgr.total_plans == 1
        assert self.mgr.active_plan_count == 0


# ============================================================
# MissionReporter Testleri
# ============================================================

class TestMissionReporter:
    """Gorev raporlayici testleri."""

    def setup_method(self):
        self.reporter = MissionReporter()

    def test_status_report(self):
        r = self.reporter.generate_status_report(
            "m1", progress=0.5, active_phases=2, total_phases=4,
        )
        assert r.report_type == ReportType.STATUS
        assert r.content["progress"] == 0.5

    def test_executive_summary(self):
        r = self.reporter.generate_executive_summary(
            "m1", "Project X", 0.7,
            key_achievements=["MVP ready"],
            risks=["Budget low"],
        )
        assert r.report_type == ReportType.EXECUTIVE
        assert "MVP ready" in r.content["key_achievements"]

    def test_detailed_report(self):
        self.reporter.add_log("m1", "Step 1 done")
        r = self.reporter.generate_detailed_report(
            "m1", {"overview": "All good"},
        )
        assert r.report_type == ReportType.DETAILED
        assert r.content["log_count"] == 1

    def test_post_mission_report(self):
        r = self.reporter.generate_post_mission_report(
            "m1", outcome="completed", duration_hours=48.0,
            lessons_learned=["Plan better"],
            success_metrics={"quality": 0.9},
        )
        assert r.report_type == ReportType.POST_MISSION
        assert r.content["duration_hours"] == 48.0

    def test_add_and_get_logs(self):
        self.reporter.add_log("m1", "Log 1", "info")
        self.reporter.add_log("m1", "Log 2", "error")
        self.reporter.add_log("m1", "Log 3", "info")

        all_logs = self.reporter.get_logs("m1")
        assert len(all_logs) == 3

        errors = self.reporter.get_logs("m1", level="error")
        assert len(errors) == 1

    def test_get_logs_with_limit(self):
        for i in range(10):
            self.reporter.add_log("m1", f"Log {i}")
        logs = self.reporter.get_logs("m1", limit=3)
        assert len(logs) == 3

    def test_get_reports_filtered(self):
        self.reporter.generate_status_report("m1")
        self.reporter.generate_executive_summary("m1")
        status_reports = self.reporter.get_reports(
            "m1", ReportType.STATUS,
        )
        assert len(status_reports) == 1

    def test_get_success_metrics(self):
        self.reporter.generate_post_mission_report(
            "m1", success_metrics={"score": 95},
        )
        metrics = self.reporter.get_success_metrics("m1")
        assert metrics["score"] == 95

    def test_get_report_by_id(self):
        r = self.reporter.generate_status_report("m1")
        found = self.reporter.get_report(r.report_id)
        assert found is not None
        assert found.report_id == r.report_id

    def test_properties(self):
        self.reporter.generate_status_report("m1")
        self.reporter.add_log("m1", "test")
        assert self.reporter.total_reports == 1
        assert self.reporter.total_logs == 1


# ============================================================
# MissionControl Testleri
# ============================================================

class TestMissionControl:
    """Gorev kontrol merkezi testleri."""

    def setup_method(self):
        self.mc = MissionControl(
            max_concurrent=3,
            auto_abort_threshold=0.3,
        )

    def test_create_mission(self):
        result = self.mc.create_mission("Test", "Hedef")
        assert result["success"]
        assert result["state"] == "draft"

    def test_create_mission_max_concurrent(self):
        for i in range(3):
            r = self.mc.create_mission(f"M{i}", "G")
            mid = r["mission_id"]
            self.mc.plan_mission(mid, [{"name": "P"}])
            self.mc.start_mission(mid)

        # 4. gorev limiti asmali
        result = self.mc.create_mission("M4", "G")
        assert not result["success"]

    def test_plan_mission(self):
        r = self.mc.create_mission("Test", "Hedef")
        mid = r["mission_id"]
        plan = self.mc.plan_mission(mid, [
            {"name": "Design", "order": 0, "gate_criteria": ["k1"]},
            {"name": "Build", "order": 1},
        ])
        assert plan["success"]
        assert len(plan["phases"]) == 2

    def test_start_mission(self):
        r = self.mc.create_mission("Test", "Hedef")
        mid = r["mission_id"]
        self.mc.plan_mission(mid, [
            {"name": "Design", "order": 0},
        ])
        start = self.mc.start_mission(mid)
        assert start["success"]
        assert start["state"] == "active"
        assert len(start["started_phases"]) == 1

    def test_update_progress(self):
        r = self.mc.create_mission("Test", "Hedef")
        mid = r["mission_id"]
        plan = self.mc.plan_mission(mid, [{"name": "Design"}])
        self.mc.start_mission(mid)

        pid = plan["phases"][0]
        assert self.mc.update_progress(mid, pid, 0.5)

    def test_advance_phase(self):
        r = self.mc.create_mission("Test", "Hedef")
        mid = r["mission_id"]
        plan = self.mc.plan_mission(mid, [
            {"name": "Design", "gate_criteria": ["quality"]},
        ])
        self.mc.start_mission(mid)
        pid = plan["phases"][0]

        result = self.mc.advance_phase(
            mid, pid, {"quality": True},
        )
        assert result.get("passed")

    def test_handle_failure(self):
        r = self.mc.create_mission("Test", "Hedef")
        mid = r["mission_id"]
        result = self.mc.handle_failure(mid, description="Bug")
        assert result["success"]
        assert "health" in result

    def test_abort_mission(self):
        r = self.mc.create_mission("Test", "Hedef")
        mid = r["mission_id"]
        result = self.mc.abort_mission(mid, "No budget")
        assert result["success"]
        assert result["state"] == "aborted"

    def test_complete_mission(self):
        r = self.mc.create_mission("Test", "Hedef")
        mid = r["mission_id"]
        plan = self.mc.plan_mission(mid, [{"name": "P"}])
        self.mc.start_mission(mid)
        result = self.mc.complete_mission(mid)
        assert result["success"]
        assert result["state"] == "completed"

    def test_assign_resource(self):
        r = self.mc.create_mission("Test", "Hedef")
        mid = r["mission_id"]
        self.mc.resources.register_agent("a1")
        result = self.mc.assign_resource(mid, "a1", "agent")
        assert result["success"]

    def test_assign_resource_invalid_type(self):
        r = self.mc.create_mission("Test", "Hedef")
        mid = r["mission_id"]
        result = self.mc.assign_resource(mid, "x", "invalid")
        assert not result["success"]

    def test_get_mission_status(self):
        r = self.mc.create_mission("Test", "Hedef")
        mid = r["mission_id"]
        self.mc.plan_mission(mid, [{"name": "P"}])
        status = self.mc.get_mission_status(mid)
        assert status["name"] == "Test"
        assert "health" in status

    def test_get_snapshot(self):
        self.mc.create_mission("M1", "G1")
        snap = self.mc.get_snapshot()
        assert snap.total_missions == 1
        assert snap.health_score >= 0.0

    def test_escalate(self):
        r = self.mc.create_mission("Test", "Hedef")
        mid = r["mission_id"]
        result = self.mc.escalate(mid, "Need approval")
        assert result["success"]
        assert result["escalated_to"] == "human"

    def test_subsystem_properties(self):
        assert self.mc.definer is not None
        assert self.mc.planner is not None
        assert self.mc.phases is not None
        assert self.mc.resources is not None
        assert self.mc.progress is not None
        assert self.mc.situation is not None
        assert self.mc.contingency is not None
        assert self.mc.reporter is not None

    def test_resource_release_on_abort(self):
        r = self.mc.create_mission("Test", "Hedef")
        mid = r["mission_id"]
        self.mc.resources.register_agent("a1")
        self.mc.assign_resource(mid, "a1", "agent")
        self.mc.abort_mission(mid, "Cancel")
        free = self.mc.resources.get_free_agents()
        assert "a1" in free


# ============================================================
# Entegrasyon Testleri
# ============================================================

class TestMissionIntegration:
    """Entegrasyon testleri."""

    def test_full_mission_lifecycle(self):
        """Tam gorev yasam dongusu."""
        mc = MissionControl()

        # 1. Olustur
        result = mc.create_mission(
            "E-Commerce Launch", "Launch online store",
            priority=8, budget=5000.0,
        )
        assert result["success"]
        mid = result["mission_id"]

        # 2. Planla
        plan = mc.plan_mission(mid, [
            {"name": "Design", "order": 0, "gate_criteria": ["mockup"]},
            {"name": "Development", "order": 1, "gate_criteria": ["tests"]},
            {"name": "Launch", "order": 2, "gate_criteria": ["deploy"]},
        ])
        assert plan["success"]
        assert len(plan["phases"]) == 3

        # 3. Baslat
        start = mc.start_mission(mid)
        assert start["success"]

        # 4. Ilerleme guncelle
        pid = plan["phases"][0]
        mc.update_progress(mid, pid, 0.5)
        mc.update_progress(mid, pid, 1.0)

        # 5. Faz ilerlet
        result = mc.advance_phase(mid, pid, {"mockup": True})
        assert result.get("passed")

        # 6. Durum kontrol
        status = mc.get_mission_status(mid)
        assert status["state"] == "active"

        # 7. Tamamla
        complete = mc.complete_mission(mid)
        assert complete["success"]

    def test_mission_with_failure_recovery(self):
        """Hata kurtarma senaryosu."""
        mc = MissionControl()

        result = mc.create_mission("Test", "G")
        mid = result["mission_id"]

        # Olasilik plani ekle
        mc.contingency.create_plan(
            mid, ContingencyType.RECOVERY,
            "Phase fails", ["rollback", "retry"],
        )

        # Hata isle
        failure = mc.handle_failure(mid, description="Agent crash")
        assert failure["success"]
        assert not failure["auto_aborted"]

    def test_multi_mission_management(self):
        """Coklu gorev yonetimi."""
        mc = MissionControl(max_concurrent=5)

        missions = []
        for i in range(3):
            r = mc.create_mission(f"Mission-{i}", f"Goal-{i}")
            missions.append(r["mission_id"])

        snap = mc.get_snapshot()
        assert snap.total_missions == 3

    def test_mission_with_resources(self):
        """Kaynak yonetimi senaryosu."""
        mc = MissionControl()

        result = mc.create_mission("Test", "G", budget=1000.0)
        mid = result["mission_id"]

        mc.resources.register_agent("agent-1")
        mc.resources.register_agent("agent-2")
        mc.resources.register_tool("scraper")

        mc.assign_resource(mid, "agent-1", "agent")
        mc.assign_resource(mid, "scraper", "tool")

        resources = mc.resources.get_mission_resources(mid)
        assert len(resources["agents"]) == 1
        assert len(resources["tools"]) == 1

    def test_mission_reporting(self):
        """Raporlama senaryosu."""
        mc = MissionControl()

        result = mc.create_mission("Test", "G")
        mid = result["mission_id"]
        mc.plan_mission(mid, [{"name": "P1"}])
        mc.start_mission(mid)

        # Durum raporu
        report = mc.reporter.generate_status_report(mid, progress=0.5)
        assert report.report_type == ReportType.STATUS

        # Yonetici ozeti
        summary = mc.reporter.generate_executive_summary(
            mid, "Test Mission", 0.5,
        )
        assert summary.report_type == ReportType.EXECUTIVE

    def test_escalation_and_alerts(self):
        """Eskalasyon ve uyari senaryosu."""
        mc = MissionControl()

        result = mc.create_mission("Test", "G")
        mid = result["mission_id"]

        # Eskalasyon
        esc = mc.escalate(mid, "Critical decision needed")
        assert esc["success"]

        # Uyari kontrol
        alerts = mc.situation.get_alerts(mid)
        assert len(alerts) > 0
        assert alerts[0].severity == AlertSeverity.EMERGENCY
