"""
AI Ethics & Bias Monitor testleri.

BiasDetector, FairnessAnalyzer,
EthicsRuleEngine, EthicsDecisionAuditor,
ProtectedClassMonitor, TransparencyReporter,
EthicsViolationAlert,
EthicsRemediationSuggester,
AIEthicsOrchestrator testleri.
"""

import pytest

from app.core.aiethics.bias_detector import (
    BiasDetector,
)
from app.core.aiethics.fairness_analyzer import (
    FairnessAnalyzer,
)
from app.core.aiethics.ethics_rule_engine import (
    EthicsRuleEngine,
)
from app.core.aiethics.decision_auditor import (
    EthicsDecisionAuditor,
)
from app.core.aiethics.protected_class_monitor import (
    ProtectedClassMonitor,
)
from app.core.aiethics.transparency_reporter import (
    TransparencyReporter,
)
from app.core.aiethics.ethics_violation_alert import (
    EthicsViolationAlert,
)
from app.core.aiethics.remediation_suggester import (
    EthicsRemediationSuggester,
)
from app.core.aiethics.aiethics_orchestrator import (
    AIEthicsOrchestrator,
)
from app.models.aiethics_models import (
    BiasType,
    BiasSeverity,
    FairnessMetric,
    RuleCategory,
    RuleSeverity,
    ComplianceLevel,
    TreatmentType,
    ViolationType,
    AlertStatus,
    SuggestionType,
    ReportType,
    BiasDetectionResult,
    FairnessAnalysisResult,
    EthicsRuleResult,
    DecisionAuditResult,
    ProtectedClassAlert,
    EthicsViolation,
    RemediationSuggestion,
    TransparencyReport,
    AIEthicsSummary,
)


# ============ BiasDetector ============


class TestBiasDetector:
    """BiasDetector testleri."""

    def test_init(self):
        bd = BiasDetector()
        assert bd.detection_count == 0
        s = bd.get_summary()
        assert s["retrieved"] is True

    def test_init_custom_thresholds(self):
        bd = BiasDetector(
            parity_threshold=0.9,
            impact_threshold=0.9,
        )
        assert bd._parity_threshold == 0.9
        assert bd._impact_threshold == 0.9

    def test_add_dataset(self):
        bd = BiasDetector()
        r = bd.add_dataset(
            name="test_ds",
            records=[{"a": 1}],
            protected_attrs=["gender"],
            outcome_attr="outcome",
        )
        assert r["added"] is True
        assert r["record_count"] == 1

    def test_add_dataset_empty(self):
        bd = BiasDetector()
        r = bd.add_dataset(name="empty")
        assert r["added"] is True
        assert r["record_count"] == 0

    def test_scan_no_dataset(self):
        bd = BiasDetector()
        r = bd.scan_for_bias(
            dataset_id="nonexistent"
        )
        assert r["scanned"] is False

    def test_scan_empty_records(self):
        bd = BiasDetector()
        ds = bd.add_dataset(
            name="empty",
            records=[],
            protected_attrs=["gender"],
            outcome_attr="result",
        )
        r = bd.scan_for_bias(
            dataset_id=ds["dataset_id"]
        )
        assert r["scanned"] is True
        assert r["bias_score"] == 0.0

    def test_scan_no_bias(self):
        bd = BiasDetector()
        records = [
            {"gender": "M", "result": True},
            {"gender": "F", "result": True},
            {"gender": "M", "result": True},
            {"gender": "F", "result": True},
        ]
        ds = bd.add_dataset(
            name="balanced",
            records=records,
            protected_attrs=["gender"],
            outcome_attr="result",
        )
        r = bd.scan_for_bias(
            dataset_id=ds["dataset_id"]
        )
        assert r["scanned"] is True

    def test_scan_with_bias(self):
        bd = BiasDetector(
            parity_threshold=0.8,
            impact_threshold=0.8,
        )
        records = []
        for _ in range(20):
            records.append(
                {"gender": "M", "result": True}
            )
        for _ in range(20):
            records.append(
                {"gender": "F", "result": False}
            )
        ds = bd.add_dataset(
            name="biased",
            records=records,
            protected_attrs=["gender"],
            outcome_attr="result",
        )
        r = bd.scan_for_bias(
            dataset_id=ds["dataset_id"]
        )
        assert r["scanned"] is True
        assert r["finding_count"] > 0
        assert r["bias_score"] > 0

    def test_analyze_patterns(self):
        bd = BiasDetector()
        records = [
            {"gender": "M", "result": True},
            {"gender": "F", "result": False},
            {"gender": "M", "result": True},
        ]
        ds = bd.add_dataset(
            name="pattern",
            records=records,
            protected_attrs=["gender"],
            outcome_attr="result",
        )
        r = bd.analyze_patterns(
            dataset_id=ds["dataset_id"]
        )
        assert r["analyzed"] is True
        assert r["pattern_count"] > 0

    def test_analyze_patterns_no_dataset(self):
        bd = BiasDetector()
        r = bd.analyze_patterns(
            dataset_id="nonexistent"
        )
        assert r["analyzed"] is False

    def test_get_detection_info(self):
        bd = BiasDetector()
        ds = bd.add_dataset(
            name="test",
            records=[],
            protected_attrs=["x"],
            outcome_attr="y",
        )
        scan = bd.scan_for_bias(
            dataset_id=ds["dataset_id"]
        )
        r = bd.get_detection_info(
            detection_id=scan["detection_id"]
        )
        assert r["retrieved"] is True

    def test_get_detection_info_not_found(self):
        bd = BiasDetector()
        r = bd.get_detection_info(
            detection_id="nonexistent"
        )
        assert r["retrieved"] is False

    def test_severity_levels(self):
        bd = BiasDetector()
        assert bd._get_severity(0.05) == "none"
        assert bd._get_severity(0.2) == "low"
        assert bd._get_severity(0.4) == "medium"
        assert bd._get_severity(0.6) == "high"
        assert bd._get_severity(0.8) == "critical"

    def test_summary(self):
        bd = BiasDetector()
        s = bd.get_summary()
        assert s["total_detections"] == 0
        assert s["total_datasets"] == 0
        assert s["retrieved"] is True


# ============ FairnessAnalyzer ============


class TestFairnessAnalyzer:
    """FairnessAnalyzer testleri."""

    def test_init(self):
        fa = FairnessAnalyzer()
        assert fa.analysis_count == 0

    def test_init_custom_threshold(self):
        fa = FairnessAnalyzer(
            fairness_threshold=0.9
        )
        assert fa._fairness_threshold == 0.9

    def test_analyze_empty(self):
        fa = FairnessAnalyzer()
        r = fa.analyze_fairness()
        assert r["analyzed"] is True
        assert r["is_fair"] is True

    def test_analyze_no_attr(self):
        fa = FairnessAnalyzer()
        r = fa.analyze_fairness(
            predictions=[{"x": 1}]
        )
        assert r["analyzed"] is True
        assert r["is_fair"] is True

    def test_analyze_fair(self):
        fa = FairnessAnalyzer()
        preds = [
            {"gender": "M", "outcome": True, "predicted": True},
            {"gender": "F", "outcome": True, "predicted": True},
            {"gender": "M", "outcome": False, "predicted": False},
            {"gender": "F", "outcome": False, "predicted": False},
        ]
        r = fa.analyze_fairness(
            predictions=preds,
            protected_attr="gender",
        )
        assert r["analyzed"] is True
        assert r["is_fair"] is True

    def test_analyze_unfair(self):
        fa = FairnessAnalyzer(
            fairness_threshold=0.9
        )
        preds = []
        for _ in range(20):
            preds.append(
                {"gender": "M", "outcome": True, "predicted": True}
            )
        for _ in range(20):
            preds.append(
                {"gender": "F", "outcome": True, "predicted": False}
            )
        r = fa.analyze_fairness(
            predictions=preds,
            protected_attr="gender",
        )
        assert r["analyzed"] is True
        assert r["fairness_score"] < 0.9

    def test_compare_analyses(self):
        fa = FairnessAnalyzer()
        a1 = fa.analyze_fairness()
        a2 = fa.analyze_fairness()
        r = fa.compare_analyses(
            analysis_ids=[
                a1["analysis_id"],
                a2["analysis_id"],
            ]
        )
        assert r["compared"] is True
        assert r["count"] == 2

    def test_compare_empty(self):
        fa = FairnessAnalyzer()
        r = fa.compare_analyses()
        assert r["compared"] is True
        assert r["count"] == 0

    def test_metrics_structure(self):
        fa = FairnessAnalyzer()
        preds = [
            {"g": "A", "outcome": True, "predicted": True},
            {"g": "B", "outcome": True, "predicted": True},
            {"g": "A", "outcome": False, "predicted": False},
            {"g": "B", "outcome": False, "predicted": False},
        ]
        r = fa.analyze_fairness(
            predictions=preds,
            protected_attr="g",
        )
        m = r["metrics"]
        assert "demographic_parity" in m
        assert "equal_opportunity" in m
        assert "equalized_odds" in m
        assert "calibration" in m
        assert "group_fairness" in m

    def test_summary(self):
        fa = FairnessAnalyzer()
        s = fa.get_summary()
        assert s["total_analyses"] == 0
        assert s["retrieved"] is True


# ============ EthicsRuleEngine ============


class TestEthicsRuleEngine:
    """EthicsRuleEngine testleri."""

    def test_init(self):
        re = EthicsRuleEngine()
        assert re.rule_count == 0

    def test_define_rule(self):
        re = EthicsRuleEngine()
        r = re.define_rule(
            name="bias_check",
            category="fairness",
            condition="bias_score",
            severity="warning",
            threshold=0.3,
        )
        assert r["defined"] is True
        assert re.rule_count == 1

    def test_evaluate_no_rules(self):
        re = EthicsRuleEngine()
        r = re.evaluate()
        assert r["evaluated"] is True
        assert r["compliant"] is True

    def test_evaluate_pass(self):
        re = EthicsRuleEngine()
        re.define_rule(
            name="bias",
            condition="bias_score",
            threshold=0.5,
        )
        r = re.evaluate(
            context={"bias_score": 0.2}
        )
        assert r["evaluated"] is True
        assert r["compliant"] is True

    def test_evaluate_violation(self):
        re = EthicsRuleEngine()
        rule = re.define_rule(
            name="bias",
            condition="bias_score",
            severity="violation",
            threshold=0.3,
        )
        r = re.evaluate(
            context={"bias_score": 0.5}
        )
        assert r["evaluated"] is True
        assert r["compliant"] is False
        assert r["violation_count"] == 1

    def test_evaluate_fairness_condition(self):
        re = EthicsRuleEngine()
        re.define_rule(
            name="fairness",
            condition="fairness_score",
            threshold=0.8,
        )
        r = re.evaluate(
            context={"fairness_score": 0.5}
        )
        assert r["evaluated"] is True
        assert r["compliant"] is False

    def test_evaluate_disparity_condition(self):
        re = EthicsRuleEngine()
        re.define_rule(
            name="disparity",
            condition="disparity_ratio",
            threshold=0.8,
        )
        r = re.evaluate(
            context={"disparity_ratio": 0.5}
        )
        assert r["evaluated"] is True
        assert r["compliant"] is False

    def test_evaluate_transparency_condition(self):
        re = EthicsRuleEngine()
        re.define_rule(
            name="transparency",
            condition="transparency",
            threshold=0.7,
        )
        r = re.evaluate(
            context={"transparency_score": 0.3}
        )
        assert r["evaluated"] is True
        assert r["compliant"] is False

    def test_grant_exception(self):
        re = EthicsRuleEngine()
        rule = re.define_rule(
            name="test",
            condition="bias_score",
            threshold=0.3,
        )
        exc = re.grant_exception(
            rule_id=rule["rule_id"],
            reason="test",
            granted_by="admin",
        )
        assert exc["granted"] is True

    def test_exception_bypasses_rule(self):
        re = EthicsRuleEngine()
        rule = re.define_rule(
            name="test",
            condition="bias_score",
            threshold=0.3,
        )
        re.grant_exception(
            rule_id=rule["rule_id"],
            reason="waived",
        )
        r = re.evaluate(
            context={"bias_score": 0.9}
        )
        assert r["compliant"] is True

    def test_revoke_exception(self):
        re = EthicsRuleEngine()
        rule = re.define_rule(
            name="test",
            condition="bias_score",
            threshold=0.3,
        )
        exc = re.grant_exception(
            rule_id=rule["rule_id"],
            reason="test",
        )
        r = re.revoke_exception(
            exception_id=exc["exception_id"]
        )
        assert r["revoked"] is True
        # After revoke, rule should apply
        ev = re.evaluate(
            context={"bias_score": 0.9}
        )
        assert ev["compliant"] is False

    def test_toggle_rule(self):
        re = EthicsRuleEngine()
        rule = re.define_rule(
            name="test",
            condition="bias_score",
            threshold=0.3,
        )
        r = re.toggle_rule(
            rule_id=rule["rule_id"],
            active=False,
        )
        assert r["toggled"] is True
        ev = re.evaluate(
            context={"bias_score": 0.9}
        )
        assert ev["compliant"] is True

    def test_grant_exception_invalid_rule(self):
        re = EthicsRuleEngine()
        r = re.grant_exception(
            rule_id="nonexistent"
        )
        assert r["granted"] is False

    def test_revoke_exception_invalid(self):
        re = EthicsRuleEngine()
        r = re.revoke_exception(
            exception_id="nonexistent"
        )
        assert r["revoked"] is False

    def test_toggle_rule_invalid(self):
        re = EthicsRuleEngine()
        r = re.toggle_rule(
            rule_id="nonexistent"
        )
        assert r["toggled"] is False

    def test_evaluate_with_rule_ids(self):
        re = EthicsRuleEngine()
        r1 = re.define_rule(
            name="a",
            condition="bias_score",
            threshold=0.3,
        )
        r2 = re.define_rule(
            name="b",
            condition="fairness_score",
            threshold=0.8,
        )
        ev = re.evaluate(
            context={"bias_score": 0.5},
            rule_ids=[r1["rule_id"]],
        )
        assert ev["evaluated"] is True
        assert ev["violation_count"] == 1

    def test_summary(self):
        re = EthicsRuleEngine()
        s = re.get_summary()
        assert s["total_rules"] == 0
        assert s["retrieved"] is True


# ============ EthicsDecisionAuditor ============


class TestDecisionAuditor:
    """EthicsDecisionAuditor testleri."""

    def test_init(self):
        da = EthicsDecisionAuditor()
        assert da.decision_count == 0

    def test_init_custom_limit(self):
        da = EthicsDecisionAuditor(
            retention_limit=100
        )
        assert da._retention_limit == 100

    def test_log_decision(self):
        da = EthicsDecisionAuditor()
        r = da.log_decision(
            decision_type="classification",
            output=True,
            confidence=0.9,
        )
        assert r["logged"] is True
        assert da.decision_count == 1

    def test_retention_limit(self):
        da = EthicsDecisionAuditor(
            retention_limit=5
        )
        for i in range(10):
            da.log_decision(output=i)
        assert da.decision_count == 5

    def test_audit_empty(self):
        da = EthicsDecisionAuditor()
        r = da.audit_decisions()
        assert r["audited"] is True
        assert r["decisions_reviewed"] == 0

    def test_audit_compliant(self):
        da = EthicsDecisionAuditor()
        for _ in range(5):
            da.log_decision(
                output=True,
                confidence=0.9,
            )
        r = da.audit_decisions()
        assert r["audited"] is True
        assert r["compliance"] == "compliant"

    def test_audit_with_disparity(self):
        da = EthicsDecisionAuditor()
        for _ in range(20):
            da.log_decision(
                output=True,
                protected_attrs={"gender": "M"},
            )
        for _ in range(20):
            da.log_decision(
                output=False,
                protected_attrs={"gender": "F"},
            )
        r = da.audit_decisions(
            protected_attr="gender"
        )
        assert r["audited"] is True
        assert r["finding_count"] > 0

    def test_audit_low_confidence(self):
        da = EthicsDecisionAuditor()
        for _ in range(20):
            da.log_decision(
                output=True,
                confidence=0.2,
            )
        r = da.audit_decisions()
        assert r["audited"] is True
        assert any(
            f["type"] == "low_confidence_pattern"
            for f in r["findings"]
        )

    def test_audit_by_type(self):
        da = EthicsDecisionAuditor()
        da.log_decision(
            decision_type="classification"
        )
        da.log_decision(
            decision_type="recommendation"
        )
        r = da.audit_decisions(
            decision_type="classification"
        )
        assert r["audited"] is True
        assert r["decisions_reviewed"] == 1

    def test_generate_report(self):
        da = EthicsDecisionAuditor()
        for _ in range(5):
            da.log_decision(confidence=0.9)
        audit = da.audit_decisions()
        r = da.generate_report(
            audit_id=audit["audit_id"]
        )
        assert r["generated"] is True

    def test_generate_report_not_found(self):
        da = EthicsDecisionAuditor()
        r = da.generate_report(
            audit_id="nonexistent"
        )
        assert r["generated"] is False

    def test_report_with_findings(self):
        da = EthicsDecisionAuditor()
        for _ in range(20):
            da.log_decision(confidence=0.1)
        audit = da.audit_decisions()
        r = da.generate_report(
            audit_id=audit["audit_id"]
        )
        assert r["generated"] is True
        assert len(r["recommendations"]) > 0

    def test_summary(self):
        da = EthicsDecisionAuditor()
        s = da.get_summary()
        assert s["total_decisions"] == 0
        assert s["retrieved"] is True


# ============ ProtectedClassMonitor ============


class TestProtectedClassMonitor:
    """ProtectedClassMonitor testleri."""

    def test_init(self):
        pcm = ProtectedClassMonitor()
        assert pcm.observation_count == 0

    def test_init_custom_threshold(self):
        pcm = ProtectedClassMonitor(
            disparity_threshold=0.1
        )
        assert pcm._disparity_threshold == 0.1

    def test_register_class(self):
        pcm = ProtectedClassMonitor()
        r = pcm.register_class(
            category="gender",
            values=["M", "F"],
        )
        assert r["registered"] is True

    def test_log_observation(self):
        pcm = ProtectedClassMonitor()
        r = pcm.log_observation(
            protected_attr="gender",
            protected_value="M",
            outcome=True,
            treatment="equal",
        )
        assert r["logged"] is True
        assert pcm.observation_count == 1

    def test_check_disparity_no_data(self):
        pcm = ProtectedClassMonitor()
        r = pcm.check_disparity(
            protected_attr="gender"
        )
        assert r["checked"] is True
        assert r["has_disparity"] is False

    def test_check_disparity_single_group(self):
        pcm = ProtectedClassMonitor()
        pcm.log_observation(
            protected_attr="gender",
            protected_value="M",
            outcome=True,
        )
        r = pcm.check_disparity(
            protected_attr="gender"
        )
        assert r["checked"] is True
        assert r["has_disparity"] is False

    def test_check_disparity_equal(self):
        pcm = ProtectedClassMonitor()
        for _ in range(10):
            pcm.log_observation(
                protected_attr="gender",
                protected_value="M",
                outcome=True,
            )
            pcm.log_observation(
                protected_attr="gender",
                protected_value="F",
                outcome=True,
            )
        r = pcm.check_disparity(
            protected_attr="gender"
        )
        assert r["checked"] is True
        assert r["has_disparity"] is False

    def test_check_disparity_found(self):
        pcm = ProtectedClassMonitor(
            disparity_threshold=0.2
        )
        for _ in range(20):
            pcm.log_observation(
                protected_attr="gender",
                protected_value="M",
                outcome=True,
            )
            pcm.log_observation(
                protected_attr="gender",
                protected_value="F",
                outcome=False,
            )
        r = pcm.check_disparity(
            protected_attr="gender"
        )
        assert r["checked"] is True
        assert r["has_disparity"] is True
        assert r["alert_id"] is not None

    def test_check_differential_treatment(self):
        pcm = ProtectedClassMonitor()
        for _ in range(10):
            pcm.log_observation(
                protected_attr="race",
                protected_value="A",
                treatment="equal",
            )
            pcm.log_observation(
                protected_attr="race",
                protected_value="B",
                treatment="unfavorable",
            )
        r = pcm.check_differential_treatment(
            protected_attr="race"
        )
        assert r["checked"] is True
        assert r["has_differential"] is True

    def test_check_differential_no_data(self):
        pcm = ProtectedClassMonitor()
        r = pcm.check_differential_treatment(
            protected_attr="age"
        )
        assert r["checked"] is True
        assert r["has_differential"] is False

    def test_get_open_alerts(self):
        pcm = ProtectedClassMonitor(
            disparity_threshold=0.1
        )
        for _ in range(20):
            pcm.log_observation(
                protected_attr="gender",
                protected_value="M",
                outcome=True,
            )
            pcm.log_observation(
                protected_attr="gender",
                protected_value="F",
                outcome=False,
            )
        pcm.check_disparity(
            protected_attr="gender"
        )
        r = pcm.get_open_alerts()
        assert r["retrieved"] is True
        assert r["count"] > 0

    def test_summary(self):
        pcm = ProtectedClassMonitor()
        s = pcm.get_summary()
        assert s["retrieved"] is True
        assert s["classes_monitored"] == 0


# ============ TransparencyReporter ============


class TestTransparencyReporter:
    """TransparencyReporter testleri."""

    def test_init(self):
        tr = TransparencyReporter()
        assert tr.report_count == 0

    def test_create_model_card(self):
        tr = TransparencyReporter()
        r = tr.create_model_card(
            model_id="model_1",
            model_name="Test Model",
            description="Desc",
            intended_use="Testing",
            limitations=["limited"],
        )
        assert r["created"] is True

    def test_get_model_card(self):
        tr = TransparencyReporter()
        card = tr.create_model_card(
            model_name="Test"
        )
        r = tr.get_model_card(
            card_id=card["card_id"]
        )
        assert r["retrieved"] is True
        assert r["model_name"] == "Test"

    def test_get_model_card_not_found(self):
        tr = TransparencyReporter()
        r = tr.get_model_card(
            card_id="nonexistent"
        )
        assert r["retrieved"] is False

    def test_explain_decision(self):
        tr = TransparencyReporter()
        r = tr.explain_decision(
            decision_id="dec_1",
            decision_type="classification",
            factors=[
                {"name": "age", "weight": 0.5},
                {"name": "income", "weight": 0.3},
            ],
            confidence=0.85,
        )
        assert r["explained"] is True
        assert r["factor_count"] == 2
        assert tr.report_count == 1

    def test_generate_stakeholder_report(self):
        tr = TransparencyReporter()
        r = tr.generate_stakeholder_report(
            title="Q1 Ethics Report",
            audience="business",
            sections=[
                {"title": "Bias", "content": "ok"},
            ],
            findings=[{"type": "bias"}],
            recommendations=["fix bias"],
        )
        assert r["generated"] is True
        assert r["section_count"] == 1

    def test_create_disclosure(self):
        tr = TransparencyReporter()
        r = tr.create_disclosure(
            title="AI Usage",
            content="We use AI for...",
            disclosure_type="public",
        )
        assert r["created"] is True

    def test_publish_disclosure(self):
        tr = TransparencyReporter()
        disc = tr.create_disclosure(
            title="Test"
        )
        r = tr.publish_disclosure(
            disclosure_id=disc["disclosure_id"]
        )
        assert r["published"] is True

    def test_publish_disclosure_not_found(self):
        tr = TransparencyReporter()
        r = tr.publish_disclosure(
            disclosure_id="nonexistent"
        )
        assert r["published"] is False

    def test_summary(self):
        tr = TransparencyReporter()
        tr.create_model_card(model_name="m1")
        tr.create_disclosure(title="d1")
        s = tr.get_summary()
        assert s["retrieved"] is True
        assert s["total_model_cards"] == 1
        assert s["total_disclosures"] == 1


# ============ EthicsViolationAlert ============


class TestEthicsViolationAlert:
    """EthicsViolationAlert testleri."""

    def test_init(self):
        va = EthicsViolationAlert()
        assert va.alert_count == 0

    def test_init_custom(self):
        va = EthicsViolationAlert(
            auto_escalate=False,
            escalation_threshold="critical",
        )
        assert va._auto_escalate is False

    def test_add_alert_rule(self):
        va = EthicsViolationAlert()
        r = va.add_alert_rule(
            name="bias_rule",
            violation_type="bias_detected",
            severity="high",
            condition="bias_score",
            threshold=0.5,
        )
        assert r["added"] is True

    def test_raise_alert(self):
        va = EthicsViolationAlert(
            auto_escalate=False
        )
        r = va.raise_alert(
            violation_type="bias_detected",
            severity="medium",
            title="Bias Found",
            description="High bias",
        )
        assert r["raised"] is True
        assert va.alert_count == 1

    def test_raise_alert_auto_escalate(self):
        va = EthicsViolationAlert(
            auto_escalate=True,
            escalation_threshold="high",
        )
        r = va.raise_alert(
            violation_type="bias_detected",
            severity="high",
            title="Critical Bias",
        )
        assert r["raised"] is True
        assert r["escalation_id"] is not None

    def test_raise_alert_no_escalate_below_threshold(self):
        va = EthicsViolationAlert(
            auto_escalate=True,
            escalation_threshold="high",
        )
        r = va.raise_alert(
            violation_type="bias_detected",
            severity="low",
            title="Minor",
        )
        assert r["raised"] is True
        assert r["escalation_id"] is None

    def test_check_violations(self):
        va = EthicsViolationAlert()
        va.add_alert_rule(
            name="bias",
            violation_type="bias_detected",
            severity="high",
            condition="bias_score",
            threshold=0.3,
        )
        r = va.check_violations(
            context={"bias_score": 0.8}
        )
        assert r["checked"] is True
        assert r["violation_count"] == 1

    def test_check_violations_pass(self):
        va = EthicsViolationAlert()
        va.add_alert_rule(
            name="bias",
            violation_type="bias_detected",
            severity="high",
            condition="bias_score",
            threshold=0.5,
        )
        r = va.check_violations(
            context={"bias_score": 0.1}
        )
        assert r["checked"] is True
        assert r["violation_count"] == 0

    def test_check_violations_empty(self):
        va = EthicsViolationAlert()
        r = va.check_violations()
        assert r["checked"] is True
        assert r["violation_count"] == 0

    def test_acknowledge_alert(self):
        va = EthicsViolationAlert(
            auto_escalate=False
        )
        alert = va.raise_alert(
            violation_type="bias_detected",
            severity="medium",
            title="Test",
        )
        r = va.acknowledge_alert(
            alert_id=alert["alert_id"],
            acknowledged_by="admin",
        )
        assert r["acknowledged"] is True

    def test_acknowledge_not_found(self):
        va = EthicsViolationAlert()
        r = va.acknowledge_alert(
            alert_id="nonexistent"
        )
        assert r["acknowledged"] is False

    def test_resolve_alert(self):
        va = EthicsViolationAlert(
            auto_escalate=False
        )
        alert = va.raise_alert(
            violation_type="bias_detected",
            severity="medium",
            title="Test",
        )
        r = va.resolve_alert(
            alert_id=alert["alert_id"],
            resolution="Fixed",
            resolved_by="admin",
        )
        assert r["resolved"] is True

    def test_resolve_not_found(self):
        va = EthicsViolationAlert()
        r = va.resolve_alert(
            alert_id="nonexistent"
        )
        assert r["resolved"] is False

    def test_get_open_alerts(self):
        va = EthicsViolationAlert(
            auto_escalate=False
        )
        va.raise_alert(
            severity="medium", title="Open"
        )
        va.raise_alert(
            severity="high", title="Also open"
        )
        r = va.get_open_alerts()
        assert r["retrieved"] is True
        assert r["count"] == 2

    def test_critical_alert_counter(self):
        va = EthicsViolationAlert(
            auto_escalate=False
        )
        va.raise_alert(
            severity="critical", title="C1"
        )
        va.raise_alert(
            severity="medium", title="M1"
        )
        s = va.get_summary()
        assert s["stats"]["critical_alerts"] == 1

    def test_summary(self):
        va = EthicsViolationAlert()
        s = va.get_summary()
        assert s["total_alerts"] == 0
        assert s["retrieved"] is True


# ============ EthicsRemediationSuggester ============


class TestRemediationSuggester:
    """EthicsRemediationSuggester testleri."""

    def test_init(self):
        rs = EthicsRemediationSuggester()
        assert rs.suggestion_count == 0

    def test_suggest_for_demographic_bias(self):
        rs = EthicsRemediationSuggester()
        r = rs.suggest_for_bias(
            bias_type="demographic",
            severity="high",
            attribute="gender",
            gap=0.5,
        )
        assert r["suggested"] is True
        assert r["suggestion_count"] >= 2

    def test_suggest_for_disparate_impact(self):
        rs = EthicsRemediationSuggester()
        r = rs.suggest_for_bias(
            bias_type="disparate_impact",
            severity="high",
        )
        assert r["suggested"] is True
        assert r["suggestion_count"] >= 2

    def test_suggest_for_representation(self):
        rs = EthicsRemediationSuggester()
        r = rs.suggest_for_bias(
            bias_type="representation",
            severity="medium",
        )
        assert r["suggested"] is True
        assert r["suggestion_count"] >= 2

    def test_suggest_for_unknown_type(self):
        rs = EthicsRemediationSuggester()
        r = rs.suggest_for_bias(
            bias_type="other",
            severity="low",
        )
        assert r["suggested"] is True
        assert r["suggestion_count"] >= 1

    def test_suggest_for_fairness(self):
        rs = EthicsRemediationSuggester()
        r = rs.suggest_for_fairness(
            metric="demographic_parity",
            score=0.4,
        )
        assert r["suggested"] is True
        assert len(r["suggestions"]) >= 2

    def test_suggest_for_calibration(self):
        rs = EthicsRemediationSuggester()
        r = rs.suggest_for_fairness(
            metric="calibration",
            score=0.3,
        )
        assert r["suggested"] is True
        # Should have calibration-specific suggestion
        techniques = [
            s["technique"]
            for s in r["suggestions"]
        ]
        assert "platt_scaling" in techniques

    def test_create_remediation_plan(self):
        rs = EthicsRemediationSuggester()
        r = rs.create_remediation_plan(
            title="Fix Gender Bias",
            issues=[
                {
                    "description": "Gender bias",
                    "action": "Retrain",
                },
                {
                    "description": "Data imbalance",
                    "action": "Resample",
                },
            ],
            priority="high",
            owner="ml_team",
        )
        assert r["created"] is True
        assert r["step_count"] == 2

    def test_create_plan_empty(self):
        rs = EthicsRemediationSuggester()
        r = rs.create_remediation_plan(
            title="Empty"
        )
        assert r["created"] is True
        assert r["step_count"] == 0

    def test_apply_technique(self):
        rs = EthicsRemediationSuggester()
        r = rs.apply_technique(
            technique="reweighting",
            target="model_1",
            parameters={"factor": 1.5},
        )
        assert r["applied"] is True

    def test_complete_remediation(self):
        rs = EthicsRemediationSuggester()
        plan = rs.create_remediation_plan(
            title="Test Plan"
        )
        r = rs.complete_remediation(
            plan_id=plan["plan_id"]
        )
        assert r["completed"] is True

    def test_complete_remediation_not_found(self):
        rs = EthicsRemediationSuggester()
        r = rs.complete_remediation(
            plan_id="nonexistent"
        )
        assert r["completed"] is False

    def test_summary(self):
        rs = EthicsRemediationSuggester()
        s = rs.get_summary()
        assert s["total_suggestions"] == 0
        assert s["retrieved"] is True


# ============ AIEthicsOrchestrator ============


class TestAIEthicsOrchestrator:
    """AIEthicsOrchestrator testleri."""

    def test_init(self):
        orch = AIEthicsOrchestrator()
        s = orch.get_summary()
        assert s["retrieved"] is True
        assert s["bias_detection"] is True

    def test_init_custom(self):
        orch = AIEthicsOrchestrator(
            bias_detection=False,
            fairness_metrics=False,
            auto_alert=False,
            transparency_reports=False,
        )
        s = orch.get_summary()
        assert s["bias_detection"] is False

    def test_full_check_empty(self):
        orch = AIEthicsOrchestrator()
        r = orch.full_ethics_check()
        assert r["checked"] is True
        assert r["is_ethical"] is True

    def test_full_check_with_bias(self):
        orch = AIEthicsOrchestrator()
        # Add biased dataset
        records = []
        for _ in range(20):
            records.append(
                {"gender": "M", "result": True}
            )
        for _ in range(20):
            records.append(
                {"gender": "F", "result": False}
            )
        ds = orch._bias_detector.add_dataset(
            name="biased",
            records=records,
            protected_attrs=["gender"],
            outcome_attr="result",
        )
        r = orch.full_ethics_check(
            dataset_id=ds["dataset_id"]
        )
        assert r["checked"] is True

    def test_full_check_with_predictions(self):
        orch = AIEthicsOrchestrator()
        preds = []
        for _ in range(20):
            preds.append({
                "gender": "M",
                "outcome": True,
                "predicted": True,
            })
        for _ in range(20):
            preds.append({
                "gender": "F",
                "outcome": True,
                "predicted": False,
            })
        r = orch.full_ethics_check(
            predictions=preds,
            protected_attr="gender",
        )
        assert r["checked"] is True

    def test_full_check_with_rules(self):
        orch = AIEthicsOrchestrator()
        orch._rule_engine.define_rule(
            name="bias",
            condition="bias_score",
            severity="violation",
            threshold=0.3,
        )
        r = orch.full_ethics_check(
            context={"bias_score": 0.8}
        )
        assert r["checked"] is True
        assert r["issue_count"] > 0
        assert r["is_ethical"] is False

    def test_log_and_audit_decision(self):
        orch = AIEthicsOrchestrator()
        r = orch.log_and_audit_decision(
            decision_type="classification",
            output=True,
            confidence=0.9,
            protected_attrs={"gender": "M"},
        )
        assert r["logged"] is True

    def test_log_decision_no_protected(self):
        orch = AIEthicsOrchestrator()
        r = orch.log_and_audit_decision(
            decision_type="prediction",
            output=0.75,
        )
        assert r["logged"] is True

    def test_generate_ethics_report(self):
        orch = AIEthicsOrchestrator()
        r = orch.generate_ethics_report(
            title="Q1 Report"
        )
        assert r["generated"] is True

    def test_generate_report_disabled(self):
        orch = AIEthicsOrchestrator(
            transparency_reports=False
        )
        r = orch.generate_ethics_report()
        assert r["generated"] is False

    def test_get_analytics(self):
        orch = AIEthicsOrchestrator()
        r = orch.get_analytics()
        assert r["retrieved"] is True
        assert "bias" in r
        assert "fairness" in r
        assert "rules" in r
        assert "alerts" in r

    def test_full_pipeline(self):
        orch = AIEthicsOrchestrator()
        # Add dataset
        records = []
        for _ in range(20):
            records.append(
                {"gender": "M", "result": True}
            )
        for _ in range(20):
            records.append(
                {"gender": "F", "result": False}
            )
        ds = orch._bias_detector.add_dataset(
            name="test",
            records=records,
            protected_attrs=["gender"],
            outcome_attr="result",
        )
        # Add rule
        orch._rule_engine.define_rule(
            name="bias",
            condition="bias_score",
            threshold=0.3,
        )
        # Full check
        r = orch.full_ethics_check(
            dataset_id=ds["dataset_id"],
            context={"bias_score": 0.5},
        )
        assert r["checked"] is True
        # Report
        report = orch.generate_ethics_report(
            title="Full Pipeline Report"
        )
        assert report["generated"] is True


# ============ Models ============


class TestAIEthicsModels:
    """aiethics_models testleri."""

    def test_bias_type_enum(self):
        assert BiasType.DEMOGRAPHIC == "demographic"
        assert BiasType.REPRESENTATION == "representation"
        assert len(BiasType) == 8

    def test_bias_severity_enum(self):
        assert BiasSeverity.NONE == "none"
        assert BiasSeverity.CRITICAL == "critical"
        assert len(BiasSeverity) == 5

    def test_fairness_metric_enum(self):
        assert (
            FairnessMetric.DEMOGRAPHIC_PARITY
            == "demographic_parity"
        )
        assert len(FairnessMetric) == 6

    def test_rule_category_enum(self):
        assert RuleCategory.FAIRNESS == "fairness"
        assert len(RuleCategory) == 8

    def test_rule_severity_enum(self):
        assert RuleSeverity.INFO == "info"
        assert len(RuleSeverity) == 4

    def test_compliance_level_enum(self):
        assert (
            ComplianceLevel.COMPLIANT
            == "compliant"
        )
        assert len(ComplianceLevel) == 4

    def test_treatment_type_enum(self):
        assert TreatmentType.EQUAL == "equal"
        assert len(TreatmentType) == 4

    def test_violation_type_enum(self):
        assert (
            ViolationType.BIAS_DETECTED
            == "bias_detected"
        )
        assert len(ViolationType) == 6

    def test_alert_status_enum(self):
        assert AlertStatus.OPEN == "open"
        assert len(AlertStatus) == 5

    def test_suggestion_type_enum(self):
        assert (
            SuggestionType.DEBIASING
            == "debiasing"
        )
        assert len(SuggestionType) == 6

    def test_report_type_enum(self):
        assert (
            ReportType.MODEL_CARD
            == "model_card"
        )
        assert len(ReportType) == 6

    def test_bias_detection_result(self):
        m = BiasDetectionResult(
            detection_id="det_1",
            bias_score=0.5,
            severity=BiasSeverity.HIGH,
        )
        assert m.detection_id == "det_1"
        assert m.bias_score == 0.5

    def test_fairness_analysis_result(self):
        m = FairnessAnalysisResult(
            analysis_id="fair_1",
            is_fair=False,
            fairness_score=0.6,
        )
        assert m.is_fair is False

    def test_ethics_rule_result(self):
        m = EthicsRuleResult(
            evaluation_id="eval_1",
            violation_count=2,
            compliant=False,
        )
        assert m.violation_count == 2

    def test_decision_audit_result(self):
        m = DecisionAuditResult(
            audit_id="aud_1",
            compliance=ComplianceLevel.MAJOR_ISSUE,
        )
        assert (
            m.compliance
            == ComplianceLevel.MAJOR_ISSUE
        )

    def test_protected_class_alert(self):
        m = ProtectedClassAlert(
            alert_id="palr_1",
            attribute="gender",
            gap=0.4,
        )
        assert m.gap == 0.4

    def test_ethics_violation(self):
        m = EthicsViolation(
            alert_id="valr_1",
            violation_type=ViolationType.FAIRNESS_VIOLATION,
        )
        assert (
            m.violation_type
            == ViolationType.FAIRNESS_VIOLATION
        )

    def test_remediation_suggestion(self):
        m = RemediationSuggestion(
            suggestion_id="sug_1",
            suggestion_type=SuggestionType.RETRAINING,
            description="Retrain model",
        )
        assert (
            m.suggestion_type
            == SuggestionType.RETRAINING
        )

    def test_transparency_report(self):
        m = TransparencyReport(
            report_id="trpt_1",
            report_type=ReportType.MODEL_CARD,
            generated=True,
        )
        assert m.generated is True

    def test_ai_ethics_summary(self):
        m = AIEthicsSummary(
            full_checks=5,
            biases_detected=2,
        )
        assert m.full_checks == 5
        assert m.biases_detected == 2


# ============ Config ============


class TestAIEthicsConfig:
    """Config testleri."""

    def test_aiethics_defaults(self):
        from app.config import settings

        assert hasattr(settings, "aiethics_enabled")
        assert settings.aiethics_enabled is True
        assert settings.aiethics_bias_detection is True
        assert settings.aiethics_fairness_metrics is True
        assert settings.aiethics_auto_alert is True
        assert settings.aiethics_transparency_reports is True
