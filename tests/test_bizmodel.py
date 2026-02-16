"""Business Model Canvas & Pivot Detector testleri."""

import pytest

from app.models.bizmodel_models import (
    CanvasSection,
    RevenueType,
    CostCategory,
    PivotType,
    CompetitivePosition,
    ModelMaturity,
    CanvasRecord,
    RevenueStreamRecord,
    PivotSignalRecord,
    CompetitiveAnalysisRecord,
)
from app.core.bizmodel.canvas_builder import (
    CanvasBuilder,
)
from app.core.bizmodel.revenue_stream_analyzer import (
    RevenueStreamAnalyzer,
)
from app.core.bizmodel.customer_segmenter import (
    BizCustomerSegmenter,
)
from app.core.bizmodel.cost_structure_mapper import (
    CostStructureMapper,
)
from app.core.bizmodel.value_proposition_tester import (
    ValuePropositionTester,
)
from app.core.bizmodel.pivot_signal_detector import (
    PivotSignalDetector,
)
from app.core.bizmodel.model_optimizer import (
    BusinessModelOptimizer,
)
from app.core.bizmodel.competitive_position_analyzer import (
    CompetitivePositionAnalyzer,
)
from app.core.bizmodel.bizmodel_orchestrator import (
    BizModelOrchestrator,
)


# ============================================================
# Enum testleri
# ============================================================


class TestCanvasSection:
    """CanvasSection enum testleri."""

    def test_values(self):
        assert CanvasSection.key_partners == "key_partners"
        assert CanvasSection.value_propositions == "value_propositions"
        assert CanvasSection.revenue_streams == "revenue_streams"

    def test_member_count(self):
        assert len(CanvasSection) == 9


class TestRevenueType:
    """RevenueType enum testleri."""

    def test_values(self):
        assert RevenueType.subscription == "subscription"
        assert RevenueType.freemium == "freemium"
        assert RevenueType.marketplace == "marketplace"

    def test_member_count(self):
        assert len(RevenueType) == 6


class TestCostCategory:
    """CostCategory enum testleri."""

    def test_values(self):
        assert CostCategory.fixed == "fixed"
        assert CostCategory.variable == "variable"
        assert CostCategory.recurring == "recurring"

    def test_member_count(self):
        assert len(CostCategory) == 5


class TestPivotType:
    """PivotType enum testleri."""

    def test_values(self):
        assert PivotType.customer_segment == "customer_segment"
        assert PivotType.revenue_model == "revenue_model"
        assert PivotType.platform == "platform"

    def test_member_count(self):
        assert len(PivotType) == 6


class TestCompetitivePosition:
    """CompetitivePosition enum testleri."""

    def test_values(self):
        assert CompetitivePosition.leader == "leader"
        assert CompetitivePosition.niche == "niche"
        assert CompetitivePosition.new_entrant == "new_entrant"

    def test_member_count(self):
        assert len(CompetitivePosition) == 5


class TestModelMaturity:
    """ModelMaturity enum testleri."""

    def test_values(self):
        assert ModelMaturity.ideation == "ideation"
        assert ModelMaturity.growth == "growth"
        assert ModelMaturity.renewal == "renewal"

    def test_member_count(self):
        assert len(ModelMaturity) == 5


# ============================================================
# Model testleri
# ============================================================


class TestCanvasRecord:
    """CanvasRecord model testleri."""

    def test_defaults(self):
        r = CanvasRecord()
        assert r.name == "Untitled Canvas"
        assert r.version == 1
        assert r.maturity == "ideation"
        assert isinstance(r.canvas_id, str)

    def test_custom(self):
        r = CanvasRecord(
            name="SaaS Model",
            version=3,
            maturity="growth",
        )
        assert r.name == "SaaS Model"
        assert r.version == 3
        assert r.maturity == "growth"


class TestRevenueStreamRecord:
    """RevenueStreamRecord model testleri."""

    def test_defaults(self):
        r = RevenueStreamRecord()
        assert r.name == "Default Stream"
        assert r.revenue_type == "subscription"
        assert r.amount == 0.0

    def test_custom(self):
        r = RevenueStreamRecord(
            name="Enterprise",
            revenue_type="licensing",
            amount=50000.0,
            growth_rate=15.0,
        )
        assert r.name == "Enterprise"
        assert r.amount == 50000.0
        assert r.growth_rate == 15.0


class TestPivotSignalRecord:
    """PivotSignalRecord model testleri."""

    def test_defaults(self):
        r = PivotSignalRecord()
        assert r.severity == "medium"
        assert r.pivot_type == "value_proposition"
        assert isinstance(r.signal_id, str)

    def test_custom(self):
        r = PivotSignalRecord(
            signal_type="metric_decline",
            severity="high",
            description="Revenue drop",
            pivot_type="revenue_model",
        )
        assert r.severity == "high"
        assert r.pivot_type == "revenue_model"


class TestCompetitiveAnalysisRecord:
    """CompetitiveAnalysisRecord model testleri."""

    def test_defaults(self):
        r = CompetitiveAnalysisRecord()
        assert r.position == "follower"
        assert r.moat_score == 0.0
        assert r.threat_level == "medium"

    def test_custom(self):
        r = CompetitiveAnalysisRecord(
            competitor="Rival Inc",
            position="leader",
            moat_score=85.0,
            threat_level="high",
        )
        assert r.competitor == "Rival Inc"
        assert r.moat_score == 85.0


# ============================================================
# CanvasBuilder testleri
# ============================================================


class TestCreateCanvas:
    """create_canvas testleri."""

    def test_basic(self):
        cb = CanvasBuilder()
        r = cb.create_canvas("SaaS")
        assert r["canvas_id"].startswith("cvs_")
        assert r["name"] == "SaaS"
        assert r["version"] == 1
        assert len(r["sections"]) == 9

    def test_count(self):
        cb = CanvasBuilder()
        cb.create_canvas("A")
        cb.create_canvas("B")
        assert cb.canvas_count == 2


class TestManageSection:
    """manage_section testleri."""

    def test_basic(self):
        cb = CanvasBuilder()
        c = cb.create_canvas("Test")
        r = cb.manage_section(
            c["canvas_id"],
            "key_partners",
            ["AWS", "Stripe"],
        )
        assert r["managed"] is True
        assert r["item_count"] == 2

    def test_not_found(self):
        cb = CanvasBuilder()
        r = cb.manage_section("xxx", "key_partners")
        assert r["managed"] is False


class TestGetTemplate:
    """get_template testleri."""

    def test_saas(self):
        cb = CanvasBuilder()
        r = cb.get_template("saas")
        assert r["template_type"] == "saas"
        assert r["component_count"] == 4

    def test_unknown(self):
        cb = CanvasBuilder()
        r = cb.get_template("unknown_type")
        assert r["component_count"] >= 1


class TestVersionCanvas:
    """version_canvas testleri."""

    def test_basic(self):
        cb = CanvasBuilder()
        c = cb.create_canvas("Test")
        r = cb.version_canvas(c["canvas_id"])
        assert r["versioned"] is True
        assert r["new_version"] == 2

    def test_not_found(self):
        cb = CanvasBuilder()
        r = cb.version_canvas("xxx")
        assert r["versioned"] is False


class TestAddCollaborator:
    """add_collaborator testleri."""

    def test_basic(self):
        cb = CanvasBuilder()
        c = cb.create_canvas("Test")
        r = cb.add_collaborator(
            c["canvas_id"], "Alice"
        )
        assert r["added"] is True
        assert r["total_collaborators"] == 1

    def test_not_found(self):
        cb = CanvasBuilder()
        r = cb.add_collaborator("xxx")
        assert r["added"] is False


# ============================================================
# RevenueStreamAnalyzer testleri
# ============================================================


class TestAnalyzeRevenue:
    """analyze_revenue testleri."""

    def test_basic(self):
        ra = RevenueStreamAnalyzer()
        streams = [
            {"name": "Sub", "amount": 5000},
            {"name": "Ads", "amount": 3000},
        ]
        r = ra.analyze_revenue(streams)
        assert r["total_revenue"] == 8000.0
        assert r["stream_count"] == 2
        assert r["analyzed"] is True

    def test_empty(self):
        ra = RevenueStreamAnalyzer()
        r = ra.analyze_revenue()
        assert r["total_revenue"] == 0.0
        assert r["stream_count"] == 0

    def test_count(self):
        ra = RevenueStreamAnalyzer()
        ra.analyze_revenue()
        ra.analyze_revenue()
        assert ra.analysis_count == 2


class TestBreakdownStreams:
    """breakdown_streams testleri."""

    def test_basic(self):
        ra = RevenueStreamAnalyzer()
        streams = [
            {"type": "subscription"},
            {"type": "subscription"},
            {"type": "advertising"},
        ]
        r = ra.breakdown_streams(streams)
        assert r["category_count"] == 2
        assert r["detailed"] is True

    def test_empty(self):
        ra = RevenueStreamAnalyzer()
        r = ra.breakdown_streams()
        assert r["category_count"] == 0


class TestTrackGrowth:
    """track_growth testleri."""

    def test_growing(self):
        ra = RevenueStreamAnalyzer()
        r = ra.track_growth(110.0, 100.0)
        assert r["trend"] == "growing"
        assert r["growth_rate"] == 10.0

    def test_declining(self):
        ra = RevenueStreamAnalyzer()
        r = ra.track_growth(90.0, 100.0)
        assert r["trend"] == "declining"

    def test_stable(self):
        ra = RevenueStreamAnalyzer()
        r = ra.track_growth(101.0, 100.0)
        assert r["trend"] == "stable"


class TestAnalyzePricing:
    """analyze_pricing testleri."""

    def test_premium(self):
        ra = RevenueStreamAnalyzer()
        r = ra.analyze_pricing(
            150.0, 50.0, [100.0, 90.0]
        )
        assert r["position"] == "premium"
        assert r["margin"] > 0

    def test_budget(self):
        ra = RevenueStreamAnalyzer()
        r = ra.analyze_pricing(
            50.0, 30.0, [100.0, 90.0]
        )
        assert r["position"] == "budget"


class TestCheckDiversification:
    """check_diversification testleri."""

    def test_diversified(self):
        ra = RevenueStreamAnalyzer()
        streams = [
            {"type": "subscription"},
            {"type": "advertising"},
            {"type": "licensing"},
            {"type": "marketplace"},
        ]
        r = ra.check_diversification(streams)
        assert r["diversification_score"] == 100
        assert r["risk_level"] == "low"

    def test_concentrated(self):
        ra = RevenueStreamAnalyzer()
        streams = [
            {"type": "subscription"},
        ]
        r = ra.check_diversification(streams)
        assert r["diversification_score"] == 25
        assert r["risk_level"] == "high"


# ============================================================
# BizCustomerSegmenter testleri
# ============================================================


class TestIdentifySegments:
    """identify_segments testleri."""

    def test_basic(self):
        cs = BizCustomerSegmenter()
        customers = [
            {"type": "enterprise"},
            {"type": "enterprise"},
            {"type": "smb"},
        ]
        r = cs.identify_segments(customers)
        assert r["segment_count"] == 2
        assert r["total_customers"] == 3
        assert r["identified"] is True

    def test_empty(self):
        cs = BizCustomerSegmenter()
        r = cs.identify_segments()
        assert r["segment_count"] == 0

    def test_count(self):
        cs = BizCustomerSegmenter()
        cs.identify_segments([{"type": "a"}])
        assert cs.segment_count == 1


class TestAnalyzeValue:
    """analyze_value testleri."""

    def test_excellent(self):
        cs = BizCustomerSegmenter()
        r = cs.analyze_value(
            "enterprise", 500.0, 100.0
        )
        assert r["ltv"] == 6000.0
        assert r["ltv_cac_ratio"] == 60.0
        assert r["grade"] == "excellent"

    def test_poor(self):
        cs = BizCustomerSegmenter()
        r = cs.analyze_value(
            "trial", 10.0, 100.0
        )
        assert r["grade"] == "poor"


class TestDetectPatterns:
    """detect_patterns testleri."""

    def test_highly_active(self):
        cs = BizCustomerSegmenter()
        behaviors = [f"b{i}" for i in range(12)]
        r = cs.detect_patterns(behaviors)
        assert r["pattern"] == "highly_active"

    def test_inactive(self):
        cs = BizCustomerSegmenter()
        r = cs.detect_patterns()
        assert r["pattern"] == "inactive"


class TestMapNeeds:
    """map_needs testleri."""

    def test_basic(self):
        cs = BizCustomerSegmenter()
        r = cs.map_needs(
            "enterprise",
            ["speed", "security", "scale", "support"],
        )
        assert r["need_count"] == 4
        assert len(r["priority_needs"]) == 3
        assert r["coverage_score"] == 80

    def test_empty(self):
        cs = BizCustomerSegmenter()
        r = cs.map_needs("basic")
        assert r["need_count"] == 0
        assert r["coverage_score"] == 0


class TestPrioritizeSegments:
    """prioritize_segments testleri."""

    def test_basic(self):
        cs = BizCustomerSegmenter()
        segs = [
            {"name": "smb", "value": 100},
            {"name": "enterprise", "value": 500},
        ]
        r = cs.prioritize_segments(segs)
        assert r["top_segment"] == "enterprise"
        assert r["total"] == 2

    def test_empty(self):
        cs = BizCustomerSegmenter()
        r = cs.prioritize_segments()
        assert r["top_segment"] == "none"


# ============================================================
# CostStructureMapper testleri
# ============================================================


class TestAnalyzeCosts:
    """analyze_costs testleri."""

    def test_basic(self):
        cm = CostStructureMapper()
        costs = [
            {"name": "servers", "amount": 5000},
            {"name": "salaries", "amount": 15000},
        ]
        r = cm.analyze_costs(costs)
        assert r["total_cost"] == 20000.0
        assert r["cost_count"] == 2
        assert r["analyzed"] is True

    def test_empty(self):
        cm = CostStructureMapper()
        r = cm.analyze_costs()
        assert r["total_cost"] == 0.0

    def test_count(self):
        cm = CostStructureMapper()
        cm.analyze_costs()
        assert cm.analysis_count == 1


class TestClassifyFixedVariable:
    """classify_fixed_variable testleri."""

    def test_cost_heavy(self):
        cm = CostStructureMapper()
        costs = [
            {"category": "fixed", "amount": 8000},
            {"category": "variable", "amount": 2000},
        ]
        r = cm.classify_fixed_variable(costs)
        assert r["structure"] == "cost_heavy"
        assert r["fixed_pct"] == 80.0

    def test_variable_heavy(self):
        cm = CostStructureMapper()
        costs = [
            {"category": "fixed", "amount": 2000},
            {"category": "variable", "amount": 8000},
        ]
        r = cm.classify_fixed_variable(costs)
        assert r["structure"] == "variable_heavy"

    def test_balanced(self):
        cm = CostStructureMapper()
        costs = [
            {"category": "fixed", "amount": 5000},
            {"category": "variable", "amount": 5000},
        ]
        r = cm.classify_fixed_variable(costs)
        assert r["structure"] == "balanced"


class TestIdentifyDrivers:
    """identify_drivers testleri."""

    def test_basic(self):
        cm = CostStructureMapper()
        costs = [
            {"name": "a", "amount": 100},
            {"name": "b", "amount": 500},
            {"name": "c", "amount": 300},
            {"name": "d", "amount": 50},
        ]
        r = cm.identify_drivers(costs)
        assert r["driver_count"] == 3
        assert r["drivers"][0]["name"] == "b"

    def test_empty(self):
        cm = CostStructureMapper()
        r = cm.identify_drivers()
        assert r["driver_count"] == 0


class TestFindOptimization:
    """find_optimization testleri."""

    def test_over_budget(self):
        cm = CostStructureMapper()
        r = cm.find_optimization(150.0, 100.0)
        assert "reduce_overhead" in r["opportunities"]
        assert r["gap"] == 50.0

    def test_efficient(self):
        cm = CostStructureMapper()
        r = cm.find_optimization(80.0, 100.0)
        assert "cost_efficient" in r["opportunities"]

    def test_major_gap(self):
        cm = CostStructureMapper()
        r = cm.find_optimization(200.0, 100.0)
        assert "renegotiate_contracts" in r["opportunities"]
        assert "restructure_operations" in r["opportunities"]


class TestBenchmarkCosts:
    """benchmark_costs testleri."""

    def test_excellent(self):
        cm = CostStructureMapper()
        r = cm.benchmark_costs(25.0)
        assert r["position"] == "excellent"
        assert r["percentile"] == 90

    def test_poor(self):
        cm = CostStructureMapper()
        r = cm.benchmark_costs(80.0)
        assert r["position"] == "poor"
        assert r["percentile"] == 10


# ============================================================
# ValuePropositionTester testleri
# ============================================================


class TestTestValueProp:
    """test_value_prop testleri."""

    def test_strong(self):
        vt = ValuePropositionTester()
        r = vt.test_value_prop(
            "Our unique platform delivers better results"
        )
        assert r["grade"] == "strong"
        assert r["score"] == 100
        assert r["tested"] is True

    def test_moderate(self):
        vt = ValuePropositionTester()
        r = vt.test_value_prop("short")
        assert r["grade"] == "moderate"
        assert len(r["issues"]) == 2

    def test_count(self):
        vt = ValuePropositionTester()
        vt.test_value_prop("test something here")
        vt.test_value_prop("another test here")
        assert vt.test_count == 2


class TestCollectFeedback:
    """collect_feedback testleri."""

    def test_positive(self):
        vt = ValuePropositionTester()
        responses = [
            {"sentiment": "positive"},
            {"sentiment": "positive"},
            {"sentiment": "negative"},
        ]
        r = vt.collect_feedback(responses)
        assert r["positive"] == 2
        assert r["negative"] == 1
        assert r["satisfaction_rate"] > 60

    def test_empty(self):
        vt = ValuePropositionTester()
        r = vt.collect_feedback()
        assert r["total_responses"] == 0
        assert r["satisfaction_rate"] == 0.0


class TestCompareCompetitors:
    """compare_competitors testleri."""

    def test_superior(self):
        vt = ValuePropositionTester()
        r = vt.compare_competitors(
            80.0, [50.0, 60.0]
        )
        assert r["position"] == "superior"
        assert r["advantage"] > 0

    def test_inferior(self):
        vt = ValuePropositionTester()
        r = vt.compare_competitors(
            30.0, [50.0, 60.0]
        )
        assert r["position"] == "inferior"

    def test_comparable(self):
        vt = ValuePropositionTester()
        r = vt.compare_competitors(
            55.0, [50.0, 60.0]
        )
        assert r["position"] == "comparable"


class TestCalculateFit:
    """calculate_fit testleri."""

    def test_excellent(self):
        vt = ValuePropositionTester()
        r = vt.calculate_fit(9, 10)
        assert r["fit_level"] == "excellent"
        assert r["fit_score"] == 90.0

    def test_poor(self):
        vt = ValuePropositionTester()
        r = vt.calculate_fit(1, 10)
        assert r["fit_level"] == "poor"


class TestSuggestIteration:
    """suggest_iteration testleri."""

    def test_high_priority(self):
        vt = ValuePropositionTester()
        r = vt.suggest_iteration(30.0, "negative")
        assert r["priority"] == "high"
        assert "major_pivot_needed" in r["suggestions"]
        assert "address_pain_points" in r["suggestions"]

    def test_low_priority(self):
        vt = ValuePropositionTester()
        r = vt.suggest_iteration(80.0, "positive")
        assert r["priority"] == "low"
        assert "maintain_and_optimize" in r["suggestions"]

    def test_medium_priority(self):
        vt = ValuePropositionTester()
        r = vt.suggest_iteration(50.0, "neutral")
        assert r["priority"] == "medium"
        assert "refine_messaging" in r["suggestions"]


# ============================================================
# PivotSignalDetector testleri
# ============================================================


class TestDetectWarnings:
    """detect_warnings testleri."""

    def test_critical(self):
        pd = PivotSignalDetector()
        metrics = {
            "churn_rate": 15,
            "growth_rate": -10,
            "satisfaction": 30,
            "burn_rate": 90,
        }
        r = pd.detect_warnings(metrics)
        assert r["severity"] == "critical"
        assert r["warning_count"] >= 3

    def test_healthy(self):
        pd = PivotSignalDetector()
        metrics = {
            "churn_rate": 2,
            "growth_rate": 10,
            "satisfaction": 80,
            "burn_rate": 40,
        }
        r = pd.detect_warnings(metrics)
        assert r["severity"] == "healthy"
        assert r["warning_count"] == 0

    def test_count(self):
        pd = PivotSignalDetector()
        pd.detect_warnings()
        pd.detect_warnings()
        assert pd.detection_count == 2


class TestAnalyzeMetrics:
    """analyze_metrics testleri."""

    def test_declining(self):
        pd = PivotSignalDetector()
        r = pd.analyze_metrics(
            {"revenue": 80, "users": 90},
            {"revenue": 100, "users": 100},
        )
        assert r["trend"] == "declining"
        assert r["declining"] == 2

    def test_improving(self):
        pd = PivotSignalDetector()
        r = pd.analyze_metrics(
            {"revenue": 120, "users": 110},
            {"revenue": 100, "users": 100},
        )
        assert r["trend"] == "improving"

    def test_stable(self):
        pd = PivotSignalDetector()
        r = pd.analyze_metrics(
            {"revenue": 100},
            {"revenue": 100},
        )
        assert r["trend"] == "stable"


class TestEvaluateMarketFeedback:
    """evaluate_market_feedback testleri."""

    def test_negative(self):
        pd = PivotSignalDetector()
        feedback = [
            "Product is bad",
            "Too expensive for features",
            "Poor support",
            "Slow performance",
        ]
        r = pd.evaluate_market_feedback(feedback)
        assert r["sentiment"] == "negative"
        assert r["negative_count"] >= 3

    def test_positive(self):
        pd = PivotSignalDetector()
        feedback = [
            "Great product",
            "Love the features",
            "Excellent support",
        ]
        r = pd.evaluate_market_feedback(feedback)
        assert r["sentiment"] == "positive"


class TestDetectTrends:
    """detect_trends testleri."""

    def test_upward(self):
        pd = PivotSignalDetector()
        r = pd.detect_trends(
            [10, 20, 30, 40, 50, 60]
        )
        assert r["trend"] == "upward"

    def test_downward(self):
        pd = PivotSignalDetector()
        r = pd.detect_trends(
            [60, 50, 40, 30, 20, 10]
        )
        assert r["trend"] == "downward"

    def test_insufficient(self):
        pd = PivotSignalDetector()
        r = pd.detect_trends([50])
        assert r["trend"] == "insufficient_data"


class TestRecommendPivot:
    """recommend_pivot testleri."""

    def test_pivot_recommended(self):
        pd = PivotSignalDetector()
        r = pd.recommend_pivot(4, "declining", 20.0)
        assert r["recommendation"] == "pivot_recommended"
        assert r["urgency"] == "high"

    def test_stay_course(self):
        pd = PivotSignalDetector()
        r = pd.recommend_pivot(0, "improving", 80.0)
        assert r["recommendation"] == "stay_the_course"
        assert r["urgency"] == "low"

    def test_consider(self):
        pd = PivotSignalDetector()
        r = pd.recommend_pivot(3, "stable", 50.0)
        assert r["recommendation"] == "consider_pivot"
        assert r["urgency"] == "medium"


# ============================================================
# BusinessModelOptimizer testleri
# ============================================================


class TestSuggestOptimizations:
    """suggest_optimizations testleri."""

    def test_low_margin(self):
        mo = BusinessModelOptimizer()
        r = mo.suggest_optimizations(100.0, 95.0, 2.0)
        assert "reduce_costs" in r["suggestions"]
        assert "restructure_pricing" in r["suggestions"]
        assert r["optimized"] is True

    def test_healthy(self):
        mo = BusinessModelOptimizer()
        r = mo.suggest_optimizations(100.0, 50.0, 10.0)
        assert "scale_operations" in r["suggestions"]

    def test_count(self):
        mo = BusinessModelOptimizer()
        mo.suggest_optimizations()
        mo.suggest_optimizations()
        assert mo.optimization_count == 2


class TestModelScenario:
    """model_scenario testleri."""

    def test_basic(self):
        mo = BusinessModelOptimizer()
        r = mo.model_scenario(100000.0)
        assert r["scenario_count"] == 3
        assert r["best_case"] == "optimistic"
        assert r["modeled"] is True

    def test_custom_rates(self):
        mo = BusinessModelOptimizer()
        r = mo.model_scenario(
            50000.0,
            [20.0, -20.0],
            2,
        )
        assert r["scenario_count"] == 2


class TestAnalyzeTradeoffs:
    """analyze_tradeoffs testleri."""

    def test_basic(self):
        mo = BusinessModelOptimizer()
        options = [
            {"name": "A", "benefit": 80, "risk": 20},
            {"name": "B", "benefit": 60, "risk": 10},
        ]
        r = mo.analyze_tradeoffs(options)
        assert r["recommended"] == "A"
        assert r["option_count"] == 2

    def test_empty(self):
        mo = BusinessModelOptimizer()
        r = mo.analyze_tradeoffs()
        assert r["recommended"] == "none"


class TestCreateRoadmap:
    """create_roadmap testleri."""

    def test_default(self):
        mo = BusinessModelOptimizer()
        r = mo.create_roadmap()
        assert r["phase_count"] == 4
        assert r["timeline_months"] == 12
        assert r["months_per_phase"] == 3.0
        assert r["created"] is True

    def test_custom(self):
        mo = BusinessModelOptimizer()
        r = mo.create_roadmap(
            ["plan", "execute"], 6
        )
        assert r["phase_count"] == 2
        assert r["months_per_phase"] == 3.0


class TestProjectImpact:
    """project_impact testleri."""

    def test_high(self):
        mo = BusinessModelOptimizer()
        r = mo.project_impact(100000.0, 15.0, 10.0)
        assert r["impact_level"] == "high"
        assert r["roi_pct"] == 25.0
        assert r["projected"] is True

    def test_low(self):
        mo = BusinessModelOptimizer()
        r = mo.project_impact(100000.0, 3.0, 2.0)
        assert r["impact_level"] == "low"


# ============================================================
# CompetitivePositionAnalyzer testleri
# ============================================================


class TestMapPosition:
    """map_position testleri."""

    def test_leader(self):
        cp = CompetitivePositionAnalyzer()
        r = cp.map_position(80.0, 50.0, 35.0)
        assert r["position"] == "leader"
        assert r["mapped"] is True

    def test_new_entrant(self):
        cp = CompetitivePositionAnalyzer()
        r = cp.map_position(40.0, 50.0, 2.0)
        assert r["position"] == "new_entrant"

    def test_count(self):
        cp = CompetitivePositionAnalyzer()
        cp.map_position()
        assert cp.analysis_count == 1


class TestAnalyzeDifferentiation:
    """analyze_differentiation testleri."""

    def test_strong(self):
        cp = CompetitivePositionAnalyzer()
        r = cp.analyze_differentiation(
            ["ai", "ml", "nlp", "cv"],
            ["ml"],
        )
        assert r["strength"] == "strong"
        assert len(r["unique_ours"]) == 3

    def test_weak(self):
        cp = CompetitivePositionAnalyzer()
        r = cp.analyze_differentiation(
            ["api", "web"],
            ["api", "web", "mobile"],
        )
        assert r["strength"] == "weak"


class TestAssessMoat:
    """assess_moat testleri."""

    def test_wide(self):
        cp = CompetitivePositionAnalyzer()
        r = cp.assess_moat(
            {"brand": 90, "tech": 85, "network": 80}
        )
        assert r["moat_strength"] == "wide"
        assert r["strongest"] == "brand"

    def test_none(self):
        cp = CompetitivePositionAnalyzer()
        r = cp.assess_moat(
            {"brand": 20, "tech": 30}
        )
        assert r["moat_strength"] == "none"

    def test_empty(self):
        cp = CompetitivePositionAnalyzer()
        r = cp.assess_moat()
        assert r["moat_strength"] == "none"


class TestDetectVulnerabilities:
    """detect_vulnerabilities testleri."""

    def test_critical(self):
        cp = CompetitivePositionAnalyzer()
        r = cp.detect_vulnerabilities(
            ["weak_brand", "no_moat", "high_cost"],
            ["new_competitor", "regulation", "recession"],
        )
        assert r["risk_level"] == "critical"
        assert r["total_vulnerabilities"] == 6

    def test_low(self):
        cp = CompetitivePositionAnalyzer()
        r = cp.detect_vulnerabilities()
        assert r["risk_level"] == "low"
        assert r["total_vulnerabilities"] == 0


class TestSuggestStrategy:
    """suggest_strategy testleri."""

    def test_leader(self):
        cp = CompetitivePositionAnalyzer()
        r = cp.suggest_strategy(
            "leader", "wide", "low"
        )
        assert "defend_market_share" in r["strategies"]
        assert r["urgency"] == "normal"

    def test_critical_risk(self):
        cp = CompetitivePositionAnalyzer()
        r = cp.suggest_strategy(
            "follower", "none", "critical"
        )
        assert "build_competitive_moat" in r["strategies"]
        assert "reduce_vulnerabilities" in r["strategies"]
        assert r["urgency"] == "immediate"

    def test_niche(self):
        cp = CompetitivePositionAnalyzer()
        r = cp.suggest_strategy("niche", "narrow", "medium")
        assert "deepen_niche" in r["strategies"]


# ============================================================
# BizModelOrchestrator testleri
# ============================================================


class TestFullModelCycle:
    """full_model_cycle testleri."""

    def test_basic(self):
        orch = BizModelOrchestrator()
        r = orch.full_model_cycle(
            "SaaS Business",
            "Our unique platform delivers better analytics",
            [
                {"name": "Sub", "amount": 10000},
                {"name": "Enterprise", "amount": 50000},
            ],
        )
        assert r["cycle_complete"] is True
        assert r["name"] == "SaaS Business"
        assert r["total_revenue"] == 60000.0
        assert r["canvas_id"] != ""

    def test_defaults(self):
        orch = BizModelOrchestrator()
        r = orch.full_model_cycle()
        assert r["cycle_complete"] is True
        assert orch.cycle_count == 1
        assert orch.managed_count == 1


class TestStrategicReview:
    """strategic_review testleri."""

    def test_basic(self):
        orch = BizModelOrchestrator()
        r = orch.strategic_review(
            70.0, 50.0, 20.0,
            {"churn_rate": 5, "growth_rate": 8},
        )
        assert r["review_complete"] is True
        assert r["position"] == "challenger"

    def test_with_warnings(self):
        orch = BizModelOrchestrator()
        r = orch.strategic_review(
            40.0, 50.0, 3.0,
            {
                "churn_rate": 15,
                "growth_rate": -10,
                "satisfaction": 30,
                "burn_rate": 90,
            },
        )
        assert r["review_complete"] is True
        assert r["warning_count"] >= 3


class TestBizModelGetAnalytics:
    """get_analytics testleri."""

    def test_initial(self):
        orch = BizModelOrchestrator()
        a = orch.get_analytics()
        assert a["cycles_run"] == 0
        assert a["models_managed"] == 0
        assert a["canvases_created"] == 0

    def test_after_operations(self):
        orch = BizModelOrchestrator()
        orch.full_model_cycle()
        orch.strategic_review()
        a = orch.get_analytics()
        assert a["cycles_run"] == 2
        assert a["models_managed"] == 1
        assert a["canvases_created"] == 1
        assert a["revenue_analyses"] >= 1
        assert a["value_tests"] >= 1
        assert a["pivot_detections"] >= 1
