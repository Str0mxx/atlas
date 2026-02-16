"""ATLAS Feedback Loop Optimizer testleri."""

from app.core.feedbackopt.auto_tuner import (
    AutoTuner,
)
from app.core.feedbackopt.continuous_improver import (
    ContinuousImprover,
)
from app.core.feedbackopt.experiment_designer import (
    FeedbackExperimentDesigner,
)
from app.core.feedbackopt.feedbackopt_orchestrator import (
    FeedbackOptOrchestrator,
)
from app.core.feedbackopt.impact_measurer import (
    ImpactMeasurer,
)
from app.core.feedbackopt.learning_synthesizer import (
    LearningSynthesizer,
)
from app.core.feedbackopt.outcome_correlator import (
    OutcomeCorrelator,
)
from app.core.feedbackopt.strategy_ranker import (
    StrategyRanker,
)
from app.core.feedbackopt.user_satisfaction_tracker import (
    UserSatisfactionTracker,
)


# ── UserSatisfactionTracker ──


class TestSatisfactionInit:
    def test_init(self):
        t = UserSatisfactionTracker()
        assert t.feedback_count == 0
        assert t.nps_count == 0


class TestScoreSatisfaction:
    def test_delighted(self):
        t = UserSatisfactionTracker()
        r = t.score_satisfaction(
            "u1", 95.0,
        )
        assert r["recorded"] is True
        assert r["level"] == "delighted"

    def test_frustrated(self):
        t = UserSatisfactionTracker()
        r = t.score_satisfaction(
            "u1", 10.0,
        )
        assert r["level"] == "frustrated"


class TestTrackNPS:
    def test_promoter(self):
        t = UserSatisfactionTracker()
        r = t.track_nps("u1", 9)
        assert r["tracked"] is True
        assert r["category"] == "promoter"
        assert r["current_nps"] == 100.0

    def test_detractor(self):
        t = UserSatisfactionTracker()
        r = t.track_nps("u1", 3)
        assert r["category"] == "detractor"
        assert r["current_nps"] == -100.0


class TestAnalyzeSentiment:
    def test_positive(self):
        t = UserSatisfactionTracker()
        r = t.analyze_sentiment(
            "great excellent amazing",
        )
        assert r["analyzed"] is True
        assert r["sentiment"] == "positive"

    def test_negative(self):
        t = UserSatisfactionTracker()
        r = t.analyze_sentiment(
            "terrible awful broken",
        )
        assert r["sentiment"] == "negative"

    def test_neutral(self):
        t = UserSatisfactionTracker()
        r = t.analyze_sentiment(
            "the system works",
        )
        assert r["sentiment"] == "neutral"


class TestCollectFeedback:
    def test_basic(self):
        t = UserSatisfactionTracker()
        r = t.collect_feedback(
            "u1",
            feedback_type="rating",
            value=4,
        )
        assert r["collected"] is True
        assert t.feedback_count == 1


class TestDetectTrend:
    def test_improving(self):
        t = UserSatisfactionTracker()
        for s in [50, 55, 60, 70, 80, 90]:
            t.score_satisfaction("u1", s)
        r = t.detect_trend()
        assert r["detected"] is True
        assert r["trend"] == "improving"

    def test_insufficient(self):
        t = UserSatisfactionTracker()
        t.score_satisfaction("u1", 50)
        r = t.detect_trend()
        assert r["detected"] is False


# ── OutcomeCorrelator ──


class TestCorrelatorInit:
    def test_init(self):
        c = OutcomeCorrelator()
        assert c.correlation_count == 0
        assert c.pattern_count == 0


class TestLinkActionOutcome:
    def test_basic(self):
        c = OutcomeCorrelator()
        r = c.link_action_outcome(
            "a1", "email", 85.0,
        )
        assert r["linked"] is True


class TestAnalyzeCorrelation:
    def test_strong(self):
        c = OutcomeCorrelator()
        for v in [80, 82, 81, 80, 83]:
            c.link_action_outcome(
                "a", "email", v,
            )
        r = c.analyze_correlation("email")
        assert r["analyzed"] is True
        assert r["strength"] in (
            "strong", "moderate",
        )

    def test_insufficient(self):
        c = OutcomeCorrelator()
        c.link_action_outcome(
            "a1", "email", 80,
        )
        r = c.analyze_correlation("email")
        assert r["analyzed"] is False


class TestInferCausality:
    def test_inferred(self):
        c = OutcomeCorrelator()
        for v in [80, 85, 90]:
            c.link_action_outcome(
                "a", "promo", v,
            )
        r = c.infer_causality(
            "promo", baseline=50.0,
        )
        assert r["inferred"] is True
        assert r["lift"] > 0

    def test_insufficient(self):
        c = OutcomeCorrelator()
        c.link_action_outcome(
            "a1", "x", 50,
        )
        r = c.infer_causality("x")
        assert r["inferred"] is False


class TestDetectPattern:
    def test_found(self):
        c = OutcomeCorrelator()
        for v in [80, 85, 90]:
            c.link_action_outcome(
                "a", "email", v,
            )
        r = c.detect_pattern(
            min_occurrences=3,
        )
        assert r["detected"] is True
        assert r["pattern_count"] >= 1

    def test_not_found(self):
        c = OutcomeCorrelator()
        r = c.detect_pattern()
        assert r["detected"] is False


class TestAttributeOutcome:
    def test_basic(self):
        c = OutcomeCorrelator()
        c.link_action_outcome(
            "a1", "email", 80,
        )
        c.link_action_outcome(
            "a2", "sms", 60,
        )
        r = c.attribute_outcome(
            100.0,
            action_types=["email", "sms"],
        )
        assert r["attributed"] is True
        assert r["attribution_count"] == 2


# ── StrategyRanker ──


class TestRankerInit:
    def test_init(self):
        r = StrategyRanker()
        assert r.strategy_count == 0
        assert r.ranking_count == 0


class TestScoreStrategy:
    def test_basic(self):
        r = StrategyRanker()
        res = r.score_strategy(
            "s1",
            success_rate=90,
            efficiency=85,
            cost=20,
            user_satisfaction=88,
        )
        assert res["scored"] is True
        assert res["total_score"] > 0


class TestRankPerformance:
    def test_ranked(self):
        r = StrategyRanker()
        r.score_strategy(
            "s1", success_rate=90,
        )
        r.score_strategy(
            "s2", success_rate=70,
        )
        res = r.rank_performance()
        assert res["ranked"] is True
        assert res["total_strategies"] == 2

    def test_empty(self):
        r = StrategyRanker()
        res = r.rank_performance()
        assert res["ranked"] is False


class TestMeasureEffectiveness:
    def test_good(self):
        r = StrategyRanker()
        r.score_strategy(
            "s1",
            success_rate=90,
            efficiency=85,
            user_satisfaction=88,
        )
        res = r.measure_effectiveness(
            "s1", target=60.0,
        )
        assert res["measured"] is True
        assert res["level"] in (
            "excellent", "good",
        )

    def test_not_found(self):
        r = StrategyRanker()
        res = r.measure_effectiveness("x")
        assert res["measured"] is False


class TestCompareStrategies:
    def test_compared(self):
        r = StrategyRanker()
        r.score_strategy(
            "s1", success_rate=90,
        )
        r.score_strategy(
            "s2", success_rate=60,
        )
        res = r.compare_strategies(
            "s1", "s2",
        )
        assert res["compared"] is True
        assert res["winner"] == "s1"

    def test_not_found(self):
        r = StrategyRanker()
        res = r.compare_strategies(
            "x", "y",
        )
        assert res["compared"] is False


class TestExtractBestPractices:
    def test_extracted(self):
        r = StrategyRanker()
        r.score_strategy(
            "s1",
            success_rate=90,
            efficiency=85,
            user_satisfaction=88,
        )
        res = r.extract_best_practices(
            min_score=50.0,
        )
        assert res["extracted"] is True

    def test_none(self):
        r = StrategyRanker()
        res = r.extract_best_practices()
        assert res["extracted"] is False


# ── AutoTuner ──


class TestTunerInit:
    def test_init(self):
        t = AutoTuner()
        assert t.optimization_count == 0
        assert t.rollback_count == 0


class TestRegisterParameter:
    def test_basic(self):
        t = AutoTuner()
        r = t.register_parameter(
            "threshold", 50.0,
        )
        assert r["registered"] is True


class TestOptimizeParameter:
    def test_increase(self):
        t = AutoTuner()
        t.register_parameter(
            "threshold", 50.0, step=5.0,
        )
        r = t.optimize_parameter(
            "threshold",
            target_metric=80.0,
            current_metric=60.0,
        )
        assert r["optimized"] is True
        assert r["action"] == "increase"
        assert r["new_value"] == 55.0

    def test_not_found(self):
        t = AutoTuner()
        r = t.optimize_parameter("x")
        assert r["optimized"] is False


class TestAdjustThreshold:
    def test_lowered(self):
        t = AutoTuner()
        t.register_parameter(
            "t1", 50.0, step=5.0,
        )
        r = t.adjust_threshold(
            "t1", performance=60.0,
            target=80.0,
        )
        assert r["adjusted"] is True
        assert r["direction"] == "lowered"

    def test_not_found(self):
        t = AutoTuner()
        r = t.adjust_threshold("x", 50.0)
        assert r["adjusted"] is False


class TestTuneConfig:
    def test_with_changes(self):
        t = AutoTuner()
        t.register_parameter(
            "speed", 50.0, step=5.0,
        )
        r = t.tune_config(
            "main",
            metrics={"speed": 90.0},
        )
        assert r["tuned"] is True
        assert r["changes"] == 1


class TestApplyGradualChange:
    def test_basic(self):
        t = AutoTuner()
        t.register_parameter(
            "rate", 10.0,
            max_value=100.0,
        )
        r = t.apply_gradual_change(
            "rate",
            target_value=60.0,
            steps=5,
        )
        assert r["applied"] is True
        assert r["remaining_steps"] == 4

    def test_not_found(self):
        t = AutoTuner()
        r = t.apply_gradual_change("x", 50)
        assert r["applied"] is False


class TestRollbackOnRegression:
    def test_rollback(self):
        t = AutoTuner()
        t.register_parameter(
            "t1", 50.0, step=5.0,
        )
        t.optimize_parameter(
            "t1",
            target_metric=80.0,
            current_metric=60.0,
        )
        r = t.rollback_on_regression(
            "t1",
            current_metric=40.0,
            previous_metric=60.0,
        )
        assert r["rolled_back"] is True

    def test_no_regression(self):
        t = AutoTuner()
        t.register_parameter("t1", 50.0)
        r = t.rollback_on_regression(
            "t1",
            current_metric=70.0,
            previous_metric=60.0,
        )
        assert r["rolled_back"] is False


# ── FeedbackExperimentDesigner ──


class TestExperimentInit:
    def test_init(self):
        e = FeedbackExperimentDesigner()
        assert e.experiment_count == 0
        assert e.hypothesis_count == 0


class TestGenerateHypothesis:
    def test_basic(self):
        e = FeedbackExperimentDesigner()
        r = e.generate_hypothesis(
            "Users prefer fast responses",
            variable="response_time",
        )
        assert r["generated"] is True
        assert e.hypothesis_count == 1


class TestDesignTest:
    def test_basic(self):
        e = FeedbackExperimentDesigner()
        h = e.generate_hypothesis("test")
        r = e.design_test(
            h["hypothesis_id"],
            test_type="ab_test",
        )
        assert r["designed"] is True
        assert e.experiment_count == 1


class TestIsolateVariable:
    def test_high_quality(self):
        e = FeedbackExperimentDesigner()
        e.generate_hypothesis("test")
        exp = e.design_test("hyp_1")
        r = e.isolate_variable(
            exp["experiment_id"],
            target_variable="speed",
            controlled=["cpu", "mem", "net"],
        )
        assert r["isolated"] is True
        assert r["quality"] == "high"

    def test_not_found(self):
        e = FeedbackExperimentDesigner()
        r = e.isolate_variable("x", "y")
        assert r["isolated"] is False


class TestCalculateSampleSize:
    def test_basic(self):
        e = FeedbackExperimentDesigner()
        r = e.calculate_sample_size(
            effect_size=0.5,
            confidence=0.95,
        )
        assert r["calculated"] is True
        assert r["sample_size"] >= 10

    def test_zero_effect(self):
        e = FeedbackExperimentDesigner()
        r = e.calculate_sample_size(
            effect_size=0,
        )
        assert r["calculated"] is False


class TestPlanDuration:
    def test_basic(self):
        e = FeedbackExperimentDesigner()
        e.generate_hypothesis("test")
        exp = e.design_test("hyp_1")
        r = e.plan_duration(
            exp["experiment_id"],
            daily_data_rate=100.0,
            required_samples=1000,
        )
        assert r["planned"] is True
        assert r["total_days"] > 0

    def test_not_found(self):
        e = FeedbackExperimentDesigner()
        r = e.plan_duration("x")
        assert r["planned"] is False


# ── ImpactMeasurer ──


class TestImpactInit:
    def test_init(self):
        m = ImpactMeasurer()
        assert m.measurement_count == 0
        assert m.significant_count == 0


class TestSetBaseline:
    def test_basic(self):
        m = ImpactMeasurer()
        r = m.set_baseline("conv", 5.0)
        assert r["set"] is True


class TestBeforeAfter:
    def test_improved(self):
        m = ImpactMeasurer()
        r = m.analyze_before_after(
            "conv", before=5.0, after=8.0,
        )
        assert r["analyzed"] is True
        assert r["direction"] == "improved"
        assert r["change"] == 3.0

    def test_declined(self):
        m = ImpactMeasurer()
        r = m.analyze_before_after(
            "conv", before=8.0, after=5.0,
        )
        assert r["direction"] == "declined"


class TestCalculateLift:
    def test_positive(self):
        m = ImpactMeasurer()
        r = m.calculate_lift(
            control=50.0, treatment=60.0,
        )
        assert r["calculated"] is True
        assert r["lift_pct"] == 20.0

    def test_zero_control(self):
        m = ImpactMeasurer()
        r = m.calculate_lift(0, 10)
        assert r["calculated"] is False


class TestStatisticalSignificance:
    def test_significant(self):
        m = ImpactMeasurer()
        r = m.check_statistical_significance(
            sample_a=[10, 12, 11, 13, 14,
                       15, 16, 12, 13, 14],
            sample_b=[20, 22, 21, 23, 24,
                       25, 26, 22, 23, 24],
        )
        assert r["significant"] is True

    def test_insufficient(self):
        m = ImpactMeasurer()
        r = m.check_statistical_significance(
            sample_a=[10],
        )
        assert r["significant"] is False


class TestMeasureROI:
    def test_profitable(self):
        m = ImpactMeasurer()
        r = m.measure_roi(
            cost=100.0, benefit=350.0,
        )
        assert r["calculated"] is True
        assert r["profitable"] is True
        assert r["roi_pct"] == 250.0

    def test_zero_cost(self):
        m = ImpactMeasurer()
        r = m.measure_roi(0, 100)
        assert r["calculated"] is False


class TestModelAttribution:
    def test_modeled(self):
        m = ImpactMeasurer()
        r = m.model_attribution(
            100.0,
            factors={
                "email": 3.0,
                "ads": 7.0,
            },
        )
        assert r["modeled"] is True
        assert r["factor_count"] == 2

    def test_empty(self):
        m = ImpactMeasurer()
        r = m.model_attribution(100.0)
        assert r["modeled"] is False


# ── ContinuousImprover ──


class TestImproverInit:
    def test_init(self):
        c = ContinuousImprover()
        assert c.improvement_count == 0
        assert c.verified_count == 0


class TestIdentifyImprovement:
    def test_basic(self):
        c = ContinuousImprover()
        r = c.identify_improvement(
            "response_time",
            current_value=500.0,
            target_value=200.0,
        )
        assert r["identified"] is True
        assert r["gap"] == -300.0


class TestPrioritize:
    def test_critical(self):
        c = ContinuousImprover()
        imp = c.identify_improvement(
            "speed",
        )
        r = c.prioritize(
            imp["improvement_id"],
            impact=90.0,
            effort=10.0,
            urgency=90.0,
        )
        assert r["prioritized"] is True
        assert r["level"] == "critical"

    def test_not_found(self):
        c = ContinuousImprover()
        r = c.prioritize("x")
        assert r["prioritized"] is False


class TestImplementImprovement:
    def test_basic(self):
        c = ContinuousImprover()
        imp = c.identify_improvement(
            "speed",
        )
        r = c.implement(
            imp["improvement_id"],
            action="optimize_query",
        )
        assert r["implemented"] is True

    def test_not_found(self):
        c = ContinuousImprover()
        r = c.implement("x")
        assert r["implemented"] is False


class TestVerifyImprovement:
    def test_success(self):
        c = ContinuousImprover()
        imp = c.identify_improvement(
            "accuracy",
            current_value=60.0,
            target_value=90.0,
        )
        r = c.verify(
            imp["improvement_id"],
            new_value=92.0,
        )
        assert r["verified"] is True
        assert r["success"] is True

    def test_not_found(self):
        c = ContinuousImprover()
        r = c.verify("x")
        assert r["verified"] is False


class TestDocumentImprovement:
    def test_basic(self):
        c = ContinuousImprover()
        imp = c.identify_improvement(
            "speed",
        )
        r = c.document(
            imp["improvement_id"],
            summary="Optimized query",
            lessons=["Index helped"],
        )
        assert r["documented"] is True
        assert r["lesson_count"] == 1

    def test_not_found(self):
        c = ContinuousImprover()
        r = c.document("x")
        assert r["documented"] is False


# ── LearningSynthesizer ──


class TestSynthesizerInit:
    def test_init(self):
        s = LearningSynthesizer()
        assert s.insight_count == 0
        assert s.knowledge_count == 0


class TestExtractInsight:
    def test_basic(self):
        s = LearningSynthesizer()
        r = s.extract_insight(
            "feedback",
            data={"score": 85},
        )
        assert r["extracted"] is True
        assert r["type"] == "performance"


class TestCodifyKnowledge:
    def test_basic(self):
        s = LearningSynthesizer()
        r = s.codify_knowledge(
            "response_time",
            findings=[
                "Cache helps",
                "Index needed",
            ],
        )
        assert r["codified"] is True
        assert r["finding_count"] == 2


class TestUpdateBestPractice:
    def test_create(self):
        s = LearningSynthesizer()
        r = s.update_best_practice(
            area="caching",
            recommendation="Use Redis",
            evidence_strength=0.9,
        )
        assert r["created"] is True

    def test_update(self):
        s = LearningSynthesizer()
        s.update_best_practice(
            practice_id="bp_1",
            area="caching",
        )
        r = s.update_best_practice(
            practice_id="bp_1",
            area="caching_v2",
        )
        assert r["updated"] is True


class TestCrossSystemLearn:
    def test_transferable(self):
        s = LearningSynthesizer()
        r = s.cross_system_learn(
            "marketing", "sales",
            learning="Email timing matters",
            applicability=0.8,
        )
        assert r["learned"] is True
        assert r["transferable"] is True

    def test_not_transferable(self):
        s = LearningSynthesizer()
        r = s.cross_system_learn(
            "marketing", "server",
            applicability=0.3,
        )
        assert r["transferable"] is False


class TestIntegrateMemory:
    def test_integrated(self):
        s = LearningSynthesizer()
        ins = s.extract_insight("test")
        r = s.integrate_memory(
            ins["insight_id"],
            importance=0.9,
        )
        assert r["integrated"] is True
        assert r["priority"] == "high"

    def test_not_found(self):
        s = LearningSynthesizer()
        r = s.integrate_memory("x")
        assert r["integrated"] is False


# ── FeedbackOptOrchestrator ──


class TestFeedbackOrchInit:
    def test_init(self):
        o = FeedbackOptOrchestrator()
        assert o.pipeline_count == 0
        assert o.optimization_count == 0


class TestRunOptPipeline:
    def test_basic(self):
        o = FeedbackOptOrchestrator()
        r = o.run_optimization_pipeline(
            "u1", 85.0,
            action_type="email",
            strategy_id="s1",
        )
        assert r["pipeline_complete"] is True
        assert r["satisfaction_level"] in (
            "delighted", "satisfied",
        )

    def test_low_score(self):
        o = FeedbackOptOrchestrator()
        r = o.run_optimization_pipeline(
            "u1", 20.0,
        )
        assert r["satisfaction_level"] == (
            "frustrated"
        )


class TestCollectCorrelateRank:
    def test_basic(self):
        o = FeedbackOptOrchestrator()
        feedbacks = [
            {"user_id": "u1",
             "score": 80.0,
             "action_type": "email"},
            {"user_id": "u2",
             "score": 90.0,
             "action_type": "sms"},
        ]
        r = o.collect_correlate_rank(
            feedbacks,
        )
        assert r["complete"] is True
        assert r["feedbacks_processed"] == 2


class TestFuelSelfEvolution:
    def test_basic(self):
        o = FeedbackOptOrchestrator()
        r = o.fuel_self_evolution()
        assert r["evolution_fuel"] is True


class TestFeedbackOptAnalytics:
    def test_basic(self):
        o = FeedbackOptOrchestrator()
        o.run_optimization_pipeline(
            "u1", 80.0,
        )
        r = o.get_analytics()
        assert r["pipelines_run"] == 1
        assert r["feedbacks"] >= 1

    def test_empty(self):
        o = FeedbackOptOrchestrator()
        r = o.get_analytics()
        assert r["pipelines_run"] == 0
        assert r["feedbacks"] == 0


# ── Config ──


class TestFeedbackOptConfig:
    def test_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.feedbackopt_enabled is True
        assert s.auto_tune is True
        assert (
            s.experiment_auto_start is True
        )
        assert (
            s.improvement_threshold == 0.1
        )
        assert (
            s.learning_integration is True
        )


# ── Imports ──


class TestFeedbackOptImports:
    def test_all_imports(self):
        from app.core.feedbackopt import (
            AutoTuner,
            ContinuousImprover,
            FeedbackExperimentDesigner,
            FeedbackOptOrchestrator,
            ImpactMeasurer,
            LearningSynthesizer,
            OutcomeCorrelator,
            StrategyRanker,
            UserSatisfactionTracker,
        )
        assert UserSatisfactionTracker
        assert OutcomeCorrelator
        assert StrategyRanker
        assert AutoTuner
        assert FeedbackExperimentDesigner
        assert ImpactMeasurer
        assert ContinuousImprover
        assert LearningSynthesizer
        assert FeedbackOptOrchestrator
