"""ATLAS Predictive Intelligence testleri.

PatternRecognizer, TrendAnalyzer, Forecaster, RiskPredictor,
DemandPredictor, BehaviorPredictor, EventPredictor, ModelManager
ve PredictionEngine testleri.
"""

import math

from app.core.predictive.behavior_predictor import BehaviorPredictor
from app.core.predictive.demand_predictor import DemandPredictor
from app.core.predictive.event_predictor import EventPredictor
from app.core.predictive.forecaster import Forecaster
from app.core.predictive.model_manager import ModelManager
from app.core.predictive.pattern_recognizer import PatternRecognizer
from app.core.predictive.prediction_engine import PredictionEngine
from app.core.predictive.risk_predictor import RiskPredictor
from app.core.predictive.trend_analyzer import TrendAnalyzer
from app.models.predictive import (
    BehaviorType,
    ConfidenceLevel,
    DataPoint,
    DemandCategory,
    DemandForecast,
    EnsembleStrategy,
    EventCategory,
    ForecastMethod,
    MetricType,
    ModelStatus,
    PatternType,
    RiskLevel,
    SeasonType,
    TrendDirection,
)


# === Yardimci fonksiyonlar ===

def _make_data(values: list[float]) -> list[DataPoint]:
    """Veri noktalari olusturur."""
    return [DataPoint(value=v, label=f"p{i}") for i, v in enumerate(values)]


def _rising_data(n: int = 20) -> list[DataPoint]:
    """Yukselis trendi verisi."""
    return _make_data([float(i) * 2 + 10 for i in range(n)])


def _falling_data(n: int = 20) -> list[DataPoint]:
    """Dusus trendi verisi."""
    return _make_data([100.0 - float(i) * 3 for i in range(n)])


def _stable_data(n: int = 20) -> list[DataPoint]:
    """Stabil veri."""
    return _make_data([50.0] * n)


def _cyclic_data(n: int = 40) -> list[DataPoint]:
    """Donesel veri."""
    return _make_data([50 + 20 * math.sin(i * 2 * math.pi / 10) for i in range(n)])


def _anomaly_data() -> list[DataPoint]:
    """Anomali iceren veri."""
    vals = [10.0] * 10 + [100.0] + [10.0] * 9
    return _make_data(vals)


# === PatternRecognizer Testleri ===


class TestPatternRecognizerInit:
    def test_defaults(self) -> None:
        pr = PatternRecognizer()
        assert pr.pattern_count == 0

    def test_custom_threshold(self) -> None:
        pr = PatternRecognizer(anomaly_threshold=3.0, min_cycle_length=5)
        assert pr.pattern_count == 0


class TestTimeSeriesPattern:
    def test_rising(self) -> None:
        pr = PatternRecognizer()
        p = pr.detect_time_series_pattern(_rising_data())
        assert p.pattern_type == PatternType.TIME_SERIES
        assert "rising" in p.parameters["trend"]
        assert p.confidence > 0

    def test_falling(self) -> None:
        pr = PatternRecognizer()
        p = pr.detect_time_series_pattern(_falling_data())
        assert "falling" in p.parameters["trend"]

    def test_empty(self) -> None:
        pr = PatternRecognizer()
        p = pr.detect_time_series_pattern([])
        assert p.confidence == 0.0

    def test_high_confidence_with_many_points(self) -> None:
        pr = PatternRecognizer()
        p = pr.detect_time_series_pattern(_rising_data(50))
        assert p.confidence >= 0.5


class TestBehavioralPattern:
    def test_dominant_action(self) -> None:
        pr = PatternRecognizer()
        actions = [{"action": "buy"}] * 8 + [{"action": "view"}] * 2
        p = pr.detect_behavioral_pattern(actions)
        assert p.pattern_type == PatternType.BEHAVIORAL
        assert p.parameters["dominant_action"] == "buy"

    def test_empty_actions(self) -> None:
        pr = PatternRecognizer()
        p = pr.detect_behavioral_pattern([])
        assert p.confidence == 0.0

    def test_repetition_rate(self) -> None:
        pr = PatternRecognizer()
        actions = [{"action": "click"}, {"action": "click"}, {"action": "click"}]
        p = pr.detect_behavioral_pattern(actions)
        assert p.parameters["repetition_rate"] > 0


class TestAnomalyDetection:
    def test_detect_anomaly(self) -> None:
        pr = PatternRecognizer()
        anomalies = pr.detect_anomalies(_anomaly_data())
        assert len(anomalies) >= 1
        assert anomalies[0].pattern_type == PatternType.ANOMALY

    def test_no_anomaly_stable(self) -> None:
        pr = PatternRecognizer()
        anomalies = pr.detect_anomalies(_stable_data())
        assert len(anomalies) == 0

    def test_few_points(self) -> None:
        pr = PatternRecognizer()
        anomalies = pr.detect_anomalies(_make_data([1.0, 2.0]))
        assert len(anomalies) == 0


class TestCyclicalPattern:
    def test_detect_cycle(self) -> None:
        pr = PatternRecognizer()
        p = pr.detect_cyclical_pattern(_cyclic_data())
        assert p is not None
        assert p.pattern_type == PatternType.CYCLICAL
        assert p.parameters["period"] > 0

    def test_no_cycle_short_data(self) -> None:
        pr = PatternRecognizer()
        p = pr.detect_cyclical_pattern(_make_data([1, 2, 3]))
        assert p is None

    def test_no_cycle_stable(self) -> None:
        pr = PatternRecognizer()
        p = pr.detect_cyclical_pattern(_stable_data())
        assert p is None


class TestTrendIdentification:
    def test_rising_trend(self) -> None:
        pr = PatternRecognizer()
        p = pr.identify_trend(_rising_data())
        assert p.pattern_type == PatternType.TREND
        assert "rising" in p.parameters["direction"]

    def test_falling_trend(self) -> None:
        pr = PatternRecognizer()
        p = pr.identify_trend(_falling_data())
        assert "falling" in p.parameters["direction"]

    def test_insufficient_data(self) -> None:
        pr = PatternRecognizer()
        p = pr.identify_trend(_make_data([5.0]))
        assert p.confidence == 0.0


class TestPatternRecognizerProperties:
    def test_patterns_list(self) -> None:
        pr = PatternRecognizer()
        pr.detect_time_series_pattern(_rising_data())
        assert pr.pattern_count == 1
        assert len(pr.patterns) == 1

    def test_clear(self) -> None:
        pr = PatternRecognizer()
        pr.detect_time_series_pattern(_rising_data())
        pr.clear()
        assert pr.pattern_count == 0


# === TrendAnalyzer Testleri ===


class TestTrendAnalyzerInit:
    def test_defaults(self) -> None:
        ta = TrendAnalyzer()
        assert ta.result_count == 0

    def test_custom(self) -> None:
        ta = TrendAnalyzer(window_size=10, smoothing_factor=0.5)
        assert ta.result_count == 0


class TestMovingAverage:
    def test_basic(self) -> None:
        ta = TrendAnalyzer(window_size=3)
        ma = ta.moving_average([1, 2, 3, 4, 5])
        assert len(ma) == 3
        assert abs(ma[0] - 2.0) < 0.01

    def test_short_data(self) -> None:
        ta = TrendAnalyzer(window_size=5)
        ma = ta.moving_average([1, 2])
        assert len(ma) == 1


class TestExponentialSmoothing:
    def test_basic(self) -> None:
        ta = TrendAnalyzer(smoothing_factor=0.5)
        es = ta.exponential_smoothing([10, 20, 30, 40])
        assert len(es) == 4
        assert es[0] == 10.0

    def test_empty(self) -> None:
        ta = TrendAnalyzer()
        es = ta.exponential_smoothing([])
        assert es == []


class TestSeasonalityDetection:
    def test_weekly_pattern(self) -> None:
        ta = TrendAnalyzer()
        # 7 gunluk periyodik veri
        vals = [10 + 5 * math.sin(i * 2 * math.pi / 7) for i in range(100)]
        season = ta.detect_seasonality(vals)
        assert season == SeasonType.WEEKLY

    def test_no_seasonality(self) -> None:
        ta = TrendAnalyzer()
        vals = [50.0] * 20
        season = ta.detect_seasonality(vals)
        assert season is None

    def test_short_data(self) -> None:
        ta = TrendAnalyzer()
        season = ta.detect_seasonality([1, 2, 3])
        assert season is None


class TestGrowthRate:
    def test_positive_growth(self) -> None:
        ta = TrendAnalyzer()
        rate = ta.calculate_growth_rate([100, 120, 150])
        assert rate > 0

    def test_negative_growth(self) -> None:
        ta = TrendAnalyzer()
        rate = ta.calculate_growth_rate([100, 80, 60])
        assert rate < 0

    def test_zero_start(self) -> None:
        ta = TrendAnalyzer()
        rate = ta.calculate_growth_rate([0, 10])
        assert rate == 1.0

    def test_single_point(self) -> None:
        ta = TrendAnalyzer()
        rate = ta.calculate_growth_rate([50])
        assert rate == 0.0


class TestInflectionPoints:
    def test_find_inflections(self) -> None:
        ta = TrendAnalyzer()
        # Onceup yuksel sonra dus
        vals = [1, 2, 4, 8, 7, 5, 3, 2, 3, 5]
        inflections = ta.find_inflection_points(vals)
        assert len(inflections) > 0

    def test_linear_no_inflection(self) -> None:
        ta = TrendAnalyzer()
        vals = [1, 2, 3, 4, 5]
        inflections = ta.find_inflection_points(vals)
        assert len(inflections) == 0


class TestTrendAnalyze:
    def test_rising(self) -> None:
        ta = TrendAnalyzer()
        result = ta.analyze(_rising_data())
        assert result.direction == TrendDirection.RISING
        assert result.slope > 0
        assert result.strength > 0

    def test_falling(self) -> None:
        ta = TrendAnalyzer()
        result = ta.analyze(_falling_data())
        assert result.direction == TrendDirection.FALLING
        assert result.slope < 0

    def test_empty(self) -> None:
        ta = TrendAnalyzer()
        result = ta.analyze([])
        assert result.direction == TrendDirection.STABLE

    def test_results_stored(self) -> None:
        ta = TrendAnalyzer()
        ta.analyze(_rising_data())
        assert ta.result_count == 1
        assert len(ta.results) == 1


# === Forecaster Testleri ===


class TestForecasterInit:
    def test_defaults(self) -> None:
        f = Forecaster()
        assert f.forecast_count == 0

    def test_custom(self) -> None:
        f = Forecaster(default_method=ForecastMethod.LINEAR_REGRESSION, confidence_level=0.90)
        assert f.forecast_count == 0


class TestForecastMovingAverage:
    def test_basic(self) -> None:
        f = Forecaster()
        result = f.forecast_moving_average([10, 20, 30, 40, 50], horizon=3)
        assert len(result.predictions) == 3
        assert result.method == ForecastMethod.MOVING_AVERAGE
        assert len(result.confidence_lower) == 3
        assert len(result.confidence_upper) == 3

    def test_empty(self) -> None:
        f = Forecaster()
        result = f.forecast_moving_average([], horizon=3)
        assert len(result.predictions) == 0


class TestForecastExponentialSmoothing:
    def test_basic(self) -> None:
        f = Forecaster()
        result = f.forecast_exponential_smoothing([10, 20, 30, 40], horizon=5)
        assert len(result.predictions) == 5
        assert result.method == ForecastMethod.EXPONENTIAL_SMOOTHING

    def test_empty(self) -> None:
        f = Forecaster()
        result = f.forecast_exponential_smoothing([])
        assert len(result.predictions) == 0


class TestForecastLinearRegression:
    def test_rising(self) -> None:
        f = Forecaster()
        result = f.forecast_linear_regression([10, 20, 30, 40, 50], horizon=3)
        assert len(result.predictions) == 3
        assert result.predictions[0].value > 50  # Trend devam etmeli

    def test_single_point(self) -> None:
        f = Forecaster()
        result = f.forecast_linear_regression([10], horizon=3)
        assert len(result.predictions) == 0


class TestForecastEnsemble:
    def test_basic(self) -> None:
        f = Forecaster()
        result = f.forecast_ensemble([10, 20, 30, 40, 50], horizon=3)
        assert len(result.predictions) == 3
        assert result.method == ForecastMethod.ENSEMBLE

    def test_empty(self) -> None:
        f = Forecaster()
        result = f.forecast_ensemble([])
        assert len(result.predictions) == 0


class TestForecastMethod:
    def test_default_method(self) -> None:
        f = Forecaster(default_method=ForecastMethod.LINEAR_REGRESSION)
        result = f.forecast([10, 20, 30, 40], horizon=2)
        assert result.method == ForecastMethod.LINEAR_REGRESSION

    def test_override_method(self) -> None:
        f = Forecaster()
        result = f.forecast([10, 20, 30], horizon=2, method=ForecastMethod.EXPONENTIAL_SMOOTHING)
        assert result.method == ForecastMethod.EXPONENTIAL_SMOOTHING


class TestScenarioProjection:
    def test_basic(self) -> None:
        f = Forecaster()
        scenarios = f.scenario_projection([10, 20, 30, 40, 50], horizon=3)
        assert "optimistic" in scenarios
        assert "baseline" in scenarios
        assert "pessimistic" in scenarios

    def test_custom_scenarios(self) -> None:
        f = Forecaster()
        scenarios = f.scenario_projection([10, 20, 30], horizon=2, scenarios={"bull": 1.5, "bear": 0.5})
        assert "bull" in scenarios
        assert "bear" in scenarios

    def test_optimistic_higher(self) -> None:
        f = Forecaster()
        scenarios = f.scenario_projection([10, 20, 30, 40, 50], horizon=3)
        opt = scenarios["optimistic"].predictions[0].value
        pes = scenarios["pessimistic"].predictions[0].value
        assert opt > pes


# === RiskPredictor Testleri ===


class TestRiskPredictorInit:
    def test_defaults(self) -> None:
        rp = RiskPredictor()
        assert len(rp.history) == 0

    def test_custom_weights(self) -> None:
        rp = RiskPredictor(factor_weights={"a": 0.5, "b": 0.5})
        assert len(rp.history) == 0


class TestFailureProbability:
    def test_stable_above_threshold(self) -> None:
        rp = RiskPredictor()
        data = _make_data([100, 100, 100, 100])
        prob = rp.calculate_failure_probability(data, threshold=50)
        assert prob < 0.3

    def test_declining_near_threshold(self) -> None:
        rp = RiskPredictor()
        data = _make_data([100, 80, 60, 40])
        prob = rp.calculate_failure_probability(data, threshold=50)
        assert prob > 0.2

    def test_empty(self) -> None:
        rp = RiskPredictor()
        prob = rp.calculate_failure_probability([], threshold=0)
        assert prob == 0.5


class TestRiskFactorWeighting:
    def test_weighted(self) -> None:
        rp = RiskPredictor()
        score = rp.weight_risk_factors({"severity": 0.8, "frequency": 0.6})
        assert 0.0 <= score <= 1.0

    def test_empty_factors(self) -> None:
        rp = RiskPredictor()
        score = rp.weight_risk_factors({})
        assert score == 0.0


class TestEarlyWarnings:
    def test_consecutive_drops(self) -> None:
        rp = RiskPredictor()
        data = _make_data([100, 90, 80, 70, 60])
        warnings = rp.detect_early_warnings(data)
        assert any("dusus" in w for w in warnings)

    def test_rapid_change(self) -> None:
        rp = RiskPredictor()
        data = _make_data([100, 100, 100, 50])
        warnings = rp.detect_early_warnings(data)
        assert len(warnings) > 0

    def test_stable_no_warnings(self) -> None:
        rp = RiskPredictor()
        data = _make_data([50, 50, 50, 50])
        warnings = rp.detect_early_warnings(data)
        assert len(warnings) == 0


class TestMitigationSuggestions:
    def test_critical_all(self) -> None:
        rp = RiskPredictor()
        suggestions = rp.suggest_mitigations("system_failure", RiskLevel.CRITICAL)
        assert len(suggestions) >= 3

    def test_low_fewer(self) -> None:
        rp = RiskPredictor()
        suggestions = rp.suggest_mitigations("security", RiskLevel.LOW)
        assert len(suggestions) == 1

    def test_unknown_category(self) -> None:
        rp = RiskPredictor()
        suggestions = rp.suggest_mitigations("unknown", RiskLevel.HIGH)
        assert len(suggestions) > 0


class TestAssessRisk:
    def test_full_assessment(self) -> None:
        rp = RiskPredictor()
        data = _make_data([100, 80, 60, 40, 20])
        result = rp.assess_risk(data, factors={"severity": 0.8, "frequency": 0.5}, category="system_failure")
        assert result.risk_level in list(RiskLevel)
        assert 0.0 <= result.risk_score <= 1.0
        assert len(result.mitigations) > 0

    def test_low_risk(self) -> None:
        rp = RiskPredictor()
        data = _make_data([100, 100, 100, 100])
        result = rp.assess_risk(data, threshold=0)
        assert result.risk_score < 0.5


# === DemandPredictor Testleri ===


class TestDemandPredictorInit:
    def test_defaults(self) -> None:
        dp = DemandPredictor()
        assert dp.forecast_count == 0


class TestSalesForecast:
    def test_basic(self) -> None:
        dp = DemandPredictor()
        history = _make_data([100, 110, 120, 130])
        result = dp.forecast_sales(history, horizon_days=30, month=12)
        assert result.category == DemandCategory.SALES
        assert result.predicted_demand > 0
        assert result.seasonal_factor == 1.3  # Aralik

    def test_empty(self) -> None:
        dp = DemandPredictor()
        result = dp.forecast_sales([])
        assert result.predicted_demand == 0.0


class TestResourceDemand:
    def test_growing(self) -> None:
        dp = DemandPredictor()
        data = _make_data([50, 60, 70])
        result = dp.forecast_resource_demand(data, horizon_days=30)
        assert result.category == DemandCategory.RESOURCE
        assert result.predicted_demand > 0


class TestCapacityPlanning:
    def test_over_capacity(self) -> None:
        dp = DemandPredictor()
        forecast = DemandForecast(predicted_demand=95, category=DemandCategory.SALES)
        plan = dp.plan_capacity(forecast, current_capacity=100)
        assert plan["urgency"] == "critical"  # %95 utilization

    def test_under_capacity(self) -> None:
        dp = DemandPredictor()
        forecast = DemandForecast(predicted_demand=30, category=DemandCategory.SALES)
        plan = dp.plan_capacity(forecast, current_capacity=100)
        assert plan["urgency"] == "low"


class TestInventoryOptimization:
    def test_basic(self) -> None:
        dp = DemandPredictor()
        forecast = DemandForecast(
            predicted_demand=300,
            current_demand=250,
            forecast_horizon_days=30,
            category=DemandCategory.SALES,
        )
        result = dp.optimize_inventory(forecast, lead_time_days=7)
        assert result.category == DemandCategory.INVENTORY
        assert result.optimal_inventory > forecast.predicted_demand
        assert result.reorder_point > 0


class TestSeasonalAdjustment:
    def test_december_high(self) -> None:
        dp = DemandPredictor()
        adjusted = dp.apply_seasonal_adjustment(100, month=12)
        assert adjusted == 130.0  # 1.3x

    def test_january_low(self) -> None:
        dp = DemandPredictor()
        adjusted = dp.apply_seasonal_adjustment(100, month=1)
        assert adjusted == 80.0  # 0.8x


# === BehaviorPredictor Testleri ===


class TestBehaviorPredictorInit:
    def test_defaults(self) -> None:
        bp = BehaviorPredictor()
        assert bp.prediction_count == 0


class TestPurchasePrediction:
    def test_active_buyer(self) -> None:
        bp = BehaviorPredictor()
        history = [
            {"days_ago": 5, "amount": 200},
            {"days_ago": 15, "amount": 300},
            {"days_ago": 30, "amount": 150},
        ]
        result = bp.predict_purchase(history)
        assert result.behavior_type == BehaviorType.PURCHASE
        assert result.probability > 0.3
        assert result.lifetime_value > 0

    def test_empty_history(self) -> None:
        bp = BehaviorPredictor()
        result = bp.predict_purchase([])
        assert result.probability == 0.1


class TestChurnPrediction:
    def test_high_risk(self) -> None:
        bp = BehaviorPredictor()
        data = [{"inactive_days": 25, "sessions": 1, "avg_duration_min": 2}]
        result = bp.predict_churn(data)
        assert result.behavior_type == BehaviorType.CHURN
        assert result.churn_risk > 0.5

    def test_low_risk(self) -> None:
        bp = BehaviorPredictor()
        data = [{"inactive_days": 0, "sessions": 20, "avg_duration_min": 30}]
        result = bp.predict_churn(data)
        assert result.churn_risk < 0.3

    def test_retention_suggestions(self) -> None:
        bp = BehaviorPredictor()
        data = [{"inactive_days": 30, "sessions": 0, "avg_duration_min": 0}]
        result = bp.predict_churn(data)
        assert len(result.next_actions) > 0


class TestNextActionPrediction:
    def test_predict(self) -> None:
        bp = BehaviorPredictor()
        seq = ["view", "search", "view", "buy", "view", "search", "view"]
        result = bp.predict_next_action(seq)
        assert len(result.next_actions) > 0

    def test_empty_sequence(self) -> None:
        bp = BehaviorPredictor()
        result = bp.predict_next_action([])
        assert result.next_actions == ["unknown"]


class TestEngagementForecast:
    def test_rising(self) -> None:
        bp = BehaviorPredictor()
        result = bp.forecast_engagement([0.3, 0.4, 0.5, 0.6, 0.7])
        assert result.engagement_score > 0.4

    def test_empty(self) -> None:
        bp = BehaviorPredictor()
        result = bp.forecast_engagement([])
        assert result.engagement_score == 0.5


class TestLifetimeValue:
    def test_high_value(self) -> None:
        bp = BehaviorPredictor()
        result = bp.estimate_lifetime_value(avg_purchase=500, purchase_frequency=2, avg_lifespan_months=24)
        assert result.lifetime_value == 24000.0
        assert "VIP" in result.next_actions[0]

    def test_low_value(self) -> None:
        bp = BehaviorPredictor()
        result = bp.estimate_lifetime_value(avg_purchase=20, purchase_frequency=0.5, avg_lifespan_months=6)
        assert result.lifetime_value == 60.0


# === EventPredictor Testleri ===


class TestEventPredictorInit:
    def test_defaults(self) -> None:
        ep = EventPredictor()
        assert ep.prediction_count == 0


class TestEventLikelihood:
    def test_high_indicators(self) -> None:
        ep = EventPredictor()
        result = ep.predict_likelihood(
            EventCategory.SYSTEM_FAILURE,
            indicators={"cpu": 0.9, "memory": 0.85, "disk": 0.95},
        )
        assert result.likelihood > 0.7
        assert result.event_category == EventCategory.SYSTEM_FAILURE

    def test_low_indicators(self) -> None:
        ep = EventPredictor()
        result = ep.predict_likelihood(
            EventCategory.SECURITY_BREACH,
            indicators={"failed_logins": 0.1, "port_scan": 0.05},
        )
        assert result.likelihood < 0.5

    def test_empty_indicators(self) -> None:
        ep = EventPredictor()
        result = ep.predict_likelihood(EventCategory.OPPORTUNITY, indicators={})
        assert result.likelihood == 0.1


class TestEventTiming:
    def test_approaching_threshold(self) -> None:
        ep = EventPredictor()
        data = _make_data([70, 75, 80, 85, 90])
        hours = ep.predict_timing(data, threshold=100)
        assert hours > 0

    def test_moving_away(self) -> None:
        ep = EventPredictor()
        data = _make_data([90, 85, 80, 75])
        hours = ep.predict_timing(data, threshold=100)
        assert hours == 0.0


class TestCascadeEffects:
    def test_high_severity(self) -> None:
        ep = EventPredictor()
        effects = ep.analyze_cascade_effects(EventCategory.SYSTEM_FAILURE, severity=0.9)
        assert len(effects) >= 3

    def test_low_severity(self) -> None:
        ep = EventPredictor()
        effects = ep.analyze_cascade_effects(EventCategory.MARKET_SHIFT, severity=0.2)
        assert len(effects) == 1


class TestTriggerConditions:
    def test_triggered(self) -> None:
        ep = EventPredictor()
        triggered = ep.check_trigger_conditions(
            EventCategory.SYSTEM_FAILURE,
            current_values={"cpu": 0.95, "memory": 0.5},
            thresholds={"cpu": 0.9, "memory": 0.8},
        )
        assert len(triggered) == 1
        assert "cpu" in triggered[0]

    def test_nothing_triggered(self) -> None:
        ep = EventPredictor()
        triggered = ep.check_trigger_conditions(
            EventCategory.SECURITY_BREACH,
            current_values={"failed_logins": 0.1},
            thresholds={"failed_logins": 0.5},
        )
        assert len(triggered) == 0


class TestPreventionRecommendations:
    def test_high_likelihood(self) -> None:
        ep = EventPredictor()
        recs = ep.get_prevention_recommendations(EventCategory.SYSTEM_FAILURE, likelihood=0.8)
        assert "Acil durum plani aktifle" in recs

    def test_low_likelihood(self) -> None:
        ep = EventPredictor()
        recs = ep.get_prevention_recommendations(EventCategory.THREAT, likelihood=0.2)
        assert len(recs) == 1


# === ModelManager Testleri ===


class TestModelManagerInit:
    def test_defaults(self) -> None:
        mm = ModelManager()
        assert mm.model_count == 0
        assert mm.active_model is None


class TestTrainModel:
    def test_linear(self) -> None:
        mm = ModelManager()
        model = mm.train_model("test_linear", "linear", [10, 20, 30, 40, 50])
        assert model.status == ModelStatus.TRAINED
        assert model.name == "test_linear"
        assert model.parameters["slope"] > 0

    def test_default_type(self) -> None:
        mm = ModelManager()
        model = mm.train_model("test_default", "average", [5, 10, 15])
        assert model.status == ModelStatus.TRAINED
        assert "mean" in model.parameters

    def test_empty_data(self) -> None:
        mm = ModelManager()
        model = mm.train_model("empty", "linear", [])
        assert model.status == ModelStatus.FAILED


class TestEvaluateModel:
    def test_evaluate(self) -> None:
        mm = ModelManager()
        model = mm.train_model("eval_test", "average", [10, 20, 30])
        metrics = mm.evaluate_model(model.id, [15, 25, 35])
        assert MetricType.MAE.value in metrics
        assert MetricType.RMSE.value in metrics
        assert MetricType.R_SQUARED.value in metrics

    def test_nonexistent(self) -> None:
        mm = ModelManager()
        metrics = mm.evaluate_model("nonexistent", [1, 2, 3])
        assert metrics == {}


class TestSelectBestModel:
    def test_select(self) -> None:
        mm = ModelManager()
        m1 = mm.train_model("good", "linear", [10, 20, 30, 40, 50])
        m2 = mm.train_model("bad", "average", [10, 20, 30, 40, 50])
        mm.evaluate_model(m1.id, [55, 65])
        mm.evaluate_model(m2.id, [55, 65])
        best = mm.select_best_model(MetricType.MAE)
        assert best is not None
        assert best.status == ModelStatus.DEPLOYED

    def test_no_candidates(self) -> None:
        mm = ModelManager()
        best = mm.select_best_model()
        assert best is None


class TestHyperparameterTuning:
    def test_tune(self) -> None:
        mm = ModelManager()
        model = mm.tune_hyperparameters(
            "tuned", "linear",
            [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            param_grid={"alpha": [0.1, 0.3, 0.5]},
        )
        assert model.status in (ModelStatus.TRAINED, ModelStatus.DEPLOYED)


class TestModelVersioning:
    def test_version(self) -> None:
        mm = ModelManager()
        model = mm.train_model("v_test", "linear", [1, 2, 3])
        assert mm.get_model_version(model.id) == "1.0.0"
        assert mm.update_model_version(model.id, "2.0.0")
        assert mm.get_model_version(model.id) == "2.0.0"

    def test_deprecate(self) -> None:
        mm = ModelManager()
        model = mm.train_model("dep_test", "linear", [1, 2, 3])
        assert mm.deprecate_model(model.id)
        assert mm.get_model(model.id).status == ModelStatus.DEPRECATED

    def test_deprecate_nonexistent(self) -> None:
        mm = ModelManager()
        assert not mm.deprecate_model("nonexistent")


# === PredictionEngine Testleri ===


class TestPredictionEngineInit:
    def test_defaults(self) -> None:
        pe = PredictionEngine()
        assert pe.result_count == 0
        assert pe.feedback_count == 0

    def test_custom(self) -> None:
        pe = PredictionEngine(
            forecast_horizon=14,
            confidence_threshold=0.8,
            ensemble_strategy="average",
        )
        assert pe.result_count == 0


class TestPredict:
    def test_with_data(self) -> None:
        pe = PredictionEngine()
        data = _rising_data(20)
        result = pe.predict("satis tahmini", data=data)
        assert result.query == "satis tahmini"
        assert result.combined_score > 0
        assert result.confidence > 0
        assert len(result.predictions) > 0
        assert result.explanation != ""

    def test_without_data(self) -> None:
        pe = PredictionEngine()
        result = pe.predict("genel tahmin")
        assert result.combined_score == 0.0

    def test_confidence_level(self) -> None:
        pe = PredictionEngine()
        data = _rising_data(30)
        result = pe.predict("trend analizi", data=data)
        assert result.confidence_level in list(ConfidenceLevel)


class TestEnsembleStrategies:
    def test_average(self) -> None:
        pe = PredictionEngine(ensemble_strategy="average")
        result = pe.predict("test", data=_rising_data())
        assert result.strategy == EnsembleStrategy.AVERAGE

    def test_weighted(self) -> None:
        pe = PredictionEngine(ensemble_strategy="weighted")
        result = pe.predict("test", data=_rising_data())
        assert result.strategy == EnsembleStrategy.WEIGHTED

    def test_best_pick(self) -> None:
        pe = PredictionEngine(ensemble_strategy="best_pick")
        result = pe.predict("test", data=_rising_data())
        assert result.strategy == EnsembleStrategy.BEST_PICK

    def test_invalid_strategy_fallback(self) -> None:
        pe = PredictionEngine(ensemble_strategy="invalid")
        assert pe._ensemble_strategy == EnsembleStrategy.WEIGHTED


class TestFeedbackIntegration:
    def test_add_feedback(self) -> None:
        pe = PredictionEngine()
        result = pe.predict("test", data=_rising_data())
        pe.add_feedback(result.id, actual_value=0.75, comment="Yakin tahmin")
        assert pe.feedback_count == 1

    def test_feedback_nonexistent(self) -> None:
        pe = PredictionEngine()
        pe.add_feedback("nonexistent", actual_value=0.5)
        assert pe.feedback_count == 1  # Yine de kaydedilir


class TestGetResult:
    def test_get(self) -> None:
        pe = PredictionEngine()
        result = pe.predict("arama", data=_rising_data())
        found = pe.get_result(result.id)
        assert found is not None
        assert found.id == result.id

    def test_get_nonexistent(self) -> None:
        pe = PredictionEngine()
        assert pe.get_result("nonexistent") is None


# === End-to-End Testleri ===


class TestEndToEnd:
    def test_full_pipeline(self) -> None:
        """Tam pipeline: oruntu -> trend -> tahmin -> risk."""
        # Oruntu tanima
        pr = PatternRecognizer()
        data = _rising_data(30)
        pattern = pr.detect_time_series_pattern(data)
        assert pattern.confidence > 0

        # Trend analizi
        ta = TrendAnalyzer()
        trend = ta.analyze(data)
        assert trend.direction == TrendDirection.RISING

        # Tahmin
        f = Forecaster()
        values = [d.value for d in data]
        forecast = f.forecast(values, horizon=7)
        assert len(forecast.predictions) == 7

        # Risk
        rp = RiskPredictor()
        risk = rp.assess_risk(data)
        assert risk.risk_level in list(RiskLevel)

    def test_demand_to_inventory(self) -> None:
        """Talep tahmini -> envanter optimizasyonu."""
        dp = DemandPredictor()
        history = _make_data([100, 110, 120, 130, 140])
        sales = dp.forecast_sales(history, horizon_days=30, month=6)
        inventory = dp.optimize_inventory(sales, lead_time_days=7)
        plan = dp.plan_capacity(sales, current_capacity=200)

        assert inventory.optimal_inventory > 0
        assert inventory.reorder_point > 0
        assert "recommendation" in plan

    def test_behavior_to_event(self) -> None:
        """Davranis tahmini -> olay tahmini."""
        bp = BehaviorPredictor()
        churn = bp.predict_churn([{"inactive_days": 20, "sessions": 2, "avg_duration_min": 5}])

        ep = EventPredictor()
        event = ep.predict_likelihood(
            EventCategory.USER_MILESTONE,
            indicators={"churn_risk": churn.churn_risk, "engagement": churn.engagement_score},
        )
        assert event.likelihood > 0

    def test_prediction_engine_orchestration(self) -> None:
        """PredictionEngine tum sistemi orkestre eder."""
        pe = PredictionEngine(ensemble_strategy="weighted")

        # Birden fazla tahmin
        r1 = pe.predict("satis trendi", data=_rising_data(20))
        r2 = pe.predict("risk analizi", data=_falling_data(20))

        assert r1.combined_score != r2.combined_score
        assert pe.result_count == 2
        assert len(pe.results) == 2

    def test_model_lifecycle(self) -> None:
        """Model yasam dongusu: egit -> degerlendir -> sec -> deprecate."""
        mm = ModelManager()
        m1 = mm.train_model("linear_v1", "linear", [10, 20, 30, 40, 50, 60])
        m2 = mm.train_model("avg_v1", "average", [10, 20, 30, 40, 50, 60])

        mm.evaluate_model(m1.id, [65, 75, 85])
        mm.evaluate_model(m2.id, [65, 75, 85])

        best = mm.select_best_model(MetricType.MAE)
        assert best is not None
        assert best.status == ModelStatus.DEPLOYED

        # Eski modeli kullanim disi birak
        other_id = m1.id if best.id != m1.id else m2.id
        mm.deprecate_model(other_id)
        assert mm.get_model(other_id).status == ModelStatus.DEPRECATED
