"""ATLAS Anomaly & Fraud Detector testleri.

AnomalyScanner, FraudPatternMatcher, BehaviorBaseline,
AlertTriager, FalsePositiveFilter, FraudIncidentReporter,
LearningDetector, FraudRiskScorer, FraudDetectOrchestrator
testleri.
"""

import pytest

from app.core.frauddetect.alert_triager import (
    AlertTriager,
)
from app.core.frauddetect.anomaly_scanner import (
    AnomalyScanner,
)
from app.core.frauddetect.behavior_baseline import (
    BehaviorBaseline,
)
from app.core.frauddetect.false_positive_filter import (
    FalsePositiveFilter,
)
from app.core.frauddetect.fraud_pattern_matcher import (
    FraudPatternMatcher,
)
from app.core.frauddetect.frauddetect_orchestrator import (
    FraudDetectOrchestrator,
)
from app.core.frauddetect.incident_reporter import (
    FraudIncidentReporter,
)
from app.core.frauddetect.learning_detector import (
    LearningDetector,
)
from app.core.frauddetect.risk_scorer import (
    FraudRiskScorer,
)
from app.models.frauddetect_models import (
    AnomalyRecord,
    AnomalyType,
    AlertPriority,
    DetectionMethod,
    FraudAlertRecord,
    FraudIncidentRecord,
    FraudSeverity,
    IncidentStatus,
    RiskLevel,
    RiskScoreRecord,
)


# ── AnomalyScanner ─────────────────────────


class TestAddDataPoint:
    """add_data_point testleri."""

    def test_basic(self):
        s = AnomalyScanner()
        r = s.add_data_point("src1", 10.0)
        assert r["added"] is True
        assert r["source"] == "src1"
        assert r["data_points"] == 1

    def test_multiple_points(self):
        s = AnomalyScanner()
        s.add_data_point("src1", 1.0)
        r = s.add_data_point("src1", 2.0)
        assert r["data_points"] == 2

    def test_different_sources(self):
        s = AnomalyScanner()
        s.add_data_point("a", 1.0)
        r = s.add_data_point("b", 2.0)
        assert r["data_points"] == 1


class TestAnalyzePattern:
    """analyze_pattern testleri."""

    def test_insufficient(self):
        s = AnomalyScanner()
        for v in [1.0, 2.0, 3.0]:
            s.add_data_point("x", v)
        r = s.analyze_pattern("x")
        assert r["analyzed"] is False

    def test_increasing(self):
        s = AnomalyScanner()
        for v in [1, 2, 3, 4, 5, 6]:
            s.add_data_point("x", float(v))
        r = s.analyze_pattern("x")
        assert r["analyzed"] is True
        assert r["pattern"] == "increasing"

    def test_stable(self):
        s = AnomalyScanner()
        for v in [50, 51, 50, 49, 50]:
            s.add_data_point("x", float(v))
        r = s.analyze_pattern("x")
        assert r["analyzed"] is True
        assert r["pattern"] == "stable"


class TestDetectStatistical:
    """detect_statistical testleri."""

    def test_insufficient_data(self):
        s = AnomalyScanner()
        s.add_data_point("x", 10.0)
        r = s.detect_statistical("x", 100.0)
        assert r["is_anomaly"] is False

    def test_normal_value(self):
        s = AnomalyScanner()
        for v in [10, 10, 10, 11, 9]:
            s.add_data_point("x", float(v))
        r = s.detect_statistical("x", 10.5)
        assert r["is_anomaly"] is False

    def test_anomaly_detected(self):
        s = AnomalyScanner()
        for v in [10, 10, 10, 10, 10]:
            s.add_data_point("x", float(v))
        r = s.detect_statistical("x", 500.0)
        assert r["is_anomaly"] is True
        assert s.anomaly_count >= 1

    def test_zero_std(self):
        s = AnomalyScanner()
        for _ in range(5):
            s.add_data_point("x", 50.0)
        r = s.detect_statistical("x", 50.0)
        assert r["is_anomaly"] is False


class TestDetectTimeseries:
    """detect_timeseries testleri."""

    def test_insufficient(self):
        s = AnomalyScanner()
        for v in [1, 2, 3]:
            s.add_data_point("x", float(v))
        r = s.detect_timeseries("x", window=5)
        assert r["detected"] is False

    def test_normal_series(self):
        s = AnomalyScanner()
        for v in [10, 10, 10, 10, 10, 10, 10, 11]:
            s.add_data_point("x", float(v))
        r = s.detect_timeseries("x", window=5)
        assert r["detected"] is False

    def test_anomalous_spike(self):
        s = AnomalyScanner()
        vals = [10, 10, 10, 10, 10, 10, 10, 500]
        for v in vals:
            s.add_data_point("x", float(v))
        r = s.detect_timeseries("x", window=5)
        assert r["detected"] is True
        assert r["anomaly_count"] >= 1


class TestDetectBehavioral:
    """detect_behavioral testleri."""

    def test_no_deviation(self):
        s = AnomalyScanner()
        r = s.detect_behavioral(
            "user1",
            current_behavior={"logins": 5},
            expected={"logins": 5},
        )
        assert r["is_anomaly"] is False

    def test_large_deviation(self):
        s = AnomalyScanner()
        r = s.detect_behavioral(
            "user1",
            current_behavior={"logins": 100},
            expected={"logins": 5},
        )
        assert r["is_anomaly"] is True
        assert r["deviation_count"] >= 1


class TestScanMultidimensional:
    """scan_multidimensional testleri."""

    def test_no_violations(self):
        s = AnomalyScanner()
        r = s.scan_multidimensional(
            "src",
            dimensions={"cpu": 50},
            thresholds={"cpu": 90},
        )
        assert r["risk"] == "low"
        assert r["violation_count"] == 0

    def test_critical(self):
        s = AnomalyScanner()
        r = s.scan_multidimensional(
            "src",
            dimensions={
                "cpu": 95, "mem": 95, "disk": 99,
            },
            thresholds={
                "cpu": 90, "mem": 90, "disk": 90,
            },
        )
        assert r["risk"] == "critical"
        assert r["violation_count"] == 3


# ── FraudPatternMatcher ────────────────────


class TestRegisterPattern:
    """register_pattern testleri."""

    def test_basic(self):
        m = FraudPatternMatcher()
        r = m.register_pattern(
            "phishing",
            indicators=["email", "link"],
        )
        assert r["registered"] is True
        assert m.pattern_count == 1

    def test_with_severity(self):
        m = FraudPatternMatcher()
        r = m.register_pattern(
            "fraud", severity="high",
        )
        assert r["registered"] is True


class TestMatchKnownPattern:
    """match_known_pattern testleri."""

    def test_no_patterns(self):
        m = FraudPatternMatcher()
        r = m.match_known_pattern(["email"])
        assert r["matched"] is False

    def test_match_found(self):
        m = FraudPatternMatcher()
        m.register_pattern(
            "phishing",
            indicators=["email", "link"],
        )
        r = m.match_known_pattern(["email"])
        assert r["matched"] is True
        assert r["match_count"] >= 1

    def test_no_match(self):
        m = FraudPatternMatcher()
        m.register_pattern(
            "phishing",
            indicators=["email", "link"],
        )
        r = m.match_known_pattern(["sms"])
        assert r["matched"] is False


class TestAddRule:
    """add_rule testleri."""

    def test_basic(self):
        m = FraudPatternMatcher()
        r = m.add_rule(
            "high_amount",
            condition="amount",
            threshold=1000.0,
        )
        assert r["added"] is True


class TestMatchRules:
    """match_rules testleri."""

    def test_triggered(self):
        m = FraudPatternMatcher()
        m.add_rule(
            "high_amount",
            condition="amount",
            threshold=1000.0,
        )
        r = m.match_rules(
            data={"amount": 5000.0},
        )
        assert r["matched"] is True

    def test_not_triggered(self):
        m = FraudPatternMatcher()
        m.add_rule(
            "high_amount",
            condition="amount",
            threshold=1000.0,
        )
        r = m.match_rules(
            data={"amount": 500.0},
        )
        assert r["matched"] is False


class TestDetectSignature:
    """detect_signature testleri."""

    def test_found(self):
        m = FraudPatternMatcher()
        m.register_pattern(
            "card_fraud",
            indicators=["login", "transfer"],
        )
        r = m.detect_signature(
            event_sequence=[
                "login", "browse", "transfer",
            ],
        )
        assert r["found"] is True

    def test_not_found(self):
        m = FraudPatternMatcher()
        m.register_pattern(
            "card_fraud",
            indicators=["login", "transfer"],
        )
        r = m.detect_signature(
            event_sequence=["browse"],
        )
        assert r["found"] is False


class TestFuzzyMatch:
    """fuzzy_match testleri."""

    def test_match(self):
        m = FraudPatternMatcher()
        m.register_pattern(
            "email_fraud",
            indicators=[
                "suspicious email",
                "fake link",
            ],
        )
        r = m.fuzzy_match(
            "suspicious email detected",
        )
        assert r["matched"] is True

    def test_no_match(self):
        m = FraudPatternMatcher()
        m.register_pattern(
            "x", indicators=["alpha beta"],
        )
        r = m.fuzzy_match("gamma delta")
        assert r["matched"] is False


# ── BehaviorBaseline ───────────────────────


class TestLearnNormal:
    """learn_normal testleri."""

    def test_basic(self):
        b = BehaviorBaseline()
        r = b.learn_normal(
            "user1", {"logins": 5.0},
        )
        assert r["learned"] is True
        assert r["observations"] == 1


class TestBuildProfile:
    """build_profile testleri."""

    def test_insufficient(self):
        b = BehaviorBaseline()
        b.learn_normal("u", {"x": 1.0})
        r = b.build_profile("u")
        assert r["built"] is False

    def test_success(self):
        b = BehaviorBaseline()
        for v in [10, 20, 30]:
            b.learn_normal(
                "u", {"logins": float(v)},
            )
        r = b.build_profile("u")
        assert r["built"] is True
        assert b.profile_count == 1


class TestMeasureDeviation:
    """measure_deviation testleri."""

    def test_no_profile(self):
        b = BehaviorBaseline()
        r = b.measure_deviation("u")
        assert r["measured"] is False

    def test_normal(self):
        b = BehaviorBaseline()
        for v in [50, 50, 50]:
            b.learn_normal(
                "u", {"x": float(v)},
            )
        b.build_profile("u")
        r = b.measure_deviation(
            "u", current={"x": 55.0},
        )
        assert r["measured"] is True
        assert r["is_anomalous"] is False

    def test_anomalous(self):
        b = BehaviorBaseline()
        for v in [10, 10, 10]:
            b.learn_normal(
                "u", {"x": float(v)},
            )
        b.build_profile("u")
        r = b.measure_deviation(
            "u", current={"x": 100.0},
        )
        assert r["is_anomalous"] is True


class TestAdaptBaseline:
    """adapt_baseline testleri."""

    def test_no_profile(self):
        b = BehaviorBaseline()
        r = b.adapt_baseline("u")
        assert r["adapted"] is False

    def test_success(self):
        b = BehaviorBaseline()
        for v in [50, 50, 50]:
            b.learn_normal(
                "u", {"x": float(v)},
            )
        b.build_profile("u")
        r = b.adapt_baseline(
            "u", new_metrics={"x": 100.0},
        )
        assert r["adapted"] is True
        assert r["metrics_updated"] == 1


class TestAdjustSeasonal:
    """adjust_seasonal testleri."""

    def test_no_profile(self):
        b = BehaviorBaseline()
        r = b.adjust_seasonal("u")
        assert r["adjusted"] is False

    def test_success(self):
        b = BehaviorBaseline()
        for v in [50, 50, 50]:
            b.learn_normal(
                "u", {"x": float(v)},
            )
        b.build_profile("u")
        r = b.adjust_seasonal(
            "u", season="winter", factor=1.2,
        )
        assert r["adjusted"] is True
        assert r["factor"] == 1.2


# ── AlertTriager ───────────────────────────


class TestScoreAlert:
    """score_alert testleri."""

    def test_basic(self):
        t = AlertTriager()
        r = t.score_alert(
            "a1", severity=80,
            confidence=70, impact=60,
        )
        assert r["scored"] is True
        assert r["score"] > 0

    def test_zero(self):
        t = AlertTriager()
        r = t.score_alert("a1")
        assert r["score"] == 0.0


class TestAssignPriority:
    """assign_priority testleri."""

    def test_p1(self):
        t = AlertTriager()
        t.score_alert(
            "a1", severity=100,
            confidence=90, impact=80,
        )
        r = t.assign_priority("a1")
        assert r["priority"] == "p1"

    def test_p4(self):
        t = AlertTriager()
        t.score_alert(
            "a1", severity=10,
            confidence=5, impact=5,
        )
        r = t.assign_priority("a1")
        assert r["priority"] == "p4"

    def test_not_found(self):
        t = AlertTriager()
        r = t.assign_priority("missing")
        assert r["assigned"] is False


class TestGroupAlerts:
    """group_alerts testleri."""

    def test_basic(self):
        t = AlertTriager()
        t.score_alert("a1", severity=50)
        t.score_alert("a2", severity=60)
        r = t.group_alerts(
            "grp1", alert_ids=["a1", "a2"],
        )
        assert r["grouped"] is True
        assert r["alert_count"] == 2

    def test_invalid_ids(self):
        t = AlertTriager()
        r = t.group_alerts(
            "grp", alert_ids=["none"],
        )
        assert r["grouped"] is False


class TestDeduplicate:
    """deduplicate testleri."""

    def test_removes_dupes(self):
        t = AlertTriager()
        t.score_alert(
            "a1", severity=50,
            confidence=50, impact=50,
        )
        t.score_alert(
            "a2", severity=50,
            confidence=50, impact=50,
        )
        r = t.deduplicate()
        assert r["removed"] >= 1

    def test_no_dupes(self):
        t = AlertTriager()
        t.score_alert("a1", severity=50)
        t.score_alert("a2", severity=70)
        r = t.deduplicate()
        assert r["removed"] == 0


class TestRouteAlert:
    """route_alert testleri."""

    def test_basic(self):
        t = AlertTriager()
        t.score_alert(
            "a1", severity=90,
            confidence=90, impact=90,
        )
        t.assign_priority("a1")
        r = t.route_alert("a1")
        assert r["routed"] is True
        assert r["destination"] == "security_team"

    def test_not_found(self):
        t = AlertTriager()
        r = t.route_alert("missing")
        assert r["routed"] is False


# ── FalsePositiveFilter ────────────────────


class TestCheckFalsePositive:
    """check_false_positive testleri."""

    def test_below_threshold(self):
        f = FalsePositiveFilter()
        r = f.check_false_positive(
            "a1", score=10.0,
        )
        assert r["is_fp"] is True

    def test_above_threshold(self):
        f = FalsePositiveFilter()
        r = f.check_false_positive(
            "a1", score=80.0,
        )
        assert r["is_fp"] is False

    def test_whitelisted(self):
        f = FalsePositiveFilter()
        f._whitelist.add("safe_user")
        r = f.check_false_positive(
            "a1", entity="safe_user",
        )
        assert r["is_fp"] is True
        assert r["reason"] == "whitelisted"


class TestLearnFromFeedback:
    """learn_from_feedback testleri."""

    def test_basic(self):
        f = FalsePositiveFilter()
        r = f.learn_from_feedback(
            "a1", was_fp=True, entity="u1",
        )
        assert r["learned"] is True

    def test_whitelist_after_3(self):
        f = FalsePositiveFilter()
        for i in range(3):
            f.learn_from_feedback(
                f"a{i}", was_fp=True,
                entity="u1",
            )
        r = f.learn_from_feedback(
            "a3", was_fp=True, entity="u1",
        )
        assert r["entity_whitelisted"] is True


class TestRefineRules:
    """refine_rules testleri."""

    def test_no_feedback(self):
        f = FalsePositiveFilter()
        r = f.refine_rules()
        assert r["refined"] is False

    def test_with_feedback(self):
        f = FalsePositiveFilter()
        for i in range(5):
            f.learn_from_feedback(
                f"a{i}", was_fp=True,
            )
        r = f.refine_rules()
        assert r["refined"] is True
        assert r["fp_rate"] == 100.0


class TestTuneThreshold:
    """tune_threshold testleri."""

    def test_basic(self):
        f = FalsePositiveFilter()
        r = f.tune_threshold(
            "default", value=50.0,
        )
        assert r["tuned"] is True
        assert r["new_threshold"] == 50.0


class TestTrackAccuracy:
    """track_accuracy testleri."""

    def test_initial(self):
        f = FalsePositiveFilter()
        r = f.track_accuracy()
        assert r["tracked"] is True
        assert r["precision"] == 100.0

    def test_after_checks(self):
        f = FalsePositiveFilter()
        f.check_false_positive("a1", score=10)
        f.check_false_positive("a2", score=80)
        r = f.track_accuracy()
        assert r["total_alerts"] == 2


# ── FraudIncidentReporter ──────────────────


class TestDocumentIncident:
    """document_incident testleri."""

    def test_basic(self):
        r = FraudIncidentReporter()
        res = r.document_incident(
            "Suspicious activity",
            severity="high",
        )
        assert res["documented"] is True
        assert r.incident_count == 1

    def test_with_entity(self):
        r = FraudIncidentReporter()
        res = r.document_incident(
            "Fraud",
            affected_entity="user1",
        )
        assert res["documented"] is True


class TestCollectEvidence:
    """collect_evidence testleri."""

    def test_no_incident(self):
        r = FraudIncidentReporter()
        res = r.collect_evidence("fake_id")
        assert res["collected"] is False

    def test_success(self):
        r = FraudIncidentReporter()
        inc = r.document_incident("Test")
        iid = inc["incident_id"]
        res = r.collect_evidence(
            iid, evidence_type="log",
            data="suspicious login",
        )
        assert res["collected"] is True
        assert r.evidence_count == 1


class TestCreateTimeline:
    """create_timeline testleri."""

    def test_no_incident(self):
        r = FraudIncidentReporter()
        res = r.create_timeline("fake_id")
        assert res["created"] is False

    def test_with_events(self):
        r = FraudIncidentReporter()
        inc = r.document_incident("Test")
        iid = inc["incident_id"]
        res = r.create_timeline(
            iid,
            events=[
                {"event": "a", "timestamp": 100},
                {"event": "b", "timestamp": 200},
            ],
        )
        assert res["created"] is True
        assert res["duration_sec"] == 100.0


class TestNotifyStakeholders:
    """notify_stakeholders testleri."""

    def test_no_incident(self):
        r = FraudIncidentReporter()
        res = r.notify_stakeholders("fake")
        assert res["notified"] is False

    def test_success(self):
        r = FraudIncidentReporter()
        inc = r.document_incident("Fraud alert")
        iid = inc["incident_id"]
        res = r.notify_stakeholders(
            iid, channels=["telegram"],
        )
        assert res["notified"] is True


class TestGenerateComplianceReport:
    """generate_compliance_report testleri."""

    def test_no_incident(self):
        r = FraudIncidentReporter()
        res = r.generate_compliance_report(
            "fake",
        )
        assert res["generated"] is False

    def test_success(self):
        r = FraudIncidentReporter()
        inc = r.document_incident(
            "Test", severity="critical",
        )
        iid = inc["incident_id"]
        res = r.generate_compliance_report(iid)
        assert res["generated"] is True
        assert res["severity"] == "critical"


# ── LearningDetector ──────────────────────


class TestDetect:
    """detect testleri."""

    def test_no_model(self):
        d = LearningDetector()
        r = d.detect("missing")
        assert r["detected"] is False

    def test_with_model(self):
        d = LearningDetector()
        d.train_model("m1", threshold=50.0)
        r = d.detect(
            "m1",
            features={"a": 30.0, "b": 20.0},
        )
        assert r["detected"] is True
        assert r["is_fraud"] is False

    def test_fraud_detected(self):
        d = LearningDetector()
        d.train_model("m1", threshold=50.0)
        r = d.detect(
            "m1",
            features={"a": 80.0, "b": 90.0},
        )
        assert r["is_fraud"] is True


class TestTrainModel:
    """train_model testleri."""

    def test_basic(self):
        d = LearningDetector()
        r = d.train_model("fraud_v1")
        assert r["trained"] is True
        assert d.model_count == 1

    def test_versioning(self):
        d = LearningDetector()
        d.train_model("m1")
        r = d.train_model("m1")
        assert r["version"] == 2


class TestEngineerFeatures:
    """engineer_features testleri."""

    def test_basic(self):
        d = LearningDetector()
        r = d.engineer_features(
            "m1",
            raw_features=["amount", "time"],
        )
        assert r["engineered"] is True
        assert r["engineered_count"] == 4


class TestAddTrainingData:
    """add_training_data testleri."""

    def test_basic(self):
        d = LearningDetector()
        r = d.add_training_data(
            features={"a": 1.0},
            label=True,
        )
        assert r["added"] is True
        assert r["data_size"] == 1


class TestGetModelVersion:
    """get_model_version testleri."""

    def test_not_found(self):
        d = LearningDetector()
        r = d.get_model_version("missing")
        assert r["found"] is False

    def test_found(self):
        d = LearningDetector()
        d.train_model(
            "m1", algorithm="random_forest",
        )
        r = d.get_model_version("m1")
        assert r["found"] is True
        assert r["algorithm"] == "random_forest"


# ── FraudRiskScorer ────────────────────────


class TestCalculateRisk:
    """calculate_risk testleri."""

    def test_no_factors(self):
        s = FraudRiskScorer()
        r = s.calculate_risk("e1")
        assert r["calculated"] is False

    def test_low_risk(self):
        s = FraudRiskScorer()
        r = s.calculate_risk(
            "e1", factors={"a": 10.0},
        )
        assert r["calculated"] is True
        assert r["level"] == "negligible"

    def test_high_risk(self):
        s = FraudRiskScorer()
        r = s.calculate_risk(
            "e1", factors={"a": 90.0},
        )
        assert r["level"] == "critical"
        assert s.high_risk_count == 1


class TestScoreMultifactor:
    """score_multifactor testleri."""

    def test_basic(self):
        s = FraudRiskScorer()
        r = s.score_multifactor(
            "e1",
            anomaly_score=80.0,
            pattern_score=70.0,
            behavior_score=60.0,
            history_score=50.0,
        )
        assert r["calculated"] is True
        assert s.score_count >= 1


class TestGetConfidence:
    """get_confidence testleri."""

    def test_not_found(self):
        s = FraudRiskScorer()
        r = s.get_confidence("missing")
        assert r["found"] is False

    def test_found(self):
        s = FraudRiskScorer()
        s.calculate_risk(
            "e1",
            factors={"a": 50.0, "b": 60.0},
        )
        r = s.get_confidence("e1")
        assert r["found"] is True
        assert r["confidence"] == 40.0


class TestSetThreshold:
    """set_threshold testleri."""

    def test_valid(self):
        s = FraudRiskScorer()
        r = s.set_threshold("high", 70.0)
        assert r["set"] is True
        assert r["new"] == 70.0

    def test_invalid_level(self):
        s = FraudRiskScorer()
        r = s.set_threshold("invalid", 50.0)
        assert r["set"] is False


class TestExplainScore:
    """explain_score testleri."""

    def test_not_found(self):
        s = FraudRiskScorer()
        r = s.explain_score("missing")
        assert r["explained"] is False

    def test_found(self):
        s = FraudRiskScorer()
        s.calculate_risk(
            "e1",
            factors={"anomaly": 80.0, "pattern": 30.0},
        )
        r = s.explain_score("e1")
        assert r["explained"] is True
        assert len(r["explanations"]) == 2
        assert r["explanations"][0]["factor"] == "anomaly"


# ── FraudDetectOrchestrator ────────────────


class TestRunDetectionPipeline:
    """run_detection_pipeline testleri."""

    def test_basic(self):
        o = FraudDetectOrchestrator()
        r = o.run_detection_pipeline("user1")
        assert r["pipeline_complete"] is True
        assert r["entity"] == "user1"
        assert o.pipeline_count == 1

    def test_with_data(self):
        o = FraudDetectOrchestrator()
        # Önce veri ekle ki istatistik çalışsın
        for v in [10, 10, 10, 10, 10]:
            o.scanner.add_data_point(
                "user2", float(v),
            )
        r = o.run_detection_pipeline(
            "user2",
            data={"amount": 500.0},
        )
        assert r["pipeline_complete"] is True

    def test_with_matching_pattern(self):
        o = FraudDetectOrchestrator()
        o.patterns.register_pattern(
            "phishing",
            indicators=["email", "link"],
        )
        r = o.run_detection_pipeline(
            "user3",
            signals=["email", "link"],
        )
        assert r["pattern_matched"] is True


class TestMonitorRealtime:
    """monitor_realtime testleri."""

    def test_basic(self):
        o = FraudDetectOrchestrator()
        r = o.monitor_realtime(
            "user1", value=50.0,
        )
        assert r["monitored"] is True
        assert r["entity"] == "user1"

    def test_anomaly(self):
        o = FraudDetectOrchestrator()
        for v in [10, 10, 10, 10, 10]:
            o.scanner.add_data_point(
                "default", float(v),
            )
        r = o.monitor_realtime(
            "user1", value=500.0,
        )
        assert r["monitored"] is True


class TestGetAnalytics:
    """get_analytics testleri."""

    def test_initial(self):
        o = FraudDetectOrchestrator()
        r = o.get_analytics()
        assert r["pipelines_run"] == 0
        assert r["frauds_detected"] == 0

    def test_after_pipeline(self):
        o = FraudDetectOrchestrator()
        o.run_detection_pipeline("u1")
        r = o.get_analytics()
        assert r["pipelines_run"] == 1


# ── Models ─────────────────────────────────


class TestAnomalyType:
    """AnomalyType testleri."""

    def test_values(self):
        assert AnomalyType.STATISTICAL == "statistical"
        assert AnomalyType.BEHAVIORAL == "behavioral"
        assert AnomalyType.TEMPORAL == "temporal"
        assert AnomalyType.STRUCTURAL == "structural"


class TestFraudSeverity:
    """FraudSeverity testleri."""

    def test_values(self):
        assert FraudSeverity.CRITICAL == "critical"
        assert FraudSeverity.HIGH == "high"
        assert FraudSeverity.MEDIUM == "medium"
        assert FraudSeverity.LOW == "low"


class TestAlertPriority:
    """AlertPriority testleri."""

    def test_values(self):
        assert AlertPriority.P1 == "p1"
        assert AlertPriority.P2 == "p2"
        assert AlertPriority.P3 == "p3"
        assert AlertPriority.P4 == "p4"


class TestDetectionMethod:
    """DetectionMethod testleri."""

    def test_values(self):
        assert DetectionMethod.RULE_BASED == "rule_based"
        assert DetectionMethod.ML_BASED == "ml_based"
        assert DetectionMethod.HYBRID == "hybrid"


class TestRiskLevel:
    """RiskLevel testleri."""

    def test_values(self):
        assert RiskLevel.CRITICAL == "critical"
        assert RiskLevel.NEGLIGIBLE == "negligible"


class TestIncidentStatus:
    """IncidentStatus testleri."""

    def test_values(self):
        assert IncidentStatus.OPEN == "open"
        assert IncidentStatus.RESOLVED == "resolved"
        assert (
            IncidentStatus.FALSE_POSITIVE
            == "false_positive"
        )


class TestAnomalyRecordModel:
    """AnomalyRecord testleri."""

    def test_defaults(self):
        r = AnomalyRecord()
        assert r.anomaly_id
        assert r.anomaly_type == "statistical"

    def test_custom(self):
        r = AnomalyRecord(
            source="src1",
            severity="high",
        )
        assert r.source == "src1"


class TestFraudAlertRecordModel:
    """FraudAlertRecord testleri."""

    def test_defaults(self):
        r = FraudAlertRecord()
        assert r.alert_id
        assert r.priority == "p3"


class TestFraudIncidentRecordModel:
    """FraudIncidentRecord testleri."""

    def test_defaults(self):
        r = FraudIncidentRecord()
        assert r.incident_id
        assert r.status == "open"


class TestRiskScoreRecordModel:
    """RiskScoreRecord testleri."""

    def test_defaults(self):
        r = RiskScoreRecord()
        assert r.score_id
        assert r.level == "low"

    def test_custom(self):
        r = RiskScoreRecord(
            entity="user1",
            score=85.0,
            level="critical",
        )
        assert r.score == 85.0
