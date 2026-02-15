"""ATLAS Cross-System Learning Transfer testleri."""

import pytest

from app.core.learntransfer import (
    KnowledgeAdapter,
    KnowledgeExtractor,
    KnowledgeInjector,
    KnowledgeNetwork,
    LearnTransferOrchestrator,
    SimilarityAnalyzer,
    TransferFeedbackLoop,
    TransferTracker,
    TransferValidator,
)
from app.models.learntransfer_models import (
    AdaptationMethod,
    FeedbackType,
    KnowledgeRecord,
    KnowledgeType,
    LearnTransferSnapshot,
    SimilarityDimension,
    SimilarityResult,
    TransferRecord,
    TransferRisk,
    TransferStatus,
)


# ── Model testleri ──


class TestLearnTransferModels:
    """Model testleri."""

    def test_transfer_status_enum(self) -> None:
        assert TransferStatus.pending == "pending"
        assert TransferStatus.completed == "completed"
        assert TransferStatus.rolled_back == "rolled_back"

    def test_knowledge_type_enum(self) -> None:
        assert KnowledgeType.pattern == "pattern"
        assert KnowledgeType.strategy == "strategy"
        assert KnowledgeType.lesson == "lesson"

    def test_similarity_dimension_enum(self) -> None:
        assert SimilarityDimension.domain == "domain"
        assert SimilarityDimension.task == "task"
        assert SimilarityDimension.context == "context"

    def test_transfer_risk_enum(self) -> None:
        assert TransferRisk.low == "low"
        assert TransferRisk.critical == "critical"

    def test_feedback_type_enum(self) -> None:
        assert FeedbackType.positive == "positive"
        assert FeedbackType.negative == "negative"

    def test_adaptation_method_enum(self) -> None:
        assert AdaptationMethod.direct == "direct"
        assert AdaptationMethod.scaled == "scaled"
        assert AdaptationMethod.hybrid == "hybrid"

    def test_knowledge_record(self) -> None:
        r = KnowledgeRecord(
            source_system="sys_a",
            knowledge_type=KnowledgeType.rule,
            confidence=0.9,
        )
        assert r.knowledge_id
        assert r.source_system == "sys_a"
        assert r.confidence == 0.9

    def test_transfer_record(self) -> None:
        r = TransferRecord(
            source_system="a",
            target_system="b",
        )
        assert r.transfer_id
        assert r.status == TransferStatus.pending

    def test_similarity_result(self) -> None:
        s = SimilarityResult(
            source="a", target="b",
            overall_score=0.75,
            transfer_potential="high",
        )
        assert s.overall_score == 0.75

    def test_snapshot(self) -> None:
        s = LearnTransferSnapshot(
            total_knowledge=10,
            total_transfers=5,
            success_rate=80.0,
        )
        assert s.total_knowledge == 10


# ── KnowledgeExtractor testleri ──


class TestKnowledgeExtractor:
    """KnowledgeExtractor testleri."""

    def setup_method(self) -> None:
        self.ext = KnowledgeExtractor()

    def test_extract_learning(self) -> None:
        result = self.ext.extract_learning(
            "sys_a",
            {
                "outcome": "success",
                "parameters": {"rate": 0.1},
                "content": {"rule": "abc"},
                "tags": ["ml"],
            },
        )
        assert result["extracted"] is True
        assert result["source_system"] == "sys_a"
        assert result["confidence"] > 0

    def test_extract_failure(self) -> None:
        result = self.ext.extract_learning(
            "sys_b",
            {
                "outcome": "failure",
                "error": "timeout",
                "root_causes": ["slow network"],
            },
        )
        assert result["lessons"] >= 1

    def test_extract_with_repeats(self) -> None:
        result = self.ext.extract_learning(
            "sys_c",
            {
                "outcome": "success",
                "repeats": 10,
                "parameters": {},
            },
        )
        assert result["confidence"] >= 0.7

    def test_abstract_pattern(self) -> None:
        r = self.ext.extract_learning(
            "sys_d",
            {
                "outcome": "success",
                "parameters": {"x": 1},
                "content": {},
            },
        )
        result = self.ext.abstract_pattern(
            r["knowledge_id"],
        )
        assert result["abstracted"] is True

    def test_abstract_not_found(self) -> None:
        result = self.ext.abstract_pattern("nope")
        assert "error" in result

    def test_get_knowledge(self) -> None:
        r = self.ext.extract_learning(
            "sys_e", {"outcome": "success"},
        )
        result = self.ext.get_knowledge(
            r["knowledge_id"],
        )
        assert result["source_system"] == "sys_e"

    def test_get_knowledge_not_found(self) -> None:
        result = self.ext.get_knowledge("nope")
        assert "error" in result

    def test_list_by_source(self) -> None:
        self.ext.extract_learning(
            "sys_f", {"outcome": "success"},
        )
        self.ext.extract_learning(
            "sys_f", {"outcome": "failure"},
        )
        self.ext.extract_learning(
            "sys_g", {"outcome": "success"},
        )
        result = self.ext.list_by_source("sys_f")
        assert len(result) == 2

    def test_knowledge_count(self) -> None:
        self.ext.extract_learning(
            "a", {"outcome": "success"},
        )
        self.ext.extract_learning(
            "b", {"outcome": "success"},
        )
        assert self.ext.knowledge_count == 2


# ── SimilarityAnalyzer testleri ──


class TestSimilarityAnalyzer:
    """SimilarityAnalyzer testleri."""

    def setup_method(self) -> None:
        self.analyzer = SimilarityAnalyzer(
            min_threshold=0.3,
        )

    def test_analyze_similarity_high(self) -> None:
        result = self.analyzer.analyze_similarity(
            {
                "system_id": "a",
                "domains": ["ml", "nlp"],
                "task_types": ["classify", "predict"],
                "components": ["model", "data"],
                "context_tags": ["prod", "fast"],
            },
            {
                "system_id": "b",
                "domains": ["ml", "nlp"],
                "task_types": ["classify", "predict"],
                "components": ["model", "data"],
                "context_tags": ["prod", "fast"],
            },
        )
        assert result["overall_score"] == 1.0
        assert result["transfer_potential"] == "high"

    def test_analyze_similarity_low(self) -> None:
        result = self.analyzer.analyze_similarity(
            {
                "system_id": "a",
                "domains": ["ml"],
                "task_types": ["classify"],
                "components": ["model"],
                "context_tags": ["prod"],
            },
            {
                "system_id": "b",
                "domains": ["web"],
                "task_types": ["render"],
                "components": ["frontend"],
                "context_tags": ["dev"],
            },
        )
        assert result["overall_score"] < 0.3
        assert result["transfer_potential"] == "low"

    def test_analyze_empty_fields(self) -> None:
        result = self.analyzer.analyze_similarity(
            {"system_id": "a"},
            {"system_id": "b"},
        )
        # Empty fields default to 0.5
        assert result["overall_score"] == 0.5

    def test_dimension_scores(self) -> None:
        result = self.analyzer.analyze_similarity(
            {
                "system_id": "a",
                "domains": ["ml", "data"],
                "task_types": ["train"],
                "components": [],
                "context_tags": ["prod"],
            },
            {
                "system_id": "b",
                "domains": ["ml"],
                "task_types": ["predict"],
                "components": [],
                "context_tags": ["prod"],
            },
        )
        dims = result["dimension_scores"]
        assert "domain" in dims
        assert "task" in dims
        assert "structure" in dims
        assert "context" in dims

    def test_find_similar_systems(self) -> None:
        source = {
            "system_id": "src",
            "domains": ["ml"],
            "task_types": ["predict"],
        }
        candidates = [
            {
                "system_id": "c1",
                "domains": ["ml"],
                "task_types": ["predict"],
            },
            {
                "system_id": "c2",
                "domains": ["web"],
                "task_types": ["render"],
            },
        ]
        results = (
            self.analyzer.find_similar_systems(
                source, candidates,
            )
        )
        assert len(results) >= 1
        assert results[0]["target"] == "c1"

    def test_get_analysis(self) -> None:
        self.analyzer.analyze_similarity(
            {"system_id": "x", "domains": ["a"]},
            {"system_id": "y", "domains": ["a"]},
        )
        result = self.analyzer.get_analysis(
            "x", "y",
        )
        assert result["source"] == "x"

    def test_get_analysis_not_found(self) -> None:
        result = self.analyzer.get_analysis(
            "no", "pe",
        )
        assert "error" in result

    def test_analysis_count(self) -> None:
        self.analyzer.analyze_similarity(
            {"system_id": "a"},
            {"system_id": "b"},
        )
        assert self.analyzer.analysis_count == 1


# ── KnowledgeAdapter testleri ──


class TestKnowledgeAdapter:
    """KnowledgeAdapter testleri."""

    def setup_method(self) -> None:
        self.adapter = KnowledgeAdapter()

    def test_direct_adapt(self) -> None:
        result = self.adapter.adapt_knowledge(
            {
                "knowledge_id": "k1",
                "content": {"rule": "abc"},
                "confidence": 0.8,
            },
            {"system_id": "target"},
            method="direct",
        )
        assert result["adapted"] is True
        assert result["method"] == "direct"

    def test_scaled_adapt(self) -> None:
        result = self.adapter.adapt_knowledge(
            {
                "knowledge_id": "k2",
                "content": {"rate": 100},
                "confidence": 0.7,
                "scale": 1.0,
            },
            {"system_id": "t", "scale": 2.0},
            method="scaled",
        )
        assert result["adapted"] is True
        assert result["method"] == "scaled"

    def test_translated_adapt(self) -> None:
        result = self.adapter.adapt_knowledge(
            {
                "knowledge_id": "k3",
                "content": {"error_rate": 0.05},
                "confidence": 0.6,
            },
            {
                "system_id": "t",
                "term_mapping": {
                    "error_rate": "failure_pct",
                },
            },
            method="translated",
        )
        assert result["adapted"] is True

    def test_constrained_adapt(self) -> None:
        result = self.adapter.adapt_knowledge(
            {
                "knowledge_id": "k4",
                "content": {"threshold": 200},
                "confidence": 0.9,
            },
            {
                "system_id": "t",
                "constraints": {
                    "threshold": {
                        "min": 0, "max": 100,
                    },
                },
            },
            method="constrained",
        )
        assert result["adapted"] is True

    def test_confidence_calculation(self) -> None:
        r = self.adapter.adapt_knowledge(
            {
                "knowledge_id": "k5",
                "content": {},
                "confidence": 1.0,
            },
            {"system_id": "t"},
            method="direct",
        )
        assert r["confidence"] == 0.9

        r2 = self.adapter.adapt_knowledge(
            {
                "knowledge_id": "k6",
                "content": {},
                "confidence": 1.0,
            },
            {"system_id": "t"},
            method="translated",
        )
        assert r2["confidence"] == 0.7

    def test_get_adaptation(self) -> None:
        r = self.adapter.adapt_knowledge(
            {
                "knowledge_id": "k7",
                "content": {},
                "confidence": 0.5,
            },
            {"system_id": "t"},
        )
        result = self.adapter.get_adaptation(
            r["adaptation_id"],
        )
        assert result["knowledge_id"] == "k7"

    def test_get_adaptation_not_found(self) -> None:
        result = self.adapter.get_adaptation("nope")
        assert "error" in result

    def test_adaptation_count(self) -> None:
        self.adapter.adapt_knowledge(
            {"knowledge_id": "a", "content": {}, "confidence": 0.5},
            {"system_id": "t"},
        )
        self.adapter.adapt_knowledge(
            {"knowledge_id": "b", "content": {}, "confidence": 0.5},
            {"system_id": "t"},
        )
        assert self.adapter.adaptation_count == 2


# ── TransferValidator testleri ──


class TestTransferValidator:
    """TransferValidator testleri."""

    def setup_method(self) -> None:
        self.val = TransferValidator()

    def test_validate_approved(self) -> None:
        result = self.val.validate_transfer(
            {
                "knowledge_id": "k1",
                "knowledge_type": "pattern",
                "confidence": 0.9,
                "content": {"safe": True},
                "rules": [],
            },
            "target_sys",
            {},
        )
        assert result["approved"] is True
        assert result["risk_level"] == "low"

    def test_validate_rejected_low_confidence(self) -> None:
        result = self.val.validate_transfer(
            {
                "knowledge_id": "k2",
                "knowledge_type": "pattern",
                "confidence": 0.2,
                "content": {},
                "rules": [],
            },
            "target_sys",
            {"is_critical": True},
        )
        assert result["approved"] is False

    def test_validate_rejected_unsafe(self) -> None:
        result = self.val.validate_transfer(
            {
                "knowledge_id": "k3",
                "knowledge_type": "rule",
                "confidence": 0.9,
                "content": {"cmd": "rm_rf /"},
                "rules": [],
            },
            "target_sys",
            {},
        )
        assert result["approved"] is False

    def test_validate_conflict_detection(self) -> None:
        result = self.val.validate_transfer(
            {
                "knowledge_id": "k4",
                "knowledge_type": "rule",
                "confidence": 0.8,
                "content": {},
                "rules": [
                    {"condition": "x>5", "outcome": "reject"},
                ],
            },
            "target_sys",
            {
                "existing_rules": [
                    {"condition": "x>5", "outcome": "accept"},
                ],
            },
        )
        conflict_check = next(
            c for c in result["checks"]
            if c["check"] == "conflict_detection"
        )
        assert not conflict_check["passed"]

    def test_validate_unsupported_type(self) -> None:
        result = self.val.validate_transfer(
            {
                "knowledge_id": "k5",
                "knowledge_type": "unknown_type",
                "confidence": 0.9,
                "content": {},
                "rules": [],
            },
            "target_sys",
            {"supported_types": ["pattern"]},
        )
        assert result["approved"] is False

    def test_get_validation(self) -> None:
        r = self.val.validate_transfer(
            {
                "knowledge_id": "k6",
                "knowledge_type": "pattern",
                "confidence": 0.8,
                "content": {},
                "rules": [],
            },
            "t", {},
        )
        result = self.val.get_validation(
            r["validation_id"],
        )
        assert result["knowledge_id"] == "k6"

    def test_get_validation_not_found(self) -> None:
        result = self.val.get_validation("nope")
        assert "error" in result

    def test_validation_count(self) -> None:
        self.val.validate_transfer(
            {"knowledge_id": "a", "knowledge_type": "pattern",
             "confidence": 0.8, "content": {}, "rules": []},
            "t", {},
        )
        assert self.val.validation_count == 1

    def test_approval_rate(self) -> None:
        self.val.validate_transfer(
            {"knowledge_id": "a", "knowledge_type": "pattern",
             "confidence": 0.9, "content": {}, "rules": []},
            "t", {},
        )
        self.val.validate_transfer(
            {"knowledge_id": "b", "knowledge_type": "pattern",
             "confidence": 0.1, "content": {}, "rules": []},
            "t", {"is_critical": True},
        )
        assert self.val.approval_rate == 50.0

    def test_approval_rate_empty(self) -> None:
        assert self.val.approval_rate == 0.0


# ── KnowledgeInjector testleri ──


class TestKnowledgeInjector:
    """KnowledgeInjector testleri."""

    def setup_method(self) -> None:
        self.inj = KnowledgeInjector()

    def test_inject_append(self) -> None:
        result = self.inj.inject_knowledge(
            "sys_a",
            {"knowledge_id": "k1", "data": "x"},
        )
        assert result["injected"] is True

    def test_inject_replace(self) -> None:
        self.inj.inject_knowledge(
            "sys_b",
            {"knowledge_id": "k1", "data": "old"},
        )
        result = self.inj.inject_knowledge(
            "sys_b",
            {"knowledge_id": "k1", "data": "new"},
            merge_strategy="replace",
        )
        assert result["injected"] is True
        items = self.inj.get_target_knowledge(
            "sys_b",
        )
        assert len(items) == 1
        assert items[0]["data"] == "new"

    def test_inject_merge(self) -> None:
        self.inj.inject_knowledge(
            "sys_c",
            {"knowledge_id": "k1", "v": 1},
        )
        self.inj.inject_knowledge(
            "sys_c",
            {"knowledge_id": "k1", "v": 2, "extra": True},
            merge_strategy="merge",
        )
        items = self.inj.get_target_knowledge(
            "sys_c",
        )
        assert len(items) == 1
        assert items[0]["v"] == 2

    def test_rollback(self) -> None:
        r = self.inj.inject_knowledge(
            "sys_d",
            {"knowledge_id": "k1"},
        )
        assert len(
            self.inj.get_target_knowledge("sys_d"),
        ) == 1

        result = self.inj.rollback(
            r["injection_id"],
        )
        assert result["rolled_back"] is True
        assert len(
            self.inj.get_target_knowledge("sys_d"),
        ) == 0

    def test_rollback_not_available(self) -> None:
        result = self.inj.rollback("nope")
        assert "error" in result

    def test_verify_injection(self) -> None:
        r = self.inj.inject_knowledge(
            "sys_e",
            {"knowledge_id": "k1"},
        )
        result = self.inj.verify_injection(
            r["injection_id"],
        )
        assert result["verified"] is True

    def test_verify_after_rollback(self) -> None:
        r = self.inj.inject_knowledge(
            "sys_f",
            {"knowledge_id": "k1"},
        )
        self.inj.rollback(r["injection_id"])
        result = self.inj.verify_injection(
            r["injection_id"],
        )
        assert result["verified"] is False

    def test_verify_not_found(self) -> None:
        result = self.inj.verify_injection("nope")
        assert "error" in result

    def test_get_injection(self) -> None:
        r = self.inj.inject_knowledge(
            "sys_g", {"knowledge_id": "k1"},
        )
        result = self.inj.get_injection(
            r["injection_id"],
        )
        assert result["target_system"] == "sys_g"

    def test_get_injection_not_found(self) -> None:
        result = self.inj.get_injection("nope")
        assert "error" in result

    def test_injection_count(self) -> None:
        self.inj.inject_knowledge(
            "a", {"knowledge_id": "k1"},
        )
        self.inj.inject_knowledge(
            "b", {"knowledge_id": "k2"},
        )
        assert self.inj.injection_count == 2

    def test_rollback_count(self) -> None:
        r = self.inj.inject_knowledge(
            "c", {"knowledge_id": "k1"},
        )
        self.inj.rollback(r["injection_id"])
        assert self.inj.rollback_count == 1


# ── TransferTracker testleri ──


class TestTransferTracker:
    """TransferTracker testleri."""

    def setup_method(self) -> None:
        self.tracker = TransferTracker()

    def test_track_transfer(self) -> None:
        result = self.tracker.track_transfer(
            "a", "b", "k1",
        )
        assert result["tracked"] is True

    def test_record_outcome_success(self) -> None:
        r = self.tracker.track_transfer(
            "a", "b", "k1",
        )
        result = self.tracker.record_outcome(
            r["transfer_id"],
            success=True,
            impact_score=0.8,
        )
        assert result["outcome"] == "success"

    def test_record_outcome_failure(self) -> None:
        r = self.tracker.track_transfer(
            "a", "b", "k1",
        )
        result = self.tracker.record_outcome(
            r["transfer_id"],
            success=False,
        )
        assert result["outcome"] == "failure"

    def test_record_not_found(self) -> None:
        result = self.tracker.record_outcome(
            "nope", success=True,
        )
        assert "error" in result

    def test_measure_success(self) -> None:
        r = self.tracker.track_transfer(
            "a", "b", "k1",
        )
        result = self.tracker.measure_success(
            r["transfer_id"],
            {"accuracy": 0.9, "speed": 0.7},
        )
        assert result["success_score"] == 0.8

    def test_measure_not_found(self) -> None:
        result = self.tracker.measure_success(
            "nope", {},
        )
        assert "error" in result

    def test_analyze_impact(self) -> None:
        r = self.tracker.track_transfer(
            "a", "b", "k1",
        )
        self.tracker.record_outcome(
            r["transfer_id"],
            success=True,
            impact_score=0.8,
        )
        result = self.tracker.analyze_impact(
            r["transfer_id"],
        )
        assert result["impact_level"] == "high"

    def test_analyze_impact_not_found(self) -> None:
        result = self.tracker.analyze_impact("nope")
        assert "error" in result

    def test_get_history(self) -> None:
        self.tracker.track_transfer("a", "b", "k1")
        self.tracker.track_transfer("c", "d", "k2")
        result = self.tracker.get_history()
        assert len(result) == 2

    def test_get_history_filtered(self) -> None:
        self.tracker.track_transfer("a", "b", "k1")
        self.tracker.track_transfer("c", "d", "k2")
        result = self.tracker.get_history("a")
        assert len(result) == 1

    def test_get_attribution(self) -> None:
        r1 = self.tracker.track_transfer(
            "a", "target", "k1",
        )
        r2 = self.tracker.track_transfer(
            "b", "target", "k2",
        )
        self.tracker.record_outcome(
            r1["transfer_id"], success=True,
        )
        self.tracker.record_outcome(
            r2["transfer_id"], success=True,
        )
        result = self.tracker.get_attribution(
            "target",
        )
        assert result["total_transfers"] == 2
        assert "a" in result["sources"]

    def test_get_transfer(self) -> None:
        r = self.tracker.track_transfer(
            "a", "b", "k1",
        )
        result = self.tracker.get_transfer(
            r["transfer_id"],
        )
        assert result["source_system"] == "a"

    def test_get_transfer_not_found(self) -> None:
        result = self.tracker.get_transfer("nope")
        assert "error" in result

    def test_transfer_count(self) -> None:
        self.tracker.track_transfer("a", "b", "k1")
        assert self.tracker.transfer_count == 1

    def test_success_rate(self) -> None:
        r1 = self.tracker.track_transfer(
            "a", "b", "k1",
        )
        r2 = self.tracker.track_transfer(
            "c", "d", "k2",
        )
        self.tracker.record_outcome(
            r1["transfer_id"], success=True,
        )
        self.tracker.record_outcome(
            r2["transfer_id"], success=False,
        )
        assert self.tracker.success_rate == 50.0

    def test_success_rate_empty(self) -> None:
        assert self.tracker.success_rate == 0.0


# ── TransferFeedbackLoop testleri ──


class TestTransferFeedbackLoop:
    """TransferFeedbackLoop testleri."""

    def setup_method(self) -> None:
        self.loop = TransferFeedbackLoop()

    def test_collect_feedback(self) -> None:
        result = self.loop.collect_feedback(
            "tr1", "positive", 0.9,
        )
        assert result["collected"] is True

    def test_measure_effectiveness(self) -> None:
        self.loop.collect_feedback(
            "tr1", "positive", 0.8,
        )
        self.loop.collect_feedback(
            "tr1", "positive", 0.6,
        )
        result = self.loop.measure_effectiveness(
            "tr1",
        )
        assert result["effectiveness"] == 0.7
        assert result["feedback_count"] == 2

    def test_measure_empty(self) -> None:
        result = self.loop.measure_effectiveness(
            "nope",
        )
        assert result["effectiveness"] == 0.0

    def test_learn_from_failure(self) -> None:
        result = self.loop.learn_from_failure(
            "tr2", "domain_mismatch",
            {"domain": "ml"},
        )
        assert result["learned"] is True
        assert result["occurrences"] == 1

    def test_learn_recurring(self) -> None:
        self.loop.learn_from_failure(
            "tr3", "scale_issue",
        )
        result = self.loop.learn_from_failure(
            "tr4", "scale_issue",
        )
        assert result["occurrences"] == 2

    def test_refine_transfer(self) -> None:
        result = self.loop.refine_transfer(
            "tr5",
            {"threshold": 0.5},
        )
        assert result["refined"] is True

    def test_optimize_matching(self) -> None:
        self.loop.learn_from_failure(
            "a", "bad_match",
        )
        self.loop.learn_from_failure(
            "b", "bad_match",
        )
        result = self.loop.optimize_matching()
        assert result["recurring_failures"] >= 1

    def test_get_feedback(self) -> None:
        self.loop.collect_feedback(
            "tr6", "positive", 0.9,
        )
        result = self.loop.get_feedback("tr6")
        assert len(result) == 1

    def test_feedback_count(self) -> None:
        self.loop.collect_feedback(
            "a", "positive", 0.8,
        )
        self.loop.collect_feedback(
            "b", "negative", 0.2,
        )
        assert self.loop.feedback_count == 2

    def test_improvement_count(self) -> None:
        self.loop.refine_transfer("a", {"x": 1})
        assert self.loop.improvement_count == 1

    def test_pattern_count(self) -> None:
        self.loop.learn_from_failure(
            "a", "reason1",
        )
        self.loop.learn_from_failure(
            "b", "reason2",
        )
        assert self.loop.pattern_count == 2


# ── KnowledgeNetwork testleri ──


class TestKnowledgeNetwork:
    """KnowledgeNetwork testleri."""

    def setup_method(self) -> None:
        self.net = KnowledgeNetwork()

    def test_add_node(self) -> None:
        result = self.net.add_node(
            "sys_a", "system",
        )
        assert result["added"] is True

    def test_add_edge(self) -> None:
        self.net.add_node("a")
        self.net.add_node("b")
        result = self.net.add_edge(
            "a", "b", "transfers_to",
        )
        assert result["added"] is True

    def test_add_edge_not_found(self) -> None:
        result = self.net.add_edge(
            "no", "pe", "test",
        )
        assert "error" in result

    def test_find_paths(self) -> None:
        self.net.add_node("a")
        self.net.add_node("b")
        self.net.add_node("c")
        self.net.add_edge("a", "b")
        self.net.add_edge("b", "c")
        result = self.net.find_propagation_paths(
            "a", "c",
        )
        assert result["path_count"] >= 1
        assert result["shortest_length"] == 3

    def test_find_paths_none(self) -> None:
        self.net.add_node("x")
        self.net.add_node("y")
        result = self.net.find_propagation_paths(
            "x", "y",
        )
        assert result["path_count"] == 0

    def test_find_paths_not_found(self) -> None:
        result = self.net.find_propagation_paths(
            "no", "pe",
        )
        assert "error" in result

    def test_get_relationships(self) -> None:
        self.net.add_node("a")
        self.net.add_node("b")
        self.net.add_edge("a", "b")
        result = self.net.get_relationships("a")
        assert result["outgoing_count"] == 1
        assert result["incoming_count"] == 0

    def test_get_relationships_not_found(self) -> None:
        result = self.net.get_relationships("nope")
        assert "error" in result

    def test_get_influence(self) -> None:
        self.net.add_node("a")
        self.net.add_node("b")
        self.net.add_edge("a", "b", weight=2.0)
        result = self.net.get_influence("a")
        assert result["influence_score"] == 2.0

    def test_get_influence_not_found(self) -> None:
        result = self.net.get_influence("nope")
        assert "error" in result

    def test_visualization_data(self) -> None:
        self.net.add_node("a")
        self.net.add_node("b")
        self.net.add_edge("a", "b")
        result = self.net.get_visualization_data()
        assert result["node_count"] == 2
        assert result["edge_count"] == 1

    def test_get_node(self) -> None:
        self.net.add_node("a", "system", {"v": 1})
        result = self.net.get_node("a")
        assert result["node_type"] == "system"

    def test_get_node_not_found(self) -> None:
        result = self.net.get_node("nope")
        assert "error" in result

    def test_node_count(self) -> None:
        self.net.add_node("a")
        self.net.add_node("b")
        assert self.net.node_count == 2

    def test_edge_count(self) -> None:
        self.net.add_node("a")
        self.net.add_node("b")
        self.net.add_edge("a", "b")
        assert self.net.edge_count == 1


# ── LearnTransferOrchestrator testleri ──


class TestLearnTransferOrchestrator:
    """LearnTransferOrchestrator testleri."""

    def setup_method(self) -> None:
        self.orch = LearnTransferOrchestrator(
            min_similarity=0.3,
            auto_transfer=False,
            require_validation=True,
        )

    def test_init(self) -> None:
        assert self.orch.extractor is not None
        assert self.orch.analyzer is not None
        assert self.orch.network is not None

    def test_transfer_knowledge(self) -> None:
        result = self.orch.transfer_knowledge(
            "sys_a", "sys_b",
            {
                "outcome": "success",
                "parameters": {"x": 1},
                "content": {"rule": "do_x"},
            },
            {"system_id": "sys_b"},
        )
        assert result["transferred"] is True
        assert "transfer_id" in result

    def test_transfer_validation_fail(self) -> None:
        result = self.orch.transfer_knowledge(
            "sys_c", "sys_d",
            {
                "outcome": "success",
                "content": {"cmd": "delete_all"},
            },
            {"system_id": "sys_d"},
        )
        assert result["transferred"] is False

    def test_transfer_no_validation(self) -> None:
        orch = LearnTransferOrchestrator(
            require_validation=False,
        )
        result = orch.transfer_knowledge(
            "a", "b",
            {"outcome": "success", "content": {}},
            {"system_id": "b"},
        )
        assert result["transferred"] is True

    def test_find_opportunities(self) -> None:
        result = (
            self.orch
            .find_transfer_opportunities(
                {
                    "system_id": "src",
                    "domains": ["ml"],
                },
                [
                    {
                        "system_id": "c1",
                        "domains": ["ml"],
                    },
                    {
                        "system_id": "c2",
                        "domains": ["web"],
                    },
                ],
            )
        )
        assert result["opportunity_count"] >= 1

    def test_get_analytics(self) -> None:
        self.orch.transfer_knowledge(
            "a", "b",
            {"outcome": "success", "content": {}},
            {"system_id": "b"},
        )
        result = self.orch.get_analytics()
        assert result["pipelines_run"] >= 1
        assert result["knowledge_extracted"] >= 1

    def test_get_status(self) -> None:
        result = self.orch.get_status()
        assert "pipelines_run" in result
        assert "total_knowledge" in result

    def test_pipelines_run(self) -> None:
        self.orch.transfer_knowledge(
            "x", "y",
            {"outcome": "success", "content": {}},
            {"system_id": "y"},
        )
        assert self.orch.pipelines_run >= 1

    def test_full_integration(self) -> None:
        orch = LearnTransferOrchestrator(
            require_validation=True,
        )

        # Transfer 1
        r1 = orch.transfer_knowledge(
            "agent_a", "agent_b",
            {
                "outcome": "success",
                "parameters": {"lr": 0.01},
                "content": {"strategy": "slow_start"},
            },
            {"system_id": "agent_b"},
        )
        assert r1["transferred"] is True

        # Transfer 2
        r2 = orch.transfer_knowledge(
            "agent_a", "agent_c",
            {
                "outcome": "success",
                "content": {"approach": "retry"},
            },
            {"system_id": "agent_c"},
        )
        assert r2["transferred"] is True

        analytics = orch.get_analytics()
        assert analytics["pipelines_run"] == 2
        assert analytics["network_nodes"] >= 2


# ── Init & Config testleri ──


class TestLearnTransferInit:
    """Init import testleri."""

    def test_imports(self) -> None:
        from app.core.learntransfer import (
            KnowledgeAdapter,
            KnowledgeExtractor,
            KnowledgeInjector,
            KnowledgeNetwork,
            LearnTransferOrchestrator,
            SimilarityAnalyzer,
            TransferFeedbackLoop,
            TransferTracker,
            TransferValidator,
        )
        assert KnowledgeExtractor is not None
        assert SimilarityAnalyzer is not None
        assert LearnTransferOrchestrator is not None

    def test_instantiate_all(self) -> None:
        assert KnowledgeExtractor()
        assert SimilarityAnalyzer()
        assert KnowledgeAdapter()
        assert TransferValidator()
        assert KnowledgeInjector()
        assert TransferTracker()
        assert TransferFeedbackLoop()
        assert KnowledgeNetwork()
        assert LearnTransferOrchestrator()


class TestLearnTransferConfig:
    """Config testleri."""

    def test_config_defaults(self) -> None:
        from app.config import settings

        assert settings.learntransfer_enabled is True
        assert settings.min_similarity_threshold == 0.3
        assert settings.auto_transfer is False
        assert settings.require_transfer_validation is True
        assert settings.max_transfer_age_days == 90
