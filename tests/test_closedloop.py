"""ATLAS Closed-Loop Execution Tracking testleri.

Aksiyon-sonuc-ogrenme dongusu bilesenlerini
kapsamli test suite.
"""

import time

import pytest


# ── Models ────────────────────────────────────

class TestClosedLoopModels:
    """Closed-loop model testleri."""

    def test_action_status_enum(self):
        from app.models.closedloop_models import ActionStatus
        assert ActionStatus.PENDING == "pending"
        assert ActionStatus.RUNNING == "running"
        assert ActionStatus.COMPLETED == "completed"
        assert ActionStatus.FAILED == "failed"
        assert ActionStatus.CANCELLED == "cancelled"

    def test_outcome_type_enum(self):
        from app.models.closedloop_models import OutcomeType
        assert OutcomeType.SUCCESS == "success"
        assert OutcomeType.FAILURE == "failure"
        assert OutcomeType.PARTIAL == "partial"
        assert OutcomeType.TIMEOUT == "timeout"
        assert OutcomeType.UNKNOWN == "unknown"

    def test_feedback_source_enum(self):
        from app.models.closedloop_models import FeedbackSource
        assert FeedbackSource.EXPLICIT == "explicit"
        assert FeedbackSource.IMPLICIT == "implicit"
        assert FeedbackSource.SYSTEM == "system"
        assert FeedbackSource.EXTERNAL == "external"
        assert FeedbackSource.AUTOMATED == "automated"

    def test_causal_confidence_enum(self):
        from app.models.closedloop_models import CausalConfidence
        assert CausalConfidence.HIGH == "high"
        assert CausalConfidence.MEDIUM == "medium"
        assert CausalConfidence.LOW == "low"
        assert CausalConfidence.UNCERTAIN == "uncertain"
        assert CausalConfidence.NONE == "none"

    def test_experiment_status_enum(self):
        from app.models.closedloop_models import ExperimentStatus
        assert ExperimentStatus.DRAFT == "draft"
        assert ExperimentStatus.RUNNING == "running"
        assert ExperimentStatus.PAUSED == "paused"
        assert ExperimentStatus.COMPLETED == "completed"
        assert ExperimentStatus.CANCELLED == "cancelled"

    def test_improvement_priority_enum(self):
        from app.models.closedloop_models import ImprovementPriority
        assert ImprovementPriority.CRITICAL == "critical"
        assert ImprovementPriority.HIGH == "high"
        assert ImprovementPriority.MEDIUM == "medium"
        assert ImprovementPriority.LOW == "low"
        assert ImprovementPriority.TRIVIAL == "trivial"

    def test_action_record(self):
        from app.models.closedloop_models import ActionRecord
        r = ActionRecord(name="test_action")
        assert r.name == "test_action"
        assert r.status.value == "pending"
        assert r.action_id
        assert r.context == {}
        assert r.parent_action_id == ""

    def test_outcome_record(self):
        from app.models.closedloop_models import OutcomeRecord
        r = OutcomeRecord(action_id="a1")
        assert r.action_id == "a1"
        assert r.outcome_type.value == "unknown"
        assert r.confidence == 0.0
        assert r.side_effects == []

    def test_experiment_record(self):
        from app.models.closedloop_models import ExperimentRecord
        r = ExperimentRecord(hypothesis="Test hyp")
        assert r.hypothesis == "Test hyp"
        assert r.status.value == "draft"
        assert r.duration_hours == 24
        assert r.variants == []

    def test_closedloop_snapshot(self):
        from app.models.closedloop_models import ClosedLoopSnapshot
        s = ClosedLoopSnapshot(total_actions=50, outcomes_detected=40)
        assert s.total_actions == 50
        assert s.outcomes_detected == 40
        assert s.learnings_count == 0
        assert s.improvements_applied == 0


# ── ActionTracker ─────────────────────────────

class TestActionTracker:
    """ActionTracker testleri."""

    def setup_method(self):
        from app.core.closedloop.action_tracker import ActionTracker
        self.tracker = ActionTracker()

    def test_register_action(self):
        r = self.tracker.register_action("a1", "test")
        assert r["action_id"] == "a1"
        assert r["status"] == "registered"
        assert self.tracker.action_count == 1

    def test_register_with_context(self):
        ctx = {"env": "production"}
        self.tracker.register_action("a1", "test", context=ctx)
        action = self.tracker.get_action("a1")
        assert action["context"]["env"] == "production"

    def test_start_action(self):
        self.tracker.register_action("a1", "test")
        r = self.tracker.start_action("a1")
        assert r["status"] == "running"
        action = self.tracker.get_action("a1")
        assert action["started_at"] is not None

    def test_start_nonexistent(self):
        r = self.tracker.start_action("nope")
        assert "error" in r

    def test_complete_action(self):
        self.tracker.register_action("a1", "test")
        self.tracker.start_action("a1")
        r = self.tracker.complete_action("a1", result={"ok": True})
        assert r["status"] == "completed"
        assert r["duration_ms"] >= 0

    def test_complete_nonexistent(self):
        r = self.tracker.complete_action("nope")
        assert "error" in r

    def test_fail_action(self):
        self.tracker.register_action("a1", "test")
        self.tracker.start_action("a1")
        r = self.tracker.fail_action("a1", error="timeout")
        assert r["status"] == "failed"
        assert r["error"] == "timeout"

    def test_fail_nonexistent(self):
        r = self.tracker.fail_action("nope")
        assert "error" in r

    def test_get_action(self):
        self.tracker.register_action("a1", "test")
        action = self.tracker.get_action("a1")
        assert action["name"] == "test"

    def test_get_action_none(self):
        assert self.tracker.get_action("nope") is None

    def test_action_chaining(self):
        self.tracker.register_action("parent", "main")
        self.tracker.register_action("child1", "sub1", parent_id="parent")
        self.tracker.register_action("child2", "sub2", parent_id="parent")
        chain = self.tracker.get_chain("parent")
        assert "child1" in chain
        assert "child2" in chain
        assert self.tracker.chain_count == 1

    def test_get_actions_by_status(self):
        self.tracker.register_action("a1", "t1")
        self.tracker.register_action("a2", "t2")
        self.tracker.start_action("a1")
        pending = self.tracker.get_actions_by_status("pending")
        assert len(pending) == 1
        running = self.tracker.get_actions_by_status("running")
        assert len(running) == 1

    def test_get_context(self):
        self.tracker.register_action("a1", "test", context={"key": "val"})
        ctx = self.tracker.get_context("a1")
        assert ctx["key"] == "val"

    def test_get_context_empty(self):
        ctx = self.tracker.get_context("nope")
        assert ctx == {}

    def test_execution_logs(self):
        self.tracker.register_action("a1", "test")
        self.tracker.start_action("a1")
        self.tracker.complete_action("a1")
        assert self.tracker.log_count >= 2

    def test_stats(self):
        self.tracker.register_action("a1", "t1")
        self.tracker.register_action("a2", "t2")
        self.tracker.start_action("a1")
        self.tracker.complete_action("a1")
        self.tracker.start_action("a2")
        self.tracker.fail_action("a2")
        assert self.tracker._stats["registered"] == 2
        assert self.tracker._stats["completed"] == 1
        assert self.tracker._stats["failed"] == 1


# ── OutcomeDetector ───────────────────────────

class TestOutcomeDetector:
    """OutcomeDetector testleri."""

    def setup_method(self):
        from app.core.closedloop.outcome_detector import OutcomeDetector
        self.detector = OutcomeDetector(detection_timeout=10)

    def test_detect_outcome(self):
        r = self.detector.detect_outcome("a1", "success")
        assert r["outcome_type"] == "success"
        assert r["action_id"] == "a1"
        assert self.detector.outcome_count == 1

    def test_detect_with_metrics(self):
        r = self.detector.detect_outcome(
            "a1", "success", metrics={"latency": 50}
        )
        assert r["confidence"] == 1.0

    def test_detect_failure(self):
        self.detector.detect_outcome("a1", "failure")
        assert self.detector._stats["failure"] == 1

    def test_check_metric_change_baseline(self):
        r = self.detector.check_metric_change("cpu", 50.0)
        assert r["changed"] is False
        assert r["reason"] == "baseline_set"

    def test_check_metric_change_detected(self):
        self.detector.set_baseline("cpu", 50.0)
        r = self.detector.check_metric_change("cpu", 60.0, threshold=0.1)
        assert r["changed"] is True
        assert r["direction"] == "up"

    def test_check_metric_no_change(self):
        self.detector.set_baseline("cpu", 50.0)
        r = self.detector.check_metric_change("cpu", 52.0, threshold=0.1)
        assert r["changed"] is False

    def test_check_metric_zero_baseline(self):
        self.detector.set_baseline("errors", 0.0)
        r = self.detector.check_metric_change("errors", 5.0)
        assert r["changed"] is True

    def test_detect_side_effect(self):
        self.detector.detect_outcome("a1", "success")
        r = self.detector.detect_side_effect(
            "a1", "memory_spike", severity="high"
        )
        assert r["severity"] == "high"
        assert r["recorded"] is True
        assert self.detector.side_effect_count == 1

    def test_side_effect_linked_to_outcome(self):
        self.detector.detect_outcome("a1", "success")
        self.detector.detect_side_effect("a1", "latency_increase")
        outcomes = self.detector.get_outcomes("a1")
        assert len(outcomes[0]["side_effects"]) == 1

    def test_register_delayed_detection(self):
        r = self.detector.register_delayed_detection(
            "a1", check_after=5, expected_metric="cpu"
        )
        assert r["status"] == "registered"
        assert self.detector.pending_count == 1

    def test_check_pending_timeout(self):
        self.detector.register_delayed_detection(
            "a1", check_after=0, expected_metric="missing_metric"
        )
        results = self.detector.check_pending_detections()
        assert len(results) >= 1

    def test_check_pending_with_metric(self):
        self.detector._metric_current["cpu"] = 75.0
        self.detector.register_delayed_detection(
            "a1", check_after=0, expected_metric="cpu"
        )
        results = self.detector.check_pending_detections()
        found = [r for r in results if r["action_id"] == "a1"]
        assert len(found) == 1
        assert found[0]["status"] == "checked"

    def test_correlate_outcomes_insufficient(self):
        r = self.detector.correlate_outcomes(["a1"])
        assert r["correlation"] == "insufficient_data"

    def test_correlate_outcomes(self):
        self.detector.detect_outcome("a1", "success")
        self.detector.detect_outcome("a2", "success")
        self.detector.detect_outcome("a3", "failure")
        r = self.detector.correlate_outcomes(["a1", "a2", "a3"])
        assert r["total_outcomes"] == 3
        assert r["success_rate"] > 0
        assert r["pattern"] in ("mostly_success", "mixed", "mostly_failure")

    def test_get_outcomes(self):
        self.detector.detect_outcome("a1", "success")
        self.detector.detect_outcome("a1", "partial")
        outcomes = self.detector.get_outcomes("a1")
        assert len(outcomes) == 2

    def test_get_outcomes_empty(self):
        assert self.detector.get_outcomes("nope") == []


# ── FeedbackCollector ─────────────────────────

class TestFeedbackCollector:
    """FeedbackCollector testleri."""

    def setup_method(self):
        from app.core.closedloop.feedback_collector import FeedbackCollector
        self.fc = FeedbackCollector()

    def test_collect_explicit(self):
        r = self.fc.collect_explicit("a1", 0.8, comment="Good")
        assert r["rating"] == 0.8
        assert r["recorded"] is True
        assert self.fc.feedback_count == 1

    def test_explicit_clamped(self):
        r = self.fc.collect_explicit("a1", 5.0)
        assert r["rating"] == 1.0
        r2 = self.fc.collect_explicit("a2", -5.0)
        assert r2["rating"] == -1.0

    def test_collect_implicit(self):
        r = self.fc.collect_implicit("a1", "click", value=1.0)
        assert r["signal_type"] == "click"
        assert r["recorded"] is True

    def test_collect_user_reaction_approve(self):
        r = self.fc.collect_user_reaction("a1", "approve", intensity=1.0)
        assert r["rating"] == 1.0
        assert r["reaction"] == "approve"

    def test_collect_user_reaction_reject(self):
        r = self.fc.collect_user_reaction("a1", "reject", intensity=1.0)
        assert r["rating"] == -1.0

    def test_collect_user_reaction_ignore(self):
        r = self.fc.collect_user_reaction("a1", "ignore")
        assert r["rating"] == 0.0

    def test_collect_user_reaction_modify(self):
        r = self.fc.collect_user_reaction("a1", "modify", intensity=1.0)
        assert r["rating"] == 0.3

    def test_collect_system_metric(self):
        r = self.fc.collect_system_metric("cpu", 75.5, action_id="a1")
        assert r["value"] == 75.5
        assert r["recorded"] is True

    def test_system_metric_without_action(self):
        r = self.fc.collect_system_metric("memory", 80.0)
        assert r["recorded"] is True

    def test_collect_external_signal(self):
        r = self.fc.collect_external_signal(
            "slack", "mention", data={"channel": "general"}, action_id="a1"
        )
        assert r["source"] == "slack"
        assert r["recorded"] is True
        assert self.fc.signal_count == 1

    def test_external_signal_without_action(self):
        r = self.fc.collect_external_signal("api", "webhook")
        assert r["recorded"] is True

    def test_get_action_feedback(self):
        self.fc.collect_explicit("a1", 0.8)
        self.fc.collect_implicit("a1", "click")
        fb = self.fc.get_action_feedback("a1")
        assert len(fb) == 2

    def test_get_action_feedback_empty(self):
        assert self.fc.get_action_feedback("nope") == []

    def test_get_average_rating(self):
        self.fc.collect_explicit("a1", 0.8)
        self.fc.collect_explicit("a1", 0.6)
        avg = self.fc.get_average_rating("a1")
        assert avg == 0.7

    def test_get_average_rating_empty(self):
        assert self.fc.get_average_rating("nope") == 0.0

    def test_get_metric_history(self):
        self.fc.collect_system_metric("cpu", 50.0)
        self.fc.collect_system_metric("cpu", 60.0)
        history = self.fc.get_metric_history("cpu")
        assert len(history) == 2

    def test_stats(self):
        self.fc.collect_explicit("a1", 0.5)
        self.fc.collect_implicit("a2", "view")
        self.fc.collect_system_metric("mem", 70.0, action_id="a3")
        self.fc.collect_external_signal("api", "hook")
        assert self.fc._stats["explicit"] == 1
        assert self.fc._stats["implicit"] == 1
        assert self.fc._stats["system"] == 1
        assert self.fc._stats["external"] == 1


# ── CausalityAnalyzer ─────────────────────────

class TestCausalityAnalyzer:
    """CausalityAnalyzer testleri."""

    def setup_method(self):
        from app.core.closedloop.causality_analyzer import CausalityAnalyzer
        self.ca = CausalityAnalyzer(min_confidence=0.5)

    def test_link_action_outcome(self):
        r = self.ca.link_action_outcome("a1", "o1", confidence=0.8)
        assert r["confidence"] == 0.8
        assert r["meets_threshold"] is True
        assert self.ca.link_count == 1

    def test_link_below_threshold(self):
        r = self.ca.link_action_outcome("a1", "o1", confidence=0.3)
        assert r["meets_threshold"] is False

    def test_link_high_confidence(self):
        self.ca.link_action_outcome("a1", "o1", confidence=0.9)
        assert self.ca._stats["high_confidence"] == 1

    def test_infer_causality(self):
        self.ca.link_action_outcome("a1", "o1", confidence=0.8)
        outcomes = [{"confidence": 0.8, "outcome_type": "success"}]
        r = self.ca.infer_causality("a1", outcomes)
        assert "confidence" in r
        assert isinstance(r["causal"], bool)

    def test_infer_no_outcomes(self):
        r = self.ca.infer_causality("a1", [])
        assert r["causal"] is False
        assert r["reason"] == "no_outcomes"

    def test_infer_multiple_outcomes(self):
        for i in range(5):
            self.ca.link_action_outcome("a1", f"o{i}", confidence=0.7)
        outcomes = [
            {"confidence": 0.7} for _ in range(5)
        ]
        r = self.ca.infer_causality("a1", outcomes)
        assert r["outcome_count"] == 5

    def test_detect_confounder(self):
        self.ca.link_action_outcome("a1", "o1", confidence=0.8)
        r = self.ca.detect_confounder("a1", "weather", impact=0.5)
        assert r["links_affected"] == 1
        assert self.ca.confounder_count == 1

    def test_confounder_reduces_confidence(self):
        self.ca.link_action_outcome("a1", "o1", confidence=0.8)
        self.ca.detect_confounder("a1", "weather", impact=0.5)
        links = self.ca.get_links("a1")
        assert links[0]["confidence"] < 0.8

    def test_compute_attribution_single(self):
        self.ca.link_action_outcome("a1", "o1", confidence=0.8)
        r = self.ca.compute_attribution("o1", ["a1"])
        assert r["attributions"]["a1"] == 1.0

    def test_compute_attribution_multiple(self):
        self.ca.link_action_outcome("a1", "o1", confidence=0.6)
        self.ca.link_action_outcome("a2", "o1", confidence=0.4)
        r = self.ca.compute_attribution("o1", ["a1", "a2"])
        assert abs(sum(r["attributions"].values()) - 1.0) < 0.01

    def test_compute_attribution_empty(self):
        r = self.ca.compute_attribution("o1", [])
        assert r["attributions"] == {}

    def test_get_confidence_score(self):
        self.ca.link_action_outcome("a1", "o1", confidence=0.8)
        self.ca.link_action_outcome("a1", "o2", confidence=0.6)
        score = self.ca.get_confidence_score("a1")
        assert score == 0.7

    def test_get_confidence_score_empty(self):
        assert self.ca.get_confidence_score("nope") == 0.0

    def test_get_links(self):
        self.ca.link_action_outcome("a1", "o1")
        self.ca.link_action_outcome("a1", "o2")
        links = self.ca.get_links("a1")
        assert len(links) == 2

    def test_get_links_empty(self):
        assert self.ca.get_links("nope") == []

    def test_std_dev(self):
        assert self.ca._std_dev([1.0]) == 0.0
        assert self.ca._std_dev([]) == 0.0
        sd = self.ca._std_dev([2.0, 4.0, 6.0])
        assert sd > 0


# ── LearningIntegrator ────────────────────────

class TestLearningIntegrator:
    """LearningIntegrator testleri."""

    def setup_method(self):
        from app.core.closedloop.learning_integrator import LearningIntegrator
        self.li = LearningIntegrator(min_confidence=0.5)

    def test_record_learning(self):
        r = self.li.record_learning("a1", "success", 0.8, insight="Good")
        assert r["recorded"] is True
        assert self.li.learning_count == 1

    def test_record_success_reinforces(self):
        self.li.record_learning("a1", "success", 0.8)
        reinforcements = self.li.get_reinforcements()
        assert "a1" in reinforcements

    def test_record_failure_avoids(self):
        self.li.record_learning("a1", "failure", 0.8)
        avoidances = self.li.get_avoidances()
        assert "a1" in avoidances

    def test_record_low_confidence_no_effect(self):
        self.li.record_learning("a1", "success", 0.2)
        assert len(self.li.get_reinforcements()) == 0

    def test_update_strategy(self):
        r = self.li.update_strategy("s1", {"param": 0.5}, reason="test")
        assert r["version"] == 1
        assert r["updated"] is True
        assert self.li.strategy_count == 1

    def test_update_strategy_increments(self):
        self.li.update_strategy("s1", {"a": 1})
        self.li.update_strategy("s1", {"b": 2})
        assert self.li._strategies["s1"]["version"] == 2

    def test_reinforce_success(self):
        r = self.li.reinforce_success("a1", strength=0.8)
        assert r["type"] == "reinforcement"
        assert r["strength"] == 0.8

    def test_reinforce_accumulates(self):
        self.li.reinforce_success("a1", 0.5)
        self.li.reinforce_success("a1", 0.5)
        r = self.li.get_reinforcements()
        assert r["a1"]["count"] == 2

    def test_avoid_failure(self):
        r = self.li.avoid_failure("a1", severity=0.9)
        assert r["type"] == "avoidance"

    def test_avoid_accumulates(self):
        self.li.avoid_failure("a1", 0.5)
        self.li.avoid_failure("a1", 0.5)
        a = self.li.get_avoidances()
        assert a["a1"]["count"] == 2

    def test_extract_pattern(self):
        self.li.record_learning("a1", "success", 0.8)
        self.li.record_learning("a2", "success", 0.7)
        r = self.li.extract_pattern("good_pattern", ["a1", "a2"])
        assert r["success_rate"] == 1.0
        assert r["extracted"] is True
        assert self.li.pattern_count == 1

    def test_extract_pattern_mixed(self):
        self.li.record_learning("a1", "success", 0.8)
        self.li.record_learning("a2", "failure", 0.7)
        r = self.li.extract_pattern("mix", ["a1", "a2"])
        assert r["success_rate"] == 0.5

    def test_get_pattern(self):
        self.li.extract_pattern("p1", ["a1"])
        p = self.li.get_pattern("p1")
        assert p is not None
        assert p["pattern_name"] == "p1"

    def test_get_pattern_none(self):
        assert self.li.get_pattern("nope") is None

    def test_update_knowledge(self):
        r = self.li.update_knowledge("key1", "value1")
        assert r["version"] == 1
        assert r["updated"] is True
        assert self.li.knowledge_count == 1

    def test_update_knowledge_increments(self):
        self.li.update_knowledge("k1", "v1")
        self.li.update_knowledge("k1", "v2")
        k = self.li.get_knowledge("k1")
        assert k["version"] == 2
        assert k["value"] == "v2"

    def test_get_knowledge_none(self):
        assert self.li.get_knowledge("nope") is None


# ── LoopMonitor ───────────────────────────────

class TestLoopMonitor:
    """LoopMonitor testleri."""

    def setup_method(self):
        from app.core.closedloop.loop_monitor import LoopMonitor
        self.mon = LoopMonitor()

    def test_track_loop_incomplete(self):
        r = self.mon.track_loop("a1", {"action": True, "outcome": True})
        assert r["completion"] == 0.4
        assert r["is_complete"] is False
        assert "feedback" in r["missing"]
        assert self.mon.loop_count == 1

    def test_track_loop_complete(self):
        stages = {
            "action": True, "outcome": True,
            "feedback": True, "learn": True, "improve": True,
        }
        r = self.mon.track_loop("a1", stages)
        assert r["completion"] == 1.0
        assert r["is_complete"] is True
        assert r["missing"] == []

    def test_track_loop_default_stages(self):
        r = self.mon.track_loop("a1")
        assert r["completion"] == 0.0
        assert r["is_complete"] is False

    def test_check_health_no_data(self):
        h = self.mon.check_health()
        assert h["status"] == "no_data"

    def test_check_health_healthy(self):
        stages_full = {
            "action": True, "outcome": True,
            "feedback": True, "learn": True, "improve": True,
        }
        for i in range(5):
            self.mon.track_loop(f"a{i}", stages_full)
        self.mon.record_velocity(15.0)
        self.mon.record_quality(0.9)
        h = self.mon.check_health()
        assert h["status"] == "healthy"
        assert h["completion_rate"] == 1.0

    def test_check_health_unhealthy(self):
        for i in range(5):
            self.mon.track_loop(f"a{i}")
        h = self.mon.check_health()
        assert h["completion_rate"] == 0.0

    def test_get_completion_rate(self):
        stages = {"action": True, "outcome": True, "feedback": True,
                   "learn": True, "improve": True}
        self.mon.track_loop("a1", stages)
        self.mon.track_loop("a2")
        rate = self.mon.get_completion_rate()
        assert rate == 0.5

    def test_get_completion_rate_empty(self):
        assert self.mon.get_completion_rate() == 0.0

    def test_record_velocity(self):
        r = self.mon.record_velocity(5.0)
        assert r["velocity"] == 5.0
        assert r["avg_velocity"] > 0

    def test_record_quality(self):
        r = self.mon.record_quality(0.8)
        assert r["quality"] == 0.8
        assert r["avg_quality"] == 0.8

    def test_record_quality_clamped(self):
        r = self.mon.record_quality(5.0)
        assert r["quality"] == 1.0

    def test_detect_gap(self):
        r = self.mon.detect_gap("a1", "feedback", severity="high")
        assert r["missing_stage"] == "feedback"
        assert r["detected"] is True
        assert self.mon.gap_count == 1

    def test_get_gaps(self):
        self.mon.detect_gap("a1", "feedback")
        self.mon.detect_gap("a2", "learn")
        gaps = self.mon.get_gaps()
        assert len(gaps) == 2

    def test_get_health_history(self):
        self.mon.check_health()
        self.mon.check_health()
        history = self.mon.get_health_history()
        assert len(history) == 2


# ── ClosedLoopExperimentTracker ───────────────

class TestExperimentTracker:
    """ClosedLoopExperimentTracker testleri."""

    def setup_method(self):
        from app.core.closedloop.experiment_tracker import (
            ClosedLoopExperimentTracker,
        )
        self.et = ClosedLoopExperimentTracker(
            default_duration_hours=24,
            significance_threshold=0.05,
        )

    def test_create_experiment(self):
        r = self.et.create_experiment(
            "exp1", "Test hypothesis", ["A", "B"]
        )
        assert r["status"] == "running"
        assert r["variants"] == ["A", "B"]
        assert self.et.experiment_count == 1

    def test_create_custom_duration(self):
        r = self.et.create_experiment(
            "exp1", "hyp", ["A", "B"], duration_hours=48
        )
        assert r["duration_hours"] == 48

    def test_record_result(self):
        self.et.create_experiment("exp1", "hyp", ["A", "B"])
        r = self.et.record_result("exp1", "A", True, value=1.0)
        assert r["recorded"] is True
        assert r["total_results"] == 1

    def test_record_result_not_found(self):
        r = self.et.record_result("nope", "A", True)
        assert r["error"] == "experiment_not_found"

    def test_record_result_not_running(self):
        self.et.create_experiment("exp1", "hyp", ["A", "B"])
        self.et.pause_experiment("exp1")
        r = self.et.record_result("exp1", "A", True)
        assert r["error"] == "experiment_not_running"

    def test_analyze_experiment(self):
        self.et.create_experiment("exp1", "hyp", ["A", "B"])
        for _ in range(20):
            self.et.record_result("exp1", "A", True, 1.0)
            self.et.record_result("exp1", "B", False, 0.0)
        r = self.et.analyze_experiment("exp1")
        assert r["variant_stats"]["A"]["success_rate"] == 1.0
        assert r["variant_stats"]["B"]["success_rate"] == 0.0
        assert r["total_samples"] == 40

    def test_analyze_not_found(self):
        r = self.et.analyze_experiment("nope")
        assert "error" in r

    def test_select_winner(self):
        self.et.create_experiment("exp1", "hyp", ["A", "B"])
        for _ in range(15):
            self.et.record_result("exp1", "A", True, 1.0)
            self.et.record_result("exp1", "B", False, 0.0)
        r = self.et.select_winner("exp1")
        assert r["winner"] == "A"
        assert r["status"] == "completed"

    def test_select_winner_not_found(self):
        r = self.et.select_winner("nope")
        assert "error" in r

    def test_get_rollout_decision(self):
        self.et.create_experiment("exp1", "hyp", ["A", "B"])
        for _ in range(15):
            self.et.record_result("exp1", "A", True, 1.0)
            self.et.record_result("exp1", "B", False, 0.0)
        self.et.select_winner("exp1")
        r = self.et.get_rollout_decision("exp1")
        assert r["decision"] == "rollout"
        assert r["winner"] == "A"

    def test_rollout_not_found(self):
        r = self.et.get_rollout_decision("nope")
        assert "error" in r

    def test_pause_resume(self):
        self.et.create_experiment("exp1", "hyp", ["A", "B"])
        r1 = self.et.pause_experiment("exp1")
        assert r1["status"] == "paused"
        r2 = self.et.resume_experiment("exp1")
        assert r2["status"] == "running"

    def test_pause_not_found(self):
        r = self.et.pause_experiment("nope")
        assert "error" in r

    def test_resume_not_found(self):
        r = self.et.resume_experiment("nope")
        assert "error" in r

    def test_get_experiment(self):
        self.et.create_experiment("exp1", "hyp", ["A", "B"])
        exp = self.et.get_experiment("exp1")
        assert exp["hypothesis"] == "hyp"

    def test_get_experiment_none(self):
        assert self.et.get_experiment("nope") is None

    def test_list_experiments(self):
        self.et.create_experiment("exp1", "h1", ["A", "B"])
        self.et.create_experiment("exp2", "h2", ["A", "B"])
        self.et.pause_experiment("exp2")
        running = self.et.list_experiments(status="running")
        assert len(running) == 1
        all_exps = self.et.list_experiments()
        assert len(all_exps) == 2

    def test_active_count(self):
        self.et.create_experiment("exp1", "h1", ["A", "B"])
        self.et.create_experiment("exp2", "h2", ["A", "B"])
        assert self.et.active_count == 2
        self.et.pause_experiment("exp2")
        assert self.et.active_count == 1

    def test_significance_insufficient_samples(self):
        self.et.create_experiment("exp1", "hyp", ["A", "B"])
        for _ in range(5):
            self.et.record_result("exp1", "A", True)
            self.et.record_result("exp1", "B", False)
        r = self.et.analyze_experiment("exp1")
        assert r["significant"] is False


# ── ImprovementEngine ─────────────────────────

class TestImprovementEngine:
    """ImprovementEngine testleri."""

    def setup_method(self):
        from app.core.closedloop.improvement_engine import ImprovementEngine
        self.ie = ImprovementEngine(auto_apply=False)

    def test_identify_improvement(self):
        r = self.ie.identify_improvement(
            "imp1", "Fix error handling", priority="high"
        )
        assert r["identified"] is True
        assert r["priority"] == "high"
        assert self.ie.improvement_count == 1

    def test_identify_with_source(self):
        r = self.ie.identify_improvement(
            "imp1", "desc", source_action="a1", expected_impact=0.8
        )
        imp = self.ie.get_improvement("imp1")
        assert imp["source_action"] == "a1"
        assert imp["expected_impact"] == 0.8

    def test_auto_apply(self):
        from app.core.closedloop.improvement_engine import ImprovementEngine
        ie = ImprovementEngine(auto_apply=True)
        ie.identify_improvement("imp1", "critical fix", priority="critical")
        imp = ie.get_improvement("imp1")
        assert imp["status"] == "applied"

    def test_auto_apply_only_high(self):
        from app.core.closedloop.improvement_engine import ImprovementEngine
        ie = ImprovementEngine(auto_apply=True)
        ie.identify_improvement("imp1", "low fix", priority="low")
        imp = ie.get_improvement("imp1")
        assert imp["status"] == "identified"

    def test_prioritize(self):
        self.ie.identify_improvement("imp1", "d1", priority="low")
        self.ie.identify_improvement("imp2", "d2", priority="critical")
        self.ie.identify_improvement("imp3", "d3", priority="high")
        result = self.ie.prioritize()
        assert result[0]["improvement_id"] == "imp2"
        assert result[1]["improvement_id"] == "imp3"

    def test_prioritize_by_impact(self):
        self.ie.identify_improvement(
            "imp1", "d1", priority="medium", expected_impact=0.3
        )
        self.ie.identify_improvement(
            "imp2", "d2", priority="medium", expected_impact=0.9
        )
        result = self.ie.prioritize()
        assert result[0]["improvement_id"] == "imp2"

    def test_apply_improvement(self):
        self.ie.identify_improvement("imp1", "test")
        r = self.ie.apply_improvement("imp1")
        assert r["applied"] is True
        assert self.ie.applied_count == 1

    def test_apply_not_found(self):
        r = self.ie.apply_improvement("nope")
        assert r["error"] == "improvement_not_found"

    def test_apply_already_applied(self):
        self.ie.identify_improvement("imp1", "test")
        self.ie.apply_improvement("imp1")
        r = self.ie.apply_improvement("imp1")
        assert r["error"] == "already_applied"

    def test_measure_impact(self):
        self.ie.identify_improvement("imp1", "test")
        r = self.ie.measure_impact("imp1", before_metric=50.0, after_metric=75.0)
        assert r["positive"] is True
        assert r["change_pct"] == 50.0
        assert self.ie.impact_count == 1

    def test_measure_negative_impact(self):
        self.ie.identify_improvement("imp1", "test")
        r = self.ie.measure_impact("imp1", before_metric=80.0, after_metric=60.0)
        assert r["positive"] is False
        assert r["change_pct"] == -25.0

    def test_measure_zero_baseline(self):
        self.ie.identify_improvement("imp1", "test")
        r = self.ie.measure_impact("imp1", before_metric=0.0, after_metric=5.0)
        assert r["change_pct"] == 100.0

    def test_measure_not_found(self):
        r = self.ie.measure_impact("nope", 0, 0)
        assert "error" in r

    def test_iterate(self):
        self.ie.identify_improvement("imp1", "d1")
        self.ie.apply_improvement("imp1")
        self.ie.measure_impact("imp1", 50.0, 70.0)
        r = self.ie.iterate("cycle1")
        assert r["iteration"] == 1
        assert r["positive_impact_rate"] == 1.0

    def test_iterate_no_impact(self):
        r = self.ie.iterate()
        assert r["positive_impact_rate"] == 0.0

    def test_get_improvement(self):
        self.ie.identify_improvement("imp1", "test")
        imp = self.ie.get_improvement("imp1")
        assert imp["description"] == "test"

    def test_get_improvement_none(self):
        assert self.ie.get_improvement("nope") is None

    def test_get_impact(self):
        self.ie.identify_improvement("imp1", "test")
        self.ie.measure_impact("imp1", 50.0, 75.0)
        impact = self.ie.get_impact("imp1")
        assert impact["positive"] is True

    def test_get_impact_none(self):
        assert self.ie.get_impact("nope") is None

    def test_get_iteration_history(self):
        self.ie.iterate("c1")
        self.ie.iterate("c2")
        history = self.ie.get_iteration_history()
        assert len(history) == 2


# ── ClosedLoopOrchestrator ────────────────────

class TestClosedLoopOrchestrator:
    """ClosedLoopOrchestrator testleri."""

    def setup_method(self):
        from app.core.closedloop.closedloop_orchestrator import (
            ClosedLoopOrchestrator,
        )
        self.orch = ClosedLoopOrchestrator(
            detection_timeout=10,
            min_confidence=0.5,
            experiment_duration_hours=24,
            auto_apply_learnings=False,
        )

    def test_execute_action(self):
        r = self.orch.execute_action("a1", "test_action")
        assert r["status"] == "running"
        assert r["loop_started"] is True
        assert self.orch.total_loops == 1

    def test_execute_with_context(self):
        r = self.orch.execute_action(
            "a1", "test", context={"env": "prod"}
        )
        action = self.orch.actions.get_action("a1")
        assert action["context"]["env"] == "prod"

    def test_record_outcome_success(self):
        self.orch.execute_action("a1", "test")
        r = self.orch.record_outcome("a1", "success", success=True)
        assert r["recorded"] is True
        assert r["outcome_type"] == "success"

    def test_record_outcome_failure(self):
        self.orch.execute_action("a1", "test")
        r = self.orch.record_outcome("a1", "failure", success=False)
        assert r["recorded"] is True

    def test_record_outcome_with_metrics(self):
        self.orch.execute_action("a1", "test")
        r = self.orch.record_outcome(
            "a1", "success", metrics={"latency": 50}
        )
        assert r["recorded"] is True

    def test_collect_and_learn(self):
        self.orch.execute_action("a1", "test")
        self.orch.record_outcome("a1", "success", success=True)
        r = self.orch.collect_and_learn("a1", rating=0.8, outcome_type="success")
        assert r["learned"] is True
        assert "confidence" in r

    def test_collect_and_learn_no_rating(self):
        self.orch.execute_action("a1", "test")
        self.orch.record_outcome("a1", "success")
        r = self.orch.collect_and_learn("a1", outcome_type="success")
        assert r["learned"] is True

    def test_full_loop_success(self):
        r = self.orch.full_loop(
            "a1", "deploy", "success", rating=0.9
        )
        assert r["outcome_type"] == "success"
        assert r["loop_complete"] is True
        assert self.orch.full_loop_count == 1

    def test_full_loop_failure(self):
        r = self.orch.full_loop(
            "a1", "deploy", "failure", rating=-0.5
        )
        assert r["outcome_type"] == "failure"
        assert r["improvement_id"] is not None

    def test_full_loop_without_rating(self):
        r = self.orch.full_loop("a1", "test", "success")
        assert r["loop_complete"] is False  # No feedback stage

    def test_full_loop_with_metrics(self):
        r = self.orch.full_loop(
            "a1", "deploy", "success",
            rating=0.8, metrics={"time": 120}
        )
        assert r["outcome_type"] == "success"

    def test_get_status(self):
        self.orch.full_loop("a1", "test", "success", rating=1.0)
        status = self.orch.get_status()
        assert status["loops_executed"] == 1
        assert status["actions"] >= 1
        assert status["outcomes"] >= 1
        assert "health" in status

    def test_get_analytics(self):
        self.orch.full_loop("a1", "test", "success", rating=0.8)
        analytics = self.orch.get_analytics()
        assert "loop_health" in analytics
        assert "completion_rate" in analytics
        assert "top_improvements" in analytics

    def test_multiple_loops(self):
        for i in range(5):
            self.orch.full_loop(
                f"a{i}", f"action_{i}", "success", rating=0.8
            )
        status = self.orch.get_status()
        assert status["loops_executed"] == 5

    def test_experiment_integration(self):
        self.orch.experiments.create_experiment(
            "exp1", "test hyp", ["A", "B"]
        )
        assert self.orch.experiments.experiment_count == 1

    def test_improvement_integration(self):
        self.orch.full_loop("a1", "test", "failure", rating=-1.0)
        status = self.orch.get_status()
        assert status["improvements"] >= 1

    def test_learning_integration(self):
        self.orch.full_loop("a1", "test", "success", rating=0.9)
        assert self.orch.learning.learning_count >= 1

    def test_causality_integration(self):
        self.orch.full_loop("a1", "test", "success", rating=0.8)
        assert self.orch.causality.link_count >= 1
