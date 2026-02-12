"""StrategyEngine testleri.

Strateji motoru: kayit, degerlendirme, adaptasyon,
senaryo planlama ve KPI trend testleri.
"""

import pytest

from app.core.planning.strategy import StrategyEngine
from app.models.planning import (
    Scenario,
    ScenarioLikelihood,
    Strategy,
    StrategyType,
)


# === Yardimci fonksiyonlar ===


def _make_engine() -> StrategyEngine:
    """Bos StrategyEngine olusturur."""
    return StrategyEngine()


def _growth_strategy(
    kpis: dict[str, float] | None = None,
    time_horizon: int = 30,
) -> Strategy:
    """Buyume stratejisi olusturur."""
    return Strategy(
        name="Growth",
        strategy_type=StrategyType.AGGRESSIVE,
        goals=["increase_revenue", "expand_market"],
        kpis=kpis or {"revenue": 10000.0, "customers": 500.0},
        time_horizon=time_horizon,
        confidence=0.7,
    )


def _defensive_strategy() -> Strategy:
    """Savunma stratejisi olusturur."""
    return Strategy(
        name="Defense",
        strategy_type=StrategyType.DEFENSIVE,
        goals=["reduce_cost"],
        kpis={"cost": 5000.0, "churn": 10.0},
        confidence=0.6,
    )


def _scenario(
    name: str = "Base",
    likelihood: ScenarioLikelihood = ScenarioLikelihood.POSSIBLE,
    probability: float = 0.5,
    conditions: dict | None = None,
    impact: dict | None = None,
) -> Scenario:
    """Senaryo olusturur."""
    return Scenario(
        name=name,
        likelihood=likelihood,
        probability=probability,
        conditions=conditions or {},
        impact=impact or {},
    )


# === Init Testleri ===


class TestStrategyEngineInit:
    """StrategyEngine initialization testleri."""

    def test_default(self) -> None:
        engine = _make_engine()
        assert engine.strategies == {}
        assert engine.active_strategy_id is None
        assert engine.kpi_history == {}
        assert engine.environment == {}


# === register_strategy Testleri ===


class TestStrategyEngineRegister:
    """register_strategy testleri."""

    def test_register(self) -> None:
        engine = _make_engine()
        strategy = _growth_strategy()
        engine.register_strategy(strategy)
        assert strategy.id in engine.strategies

    def test_register_multiple(self) -> None:
        engine = _make_engine()
        engine.register_strategy(_growth_strategy())
        engine.register_strategy(_defensive_strategy())
        assert len(engine.strategies) == 2


# === activate_strategy Testleri ===


class TestStrategyEngineActivate:
    """activate_strategy testleri."""

    def test_activate(self) -> None:
        engine = _make_engine()
        strategy = _growth_strategy()
        engine.register_strategy(strategy)
        result = engine.activate_strategy(strategy.id)
        assert result is True
        assert engine.active_strategy_id == strategy.id
        assert engine.strategies[strategy.id].active is True

    def test_activate_nonexistent(self) -> None:
        engine = _make_engine()
        result = engine.activate_strategy("nope")
        assert result is False

    def test_switch_active(self) -> None:
        engine = _make_engine()
        s1 = _growth_strategy()
        s2 = _defensive_strategy()
        engine.register_strategy(s1)
        engine.register_strategy(s2)
        engine.activate_strategy(s1.id)
        engine.activate_strategy(s2.id)
        assert engine.active_strategy_id == s2.id
        assert engine.strategies[s1.id].active is False
        assert engine.strategies[s2.id].active is True


# === environment Testleri ===


class TestStrategyEngineEnvironment:
    """Cevresel kosul testleri."""

    def test_update(self) -> None:
        engine = _make_engine()
        engine.update_environment({"market": "bull", "season": "summer"})
        assert engine.environment["market"] == "bull"

    def test_overwrite(self) -> None:
        engine = _make_engine()
        engine.update_environment({"market": "bull"})
        engine.update_environment({"market": "bear"})
        assert engine.environment["market"] == "bear"


# === KPI Testleri ===


class TestStrategyEngineKPI:
    """KPI kayit ve trend testleri."""

    def test_record(self) -> None:
        engine = _make_engine()
        engine.record_kpi("revenue", 5000.0)
        engine.record_kpi("revenue", 6000.0)
        assert engine.kpi_history["revenue"] == [5000.0, 6000.0]

    def test_trend_positive(self) -> None:
        engine = _make_engine()
        for v in [100.0, 120.0, 140.0, 160.0, 200.0]:
            engine.record_kpi("revenue", v)
        trend = engine.get_kpi_trend("revenue")
        assert trend is not None
        assert trend > 0  # Pozitif trend

    def test_trend_negative(self) -> None:
        engine = _make_engine()
        for v in [200.0, 180.0, 160.0, 140.0, 100.0]:
            engine.record_kpi("revenue", v)
        trend = engine.get_kpi_trend("revenue")
        assert trend is not None
        assert trend < 0

    def test_trend_insufficient_data(self) -> None:
        engine = _make_engine()
        engine.record_kpi("revenue", 100.0)
        trend = engine.get_kpi_trend("revenue")
        assert trend is None

    def test_trend_unknown_kpi(self) -> None:
        engine = _make_engine()
        trend = engine.get_kpi_trend("unknown")
        assert trend is None

    def test_trend_zero_first(self) -> None:
        engine = _make_engine()
        engine.record_kpi("x", 0.0)
        engine.record_kpi("x", 10.0)
        trend = engine.get_kpi_trend("x")
        assert trend is None  # Division by zero korunmasi

    def test_trend_window(self) -> None:
        engine = _make_engine()
        # 10 deger, son 3'u kullan
        for v in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            engine.record_kpi("x", float(v))
        trend = engine.get_kpi_trend("x", window=3)
        # Son 3: [8, 9, 10], trend = (10-8)/8 = 0.25
        assert trend == pytest.approx(0.25)


# === evaluate_strategy Testleri ===


class TestStrategyEngineEvaluate:
    """evaluate_strategy testleri."""

    async def test_basic_evaluation(self) -> None:
        engine = _make_engine()
        strategy = _growth_strategy(kpis={"revenue": 10000.0})
        engine.register_strategy(strategy)
        engine.record_kpi("revenue", 8000.0)
        evaluation = await engine.evaluate_strategy(strategy.id)
        assert 0.0 <= evaluation.score <= 1.0
        assert "revenue" in evaluation.kpi_scores

    async def test_high_performance(self) -> None:
        engine = _make_engine()
        strategy = _growth_strategy(kpis={"revenue": 10000.0})
        engine.register_strategy(strategy)
        engine.record_kpi("revenue", 9000.0)
        evaluation = await engine.evaluate_strategy(strategy.id)
        assert evaluation.score > 0.5
        assert any("hedefe yakin" in s for s in evaluation.strengths)

    async def test_low_performance(self) -> None:
        engine = _make_engine()
        strategy = _growth_strategy(kpis={"revenue": 10000.0})
        engine.register_strategy(strategy)
        engine.record_kpi("revenue", 2000.0)
        evaluation = await engine.evaluate_strategy(strategy.id)
        assert any("hedefin altinda" in w for w in evaluation.weaknesses)

    async def test_no_kpi_data(self) -> None:
        engine = _make_engine()
        strategy = _growth_strategy(kpis={"revenue": 10000.0})
        engine.register_strategy(strategy)
        evaluation = await engine.evaluate_strategy(strategy.id)
        assert any("KPI verisi yok" in w for w in evaluation.weaknesses)

    async def test_nonexistent_strategy(self) -> None:
        engine = _make_engine()
        with pytest.raises(ValueError, match="Strateji bulunamadi"):
            await engine.evaluate_strategy("nope")

    async def test_recommendation_success(self) -> None:
        engine = _make_engine()
        strategy = _growth_strategy(kpis={"revenue": 100.0})
        engine.register_strategy(strategy)
        engine.record_kpi("revenue", 90.0)
        evaluation = await engine.evaluate_strategy(strategy.id)
        assert evaluation.recommendation != ""

    async def test_zero_target_kpi(self) -> None:
        engine = _make_engine()
        strategy = Strategy(
            name="Zero",
            kpis={"errors": 0.0},
        )
        engine.register_strategy(strategy)
        engine.record_kpi("errors", 0.0)
        evaluation = await engine.evaluate_strategy(strategy.id)
        assert evaluation.kpi_scores["errors"] == 1.0

    async def test_with_scenarios(self) -> None:
        engine = _make_engine()
        scenario = _scenario(
            conditions={"market": "bull"},
            likelihood=ScenarioLikelihood.LIKELY,
        )
        strategy = Strategy(
            name="WithScenario",
            kpis={"revenue": 100.0},
            scenarios=[scenario],
        )
        engine.register_strategy(strategy)
        engine.record_kpi("revenue", 80.0)
        engine.update_environment({"market": "bull"})
        evaluation = await engine.evaluate_strategy(strategy.id)
        assert evaluation.score > 0


# === select_best_strategy Testleri ===


class TestStrategyEngineSelectBest:
    """select_best_strategy testleri."""

    async def test_empty(self) -> None:
        engine = _make_engine()
        result = await engine.select_best_strategy()
        assert result is None

    async def test_single(self) -> None:
        engine = _make_engine()
        strategy = _growth_strategy(kpis={"revenue": 100.0})
        engine.register_strategy(strategy)
        engine.record_kpi("revenue", 80.0)
        result = await engine.select_best_strategy()
        assert result is not None
        assert result.id == strategy.id

    async def test_best_of_two(self) -> None:
        engine = _make_engine()
        good = Strategy(name="Good", kpis={"revenue": 100.0}, confidence=0.9)
        bad = Strategy(name="Bad", kpis={"revenue": 100.0}, confidence=0.1)
        engine.register_strategy(good)
        engine.register_strategy(bad)
        engine.record_kpi("revenue", 90.0)
        result = await engine.select_best_strategy()
        assert result is not None
        assert result.name == "Good"


# === adapt_strategy Testleri ===


class TestStrategyEngineAdapt:
    """adapt_strategy testleri."""

    async def test_adapt_low_kpi(self) -> None:
        engine = _make_engine()
        strategy = _growth_strategy(kpis={"revenue": 10000.0})
        engine.register_strategy(strategy)
        # Dusuk performans
        for v in [2000.0, 2100.0, 2200.0, 2300.0, 2400.0]:
            engine.record_kpi("revenue", v)
        adapted = await engine.adapt_strategy(strategy.id)
        assert adapted is not None
        # Hedef gercekci seviyeye gelmeli
        assert adapted.kpis["revenue"] < 10000.0

    async def test_adapt_good_kpi(self) -> None:
        engine = _make_engine()
        strategy = _growth_strategy(kpis={"revenue": 100.0})
        engine.register_strategy(strategy)
        engine.record_kpi("revenue", 90.0)
        adapted = await engine.adapt_strategy(strategy.id)
        assert adapted is not None
        # Hedef degismemeli (performans iyi)
        assert adapted.kpis["revenue"] == 100.0

    async def test_adapt_nonexistent(self) -> None:
        engine = _make_engine()
        result = await engine.adapt_strategy("nope")
        assert result is None

    async def test_adapt_updates_confidence(self) -> None:
        engine = _make_engine()
        strategy = _growth_strategy(kpis={"revenue": 10000.0})
        engine.register_strategy(strategy)
        engine.record_kpi("revenue", 1000.0)
        adapted = await engine.adapt_strategy(strategy.id)
        assert adapted is not None
        assert 0.0 <= adapted.confidence <= 1.0


# === scenario_planning Testleri ===


class TestStrategyEngineScenarioPlanning:
    """scenario_planning testleri."""

    async def test_empty(self) -> None:
        engine = _make_engine()
        result = await engine.scenario_planning([])
        assert result == {}

    async def test_single_scenario(self) -> None:
        engine = _make_engine()
        s = _scenario(probability=0.8, impact={"revenue": 1000.0})
        result = await engine.scenario_planning([s])
        assert s.id in result
        # 0.8 * 0.5 (POSSIBLE weight) * 1000 = 400
        assert result[s.id] == pytest.approx(400.0)

    async def test_multiple_scenarios(self) -> None:
        engine = _make_engine()
        s1 = _scenario("Best", ScenarioLikelihood.VERY_LIKELY, 0.9, impact={"rev": 500.0})
        s2 = _scenario("Worst", ScenarioLikelihood.RARE, 0.1, impact={"rev": -200.0})
        result = await engine.scenario_planning([s1, s2])
        assert len(result) == 2
        assert result[s1.id] > result[s2.id]

    async def test_no_impact(self) -> None:
        engine = _make_engine()
        s = _scenario(probability=0.5)
        result = await engine.scenario_planning([s])
        assert result[s.id] == 0.0

    async def test_high_likelihood_weight(self) -> None:
        engine = _make_engine()
        vl = _scenario("VL", ScenarioLikelihood.VERY_LIKELY, 1.0, impact={"x": 100.0})
        r = _scenario("R", ScenarioLikelihood.RARE, 1.0, impact={"x": 100.0})
        result = await engine.scenario_planning([vl, r])
        # VERY_LIKELY: 1.0 * 0.9 * 100 = 90
        # RARE: 1.0 * 0.1 * 100 = 10
        assert result[vl.id] == pytest.approx(90.0)
        assert result[r.id] == pytest.approx(10.0)


# === get_active_strategy Testleri ===


class TestStrategyEngineActiveStrategy:
    """get_active_strategy testleri."""

    def test_none(self) -> None:
        engine = _make_engine()
        assert engine.get_active_strategy() is None

    def test_with_active(self) -> None:
        engine = _make_engine()
        strategy = _growth_strategy()
        engine.register_strategy(strategy)
        engine.activate_strategy(strategy.id)
        active = engine.get_active_strategy()
        assert active is not None
        assert active.id == strategy.id
