"""Adaptive Learning Engine sistemi testleri."""

import pytest

from app.models.adaptive import (
    AdaptiveSnapshot,
    ExperienceRecord,
    ExperienceType,
    FeedbackType,
    KnowledgeRule,
    OutcomeType,
    PatternRecord,
    PatternType,
    SkillLevel,
    StrategyRecord,
    StrategyStatus,
)
from app.core.adaptive.experience_collector import ExperienceCollector
from app.core.adaptive.pattern_miner import PatternMiner
from app.core.adaptive.strategy_evolver import StrategyEvolver
from app.core.adaptive.knowledge_distiller import KnowledgeDistiller
from app.core.adaptive.skill_optimizer import SkillOptimizer
from app.core.adaptive.feedback_processor import FeedbackProcessor
from app.core.adaptive.transfer_learner import TransferLearner
from app.core.adaptive.curriculum_manager import CurriculumManager
from app.core.adaptive.adaptive_engine import AdaptiveEngine


# ── Model Testleri ──────────────────────────────────────────


class TestModels:
    """Veri modeli testleri."""

    def test_experience_type_values(self):
        assert ExperienceType.INTERACTION == "interaction"
        assert ExperienceType.TASK == "task"
        assert ExperienceType.FEEDBACK == "feedback"

    def test_outcome_type_values(self):
        assert OutcomeType.SUCCESS == "success"
        assert OutcomeType.FAILURE == "failure"
        assert OutcomeType.PARTIAL == "partial"

    def test_pattern_type_values(self):
        assert PatternType.SUCCESS == "success"
        assert PatternType.FAILURE == "failure"
        assert PatternType.CORRELATION == "correlation"
        assert PatternType.TREND == "trend"
        assert PatternType.CLUSTER == "cluster"

    def test_strategy_status_values(self):
        assert StrategyStatus.ACTIVE == "active"
        assert StrategyStatus.TESTING == "testing"
        assert StrategyStatus.RETIRED == "retired"

    def test_feedback_type_values(self):
        assert FeedbackType.EXPLICIT == "explicit"
        assert FeedbackType.IMPLICIT == "implicit"
        assert FeedbackType.CORRECTION == "correction"

    def test_skill_level_values(self):
        assert SkillLevel.NOVICE == "novice"
        assert SkillLevel.EXPERT == "expert"

    def test_experience_record_defaults(self):
        r = ExperienceRecord()
        assert len(r.experience_id) == 8
        assert r.outcome == OutcomeType.UNKNOWN
        assert r.reward == 0.0

    def test_pattern_record_defaults(self):
        r = PatternRecord()
        assert len(r.pattern_id) == 8
        assert r.confidence == 0.0

    def test_strategy_record_defaults(self):
        r = StrategyRecord()
        assert r.status == StrategyStatus.CANDIDATE
        assert r.fitness == 0.0

    def test_knowledge_rule_defaults(self):
        r = KnowledgeRule()
        assert r.valid is True
        assert r.usage_count == 0

    def test_adaptive_snapshot_defaults(self):
        s = AdaptiveSnapshot()
        assert s.total_experiences == 0
        assert s.avg_learning_rate == 0.0


# ── ExperienceCollector Testleri ────────────────────────────


class TestExperienceCollector:
    """Deneyim toplayici testleri."""

    @pytest.fixture()
    def ec(self):
        return ExperienceCollector()

    def test_init(self, ec):
        assert ec.total_count == 0
        assert ec.success_count == 0

    def test_record(self, ec):
        exp = ec.record("test_action")
        assert exp.action == "test_action"
        assert ec.total_count == 1

    def test_record_success(self, ec):
        exp = ec.record_success("deploy", reward=1.0)
        assert exp.outcome == OutcomeType.SUCCESS
        assert ec.success_count == 1

    def test_record_failure(self, ec):
        exp = ec.record_failure("build", reward=-1.0)
        assert exp.outcome == OutcomeType.FAILURE
        assert ec.failure_count == 1

    def test_record_with_tags(self, ec):
        ec.record("action", tags=["deploy", "prod"])
        assert ec.tag_count == 2

    def test_record_with_context(self, ec):
        exp = ec.record(
            "action",
            context={"env": "prod"},
        )
        assert exp.context["env"] == "prod"

    def test_push_pop_context(self, ec):
        ec.push_context({"env": "prod"})
        exp = ec.record("action")
        assert exp.context["env"] == "prod"
        ctx = ec.pop_context()
        assert ctx["env"] == "prod"

    def test_pop_empty_context(self, ec):
        assert ec.pop_context() is None

    def test_get_by_outcome(self, ec):
        ec.record_success("a")
        ec.record_failure("b")
        results = ec.get_by_outcome(OutcomeType.SUCCESS)
        assert len(results) == 1

    def test_get_by_tag(self, ec):
        ec.record("a", tags=["deploy"])
        ec.record("b", tags=["test"])
        results = ec.get_by_tag("deploy")
        assert len(results) == 1

    def test_get_success_rate(self, ec):
        ec.record_success("a")
        ec.record_success("b")
        ec.record_failure("c")
        rate = ec.get_success_rate()
        assert abs(rate - 2 / 3) < 0.01

    def test_get_success_rate_empty(self, ec):
        assert ec.get_success_rate() == 0.0

    def test_get_success_rate_by_tag(self, ec):
        ec.record_success("a", tags=["deploy"])
        ec.record_failure("b", tags=["deploy"])
        rate = ec.get_success_rate(tag="deploy")
        assert rate == 0.5

    def test_get_recent(self, ec):
        for i in range(5):
            ec.record(f"action_{i}")
        recent = ec.get_recent(limit=3)
        assert len(recent) == 3

    def test_context_stacking(self, ec):
        ec.push_context({"a": 1})
        ec.push_context({"b": 2})
        exp = ec.record("action")
        assert exp.context["a"] == 1
        assert exp.context["b"] == 2


# ── PatternMiner Testleri ───────────────────────────────────


class TestPatternMiner:
    """Oruntu madencisi testleri."""

    @pytest.fixture()
    def pm(self):
        return PatternMiner(min_support=2, min_confidence=0.5)

    def _make_experiences(self, actions_outcomes):
        exps = []
        for action, outcome, reward, tags in actions_outcomes:
            exps.append(ExperienceRecord(
                action=action,
                outcome=outcome,
                reward=reward,
                tags=tags,
            ))
        return exps

    def test_init(self, pm):
        assert pm.pattern_count == 0

    def test_mine_success_patterns(self, pm):
        exps = self._make_experiences([
            ("deploy", OutcomeType.SUCCESS, 1.0, []),
            ("deploy", OutcomeType.SUCCESS, 0.9, []),
            ("test", OutcomeType.FAILURE, -1.0, []),
        ])
        patterns = pm.mine_success_patterns(exps)
        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.SUCCESS

    def test_mine_failure_patterns(self, pm):
        exps = self._make_experiences([
            ("build", OutcomeType.FAILURE, -1.0, []),
            ("build", OutcomeType.FAILURE, -0.5, []),
            ("deploy", OutcomeType.SUCCESS, 1.0, []),
        ])
        patterns = pm.mine_failure_patterns(exps)
        assert len(patterns) == 1

    def test_discover_correlations(self, pm):
        exps = self._make_experiences([
            ("a", OutcomeType.SUCCESS, 1.0, ["ci"]),
            ("b", OutcomeType.SUCCESS, 1.0, ["ci"]),
            ("c", OutcomeType.FAILURE, -1.0, ["manual"]),
            ("d", OutcomeType.FAILURE, -1.0, ["manual"]),
        ])
        patterns = pm.discover_correlations(exps)
        assert len(patterns) >= 1

    def test_identify_trends_improving(self, pm):
        exps = []
        for i in range(20):
            reward = 0.3 if i < 10 else 0.8
            exps.append(ExperienceRecord(
                action="task", reward=reward,
            ))
        trends = pm.identify_trends(exps, window=10)
        assert len(trends) >= 1
        assert trends[0].features["direction"] == "improving"

    def test_identify_trends_declining(self, pm):
        exps = []
        for i in range(20):
            reward = 0.8 if i < 10 else 0.3
            exps.append(ExperienceRecord(
                action="task", reward=reward,
            ))
        trends = pm.identify_trends(exps, window=10)
        assert len(trends) >= 1
        assert trends[0].features["direction"] == "declining"

    def test_identify_trends_insufficient(self, pm):
        exps = [ExperienceRecord(action="a", reward=0.5)]
        trends = pm.identify_trends(exps, window=10)
        assert len(trends) == 0

    def test_cluster_experiences(self, pm):
        exps = self._make_experiences([
            ("deploy", OutcomeType.SUCCESS, 1.0, []),
            ("deploy", OutcomeType.SUCCESS, 0.8, []),
            ("deploy", OutcomeType.FAILURE, -1.0, []),
        ])
        clusters = pm.cluster_experiences(exps)
        assert len(clusters) == 1
        assert clusters[0].features["action"] == "deploy"

    def test_get_patterns_filtered(self, pm):
        exps = self._make_experiences([
            ("a", OutcomeType.SUCCESS, 1.0, []),
            ("a", OutcomeType.SUCCESS, 1.0, []),
        ])
        pm.mine_success_patterns(exps)
        results = pm.get_patterns(PatternType.SUCCESS)
        assert len(results) >= 1

    def test_empty_experiences(self, pm):
        assert pm.mine_success_patterns([]) == []
        assert pm.mine_failure_patterns([]) == []
        assert pm.cluster_experiences([]) == []


# ── StrategyEvolver Testleri ────────────────────────────────


class TestStrategyEvolver:
    """Strateji evrimcisi testleri."""

    @pytest.fixture()
    def se(self):
        return StrategyEvolver(mutation_rate=0.2, crossover_rate=0.7)

    def test_init(self, se):
        assert se.strategy_count == 0
        assert se.generation == 0

    def test_create_strategy(self, se):
        s = se.create_strategy("s1", {"lr": 0.1, "batch": 32})
        assert s.name == "s1"
        assert se.strategy_count == 1

    def test_mutate(self, se):
        s = se.create_strategy("s1", {"lr": 0.1, "batch": 32})
        child = se.mutate(s.strategy_id)
        assert child is not None
        assert se.strategy_count == 2

    def test_mutate_specific_param(self, se):
        s = se.create_strategy("s1", {"lr": 0.1})
        child = se.mutate(s.strategy_id, "lr")
        assert child is not None
        assert child.parameters["lr"] != s.parameters["lr"]

    def test_mutate_nonexistent(self, se):
        assert se.mutate("fake") is None

    def test_crossover(self, se):
        a = se.create_strategy("a", {"x": 1, "y": 2})
        b = se.create_strategy("b", {"x": 3, "y": 4})
        child = se.crossover(a.strategy_id, b.strategy_id)
        assert child is not None
        assert "x" in child.parameters

    def test_crossover_nonexistent(self, se):
        a = se.create_strategy("a", {"x": 1})
        assert se.crossover(a.strategy_id, "fake") is None

    def test_evaluate_fitness(self, se):
        s = se.create_strategy("s1", {})
        assert se.evaluate_fitness(s.strategy_id, 0.85) is True
        assert s.fitness == 0.85
        assert s.status == StrategyStatus.TESTING

    def test_evaluate_nonexistent(self, se):
        assert se.evaluate_fitness("fake", 0.5) is False

    def test_select_best(self, se):
        for i in range(5):
            s = se.create_strategy(f"s{i}", {})
            se.evaluate_fitness(s.strategy_id, i * 0.2)
        best = se.select_best(top_n=2)
        assert len(best) == 2
        assert best[0].fitness >= best[1].fitness

    def test_promote(self, se):
        s = se.create_strategy("s1", {})
        assert se.promote(s.strategy_id) is True
        assert se.active_count == 1

    def test_promote_nonexistent(self, se):
        assert se.promote("fake") is False

    def test_retire(self, se):
        s = se.create_strategy("s1", {})
        se.promote(s.strategy_id)
        assert se.retire(s.strategy_id) is True
        assert se.active_count == 0

    def test_retire_nonexistent(self, se):
        assert se.retire("fake") is False

    def test_advance_generation(self, se):
        gen = se.advance_generation()
        assert gen == 1
        assert se.generation == 1

    def test_get_strategy(self, se):
        s = se.create_strategy("s1", {"lr": 0.1})
        info = se.get_strategy(s.strategy_id)
        assert info is not None
        assert info["name"] == "s1"

    def test_get_strategy_nonexistent(self, se):
        assert se.get_strategy("fake") is None


# ── KnowledgeDistiller Testleri ─────────────────────────────


class TestKnowledgeDistiller:
    """Bilgi damitici testleri."""

    @pytest.fixture()
    def kd(self):
        return KnowledgeDistiller(min_evidence=2)

    def test_init(self, kd):
        assert kd.rule_count == 0
        assert kd.pruned_count == 0

    def test_extract_generalizations(self, kd):
        exps = [
            ExperienceRecord(
                action="deploy", outcome=OutcomeType.SUCCESS,
            )
            for _ in range(5)
        ]
        rules = kd.extract_generalizations(exps)
        assert len(rules) >= 1

    def test_extract_empty(self, kd):
        assert kd.extract_generalizations([]) == []

    def test_create_rule(self, kd):
        rule = kd.create_rule("if_test", "then_deploy", 0.8)
        assert rule.confidence == 0.8
        assert kd.rule_count == 1

    def test_validate_hypothesis_supported(self, kd):
        result = kd.validate_hypothesis("ci_helps", 8, 2)
        assert result["supported"] is True
        assert result["verdict"] == "supported"

    def test_validate_hypothesis_rejected(self, kd):
        result = kd.validate_hypothesis("bad_idea", 1, 9)
        assert result["supported"] is False
        assert result["verdict"] == "rejected"

    def test_validate_hypothesis_insufficient(self, kd):
        result = kd.validate_hypothesis("maybe", 1, 0)
        assert result["verdict"] == "insufficient_evidence"

    def test_validate_zero_evidence(self, kd):
        result = kd.validate_hypothesis("empty", 0, 0)
        assert result["verdict"] == "insufficient_evidence"

    def test_refine_rule(self, kd):
        rule = kd.create_rule("cond", "act", 0.5)
        assert kd.refine_rule(rule.rule_id, 0.9, 3) is True
        assert rule.confidence > 0.5

    def test_refine_nonexistent(self, kd):
        assert kd.refine_rule("fake", 0.9) is False

    def test_prune_outdated(self, kd):
        kd.create_rule("weak", "act", 0.1)
        kd.create_rule("strong", "act", 0.9)
        pruned = kd.prune_outdated(min_confidence=0.3)
        assert pruned == 1
        assert kd.rule_count == 1

    def test_invalidate_rule(self, kd):
        rule = kd.create_rule("cond", "act")
        assert kd.invalidate_rule(rule.rule_id) is True
        assert kd.rule_count == 0

    def test_invalidate_nonexistent(self, kd):
        assert kd.invalidate_rule("fake") is False

    def test_get_rules(self, kd):
        kd.create_rule("a", "b", 0.8)
        kd.create_rule("c", "d", 0.5)
        rules = kd.get_rules(min_confidence=0.6)
        assert len(rules) == 1

    def test_get_rule(self, kd):
        rule = kd.create_rule("cond", "act")
        info = kd.get_rule(rule.rule_id)
        assert info is not None
        assert info["condition"] == "cond"

    def test_get_rule_nonexistent(self, kd):
        assert kd.get_rule("fake") is None

    def test_hypothesis_creates_rule(self, kd):
        kd.validate_hypothesis("good_pattern", 8, 2)
        assert kd.rule_count == 1


# ── SkillOptimizer Testleri ─────────────────────────────────


class TestSkillOptimizer:
    """Yetenek optimizasyonu testleri."""

    @pytest.fixture()
    def so(self):
        return SkillOptimizer()

    def test_init(self, so):
        assert so.skill_count == 0

    def test_register_skill(self, so):
        skill = so.register_skill("coding")
        assert skill["name"] == "coding"
        assert so.skill_count == 1

    def test_record_performance(self, so):
        so.register_skill("coding")
        assert so.record_performance("coding", 0.8) is True

    def test_record_performance_nonexistent(self, so):
        assert so.record_performance("ghost", 0.5) is False

    def test_identify_bottlenecks(self, so):
        so.register_skill("weak_skill")
        for _ in range(5):
            so.record_performance("weak_skill", 0.2)
        bns = so.identify_bottlenecks(threshold=0.4)
        assert len(bns) == 1
        assert bns[0]["skill"] == "weak_skill"

    def test_no_bottlenecks(self, so):
        so.register_skill("strong")
        for _ in range(5):
            so.record_performance("strong", 0.9)
        assert so.identify_bottlenecks(0.4) == []

    def test_tune_parameter(self, so):
        so.register_skill("s1", parameters={"lr": 0.1})
        assert so.tune_parameter("s1", "lr", 0.05) is True
        assert so.optimization_count == 1

    def test_tune_nonexistent(self, so):
        assert so.tune_parameter("ghost", "lr", 0.1) is False

    def test_get_skill_profile(self, so):
        so.register_skill("coding")
        so.record_performance("coding", 0.8)
        profile = so.get_skill_profile("coding")
        assert profile is not None
        assert profile["avg_score"] == 0.8

    def test_get_skill_profile_nonexistent(self, so):
        assert so.get_skill_profile("ghost") is None

    def test_skill_level_upgrade(self, so):
        so.register_skill("coding")
        for _ in range(5):
            so.record_performance("coding", 0.95)
        profile = so.get_skill_profile("coding")
        assert profile["level"] == SkillLevel.EXPERT.value

    def test_improvement_suggestions(self, so):
        so.register_skill("weak")
        for _ in range(5):
            so.record_performance("weak", 0.3)
        suggestions = so.get_improvement_suggestions()
        assert len(suggestions) >= 1

    def test_trend_calculation(self, so):
        so.register_skill("trending")
        scores = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        for s in scores:
            so.record_performance("trending", s)
        profile = so.get_skill_profile("trending")
        assert profile["trend"] == "improving"


# ── FeedbackProcessor Testleri ──────────────────────────────


class TestFeedbackProcessor:
    """Geri bildirim isleyici testleri."""

    @pytest.fixture()
    def fp(self):
        return FeedbackProcessor()

    def test_init(self, fp):
        assert fp.feedback_count == 0

    def test_process_explicit_positive(self, fp):
        fb = fp.process_explicit("alice", "harika sonuc", 0.9)
        assert fb["sentiment"] == "positive"
        assert fp.feedback_count == 1

    def test_process_explicit_negative(self, fp):
        fb = fp.process_explicit("alice", "kotu sonuc", -0.8)
        assert fb["sentiment"] == "negative"

    def test_process_explicit_neutral(self, fp):
        fb = fp.process_explicit("alice", "filler content", 0.0)
        assert fb["sentiment"] == "neutral"

    def test_process_implicit_completed(self, fp):
        fb = fp.process_implicit(
            "alice", "task_a", duration=2.0, completed=True,
        )
        assert fb["inferred_rating"] == 0.8

    def test_process_implicit_slow(self, fp):
        fb = fp.process_implicit(
            "alice", "task_b", duration=60.0, completed=True,
        )
        assert fb["inferred_rating"] == 0.5

    def test_process_implicit_incomplete(self, fp):
        fb = fp.process_implicit(
            "alice", "task_c", completed=False,
        )
        assert fb["inferred_rating"] == -0.5

    def test_process_correction(self, fp):
        fb = fp.process_correction(
            "alice", "wrong_action", "right_action",
        )
        assert fb["original"] == "wrong_action"
        assert fp.correction_count == 1

    def test_infer_preferences(self, fp):
        fp.process_explicit(
            "alice", "iyi", 0.8,
            context={"style": "formal"},
        )
        prefs = fp.infer_preferences("alice")
        assert "likes" in prefs

    def test_infer_preferences_empty(self, fp):
        prefs = fp.infer_preferences("ghost")
        assert prefs == {}

    def test_sentiment_summary(self, fp):
        fp.process_explicit("a", "harika", 0.9)
        fp.process_explicit("b", "kotu", -0.8)
        fp.process_explicit("c", "ok", 0.0)
        summary = fp.get_sentiment_summary()
        assert summary["total"] == 3
        assert summary["positive"] == 1

    def test_get_corrections(self, fp):
        fp.process_correction("alice", "a", "b")
        fp.process_correction("bob", "c", "d")
        corrections = fp.get_corrections(source="alice")
        assert len(corrections) == 1

    def test_get_feedback_by_source(self, fp):
        fp.process_explicit("alice", "good", 0.5)
        fp.process_explicit("bob", "bad", -0.5)
        feedbacks = fp.get_feedback_by_source("alice")
        assert len(feedbacks) == 1

    def test_preference_tracking(self, fp):
        fp.process_explicit(
            "alice", "test", 0.8,
            context={"theme": "dark"},
        )
        fp.process_explicit(
            "alice", "test", -0.8,
            context={"theme": "light"},
        )
        prefs = fp.infer_preferences("alice")
        assert len(prefs["likes"]) >= 1
        assert len(prefs["dislikes"]) >= 1


# ── TransferLearner Testleri ────────────────────────────────


class TestTransferLearner:
    """Transfer ogrenici testleri."""

    @pytest.fixture()
    def tl(self):
        return TransferLearner()

    def test_init(self, tl):
        assert tl.domain_count == 0

    def test_register_domain(self, tl):
        d = tl.register_domain("web", ["html", "css", "js"])
        assert d["name"] == "web"
        assert tl.domain_count == 1

    def test_find_transferable_skills(self, tl):
        tl.register_domain("web", ["html", "css", "js"])
        tl.register_domain("mobile", ["css", "js", "react"])
        common = tl.find_transferable_skills("web", "mobile")
        assert "css" in common
        assert "js" in common

    def test_find_transferable_nonexistent(self, tl):
        assert tl.find_transferable_skills("a", "b") == []

    def test_transfer_knowledge(self, tl):
        tl.register_domain(
            "web", ["html"],
            knowledge={"routing": "react-router"},
        )
        tl.register_domain("mobile", ["react"])
        result = tl.transfer_knowledge("web", "mobile")
        assert result["success"] is True
        assert result["transferred"] == 1
        assert tl.transfer_count == 1

    def test_transfer_knowledge_nonexistent(self, tl):
        result = tl.transfer_knowledge("a", "b")
        assert result["success"] is False

    def test_transfer_specific_keys(self, tl):
        tl.register_domain(
            "a", [],
            knowledge={"x": 1, "y": 2, "z": 3},
        )
        tl.register_domain("b", [])
        result = tl.transfer_knowledge("a", "b", ["x", "y"])
        assert result["transferred"] == 2

    def test_detect_analogy(self, tl):
        tl.register_domain(
            "web", ["routing"],
            knowledge={"routing": "react-router"},
        )
        tl.register_domain(
            "mobile", ["navigation"],
            knowledge={"routing_mobile": "react-navigation"},
        )
        analogy = tl.detect_analogy("routing", "web", "mobile")
        assert analogy is not None
        assert tl.analogy_count == 1

    def test_detect_analogy_none(self, tl):
        tl.register_domain("a", [])
        tl.register_domain("b", [])
        assert tl.detect_analogy("xyz", "a", "b") is None

    def test_add_adaptation_rule(self, tl):
        rule = tl.add_adaptation_rule("web_", "mobile_", "scale")
        assert rule["transform"] == "scale"
        assert tl.rule_count == 1

    def test_domain_similarity(self, tl):
        tl.register_domain("a", ["x", "y", "z"])
        tl.register_domain("b", ["y", "z", "w"])
        sim = tl.get_domain_similarity("a", "b")
        # Jaccard: {y,z} / {x,y,z,w} = 2/4 = 0.5
        assert abs(sim - 0.5) < 0.01

    def test_domain_similarity_none(self, tl):
        assert tl.get_domain_similarity("a", "b") == 0.0

    def test_domain_similarity_identical(self, tl):
        tl.register_domain("a", ["x", "y"])
        tl.register_domain("b", ["x", "y"])
        assert tl.get_domain_similarity("a", "b") == 1.0


# ── CurriculumManager Testleri ──────────────────────────────


class TestCurriculumManager:
    """Mufredat yoneticisi testleri."""

    @pytest.fixture()
    def cm(self):
        return CurriculumManager()

    def test_init(self, cm):
        assert cm.topic_count == 0
        assert cm.learner_count == 0

    def test_add_topic(self, cm):
        topic = cm.add_topic("python_basics", 0.3)
        assert topic["name"] == "python_basics"
        assert cm.topic_count == 1

    def test_add_topic_with_prereqs(self, cm):
        cm.add_topic("basics", 0.2)
        cm.add_topic("advanced", 0.8, prerequisites=["basics"])
        assert cm.topic_count == 2

    def test_record_progress(self, cm):
        cm.add_topic("python")
        progress = cm.record_progress("alice", "python", 0.7)
        assert progress["attempts"] == 1
        assert cm.learner_count == 1

    def test_check_prerequisites_met(self, cm):
        cm.add_topic("basics")
        cm.add_topic("advanced", prerequisites=["basics"])
        # Basici tamamla
        for _ in range(5):
            cm.record_progress("alice", "basics", 0.9)
        result = cm.check_prerequisites("alice", "advanced")
        assert result["met"] is True

    def test_check_prerequisites_not_met(self, cm):
        cm.add_topic("basics")
        cm.add_topic("advanced", prerequisites=["basics"])
        result = cm.check_prerequisites("alice", "advanced")
        assert result["met"] is False
        assert "basics" in result["missing"]

    def test_check_no_prerequisites(self, cm):
        cm.add_topic("intro")
        result = cm.check_prerequisites("alice", "intro")
        assert result["met"] is True

    def test_assess_mastery_novice(self, cm):
        cm.add_topic("topic")
        result = cm.assess_mastery("alice", "topic")
        assert result["level"] == SkillLevel.NOVICE.value
        assert result["mastered"] is False

    def test_assess_mastery_expert(self, cm):
        cm.add_topic("topic")
        for _ in range(5):
            cm.record_progress("alice", "topic", 0.95)
        result = cm.assess_mastery("alice", "topic")
        assert result["level"] == SkillLevel.EXPERT.value
        assert result["mastered"] is True

    def test_identify_gaps(self, cm):
        cm.add_topic("a", 0.3)
        cm.add_topic("b", 0.5)
        # a: not started, b: low
        cm.record_progress("alice", "b", 0.2)
        gaps = cm.identify_gaps("alice")
        assert len(gaps) == 2

    def test_get_next_topics(self, cm):
        cm.add_topic("basics", 0.2)
        cm.add_topic("intermediate", 0.5)
        cm.add_topic("advanced", 0.8, prerequisites=["basics"])
        topics = cm.get_next_topics("alice")
        # basics ve intermediate olmali (advanced on kosul karsilanmadi)
        topic_names = [t["topic"] for t in topics]
        assert "basics" in topic_names
        assert "intermediate" in topic_names

    def test_scale_difficulty(self, cm):
        cm.add_topic("topic", 0.5)
        new_diff = cm.scale_difficulty("topic", 1.5)
        assert new_diff == 0.75

    def test_scale_difficulty_clamped(self, cm):
        cm.add_topic("topic", 0.8)
        new_diff = cm.scale_difficulty("topic", 2.0)
        assert new_diff == 1.0

    def test_scale_nonexistent(self, cm):
        assert cm.scale_difficulty("ghost", 1.5) == 0.0

    def test_mastery_count(self, cm):
        cm.add_topic("a")
        cm.add_topic("b")
        cm.record_progress("alice", "a", 0.8)
        cm.record_progress("alice", "b", 0.5)
        assert cm.mastery_count == 2


# ── AdaptiveEngine Testleri ─────────────────────────────────


class TestAdaptiveEngine:
    """Adaptif motor testleri."""

    @pytest.fixture()
    def ae(self):
        return AdaptiveEngine(
            learning_rate=0.1, exploration_rate=0.2,
        )

    def test_init(self, ae):
        assert ae.learning_rate == 0.1
        assert ae.exploration_rate == 0.2
        assert ae.cycle_count == 0

    def test_learn_from_experience(self, ae):
        result = ae.learn_from_experience(
            "deploy", OutcomeType.SUCCESS, reward=1.0,
        )
        assert "experience_id" in result
        assert ae.experiences.total_count == 1

    def test_process_feedback(self, ae):
        result = ae.process_feedback(
            "alice", "harika sonuc", rating=0.9,
        )
        assert result["sentiment"] == "positive"
        assert ae.feedback.feedback_count == 1
        # Deneyim olarak da kaydedilmeli
        assert ae.experiences.total_count == 1

    def test_run_improvement_cycle(self, ae):
        # Yeterli deneyim ekle
        for i in range(25):
            outcome = (
                OutcomeType.SUCCESS if i % 2 == 0
                else OutcomeType.FAILURE
            )
            ae.learn_from_experience(
                f"action_{i % 5}", outcome,
                reward=1.0 if outcome == OutcomeType.SUCCESS else -1.0,
                tags=["auto"],
            )
        result = ae.run_improvement_cycle()
        assert "actions" in result
        assert len(result["actions"]) >= 4

    def test_get_learning_summary(self, ae):
        ae.learn_from_experience("test", OutcomeType.SUCCESS)
        summary = ae.get_learning_summary()
        assert summary["total_experiences"] == 1
        assert summary["learning_rate"] == 0.1

    def test_adjust_learning_rate(self, ae):
        new_lr = ae.adjust_learning_rate(0.05)
        assert new_lr == 0.05
        assert ae.learning_rate == 0.05

    def test_adjust_learning_rate_clamped(self, ae):
        new_lr = ae.adjust_learning_rate(5.0)
        assert new_lr == 1.0

    def test_adjust_exploration_rate(self, ae):
        new_er = ae.adjust_exploration_rate(0.3)
        assert new_er == 0.3

    def test_get_snapshot(self, ae):
        ae.learn_from_experience("test", OutcomeType.SUCCESS)
        snapshot = ae.get_snapshot()
        assert isinstance(snapshot, AdaptiveSnapshot)
        assert snapshot.total_experiences == 1

    def test_all_components_accessible(self, ae):
        assert ae.experiences is not None
        assert ae.patterns is not None
        assert ae.strategies is not None
        assert ae.knowledge is not None
        assert ae.skills is not None
        assert ae.feedback is not None
        assert ae.transfer is not None
        assert ae.curriculum is not None


# ── Entegrasyon Testleri ────────────────────────────────────


class TestAdaptiveIntegration:
    """Entegrasyon testleri."""

    def test_full_learning_pipeline(self):
        ae = AdaptiveEngine()

        # Deneyim topla
        for i in range(30):
            outcome = (
                OutcomeType.SUCCESS if i % 3 != 0
                else OutcomeType.FAILURE
            )
            ae.learn_from_experience(
                f"task_{i % 5}", outcome,
                reward=1.0 if outcome == OutcomeType.SUCCESS else -0.5,
                tags=["pipeline"],
            )

        # Geri bildirim isle
        ae.process_feedback("user", "iyi gidiyor", 0.8)

        # Iyilestirme dongusu
        result = ae.run_improvement_cycle()
        assert len(result["actions"]) >= 4

        # Ozet
        summary = ae.get_learning_summary()
        assert summary["total_experiences"] > 30

    def test_strategy_evolution_cycle(self):
        se = StrategyEvolver()
        # Strateji olustur
        s1 = se.create_strategy("s1", {"lr": 0.1, "batch": 32})
        s2 = se.create_strategy("s2", {"lr": 0.01, "batch": 64})

        # Fitness degerlendir
        se.evaluate_fitness(s1.strategy_id, 0.7)
        se.evaluate_fitness(s2.strategy_id, 0.9)

        # Caprazla
        child = se.crossover(s1.strategy_id, s2.strategy_id)
        assert child is not None

        # Mutasyon
        mutant = se.mutate(child.strategy_id)
        assert mutant is not None

        # En iyiyi sec
        best = se.select_best(1)
        assert best[0].fitness == 0.9

        # Nesil ilerlet
        se.advance_generation()
        assert se.generation == 1

    def test_knowledge_lifecycle(self):
        kd = KnowledgeDistiller(min_evidence=2)

        # Kurallar olustur
        r1 = kd.create_rule("if_ci", "expect_success", 0.9)
        r2 = kd.create_rule("if_manual", "expect_failure", 0.2)

        # Rafine et
        kd.refine_rule(r1.rule_id, 0.95, 5)

        # Buda
        pruned = kd.prune_outdated(min_confidence=0.3)
        assert pruned == 1
        assert kd.rule_count == 1

    def test_transfer_learning_flow(self):
        tl = TransferLearner()
        tl.register_domain(
            "backend", ["python", "api", "database"],
            knowledge={"framework": "fastapi", "orm": "sqlalchemy"},
        )
        tl.register_domain(
            "frontend", ["js", "api", "css"],
        )

        # Transfer
        result = tl.transfer_knowledge("backend", "frontend", ["framework"])
        assert result["success"] is True

        # Benzerlik
        sim = tl.get_domain_similarity("backend", "frontend")
        assert sim > 0  # "api" ortak

    def test_curriculum_progression(self):
        cm = CurriculumManager()
        cm.add_topic("intro", 0.2)
        cm.add_topic("basics", 0.4, prerequisites=["intro"])
        cm.add_topic("advanced", 0.8, prerequisites=["basics"])

        # Intro tamamla
        for _ in range(5):
            cm.record_progress("alice", "intro", 0.9)

        # Basics acilmis olmali
        prereq = cm.check_prerequisites("alice", "basics")
        assert prereq["met"] is True

        # Advanced henuz acilmamis
        prereq = cm.check_prerequisites("alice", "advanced")
        assert prereq["met"] is False

    def test_snapshot_reflects_state(self):
        ae = AdaptiveEngine()
        ae.learn_from_experience("test", OutcomeType.SUCCESS)
        ae.skills.register_skill("coding")
        ae.feedback.process_explicit("user", "good", 0.5)
        ae.transfer.register_domain("web", ["html"])

        snapshot = ae.get_snapshot()
        assert snapshot.total_experiences == 1
        assert snapshot.skills_tracked == 1
        assert snapshot.feedback_processed == 1
