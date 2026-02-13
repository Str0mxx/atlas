"""ATLAS Self-Evolution sistemi testleri.

PerformanceMonitor, WeaknessDetector, ImprovementPlanner,
CodeEvolver, SafetyGuardian, ExperimentRunner,
ApprovalManager, KnowledgeLearner, EvolutionController testleri.
"""

from app.core.evolution.approval_manager import ApprovalManager
from app.core.evolution.code_evolver import CodeEvolver
from app.core.evolution.evolution_controller import EvolutionController
from app.core.evolution.experiment_runner import ExperimentRunner
from app.core.evolution.improvement_planner import ImprovementPlanner
from app.core.evolution.knowledge_learner import KnowledgeLearner
from app.core.evolution.performance_monitor import PerformanceMonitor
from app.core.evolution.safety_guardian import SafetyGuardian
from app.core.evolution.weakness_detector import WeaknessDetector
from app.models.evolution import (
    ApprovalRequest,
    ApprovalStatus,
    ChangeSeverity,
    CodeChange,
    EvolutionCycle,
    EvolutionCycleType,
    EvolutionPhase,
    ExperimentResult,
    ExperimentStatus,
    ImprovementPlan,
    ImprovementType,
    LearnedPattern,
    PerformanceMetric,
    SafetyCheckResult,
    TrendDirection,
    WeaknessReport,
    WeaknessType,
)


# === Helper fonksiyonlar ===


def _make_metric(
    agent: str = "test_agent",
    task: str = "test_task",
    success: int = 8,
    failure: int = 2,
    avg_ms: float = 100.0,
) -> PerformanceMetric:
    """Test metrigi olusturur."""
    total = success + failure
    return PerformanceMetric(
        agent_name=agent,
        task_type=task,
        success_count=success,
        failure_count=failure,
        total_count=total,
        avg_response_ms=avg_ms,
        error_rate=failure / total if total > 0 else 0.0,
    )


def _make_weakness(
    wtype: WeaknessType = WeaknessType.FAILURE,
    component: str = "test_comp",
    severity: ChangeSeverity = ChangeSeverity.MINOR,
    impact: float = 5.0,
) -> WeaknessReport:
    """Test zayiflik raporu olusturur."""
    return WeaknessReport(
        weakness_type=wtype,
        component=component,
        description=f"Test zayiflik: {component}",
        severity=severity,
        impact_score=impact,
    )


def _make_change(
    path: str = "app/core/test.py",
    change_type: str = "fix",
    diff: str = "+# FIX: test",
    severity: ChangeSeverity = ChangeSeverity.MINOR,
) -> CodeChange:
    """Test kod degisikligi olusturur."""
    return CodeChange(
        file_path=path,
        change_type=change_type,
        diff=diff,
        description=f"Test degisiklik: {path}",
        severity=severity,
    )


def _make_plan(
    title: str = "Test plan",
    component: str = "test_comp",
    imp_type: ImprovementType = ImprovementType.BUG_FIX,
    impact: float = 5.0,
    effort: float = 10.0,
    risk: ChangeSeverity = ChangeSeverity.MINOR,
) -> ImprovementPlan:
    """Test iyilestirme plani olusturur."""
    return ImprovementPlan(
        title=title,
        improvement_type=imp_type,
        target_component=component,
        description=f"Test: {title}",
        expected_impact=impact,
        estimated_effort=effort,
        risk_level=risk,
        steps=["Adim 1", "Adim 2"],
    )


def _make_experiment(
    name: str = "test_exp",
    status: ExperimentStatus = ExperimentStatus.PASSED,
    improvement: float = 10.0,
    confidence: float = 0.95,
) -> ExperimentResult:
    """Test deney sonucu olusturur."""
    return ExperimentResult(
        experiment_name=name,
        status=status,
        baseline_score=1.0,
        variant_score=1.1,
        improvement_pct=improvement,
        confidence=confidence,
    )


# === Model Testleri ===


class TestEvolutionModels:
    """Evolution model testleri."""

    def test_performance_metric_defaults(self) -> None:
        """PerformanceMetric varsayilan degerler."""
        m = PerformanceMetric()
        assert m.agent_name == ""
        assert m.success_count == 0
        assert m.error_rate == 0.0
        assert m.trend == TrendDirection.STABLE

    def test_weakness_report_defaults(self) -> None:
        """WeaknessReport varsayilan degerler."""
        w = WeaknessReport()
        assert w.weakness_type == WeaknessType.FAILURE
        assert w.severity == ChangeSeverity.MINOR
        assert w.frequency == 1
        assert w.examples == []

    def test_improvement_plan_defaults(self) -> None:
        """ImprovementPlan varsayilan degerler."""
        p = ImprovementPlan()
        assert p.improvement_type == ImprovementType.BUG_FIX
        assert p.risk_level == ChangeSeverity.MINOR
        assert p.dependencies == []
        assert p.steps == []

    def test_code_change_defaults(self) -> None:
        """CodeChange varsayilan degerler."""
        c = CodeChange()
        assert c.file_path == ""
        assert c.version == 1
        assert c.severity == ChangeSeverity.MINOR

    def test_safety_check_result_defaults(self) -> None:
        """SafetyCheckResult varsayilan degerler."""
        s = SafetyCheckResult()
        assert s.is_safe is True
        assert s.requires_approval is False
        assert s.issues == []

    def test_experiment_result_defaults(self) -> None:
        """ExperimentResult varsayilan degerler."""
        e = ExperimentResult()
        assert e.status == ExperimentStatus.PENDING
        assert e.improvement_pct == 0.0
        assert e.confidence == 0.0

    def test_approval_request_defaults(self) -> None:
        """ApprovalRequest varsayilan degerler."""
        a = ApprovalRequest()
        assert a.status == ApprovalStatus.PENDING
        assert a.severity == ChangeSeverity.MAJOR
        assert a.timeout_hours == 24

    def test_learned_pattern_defaults(self) -> None:
        """LearnedPattern varsayilan degerler."""
        l = LearnedPattern()
        assert l.pattern_name == ""
        assert l.success_count == 0
        assert l.source_components == []

    def test_evolution_cycle_defaults(self) -> None:
        """EvolutionCycle varsayilan degerler."""
        c = EvolutionCycle()
        assert c.cycle_type == EvolutionCycleType.DAILY
        assert c.phase == EvolutionPhase.OBSERVING
        assert c.paused is False

    def test_change_severity_values(self) -> None:
        """ChangeSeverity enum degerleri."""
        assert ChangeSeverity.MINOR.value == "minor"
        assert ChangeSeverity.MAJOR.value == "major"
        assert ChangeSeverity.CRITICAL.value == "critical"

    def test_evolution_phase_values(self) -> None:
        """EvolutionPhase enum degerleri."""
        assert EvolutionPhase.OBSERVING.value == "observing"
        assert EvolutionPhase.COMPLETE.value == "complete"
        assert EvolutionPhase.PAUSED.value == "paused"

    def test_weakness_type_values(self) -> None:
        """WeaknessType enum degerleri."""
        assert len(WeaknessType) == 6
        assert WeaknessType.FAILURE.value == "failure"
        assert WeaknessType.RESOURCE_WASTE.value == "resource_waste"

    def test_improvement_type_values(self) -> None:
        """ImprovementType enum degerleri."""
        assert len(ImprovementType) == 6
        assert ImprovementType.BUG_FIX.value == "bug_fix"
        assert ImprovementType.DOCUMENTATION.value == "documentation"

    def test_trend_direction_values(self) -> None:
        """TrendDirection enum degerleri."""
        assert len(TrendDirection) == 4
        assert TrendDirection.IMPROVING.value == "improving"
        assert TrendDirection.VOLATILE.value == "volatile"

    def test_metric_with_custom_values(self) -> None:
        """PerformanceMetric ozel degerlerle."""
        m = _make_metric(agent="coding", task="review", success=90, failure=10)
        assert m.agent_name == "coding"
        assert m.total_count == 100
        assert m.error_rate == 0.1

    def test_weakness_with_examples(self) -> None:
        """WeaknessReport orneklerle."""
        w = WeaknessReport(examples=["hata1", "hata2"])
        assert len(w.examples) == 2

    def test_plan_with_steps(self) -> None:
        """ImprovementPlan adimlarla."""
        p = ImprovementPlan(steps=["a", "b", "c"])
        assert len(p.steps) == 3

    def test_experiment_status_values(self) -> None:
        """ExperimentStatus enum degerleri."""
        assert len(ExperimentStatus) == 5
        assert ExperimentStatus.RUNNING.value == "running"

    def test_approval_status_values(self) -> None:
        """ApprovalStatus enum degerleri."""
        assert len(ApprovalStatus) == 5
        assert ApprovalStatus.AUTO_APPROVED.value == "auto_approved"


# === PerformanceMonitor Testleri ===


class TestPerformanceMonitor:
    """PerformanceMonitor testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        pm = PerformanceMonitor()
        assert pm.metric_count == 0
        assert pm.total_errors == 0

    def test_record_success(self) -> None:
        """Basari kaydi."""
        pm = PerformanceMonitor()
        pm.record_success("agent1", "task1", 150.0)
        m = pm.get_metric("agent1", "task1")
        assert m is not None
        assert m.success_count == 1
        assert m.total_count == 1

    def test_record_failure(self) -> None:
        """Basarisizlik kaydi."""
        pm = PerformanceMonitor()
        pm.record_failure("agent1", "task1", "connection error", 200.0)
        m = pm.get_metric("agent1", "task1")
        assert m is not None
        assert m.failure_count == 1
        assert pm.total_errors == 1

    def test_success_rate(self) -> None:
        """Basari orani hesabi."""
        pm = PerformanceMonitor()
        for _ in range(8):
            pm.record_success("a1", "t1", 100.0)
        for _ in range(2):
            pm.record_failure("a1", "t1", "err")
        rate = pm.get_success_rate("a1", "t1")
        assert rate == 0.8

    def test_success_rate_agent_level(self) -> None:
        """Agent bazinda basari orani."""
        pm = PerformanceMonitor()
        pm.record_success("a1", "t1", 100.0)
        pm.record_success("a1", "t2", 100.0)
        pm.record_failure("a1", "t2", "err")
        rate = pm.get_success_rate("a1")
        assert abs(rate - 2.0 / 3.0) < 0.01

    def test_avg_response_time(self) -> None:
        """Ortalama yanit suresi."""
        pm = PerformanceMonitor()
        pm.record_success("a1", "t1", 100.0)
        pm.record_success("a1", "t1", 200.0)
        avg = pm.get_avg_response_time("a1", "t1")
        assert avg == 150.0

    def test_error_patterns(self) -> None:
        """Hata kalip tespiti."""
        pm = PerformanceMonitor()
        for _ in range(5):
            pm.record_failure("a1", "t1", "connection timeout occurred")
        patterns = pm.detect_error_patterns(min_count=3)
        assert len(patterns) >= 1
        assert patterns[0]["count"] >= 5

    def test_resource_usage(self) -> None:
        """Kaynak kullanimi kaydi."""
        pm = PerformanceMonitor()
        pm.record_resource_usage(50.0, 256.0, 10.0)
        pm.record_resource_usage(60.0, 300.0, 15.0)
        trend = pm.get_resource_trend()
        assert trend["cpu_pct"] == 55.0
        assert trend["memory_mb"] == 278.0

    def test_trend_stable(self) -> None:
        """Stabil trend."""
        pm = PerformanceMonitor()
        for _ in range(10):
            pm.record_success("a1", "t1", 100.0)
        trend = pm.analyze_trend("a1", "t1")
        assert trend == TrendDirection.STABLE

    def test_trend_improving(self) -> None:
        """Iyilesen trend."""
        pm = PerformanceMonitor()
        for i in range(10):
            pm.record_success("a1", "t1", 200.0 - i * 15)
        trend = pm.analyze_trend("a1", "t1")
        assert trend == TrendDirection.IMPROVING

    def test_trend_declining(self) -> None:
        """Kotulesen trend."""
        pm = PerformanceMonitor()
        for i in range(10):
            pm.record_success("a1", "t1", 100.0 + i * 15)
        trend = pm.analyze_trend("a1", "t1")
        assert trend == TrendDirection.DECLINING

    def test_trend_insufficient_data(self) -> None:
        """Yetersiz veri ile trend."""
        pm = PerformanceMonitor()
        pm.record_success("a1", "t1", 100.0)
        trend = pm.analyze_trend("a1", "t1")
        assert trend == TrendDirection.STABLE

    def test_worst_performers(self) -> None:
        """En kotu performanslilar."""
        pm = PerformanceMonitor()
        pm.record_success("good", "t1", 50.0)
        for _ in range(5):
            pm.record_failure("bad", "t1", "err")
        worst = pm.get_worst_performers(top_k=1)
        assert len(worst) == 1
        assert worst[0].agent_name == "bad"

    def test_get_all_metrics(self) -> None:
        """Tum metrikler."""
        pm = PerformanceMonitor()
        pm.record_success("a1", "t1", 100.0)
        pm.record_success("a2", "t2", 200.0)
        assert len(pm.get_all_metrics()) == 2

    def test_snapshot(self) -> None:
        """Snapshot alma."""
        pm = PerformanceMonitor()
        pm.record_success("a1", "t1", 100.0)
        pm.snapshot()
        assert len(pm.history) == 1

    def test_p95_calculation(self) -> None:
        """P95 hesabi."""
        pm = PerformanceMonitor()
        for i in range(20):
            pm.record_success("a1", "t1", float(i * 10))
        m = pm.get_metric("a1", "t1")
        assert m is not None
        assert m.p95_response_ms > 0

    def test_empty_success_rate(self) -> None:
        """Bos metrik basari orani."""
        pm = PerformanceMonitor()
        assert pm.get_success_rate("nonexistent") == 0.0

    def test_empty_response_time(self) -> None:
        """Bos metrik yanit suresi."""
        pm = PerformanceMonitor()
        assert pm.get_avg_response_time("nonexistent") == 0.0

    def test_empty_resource_trend(self) -> None:
        """Bos kaynak trendi."""
        pm = PerformanceMonitor()
        trend = pm.get_resource_trend()
        assert trend["cpu_pct"] == 0.0


# === WeaknessDetector Testleri ===


class TestWeaknessDetector:
    """WeaknessDetector testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        wd = WeaknessDetector()
        assert wd.weakness_count == 0
        assert wd.complaint_count == 0

    def test_analyze_failures(self) -> None:
        """Basarisizlik analizi."""
        wd = WeaknessDetector(failure_rate_threshold=0.2)
        metrics = [_make_metric(success=5, failure=5)]  # %50 hata
        reports = wd.analyze_failures(metrics)
        assert len(reports) == 1
        assert reports[0].severity == ChangeSeverity.CRITICAL

    def test_no_failures_below_threshold(self) -> None:
        """Esik altinda basarisizlik yok."""
        wd = WeaknessDetector(failure_rate_threshold=0.3)
        metrics = [_make_metric(success=8, failure=2)]  # %20 hata
        reports = wd.analyze_failures(metrics)
        assert len(reports) == 0

    def test_detect_missing_capabilities(self) -> None:
        """Eksik yetenek tespiti."""
        wd = WeaknessDetector()
        tasks = [
            {"task_type": "voice_translate", "error": "not supported operation"},
            {"task_type": "voice_translate", "error": "not supported operation"},
        ]
        reports = wd.detect_missing_capabilities(tasks)
        assert len(reports) == 1
        assert reports[0].weakness_type == WeaknessType.MISSING_CAPABILITY

    def test_find_slow_operations(self) -> None:
        """Yavas islem tespiti."""
        wd = WeaknessDetector(slow_operation_ms=1000.0)
        metrics = [_make_metric(avg_ms=5000.0)]
        reports = wd.find_slow_operations(metrics)
        assert len(reports) == 1
        assert reports[0].weakness_type == WeaknessType.SLOW_OPERATION

    def test_find_error_hotspots(self) -> None:
        """Hata odagi tespiti."""
        wd = WeaknessDetector(error_hotspot_count=3)
        patterns = [{"pattern": "connection timeout", "count": 10}]
        reports = wd.find_error_hotspots(patterns)
        assert len(reports) == 1
        assert reports[0].weakness_type == WeaknessType.ERROR_HOTSPOT

    def test_record_complaint(self) -> None:
        """Sikayet kaydi."""
        wd = WeaknessDetector()
        report = wd.record_complaint("fatih", "Yavas calisiyorsun", "agent1")
        assert report.weakness_type == WeaknessType.USER_COMPLAINT
        assert wd.complaint_count == 1

    def test_complaint_patterns(self) -> None:
        """Sikayet kaliplari."""
        wd = WeaknessDetector()
        wd.record_complaint("u1", "yavas", "agent1")
        wd.record_complaint("u2", "yavas", "agent1")
        patterns = wd.analyze_complaint_patterns(min_count=2)
        assert len(patterns) == 1
        assert patterns[0]["component"] == "agent1"

    def test_run_full_analysis(self) -> None:
        """Tam analiz."""
        wd = WeaknessDetector(failure_rate_threshold=0.1)
        metrics = [_make_metric(success=5, failure=5, avg_ms=10000.0)]
        results = wd.run_full_analysis(metrics=metrics)
        assert len(results) >= 2  # failure + slow

    def test_get_all_weaknesses_filter(self) -> None:
        """Zayiflik filtreleme."""
        wd = WeaknessDetector()
        wd.record_complaint("u1", "minor issue", "comp1")
        all_w = wd.get_all_weaknesses(min_impact=0.0)
        assert len(all_w) >= 1

    def test_severity_classification(self) -> None:
        """Ciddiyet siniflandirmasi."""
        wd = WeaknessDetector(failure_rate_threshold=0.1)
        major_metric = _make_metric(success=6, failure=4)  # %40
        reports = wd.analyze_failures([major_metric])
        assert len(reports) == 1
        assert reports[0].severity == ChangeSeverity.MAJOR

    def test_empty_metrics(self) -> None:
        """Bos metrikler."""
        wd = WeaknessDetector()
        assert wd.analyze_failures([]) == []

    def test_zero_total_metric(self) -> None:
        """Sifir toplam metrik."""
        wd = WeaknessDetector()
        m = PerformanceMetric(total_count=0)
        assert wd.analyze_failures([m]) == []


# === ImprovementPlanner Testleri ===


class TestImprovementPlanner:
    """ImprovementPlanner testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        ip = ImprovementPlanner()
        assert ip.plan_count == 0

    def test_create_plan_from_failure(self) -> None:
        """Basarisizliktan plan."""
        ip = ImprovementPlanner()
        w = _make_weakness(wtype=WeaknessType.FAILURE)
        plan = ip.create_plan(w)
        assert plan.improvement_type == ImprovementType.BUG_FIX
        assert len(plan.steps) > 0

    def test_create_plan_from_slow(self) -> None:
        """Yavas islemden plan."""
        ip = ImprovementPlanner()
        w = _make_weakness(wtype=WeaknessType.SLOW_OPERATION)
        plan = ip.create_plan(w)
        assert plan.improvement_type == ImprovementType.PERFORMANCE

    def test_create_plan_from_missing(self) -> None:
        """Eksik yetenekten plan."""
        ip = ImprovementPlanner()
        w = _make_weakness(wtype=WeaknessType.MISSING_CAPABILITY)
        plan = ip.create_plan(w)
        assert plan.improvement_type == ImprovementType.NEW_CAPABILITY

    def test_prioritize(self) -> None:
        """Onceliklendirme."""
        ip = ImprovementPlanner()
        w1 = _make_weakness(impact=2.0)
        w2 = _make_weakness(impact=8.0)
        ip.create_plan(w1)
        ip.create_plan(w2)
        prioritized = ip.prioritize()
        assert prioritized[0].expected_impact >= prioritized[1].expected_impact

    def test_create_plans_from_weaknesses(self) -> None:
        """Toplu plan olusturma."""
        ip = ImprovementPlanner()
        weaknesses = [_make_weakness(impact=3.0), _make_weakness(impact=7.0)]
        plans = ip.create_plans_from_weaknesses(weaknesses)
        assert len(plans) == 2
        assert plans[0].priority_score >= plans[1].priority_score

    def test_get_plan(self) -> None:
        """Plan getirme."""
        ip = ImprovementPlanner()
        w = _make_weakness()
        plan = ip.create_plan(w)
        found = ip.get_plan(plan.id)
        assert found is not None
        assert found.id == plan.id

    def test_get_plan_not_found(self) -> None:
        """Olmayan plan."""
        ip = ImprovementPlanner()
        assert ip.get_plan("nonexistent") is None

    def test_get_top_plans(self) -> None:
        """En iyi planlar."""
        ip = ImprovementPlanner()
        for i in range(10):
            ip.create_plan(_make_weakness(impact=float(i)))
        top = ip.get_top_plans(count=3)
        assert len(top) == 3

    def test_add_dependency(self) -> None:
        """Bagimlilik ekleme."""
        ip = ImprovementPlanner()
        ip.add_dependency("comp_a", "comp_b")
        w = _make_weakness(component="comp_a")
        plan = ip.create_plan(w)
        assert "comp_b" in plan.dependencies

    def test_effort_estimation_minor(self) -> None:
        """Minor efor tahmini."""
        ip = ImprovementPlanner()
        w = _make_weakness(severity=ChangeSeverity.MINOR)
        plan = ip.create_plan(w)
        assert plan.estimated_effort < 20.0

    def test_effort_estimation_critical(self) -> None:
        """Critical efor tahmini."""
        ip = ImprovementPlanner()
        w = _make_weakness(severity=ChangeSeverity.CRITICAL)
        plan = ip.create_plan(w)
        assert plan.estimated_effort > 10.0

    def test_risk_assessment_new_capability(self) -> None:
        """Yeni yetenek risk degerlendirmesi."""
        ip = ImprovementPlanner()
        w = _make_weakness(wtype=WeaknessType.MISSING_CAPABILITY)
        plan = ip.create_plan(w)
        assert plan.risk_level == ChangeSeverity.MAJOR

    def test_config_improvement_steps(self) -> None:
        """Konfigurasyon iyilestirme adimlari."""
        ip = ImprovementPlanner()
        w = _make_weakness(wtype=WeaknessType.RESOURCE_WASTE)
        plan = ip.create_plan(w)
        assert len(plan.steps) > 0

    def test_plans_property(self) -> None:
        """Plans property."""
        ip = ImprovementPlanner()
        ip.create_plan(_make_weakness())
        assert len(ip.plans) == 1


# === CodeEvolver Testleri ===


class TestCodeEvolver:
    """CodeEvolver testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        ce = CodeEvolver()
        assert ce.change_count == 0
        assert ce.pending_rollbacks == 0

    def test_generate_change(self) -> None:
        """Degisiklik uretimi."""
        ce = CodeEvolver()
        plan = _make_plan()
        change = ce.generate_change(plan)
        assert change.file_path != ""
        assert change.version == 1
        assert change.diff != ""

    def test_generate_changes(self) -> None:
        """Toplu degisiklik uretimi."""
        ce = CodeEvolver()
        plans = [_make_plan(title="plan1"), _make_plan(title="plan2")]
        changes = ce.generate_changes(plans)
        assert len(changes) == 2

    def test_version_increment(self) -> None:
        """Versiyon artisi."""
        ce = CodeEvolver()
        plan = _make_plan(component="comp1")
        c1 = ce.generate_change(plan)
        c2 = ce.generate_change(plan)
        assert c2.version == c1.version + 1

    def test_apply_change(self) -> None:
        """Degisiklik uygulama."""
        ce = CodeEvolver()
        change = _make_change()
        result = ce.apply_change(change)
        assert result is True
        assert ce.pending_rollbacks == 1

    def test_rollback_change(self) -> None:
        """Degisiklik geri alma."""
        ce = CodeEvolver()
        change = _make_change()
        ce.apply_change(change)
        result = ce.rollback_change(change)
        assert result is True
        assert ce.pending_rollbacks == 0

    def test_rollback_not_applied(self) -> None:
        """Uygulanmamis geri alma."""
        ce = CodeEvolver()
        change = _make_change()
        result = ce.rollback_change(change)
        assert result is False

    def test_rollback_all(self) -> None:
        """Toplu geri alma."""
        ce = CodeEvolver()
        for _ in range(3):
            ce.apply_change(_make_change())
        count = ce.rollback_all()
        assert count == 3
        assert ce.pending_rollbacks == 0

    def test_get_change(self) -> None:
        """Degisiklik getirme."""
        ce = CodeEvolver()
        plan = _make_plan()
        change = ce.generate_change(plan)
        found = ce.get_change(change.id)
        assert found is not None
        assert found.id == change.id

    def test_get_change_not_found(self) -> None:
        """Olmayan degisiklik."""
        ce = CodeEvolver()
        assert ce.get_change("nonexistent") is None

    def test_diff_summary(self) -> None:
        """Diff ozeti."""
        ce = CodeEvolver()
        change = _make_change(diff="+line1\n+line2\n-old_line")
        summary = ce.get_diff_summary(change)
        assert summary["additions"] == 2
        assert summary["deletions"] == 1

    def test_resolve_file_path_with_colon(self) -> None:
        """Dosya yolu cozumleme (iki noktali)."""
        ce = CodeEvolver()
        plan = _make_plan(component="agents:coding")
        change = ce.generate_change(plan)
        assert "agents/coding" in change.file_path

    def test_get_version(self) -> None:
        """Versiyon sorgulama."""
        ce = CodeEvolver()
        assert ce.get_version("nonexistent") == 0

    def test_changes_property(self) -> None:
        """Changes property."""
        ce = CodeEvolver()
        ce.generate_change(_make_plan())
        assert len(ce.changes) == 1

    def test_fix_change_type(self) -> None:
        """Fix degisiklik tipi."""
        ce = CodeEvolver()
        plan = _make_plan(imp_type=ImprovementType.BUG_FIX)
        change = ce.generate_change(plan)
        assert change.change_type == "fix"

    def test_optimize_change_type(self) -> None:
        """Optimize degisiklik tipi."""
        ce = CodeEvolver()
        plan = _make_plan(imp_type=ImprovementType.PERFORMANCE)
        change = ce.generate_change(plan)
        assert change.change_type == "optimize"


# === SafetyGuardian Testleri ===


class TestSafetyGuardian:
    """SafetyGuardian testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        sg = SafetyGuardian()
        assert sg.result_count == 0

    def test_classify_minor(self) -> None:
        """Minor siniflandirma."""
        sg = SafetyGuardian()
        change = _make_change(diff="+x = 1", change_type="config")
        severity = sg.classify_severity(change)
        assert severity == ChangeSeverity.MINOR

    def test_classify_major_by_size(self) -> None:
        """Buyukluge gore major."""
        sg = SafetyGuardian()
        big_diff = "\n".join([f"+line{i}" for i in range(25)])
        change = _make_change(diff=big_diff)
        severity = sg.classify_severity(change)
        assert severity in (ChangeSeverity.MAJOR, ChangeSeverity.CRITICAL)

    def test_classify_critical_by_size(self) -> None:
        """Buyukluge gore critical."""
        sg = SafetyGuardian()
        huge_diff = "\n".join([f"+line{i}" for i in range(60)])
        change = _make_change(diff=huge_diff)
        severity = sg.classify_severity(change)
        assert severity == ChangeSeverity.CRITICAL

    def test_check_safety_clean(self) -> None:
        """Temiz guvenlik kontrolu."""
        sg = SafetyGuardian()
        change = _make_change(diff="+result = calculate()")
        result = sg.check_safety(change)
        assert result.is_safe is True

    def test_check_safety_harmful(self) -> None:
        """Zararli kod tespiti."""
        sg = SafetyGuardian()
        change = _make_change(diff="+os.system('rm -rf /')")
        result = sg.check_safety(change)
        assert result.is_safe is False
        assert len(result.issues) > 0

    def test_detect_eval(self) -> None:
        """eval tespiti."""
        sg = SafetyGuardian()
        change = _make_change(diff="+result = eval(user_input)")
        result = sg.check_safety(change)
        assert result.is_safe is False

    def test_detect_exec(self) -> None:
        """exec tespiti."""
        sg = SafetyGuardian()
        change = _make_change(diff="+exec(code_string)")
        result = sg.check_safety(change)
        assert result.is_safe is False

    def test_detect_hardcoded_password(self) -> None:
        """Hardcoded sifre tespiti."""
        sg = SafetyGuardian()
        change = _make_change(diff="+password = 'secret123'")
        result = sg.check_safety(change)
        assert result.is_safe is False

    def test_can_auto_approve_minor(self) -> None:
        """Minor otomatik onay."""
        sg = SafetyGuardian(auto_approve_minor=True)
        change = _make_change(diff="+x = 1", change_type="config")
        result = sg.check_safety(change)
        if result.is_safe and result.severity == ChangeSeverity.MINOR:
            assert sg.can_auto_approve(result) is True

    def test_cannot_auto_approve_major(self) -> None:
        """Major otomatik onaylanamaz."""
        sg = SafetyGuardian()
        result = SafetyCheckResult(
            severity=ChangeSeverity.MAJOR,
            is_safe=True,
            requires_approval=True,
        )
        assert sg.can_auto_approve(result) is False

    def test_auto_approve_disabled(self) -> None:
        """Otomatik onay kapali."""
        sg = SafetyGuardian(auto_approve_minor=False)
        result = SafetyCheckResult(
            severity=ChangeSeverity.MINOR,
            is_safe=True,
            requires_approval=False,
        )
        assert sg.can_auto_approve(result) is False

    def test_resource_limits(self) -> None:
        """Kaynak limit kontrolu."""
        sg = SafetyGuardian()
        violations = sg.enforce_resource_limits({"max_cpu_pct": 95.0})
        assert len(violations) == 1

    def test_no_resource_violations(self) -> None:
        """Kaynak ihlali yok."""
        sg = SafetyGuardian()
        violations = sg.enforce_resource_limits({"max_cpu_pct": 50.0})
        assert len(violations) == 0

    def test_check_batch(self) -> None:
        """Toplu kontrol."""
        sg = SafetyGuardian()
        changes = [_make_change(), _make_change()]
        results = sg.check_batch(changes)
        assert len(results) == 2

    def test_safe_count(self) -> None:
        """Guvenli sayisi."""
        sg = SafetyGuardian()
        sg.check_safety(_make_change(diff="+x = 1"))
        assert sg.safe_count >= 0

    def test_unsafe_count(self) -> None:
        """Guvenli olmayan sayisi."""
        sg = SafetyGuardian()
        sg.check_safety(_make_change(diff="+eval('code')"))
        assert sg.unsafe_count == 1


# === ExperimentRunner Testleri ===


class TestExperimentRunner:
    """ExperimentRunner testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        er = ExperimentRunner()
        assert er.experiment_count == 0

    def test_sandbox_test_pass(self) -> None:
        """Sandbox test basarili."""
        er = ExperimentRunner()
        change = _make_change(diff="+x = 42\n+y = x * 2")
        result = er.run_sandbox_test(change)
        assert result.status == ExperimentStatus.PASSED

    def test_sandbox_test_syntax_error(self) -> None:
        """Sandbox test syntax hatasi."""
        er = ExperimentRunner()
        change = _make_change(diff="+def broken(:\n+    pass")
        result = er.run_sandbox_test(change)
        assert result.status == ExperimentStatus.FAILED

    def test_ab_comparison_improvement(self) -> None:
        """A/B karsilastirma iyilestirme."""
        er = ExperimentRunner(confidence_threshold=0.5)
        baseline = [1.0, 1.1, 0.9, 1.0, 1.0, 0.95, 1.05, 1.0]
        variant = [2.0, 2.1, 1.9, 2.0, 2.0, 1.95, 2.05, 2.0]
        result = er.run_ab_comparison(baseline, variant)
        assert result.improvement_pct > 0
        assert result.status == ExperimentStatus.PASSED

    def test_ab_comparison_empty(self) -> None:
        """A/B bos veri."""
        er = ExperimentRunner()
        result = er.run_ab_comparison([], [])
        assert result.status == ExperimentStatus.INCONCLUSIVE

    def test_ab_comparison_decline(self) -> None:
        """A/B gerileme."""
        er = ExperimentRunner(confidence_threshold=0.5)
        baseline = [2.0, 2.1, 1.9, 2.0, 2.0, 1.95, 2.05, 2.0]
        variant = [1.0, 1.1, 0.9, 1.0, 1.0, 0.95, 1.05, 1.0]
        result = er.run_ab_comparison(baseline, variant)
        assert result.improvement_pct < 0

    def test_benchmark(self) -> None:
        """Benchmark testi."""
        er = ExperimentRunner()
        result = er.run_benchmark("speed", [100.0, 110.0, 105.0])
        assert result.status == ExperimentStatus.PASSED

    def test_benchmark_comparison(self) -> None:
        """Benchmark karsilastirma."""
        er = ExperimentRunner()
        er.run_benchmark("speed", [100.0, 110.0])
        result = er.run_benchmark("speed", [120.0, 130.0])
        assert result.improvement_pct > 0

    def test_benchmark_empty(self) -> None:
        """Benchmark bos veri."""
        er = ExperimentRunner()
        result = er.run_benchmark("speed", [])
        assert result.status == ExperimentStatus.INCONCLUSIVE

    def test_statistical_validation(self) -> None:
        """Istatistiksel dogrulama."""
        er = ExperimentRunner()
        a = [1.0, 1.1, 0.9, 1.0, 1.05]
        b = [2.0, 2.1, 1.9, 2.0, 2.05]
        result = er.validate_statistically(a, b)
        assert result["valid"] is True
        assert result["mean_b"] > result["mean_a"]

    def test_statistical_validation_empty(self) -> None:
        """Bos istatistiksel dogrulama."""
        er = ExperimentRunner()
        result = er.validate_statistically([], [])
        assert result["valid"] is False

    def test_gradual_rollout(self) -> None:
        """Kademeli yayilim plani."""
        er = ExperimentRunner()
        rollout = er.plan_gradual_rollout(1000, phases=4)
        assert len(rollout) == 4
        assert rollout[0]["phase"] == 1

    def test_get_experiment(self) -> None:
        """Deney getirme."""
        er = ExperimentRunner()
        change = _make_change(diff="+x = 1")
        er.run_sandbox_test(change)
        found = er.get_experiment(f"sandbox_{change.id[:8]}")
        assert found is not None

    def test_get_experiment_not_found(self) -> None:
        """Olmayan deney."""
        er = ExperimentRunner()
        assert er.get_experiment("nonexistent") is None

    def test_pass_fail_counts(self) -> None:
        """Gecen/kalan sayilari."""
        er = ExperimentRunner()
        er.run_sandbox_test(_make_change(diff="+x = 1"))
        er.run_sandbox_test(_make_change(diff="+def f(:\n+  pass"))
        assert er.pass_count + er.fail_count == er.experiment_count

    def test_experiments_property(self) -> None:
        """Experiments property."""
        er = ExperimentRunner()
        er.run_sandbox_test(_make_change(diff="+x = 1"))
        assert len(er.experiments) == 1


# === ApprovalManager Testleri ===


class TestApprovalManager:
    """ApprovalManager testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        am = ApprovalManager()
        assert am.queue_size == 0
        assert am.pending_count == 0

    def test_queue_change(self) -> None:
        """Onay kuyuguna ekleme."""
        am = ApprovalManager()
        change = _make_change()
        request = am.queue_change(change, "Test baslik")
        assert request.status == ApprovalStatus.PENDING
        assert am.queue_size == 1

    def test_approve(self) -> None:
        """Onaylama."""
        am = ApprovalManager()
        change = _make_change()
        req = am.queue_change(change)
        result = am.approve(req.id, "fatih")
        assert result is True
        assert am.pending_count == 0
        assert am.approved_count == 1

    def test_reject(self) -> None:
        """Reddetme."""
        am = ApprovalManager()
        change = _make_change()
        req = am.queue_change(change)
        result = am.reject(req.id, "fatih", "riskli")
        assert result is True
        r = am.get_request(req.id)
        assert r is not None
        assert r.status == ApprovalStatus.REJECTED

    def test_auto_approve(self) -> None:
        """Otomatik onay."""
        am = ApprovalManager()
        change = _make_change()
        req = am.queue_change(change)
        result = am.auto_approve(req.id)
        assert result is True
        assert am.approved_count == 1

    def test_approve_nonexistent(self) -> None:
        """Olmayan istek onaylama."""
        am = ApprovalManager()
        assert am.approve("nonexistent") is False

    def test_reject_nonexistent(self) -> None:
        """Olmayan istek reddetme."""
        am = ApprovalManager()
        assert am.reject("nonexistent") is False

    def test_approve_already_approved(self) -> None:
        """Zaten onaylanmis istek."""
        am = ApprovalManager()
        change = _make_change()
        req = am.queue_change(change)
        am.approve(req.id)
        result = am.approve(req.id)
        assert result is False

    def test_create_batch(self) -> None:
        """Batch olusturma."""
        am = ApprovalManager()
        r1 = am.queue_change(_make_change())
        r2 = am.queue_change(_make_change())
        batch_id = am.create_batch([r1.id, r2.id])
        assert batch_id.startswith("batch_")

    def test_approve_batch(self) -> None:
        """Toplu onay."""
        am = ApprovalManager()
        r1 = am.queue_change(_make_change())
        r2 = am.queue_change(_make_change())
        batch_id = am.create_batch([r1.id, r2.id])
        count = am.approve_batch(batch_id)
        assert count == 2
        assert am.pending_count == 0

    def test_get_pending(self) -> None:
        """Bekleyenler listesi."""
        am = ApprovalManager()
        am.queue_change(_make_change())
        am.queue_change(_make_change())
        pending = am.get_pending()
        assert len(pending) == 2

    def test_get_request(self) -> None:
        """Istek getirme."""
        am = ApprovalManager()
        change = _make_change()
        req = am.queue_change(change)
        found = am.get_request(req.id)
        assert found is not None
        assert found.id == req.id

    def test_get_request_not_found(self) -> None:
        """Olmayan istek."""
        am = ApprovalManager()
        assert am.get_request("nonexistent") is None

    def test_audit_trail(self) -> None:
        """Denetim izi."""
        am = ApprovalManager()
        change = _make_change()
        req = am.queue_change(change)
        am.approve(req.id)
        trail = am.get_audit_trail()
        assert len(trail) == 2  # queued + approved

    def test_format_for_telegram(self) -> None:
        """Telegram formatlama."""
        am = ApprovalManager()
        req = ApprovalRequest(
            title="Test degisiklik",
            severity=ChangeSeverity.MAJOR,
            description="Test aciklama",
        )
        msg = am.format_for_telegram(req)
        assert "Test degisiklik" in msg
        assert "major" in msg

    def test_check_timeouts(self) -> None:
        """Timeout kontrolu."""
        am = ApprovalManager(timeout_hours=0)
        change = _make_change()
        am.queue_change(change)
        # timeout_hours=0, hemen timeout olmali
        import time
        time.sleep(0.01)
        timed_out = am.check_timeouts()
        assert len(timed_out) == 1
        assert timed_out[0].status == ApprovalStatus.TIMEOUT


# === KnowledgeLearner Testleri ===


class TestKnowledgeLearner:
    """KnowledgeLearner testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        kl = KnowledgeLearner()
        assert kl.pattern_count == 0
        assert kl.practice_count == 0

    def test_learn_from_fix(self) -> None:
        """Basarili fix'ten ogrenme."""
        kl = KnowledgeLearner()
        change = _make_change()
        exp = _make_experiment(status=ExperimentStatus.PASSED)
        pattern = kl.learn_from_fix(change, exp)
        assert pattern is not None
        assert kl.pattern_count == 1

    def test_learn_from_failed_fix(self) -> None:
        """Basarisiz fix'ten ogrenme (None)."""
        kl = KnowledgeLearner()
        change = _make_change()
        exp = _make_experiment(status=ExperimentStatus.FAILED)
        pattern = kl.learn_from_fix(change, exp)
        assert pattern is None

    def test_learn_duplicate_increments(self) -> None:
        """Tekrar ogrenme sayaci artirir."""
        kl = KnowledgeLearner()
        change = _make_change()
        exp = _make_experiment(status=ExperimentStatus.PASSED)
        p1 = kl.learn_from_fix(change, exp)
        p2 = kl.learn_from_fix(change, exp)
        assert p1 is not None
        assert p2 is not None
        assert p2.success_count == 2

    def test_learn_from_experiment(self) -> None:
        """Deney sonucundan ogrenme."""
        kl = KnowledgeLearner()
        exp = _make_experiment(status=ExperimentStatus.PASSED)
        pattern = kl.learn_from_experiment(exp)
        assert pattern is not None

    def test_learn_from_inconclusive(self) -> None:
        """Kararsiz deneyden ogrenme (None)."""
        kl = KnowledgeLearner()
        exp = _make_experiment(status=ExperimentStatus.INCONCLUSIVE)
        pattern = kl.learn_from_experiment(exp)
        assert pattern is None

    def test_document_pattern(self) -> None:
        """Kalip dokumantasyonu."""
        kl = KnowledgeLearner()
        p = kl.document_pattern("retry_pattern", "resilience", "Tekrar deneme", "3 kez dene")
        assert p.pattern_name == "retry_pattern"
        assert kl.pattern_count == 1

    def test_best_practice(self) -> None:
        """En iyi pratik."""
        kl = KnowledgeLearner()
        kl.update_best_practice("error_handling", "Her zaman try-except kullan")
        assert kl.get_best_practice("error_handling") == "Her zaman try-except kullan"

    def test_best_practice_not_found(self) -> None:
        """Olmayan pratik."""
        kl = KnowledgeLearner()
        assert kl.get_best_practice("nonexistent") == ""

    def test_share_with_agent(self) -> None:
        """Agent ile paylasim."""
        kl = KnowledgeLearner()
        kl.share_with_agent("coding_agent", "Her zaman test yaz")
        knowledge = kl.get_agent_knowledge("coding_agent")
        assert len(knowledge) == 1

    def test_get_agent_knowledge_empty(self) -> None:
        """Bos agent bilgisi."""
        kl = KnowledgeLearner()
        assert kl.get_agent_knowledge("unknown") == []

    def test_find_patterns(self) -> None:
        """Kalip arama."""
        kl = KnowledgeLearner()
        kl.document_pattern("p1", "fix", "d1", "s1")
        kl.document_pattern("p2", "perf", "d2", "s2")
        found = kl.find_patterns(category="fix")
        assert len(found) == 1

    def test_find_patterns_with_score(self) -> None:
        """Puan filtreli kalip arama."""
        kl = KnowledgeLearner()
        kl.document_pattern("p1", "fix", "d1", "s1")  # score 0.3
        found = kl.find_patterns(min_score=0.5)
        assert len(found) == 0

    def test_get_statistics(self) -> None:
        """Istatistikler."""
        kl = KnowledgeLearner()
        kl.document_pattern("p1", "fix", "d1", "s1")
        kl.update_best_practice("cat", "practice")
        stats = kl.get_statistics()
        assert stats["total_patterns"] == 1
        assert stats["best_practices"] == 1

    def test_build_knowledge_base(self) -> None:
        """Bilgi tabani olusturma."""
        kl = KnowledgeLearner()
        kl.document_pattern("p1", "fix", "d1", "s1")
        kl.update_best_practice("cat", "practice")
        kb = kl.build_knowledge_base()
        assert len(kb["patterns"]) == 1
        assert len(kb["best_practices"]) == 1

    def test_patterns_property(self) -> None:
        """Patterns property."""
        kl = KnowledgeLearner()
        kl.document_pattern("p1", "fix", "d1", "s1")
        assert len(kl.patterns) == 1


# === EvolutionController Testleri ===


class TestEvolutionController:
    """EvolutionController testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        ec = EvolutionController()
        assert ec.is_paused is False
        assert ec.cycle_count == 0

    def test_components_accessible(self) -> None:
        """Bilesenler erisilebilir."""
        ec = EvolutionController()
        assert ec.monitor is not None
        assert ec.detector is not None
        assert ec.planner is not None
        assert ec.evolver is not None
        assert ec.guardian is not None
        assert ec.runner is not None
        assert ec.approvals is not None
        assert ec.learner is not None

    def test_run_empty_cycle(self) -> None:
        """Bos dongu (zayiflik yok)."""
        ec = EvolutionController()
        cycle = ec.run_cycle()
        assert cycle.phase == EvolutionPhase.COMPLETE
        assert cycle.weaknesses_found == 0

    def test_run_cycle_with_weaknesses(self) -> None:
        """Zayiflikli dongu."""
        ec = EvolutionController(auto_approve_minor=True, max_daily_changes=10)

        # Basarisizlik kaydet
        for _ in range(10):
            ec.monitor.record_failure("agent1", "task1", "timeout error", 100.0)
        for _ in range(2):
            ec.monitor.record_success("agent1", "task1", 100.0)

        cycle = ec.run_cycle()
        assert cycle.weaknesses_found > 0
        assert cycle.improvements_planned > 0
        assert cycle.phase == EvolutionPhase.COMPLETE

    def test_pause_resume(self) -> None:
        """Durdur/devam."""
        ec = EvolutionController()
        ec.pause()
        assert ec.is_paused is True

        cycle = ec.run_cycle()
        assert cycle.paused is True

        ec.resume()
        assert ec.is_paused is False

    def test_emergency_stop(self) -> None:
        """Acil durdurma."""
        ec = EvolutionController()
        ec.evolver.apply_change(_make_change())
        ec.evolver.apply_change(_make_change())
        count = ec.emergency_stop()
        assert count == 2
        assert ec.is_paused is True

    def test_process_approval_approve(self) -> None:
        """Onay isleme - kabul."""
        ec = EvolutionController()
        change = _make_change()
        ec.evolver._changes.append(change)
        req = ec.approvals.queue_change(change)
        result = ec.process_approval(req.id, True, "fatih")
        assert result is True

    def test_process_approval_reject(self) -> None:
        """Onay isleme - red."""
        ec = EvolutionController()
        change = _make_change()
        req = ec.approvals.queue_change(change)
        result = ec.process_approval(req.id, False, "fatih")
        assert result is True

    def test_reset_daily_counter(self) -> None:
        """Gunluk sayac sifirlama."""
        ec = EvolutionController()
        ec._daily_auto_count = 5
        ec.reset_daily_counter()
        assert ec._daily_auto_count == 0

    def test_get_status(self) -> None:
        """Durum sorgulama."""
        ec = EvolutionController()
        status = ec.get_status()
        assert "paused" in status
        assert "daily_auto_count" in status
        assert "total_cycles" in status
        assert status["paused"] is False

    def test_max_daily_limit(self) -> None:
        """Gunluk limit kontrolu."""
        ec = EvolutionController(max_daily_changes=1)

        # Cok fazla basarisizlik kaydet
        for _ in range(20):
            ec.monitor.record_failure("a1", "t1", "err", 100.0)

        cycle = ec.run_cycle()
        assert cycle.changes_auto_approved <= 1

    def test_weekly_cycle(self) -> None:
        """Haftalik dongu."""
        ec = EvolutionController()
        cycle = ec.run_cycle(EvolutionCycleType.WEEKLY)
        assert cycle.cycle_type == EvolutionCycleType.WEEKLY

    def test_emergency_cycle(self) -> None:
        """Acil dongu."""
        ec = EvolutionController()
        cycle = ec.run_cycle(EvolutionCycleType.EMERGENCY)
        assert cycle.cycle_type == EvolutionCycleType.EMERGENCY

    def test_cycles_history(self) -> None:
        """Dongu gecmisi."""
        ec = EvolutionController()
        ec.run_cycle()
        ec.run_cycle()
        assert len(ec.cycles) == 2


# === Entegrasyon Testleri ===


class TestEvolutionIntegration:
    """Entegrasyon testleri."""

    def test_monitor_to_detector(self) -> None:
        """Monitor -> Detector entegrasyonu."""
        pm = PerformanceMonitor()
        for _ in range(10):
            pm.record_failure("a1", "t1", "timeout", 100.0)
        pm.record_success("a1", "t1", 50.0)

        wd = WeaknessDetector(failure_rate_threshold=0.1)
        metrics = pm.get_all_metrics()
        weaknesses = wd.analyze_failures(metrics)
        assert len(weaknesses) > 0

    def test_detector_to_planner(self) -> None:
        """Detector -> Planner entegrasyonu."""
        wd = WeaknessDetector()
        weakness = wd.record_complaint("user", "yavas", "agent1")

        ip = ImprovementPlanner()
        plan = ip.create_plan(weakness)
        assert plan is not None
        assert plan.target_component == "agent1"

    def test_planner_to_evolver(self) -> None:
        """Planner -> Evolver entegrasyonu."""
        ip = ImprovementPlanner()
        w = _make_weakness()
        plan = ip.create_plan(w)

        ce = CodeEvolver()
        change = ce.generate_change(plan)
        assert change is not None
        assert change.diff != ""

    def test_evolver_to_guardian(self) -> None:
        """Evolver -> Guardian entegrasyonu."""
        ce = CodeEvolver()
        plan = _make_plan()
        change = ce.generate_change(plan)

        sg = SafetyGuardian()
        result = sg.check_safety(change)
        assert result is not None

    def test_full_pipeline(self) -> None:
        """Tam pipeline testi."""
        # 1. Performans kaydi
        pm = PerformanceMonitor()
        for _ in range(15):
            pm.record_failure("agent1", "task1", "error", 100.0)
        pm.record_success("agent1", "task1", 50.0)

        # 2. Zayiflik tespiti
        wd = WeaknessDetector(failure_rate_threshold=0.1)
        weaknesses = wd.run_full_analysis(metrics=pm.get_all_metrics())
        assert len(weaknesses) > 0

        # 3. Plan
        ip = ImprovementPlanner()
        plans = ip.create_plans_from_weaknesses(weaknesses)
        assert len(plans) > 0

        # 4. Degisiklik
        ce = CodeEvolver()
        changes = ce.generate_changes(plans)
        assert len(changes) > 0

        # 5. Guvenlik
        sg = SafetyGuardian()
        results = sg.check_batch(changes)
        assert len(results) > 0

        # 6. Deney
        er = ExperimentRunner()
        for change in changes:
            er.run_sandbox_test(change)

        # 7. Onay
        am = ApprovalManager()
        for change in changes:
            am.queue_change(change)

        # 8. Ogrenme
        kl = KnowledgeLearner()
        for change in changes:
            exp = _make_experiment(status=ExperimentStatus.PASSED)
            kl.learn_from_fix(change, exp)

        assert kl.pattern_count > 0

    def test_end_to_end_controller(self) -> None:
        """Uctan uca controller testi."""
        ec = EvolutionController(auto_approve_minor=True, max_daily_changes=50)

        # Performans verisi yukle
        for i in range(20):
            if i < 15:
                ec.monitor.record_failure("agent1", "task1", "timeout error", 500.0)
            else:
                ec.monitor.record_success("agent1", "task1", 100.0)

        # Dongu calistir
        cycle = ec.run_cycle()

        assert cycle.weaknesses_found > 0
        assert cycle.improvements_planned > 0
        status = ec.get_status()
        assert status["total_cycles"] == 1

    def test_learn_and_share_across_agents(self) -> None:
        """Agentler arasi ogrenme ve paylasim."""
        kl = KnowledgeLearner()

        # Fix'ten ogren
        change = _make_change(path="app/agents/coding.py")
        exp = _make_experiment(status=ExperimentStatus.PASSED)
        kl.learn_from_fix(change, exp)

        # Diger agentlerle paylas
        kl.share_with_agent("security_agent", "timeout icin retry yap")
        kl.share_with_agent("research_agent", "timeout icin retry yap")

        assert len(kl.get_agent_knowledge("security_agent")) == 1
        assert len(kl.get_agent_knowledge("research_agent")) == 1

    def test_safety_blocks_harmful(self) -> None:
        """Guvenlik zararli kodu engeller."""
        sg = SafetyGuardian(auto_approve_minor=True)
        harmful = _make_change(diff="+eval(user_input)")
        result = sg.check_safety(harmful)
        assert not sg.can_auto_approve(result)

    def test_approval_flow(self) -> None:
        """Onay akisi."""
        am = ApprovalManager()
        sg = SafetyGuardian()

        change = _make_change(diff="+x = 1", change_type="config")
        safety = sg.check_safety(change)

        if safety.requires_approval:
            req = am.queue_change(change)
            am.approve(req.id, "fatih")
            assert am.approved_count == 1
        else:
            assert safety.is_safe
