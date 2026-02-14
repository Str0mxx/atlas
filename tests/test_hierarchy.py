"""ATLAS Hierarchical Agent Controller testleri.

AgentHierarchy, ClusterManager, DelegationEngine,
SupervisionController, ReportingSystem, CommandChain,
AutonomyController, ConflictArbiter ve HierarchyOrchestrator testleri.
"""

import pytest

from app.models.hierarchy import (
    AgentNode,
    AuthorityLevel,
    AutonomyLevel,
    ClusterInfo,
    ClusterType,
    CommandMessage,
    CommandType,
    ConflictRecord,
    ConflictType,
    DelegationRecord,
    DelegationStatus,
    HierarchyReport,
    HierarchySnapshot,
    ReportType,
    ResolutionStrategy,
    SupervisionEvent,
)

from app.core.hierarchy import (
    AgentHierarchy,
    AutonomyController,
    ClusterManager,
    CommandChain,
    ConflictArbiter,
    DelegationEngine,
    HierarchyOrchestrator,
    ReportingSystem,
    SupervisionController,
)


# ============================================================
# Yardimci fonksiyonlar
# ============================================================

def _build_simple_hierarchy():
    """Basit hiyerarsi olusturur (master -> 2 supervisor -> 2 worker)."""
    h = AgentHierarchy()
    master = h.add_agent("master", AuthorityLevel.MASTER)
    sup1 = h.add_agent(
        "sup1", AuthorityLevel.SUPERVISOR,
        parent_id=master.agent_id,
        capabilities=["analyze", "plan"],
    )
    sup2 = h.add_agent(
        "sup2", AuthorityLevel.SUPERVISOR,
        parent_id=master.agent_id,
        capabilities=["execute", "monitor"],
    )
    w1 = h.add_agent(
        "worker1", AuthorityLevel.WORKER,
        parent_id=sup1.agent_id,
        capabilities=["code", "test"],
    )
    w2 = h.add_agent(
        "worker2", AuthorityLevel.WORKER,
        parent_id=sup2.agent_id,
        capabilities=["deploy", "monitor"],
    )
    return h, master, sup1, sup2, w1, w2


# ============================================================
# Model Testleri
# ============================================================

class TestModels:
    """Model testleri."""

    def test_authority_level_values(self):
        assert AuthorityLevel.MASTER == "master"
        assert AuthorityLevel.WORKER == "worker"
        assert AuthorityLevel.OBSERVER == "observer"

    def test_cluster_type_values(self):
        assert ClusterType.BUSINESS == "business"
        assert ClusterType.TECHNICAL == "technical"
        assert ClusterType.COMMUNICATION == "communication"

    def test_delegation_status_values(self):
        assert DelegationStatus.PENDING == "pending"
        assert DelegationStatus.COMPLETED == "completed"
        assert DelegationStatus.ESCALATED == "escalated"

    def test_autonomy_level_values(self):
        assert AutonomyLevel.FULL == "full"
        assert AutonomyLevel.NONE == "none"

    def test_command_type_values(self):
        assert CommandType.EMERGENCY == "emergency"
        assert CommandType.BROADCAST == "broadcast"

    def test_conflict_type_values(self):
        assert ConflictType.RESOURCE == "resource"
        assert ConflictType.DEADLOCK == "deadlock"

    def test_resolution_strategy_values(self):
        assert ResolutionStrategy.PRIORITY_BASED == "priority_based"
        assert ResolutionStrategy.CONSENSUS == "consensus"

    def test_report_type_values(self):
        assert ReportType.DAILY == "daily"
        assert ReportType.CUSTOM == "custom"

    def test_agent_node_defaults(self):
        node = AgentNode()
        assert node.agent_id
        assert node.authority == AuthorityLevel.WORKER
        assert node.active

    def test_agent_node_custom(self):
        node = AgentNode(
            name="test", authority=AuthorityLevel.MASTER,
            capabilities=["code"],
        )
        assert node.name == "test"
        assert "code" in node.capabilities

    def test_cluster_info_defaults(self):
        info = ClusterInfo()
        assert info.cluster_id
        assert info.max_members == 10
        assert info.active

    def test_delegation_record(self):
        rec = DelegationRecord(
            task_id="t1", from_agent="a1", to_agent="a2",
            priority=8,
        )
        assert rec.delegation_id
        assert rec.priority == 8
        assert rec.status == DelegationStatus.PENDING

    def test_supervision_event(self):
        ev = SupervisionEvent(
            agent_id="a1", event_type="error",
            severity="critical", requires_intervention=True,
        )
        assert ev.requires_intervention

    def test_command_message(self):
        cmd = CommandMessage(
            command_type=CommandType.EMERGENCY,
            from_agent="master", to_agents=["w1", "w2"],
            content="Stop", priority=10,
        )
        assert cmd.priority == 10

    def test_conflict_record(self):
        rec = ConflictRecord(
            conflict_type=ConflictType.RESOURCE,
            agents_involved=["a1", "a2"],
            resource="gpu",
        )
        assert not rec.resolved

    def test_hierarchy_report(self):
        rep = HierarchyReport(
            report_type=ReportType.DAILY,
            title="Gunluk",
        )
        assert rep.report_id
        assert rep.timestamp

    def test_hierarchy_snapshot(self):
        snap = HierarchySnapshot(
            total_agents=10, active_agents=8,
            health_score=0.9,
        )
        assert snap.health_score == 0.9


# ============================================================
# AgentHierarchy Testleri
# ============================================================

class TestAgentHierarchy:
    """Agent hiyerarsi testleri."""

    def test_init(self):
        h = AgentHierarchy()
        assert h.agent_count == 0

    def test_add_agent(self):
        h = AgentHierarchy()
        agent = h.add_agent("test", AuthorityLevel.WORKER)
        assert agent.name == "test"
        assert h.agent_count == 1

    def test_add_agent_with_parent(self):
        h = AgentHierarchy()
        parent = h.add_agent("parent", AuthorityLevel.MASTER)
        child = h.add_agent(
            "child", AuthorityLevel.WORKER, parent_id=parent.agent_id,
        )
        assert child.parent_id == parent.agent_id
        assert child.agent_id in parent.children_ids

    def test_root(self):
        h = AgentHierarchy()
        master = h.add_agent("master", AuthorityLevel.MASTER)
        assert h.root is not None
        assert h.root.agent_id == master.agent_id

    def test_remove_agent(self):
        h = AgentHierarchy()
        agent = h.add_agent("test")
        assert h.remove_agent(agent.agent_id)
        assert h.agent_count == 0

    def test_remove_agent_with_children(self):
        h = AgentHierarchy()
        p = h.add_agent("parent", AuthorityLevel.MASTER)
        c = h.add_agent("child", parent_id=p.agent_id)
        h.remove_agent(p.agent_id)
        # Cocuk artik yetim ama hala mevcut
        assert h.agent_count == 1
        assert h.get_agent(c.agent_id) is not None

    def test_remove_not_found(self):
        h = AgentHierarchy()
        assert not h.remove_agent("nonexistent")

    def test_get_agent(self):
        h = AgentHierarchy()
        agent = h.add_agent("test")
        found = h.get_agent(agent.agent_id)
        assert found is not None
        assert found.name == "test"

    def test_get_parent(self):
        h, master, sup1, _, _, _ = _build_simple_hierarchy()
        parent = h.get_parent(sup1.agent_id)
        assert parent is not None
        assert parent.agent_id == master.agent_id

    def test_get_parent_root(self):
        h, master, _, _, _, _ = _build_simple_hierarchy()
        assert h.get_parent(master.agent_id) is None

    def test_get_children(self):
        h, master, _, _, _, _ = _build_simple_hierarchy()
        children = h.get_children(master.agent_id)
        assert len(children) == 2

    def test_get_ancestors(self):
        h, master, sup1, _, w1, _ = _build_simple_hierarchy()
        ancestors = h.get_ancestors(w1.agent_id)
        ancestor_ids = [a.agent_id for a in ancestors]
        assert sup1.agent_id in ancestor_ids
        assert master.agent_id in ancestor_ids

    def test_get_descendants(self):
        h, master, _, _, _, _ = _build_simple_hierarchy()
        descendants = h.get_descendants(master.agent_id)
        assert len(descendants) == 4  # 2 supervisors + 2 workers

    def test_can_delegate(self):
        h, master, sup1, _, w1, _ = _build_simple_hierarchy()
        assert h.can_delegate(master.agent_id, sup1.agent_id)
        assert h.can_delegate(sup1.agent_id, w1.agent_id)
        assert not h.can_delegate(w1.agent_id, sup1.agent_id)

    def test_can_delegate_same_level(self):
        h, _, sup1, sup2, _, _ = _build_simple_hierarchy()
        assert not h.can_delegate(sup1.agent_id, sup2.agent_id)

    def test_reporting_chain(self):
        h, master, sup1, _, w1, _ = _build_simple_hierarchy()
        chain = h.get_reporting_chain(w1.agent_id)
        assert sup1.agent_id in chain
        assert master.agent_id in chain

    def test_find_by_capability(self):
        h, _, _, _, _, _ = _build_simple_hierarchy()
        agents = h.find_by_capability("code")
        assert len(agents) >= 1

    def test_set_authority(self):
        h = AgentHierarchy()
        agent = h.add_agent("test", AuthorityLevel.WORKER)
        assert h.set_authority(agent.agent_id, AuthorityLevel.LEAD)
        assert agent.authority == AuthorityLevel.LEAD

    def test_active_count(self):
        h, _, _, _, _, _ = _build_simple_hierarchy()
        assert h.active_count == 5


# ============================================================
# ClusterManager Testleri
# ============================================================

class TestClusterManager:
    """Kume yoneticisi testleri."""

    def test_init(self):
        cm = ClusterManager()
        assert cm.cluster_count == 0

    def test_create_cluster(self):
        cm = ClusterManager()
        cluster = cm.create_cluster("Tech", ClusterType.TECHNICAL)
        assert cluster.name == "Tech"
        assert cluster.cluster_type == ClusterType.TECHNICAL
        assert cm.cluster_count == 1

    def test_destroy_cluster(self):
        cm = ClusterManager()
        cluster = cm.create_cluster("Test")
        assert cm.destroy_cluster(cluster.cluster_id)
        assert cm.cluster_count == 0

    def test_destroy_not_found(self):
        cm = ClusterManager()
        assert not cm.destroy_cluster("nonexistent")

    def test_assign_agent(self):
        cm = ClusterManager()
        cluster = cm.create_cluster("Test")
        assert cm.assign_agent("a1", cluster.cluster_id)
        assert "a1" in cluster.member_ids

    def test_assign_agent_as_leader(self):
        cm = ClusterManager()
        cluster = cm.create_cluster("Test")
        cm.assign_agent("a1", cluster.cluster_id, as_leader=True)
        assert cluster.leader_id == "a1"

    def test_assign_agent_full(self):
        cm = ClusterManager()
        cluster = cm.create_cluster("Test", max_members=2)
        cm.assign_agent("a1", cluster.cluster_id)
        cm.assign_agent("a2", cluster.cluster_id)
        assert not cm.assign_agent("a3", cluster.cluster_id)

    def test_remove_agent(self):
        cm = ClusterManager()
        cluster = cm.create_cluster("Test")
        cm.assign_agent("a1", cluster.cluster_id)
        assert cm.remove_agent("a1")
        assert "a1" not in cluster.member_ids

    def test_remove_agent_not_found(self):
        cm = ClusterManager()
        assert not cm.remove_agent("nonexistent")

    def test_get_cluster(self):
        cm = ClusterManager()
        cluster = cm.create_cluster("Test")
        found = cm.get_cluster(cluster.cluster_id)
        assert found is not None
        assert found.name == "Test"

    def test_get_agent_cluster(self):
        cm = ClusterManager()
        cluster = cm.create_cluster("Test")
        cm.assign_agent("a1", cluster.cluster_id)
        found = cm.get_agent_cluster("a1")
        assert found is not None
        assert found.cluster_id == cluster.cluster_id

    def test_get_cluster_members(self):
        cm = ClusterManager()
        cluster = cm.create_cluster("Test")
        cm.assign_agent("a1", cluster.cluster_id)
        cm.assign_agent("a2", cluster.cluster_id)
        members = cm.get_cluster_members(cluster.cluster_id)
        assert len(members) == 2

    def test_check_cluster_health_good(self):
        cm = ClusterManager()
        cluster = cm.create_cluster("Test")
        cm.assign_agent("a1", cluster.cluster_id, as_leader=True)
        cm.assign_agent("a2", cluster.cluster_id)
        health = cm.check_cluster_health(
            cluster.cluster_id, {"a1": 0.3, "a2": 0.4},
        )
        assert health > 0.5

    def test_check_cluster_health_overloaded(self):
        cm = ClusterManager()
        cluster = cm.create_cluster("Test")
        cm.assign_agent("a1", cluster.cluster_id, as_leader=True)
        cm.assign_agent("a2", cluster.cluster_id)
        health = cm.check_cluster_health(
            cluster.cluster_id, {"a1": 0.95, "a2": 0.95},
        )
        assert health < 0.9

    def test_balance_load(self):
        cm = ClusterManager()
        cluster = cm.create_cluster("Test")
        cm.assign_agent("a1", cluster.cluster_id)
        cm.assign_agent("a2", cluster.cluster_id)
        suggestions = cm.balance_load(
            cluster.cluster_id, {"a1": 0.9, "a2": 0.1},
        )
        assert len(suggestions) >= 1

    def test_send_inter_cluster(self):
        cm = ClusterManager()
        c1 = cm.create_cluster("Tech", ClusterType.TECHNICAL)
        c2 = cm.create_cluster("Biz", ClusterType.BUSINESS)
        result = cm.send_inter_cluster(c1.cluster_id, c2.cluster_id, "test")
        assert result["success"]

    def test_list_clusters(self):
        cm = ClusterManager()
        cm.create_cluster("A", ClusterType.TECHNICAL)
        cm.create_cluster("B", ClusterType.BUSINESS)
        assert len(cm.list_clusters()) == 2

    def test_list_clusters_by_type(self):
        cm = ClusterManager()
        cm.create_cluster("A", ClusterType.TECHNICAL)
        cm.create_cluster("B", ClusterType.BUSINESS)
        tech = cm.list_clusters(ClusterType.TECHNICAL)
        assert len(tech) == 1


# ============================================================
# DelegationEngine Testleri
# ============================================================

class TestDelegationEngine:
    """Yetki devri motoru testleri."""

    def test_init(self):
        de = DelegationEngine()
        assert de.total_delegations == 0
        assert de.active_delegations == 0

    def test_delegate(self):
        de = DelegationEngine()
        rec = de.delegate("t1", "master", "worker1", priority=7)
        assert rec.task_id == "t1"
        assert rec.priority == 7
        assert de.total_delegations == 1
        assert de.active_delegations == 1

    def test_accept(self):
        de = DelegationEngine()
        rec = de.delegate("t1", "a1", "a2")
        assert de.accept(rec.delegation_id)
        assert rec.status == DelegationStatus.ACCEPTED

    def test_start(self):
        de = DelegationEngine()
        rec = de.delegate("t1", "a1", "a2")
        de.accept(rec.delegation_id)
        assert de.start(rec.delegation_id)
        assert rec.status == DelegationStatus.IN_PROGRESS

    def test_complete(self):
        de = DelegationEngine()
        rec = de.delegate("t1", "a1", "a2")
        de.start(rec.delegation_id)
        assert de.complete(rec.delegation_id, "done")
        assert rec.status == DelegationStatus.COMPLETED
        assert de.active_delegations == 0

    def test_fail(self):
        de = DelegationEngine()
        rec = de.delegate("t1", "a1", "a2")
        assert de.fail(rec.delegation_id, "hata")
        assert rec.status == DelegationStatus.FAILED

    def test_escalate(self):
        de = DelegationEngine()
        rec = de.delegate("t1", "a1", "a2")
        assert de.escalate(rec.delegation_id)
        assert rec.status == DelegationStatus.ESCALATED

    def test_decompose_task(self):
        de = DelegationEngine()
        subtasks = de.decompose_task("Kodu analiz et ve test yaz", 2)
        assert len(subtasks) == 2
        assert subtasks[0]["order"] == 1

    def test_match_capability(self):
        de = DelegationEngine()
        agents = [
            AgentNode(name="a1", capabilities=["code", "test"], active=True),
            AgentNode(name="a2", capabilities=["deploy"], active=True),
            AgentNode(name="a3", capabilities=["code"], active=True),
        ]
        matched = de.match_capability(["code"], agents)
        assert len(matched) >= 2
        assert matched[0].name == "a1"  # Daha fazla eslesen

    def test_match_capability_empty(self):
        de = DelegationEngine()
        agents = [AgentNode(name="a1", capabilities=["x"], active=True)]
        matched = de.match_capability(["code"], agents)
        assert len(matched) == 0

    def test_distribute_workload(self):
        de = DelegationEngine()
        tasks = [
            {"subtask_id": "s1"}, {"subtask_id": "s2"}, {"subtask_id": "s3"},
        ]
        agents = [
            AgentNode(name="a1", workload=0.2, active=True),
            AgentNode(name="a2", workload=0.5, active=True),
        ]
        assignments = de.distribute_workload(tasks, agents)
        assert len(assignments) == 3

    def test_propagate_priority(self):
        de = DelegationEngine()
        rec = de.delegate("t1", "a1", "a2", priority=3)
        assert de.propagate_priority(rec.delegation_id, 9)
        assert rec.priority == 9

    def test_get_delegation(self):
        de = DelegationEngine()
        rec = de.delegate("t1", "a1", "a2")
        found = de.get_delegation(rec.delegation_id)
        assert found is not None

    def test_get_agent_delegations(self):
        de = DelegationEngine()
        de.delegate("t1", "a1", "a2")
        de.delegate("t2", "a1", "a3")
        delegations = de.get_agent_delegations("a1")
        assert len(delegations) == 2

    def test_completion_rate(self):
        de = DelegationEngine()
        r1 = de.delegate("t1", "a1", "a2")
        r2 = de.delegate("t2", "a1", "a3")
        de.complete(r1.delegation_id)
        assert de.completion_rate == 0.5


# ============================================================
# SupervisionController Testleri
# ============================================================

class TestSupervisionController:
    """Denetim kontrolcusu testleri."""

    def test_init(self):
        sc = SupervisionController()
        assert sc.event_count == 0

    def test_monitor_info(self):
        sc = SupervisionController()
        ev = sc.monitor("a1", "task_started", "Gorev basladi")
        assert ev.severity == "info"
        assert not ev.requires_intervention
        assert sc.event_count == 1

    def test_monitor_critical(self):
        sc = SupervisionController()
        ev = sc.monitor("a1", "crash", "Agent coktu", severity="critical")
        assert ev.requires_intervention
        assert sc.intervention_count == 1

    def test_track_progress(self):
        sc = SupervisionController()
        result = sc.track_progress("a1", "t1", 0.5)
        assert result["progress"] == 0.5

    def test_get_progress(self):
        sc = SupervisionController()
        sc.track_progress("a1", "t1", 0.3)
        sc.track_progress("a1", "t2", 0.7)
        progress = sc.get_progress("a1")
        assert len(progress) == 2

    def test_get_progress_specific_task(self):
        sc = SupervisionController()
        sc.track_progress("a1", "t1", 0.5)
        sc.track_progress("a1", "t2", 0.8)
        progress = sc.get_progress("a1", "t1")
        assert len(progress) == 1
        assert progress[0]["progress"] == 0.5

    def test_check_intervention_not_needed(self):
        sc = SupervisionController()
        sc.monitor("a1", "ok", severity="info")
        result = sc.check_intervention("a1")
        assert not result["needs_intervention"]

    def test_check_intervention_needed(self):
        sc = SupervisionController()
        sc.monitor("a1", "error", severity="error")
        result = sc.check_intervention("a1")
        assert result["needs_intervention"]

    def test_should_escalate_errors(self):
        sc = SupervisionController()
        assert sc.should_escalate("a1", error_count=3)

    def test_should_escalate_timeout(self):
        sc = SupervisionController(escalation_timeout=100)
        assert sc.should_escalate("a1", stall_time_seconds=150)

    def test_should_not_escalate(self):
        sc = SupervisionController()
        assert not sc.should_escalate("a1", error_count=1)

    def test_record_performance(self):
        sc = SupervisionController()
        avg = sc.record_performance("a1", 0.8)
        assert avg == 0.8

    def test_get_avg_performance(self):
        sc = SupervisionController()
        sc.record_performance("a1", 0.6)
        sc.record_performance("a1", 0.8)
        avg = sc.get_avg_performance("a1")
        assert abs(avg - 0.7) < 0.01

    def test_get_events_filtered(self):
        sc = SupervisionController()
        sc.monitor("a1", "ok", severity="info")
        sc.monitor("a1", "err", severity="error")
        sc.monitor("a2", "ok", severity="info")
        events = sc.get_events(agent_id="a1", severity="error")
        assert len(events) == 1


# ============================================================
# ReportingSystem Testleri
# ============================================================

class TestReportingSystem:
    """Raporlama sistemi testleri."""

    def test_init(self):
        rs = ReportingSystem()
        assert rs.report_count == 0

    def test_submit_status(self):
        rs = ReportingSystem()
        report = rs.submit_status("a1", "active")
        assert report.report_type == ReportType.STATUS
        assert rs.report_count == 1

    def test_submit_progress(self):
        rs = ReportingSystem()
        report = rs.submit_progress("a1", "t1", 0.5, "devam ediyor")
        assert report.report_type == ReportType.PROGRESS
        assert "50%" in report.title

    def test_submit_exception(self):
        rs = ReportingSystem()
        report = rs.submit_exception("a1", "NullPointer", "critical")
        assert report.report_type == ReportType.EXCEPTION
        assert rs.exception_count == 1

    def test_aggregate_status(self):
        rs = ReportingSystem()
        rs.submit_status("a1", "active")
        rs.submit_status("a2", "idle")
        result = rs.aggregate_status()
        assert result["total_agents"] == 2

    def test_rollup_progress(self):
        rs = ReportingSystem()
        rs.submit_progress("a1", "t1", 0.5)
        rs.submit_progress("a1", "t2", 1.0)
        rollup = rs.rollup_progress()
        assert rollup["total_tasks"] == 2
        assert rollup["completed_tasks"] == 1

    def test_generate_daily_summary(self):
        rs = ReportingSystem()
        rs.submit_status("a1", "active")
        rs.submit_exception("a1", "err")
        report = rs.generate_daily_summary()
        assert report.report_type == ReportType.DAILY
        assert report.content["total_reports"] >= 2

    def test_generate_weekly_summary(self):
        rs = ReportingSystem()
        rs.submit_exception("a1", "hata1")
        report = rs.generate_weekly_summary()
        assert report.report_type == ReportType.WEEKLY

    def test_generate_custom_report(self):
        rs = ReportingSystem()
        rs.submit_status("a1", "ok")
        rs.submit_exception("a1", "err")
        report = rs.generate_custom_report(
            "Test Raporu",
            report_types=[ReportType.EXCEPTION],
        )
        assert report.report_type == ReportType.CUSTOM
        assert report.content["total_matching"] == 1

    def test_get_reports_filtered(self):
        rs = ReportingSystem()
        rs.submit_status("a1", "ok")
        rs.submit_exception("a2", "err")
        reports = rs.get_reports(agent_id="a1")
        assert len(reports) == 1

    def test_get_reports_by_type(self):
        rs = ReportingSystem()
        rs.submit_status("a1", "ok")
        rs.submit_exception("a1", "err")
        reports = rs.get_reports(report_type=ReportType.EXCEPTION)
        assert len(reports) == 1


# ============================================================
# CommandChain Testleri
# ============================================================

class TestCommandChain:
    """Komut zinciri testleri."""

    def test_init(self):
        cc = CommandChain()
        assert cc.total_commands == 0

    def test_send_directive(self):
        cc = CommandChain()
        cmd = cc.send_directive("master", ["w1", "w2"], "Calis")
        assert cmd.command_type == CommandType.DIRECTIVE
        assert cc.total_commands == 1

    def test_send_broadcast(self):
        cc = CommandChain()
        cmd = cc.send_broadcast("master", "Duyuru", ["a1", "a2", "a3"])
        assert cmd.command_type == CommandType.BROADCAST
        assert len(cmd.to_agents) == 3

    def test_send_targeted(self):
        cc = CommandChain()
        cmd = cc.send_targeted("sup", "worker", "Gor")
        assert cmd.command_type == CommandType.TARGETED
        assert cmd.to_agents == ["worker"]

    def test_send_emergency(self):
        cc = CommandChain()
        cmd = cc.send_emergency("master", "ACIL DURUM", ["a1", "a2"])
        assert cmd.command_type == CommandType.EMERGENCY
        assert cmd.priority == 10
        assert cc.emergency_count == 1

    def test_send_feedback(self):
        cc = CommandChain()
        cmd = cc.send_feedback("worker", "sup", "Tamamlandi")
        assert cmd.command_type == CommandType.FEEDBACK

    def test_acknowledge(self):
        cc = CommandChain()
        cmd = cc.send_directive("master", ["w1"], "Test")
        assert cc.acknowledge(cmd.command_id, "w1")
        assert "w1" in cmd.acknowledged_by

    def test_fully_acknowledged(self):
        cc = CommandChain()
        cmd = cc.send_directive("master", ["w1", "w2"], "Test")
        cc.acknowledge(cmd.command_id, "w1")
        assert not cc.is_fully_acknowledged(cmd.command_id)
        cc.acknowledge(cmd.command_id, "w2")
        assert cc.is_fully_acknowledged(cmd.command_id)

    def test_get_inbox(self):
        cc = CommandChain()
        cc.send_targeted("master", "w1", "Gorev 1", priority=3)
        cc.send_targeted("master", "w1", "Gorev 2", priority=8)
        inbox = cc.get_inbox("w1")
        assert len(inbox) == 2
        assert inbox[0].priority >= inbox[1].priority

    def test_get_pending(self):
        cc = CommandChain()
        cc.send_directive("master", ["w1"], "Test")
        assert cc.pending_count == 1

    def test_get_command(self):
        cc = CommandChain()
        cmd = cc.send_targeted("m", "w", "test")
        found = cc.get_command(cmd.command_id)
        assert found is not None


# ============================================================
# AutonomyController Testleri
# ============================================================

class TestAutonomyController:
    """Otonomi kontrolcusu testleri."""

    def test_init(self):
        ac = AutonomyController()
        assert ac.managed_agents == 0

    def test_set_and_get_autonomy(self):
        ac = AutonomyController()
        ac.set_autonomy("a1", AutonomyLevel.HIGH)
        assert ac.get_autonomy("a1") == AutonomyLevel.HIGH

    def test_default_autonomy(self):
        ac = AutonomyController(default_level=AutonomyLevel.LOW)
        assert ac.get_autonomy("unknown") == AutonomyLevel.LOW

    def test_can_act_independently_full(self):
        ac = AutonomyController()
        ac.set_autonomy("a1", AutonomyLevel.FULL)
        assert ac.can_act_independently("a1", "delete")
        assert ac.can_act_independently("a1", "production_change")

    def test_can_act_independently_none(self):
        ac = AutonomyController()
        ac.set_autonomy("a1", AutonomyLevel.NONE)
        assert not ac.can_act_independently("a1", "read")

    def test_can_act_low_risk(self):
        ac = AutonomyController()
        ac.set_autonomy("a1", AutonomyLevel.LOW)
        assert ac.can_act_independently("a1", "read")
        assert not ac.can_act_independently("a1", "deploy")

    def test_can_act_medium_risk(self):
        ac = AutonomyController()
        ac.set_autonomy("a1", AutonomyLevel.MEDIUM)
        assert ac.can_act_independently("a1", "notify")
        assert not ac.can_act_independently("a1", "delete")

    def test_should_ask_permission(self):
        ac = AutonomyController()
        ac.set_autonomy("a1", AutonomyLevel.LOW)
        assert ac.should_ask_permission("a1", "deploy")
        assert not ac.should_ask_permission("a1", "read")

    def test_should_report(self):
        ac = AutonomyController()
        ac.set_autonomy("a1", AutonomyLevel.MEDIUM)
        assert ac.should_report("a1", "update")
        assert not ac.should_report("a1", "read")

    def test_should_report_full(self):
        ac = AutonomyController()
        ac.set_autonomy("a1", AutonomyLevel.FULL)
        assert not ac.should_report("a1", "deploy")
        assert ac.should_report("a1", "production_change")

    def test_record_action(self):
        ac = AutonomyController()
        ac.record_action("a1", "read", True)
        assert ac.total_actions == 1

    def test_adjust_autonomy_increase(self):
        ac = AutonomyController()
        ac.set_autonomy("a1", AutonomyLevel.MEDIUM)
        # 10 basarili aksiyon
        for _ in range(10):
            ac.record_action("a1", "read", True)
        new_level = ac.adjust_autonomy("a1")
        assert new_level == AutonomyLevel.HIGH

    def test_adjust_autonomy_decrease(self):
        ac = AutonomyController()
        ac.set_autonomy("a1", AutonomyLevel.MEDIUM)
        # 10 basarisiz aksiyon
        for _ in range(10):
            ac.record_action("a1", "read", False)
        new_level = ac.adjust_autonomy("a1")
        assert new_level == AutonomyLevel.LOW

    def test_get_success_rate(self):
        ac = AutonomyController()
        ac.record_action("a1", "read", True)
        ac.record_action("a1", "write", False)
        assert ac.get_success_rate("a1") == 0.5

    def test_get_action_history(self):
        ac = AutonomyController()
        ac.record_action("a1", "read", True)
        ac.record_action("a2", "write", False)
        history = ac.get_action_history("a1")
        assert len(history) == 1


# ============================================================
# ConflictArbiter Testleri
# ============================================================

class TestConflictArbiter:
    """Catisma hakemi testleri."""

    def test_init(self):
        ca = ConflictArbiter()
        assert ca.total_conflicts == 0

    def test_report_conflict(self):
        ca = ConflictArbiter()
        rec = ca.report_conflict(
            ConflictType.RESOURCE, ["a1", "a2"], "gpu",
        )
        assert rec.conflict_type == ConflictType.RESOURCE
        assert ca.total_conflicts == 1
        assert ca.active_conflicts == 1

    def test_resolve_by_priority(self):
        ca = ConflictArbiter()
        rec = ca.report_conflict(
            ConflictType.PRIORITY, ["a1", "a2"],
        )
        winner = ca.resolve_by_priority(
            rec.conflict_id, {"a1": 5, "a2": 8},
        )
        assert winner == "a2"
        assert ca.active_conflicts == 0
        assert ca.resolved_count == 1

    def test_resolve_by_authority(self):
        ca = ConflictArbiter()
        rec = ca.report_conflict(
            ConflictType.DECISION, ["a1", "a2"],
        )
        winner = ca.resolve_by_authority(
            rec.conflict_id, {"a1": 3, "a2": 1},
        )
        assert winner == "a1"

    def test_resolve_by_consensus(self):
        ca = ConflictArbiter()
        rec = ca.report_conflict(
            ConflictType.DECISION, ["a1", "a2", "a3"],
        )
        winner = ca.resolve_by_consensus(
            rec.conflict_id,
            {"a1": "optionA", "a2": "optionB", "a3": "optionA"},
        )
        assert winner == "optionA"

    def test_escalate_conflict(self):
        ca = ConflictArbiter()
        rec = ca.report_conflict(
            ConflictType.DEADLOCK, ["a1", "a2"],
        )
        assert ca.escalate_conflict(rec.conflict_id)
        assert rec.resolution == ResolutionStrategy.ESCALATION

    def test_detect_deadlock_simple(self):
        ca = ConflictArbiter()
        # A bekliyor B, B bekliyor A -> deadlock
        cycles = ca.detect_deadlock({"a": ["b"], "b": ["a"]})
        assert len(cycles) >= 1

    def test_detect_deadlock_none(self):
        ca = ConflictArbiter()
        cycles = ca.detect_deadlock({"a": ["b"], "b": ["c"]})
        assert len(cycles) == 0

    def test_lock_resource(self):
        ca = ConflictArbiter()
        assert ca.lock_resource("gpu", "a1")
        assert ca.locked_resources == 1

    def test_lock_resource_conflict(self):
        ca = ConflictArbiter()
        ca.lock_resource("gpu", "a1")
        assert not ca.lock_resource("gpu", "a2")

    def test_unlock_resource(self):
        ca = ConflictArbiter()
        ca.lock_resource("gpu", "a1")
        assert ca.unlock_resource("gpu", "a1")
        assert ca.locked_resources == 0

    def test_unlock_wrong_owner(self):
        ca = ConflictArbiter()
        ca.lock_resource("gpu", "a1")
        assert not ca.unlock_resource("gpu", "a2")

    def test_get_resource_owner(self):
        ca = ConflictArbiter()
        ca.lock_resource("gpu", "a1")
        assert ca.get_resource_owner("gpu") == "a1"
        assert ca.get_resource_owner("cpu") == ""

    def test_get_active_conflicts(self):
        ca = ConflictArbiter()
        ca.report_conflict(ConflictType.RESOURCE, ["a1", "a2"])
        ca.report_conflict(ConflictType.PRIORITY, ["a3", "a4"])
        actives = ca.get_active_conflicts()
        assert len(actives) == 2


# ============================================================
# HierarchyOrchestrator Testleri
# ============================================================

class TestHierarchyOrchestrator:
    """Hiyerarsi orkestrator testleri."""

    def test_init(self):
        ho = HierarchyOrchestrator()
        snap = ho.get_snapshot()
        assert snap.total_agents == 0

    def test_setup_agent(self):
        ho = HierarchyOrchestrator()
        agent = ho.setup_agent("master", AuthorityLevel.MASTER)
        assert agent.name == "master"
        assert ho.hierarchy.agent_count == 1

    def test_setup_agent_with_cluster(self):
        ho = HierarchyOrchestrator()
        cluster = ho.clusters.create_cluster("Tech", ClusterType.TECHNICAL)
        agent = ho.setup_agent(
            "worker", cluster_id=cluster.cluster_id,
        )
        assert agent.cluster_id == cluster.cluster_id

    def test_delegate_task(self):
        ho = HierarchyOrchestrator()
        master = ho.setup_agent(
            "master", AuthorityLevel.MASTER,
            autonomy=AutonomyLevel.FULL,
        )
        worker = ho.setup_agent(
            "worker", AuthorityLevel.WORKER,
            parent_id=master.agent_id,
            capabilities=["code"],
        )
        result = ho.delegate_task(
            master.agent_id, "task1",
            required_capabilities=["code"],
        )
        assert result["success"]
        assert result["to_agent"] == worker.agent_id

    def test_delegate_task_no_children(self):
        ho = HierarchyOrchestrator()
        agent = ho.setup_agent("lone", AuthorityLevel.WORKER)
        result = ho.delegate_task(agent.agent_id, "task1")
        assert not result["success"]

    def test_check_action(self):
        ho = HierarchyOrchestrator()
        ho.setup_agent("w1", autonomy=AutonomyLevel.LOW)
        agent_id = ho.hierarchy.all_agents[0].agent_id
        result = ho.check_action(agent_id, "deploy")
        assert result["needs_permission"]

    def test_report_conflict(self):
        ho = HierarchyOrchestrator()
        result = ho.report_conflict(
            ConflictType.RESOURCE,
            ["a1", "a2"],
            resource="gpu",
            agent_priorities={"a1": 5, "a2": 8},
        )
        assert result["resolved"]
        assert result["winner"] == "a2"

    def test_send_command_directive(self):
        ho = HierarchyOrchestrator()
        result = ho.send_command(
            "master", "Do it", to_agents=["w1"],
            command_type="directive",
        )
        assert result["command_id"]

    def test_send_command_broadcast(self):
        ho = HierarchyOrchestrator()
        result = ho.send_command(
            "master", "Duyuru",
            to_agents=["a1", "a2"],
            command_type="broadcast",
        )
        assert result["type"] == "broadcast"

    def test_send_command_emergency(self):
        ho = HierarchyOrchestrator()
        result = ho.send_command(
            "master", "ACIL",
            to_agents=["a1"],
            command_type="emergency",
        )
        assert result["type"] == "emergency"

    def test_get_snapshot(self):
        ho = HierarchyOrchestrator()
        ho.setup_agent("m", AuthorityLevel.MASTER)
        ho.setup_agent("w", AuthorityLevel.WORKER)
        snap = ho.get_snapshot()
        assert snap.total_agents == 2
        assert snap.active_agents == 2

    def test_get_tree_view(self):
        ho = HierarchyOrchestrator()
        m = ho.setup_agent("master", AuthorityLevel.MASTER)
        ho.setup_agent("worker", parent_id=m.agent_id)
        tree = ho.get_tree_view()
        assert tree["name"] == "master"
        assert len(tree["children"]) == 1

    def test_restructure(self):
        ho = HierarchyOrchestrator()
        m = ho.setup_agent("master", AuthorityLevel.MASTER)
        s1 = ho.setup_agent("sup1", parent_id=m.agent_id)
        s2 = ho.setup_agent("sup2", parent_id=m.agent_id)
        w = ho.setup_agent("worker", parent_id=s1.agent_id)
        assert ho.restructure(w.agent_id, s2.agent_id)
        assert w.parent_id == s2.agent_id

    def test_optimize_workload(self):
        ho = HierarchyOrchestrator()
        cluster = ho.clusters.create_cluster("Tech")
        m = ho.setup_agent(
            "master", AuthorityLevel.MASTER,
            cluster_id=cluster.cluster_id,
        )
        w1 = ho.setup_agent(
            "worker1", parent_id=m.agent_id,
            cluster_id=cluster.cluster_id,
        )
        w2 = ho.setup_agent(
            "worker2", parent_id=m.agent_id,
            cluster_id=cluster.cluster_id,
        )
        w1.workload = 0.9
        w2.workload = 0.1
        suggestions = ho.optimize_workload()
        assert len(suggestions) >= 1

    def test_sub_components(self):
        ho = HierarchyOrchestrator()
        assert ho.hierarchy is not None
        assert ho.clusters is not None
        assert ho.delegation is not None
        assert ho.supervision is not None
        assert ho.reporting is not None
        assert ho.commands is not None
        assert ho.autonomy is not None
        assert ho.conflicts is not None


# ============================================================
# Entegrasyon Testleri
# ============================================================

class TestIntegration:
    """Entegrasyon testleri."""

    def test_full_hierarchy_workflow(self):
        """Tam hiyerarsi is akisi."""
        ho = HierarchyOrchestrator()

        # Kume olustur
        tech = ho.clusters.create_cluster("Tech", ClusterType.TECHNICAL)

        # Agent'lar kur
        master = ho.setup_agent(
            "master", AuthorityLevel.MASTER,
            autonomy=AutonomyLevel.FULL,
            cluster_id=tech.cluster_id,
        )
        worker = ho.setup_agent(
            "worker", AuthorityLevel.WORKER,
            parent_id=master.agent_id,
            capabilities=["code", "test"],
            cluster_id=tech.cluster_id,
        )

        # Gorev devret
        result = ho.delegate_task(
            master.agent_id, "task1",
            required_capabilities=["code"],
        )
        assert result["success"]

        # Ilerleme raporla
        ho.reporting.submit_progress(worker.agent_id, "task1", 0.5)
        ho.reporting.submit_progress(worker.agent_id, "task1", 1.0)

        # Snapshot kontrol
        snap = ho.get_snapshot()
        assert snap.total_agents == 2
        assert snap.pending_delegations >= 1

    def test_conflict_and_resolution(self):
        """Catisma tespiti ve cozumu."""
        ho = HierarchyOrchestrator()

        ho.setup_agent("a1", capabilities=["gpu"])
        ho.setup_agent("a2", capabilities=["gpu"])

        # Catisma bildir
        result = ho.report_conflict(
            ConflictType.RESOURCE,
            ["a1", "a2"],
            resource="gpu",
            agent_priorities={"a1": 3, "a2": 7},
        )
        assert result["resolved"]
        assert result["winner"] == "a2"

    def test_autonomy_dynamic_adjustment(self):
        """Dinamik otonomi ayarlama."""
        ho = HierarchyOrchestrator()
        agent = ho.setup_agent(
            "worker", autonomy=AutonomyLevel.MEDIUM,
        )

        # Basarili aksiyonlar kaydet
        for _ in range(10):
            ho.autonomy.record_action(agent.agent_id, "read", True)

        new_level = ho.autonomy.adjust_autonomy(agent.agent_id)
        assert new_level == AutonomyLevel.HIGH

    def test_command_and_acknowledge(self):
        """Komut gonder ve onayla."""
        ho = HierarchyOrchestrator()
        m = ho.setup_agent("master", AuthorityLevel.MASTER)
        w = ho.setup_agent("worker", parent_id=m.agent_id)

        cmd_result = ho.send_command(
            m.agent_id, "Rapor ver",
            to_agents=[w.agent_id],
        )

        # Onayla
        ho.commands.acknowledge(cmd_result["command_id"], w.agent_id)
        assert ho.commands.is_fully_acknowledged(cmd_result["command_id"])

    def test_supervision_and_escalation(self):
        """Denetim ve eskalasyon."""
        ho = HierarchyOrchestrator()
        w = ho.setup_agent("worker")

        # Kritik olay
        ho.supervision.monitor(w.agent_id, "crash", severity="critical")

        # Eskalasyon kontrol
        assert ho.supervision.should_escalate(w.agent_id)

        # Mudahale kontrol
        result = ho.supervision.check_intervention(w.agent_id)
        assert result["needs_intervention"]

    def test_reporting_with_summary(self):
        """Raporlama ve ozet."""
        ho = HierarchyOrchestrator()

        ho.reporting.submit_status("a1", "active")
        ho.reporting.submit_progress("a1", "t1", 0.5)
        ho.reporting.submit_exception("a1", "timeout")

        daily = ho.reporting.generate_daily_summary()
        assert daily.content["total_reports"] >= 3

    def test_deadlock_detection(self):
        """Kilitlenme tespiti."""
        ho = HierarchyOrchestrator()

        # Dongusel bekleme
        cycles = ho.conflicts.detect_deadlock({
            "a1": ["a2"],
            "a2": ["a3"],
            "a3": ["a1"],
        })
        assert len(cycles) >= 1
