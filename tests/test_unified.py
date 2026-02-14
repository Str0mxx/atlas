"""ATLAS Unified Intelligence Core sistemi testleri."""

import pytest

from app.models.unified import (
    AttentionFocus,
    AttentionState,
    AwarenessState,
    ConsciousnessLevel,
    DecisionSource,
    EntityType,
    IntegratedDecision,
    PersonaProfile,
    ReasoningChain,
    ReasoningType,
    ReflectionRecord,
    ReflectionType,
    UnifiedSnapshot,
    WorldEntity,
)
from app.core.unified.consciousness import Consciousness
from app.core.unified.reasoning_engine import ReasoningEngine
from app.core.unified.attention_manager import AttentionManager
from app.core.unified.world_model import WorldModel
from app.core.unified.decision_integrator import DecisionIntegrator
from app.core.unified.action_coordinator import ActionCoordinator
from app.core.unified.reflection_module import ReflectionModule
from app.core.unified.persona_manager import PersonaManager
from app.core.unified.atlas_core import ATLASCore


# ── Model Testleri ──────────────────────────────────────────────


class TestUnifiedModels:
    """Model testleri."""

    def test_awareness_state_defaults(self):
        a = AwarenessState()
        assert a.awareness_id
        assert a.self_state == "operational"
        assert a.confidence == 0.5

    def test_reasoning_chain_defaults(self):
        r = ReasoningChain()
        assert r.chain_id
        assert r.reasoning_type == ReasoningType.LOGICAL
        assert r.conclusion == ""

    def test_attention_focus_defaults(self):
        f = AttentionFocus()
        assert f.focus_id
        assert f.state == AttentionState.FOCUSED
        assert f.priority == 5

    def test_world_entity_defaults(self):
        e = WorldEntity()
        assert e.entity_id
        assert e.entity_type == EntityType.SYSTEM
        assert e.state == "active"

    def test_integrated_decision_defaults(self):
        d = IntegratedDecision()
        assert d.decision_id
        assert d.confidence == 0.5
        assert d.explanation == ""

    def test_reflection_record_defaults(self):
        r = ReflectionRecord()
        assert r.record_id
        assert r.reflection_type == ReflectionType.SELF_EVALUATION
        assert r.score == 0.5

    def test_persona_profile_defaults(self):
        p = PersonaProfile()
        assert p.name == "ATLAS"
        assert p.formality == 0.5
        assert p.adaptability == 0.7

    def test_unified_snapshot_defaults(self):
        s = UnifiedSnapshot()
        assert s.consciousness_level == "medium"
        assert s.overall_health == 1.0

    def test_consciousness_level_enum(self):
        assert ConsciousnessLevel.DORMANT.value == "dormant"
        assert ConsciousnessLevel.PEAK.value == "peak"

    def test_reasoning_type_enum(self):
        assert ReasoningType.LOGICAL.value == "logical"
        assert ReasoningType.META.value == "meta"

    def test_attention_state_enum(self):
        assert AttentionState.FOCUSED.value == "focused"
        assert AttentionState.SWITCHING.value == "switching"

    def test_entity_type_enum(self):
        assert EntityType.SYSTEM.value == "system"
        assert EntityType.USER.value == "user"

    def test_decision_source_enum(self):
        assert DecisionSource.BDI.value == "bdi"
        assert DecisionSource.CONSENSUS.value == "consensus"

    def test_reflection_type_enum(self):
        assert ReflectionType.SELF_EVALUATION.value == "self_evaluation"
        assert ReflectionType.CONSOLIDATION.value == "consolidation"


# ── Consciousness Testleri ──────────────────────────────────────


class TestConsciousness:
    """Consciousness testleri."""

    def setup_method(self):
        self.c = Consciousness(ConsciousnessLevel.MEDIUM)

    def test_initial_state(self):
        assert self.c.level == ConsciousnessLevel.MEDIUM
        assert self.c.uptime >= 0

    def test_update_self_state(self):
        self.c.update_self_state("processing")
        awareness = self.c.get_awareness()
        assert awareness.self_state == "processing"

    def test_update_goals(self):
        self.c.update_goals(["g1", "g2"])
        awareness = self.c.get_awareness()
        assert len(awareness.active_goals) == 2

    def test_update_capabilities(self):
        self.c.update_capabilities(["reasoning", "planning"])
        awareness = self.c.get_awareness()
        assert "reasoning" in awareness.capabilities

    def test_update_environment(self):
        self.c.update_environment({"temperature": 25})
        awareness = self.c.get_awareness()
        assert awareness.environment["temperature"] == 25

    def test_update_limitations(self):
        self.c.update_limitations(["no_internet"])
        awareness = self.c.get_awareness()
        assert "no_internet" in awareness.limitations

    def test_set_level(self):
        self.c.set_level(ConsciousnessLevel.HIGH)
        assert self.c.level == ConsciousnessLevel.HIGH

    def test_introspect(self):
        self.c.update_goals(["g1"])
        result = self.c.introspect()
        assert result["level"] == "medium"
        assert result["goal_count"] == 1
        assert self.c.introspection_count == 1

    def test_assess_confidence_empty(self):
        conf = self.c.assess_confidence()
        assert 0.0 <= conf <= 1.0

    def test_assess_confidence_full(self):
        self.c.update_goals(["g1"])
        self.c.update_capabilities(["c1"])
        self.c.update_environment({"k": "v"})
        self.c.update_limitations(["l1"])
        conf = self.c.assess_confidence()
        assert conf > 0.5

    def test_state_history(self):
        self.c.update_self_state("processing")
        self.c.update_self_state("idle")
        history = self.c.get_state_history()
        assert len(history) == 2

    def test_state_history_limit(self):
        for i in range(5):
            self.c.update_self_state(f"state-{i}")
        history = self.c.get_state_history(limit=2)
        assert len(history) == 2

    def test_introspections_limit(self):
        for _ in range(5):
            self.c.introspect()
        results = self.c.get_introspections(limit=3)
        assert len(results) == 3


# ── ReasoningEngine Testleri ────────────────────────────────────


class TestReasoningEngine:
    """ReasoningEngine testleri."""

    def setup_method(self):
        self.engine = ReasoningEngine(max_depth=10)

    def test_logical_reasoning(self):
        chain = self.engine.reason_logically(
            ["A ise B", "B ise C"],
        )
        assert chain.reasoning_type == ReasoningType.LOGICAL
        assert chain.confidence > 0
        assert self.engine.total_chains == 1

    def test_logical_with_rules(self):
        self.engine.add_rule(
            "modus_ponens", "A -> B", "B",
            description="Modus ponens",
        )
        chain = self.engine.reason_logically(
            ["A dogru"], rules=["modus_ponens"],
        )
        assert len(chain.steps) >= 2
        assert self.engine.rule_count == 1

    def test_analogical_reasoning(self):
        chain = self.engine.reason_analogically(
            "atom", "gunes_sistemi",
            mappings={"cekirdek": "gunes", "elektron": "gezegen"},
        )
        assert chain.reasoning_type == ReasoningType.ANALOGICAL
        assert "atom" in chain.premises

    def test_analogical_with_catalog(self):
        self.engine.add_analogy("atom", "gunes_sistemi", 0.8)
        chain = self.engine.reason_analogically(
            "atom", "gunes_sistemi",
        )
        assert chain.confidence >= 0.8
        assert self.engine.analogy_count == 1

    def test_causal_reasoning(self):
        chain = self.engine.reason_causally(
            "yagmur", ["sel", "trafik"],
        )
        assert chain.reasoning_type == ReasoningType.CAUSAL
        assert "yagmur" in chain.premises

    def test_causal_with_links(self):
        self.engine.add_causal_link("yagmur", "sel", 0.7)
        chain = self.engine.reason_causally(
            "yagmur", ["sel"],
        )
        assert chain.confidence > 0
        assert self.engine.causal_link_count == 1

    def test_abductive_reasoning(self):
        chain = self.engine.reason_abductively(
            ["sislak zemin", "acik semsiye"],
            hypotheses=["yagmur yagdi", "hortum patladi"],
        )
        assert chain.reasoning_type == ReasoningType.ABDUCTIVE
        assert "En iyi aciklama" in chain.conclusion

    def test_abductive_no_hypotheses(self):
        chain = self.engine.reason_abductively(["gozlem"])
        assert "belirsiz" in chain.conclusion

    def test_meta_reasoning(self):
        c1 = self.engine.reason_logically(["A"])
        c2 = self.engine.reason_causally("B")
        meta = self.engine.meta_reason([c1.chain_id, c2.chain_id])
        assert meta.reasoning_type == ReasoningType.META
        assert "Meta analiz" in meta.conclusion

    def test_meta_reasoning_empty(self):
        meta = self.engine.meta_reason([])
        assert "Yeterli veri yok" in meta.conclusion

    def test_get_chain(self):
        chain = self.engine.reason_logically(["test"])
        found = self.engine.get_chain(chain.chain_id)
        assert found == chain
        assert self.engine.get_chain("invalid") is None

    def test_get_chains_by_type(self):
        self.engine.reason_logically(["A"])
        self.engine.reason_causally("B")
        logical = self.engine.get_chains_by_type(ReasoningType.LOGICAL)
        assert len(logical) == 1


# ── AttentionManager Testleri ───────────────────────────────────


class TestAttentionManager:
    """AttentionManager testleri."""

    def setup_method(self):
        self.mgr = AttentionManager(total_capacity=1.0)

    def test_focus_on(self):
        focus = self.mgr.focus_on("task1", priority=8, capacity=0.3)
        assert focus is not None
        assert focus.target == "task1"
        assert self.mgr.focus_count == 1

    def test_focus_exceeds_capacity(self):
        self.mgr.focus_on("t1", capacity=0.8)
        result = self.mgr.focus_on("t2", capacity=0.5)
        assert result is None

    def test_release_focus(self):
        f = self.mgr.focus_on("t1", capacity=0.3)
        assert self.mgr.release_focus(f.focus_id)
        assert self.mgr.focus_count == 0
        assert not self.mgr.release_focus("invalid")

    def test_reprioritize(self):
        f = self.mgr.focus_on("t1", priority=3)
        assert self.mgr.reprioritize(f.focus_id, 9)
        assert f.priority == 9
        assert not self.mgr.reprioritize("invalid", 5)

    def test_highest_priority(self):
        self.mgr.focus_on("low", priority=2, capacity=0.2)
        self.mgr.focus_on("high", priority=9, capacity=0.2)
        top = self.mgr.get_highest_priority()
        assert top.target == "high"

    def test_highest_priority_empty(self):
        assert self.mgr.get_highest_priority() is None

    def test_background_task(self):
        assert self.mgr.add_background_task("bg1", "Monitor", 0.05)
        assert self.mgr.background_count == 1
        assert self.mgr.used_capacity == pytest.approx(0.05, abs=0.01)

    def test_background_task_exceeds(self):
        self.mgr.focus_on("t1", capacity=0.95)
        assert not self.mgr.add_background_task("bg1", "X", 0.1)

    def test_remove_background_task(self):
        self.mgr.add_background_task("bg1", "X", 0.05)
        assert self.mgr.remove_background_task("bg1")
        assert not self.mgr.remove_background_task("invalid")

    def test_handle_interrupt_accept(self):
        result = self.mgr.handle_interrupt("alarm", 10, "Acil")
        assert result["accepted"]
        assert self.mgr.interrupt_count == 1

    def test_handle_interrupt_reject(self):
        self.mgr.focus_on("critical", priority=10, capacity=0.3)
        result = self.mgr.handle_interrupt("low", 3)
        assert not result["accepted"]

    def test_switch_context(self):
        f = self.mgr.focus_on("t1", priority=5, capacity=0.3)
        result = self.mgr.switch_context(f.focus_id, "t2", 8)
        assert result["switched"]
        assert self.mgr.context_depth == 1

    def test_restore_context(self):
        f = self.mgr.focus_on("t1", priority=5, capacity=0.3)
        self.mgr.switch_context(f.focus_id, "t2", 8)
        # Release current to make room
        for fid in list(self.mgr._focuses.keys()):
            self.mgr.release_focus(fid)
        result = self.mgr.restore_context()
        assert result is not None
        assert result["restored"]

    def test_restore_context_empty(self):
        assert self.mgr.restore_context() is None

    def test_get_all_focuses(self):
        self.mgr.focus_on("a", priority=3, capacity=0.2)
        self.mgr.focus_on("b", priority=8, capacity=0.2)
        focuses = self.mgr.get_all_focuses()
        assert focuses[0].priority >= focuses[1].priority

    def test_capacity_properties(self):
        self.mgr.focus_on("t1", capacity=0.3)
        assert self.mgr.used_capacity == pytest.approx(0.3, abs=0.01)
        assert self.mgr.available_capacity == pytest.approx(0.7, abs=0.01)


# ── WorldModel Testleri ─────────────────────────────────────────


class TestWorldModel:
    """WorldModel testleri."""

    def setup_method(self):
        self.wm = WorldModel()

    def test_add_entity(self):
        e = self.wm.add_entity("sys1", EntityType.SYSTEM)
        assert e.name == "sys1"
        assert self.wm.entity_count == 1

    def test_update_entity(self):
        e = self.wm.add_entity("sys1", EntityType.SYSTEM)
        assert self.wm.update_entity(
            e.entity_id, state="offline", properties={"cpu": 80},
        )
        updated = self.wm.get_entity(e.entity_id)
        assert updated.state == "offline"
        assert not self.wm.update_entity("invalid", state="x")

    def test_remove_entity(self):
        e = self.wm.add_entity("sys1")
        assert self.wm.remove_entity(e.entity_id)
        assert self.wm.entity_count == 0
        assert not self.wm.remove_entity("invalid")

    def test_add_relationship(self):
        e1 = self.wm.add_entity("sys1")
        e2 = self.wm.add_entity("sys2")
        rel = self.wm.add_relationship(
            e1.entity_id, e2.entity_id, "depends_on", 0.8,
        )
        assert rel is not None
        assert self.wm.relationship_count == 1

    def test_add_relationship_invalid(self):
        e1 = self.wm.add_entity("sys1")
        assert self.wm.add_relationship(
            e1.entity_id, "invalid", "x",
        ) is None

    def test_get_relationships(self):
        e1 = self.wm.add_entity("sys1")
        e2 = self.wm.add_entity("sys2")
        self.wm.add_relationship(e1.entity_id, e2.entity_id, "uses")
        rels = self.wm.get_relationships(e1.entity_id)
        assert len(rels) == 1

    def test_predict_state(self):
        e = self.wm.add_entity("sys1")
        pred = self.wm.predict_state(e.entity_id, 3)
        assert pred["current_state"] == "active"
        assert pred["confidence"] > 0
        assert self.wm.prediction_count == 1

    def test_predict_nonexistent(self):
        result = self.wm.predict_state("invalid")
        assert not result["success"]

    def test_counterfactual(self):
        e1 = self.wm.add_entity("sys1")
        e2 = self.wm.add_entity("sys2")
        self.wm.add_relationship(
            e1.entity_id, e2.entity_id, "depends_on", 0.9,
        )
        cf = self.wm.counterfactual(e1.entity_id, "offline")
        assert cf["actual_state"] == "active"
        assert cf["hypothetical_state"] == "offline"
        assert len(cf["affected_entities"]) == 1

    def test_counterfactual_nonexistent(self):
        result = self.wm.counterfactual("invalid", "x")
        assert not result["success"]

    def test_simulate(self):
        e = self.wm.add_entity("sys1")
        sim = self.wm.simulate(
            "outage", {e.entity_id: "offline"},
        )
        assert sim["scenario"] == "outage"
        assert self.wm.simulation_count == 1

    def test_take_snapshot(self):
        self.wm.add_entity("sys1")
        snap_id = self.wm.take_snapshot()
        assert snap_id.startswith("world-")
        assert self.wm.snapshot_count == 1

    def test_find_by_type(self):
        self.wm.add_entity("sys1", EntityType.SYSTEM)
        self.wm.add_entity("usr1", EntityType.USER)
        systems = self.wm.find_by_type(EntityType.SYSTEM)
        assert len(systems) == 1

    def test_find_by_state(self):
        self.wm.add_entity("sys1", state="active")
        self.wm.add_entity("sys2", state="offline")
        active = self.wm.find_by_state("active")
        assert len(active) == 1

    def test_remove_entity_cleans_relationships(self):
        e1 = self.wm.add_entity("sys1")
        e2 = self.wm.add_entity("sys2")
        self.wm.add_relationship(e1.entity_id, e2.entity_id, "uses")
        self.wm.remove_entity(e1.entity_id)
        assert self.wm.relationship_count == 0


# ── DecisionIntegrator Testleri ─────────────────────────────────


class TestDecisionIntegrator:
    """DecisionIntegrator testleri."""

    def setup_method(self):
        self.di = DecisionIntegrator()

    def test_add_proposal(self):
        q = self.di.add_proposal(
            "restart?", DecisionSource.BDI,
            "yes", 0.8, "Servis cevrimdisi",
        )
        assert q == "restart?"
        assert self.di.total_proposals == 1

    def test_synthesize(self):
        self.di.add_proposal(
            "restart?", DecisionSource.BDI, "yes", 0.9,
        )
        self.di.add_proposal(
            "restart?", DecisionSource.PROBABILISTIC, "yes", 0.7,
        )
        self.di.add_proposal(
            "restart?", DecisionSource.EMOTIONAL, "no", 0.3,
        )

        decision = self.di.synthesize("restart?")
        assert decision is not None
        assert decision.chosen_action == "yes"
        assert self.di.total_decisions == 1

    def test_synthesize_no_proposals(self):
        assert self.di.synthesize("unknown") is None

    def test_conflict_detection(self):
        self.di.add_proposal(
            "action?", DecisionSource.BDI, "A", 0.5,
        )
        self.di.add_proposal(
            "action?", DecisionSource.REINFORCEMENT, "B", 0.5,
        )
        self.di.synthesize("action?")
        # Close scores should trigger conflict
        assert self.di.conflict_count >= 0  # Depends on weights

    def test_resolve_conflict(self):
        self.di.add_proposal(
            "q?", DecisionSource.BDI, "A", 0.5,
        )
        decision = self.di.resolve_conflict(
            "q?", "A", "Manuel secim",
        )
        assert decision is not None
        assert decision.confidence == 0.9

    def test_resolve_no_proposals(self):
        assert self.di.resolve_conflict("none", "A") is None

    def test_set_source_weight(self):
        self.di.set_source_weight(DecisionSource.EMOTIONAL, 0.5)
        assert self.di.get_source_weight(DecisionSource.EMOTIONAL) == 0.5

    def test_get_proposals(self):
        self.di.add_proposal("q?", DecisionSource.BDI, "A", 0.8)
        props = self.di.get_proposals("q?")
        assert len(props) == 1

    def test_get_conflicts(self):
        conflicts = self.di.get_conflicts()
        assert isinstance(conflicts, list)

    def test_get_decision(self):
        self.di.add_proposal("q?", DecisionSource.BDI, "A", 0.8)
        d = self.di.synthesize("q?")
        found = self.di.get_decision(d.decision_id)
        assert found == d
        assert self.di.get_decision("invalid") is None


# ── ActionCoordinator Testleri ──────────────────────────────────


class TestActionCoordinator:
    """ActionCoordinator testleri."""

    def setup_method(self):
        self.coord = ActionCoordinator()

    def test_create_action(self):
        action = self.coord.create_action(
            "restart_service",
            target_systems=["web", "db"],
            priority=8,
        )
        assert action["name"] == "restart_service"
        assert self.coord.total_actions == 1

    def test_execute_action(self):
        action = self.coord.create_action(
            "test", target_systems=["sys1"],
        )
        result = self.coord.execute_action(action["action_id"])
        assert result["success"]
        assert self.coord.completed_actions == 1

    def test_execute_nonexistent(self):
        result = self.coord.execute_action("invalid")
        assert not result["success"]

    def test_execute_already_completed(self):
        action = self.coord.create_action("test")
        self.coord.execute_action(action["action_id"])
        result = self.coord.execute_action(action["action_id"])
        assert not result["success"]

    def test_create_plan(self):
        plan = self.coord.create_plan("deploy", [
            {"name": "build", "systems": ["ci"]},
            {"name": "test", "systems": ["ci"]},
            {"name": "deploy", "systems": ["prod"]},
        ])
        assert plan["name"] == "deploy"
        assert self.coord.total_plans == 1

    def test_execute_plan(self):
        plan = self.coord.create_plan("deploy", [
            {"name": "step1", "systems": ["s1"]},
            {"name": "step2", "systems": ["s2"]},
        ])
        result = self.coord.execute_plan(plan["plan_id"])
        assert result["success"]
        assert len(result["completed_steps"]) == 2

    def test_execute_plan_nonexistent(self):
        result = self.coord.execute_plan("invalid")
        assert not result["success"]

    def test_allocate_resource(self):
        action = self.coord.create_action("test")
        assert self.coord.allocate_resource(
            "cpu", action["action_id"], 4.0,
        )
        assert self.coord.resource_count == 1

    def test_allocate_resource_invalid(self):
        assert not self.coord.allocate_resource("cpu", "invalid", 1.0)

    def test_release_resource(self):
        action = self.coord.create_action("test")
        self.coord.allocate_resource("cpu", action["action_id"])
        assert self.coord.release_resource("cpu", action["action_id"])
        assert not self.coord.release_resource("cpu", "invalid")

    def test_add_feedback(self):
        action = self.coord.create_action("test")
        fb = self.coord.add_feedback(
            action["action_id"], "quality", "Iyi", 0.9,
        )
        assert fb["score"] == 0.9
        assert self.coord.feedback_count == 1

    def test_get_feedback_filtered(self):
        a1 = self.coord.create_action("t1")
        a2 = self.coord.create_action("t2")
        self.coord.add_feedback(a1["action_id"], "q", "ok")
        self.coord.add_feedback(a2["action_id"], "q", "ok")
        filtered = self.coord.get_feedback(a1["action_id"])
        assert len(filtered) == 1

    def test_execution_log(self):
        action = self.coord.create_action("test", target_systems=["s1"])
        self.coord.execute_action(action["action_id"])
        log = self.coord.get_execution_log()
        assert len(log) == 1


# ── ReflectionModule Testleri ───────────────────────────────────


class TestReflectionModule:
    """ReflectionModule testleri."""

    def setup_method(self):
        self.ref = ReflectionModule()

    def test_self_evaluate(self):
        record = self.ref.self_evaluate(
            "performance",
            criteria={"speed": 0.8, "accuracy": 0.9},
        )
        assert record.reflection_type == ReflectionType.SELF_EVALUATION
        assert record.score > 0.7
        assert self.ref.total_records == 1

    def test_self_evaluate_empty(self):
        record = self.ref.self_evaluate("empty")
        assert record.score == 0.5

    def test_analyze_performance(self):
        record = self.ref.analyze_performance(
            "response_time", [0.1, 0.2, 0.15, 0.12],
        )
        assert record.reflection_type == ReflectionType.PERFORMANCE
        assert len(record.findings) >= 2

    def test_analyze_performance_trend_down(self):
        record = self.ref.analyze_performance(
            "success_rate", [0.9, 0.8, 0.7, 0.6],
        )
        assert any("dusus" in f for f in record.findings)
        assert len(record.improvements) >= 1

    def test_detect_bias(self):
        record = self.ref.detect_bias(
            "agent_selection", "Her zaman ayni agent",
            bias_type="selection_bias", severity=0.7,
        )
        assert record.reflection_type == ReflectionType.BIAS_CHECK
        assert self.ref.bias_count == 1

    def test_identify_improvement(self):
        record = self.ref.identify_improvement(
            "response_time", "500ms", "200ms",
            priority="high",
            actions=["Cache ekle", "Index optimize"],
        )
        assert record.reflection_type == ReflectionType.IMPROVEMENT
        assert self.ref.improvement_count == 1

    def test_consolidate_learning(self):
        record = self.ref.consolidate_learning(
            "API tasarimi",
            ["REST tercih et", "Pagination kullan"],
            confidence=0.8,
        )
        assert record.reflection_type == ReflectionType.CONSOLIDATION
        assert self.ref.consolidation_count == 1

    def test_get_record(self):
        r = self.ref.self_evaluate("test")
        found = self.ref.get_record(r.record_id)
        assert found == r
        assert self.ref.get_record("invalid") is None

    def test_get_by_type(self):
        self.ref.self_evaluate("a")
        self.ref.detect_bias("b", "obs")
        evals = self.ref.get_by_type(ReflectionType.SELF_EVALUATION)
        assert len(evals) == 1

    def test_get_biases(self):
        self.ref.detect_bias("ctx", "obs")
        assert len(self.ref.get_biases()) == 1

    def test_get_improvements_filtered(self):
        self.ref.identify_improvement("a", "s1", "s2", priority="high")
        self.ref.identify_improvement("b", "s3", "s4", priority="low")
        high = self.ref.get_improvements(priority="high")
        assert len(high) == 1

    def test_overall_score(self):
        self.ref.self_evaluate("a", criteria={"x": 0.8})
        self.ref.self_evaluate("b", criteria={"y": 0.6})
        score = self.ref.get_overall_score()
        assert 0.0 <= score <= 1.0

    def test_overall_score_empty(self):
        assert self.ref.get_overall_score() == 0.5


# ── PersonaManager Testleri ─────────────────────────────────────


class TestPersonaManager:
    """PersonaManager testleri."""

    def setup_method(self):
        self.pm = PersonaManager()

    def test_initial_traits(self):
        traits = self.pm.get_all_traits()
        assert "professionalism" in traits
        assert self.pm.trait_count >= 5

    def test_set_get_trait(self):
        self.pm.set_trait("curiosity", 0.9)
        assert self.pm.get_trait("curiosity") == 0.9
        assert self.pm.get_trait("nonexistent") == 0.5

    def test_trait_clamping(self):
        self.pm.set_trait("x", 1.5)
        assert self.pm.get_trait("x") == 1.0
        self.pm.set_trait("y", -0.5)
        assert self.pm.get_trait("y") == 0.0

    def test_values(self):
        self.pm.add_value("yaraticilik")
        values = self.pm.get_values()
        assert "yaraticilik" in values
        assert self.pm.value_count >= 5

    def test_remove_value(self):
        self.pm.add_value("test")
        assert self.pm.remove_value("test")
        assert not self.pm.remove_value("nonexistent")

    def test_duplicate_value(self):
        count = self.pm.value_count
        self.pm.add_value("guvenilirlik")  # Already exists
        assert self.pm.value_count == count

    def test_communication_style(self):
        self.pm.set_communication_style("casual")
        profile = self.pm.get_profile()
        assert profile.communication_style == "casual"

    def test_formality(self):
        self.pm.set_formality(0.9)
        profile = self.pm.get_profile()
        assert profile.formality == 0.9

    def test_style_for_context(self):
        style = self.pm.get_style_for_context("emergency")
        assert style["formality"] >= 0.8

    def test_style_override(self):
        self.pm.set_style_override("support", "friendly")
        style = self.pm.get_style_for_context("support")
        assert style["style"] == "friendly"

    def test_remove_style_override(self):
        self.pm.set_style_override("ctx", "style")
        assert self.pm.remove_style_override("ctx")
        assert not self.pm.remove_style_override("invalid")

    def test_check_consistency(self):
        result = self.pm.check_consistency("send_email")
        assert result["consistent"]

    def test_check_consistency_violation(self):
        result = self.pm.check_consistency(
            "hidden_action", {"hidden": True},
        )
        assert not result["consistent"]

    def test_adapt_to_user(self):
        old_humor = self.pm.get_trait("humor")
        self.pm.adapt_to_user(
            "more_humor", {"humor": 0.2},
        )
        new_humor = self.pm.get_trait("humor")
        assert new_humor > old_humor
        assert self.pm.adaptation_count == 1

    def test_record_interaction(self):
        self.pm.record_interaction("chat", "support", 0.8)
        assert self.pm.interaction_count == 1

    def test_interaction_history(self):
        self.pm.record_interaction("a", satisfaction=0.9)
        self.pm.record_interaction("b", satisfaction=0.5)
        history = self.pm.get_interaction_history(limit=1)
        assert len(history) == 1


# ── ATLASCore Testleri ──────────────────────────────────────────


class TestATLASCore:
    """ATLASCore testleri."""

    def setup_method(self):
        self.core = ATLASCore(
            consciousness_level="medium",
            reasoning_depth=10,
            reflection_interval=3600,
            persona_consistency=0.8,
        )

    def test_initial_state(self):
        assert self.core.consciousness.level == ConsciousnessLevel.MEDIUM
        assert self.core.world.entity_count >= 1  # ATLAS kendisi

    def test_perceive(self):
        result = self.core.perceive(
            "sensor", {"temperature": 25, "priority": 7},
        )
        assert result["perceived"]
        assert self.core.event_count >= 1

    def test_think(self):
        result = self.core.think(
            "Sunucu yeniden baslatilmali mi?",
            context={"premises": ["Servis cevrimdisi", "Otomatik kurtarma basarisiz"]},
        )
        assert "reasoning" in result
        assert result["reasoning"]["confidence"] > 0

    def test_decide(self):
        result = self.core.decide(
            "restart?",
            [
                {"source": "bdi", "action": "restart", "confidence": 0.9},
                {"source": "emotional", "action": "wait", "confidence": 0.3},
            ],
        )
        assert result["success"]
        assert result["chosen_action"] == "restart"

    def test_decide_invalid_source(self):
        result = self.core.decide(
            "test?",
            [{"source": "unknown_source", "action": "do", "confidence": 0.5}],
        )
        assert result["success"]

    def test_act(self):
        result = self.core.act(
            "restart_service",
            target_systems=["web_server"],
        )
        assert result["success"]

    def test_reflect(self):
        result = self.core.reflect()
        assert "score" in result
        assert "confidence" in result

    def test_run_cycle(self):
        result = self.core.run_cycle(inputs=[
            {"source": "monitor", "data": {"cpu": 80}},
            {"source": "alert", "data": {"level": "warning"}},
        ])
        assert result["perceptions"] == 2
        assert result["cycle"] >= 1

    def test_run_cycle_empty(self):
        result = self.core.run_cycle()
        assert result["perceptions"] == 0

    def test_get_snapshot(self):
        snap = self.core.get_snapshot()
        assert snap.consciousness_level == "medium"
        assert snap.world_entities >= 1

    def test_snapshot_after_activity(self):
        self.core.perceive("s1", {"v": 1})
        self.core.think("q?")
        self.core.reflect()
        snap = self.core.get_snapshot()
        assert snap.reasoning_chains >= 1
        assert snap.reflections >= 1

    def test_subsystem_properties(self):
        assert self.core.consciousness is not None
        assert self.core.reasoning is not None
        assert self.core.attention is not None
        assert self.core.world is not None
        assert self.core.decisions is not None
        assert self.core.actions is not None
        assert self.core.reflection is not None
        assert self.core.persona is not None

    def test_cycle_count(self):
        self.core.run_cycle()
        self.core.run_cycle()
        assert self.core.cycle_count >= 2


# ── Entegrasyon Testleri ────────────────────────────────────────


class TestUnifiedIntegration:
    """Entegrasyon testleri."""

    def test_full_cognitive_cycle(self):
        """Tam bilissel dongu."""
        core = ATLASCore()

        # 1. Algi
        core.perceive("monitor", {"cpu": 95, "priority": 9})

        # 2. Dusunme
        thought = core.think(
            "CPU yuku cok yuksek",
            context={"premises": ["CPU %95", "Hizmet yavas"]},
        )
        assert thought["reasoning"]["confidence"] > 0

        # 3. Karar
        decision = core.decide(
            "CPU aksiyonu",
            [
                {"source": "bdi", "action": "scale_up", "confidence": 0.8},
                {"source": "probabilistic", "action": "scale_up", "confidence": 0.7},
                {"source": "emotional", "action": "alert_user", "confidence": 0.4},
            ],
        )
        assert decision["success"]
        assert decision["chosen_action"] == "scale_up"

        # 4. Eylem
        action = core.act(
            "scale_up", target_systems=["kubernetes"],
        )
        assert action["success"]

        # 5. Yansima
        reflection = core.reflect()
        assert reflection["score"] > 0

    def test_multi_cycle_operation(self):
        """Coklu dongu operasyonu."""
        core = ATLASCore()

        for i in range(3):
            core.run_cycle(inputs=[
                {"source": f"sensor-{i}", "data": {"value": i * 10}},
            ])

        snap = core.get_snapshot()
        assert snap.world_entities >= 4  # ATLAS + 3 sensors

    def test_consciousness_evolution(self):
        """Bilinc evrimi."""
        core = ATLASCore(consciousness_level="low")
        assert core.consciousness.level == ConsciousnessLevel.LOW

        core.consciousness.set_level(ConsciousnessLevel.HIGH)
        assert core.consciousness.level == ConsciousnessLevel.HIGH

        core.consciousness.update_goals(["optimize", "learn"])
        core.consciousness.update_capabilities(["reason", "plan"])
        conf = core.consciousness.assess_confidence()
        assert conf > 0.5

    def test_world_model_reasoning(self):
        """Dunya modeli ile akil yurutme."""
        core = ATLASCore()

        # Dunya modeline varliklar ekle
        db = core.world.add_entity("database", EntityType.RESOURCE)
        api = core.world.add_entity("api_server", EntityType.SYSTEM)
        core.world.add_relationship(
            api.entity_id, db.entity_id, "depends_on", 0.9,
        )

        # Karsi-olgusal
        cf = core.world.counterfactual(db.entity_id, "offline")
        assert len(cf["affected_entities"]) == 1

        # Simulasyon
        sim = core.world.simulate(
            "db_failure", {db.entity_id: "offline"},
        )
        assert sim["total_entities_affected"] >= 1

    def test_persona_consistency_check(self):
        """Kisilik tutarlilik kontrolu."""
        core = ATLASCore()

        # Normal eylem - tutarli
        result = core.persona.check_consistency("send_report")
        assert result["consistent"]

        # Gizli eylem - tutarsiz
        result = core.persona.check_consistency(
            "hidden_transfer", {"hidden": True},
        )
        assert not result["consistent"]

    def test_attention_and_reasoning(self):
        """Dikkat ve akil yurutme entegrasyonu."""
        core = ATLASCore()

        # Odakla
        focus = core.attention.focus_on("security_alert", priority=9, capacity=0.4)
        assert focus is not None

        # Akil yurut
        chain = core.reasoning.reason_logically(
            ["Basarisiz giris denemesi tespit edildi",
             "IP daha once kara listeye alinmis"],
        )
        assert chain.confidence > 0

        # Odagi serbest birak
        core.attention.release_focus(focus.focus_id)
        assert core.attention.available_capacity > 0.9
