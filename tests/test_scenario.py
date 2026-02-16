"""ATLAS Scenario Planning & War Gaming testleri."""

import pytest

from app.models.scenario_models import (
    DecisionRecord,
    GameOutcome,
    ImpactLevel,
    RiskTolerance,
    ScenarioRecord,
    ScenarioType,
    SimulationRecord,
    SimulationStatus,
    StrategyType,
    WarGameRecord,
)
from app.core.scenario import (
    BestCaseOptimizer,
    DecisionTreeGenerator,
    ScenarioBuilder,
    ScenarioImpactCalculator,
    ScenarioOrchestrator,
    ScenarioProbabilityEstimator,
    StrategicRecommender,
    WarGameSimulator,
    WorstCaseAnalyzer,
)


# ── Model testleri ──


class TestScenarioType:
    def test_values(self):
        assert ScenarioType.OPTIMISTIC == "optimistic"
        assert ScenarioType.PESSIMISTIC == "pessimistic"
        assert ScenarioType.STRESS_TEST == "stress_test"

    def test_member_count(self):
        assert len(ScenarioType) == 5


class TestImpactLevel:
    def test_values(self):
        assert ImpactLevel.NEGLIGIBLE == "negligible"
        assert ImpactLevel.CRITICAL == "critical"

    def test_member_count(self):
        assert len(ImpactLevel) == 5


class TestStrategyType:
    def test_values(self):
        assert StrategyType.AGGRESSIVE == "aggressive"
        assert StrategyType.CONSERVATIVE == "conservative"

    def test_member_count(self):
        assert len(StrategyType) == 5


class TestSimulationStatus:
    def test_values(self):
        assert SimulationStatus.PENDING == "pending"
        assert SimulationStatus.COMPLETED == "completed"

    def test_member_count(self):
        assert len(SimulationStatus) == 5


class TestRiskTolerance:
    def test_values(self):
        assert RiskTolerance.VERY_LOW == "very_low"
        assert RiskTolerance.VERY_HIGH == "very_high"

    def test_member_count(self):
        assert len(RiskTolerance) == 5


class TestGameOutcome:
    def test_values(self):
        assert GameOutcome.WIN == "win"
        assert GameOutcome.PARTIAL_WIN == "partial_win"

    def test_member_count(self):
        assert len(GameOutcome) == 5


class TestScenarioRecord:
    def test_defaults(self):
        r = ScenarioRecord()
        assert len(r.scenario_id) == 8
        assert r.scenario_type == ScenarioType.REALISTIC
        assert r.probability == 0.0

    def test_custom(self):
        r = ScenarioRecord(
            name="test",
            scenario_type=ScenarioType.OPTIMISTIC,
            probability=0.8,
        )
        assert r.name == "test"
        assert r.probability == 0.8


class TestSimulationRecord:
    def test_defaults(self):
        r = SimulationRecord()
        assert len(r.simulation_id) == 8
        assert r.status == SimulationStatus.PENDING

    def test_custom(self):
        r = SimulationRecord(
            iterations=100,
            outcome=GameOutcome.WIN,
        )
        assert r.iterations == 100
        assert r.outcome == GameOutcome.WIN


class TestDecisionRecord:
    def test_defaults(self):
        r = DecisionRecord()
        assert r.strategy_type == StrategyType.BALANCED
        assert r.risk_tolerance == RiskTolerance.MEDIUM

    def test_custom(self):
        r = DecisionRecord(
            expected_value=42.5,
        )
        assert r.expected_value == 42.5


class TestWarGameRecord:
    def test_defaults(self):
        r = WarGameRecord()
        assert r.rounds == 0
        assert r.outcome == GameOutcome.UNDETERMINED

    def test_custom(self):
        r = WarGameRecord(
            players=["a", "b"],
            winner="a",
        )
        assert r.players == ["a", "b"]
        assert r.winner == "a"


# ── ScenarioBuilder testleri ──


class TestCreateScenario:
    def test_basic(self):
        b = ScenarioBuilder()
        r = b.create_scenario("market_entry", "optimistic")
        assert r["created"] is True
        assert r["name"] == "market_entry"
        assert r["type"] == "optimistic"
        assert r["scenario_id"].startswith("sc_")

    def test_count(self):
        b = ScenarioBuilder()
        b.create_scenario("s1")
        b.create_scenario("s2")
        assert b.scenario_count == 2


class TestDefineVariable:
    def test_basic(self):
        b = ScenarioBuilder()
        sc = b.create_scenario("test")
        r = b.define_variable(
            sc["scenario_id"], "price", 50.0, 10.0, 100.0,
        )
        assert r["defined"] is True
        assert r["variable"] == "price"
        assert r["base_value"] == 50.0
        assert r["range"] == [10.0, 100.0]

    def test_count(self):
        b = ScenarioBuilder()
        sc = b.create_scenario("test")
        b.define_variable(sc["scenario_id"], "v1")
        b.define_variable(sc["scenario_id"], "v2")
        assert b.variable_count == 2


class TestSetAssumption:
    def test_basic(self):
        b = ScenarioBuilder()
        sc = b.create_scenario("test")
        r = b.set_assumption(
            sc["scenario_id"], "stable_market", 0.8,
        )
        assert r["set"] is True
        assert r["confidence"] == 0.8


class TestCreateBranch:
    def test_basic(self):
        b = ScenarioBuilder()
        sc = b.create_scenario("test")
        r = b.create_branch(
            sc["scenario_id"], "expansion", 0.6,
        )
        assert r["created"] is True
        assert r["branch_name"] == "expansion"
        assert r["probability"] == 0.6


class TestGetTemplate:
    def test_found(self):
        b = ScenarioBuilder()
        r = b.get_template("market_entry")
        assert r["found"] is True
        assert "market_size" in r["variables"]

    def test_not_found(self):
        b = ScenarioBuilder()
        r = b.get_template("nonexistent")
        assert r["found"] is False


# ── ScenarioProbabilityEstimator testleri ──


class TestAssessProbability:
    def test_high(self):
        e = ScenarioProbabilityEstimator()
        r = e.assess_probability("s1", 0.8)
        assert r["assessed"] is True
        assert r["probability"] == 0.8
        assert r["level"] == "high"

    def test_with_factors(self):
        e = ScenarioProbabilityEstimator()
        r = e.assess_probability("s1", 0.5, [0.8, 0.9])
        assert r["probability"] == 0.36
        assert r["level"] == "low"

    def test_count(self):
        e = ScenarioProbabilityEstimator()
        e.assess_probability("s1")
        e.assess_probability("s2")
        assert e.assessment_count == 2


class TestIntegrateExpert:
    def test_with_data(self):
        e = ScenarioProbabilityEstimator()
        r = e.integrate_expert("s1", [0.3, 0.5, 0.7])
        assert r["integrated"] is True
        assert r["consensus"] == 0.5
        assert r["spread"] == 0.4

    def test_no_data(self):
        e = ScenarioProbabilityEstimator()
        r = e.integrate_expert("s1", [])
        assert r["integrated"] is False


class TestAnalyzeHistorical:
    def test_basic(self):
        e = ScenarioProbabilityEstimator()
        r = e.analyze_historical("s1", 3, 10)
        assert r["analyzed"] is True
        assert r["frequency"] == 0.3


class TestBayesianUpdate:
    def test_basic(self):
        e = ScenarioProbabilityEstimator()
        r = e.bayesian_update("s1", 0.5, 0.7, 0.5)
        assert r["updated"] is True
        assert r["posterior"] == 0.7

    def test_count(self):
        e = ScenarioProbabilityEstimator()
        e.bayesian_update("s1")
        e.bayesian_update("s2")
        assert e.update_count == 2


class TestConfidenceInterval:
    def test_basic(self):
        e = ScenarioProbabilityEstimator()
        r = e.confidence_interval("s1", 0.5, 100)
        assert r["calculated"] is True
        assert r["lower"] < 0.5
        assert r["upper"] > 0.5
        assert r["margin"] > 0


# ── ScenarioImpactCalculator testleri ──


class TestCalculateFinancial:
    def test_positive(self):
        c = ScenarioImpactCalculator()
        r = c.calculate_financial("s1", 100000, 30000, 20000)
        assert r["calculated"] is True
        assert r["net_impact"] == 50000.0
        assert r["direction"] == "positive"

    def test_negative(self):
        c = ScenarioImpactCalculator()
        r = c.calculate_financial("s1", 10000, 30000, 20000)
        assert r["net_impact"] == -40000.0
        assert r["direction"] == "negative"

    def test_count(self):
        c = ScenarioImpactCalculator()
        c.calculate_financial("s1")
        c.calculate_financial("s2")
        assert c.calculation_count == 2


class TestCalculateOperational:
    def test_transformative(self):
        c = ScenarioImpactCalculator()
        r = c.calculate_operational("s1", 30.0, 5, 1.0)
        assert r["severity"] == "transformative"

    def test_disruptive(self):
        c = ScenarioImpactCalculator()
        r = c.calculate_operational("s1", -10.0, -3, 1.0)
        assert r["severity"] == "disruptive"


class TestCalculateStrategic:
    def test_basic(self):
        c = ScenarioImpactCalculator()
        r = c.calculate_strategic("s1", 80.0, 70.0, 60.0)
        # 80*0.4 + 70*0.35 + 60*0.25 = 32 + 24.5 + 15 = 71.5
        assert r["strategic_score"] == 71.5


class TestEstimateTimeline:
    def test_immediate(self):
        c = ScenarioImpactCalculator()
        r = c.estimate_timeline("s1", [
            {"name": "p1", "duration_days": 10},
            {"name": "p2", "duration_days": 15},
        ])
        assert r["total_days"] == 25
        assert r["urgency"] == "immediate"

    def test_long_term(self):
        c = ScenarioImpactCalculator()
        r = c.estimate_timeline("s1", [
            {"name": "p1", "duration_days": 200},
            {"name": "p2", "duration_days": 200},
        ])
        assert r["urgency"] == "long_term"


class TestAnalyzeRipple:
    def test_basic(self):
        c = ScenarioImpactCalculator()
        r = c.analyze_ripple("s1", 100.0, ["sales", "ops"], 0.5)
        assert r["analyzed"] is True
        assert len(r["ripples"]) == 2
        assert r["ripples"][0]["impact"] == 50.0
        assert r["ripples"][1]["impact"] == 25.0
        assert r["total_impact"] == 175.0

    def test_count(self):
        c = ScenarioImpactCalculator()
        c.analyze_ripple("s1", 10.0, ["a"])
        assert c.ripple_count == 1


# ── DecisionTreeGenerator testleri ──


class TestBuildTree:
    def test_basic(self):
        g = DecisionTreeGenerator()
        r = g.build_tree("invest?", ["yes", "no"])
        assert r["built"] is True
        assert r["option_count"] == 2
        assert r["tree_id"].startswith("dt_")

    def test_count(self):
        g = DecisionTreeGenerator()
        g.build_tree("d1")
        g.build_tree("d2")
        assert g.tree_count == 2


class TestMapOption:
    def test_basic(self):
        g = DecisionTreeGenerator()
        t = g.build_tree("test", ["a"])
        r = g.map_option(t["tree_id"], "a", 0.7, 100.0, ["win", "lose"])
        assert r["mapped"] is True
        assert r["probability"] == 0.7
        assert r["outcome_count"] == 2


class TestProjectOutcome:
    def test_basic(self):
        g = DecisionTreeGenerator()
        t = g.build_tree("test")
        r = g.project_outcome(t["tree_id"], "opt", 0.6, 1000.0, 200.0)
        # expected = 0.6*1000 - 0.4*200 = 600 - 80 = 520
        assert r["expected_value"] == 520.0
        assert r["net_payoff"] == 800.0


class TestAnalyzePath:
    def test_basic(self):
        g = DecisionTreeGenerator()
        t = g.build_tree("test")
        r = g.analyze_path(
            t["tree_id"],
            ["a", "b", "c"],
            [0.8, 0.7, 0.5],
            [100, 50, 200],
        )
        assert r["analyzed"] is True
        assert r["combined_probability"] == 0.28
        assert r["total_value"] == 350.0
        assert r["expected_value"] == 98.0

    def test_count(self):
        g = DecisionTreeGenerator()
        g.analyze_path("t1")
        g.analyze_path("t2")
        assert g.path_count == 2


class TestVisualize:
    def test_found(self):
        g = DecisionTreeGenerator()
        t = g.build_tree("test", ["a", "b"])
        r = g.visualize(t["tree_id"])
        assert r["visualized"] is True
        assert r["node_count"] == 3  # root + 2 options

    def test_not_found(self):
        g = DecisionTreeGenerator()
        r = g.visualize("nonexistent")
        assert r["found"] is False


# ── WorstCaseAnalyzer testleri ──


class TestAnalyzeDownside:
    def test_catastrophic(self):
        a = WorstCaseAnalyzer()
        r = a.analyze_downside("s1", 500000.0, 0.3)
        assert r["analyzed"] is True
        assert r["expected_loss"] == 150000.0
        assert r["severity"] == "catastrophic"

    def test_manageable(self):
        a = WorstCaseAnalyzer()
        r = a.analyze_downside("s1", 5000.0, 0.5)
        assert r["severity"] == "manageable"

    def test_count(self):
        a = WorstCaseAnalyzer()
        a.analyze_downside("s1")
        assert a.analysis_count == 1


class TestQuantifyRisk:
    def test_critical(self):
        a = WorstCaseAnalyzer()
        r = a.quantify_risk("s1", 80.0, 0.9, 0.2)
        # 80 * 0.9 * (1-0.2) = 80 * 0.9 * 0.8 = 57.6
        assert r["risk_score"] == 57.6
        assert r["level"] == "critical"

    def test_low(self):
        a = WorstCaseAnalyzer()
        r = a.quantify_risk("s1", 10.0, 0.2, 0.8)
        # 10 * 0.2 * 0.2 = 0.4
        assert r["level"] == "low"


class TestSuggestMitigation:
    def test_financial(self):
        a = WorstCaseAnalyzer()
        r = a.suggest_mitigation("s1", "financial", "severe")
        assert r["suggested"] is True
        assert "diversify_revenue" in r["suggestions"]
        assert r["priority"] == "immediate"

    def test_operational(self):
        a = WorstCaseAnalyzer()
        r = a.suggest_mitigation("s1", "operational", "moderate")
        assert r["priority"] == "planned"


class TestPlanSurvival:
    def test_comfortable(self):
        a = WorstCaseAnalyzer()
        r = a.plan_survival("s1", 120000.0, 10000.0, 50.0)
        # adjusted_burn = 10000 * (1 - 0.5) = 5000
        # runway = 120000 / 5000 = 24
        assert r["runway_months"] == 24.0
        assert r["status"] == "comfortable"

    def test_emergency(self):
        a = WorstCaseAnalyzer()
        r = a.plan_survival("s1", 20000.0, 10000.0, 10.0)
        # adjusted_burn = 10000 * 0.9 = 9000
        # runway = 20000 / 9000 = 2.2
        assert r["status"] == "emergency"


class TestStressTest:
    def test_recovery(self):
        a = WorstCaseAnalyzer()
        r = a.stress_test("s1", 100.0, -30.0, 0.1, 6)
        assert r["tested"] is True
        assert r["shocked_value"] == 70.0
        assert len(r["timeline"]) == 8  # base + shock + 6 periods

    def test_count(self):
        a = WorstCaseAnalyzer()
        a.stress_test("s1")
        assert a.stress_test_count == 1


# ── BestCaseOptimizer testleri ──


class TestAnalyzeUpside:
    def test_exceptional(self):
        o = BestCaseOptimizer()
        r = o.analyze_upside("s1", 500000.0, 0.5)
        assert r["analyzed"] is True
        assert r["expected_gain"] == 250000.0
        assert r["opportunity"] == "exceptional"

    def test_marginal(self):
        o = BestCaseOptimizer()
        r = o.analyze_upside("s1", 5000.0, 0.5)
        assert r["opportunity"] == "marginal"

    def test_count(self):
        o = BestCaseOptimizer()
        o.analyze_upside("s1")
        assert o.analysis_count == 1


class TestMaximizeOpportunity:
    def test_basic(self):
        o = BestCaseOptimizer()
        r = o.maximize_opportunity("s1", [
            {"name": "a", "value": 100, "effort": 10},
            {"name": "b", "value": 200, "effort": 50},
        ])
        assert r["maximized"] is True
        assert r["top_opportunity"] == "a"
        assert r["ranked"][0]["ratio"] == 10.0

    def test_count(self):
        o = BestCaseOptimizer()
        o.maximize_opportunity("s1")
        assert o.optimization_count == 1


class TestAllocateResources:
    def test_basic(self):
        o = BestCaseOptimizer()
        r = o.allocate_resources("s1", 100.0, [
            {"name": "marketing", "weight": 3.0},
            {"name": "dev", "weight": 2.0},
        ])
        assert r["allocated"] is True
        assert r["allocations"][0]["allocation"] == 60.0
        assert r["allocations"][1]["allocation"] == 40.0


class TestBestCaseOptimizeTiming:
    def test_act_now(self):
        o = BestCaseOptimizer()
        r = o.optimize_timing("s1", 0.8, 0.8, 0.8)
        assert r["recommendation"] == "act_now"

    def test_wait(self):
        o = BestCaseOptimizer()
        r = o.optimize_timing("s1", 0.3, 0.3, 0.3)
        assert r["recommendation"] == "wait"


class TestIdentifySuccessFactors:
    def test_basic(self):
        o = BestCaseOptimizer()
        r = o.identify_success_factors("s1", [
            {"name": "talent", "importance": 0.9, "current": 0.3},
            {"name": "funding", "importance": 0.8, "current": 0.7},
        ])
        assert r["identified"] is True
        assert r["critical_gaps"] == 1
        assert r["factors"][0]["name"] == "talent"


# ── StrategicRecommender testleri ──


class TestSuggestStrategy:
    def test_aggressive(self):
        s = StrategicRecommender()
        r = s.suggest_strategy("s1", "low", "high")
        assert r["suggested"] is True
        assert r["strategy"] == "aggressive"

    def test_defensive(self):
        s = StrategicRecommender()
        r = s.suggest_strategy("s1", "high", "low")
        assert r["strategy"] == "defensive"

    def test_count(self):
        s = StrategicRecommender()
        s.suggest_strategy("s1")
        assert s.recommendation_count == 1


class TestBalanceRiskReward:
    def test_favorable(self):
        s = StrategicRecommender()
        r = s.balance_risk_reward("s1", 300.0, 100.0)
        assert r["balanced"] is True
        assert r["risk_reward_ratio"] == 3.0
        assert r["verdict"] == "strongly_favorable"

    def test_unfavorable(self):
        s = StrategicRecommender()
        r = s.balance_risk_reward("s1", 30.0, 100.0)
        assert r["verdict"] == "strongly_unfavorable"


class TestRankPriorities:
    def test_basic(self):
        s = StrategicRecommender()
        r = s.rank_priorities("s1", [
            {"name": "a", "impact": 0.9, "urgency": 0.9, "effort": 0.2},
            {"name": "b", "impact": 0.3, "urgency": 0.3, "effort": 0.8},
        ])
        assert r["top_priority"] == "a"
        assert r["ranked_count"] == 2


class TestCreateActionPlan:
    def test_basic(self):
        s = StrategicRecommender()
        r = s.create_action_plan(
            "s1", "aggressive",
            ["expand", "hire", "launch"],
            90,
        )
        assert r["created"] is True
        assert len(r["phases"]) == 3

    def test_default_actions(self):
        s = StrategicRecommender()
        r = s.create_action_plan("s1", "defensive")
        assert r["created"] is True
        assert len(r["phases"]) >= 1

    def test_count(self):
        s = StrategicRecommender()
        s.create_action_plan("s1")
        assert s.plan_count == 1


class TestPlanContingency:
    def test_basic(self):
        s = StrategicRecommender()
        r = s.plan_contingency(
            "s1",
            "expand_market",
            ["market_crash", "competitor_entry"],
            ["pivot_strategy", "price_war"],
        )
        assert r["planned"] is True
        assert r["contingency_count"] == 2
        assert r["contingencies"][0]["plan_label"] == "B"


# ── WarGameSimulator testleri ──


class TestSimulateCompetition:
    def test_basic(self):
        w = WarGameSimulator()
        r = w.simulate_competition("market_war", ["us", "rival"], 3)
        assert r["simulated"] is True
        assert r["winner"] in ["us", "rival"]
        assert r["rounds"] == 3

    def test_count(self):
        w = WarGameSimulator()
        w.simulate_competition("g1")
        assert w.simulation_count == 1


class TestModelMove:
    def test_offensive(self):
        w = WarGameSimulator()
        r = w.model_move("g1", "us", "offensive", 0.8)
        assert r["modeled"] is True
        assert r["impact"] == 12.0  # 0.8 * 1.5 * 10

    def test_defensive(self):
        w = WarGameSimulator()
        r = w.model_move("g1", "us", "defensive", 0.5)
        assert r["impact"] == 5.0  # 0.5 * 1.0 * 10

    def test_count(self):
        w = WarGameSimulator()
        w.model_move("g1", "p1")
        assert w.move_count == 1


class TestCounterMove:
    def test_offensive_counter(self):
        w = WarGameSimulator()
        r = w.counter_move("g1", "offensive", 0.7)
        assert r["countered"] is True
        assert r["counter_move"] == "defensive"
        assert r["effectiveness"] == 0.56

    def test_flanking_counter(self):
        w = WarGameSimulator()
        r = w.counter_move("g1", "flanking")
        assert r["counter_move"] == "offensive"


class TestModelMarketDynamics:
    def test_basic(self):
        w = WarGameSimulator()
        r = w.model_market_dynamics(
            "g1", 1000.0, 0.1,
            {"us": 0.4, "rival": 0.6},
        )
        assert r["modeled"] is True
        assert r["future_size"] == 1100.0
        assert r["leader"] == "rival"


class TestPredictOutcome:
    def test_win(self):
        w = WarGameSimulator()
        r = w.predict_outcome("g1", 0.9, 0.3, 0.8)
        assert r["predicted"] is True
        assert r["outcome"] == "win"

    def test_loss(self):
        w = WarGameSimulator()
        r = w.predict_outcome("g1", 0.2, 0.9, 0.2)
        assert r["outcome"] == "loss"

    def test_draw(self):
        w = WarGameSimulator()
        r = w.predict_outcome("g1", 0.5, 0.5, 0.5)
        assert r["outcome"] == "draw"


# ── ScenarioOrchestrator testleri ──


class TestFullScenarioAnalysis:
    def test_basic(self):
        o = ScenarioOrchestrator()
        r = o.full_scenario_analysis(
            "market_entry", "realistic",
            100000.0, 30000.0, 0.6,
        )
        assert r["pipeline_complete"] is True
        assert r["name"] == "market_entry"
        assert r["probability"] == 0.6
        assert r["recommended_strategy"] in (
            "aggressive", "defensive",
            "balanced", "calculated_risk",
        )

    def test_count(self):
        o = ScenarioOrchestrator()
        o.full_scenario_analysis("s1")
        o.full_scenario_analysis("s2")
        assert o.pipeline_count == 2


class TestStrategicDecision:
    def test_basic(self):
        o = ScenarioOrchestrator()
        r = o.strategic_decision(
            "expand?", ["yes", "no", "later"],
        )
        assert r["supported"] is True
        assert r["option_count"] == 3

    def test_count(self):
        o = ScenarioOrchestrator()
        o.strategic_decision("d1")
        assert o.decision_count == 1


class TestScenarioGetAnalytics:
    def test_initial(self):
        o = ScenarioOrchestrator()
        a = o.get_analytics()
        assert a["pipelines_run"] == 0
        assert a["scenarios_created"] == 0
        assert a["war_games"] == 0

    def test_after_operations(self):
        o = ScenarioOrchestrator()
        o.full_scenario_analysis("test")
        o.strategic_decision("d1")
        o.war_game.simulate_competition("g1")
        a = o.get_analytics()
        assert a["pipelines_run"] == 1
        assert a["decisions_supported"] == 1
        assert a["war_games"] == 1
        assert a["scenarios_created"] >= 1
