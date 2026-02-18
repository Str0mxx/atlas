"""
Zero Trust Access Controller testleri.

IdentityVerifier, MFAEnforcer,
DeviceFingerprinter, GeoAccessPolicy,
LeastPrivilegeEnforcer, ZTSessionManager,
ZTTokenValidator, PrivilegeEscalationDetector,
ZeroTrustOrchestrator ve modelleri test eder.
"""

import pytest

from app.core.zerotrust.identity_verifier import (
    IdentityVerifier,
)
from app.core.zerotrust.mfa_enforcer import (
    MFAEnforcer,
)
from app.core.zerotrust.device_fingerprinter import (
    DeviceFingerprinter,
)
from app.core.zerotrust.geo_access_policy import (
    GeoAccessPolicy,
)
from app.core.zerotrust.least_privilege_enforcer import (
    LeastPrivilegeEnforcer,
)
from app.core.zerotrust.zt_session_manager import (
    ZTSessionManager,
)
from app.core.zerotrust.zt_token_validator import (
    ZTTokenValidator,
)
from app.core.zerotrust.privilege_escalation_detector import (
    PrivilegeEscalationDetector,
)
from app.core.zerotrust.zerotrust_orchestrator import (
    ZeroTrustOrchestrator,
)
from app.models.zerotrust_models import (
    VerificationMethod,
    RiskLevel,
    SessionState,
    TokenType,
    EscalationType,
    AlertSeverity,
    TrustLevel,
    IdentityRecord,
    SessionRecord,
    TokenRecord,
    DeviceRecord,
    EscalationAlert,
    AccessCheckResult,
    ZeroTrustStatus,
)


# ============================================================
# IdentityVerifier Testleri
# ============================================================
class TestIdentityVerifier:
    """IdentityVerifier testleri."""

    def setup_method(self):
        self.iv = IdentityVerifier()

    def test_init(self):
        assert self.iv.identity_count == 0
        s = self.iv.get_summary()
        assert s["retrieved"] is True
        assert s["total_identities"] == 0

    def test_register_identity(self):
        r = self.iv.register_identity(
            user_id="u1",
            methods=["password", "totp"],
            risk_level="low",
        )
        assert r["registered"] is True
        assert r["user_id"] == "u1"
        assert "password" in r["methods"]
        assert self.iv.identity_count == 1

    def test_register_invalid_method(self):
        r = self.iv.register_identity(
            user_id="u1",
            methods=["invalid_method"],
        )
        assert r["registered"] is False
        assert "Gecersiz" in r["error"]

    def test_verify_identity(self):
        self.iv.register_identity(
            user_id="u1",
            methods=["password"],
        )
        r = self.iv.verify_identity(
            user_id="u1",
            method="password",
            credential="pass123",
        )
        assert r["verified"] is True
        assert r["risk_level"] == "low"

    def test_verify_unknown_user(self):
        r = self.iv.verify_identity(
            user_id="unknown",
        )
        assert r["verified"] is False

    def test_verify_unsupported_method(self):
        self.iv.register_identity(
            user_id="u1",
            methods=["password"],
        )
        r = self.iv.verify_identity(
            user_id="u1",
            method="biometric",
        )
        assert r["verified"] is False

    def test_risk_assessment_new_device(self):
        self.iv.register_identity(
            user_id="u1",
            methods=["password"],
        )
        r = self.iv.verify_identity(
            user_id="u1",
            method="password",
            credential="pass",
            context={"new_device": True},
        )
        assert r["risk_level"] in (
            "medium", "high", "critical"
        )

    def test_risk_assessment_critical(self):
        self.iv.register_identity(
            user_id="u1",
            methods=["password"],
        )
        r = self.iv.verify_identity(
            user_id="u1",
            method="password",
            credential="pass",
            context={
                "new_device": True,
                "new_location": True,
                "failed_attempts": 5,
            },
        )
        assert r["risk_level"] == "critical"
        assert r["requires_mfa"] is True

    def test_continuous_verify(self):
        self.iv.register_identity(
            user_id="u1",
        )
        r = self.iv.continuous_verify(
            user_id="u1",
            session_id="s1",
        )
        assert r["valid"] is True
        assert r["anomaly_score"] == 0.0

    def test_continuous_verify_anomaly(self):
        self.iv.register_identity(
            user_id="u1",
        )
        r = self.iv.continuous_verify(
            user_id="u1",
            session_id="s1",
            behavior={
                "typing_speed_change": True,
                "unusual_action": True,
            },
        )
        assert r["anomaly_score"] == 0.7
        assert r["requires_reauth"] is True

    def test_continuous_verify_unknown(self):
        r = self.iv.continuous_verify(
            user_id="unknown",
        )
        assert r["valid"] is False

    def test_bind_session(self):
        self.iv.register_identity(
            user_id="u1",
        )
        r = self.iv.bind_session(
            user_id="u1",
            session_id="s1",
            device_fingerprint="fp1",
            ip_address="1.2.3.4",
        )
        assert r["bound"] is True
        assert "binding_hash" in r

    def test_bind_session_unknown(self):
        r = self.iv.bind_session(
            user_id="unknown",
        )
        assert r["bound"] is False

    def test_validate_binding(self):
        self.iv.register_identity(
            user_id="u1",
        )
        self.iv.bind_session(
            user_id="u1",
            session_id="s1",
            device_fingerprint="fp1",
            ip_address="1.2.3.4",
        )
        r = self.iv.validate_binding(
            session_id="s1",
            device_fingerprint="fp1",
            ip_address="1.2.3.4",
        )
        assert r["valid"] is True

    def test_validate_binding_changed(self):
        self.iv.register_identity(
            user_id="u1",
        )
        self.iv.bind_session(
            user_id="u1",
            session_id="s1",
            device_fingerprint="fp1",
            ip_address="1.2.3.4",
        )
        r = self.iv.validate_binding(
            session_id="s1",
            device_fingerprint="fp2",
            ip_address="5.6.7.8",
        )
        assert r["valid"] is False
        assert "device_changed" in r["issues"]
        assert "ip_changed" in r["issues"]

    def test_validate_binding_unknown(self):
        r = self.iv.validate_binding(
            session_id="unknown",
        )
        assert r["valid"] is False

    def test_summary_stats(self):
        self.iv.register_identity(
            user_id="u1",
            methods=["password"],
        )
        self.iv.verify_identity(
            user_id="u1",
            method="password",
            credential="pass",
        )
        s = self.iv.get_summary()
        assert s["total_identities"] == 1
        assert s["total_verifications"] == 1
        assert s["stats"]["successful"] == 1


# ============================================================
# MFAEnforcer Testleri
# ============================================================
class TestMFAEnforcer:
    """MFAEnforcer testleri."""

    def setup_method(self):
        self.mfa = MFAEnforcer()

    def test_init(self):
        assert self.mfa.policy_count == 0

    def test_create_policy(self):
        r = self.mfa.create_policy(
            name="standard",
            required_methods=2,
        )
        assert r["created"] is True
        assert r["required_methods"] == 2
        assert self.mfa.policy_count == 1

    def test_enroll_method(self):
        r = self.mfa.enroll_method(
            user_id="u1",
            method="totp",
            device_id="d1",
        )
        assert r["enrolled"] is True
        assert r["method"] == "totp"

    def test_enroll_invalid_method(self):
        r = self.mfa.enroll_method(
            user_id="u1",
            method="carrier_pigeon",
        )
        assert r["enrolled"] is False

    def test_verify_mfa_success(self):
        self.mfa.enroll_method(
            user_id="u1", method="totp",
        )
        r = self.mfa.verify_mfa(
            user_id="u1",
            method="totp",
            code="123456",
        )
        assert r["verified"] is True

    def test_verify_mfa_short_code(self):
        self.mfa.enroll_method(
            user_id="u1", method="totp",
        )
        r = self.mfa.verify_mfa(
            user_id="u1",
            method="totp",
            code="123",
        )
        assert r["verified"] is False

    def test_verify_mfa_not_enrolled(self):
        r = self.mfa.verify_mfa(
            user_id="u1",
            method="totp",
            code="123456",
        )
        assert r["verified"] is False

    def test_generate_recovery_codes(self):
        r = self.mfa.generate_recovery_codes(
            user_id="u1", count=5,
        )
        assert r["generated"] is True
        assert r["count"] == 5
        assert len(r["codes"]) == 5
        assert "-" in r["codes"][0]

    def test_use_recovery_code(self):
        r = self.mfa.generate_recovery_codes(
            user_id="u1", count=3,
        )
        code = r["codes"][0]
        u = self.mfa.use_recovery_code(
            user_id="u1", code=code,
        )
        assert u["accepted"] is True
        assert u["remaining"] == 2

    def test_use_recovery_code_invalid(self):
        self.mfa.generate_recovery_codes(
            user_id="u1",
        )
        r = self.mfa.use_recovery_code(
            user_id="u1", code="invalid",
        )
        assert r["accepted"] is False

    def test_use_recovery_code_twice(self):
        r = self.mfa.generate_recovery_codes(
            user_id="u1", count=3,
        )
        code = r["codes"][0]
        self.mfa.use_recovery_code(
            user_id="u1", code=code,
        )
        u = self.mfa.use_recovery_code(
            user_id="u1", code=code,
        )
        assert u["accepted"] is False

    def test_trust_device(self):
        r = self.mfa.trust_device(
            user_id="u1",
            device_id="d1",
            device_name="Phone",
        )
        assert r["trusted"] is True

    def test_is_device_trusted(self):
        self.mfa.trust_device(
            user_id="u1",
            device_id="d1",
        )
        r = self.mfa.is_device_trusted(
            user_id="u1",
            device_id="d1",
        )
        assert r["trusted"] is True

    def test_is_device_not_trusted(self):
        r = self.mfa.is_device_trusted(
            user_id="u1",
            device_id="unknown",
        )
        assert r["trusted"] is False

    def test_check_compliance_pass(self):
        self.mfa.create_policy(
            name="p1", required_methods=1,
        )
        self.mfa.enroll_method(
            user_id="u1", method="totp",
        )
        r = self.mfa.check_compliance(
            user_id="u1",
            policy_name="p1",
        )
        assert r["compliant"] is True

    def test_check_compliance_fail(self):
        self.mfa.create_policy(
            name="p1", required_methods=3,
        )
        self.mfa.enroll_method(
            user_id="u1", method="totp",
        )
        r = self.mfa.check_compliance(
            user_id="u1",
            policy_name="p1",
        )
        assert r["compliant"] is False

    def test_check_compliance_no_policy(self):
        r = self.mfa.check_compliance(
            user_id="u1",
            policy_name="missing",
        )
        assert r["compliant"] is False

    def test_summary(self):
        self.mfa.create_policy(name="p1")
        self.mfa.enroll_method(
            user_id="u1", method="totp",
        )
        s = self.mfa.get_summary()
        assert s["retrieved"] is True
        assert s["total_policies"] == 1
        assert s["total_users"] == 1


# ============================================================
# DeviceFingerprinter Testleri
# ============================================================
class TestDeviceFingerprinter:
    """DeviceFingerprinter testleri."""

    def setup_method(self):
        self.df = DeviceFingerprinter()

    def test_init(self):
        assert self.df.device_count == 0

    def test_register_device(self):
        r = self.df.register_device(
            device_id="d1",
            user_id="u1",
            components={
                "user_agent": "Chrome",
                "platform": "Win",
            },
        )
        assert r["registered"] is True
        assert len(r["fingerprint"]) == 32
        assert r["trust_score"] == 0.5
        assert self.df.device_count == 1

    def test_generate_fingerprint(self):
        r = self.df.generate_fingerprint(
            components={"a": "1", "b": "2"},
        )
        assert r["generated"] is True
        assert r["components_used"] == 2

    def test_fingerprint_deterministic(self):
        c = {"x": "1", "y": "2"}
        r1 = self.df.generate_fingerprint(
            components=c,
        )
        r2 = self.df.generate_fingerprint(
            components=c,
        )
        assert r1["fingerprint"] == r2["fingerprint"]

    def test_check_device_known(self):
        comps = {"ua": "Chrome"}
        self.df.register_device(
            device_id="d1",
            user_id="u1",
            components=comps,
        )
        r = self.df.check_device(
            device_id="d1",
            components=comps,
        )
        assert r["known"] is True
        assert r["fingerprint_match"] is True

    def test_check_device_changed(self):
        self.df.register_device(
            device_id="d1",
            user_id="u1",
            components={"ua": "Chrome"},
        )
        r = self.df.check_device(
            device_id="d1",
            components={"ua": "Firefox"},
        )
        assert r["known"] is True
        assert r["fingerprint_match"] is False
        assert "ua" in r["changes"]

    def test_check_device_unknown(self):
        r = self.df.check_device(
            device_id="unknown",
        )
        assert r["known"] is False

    def test_calculate_trust(self):
        self.df.register_device(
            device_id="d1",
            user_id="u1",
        )
        r = self.df.calculate_trust(
            device_id="d1",
        )
        assert r["calculated"] is True
        assert r["trust_score"] >= 0.0
        assert r["trust_level"] in (
            "low", "medium", "high",
        )

    def test_calculate_trust_high(self):
        self.df.register_device(
            device_id="d1",
            user_id="u1",
        )
        d = self.df._devices["d1"]
        d["seen_count"] = 15
        r = self.df.calculate_trust(
            device_id="d1",
        )
        assert r["trust_score"] == 0.8
        assert r["trust_level"] == "high"

    def test_calculate_trust_unknown(self):
        r = self.df.calculate_trust(
            device_id="unknown",
        )
        assert r["calculated"] is False

    def test_revoke_device(self):
        self.df.register_device(
            device_id="d1",
            user_id="u1",
        )
        r = self.df.revoke_device(
            device_id="d1",
        )
        assert r["revoked"] is True
        assert self.df._devices["d1"]["trust_score"] == 0.0

    def test_revoke_unknown(self):
        r = self.df.revoke_device(
            device_id="unknown",
        )
        assert r["revoked"] is False

    def test_summary(self):
        self.df.register_device(
            device_id="d1",
            user_id="u1",
        )
        s = self.df.get_summary()
        assert s["retrieved"] is True
        assert s["total_devices"] == 1


# ============================================================
# GeoAccessPolicy Testleri
# ============================================================
class TestGeoAccessPolicy:
    """GeoAccessPolicy testleri."""

    def setup_method(self):
        self.geo = GeoAccessPolicy()

    def test_init(self):
        assert self.geo.policy_count == 0

    def test_create_policy(self):
        r = self.geo.create_policy(
            name="eu_only",
            allowed_countries=["DE", "FR"],
        )
        assert r["created"] is True
        assert self.geo.policy_count == 1

    def test_check_access_allowed(self):
        self.geo.create_policy(
            name="open",
            allowed_countries=[],
        )
        r = self.geo.check_access(
            user_id="u1",
            country="TR",
            ip_address="8.8.8.8",
            policy_name="open",
        )
        assert r["allowed"] is True

    def test_check_access_country_blocked(self):
        self.geo.create_policy(
            name="strict",
            blocked_countries=["CN"],
        )
        r = self.geo.check_access(
            user_id="u1",
            country="CN",
            ip_address="8.8.8.8",
            policy_name="strict",
        )
        assert r["allowed"] is False
        assert "country_blocked" in r["issues"]

    def test_check_access_country_not_allowed(self):
        self.geo.create_policy(
            name="eu",
            allowed_countries=["DE", "FR"],
        )
        r = self.geo.check_access(
            user_id="u1",
            country="US",
            ip_address="8.8.8.8",
            policy_name="eu",
        )
        assert r["allowed"] is False
        assert "country_not_allowed" in r["issues"]

    def test_check_access_vpn_detected(self):
        self.geo.create_policy(
            name="no_vpn",
            allow_vpn=False,
        )
        r = self.geo.check_access(
            user_id="u1",
            country="TR",
            ip_address="10.0.0.5",
            policy_name="no_vpn",
        )
        assert r["vpn_detected"] is True
        assert "vpn_detected" in r["issues"]

    def test_check_access_vpn_allowed(self):
        self.geo.create_policy(
            name="vpn_ok",
            allow_vpn=True,
        )
        r = self.geo.check_access(
            user_id="u1",
            country="TR",
            ip_address="10.0.0.5",
            policy_name="vpn_ok",
        )
        assert "vpn_detected" not in r.get("issues", [])

    def test_check_access_no_policy(self):
        r = self.geo.check_access(
            user_id="u1",
            policy_name="missing",
        )
        assert r["allowed"] is False

    def test_impossible_travel(self):
        self.geo.create_policy(
            name="travel",
            max_travel_speed_kmh=900,
        )
        self.geo.check_access(
            user_id="u1",
            country="TR",
            ip_address="1.1.1.1",
            latitude=41.0,
            longitude=29.0,
            policy_name="travel",
        )
        r = self.geo.check_access(
            user_id="u1",
            country="US",
            ip_address="2.2.2.2",
            latitude=-33.0,
            longitude=151.0,
            policy_name="travel",
        )
        assert "impossible_travel" in r["issues"]

    def test_get_user_locations(self):
        self.geo.create_policy(name="p1")
        self.geo.check_access(
            user_id="u1",
            country="TR",
            ip_address="1.1.1.1",
            latitude=41.0,
            longitude=29.0,
            policy_name="p1",
        )
        r = self.geo.get_user_locations(
            user_id="u1",
        )
        assert r["retrieved"] is True
        assert r["count"] == 1

    def test_summary(self):
        self.geo.create_policy(name="p1")
        s = self.geo.get_summary()
        assert s["retrieved"] is True
        assert s["total_policies"] == 1


# ============================================================
# LeastPrivilegeEnforcer Testleri
# ============================================================
class TestLeastPrivilegeEnforcer:
    """LeastPrivilegeEnforcer testleri."""

    def setup_method(self):
        self.lp = LeastPrivilegeEnforcer()

    def test_init(self):
        assert self.lp.role_count == 0

    def test_define_role(self):
        r = self.lp.define_role(
            name="viewer",
            permissions=["read"],
            description="Salt okunur",
        )
        assert r["defined"] is True
        assert r["permissions_count"] == 1
        assert self.lp.role_count == 1

    def test_assign_permissions(self):
        self.lp.define_role(
            name="editor",
            permissions=["read", "write"],
        )
        r = self.lp.assign_permissions(
            user_id="u1",
            role="editor",
        )
        assert r["assigned"] is True
        assert r["total_permissions"] == 2

    def test_assign_permissions_extra(self):
        self.lp.define_role(
            name="viewer",
            permissions=["read"],
        )
        r = self.lp.assign_permissions(
            user_id="u1",
            role="viewer",
            extra_permissions=["comment"],
        )
        assert r["total_permissions"] == 2

    def test_assign_permissions_no_role(self):
        r = self.lp.assign_permissions(
            user_id="u1",
            role="nonexistent",
        )
        assert r["assigned"] is False

    def test_check_permission_has(self):
        self.lp.define_role(
            name="r1",
            permissions=["read", "write"],
        )
        self.lp.assign_permissions(
            user_id="u1", role="r1",
        )
        r = self.lp.check_permission(
            user_id="u1",
            permission="read",
        )
        assert r["has_permission"] is True

    def test_check_permission_no(self):
        self.lp.define_role(
            name="r1",
            permissions=["read"],
        )
        self.lp.assign_permissions(
            user_id="u1", role="r1",
        )
        r = self.lp.check_permission(
            user_id="u1",
            permission="delete",
        )
        assert r["has_permission"] is False

    def test_check_permission_unknown_user(self):
        r = self.lp.check_permission(
            user_id="unknown",
            permission="read",
        )
        assert r["has_permission"] is False

    def test_analyze_usage(self):
        self.lp.define_role(
            name="r1",
            permissions=["read", "write", "delete"],
        )
        self.lp.assign_permissions(
            user_id="u1", role="r1",
        )
        self.lp.check_permission(
            user_id="u1", permission="read",
        )
        r = self.lp.analyze_usage(
            user_id="u1",
        )
        assert r["analyzed"] is True
        assert r["total_permissions"] == 3
        assert r["used_permissions"] == 1
        assert len(r["unused_permissions"]) == 2

    def test_analyze_usage_unknown(self):
        r = self.lp.analyze_usage(
            user_id="unknown",
        )
        assert r["analyzed"] is False

    def test_prune_permissions(self):
        self.lp.define_role(
            name="r1",
            permissions=["read", "write", "delete"],
        )
        self.lp.assign_permissions(
            user_id="u1", role="r1",
        )
        self.lp.check_permission(
            user_id="u1", permission="read",
        )
        r = self.lp.prune_permissions(
            user_id="u1",
        )
        assert r["pruned"] is True
        assert r["permissions_pruned"] == 2
        assert r["remaining"] == 1

    def test_prune_permissions_non_unused(self):
        self.lp.define_role(
            name="r1",
            permissions=["read"],
        )
        self.lp.assign_permissions(
            user_id="u1",
            role="r1",
            extra_permissions=["write"],
        )
        r = self.lp.prune_permissions(
            user_id="u1",
            unused_only=False,
        )
        assert r["pruned"] is True

    def test_prune_unknown(self):
        r = self.lp.prune_permissions(
            user_id="unknown",
        )
        assert r["pruned"] is False

    def test_run_access_review(self):
        self.lp.define_role(
            name="r1",
            permissions=["read", "write"],
        )
        self.lp.assign_permissions(
            user_id="u1", role="r1",
        )
        r = self.lp.run_access_review()
        assert r["reviewed"] is True
        assert r["users_reviewed"] == 1
        assert r["findings"] >= 0

    def test_summary(self):
        self.lp.define_role(name="r1")
        s = self.lp.get_summary()
        assert s["retrieved"] is True
        assert s["total_roles"] == 1


# ============================================================
# ZTSessionManager Testleri
# ============================================================
class TestZTSessionManager:
    """ZTSessionManager testleri."""

    def setup_method(self):
        self.sm = ZTSessionManager()

    def test_init(self):
        assert self.sm.session_count == 0

    def test_create_session(self):
        r = self.sm.create_session(
            user_id="u1",
            device_id="d1",
            ip_address="1.2.3.4",
        )
        assert r["created"] is True
        assert len(r["token"]) == 32
        assert r["timeout_min"] == 30
        assert self.sm.session_count == 1

    def test_create_session_high_risk(self):
        r = self.sm.create_session(
            user_id="u1",
            risk_level="high",
            timeout_min=60,
        )
        assert r["created"] is True
        assert r["timeout_min"] <= 15

    def test_create_session_max_limit(self):
        sm = ZTSessionManager(
            max_sessions_per_user=2,
        )
        sm.create_session(user_id="u1")
        sm.create_session(user_id="u1")
        r = sm.create_session(user_id="u1")
        assert r["created"] is False

    def test_validate_session(self):
        c = self.sm.create_session(
            user_id="u1",
            ip_address="1.2.3.4",
        )
        r = self.sm.validate_session(
            session_id=c["session_id"],
            token=c["token"],
            ip_address="1.2.3.4",
        )
        assert r["valid"] is True

    def test_validate_session_bad_token(self):
        c = self.sm.create_session(
            user_id="u1",
        )
        r = self.sm.validate_session(
            session_id=c["session_id"],
            token="bad_token",
        )
        assert r["valid"] is False
        assert "token_mismatch" in r["issues"]

    def test_validate_session_ip_change(self):
        c = self.sm.create_session(
            user_id="u1",
            ip_address="1.2.3.4",
        )
        r = self.sm.validate_session(
            session_id=c["session_id"],
            ip_address="5.6.7.8",
        )
        assert "ip_changed" in r["issues"]

    def test_validate_unknown_session(self):
        r = self.sm.validate_session(
            session_id="unknown",
        )
        assert r["valid"] is False

    def test_refresh_session(self):
        c = self.sm.create_session(
            user_id="u1",
        )
        old_token = c["token"]
        r = self.sm.refresh_session(
            session_id=c["session_id"],
        )
        assert r["refreshed"] is True
        assert r["new_token"] != old_token

    def test_refresh_unknown(self):
        r = self.sm.refresh_session(
            session_id="unknown",
        )
        assert r["refreshed"] is False

    def test_terminate_session(self):
        c = self.sm.create_session(
            user_id="u1",
        )
        r = self.sm.terminate_session(
            session_id=c["session_id"],
            reason="logout",
        )
        assert r["terminated"] is True
        assert self.sm.session_count == 0

    def test_terminate_forced(self):
        c = self.sm.create_session(
            user_id="u1",
        )
        r = self.sm.terminate_session(
            session_id=c["session_id"],
            forced=True,
        )
        assert r["terminated"] is True
        assert r["forced"] is True

    def test_terminate_unknown(self):
        r = self.sm.terminate_session(
            session_id="unknown",
        )
        assert r["terminated"] is False

    def test_terminate_user_sessions(self):
        self.sm.create_session(user_id="u1")
        self.sm.create_session(user_id="u1")
        self.sm.create_session(user_id="u2")
        r = self.sm.terminate_user_sessions(
            user_id="u1",
        )
        assert r["terminated"] is True
        assert r["terminated_count"] == 2
        assert self.sm.session_count == 1

    def test_check_timeout_not_expired(self):
        c = self.sm.create_session(
            user_id="u1",
        )
        r = self.sm.check_timeout(
            session_id=c["session_id"],
        )
        assert r["checked"] is True
        assert r["expired"] is False

    def test_check_timeout_unknown(self):
        r = self.sm.check_timeout(
            session_id="unknown",
        )
        assert r["checked"] is False

    def test_get_user_sessions(self):
        self.sm.create_session(user_id="u1")
        self.sm.create_session(user_id="u1")
        r = self.sm.get_user_sessions(
            user_id="u1",
        )
        assert r["retrieved"] is True
        assert r["count"] == 2

    def test_get_analytics(self):
        self.sm.create_session(user_id="u1")
        r = self.sm.get_analytics()
        assert r["retrieved"] is True
        assert r["active"] == 1
        assert r["unique_users"] == 1

    def test_summary(self):
        self.sm.create_session(user_id="u1")
        s = self.sm.get_summary()
        assert s["retrieved"] is True
        assert s["total_sessions"] == 1
        assert s["active_sessions"] == 1


# ============================================================
# ZTTokenValidator Testleri
# ============================================================
class TestZTTokenValidator:
    """ZTTokenValidator testleri."""

    def setup_method(self):
        self.tv = ZTTokenValidator()

    def test_init(self):
        assert self.tv.token_count == 0

    def test_issue_token(self):
        r = self.tv.issue_token(
            user_id="u1",
            token_type="access",
            claims={"role": "admin"},
        )
        assert r["issued"] is True
        assert len(r["token_value"]) == 64
        assert len(r["signature"]) == 16
        assert self.tv.token_count == 1

    def test_issue_invalid_type(self):
        r = self.tv.issue_token(
            user_id="u1",
            token_type="invalid",
        )
        assert r["issued"] is False

    def test_validate_token(self):
        t = self.tv.issue_token(
            user_id="u1",
        )
        r = self.tv.validate_token(
            token_id=t["token_id"],
            token_value=t["token_value"],
        )
        assert r["valid"] is True

    def test_validate_token_bad_value(self):
        t = self.tv.issue_token(
            user_id="u1",
        )
        r = self.tv.validate_token(
            token_id=t["token_id"],
            token_value="wrong",
        )
        assert r["valid"] is False
        assert "value_mismatch" in r["issues"]

    def test_validate_unknown_token(self):
        r = self.tv.validate_token(
            token_id="unknown",
        )
        assert r["valid"] is False

    def test_validate_with_claims(self):
        t = self.tv.issue_token(
            user_id="u1",
            claims={"role": "admin"},
        )
        r = self.tv.validate_token(
            token_id=t["token_id"],
            required_claims={"role": "admin"},
        )
        assert r["valid"] is True

    def test_validate_wrong_claims(self):
        t = self.tv.issue_token(
            user_id="u1",
            claims={"role": "user"},
        )
        r = self.tv.validate_token(
            token_id=t["token_id"],
            required_claims={"role": "admin"},
        )
        assert r["valid"] is False

    def test_validate_with_scope(self):
        t = self.tv.issue_token(
            user_id="u1",
            scope="read:all",
        )
        r = self.tv.validate_token(
            token_id=t["token_id"],
            required_scope="read:all",
        )
        assert r["valid"] is True

    def test_validate_wrong_scope(self):
        t = self.tv.issue_token(
            user_id="u1",
            scope="read",
        )
        r = self.tv.validate_token(
            token_id=t["token_id"],
            required_scope="write",
        )
        assert r["valid"] is False

    def test_revoke_token(self):
        t = self.tv.issue_token(
            user_id="u1",
        )
        r = self.tv.revoke_token(
            token_id=t["token_id"],
            reason="security",
        )
        assert r["revoked"] is True
        assert self.tv.token_count == 0

    def test_revoke_unknown(self):
        r = self.tv.revoke_token(
            token_id="unknown",
        )
        assert r["revoked"] is False

    def test_revoke_user_tokens(self):
        self.tv.issue_token(user_id="u1")
        self.tv.issue_token(user_id="u1")
        self.tv.issue_token(user_id="u2")
        r = self.tv.revoke_user_tokens(
            user_id="u1",
        )
        assert r["revoked"] is True
        assert r["revoked_count"] == 2
        assert self.tv.token_count == 1

    def test_validate_revoked_token(self):
        t = self.tv.issue_token(
            user_id="u1",
        )
        self.tv.revoke_token(
            token_id=t["token_id"],
        )
        r = self.tv.validate_token(
            token_id=t["token_id"],
        )
        assert r["valid"] is False
        assert "revoked" in r["issues"]

    def test_is_revoked(self):
        t = self.tv.issue_token(
            user_id="u1",
        )
        self.tv.revoke_token(
            token_id=t["token_id"],
        )
        r = self.tv.is_revoked(
            token_id=t["token_id"],
        )
        assert r["revoked"] is True

    def test_is_not_revoked(self):
        t = self.tv.issue_token(
            user_id="u1",
        )
        r = self.tv.is_revoked(
            token_id=t["token_id"],
        )
        assert r["revoked"] is False

    def test_rotate_signing_key(self):
        r = self.tv.rotate_signing_key()
        assert r["rotated"] is True
        assert r["total_keys"] == 2

    def test_summary(self):
        self.tv.issue_token(user_id="u1")
        s = self.tv.get_summary()
        assert s["retrieved"] is True
        assert s["total_tokens"] == 1
        assert s["active_tokens"] == 1
        assert s["revoked_tokens"] == 0


# ============================================================
# PrivilegeEscalationDetector Testleri
# ============================================================
class TestPrivilegeEscalationDetector:
    """PrivilegeEscalationDetector testleri."""

    def setup_method(self):
        self.ped = PrivilegeEscalationDetector()

    def test_init(self):
        assert self.ped.alert_count == 0
        assert len(self.ped._rules) == 4

    def test_add_rule(self):
        r = self.ped.add_rule(
            name="custom",
            description="Test",
            severity="warning",
        )
        assert r["added"] is True
        assert len(self.ped._rules) == 5

    def test_add_rule_invalid_severity(self):
        r = self.ped.add_rule(
            name="bad",
            severity="extreme",
        )
        assert r["added"] is False

    def test_check_no_escalation(self):
        r = self.ped.check_escalation(
            user_id="u1",
            action="read_file",
        )
        assert r["checked"] is True
        assert r["escalation_detected"] is False

    def test_check_admin_escalation(self):
        r = self.ped.check_escalation(
            user_id="u1",
            action="admin_access",
            context={"admin_attempt": True},
        )
        assert r["escalation_detected"] is True
        assert r["risk_score"] > 0

    def test_check_rapid_change(self):
        r = self.ped.check_escalation(
            user_id="u1",
            action="change_perm",
            context={"rapid_change": True},
        )
        assert r["escalation_detected"] is True

    def test_check_cross_role(self):
        r = self.ped.check_escalation(
            user_id="u1",
            action="access",
            context={"cross_role": True},
        )
        assert r["escalation_detected"] is True

    def test_check_auto_block(self):
        r = self.ped.check_escalation(
            user_id="u1",
            action="admin_access",
            context={
                "admin_attempt": True,
                "rapid_change": True,
            },
        )
        assert r["blocked"] is True

    def test_check_no_auto_block(self):
        ped = PrivilegeEscalationDetector(
            auto_block=False,
        )
        r = ped.check_escalation(
            user_id="u1",
            action="admin_access",
            context={
                "admin_attempt": True,
                "rapid_change": True,
            },
        )
        assert r["blocked"] is False

    def test_acknowledge_alert(self):
        self.ped.check_escalation(
            user_id="u1",
            action="admin_access",
            context={"admin_attempt": True},
        )
        aid = self.ped._alerts[0]["alert_id"]
        r = self.ped.acknowledge_alert(
            alert_id=aid,
            analyst="admin",
            notes="Checked",
        )
        assert r["acknowledged"] is True

    def test_acknowledge_unknown(self):
        r = self.ped.acknowledge_alert(
            alert_id="unknown",
        )
        assert r["acknowledged"] is False

    def test_open_investigation(self):
        self.ped.check_escalation(
            user_id="u1",
            action="admin_access",
            context={"admin_attempt": True},
        )
        aid = self.ped._alerts[0]["alert_id"]
        r = self.ped.open_investigation(
            alert_id=aid,
            user_id="u1",
            description="Investigating",
        )
        assert r["opened"] is True
        assert r["patterns_found"] >= 1

    def test_add_finding(self):
        self.ped.check_escalation(
            user_id="u1",
            action="admin_access",
            context={"admin_attempt": True},
        )
        aid = self.ped._alerts[0]["alert_id"]
        inv = self.ped.open_investigation(
            alert_id=aid, user_id="u1",
        )
        r = self.ped.add_finding(
            investigation_id=inv["investigation_id"],
            finding="Suspicious",
            severity="critical",
        )
        assert r["added"] is True

    def test_add_finding_unknown(self):
        r = self.ped.add_finding(
            investigation_id="unknown",
        )
        assert r["added"] is False

    def test_close_investigation(self):
        self.ped.check_escalation(
            user_id="u1",
            action="admin_access",
            context={"admin_attempt": True},
        )
        aid = self.ped._alerts[0]["alert_id"]
        inv = self.ped.open_investigation(
            alert_id=aid, user_id="u1",
        )
        r = self.ped.close_investigation(
            investigation_id=inv["investigation_id"],
            resolution="False alarm",
        )
        assert r["closed"] is True

    def test_close_unknown(self):
        r = self.ped.close_investigation(
            investigation_id="unknown",
        )
        assert r["closed"] is False

    def test_summary(self):
        self.ped.check_escalation(
            user_id="u1",
            action="admin_access",
            context={"admin_attempt": True},
        )
        s = self.ped.get_summary()
        assert s["retrieved"] is True
        assert s["total_alerts"] >= 1
        assert s["total_rules"] >= 4


# ============================================================
# ZeroTrustOrchestrator Testleri
# ============================================================
class TestZeroTrustOrchestrator:
    """ZeroTrustOrchestrator testleri."""

    def setup_method(self):
        self.zt = ZeroTrustOrchestrator()

    def test_init(self):
        s = self.zt.get_summary()
        assert s["retrieved"] is True
        assert s["identities"] == 0

    def test_full_access_check_pass(self):
        self.zt.identity.register_identity(
            user_id="u1",
            methods=["password"],
        )
        r = self.zt.full_access_check(
            user_id="u1",
            method="password",
            credential="pass",
        )
        assert r["checked"] is True
        assert r["access"] is True

    def test_full_access_check_identity_fail(self):
        r = self.zt.full_access_check(
            user_id="unknown",
            method="password",
        )
        assert r["access"] is False
        assert "identity_failed" in r["issues"]

    def test_full_access_check_with_device(self):
        self.zt.identity.register_identity(
            user_id="u1",
            methods=["password"],
        )
        self.zt.device.register_device(
            device_id="d1",
            user_id="u1",
            components={"ua": "Chrome"},
        )
        r = self.zt.full_access_check(
            user_id="u1",
            method="password",
            credential="pass",
            device_id="d1",
            device_components={"ua": "Chrome"},
        )
        assert r["access"] is True

    def test_full_access_check_unknown_device(self):
        self.zt.identity.register_identity(
            user_id="u1",
            methods=["password"],
        )
        r = self.zt.full_access_check(
            user_id="u1",
            method="password",
            credential="pass",
            device_id="new_device",
        )
        assert "unknown_device" in r["issues"]

    def test_full_access_check_geo_fail(self):
        self.zt.identity.register_identity(
            user_id="u1",
            methods=["password"],
        )
        self.zt.geo.create_policy(
            name="eu",
            allowed_countries=["DE"],
        )
        r = self.zt.full_access_check(
            user_id="u1",
            method="password",
            credential="pass",
            country="TR",
            geo_policy="eu",
        )
        assert r["access"] is False

    def test_full_access_check_with_mfa(self):
        self.zt.identity.register_identity(
            user_id="u1",
            methods=["password"],
        )
        self.zt.mfa.enroll_method(
            user_id="u1", method="totp",
        )
        r = self.zt.full_access_check(
            user_id="u1",
            method="password",
            credential="pass",
            mfa_code="123456",
            mfa_method="totp",
        )
        assert r["access"] is True

    def test_full_access_check_permission(self):
        self.zt.identity.register_identity(
            user_id="u1",
            methods=["password"],
        )
        self.zt.privilege.define_role(
            name="viewer",
            permissions=["read"],
        )
        self.zt.privilege.assign_permissions(
            user_id="u1", role="viewer",
        )
        r = self.zt.full_access_check(
            user_id="u1",
            method="password",
            credential="pass",
            permission="read",
        )
        assert r["access"] is True

    def test_full_access_check_perm_denied(self):
        self.zt.identity.register_identity(
            user_id="u1",
            methods=["password"],
        )
        self.zt.privilege.define_role(
            name="viewer",
            permissions=["read"],
        )
        self.zt.privilege.assign_permissions(
            user_id="u1", role="viewer",
        )
        r = self.zt.full_access_check(
            user_id="u1",
            method="password",
            credential="pass",
            permission="delete",
        )
        assert r["access"] is False
        assert "permission_denied" in r["issues"]

    def test_create_secure_session(self):
        r = self.zt.create_secure_session(
            user_id="u1",
            device_id="d1",
            ip_address="1.2.3.4",
        )
        assert r["created"] is True
        assert "session_id" in r
        assert "access_token" in r

    def test_revoke_all_access(self):
        self.zt.create_secure_session(
            user_id="u1",
        )
        self.zt.create_secure_session(
            user_id="u1",
        )
        r = self.zt.revoke_all_access(
            user_id="u1",
            reason="compromised",
        )
        assert r["revoked"] is True
        assert r["sessions_terminated"] == 2
        assert r["tokens_revoked"] == 2

    def test_get_security_posture(self):
        r = self.zt.get_security_posture()
        assert r["retrieved"] is True
        assert r["health"] == "good"

    def test_get_analytics(self):
        r = self.zt.get_analytics()
        assert r["retrieved"] is True
        assert "identity" in r
        assert "mfa" in r
        assert "device" in r
        assert "geo" in r
        assert "session" in r
        assert "token" in r

    def test_summary(self):
        s = self.zt.get_summary()
        assert s["retrieved"] is True
        assert "identities" in s
        assert "active_sessions" in s
        assert "active_tokens" in s
        assert "alerts" in s


# ============================================================
# Zerotrust Modeller Testleri
# ============================================================
class TestZeroTrustModels:
    """Zerotrust model testleri."""

    def test_verification_method_enum(self):
        assert VerificationMethod.PASSWORD == "password"
        assert VerificationMethod.TOTP == "totp"
        assert VerificationMethod.BIOMETRIC == "biometric"

    def test_risk_level_enum(self):
        assert RiskLevel.LOW == "low"
        assert RiskLevel.CRITICAL == "critical"

    def test_session_state_enum(self):
        assert SessionState.ACTIVE == "active"
        assert SessionState.EXPIRED == "expired"

    def test_token_type_enum(self):
        assert TokenType.ACCESS == "access"
        assert TokenType.API_KEY == "api_key"

    def test_escalation_type_enum(self):
        assert EscalationType.VERTICAL == "vertical"
        assert EscalationType.LATERAL == "lateral"

    def test_alert_severity_enum(self):
        assert AlertSeverity.INFO == "info"
        assert AlertSeverity.EMERGENCY == "emergency"

    def test_trust_level_enum(self):
        assert TrustLevel.LOW == "low"
        assert TrustLevel.HIGH == "high"

    def test_identity_record(self):
        r = IdentityRecord(
            identity_id="id1",
            user_id="u1",
            methods=["password"],
        )
        assert r.user_id == "u1"
        assert r.verified is False

    def test_session_record(self):
        r = SessionRecord(
            session_id="s1",
            user_id="u1",
            state="active",
        )
        assert r.state == "active"
        assert r.timeout_min == 30

    def test_token_record(self):
        r = TokenRecord(
            token_id="t1",
            user_id="u1",
            token_type="access",
        )
        assert r.active is True
        assert r.ttl_min == 60

    def test_device_record(self):
        r = DeviceRecord(
            device_id="d1",
            trust_score=0.8,
        )
        assert r.trust_score == 0.8
        assert r.revoked is False

    def test_escalation_alert(self):
        r = EscalationAlert(
            alert_id="a1",
            severity="critical",
            risk_score=0.7,
        )
        assert r.severity == "critical"
        assert r.acknowledged is False

    def test_access_check_result(self):
        r = AccessCheckResult(
            user_id="u1",
            access=True,
        )
        assert r.access is True
        assert r.risk_score == 0.0

    def test_zerotrust_status(self):
        r = ZeroTrustStatus(
            health="good",
            active_sessions=5,
        )
        assert r.health == "good"
        assert r.active_sessions == 5
