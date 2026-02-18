"""
AI Safety & Hallucination Guard testleri.
"""

import pytest

from app.core.aisafety.hallucination_detector import (
    HallucinationDetector,
)
from app.core.aisafety.fact_checker import (
    FactChecker,
)
from app.core.aisafety.source_verifier import (
    SourceVerifier,
)
from app.core.aisafety.consistency_analyzer import (
    ConsistencyAnalyzer,
)
from app.core.aisafety.confidence_calibrator import (
    AIConfidenceCalibrator,
)
from app.core.aisafety.uncertainty_flagger import (
    UncertaintyFlagger,
)
from app.core.aisafety.human_escalation_trigger import (
    HumanEscalationTrigger,
)
from app.core.aisafety.safety_boundary_enforcer import (
    SafetyBoundaryEnforcer,
)
from app.core.aisafety.aisafety_orchestrator import (
    AISafetyOrchestrator,
)
from app.models.aisafety_models import (
    RiskLevel,
    DetectionType,
    VerdictType,
    AuthorityLevel,
    BiasType,
    CalibrationState,
    FlagType,
    EscalationPriority,
    EscalationStatus,
    BoundaryAction,
    HallucinationDetection,
    FactCheckResult,
    SourceVerification,
    ConsistencyResult,
    CalibrationResult,
    UncertaintyFlag,
    EscalationRecord,
    SafetyCheckResult,
    AISafetySummary,
)


# ==========================================
# HallucinationDetector Testleri
# ==========================================


class TestHallucinationDetector:
    """HallucinationDetector testleri."""

    def setup_method(self):
        self.det = HallucinationDetector()

    def test_init(self):
        assert self.det.detection_count == 0

    def test_register_fact(self):
        r = self.det.register_fact(
            statement="Python 1991de cikti",
            source="wikipedia",
        )
        assert r["registered"] is True

    def test_check_response_no_sources(self):
        r = self.det.check_response(
            response_text="Test yaniti"
        )
        assert r["checked"] is True
        assert "risk_score" in r
        assert "risk_level" in r

    def test_check_response_with_claims(self):
        self.det.register_fact(
            statement=(
                "Dunya gunes etrafinda doner"
            ),
            source="bilim",
        )
        r = self.det.check_response(
            response_text="Test",
            claims=[
                "Dunya gunes etrafinda doner"
            ],
        )
        assert r["checked"] is True

    def test_check_response_with_sources(self):
        r = self.det.check_response(
            response_text="Bilgi",
            sources=["kaynak1"],
        )
        assert r["checked"] is True

    def test_contradiction_detection(self):
        text = (
            "Bu dogru ve guzel. "
            "Bu dogru ve guzel degil."
        )
        r = self.det.check_response(
            response_text=text
        )
        assert r["checked"] is True

    def test_confidence_analysis_uncertain(self):
        text = (
            "Belki bu dogru olabilir. "
            "Muhtemelen sanirim galiba."
        )
        r = self.det.check_response(
            response_text=text
        )
        assert r["checked"] is True

    def test_get_detection_info(self):
        r = self.det.check_response(
            response_text="Test"
        )
        info = self.det.get_detection_info(
            r["detection_id"]
        )
        assert info["retrieved"] is True

    def test_get_detection_info_not_found(self):
        info = self.det.get_detection_info(
            "yok"
        )
        assert info["retrieved"] is False

    def test_get_summary(self):
        s = self.det.get_summary()
        assert s["retrieved"] is True
        assert "total_detections" in s

    def test_risk_levels(self):
        assert len(self.det.RISK_LEVELS) == 5
        assert "critical" in self.det.RISK_LEVELS

    def test_detection_types(self):
        assert len(self.det.DETECTION_TYPES) == 6

    def test_high_risk_tracking(self):
        self.det.check_response(
            response_text="Test",
            claims=["a", "b", "c"],
        )
        s = self.det.get_summary()
        assert s["stats"]["checks_done"] >= 1


# ==========================================
# FactChecker Testleri
# ==========================================


class TestFactChecker:
    """FactChecker testleri."""

    def setup_method(self):
        self.fc = FactChecker()

    def test_init(self):
        assert self.fc.check_count == 0

    def test_add_fact(self):
        r = self.fc.add_fact(
            statement="Python 1991de cikti",
            source="wikipedia",
            category="teknoloji",
        )
        assert r["added"] is True
        assert "fact_id" in r

    def test_extract_claims(self):
        text = (
            "Python dunyanin en populer "
            "programlama dilidir. "
            "Yuzde 30 pazar payina sahiptir. "
            "Cok iyi bir dildir."
        )
        r = self.fc.extract_claims(text)
        assert r["extracted"] is True
        assert r["claims_found"] >= 1

    def test_extract_claims_with_numbers(self):
        text = (
            "Turkiye nufusu 85 milyondur. "
            "Istanbul 16 milyon insana ev "
            "sahipligi yapar."
        )
        r = self.fc.extract_claims(text)
        assert r["extracted"] is True

    def test_verify_claim_match(self):
        self.fc.add_fact(
            statement=(
                "Python programlama "
                "dili 1991 yilinda cikti"
            ),
            source="wiki",
            confidence=0.9,
        )
        r = self.fc.verify_claim(
            claim=(
                "Python programlama dili "
                "1991 yilinda gelistirildi"
            )
        )
        assert r["verified"] is True

    def test_verify_claim_no_match(self):
        r = self.fc.verify_claim(
            claim="Tamamen farkli bir konu"
        )
        assert r["verified"] is True
        assert r["verdict"] == "unverifiable"

    def test_check_text(self):
        self.fc.add_fact(
            statement=(
                "Python populer bir dildir"
            ),
            source="test",
        )
        r = self.fc.check_text(
            "Python populer bir dildir. "
            "Cok kullanilir."
        )
        assert r["checked"] is True
        assert "overall_score" in r

    def test_suggest_corrections(self):
        r = self.fc.check_text(
            "Bilinmeyen iddia."
        )
        corr = self.fc.suggest_corrections(
            r["check_id"]
        )
        assert corr["suggested"] is True

    def test_suggest_corrections_not_found(self):
        r = self.fc.suggest_corrections("yok")
        assert r["suggested"] is False

    def test_get_summary(self):
        s = self.fc.get_summary()
        assert s["retrieved"] is True
        assert "fact_db_size" in s

    def test_verdict_types(self):
        assert len(self.fc.VERDICT_TYPES) == 6

    def test_add_fact_with_metadata(self):
        r = self.fc.add_fact(
            statement="test",
            metadata={"key": "val"},
        )
        assert r["added"] is True


# ==========================================
# SourceVerifier Testleri
# ==========================================


class TestSourceVerifier:
    """SourceVerifier testleri."""

    def setup_method(self):
        self.sv = SourceVerifier()

    def test_init(self):
        assert self.sv.verification_count == 0

    def test_register_source(self):
        r = self.sv.register_source(
            name="Wikipedia",
            url="https://wikipedia.org",
            source_type="encyclopedia",
            authority_score=0.8,
        )
        assert r["registered"] is True

    def test_verify_known_source(self):
        self.sv.register_source(
            name="Wikipedia",
            authority_score=0.85,
        )
        r = self.sv.verify_source(
            source_name="Wikipedia"
        )
        assert r["verified"] is True
        assert r["is_reliable"] is True

    def test_verify_unknown_source(self):
        r = self.sv.verify_source(
            source_name="Unknown Blog"
        )
        assert r["verified"] is True

    def test_verify_with_date(self):
        r = self.sv.verify_source(
            source_name="Test",
            published_date="2025-01-15",
        )
        assert r["verified"] is True
        assert "recency" in r

    def test_verify_with_bias(self):
        self.sv.register_source(
            name="Biased Source",
            bias_type="commercial",
        )
        r = self.sv.verify_source(
            source_name="Biased Source"
        )
        assert r["verified"] is True
        assert r["bias"]["detected"] is True

    def test_verify_citation(self):
        r = self.sv.verify_citation(
            claim="Python populer bir dildir",
            cited_source="wiki",
            cited_text=(
                "Python en populer "
                "programlama dillerinden "
                "biridir"
            ),
        )
        assert r["checked"] is True

    def test_verify_citation_empty(self):
        r = self.sv.verify_citation(
            claim="test",
            cited_text="",
        )
        assert r["checked"] is True
        assert r["is_valid"] is False

    def test_get_summary(self):
        s = self.sv.get_summary()
        assert s["retrieved"] is True

    def test_authority_levels(self):
        assert len(self.sv.AUTHORITY_LEVELS) == 5

    def test_bias_types(self):
        assert len(self.sv.BIAS_TYPES) == 6

    def test_recency_no_date(self):
        r = self.sv.verify_source(
            source_name="Test",
            published_date="",
        )
        assert r["verified"] is True

    def test_register_source_with_url(self):
        self.sv.register_source(
            name="Test",
            url="https://test.com",
            authority_score=0.9,
        )
        r = self.sv.verify_source(
            source_name="Other",
            source_url="https://test.com",
        )
        assert r["verified"] is True


# ==========================================
# ConsistencyAnalyzer Testleri
# ==========================================


class TestConsistencyAnalyzer:
    """ConsistencyAnalyzer testleri."""

    def setup_method(self):
        self.ca = ConsistencyAnalyzer()

    def test_init(self):
        assert self.ca.analysis_count == 0

    def test_track_response(self):
        r = self.ca.track_response(
            response_text="Test yaniti",
            topic="genel",
        )
        assert r["tracked"] is True

    def test_internal_consistency_clean(self):
        text = (
            "Python iyi bir dildir. "
            "Kolay ogrenilebilir. "
            "Cok kullanilir."
        )
        r = self.ca.check_internal_consistency(
            text
        )
        assert r["analyzed"] is True
        assert r["is_consistent"] is True

    def test_internal_consistency_contradiction(self):
        text = (
            "Python cok hizli bir dildir. "
            "Python cok hizli bir dil degil."
        )
        r = self.ca.check_internal_consistency(
            text
        )
        assert r["analyzed"] is True

    def test_cross_consistency(self):
        self.ca.track_response(
            response_text=(
                "Python iyi bir dildir"
            ),
            topic="python",
        )
        r = self.ca.check_cross_consistency(
            current_text=(
                "Python iyi bir dildir"
            ),
            topic="python",
        )
        assert r["analyzed"] is True

    def test_cross_consistency_mismatch(self):
        self.ca.track_response(
            response_text=(
                "Python cok yavas ve "
                "kotu bir programlama dili"
            ),
            topic="python",
        )
        r = self.ca.check_cross_consistency(
            current_text=(
                "Java dunyanin en hizli "
                "ve guzel programlama dili"
            ),
            topic="python",
        )
        assert r["analyzed"] is True

    def test_check_logic(self):
        text = (
            "Her zaman basarili oluruz "
            "ve asla kaybetmeyiz."
        )
        r = self.ca.check_logic(text)
        assert r["analyzed"] is True

    def test_check_logic_contradiction(self):
        text = (
            "Everyone knows this. "
            "Nobody knows this."
        )
        r = self.ca.check_logic(text)
        assert r["analyzed"] is True
        assert r["issue_count"] >= 1

    def test_check_timeline(self):
        text = (
            "2020 yilinda basladik. "
            "2023 yilinda bitirdik."
        )
        r = self.ca.check_timeline(text)
        assert r["analyzed"] is True

    def test_full_analysis(self):
        r = self.ca.full_analysis(
            text="Test metin.",
            topic="test",
        )
        assert r["analyzed"] is True
        assert "overall_score" in r

    def test_get_summary(self):
        s = self.ca.get_summary()
        assert s["retrieved"] is True

    def test_history_limit(self):
        ca = ConsistencyAnalyzer(
            history_limit=3
        )
        for i in range(5):
            ca.track_response(
                response_text=f"Yanit {i}",
                topic="test",
            )
        assert len(ca._responses) <= 3

    def test_issue_types(self):
        assert (
            len(self.ca.ISSUE_TYPES) == 6
        )


# ==========================================
# AIConfidenceCalibrator Testleri
# ==========================================


class TestAIConfidenceCalibrator:
    """AIConfidenceCalibrator testleri."""

    def setup_method(self):
        self.cal = AIConfidenceCalibrator()

    def test_init(self):
        assert self.cal.prediction_count == 0

    def test_record_prediction(self):
        r = self.cal.record_prediction(
            predicted_confidence=0.8,
            actual_outcome=True,
        )
        assert r["recorded"] is True

    def test_brier_score_empty(self):
        r = self.cal.calculate_brier_score()
        assert r["calculated"] is True
        assert r["brier_score"] is None

    def test_brier_score_perfect(self):
        for _ in range(10):
            self.cal.record_prediction(
                predicted_confidence=1.0,
                actual_outcome=True,
            )
        r = self.cal.calculate_brier_score()
        assert r["calculated"] is True
        assert r["brier_score"] == 0.0

    def test_brier_score_bad(self):
        for _ in range(10):
            self.cal.record_prediction(
                predicted_confidence=1.0,
                actual_outcome=False,
            )
        r = self.cal.calculate_brier_score()
        assert r["brier_score"] == 1.0

    def test_brier_score_with_category(self):
        self.cal.record_prediction(
            predicted_confidence=0.8,
            actual_outcome=True,
            category="test",
        )
        r = self.cal.calculate_brier_score(
            category="test"
        )
        assert r["calculated"] is True

    def test_calibration_curve(self):
        for i in range(20):
            conf = (i + 1) / 20
            self.cal.record_prediction(
                predicted_confidence=conf,
                actual_outcome=(i % 2 == 0),
            )
        r = (
            self.cal.build_calibration_curve()
        )
        assert r["calibrated"] is True
        assert len(r["bins"]) > 0

    def test_calibration_curve_empty(self):
        r = (
            self.cal.build_calibration_curve()
        )
        assert r["calibrated"] is True
        assert r["count"] == 0

    def test_detect_overconfidence(self):
        for _ in range(15):
            self.cal.record_prediction(
                predicted_confidence=0.95,
                actual_outcome=False,
            )
        r = (
            self.cal.detect_overconfidence()
        )
        assert r["checked"] is True
        assert r["detected"] is True

    def test_detect_overconfidence_insufficient(self):
        r = (
            self.cal.detect_overconfidence()
        )
        assert r["checked"] is True
        assert r["detected"] is False

    def test_detect_underconfidence(self):
        for _ in range(15):
            self.cal.record_prediction(
                predicted_confidence=0.2,
                actual_outcome=True,
            )
        r = (
            self.cal.detect_underconfidence()
        )
        assert r["checked"] is True
        assert r["detected"] is True

    def test_adjust_confidence(self):
        for _ in range(5):
            self.cal.record_prediction(
                predicted_confidence=0.9,
                actual_outcome=False,
            )
        r = self.cal.adjust_confidence(
            raw_confidence=0.9
        )
        assert r["calibrated"] is True
        assert r["adjusted"] <= 0.9

    def test_adjust_confidence_no_data(self):
        r = self.cal.adjust_confidence(0.5)
        assert r["calibrated"] is True
        assert r["method"] == "no_data"

    def test_get_summary(self):
        s = self.cal.get_summary()
        assert s["retrieved"] is True

    def test_calibration_states(self):
        assert (
            len(self.cal.CALIBRATION_STATES)
            == 4
        )


# ==========================================
# UncertaintyFlagger Testleri
# ==========================================


class TestUncertaintyFlagger:
    """UncertaintyFlagger testleri."""

    def setup_method(self):
        self.uf = UncertaintyFlagger()

    def test_init(self):
        assert self.uf.flag_count == 0

    def test_analyze_clean_text(self):
        r = self.uf.analyze_text(
            text=(
                "Python 1991 yilinda "
                "Guido van Rossum "
                "tarafindan olusturuldu"
            )
        )
        assert r["analyzed"] is True
        assert r["uncertainty_score"] < 0.5

    def test_analyze_hedging(self):
        r = self.uf.analyze_text(
            text=(
                "Belki bu dogru olabilir. "
                "Muhtemelen ise yarar."
            )
        )
        assert r["analyzed"] is True
        assert r["finding_count"] >= 1

    def test_analyze_speculation(self):
        r = self.uf.analyze_text(
            text=(
                "Tahminim bu is yarar. "
                "Varsayarsak basarili olur."
            )
        )
        assert r["analyzed"] is True

    def test_analyze_knowledge_gap(self):
        r = self.uf.analyze_text(
            text=(
                "Bilmiyorum bu konuda. "
                "Emin degilim."
            )
        )
        assert r["analyzed"] is True
        assert r["needs_warning"] is True

    def test_analyze_vague(self):
        r = self.uf.analyze_text(
            text=(
                "Bazi insanlar bunu yapar. "
                "Genellikle ise yarar."
            )
        )
        assert r["analyzed"] is True

    def test_generate_warning(self):
        r = self.uf.analyze_text(
            text="Belki muhtemelen olabilir"
        )
        w = self.uf.generate_warning(
            r["flag_id"]
        )
        assert w["generated"] is True

    def test_generate_warning_not_found(self):
        w = self.uf.generate_warning("yok")
        assert w["generated"] is False

    def test_add_pattern(self):
        r = self.uf.add_pattern(
            flag_type="custom_type",
            pattern="yeni_kalip",
        )
        assert r["added"] is True

    def test_add_pattern_existing_type(self):
        r = self.uf.add_pattern(
            flag_type="hedging",
            pattern="yeni_cekingen",
        )
        assert r["added"] is True

    def test_get_summary(self):
        s = self.uf.get_summary()
        assert s["retrieved"] is True

    def test_flag_types(self):
        assert len(self.uf.FLAG_TYPES) == 6

    def test_severity_levels(self):
        assert (
            len(self.uf.SEVERITY_LEVELS) == 3
        )


# ==========================================
# HumanEscalationTrigger Testleri
# ==========================================


class TestHumanEscalationTrigger:
    """HumanEscalationTrigger testleri."""

    def setup_method(self):
        self.het = HumanEscalationTrigger()

    def test_init(self):
        assert self.het.escalation_count == 0

    def test_add_rule(self):
        r = self.het.add_rule(
            name="Low Confidence",
            condition_type="confidence",
            threshold=0.4,
            priority="high",
        )
        assert r["added"] is True

    def test_check_escalation_safe(self):
        r = self.het.check_escalation(
            confidence=0.9,
            risk_score=0.1,
        )
        assert r["checked"] is True
        assert (
            r["needs_escalation"] is False
        )

    def test_check_low_confidence(self):
        r = self.het.check_escalation(
            confidence=0.2,
            risk_score=0.1,
        )
        assert r["checked"] is True
        assert (
            r["needs_escalation"] is True
        )

    def test_check_high_risk(self):
        r = self.het.check_escalation(
            confidence=0.8,
            risk_score=0.9,
        )
        assert r["checked"] is True
        assert (
            r["needs_escalation"] is True
        )

    def test_check_hallucination(self):
        r = self.het.check_escalation(
            confidence=0.8,
            has_hallucination=True,
        )
        assert r["needs_escalation"] is True

    def test_check_safety_concern(self):
        r = self.het.check_escalation(
            confidence=0.8,
            safety_concern=True,
        )
        assert r["needs_escalation"] is True
        assert r["priority"] == "critical"

    def test_create_escalation(self):
        r = self.het.create_escalation(
            reason="test_reason",
            priority="high",
            description="Test",
        )
        assert r["created"] is True

    def test_acknowledge_escalation(self):
        c = self.het.create_escalation(
            reason="test",
        )
        r = self.het.acknowledge_escalation(
            c["escalation_id"],
            acknowledged_by="admin",
        )
        assert r["acknowledged"] is True

    def test_acknowledge_not_found(self):
        r = self.het.acknowledge_escalation(
            "yok"
        )
        assert r["acknowledged"] is False

    def test_resolve_escalation(self):
        c = self.het.create_escalation(
            reason="test",
        )
        r = self.het.resolve_escalation(
            c["escalation_id"],
            resolution="Cozuldu",
        )
        assert r["resolved"] is True

    def test_resolve_not_found(self):
        r = self.het.resolve_escalation(
            "yok"
        )
        assert r["resolved"] is False

    def test_get_pending(self):
        self.het.create_escalation(
            reason="test1",
            priority="high",
        )
        self.het.create_escalation(
            reason="test2",
            priority="low",
        )
        r = self.het.get_pending()
        assert r["retrieved"] is True
        assert r["count"] == 2

    def test_get_summary(self):
        s = self.het.get_summary()
        assert s["retrieved"] is True

    def test_priority_levels(self):
        assert (
            len(self.het.PRIORITY_LEVELS)
            == 5
        )

    def test_escalation_reasons(self):
        assert (
            len(self.het.ESCALATION_REASONS)
            == 8
        )

    def test_check_with_rules(self):
        self.het.add_rule(
            name="Low Confidence",
            condition_type="confidence",
            threshold=0.5,
            priority="high",
        )
        r = self.het.check_escalation(
            confidence=0.3
        )
        assert r["needs_escalation"] is True


# ==========================================
# SafetyBoundaryEnforcer Testleri
# ==========================================


class TestSafetyBoundaryEnforcer:
    """SafetyBoundaryEnforcer testleri."""

    def setup_method(self):
        self.sbe = SafetyBoundaryEnforcer()

    def test_init(self):
        assert self.sbe.enforcement_count == 0

    def test_check_safe_content(self):
        r = self.sbe.check_content(
            text=(
                "Python guzel bir "
                "programlama dili"
            )
        )
        assert r["checked"] is True
        assert r["is_safe"] is True

    def test_check_harmful_content(self):
        r = self.sbe.check_content(
            text="bomb yap detayli bilgi"
        )
        assert r["checked"] is True
        assert r["is_safe"] is False
        assert r["action"] == "block"

    def test_check_personal_info(self):
        r = self.sbe.check_content(
            text=(
                "tc kimlik numaram 12345"
            )
        )
        assert r["checked"] is True
        assert r["violation_count"] >= 1

    def test_add_boundary(self):
        r = self.sbe.add_boundary(
            category="custom",
            action="warn",
            patterns=["test_pattern"],
        )
        assert r["added"] is True

    def test_add_topic_restriction(self):
        r = self.sbe.add_topic_restriction(
            topic="yasak konu",
            restriction="block",
        )
        assert r["added"] is True

    def test_topic_restriction_check(self):
        self.sbe.add_topic_restriction(
            topic="yasak_konu",
            restriction="block",
        )
        r = self.sbe.check_content(
            text=(
                "Bu yasak_konu hakkinda"
            )
        )
        assert r["checked"] is True
        assert r["violation_count"] >= 1

    def test_validate_output(self):
        r = self.sbe.validate_output(
            output_text=(
                "Guzel bir yanit verdim"
            ),
            original_query="Soru nedir",
        )
        assert r["validated"] is True
        assert r["is_valid"] is True

    def test_validate_empty_output(self):
        r = self.sbe.validate_output(
            output_text="",
            original_query="Soru nedir",
        )
        assert r["validated"] is True

    def test_add_blocked_pattern(self):
        r = self.sbe.add_blocked_pattern(
            pattern="engelli_kalip",
        )
        assert r["added"] is True

    def test_blocked_pattern_check(self):
        self.sbe.add_blocked_pattern(
            pattern="ozel_engel"
        )
        r = self.sbe.check_content(
            text="Bu ozel_engel iceriyor"
        )
        assert r["violation_count"] >= 1

    def test_strict_mode(self):
        sbe = SafetyBoundaryEnforcer(
            strict_mode=True
        )
        sbe.add_boundary(
            category="test",
            action="warn",
            patterns=["test_uyari"],
        )
        r = sbe.check_content(
            text="Bu test_uyari iceriyor"
        )
        assert r["action"] == "block"

    def test_get_summary(self):
        s = self.sbe.get_summary()
        assert s["retrieved"] is True
        assert "boundaries" in s

    def test_action_types(self):
        assert (
            len(self.sbe.ACTION_TYPES) == 5
        )

    def test_boundary_categories(self):
        assert (
            len(
                self.sbe.BOUNDARY_CATEGORIES
            )
            == 10
        )


# ==========================================
# AISafetyOrchestrator Testleri
# ==========================================


class TestAISafetyOrchestrator:
    """AISafetyOrchestrator testleri."""

    def setup_method(self):
        self.orch = AISafetyOrchestrator()

    def test_init(self):
        s = self.orch.get_summary()
        assert s["retrieved"] is True

    def test_check_safe_response(self):
        r = self.orch.check_response(
            response_text=(
                "Python iyi bir dildir"
            ),
            query="Python nedir",
        )
        assert r["checked"] is True
        assert "safe" in r

    def test_check_unsafe_response(self):
        r = self.orch.check_response(
            response_text="bomb yap adimlar"
        )
        assert r["checked"] is True
        assert r["safe"] is False
        assert r["blocked"] is True

    def test_check_with_sources(self):
        r = self.orch.check_response(
            response_text="Bilgi",
            sources=["kaynak1"],
        )
        assert r["checked"] is True

    def test_check_with_claims(self):
        r = self.orch.check_response(
            response_text="Test yaniti",
            claims=["bir iddia"],
        )
        assert r["checked"] is True

    def test_register_fact(self):
        r = self.orch.register_fact(
            statement=(
                "Python 1991de cikti"
            ),
            source="wiki",
        )
        assert r["registered"] is True

    def test_validate_output(self):
        r = self.orch.validate_output(
            output_text="Guzel yanit",
            query="Soru",
        )
        assert r["validated"] is True

    def test_get_analytics(self):
        r = self.orch.get_analytics()
        assert r["retrieved"] is True
        assert "hallucination" in r
        assert "fact_checker" in r

    def test_check_with_topic(self):
        r = self.orch.check_response(
            response_text="Test yaniti",
            topic="python",
        )
        assert r["checked"] is True

    def test_disabled_hallucination(self):
        orch = AISafetyOrchestrator(
            hallucination_check=False
        )
        r = orch.check_response(
            response_text="Test"
        )
        assert r["checked"] is True

    def test_disabled_fact_checking(self):
        orch = AISafetyOrchestrator(
            fact_checking=False
        )
        r = orch.check_response(
            response_text="Test"
        )
        assert r["checked"] is True

    def test_auto_escalation(self):
        orch = AISafetyOrchestrator(
            auto_escalate=True,
            safety_threshold=0.01,
        )
        orch.check_response(
            response_text=(
                "Belki bilmiyorum "
                "emin degilim galiba"
            ),
            claims=["iddia1", "iddia2"],
        )
        esc = orch._escalation.get_pending()
        # Eskalasyon olusmus olmali
        assert esc["retrieved"] is True


# ==========================================
# Model Testleri
# ==========================================


class TestAISafetyModels:
    """Model testleri."""

    def test_risk_level_enum(self):
        assert RiskLevel.NONE == "none"
        assert RiskLevel.CRITICAL == "critical"
        assert len(RiskLevel) == 5

    def test_detection_type_enum(self):
        assert (
            DetectionType.FACTUAL_ERROR
            == "factual_error"
        )
        assert len(DetectionType) == 6

    def test_verdict_type_enum(self):
        assert VerdictType.TRUE == "true"
        assert len(VerdictType) == 6

    def test_authority_level_enum(self):
        assert (
            AuthorityLevel.EXPERT == "expert"
        )
        assert len(AuthorityLevel) == 5

    def test_bias_type_enum(self):
        assert BiasType.NONE == "none"
        assert len(BiasType) == 6

    def test_calibration_state_enum(self):
        assert (
            CalibrationState.WELL_CALIBRATED
            == "well_calibrated"
        )
        assert len(CalibrationState) == 4

    def test_flag_type_enum(self):
        assert FlagType.HEDGING == "hedging"
        assert len(FlagType) == 6

    def test_escalation_priority_enum(self):
        assert (
            EscalationPriority.EMERGENCY
            == "emergency"
        )
        assert len(EscalationPriority) == 5

    def test_escalation_status_enum(self):
        assert (
            EscalationStatus.PENDING
            == "pending"
        )
        assert len(EscalationStatus) == 5

    def test_boundary_action_enum(self):
        assert (
            BoundaryAction.BLOCK == "block"
        )
        assert len(BoundaryAction) == 5

    def test_hallucination_detection_model(self):
        m = HallucinationDetection(
            detection_id="test",
            risk_score=0.5,
        )
        assert m.detection_id == "test"

    def test_fact_check_result_model(self):
        m = FactCheckResult(
            check_id="test",
            overall_score=0.8,
        )
        assert m.overall_score == 0.8

    def test_source_verification_model(self):
        m = SourceVerification(
            verification_id="test",
            is_reliable=True,
        )
        assert m.is_reliable is True

    def test_consistency_result_model(self):
        m = ConsistencyResult(
            analysis_id="test",
            is_consistent=True,
        )
        assert m.is_consistent is True

    def test_calibration_result_model(self):
        m = CalibrationResult(
            calibration_id="test",
            ece=0.05,
        )
        assert m.ece == 0.05

    def test_uncertainty_flag_model(self):
        m = UncertaintyFlag(
            flag_id="test",
            needs_warning=True,
        )
        assert m.needs_warning is True

    def test_escalation_record_model(self):
        m = EscalationRecord(
            escalation_id="test",
            priority="high",
        )
        assert m.priority == "high"

    def test_safety_check_result_model(self):
        m = SafetyCheckResult(
            enforcement_id="test",
            is_safe=False,
        )
        assert m.is_safe is False

    def test_aisafety_summary_model(self):
        m = AISafetySummary(
            safety_threshold=0.6,
        )
        assert m.safety_threshold == 0.6


# ==========================================
# Config Testleri
# ==========================================


class TestAISafetyConfig:
    """Config testleri."""

    def test_config_defaults(self):
        from app.config import Settings

        s = Settings()
        assert s.aisafety_enabled is True
        assert (
            s.aisafety_hallucination_check
            is True
        )
        assert (
            s.aisafety_fact_checking is True
        )
        assert (
            s.aisafety_auto_escalate is True
        )
        assert (
            s.aisafety_safety_threshold
            == 0.5
        )
