"""ATLAS Project & Deadline Manager testleri.

ProjectTracker, MilestoneManager,
ProjectDependencyResolver, DeadlinePredictor,
BlockerDetector, ProjectProgressReporter,
AutoEscalator, ProjectResourceBalancer,
ProjectMgrOrchestrator testleri.
"""

import pytest

from app.core.projectmgr.project_tracker import (
    ProjectTracker,
)
from app.core.projectmgr.milestone_manager import (
    MilestoneManager,
)
from app.core.projectmgr.dependency_resolver import (
    ProjectDependencyResolver,
)
from app.core.projectmgr.deadline_predictor import (
    DeadlinePredictor,
)
from app.core.projectmgr.blocker_detector import (
    BlockerDetector,
)
from app.core.projectmgr.progress_reporter import (
    ProjectProgressReporter,
)
from app.core.projectmgr.auto_escalator import (
    AutoEscalator,
)
from app.core.projectmgr.resource_balancer import (
    ProjectResourceBalancer,
)
from app.core.projectmgr.projectmgr_orchestrator import (
    ProjectMgrOrchestrator,
)


# ─── ProjectTracker ─────────────────────


class TestProjectTrackerInit:
    """ProjectTracker başlatma testleri."""

    def test_init(self):
        t = ProjectTracker()
        assert t.project_count == 0

    def test_init_empty(self):
        t = ProjectTracker()
        assert t.active_count == 0

    def test_init_stats(self):
        t = ProjectTracker()
        assert t._stats["projects_created"] == 0


class TestProjectTrackerCreate:
    """Proje oluşturma testleri."""

    def test_create_basic(self):
        t = ProjectTracker()
        r = t.create_project("Test Proj")
        assert r["created"] is True
        assert "project_id" in r

    def test_create_with_details(self):
        t = ProjectTracker()
        r = t.create_project(
            "P1", owner="fatih",
            description="desc",
            deadline="2026-03-01",
            priority="high",
        )
        assert r["name"] == "P1"

    def test_create_increments(self):
        t = ProjectTracker()
        t.create_project("P1")
        t.create_project("P2")
        assert t.project_count == 2

    def test_create_status_draft(self):
        t = ProjectTracker()
        r = t.create_project("P")
        assert r["status"] == "draft"


class TestProjectTrackerStatus:
    """Durum güncelleme testleri."""

    def test_update_status(self):
        t = ProjectTracker()
        r = t.create_project("P")
        pid = r["project_id"]
        u = t.update_status(pid, "active")
        assert u["updated"] is True
        assert u["new_status"] == "active"

    def test_update_not_found(self):
        t = ProjectTracker()
        u = t.update_status("xxx", "active")
        assert u["updated"] is False

    def test_update_tracks_old(self):
        t = ProjectTracker()
        r = t.create_project("P")
        pid = r["project_id"]
        u = t.update_status(pid, "active")
        assert u["old_status"] == "draft"


class TestProjectTrackerProgress:
    """İlerleme testleri."""

    def test_update_progress(self):
        t = ProjectTracker()
        r = t.create_project("P")
        pid = r["project_id"]
        u = t.update_progress(pid, 5, 10)
        assert u["progress"] == 50.0

    def test_progress_not_found(self):
        t = ProjectTracker()
        u = t.update_progress("x", 1, 1)
        assert u["updated"] is False

    def test_progress_zero_total(self):
        t = ProjectTracker()
        r = t.create_project("P")
        pid = r["project_id"]
        u = t.update_progress(pid, 0, 0)
        assert u["progress"] == 0.0


class TestProjectTrackerHealth:
    """Sağlık puanlama testleri."""

    def test_score_healthy(self):
        t = ProjectTracker()
        r = t.create_project("P")
        pid = r["project_id"]
        h = t.score_health(pid)
        assert h["level"] == "healthy"

    def test_score_at_risk(self):
        t = ProjectTracker()
        r = t.create_project("P")
        pid = r["project_id"]
        h = t.score_health(
            pid, on_schedule=False,
            blockers=2,
        )
        assert h["level"] == "at_risk"

    def test_score_critical(self):
        t = ProjectTracker()
        r = t.create_project("P")
        pid = r["project_id"]
        h = t.score_health(
            pid, on_schedule=False,
            blockers=3, team_morale=30,
        )
        assert h["level"] == "critical"

    def test_score_not_found(self):
        t = ProjectTracker()
        h = t.score_health("xxx")
        assert h["scored"] is False


class TestProjectTrackerTeam:
    """Takım atama testleri."""

    def test_assign_team(self):
        t = ProjectTracker()
        r = t.create_project("P")
        pid = r["project_id"]
        a = t.assign_team(
            pid, ["alice", "bob"],
        )
        assert a["assigned"] is True
        assert a["count"] == 2

    def test_assign_not_found(self):
        t = ProjectTracker()
        a = t.assign_team("x", ["a"])
        assert a["assigned"] is False


class TestProjectTrackerQuery:
    """Sorgu testleri."""

    def test_get_project(self):
        t = ProjectTracker()
        r = t.create_project("P")
        pid = r["project_id"]
        p = t.get_project(pid)
        assert p["name"] == "P"

    def test_get_none(self):
        t = ProjectTracker()
        assert t.get_project("x") is None

    def test_list_projects(self):
        t = ProjectTracker()
        t.create_project("P1")
        t.create_project("P2")
        assert len(t.list_projects()) == 2

    def test_list_by_status(self):
        t = ProjectTracker()
        r = t.create_project("P1")
        t.update_status(
            r["project_id"], "active",
        )
        t.create_project("P2")
        active = t.list_projects("active")
        assert len(active) == 1


# ─── MilestoneManager ───────────────────


class TestMilestoneManagerInit:
    """MilestoneManager başlatma testleri."""

    def test_init(self):
        m = MilestoneManager()
        assert m.milestone_count == 0

    def test_init_completed(self):
        m = MilestoneManager()
        assert m.completed_count == 0


class TestMilestoneCreate:
    """Kilometre taşı oluşturma testleri."""

    def test_create(self):
        m = MilestoneManager()
        r = m.create_milestone("p1", "MS1")
        assert r["created"] is True

    def test_create_with_details(self):
        m = MilestoneManager()
        r = m.create_milestone(
            "p1", "MS1",
            due_date="2026-04-01",
            description="Test",
            weight=2.0,
        )
        assert r["name"] == "MS1"

    def test_create_increments(self):
        m = MilestoneManager()
        m.create_milestone("p1", "A")
        m.create_milestone("p1", "B")
        assert m.milestone_count == 2


class TestMilestoneProgress:
    """İlerleme testleri."""

    def test_update_progress(self):
        m = MilestoneManager()
        r = m.create_milestone("p1", "M")
        mid = r["milestone_id"]
        u = m.update_progress(mid, 50)
        assert u["updated"] is True
        assert u["status"] == "in_progress"

    def test_complete(self):
        m = MilestoneManager()
        r = m.create_milestone("p1", "M")
        mid = r["milestone_id"]
        u = m.update_progress(mid, 100)
        assert u["status"] == "completed"
        assert m.completed_count == 1

    def test_not_found(self):
        m = MilestoneManager()
        u = m.update_progress("x", 50)
        assert u["updated"] is False


class TestMilestoneVerify:
    """Doğrulama testleri."""

    def test_verify_incomplete(self):
        m = MilestoneManager()
        r = m.create_milestone("p1", "M")
        mid = r["milestone_id"]
        v = m.verify_completion(mid)
        assert v["complete"] is False

    def test_verify_complete(self):
        m = MilestoneManager()
        r = m.create_milestone("p1", "M")
        mid = r["milestone_id"]
        m.update_progress(mid, 100)
        v = m.verify_completion(mid)
        assert v["complete"] is True

    def test_verify_not_found(self):
        m = MilestoneManager()
        v = m.verify_completion("x")
        assert v["verified"] is False

    def test_verify_with_deps(self):
        m = MilestoneManager()
        r1 = m.create_milestone("p1", "A")
        r2 = m.create_milestone("p1", "B")
        m.add_dependency(
            r2["milestone_id"],
            r1["milestone_id"],
        )
        m.update_progress(
            r2["milestone_id"], 100,
        )
        v = m.verify_completion(
            r2["milestone_id"],
        )
        assert v["dependencies_met"] is False


class TestMilestoneCelebration:
    """Kutlama testleri."""

    def test_no_celebrate(self):
        m = MilestoneManager()
        r = m.create_milestone("p1", "M")
        c = m.check_celebration(
            r["milestone_id"],
        )
        assert c["celebrate"] is False

    def test_celebrate(self):
        m = MilestoneManager()
        r = m.create_milestone("p1", "M")
        m.update_progress(
            r["milestone_id"], 100,
        )
        c = m.check_celebration(
            r["milestone_id"],
        )
        assert c["celebrate"] is True

    def test_major_significance(self):
        m = MilestoneManager()
        r = m.create_milestone(
            "p1", "M", weight=3.0,
        )
        m.update_progress(
            r["milestone_id"], 100,
        )
        c = m.check_celebration(
            r["milestone_id"],
        )
        assert c["significance"] == "major"

    def test_not_found(self):
        m = MilestoneManager()
        c = m.check_celebration("x")
        assert c["celebrate"] is False


class TestMilestoneQuery:
    """Sorgu testleri."""

    def test_get_milestones(self):
        m = MilestoneManager()
        m.create_milestone("p1", "A")
        m.create_milestone("p2", "B")
        r = m.get_milestones("p1")
        assert len(r) == 1

    def test_get_by_status(self):
        m = MilestoneManager()
        r = m.create_milestone("p1", "A")
        m.update_progress(
            r["milestone_id"], 100,
        )
        m.create_milestone("p1", "B")
        done = m.get_milestones(
            status="completed",
        )
        assert len(done) == 1

    def test_get_milestone(self):
        m = MilestoneManager()
        r = m.create_milestone("p1", "A")
        ms = m.get_milestone(
            r["milestone_id"],
        )
        assert ms is not None

    def test_get_milestone_none(self):
        m = MilestoneManager()
        assert m.get_milestone("x") is None


# ─── ProjectDependencyResolver ──────────


class TestDependencyInit:
    """DependencyResolver başlatma."""

    def test_init(self):
        d = ProjectDependencyResolver()
        assert d.dependency_count == 0

    def test_init_tasks(self):
        d = ProjectDependencyResolver()
        assert d.task_count == 0


class TestDependencyTasks:
    """Görev testleri."""

    def test_add_task(self):
        d = ProjectDependencyResolver()
        r = d.add_task("t1", "Task 1")
        assert r["added"] is True

    def test_add_dependency(self):
        d = ProjectDependencyResolver()
        d.add_task("t1")
        d.add_task("t2")
        r = d.add_dependency("t2", "t1")
        assert r["added"] is True
        assert d.dependency_count == 1


class TestDependencyCycle:
    """Döngü tespiti testleri."""

    def test_no_cycle(self):
        d = ProjectDependencyResolver()
        d.add_task("t1")
        d.add_task("t2")
        d.add_dependency("t2", "t1")
        r = d.detect_circular()
        assert r["has_cycles"] is False

    def test_cycle(self):
        d = ProjectDependencyResolver()
        d.add_task("t1")
        d.add_task("t2")
        d.add_dependency("t1", "t2")
        d.add_dependency("t2", "t1")
        r = d.detect_circular()
        assert r["has_cycles"] is True
        assert r["count"] > 0


class TestCriticalPath:
    """Kritik yol testleri."""

    def test_empty(self):
        d = ProjectDependencyResolver()
        r = d.find_critical_path()
        assert r["path"] == []

    def test_with_tasks(self):
        d = ProjectDependencyResolver()
        d.add_task("t1", duration=3)
        d.add_task("t2", duration=5)
        d.add_task("t3", duration=2)
        d.add_dependency("t2", "t1")
        d.add_dependency("t3", "t2")
        r = d.find_critical_path()
        assert len(r["path"]) > 0
        assert r["duration"] > 0


class TestDependencyImpact:
    """Etki analizi testleri."""

    def test_impact(self):
        d = ProjectDependencyResolver()
        d.add_task("t1")
        d.add_task("t2")
        d.add_task("t3")
        d.add_dependency("t2", "t1")
        d.add_dependency("t3", "t1")
        r = d.analyze_impact("t1")
        assert r["total_impact"] >= 2

    def test_no_impact(self):
        d = ProjectDependencyResolver()
        d.add_task("t1")
        r = d.analyze_impact("t1")
        assert r["impact_level"] == "low"


class TestExecutionOrder:
    """Yürütme sırası testleri."""

    def test_order(self):
        d = ProjectDependencyResolver()
        d.add_task("t1")
        d.add_task("t2")
        d.add_dependency("t2", "t1")
        r = d.get_execution_order()
        assert r["count"] == 2


# ─── DeadlinePredictor ──────────────────


class TestPredictorInit:
    """DeadlinePredictor başlatma."""

    def test_init(self):
        p = DeadlinePredictor()
        assert p.prediction_count == 0

    def test_init_history(self):
        p = DeadlinePredictor()
        assert p.history_count == 0


class TestPredictCompletion:
    """Tamamlanma tahmini testleri."""

    def test_progress_based(self):
        p = DeadlinePredictor()
        r = p.predict_completion(
            "p1", progress=50,
            elapsed_days=10,
        )
        assert r["predicted"] is True
        assert r["remaining_days"] >= 0

    def test_velocity_based(self):
        p = DeadlinePredictor()
        r = p.predict_completion(
            "p1", progress=0,
            elapsed_days=5,
            remaining_tasks=20,
            velocity=4.0,
        )
        assert r["remaining_days"] == 5.0

    def test_no_data(self):
        p = DeadlinePredictor()
        r = p.predict_completion(
            "p1", progress=0,
            elapsed_days=0,
        )
        assert r["predicted"] is True


class TestRiskFactors:
    """Risk faktörleri testleri."""

    def test_no_risks(self):
        p = DeadlinePredictor()
        r = p.assess_risk_factors("p1")
        assert r["risk_level"] == "low"

    def test_multiple_risks(self):
        p = DeadlinePredictor()
        r = p.assess_risk_factors(
            "p1", {
                "scope_creep": True,
                "resource_shortage": True,
                "technical_debt": True,
            },
        )
        assert r["risk_level"] == "high"
        assert len(r["risks"]) == 3

    def test_single_risk(self):
        p = DeadlinePredictor()
        r = p.assess_risk_factors(
            "p1", {"scope_creep": True},
        )
        assert r["risk_level"] == "medium"


class TestHistorical:
    """Geçmiş analiz testleri."""

    def test_empty(self):
        p = DeadlinePredictor()
        r = p.analyze_historical()
        assert r["analyzed"] is False

    def test_with_data(self):
        p = DeadlinePredictor()
        p.add_historical("web", 30, 35)
        p.add_historical("web", 20, 18)
        r = p.analyze_historical()
        assert r["analyzed"] is True
        assert r["data_points"] == 2

    def test_add_historical(self):
        p = DeadlinePredictor()
        r = p.add_historical("web", 30, 35)
        assert r["added"] is True
        assert r["delay"] == 5.0

    def test_filter_type(self):
        p = DeadlinePredictor()
        p.add_historical("web", 30, 35)
        p.add_historical("mobile", 20, 25)
        r = p.analyze_historical("web")
        assert r["data_points"] == 1


class TestBuffer:
    """Tampon hesaplama testleri."""

    def test_medium_risk(self):
        p = DeadlinePredictor()
        r = p.calculate_buffer(100)
        assert r["buffer_days"] == 20.0

    def test_high_risk(self):
        p = DeadlinePredictor()
        r = p.calculate_buffer(
            100, risk_level="high",
        )
        assert r["buffer_days"] == 35.0

    def test_low_confidence(self):
        p = DeadlinePredictor()
        r = p.calculate_buffer(
            100, confidence=50.0,
        )
        assert r["buffer_days"] > 20

    def test_high_confidence(self):
        p = DeadlinePredictor()
        r = p.calculate_buffer(
            100, confidence=95.0,
        )
        assert r["buffer_days"] < 20


class TestConfidenceScore:
    """Güven puanlama testleri."""

    def test_low_progress(self):
        p = DeadlinePredictor()
        r = p.score_confidence(10)
        assert r["level"] == "low"

    def test_high_progress(self):
        p = DeadlinePredictor()
        r = p.score_confidence(
            100, data_points=5,
        )
        assert r["level"] == "high"

    def test_risk_penalty(self):
        p = DeadlinePredictor()
        r = p.score_confidence(
            50, risk_level="high",
        )
        assert (
            r["factors"]["risk_penalty"]
            == 15
        )


# ─── BlockerDetector ────────────────────


class TestBlockerInit:
    """BlockerDetector başlatma."""

    def test_init(self):
        b = BlockerDetector()
        assert b.blocker_count == 0

    def test_init_active(self):
        b = BlockerDetector()
        assert b.active_blocker_count == 0


class TestDetectBlocker:
    """Engel tespiti testleri."""

    def test_detect(self):
        b = BlockerDetector()
        r = b.detect_blocker(
            "p1", "API down",
        )
        assert r["detected"] is True

    def test_with_tasks(self):
        b = BlockerDetector()
        r = b.detect_blocker(
            "p1", "Bug",
            affected_tasks=["t1", "t2"],
        )
        assert r["affected_count"] == 2

    def test_severity(self):
        b = BlockerDetector()
        r = b.detect_blocker(
            "p1", "Critical bug",
            severity="critical",
        )
        assert r["severity"] == "critical"

    def test_increments(self):
        b = BlockerDetector()
        b.detect_blocker("p1", "A")
        b.detect_blocker("p1", "B")
        assert b.blocker_count == 2


class TestAssessImpact:
    """Etki değerlendirme testleri."""

    def test_assess(self):
        b = BlockerDetector()
        r = b.detect_blocker(
            "p1", "Bug",
            affected_tasks=["t1", "t2"],
            severity="high",
        )
        a = b.assess_impact(
            r["blocker_id"],
        )
        assert a["assessed"] is True
        assert a["impact_score"] > 0

    def test_not_found(self):
        b = BlockerDetector()
        a = b.assess_impact("xxx")
        assert a["assessed"] is False

    def test_critical_impact(self):
        b = BlockerDetector()
        r = b.detect_blocker(
            "p1", "Bug",
            affected_tasks=[
                "t1", "t2", "t3", "t4",
            ],
            severity="critical",
        )
        a = b.assess_impact(
            r["blocker_id"],
        )
        assert a["impact_level"] in (
            "high", "critical",
        )


class TestSuggestResolution:
    """Çözüm önerisi testleri."""

    def test_technical(self):
        b = BlockerDetector()
        r = b.detect_blocker(
            "p1", "Bug",
            category="technical",
        )
        s = b.suggest_resolution(
            r["blocker_id"],
        )
        assert s["count"] == 3
        assert s["category"] == "technical"

    def test_resource(self):
        b = BlockerDetector()
        r = b.detect_blocker(
            "p1", "Staff",
            category="resource",
        )
        s = b.suggest_resolution(
            r["blocker_id"],
        )
        assert s["count"] == 3

    def test_not_found(self):
        b = BlockerDetector()
        s = b.suggest_resolution("x")
        assert s["suggestions"] == []


class TestResolveBlocker:
    """Engel çözme testleri."""

    def test_resolve(self):
        b = BlockerDetector()
        r = b.detect_blocker("p1", "Bug")
        res = b.resolve_blocker(
            r["blocker_id"], "Fixed",
        )
        assert res["resolved"] is True
        assert b.resolved_count == 1

    def test_not_found(self):
        b = BlockerDetector()
        res = b.resolve_blocker("x")
        assert res["resolved"] is False


class TestEscalate:
    """Eskalasyon testleri."""

    def test_high_severity(self):
        b = BlockerDetector()
        r = b.detect_blocker(
            "p1", "Bug", severity="high",
        )
        e = b.should_escalate(
            r["blocker_id"],
        )
        assert e["escalate"] is True

    def test_low_severity(self):
        b = BlockerDetector()
        r = b.detect_blocker(
            "p1", "Bug", severity="low",
        )
        e = b.should_escalate(
            r["blocker_id"],
        )
        assert e["escalate"] is False

    def test_resolved(self):
        b = BlockerDetector()
        r = b.detect_blocker("p1", "Bug")
        b.resolve_blocker(
            r["blocker_id"],
        )
        e = b.should_escalate(
            r["blocker_id"],
        )
        assert e["escalate"] is False

    def test_not_found(self):
        b = BlockerDetector()
        e = b.should_escalate("x")
        assert e["escalate"] is False


class TestActiveBlockers:
    """Aktif engeller testleri."""

    def test_active(self):
        b = BlockerDetector()
        b.detect_blocker("p1", "A")
        b.detect_blocker("p1", "B")
        assert len(
            b.get_active_blockers(),
        ) == 2

    def test_filter_project(self):
        b = BlockerDetector()
        b.detect_blocker("p1", "A")
        b.detect_blocker("p2", "B")
        r = b.get_active_blockers("p1")
        assert len(r) == 1


# ─── ProjectProgressReporter ────────────


class TestReporterInit:
    """Reporter başlatma."""

    def test_init(self):
        r = ProjectProgressReporter()
        assert r.report_count == 0

    def test_init_updates(self):
        r = ProjectProgressReporter()
        assert r.update_count == 0


class TestStatusReport:
    """Durum raporu testleri."""

    def test_generate(self):
        r = ProjectProgressReporter()
        rpt = r.generate_status_report(
            "p1", 50, 5, 10,
        )
        assert rpt["generated"] is True

    def test_on_track(self):
        r = ProjectProgressReporter()
        rpt = r.generate_status_report(
            "p1", 80, 8, 10,
            health_score=90,
        )
        assert rpt["status"] == "on_track"

    def test_critical(self):
        r = ProjectProgressReporter()
        rpt = r.generate_status_report(
            "p1", 20, 2, 10,
            health_score=30,
        )
        assert rpt["status"] == "critical"


class TestBurndown:
    """Burndown testleri."""

    def test_create(self):
        r = ProjectProgressReporter()
        b = r.create_burndown(
            "p1", 100, [10, 15, 12],
        )
        assert b["completed"] == 37
        assert len(b["remaining"]) == 3

    def test_on_track(self):
        r = ProjectProgressReporter()
        b = r.create_burndown(
            "p1", 100,
            [8, 8, 8, 8, 8],
            sprint_days=14,
        )
        assert b["on_track"] is True

    def test_behind(self):
        r = ProjectProgressReporter()
        b = r.create_burndown(
            "p1", 100, [2, 1, 1],
            sprint_days=14,
        )
        assert b["on_track"] is False


class TestVelocity:
    """Hız takibi testleri."""

    def test_track(self):
        r = ProjectProgressReporter()
        v = r.track_velocity("p1", 30)
        assert v["current_velocity"] > 0

    def test_trend_improving(self):
        r = ProjectProgressReporter()
        r.track_velocity("p1", 20)
        v = r.track_velocity("p1", 30)
        assert v["trend"] == "improving"

    def test_trend_declining(self):
        r = ProjectProgressReporter()
        r.track_velocity("p1", 30)
        v = r.track_velocity("p1", 20)
        assert v["trend"] == "declining"


class TestStakeholderUpdate:
    """Paydaş güncelleme testleri."""

    def test_send(self):
        r = ProjectProgressReporter()
        u = r.send_stakeholder_update(
            "p1", ["alice", "bob"],
            summary="All good",
        )
        assert u["sent"] is True
        assert u["recipients_count"] == 2

    def test_with_highlights(self):
        r = ProjectProgressReporter()
        u = r.send_stakeholder_update(
            "p1", ["alice"],
            highlights=["A", "B"],
        )
        assert u["highlights_count"] == 2


class TestFormatReport:
    """Rapor formatlama testleri."""

    def test_summary(self):
        r = ProjectProgressReporter()
        f = r.format_report(
            {"project_id": "p1"},
        )
        assert f["formatted"] is True

    def test_detailed(self):
        r = ProjectProgressReporter()
        f = r.format_report(
            {"project_id": "p1"},
            format_type="detailed",
        )
        assert f["section_count"] == 5

    def test_executive(self):
        r = ProjectProgressReporter()
        f = r.format_report(
            {"project_id": "p1"},
            format_type="executive",
        )
        assert f["section_count"] == 3


class TestReporterQuery:
    """Sorgu testleri."""

    def test_get_reports(self):
        r = ProjectProgressReporter()
        r.generate_status_report(
            "p1", 50, 5, 10,
        )
        r.generate_status_report(
            "p2", 30, 3, 10,
        )
        assert len(r.get_reports()) == 2

    def test_filter_project(self):
        r = ProjectProgressReporter()
        r.generate_status_report(
            "p1", 50, 5, 10,
        )
        r.generate_status_report(
            "p2", 30, 3, 10,
        )
        assert len(r.get_reports("p1")) == 1


# ─── AutoEscalator ──────────────────────


class TestEscalatorInit:
    """AutoEscalator başlatma."""

    def test_init(self):
        e = AutoEscalator()
        assert e.rule_count == 0

    def test_init_escalations(self):
        e = AutoEscalator()
        assert e.escalation_count == 0


class TestCreateRule:
    """Kural oluşturma testleri."""

    def test_create(self):
        e = AutoEscalator()
        r = e.create_rule(
            "Late", "deadline_missed",
        )
        assert r["created"] is True

    def test_with_notify(self):
        e = AutoEscalator()
        r = e.create_rule(
            "Late", "deadline_missed",
            notify=["manager"],
        )
        assert r["severity"] == "medium"

    def test_increments(self):
        e = AutoEscalator()
        e.create_rule("R1", "c1")
        e.create_rule("R2", "c2")
        assert e.rule_count == 2


class TestDetectTrigger:
    """Tetik algılama testleri."""

    def test_trigger_match(self):
        e = AutoEscalator()
        e.create_rule(
            "Late", "deadline_missed",
        )
        r = e.detect_trigger(
            "p1", "deadline_missed",
        )
        assert r["triggered"] is True

    def test_no_match(self):
        e = AutoEscalator()
        e.create_rule(
            "Late", "deadline_missed",
        )
        r = e.detect_trigger(
            "p1", "task_complete",
        )
        assert r["triggered"] is False

    def test_partial_match(self):
        e = AutoEscalator()
        e.create_rule(
            "Block", "blocker_detected",
        )
        r = e.detect_trigger(
            "p1", "blocker",
        )
        assert r["triggered"] is True


class TestRouteNotification:
    """Bildirim yönlendirme testleri."""

    def test_route(self):
        e = AutoEscalator()
        e.create_rule("R", "event")
        t = e.detect_trigger("p1", "event")
        eid = t["escalation_id"]
        r = e.route_notification(
            eid, ["manager"],
        )
        assert r["routed"] is True

    def test_not_found(self):
        e = AutoEscalator()
        r = e.route_notification("x", [])
        assert r["routed"] is False


class TestTrackFollowup:
    """Takip testleri."""

    def test_track(self):
        e = AutoEscalator()
        e.create_rule("R", "event")
        t = e.detect_trigger("p1", "event")
        eid = t["escalation_id"]
        f = e.track_followup(
            eid, "Investigate",
            assignee="alice",
        )
        assert f["tracked"] is True

    def test_due_hours(self):
        e = AutoEscalator()
        f = e.track_followup(
            "e1", "Fix", due_hours=48,
        )
        assert f["due_hours"] == 48


class TestVerifyResolution:
    """Çözüm doğrulama testleri."""

    def test_verify(self):
        e = AutoEscalator()
        e.create_rule("R", "event")
        t = e.detect_trigger("p1", "event")
        eid = t["escalation_id"]
        v = e.verify_resolution(
            eid, "Fixed", "bob",
        )
        assert v["verified"] is True

    def test_not_found(self):
        e = AutoEscalator()
        v = e.verify_resolution("x")
        assert v["verified"] is False


class TestActiveEscalations:
    """Aktif eskalasyon testleri."""

    def test_active(self):
        e = AutoEscalator()
        e.create_rule("R", "event")
        e.detect_trigger("p1", "event")
        e.detect_trigger("p1", "event")
        assert len(
            e.get_active_escalations(),
        ) == 2

    def test_filter_project(self):
        e = AutoEscalator()
        e.create_rule("R", "event")
        e.detect_trigger("p1", "event")
        e.detect_trigger("p2", "event")
        r = e.get_active_escalations("p1")
        assert len(r) == 1


# ─── ProjectResourceBalancer ────────────


class TestBalancerInit:
    """ResourceBalancer başlatma."""

    def test_init(self):
        b = ProjectResourceBalancer()
        assert b.analysis_count == 0

    def test_init_realloc(self):
        b = ProjectResourceBalancer()
        assert b.reallocation_count == 0


class TestWorkloadAnalysis:
    """İş yükü analizi testleri."""

    def test_balanced(self):
        b = ProjectResourceBalancer()
        r = b.analyze_workload([
            {"name": "alice", "tasks": 8,
             "capacity": 10},
            {"name": "bob", "tasks": 7,
             "capacity": 10},
        ])
        assert r["balanced"] is True

    def test_overloaded(self):
        b = ProjectResourceBalancer()
        r = b.analyze_workload([
            {"name": "alice", "tasks": 15,
             "capacity": 10},
        ])
        assert r["balanced"] is False
        assert "alice" in r["overloaded"]

    def test_empty(self):
        b = ProjectResourceBalancer()
        r = b.analyze_workload([])
        assert r["analyzed"] is False

    def test_underloaded(self):
        b = ProjectResourceBalancer()
        r = b.analyze_workload([
            {"name": "bob", "tasks": 2,
             "capacity": 10},
        ])
        assert "bob" in r["underloaded"]


class TestReallocation:
    """Yeniden tahsis testleri."""

    def test_suggest(self):
        b = ProjectResourceBalancer()
        r = b.suggest_reallocation(
            "alice", "bob", 3,
        )
        assert r["suggested"] is True
        assert r["task_count"] == 3

    def test_increments(self):
        b = ProjectResourceBalancer()
        b.suggest_reallocation("a", "b")
        b.suggest_reallocation("c", "d")
        assert b.reallocation_count == 2


class TestConflictResolution:
    """Çatışma çözümü testleri."""

    def test_priority(self):
        b = ProjectResourceBalancer()
        r = b.resolve_conflict(
            "dev1", ["p1", "p2"],
        )
        assert r["resolved"] is True
        assert r["winner"] == "p1"

    def test_split(self):
        b = ProjectResourceBalancer()
        r = b.resolve_conflict(
            "dev1", ["p1", "p2"],
            strategy="split",
        )
        assert r["winner"] == "shared"

    def test_no_conflict(self):
        b = ProjectResourceBalancer()
        r = b.resolve_conflict(
            "dev1", ["p1"],
        )
        assert r["conflict"] is False


class TestCapacityPlanning:
    """Kapasite planlama testleri."""

    def test_sufficient(self):
        b = ProjectResourceBalancer()
        r = b.plan_capacity(
            5, 30, avg_capacity=10,
        )
        assert r["sufficient"] is True

    def test_insufficient(self):
        b = ProjectResourceBalancer()
        r = b.plan_capacity(
            2, 50, avg_capacity=10,
        )
        assert r["sufficient"] is False
        assert r["gap"] > 0

    def test_buffer(self):
        b = ProjectResourceBalancer()
        r = b.plan_capacity(
            5, 40, buffer_percent=20,
        )
        assert (
            r["effective_capacity"]
            < r["total_capacity"]
        )


class TestOptimize:
    """Optimizasyon testleri."""

    def test_optimize(self):
        b = ProjectResourceBalancer()
        r = b.optimize("p1", [
            {"name": "r1", "cost": 100,
             "capacity": 50,
             "utilization": 20},
            {"name": "r2", "cost": 80,
             "capacity": 40,
             "utilization": 95},
        ])
        assert r["optimized"] is True
        assert r["suggestion_count"] == 2

    def test_empty(self):
        b = ProjectResourceBalancer()
        r = b.optimize("p1")
        assert r["optimized"] is True
        assert r["resources_count"] == 0


# ─── ProjectMgrOrchestrator ─────────────


class TestOrchestratorInit:
    """Orchestrator başlatma."""

    def test_init(self):
        o = ProjectMgrOrchestrator()
        assert o.project_count == 0

    def test_init_cycles(self):
        o = ProjectMgrOrchestrator()
        assert o.cycle_count == 0

    def test_has_components(self):
        o = ProjectMgrOrchestrator()
        assert o.tracker is not None
        assert o.milestones is not None
        assert o.dependencies is not None
        assert o.predictor is not None
        assert o.blockers is not None
        assert o.reporter is not None
        assert o.escalator is not None
        assert o.balancer is not None


class TestManageProject:
    """Proje yönetimi testleri."""

    def test_manage(self):
        o = ProjectMgrOrchestrator()
        r = o.manage_project("Test")
        assert r["managed"] is True

    def test_with_team(self):
        o = ProjectMgrOrchestrator()
        r = o.manage_project(
            "Test",
            team=["alice", "bob"],
        )
        assert r["team_size"] == 2

    def test_increments(self):
        o = ProjectMgrOrchestrator()
        o.manage_project("P1")
        o.manage_project("P2")
        assert o.project_count == 2


class TestProjectCycle:
    """Proje döngüsü testleri."""

    def test_cycle(self):
        o = ProjectMgrOrchestrator()
        r = o.manage_project("Test")
        pid = r["project_id"]
        c = o.run_project_cycle(
            pid, progress=50,
            tasks_done=5,
            tasks_total=10,
            elapsed_days=10,
        )
        assert c["cycle_complete"] is True

    def test_cycle_healthy(self):
        o = ProjectMgrOrchestrator()
        r = o.manage_project("Test")
        pid = r["project_id"]
        c = o.run_project_cycle(
            pid, progress=80,
            tasks_done=8,
            tasks_total=10,
            elapsed_days=5,
        )
        assert c["health"] == "healthy"

    def test_cycle_increments(self):
        o = ProjectMgrOrchestrator()
        r = o.manage_project("Test")
        pid = r["project_id"]
        o.run_project_cycle(
            pid, progress=50,
            tasks_done=5,
            tasks_total=10,
            elapsed_days=10,
        )
        assert o.cycle_count == 1


class TestMultiProjectStatus:
    """Çoklu proje testleri."""

    def test_empty(self):
        o = ProjectMgrOrchestrator()
        r = o.get_multi_project_status()
        assert r["total_projects"] == 0

    def test_multiple(self):
        o = ProjectMgrOrchestrator()
        o.manage_project("P1")
        o.manage_project("P2")
        r = o.get_multi_project_status()
        assert r["total_projects"] == 2


class TestOrchestratorAnalytics:
    """Analitik testleri."""

    def test_analytics(self):
        o = ProjectMgrOrchestrator()
        o.manage_project("Test")
        a = o.get_analytics()
        assert a["projects_managed"] == 1
        assert a["total_milestones"] >= 1

    def test_analytics_empty(self):
        o = ProjectMgrOrchestrator()
        a = o.get_analytics()
        assert a["projects_managed"] == 0
