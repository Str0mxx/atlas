"""ATLAS A/B Testing & Experiment Platform testleri.

ABExperimentDesigner, VariantManager,
TrafficSplitter, ABStatisticalAnalyzer,
WinnerDetector, AutoRollout,
ExperimentArchive, MultivariateTester,
ABTestingOrchestrator testleri.
"""

import pytest

from app.core.abtesting.ab_statistical_analyzer import (
    ABStatisticalAnalyzer,
)
from app.core.abtesting.abtesting_orchestrator import (
    ABTestingOrchestrator,
)
from app.core.abtesting.auto_rollout import (
    AutoRollout,
)
from app.core.abtesting.experiment_archive import (
    ExperimentArchive,
)
from app.core.abtesting.experiment_designer import (
    ABExperimentDesigner,
)
from app.core.abtesting.multivariate_tester import (
    MultivariateTester,
)
from app.core.abtesting.traffic_splitter import (
    TrafficSplitter,
)
from app.core.abtesting.variant_manager import (
    VariantManager,
)
from app.core.abtesting.winner_detector import (
    WinnerDetector,
)
from app.models.abtesting_models import (
    DesignType,
    ExperimentRecord,
    ExperimentStatus,
    MetricType,
    ResultRecord,
    RolloutRecord,
    RolloutStage,
    SignificanceLevel,
    VariantRecord,
    VariantType,
)


# ── ABExperimentDesigner ────────────────


class TestDefineHypothesis:
    """define_hypothesis testleri."""

    def test_basic(self):
        d = ABExperimentDesigner()
        r = d.define_hypothesis("exp_1")
        assert r["defined"] is True
        assert r["metric"] == "conversion"

    def test_with_lift(self):
        d = ABExperimentDesigner()
        r = d.define_hypothesis(
            "exp_1", expected_lift=0.10,
        )
        assert r["expected_lift"] == 0.10
        assert d.hypothesis_count == 1


class TestCreateVariants:
    """create_variants testleri."""

    def test_two_variants(self):
        d = ABExperimentDesigner()
        r = d.create_variants("exp_1")
        assert r["created"] is True
        assert r["count"] == 2

    def test_three_variants(self):
        d = ABExperimentDesigner()
        r = d.create_variants(
            "exp_1", variant_count=3,
        )
        assert r["count"] == 3

    def test_named(self):
        d = ABExperimentDesigner()
        r = d.create_variants(
            "exp_1",
            names=["A", "B"],
        )
        assert r["variants"][0]["name"] == "A"


class TestCalculateSampleSize:
    """calculate_sample_size testleri."""

    def test_basic(self):
        d = ABExperimentDesigner()
        r = d.calculate_sample_size()
        assert r["calculated"] is True
        assert r["sample_size_per_variant"] > 0
        assert r["total_sample_size"] > 0

    def test_high_confidence(self):
        d = ABExperimentDesigner()
        r1 = d.calculate_sample_size(
            confidence=0.95,
        )
        r2 = d.calculate_sample_size(
            confidence=0.99,
        )
        assert (
            r2["sample_size_per_variant"]
            >= r1["sample_size_per_variant"]
        )


class TestCalculateDuration:
    """calculate_duration testleri."""

    def test_basic(self):
        d = ABExperimentDesigner()
        r = d.calculate_duration(
            sample_size=1000,
            daily_traffic=100,
        )
        assert r["calculated"] is True
        assert r["duration_days"] == 20


class TestDefineSuccessMetrics:
    """define_success_metrics testleri."""

    def test_basic(self):
        d = ABExperimentDesigner()
        r = d.define_success_metrics(
            "exp_1",
            secondary_metrics=["revenue"],
            guardrails=["latency"],
        )
        assert r["defined"] is True
        assert r["secondary_count"] == 1
        assert r["guardrail_count"] == 1
        assert d.experiment_count == 1


# ── VariantManager ──────────────────────


class TestConfigureVariant:
    """configure_variant testleri."""

    def test_basic(self):
        v = VariantManager()
        r = v.configure_variant(
            "exp_1", "control",
        )
        assert r["configured"] is True
        assert v.variant_count == 1

    def test_with_config(self):
        v = VariantManager()
        r = v.configure_variant(
            "exp_1", "treatment",
            config={"color": "blue"},
            traffic_pct=30.0,
        )
        assert r["traffic_pct"] == 30.0


class TestCreateFeatureFlag:
    """create_feature_flag testleri."""

    def test_basic(self):
        v = VariantManager()
        r = v.create_feature_flag(
            "new_checkout",
        )
        assert r["created"] is True
        assert r["default_value"] is False
        assert v.flag_count == 1


class TestSetRolloutPercentage:
    """set_rollout_percentage testleri."""

    def test_basic(self):
        v = VariantManager()
        v.configure_variant(
            "exp_1", "treatment",
        )
        r = v.set_rollout_percentage(
            "exp_1", "treatment", 75.0,
        )
        assert r["updated"] is True
        assert r["percentage"] == 75.0

    def test_not_found(self):
        v = VariantManager()
        r = v.set_rollout_percentage(
            "xxx", "yyy", 50.0,
        )
        assert r["found"] is False


class TestAddTargetingRule:
    """add_targeting_rule testleri."""

    def test_basic(self):
        v = VariantManager()
        r = v.add_targeting_rule(
            "exp_1",
            rule_type="segment",
            condition="country",
            value="TR",
        )
        assert r["added"] is True
        assert r["rule_count"] == 1


class TestSetMutualExclusion:
    """set_mutual_exclusion testleri."""

    def test_basic(self):
        v = VariantManager()
        r = v.set_mutual_exclusion(
            "exp_1", "exp_2",
        )
        assert r["excluded"] is True

    def test_check(self):
        v = VariantManager()
        v.set_mutual_exclusion(
            "exp_1", "exp_2",
        )
        r = v.check_exclusion("exp_1")
        assert r["count"] == 1
        assert "exp_2" in r["excluded_with"]


# ── TrafficSplitter ─────────────────────


class TestAssignRandom:
    """assign_random testleri."""

    def test_basic(self):
        s = TrafficSplitter()
        r = s.assign_random(
            "user_1", "exp_1",
        )
        assert r["assigned"] is True
        assert r["variant"] in [
            "control", "treatment",
        ]
        assert s.assignment_count == 1

    def test_holdout(self):
        s = TrafficSplitter()
        s.create_holdout(
            ["user_1", "user_2"],
            holdout_pct=100,
        )
        r = s.assign_random(
            "user_1", "exp_1",
        )
        assert r["holdout"] is True


class TestAssignConsistent:
    """assign_consistent testleri."""

    def test_same_assignment(self):
        s = TrafficSplitter()
        r1 = s.assign_consistent(
            "user_1", "exp_1",
        )
        r2 = s.assign_consistent(
            "user_1", "exp_1",
        )
        assert r1["variant"] == r2["variant"]
        assert r2["cached"] is True


class TestStratifiedSample:
    """stratified_sample testleri."""

    def test_basic(self):
        s = TrafficSplitter()
        users = [
            {"user_id": "u1", "segment": "A"},
            {"user_id": "u2", "segment": "A"},
            {"user_id": "u3", "segment": "B"},
        ]
        r = s.stratified_sample(
            users, "exp_1",
        )
        assert r["sampled"] is True
        assert r["strata_count"] == 2
        assert r["total_assigned"] == 3


class TestCreateHoldout:
    """create_holdout testleri."""

    def test_basic(self):
        s = TrafficSplitter()
        r = s.create_holdout(
            ["u1", "u2", "u3", "u4"],
            holdout_pct=25.0,
        )
        assert r["created"] is True
        assert r["holdout_size"] >= 1


class TestRebalance:
    """rebalance testleri."""

    def test_basic(self):
        s = TrafficSplitter()
        r = s.rebalance(
            "exp_1",
            new_weights={
                "control": 0.3,
                "treatment": 0.7,
            },
        )
        assert r["rebalanced"] is True


# ── ABStatisticalAnalyzer ───────────────


class TestTestSignificance:
    """test_significance testleri."""

    def test_significant(self):
        a = ABStatisticalAnalyzer()
        r = a.test_significance(
            100, 1000, 150, 1000,
        )
        assert r["tested"] is True
        assert r["significant"] is True
        assert r["lift_pct"] > 0

    def test_not_significant(self):
        a = ABStatisticalAnalyzer()
        r = a.test_significance(
            100, 1000, 102, 1000,
        )
        assert r["significant"] is False

    def test_counts(self):
        a = ABStatisticalAnalyzer()
        a.test_significance(
            100, 1000, 150, 1000,
        )
        assert a.test_count == 1
        assert a.significant_count == 1


class TestConfidenceInterval:
    """confidence_interval testleri."""

    def test_basic(self):
        a = ABStatisticalAnalyzer()
        r = a.confidence_interval(
            100, 1000,
        )
        assert r["calculated"] is True
        assert r["lower"] < r["rate"]
        assert r["upper"] > r["rate"]

    def test_high_confidence(self):
        a = ABStatisticalAnalyzer()
        r95 = a.confidence_interval(
            100, 1000, confidence=0.95,
        )
        r99 = a.confidence_interval(
            100, 1000, confidence=0.99,
        )
        assert r99["margin"] > r95["margin"]


class TestPowerAnalysis:
    """power_analysis testleri."""

    def test_basic(self):
        a = ABStatisticalAnalyzer()
        r = a.power_analysis(
            effect_size=0.05,
            sample_size=5000,
        )
        assert r["analyzed"] is True
        assert 0 < r["power"] <= 1

    def test_inadequate(self):
        a = ABStatisticalAnalyzer()
        r = a.power_analysis(
            effect_size=0.01,
            sample_size=10,
        )
        assert r["adequate"] is False


class TestBayesianAnalysis:
    """bayesian_analysis testleri."""

    def test_basic(self):
        a = ABStatisticalAnalyzer()
        r = a.bayesian_analysis(
            100, 1000, 150, 1000,
        )
        assert r["analyzed"] is True
        assert (
            r["prob_treatment_better"] > 0.5
        )


class TestSequentialTest:
    """sequential_test testleri."""

    def test_basic(self):
        a = ABStatisticalAnalyzer()
        obs = [{"z_score": 1.5}]
        r = a.sequential_test(obs)
        assert r["tested"] is True
        assert r["should_stop"] is False

    def test_stop(self):
        a = ABStatisticalAnalyzer()
        obs = [{"z_score": 5.0}]
        r = a.sequential_test(obs)
        assert r["should_stop"] is True


# ── WinnerDetector ──────────────────────


class TestDetermineWinner:
    """determine_winner testleri."""

    def test_basic(self):
        w = WinnerDetector()
        results = [
            {"name": "A", "conversion": 0.10},
            {"name": "B", "conversion": 0.15},
        ]
        r = w.determine_winner(
            "exp_1", results,
        )
        assert r["determined"] is True
        assert r["winner"] == "B"
        assert w.detection_count == 1

    def test_empty(self):
        w = WinnerDetector()
        r = w.determine_winner("exp_1", [])
        assert r["determined"] is False


class TestCheckEarlyStop:
    """check_early_stop testleri."""

    def test_stop(self):
        w = WinnerDetector()
        r = w.check_early_stop(
            "exp_1",
            current_p_value=0.001,
            threshold=0.01,
            min_samples=100,
            current_samples=500,
        )
        assert r["should_stop"] is True
        assert w.early_stop_count == 1

    def test_continue(self):
        w = WinnerDetector()
        r = w.check_early_stop(
            "exp_1",
            current_p_value=0.05,
            current_samples=50,
        )
        assert r["should_stop"] is False


class TestEvaluateMultiMetric:
    """evaluate_multi_metric testleri."""

    def test_winner(self):
        w = WinnerDetector()
        r = w.evaluate_multi_metric(
            "exp_1",
            metrics={
                "conversion": {
                    "lift": 5, "significant": True,
                },
                "revenue": {
                    "lift": 3, "significant": True,
                },
            },
        )
        assert r["overall"] == "winner"

    def test_mixed(self):
        w = WinnerDetector()
        r = w.evaluate_multi_metric(
            "exp_1",
            metrics={
                "conversion": {
                    "lift": 5, "significant": True,
                },
                "latency": {
                    "lift": -2, "significant": True,
                },
            },
        )
        assert r["overall"] == "mixed"

    def test_inconclusive(self):
        w = WinnerDetector()
        r = w.evaluate_multi_metric(
            "exp_1",
            metrics={
                "conversion": {
                    "lift": 1, "significant": False,
                },
            },
        )
        assert r["overall"] == "inconclusive"


class TestCheckGuardrails:
    """check_guardrails testleri."""

    def test_safe(self):
        w = WinnerDetector()
        r = w.check_guardrails(
            "exp_1",
            guardrail_metrics={
                "error_rate": {
                    "threshold": 0.05,
                    "current": 0.01,
                    "direction": "above",
                },
            },
        )
        assert r["safe"] is True

    def test_violation(self):
        w = WinnerDetector()
        r = w.check_guardrails(
            "exp_1",
            guardrail_metrics={
                "error_rate": {
                    "threshold": 0.05,
                    "current": 0.10,
                    "direction": "above",
                },
            },
        )
        assert r["safe"] is False
        assert r["violation_count"] == 1


class TestRecommend:
    """recommend testleri."""

    def test_rollout(self):
        w = WinnerDetector()
        r = w.recommend(
            "exp_1",
            winner="B",
            significant=True,
            guardrails_safe=True,
        )
        assert r["action"] == "rollout"

    def test_continue(self):
        w = WinnerDetector()
        r = w.recommend(
            "exp_1",
            significant=False,
        )
        assert r["action"] == "continue"

    def test_investigate(self):
        w = WinnerDetector()
        r = w.recommend(
            "exp_1",
            winner="B",
            significant=True,
            guardrails_safe=False,
        )
        assert r["action"] == "investigate"


# ── AutoRollout ─────────────────────────


class TestGradualRollout:
    """gradual_rollout testleri."""

    def test_basic(self):
        a = AutoRollout()
        r = a.gradual_rollout(
            "exp_1", "treatment",
        )
        assert r["started"] is True
        assert r["current_pct"] == 5.0
        assert a.rollout_count == 1

    def test_custom_stages(self):
        a = AutoRollout()
        r = a.gradual_rollout(
            "exp_1", "B",
            stages=[10.0, 50.0, 100.0],
        )
        assert r["current_pct"] == 10.0


class TestPromote:
    """promote testleri."""

    def test_basic(self):
        a = AutoRollout()
        a.gradual_rollout(
            "exp_1", "treatment",
        )
        r = a.promote("exp_1")
        assert r["promoted"] is True
        assert r["current_pct"] == 25.0

    def test_not_found(self):
        a = AutoRollout()
        r = a.promote("xxx")
        assert r["found"] is False


class TestTriggerRollback:
    """trigger_rollback testleri."""

    def test_basic(self):
        a = AutoRollout()
        a.gradual_rollout(
            "exp_1", "treatment",
        )
        r = a.trigger_rollback(
            "exp_1", reason="Error spike",
        )
        assert r["rolled_back"] is True
        assert a.rollback_count == 1


class TestMonitorHealth:
    """monitor_health testleri."""

    def test_healthy(self):
        a = AutoRollout()
        r = a.monitor_health(
            "exp_1",
            error_rate=0.01,
            latency_ms=200,
        )
        assert r["healthy"] is True

    def test_unhealthy(self):
        a = AutoRollout()
        r = a.monitor_health(
            "exp_1",
            error_rate=0.10,
            latency_ms=200,
        )
        assert r["healthy"] is False


class TestFullDeploy:
    """full_deploy testleri."""

    def test_basic(self):
        a = AutoRollout()
        a.gradual_rollout(
            "exp_1", "treatment",
        )
        r = a.full_deploy("exp_1")
        assert r["deployed"] is True
        assert r["percentage"] == 100.0


# ── ExperimentArchive ───────────────────


class TestArchiveExperiment:
    """archive_experiment testleri."""

    def test_basic(self):
        a = ExperimentArchive()
        r = a.archive_experiment(
            "exp_1",
            name="Button Color",
            winner="blue",
            lift_pct=5.2,
        )
        assert r["archived"] is True
        assert a.archive_count == 1


class TestAddLearning:
    """add_learning testleri."""

    def test_basic(self):
        a = ExperimentArchive()
        r = a.add_learning(
            "exp_1",
            "Blue buttons convert better",
        )
        assert r["added"] is True
        assert a.learning_count == 1


class TestArchiveSearch:
    """search testleri."""

    def test_by_name(self):
        a = ExperimentArchive()
        a.archive_experiment(
            "exp_1", name="Button Test",
        )
        r = a.search(query="Button")
        assert r["count"] == 1

    def test_by_tags(self):
        a = ExperimentArchive()
        a.archive_experiment(
            "exp_1", tags=["ui"],
        )
        r = a.search(tags=["ui"])
        assert r["count"] == 1

    def test_no_match(self):
        a = ExperimentArchive()
        r = a.search(query="xyz")
        assert r["count"] == 0


class TestReplicate:
    """replicate testleri."""

    def test_basic(self):
        a = ExperimentArchive()
        a.archive_experiment(
            "exp_1", name="Test",
        )
        r = a.replicate("exp_1")
        assert r["replicated"] is True

    def test_not_found(self):
        a = ExperimentArchive()
        r = a.replicate("xxx")
        assert r["found"] is False


class TestExtractKnowledge:
    """extract_knowledge testleri."""

    def test_basic(self):
        a = ExperimentArchive()
        a.archive_experiment(
            "exp_1", winner="B", lift_pct=5.0,
        )
        a.add_learning("exp_1", "insight")
        r = a.extract_knowledge()
        assert r["extracted"] is True
        assert r["learning_count"] == 1
        assert r["avg_lift_pct"] == 5.0


# ── MultivariateTester ──────────────────


class TestDefineVariables:
    """define_variables testleri."""

    def test_basic(self):
        m = MultivariateTester()
        r = m.define_variables(
            "mvt_1",
            variables={
                "color": ["red", "blue"],
                "size": ["small", "large"],
            },
        )
        assert r["defined"] is True
        assert r["total_combinations"] == 4
        assert m.test_count == 1


class TestAnalyzeInteractions:
    """analyze_interactions testleri."""

    def test_basic(self):
        m = MultivariateTester()
        m.define_variables(
            "mvt_1",
            variables={
                "color": ["red", "blue"],
                "size": ["small", "large"],
            },
        )
        r = m.analyze_interactions("mvt_1")
        assert r["analyzed"] is True
        assert r["interaction_count"] >= 1

    def test_not_found(self):
        m = MultivariateTester()
        r = m.analyze_interactions("xxx")
        assert r["found"] is False


class TestFactorialDesign:
    """factorial_design testleri."""

    def test_full(self):
        m = MultivariateTester()
        m.define_variables(
            "mvt_1",
            variables={
                "color": ["red", "blue"],
                "size": ["S", "L"],
            },
        )
        r = m.factorial_design("mvt_1")
        assert r["designed"] is True
        assert r["design_type"] == "full"
        assert r["run_count"] == 4

    def test_fractional(self):
        m = MultivariateTester()
        m.define_variables(
            "mvt_1",
            variables={
                "a": ["1", "2", "3"],
                "b": ["x", "y", "z"],
                "c": ["p", "q", "r"],
            },
        )
        r = m.factorial_design(
            "mvt_1", fractional=True,
        )
        assert r["design_type"] == "fractional"
        assert r["run_count"] < 27


class TestOptimize:
    """optimize testleri."""

    def test_basic(self):
        m = MultivariateTester()
        m.define_variables("mvt_1")
        results = [
            {"combo": "A", "conversion": 0.10},
            {"combo": "B", "conversion": 0.15},
        ]
        r = m.optimize(
            "mvt_1", results,
        )
        assert r["optimized"] is True
        assert r["best_value"] == 0.15
        assert m.optimization_count == 1

    def test_no_results(self):
        m = MultivariateTester()
        m.define_variables("mvt_1")
        r = m.optimize("mvt_1")
        assert r["optimized"] is False


class TestManageComplexity:
    """manage_complexity testleri."""

    def test_feasible(self):
        m = MultivariateTester()
        m.define_variables(
            "mvt_1",
            variables={
                "a": ["1", "2"],
                "b": ["x", "y"],
            },
        )
        r = m.manage_complexity("mvt_1")
        assert r["feasible"] is True

    def test_too_complex(self):
        m = MultivariateTester()
        m.define_variables(
            "mvt_1",
            variables={
                "a": ["1", "2", "3", "4", "5"],
                "b": ["1", "2", "3", "4", "5"],
            },
        )
        r = m.manage_complexity(
            "mvt_1", max_combinations=16,
        )
        assert r["feasible"] is False
        assert r["recommendation"] == "fractional"


# ── ABTestingOrchestrator ───────────────


class TestRunExperiment:
    """run_experiment testleri."""

    def test_basic(self):
        o = ABTestingOrchestrator()
        r = o.run_experiment(
            "exp_1",
            name="Button Test",
            control_conversions=100,
            control_total=1000,
            treatment_conversions=150,
            treatment_total=1000,
        )
        assert r["pipeline_complete"] is True
        assert r["significant"] is True
        assert r["winner"] in [
            "control", "treatment",
        ]
        assert o.pipeline_count == 1

    def test_not_significant(self):
        o = ABTestingOrchestrator()
        r = o.run_experiment(
            "exp_2",
            control_conversions=100,
            control_total=1000,
            treatment_conversions=102,
            treatment_total=1000,
        )
        assert r["significant"] is False


class TestQuickTest:
    """quick_test testleri."""

    def test_basic(self):
        o = ABTestingOrchestrator()
        r = o.quick_test(
            control_rate=0.10,
            treatment_rate=0.15,
            sample_size=1000,
        )
        assert r["tested"] is True
        assert r["significant"] is True


class TestGetAnalyticsOrch:
    """get_analytics testleri."""

    def test_basic(self):
        o = ABTestingOrchestrator()
        o.run_experiment(
            "exp_1",
            control_conversions=100,
            control_total=1000,
            treatment_conversions=150,
            treatment_total=1000,
        )
        r = o.get_analytics()
        assert r["pipelines_run"] == 1
        assert r["tests_performed"] >= 1
        assert r["experiments_archived"] >= 1


# ── Models ──────────────────────────────


class TestModels:
    """Model testleri."""

    def test_experiment_status(self):
        assert ExperimentStatus.DRAFT == "draft"
        assert ExperimentStatus.RUNNING == "running"

    def test_variant_type(self):
        assert VariantType.CONTROL == "control"
        assert VariantType.TREATMENT == "treatment"

    def test_significance_level(self):
        assert SignificanceLevel.P95 == "0.05"
        assert SignificanceLevel.P99 == "0.01"

    def test_rollout_stage(self):
        assert RolloutStage.CANARY == "canary"
        assert RolloutStage.FULL == "full"

    def test_metric_type(self):
        assert MetricType.CONVERSION == "conversion"
        assert MetricType.REVENUE == "revenue"

    def test_design_type(self):
        assert DesignType.AB == "ab"
        assert DesignType.MULTIVARIATE == "multivariate"

    def test_experiment_record(self):
        r = ExperimentRecord(name="Test")
        assert r.name == "Test"
        assert r.experiment_id

    def test_variant_record(self):
        r = VariantRecord(name="A")
        assert r.name == "A"
        assert r.variant_id

    def test_result_record(self):
        r = ResultRecord(winner="B")
        assert r.winner == "B"
        assert r.result_id

    def test_rollout_record(self):
        r = RolloutRecord(stage="canary")
        assert r.stage == "canary"
        assert r.rollout_id
