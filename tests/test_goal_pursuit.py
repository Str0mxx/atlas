"""ATLAS Autonomous Goal Pursuit sistemi testleri."""

import pytest

from app.models.goal_pursuit import (
    AlignmentLevel,
    GoalCandidate,
    GoalDefinition,
    GoalPriority,
    GoalPursuitSnapshot,
    GoalState,
    Initiative,
    InitiativeState,
    LearningRecord,
    LearningType,
    OpportunityScan,
    OpportunityType,
    ValueEstimate,
)
from app.core.goal_pursuit.goal_generator import GoalGenerator
from app.core.goal_pursuit.value_estimator import ValueEstimator
from app.core.goal_pursuit.goal_selector import GoalSelector
from app.core.goal_pursuit.initiative_launcher import InitiativeLauncher
from app.core.goal_pursuit.progress_evaluator import ProgressEvaluator
from app.core.goal_pursuit.learning_extractor import LearningExtractor
from app.core.goal_pursuit.proactive_scanner import ProactiveScanner
from app.core.goal_pursuit.user_aligner import UserAligner
from app.core.goal_pursuit.goal_pursuit_engine import GoalPursuitEngine


# ── Model Testleri ──────────────────────────────────────────────


class TestGoalPursuitModels:
    """Model testleri."""

    def test_goal_candidate_defaults(self):
        c = GoalCandidate()
        assert c.candidate_id
        assert c.title == ""
        assert c.opportunity_type == OpportunityType.GROWTH
        assert c.feasibility == 0.5
        assert c.alignment == AlignmentLevel.NEUTRAL

    def test_goal_definition_defaults(self):
        g = GoalDefinition()
        assert g.goal_id
        assert g.state == GoalState.CANDIDATE
        assert g.priority == GoalPriority.MEDIUM
        assert g.estimated_value == 0.0
        assert g.roi == 0.0
        assert g.started_at is None

    def test_value_estimate_defaults(self):
        v = ValueEstimate()
        assert v.estimate_id
        assert v.expected_benefit == 0.0
        assert v.confidence == 0.5
        assert v.time_horizon_days == 30

    def test_initiative_defaults(self):
        i = Initiative()
        assert i.initiative_id
        assert i.state == InitiativeState.PLANNED
        assert i.progress == 0.0
        assert i.timeline_days == 30

    def test_learning_record_defaults(self):
        r = LearningRecord()
        assert r.record_id
        assert r.learning_type == LearningType.SUCCESS_PATTERN
        assert r.confidence == 0.5

    def test_opportunity_scan_defaults(self):
        s = OpportunityScan()
        assert s.scan_id
        assert s.urgency == 0.5
        assert s.confidence == 0.5

    def test_snapshot_defaults(self):
        s = GoalPursuitSnapshot()
        assert s.total_goals == 0
        assert s.active_goals == 0
        assert s.avg_roi == 0.0
        assert s.success_rate == 0.0

    def test_goal_state_enum(self):
        assert GoalState.CANDIDATE.value == "candidate"
        assert GoalState.ACTIVE.value == "active"
        assert GoalState.COMPLETED.value == "completed"
        assert GoalState.ABANDONED.value == "abandoned"

    def test_goal_priority_enum(self):
        assert GoalPriority.CRITICAL.value == "critical"
        assert GoalPriority.OPPORTUNISTIC.value == "opportunistic"

    def test_initiative_state_enum(self):
        assert InitiativeState.PLANNED.value == "planned"
        assert InitiativeState.RUNNING.value == "running"
        assert InitiativeState.COMPLETED.value == "completed"

    def test_opportunity_type_enum(self):
        assert OpportunityType.MARKET.value == "market"
        assert OpportunityType.COST_SAVING.value == "cost_saving"
        assert OpportunityType.INNOVATION.value == "innovation"

    def test_learning_type_enum(self):
        assert LearningType.SUCCESS_PATTERN.value == "success_pattern"
        assert LearningType.ANTI_PATTERN.value == "anti_pattern"

    def test_alignment_level_enum(self):
        assert AlignmentLevel.STRONG.value == "strong"
        assert AlignmentLevel.MISALIGNED.value == "misaligned"

    def test_goal_with_custom_values(self):
        g = GoalDefinition(
            title="Test Goal",
            priority=GoalPriority.HIGH,
            estimated_value=5000.0,
            success_criteria=["KPI1", "KPI2"],
        )
        assert g.title == "Test Goal"
        assert g.priority == GoalPriority.HIGH
        assert g.estimated_value == 5000.0
        assert len(g.success_criteria) == 2

    def test_initiative_with_milestones(self):
        i = Initiative(
            name="Test",
            milestones=["M1", "M2", "M3"],
            success_metrics={"revenue": 1000.0},
        )
        assert len(i.milestones) == 3
        assert i.success_metrics["revenue"] == 1000.0


# ── GoalGenerator Testleri ──────────────────────────────────────


class TestGoalGenerator:
    """GoalGenerator testleri."""

    def setup_method(self):
        self.gen = GoalGenerator()

    def test_identify_opportunity(self):
        c = self.gen.identify_opportunity(
            OpportunityType.MARKET, "Yeni pazar",
            estimated_value=5000.0, source="tarama",
        )
        assert c.title == "Yeni pazar"
        assert c.opportunity_type == OpportunityType.MARKET
        assert c.expected_value == 5000.0
        assert self.gen.total_candidates == 1

    def test_generate_goal(self):
        c = self.gen.identify_opportunity(
            OpportunityType.GROWTH, "Buyume firsati",
        )
        g = self.gen.generate_goal(
            c.candidate_id,
            success_criteria=["KPI1"],
            priority=GoalPriority.HIGH,
        )
        assert g is not None
        assert g.title == "Buyume firsati"
        assert g.priority == GoalPriority.HIGH
        assert self.gen.total_goals == 1

    def test_generate_goal_invalid_candidate(self):
        result = self.gen.generate_goal("invalid")
        assert result is None

    def test_register_and_use_template(self):
        self.gen.register_template("growth", {
            "title": "Growth Template",
            "priority": GoalPriority.HIGH,
        })
        assert self.gen.template_count == 1

        g = self.gen.generate_from_template("growth")
        assert g is not None
        assert g.title == "Growth Template"

    def test_generate_from_invalid_template(self):
        result = self.gen.generate_from_template("invalid")
        assert result is None

    def test_prioritize_candidates(self):
        c1 = self.gen.identify_opportunity(
            OpportunityType.GROWTH, "Low", estimated_value=100,
        )
        c2 = self.gen.identify_opportunity(
            OpportunityType.GROWTH, "High", estimated_value=1000,
        )
        self.gen.check_feasibility(c1.candidate_id, 0.5)
        self.gen.check_feasibility(c2.candidate_id, 0.9)

        ranked = self.gen.prioritize_candidates()
        assert ranked[0].title == "High"

    def test_check_feasibility(self):
        c = self.gen.identify_opportunity(
            OpportunityType.GROWTH, "Test",
        )
        assert self.gen.check_feasibility(c.candidate_id, 0.8)
        assert c.feasibility == 0.8
        assert not self.gen.check_feasibility("invalid", 0.5)

    def test_check_alignment(self):
        c = self.gen.identify_opportunity(
            OpportunityType.GROWTH, "Test",
        )
        assert self.gen.check_alignment(
            c.candidate_id, AlignmentLevel.STRONG,
        )
        assert c.alignment == AlignmentLevel.STRONG
        assert not self.gen.check_alignment(
            "invalid", AlignmentLevel.STRONG,
        )

    def test_get_candidates_by_type(self):
        self.gen.identify_opportunity(OpportunityType.MARKET, "A")
        self.gen.identify_opportunity(OpportunityType.GROWTH, "B")
        self.gen.identify_opportunity(OpportunityType.MARKET, "C")

        market = self.gen.get_candidates_by_type(OpportunityType.MARKET)
        assert len(market) == 2

    def test_remove_candidate(self):
        c = self.gen.identify_opportunity(
            OpportunityType.GROWTH, "Test",
        )
        assert self.gen.remove_candidate(c.candidate_id)
        assert self.gen.total_candidates == 0
        assert not self.gen.remove_candidate("invalid")

    def test_get_candidate_and_goal(self):
        c = self.gen.identify_opportunity(
            OpportunityType.GROWTH, "Test",
        )
        assert self.gen.get_candidate(c.candidate_id) == c
        assert self.gen.get_candidate("invalid") is None

        g = self.gen.generate_goal(c.candidate_id)
        assert self.gen.get_goal(g.goal_id) == g
        assert self.gen.get_goal("invalid") is None

    def test_feasibility_clamping(self):
        c = self.gen.identify_opportunity(
            OpportunityType.GROWTH, "Test",
        )
        self.gen.check_feasibility(c.candidate_id, 1.5)
        assert c.feasibility == 1.0
        self.gen.check_feasibility(c.candidate_id, -0.5)
        assert c.feasibility == 0.0

    def test_template_with_overrides(self):
        self.gen.register_template("base", {
            "title": "Base",
            "priority": GoalPriority.LOW,
        })
        g = self.gen.generate_from_template(
            "base", {"title": "Override"},
        )
        assert g.title == "Override"


# ── ValueEstimator Testleri ─────────────────────────────────────


class TestValueEstimator:
    """ValueEstimator testleri."""

    def setup_method(self):
        self.est = ValueEstimator(discount_rate=0.1)

    def test_estimate_benefit(self):
        total = self.est.estimate_benefit(
            "g1",
            revenue_impact=1000,
            cost_saving=500,
            efficiency_gain=200,
            strategic_value=300,
        )
        assert total == 2000.0
        est = self.est.get_estimate("g1")
        assert est.expected_benefit == 2000.0

    def test_estimate_cost(self):
        total = self.est.estimate_cost(
            "g1",
            direct_cost=500,
            opportunity_cost=200,
            resource_cost=100,
            risk_cost=50,
        )
        assert total == 850.0

    def test_calculate_roi(self):
        self.est.estimate_benefit("g1", revenue_impact=2000)
        self.est.estimate_cost("g1", direct_cost=1000)
        roi = self.est.calculate_roi("g1")
        assert roi == 1.0  # (2000 - 1000) / 1000

    def test_roi_zero_cost(self):
        roi = self.est.calculate_roi("nonexistent")
        assert roi == 0.0

    def test_risk_adjusted_value(self):
        self.est.estimate_benefit("g1", revenue_impact=1000)
        self.est.estimate_cost("g1", direct_cost=200)
        rav = self.est.calculate_risk_adjusted_value("g1", 0.8)
        # 1000 * 0.8 - 200 * 0.2 = 800 - 40 = 760
        assert rav == 760.0

    def test_risk_adjusted_nonexistent(self):
        result = self.est.calculate_risk_adjusted_value("invalid")
        assert result == 0.0

    def test_time_value(self):
        self.est.estimate_benefit("g1", revenue_impact=1000)
        self.est.estimate_cost("g1", direct_cost=500)
        npv = self.est.calculate_time_value("g1", 365)
        # NPV = 1000 / 1.1 - 500 ≈ 909.09 - 500 = 409.09
        assert 400 < npv < 420

    def test_time_value_nonexistent(self):
        result = self.est.calculate_time_value("invalid")
        assert result == 0.0

    def test_compare_goals(self):
        self.est.estimate_benefit("g1", revenue_impact=1000)
        self.est.estimate_cost("g1", direct_cost=500)
        self.est.calculate_risk_adjusted_value("g1", 0.8)

        self.est.estimate_benefit("g2", revenue_impact=2000)
        self.est.estimate_cost("g2", direct_cost=800)
        self.est.calculate_risk_adjusted_value("g2", 0.6)

        compared = self.est.compare_goals(["g1", "g2"])
        assert len(compared) == 2
        # g2: 2000*0.6 - 800*0.4 = 1200 - 320 = 880
        # g1: 1000*0.8 - 500*0.2 = 800 - 100 = 700
        assert compared[0]["goal_id"] == "g2"

    def test_set_risk_factor(self):
        self.est.set_risk_factor("market", 0.7)
        assert self.est._risk_factors["market"] == 0.7

    def test_set_benchmark(self):
        self.est.set_benchmark("retail", {"avg_roi": 0.15})
        assert self.est._benchmarks["retail"]["avg_roi"] == 0.15

    def test_remove_estimate(self):
        self.est.estimate_benefit("g1", revenue_impact=100)
        assert self.est.total_estimates == 1
        assert self.est.remove_estimate("g1")
        assert self.est.total_estimates == 0
        assert not self.est.remove_estimate("invalid")

    def test_discount_rate_property(self):
        assert self.est.discount_rate == 0.1


# ── GoalSelector Testleri ───────────────────────────────────────


class TestGoalSelector:
    """GoalSelector testleri."""

    def setup_method(self):
        self.sel = GoalSelector()
        self.goal1 = GoalDefinition(
            title="Goal 1",
            priority=GoalPriority.HIGH,
        )
        self.goal2 = GoalDefinition(
            title="Goal 2",
            priority=GoalPriority.LOW,
        )

    def test_add_and_score_goal(self):
        self.sel.add_goal(self.goal1)
        scores = self.sel.score_goal(
            self.goal1.goal_id,
            value_score=0.8,
            feasibility_score=0.7,
            alignment_level=AlignmentLevel.STRONG,
            strategic_fit=0.9,
        )
        assert scores is not None
        assert "weighted_total" in scores
        assert scores["weighted_total"] > 0

    def test_score_nonexistent(self):
        result = self.sel.score_goal("invalid")
        assert result is None

    def test_select_top(self):
        self.sel.add_goal(self.goal1)
        self.sel.add_goal(self.goal2)
        self.sel.score_goal(
            self.goal1.goal_id, value_score=0.9,
            feasibility_score=0.8,
        )
        self.sel.score_goal(
            self.goal2.goal_id, value_score=0.3,
            feasibility_score=0.4,
        )
        top = self.sel.select_top(1)
        assert len(top) == 1
        assert top[0]["goal_id"] == self.goal1.goal_id

    def test_resource_availability(self):
        self.sel.set_available_resources({"budget": 1000, "cpu": 4})
        result = self.sel.check_resource_availability(
            "g1", {"budget": 500, "cpu": 8},
        )
        assert not result["available"]
        assert "cpu" in result["missing"]

    def test_resource_sufficient(self):
        self.sel.set_available_resources({"budget": 1000})
        result = self.sel.check_resource_availability(
            "g1", {"budget": 500},
        )
        assert result["available"]

    def test_detect_conflicts(self):
        g1 = GoalDefinition(
            title="G1", dependencies=["db", "api"],
        )
        g2 = GoalDefinition(
            title="G2", dependencies=["db", "cache"],
        )
        self.sel.add_goal(g1)
        self.sel.add_goal(g2)
        conflicts = self.sel.detect_conflicts(
            [g1.goal_id, g2.goal_id],
        )
        assert len(conflicts) >= 1
        assert conflicts[0]["type"] == "resource"

    def test_set_criteria_weights(self):
        self.sel.set_criteria_weights({"value": 0.5})
        assert self.sel._criteria_weights["value"] == 0.5

    def test_approve_goal(self):
        self.sel.add_goal(self.goal1)
        assert self.sel.approve_goal(self.goal1.goal_id)
        assert self.goal1.state == GoalState.APPROVED
        assert not self.sel.approve_goal("invalid")

    def test_reject_goal(self):
        self.sel.add_goal(self.goal1)
        assert self.sel.reject_goal(self.goal1.goal_id)
        assert self.goal1.state == GoalState.ABANDONED
        assert not self.sel.reject_goal("invalid")

    def test_filter_by_state(self):
        self.sel.add_goal(self.goal1)
        self.sel.add_goal(self.goal2)
        self.sel.approve_goal(self.goal1.goal_id)
        approved = self.sel.filter_by_state(GoalState.APPROVED)
        assert len(approved) == 1

    def test_set_user_preferences(self):
        self.sel.set_user_preferences({"domain": "tech"})
        assert self.sel._user_preferences["domain"] == "tech"

    def test_properties(self):
        self.sel.add_goal(self.goal1)
        self.sel.score_goal(self.goal1.goal_id, value_score=0.5)
        assert self.sel.total_goals == 1
        assert self.sel.scored_count == 1
        assert self.sel.conflict_count == 0


# ── InitiativeLauncher Testleri ─────────────────────────────────


class TestInitiativeLauncher:
    """InitiativeLauncher testleri."""

    def setup_method(self):
        self.launcher = InitiativeLauncher()
        self.goal = GoalDefinition(
            title="Test Goal",
            priority=GoalPriority.HIGH,
        )

    def test_create_initiative(self):
        init = self.launcher.create_initiative(
            self.goal,
            resources=["dev1"],
            milestones=["M1", "M2"],
            timeline_days=60,
        )
        assert init.name == "Test Goal"
        assert init.timeline_days == 60
        assert self.launcher.total_initiatives == 1

    def test_launch(self):
        init = self.launcher.create_initiative(self.goal)
        result = self.launcher.launch(init.initiative_id)
        assert result["success"]
        assert init.state == InitiativeState.RUNNING

    def test_launch_nonexistent(self):
        result = self.launcher.launch("invalid")
        assert not result["success"]

    def test_launch_already_running(self):
        init = self.launcher.create_initiative(self.goal)
        self.launcher.launch(init.initiative_id)
        result = self.launcher.launch(init.initiative_id)
        assert not result["success"]

    def test_allocate_resources(self):
        self.launcher.set_resource_pool({"budget": 1000, "cpu": 4})
        init = self.launcher.create_initiative(self.goal)
        result = self.launcher.allocate_resources(
            init.initiative_id, {"budget": 500, "cpu": 2},
        )
        assert result["success"]
        assert self.launcher._resource_pool["budget"] == 500

    def test_allocate_insufficient(self):
        self.launcher.set_resource_pool({"budget": 100})
        init = self.launcher.create_initiative(self.goal)
        result = self.launcher.allocate_resources(
            init.initiative_id, {"budget": 500},
        )
        assert not result["success"]

    def test_set_success_metrics(self):
        init = self.launcher.create_initiative(self.goal)
        assert self.launcher.set_success_metrics(
            init.initiative_id, {"revenue": 5000},
        )
        assert init.success_metrics["revenue"] == 5000
        assert not self.launcher.set_success_metrics(
            "invalid", {},
        )

    def test_add_milestone(self):
        init = self.launcher.create_initiative(self.goal)
        assert self.launcher.add_milestone(
            init.initiative_id, "Phase 1",
        )
        assert "Phase 1" in init.milestones
        assert not self.launcher.add_milestone("invalid", "X")

    def test_update_progress(self):
        init = self.launcher.create_initiative(self.goal)
        assert self.launcher.update_progress(
            init.initiative_id, 0.5,
        )
        assert init.progress == 0.5
        assert not self.launcher.update_progress("invalid", 0.5)

    def test_complete_initiative(self):
        init = self.launcher.create_initiative(self.goal)
        self.launcher.launch(init.initiative_id)
        assert self.launcher.complete_initiative(init.initiative_id)
        assert init.state == InitiativeState.COMPLETED
        assert init.progress == 1.0

    def test_abort_initiative(self):
        init = self.launcher.create_initiative(self.goal)
        self.launcher.launch(init.initiative_id)
        assert self.launcher.abort_initiative(
            init.initiative_id, "Bütçe yetersiz",
        )
        assert init.state == InitiativeState.ABORTED

    def test_get_by_goal(self):
        self.launcher.create_initiative(self.goal)
        self.launcher.create_initiative(self.goal)
        found = self.launcher.get_by_goal(self.goal.goal_id)
        assert len(found) == 2

    def test_get_active(self):
        init = self.launcher.create_initiative(self.goal)
        self.launcher.launch(init.initiative_id)
        assert len(self.launcher.get_active()) == 1
        assert self.launcher.active_count == 1

    def test_completed_count(self):
        init = self.launcher.create_initiative(self.goal)
        self.launcher.launch(init.initiative_id)
        self.launcher.complete_initiative(init.initiative_id)
        assert self.launcher.completed_count == 1


# ── ProgressEvaluator Testleri ──────────────────────────────────


class TestProgressEvaluator:
    """ProgressEvaluator testleri."""

    def setup_method(self):
        self.eval = ProgressEvaluator()

    def test_track_progress(self):
        result = self.eval.track_progress("g1", 0.3)
        assert result["progress"] == 0.3
        assert result["delta"] == 0.3
        assert self.eval.total_tracked == 1

    def test_track_progress_update(self):
        self.eval.track_progress("g1", 0.3)
        result = self.eval.track_progress("g1", 0.7)
        assert result["delta"] == pytest.approx(0.4, abs=0.001)

    def test_add_milestone(self):
        ms = self.eval.add_milestone("g1", "Phase 1", 0.5)
        assert ms["name"] == "Phase 1"
        assert not ms["reached"]

    def test_evaluate_milestones(self):
        self.eval.add_milestone("g1", "Phase 1", 0.3)
        self.eval.add_milestone("g1", "Phase 2", 0.7)
        self.eval.track_progress("g1", 0.5)
        result = self.eval.evaluate_milestones("g1")
        assert result["reached"] == 1
        assert result["remaining"] == 1

    def test_suggest_correction(self):
        correction = self.eval.suggest_correction(
            "g1", "Ilerleme yavas", "Kaynak artir",
        )
        assert correction["issue"] == "Ilerleme yavas"
        assert not correction["applied"]

    def test_apply_correction(self):
        self.eval.suggest_correction("g1", "issue", "fix")
        assert self.eval.apply_correction("g1", 0)
        corrections = self.eval.get_corrections("g1")
        assert corrections[0]["applied"]
        assert not self.eval.apply_correction("g1", 99)

    def test_should_abandon_stale(self):
        for _ in range(6):
            self.eval.track_progress("g1", 0.1)
        result = self.eval.should_abandon("g1")
        assert result["should_abandon"]

    def test_should_abandon_progressing(self):
        for i in range(6):
            self.eval.track_progress("g1", i * 0.1)
        result = self.eval.should_abandon("g1")
        assert not result["should_abandon"]

    def test_should_abandon_no_data(self):
        result = self.eval.should_abandon("g1")
        assert not result["should_abandon"]

    def test_declare_success(self):
        self.eval.track_progress("g1", 1.0)
        self.eval.add_milestone("g1", "M1", 0.5)
        self.eval.evaluate_milestones("g1")
        result = self.eval.declare_success("g1")
        assert result["success"]
        assert result["final_progress"] == 1.0
        assert self.eval.success_count == 1

    def test_declare_success_no_data(self):
        result = self.eval.declare_success("invalid")
        assert not result["success"]

    def test_declare_failure(self):
        self.eval.track_progress("g1", 0.2)
        result = self.eval.declare_failure("g1", "Bütçe bitti")
        assert result["success"]
        assert result["reason"] == "Bütçe bitti"

    def test_get_progress(self):
        self.eval.track_progress("g1", 0.5)
        progress = self.eval.get_progress("g1")
        assert progress["current"] == 0.5
        assert self.eval.get_progress("invalid") is None

    def test_properties(self):
        self.eval.track_progress("g1", 0.5)
        self.eval.declare_success("g1")
        assert self.eval.total_tracked == 1
        assert self.eval.total_evaluations == 1


# ── LearningExtractor Testleri ──────────────────────────────────


class TestLearningExtractor:
    """LearningExtractor testleri."""

    def setup_method(self):
        self.learner = LearningExtractor()

    def test_extract_success_pattern(self):
        r = self.learner.extract_success_pattern(
            "g1", "Erken teslimat",
            insights=["Kaynak yeterli"],
            confidence=0.9,
        )
        assert r.learning_type == LearningType.SUCCESS_PATTERN
        assert r.confidence == 0.9
        assert self.learner.success_pattern_count == 1

    def test_analyze_failure(self):
        r = self.learner.analyze_failure(
            "g1", "Bütçe aşımı",
            root_causes=["Yetersiz planlama"],
            lessons=["Daha iyi tahmin yap"],
        )
        assert r.learning_type == LearningType.FAILURE_ANALYSIS
        assert self.learner.anti_pattern_count == 1

    def test_refine_strategy(self):
        r = self.learner.refine_strategy(
            "g1", "Strateji güncelleme",
            current_strategy="A", refined_strategy="B",
            rationale=["Daha etkili"],
        )
        assert r.learning_type == LearningType.STRATEGY_INSIGHT

    def test_capture_knowledge(self):
        r = self.learner.capture_knowledge(
            "g1", "API entegrasyonu",
            knowledge="REST API kullan",
            tags=["api", "integration"],
        )
        assert r.learning_type == LearningType.BEST_PRACTICE
        assert len(r.applicability) == 2

    def test_add_best_practice(self):
        p = self.learner.add_best_practice(
            "Erken test", "Her zaman test yaz",
            effectiveness=0.9,
        )
        assert p["effectiveness"] == 0.9
        assert self.learner.best_practice_count == 1

    def test_update_best_practice(self):
        self.learner.add_best_practice("P1", "D1", effectiveness=0.5)
        assert self.learner.update_best_practice(
            0, effectiveness=0.8, increment_usage=True,
        )
        practices = self.learner.get_best_practices()
        assert practices[0]["effectiveness"] == 0.8
        assert practices[0]["usage_count"] == 1
        assert not self.learner.update_best_practice(99)

    def test_get_learnings_for_goal(self):
        self.learner.extract_success_pattern("g1", "P1")
        self.learner.analyze_failure("g1", "F1")
        self.learner.extract_success_pattern("g2", "P2")

        g1_learnings = self.learner.get_learnings_for_goal("g1")
        assert len(g1_learnings) == 2

    def test_get_by_type(self):
        self.learner.extract_success_pattern("g1", "P1")
        self.learner.analyze_failure("g1", "F1")
        successes = self.learner.get_by_type(LearningType.SUCCESS_PATTERN)
        assert len(successes) == 1

    def test_get_record(self):
        r = self.learner.extract_success_pattern("g1", "Test")
        found = self.learner.get_record(r.record_id)
        assert found == r
        assert self.learner.get_record("invalid") is None

    def test_get_anti_patterns(self):
        self.learner.analyze_failure("g1", "F1")
        anti = self.learner.get_anti_patterns()
        assert len(anti) == 1

    def test_properties(self):
        self.learner.extract_success_pattern("g1", "P1")
        self.learner.analyze_failure("g1", "F1")
        assert self.learner.total_records == 2


# ── ProactiveScanner Testleri ───────────────────────────────────


class TestProactiveScanner:
    """ProactiveScanner testleri."""

    def setup_method(self):
        self.scanner = ProactiveScanner()

    def test_scan_environment(self):
        result = self.scanner.scan_environment(
            "market", {"price": 100},
        )
        assert result["domain"] == "market"

    def test_scan_with_watcher(self):
        self.scanner.add_watcher(
            "w1", "market",
            condition=lambda d: d.get("price", 0) > 50,
            watcher_type="warning",
            message="Fiyat yüksek",
        )
        result = self.scanner.scan_environment(
            "market", {"price": 100},
        )
        assert len(result["findings"]) == 1

    def test_detect_opportunity(self):
        scan = self.scanner.detect_opportunity(
            "Yeni pazar",
            OpportunityType.MARKET,
            estimated_value=5000,
            urgency=0.8,
        )
        assert scan.title == "Yeni pazar"
        assert self.scanner.opportunity_count == 1

    def test_detect_threat(self):
        threat = self.scanner.detect_threat(
            "Rakip saldırısı",
            severity=0.8, probability=0.6,
            mitigation=["Fiyat düşür"],
        )
        assert threat["risk_score"] == pytest.approx(0.48, abs=0.01)
        assert self.scanner.threat_count == 1

    def test_analyze_trend(self):
        trend = self.scanner.analyze_trend(
            "Satış artışı", "up", 0.7,
            data_points=[100, 110, 120],
        )
        assert trend["direction"] == "up"
        assert self.scanner.trend_count == 1

    def test_generate_recommendation(self):
        rec = self.scanner.generate_recommendation(
            "Pazar genişlet", "Yeni bölgelere gir",
            priority="high",
            action_items=["Araştırma yap"],
        )
        assert rec["priority"] == "high"
        assert self.scanner.recommendation_count == 1

    def test_add_remove_watcher(self):
        self.scanner.add_watcher("w1", "market")
        assert self.scanner.watcher_count == 1
        assert self.scanner.remove_watcher("w1")
        assert self.scanner.watcher_count == 0
        assert not self.scanner.remove_watcher("invalid")

    def test_get_opportunities_filtered(self):
        self.scanner.detect_opportunity(
            "Low", OpportunityType.MARKET, estimated_value=100,
        )
        self.scanner.detect_opportunity(
            "High", OpportunityType.GROWTH, estimated_value=5000,
        )
        high = self.scanner.get_opportunities(min_value=1000)
        assert len(high) == 1
        market = self.scanner.get_opportunities(
            opportunity_type=OpportunityType.MARKET,
        )
        assert len(market) == 1

    def test_get_threats_filtered(self):
        self.scanner.detect_threat("Low", severity=0.1, probability=0.1)
        self.scanner.detect_threat("High", severity=0.9, probability=0.9)
        high = self.scanner.get_threats(min_risk=0.5)
        assert len(high) == 1

    def test_get_trends(self):
        self.scanner.analyze_trend("T1", "up", 0.5)
        assert len(self.scanner.get_trends()) == 1

    def test_get_recommendations_filtered(self):
        self.scanner.generate_recommendation("R1", "D1")
        all_recs = self.scanner.get_recommendations()
        assert len(all_recs) == 1
        pending = self.scanner.get_recommendations(status="pending")
        assert len(pending) == 1

    def test_get_scan(self):
        scan = self.scanner.detect_opportunity(
            "Test", OpportunityType.GROWTH,
        )
        assert self.scanner.get_scan(scan.scan_id) is not None
        assert self.scanner.get_scan("invalid") is None

    def test_watcher_wildcard(self):
        self.scanner.add_watcher(
            "w1", "*",
            condition=lambda d: True,
            message="Catch all",
        )
        result = self.scanner.scan_environment("anything", {})
        assert len(result["findings"]) == 1


# ── UserAligner Testleri ────────────────────────────────────────


class TestUserAligner:
    """UserAligner testleri."""

    def setup_method(self):
        self.aligner = UserAligner()

    def test_learn_preference(self):
        self.aligner.learn_preference("domain", "tech")
        assert self.aligner.get_preference("domain") == "tech"
        assert self.aligner.preference_count == 1

    def test_get_preference_default(self):
        assert self.aligner.get_preference("missing", "default") == "default"

    def test_get_all_preferences(self):
        self.aligner.learn_preference("a", 1)
        self.aligner.learn_preference("b", 2)
        prefs = self.aligner.get_all_preferences()
        assert len(prefs) == 2

    def test_set_boundary(self):
        self.aligner.set_boundary(
            "budget", "Maks bütçe", True,
            conditions={"cost": 10000},
        )
        assert self.aligner.boundary_count == 1

    def test_remove_boundary(self):
        self.aligner.set_boundary("test", "Test")
        assert self.aligner.remove_boundary("test")
        assert not self.aligner.remove_boundary("invalid")

    def test_check_boundaries_pass(self):
        self.aligner.set_boundary(
            "budget", conditions={"cost": 10000},
        )
        result = self.aligner.check_boundaries({"cost": 5000})
        assert result["passed"]

    def test_check_boundaries_violation(self):
        self.aligner.set_boundary(
            "budget", hard_limit=True,
            conditions={"cost": 10000},
        )
        result = self.aligner.check_boundaries({"cost": 15000})
        assert not result["passed"]
        assert len(result["violations"]) == 1

    def test_check_boundaries_warning(self):
        self.aligner.set_boundary(
            "budget", hard_limit=False,
            conditions={"cost": 10000},
        )
        result = self.aligner.check_boundaries({"cost": 15000})
        assert result["passed"]
        assert len(result["warnings"]) == 1

    def test_suggest_goal(self):
        suggestion = self.aligner.suggest_goal(
            "g1", "Test Goal",
            rationale="ROI yüksek",
        )
        assert suggestion["status"] == "pending"
        assert self.aligner.suggestion_count == 1
        assert self.aligner.pending_approvals == 1

    def test_approve_goal(self):
        self.aligner.suggest_goal("g1", "Test")
        assert self.aligner.approve_goal("g1")
        assert self.aligner.is_approved("g1") is True
        assert self.aligner.pending_approvals == 0

    def test_reject_goal(self):
        self.aligner.suggest_goal("g1", "Test")
        assert self.aligner.reject_goal("g1", "Uygun değil")
        assert self.aligner.is_approved("g1") is False

    def test_is_approved_pending(self):
        assert self.aligner.is_approved("unknown") is None

    def test_add_feedback(self):
        fb = self.aligner.add_feedback(
            "suggestion", "Güzel fikir",
            goal_id="g1", sentiment="positive",
        )
        assert fb["sentiment"] == "positive"
        assert self.aligner.feedback_count == 1

    def test_calculate_alignment_strong(self):
        self.aligner.learn_preference("domain", "tech")
        self.aligner.learn_preference("budget", 5000)
        level = self.aligner.calculate_alignment({
            "domain": "tech", "budget": 5000,
        })
        assert level == AlignmentLevel.STRONG

    def test_calculate_alignment_misaligned(self):
        self.aligner.set_boundary(
            "limit", hard_limit=True,
            conditions={"cost": 100},
        )
        level = self.aligner.calculate_alignment({"cost": 500})
        assert level == AlignmentLevel.MISALIGNED

    def test_calculate_alignment_neutral(self):
        level = self.aligner.calculate_alignment({"x": 1})
        assert level == AlignmentLevel.NEUTRAL

    def test_get_approval_queue(self):
        self.aligner.suggest_goal("g1", "T1")
        self.aligner.suggest_goal("g2", "T2")
        queue = self.aligner.get_approval_queue()
        assert len(queue) == 2

    def test_get_suggestions_filtered(self):
        self.aligner.suggest_goal("g1", "T1")
        self.aligner.approve_goal("g1")
        approved = self.aligner.get_suggestions(status="approved")
        assert len(approved) == 1

    def test_get_feedback_filtered(self):
        self.aligner.add_feedback("suggestion", "Good", sentiment="positive")
        self.aligner.add_feedback("rejection", "Bad", sentiment="negative")
        suggestions = self.aligner.get_feedback(feedback_type="suggestion")
        assert len(suggestions) == 1


# ── GoalPursuitEngine Testleri ──────────────────────────────────


class TestGoalPursuitEngine:
    """GoalPursuitEngine testleri."""

    def setup_method(self):
        self.engine = GoalPursuitEngine(
            max_autonomous_goals=3,
            require_approval=True,
            value_threshold=0.3,
        )

    def test_discover_and_propose(self):
        result = self.engine.discover_and_propose(
            OpportunityType.GROWTH,
            "Yeni ürün",
            estimated_value=5000,
        )
        assert result["success"]
        assert result["needs_approval"]
        assert "goal_id" in result

    def test_approve_and_launch(self):
        result = self.engine.discover_and_propose(
            OpportunityType.GROWTH, "Test",
            estimated_value=1000,
        )
        goal_id = result["goal_id"]

        launch = self.engine.approve_and_launch(
            goal_id,
            resources=["dev1"],
            milestones=["M1", "M2"],
            timeline_days=30,
        )
        assert launch["success"]
        assert self.engine.active_goal_count == 1

    def test_max_capacity(self):
        for i in range(3):
            r = self.engine.discover_and_propose(
                OpportunityType.GROWTH, f"G{i}",
                estimated_value=1000,
            )
            self.engine.approve_and_launch(r["goal_id"])

        r = self.engine.discover_and_propose(
            OpportunityType.GROWTH, "Extra",
            estimated_value=1000,
        )
        result = self.engine.approve_and_launch(r["goal_id"])
        assert not result["success"]
        assert "Maks" in result["reason"]

    def test_approve_nonexistent(self):
        result = self.engine.approve_and_launch("invalid")
        assert not result["success"]

    def test_update_progress(self):
        r = self.engine.discover_and_propose(
            OpportunityType.GROWTH, "Test",
            estimated_value=1000,
        )
        self.engine.approve_and_launch(
            r["goal_id"], milestones=["M1"],
        )
        result = self.engine.update_progress(r["goal_id"], 0.5)
        assert result["progress"] == 0.5

    def test_evaluate_goal(self):
        r = self.engine.discover_and_propose(
            OpportunityType.GROWTH, "Test",
            estimated_value=1000,
        )
        self.engine.approve_and_launch(r["goal_id"])
        self.engine.update_progress(r["goal_id"], 0.5)

        evaluation = self.engine.evaluate_goal(r["goal_id"])
        assert evaluation["progress"] == 0.5

    def test_evaluate_no_data(self):
        result = self.engine.evaluate_goal("invalid")
        assert result["status"] == "no_data"

    def test_complete_goal(self):
        r = self.engine.discover_and_propose(
            OpportunityType.GROWTH, "Test",
            estimated_value=1000,
        )
        self.engine.approve_and_launch(r["goal_id"])
        self.engine.update_progress(r["goal_id"], 1.0)

        result = self.engine.complete_goal(r["goal_id"])
        assert result["success"]
        assert self.engine.active_goal_count == 0

    def test_abandon_goal(self):
        r = self.engine.discover_and_propose(
            OpportunityType.GROWTH, "Test",
            estimated_value=1000,
        )
        self.engine.approve_and_launch(r["goal_id"])

        result = self.engine.abandon_goal(
            r["goal_id"], "Bütçe yetersiz",
        )
        assert result["success"]
        assert self.engine.active_goal_count == 0

    def test_escalate(self):
        r = self.engine.discover_and_propose(
            OpportunityType.GROWTH, "Test",
            estimated_value=1000,
        )
        self.engine.approve_and_launch(r["goal_id"])

        esc = self.engine.escalate(
            r["goal_id"], "Kaynak yetersiz", "high",
        )
        assert esc["success"]
        assert self.engine.escalation_count == 1

    def test_scan_and_discover(self):
        result = self.engine.scan_and_discover()
        assert "opportunities" in result
        assert "threats" in result

    def test_get_snapshot(self):
        snap = self.engine.get_snapshot()
        assert snap.total_goals == 0
        assert snap.active_goals == 0
        assert snap.success_rate == 0.0

    def test_snapshot_with_data(self):
        r = self.engine.discover_and_propose(
            OpportunityType.GROWTH, "Test",
            estimated_value=1000,
        )
        self.engine.approve_and_launch(r["goal_id"])
        snap = self.engine.get_snapshot()
        assert snap.total_goals >= 1
        assert snap.active_goals == 1

    def test_subsystem_properties(self):
        assert self.engine.generator is not None
        assert self.engine.estimator is not None
        assert self.engine.selector is not None
        assert self.engine.launcher is not None
        assert self.engine.evaluator is not None
        assert self.engine.learner is not None
        assert self.engine.scanner is not None
        assert self.engine.aligner is not None


# ── Entegrasyon Testleri ────────────────────────────────────────


class TestGoalPursuitIntegration:
    """Entegrasyon testleri."""

    def test_full_lifecycle(self):
        """Tam hedef yasam dongusu."""
        engine = GoalPursuitEngine(
            max_autonomous_goals=5,
            require_approval=True,
        )

        # 1. Kesfet ve oner
        result = engine.discover_and_propose(
            OpportunityType.MARKET,
            "E-ticaret genişleme",
            estimated_value=10000,
            source="pazar_taramasi",
        )
        assert result["success"]
        goal_id = result["goal_id"]

        # 2. Onayla ve baslat
        launch = engine.approve_and_launch(
            goal_id,
            resources=["dev1", "marketing"],
            milestones=["Araştırma", "Prototip", "Lansman"],
            timeline_days=90,
        )
        assert launch["success"]

        # 3. Ilerleme guncelle
        engine.update_progress(goal_id, 0.3)
        engine.update_progress(goal_id, 0.6)
        engine.update_progress(goal_id, 0.9)

        # 4. Degerlendir
        evaluation = engine.evaluate_goal(goal_id)
        assert evaluation["progress"] == 0.9

        # 5. Tamamla
        complete = engine.complete_goal(goal_id)
        assert complete["success"]

        # 6. Snapshot kontrol
        snap = engine.get_snapshot()
        assert snap.total_learnings >= 1

    def test_multi_goal_management(self):
        """Coklu hedef yonetimi."""
        engine = GoalPursuitEngine(max_autonomous_goals=3)

        goals = []
        for i in range(3):
            r = engine.discover_and_propose(
                OpportunityType.GROWTH,
                f"Hedef {i + 1}",
                estimated_value=1000 * (i + 1),
            )
            engine.approve_and_launch(r["goal_id"])
            goals.append(r["goal_id"])

        assert engine.active_goal_count == 3

        # Birini tamamla
        engine.update_progress(goals[0], 1.0)
        engine.complete_goal(goals[0])
        assert engine.active_goal_count == 2

        # Birini terk et
        engine.abandon_goal(goals[1], "Düşük ROI")
        assert engine.active_goal_count == 1

    def test_learning_from_outcomes(self):
        """Sonuclardan ogrenme."""
        engine = GoalPursuitEngine()

        # Basarili hedef
        r1 = engine.discover_and_propose(
            OpportunityType.GROWTH, "Başarılı",
            estimated_value=5000,
        )
        engine.approve_and_launch(r1["goal_id"])
        engine.update_progress(r1["goal_id"], 1.0)
        engine.complete_goal(r1["goal_id"])

        # Basarisiz hedef
        r2 = engine.discover_and_propose(
            OpportunityType.MARKET, "Başarısız",
            estimated_value=3000,
        )
        engine.approve_and_launch(r2["goal_id"])
        engine.abandon_goal(r2["goal_id"], "Pazar uyumsuz")

        # Ogrenimler kontrol
        assert engine.learner.total_records >= 2

    def test_proactive_scanning_cycle(self):
        """Proaktif tarama dongusu."""
        engine = GoalPursuitEngine(value_threshold=100)

        # Firsat ekle
        engine.scanner.detect_opportunity(
            "Yeni pazar", OpportunityType.MARKET,
            estimated_value=5000,
        )
        engine.scanner.detect_threat(
            "Rakip", severity=0.5, probability=0.3,
        )

        result = engine.scan_and_discover()
        assert result["opportunities"] >= 1

    def test_user_alignment_workflow(self):
        """Kullanici hizalama akisi."""
        engine = GoalPursuitEngine(require_approval=True)

        # Tercih ogren
        engine.aligner.learn_preference("domain", "tech")
        engine.aligner.set_boundary(
            "budget", hard_limit=True,
            conditions={"cost": 50000},
        )

        # Hedef oner
        r = engine.discover_and_propose(
            OpportunityType.GROWTH, "AI projesi",
            estimated_value=20000,
        )
        assert r["needs_approval"]

        # Onayla
        engine.approve_and_launch(r["goal_id"])
        assert engine.active_goal_count == 1

    def test_escalation_flow(self):
        """Eskalasyon akisi."""
        engine = GoalPursuitEngine()

        r = engine.discover_and_propose(
            OpportunityType.GROWTH, "Zor hedef",
            estimated_value=50000,
        )
        engine.approve_and_launch(r["goal_id"])

        # Sorun çıktı - eskale et
        esc = engine.escalate(
            r["goal_id"],
            "Bütçe aşımı riski",
            "critical",
        )
        assert esc["success"]
        assert esc["severity"] == "critical"
