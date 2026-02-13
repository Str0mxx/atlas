"""Autonomous Business Runner testleri.

Firsat tespiti, strateji uretimi, uygulama motoru,
performans analizi, optimizasyon, geri bildirim dongusu,
otonom dongu ve is hafizasi testleri.
"""

from datetime import datetime, timedelta, timezone

from app.core.business.autonomous_cycle import AutonomousCycle
from app.core.business.business_memory import BusinessMemory
from app.core.business.execution_engine import ExecutionEngine
from app.core.business.feedback_loop import FeedbackLoop
from app.core.business.opportunity_detector import OpportunityDetector
from app.core.business.optimizer import BusinessOptimizer
from app.core.business.performance_analyzer import PerformanceAnalyzer
from app.core.business.strategy_generator import StrategyGenerator
from app.models.business import (
    ActionPriority,
    AnomalySeverity,
    CheckpointStatus,
    CyclePhase,
    CycleStatus,
    EscalationLevel,
    ExecutionStatus,
    ExperimentStatus,
    InsightType,
    KPIDirection,
    OpportunityStatus,
    OpportunityType,
    StrategyStatus,
)


# === Yardimci fonksiyonlar ===


def _make_detector(**kwargs) -> OpportunityDetector:
    """OpportunityDetector olusturur."""
    return OpportunityDetector(**kwargs)


def _make_generator(**kwargs) -> StrategyGenerator:
    """StrategyGenerator olusturur."""
    return StrategyGenerator(**kwargs)


def _make_engine(**kwargs) -> ExecutionEngine:
    """ExecutionEngine olusturur."""
    return ExecutionEngine(**kwargs)


def _make_analyzer() -> PerformanceAnalyzer:
    """PerformanceAnalyzer olusturur."""
    return PerformanceAnalyzer()


def _make_optimizer() -> BusinessOptimizer:
    """BusinessOptimizer olusturur."""
    return BusinessOptimizer()


def _make_feedback() -> FeedbackLoop:
    """FeedbackLoop olusturur."""
    return FeedbackLoop()


def _make_cycle(**kwargs) -> AutonomousCycle:
    """AutonomousCycle olusturur."""
    return AutonomousCycle(**kwargs)


def _make_memory() -> BusinessMemory:
    """BusinessMemory olusturur."""
    return BusinessMemory()


# ============================================================
# OpportunityDetector Testleri
# ============================================================


class TestOpportunityDetectorInit:
    """OpportunityDetector baslatma testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerle baslatma."""
        det = _make_detector()
        assert det.opportunity_count == 0
        assert det.signal_count == 0
        assert det.competitor_count == 0

    def test_custom_min_confidence(self) -> None:
        """Ozel minimum guven esigi."""
        det = _make_detector(min_confidence=0.7)
        assert det._min_confidence == 0.7


class TestAddSignal:
    """OpportunityDetector.add_signal testleri."""

    def test_add_signal(self) -> None:
        """Pazar sinyali ekleme."""
        det = _make_detector()
        signal = det.add_signal("web", "yeni trend", strength=0.8)
        assert signal.source == "web"
        assert signal.strength == 0.8
        assert det.signal_count == 1

    def test_signal_strength_clamped(self) -> None:
        """Sinyal gucu 0-1 araliginda kalmali."""
        det = _make_detector()
        s1 = det.add_signal("x", "a", strength=1.5)
        s2 = det.add_signal("y", "b", strength=-0.5)
        assert s1.strength == 1.0
        assert s2.strength == 0.0

    def test_signal_type(self) -> None:
        """Sinyal tipi atamasi."""
        det = _make_detector()
        signal = det.add_signal("src", "data", signal_type="social_media")
        assert signal.signal_type == "social_media"


class TestScanMarket:
    """OpportunityDetector.scan_market testleri."""

    def test_scan_finds_opportunities(self) -> None:
        """Pazar taramasi firsat bulur."""
        det = _make_detector(min_confidence=0.3)
        det.add_signal("web", "sac ekimi talebi artiyor", strength=0.8)
        det.add_signal("survey", "fiyat hassasiyeti", strength=0.5)

        opps = det.scan_market("medikal turizm")
        assert len(opps) == 2
        assert all(o.opportunity_type == OpportunityType.MARKET_GAP for o in opps)

    def test_scan_filters_low_confidence(self) -> None:
        """Dusuk guvenli sinyaller filtrelenir."""
        det = _make_detector(min_confidence=0.6)
        det.add_signal("web", "zayif sinyal", strength=0.3)

        opps = det.scan_market("kozmetik")
        assert len(opps) == 0

    def test_scan_with_custom_signals(self) -> None:
        """Ozel sinyal listesi ile tarama."""
        det = _make_detector()
        from app.models.business import MarketSignal
        signals = [MarketSignal(source="manual", content="firsat", strength=0.9)]
        opps = det.scan_market("e-ticaret", signals=signals)
        assert len(opps) == 1

    def test_scan_tags_include_domain(self) -> None:
        """Firsat etiketleri domain icerir."""
        det = _make_detector()
        det.add_signal("web", "trend", strength=0.7, signal_type="social")
        opps = det.scan_market("kozmetik")
        assert "kozmetik" in opps[0].tags


class TestAnalyzeTrends:
    """OpportunityDetector.analyze_trends testleri."""

    def test_positive_trend(self) -> None:
        """Yukaris trend tespiti."""
        det = _make_detector()
        trend = det.analyze_trends([10, 20, 30, 40, 50], "sac_ekimi")
        assert trend.direction == "positive"
        assert trend.momentum > 0

    def test_negative_trend(self) -> None:
        """Asagi trend tespiti."""
        det = _make_detector()
        trend = det.analyze_trends([50, 40, 30, 20, 10], "eski_urun")
        assert trend.direction == "negative"

    def test_stable_trend(self) -> None:
        """Stabil trend tespiti."""
        det = _make_detector()
        trend = det.analyze_trends([50, 50, 50, 50, 50], "sabit")
        assert trend.direction == "stable"

    def test_single_point(self) -> None:
        """Tek veri noktasinda stable."""
        det = _make_detector()
        trend = det.analyze_trends([100], "tek")
        assert trend.direction == "stable"
        assert trend.momentum == 0.0

    def test_empty_data(self) -> None:
        """Bos veri stable."""
        det = _make_detector()
        trend = det.analyze_trends([], "bos")
        assert trend.direction == "stable"

    def test_trend_stored(self) -> None:
        """Trend verisi kaydedilir."""
        det = _make_detector()
        det.analyze_trends([1, 2, 3], "test")
        assert "test" in det._trends


class TestCompetitorMonitoring:
    """OpportunityDetector rakip izleme testleri."""

    def test_add_competitor(self) -> None:
        """Rakip ekleme."""
        det = _make_detector()
        comp = det.add_competitor("RakipA", strengths=["fiyat"], weaknesses=["kalite"])
        assert comp.name == "RakipA"
        assert det.competitor_count == 1

    def test_monitor_competitors(self) -> None:
        """Rakip zayifliklarindan firsat cikarma."""
        det = _make_detector(min_confidence=0.3)
        det.add_competitor("RakipB", weaknesses=["musteri hizmeti", "teslimat"], threat_level=0.7)
        opps = det.monitor_competitors()
        assert len(opps) == 2
        assert all(o.opportunity_type == OpportunityType.COMPETITOR_WEAKNESS for o in opps)

    def test_monitor_filters_low_threat(self) -> None:
        """Dusuk tehditteki rakipler filtrelenir."""
        det = _make_detector(min_confidence=0.5)
        det.add_competitor("ZayifRakip", weaknesses=["x"], threat_level=0.2)
        opps = det.monitor_competitors()
        assert len(opps) == 0


class TestIdentifyGaps:
    """OpportunityDetector.identify_gaps testleri."""

    def test_find_gaps(self) -> None:
        """Pazar boslugu tespiti."""
        det = _make_detector()
        needs = ["online satis", "kargo takip", "iade yonetimi"]
        offerings = ["online satis"]
        gaps = det.identify_gaps(needs, offerings)
        assert len(gaps) == 2

    def test_no_gaps(self) -> None:
        """Bosluk yoksa bos liste."""
        det = _make_detector()
        gaps = det.identify_gaps(["a", "b"], ["a", "b"])
        assert len(gaps) == 0

    def test_case_insensitive(self) -> None:
        """Buyuk/kucuk harf duyarsiz esleme."""
        det = _make_detector()
        gaps = det.identify_gaps(["Online Satis"], ["online satis"])
        assert len(gaps) == 0


class TestLeadScoring:
    """OpportunityDetector.score_lead testleri."""

    def test_score_lead(self) -> None:
        """Lead puanlama."""
        det = _make_detector()
        det.add_signal("web", "firsat", strength=0.9)
        opps = det.scan_market("test")
        score = det.score_lead(opps[0].id)
        assert 0.0 <= score <= 1.0
        assert opps[0].lead_score == score

    def test_score_nonexistent(self) -> None:
        """Var olmayan firsat icin 0."""
        det = _make_detector()
        assert det.score_lead("yok") == 0.0

    def test_top_opportunities(self) -> None:
        """En iyi firsatlar siralamasi."""
        det = _make_detector()
        det.add_signal("a", "x", strength=0.5)
        det.add_signal("b", "y", strength=0.9)
        opps = det.scan_market("test")
        for o in opps:
            det.score_lead(o.id)
        top = det.get_top_opportunities(limit=1)
        assert len(top) == 1


class TestExpireOpportunities:
    """OpportunityDetector.expire_old_opportunities testleri."""

    def test_expire(self) -> None:
        """Suresi dolan firsatlar expire olur."""
        det = _make_detector()
        det.add_signal("x", "y", strength=0.8)
        opps = det.scan_market("test")
        opps[0].expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        expired = det.expire_old_opportunities()
        assert expired == 1
        assert opps[0].status == OpportunityStatus.EXPIRED

    def test_no_expire_future(self) -> None:
        """Suresi dolmamis firsatlar etkilenmez."""
        det = _make_detector()
        det.add_signal("x", "y", strength=0.8)
        opps = det.scan_market("test")
        opps[0].expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        expired = det.expire_old_opportunities()
        assert expired == 0


# ============================================================
# StrategyGenerator Testleri
# ============================================================


class TestStrategyGeneratorInit:
    """StrategyGenerator baslatma testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerle baslatma."""
        gen = _make_generator()
        assert gen.strategy_count == 0
        assert gen._default_timeline_days == 30

    def test_custom_params(self) -> None:
        """Ozel parametrelerle baslatma."""
        gen = _make_generator(default_timeline_days=60, risk_tolerance=0.8)
        assert gen._default_timeline_days == 60
        assert gen._risk_tolerance == 0.8


class TestCreateStrategy:
    """StrategyGenerator.create_strategy testleri."""

    def test_basic_creation(self) -> None:
        """Temel strateji olusturma."""
        gen = _make_generator()
        s = gen.create_strategy("Satis artirma", goals=["online satis", "magaza satis"])
        assert s.title == "Satis artirma"
        assert len(s.goals) == 2
        assert s.status == StrategyStatus.DRAFT

    def test_with_opportunity(self) -> None:
        """Firsat baglantili strateji."""
        gen = _make_generator()
        s = gen.create_strategy("Test", opportunity_id="opp-123")
        assert s.opportunity_id == "opp-123"

    def test_custom_timeline(self) -> None:
        """Ozel zaman cizgisi."""
        gen = _make_generator()
        s = gen.create_strategy("Test", timeline_days=90)
        assert s.timeline_days == 90


class TestDecomposeGoals:
    """StrategyGenerator.decompose_goals testleri."""

    def test_decompose(self) -> None:
        """Hedef ayristirma."""
        gen = _make_generator()
        s = gen.create_strategy("Test", goals=["hedef1", "hedef2", "hedef3"])
        steps = gen.decompose_goals(s.id)
        assert len(steps) == 3
        assert steps[0].priority == ActionPriority.HIGH
        assert steps[1].priority == ActionPriority.MEDIUM

    def test_decompose_dependencies(self) -> None:
        """Adimlar arasi bagimliliklar."""
        gen = _make_generator()
        s = gen.create_strategy("Test", goals=["a", "b"])
        steps = gen.decompose_goals(s.id)
        assert len(steps[0].dependencies) == 0
        assert steps[1].dependencies == [steps[0].id]

    def test_decompose_nonexistent(self) -> None:
        """Var olmayan strateji icin bos liste."""
        gen = _make_generator()
        assert gen.decompose_goals("yok") == []


class TestCreateActionPlan:
    """StrategyGenerator.create_action_plan testleri."""

    def test_manual_plan(self) -> None:
        """Manuel aksiyon plani."""
        gen = _make_generator()
        s = gen.create_strategy("Test")
        steps = gen.create_action_plan(s.id, [
            {"description": "Arastirma", "priority": "high", "duration_hours": 4},
            {"description": "Uygulama", "priority": "medium", "agent_type": "coding"},
        ])
        assert len(steps) == 2
        assert steps[0].priority == ActionPriority.HIGH
        assert steps[1].agent_type == "coding"

    def test_invalid_priority_fallback(self) -> None:
        """Gecersiz oncelik varsayilana doner."""
        gen = _make_generator()
        s = gen.create_strategy("Test")
        steps = gen.create_action_plan(s.id, [{"description": "x", "priority": "invalid"}])
        assert steps[0].priority == ActionPriority.MEDIUM


class TestEstimateResources:
    """StrategyGenerator.estimate_resources testleri."""

    def test_estimate(self) -> None:
        """Kaynak tahmini."""
        gen = _make_generator()
        s = gen.create_strategy("Test")
        gen.create_action_plan(s.id, [
            {"description": "a", "duration_hours": 10, "agent_type": "research"},
            {"description": "b", "duration_hours": 20, "agent_type": "coding"},
        ])
        resources = gen.estimate_resources(s.id)
        assert len(resources) == 3

        time_res = next(r for r in resources if r.resource_type == "time")
        assert time_res.amount == 30.0

        agent_res = next(r for r in resources if r.resource_type == "agents")
        assert agent_res.amount == 2.0

    def test_estimate_nonexistent(self) -> None:
        """Var olmayan strateji icin bos liste."""
        gen = _make_generator()
        assert gen.estimate_resources("yok") == []


class TestAssessRisks:
    """StrategyGenerator.assess_risks testleri."""

    def test_default_risks(self) -> None:
        """Standart risk degerlendirmesi."""
        gen = _make_generator()
        s = gen.create_strategy("Test")
        risks = gen.assess_risks(s.id)
        assert len(risks) == 3
        assert all(r.risk_score == r.probability * r.impact for r in risks)

    def test_custom_risks(self) -> None:
        """Ozel risk ekleme."""
        gen = _make_generator()
        s = gen.create_strategy("Test")
        risks = gen.assess_risks(s.id, custom_risks=[
            {"description": "Ozel risk", "probability": 0.9, "impact": 0.9},
        ])
        assert len(risks) == 4

    def test_assess_nonexistent(self) -> None:
        """Var olmayan strateji."""
        gen = _make_generator()
        assert gen.assess_risks("yok") == []


class TestProjectROI:
    """StrategyGenerator.project_roi testleri."""

    def test_positive_roi(self) -> None:
        """Pozitif ROI projeksiyonu."""
        gen = _make_generator()
        s = gen.create_strategy("Test")
        gen.estimate_resources(s.id)
        roi = gen.project_roi(s.id, investment=1000)
        assert roi > 0

    def test_roi_with_risks(self) -> None:
        """Riskli stratejide dusuk ROI."""
        gen = _make_generator()
        s = gen.create_strategy("Test")
        gen.assess_risks(s.id, custom_risks=[
            {"description": "buyuk risk", "probability": 0.9, "impact": 0.9},
        ])
        roi = gen.project_roi(s.id, investment=1000)
        # Risk faktoru ROI'yi dusurur
        assert roi < 200  # Risksiz 200% olurdu

    def test_roi_nonexistent(self) -> None:
        """Var olmayan strateji icin 0."""
        gen = _make_generator()
        assert gen.project_roi("yok") == 0.0


class TestStrategyViability:
    """StrategyGenerator.is_viable testleri."""

    def test_viable_strategy(self) -> None:
        """Uygulanabilir strateji."""
        gen = _make_generator(risk_tolerance=0.5)
        s = gen.create_strategy("Test")
        gen.assess_risks(s.id)
        gen.project_roi(s.id, investment=1000)
        assert gen.is_viable(s.id) is True

    def test_high_risk_not_viable(self) -> None:
        """Yuksek riskli strateji uygulanamaz."""
        gen = _make_generator(risk_tolerance=0.1)
        s = gen.create_strategy("Test")
        gen.assess_risks(s.id, custom_risks=[
            {"description": "cok riskli", "probability": 0.9, "impact": 0.9},
        ])
        gen.project_roi(s.id, investment=1000)
        assert gen.is_viable(s.id) is False

    def test_nonexistent_not_viable(self) -> None:
        """Var olmayan strateji uygulanamaz."""
        gen = _make_generator()
        assert gen.is_viable("yok") is False


class TestActivateStrategy:
    """StrategyGenerator.activate_strategy testleri."""

    def test_activate(self) -> None:
        """Strateji aktivasyonu."""
        gen = _make_generator()
        s = gen.create_strategy("Test")
        assert gen.activate_strategy(s.id) is True
        assert s.status == StrategyStatus.ACTIVE
        assert len(gen.active_strategies) == 1

    def test_activate_nonexistent(self) -> None:
        """Var olmayan strateji aktivasyonu."""
        gen = _make_generator()
        assert gen.activate_strategy("yok") is False


# ============================================================
# ExecutionEngine Testleri
# ============================================================


class TestExecutionEngineInit:
    """ExecutionEngine baslatma testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerle baslatma."""
        eng = _make_engine()
        assert eng.execution_count == 0
        assert eng._max_retries == 3

    def test_custom_retries(self) -> None:
        """Ozel retry sayisi."""
        eng = _make_engine(max_retries=5)
        assert eng._max_retries == 5


def _create_test_strategy() -> tuple[StrategyGenerator, ExecutionEngine, str]:
    """Test strateji ve engine olusturur."""
    gen = _make_generator()
    s = gen.create_strategy("Test", goals=["hedef1", "hedef2"])
    gen.decompose_goals(s.id)
    eng = _make_engine()
    eng.register_strategy(s)
    return gen, eng, s.id


class TestScheduleTasks:
    """ExecutionEngine.schedule_tasks testleri."""

    def test_schedule(self) -> None:
        """Gorev zamanlama."""
        _, eng, sid = _create_test_strategy()
        execs = eng.schedule_tasks(sid)
        assert len(execs) == 2
        # Ilk gorev bagimlilik yok -> SCHEDULED
        assert execs[0].status == ExecutionStatus.SCHEDULED
        # Ikinci gorev bagimli -> PENDING
        assert execs[1].status == ExecutionStatus.PENDING

    def test_schedule_nonexistent(self) -> None:
        """Var olmayan strateji."""
        eng = _make_engine()
        assert eng.schedule_tasks("yok") == []


class TestDelegateTask:
    """ExecutionEngine.delegate_task testleri."""

    def test_delegate(self) -> None:
        """Gorev delegasyonu."""
        _, eng, sid = _create_test_strategy()
        execs = eng.schedule_tasks(sid)
        assert eng.delegate_task(execs[0].id, "research_agent") is True
        assert execs[0].status == ExecutionStatus.RUNNING
        assert execs[0].agent_id == "research_agent"

    def test_delegate_running_fails(self) -> None:
        """Calisan goreve tekrar delege edilemez."""
        _, eng, sid = _create_test_strategy()
        execs = eng.schedule_tasks(sid)
        eng.delegate_task(execs[0].id, "agent1")
        assert eng.delegate_task(execs[0].id, "agent2") is False


class TestCompleteTask:
    """ExecutionEngine.complete_task testleri."""

    def test_complete(self) -> None:
        """Gorev tamamlama."""
        _, eng, sid = _create_test_strategy()
        execs = eng.schedule_tasks(sid)
        eng.start_task(execs[0].id)
        assert eng.complete_task(execs[0].id, {"sonuc": "basarili"}) is True
        assert execs[0].status == ExecutionStatus.COMPLETED
        assert execs[0].result == {"sonuc": "basarili"}

    def test_complete_unblocks_dependent(self) -> None:
        """Tamamlanan gorev bagimli gorevi acar."""
        _, eng, sid = _create_test_strategy()
        execs = eng.schedule_tasks(sid)
        eng.start_task(execs[0].id)
        eng.complete_task(execs[0].id)
        # Ikinci gorev artik SCHEDULED olmali
        assert execs[1].status == ExecutionStatus.SCHEDULED

    def test_complete_not_running(self) -> None:
        """Calismayan gorev tamamlanamaz."""
        _, eng, sid = _create_test_strategy()
        execs = eng.schedule_tasks(sid)
        assert eng.complete_task(execs[0].id) is False


class TestFailTask:
    """ExecutionEngine.fail_task testleri."""

    def test_fail_with_retry(self) -> None:
        """Basarisizlik tekrar dener."""
        _, eng, sid = _create_test_strategy()
        execs = eng.schedule_tasks(sid)
        eng.start_task(execs[0].id)
        eng.fail_task(execs[0].id, "timeout")
        assert execs[0].status == ExecutionStatus.PENDING
        assert execs[0].retry_count == 1

    def test_fail_max_retries(self) -> None:
        """Maksimum tekrar sonrasi FAILED."""
        eng = _make_engine(max_retries=2)
        gen = _make_generator()
        s = gen.create_strategy("Test", goals=["a"])
        gen.decompose_goals(s.id)
        eng.register_strategy(s)
        execs = eng.schedule_tasks(s.id)

        for _ in range(2):
            eng.start_task(execs[0].id)
            eng.fail_task(execs[0].id, "hata")

        assert execs[0].status == ExecutionStatus.FAILED


class TestGetProgress:
    """ExecutionEngine.get_progress testleri."""

    def test_progress(self) -> None:
        """Ilerleme takibi."""
        _, eng, sid = _create_test_strategy()
        execs = eng.schedule_tasks(sid)
        eng.start_task(execs[0].id)
        eng.complete_task(execs[0].id)

        progress = eng.get_progress(sid)
        assert progress["total"] == 2
        assert progress["completed"] == 1
        assert progress["progress_pct"] == 50.0

    def test_empty_progress(self) -> None:
        """Bos strateji icin 0 ilerleme."""
        eng = _make_engine()
        progress = eng.get_progress("yok")
        assert progress["total"] == 0
        assert progress["progress_pct"] == 0.0


class TestCheckpoints:
    """ExecutionEngine checkpoint testleri."""

    def test_create_checkpoint(self) -> None:
        """Checkpoint olusturma."""
        _, eng, sid = _create_test_strategy()
        eng.schedule_tasks(sid)
        cp = eng.create_checkpoint(sid, "v1")
        assert cp.strategy_id == sid
        assert cp.description == "v1"
        assert "executions" in cp.state_snapshot

    def test_rollback(self) -> None:
        """Checkpoint'e geri donme."""
        _, eng, sid = _create_test_strategy()
        execs = eng.schedule_tasks(sid)
        cp = eng.create_checkpoint(sid, "onceki")

        eng.start_task(execs[0].id)
        eng.complete_task(execs[0].id)

        assert eng.rollback_to_checkpoint(cp.id) is True
        assert cp.status == CheckpointStatus.RESTORED

    def test_rollback_nonexistent(self) -> None:
        """Var olmayan checkpoint."""
        eng = _make_engine()
        assert eng.rollback_to_checkpoint("yok") is False


class TestPauseResume:
    """ExecutionEngine pause/resume testleri."""

    def test_pause(self) -> None:
        """Strateji durdurma."""
        _, eng, sid = _create_test_strategy()
        execs = eng.schedule_tasks(sid)
        eng.start_task(execs[0].id)
        paused = eng.pause_strategy(sid)
        assert paused == 1
        assert execs[0].status == ExecutionStatus.PAUSED

    def test_resume(self) -> None:
        """Strateji devam ettirme."""
        _, eng, sid = _create_test_strategy()
        execs = eng.schedule_tasks(sid)
        eng.start_task(execs[0].id)
        eng.pause_strategy(sid)
        resumed = eng.resume_strategy(sid)
        assert resumed == 1
        assert execs[0].status == ExecutionStatus.RUNNING


# ============================================================
# PerformanceAnalyzer Testleri
# ============================================================


class TestPerformanceAnalyzerInit:
    """PerformanceAnalyzer baslatma testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler."""
        pa = _make_analyzer()
        assert pa.kpi_count == 0
        assert pa.anomaly_count == 0


class TestDefineKPI:
    """PerformanceAnalyzer.define_kpi testleri."""

    def test_define(self) -> None:
        """KPI tanimlama."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Gelir", unit="TL", target_value=100000)
        assert kpi.name == "Gelir"
        assert kpi.target_value == 100000
        assert pa.kpi_count == 1

    def test_direction(self) -> None:
        """KPI yonu."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Maliyet", direction=KPIDirection.LOWER_IS_BETTER)
        assert kpi.direction == KPIDirection.LOWER_IS_BETTER


class TestRecordValue:
    """PerformanceAnalyzer.record_value testleri."""

    def test_record(self) -> None:
        """Deger kaydetme."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Satis")
        dp = pa.record_value(kpi.id, 150.0)
        assert dp is not None
        assert dp.value == 150.0

    def test_record_nonexistent(self) -> None:
        """Var olmayan KPI'a kayit."""
        pa = _make_analyzer()
        assert pa.record_value("yok", 100) is None

    def test_latest_value(self) -> None:
        """Son deger getirme."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Test")
        pa.record_value(kpi.id, 10.0)
        pa.record_value(kpi.id, 20.0)
        assert pa.get_latest_value(kpi.id) == 20.0


class TestCompareGoalVsActual:
    """PerformanceAnalyzer.compare_goal_vs_actual testleri."""

    def test_on_track(self) -> None:
        """Hedefe uygun."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Gelir", target_value=100, direction=KPIDirection.HIGHER_IS_BETTER)
        pa.record_value(kpi.id, 120)
        result = pa.compare_goal_vs_actual(kpi.id)
        assert result["on_track"] is True
        assert result["gap"] == 20

    def test_off_track(self) -> None:
        """Hedefin altinda."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Gelir", target_value=100, direction=KPIDirection.HIGHER_IS_BETTER)
        pa.record_value(kpi.id, 80)
        result = pa.compare_goal_vs_actual(kpi.id)
        assert result["on_track"] is False

    def test_lower_is_better(self) -> None:
        """Dusuk hedef."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Maliyet", target_value=50, direction=KPIDirection.LOWER_IS_BETTER)
        pa.record_value(kpi.id, 30)
        result = pa.compare_goal_vs_actual(kpi.id)
        assert result["on_track"] is True

    def test_nonexistent_kpi(self) -> None:
        """Var olmayan KPI."""
        pa = _make_analyzer()
        assert pa.compare_goal_vs_actual("yok") == {}


class TestDetectTrend:
    """PerformanceAnalyzer.detect_trend testleri."""

    def test_increasing(self) -> None:
        """Artan trend."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Test")
        for v in [10, 20, 30, 40, 50]:
            pa.record_value(kpi.id, v)
        assert pa.detect_trend(kpi.id) == "increasing"

    def test_decreasing(self) -> None:
        """Azalan trend."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Test")
        for v in [50, 40, 30, 20, 10]:
            pa.record_value(kpi.id, v)
        assert pa.detect_trend(kpi.id) == "decreasing"

    def test_stable(self) -> None:
        """Sabit trend."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Test")
        for v in [50, 50, 50, 50, 50]:
            pa.record_value(kpi.id, v)
        assert pa.detect_trend(kpi.id) == "stable"

    def test_insufficient_data(self) -> None:
        """Yetersiz veri."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Test")
        pa.record_value(kpi.id, 10)
        assert pa.detect_trend(kpi.id) == "stable"


class TestDetectAnomalies:
    """PerformanceAnalyzer.detect_anomalies testleri."""

    def test_detect_anomaly(self) -> None:
        """Anomali tespiti."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Test")
        for v in [10, 10, 10, 10, 10, 10, 10, 10, 10, 100]:
            pa.record_value(kpi.id, v)
        anomalies = pa.detect_anomalies(kpi.id)
        assert len(anomalies) > 0
        assert pa.anomaly_count > 0

    def test_no_anomaly(self) -> None:
        """Anomali yok."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Test")
        for v in [10, 10, 10, 10, 10]:
            pa.record_value(kpi.id, v)
        anomalies = pa.detect_anomalies(kpi.id)
        assert len(anomalies) == 0

    def test_insufficient_data(self) -> None:
        """Yetersiz veri."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Test")
        pa.record_value(kpi.id, 10)
        pa.record_value(kpi.id, 100)
        assert pa.detect_anomalies(kpi.id) == []


class TestGenerateReport:
    """PerformanceAnalyzer.generate_report testleri."""

    def test_report(self) -> None:
        """Rapor uretimi."""
        pa = _make_analyzer()
        kpi = pa.define_kpi("Gelir", target_value=100)
        pa.record_value(kpi.id, 120)
        report = pa.generate_report(strategy_id="s-1")
        assert report.strategy_id == "s-1"
        assert "Gelir" in report.kpi_results
        assert len(report.summary) > 0

    def test_empty_report(self) -> None:
        """Bos rapor."""
        pa = _make_analyzer()
        report = pa.generate_report()
        assert report.summary.startswith("0 KPI")


# ============================================================
# BusinessOptimizer Testleri
# ============================================================


class TestBusinessOptimizerInit:
    """BusinessOptimizer baslatma testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler."""
        opt = _make_optimizer()
        assert opt.experiment_count == 0
        assert opt.suggestion_count == 0


class TestCreateExperiment:
    """BusinessOptimizer.create_experiment testleri."""

    def test_create(self) -> None:
        """Deney olusturma."""
        opt = _make_optimizer()
        exp = opt.create_experiment(
            "Fiyat testi",
            metric_name="conversion_rate",
            variants=[
                {"name": "control", "parameters": {"price": 100}},
                {"name": "variant_a", "parameters": {"price": 90}},
            ],
        )
        assert exp.name == "Fiyat testi"
        assert len(exp.variants) == 2
        assert exp.status == ExperimentStatus.DRAFT


class TestExperimentLifecycle:
    """Deney yasam dongusu testleri."""

    def test_start(self) -> None:
        """Deney baslatma."""
        opt = _make_optimizer()
        exp = opt.create_experiment("Test", "metric", [{"name": "a"}, {"name": "b"}])
        assert opt.start_experiment(exp.id) is True
        assert exp.status == ExperimentStatus.RUNNING

    def test_start_already_running(self) -> None:
        """Zaten calisan deney baslatilamaz."""
        opt = _make_optimizer()
        exp = opt.create_experiment("Test", "metric", [{"name": "a"}, {"name": "b"}])
        opt.start_experiment(exp.id)
        assert opt.start_experiment(exp.id) is False

    def test_record_and_conclude(self) -> None:
        """Sonuc kaydedip sonuclandirma."""
        opt = _make_optimizer()
        exp = opt.create_experiment("Test", "rate", [{"name": "a"}, {"name": "b"}])
        opt.start_experiment(exp.id)

        opt.record_result(exp.id, exp.variants[0].id, 0.15)
        opt.record_result(exp.id, exp.variants[1].id, 0.22)

        winner_id = opt.conclude_experiment(exp.id)
        assert winner_id == exp.variants[1].id
        assert exp.status == ExperimentStatus.CONCLUDED

    def test_conclude_no_data(self) -> None:
        """Veri olmadan sonuclandirma basarisiz."""
        opt = _make_optimizer()
        exp = opt.create_experiment("Test", "rate", [{"name": "a"}])
        opt.start_experiment(exp.id)
        assert opt.conclude_experiment(exp.id) is None


class TestParameterTuning:
    """BusinessOptimizer parametre ayarlama testleri."""

    def test_tune(self) -> None:
        """Parametre ayarlama."""
        opt = _make_optimizer()
        old = opt.tune_parameter("bid_multiplier", 1.5)
        assert old is None
        assert opt.get_parameter("bid_multiplier") == 1.5

    def test_tune_update(self) -> None:
        """Parametre guncelleme."""
        opt = _make_optimizer()
        opt.tune_parameter("x", 10)
        old = opt.tune_parameter("x", 20)
        assert old == 10
        assert opt.get_parameter("x") == 20

    def test_get_default(self) -> None:
        """Varsayilan deger."""
        opt = _make_optimizer()
        assert opt.get_parameter("yok", 42) == 42


class TestResourceAllocation:
    """BusinessOptimizer kaynak dagitimi testleri."""

    def test_allocate(self) -> None:
        """Kaynak dagitimi."""
        opt = _make_optimizer()
        assert opt.allocate_resources({"marketing": 40, "development": 30}) is True
        alloc = opt.get_resource_allocation()
        assert alloc["marketing"] == 40

    def test_allocate_over_100(self) -> None:
        """%100'u asan dagilim reddedilir."""
        opt = _make_optimizer()
        assert opt.allocate_resources({"a": 60, "b": 50}) is False


class TestSuggestImprovement:
    """BusinessOptimizer oneri testleri."""

    def test_suggest(self) -> None:
        """Iyilestirme onerisi."""
        opt = _make_optimizer()
        s = opt.suggest_improvement("marketing", "A/B test ekle", expected_improvement=15)
        assert s.area == "marketing"
        assert not s.applied
        assert opt.suggestion_count == 1

    def test_apply(self) -> None:
        """Oneri uygulama."""
        opt = _make_optimizer()
        s = opt.suggest_improvement("ops", "otomasyon")
        assert opt.apply_suggestion(s.id) is True
        assert s.applied is True
        assert opt.apply_suggestion(s.id) is False  # Tekrar uygulanamaz

    def test_pending_suggestions(self) -> None:
        """Bekleyen oneriler."""
        opt = _make_optimizer()
        opt.suggest_improvement("a", "x")
        s2 = opt.suggest_improvement("b", "y")
        opt.apply_suggestion(s2.id)
        pending = opt.get_pending_suggestions()
        assert len(pending) == 1


class TestCostReduction:
    """BusinessOptimizer maliyet azaltma testleri."""

    def test_suggest_cost_reductions(self) -> None:
        """Maliyet azaltma onerileri."""
        opt = _make_optimizer()
        suggestions = opt.suggest_cost_reductions(
            {"pazarlama": 5000, "altyapi": 3000, "personel": 10000},
            target_reduction_pct=10,
        )
        assert len(suggestions) > 0
        assert all(s.area in ["personel", "pazarlama", "altyapi"] for s in suggestions)

    def test_empty_costs(self) -> None:
        """Bos maliyet."""
        opt = _make_optimizer()
        assert opt.suggest_cost_reductions({}) == []


# ============================================================
# FeedbackLoop Testleri
# ============================================================


class TestFeedbackLoopInit:
    """FeedbackLoop baslatma testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler."""
        fl = _make_feedback()
        assert fl.feedback_count == 0
        assert fl.insight_count == 0


class TestCollectResult:
    """FeedbackLoop.collect_result testleri."""

    def test_collect_success(self) -> None:
        """Basarili sonuc toplama."""
        fl = _make_feedback()
        entry = fl.collect_result("s-1", "success", lessons=["iyi planlama"])
        assert entry.outcome == "success"
        assert fl.feedback_count == 1

    def test_collect_failure(self) -> None:
        """Basarisiz sonuc toplama."""
        fl = _make_feedback()
        entry = fl.collect_result("s-2", "failure", lessons=["kaynak yetersiz"])
        assert entry.outcome == "failure"

    def test_collect_with_metrics(self) -> None:
        """Metrik ile sonuc toplama."""
        fl = _make_feedback()
        entry = fl.collect_result("s-1", "success", metrics={"revenue": 5000})
        assert entry.metrics["revenue"] == 5000


class TestExtractLearning:
    """FeedbackLoop.extract_learning testleri."""

    def test_extract_from_success(self) -> None:
        """Basaridan ogrenme cikarma."""
        fl = _make_feedback()
        entry = fl.collect_result("s-1", "success", lessons=["erken test onemli"])
        insight = fl.extract_learning(entry.id)
        assert insight is not None
        assert insight.insight_type == InsightType.SUCCESS_PATTERN
        assert insight.confidence == 0.8

    def test_extract_from_failure(self) -> None:
        """Basarisizliktan ogrenme cikarma."""
        fl = _make_feedback()
        entry = fl.collect_result("s-2", "failure", lessons=["butce asimi"])
        insight = fl.extract_learning(entry.id)
        assert insight is not None
        assert insight.insight_type == InsightType.FAILURE_LESSON

    def test_extract_no_lessons(self) -> None:
        """Ders olmadan cikarma."""
        fl = _make_feedback()
        entry = fl.collect_result("s-1", "success")
        assert fl.extract_learning(entry.id) is None

    def test_extract_nonexistent(self) -> None:
        """Var olmayan geri bildirim."""
        fl = _make_feedback()
        assert fl.extract_learning("yok") is None


class TestAdjustStrategy:
    """FeedbackLoop.adjust_strategy testleri."""

    def test_adjust(self) -> None:
        """Strateji duzeltme."""
        fl = _make_feedback()
        adj = fl.adjust_strategy("s-1", adjustment_type="pivot", description="yeni hedef")
        assert adj.strategy_id == "s-1"
        assert adj.adjustment_type == "pivot"


class TestContinuousImprovement:
    """FeedbackLoop.continuous_improvement testleri."""

    def test_actionable_insights(self) -> None:
        """Eyleme gecirilebilir ic goruler."""
        fl = _make_feedback()
        e1 = fl.collect_result("s-1", "success", lessons=["erken test"])
        e2 = fl.collect_result("s-2", "failure", lessons=["kaynak azligi"])
        fl.extract_learning(e1.id)
        fl.extract_learning(e2.id)

        improvements = fl.continuous_improvement(min_confidence=0.5)
        assert len(improvements) == 2

    def test_filter_low_confidence(self) -> None:
        """Dusuk guvenli ic goruleri filtrele."""
        fl = _make_feedback()
        e = fl.collect_result("s-1", "partial", lessons=["belirsiz sonuc"])
        fl.extract_learning(e.id)

        improvements = fl.continuous_improvement(min_confidence=0.6)
        assert len(improvements) == 0


class TestKnowledgeBase:
    """FeedbackLoop bilgi tabani testleri."""

    def test_update_and_query(self) -> None:
        """Bilgi tabani guncelleme ve sorgulama."""
        fl = _make_feedback()
        fl.update_knowledge_base("kozmetik", "parfum trendi yukseliyor")
        fl.update_knowledge_base("kozmetik", "dogal icerik onemli")

        results = fl.query_knowledge("kozmetik")
        assert len(results) == 2

    def test_query_empty(self) -> None:
        """Bos konu sorgusu."""
        fl = _make_feedback()
        assert fl.query_knowledge("yok") == []

    def test_knowledge_topics(self) -> None:
        """Bilgi tabani konulari."""
        fl = _make_feedback()
        fl.update_knowledge_base("a", "1")
        fl.update_knowledge_base("b", "2")
        assert set(fl.knowledge_topics) == {"a", "b"}


class TestGetStrategyFeedback:
    """FeedbackLoop.get_strategy_feedback testleri."""

    def test_filter_by_strategy(self) -> None:
        """Stratejiye gore filtreleme."""
        fl = _make_feedback()
        fl.collect_result("s-1", "success")
        fl.collect_result("s-2", "failure")
        fl.collect_result("s-1", "partial")

        fb = fl.get_strategy_feedback("s-1")
        assert len(fb) == 2


class TestMarkInsightApplied:
    """FeedbackLoop.mark_insight_applied testleri."""

    def test_mark(self) -> None:
        """Ic goru uygulama isareti."""
        fl = _make_feedback()
        e = fl.collect_result("s-1", "success", lessons=["x"])
        insight = fl.extract_learning(e.id)
        assert insight is not None
        assert fl.mark_insight_applied(insight.id) is True
        assert insight.applied_count == 1

    def test_mark_nonexistent(self) -> None:
        """Var olmayan ic goru."""
        fl = _make_feedback()
        assert fl.mark_insight_applied("yok") is False


# ============================================================
# AutonomousCycle Testleri
# ============================================================


class TestAutonomousCycleInit:
    """AutonomousCycle baslatma testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler."""
        ac = _make_cycle()
        assert ac.status == CycleStatus.IDLE
        assert ac.current_phase == CyclePhase.DETECT
        assert ac.cycle_count == 0
        assert not ac.is_running
        assert not ac.is_emergency

    def test_custom_params(self) -> None:
        """Ozel parametreler."""
        ac = _make_cycle(cycle_interval_minutes=30, max_parallel=5, human_approval_threshold=0.9)
        assert ac._cycle_interval_minutes == 30
        assert ac._max_parallel == 5
        assert ac._human_approval_threshold == 0.9


class TestStartCycle:
    """AutonomousCycle.start_cycle testleri."""

    def test_start(self) -> None:
        """Dongu baslatma."""
        ac = _make_cycle()
        run = ac.start_cycle()
        assert run.cycle_number == 1
        assert ac.is_running
        assert ac.current_phase == CyclePhase.DETECT
        assert ac.cycle_count == 1

    def test_multiple_starts(self) -> None:
        """Birden fazla dongu baslatma."""
        ac = _make_cycle()
        ac.start_cycle()
        ac.start_cycle()
        assert ac.cycle_count == 2


class TestAdvancePhase:
    """AutonomousCycle.advance_phase testleri."""

    def test_phase_progression(self) -> None:
        """Asama ilerlemesi."""
        ac = _make_cycle()
        ac.start_cycle()

        assert ac.advance_phase() == CyclePhase.PLAN
        assert ac.advance_phase() == CyclePhase.EXECUTE
        assert ac.advance_phase() == CyclePhase.MEASURE
        assert ac.advance_phase() == CyclePhase.OPTIMIZE

    def test_cycle_completes(self) -> None:
        """Dongu tamamlanmasi."""
        ac = _make_cycle()
        ac.start_cycle()

        for _ in range(5):
            ac.advance_phase()

        assert ac.current_phase == CyclePhase.DETECT
        assert ac.status == CycleStatus.IDLE

    def test_update_run_stats(self) -> None:
        """Dongu istatistikleri."""
        ac = _make_cycle()
        run = ac.start_cycle()
        ac.update_run_stats(opportunities_found=3, strategies_created=1)
        assert run.opportunities_found == 3
        assert run.strategies_created == 1


class TestSleepWake:
    """AutonomousCycle uyku/uyanma testleri."""

    def test_sleep(self) -> None:
        """Uyku moduna gecis."""
        ac = _make_cycle()
        ac.start_cycle()
        ac.enter_sleep()
        assert ac.status == CycleStatus.PAUSED
        assert ac.current_phase == CyclePhase.SLEEP
        assert ac._last_sleep is not None

    def test_wake(self) -> None:
        """Uyanma."""
        ac = _make_cycle()
        ac.start_cycle()
        ac.enter_sleep()
        ac.wake_up()
        assert ac.status == CycleStatus.RUNNING
        assert ac.current_phase == CyclePhase.DETECT


class TestPriorityManagement:
    """AutonomousCycle oncelik yonetimi testleri."""

    def test_add_and_get(self) -> None:
        """Oncelik ekleme ve alma."""
        ac = _make_cycle()
        ac.add_priority_item(2, {"task": "low"})
        ac.add_priority_item(1, {"task": "high"})
        ac.add_priority_item(1, {"task": "high2"})

        item = ac.get_next_priority()
        assert item is not None
        assert item["task"] == "high"

    def test_priority_order(self) -> None:
        """Oncelik sirasi."""
        ac = _make_cycle()
        ac.add_priority_item(3, {"task": "c"})
        ac.add_priority_item(1, {"task": "a"})
        ac.add_priority_item(2, {"task": "b"})

        assert ac.get_next_priority()["task"] == "a"
        assert ac.get_next_priority()["task"] == "b"
        assert ac.get_next_priority()["task"] == "c"

    def test_empty_priority(self) -> None:
        """Bos kuyruk."""
        ac = _make_cycle()
        assert ac.get_next_priority() is None


class TestEmergencyHandling:
    """AutonomousCycle acil durum testleri."""

    def test_handle_emergency(self) -> None:
        """Acil durum isleme."""
        ac = _make_cycle()
        ac.start_cycle()
        esc = ac.handle_emergency("sunucu coktu")
        assert ac.is_emergency
        assert ac.status == CycleStatus.EMERGENCY
        assert esc.level == EscalationLevel.EMERGENCY
        assert esc.requires_response is True

    def test_respond_to_emergency(self) -> None:
        """Acil duruma yanit."""
        ac = _make_cycle()
        ac.start_cycle()
        esc = ac.handle_emergency("kritik hata")
        ac.respond_to_escalation(esc.id, "duzeltildi")
        assert not ac.is_emergency
        assert ac.status == CycleStatus.RUNNING


class TestEscalation:
    """AutonomousCycle eskalasyon testleri."""

    def test_escalate_info(self) -> None:
        """Bilgi eskalasyonu."""
        ac = _make_cycle()
        ac.start_cycle()
        esc = ac.escalate("bilgilendirme", level=EscalationLevel.INFO)
        assert esc.level == EscalationLevel.INFO
        assert ac.escalation_count == 1

    def test_escalate_approval(self) -> None:
        """Onay eskalasyonu."""
        ac = _make_cycle()
        esc = ac.escalate("butce onay", level=EscalationLevel.APPROVAL_NEEDED, requires_response=True)
        assert esc.requires_response is True

    def test_pending_escalations(self) -> None:
        """Bekleyen eskalasyonlar."""
        ac = _make_cycle()
        ac.escalate("a", level=EscalationLevel.INFO, requires_response=True)
        ac.escalate("b", level=EscalationLevel.WARNING, requires_response=False)
        pending = ac.get_pending_escalations()
        assert len(pending) == 1

    def test_respond(self) -> None:
        """Eskalasyon yaniti."""
        ac = _make_cycle()
        esc = ac.escalate("test", requires_response=True)
        assert ac.respond_to_escalation(esc.id, "onaylandi") is True
        assert esc.response == "onaylandi"

    def test_respond_nonexistent(self) -> None:
        """Var olmayan eskalasyon."""
        ac = _make_cycle()
        assert ac.respond_to_escalation("yok", "x") is False


class TestNeedsApproval:
    """AutonomousCycle.needs_approval testleri."""

    def test_high_risk_needs_approval(self) -> None:
        """Yuksek risk onay gerektirir."""
        ac = _make_cycle(human_approval_threshold=0.7)
        assert ac.needs_approval(0.8) is True

    def test_low_risk_no_approval(self) -> None:
        """Dusuk risk onay gerektirmez."""
        ac = _make_cycle(human_approval_threshold=0.7)
        assert ac.needs_approval(0.5) is False


class TestStopCycle:
    """AutonomousCycle.stop testleri."""

    def test_stop(self) -> None:
        """Dongu durdurma."""
        ac = _make_cycle()
        ac.start_cycle()
        ac.stop()
        assert ac.status == CycleStatus.STOPPED

    def test_run_history(self) -> None:
        """Dongu gecmisi."""
        ac = _make_cycle()
        ac.start_cycle()
        ac.start_cycle()
        history = ac.get_run_history()
        assert len(history) == 2


# ============================================================
# BusinessMemory Testleri
# ============================================================


class TestBusinessMemoryInit:
    """BusinessMemory baslatma testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler."""
        bm = _make_memory()
        stats = bm.get_stats()
        assert stats.total_success_patterns == 0
        assert stats.total_failure_lessons == 0


class TestSuccessPatterns:
    """BusinessMemory basari oruntuleri testleri."""

    def test_record_success(self) -> None:
        """Basari kaydı."""
        bm = _make_memory()
        p = bm.record_success("erken lansman", conditions={"pazar": "hazir"}, confidence=0.8)
        assert p.pattern_name == "erken lansman"
        assert p.confidence == 0.8

    def test_find_patterns(self) -> None:
        """Yuksek guvenli oruntu arama."""
        bm = _make_memory()
        bm.record_success("a", confidence=0.3)
        bm.record_success("b", confidence=0.8)
        bm.record_success("c", confidence=0.9)

        patterns = bm.find_success_patterns(min_confidence=0.7)
        assert len(patterns) == 2
        assert patterns[0].confidence >= patterns[1].confidence

    def test_use_pattern(self) -> None:
        """Oruntu kullanimi."""
        bm = _make_memory()
        p = bm.record_success("test")
        assert bm.use_pattern(p.id) is True
        assert p.usage_count == 1
        assert p.last_used is not None

    def test_use_nonexistent(self) -> None:
        """Var olmayan oruntu."""
        bm = _make_memory()
        assert bm.use_pattern("yok") is False


class TestFailureLessons:
    """BusinessMemory basarisizlik dersleri testleri."""

    def test_record_failure(self) -> None:
        """Basarisizlik kaydi."""
        bm = _make_memory()
        l = bm.record_failure("butce asimi", root_cause="kotu planlama", severity=0.8)
        assert l.title == "butce asimi"
        assert l.severity == 0.8

    def test_get_lessons(self) -> None:
        """Ders arama."""
        bm = _make_memory()
        bm.record_failure("a", severity=0.3)
        bm.record_failure("b", severity=0.9)

        lessons = bm.get_failure_lessons(min_severity=0.5)
        assert len(lessons) == 1
        assert lessons[0].title == "b"

    def test_severity_clamped(self) -> None:
        """Ciddiyet sinirlandirmasi."""
        bm = _make_memory()
        l = bm.record_failure("x", severity=1.5)
        assert l.severity == 1.0


class TestMarketKnowledge:
    """BusinessMemory pazar bilgisi testleri."""

    def test_store(self) -> None:
        """Pazar bilgisi depolama."""
        bm = _make_memory()
        mk = bm.store_market_knowledge("kozmetik", "parfum trendi", reliability=0.9)
        assert mk.domain == "kozmetik"

    def test_query_by_domain(self) -> None:
        """Alana gore sorgulama."""
        bm = _make_memory()
        bm.store_market_knowledge("kozmetik", "a")
        bm.store_market_knowledge("medikal", "b")
        bm.store_market_knowledge("kozmetik", "c")

        results = bm.query_market(domain="kozmetik")
        assert len(results) == 2

    def test_query_by_reliability(self) -> None:
        """Guvenilirlige gore sorgulama."""
        bm = _make_memory()
        bm.store_market_knowledge("x", "low", reliability=0.2)
        bm.store_market_knowledge("x", "high", reliability=0.9)

        results = bm.query_market(min_reliability=0.5)
        assert len(results) == 1


class TestCustomerInsights:
    """BusinessMemory musteri ic goruleri testleri."""

    def test_record(self) -> None:
        """Musteri ic gorusu kaydi."""
        bm = _make_memory()
        ci = bm.record_customer_insight("premium", "kaliteye onem verir", impact_score=0.9)
        assert ci.segment == "premium"
        assert ci.impact_score == 0.9

    def test_filter_by_segment(self) -> None:
        """Segmente gore filtreleme."""
        bm = _make_memory()
        bm.record_customer_insight("premium", "a")
        bm.record_customer_insight("budget", "b")
        bm.record_customer_insight("premium", "c")

        results = bm.get_customer_insights(segment="premium")
        assert len(results) == 2

    def test_all_segments(self) -> None:
        """Tum segmentler."""
        bm = _make_memory()
        bm.record_customer_insight("a", "x")
        bm.record_customer_insight("b", "y")
        assert len(bm.get_customer_insights()) == 2


class TestCompetitiveIntel:
    """BusinessMemory rekabet istihbarati testleri."""

    def test_record_competitor(self) -> None:
        """Rakip kaydi."""
        bm = _make_memory()
        comp = bm.record_competitor("RakipA", strengths=["fiyat"], threat_level=0.7)
        assert comp.name == "RakipA"
        assert comp.threat_level == 0.7

    def test_get_by_threat(self) -> None:
        """Tehdit seviyesine gore getirme."""
        bm = _make_memory()
        bm.record_competitor("zayif", threat_level=0.2)
        bm.record_competitor("guclu", threat_level=0.9)

        comps = bm.get_competitors(min_threat=0.5)
        assert len(comps) == 1
        assert comps[0].name == "guclu"


class TestBusinessMemoryStats:
    """BusinessMemory istatistik testleri."""

    def test_stats(self) -> None:
        """Istatistik hesaplama."""
        bm = _make_memory()
        bm.record_success("a", confidence=0.8)
        bm.record_success("b", confidence=0.6)
        bm.record_failure("c")
        bm.store_market_knowledge("d", "e")
        bm.record_customer_insight("f", "g")
        bm.record_competitor("h")

        stats = bm.get_stats()
        assert stats.total_success_patterns == 2
        assert stats.total_failure_lessons == 1
        assert stats.total_market_knowledge == 1
        assert stats.total_customer_insights == 1
        assert stats.total_competitor_records == 1
        assert stats.avg_pattern_confidence == 0.7


class TestBusinessMemorySearch:
    """BusinessMemory.search testleri."""

    def test_search_patterns(self) -> None:
        """Basari oruntuleri arama."""
        bm = _make_memory()
        bm.record_success("erken lansman stratejisi")
        results = bm.search("lansman")
        assert len(results) == 1
        assert results[0]["type"] == "success_pattern"

    def test_search_failures(self) -> None:
        """Basarisizlik dersleri arama."""
        bm = _make_memory()
        bm.record_failure("butce asimi problemi")
        results = bm.search("butce")
        assert len(results) == 1
        assert results[0]["type"] == "failure_lesson"

    def test_search_market(self) -> None:
        """Pazar bilgisi arama."""
        bm = _make_memory()
        bm.store_market_knowledge("x", "parfum trendi")
        results = bm.search("parfum")
        assert len(results) == 1

    def test_search_customer(self) -> None:
        """Musteri ic gorusu arama."""
        bm = _make_memory()
        bm.record_customer_insight("premium", "kaliteye onem verir")
        results = bm.search("kalite")
        assert len(results) == 1

    def test_search_competitor(self) -> None:
        """Rakip arama."""
        bm = _make_memory()
        bm.record_competitor("MegaCorp")
        results = bm.search("mega")
        assert len(results) == 1

    def test_search_no_results(self) -> None:
        """Sonucsuz arama."""
        bm = _make_memory()
        assert bm.search("bilinmeyen") == []

    def test_search_cross_category(self) -> None:
        """Kategoriler arasi arama."""
        bm = _make_memory()
        bm.record_success("kozmetik basarisi")
        bm.store_market_knowledge("kozmetik", "yukselen trend")
        results = bm.search("kozmetik")
        assert len(results) == 2


# ============================================================
# Entegrasyon Testleri
# ============================================================


class TestEndToEndCycle:
    """Uc-uca dongu testleri."""

    def test_full_cycle(self) -> None:
        """Tam dongu: Detect -> Plan -> Execute -> Measure -> Optimize."""
        # 1. Detect
        detector = _make_detector()
        detector.add_signal("web", "sac ekimi talebi artisi", strength=0.9)
        opps = detector.scan_market("medikal turizm")
        assert len(opps) == 1

        # 2. Plan
        gen = _make_generator()
        strategy = gen.create_strategy(
            "Sac ekimi kampanyasi",
            opportunity_id=opps[0].id,
            goals=["reklam ver", "hasta topla"],
        )
        gen.decompose_goals(strategy.id)
        gen.estimate_resources(strategy.id)
        gen.assess_risks(strategy.id)
        gen.project_roi(strategy.id, investment=5000)
        assert gen.is_viable(strategy.id)
        gen.activate_strategy(strategy.id)

        # 3. Execute
        engine = _make_engine()
        engine.register_strategy(strategy)
        execs = engine.schedule_tasks(strategy.id)
        engine.start_task(execs[0].id)
        engine.complete_task(execs[0].id, {"leads": 50})
        engine.start_task(execs[1].id)
        engine.complete_task(execs[1].id, {"patients": 10})
        progress = engine.get_progress(strategy.id)
        assert progress["progress_pct"] == 100.0

        # 4. Measure
        analyzer = _make_analyzer()
        kpi = analyzer.define_kpi("Hasta sayisi", target_value=15)
        analyzer.record_value(kpi.id, 10)
        comparison = analyzer.compare_goal_vs_actual(kpi.id)
        assert comparison["on_track"] is False

        # 5. Optimize + Feedback
        feedback = _make_feedback()
        entry = feedback.collect_result(strategy.id, "partial", lessons=["hedef tutmadi"])
        insight = feedback.extract_learning(entry.id)
        assert insight is not None

        optimizer = _make_optimizer()
        suggestion = optimizer.suggest_improvement(
            "marketing", "bid artir", expected_improvement=20,
        )
        assert suggestion is not None

        # 6. Memory
        memory = _make_memory()
        memory.record_success("sac ekimi kampanyasi", confidence=0.6)
        memory.store_market_knowledge("medikal", "sac ekimi talebi artiyor")

    def test_cycle_with_autonomous_runner(self) -> None:
        """Otonom dongu entegrasyonu."""
        cycle = _make_cycle(human_approval_threshold=0.8)
        run = cycle.start_cycle()

        # DETECT
        assert cycle.current_phase == CyclePhase.DETECT
        cycle.update_run_stats(opportunities_found=2)

        # PLAN
        cycle.advance_phase()
        assert cycle.current_phase == CyclePhase.PLAN
        cycle.update_run_stats(strategies_created=1)

        # Yuksek riskli strateji onay gerektirir
        assert cycle.needs_approval(0.9) is True
        esc = cycle.escalate("Yuksek riskli strateji onayi", level=EscalationLevel.APPROVAL_NEEDED, requires_response=True)
        cycle.respond_to_escalation(esc.id, "onaylandi")

        # EXECUTE
        cycle.advance_phase()
        assert cycle.current_phase == CyclePhase.EXECUTE
        cycle.update_run_stats(tasks_executed=3)

        # MEASURE
        cycle.advance_phase()
        assert cycle.current_phase == CyclePhase.MEASURE

        # OPTIMIZE
        cycle.advance_phase()
        assert cycle.current_phase == CyclePhase.OPTIMIZE
        cycle.update_run_stats(optimizations_applied=1)

        # Dongu tamamlanir
        cycle.advance_phase()
        assert cycle.status == CycleStatus.IDLE

        assert run.opportunities_found == 2
        assert run.strategies_created == 1
        assert run.tasks_executed == 3
        assert run.optimizations_applied == 1

    def test_emergency_interruption(self) -> None:
        """Acil durum kesintisi."""
        cycle = _make_cycle()
        cycle.start_cycle()
        cycle.advance_phase()  # PLAN

        # Acil durum
        esc = cycle.handle_emergency("sunucu coktu", context={"server": "prod-1"})
        assert cycle.is_emergency
        assert cycle.status == CycleStatus.EMERGENCY

        # Cozum
        cycle.respond_to_escalation(esc.id, "sunucu yeniden baslatildi")
        assert not cycle.is_emergency
        assert cycle.status == CycleStatus.RUNNING
