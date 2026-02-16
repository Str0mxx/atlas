"""ATLAS Autonomous Revenue Optimizer testleri."""

import pytest

from app.core.revenueopt.revenue_tracker import (
    RevenueTracker,
)
from app.core.revenueopt.pricing_optimizer import (
    PricingOptimizer,
)
from app.core.revenueopt.upsell_detector import (
    UpsellDetector,
)
from app.core.revenueopt.churn_predictor import (
    ChurnPredictor,
)
from app.core.revenueopt.ltv_calculator import (
    LTVCalculator,
)
from app.core.revenueopt.campaign_roi_analyzer import (
    CampaignROIAnalyzer,
)
from app.core.revenueopt.revenue_forecaster import (
    RevenueForecaster,
)
from app.core.revenueopt.monetization_advisor import (
    MonetizationAdvisor,
)
from app.core.revenueopt.revenueopt_orchestrator import (
    RevenueOptOrchestrator,
)
from app.models.revenueopt_models import (
    RevenueStream,
    PricingStrategy,
    ChurnRisk,
    CampaignChannel,
    ForecastMethod,
    MonetizationType,
    RevenueRecord,
    ChurnRecord,
    LTVRecord,
    ForecastRecord,
)


# --- RevenueTracker ---

class TestMonitorRevenue:
    def test_basic(self):
        rt = RevenueTracker()
        r = rt.monitor_revenue(
            "product", 1000.0, "2024-Q1",
        )
        assert r["monitored"]
        assert r["amount"] == 1000.0

    def test_count(self):
        rt = RevenueTracker()
        rt.monitor_revenue("a", 100)
        rt.monitor_revenue("b", 200)
        assert rt.record_count == 2


class TestBreakdownStreams:
    def test_basic(self):
        rt = RevenueTracker()
        rt.monitor_revenue("product", 700)
        rt.monitor_revenue("service", 300)
        r = rt.breakdown_streams()
        assert r["breakdown"]
        assert r["total"] == 1000

    def test_empty(self):
        rt = RevenueTracker()
        r = rt.breakdown_streams()
        assert r["total"] == 0


class TestAnalyzeTrend:
    def test_growing(self):
        rt = RevenueTracker()
        for v in [100, 110, 120, 150]:
            rt.monitor_revenue("p", v)
        r = rt.analyze_trend("p")
        assert r["analyzed"]
        assert r["trend"] == "growing"

    def test_declining(self):
        rt = RevenueTracker()
        for v in [200, 180, 150, 100]:
            rt.monitor_revenue("p", v)
        r = rt.analyze_trend("p")
        assert r["trend"] == "declining"

    def test_insufficient(self):
        rt = RevenueTracker()
        rt.monitor_revenue("p", 100)
        r = rt.analyze_trend("p")
        assert r["trend"] == (
            "insufficient_data"
        )


class TestDetectRevenueAnomaly:
    def test_anomaly(self):
        rt = RevenueTracker()
        for v in [100, 102, 98, 101]:
            rt.monitor_revenue("p", v)
        r = rt.detect_anomaly(500, "p")
        assert r["detected"]
        assert r["is_anomaly"]

    def test_normal(self):
        rt = RevenueTracker()
        for v in [100, 100, 100, 100]:
            rt.monitor_revenue("p", v)
        r = rt.detect_anomaly(105, "p")
        assert not r["is_anomaly"]

    def test_no_baseline(self):
        rt = RevenueTracker()
        r = rt.detect_anomaly(100, "p")
        assert not r["is_anomaly"]


class TestTrackGoal:
    def test_on_track(self):
        rt = RevenueTracker()
        r = rt.track_goal(
            "Q1", target=1000, current=900,
        )
        assert r["tracked"]
        assert r["on_track"]

    def test_behind(self):
        rt = RevenueTracker()
        r = rt.track_goal(
            "Q1", target=1000, current=500,
        )
        assert not r["on_track"]


# --- PricingOptimizer ---

class TestDynamicPricing:
    def test_basic(self):
        po = PricingOptimizer()
        r = po.dynamic_pricing(
            "p1", base_price=100,
            demand_factor=1.2,
        )
        assert r["optimized"]
        assert r["adjusted_price"] == 120.0

    def test_low_supply(self):
        po = PricingOptimizer()
        r = po.dynamic_pricing(
            "p1", base_price=100,
            supply_factor=0.5,
        )
        assert r["adjusted_price"] == 200.0


class TestAnalyzeElasticity:
    def test_elastic(self):
        po = PricingOptimizer()
        r = po.analyze_elasticity(
            "p1",
            price_changes=[
                {"price": 100, "demand": 100},
                {"price": 120, "demand": 60},
            ],
        )
        assert r["analyzed"]
        assert r["type"] == "elastic"

    def test_insufficient(self):
        po = PricingOptimizer()
        r = po.analyze_elasticity("p1")
        assert r["type"] == "unknown"


class TestCompareCompetitors:
    def test_below(self):
        po = PricingOptimizer()
        r = po.compare_competitors(
            "p1", our_price=50,
            competitor_prices=[100, 120],
        )
        assert r["compared"]
        assert r["position"] == "below_market"

    def test_no_comps(self):
        po = PricingOptimizer()
        r = po.compare_competitors("p1")
        assert r["position"] == "unknown"


class TestOptimizeBundle:
    def test_basic(self):
        po = PricingOptimizer()
        r = po.optimize_bundle(
            "bundle1",
            products=[
                {"name": "a", "price": 50},
                {"name": "b", "price": 50},
            ],
            discount_pct=10,
        )
        assert r["optimized"]
        assert r["bundle_price"] == 90.0
        assert r["savings"] == 10.0


class TestProtectMargin:
    def test_protected(self):
        po = PricingOptimizer()
        r = po.protect_margin(
            "p1", cost=60,
            current_price=100,
            min_margin_pct=20,
        )
        assert r["checked"]
        assert r["protected"]

    def test_not_protected(self):
        po = PricingOptimizer()
        r = po.protect_margin(
            "p1", cost=90,
            current_price=100,
            min_margin_pct=20,
        )
        assert not r["protected"]


# --- UpsellDetector ---

class TestDetectOpportunity:
    def test_basic(self):
        ud = UpsellDetector()
        r = ud.detect_opportunity(
            "c1", current_product="basic",
        )
        assert r["detected"]
        assert len(r["upgrades"]) == 2


class TestRecommendProducts:
    def test_basic(self):
        ud = UpsellDetector()
        r = ud.recommend_products(
            "c1",
            current_products=["a"],
            catalog=["a", "b", "c"],
        )
        assert r["recommended"]
        assert "b" in r["recommendations"]
        assert "a" not in r["recommendations"]


class TestOptimizeTiming:
    def test_optimal(self):
        ud = UpsellDetector()
        r = ud.optimize_timing(
            "c1",
            days_since_purchase=14,
            engagement_score=70,
        )
        assert r["timing"] == "optimal"

    def test_too_early(self):
        ud = UpsellDetector()
        r = ud.optimize_timing(
            "c1", days_since_purchase=2,
        )
        assert r["timing"] == "too_early"


class TestScorePropensity:
    def test_high(self):
        ud = UpsellDetector()
        r = ud.score_propensity(
            "c1",
            purchase_frequency=2,
            avg_order_value=200,
            engagement_score=80,
        )
        assert r["scored"]
        assert r["likelihood"] == "high"

    def test_low(self):
        ud = UpsellDetector()
        r = ud.score_propensity(
            "c1",
            purchase_frequency=0,
            avg_order_value=0,
            engagement_score=10,
        )
        assert r["likelihood"] == "low"


class TestTrackConversion:
    def test_converted(self):
        ud = UpsellDetector()
        r = ud.track_conversion(
            "opp_1", converted=True,
            revenue=500,
        )
        assert r["tracked"]
        assert r["conversion_rate"] == 100.0

    def test_not_converted(self):
        ud = UpsellDetector()
        r = ud.track_conversion(
            "opp_1", converted=False,
        )
        assert r["conversion_rate"] == 0.0


# --- ChurnPredictor ---

class TestScoreChurnRisk:
    def test_critical(self):
        cp = ChurnPredictor()
        r = cp.score_churn_risk(
            "c1",
            days_inactive=60,
            support_tickets=5,
        )
        assert r["scored"]
        assert r["risk_level"] == "critical"

    def test_low(self):
        cp = ChurnPredictor()
        r = cp.score_churn_risk(
            "c1",
            days_inactive=5,
        )
        assert r["risk_level"] == "low"


class TestIssueEarlyWarning:
    def test_warning(self):
        cp = ChurnPredictor()
        cp.score_churn_risk(
            "c1", days_inactive=60,
        )
        r = cp.issue_early_warning("c1")
        assert r["issued"]

    def test_no_warning(self):
        cp = ChurnPredictor()
        cp.score_churn_risk(
            "c1", days_inactive=5,
        )
        r = cp.issue_early_warning("c1")
        assert not r["issued"]

    def test_not_found(self):
        cp = ChurnPredictor()
        r = cp.issue_early_warning("x")
        assert not r["found"]


class TestAnalyzeRootCause:
    def test_price(self):
        cp = ChurnPredictor()
        r = cp.analyze_root_cause(
            "c1",
            factors={
                "price_sensitivity": 80,
            },
        )
        assert r["analyzed"]
        assert "price_too_high" in (
            r["all_causes"]
        )

    def test_unknown(self):
        cp = ChurnPredictor()
        r = cp.analyze_root_cause("c1")
        assert r["primary_cause"] == "unknown"


class TestRetentionActions:
    def test_critical(self):
        cp = ChurnPredictor()
        r = cp.suggest_retention_actions(
            "c1", risk_level="critical",
        )
        assert r["suggested"]
        assert r["action_count"] == 3

    def test_low(self):
        cp = ChurnPredictor()
        r = cp.suggest_retention_actions(
            "c1", risk_level="low",
        )
        assert r["action_count"] == 1


class TestWinbackCampaign:
    def test_basic(self):
        cp = ChurnPredictor()
        r = cp.create_winback_campaign(
            customer_ids=["c1", "c2"],
            discount_pct=25,
        )
        assert r["created"]
        assert r["target_count"] == 2


# --- LTVCalculator ---

class TestCalculateLTV:
    def test_basic(self):
        lc = LTVCalculator()
        r = lc.calculate_ltv(
            "c1",
            avg_purchase=100,
            purchase_frequency=2,
            lifespan_months=24,
        )
        assert r["calculated"]
        assert r["ltv"] == 4800.0

    def test_zero(self):
        lc = LTVCalculator()
        r = lc.calculate_ltv("c1")
        assert r["ltv"] == 0.0


class TestAnalyzeSegment:
    def test_basic(self):
        lc = LTVCalculator()
        lc.calculate_ltv(
            "c1", avg_purchase=100,
            purchase_frequency=1,
        )
        lc.calculate_ltv(
            "c2", avg_purchase=200,
            purchase_frequency=1,
        )
        r = lc.analyze_segment(
            "premium", ["c1", "c2"],
        )
        assert r["analyzed"]
        assert r["count"] == 2

    def test_empty(self):
        lc = LTVCalculator()
        r = lc.analyze_segment("x")
        assert r["avg_ltv"] == 0.0


class TestTrackCohort:
    def test_basic(self):
        lc = LTVCalculator()
        lc.calculate_ltv(
            "c1", avg_purchase=100,
            purchase_frequency=1,
        )
        r = lc.track_cohort(
            "2024-Q1", ["c1"],
        )
        assert r["tracked"]
        assert r["size"] == 1


class TestPredictLTV:
    def test_growth(self):
        lc = LTVCalculator()
        lc.calculate_ltv(
            "c1", avg_purchase=100,
            purchase_frequency=1,
        )
        r = lc.predict_ltv(
            "c1", growth_rate=10,
        )
        assert r["predicted"]
        assert r["predicted_ltv"] > r[
            "current_ltv"
        ]

    def test_not_found(self):
        lc = LTVCalculator()
        r = lc.predict_ltv("x")
        assert not r["found"]


class TestGuideInvestment:
    def test_invest_more(self):
        lc = LTVCalculator()
        lc.calculate_ltv(
            "c1", avg_purchase=100,
            purchase_frequency=2,
            lifespan_months=24,
        )
        r = lc.guide_investment(
            "c1", acquisition_cost=100,
        )
        assert r["guided"]
        assert r["recommendation"] == (
            "invest_more"
        )

    def test_not_found(self):
        lc = LTVCalculator()
        r = lc.guide_investment("x")
        assert not r["found"]


# --- CampaignROIAnalyzer ---

class TestCalculateROI:
    def test_positive(self):
        ca = CampaignROIAnalyzer()
        r = ca.calculate_roi(
            "camp1", spend=100,
            revenue=300,
        )
        assert r["calculated"]
        assert r["roi_pct"] == 200.0

    def test_zero_spend(self):
        ca = CampaignROIAnalyzer()
        r = ca.calculate_roi(
            "camp1", spend=0,
        )
        assert r["roi_pct"] == 0.0


class TestModelAttribution:
    def test_last_touch(self):
        ca = CampaignROIAnalyzer()
        r = ca.model_attribution(
            "camp1",
            touchpoints=[
                {"channel": "google"},
                {"channel": "email"},
            ],
            model="last_touch",
        )
        assert r["modeled"]
        assert r["attributions"]["email"] == (
            100.0
        )

    def test_linear(self):
        ca = CampaignROIAnalyzer()
        r = ca.model_attribution(
            "camp1",
            touchpoints=[
                {"channel": "google"},
                {"channel": "email"},
            ],
            model="linear",
        )
        assert r["attributions"]["google"] == (
            50.0
        )

    def test_empty(self):
        ca = CampaignROIAnalyzer()
        r = ca.model_attribution("camp1")
        assert r["attributions"] == {}


class TestCompareChannels:
    def test_basic(self):
        ca = CampaignROIAnalyzer()
        r = ca.compare_channels(
            channels={
                "google": {
                    "spend": 100,
                    "revenue": 500,
                },
                "email": {
                    "spend": 50,
                    "revenue": 200,
                },
            },
        )
        assert r["compared"]
        assert r["best_channel"] == "google"


class TestOptimizeBudget:
    def test_basic(self):
        ca = CampaignROIAnalyzer()
        r = ca.optimize_budget(
            total_budget=1000,
            channel_rois={
                "google": 200,
                "email": 100,
            },
        )
        assert r["optimized"]
        total = sum(
            r["allocations"].values(),
        )
        assert abs(total - 1000) < 1


class TestPredictPerformance:
    def test_basic(self):
        ca = CampaignROIAnalyzer()
        ca.calculate_roi(
            "c1", spend=100, revenue=300,
        )
        r = ca.predict_performance(
            "c1", planned_spend=200,
        )
        assert r["predicted"]
        assert r["predicted_revenue"] > 200

    def test_not_found(self):
        ca = CampaignROIAnalyzer()
        r = ca.predict_performance("x")
        assert not r["found"]


# --- RevenueForecaster ---

class TestForecastRevenue:
    def test_linear(self):
        rf = RevenueForecaster()
        r = rf.forecast_revenue(
            historical=[100, 110, 120],
            periods_ahead=2,
        )
        assert r["forecasted"]
        assert len(r["predictions"]) == 2
        assert r["predictions"][0] > 120

    def test_empty(self):
        rf = RevenueForecaster()
        r = rf.forecast_revenue()
        assert r["predictions"] == []


class TestModelScenario:
    def test_growth(self):
        rf = RevenueForecaster()
        r = rf.model_scenario(
            "optimistic",
            base_revenue=1000,
            growth_pct=10,
            periods=4,
        )
        assert r["modeled"]
        assert len(r["projections"]) == 4
        assert r["projections"][-1] > 1000

    def test_decline(self):
        rf = RevenueForecaster()
        r = rf.model_scenario(
            "pessimistic",
            base_revenue=1000,
            growth_pct=-10,
            periods=2,
        )
        assert r["projections"][-1] < 1000


class TestHandleSeasonality:
    def test_seasonal(self):
        rf = RevenueForecaster()
        data = [
            100, 80, 90, 120,
            150, 200, 180, 160,
            140, 110, 90, 80,
        ]
        r = rf.handle_seasonality(data)
        assert r["handled"]
        assert r["seasonal"]

    def test_insufficient(self):
        rf = RevenueForecaster()
        r = rf.handle_seasonality([1, 2])
        assert not r["seasonal"]


class TestConfidenceInterval:
    def test_basic(self):
        rf = RevenueForecaster()
        rf.forecast_revenue(
            historical=[100, 110, 120],
        )
        r = rf.confidence_interval("fcst_1")
        assert r["calculated"]
        assert len(r["intervals"]) > 0

    def test_not_found(self):
        rf = RevenueForecaster()
        r = rf.confidence_interval("x")
        assert not r["found"]


class TestAnalyzeVariance:
    def test_basic(self):
        rf = RevenueForecaster()
        r = rf.analyze_variance(
            predicted=[100, 110, 120],
            actual=[105, 108, 125],
        )
        assert r["analyzed"]
        assert r["data_points"] == 3
        assert r["accuracy_pct"] > 0

    def test_empty(self):
        rf = RevenueForecaster()
        r = rf.analyze_variance()
        assert r["mape"] == 0.0


# --- MonetizationAdvisor ---

class TestFindOpportunities:
    def test_basic(self):
        ma = MonetizationAdvisor()
        r = ma.find_opportunities(
            current_streams=["product"],
        )
        assert r["found"]
        assert r["count"] > 0

    def test_with_trends(self):
        ma = MonetizationAdvisor()
        r = ma.find_opportunities(
            market_trends=["ai_tools"],
        )
        assert r["count"] > 0


class TestSuggestPricingStrategy:
    def test_saas(self):
        ma = MonetizationAdvisor()
        r = ma.suggest_pricing_strategy(
            "saas", "premium",
        )
        assert r["suggested"]
        assert r["strategy"] == "value_based"

    def test_ecommerce(self):
        ma = MonetizationAdvisor()
        r = ma.suggest_pricing_strategy(
            "ecommerce", "budget",
        )
        assert r["strategy"] == "cost_plus"


class TestIdentifyNewStreams:
    def test_with_caps(self):
        ma = MonetizationAdvisor()
        r = ma.identify_new_streams(
            capabilities=["content", "data"],
        )
        assert r["identified"]
        assert r["count"] == 2

    def test_default(self):
        ma = MonetizationAdvisor()
        r = ma.identify_new_streams()
        assert r["count"] == 1


class TestAnalyzeMarket:
    def test_blue_ocean(self):
        ma = MonetizationAdvisor()
        r = ma.analyze_market(
            "ai", competitors=0,
            market_size=1000000,
        )
        assert r["analyzed"]
        assert r["competition_level"] == (
            "blue_ocean"
        )

    def test_intense(self):
        ma = MonetizationAdvisor()
        r = ma.analyze_market(
            "retail", competitors=20,
        )
        assert r["competition_level"] == (
            "intense"
        )


class TestRecommend:
    def test_low_growth(self):
        ma = MonetizationAdvisor()
        r = ma.recommend(
            context={"growth_pct": 2},
        )
        assert r["recommended"]
        assert any(
            rec["action"]
            == "diversify_revenue"
            for rec in r["recommendations"]
        )

    def test_default(self):
        ma = MonetizationAdvisor()
        r = ma.recommend()
        assert r["count"] >= 1


# --- RevenueOptOrchestrator ---

class TestOptimizeRevenue:
    def test_basic(self):
        ro = RevenueOptOrchestrator()
        r = ro.optimize_revenue(
            stream="product",
            amount=1000,
            customer_id="c1",
            historical=[800, 900, 1000],
        )
        assert r["pipeline_complete"]
        assert r["tracked"]
        assert r["ltv"] is not None
        assert len(r["forecast"]) > 0

    def test_minimal(self):
        ro = RevenueOptOrchestrator()
        r = ro.optimize_revenue(
            amount=500,
        )
        assert r["pipeline_complete"]


class TestQuickAnalysis:
    def test_basic(self):
        ro = RevenueOptOrchestrator()
        r = ro.quick_analysis(
            "c1", days_inactive=60,
        )
        assert r["analyzed"]
        assert r["churn_risk"] is not None
        assert r["upsell_likelihood"] is not None


class TestRevenueOptAnalytics:
    def test_basic(self):
        ro = RevenueOptOrchestrator()
        ro.optimize_revenue(amount=100)
        r = ro.get_analytics()
        assert r["pipelines_run"] == 1
        assert r["revenues_tracked"] >= 1


# --- Models ---

class TestRevenueOptModels:
    def test_revenue_stream(self):
        assert (
            RevenueStream.PRODUCT
            == "product"
        )
        assert (
            RevenueStream.SUBSCRIPTION
            == "subscription"
        )

    def test_pricing_strategy(self):
        assert (
            PricingStrategy.DYNAMIC
            == "dynamic"
        )
        assert (
            PricingStrategy.VALUE_BASED
            == "value_based"
        )

    def test_churn_risk(self):
        assert ChurnRisk.LOW == "low"
        assert (
            ChurnRisk.CRITICAL == "critical"
        )

    def test_campaign_channel(self):
        assert (
            CampaignChannel.GOOGLE_ADS
            == "google_ads"
        )
        assert (
            CampaignChannel.EMAIL == "email"
        )

    def test_forecast_method(self):
        assert (
            ForecastMethod.LINEAR == "linear"
        )
        assert (
            ForecastMethod.SEASONAL
            == "seasonal"
        )

    def test_monetization_type(self):
        assert (
            MonetizationType.FREEMIUM
            == "freemium"
        )
        assert (
            MonetizationType.MARKETPLACE
            == "marketplace"
        )

    def test_revenue_record(self):
        r = RevenueRecord(
            stream="service",
            amount=500,
        )
        assert r.stream == "service"
        assert r.record_id

    def test_churn_record(self):
        r = ChurnRecord(
            customer_id="c1",
            risk_level="high",
        )
        assert r.customer_id == "c1"
        assert r.record_id

    def test_ltv_record(self):
        r = LTVRecord(
            customer_id="c1",
            ltv_value=5000,
        )
        assert r.ltv_value == 5000
        assert r.record_id

    def test_forecast_record(self):
        r = ForecastRecord(
            period="2024-Q1",
            predicted_revenue=10000,
        )
        assert r.predicted_revenue == 10000
        assert r.record_id
