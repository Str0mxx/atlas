"""
Security Incident Response & Forensics
test modulu.
"""

import pytest

from app.core.incident.incident_detector import (
    IncidentDetector,
)
from app.core.incident.auto_containment import (
    AutoContainment,
)
from app.core.incident.forensic_collector import (
    ForensicCollector,
)
from app.core.incident.incident_root_cause_analyzer import (
    IncidentRootCauseAnalyzer,
)
from app.core.incident.incident_impact_assessor import (
    IncidentImpactAssessor,
)
from app.core.incident.recovery_executor import (
    RecoveryExecutor,
)
from app.core.incident.incident_lesson_learner import (
    IncidentLessonLearner,
)
from app.core.incident.playbook_generator import (
    PlaybookGenerator,
)
from app.core.incident.incident_orchestrator import (
    IncidentOrchestrator,
)


# ==================== IncidentDetector ====================

class TestIncidentDetector:
    """IncidentDetector testleri."""

    def setup_method(self):
        self.det = IncidentDetector()

    def test_init(self):
        assert self.det.incident_count == 0
        assert len(self.det.SEVERITY_LEVELS) == 5
        assert len(self.det.INCIDENT_TYPES) == 10

    def test_detect_incident(self):
        r = self.det.detect_incident(
            title="Malware tespit",
            incident_type="malware",
            severity="high",
            source="antivirus",
        )
        assert r["detected"] is True
        assert "incident_id" in r
        assert r["severity"] == "high"

    def test_detect_invalid_type(self):
        r = self.det.detect_incident(
            incident_type="invalid_type",
        )
        assert r["detected"] is False
        assert "error" in r

    def test_detect_invalid_severity(self):
        r = self.det.detect_incident(
            incident_type="malware",
            severity="invalid",
        )
        assert r["detected"] is False

    def test_define_pattern(self):
        r = self.det.define_pattern(
            name="Brute force",
            pattern_type="auth",
            indicators=["failed_login", "ip_scan"],
            threshold=1,
            severity="high",
        )
        assert r["created"] is True
        assert "pattern_id" in r

    def test_pattern_matching(self):
        self.det.define_pattern(
            name="Test pattern",
            indicators=["indicator_a", "indicator_b"],
            threshold=1,
        )
        r = self.det.detect_incident(
            title="Test",
            incident_type="malware",
            severity="high",
            indicators=["indicator_a"],
        )
        assert r["detected"] is True
        assert r["matched_patterns"] >= 1

    def test_correlate_incidents(self):
        r1 = self.det.detect_incident(
            title="Inc 1",
            incident_type="malware",
            severity="high",
            indicators=["ip_1", "hash_1"],
            affected_systems=["srv1"],
        )
        r2 = self.det.detect_incident(
            title="Inc 2",
            incident_type="phishing",
            severity="medium",
            indicators=["ip_1", "url_1"],
            affected_systems=["srv1"],
        )
        cr = self.det.correlate_incidents(
            incident_ids=[
                r1["incident_id"],
                r2["incident_id"],
            ]
        )
        assert cr["correlated"] is True
        assert cr["common_indicators"] >= 1

    def test_correlate_insufficient(self):
        r = self.det.correlate_incidents(
            incident_ids=["single"]
        )
        assert r["correlated"] is False

    def test_update_status(self):
        r = self.det.detect_incident(
            title="Test",
            incident_type="malware",
            severity="low",
        )
        iid = r["incident_id"]
        u = self.det.update_status(
            incident_id=iid,
            status="contained",
        )
        assert u["updated"] is True
        assert u["status"] == "contained"

    def test_update_status_invalid(self):
        r = self.det.detect_incident(
            title="Test",
            incident_type="malware",
            severity="low",
        )
        u = self.det.update_status(
            incident_id=r["incident_id"],
            status="invalid_status",
        )
        assert u["updated"] is False

    def test_update_status_not_found(self):
        u = self.det.update_status(
            incident_id="nonexistent",
            status="active",
        )
        assert u["updated"] is False

    def test_get_alerts(self):
        self.det.detect_incident(
            title="Alert test",
            incident_type="malware",
            severity="critical",
        )
        r = self.det.get_alerts(
            severity="critical"
        )
        assert r["retrieved"] is True
        assert r["count"] >= 1

    def test_get_alerts_all(self):
        self.det.detect_incident(
            title="A1",
            incident_type="malware",
            severity="high",
        )
        r = self.det.get_alerts()
        assert r["retrieved"] is True
        assert r["count"] >= 1

    def test_incident_count_property(self):
        self.det.detect_incident(
            title="Active",
            incident_type="malware",
            severity="high",
        )
        assert self.det.incident_count >= 1

    def test_get_summary(self):
        self.det.detect_incident(
            title="Summary test",
            incident_type="phishing",
            severity="medium",
        )
        s = self.det.get_summary()
        assert s["retrieved"] is True
        assert s["total_incidents"] >= 1
        assert "by_severity" in s


# ==================== AutoContainment ====================

class TestAutoContainment:
    """AutoContainment testleri."""

    def setup_method(self):
        self.ac = AutoContainment(
            auto_contain=True
        )

    def test_init(self):
        assert self.ac.active_quarantines == 0
        assert len(self.ac.ACTION_TYPES) == 8

    def test_contain_incident(self):
        r = self.ac.contain_incident(
            incident_id="inc_1",
            actions=["network_isolate"],
            targets=["srv1"],
            reason="Test",
        )
        assert r["contained"] is True
        assert r["actions_taken"] >= 1

    def test_contain_disabled(self):
        ac = AutoContainment(
            auto_contain=False
        )
        r = ac.contain_incident(
            incident_id="inc_1",
            actions=["network_isolate"],
            targets=["srv1"],
        )
        assert r["contained"] is False

    def test_contain_multiple_actions(self):
        r = self.ac.contain_incident(
            incident_id="inc_2",
            actions=[
                "network_isolate",
                "account_suspend",
            ],
            targets=["srv1", "srv2"],
            reason="Multi",
        )
        assert r["contained"] is True
        assert r["actions_taken"] == 4

    def test_contain_invalid_action_skipped(self):
        r = self.ac.contain_incident(
            incident_id="inc_3",
            actions=["invalid_action"],
            targets=["srv1"],
        )
        assert r["contained"] is True
        assert r["actions_taken"] == 0

    def test_quarantine_created(self):
        self.ac.contain_incident(
            incident_id="inc_q",
            actions=["network_isolate"],
            targets=["srv1"],
        )
        assert self.ac.active_quarantines >= 1

    def test_release_quarantine(self):
        self.ac.contain_incident(
            incident_id="inc_r",
            actions=["network_isolate"],
            targets=["srv1"],
        )
        # Karantina ID bul
        qid = list(
            self.ac._quarantines.keys()
        )[0]
        r = self.ac.release_quarantine(
            quarantine_id=qid,
            reason="Clear",
        )
        assert r["released"] is True

    def test_release_not_found(self):
        r = self.ac.release_quarantine(
            quarantine_id="nonexistent"
        )
        assert r["released"] is False

    def test_reinstate_account(self):
        self.ac.contain_incident(
            incident_id="inc_s",
            actions=["account_suspend"],
            targets=["user1"],
        )
        sid = list(
            self.ac._suspensions.keys()
        )[0]
        r = self.ac.reinstate_account(
            suspension_id=sid,
            reason="Clear",
        )
        assert r["reinstated"] is True

    def test_reinstate_not_found(self):
        r = self.ac.reinstate_account(
            suspension_id="nonexistent"
        )
        assert r["reinstated"] is False

    def test_get_actions(self):
        self.ac.contain_incident(
            incident_id="inc_ga",
            actions=["port_block"],
            targets=["port_22"],
        )
        r = self.ac.get_actions(
            incident_id="inc_ga"
        )
        assert r["retrieved"] is True
        assert r["count"] >= 1

    def test_get_actions_all(self):
        self.ac.contain_incident(
            incident_id="inc_all",
            actions=["ip_block"],
            targets=["10.0.0.1"],
        )
        r = self.ac.get_actions()
        assert r["retrieved"] is True

    def test_service_shutdown_stat(self):
        self.ac.contain_incident(
            incident_id="inc_ss",
            actions=["service_shutdown"],
            targets=["web_server"],
        )
        assert (
            self.ac._stats["services_shutdown"]
            >= 1
        )

    def test_get_summary(self):
        s = self.ac.get_summary()
        assert s["retrieved"] is True
        assert "auto_contain" in s
        assert "stats" in s


# ==================== ForensicCollector ====================

class TestForensicCollector:
    """ForensicCollector testleri."""

    def setup_method(self):
        self.fc = ForensicCollector()

    def test_init(self):
        assert self.fc.evidence_count == 0
        assert len(self.fc.EVIDENCE_TYPES) == 8

    def test_collect_evidence(self):
        r = self.fc.collect_evidence(
            incident_id="inc_1",
            evidence_type="log_file",
            title="Auth logs",
            content="login failed",
            collector="analyst1",
        )
        assert r["collected"] is True
        assert "evidence_id" in r
        assert "hash" in r

    def test_collect_invalid_type(self):
        r = self.fc.collect_evidence(
            evidence_type="invalid_type",
        )
        assert r["collected"] is False

    def test_transfer_custody(self):
        r = self.fc.collect_evidence(
            incident_id="inc_t",
            title="Transfer test",
            content="data",
            collector="a1",
        )
        eid = r["evidence_id"]
        t = self.fc.transfer_custody(
            evidence_id=eid,
            from_handler="a1",
            to_handler="a2",
            reason="Handoff",
        )
        assert t["transferred"] is True
        assert t["chain_length"] == 2

    def test_transfer_not_found(self):
        t = self.fc.transfer_custody(
            evidence_id="nonexistent",
        )
        assert t["transferred"] is False

    def test_verify_integrity_intact(self):
        r = self.fc.collect_evidence(
            incident_id="inc_v",
            title="Verify",
            content="test_content_123",
        )
        v = self.fc.verify_integrity(
            evidence_id=r["evidence_id"]
        )
        assert v["verified"] is True
        assert v["is_intact"] is True

    def test_verify_integrity_tampered(self):
        r = self.fc.collect_evidence(
            incident_id="inc_vt",
            title="Tamper",
            content="original",
        )
        # Icerigi degistir
        eid = r["evidence_id"]
        self.fc._evidence[eid][
            "content"
        ] = "modified"
        v = self.fc.verify_integrity(
            evidence_id=eid
        )
        assert v["verified"] is True
        assert v["is_intact"] is False

    def test_verify_not_found(self):
        v = self.fc.verify_integrity(
            evidence_id="nonexistent"
        )
        assert v["verified"] is False

    def test_take_snapshot(self):
        r = self.fc.take_snapshot(
            incident_id="inc_s",
            system="web_server",
            snapshot_type="full",
            data={"cpu": 80},
        )
        assert r["taken"] is True
        assert "snapshot_id" in r

    def test_get_evidence(self):
        self.fc.collect_evidence(
            incident_id="inc_ge",
            title="Get test",
            content="data",
        )
        r = self.fc.get_evidence(
            incident_id="inc_ge"
        )
        assert r["retrieved"] is True
        assert r["count"] >= 1

    def test_get_evidence_all(self):
        self.fc.collect_evidence(
            incident_id="inc_all",
            title="All",
            content="data",
        )
        r = self.fc.get_evidence()
        assert r["retrieved"] is True

    def test_get_custody_chain(self):
        ev = self.fc.collect_evidence(
            incident_id="inc_cc",
            title="Chain",
            content="data",
            collector="a1",
        )
        r = self.fc.get_custody_chain(
            evidence_id=ev["evidence_id"]
        )
        assert r["retrieved"] is True
        assert r["length"] >= 1

    def test_get_custody_not_found(self):
        r = self.fc.get_custody_chain(
            evidence_id="nonexistent"
        )
        assert r["retrieved"] is False

    def test_get_summary(self):
        self.fc.collect_evidence(
            incident_id="inc_sum",
            title="Sum",
            content="data",
        )
        s = self.fc.get_summary()
        assert s["retrieved"] is True
        assert s["total_evidence"] >= 1
        assert "by_type" in s


# ==================== RootCauseAnalyzer ====================

class TestRootCauseAnalyzer:
    """IncidentRootCauseAnalyzer testleri."""

    def setup_method(self):
        self.rca = IncidentRootCauseAnalyzer()

    def test_init(self):
        assert self.rca.analysis_count == 0
        assert (
            len(self.rca.CAUSE_CATEGORIES) == 10
        )

    def test_start_analysis(self):
        r = self.rca.start_analysis(
            incident_id="inc_1",
            title="RCA Test",
            analyst="analyst1",
        )
        assert r["started"] is True
        assert "analysis_id" in r

    def test_add_root_cause(self):
        r = self.rca.start_analysis(
            incident_id="inc_2",
            title="RCA 2",
        )
        aid = r["analysis_id"]
        c = self.rca.add_root_cause(
            analysis_id=aid,
            category="software_bug",
            description="Buffer overflow",
            confidence=0.8,
        )
        assert c["added"] is True
        assert c["confidence"] == 0.8

    def test_add_root_cause_not_found(self):
        c = self.rca.add_root_cause(
            analysis_id="nonexistent",
        )
        assert c["added"] is False

    def test_add_root_cause_invalid_cat(self):
        r = self.rca.start_analysis(
            incident_id="inc_3",
            title="RCA 3",
        )
        c = self.rca.add_root_cause(
            analysis_id=r["analysis_id"],
            category="invalid_cat",
        )
        assert c["added"] is False

    def test_add_root_cause_clamp_confidence(self):
        r = self.rca.start_analysis(
            incident_id="inc_cl",
            title="Clamp",
        )
        c = self.rca.add_root_cause(
            analysis_id=r["analysis_id"],
            category="human_error",
            confidence=1.5,
        )
        assert c["added"] is True
        assert c["confidence"] == 1.0

    def test_build_timeline(self):
        r = self.rca.start_analysis(
            incident_id="inc_4",
            title="Timeline",
        )
        t = self.rca.build_timeline(
            analysis_id=r["analysis_id"],
            event="Initial access",
            source="firewall",
            severity="high",
        )
        assert t["added"] is True

    def test_build_timeline_not_found(self):
        t = self.rca.build_timeline(
            analysis_id="nonexistent",
            event="Test",
        )
        assert t["added"] is False

    def test_identify_entry_point(self):
        r = self.rca.identify_entry_point(
            incident_id="inc_5",
            entry_type="phishing_email",
            target="user@test.com",
            method="spear_phishing",
        )
        assert r["identified"] is True
        assert "entry_id" in r

    def test_track_propagation(self):
        r = self.rca.track_propagation(
            incident_id="inc_6",
            from_system="workstation",
            to_system="server",
            method="lateral_movement",
        )
        assert r["tracked"] is True

    def test_link_vulnerability(self):
        r = self.rca.link_vulnerability(
            incident_id="inc_7",
            cve_id="CVE-2024-1234",
            severity="critical",
            description="RCE vuln",
            affected_component="web_server",
        )
        assert r["linked"] is True
        assert r["cve_id"] == "CVE-2024-1234"

    def test_complete_analysis(self):
        r = self.rca.start_analysis(
            incident_id="inc_8",
            title="Complete",
        )
        c = self.rca.complete_analysis(
            analysis_id=r["analysis_id"],
            conclusion="Root cause found",
        )
        assert c["completed"] is True

    def test_complete_not_found(self):
        c = self.rca.complete_analysis(
            analysis_id="nonexistent",
        )
        assert c["completed"] is False

    def test_get_timeline(self):
        r = self.rca.start_analysis(
            incident_id="inc_gt",
            title="Get TL",
        )
        self.rca.build_timeline(
            analysis_id=r["analysis_id"],
            event="Event 1",
        )
        t = self.rca.get_timeline(
            analysis_id=r["analysis_id"]
        )
        assert t["retrieved"] is True
        assert t["count"] >= 1

    def test_get_timeline_not_found(self):
        t = self.rca.get_timeline(
            analysis_id="nonexistent"
        )
        assert t["retrieved"] is False

    def test_get_summary(self):
        s = self.rca.get_summary()
        assert s["retrieved"] is True
        assert "by_category" in s


# ==================== ImpactAssessor ====================

class TestImpactAssessor:
    """IncidentImpactAssessor testleri."""

    def setup_method(self):
        self.ia = IncidentImpactAssessor()

    def test_init(self):
        assert self.ia.assessment_count == 0
        assert len(self.ia.IMPACT_LEVELS) == 6
        assert (
            len(self.ia.IMPACT_CATEGORIES) == 8
        )

    def test_assess_impact(self):
        r = self.ia.assess_impact(
            incident_id="inc_1",
            title="Impact test",
            impact_level="severe",
            affected_users=5000,
            financial_impact=500000,
        )
        assert r["assessed"] is True
        assert r["impact_score"] > 0

    def test_assess_invalid_level(self):
        r = self.ia.assess_impact(
            impact_level="invalid",
        )
        assert r["assessed"] is False

    def test_assess_catastrophic_score(self):
        r = self.ia.assess_impact(
            incident_id="inc_cat",
            impact_level="catastrophic",
            categories=[
                "data_exposure",
                "financial",
                "regulatory",
                "reputational",
            ],
            affected_users=50000,
            financial_impact=5000000,
        )
        assert r["assessed"] is True
        assert r["impact_score"] == 1.0

    def test_assess_negligible_score(self):
        r = self.ia.assess_impact(
            incident_id="inc_neg",
            impact_level="negligible",
        )
        assert r["assessed"] is True
        assert r["impact_score"] == 0.1

    def test_record_data_exposure(self):
        r = self.ia.record_data_exposure(
            incident_id="inc_de",
            data_type="PII",
            record_count=10000,
            sensitivity="high",
        )
        assert r["recorded"] is True
        assert r["record_count"] == 10000

    def test_record_system_compromise(self):
        r = self.ia.record_system_compromise(
            incident_id="inc_sc",
            system="database_server",
            compromise_type="unauthorized_access",
            access_level="admin",
        )
        assert r["recorded"] is True
        assert r["system"] == "database_server"

    def test_assess_regulatory_impact(self):
        self.ia.assess_impact(
            incident_id="inc_ri",
            title="Reg test",
            impact_level="major",
        )
        r = self.ia.assess_regulatory_impact(
            incident_id="inc_ri",
            regulation="GDPR",
            breach_type="personal_data",
            notification_required=True,
            deadline_hours=72,
            potential_fine=20000000,
        )
        assert r["assessed"] is True
        assert r["notification_required"] is True

    def test_get_business_impact(self):
        self.ia.assess_impact(
            incident_id="inc_bi",
            title="BI test",
            impact_level="moderate",
            affected_users=100,
            financial_impact=50000,
        )
        self.ia.record_data_exposure(
            incident_id="inc_bi",
            data_type="email",
            record_count=500,
        )
        r = self.ia.get_business_impact(
            incident_id="inc_bi"
        )
        assert r["retrieved"] is True
        assert r["total_users_affected"] == 100
        assert r["total_records_exposed"] == 500

    def test_get_business_impact_empty(self):
        r = self.ia.get_business_impact(
            incident_id="nonexistent"
        )
        assert r["retrieved"] is True
        assert r["assessments"] == 0

    def test_get_summary(self):
        self.ia.assess_impact(
            incident_id="inc_sum",
            title="Sum",
            impact_level="minor",
        )
        s = self.ia.get_summary()
        assert s["retrieved"] is True
        assert s["total_assessments"] >= 1
        assert "by_level" in s


# ==================== RecoveryExecutor ====================

class TestRecoveryExecutor:
    """RecoveryExecutor testleri."""

    def setup_method(self):
        self.re = RecoveryExecutor()

    def test_init(self):
        assert self.re.active_plans == 0
        assert len(self.re.RECOVERY_TYPES) == 8

    def test_create_plan(self):
        r = self.re.create_plan(
            incident_id="inc_1",
            title="Recovery plan",
            priority="critical",
            steps=[
                {"type": "service_restore"},
            ],
        )
        assert r["created"] is True
        assert r["steps"] == 1

    def test_execute_recovery(self):
        p = self.re.create_plan(
            incident_id="inc_2",
            title="Exec plan",
        )
        r = self.re.execute_recovery(
            plan_id=p["plan_id"],
            recovery_type="service_restore",
            target="web_server",
        )
        assert r["executed"] is True
        assert "checkpoint_id" in r

    def test_execute_invalid_type(self):
        r = self.re.execute_recovery(
            recovery_type="invalid_type",
        )
        assert r["executed"] is False

    def test_verify_recovery(self):
        p = self.re.create_plan(
            incident_id="inc_v",
            title="Verify",
        )
        ex = self.re.execute_recovery(
            plan_id=p["plan_id"],
            recovery_type="data_recovery",
            target="database",
        )
        v = self.re.verify_recovery(
            action_id=ex["action_id"],
            checks=["data_integrity"],
        )
        assert v["verified"] is True
        assert v["all_passed"] is True

    def test_verify_not_found(self):
        v = self.re.verify_recovery(
            action_id="nonexistent"
        )
        assert v["verified"] is False

    def test_rollback(self):
        p = self.re.create_plan(
            incident_id="inc_rb",
            title="Rollback",
        )
        ex = self.re.execute_recovery(
            plan_id=p["plan_id"],
            recovery_type="patch_apply",
            target="app_server",
        )
        r = self.re.rollback(
            action_id=ex["action_id"],
            reason="Patch caused issues",
        )
        assert r["rolled_back"] is True

    def test_rollback_not_found(self):
        r = self.re.rollback(
            action_id="nonexistent"
        )
        assert r["rolled_back"] is False

    def test_complete_plan(self):
        p = self.re.create_plan(
            incident_id="inc_cp",
            title="Complete",
        )
        self.re.execute_recovery(
            plan_id=p["plan_id"],
            recovery_type="service_restore",
            target="srv1",
        )
        r = self.re.complete_plan(
            plan_id=p["plan_id"]
        )
        assert r["completed"] is True
        assert r["actions_count"] >= 1

    def test_complete_not_found(self):
        r = self.re.complete_plan(
            plan_id="nonexistent"
        )
        assert r["completed"] is False

    def test_active_plans_property(self):
        self.re.create_plan(
            incident_id="inc_ap",
            title="Active",
        )
        assert self.re.active_plans >= 1

    def test_failover_restores_service(self):
        p = self.re.create_plan(
            incident_id="inc_fo",
            title="Failover",
        )
        self.re.execute_recovery(
            plan_id=p["plan_id"],
            recovery_type="failover",
            target="primary_db",
        )
        assert (
            self.re._stats["services_restored"]
            >= 1
        )

    def test_get_summary(self):
        s = self.re.get_summary()
        assert s["retrieved"] is True
        assert "by_type" in s
        assert "stats" in s


# ==================== LessonLearner ====================

class TestLessonLearner:
    """IncidentLessonLearner testleri."""

    def setup_method(self):
        self.ll = IncidentLessonLearner()

    def test_init(self):
        assert self.ll.lesson_count == 0
        assert (
            len(self.ll.LESSON_CATEGORIES) == 8
        )

    def test_record_lesson(self):
        r = self.ll.record_lesson(
            incident_id="inc_1",
            title="Lesson 1",
            category="detection",
            what_went_well="Fast alert",
            what_went_wrong="Slow contain",
            recommendations=["Automate"],
        )
        assert r["recorded"] is True
        assert r["category"] == "detection"

    def test_record_invalid_category(self):
        r = self.ll.record_lesson(
            category="invalid_cat",
        )
        assert r["recorded"] is False

    def test_define_prevention(self):
        l = self.ll.record_lesson(
            incident_id="inc_p",
            title="Prev lesson",
            category="containment",
        )
        r = self.ll.define_prevention(
            lesson_id=l["lesson_id"],
            title="Auto-isolate",
            measure_type="automation",
            priority="critical",
            owner="security_team",
        )
        assert r["defined"] is True
        assert r["priority"] == "critical"

    def test_propose_improvement(self):
        l = self.ll.record_lesson(
            incident_id="inc_i",
            title="Improve",
            category="process",
        )
        r = self.ll.propose_improvement(
            lesson_id=l["lesson_id"],
            area="incident_response",
            current_state="Manual",
            proposed_state="Automated",
            effort="medium",
            impact="high",
        )
        assert r["proposed"] is True

    def test_create_kb_article(self):
        r = self.ll.create_kb_article(
            incident_id="inc_kb",
            title="Malware guide",
            content="Steps to handle...",
            tags=["malware", "response"],
            category="playbook",
        )
        assert r["created"] is True
        assert r["title"] == "Malware guide"

    def test_trigger_training(self):
        r = self.ll.trigger_training(
            lesson_id="ll_1",
            topic="Phishing awareness",
            target_audience="all_staff",
            urgency="high",
        )
        assert r["triggered"] is True
        assert r["topic"] == "Phishing awareness"

    def test_get_lessons(self):
        self.ll.record_lesson(
            incident_id="inc_gl",
            title="Get test",
            category="recovery",
        )
        r = self.ll.get_lessons(
            incident_id="inc_gl"
        )
        assert r["retrieved"] is True
        assert r["count"] >= 1

    def test_get_lessons_all(self):
        self.ll.record_lesson(
            incident_id="inc_all",
            title="All",
            category="technology",
        )
        r = self.ll.get_lessons()
        assert r["retrieved"] is True

    def test_get_summary(self):
        self.ll.record_lesson(
            incident_id="inc_s",
            title="Sum",
            category="communication",
        )
        s = self.ll.get_summary()
        assert s["retrieved"] is True
        assert s["total_lessons"] >= 1
        assert "by_category" in s


# ==================== PlaybookGenerator ====================

class TestPlaybookGenerator:
    """PlaybookGenerator testleri."""

    def setup_method(self):
        self.pg = PlaybookGenerator()

    def test_init(self):
        assert self.pg.playbook_count == 0
        assert len(self.pg.PLAYBOOK_TYPES) == 8

    def test_create_playbook(self):
        r = self.pg.create_playbook(
            name="Malware PB",
            playbook_type="malware_response",
            description="Handle malware",
            severity_trigger="high",
        )
        assert r["created"] is True
        assert r["name"] == "Malware PB"

    def test_create_invalid_type(self):
        r = self.pg.create_playbook(
            playbook_type="invalid_type",
        )
        assert r["created"] is False

    def test_add_procedure(self):
        pb = self.pg.create_playbook(
            name="Proc PB",
            playbook_type="phishing_response",
        )
        r = self.pg.add_procedure(
            playbook_id=pb["playbook_id"],
            name="Isolate system",
            step_order=1,
            action="network_isolate",
            responsible="soc_team",
            timeout_minutes=15,
        )
        assert r["added"] is True
        assert r["step_order"] == 1

    def test_add_procedure_not_found(self):
        r = self.pg.add_procedure(
            playbook_id="nonexistent",
            name="Test",
        )
        assert r["added"] is False

    def test_add_multiple_procedures(self):
        pb = self.pg.create_playbook(
            name="Multi PB",
            playbook_type="data_breach",
        )
        pid = pb["playbook_id"]
        self.pg.add_procedure(
            playbook_id=pid,
            name="Step 1",
            step_order=1,
            action="detect",
        )
        self.pg.add_procedure(
            playbook_id=pid,
            name="Step 2",
            step_order=2,
            action="contain",
        )
        pb_data = self.pg._playbooks[pid]
        assert len(pb_data["procedures"]) == 2

    def test_create_automation(self):
        pb = self.pg.create_playbook(
            name="Auto PB",
            playbook_type="ransomware",
        )
        r = self.pg.create_automation(
            playbook_id=pb["playbook_id"],
            name="Auto isolate",
            trigger_condition="severity==critical",
            action_type="network_isolate",
            enabled=True,
        )
        assert r["created"] is True
        assert r["enabled"] is True

    def test_test_playbook(self):
        pb = self.pg.create_playbook(
            name="Test PB",
            playbook_type="dos_attack",
        )
        pid = pb["playbook_id"]
        self.pg.add_procedure(
            playbook_id=pid,
            name="Block",
            step_order=1,
            action="ip_block",
        )
        r = self.pg.test_playbook(
            playbook_id=pid,
            scenario="DDoS simulation",
            dry_run=True,
        )
        assert r["tested"] is True
        assert r["all_passed"] is True
        assert r["steps_tested"] >= 1

    def test_test_not_found(self):
        r = self.pg.test_playbook(
            playbook_id="nonexistent",
        )
        assert r["tested"] is False

    def test_publish_version(self):
        pb = self.pg.create_playbook(
            name="Publish PB",
            playbook_type="insider_threat",
        )
        r = self.pg.publish_version(
            playbook_id=pb["playbook_id"],
            notes="v2 release",
        )
        assert r["published"] is True
        assert r["version"] == 2

    def test_publish_not_found(self):
        r = self.pg.publish_version(
            playbook_id="nonexistent",
        )
        assert r["published"] is False

    def test_get_playbook(self):
        pb = self.pg.create_playbook(
            name="Get PB",
            playbook_type="unauthorized_access",
        )
        r = self.pg.get_playbook(
            playbook_id=pb["playbook_id"]
        )
        assert r["retrieved"] is True
        assert r["name"] == "Get PB"

    def test_get_playbook_not_found(self):
        r = self.pg.get_playbook(
            playbook_id="nonexistent"
        )
        assert r["retrieved"] is False

    def test_get_summary(self):
        self.pg.create_playbook(
            name="Sum PB",
            playbook_type="general_incident",
        )
        s = self.pg.get_summary()
        assert s["retrieved"] is True
        assert s["total_playbooks"] >= 1
        assert "by_type" in s


# ==================== Orchestrator ====================

class TestIncidentOrchestrator:
    """IncidentOrchestrator testleri."""

    def setup_method(self):
        self.orch = IncidentOrchestrator(
            auto_contain=True
        )

    def test_init(self):
        assert self.orch.detector is not None
        assert self.orch.containment is not None
        assert self.orch.forensic is not None
        assert self.orch.root_cause is not None
        assert self.orch.impact is not None
        assert self.orch.recovery is not None
        assert self.orch.lessons is not None
        assert self.orch.playbook is not None

    def test_respond_to_incident(self):
        r = self.orch.respond_to_incident(
            title="Malware attack",
            incident_type="malware",
            severity="critical",
            source="EDR",
            description="Malware detected",
            indicators=["hash_1", "ip_1"],
            affected_systems=["srv1"],
            auto_contain_actions=[
                "network_isolate",
            ],
        )
        assert r["responded"] is True
        assert "incident_id" in r
        assert "detection" in r
        assert "containment" in r
        assert "impact" in r
        assert "root_cause" in r

    def test_respond_without_containment(self):
        r = self.orch.respond_to_incident(
            title="Info event",
            incident_type="phishing",
            severity="low",
            source="email",
        )
        assert r["responded"] is True
        assert "containment" not in r

    def test_respond_invalid_type(self):
        r = self.orch.respond_to_incident(
            incident_type="invalid",
        )
        assert r["responded"] is False

    def test_recover_incident(self):
        resp = self.orch.respond_to_incident(
            title="Recovery test",
            incident_type="ransomware",
            severity="high",
        )
        r = self.orch.recover_incident(
            incident_id=resp["incident_id"],
            title="Recovery plan",
            recovery_steps=[
                {
                    "type": "service_restore",
                    "target": "web_app",
                },
                {
                    "type": "data_recovery",
                    "target": "database",
                },
            ],
        )
        assert r["recovered"] is True
        assert r["actions"] == 2

    def test_recover_empty_steps(self):
        resp = self.orch.respond_to_incident(
            title="Empty recovery",
            incident_type="malware",
            severity="medium",
        )
        r = self.orch.recover_incident(
            incident_id=resp["incident_id"],
            title="Empty plan",
        )
        assert r["recovered"] is True
        assert r["actions"] == 0

    def test_close_incident(self):
        resp = self.orch.respond_to_incident(
            title="Close test",
            incident_type="data_breach",
            severity="high",
        )
        r = self.orch.close_incident(
            incident_id=resp["incident_id"],
            lesson_title="Better monitoring",
            lesson_category="detection",
            what_went_well="Quick detect",
            what_went_wrong="Slow contain",
            recommendations=["Automate"],
        )
        assert r["closed"] is True
        assert r["lesson"]["recorded"] is True

    def test_full_lifecycle(self):
        # Detect -> Contain -> Recover -> Close
        resp = self.orch.respond_to_incident(
            title="Full cycle",
            incident_type="unauthorized_access",
            severity="critical",
            indicators=["ip_suspicious"],
            affected_systems=["auth_server"],
            auto_contain_actions=[
                "account_suspend",
            ],
        )
        iid = resp["incident_id"]
        assert resp["responded"] is True

        # Recover
        rec = self.orch.recover_incident(
            incident_id=iid,
            title="Restore auth",
            recovery_steps=[
                {
                    "type": "credential_reset",
                    "target": "admin_user",
                },
            ],
        )
        assert rec["recovered"] is True

        # Close
        cl = self.orch.close_incident(
            incident_id=iid,
            lesson_title="Auth hardening",
            lesson_category="technology",
        )
        assert cl["closed"] is True

    def test_severity_to_impact(self):
        assert (
            self.orch._severity_to_impact(
                "critical"
            )
            == "catastrophic"
        )
        assert (
            self.orch._severity_to_impact(
                "high"
            )
            == "severe"
        )
        assert (
            self.orch._severity_to_impact(
                "medium"
            )
            == "moderate"
        )
        assert (
            self.orch._severity_to_impact(
                "low"
            )
            == "minor"
        )
        assert (
            self.orch._severity_to_impact(
                "unknown"
            )
            == "moderate"
        )

    def test_get_analytics(self):
        self.orch.respond_to_incident(
            title="Analytics test",
            incident_type="malware",
            severity="high",
        )
        r = self.orch.get_analytics()
        assert r["retrieved"] is True
        assert "detection" in r
        assert "containment" in r
        assert "forensics" in r
        assert "impact" in r
        assert "lessons" in r
        assert "playbook" in r

    def test_get_summary(self):
        self.orch.respond_to_incident(
            title="Summary test",
            incident_type="phishing",
            severity="medium",
        )
        s = self.orch.get_summary()
        assert s["retrieved"] is True
        assert s["total_incidents"] >= 1
        assert "active_quarantines" in s


# ==================== Models ====================

class TestIncidentModels:
    """Incident modelleri testleri."""

    def test_incident_type_enum(self):
        from app.models.incident_models import (
            IncidentType,
        )
        assert IncidentType.MALWARE == "malware"
        assert len(IncidentType) == 10

    def test_severity_level_enum(self):
        from app.models.incident_models import (
            SeverityLevel,
        )
        assert SeverityLevel.CRITICAL == "critical"
        assert len(SeverityLevel) == 5

    def test_incident_status_enum(self):
        from app.models.incident_models import (
            IncidentStatus,
        )
        assert IncidentStatus.ACTIVE == "active"
        assert len(IncidentStatus) == 6

    def test_impact_level_enum(self):
        from app.models.incident_models import (
            ImpactLevel,
        )
        assert (
            ImpactLevel.CATASTROPHIC
            == "catastrophic"
        )
        assert len(ImpactLevel) == 6

    def test_evidence_type_enum(self):
        from app.models.incident_models import (
            EvidenceType,
        )
        assert (
            EvidenceType.LOG_FILE == "log_file"
        )
        assert len(EvidenceType) == 8

    def test_containment_action_enum(self):
        from app.models.incident_models import (
            ContainmentAction,
        )
        assert (
            ContainmentAction.NETWORK_ISOLATE
            == "network_isolate"
        )
        assert len(ContainmentAction) == 8

    def test_playbook_type_enum(self):
        from app.models.incident_models import (
            PlaybookType,
        )
        assert (
            PlaybookType.GENERAL
            == "general_incident"
        )
        assert len(PlaybookType) == 8

    def test_cause_category_enum(self):
        from app.models.incident_models import (
            CauseCategory,
        )
        assert (
            CauseCategory.HUMAN_ERROR
            == "human_error"
        )
        assert len(CauseCategory) == 10

    def test_incident_record_model(self):
        from app.models.incident_models import (
            IncidentRecord,
        )
        rec = IncidentRecord(
            incident_id="inc_1",
            title="Test",
            incident_type="malware",
            severity="high",
        )
        assert rec.incident_id == "inc_1"
        assert rec.indicators == []

    def test_evidence_record_model(self):
        from app.models.incident_models import (
            EvidenceRecord,
        )
        ev = EvidenceRecord(
            evidence_id="ev_1",
            evidence_type="log_file",
        )
        assert ev.integrity == "verified"

    def test_impact_assessment_model(self):
        from app.models.incident_models import (
            ImpactAssessment,
        )
        ia = ImpactAssessment(
            impact_level="severe",
            impact_score=0.85,
        )
        assert ia.impact_score == 0.85

    def test_recovery_plan_model(self):
        from app.models.incident_models import (
            RecoveryPlan,
        )
        rp = RecoveryPlan(
            plan_id="rp_1",
            priority="critical",
        )
        assert rp.status == "created"

    def test_playbook_record_model(self):
        from app.models.incident_models import (
            PlaybookRecord,
        )
        pb = PlaybookRecord(
            name="Test PB",
            version=2,
        )
        assert pb.version == 2
        assert pb.auto_execute is False

    def test_lesson_record_model(self):
        from app.models.incident_models import (
            LessonRecord,
        )
        lr = LessonRecord(
            title="Lesson",
            category="process",
        )
        assert lr.recommendations == []

    def test_root_cause_model(self):
        from app.models.incident_models import (
            RootCauseAnalysis,
        )
        rca = RootCauseAnalysis(
            analysis_id="rca_1",
            status="in_progress",
        )
        assert rca.root_causes == []

    def test_incident_summary_model(self):
        from app.models.incident_models import (
            IncidentSummary,
        )
        s = IncidentSummary(
            total_incidents=10,
            active_incidents=3,
        )
        assert s.total_incidents == 10


# ==================== Config ====================

class TestIncidentConfig:
    """Incident config testleri."""

    def test_incident_config_defaults(self):
        from app.config import Settings

        s = Settings()
        assert s.incident_enabled is True
        assert s.auto_contain is True
        assert s.forensic_collection is True
        assert s.playbook_enabled is True
        assert s.lesson_learning is True
