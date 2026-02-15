"""ATLAS Confidence-Based Autonomy testleri.

Guven tabanli otonom karar bilesenlerini
kapsamli test suite.
"""

import time

import pytest


# ── Models ────────────────────────────────────

class TestConfidenceModels:
    """Confidence model testleri."""

    def test_confidence_level_enum(self):
        from app.models.confidence_models import ConfidenceLevel
        assert ConfidenceLevel.VERY_HIGH == "very_high"
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.LOW == "low"
        assert ConfidenceLevel.VERY_LOW == "very_low"

    def test_autonomy_action_enum(self):
        from app.models.confidence_models import AutonomyAction
        assert AutonomyAction.AUTO_EXECUTE == "auto_execute"
        assert AutonomyAction.SUGGEST == "suggest"
        assert AutonomyAction.ASK_HUMAN == "ask_human"
        assert AutonomyAction.REJECT == "reject"
        assert AutonomyAction.ESCALATE == "escalate"

    def test_trust_level_enum(self):
        from app.models.confidence_models import TrustLevel
        assert TrustLevel.FULL == "full"
        assert TrustLevel.HIGH == "high"
        assert TrustLevel.MODERATE == "moderate"
        assert TrustLevel.LIMITED == "limited"
        assert TrustLevel.NONE == "none"

    def test_escalation_urgency_enum(self):
        from app.models.confidence_models import EscalationUrgency
        assert EscalationUrgency.CRITICAL == "critical"
        assert EscalationUrgency.HIGH == "high"
        assert EscalationUrgency.MEDIUM == "medium"
        assert EscalationUrgency.LOW == "low"
        assert EscalationUrgency.INFORMATIONAL == "informational"

    def test_calibration_status_enum(self):
        from app.models.confidence_models import CalibrationStatus
        assert CalibrationStatus.WELL_CALIBRATED == "well_calibrated"
        assert CalibrationStatus.OVERCONFIDENT == "overconfident"
        assert CalibrationStatus.UNDERCONFIDENT == "underconfident"
        assert CalibrationStatus.INSUFFICIENT_DATA == "insufficient_data"
        assert CalibrationStatus.NEEDS_RECALIBRATION == "needs_recalibration"

    def test_feedback_type_enum(self):
        from app.models.confidence_models import FeedbackType
        assert FeedbackType.APPROVAL == "approval"
        assert FeedbackType.REJECTION == "rejection"
        assert FeedbackType.CORRECTION == "correction"
        assert FeedbackType.PREFERENCE == "preference"
        assert FeedbackType.OVERRIDE == "override"
        assert FeedbackType.IGNORE == "ignore"

    def test_confidence_record(self):
        from app.models.confidence_models import ConfidenceRecord
        r = ConfidenceRecord(action_id="a1", score=0.85)
        assert r.action_id == "a1"
        assert r.score == 0.85
        assert r.level.value == "medium"
        assert r.record_id

    def test_trust_record(self):
        from app.models.confidence_models import TrustRecord
        r = TrustRecord(domain="security")
        assert r.domain == "security"
        assert r.score == 0.5
        assert r.level.value == "moderate"

    def test_escalation_record(self):
        from app.models.confidence_models import EscalationRecord
        r = EscalationRecord(action_id="a1", target="admin")
        assert r.action_id == "a1"
        assert r.target == "admin"
        assert r.status == "pending"

    def test_confidence_snapshot(self):
        from app.models.confidence_models import ConfidenceSnapshot
        s = ConfidenceSnapshot(total_decisions=100, auto_executed=60)
        assert s.total_decisions == 100
        assert s.auto_executed == 60
        assert s.avg_confidence == 0.0


# ── ConfidenceCalculator ──────────────────────

class TestConfidenceCalculator:
    """ConfidenceCalculator testleri."""

    def setup_method(self):
        from app.core.confidence.confidence_calculator import ConfidenceCalculator
        self.cc = ConfidenceCalculator()

    def test_calculate_basic(self):
        r = self.cc.calculate({
            "historical_accuracy": 0.8,
            "data_quality": 0.7,
            "model_certainty": 0.9,
            "context_familiarity": 0.6,
        })
        assert 0 <= r["score"] <= 1
        assert r["level"] in ("very_high", "high", "medium", "low", "very_low")
        assert self.cc.calculation_count == 1

    def test_calculate_all_high(self):
        r = self.cc.calculate({
            "historical_accuracy": 1.0,
            "data_quality": 1.0,
            "model_certainty": 1.0,
            "context_familiarity": 1.0,
        })
        assert r["score"] == 1.0
        assert r["level"] == "very_high"

    def test_calculate_all_low(self):
        r = self.cc.calculate({
            "historical_accuracy": 0.0,
            "data_quality": 0.0,
            "model_certainty": 0.0,
            "context_familiarity": 0.0,
        })
        assert r["score"] == 0.0
        assert r["level"] == "very_low"

    def test_calculate_with_domain(self):
        r = self.cc.calculate(
            {"historical_accuracy": 0.8}, domain="security"
        )
        assert r["domain"] == "security"

    def test_calculate_custom_weights(self):
        r = self.cc.calculate(
            {"factor_a": 1.0, "factor_b": 0.0},
            weights={"factor_a": 0.5, "factor_b": 0.5},
        )
        assert r["score"] == 0.5

    def test_calculate_clamping(self):
        r = self.cc.calculate(
            {"test": 5.0},
            weights={"test": 1.0},
        )
        assert r["score"] == 1.0

    def test_historical_accuracy(self):
        self.cc.record_accuracy("security", True)
        self.cc.record_accuracy("security", True)
        self.cc.record_accuracy("security", False)
        acc = self.cc.calculate_historical_accuracy("security")
        assert abs(acc - 0.6667) < 0.01

    def test_historical_accuracy_empty(self):
        assert self.cc.calculate_historical_accuracy("unknown") == 0.5

    def test_assess_data_quality(self):
        score = self.cc.assess_data_quality(
            completeness=1.0, freshness=1.0, consistency=1.0
        )
        assert score == 1.0

    def test_assess_data_quality_partial(self):
        score = self.cc.assess_data_quality(
            completeness=0.5, freshness=0.5, consistency=0.5
        )
        assert score == 0.5

    def test_assess_model_certainty(self):
        score = self.cc.assess_model_certainty(
            prediction_confidence=0.9, validation_score=0.8
        )
        assert score > 0.7

    def test_assess_model_certainty_old(self):
        score = self.cc.assess_model_certainty(
            prediction_confidence=0.9, model_age_days=30, validation_score=0.8
        )
        assert score < 0.9

    def test_assess_context_familiarity(self):
        # First encounter = low familiarity
        f1 = self.cc.assess_context_familiarity("new_ctx")
        assert f1 == 0.0
        # Repeated encounters increase familiarity
        for _ in range(10):
            f = self.cc.assess_context_familiarity("new_ctx")
        assert f > f1

    def test_avg_score(self):
        self.cc.calculate({"a": 1.0}, weights={"a": 1.0})
        self.cc.calculate({"a": 0.0}, weights={"a": 1.0})
        assert self.cc.avg_score == 0.5

    def test_factor_details(self):
        r = self.cc.calculate(
            {"factor_a": 0.8},
            weights={"factor_a": 1.0},
        )
        assert "factor_a" in r["factors"]
        assert r["factors"]["factor_a"]["value"] == 0.8


# ── ThresholdManager ──────────────────────────

class TestThresholdManager:
    """ThresholdManager testleri."""

    def setup_method(self):
        from app.core.confidence.threshold_manager import ThresholdManager
        self.tm = ThresholdManager(
            auto_execute=0.8, suggest=0.5, ask_human=0.3
        )

    def test_get_default_threshold(self):
        t = self.tm.get_threshold()
        assert t["auto_execute"] == 0.8
        assert t["suggest"] == 0.5
        assert t["ask_human"] == 0.3

    def test_evaluate_auto_execute(self):
        r = self.tm.evaluate(0.9)
        assert r["action"] == "auto_execute"

    def test_evaluate_suggest(self):
        r = self.tm.evaluate(0.6)
        assert r["action"] == "suggest"

    def test_evaluate_ask_human(self):
        r = self.tm.evaluate(0.35)
        assert r["action"] == "ask_human"

    def test_evaluate_reject(self):
        r = self.tm.evaluate(0.1)
        assert r["action"] == "reject"

    def test_set_action_threshold(self):
        self.tm.set_action_threshold("deploy", auto_execute=0.95)
        t = self.tm.get_threshold(action_type="deploy")
        assert t["auto_execute"] == 0.95
        assert self.tm.action_threshold_count == 1

    def test_set_domain_threshold(self):
        self.tm.set_domain_threshold("security", auto_execute=0.9)
        t = self.tm.get_threshold(domain="security")
        assert t["auto_execute"] == 0.9
        assert self.tm.domain_threshold_count == 1

    def test_action_overrides_domain(self):
        self.tm.set_domain_threshold("security", auto_execute=0.9)
        self.tm.set_action_threshold("deploy", auto_execute=0.95)
        t = self.tm.get_threshold(action_type="deploy", domain="security")
        assert t["auto_execute"] == 0.95

    def test_adaptive_adjust_tighten(self):
        self.tm.set_domain_threshold("test", auto_execute=0.8)
        r = self.tm.adaptive_adjust("test", accuracy=0.5)
        assert r["adjusted"] is True
        assert r["direction"] == "tighten"
        t = self.tm.get_threshold(domain="test")
        assert t["auto_execute"] > 0.8

    def test_adaptive_adjust_loosen(self):
        self.tm.set_domain_threshold("test", auto_execute=0.8)
        r = self.tm.adaptive_adjust("test", accuracy=0.95)
        assert r["adjusted"] is True
        assert r["direction"] == "loosen"
        t = self.tm.get_threshold(domain="test")
        assert t["auto_execute"] < 0.8

    def test_adaptive_adjust_no_change(self):
        self.tm.set_domain_threshold("test", auto_execute=0.8)
        r = self.tm.adaptive_adjust("test", accuracy=0.8)
        assert r["adjusted"] is False

    def test_safety_margin(self):
        self.tm.set_safety_margin(0.1)
        r = self.tm.evaluate(0.85)
        # 0.85 < 0.8 + 0.1 margin, so suggest
        assert r["action"] == "suggest"

    def test_adjustment_count(self):
        self.tm.adaptive_adjust("d1", accuracy=0.5)
        self.tm.adaptive_adjust("d2", accuracy=0.95)
        assert self.tm.adjustment_count == 2


# ── ConfidenceAutonomyController ──────────────

class TestAutonomyController:
    """ConfidenceAutonomyController testleri."""

    def setup_method(self):
        from app.core.confidence.autonomy_controller import (
            ConfidenceAutonomyController,
        )
        self.ac = ConfidenceAutonomyController(
            auto_threshold=0.8, suggest_threshold=0.5, ask_threshold=0.3
        )

    def test_decide_auto_execute(self):
        r = self.ac.decide("a1", 0.9)
        assert r["decision"] == "auto_execute"
        assert self.ac.decision_count == 1

    def test_decide_suggest(self):
        r = self.ac.decide("a1", 0.6)
        assert r["decision"] == "suggest"

    def test_decide_ask_human(self):
        r = self.ac.decide("a1", 0.35)
        assert r["decision"] == "ask_human"

    def test_decide_reject(self):
        r = self.ac.decide("a1", 0.1)
        assert r["decision"] == "reject"

    def test_emergency_override(self):
        self.ac.emergency_override(reason="system_failure", enable=True)
        assert self.ac.is_emergency is True
        r = self.ac.decide("a1", 0.99)
        assert r["decision"] == "ask_human"

    def test_emergency_disable(self):
        self.ac.emergency_override(enable=True)
        self.ac.emergency_override(enable=False)
        assert self.ac.is_emergency is False
        r = self.ac.decide("a1", 0.9)
        assert r["decision"] == "auto_execute"

    def test_decision_history(self):
        self.ac.decide("a1", 0.9)
        self.ac.decide("a2", 0.3)
        history = self.ac.get_decision_history()
        assert len(history) == 2

    def test_audit_log(self):
        self.ac.decide("a1", 0.9)
        self.ac.emergency_override(reason="test")
        log = self.ac.get_audit_log()
        assert len(log) >= 2

    def test_decide_with_context(self):
        r = self.ac.decide("a1", 0.9, context={"env": "prod"})
        assert r["decision"] == "auto_execute"


# ── AccuracyTracker ───────────────────────────

class TestAccuracyTracker:
    """AccuracyTracker testleri."""

    def setup_method(self):
        from app.core.confidence.accuracy_tracker import AccuracyTracker
        self.at = AccuracyTracker()

    def test_record_and_resolve(self):
        self.at.record_prediction("p1", 0.8, "success", domain="test")
        r = self.at.record_outcome("p1", "success")
        assert r["correct"] is True

    def test_record_incorrect(self):
        self.at.record_prediction("p1", 0.8, "success")
        r = self.at.record_outcome("p1", "failure")
        assert r["correct"] is False

    def test_record_outcome_not_found(self):
        r = self.at.record_outcome("nope", "success")
        assert "error" in r

    def test_get_accuracy(self):
        self.at.record_prediction("p1", 0.8, "success")
        self.at.record_prediction("p2", 0.8, "success")
        self.at.record_outcome("p1", "success")
        self.at.record_outcome("p2", "failure")
        assert self.at.get_accuracy() == 0.5

    def test_get_accuracy_by_domain(self):
        self.at.record_prediction("p1", 0.8, "success", domain="d1")
        self.at.record_prediction("p2", 0.8, "success", domain="d2")
        self.at.record_outcome("p1", "success")
        self.at.record_outcome("p2", "failure")
        assert self.at.get_accuracy(domain="d1") == 1.0
        assert self.at.get_accuracy(domain="d2") == 0.0

    def test_get_accuracy_empty(self):
        assert self.at.get_accuracy() == 0.0

    def test_accuracy_history(self):
        for i in range(10):
            self.at.record_prediction(f"p{i}", 0.8, "success")
            self.at.record_outcome(f"p{i}", "success" if i % 2 == 0 else "failure")
        history = self.at.get_accuracy_history(window=5)
        assert len(history) > 0

    def test_analyze_trend_insufficient(self):
        r = self.at.analyze_trend()
        assert r["trend"] == "insufficient_data"

    def test_analyze_trend(self):
        for i in range(10):
            self.at.record_prediction(f"p{i}", 0.8, "success")
            self.at.record_outcome(f"p{i}", "success")
        r = self.at.analyze_trend()
        assert r["trend"] in ("improving", "declining", "stable")

    def test_domain_accuracy(self):
        self.at.record_prediction("p1", 0.8, "s", domain="d1")
        self.at.record_prediction("p2", 0.8, "s", domain="d2")
        self.at.record_outcome("p1", "s")
        self.at.record_outcome("p2", "f")
        da = self.at.get_domain_accuracy()
        assert da["d1"] == 1.0
        assert da["d2"] == 0.0

    def test_check_calibration_insufficient(self):
        r = self.at.check_calibration()
        assert r["status"] == "insufficient_data"

    def test_check_calibration(self):
        for i in range(20):
            self.at.record_prediction(f"p{i}", 0.8, "success")
            self.at.record_outcome(f"p{i}", "success" if i < 16 else "failure")
        r = self.at.check_calibration()
        assert "brier_score" in r

    def test_overall_accuracy(self):
        self.at.record_prediction("p1", 0.8, "success")
        self.at.record_outcome("p1", "success")
        assert self.at.overall_accuracy == 1.0

    def test_record_count(self):
        self.at.record_prediction("p1", 0.8, "s")
        self.at.record_outcome("p1", "s")
        assert self.at.record_count == 1


# ── TrustEvolver ──────────────────────────────

class TestTrustEvolver:
    """TrustEvolver testleri."""

    def setup_method(self):
        from app.core.confidence.trust_evolver import TrustEvolver
        self.te = TrustEvolver(
            decay_rate=0.01, recovery_rate=0.05, initial_trust=0.5
        )

    def test_get_trust_initial(self):
        t = self.te.get_trust("security")
        assert t["score"] == 0.5
        assert t["level"] == "moderate"
        assert self.te.domain_count == 1

    def test_record_success(self):
        r = self.te.record_success("security", magnitude=0.1)
        assert r["new_score"] == 0.6
        assert r["old_score"] == 0.5

    def test_record_failure(self):
        r = self.te.record_failure("security", magnitude=0.2)
        assert r["new_score"] == 0.3

    def test_trust_cap_at_one(self):
        for _ in range(20):
            self.te.record_success("d1", 0.1)
        t = self.te.get_trust("d1")
        assert t["score"] <= 1.0

    def test_trust_floor_at_zero(self):
        for _ in range(20):
            self.te.record_failure("d1", 0.1)
        t = self.te.get_trust("d1")
        assert t["score"] >= 0.0

    def test_apply_decay(self):
        self.te.get_trust("d1")
        results = self.te.apply_decay("d1")
        assert len(results) == 1
        assert results[0]["new_score"] < 0.5

    def test_apply_decay_all(self):
        self.te.get_trust("d1")
        self.te.get_trust("d2")
        results = self.te.apply_decay()
        assert len(results) == 2

    def test_recover_trust(self):
        self.te.record_failure("d1", 0.3)
        r = self.te.recover_trust("d1", amount=0.1)
        assert r["new_score"] > r["old_score"]

    def test_recover_trust_default(self):
        self.te.record_failure("d1", 0.3)
        r = self.te.recover_trust("d1")
        assert r["recovered"] == 0.05

    def test_get_all_trust(self):
        self.te.get_trust("d1")
        self.te.get_trust("d2")
        all_t = self.te.get_all_trust()
        assert "d1" in all_t
        assert "d2" in all_t

    def test_get_history(self):
        self.te.record_success("d1")
        self.te.record_failure("d1")
        history = self.te.get_history("d1")
        assert len(history) == 2

    def test_trust_levels(self):
        self.te._trust["d1"] = {
            "domain": "d1", "score": 0.95,
            "level": "", "successes": 0, "failures": 0,
            "last_updated": time.time(),
        }
        assert self.te._score_to_level(0.95) == "full"
        assert self.te._score_to_level(0.75) == "high"
        assert self.te._score_to_level(0.5) == "moderate"
        assert self.te._score_to_level(0.25) == "limited"
        assert self.te._score_to_level(0.1) == "none"


# ── ConfidenceEscalationRouter ────────────────

class TestEscalationRouter:
    """ConfidenceEscalationRouter testleri."""

    def setup_method(self):
        from app.core.confidence.escalation_router import (
            ConfidenceEscalationRouter,
        )
        self.er = ConfidenceEscalationRouter(
            default_timeout=5, default_target="admin"
        )

    def test_add_route(self):
        r = self.er.add_route("security", "sec_team", urgency="high")
        assert r["added"] is True
        assert self.er.route_count == 1

    def test_escalate(self):
        r = self.er.escalate("a1", domain="security", reason="low conf")
        assert r["status"] == "escalated"
        assert r["target"] == "admin"
        assert self.er.pending_count == 1

    def test_escalate_with_route(self):
        self.er.add_route("security", "sec_team")
        r = self.er.escalate("a1", domain="security")
        assert r["target"] == "sec_team"

    def test_resolve(self):
        self.er.escalate("a1")
        r = self.er.resolve("a1", decision="approve")
        assert r["resolved"] is True
        assert self.er.pending_count == 0

    def test_resolve_not_found(self):
        r = self.er.resolve("nope")
        assert "error" in r

    def test_check_timeouts(self):
        self.er._default_timeout = 0
        self.er.escalate("a1")
        time.sleep(0.01)
        results = self.er.check_timeouts()
        assert len(results) == 1
        assert results[0]["status"] == "timed_out"

    def test_timeout_default_action(self):
        self.er.add_route(
            "security", "admin",
            default_action="reject", timeout=0,
        )
        self.er.escalate("a1", domain="security")
        time.sleep(0.01)
        results = self.er.check_timeouts()
        assert len(results) == 1
        assert results[0]["default_action"] == "reject"

    def test_get_pending(self):
        self.er.escalate("a1")
        self.er.escalate("a2")
        pending = self.er.get_pending()
        assert len(pending) == 2

    def test_get_pending_by_target(self):
        self.er.add_route("sec", "sec_team")
        self.er.escalate("a1", domain="sec")
        self.er.escalate("a2")
        pending = self.er.get_pending(target="sec_team")
        assert len(pending) == 1

    def test_get_route(self):
        self.er.add_route("security", "sec_team")
        route = self.er.get_route("security")
        assert route["target"] == "sec_team"

    def test_get_route_none(self):
        assert self.er.get_route("nope") is None

    def test_escalation_count(self):
        self.er.escalate("a1")
        self.er.escalate("a2")
        assert self.er.escalation_count == 2


# ── HumanFeedbackHandler ─────────────────────

class TestHumanFeedback:
    """HumanFeedbackHandler testleri."""

    def setup_method(self):
        from app.core.confidence.human_feedback import HumanFeedbackHandler
        self.hf = HumanFeedbackHandler()

    def test_collect_decision_agree(self):
        r = self.hf.collect_decision("a1", "approve", system_suggestion="approve")
        assert r["agreed"] is True
        assert self.hf.feedback_count == 1

    def test_collect_decision_disagree(self):
        r = self.hf.collect_decision("a1", "reject", system_suggestion="approve")
        assert r["agreed"] is False
        assert self.hf.disagreement_count == 1

    def test_collect_decision_override(self):
        self.hf.collect_decision("a1", "override")
        assert self.hf._stats["overrides"] == 1

    def test_learn_from_correction(self):
        r = self.hf.learn_from_correction("a1", "reject", "approve", domain="sec")
        assert r["learned"] is True
        assert self.hf.correction_count == 1

    def test_correction_updates_preference(self):
        self.hf.learn_from_correction("a1", "reject", "approve", domain="sec")
        pref = self.hf.get_preference("sec", "preferred_action")
        assert pref == "approve"

    def test_update_confidence_from_feedback_agreed(self):
        self.hf.collect_decision("a1", "approve", system_suggestion="approve")
        self.hf.collect_decision("a1", "approve", system_suggestion="approve")
        r = self.hf.update_confidence_from_feedback("a1")
        assert r["adjustment"] == 0.1

    def test_update_confidence_from_feedback_disagreed(self):
        self.hf.collect_decision("a1", "reject", system_suggestion="approve")
        self.hf.collect_decision("a1", "reject", system_suggestion="approve")
        r = self.hf.update_confidence_from_feedback("a1")
        assert r["adjustment"] == -0.1

    def test_update_confidence_empty(self):
        r = self.hf.update_confidence_from_feedback("nope")
        assert r["adjustment"] == 0.0

    def test_learn_preference(self):
        r = self.hf.learn_preference("security", "style", "conservative")
        assert r["learned"] is True

    def test_get_preference(self):
        self.hf.learn_preference("sec", "style", "aggressive")
        assert self.hf.get_preference("sec", "style") == "aggressive"

    def test_get_preference_none(self):
        assert self.hf.get_preference("nope", "key") is None

    def test_get_disagreements(self):
        self.hf.collect_decision("a1", "reject", system_suggestion="approve")
        self.hf.collect_decision("a2", "reject", system_suggestion="approve")
        d = self.hf.get_disagreements()
        assert len(d) == 2

    def test_get_agreement_rate(self):
        self.hf.collect_decision("a1", "approve", system_suggestion="approve")
        self.hf.collect_decision("a2", "reject", system_suggestion="approve")
        assert self.hf.get_agreement_rate() == 0.5

    def test_get_agreement_rate_empty(self):
        assert self.hf.get_agreement_rate() == 0.0

    def test_get_corrections_by_domain(self):
        self.hf.learn_from_correction("a1", "a", "b", domain="d1")
        self.hf.learn_from_correction("a2", "a", "b", domain="d2")
        c = self.hf.get_corrections(domain="d1")
        assert len(c) == 1

    def test_preference_count(self):
        self.hf.learn_preference("d1", "k1", "v1")
        self.hf.learn_preference("d1", "k2", "v2")
        assert self.hf.preference_count == 2


# ── CalibrationEngine ─────────────────────────

class TestCalibrationEngine:
    """CalibrationEngine testleri."""

    def setup_method(self):
        from app.core.confidence.calibration_engine import CalibrationEngine
        self.ce = CalibrationEngine(bins=5, recalibration_threshold=0.15)

    def test_add_sample(self):
        r = self.ce.add_sample(0.8, True)
        assert r["recorded"] is True
        assert self.ce.sample_count == 1

    def test_brier_score_perfect(self):
        for _ in range(10):
            self.ce.add_sample(1.0, True)
            self.ce.add_sample(0.0, False)
        assert self.ce.compute_brier_score() == 0.0

    def test_brier_score_worst(self):
        for _ in range(10):
            self.ce.add_sample(1.0, False)
            self.ce.add_sample(0.0, True)
        assert self.ce.compute_brier_score() == 1.0

    def test_brier_score_empty(self):
        assert self.ce.compute_brier_score() == 0.0

    def test_reliability_diagram(self):
        for _ in range(20):
            self.ce.add_sample(0.9, True)
            self.ce.add_sample(0.1, False)
        diagram = self.ce.reliability_diagram()
        assert len(diagram) > 0
        assert "avg_confidence" in diagram[0]

    def test_reliability_diagram_empty(self):
        assert self.ce.reliability_diagram() == []

    def test_detect_miscalibration_insufficient(self):
        r = self.ce.detect_miscalibration()
        assert r["status"] == "insufficient_data"

    def test_detect_well_calibrated(self):
        for _ in range(30):
            self.ce.add_sample(0.8, True)
            self.ce.add_sample(0.2, False)
        r = self.ce.detect_miscalibration()
        assert r["status"] == "well_calibrated"

    def test_detect_overconfident(self):
        for _ in range(30):
            self.ce.add_sample(0.95, False)
        r = self.ce.detect_miscalibration()
        assert r["status"] == "overconfident"

    def test_auto_correct(self):
        for _ in range(30):
            self.ce.add_sample(0.9, False)
        r = self.ce.auto_correct()
        assert r["corrected"] is True
        assert self.ce.correction_factor != 0.0

    def test_auto_correct_insufficient(self):
        r = self.ce.auto_correct()
        assert r["corrected"] is False

    def test_auto_correct_acceptable(self):
        for _ in range(30):
            self.ce.add_sample(0.8, True)
            self.ce.add_sample(0.2, False)
        r = self.ce.auto_correct()
        assert r["corrected"] is False

    def test_calibrate_score(self):
        self.ce._correction_factor = -0.1
        assert self.ce.calibrate_score(0.8) == 0.7

    def test_calibrate_score_clamped(self):
        self.ce._correction_factor = -1.0
        assert self.ce.calibrate_score(0.5) == 0.0

    def test_correction_history(self):
        for _ in range(30):
            self.ce.add_sample(0.9, False)
        self.ce.auto_correct()
        history = self.ce.get_correction_history()
        assert len(history) == 1


# ── ConfidenceOrchestrator ────────────────────

class TestConfidenceOrchestrator:
    """ConfidenceOrchestrator testleri."""

    def setup_method(self):
        from app.core.confidence.confidence_orchestrator import (
            ConfidenceOrchestrator,
        )
        self.orch = ConfidenceOrchestrator(
            auto_execute_threshold=0.8,
            ask_human_threshold=0.3,
            trust_decay_rate=0.01,
        )

    def test_make_decision_high_confidence(self):
        # Trust baslatarak guven yukselt
        for _ in range(5):
            self.orch.trust.record_success("test", 0.1)
        r = self.orch.make_decision(
            "a1",
            factors={"historical_accuracy": 0.99, "data_quality": 0.99,
                     "model_certainty": 0.99, "context_familiarity": 0.99},
            domain="test",
        )
        assert r["decision"] == "auto_execute"
        assert self.orch.total_decisions == 1

    def test_make_decision_low_confidence(self):
        r = self.orch.make_decision(
            "a1",
            factors={"historical_accuracy": 0.1, "data_quality": 0.1,
                     "model_certainty": 0.1, "context_familiarity": 0.1},
        )
        assert r["decision"] in ("ask_human", "reject")

    def test_make_decision_with_domain(self):
        r = self.orch.make_decision(
            "a1",
            factors={"historical_accuracy": 0.9, "data_quality": 0.9,
                     "model_certainty": 0.9, "context_familiarity": 0.9},
            domain="security",
        )
        assert r["domain"] == "security"

    def test_record_result_correct(self):
        r = self.orch.record_result(
            "a1", "success", "success", domain="test"
        )
        assert r["correct"] is True
        assert r["trust_updated"] is True

    def test_record_result_incorrect(self):
        r = self.orch.record_result(
            "a1", "success", "failure", domain="test"
        )
        assert r["correct"] is False

    def test_get_status(self):
        self.orch.make_decision(
            "a1",
            factors={"historical_accuracy": 0.9, "data_quality": 0.9,
                     "model_certainty": 0.9, "context_familiarity": 0.9},
        )
        status = self.orch.get_status()
        assert status["total_decisions"] == 1
        assert "calibration" in status
        assert "overall_accuracy" in status

    def test_get_analytics(self):
        self.orch.make_decision(
            "a1",
            factors={"historical_accuracy": 0.9, "data_quality": 0.9,
                     "model_certainty": 0.9, "context_familiarity": 0.9},
        )
        analytics = self.orch.get_analytics()
        assert "accuracy" in analytics
        assert "brier_score" in analytics
        assert "trust_levels" in analytics

    def test_auto_rate(self):
        self.orch.make_decision(
            "a1",
            factors={"historical_accuracy": 0.95, "data_quality": 0.95,
                     "model_certainty": 0.95, "context_familiarity": 0.95},
        )
        assert self.orch.auto_rate > 0

    def test_auto_rate_empty(self):
        assert self.orch.auto_rate == 0.0

    def test_multiple_decisions(self):
        for i in range(5):
            self.orch.make_decision(
                f"a{i}",
                factors={"a": 0.9},
                domain="test",
            )
        assert self.orch.total_decisions == 5

    def test_trust_affects_decision(self):
        # Build trust
        for _ in range(5):
            self.orch.trust.record_success("trusted_domain", 0.1)
        r = self.orch.make_decision(
            "a1",
            factors={"historical_accuracy": 0.7, "data_quality": 0.7,
                     "model_certainty": 0.7, "context_familiarity": 0.7},
            domain="trusted_domain",
        )
        assert r["trust_score"] > 0.5

    def test_escalation_on_low_confidence(self):
        self.orch.make_decision(
            "a1",
            factors={"historical_accuracy": 0.1, "data_quality": 0.1,
                     "model_certainty": 0.1, "context_familiarity": 0.1},
        )
        assert self.orch.escalation.pending_count >= 1

    def test_feedback_integration(self):
        self.orch.feedback.collect_decision(
            "a1", "approve", system_suggestion="approve"
        )
        assert self.orch.feedback.feedback_count == 1

    def test_calibration_integration(self):
        self.orch.make_decision(
            "a1", factors={"a": 0.9}, domain="test"
        )
        self.orch.record_result("a1", "success", "success", domain="test")
        assert self.orch.calibration.sample_count >= 1
