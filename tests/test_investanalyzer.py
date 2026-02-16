"""ATLAS Investment & ROI Analyzer testleri."""

import pytest

from app.models.investanalyzer_models import (
    AnalysisRecord,
    DDRecord,
    DDStatus,
    InvestmentRecord,
    InvestmentType,
    PortfolioRecord,
    PortfolioStrategy,
    RecommendationAction,
    RiskCategory,
    ValuationMethod,
)
from app.core.investanalyzer import (
    DueDiligenceTracker,
    IRREngine,
    InvestAnalyzerOrchestrator,
    InvestmentCalculator,
    InvestmentPortfolioOptimizer,
    InvestmentRecommender,
    OpportunityCostCalculator,
    PaybackAnalyzer,
    RiskReturnMapper,
)


# ── Model testleri ──


class TestInvestmentType:
    def test_values(self):
        assert InvestmentType.EQUITY == "equity"
        assert InvestmentType.ACQUISITION == "acquisition"

    def test_member_count(self):
        assert len(InvestmentType) == 5


class TestRiskCategory:
    def test_values(self):
        assert RiskCategory.VERY_LOW == "very_low"
        assert RiskCategory.VERY_HIGH == "very_high"

    def test_member_count(self):
        assert len(RiskCategory) == 5


class TestDDStatus:
    def test_values(self):
        assert DDStatus.NOT_STARTED == "not_started"
        assert DDStatus.APPROVED == "approved"

    def test_member_count(self):
        assert len(DDStatus) == 5


class TestValuationMethod:
    def test_values(self):
        assert ValuationMethod.DCF == "dcf"
        assert ValuationMethod.BOOK_VALUE == "book_value"

    def test_member_count(self):
        assert len(ValuationMethod) == 5


class TestPortfolioStrategy:
    def test_values(self):
        assert PortfolioStrategy.CONSERVATIVE == "conservative"
        assert PortfolioStrategy.INCOME == "income"

    def test_member_count(self):
        assert len(PortfolioStrategy) == 5


class TestRecommendationAction:
    def test_values(self):
        assert RecommendationAction.BUY == "buy"
        assert RecommendationAction.INVESTIGATE == "investigate"

    def test_member_count(self):
        assert len(RecommendationAction) == 5


class TestInvestmentRecord:
    def test_defaults(self):
        r = InvestmentRecord()
        assert len(r.investment_id) == 8
        assert r.investment_type == InvestmentType.PROJECT

    def test_custom(self):
        r = InvestmentRecord(name="test", amount=50000)
        assert r.name == "test"
        assert r.amount == 50000


class TestPortfolioRecord:
    def test_defaults(self):
        r = PortfolioRecord()
        assert r.strategy == PortfolioStrategy.BALANCED

    def test_custom(self):
        r = PortfolioRecord(name="growth_pf", total_value=100000)
        assert r.total_value == 100000


class TestDDRecordModel:
    def test_defaults(self):
        r = DDRecord()
        assert r.status == DDStatus.NOT_STARTED

    def test_custom(self):
        r = DDRecord(findings=3)
        assert r.findings == 3


class TestAnalysisRecord:
    def test_defaults(self):
        r = AnalysisRecord()
        assert r.method == ValuationMethod.DCF

    def test_custom(self):
        r = AnalysisRecord(result=150000, recommendation=RecommendationAction.BUY)
        assert r.result == 150000


# ── InvestmentCalculator testleri ──


class TestModelInvestment:
    def test_basic(self):
        c = InvestmentCalculator()
        r = c.model_investment("project_a", 100000, 50000, 20000, 5)
        assert r["modeled"] is True
        assert r["annual_profit"] == 30000
        assert r["total_profit"] == 50000
        assert r["roi_pct"] == 50.0

    def test_count(self):
        c = InvestmentCalculator()
        c.model_investment("a")
        c.model_investment("b")
        assert c.model_count == 2


class TestProjectCashFlow:
    def test_profitable(self):
        c = InvestmentCalculator()
        r = c.project_cash_flow(100000, [40000, 40000, 40000], 0.1)
        assert r["projected"] is True
        assert r["profitable"] is False  # NPV < 0 for 3 years at 10%
        assert r["periods"] == 3

    def test_no_flows(self):
        c = InvestmentCalculator()
        r = c.project_cash_flow(100000, [])
        assert r["npv"] == -100000


class TestValuateDCF:
    def test_basic(self):
        c = InvestmentCalculator()
        r = c.valuate_dcf([100000, 120000, 150000], 0.1, 0.02)
        assert r["valuated"] is True
        assert r["total_value"] > 0
        assert r["method"] == "dcf"

    def test_count(self):
        c = InvestmentCalculator()
        c.valuate_dcf([100])
        assert c.valuation_count == 1


class TestSensitivityAnalysis:
    def test_basic(self):
        c = InvestmentCalculator()
        r = c.sensitivity_analysis(50000, "discount_rate", [-20, -10, 0, 10, 20])
        assert r["analyzed"] is True
        assert len(r["results"]) == 5
        assert r["results"][2]["npv"] == 50000  # 0% variation


class TestCompareScenarios:
    def test_basic(self):
        c = InvestmentCalculator()
        r = c.compare_scenarios([
            {"name": "a", "npv": 50000},
            {"name": "b", "npv": 80000},
        ])
        assert r["compared"] is True
        assert r["best_scenario"] == "b"


# ── IRREngine testleri ──


class TestCalculateIRR:
    def test_basic(self):
        e = IRREngine()
        r = e.calculate_irr(100000, [40000, 40000, 40000, 40000])
        assert r["calculated"] is True
        assert r["irr"] > 0

    def test_no_flows(self):
        e = IRREngine()
        r = e.calculate_irr(100000, [])
        assert r["converged"] is False

    def test_count(self):
        e = IRREngine()
        e.calculate_irr(100, [50, 50, 50])
        assert e.calculation_count == 1


class TestCalculateMIRR:
    def test_basic(self):
        e = IRREngine()
        r = e.calculate_mirr(100000, [30000, 40000, 50000], 0.08, 0.1)
        assert r["calculated"] is True
        assert r["mirr"] > 0


class TestHandleMultipleIRR:
    def test_multiple(self):
        e = IRREngine()
        r = e.handle_multiple_irr([-100, 200, -150, 100])
        assert r["analyzed"] is True
        assert r["sign_changes"] == 3
        assert r["multiple_irr_possible"] is True
        assert r["recommendation"] == "use_mirr"

    def test_single(self):
        e = IRREngine()
        r = e.handle_multiple_irr([-100, 50, 50, 50])
        assert r["multiple_irr_possible"] is False


class TestCompareHurdle:
    def test_excellent(self):
        e = IRREngine()
        r = e.compare_hurdle(25.0, 10.0)
        assert r["compared"] is True
        assert r["verdict"] == "excellent"
        assert r["acceptable"] is True

    def test_reject(self):
        e = IRREngine()
        r = e.compare_hurdle(5.0, 15.0)
        assert r["verdict"] == "reject"
        assert r["acceptable"] is False


class TestRankInvestments:
    def test_basic(self):
        e = IRREngine()
        r = e.rank_investments([
            {"name": "a", "irr": 15},
            {"name": "b", "irr": 25},
            {"name": "c", "irr": 10},
        ])
        assert r["ranked_done"] is True
        assert r["best"] == "b"
        assert r["ranked"][0]["rank"] == 1

    def test_count(self):
        e = IRREngine()
        e.rank_investments([])
        assert e.ranking_count == 1


# ── PaybackAnalyzer testleri ──


class TestCalculatePayback:
    def test_recovered(self):
        a = PaybackAnalyzer()
        r = a.calculate_payback(100000, [30000, 30000, 30000, 30000])
        assert r["calculated"] is True
        assert r["payback_period"] == 4
        assert r["fully_recovered"] is True

    def test_not_recovered(self):
        a = PaybackAnalyzer()
        r = a.calculate_payback(100000, [10000, 10000])
        assert r["fully_recovered"] is False

    def test_count(self):
        a = PaybackAnalyzer()
        a.calculate_payback(100, [50, 60])
        assert a.payback_count == 1


class TestDiscountedPayback:
    def test_basic(self):
        a = PaybackAnalyzer()
        r = a.calculate_discounted_payback(100000, [50000, 50000, 50000], 0.1)
        assert r["calculated"] is True
        assert r["payback_period"] > 0


class TestAnalyzeBreakeven:
    def test_feasible(self):
        a = PaybackAnalyzer()
        r = a.analyze_breakeven(50000, 10.0, 25.0)
        assert r["analyzed"] is True
        assert r["feasible"] is True
        assert r["breakeven_units"] == 3333  # 50000/(25-10) = 3333.3 → 3333

    def test_infeasible(self):
        a = PaybackAnalyzer()
        r = a.analyze_breakeven(50000, 30.0, 20.0)
        assert r["feasible"] is False

    def test_count(self):
        a = PaybackAnalyzer()
        a.analyze_breakeven(100, 5, 10)
        assert a.breakeven_count == 1


class TestCashRecovery:
    def test_basic(self):
        a = PaybackAnalyzer()
        r = a.calculate_cash_recovery(100000, [30000, 40000, 50000])
        assert r["calculated"] is True
        assert r["total_recovered"] == 120000
        assert r["recovery_rate"] == 120.0


class TestVisualizeTimeline:
    def test_basic(self):
        a = PaybackAnalyzer()
        r = a.visualize_timeline(100000, [40000, 40000, 40000])
        assert r["visualized"] is True
        assert len(r["timeline"]) == 4  # period 0 + 3
        assert r["breakeven_period"] == 3


# ── RiskReturnMapper testleri ──


class TestAssessRisk:
    def test_very_high(self):
        m = RiskReturnMapper()
        r = m.assess_risk("i1", 0.9, 0.8, 0.7, 0.8)
        assert r["assessed"] is True
        assert r["level"] == "very_high"

    def test_low(self):
        m = RiskReturnMapper()
        r = m.assess_risk("i1", 0.1, 0.1, 0.1, 0.1)
        assert r["level"] == "very_low"

    def test_count(self):
        m = RiskReturnMapper()
        m.assess_risk("i1")
        assert m.assessment_count == 1


class TestProjectReturn:
    def test_basic(self):
        m = RiskReturnMapper()
        r = m.project_return("i1", 10.0, 1.2, 5)
        assert r["projected"] is True
        assert r["annual_return"] == 12.0


class TestEfficientFrontier:
    def test_basic(self):
        m = RiskReturnMapper()
        r = m.calculate_efficient_frontier([
            {"name": "a", "return_pct": 10, "risk": 0.3},
            {"name": "b", "return_pct": 15, "risk": 0.2},
            {"name": "c", "return_pct": 8, "risk": 0.5},
        ])
        assert r["calculated"] is True
        assert "b" in r["efficient_set"]  # b dominates a and c


class TestCalculateSharpe:
    def test_excellent(self):
        m = RiskReturnMapper()
        r = m.calculate_sharpe(20.0, 3.0, 5.0)
        # (20-3)/5 = 3.4
        assert r["sharpe_ratio"] == 3.4
        assert r["quality"] == "excellent"

    def test_negative(self):
        m = RiskReturnMapper()
        r = m.calculate_sharpe(2.0, 5.0, 10.0)
        assert r["quality"] == "negative"

    def test_count(self):
        m = RiskReturnMapper()
        m.calculate_sharpe(10, 3, 5)
        assert m.sharpe_count == 1


class TestRiskAdjustedReturn:
    def test_attractive(self):
        m = RiskReturnMapper()
        r = m.risk_adjusted_return("i1", 20.0, 0.3)
        # 20 - 30*0.1 = 20 - 3 = 17
        assert r["risk_adjusted_return"] == 17.0
        assert r["attractive"] is True


# ── OpportunityCostCalculator testleri ──


class TestCalculateOpportunityCost:
    def test_optimal(self):
        c = OpportunityCostCalculator()
        r = c.calculate_opportunity_cost(15.0, 10.0, 100000)
        assert r["calculated"] is True
        assert r["verdict"] == "optimal_choice"

    def test_reconsider(self):
        c = OpportunityCostCalculator()
        r = c.calculate_opportunity_cost(5.0, 15.0, 100000)
        assert r["verdict"] == "reconsider"
        assert r["opportunity_cost_pct"] == 10.0

    def test_count(self):
        c = OpportunityCostCalculator()
        c.calculate_opportunity_cost(10, 12, 100)
        assert c.calculation_count == 1


class TestAnalyzeAlternatives:
    def test_basic(self):
        c = OpportunityCostCalculator()
        r = c.analyze_alternatives([
            {"name": "a", "return_pct": 10},
            {"name": "b", "return_pct": 15},
        ])
        assert r["analyzed"] is True
        assert r["best_alternative"] == "b"


class TestOCAllocateResources:
    def test_basic(self):
        c = OpportunityCostCalculator()
        r = c.allocate_resources(100000, [
            {"name": "a", "min_invest": 30000, "return_pct": 15},
            {"name": "b", "min_invest": 20000, "return_pct": 10},
        ])
        assert r["allocated_done"] is True
        assert r["allocated"] > 0


class TestAnalyzeTradeoff:
    def test_dominant(self):
        c = OpportunityCostCalculator()
        r = c.analyze_tradeoff(
            {"name": "A", "return_pct": 15, "risk": 0.3},
            {"name": "B", "return_pct": 10, "risk": 0.5},
        )
        assert r["analyzed"] is True
        assert r["winner"] == "A"
        assert r["dominant"] is True


class TestDetermineBestUse:
    def test_basic(self):
        c = OpportunityCostCalculator()
        r = c.determine_best_use(100000, [
            {"name": "marketing", "return_per_unit": 2.5},
            {"name": "r_and_d", "return_per_unit": 3.0},
        ])
        assert r["determined"] is True
        assert r["best_use"] == "r_and_d"
        assert r["expected_return"] == 300000.0


# ── InvestmentPortfolioOptimizer testleri ──


class TestConstructPortfolio:
    def test_basic(self):
        o = InvestmentPortfolioOptimizer()
        r = o.construct_portfolio("growth", "growth", [
            {"name": "stock_a", "weight": 0.6, "return_pct": 12},
            {"name": "bond_b", "weight": 0.4, "return_pct": 5},
        ])
        assert r["constructed"] is True
        assert r["holding_count"] == 2

    def test_count(self):
        o = InvestmentPortfolioOptimizer()
        o.construct_portfolio("test")
        assert o.portfolio_count == 1


class TestAnalyzeDiversification:
    def test_poor(self):
        o = InvestmentPortfolioOptimizer()
        r = o.analyze_diversification([
            {"name": "a", "weight": 0.7, "sector": "tech"},
            {"name": "b", "weight": 0.3, "sector": "finance"},
        ])
        assert r["analyzed"] is True
        assert r["diversity_level"] == "poor"

    def test_good(self):
        o = InvestmentPortfolioOptimizer()
        r = o.analyze_diversification([
            {"name": "a", "weight": 0.25, "sector": "tech"},
            {"name": "b", "weight": 0.25, "sector": "finance"},
            {"name": "c", "weight": 0.25, "sector": "health"},
            {"name": "d", "weight": 0.25, "sector": "energy"},
        ])
        assert r["diversity_level"] == "good"


class TestRebalance:
    def test_basic(self):
        o = InvestmentPortfolioOptimizer()
        r = o.rebalance("pf1",
            {"stocks": 0.7, "bonds": 0.3},
            {"stocks": 0.6, "bonds": 0.4},
        )
        assert r["rebalanced"] is True
        assert r["trade_count"] == 2

    def test_count(self):
        o = InvestmentPortfolioOptimizer()
        o.rebalance("pf1")
        assert o.rebalance_count == 1


class TestManageRisk:
    def test_within(self):
        o = InvestmentPortfolioOptimizer()
        r = o.manage_risk("pf1", 0.5, 0.7)
        assert r["managed"] is True
        assert r["within_tolerance"] is True
        assert r["action"] == "maintain"

    def test_excess(self):
        o = InvestmentPortfolioOptimizer()
        r = o.manage_risk("pf1", 0.9, 0.6)
        assert r["action"] == "significant_reduction"


class TestTrackPerformance:
    def test_outperforming(self):
        o = InvestmentPortfolioOptimizer()
        r = o.track_performance("pf1", [12, 15, 10], 10.0)
        assert r["tracked"] is True
        assert r["performance"] == "outperforming"

    def test_empty(self):
        o = InvestmentPortfolioOptimizer()
        r = o.track_performance("pf1", [])
        assert r["tracked"] is False


# ── InvestmentRecommender testleri ──


class TestSuggestInvestment:
    def test_conservative(self):
        r_obj = InvestmentRecommender()
        r = r_obj.suggest_investment(50000, "low", "short")
        assert r["suggested"] is True
        assert "treasury_bonds" in r["suggestions"]

    def test_count(self):
        r_obj = InvestmentRecommender()
        r_obj.suggest_investment(100000)
        assert r_obj.suggestion_count == 1


class TestScoreFit:
    def test_excellent(self):
        r_obj = InvestmentRecommender()
        r = r_obj.score_fit("i1", 0.9, 0.9, 0.8, 0.8)
        assert r["scored"] is True
        assert r["fit_level"] == "excellent"

    def test_poor(self):
        r_obj = InvestmentRecommender()
        r = r_obj.score_fit("i1", 0.1, 0.1, 0.2, 0.2)
        assert r["fit_level"] == "poor"


class TestInvestRankPriorities:
    def test_basic(self):
        r_obj = InvestmentRecommender()
        r = r_obj.rank_priorities([
            {"name": "a", "fit_score": 0.9, "urgency": 0.8},
            {"name": "b", "fit_score": 0.5, "urgency": 0.3},
        ])
        assert r["ranked_done"] is True
        assert r["top_priority"] == "a"


class TestAdviseTiming:
    def test_buy_now(self):
        r_obj = InvestmentRecommender()
        r = r_obj.advise_timing("i1", "bullish", "undervalued")
        assert r["advised"] is True
        assert r["timing_advice"] == "buy_now"

    def test_sell(self):
        r_obj = InvestmentRecommender()
        r = r_obj.advise_timing("i1", "bearish", "overvalued")
        assert r["timing_advice"] == "sell"


class TestCreateActionItems:
    def test_buy(self):
        r_obj = InvestmentRecommender()
        r = r_obj.create_action_items("i1", "buy")
        assert r["created"] is True
        assert r["action_count"] == 3
        assert "execute_purchase" in r["actions"]

    def test_count(self):
        r_obj = InvestmentRecommender()
        r_obj.create_action_items("i1", "buy")
        assert r_obj.action_count == 3


# ── DueDiligenceTracker testleri ──


class TestCreateChecklist:
    def test_standard(self):
        t = DueDiligenceTracker()
        r = t.create_checklist("i1", "standard")
        assert r["created"] is True
        assert r["item_count"] == 5

    def test_comprehensive(self):
        t = DueDiligenceTracker()
        r = t.create_checklist("i1", "comprehensive")
        assert r["item_count"] == 8

    def test_count(self):
        t = DueDiligenceTracker()
        t.create_checklist("i1")
        assert t.checklist_count == 1


class TestTrackDocument:
    def test_basic(self):
        t = DueDiligenceTracker()
        cl = t.create_checklist("i1")
        r = t.track_document(cl["checklist_id"], "financial_review", "completed")
        assert r["tracked"] is True
        assert r["status"] == "completed"


class TestRecordFinding:
    def test_basic(self):
        t = DueDiligenceTracker()
        cl = t.create_checklist("i1")
        r = t.record_finding(cl["checklist_id"], "legal", "Missing license", "high")
        assert r["recorded"] is True
        assert r["severity"] == "high"

    def test_count(self):
        t = DueDiligenceTracker()
        cl = t.create_checklist("i1")
        t.record_finding(cl["checklist_id"], "a", "b")
        assert t.finding_count == 1


class TestFlagRisk:
    def test_red_flag(self):
        t = DueDiligenceTracker()
        r = t.flag_risk("dd1", "compliance", "Missing permits", "critical")
        assert r["flagged"] is True
        assert r["red_flag"] is True

    def test_no_flag(self):
        t = DueDiligenceTracker()
        r = t.flag_risk("dd1", "operations", "Minor issue", "low")
        assert r["red_flag"] is False


class TestDDGenerateReport:
    def test_proceed(self):
        t = DueDiligenceTracker()
        cl = t.create_checklist("i1", "quick")
        for item in ["financial_review", "legal_review", "market_analysis"]:
            t.track_document(cl["checklist_id"], item, "completed")
        r = t.generate_report(cl["checklist_id"])
        assert r["generated"] is True
        assert r["recommendation"] == "proceed"
        assert r["completion_pct"] == 100.0

    def test_not_found(self):
        t = DueDiligenceTracker()
        r = t.generate_report("nonexistent")
        assert r["found"] is False


# ── InvestAnalyzerOrchestrator testleri ──


class TestFullInvestmentAnalysis:
    def test_basic(self):
        o = InvestAnalyzerOrchestrator()
        r = o.full_investment_analysis("project_x", 100000, 50000, 15000, 5, 0.1)
        assert r["pipeline_complete"] is True
        assert r["name"] == "project_x"
        assert r["npv"] != 0
        assert r["irr"] > 0
        assert r["recommendation"] in ("invest", "consider", "pass")

    def test_count(self):
        o = InvestAnalyzerOrchestrator()
        o.full_investment_analysis("a")
        assert o.pipeline_count == 1
        assert o.decision_count == 1


class TestCompareInvestments:
    def test_basic(self):
        o = InvestAnalyzerOrchestrator()
        r = o.compare_investments([
            {"name": "a", "npv": 50000},
            {"name": "b", "npv": 80000},
        ])
        assert r["compared"] is True
        assert r["best_investment"] == "b"


class TestInvestGetAnalytics:
    def test_initial(self):
        o = InvestAnalyzerOrchestrator()
        a = o.get_analytics()
        assert a["pipelines_run"] == 0
        assert a["models_created"] == 0

    def test_after_operations(self):
        o = InvestAnalyzerOrchestrator()
        o.full_investment_analysis("test")
        a = o.get_analytics()
        assert a["pipelines_run"] == 1
        assert a["models_created"] == 1
        assert a["irr_calculated"] == 1
        assert a["paybacks_calculated"] == 1
