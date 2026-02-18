"""
Compliance & Regulatory Monitor testleri.

ComplianceFrameworkLoader,
CompliancePolicyEnforcer,
DataFlowMapper,
ComplianceAccessAuditor,
RetentionPolicyChecker,
ComplianceConsentManager,
ComplianceReportGenerator,
ComplianceGapAnalyzer,
ComplianceOrchestrator,
modeller ve config testleri.
"""

import pytest
from datetime import (
    datetime,
    timezone,
    timedelta,
)

from app.core.compliance.compliance_framework_loader import (
    ComplianceFrameworkLoader,
)
from app.core.compliance.policy_enforcer import (
    CompliancePolicyEnforcer,
)
from app.core.compliance.data_flow_mapper import (
    DataFlowMapper,
)
from app.core.compliance.compliance_access_auditor import (
    ComplianceAccessAuditor,
)
from app.core.compliance.retention_policy_checker import (
    RetentionPolicyChecker,
)
from app.core.compliance.consent_manager import (
    ComplianceConsentManager,
)
from app.core.compliance.compliance_report_generator import (
    ComplianceReportGenerator,
)
from app.core.compliance.compliance_gap_analyzer import (
    ComplianceGapAnalyzer,
)
from app.core.compliance.compliance_orchestrator import (
    ComplianceOrchestrator,
)
from app.models.compliance_models import (
    ComplianceFramework,
    PolicyType,
    DataCategory,
    ConsentStatus,
    GapSeverity,
    GapStatus,
    ReportType,
    RetentionType,
    FrameworkInfo,
    PolicyRecord,
    DataFlowRecord,
    ConsentRecord,
    GapRecord,
    ComplianceReport,
    RetentionPolicy,
    ComplianceStatus,
)


# ──────────────────────────────────
# ComplianceFrameworkLoader
# ──────────────────────────────────
class TestComplianceFrameworkLoader:
    """ComplianceFrameworkLoader testleri."""

    def setup_method(self):
        self.loader = (
            ComplianceFrameworkLoader()
        )

    def test_init_builtin(self):
        assert self.loader.framework_count == 4
        s = self.loader.get_summary()
        assert s["retrieved"]
        assert s["total_frameworks"] == 4

    def test_get_builtin_gdpr(self):
        r = self.loader.get_framework(
            key="gdpr"
        )
        assert r["retrieved"]
        assert r["name"] == "GDPR"
        assert r["region"] == "EU"

    def test_get_builtin_kvkk(self):
        r = self.loader.get_framework(
            key="kvkk"
        )
        assert r["retrieved"]
        assert "KVKK" in r["name"]

    def test_get_builtin_pci_dss(self):
        r = self.loader.get_framework(
            key="pci_dss"
        )
        assert r["retrieved"]

    def test_get_builtin_soc2(self):
        r = self.loader.get_framework(
            key="soc2"
        )
        assert r["retrieved"]

    def test_load_custom_framework(self):
        r = self.loader.load_framework(
            key="custom1",
            name="Custom Framework",
            version="2.0",
            region="TR",
            categories=["data", "access"],
        )
        assert r["loaded"]
        assert self.loader.framework_count == 5

    def test_duplicate_key(self):
        r = self.loader.load_framework(
            key="gdpr",
            name="Duplicate",
        )
        assert not r["loaded"]
        assert "error" in r

    def test_map_requirement(self):
        r = self.loader.map_requirement(
            framework_key="gdpr",
            requirement_id="art5",
            title="Data Processing",
            category="data_protection",
            severity="high",
        )
        assert r["mapped"]

    def test_map_requirement_invalid(self):
        r = self.loader.map_requirement(
            framework_key="nonexistent",
            requirement_id="x",
            title="x",
        )
        assert not r["mapped"]

    def test_list_frameworks(self):
        r = self.loader.list_frameworks()
        assert r["retrieved"]
        assert r["total"] >= 4

    def test_get_nonexistent(self):
        r = self.loader.get_framework(
            key="nonexistent"
        )
        assert not r["retrieved"]

    def test_framework_count_property(self):
        assert (
            self.loader.framework_count
            >= 4
        )

    def test_get_summary_stats(self):
        s = self.loader.get_summary()
        assert s["retrieved"]
        assert (
            s["stats"]["frameworks_loaded"]
            >= 4
        )


# ──────────────────────────────────
# CompliancePolicyEnforcer
# ──────────────────────────────────
class TestCompliancePolicyEnforcer:
    """CompliancePolicyEnforcer testleri."""

    def setup_method(self):
        self.enforcer = (
            CompliancePolicyEnforcer()
        )

    def test_create_policy(self):
        r = self.enforcer.create_policy(
            name="Sifreleme",
            policy_type="encryption",
            severity="high",
        )
        assert r["created"]
        assert r["policy_id"].startswith(
            "pl_"
        )

    def test_create_invalid_type(self):
        r = self.enforcer.create_policy(
            name="x",
            policy_type="invalid",
        )
        assert not r["created"]

    def test_evaluate_compliant(self):
        cp = self.enforcer.create_policy(
            name="Test",
            rules=[
                {
                    "field": "encryption",
                    "operator": "equals",
                    "value": True,
                }
            ],
        )
        r = self.enforcer.evaluate(
            policy_id=cp["policy_id"],
            context={"encryption": True},
        )
        assert r["evaluated"]
        assert r["compliant"]
        assert r["violations"] == 0

    def test_evaluate_violation(self):
        cp = self.enforcer.create_policy(
            name="Test",
            rules=[
                {
                    "field": "encryption",
                    "operator": "equals",
                    "value": True,
                }
            ],
            severity="high",
        )
        r = self.enforcer.evaluate(
            policy_id=cp["policy_id"],
            context={"encryption": False},
        )
        assert r["evaluated"]
        assert not r["compliant"]
        assert r["violations"] > 0

    def test_evaluate_exists_operator(self):
        cp = self.enforcer.create_policy(
            name="Test",
            rules=[
                {
                    "field": "consent",
                    "operator": "exists",
                }
            ],
        )
        r = self.enforcer.evaluate(
            policy_id=cp["policy_id"],
            context={},
        )
        assert not r["compliant"]

    def test_evaluate_min_operator(self):
        cp = self.enforcer.create_policy(
            name="Test",
            rules=[
                {
                    "field": "password_len",
                    "operator": "min",
                    "value": 8,
                }
            ],
        )
        r = self.enforcer.evaluate(
            policy_id=cp["policy_id"],
            context={"password_len": 5},
        )
        assert not r["compliant"]

    def test_evaluate_max_operator(self):
        cp = self.enforcer.create_policy(
            name="Test",
            rules=[
                {
                    "field": "retry",
                    "operator": "max",
                    "value": 3,
                }
            ],
        )
        r = self.enforcer.evaluate(
            policy_id=cp["policy_id"],
            context={"retry": 5},
        )
        assert not r["compliant"]

    def test_evaluate_not_equals(self):
        cp = self.enforcer.create_policy(
            name="Test",
            rules=[
                {
                    "field": "status",
                    "operator": "not_equals",
                    "value": "disabled",
                }
            ],
        )
        r = self.enforcer.evaluate(
            policy_id=cp["policy_id"],
            context={
                "status": "disabled"
            },
        )
        assert not r["compliant"]

    def test_auto_remediate(self):
        enf = CompliancePolicyEnforcer(
            auto_remediate=True
        )
        cp = enf.create_policy(
            name="Test",
            rules=[
                {
                    "field": "x",
                    "operator": "exists",
                }
            ],
        )
        r = enf.evaluate(
            policy_id=cp["policy_id"],
            context={},
        )
        assert not r["compliant"]
        s = enf.get_summary()
        assert (
            s["stats"]["auto_remediations"]
            > 0
        )

    def test_grant_exception(self):
        cp = self.enforcer.create_policy(
            name="Test"
        )
        r = self.enforcer.grant_exception(
            policy_id=cp["policy_id"],
            reason="Migration",
            approved_by="admin",
        )
        assert r["granted"]

    def test_grant_exception_invalid(self):
        r = self.enforcer.grant_exception(
            policy_id="nonexistent"
        )
        assert not r["granted"]

    def test_get_violations(self):
        cp = self.enforcer.create_policy(
            name="Test",
            rules=[
                {
                    "field": "x",
                    "operator": "exists",
                }
            ],
            severity="critical",
        )
        self.enforcer.evaluate(
            policy_id=cp["policy_id"],
            context={},
        )
        r = self.enforcer.get_violations(
            severity="critical"
        )
        assert r["retrieved"]
        assert r["count"] > 0

    def test_get_all_violations(self):
        r = self.enforcer.get_violations()
        assert r["retrieved"]

    def test_evaluate_nonexistent(self):
        r = self.enforcer.evaluate(
            policy_id="nonexistent"
        )
        assert not r["evaluated"]

    def test_violation_count_property(self):
        assert (
            self.enforcer.violation_count
            == 0
        )

    def test_get_summary(self):
        s = self.enforcer.get_summary()
        assert s["retrieved"]
        assert "auto_remediate" in s


# ──────────────────────────────────
# DataFlowMapper
# ──────────────────────────────────
class TestDataFlowMapper:
    """DataFlowMapper testleri."""

    def setup_method(self):
        self.mapper = DataFlowMapper()

    def test_register_asset(self):
        r = self.mapper.register_data_asset(
            name="Musteri Verisi",
            category="personal",
            country="TR",
        )
        assert r["registered"]
        assert r["asset_id"].startswith(
            "da_"
        )

    def test_register_invalid_category(self):
        r = self.mapper.register_data_asset(
            name="x",
            category="invalid",
        )
        assert not r["registered"]

    def test_add_processor(self):
        r = self.mapper.add_processor(
            name="AWS",
            processor_type="cloud",
            country="US",
            dpa_signed=True,
        )
        assert r["added"]

    def test_map_flow(self):
        a = self.mapper.register_data_asset(
            name="Data", category="personal"
        )
        r = self.mapper.map_flow(
            source_asset_id=a["asset_id"],
            destination="Analytics",
            purpose="Reporting",
        )
        assert r["mapped"]

    def test_map_flow_cross_border(self):
        a = self.mapper.register_data_asset(
            name="Data",
            category="financial",
            country="TR",
        )
        r = self.mapper.map_flow(
            source_asset_id=a["asset_id"],
            destination="EU Analytics",
            purpose="Compliance",
            is_cross_border=True,
            destination_country="DE",
        )
        assert r["mapped"]
        assert r["is_cross_border"]

    def test_map_flow_invalid_asset(self):
        r = self.mapper.map_flow(
            source_asset_id="nonexistent"
        )
        assert not r["mapped"]

    def test_get_cross_border(self):
        a = self.mapper.register_data_asset(
            name="D", category="personal"
        )
        self.mapper.map_flow(
            source_asset_id=a["asset_id"],
            destination="EU",
            is_cross_border=True,
        )
        r = self.mapper.get_cross_border_transfers()
        assert r["retrieved"]
        assert r["count"] > 0

    def test_get_asset_flows(self):
        a = self.mapper.register_data_asset(
            name="D", category="health"
        )
        self.mapper.map_flow(
            source_asset_id=a["asset_id"],
            destination="Lab",
        )
        r = self.mapper.get_asset_flows(
            asset_id=a["asset_id"]
        )
        assert r["retrieved"]
        assert r["count"] > 0

    def test_asset_count_property(self):
        assert self.mapper.asset_count == 0
        self.mapper.register_data_asset(
            name="D", category="personal"
        )
        assert self.mapper.asset_count == 1

    def test_get_summary(self):
        s = self.mapper.get_summary()
        assert s["retrieved"]
        assert "total_assets" in s

    def test_multiple_categories(self):
        for cat in [
            "personal", "sensitive",
            "financial", "health",
        ]:
            r = self.mapper.register_data_asset(
                name=f"D_{cat}",
                category=cat,
            )
            assert r["registered"]
        assert self.mapper.asset_count == 4


# ──────────────────────────────────
# ComplianceAccessAuditor
# ──────────────────────────────────
class TestComplianceAccessAuditor:
    """ComplianceAccessAuditor testleri."""

    def setup_method(self):
        self.auditor = (
            ComplianceAccessAuditor()
        )

    def test_log_access(self):
        r = self.auditor.log_access(
            user_id="u1",
            resource_id="r1",
            access_type="read",
        )
        assert r["logged"]
        assert r["is_authorized"]

    def test_log_unauthorized(self):
        r = self.auditor.log_access(
            user_id="u1",
            resource_id="r1",
            is_authorized=False,
        )
        assert r["logged"]
        assert not r["is_authorized"]

    def test_privilege_usage(self):
        self.auditor.log_access(
            user_id="u1",
            access_type="admin",
        )
        self.auditor.log_access(
            user_id="u1",
            access_type="delete",
        )
        self.auditor.log_access(
            user_id="u1",
            access_type="export",
        )
        r = self.auditor.get_privilege_report()
        assert r["retrieved"]
        assert (
            r["total_privilege_uses"] == 3
        )

    def test_get_user_access(self):
        self.auditor.log_access(
            user_id="u1",
            resource_id="r1",
        )
        self.auditor.log_access(
            user_id="u1",
            resource_id="r2",
        )
        r = self.auditor.get_user_access(
            user_id="u1"
        )
        assert r["retrieved"]
        assert r["count"] == 2

    def test_get_resource_access(self):
        self.auditor.log_access(
            user_id="u1",
            resource_id="r1",
        )
        self.auditor.log_access(
            user_id="u2",
            resource_id="r1",
        )
        r = self.auditor.get_resource_access(
            resource_id="r1"
        )
        assert r["retrieved"]
        assert r["count"] == 2
        assert len(r["unique_users"]) == 2

    def test_get_unauthorized(self):
        self.auditor.log_access(
            user_id="u1",
            is_authorized=False,
        )
        r = self.auditor.get_unauthorized_attempts()
        assert r["retrieved"]
        assert r["count"] == 1

    def test_privilege_report_by_user(self):
        self.auditor.log_access(
            user_id="u1",
            access_type="admin",
        )
        self.auditor.log_access(
            user_id="u2",
            access_type="admin",
        )
        r = self.auditor.get_privilege_report()
        assert "u1" in r["by_user"]
        assert "u2" in r["by_user"]

    def test_log_count_property(self):
        assert self.auditor.log_count == 0
        self.auditor.log_access(
            user_id="u1"
        )
        assert self.auditor.log_count == 1

    def test_get_summary(self):
        s = self.auditor.get_summary()
        assert s["retrieved"]
        assert "total_logs" in s

    def test_user_access_limit(self):
        for i in range(10):
            self.auditor.log_access(
                user_id="u1",
                resource_id=f"r{i}",
            )
        r = self.auditor.get_user_access(
            user_id="u1", limit=5
        )
        assert r["count"] == 5
        assert r["total"] == 10


# ──────────────────────────────────
# RetentionPolicyChecker
# ──────────────────────────────────
class TestRetentionPolicyChecker:
    """RetentionPolicyChecker testleri."""

    def setup_method(self):
        self.checker = (
            RetentionPolicyChecker()
        )

    def test_create_policy(self):
        r = self.checker.create_policy(
            name="GDPR Retention",
            data_category="personal",
            retention_days=365,
        )
        assert r["created"]

    def test_create_invalid_type(self):
        r = self.checker.create_policy(
            name="x",
            retention_type="invalid",
        )
        assert not r["created"]

    def test_track_record(self):
        p = self.checker.create_policy(
            name="P1"
        )
        r = self.checker.track_record(
            record_id="rec1",
            data_category="personal",
            policy_id=p["policy_id"],
        )
        assert r["tracked"]

    def test_track_invalid_policy(self):
        r = self.checker.track_record(
            record_id="rec1",
            policy_id="nonexistent",
        )
        assert not r["tracked"]

    def test_check_expiration_not_expired(
        self,
    ):
        p = self.checker.create_policy(
            name="P1",
            retention_days=365,
        )
        now = datetime.now(
            timezone.utc
        ).isoformat()
        self.checker.track_record(
            record_id="rec1",
            policy_id=p["policy_id"],
            created_date=now,
        )
        r = self.checker.check_expiration(
            record_id="rec1"
        )
        assert r["checked"]
        assert not r["expired"]
        assert r["days_left"] > 0

    def test_check_expiration_expired(self):
        p = self.checker.create_policy(
            name="P1",
            retention_days=30,
        )
        old = (
            datetime.now(timezone.utc)
            - timedelta(days=60)
        ).isoformat()
        self.checker.track_record(
            record_id="rec1",
            policy_id=p["policy_id"],
            created_date=old,
        )
        r = self.checker.check_expiration(
            record_id="rec1"
        )
        assert r["checked"]
        assert r["expired"]

    def test_check_nonexistent(self):
        r = self.checker.check_expiration(
            record_id="nonexistent"
        )
        assert not r["checked"]

    def test_apply_legal_hold(self):
        p = self.checker.create_policy(
            name="P1"
        )
        self.checker.track_record(
            record_id="rec1",
            policy_id=p["policy_id"],
        )
        r = self.checker.apply_legal_hold(
            record_id="rec1",
            reason="Investigation",
            authority="Legal",
        )
        assert r["applied"]

    def test_legal_hold_prevents_expire(
        self,
    ):
        p = self.checker.create_policy(
            name="P1",
            retention_days=1,
        )
        old = (
            datetime.now(timezone.utc)
            - timedelta(days=30)
        ).isoformat()
        self.checker.track_record(
            record_id="rec1",
            policy_id=p["policy_id"],
            created_date=old,
        )
        self.checker.apply_legal_hold(
            record_id="rec1",
            reason="Hold",
        )
        r = self.checker.check_expiration(
            record_id="rec1"
        )
        assert not r["expired"]
        assert r["legal_hold"]

    def test_release_legal_hold(self):
        p = self.checker.create_policy(
            name="P1"
        )
        self.checker.track_record(
            record_id="rec1",
            policy_id=p["policy_id"],
        )
        h = self.checker.apply_legal_hold(
            record_id="rec1"
        )
        r = self.checker.release_legal_hold(
            hold_id=h["hold_id"]
        )
        assert r["released"]

    def test_release_nonexistent(self):
        r = self.checker.release_legal_hold(
            hold_id="nonexistent"
        )
        assert not r["released"]

    def test_auto_delete_expired(self):
        p = self.checker.create_policy(
            name="P1",
            retention_days=1,
            auto_delete=True,
        )
        old = (
            datetime.now(timezone.utc)
            - timedelta(days=30)
        ).isoformat()
        self.checker.track_record(
            record_id="rec1",
            policy_id=p["policy_id"],
            created_date=old,
        )
        r = self.checker.auto_delete_expired()
        assert r["completed"]
        assert r["deleted"] == 1

    def test_auto_delete_no_flag(self):
        p = self.checker.create_policy(
            name="P1",
            retention_days=1,
            auto_delete=False,
        )
        old = (
            datetime.now(timezone.utc)
            - timedelta(days=30)
        ).isoformat()
        self.checker.track_record(
            record_id="rec1",
            policy_id=p["policy_id"],
            created_date=old,
        )
        r = self.checker.auto_delete_expired()
        assert r["completed"]
        assert r["deleted"] == 0

    def test_apply_hold_invalid_record(
        self,
    ):
        r = self.checker.apply_legal_hold(
            record_id="nonexistent"
        )
        assert not r["applied"]

    def test_policy_count_property(self):
        assert (
            self.checker.policy_count == 0
        )
        self.checker.create_policy(
            name="P1"
        )
        assert (
            self.checker.policy_count == 1
        )

    def test_get_summary(self):
        s = self.checker.get_summary()
        assert s["retrieved"]


# ──────────────────────────────────
# ComplianceConsentManager
# ──────────────────────────────────
class TestComplianceConsentManager:
    """ComplianceConsentManager testleri."""

    def setup_method(self):
        self.mgr = (
            ComplianceConsentManager()
        )

    def test_define_purpose(self):
        r = self.mgr.define_purpose(
            name="Marketing",
            description="Email marketing",
        )
        assert r["defined"]
        assert r["purpose_id"].startswith(
            "pp_"
        )

    def test_collect_consent_granted(self):
        p = self.mgr.define_purpose(
            name="Analytics"
        )
        r = self.mgr.collect_consent(
            user_id="u1",
            purpose_id=p["purpose_id"],
            granted=True,
        )
        assert r["collected"]
        assert r["status"] == "granted"

    def test_collect_consent_denied(self):
        p = self.mgr.define_purpose(
            name="Ads"
        )
        r = self.mgr.collect_consent(
            user_id="u1",
            purpose_id=p["purpose_id"],
            granted=False,
        )
        assert r["collected"]
        assert r["status"] == "denied"

    def test_collect_invalid_purpose(self):
        r = self.mgr.collect_consent(
            user_id="u1",
            purpose_id="nonexistent",
        )
        assert not r["collected"]

    def test_withdraw_consent(self):
        p = self.mgr.define_purpose(
            name="P1"
        )
        self.mgr.collect_consent(
            user_id="u1",
            purpose_id=p["purpose_id"],
        )
        r = self.mgr.withdraw_consent(
            user_id="u1",
            purpose_id=p["purpose_id"],
            reason="Changed mind",
        )
        assert r["withdrawn"]

    def test_withdraw_nonexistent(self):
        r = self.mgr.withdraw_consent(
            user_id="u1",
            purpose_id="nonexistent",
        )
        assert not r["withdrawn"]

    def test_withdraw_denied_consent(self):
        p = self.mgr.define_purpose(
            name="P1"
        )
        self.mgr.collect_consent(
            user_id="u1",
            purpose_id=p["purpose_id"],
            granted=False,
        )
        r = self.mgr.withdraw_consent(
            user_id="u1",
            purpose_id=p["purpose_id"],
        )
        assert not r["withdrawn"]

    def test_get_user_consents(self):
        p = self.mgr.define_purpose(
            name="P1"
        )
        self.mgr.collect_consent(
            user_id="u1",
            purpose_id=p["purpose_id"],
        )
        r = self.mgr.get_user_consents(
            user_id="u1"
        )
        assert r["retrieved"]
        assert r["count"] == 1

    def test_check_consent_granted(self):
        p = self.mgr.define_purpose(
            name="P1"
        )
        self.mgr.collect_consent(
            user_id="u1",
            purpose_id=p["purpose_id"],
        )
        r = self.mgr.check_consent(
            user_id="u1",
            purpose_id=p["purpose_id"],
        )
        assert r["checked"]
        assert r["has_consent"]

    def test_check_consent_none(self):
        r = self.mgr.check_consent(
            user_id="u1",
            purpose_id="nonexistent",
        )
        assert r["checked"]
        assert not r["has_consent"]
        assert r["status"] == "none"

    def test_consent_count_property(self):
        assert self.mgr.consent_count == 0
        p = self.mgr.define_purpose(
            name="P1"
        )
        self.mgr.collect_consent(
            user_id="u1",
            purpose_id=p["purpose_id"],
        )
        assert self.mgr.consent_count == 1

    def test_consent_count_after_withdraw(
        self,
    ):
        p = self.mgr.define_purpose(
            name="P1"
        )
        self.mgr.collect_consent(
            user_id="u1",
            purpose_id=p["purpose_id"],
        )
        self.mgr.withdraw_consent(
            user_id="u1",
            purpose_id=p["purpose_id"],
        )
        assert self.mgr.consent_count == 0

    def test_get_summary(self):
        s = self.mgr.get_summary()
        assert s["retrieved"]
        assert "active_consents" in s


# ──────────────────────────────────
# ComplianceReportGenerator
# ──────────────────────────────────
class TestComplianceReportGenerator:
    """ComplianceReportGenerator testleri."""

    def setup_method(self):
        self.gen = (
            ComplianceReportGenerator()
        )

    def test_create_template(self):
        r = self.gen.create_template(
            name="GDPR Report",
            report_type="compliance_status",
        )
        assert r["created"]

    def test_create_template_invalid(self):
        r = self.gen.create_template(
            name="x",
            report_type="invalid",
        )
        assert not r["created"]

    def test_generate_report(self):
        r = self.gen.generate_report(
            title="Q1 Report",
            report_type="compliance_status",
            framework_key="gdpr",
        )
        assert r["generated"]
        assert r["sections"] > 0

    def test_generate_invalid_type(self):
        r = self.gen.generate_report(
            title="x",
            report_type="invalid",
        )
        assert not r["generated"]

    def test_generate_audit_ready(self):
        r = self.gen.generate_report(
            title="Audit",
            report_type="audit_ready",
            report_format="detailed",
        )
        assert r["generated"]

    def test_generate_executive(self):
        r = self.gen.generate_report(
            title="Exec",
            report_type=(
                "executive_summary"
            ),
            report_format="executive",
        )
        assert r["generated"]

    def test_generate_technical(self):
        r = self.gen.generate_report(
            title="Tech",
            report_type="gap_analysis",
            report_format="technical",
        )
        assert r["generated"]

    def test_collect_evidence(self):
        rp = self.gen.generate_report(
            title="Test"
        )
        r = self.gen.collect_evidence(
            report_id=rp["report_id"],
            evidence_type="screenshot",
            title="Config Screen",
        )
        assert r["collected"]

    def test_collect_evidence_invalid(self):
        r = self.gen.collect_evidence(
            report_id="nonexistent"
        )
        assert not r["collected"]

    def test_executive_summary(self):
        r = self.gen.generate_executive_summary(
            framework_key="gdpr",
            compliance_score=85.0,
            total_controls=100,
            passed_controls=85,
        )
        assert r["generated"]
        assert (
            r["status"]
            == "partially_compliant"
        )

    def test_executive_summary_compliant(
        self,
    ):
        r = self.gen.generate_executive_summary(
            compliance_score=95.0,
            total_controls=100,
            passed_controls=95,
        )
        assert r["status"] == "compliant"

    def test_executive_summary_non(self):
        r = self.gen.generate_executive_summary(
            compliance_score=50.0,
            total_controls=100,
            passed_controls=50,
            findings=[
                {"severity": "critical"},
                {"severity": "high"},
            ],
        )
        assert (
            r["status"] == "non_compliant"
        )
        s = r["summary"]
        assert s["critical_findings"] == 1
        assert s["high_findings"] == 1

    def test_export_report(self):
        rp = self.gen.generate_report(
            title="Test"
        )
        r = self.gen.export_report(
            report_id=rp["report_id"],
            export_format="pdf",
        )
        assert r["exported"]
        assert r["format"] == "pdf"

    def test_export_nonexistent(self):
        r = self.gen.export_report(
            report_id="nonexistent"
        )
        assert not r["exported"]

    def test_report_count_property(self):
        assert self.gen.report_count == 0
        self.gen.generate_report(
            title="x"
        )
        assert self.gen.report_count == 1

    def test_get_summary(self):
        s = self.gen.get_summary()
        assert s["retrieved"]
        assert "by_type" in s


# ──────────────────────────────────
# ComplianceGapAnalyzer
# ──────────────────────────────────
class TestComplianceGapAnalyzer:
    """ComplianceGapAnalyzer testleri."""

    def setup_method(self):
        self.analyzer = (
            ComplianceGapAnalyzer()
        )

    def test_identify_gap(self):
        r = self.analyzer.identify_gap(
            framework_key="gdpr",
            title="Encryption Missing",
            severity="high",
        )
        assert r["identified"]
        assert r["risk_score"] == 0.8

    def test_identify_invalid_severity(
        self,
    ):
        r = self.analyzer.identify_gap(
            severity="invalid"
        )
        assert not r["identified"]

    def test_severity_risk_scores(self):
        scores = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
            "info": 0.2,
        }
        for sev, expected in scores.items():
            r = self.analyzer.identify_gap(
                title=f"Gap {sev}",
                severity=sev,
            )
            assert r["risk_score"] == (
                expected
            )

    def test_run_assessment(self):
        controls = [
            {
                "id": "c1",
                "name": "Encryption",
                "status": "passed",
            },
            {
                "id": "c2",
                "name": "Access",
                "status": "failed",
                "severity": "high",
            },
            {
                "id": "c3",
                "name": "Logging",
                "status": "partial",
                "severity": "medium",
            },
        ]
        r = self.analyzer.run_assessment(
            framework_key="gdpr",
            controls=controls,
        )
        assert r["assessed"]
        assert r["passed"] == 1
        assert r["failed"] == 1
        assert r["gaps_found"] == 2

    def test_run_assessment_empty(self):
        r = self.analyzer.run_assessment(
            framework_key="gdpr",
            controls=[],
        )
        assert r["assessed"]
        assert r["score"] == 0.0

    def test_run_assessment_all_pass(self):
        controls = [
            {"id": "c1", "status": "passed"},
            {"id": "c2", "status": "passed"},
        ]
        r = self.analyzer.run_assessment(
            controls=controls
        )
        assert r["score"] == 100.0
        assert r["gaps_found"] == 0

    def test_create_roadmap(self):
        g1 = self.analyzer.identify_gap(
            title="G1", severity="critical"
        )
        g2 = self.analyzer.identify_gap(
            title="G2", severity="low"
        )
        r = self.analyzer.create_roadmap(
            name="Q1 Roadmap",
            gap_ids=[
                g1["gap_id"],
                g2["gap_id"],
            ],
        )
        assert r["created"]
        assert r["gaps_count"] == 2

    def test_update_gap_status(self):
        g = self.analyzer.identify_gap(
            title="G1", severity="high"
        )
        r = self.analyzer.update_gap_status(
            gap_id=g["gap_id"],
            status="in_progress",
        )
        assert r["updated"]

    def test_update_to_remediated(self):
        g = self.analyzer.identify_gap(
            title="G1"
        )
        self.analyzer.update_gap_status(
            gap_id=g["gap_id"],
            status="remediated",
        )
        s = self.analyzer.get_summary()
        assert (
            s["stats"]["gaps_remediated"]
            == 1
        )

    def test_update_nonexistent(self):
        r = self.analyzer.update_gap_status(
            gap_id="nonexistent"
        )
        assert not r["updated"]

    def test_update_invalid_status(self):
        g = self.analyzer.identify_gap(
            title="G1"
        )
        r = self.analyzer.update_gap_status(
            gap_id=g["gap_id"],
            status="invalid",
        )
        assert not r["updated"]

    def test_roadmap_progress(self):
        g1 = self.analyzer.identify_gap(
            title="G1"
        )
        g2 = self.analyzer.identify_gap(
            title="G2"
        )
        rm = self.analyzer.create_roadmap(
            name="RM",
            gap_ids=[
                g1["gap_id"],
                g2["gap_id"],
            ],
        )
        self.analyzer.update_gap_status(
            gap_id=g1["gap_id"],
            status="remediated",
        )
        roadmap = (
            self.analyzer._roadmaps[
                rm["roadmap_id"]
            ]
        )
        assert roadmap["progress"] == 50.0

    def test_get_gaps_by_severity(self):
        self.analyzer.identify_gap(
            title="G1", severity="critical"
        )
        self.analyzer.identify_gap(
            title="G2", severity="low"
        )
        r = self.analyzer.get_gaps_by_severity(
            severity="critical"
        )
        assert r["count"] == 1

    def test_get_all_gaps(self):
        self.analyzer.identify_gap(
            title="G1"
        )
        r = self.analyzer.get_gaps_by_severity()
        assert r["count"] > 0

    def test_get_risk_summary(self):
        self.analyzer.identify_gap(
            title="G1", severity="critical"
        )
        self.analyzer.identify_gap(
            title="G2", severity="low"
        )
        r = self.analyzer.get_risk_summary()
        assert r["retrieved"]
        assert r["open_gaps"] == 2
        assert r["average_risk"] > 0

    def test_gap_count_property(self):
        assert self.analyzer.gap_count == 0
        self.analyzer.identify_gap(
            title="G1"
        )
        assert self.analyzer.gap_count == 1

    def test_gap_count_excludes_closed(self):
        g = self.analyzer.identify_gap(
            title="G1"
        )
        self.analyzer.update_gap_status(
            gap_id=g["gap_id"],
            status="remediated",
        )
        assert self.analyzer.gap_count == 0

    def test_get_summary(self):
        s = self.analyzer.get_summary()
        assert s["retrieved"]
        assert "open_gaps" in s


# ──────────────────────────────────
# ComplianceOrchestrator
# ──────────────────────────────────
class TestComplianceOrchestrator:
    """ComplianceOrchestrator testleri."""

    def setup_method(self):
        self.orch = (
            ComplianceOrchestrator()
        )

    def test_init(self):
        assert (
            self.orch.framework_loader
            is not None
        )
        assert (
            self.orch.policy_enforcer
            is not None
        )

    def test_init_auto_remediate(self):
        o = ComplianceOrchestrator(
            auto_remediate=True
        )
        assert o._auto_remediate

    def test_load_framework(self):
        r = self.orch.load_framework(
            key="custom1",
            name="Custom",
            region="US",
        )
        assert r["loaded"]

    def test_builtin_frameworks(self):
        s = self.orch.get_summary()
        assert s["frameworks"] >= 4

    def test_enforce_policy_compliant(self):
        r = self.orch.enforce_policy(
            name="Enc Policy",
            policy_type="encryption",
            rules=[
                {
                    "field": "encrypted",
                    "operator": "equals",
                    "value": True,
                }
            ],
            context={"encrypted": True},
        )
        assert r["enforced"]
        assert r["compliant"]

    def test_enforce_policy_violation(self):
        r = self.orch.enforce_policy(
            name="Enc Policy",
            rules=[
                {
                    "field": "encrypted",
                    "operator": "equals",
                    "value": True,
                }
            ],
            context={"encrypted": False},
        )
        assert r["enforced"]
        assert not r["compliant"]

    def test_track_data_flow(self):
        r = self.orch.track_data_flow(
            asset_name="Customer Data",
            category="personal",
            country="TR",
            destination="Analytics",
            purpose="Reporting",
        )
        assert r["tracked"]

    def test_track_cross_border(self):
        r = self.orch.track_data_flow(
            asset_name="Health Data",
            category="health",
            country="TR",
            destination="EU Lab",
            purpose="Analysis",
            is_cross_border=True,
            destination_country="DE",
        )
        assert r["tracked"]
        assert r["is_cross_border"]

    def test_audit_access(self):
        r = self.orch.audit_access(
            user_id="u1",
            resource_id="r1",
            access_type="read",
        )
        assert r["logged"]

    def test_manage_consent(self):
        r = self.orch.manage_consent(
            user_id="u1",
            purpose_name="Marketing",
            granted=True,
        )
        assert r["managed"]
        assert r["status"] == "granted"

    def test_run_gap_analysis(self):
        controls = [
            {"id": "c1", "status": "passed"},
            {
                "id": "c2",
                "status": "failed",
                "severity": "high",
            },
        ]
        r = self.orch.run_gap_analysis(
            framework_key="gdpr",
            controls=controls,
        )
        assert r["assessed"]
        assert r["gaps_found"] == 1

    def test_generate_report(self):
        r = self.orch.generate_compliance_report(
            framework_key="gdpr",
            title="Q1 GDPR Report",
        )
        assert r["generated"]
        assert r["frameworks"] >= 4

    def test_get_analytics(self):
        r = self.orch.get_analytics()
        assert r["retrieved"]
        assert "violations" in r
        assert "open_gaps" in r

    def test_get_summary(self):
        s = self.orch.get_summary()
        assert s["retrieved"]
        assert "frameworks" in s
        assert "violations" in s
        assert "data_assets" in s
        assert "access_logs" in s
        assert "active_consents" in s
        assert "open_gaps" in s
        assert "reports" in s


# ──────────────────────────────────
# Models
# ──────────────────────────────────
class TestComplianceModels:
    """Compliance modelleri testleri."""

    def test_framework_enum(self):
        assert (
            ComplianceFramework.GDPR.value
            == "gdpr"
        )
        assert (
            ComplianceFramework.KVKK.value
            == "kvkk"
        )
        assert len(ComplianceFramework) == 7

    def test_policy_type_enum(self):
        assert (
            PolicyType.DATA_PROTECTION.value
            == "data_protection"
        )
        assert len(PolicyType) == 8

    def test_data_category_enum(self):
        assert (
            DataCategory.PERSONAL.value
            == "personal"
        )
        assert len(DataCategory) == 7

    def test_consent_status_enum(self):
        assert (
            ConsentStatus.GRANTED.value
            == "granted"
        )
        assert len(ConsentStatus) == 4

    def test_gap_severity_enum(self):
        assert (
            GapSeverity.CRITICAL.value
            == "critical"
        )
        assert len(GapSeverity) == 5

    def test_gap_status_enum(self):
        assert (
            GapStatus.IDENTIFIED.value
            == "identified"
        )
        assert len(GapStatus) == 5

    def test_report_type_enum(self):
        assert (
            ReportType.AUDIT_READY.value
            == "audit_ready"
        )
        assert len(ReportType) == 7

    def test_retention_type_enum(self):
        assert (
            RetentionType.FIXED.value
            == "fixed"
        )
        assert len(RetentionType) == 4

    def test_framework_info_model(self):
        m = FrameworkInfo(
            key="gdpr",
            name="GDPR",
            region="EU",
        )
        assert m.key == "gdpr"
        assert m.is_active

    def test_policy_record_model(self):
        m = PolicyRecord(
            policy_id="pl_1",
            name="Test",
        )
        assert m.policy_id == "pl_1"
        assert (
            m.policy_type
            == PolicyType.DATA_PROTECTION
        )

    def test_data_flow_model(self):
        m = DataFlowRecord(
            asset_id="da_1",
            name="Data",
        )
        assert m.asset_id == "da_1"
        assert not m.is_cross_border

    def test_consent_record_model(self):
        m = ConsentRecord(
            consent_id="cn_1",
            user_id="u1",
        )
        assert (
            m.status
            == ConsentStatus.GRANTED
        )

    def test_gap_record_model(self):
        m = GapRecord(
            gap_id="cg_1",
            title="Missing Encryption",
            risk_score=0.8,
        )
        assert m.risk_score == 0.8
        assert (
            m.severity
            == GapSeverity.MEDIUM
        )

    def test_compliance_report_model(self):
        m = ComplianceReport(
            report_id="cr_1",
            title="Q1",
        )
        assert m.status == "generated"

    def test_retention_policy_model(self):
        m = RetentionPolicy(
            policy_id="rp_1",
            retention_days=730,
        )
        assert m.retention_days == 730
        assert not m.auto_delete

    def test_compliance_status_model(self):
        m = ComplianceStatus(
            frameworks=4,
            violations=2,
            open_gaps=3,
        )
        assert m.frameworks == 4
        assert m.violations == 2


# ──────────────────────────────────
# Config
# ──────────────────────────────────
class TestComplianceConfig:
    """Compliance config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.compliance_enabled is True
        assert "gdpr" in (
            s.compliance_frameworks
        )
        assert (
            s.compliance_auto_remediate
            is False
        )
        assert (
            s.compliance_report_frequency
            == "monthly"
        )
        assert (
            s.compliance_consent_required
            is True
        )
