"""
API Key & Credential Lifecycle Manager testleri.

KeyInventory, AutoRotationScheduler,
KeyUsageAnalyzer, OverPermissionDetector,
CredentialLeakDetector, InstantRevocator,
KeyHealthScore, RotationVerifier,
CredLifeOrchestrator testleri.
"""

import pytest

from app.core.credlife.key_inventory import (
    KeyInventory,
)
from app.core.credlife.auto_rotation_scheduler import (
    AutoRotationScheduler,
)
from app.core.credlife.key_usage_analyzer import (
    KeyUsageAnalyzer,
)
from app.core.credlife.over_permission_detector import (
    OverPermissionDetector,
)
from app.core.credlife.credential_leak_detector import (
    CredentialLeakDetector,
)
from app.core.credlife.instant_revocator import (
    InstantRevocator,
)
from app.core.credlife.key_health_score import (
    KeyHealthScore,
)
from app.core.credlife.rotation_verifier import (
    RotationVerifier,
)
from app.core.credlife.credlife_orchestrator import (
    CredLifeOrchestrator,
)
from app.models.credlife_models import (
    KeyType,
    KeyStatus,
    RotationStrategy,
    LeakSource,
    RevocationReason,
    HealthGrade,
    VerificationStatus,
    KeyRecord,
    RotationSchedule,
    UsageLog,
    LeakAlert,
    RevocationRecord,
    HealthReport,
    VerificationResult,
    CredLifeStatus,
)


# ==================== KeyInventory ====================


class TestKeyInventory:
    """KeyInventory testleri."""

    def test_init(self):
        inv = KeyInventory()
        assert inv.key_count == 0
        s = inv.get_summary()
        assert s["retrieved"] is True
        assert s["total_keys"] == 0

    def test_register_key(self):
        inv = KeyInventory()
        r = inv.register_key(
            name="test-api",
            key_type="api_key",
            owner="fatih",
            service="mapa",
            scopes=["read", "write"],
            expires_days=90,
        )
        assert r["registered"] is True
        assert r["key_id"].startswith("ki_")
        assert r["name"] == "test-api"
        assert inv.key_count == 1

    def test_register_invalid_type(self):
        inv = KeyInventory()
        r = inv.register_key(
            name="bad",
            key_type="invalid_type",
        )
        assert r["registered"] is False
        assert "Gecersiz" in r["error"]

    def test_get_key(self):
        inv = KeyInventory()
        reg = inv.register_key(
            name="k1", key_type="ssh_key",
        )
        kid = reg["key_id"]
        r = inv.get_key(kid)
        assert r["found"] is True
        assert r["name"] == "k1"
        assert r["status"] == "active"

    def test_get_key_not_found(self):
        inv = KeyInventory()
        r = inv.get_key("nonexistent")
        assert r["found"] is False

    def test_update_status(self):
        inv = KeyInventory()
        reg = inv.register_key(name="k2")
        kid = reg["key_id"]
        r = inv.update_status(kid, "expired")
        assert r["updated"] is True
        assert r["old_status"] == "active"
        assert r["new_status"] == "expired"

    def test_update_status_invalid(self):
        inv = KeyInventory()
        reg = inv.register_key(name="k3")
        kid = reg["key_id"]
        r = inv.update_status(kid, "bad")
        assert r["updated"] is False

    def test_record_usage(self):
        inv = KeyInventory()
        reg = inv.register_key(name="k4")
        kid = reg["key_id"]
        r = inv.record_usage(kid)
        assert r["recorded"] is True
        assert r["usage_count"] == 1
        r2 = inv.record_usage(kid)
        assert r2["usage_count"] == 2

    def test_update_scopes(self):
        inv = KeyInventory()
        reg = inv.register_key(
            name="k5", scopes=["read"],
        )
        kid = reg["key_id"]
        r = inv.update_scopes(
            kid, ["read", "write", "delete"],
        )
        assert r["updated"] is True
        assert len(r["new_scopes"]) == 3

    def test_get_keys_by_owner(self):
        inv = KeyInventory()
        inv.register_key(
            name="k6", owner="fatih",
        )
        inv.register_key(
            name="k7", owner="fatih",
        )
        inv.register_key(
            name="k8", owner="ahmet",
        )
        r = inv.get_keys_by_owner("fatih")
        assert r["retrieved"] is True
        assert r["count"] == 2

    def test_get_expiring_keys(self):
        inv = KeyInventory()
        inv.register_key(
            name="short", expires_days=10,
        )
        inv.register_key(
            name="long", expires_days=365,
        )
        r = inv.get_expiring_keys(
            within_days=30,
        )
        assert r["retrieved"] is True
        assert r["count"] == 1

    def test_get_summary(self):
        inv = KeyInventory()
        inv.register_key(
            name="s1",
            key_type="api_key",
            owner="o1",
        )
        inv.register_key(
            name="s2",
            key_type="ssh_key",
            owner="o2",
        )
        s = inv.get_summary()
        assert s["total_keys"] == 2
        assert s["active_keys"] == 2
        assert "api_key" in s["by_type"]
        assert s["total_owners"] == 2

    def test_key_types_class_var(self):
        assert "api_key" in KeyInventory.KEY_TYPES
        assert "tls_cert" in KeyInventory.KEY_TYPES

    def test_key_statuses_class_var(self):
        assert "active" in KeyInventory.KEY_STATUSES
        assert "revoked" in KeyInventory.KEY_STATUSES

    def test_register_with_metadata(self):
        inv = KeyInventory()
        r = inv.register_key(
            name="meta",
            metadata={"env": "prod"},
        )
        assert r["registered"] is True
        kid = r["key_id"]
        k = inv.get_key(kid)
        assert k["metadata"]["env"] == "prod"


# ==================== AutoRotationScheduler ====================


class TestAutoRotationScheduler:
    """AutoRotationScheduler testleri."""

    def test_init(self):
        s = AutoRotationScheduler()
        assert s.schedule_count == 0
        r = s.get_summary()
        assert r["retrieved"] is True

    def test_init_custom_days(self):
        s = AutoRotationScheduler(
            default_rotation_days=30,
        )
        assert s._default_days == 30

    def test_create_policy(self):
        s = AutoRotationScheduler()
        r = s.create_policy(
            name="standard",
            rotation_days=60,
            strategy="time_based",
        )
        assert r["created"] is True
        assert r["rotation_days"] == 60

    def test_create_policy_invalid_strategy(self):
        s = AutoRotationScheduler()
        r = s.create_policy(
            name="bad",
            strategy="invalid",
        )
        assert r["created"] is False

    def test_schedule_rotation(self):
        s = AutoRotationScheduler()
        r = s.schedule_rotation(
            key_id="k1",
            custom_days=45,
        )
        assert r["scheduled"] is True
        assert r["rotation_days"] == 45
        assert s.schedule_count == 1

    def test_schedule_with_policy(self):
        s = AutoRotationScheduler()
        s.create_policy(
            name="fast", rotation_days=30,
        )
        r = s.schedule_rotation(
            key_id="k2",
            policy_name="fast",
        )
        assert r["rotation_days"] == 30

    def test_register_hook(self):
        s = AutoRotationScheduler()
        r = s.register_hook(
            key_id="k1",
            hook_type="pre",
            action="backup",
            description="Yedekle",
        )
        assert r["registered"] is True
        assert r["hook_type"] == "pre"

    def test_register_hook_invalid_type(self):
        s = AutoRotationScheduler()
        r = s.register_hook(
            key_id="k1",
            hook_type="invalid",
        )
        assert r["registered"] is False

    def test_execute_rotation(self):
        s = AutoRotationScheduler()
        s.schedule_rotation(key_id="k1")
        s.register_hook(
            key_id="k1",
            hook_type="pre",
            action="backup",
        )
        s.register_hook(
            key_id="k1",
            hook_type="post",
            action="notify",
        )
        r = s.execute_rotation(key_id="k1")
        assert r["rotated"] is True
        assert r["pre_hooks_run"] == 1
        assert r["post_hooks_run"] == 1
        assert len(r["new_key_prefix"]) == 8

    def test_execute_rotation_no_schedule(self):
        s = AutoRotationScheduler()
        r = s.execute_rotation(key_id="none")
        assert r["rotated"] is False

    def test_check_due_rotations(self):
        s = AutoRotationScheduler()
        s.schedule_rotation(
            key_id="k1", custom_days=3,
        )
        s.schedule_rotation(
            key_id="k2", custom_days=100,
        )
        r = s.check_due_rotations()
        assert r["checked"] is True
        assert r["count"] == 1
        assert r["due_rotations"][0]["urgent"] is True

    def test_get_rotation_history(self):
        s = AutoRotationScheduler()
        s.schedule_rotation(key_id="k1")
        s.execute_rotation(key_id="k1")
        r = s.get_rotation_history(key_id="k1")
        assert r["retrieved"] is True
        assert r["count"] == 1

    def test_rotation_strategies(self):
        assert "time_based" in AutoRotationScheduler.ROTATION_STRATEGIES
        assert "usage_based" in AutoRotationScheduler.ROTATION_STRATEGIES


# ==================== KeyUsageAnalyzer ====================


class TestKeyUsageAnalyzer:
    """KeyUsageAnalyzer testleri."""

    def test_init(self):
        a = KeyUsageAnalyzer()
        assert a.anomaly_count == 0
        s = a.get_summary()
        assert s["retrieved"] is True

    def test_record_usage(self):
        a = KeyUsageAnalyzer()
        r = a.record_usage(
            key_id="k1",
            action="read",
            source_ip="1.2.3.4",
            endpoint="/api/data",
        )
        assert r["recorded"] is True
        assert r["total_logs"] == 1

    def test_analyze_patterns(self):
        a = KeyUsageAnalyzer()
        a.record_usage(
            key_id="k1",
            source_ip="1.1.1.1",
            endpoint="/api/a",
        )
        a.record_usage(
            key_id="k1",
            source_ip="2.2.2.2",
            endpoint="/api/a",
            response_code=500,
        )
        r = a.analyze_patterns(key_id="k1")
        assert r["analyzed"] is True
        assert r["total_usage"] == 2
        assert r["unique_ips"] == 2
        assert r["error_count"] == 1

    def test_analyze_empty(self):
        a = KeyUsageAnalyzer()
        r = a.analyze_patterns(key_id="none")
        assert r["analyzed"] is True
        assert r["total_usage"] == 0

    def test_detect_anomalies_too_many_ips(self):
        a = KeyUsageAnalyzer()
        for i in range(10):
            a.record_usage(
                key_id="k1",
                source_ip=f"10.0.0.{i}",
            )
        r = a.detect_anomalies(
            key_id="k1", max_ips=5,
        )
        assert r["detected"] is True
        assert r["count"] >= 1
        types = [
            an["type"]
            for an in r["anomalies"]
        ]
        assert "too_many_ips" in types

    def test_detect_anomalies_high_error_rate(self):
        a = KeyUsageAnalyzer()
        for _ in range(5):
            a.record_usage(
                key_id="k2",
                source_ip="1.1.1.1",
                response_code=500,
            )
        r = a.detect_anomalies(
            key_id="k2", max_error_rate=0.3,
        )
        types = [
            an["type"]
            for an in r["anomalies"]
        ]
        assert "high_error_rate" in types

    def test_detect_anomalies_rapid_ip_change(self):
        a = KeyUsageAnalyzer()
        for i in range(10):
            a.record_usage(
                key_id="k3",
                source_ip=f"192.168.{i}.1",
            )
        r = a.detect_anomalies(key_id="k3")
        types = [
            an["type"]
            for an in r["anomalies"]
        ]
        assert "rapid_ip_change" in types

    def test_detect_anomalies_empty(self):
        a = KeyUsageAnalyzer()
        r = a.detect_anomalies(key_id="none")
        assert r["detected"] is True
        assert len(r["anomalies"]) == 0

    def test_find_unused_keys(self):
        a = KeyUsageAnalyzer()
        a.record_usage(key_id="k1")
        a.record_usage(key_id="k1")
        a.record_usage(key_id="k1")
        a.record_usage(key_id="k2")
        r = a.find_unused_keys(
            all_key_ids=["k1", "k2", "k3"],
        )
        assert r["found"] is True
        assert r["count"] == 2  # k2 rarely, k3 never

    def test_get_recommendations_unused(self):
        a = KeyUsageAnalyzer()
        r = a.get_recommendations(key_id="none")
        assert r["retrieved"] is True
        assert r["count"] >= 1
        types = [
            rec["type"]
            for rec in r["recommendations"]
        ]
        assert "remove_unused" in types

    def test_get_recommendations_errors(self):
        a = KeyUsageAnalyzer()
        for _ in range(10):
            a.record_usage(
                key_id="err",
                source_ip="1.1.1.1",
                response_code=500,
            )
        r = a.get_recommendations(key_id="err")
        types = [
            rec["type"]
            for rec in r["recommendations"]
        ]
        assert "investigate_errors" in types

    def test_get_recommendations_many_ips(self):
        a = KeyUsageAnalyzer()
        for i in range(15):
            a.record_usage(
                key_id="multi",
                source_ip=f"10.0.{i}.1",
            )
        r = a.get_recommendations(key_id="multi")
        types = [
            rec["type"]
            for rec in r["recommendations"]
        ]
        assert "restrict_ips" in types

    def test_risk_levels(self):
        assert "critical" in KeyUsageAnalyzer.RISK_LEVELS


# ==================== OverPermissionDetector ====================


class TestOverPermissionDetector:
    """OverPermissionDetector testleri."""

    def test_init(self):
        d = OverPermissionDetector()
        assert d.violation_count == 0
        s = d.get_summary()
        assert s["retrieved"] is True

    def test_create_policy(self):
        d = OverPermissionDetector()
        r = d.create_policy(
            name="strict",
            service="api",
            max_scopes=3,
            forbidden_scopes=["admin:delete"],
        )
        assert r["created"] is True

    def test_scan_unused_scopes(self):
        d = OverPermissionDetector()
        r = d.scan_key_permissions(
            key_id="k1",
            current_scopes=[
                "read", "write", "delete",
                "admin",
            ],
            used_scopes=["read"],
        )
        assert r["scanned"] is True
        assert r["unused_scopes"] == 3
        assert r["violations"] > 0

    def test_scan_admin_unused(self):
        d = OverPermissionDetector()
        r = d.scan_key_permissions(
            key_id="k2",
            current_scopes=[
                "read", "admin", "delete",
            ],
            used_scopes=["read"],
        )
        types = [
            v["type"]
            for v in r["violation_details"]
        ]
        assert "unused_admin" in types

    def test_scan_exceeds_max_scopes(self):
        d = OverPermissionDetector()
        d.create_policy(
            name="tight",
            max_scopes=2,
        )
        r = d.scan_key_permissions(
            key_id="k3",
            current_scopes=[
                "a", "b", "c", "d",
            ],
            used_scopes=["a", "b", "c", "d"],
            policy_name="tight",
        )
        types = [
            v["type"]
            for v in r["violation_details"]
        ]
        assert "exceeds_max_scopes" in types

    def test_scan_forbidden_scopes(self):
        d = OverPermissionDetector()
        d.create_policy(
            name="safe",
            forbidden_scopes=["danger"],
        )
        r = d.scan_key_permissions(
            key_id="k4",
            current_scopes=[
                "read", "danger",
            ],
            used_scopes=["read", "danger"],
            policy_name="safe",
        )
        types = [
            v["type"]
            for v in r["violation_details"]
        ]
        assert "forbidden_scopes" in types

    def test_risk_score(self):
        d = OverPermissionDetector()
        r = d.scan_key_permissions(
            key_id="k5",
            current_scopes=[
                "read", "admin", "delete",
                "write", "exec",
            ],
            used_scopes=["read"],
        )
        assert r["risk_score"] > 0

    def test_get_remediation(self):
        d = OverPermissionDetector()
        r = d.get_remediation(
            key_id="k1",
            current_scopes=[
                "read", "write", "delete",
            ],
            used_scopes=["read"],
        )
        assert r["retrieved"] is True
        assert r["count"] > 0

    def test_apply_remediation(self):
        d = OverPermissionDetector()
        r = d.apply_remediation(
            key_id="k1",
            scopes_to_remove=["write", "delete"],
        )
        assert r["applied"] is True
        assert r["count"] == 2

    def test_scan_no_issues(self):
        d = OverPermissionDetector()
        r = d.scan_key_permissions(
            key_id="ok",
            current_scopes=["read"],
            used_scopes=["read"],
        )
        assert r["scanned"] is True
        assert r["violations"] == 0
        assert r["risk_score"] == 0.0


# ==================== CredentialLeakDetector ====================


class TestCredentialLeakDetector:
    """CredentialLeakDetector testleri."""

    def test_init(self):
        d = CredentialLeakDetector()
        assert d.leak_count == 0
        s = d.get_summary()
        assert s["retrieved"] is True
        assert s["total_patterns"] >= 5

    def test_init_auto_revoke(self):
        d = CredentialLeakDetector(
            auto_revoke=False,
        )
        assert d._auto_revoke is False

    def test_register_pattern(self):
        d = CredentialLeakDetector()
        before = len(d._patterns)
        r = d.register_pattern(
            name="custom",
            pattern=r"SECRET_\w+",
            severity="critical",
        )
        assert r["registered"] is True
        assert len(d._patterns) == before + 1

    def test_register_pattern_invalid(self):
        d = CredentialLeakDetector()
        r = d.register_pattern(
            name="bad",
            pattern="x",
            severity="invalid",
        )
        assert r["registered"] is False

    def test_monitor_key(self):
        d = CredentialLeakDetector()
        r = d.monitor_key(
            key_id="k1",
            key_prefix="sk-abc123",
            service="openai",
        )
        assert r["monitoring"] is True

    def test_scan_content_api_key(self):
        d = CredentialLeakDetector()
        content = 'api_key = "abcdefghijklmnopqrstuvwx"'
        r = d.scan_content(
            content=content,
            source="config_file",
        )
        assert r["scanned"] is True
        assert r["findings"] > 0

    def test_scan_content_aws_key(self):
        d = CredentialLeakDetector()
        content = "AKIAIOSFODNN7EXAMPLE"
        r = d.scan_content(
            content=content,
            source="github_public",
        )
        assert r["findings"] > 0

    def test_scan_content_private_key(self):
        d = CredentialLeakDetector()
        content = "-----BEGIN RSA PRIVATE KEY-----"
        r = d.scan_content(
            content=content,
            source="git_history",
        )
        assert r["findings"] > 0

    def test_scan_content_clean(self):
        d = CredentialLeakDetector()
        r = d.scan_content(
            content="Hello world, no secrets here.",
            source="log_file",
        )
        assert r["scanned"] is True
        assert r["findings"] == 0

    def test_scan_monitored_key(self):
        d = CredentialLeakDetector()
        d.monitor_key(
            key_id="k1",
            key_prefix="my-secret-key",
        )
        r = d.scan_content(
            content="found my-secret-key in code",
            source="github_public",
        )
        assert r["findings"] > 0

    def test_auto_revocation(self):
        d = CredentialLeakDetector(
            auto_revoke=True,
        )
        content = "AKIAIOSFODNN7EXAMPLE"
        d.scan_content(content=content)
        alerts = d.get_alerts()
        revoked = [
            a for a in alerts["alerts"]
            if a.get("auto_revoked")
        ]
        assert len(revoked) > 0

    def test_scan_git_history(self):
        d = CredentialLeakDetector()
        commits = [
            {
                "commit_id": "abc123",
                "diff": 'password = "mysecretpass123"',
            },
            {
                "commit_id": "def456",
                "diff": "clean code here",
            },
        ]
        r = d.scan_git_history(commits=commits)
        assert r["scanned"] is True
        assert r["total_findings"] > 0
        assert len(r["affected_commits"]) == 1

    def test_check_dark_web(self):
        d = CredentialLeakDetector()
        r = d.check_dark_web(
            key_hash="abc123",
            known_breaches=[
                {
                    "name": "breach1",
                    "date": "2025-01-01",
                    "hashes": ["abc123", "def456"],
                },
            ],
        )
        assert r["checked"] is True
        assert r["found_in_breaches"] == 1

    def test_check_dark_web_clean(self):
        d = CredentialLeakDetector()
        r = d.check_dark_web(
            key_hash="safe_key",
            known_breaches=[
                {
                    "name": "b1",
                    "date": "2025",
                    "hashes": ["other"],
                },
            ],
        )
        assert r["found_in_breaches"] == 0

    def test_get_alerts_filter(self):
        d = CredentialLeakDetector()
        d.scan_content(
            content="AKIAIOSFODNN7EXAMPLE",
        )
        r = d.get_alerts(severity="emergency")
        assert r["retrieved"] is True
        assert r["count"] >= 1

    def test_leak_sources(self):
        assert "github_public" in CredentialLeakDetector.LEAK_SOURCES
        assert "dark_web" in CredentialLeakDetector.LEAK_SOURCES


# ==================== InstantRevocator ====================


class TestInstantRevocator:
    """InstantRevocator testleri."""

    def test_init(self):
        r = InstantRevocator()
        assert r.revocation_count == 0
        s = r.get_summary()
        assert s["retrieved"] is True

    def test_revoke_key(self):
        r = InstantRevocator()
        result = r.revoke_key(
            key_id="k1",
            reason="leaked",
            revoked_by="system",
        )
        assert result["revoked"] is True
        assert r.revocation_count == 1

    def test_revoke_invalid_reason(self):
        r = InstantRevocator()
        result = r.revoke_key(
            key_id="k1", reason="invalid",
        )
        assert result["revoked"] is False

    def test_revoke_with_cascade(self):
        r = InstantRevocator()
        result = r.revoke_key(
            key_id="k1",
            reason="compromised",
            cascade=True,
        )
        assert result["revoked"] is True
        assert result["cascade_result"] is not None

    def test_revoke_with_replacement(self):
        r = InstantRevocator()
        result = r.revoke_key(
            key_id="k1",
            reason="rotation",
            generate_replacement=True,
        )
        assert result["revoked"] is True
        assert result["replacement"] is not None
        assert result["replacement"]["generated"] is True

    def test_revoke_with_notifications(self):
        r = InstantRevocator()
        result = r.revoke_key(
            key_id="k1",
            reason="leaked",
            notify_services=["api", "web"],
        )
        assert result["notifications"] == 2

    def test_bulk_revoke(self):
        r = InstantRevocator()
        result = r.bulk_revoke(
            key_ids=["k1", "k2", "k3"],
            reason="compromised",
        )
        assert result["completed"] is True
        assert result["revoked"] == 3
        assert r.revocation_count == 3

    def test_get_revocation(self):
        r = InstantRevocator()
        r.revoke_key(
            key_id="k1", reason="manual",
        )
        result = r.get_revocation("k1")
        assert result["found"] is True
        assert result["reason"] == "manual"

    def test_get_revocation_not_found(self):
        r = InstantRevocator()
        result = r.get_revocation("none")
        assert result["found"] is False

    def test_get_audit_log(self):
        r = InstantRevocator()
        r.revoke_key(
            key_id="k1",
            reason="leaked",
            cascade=True,
            generate_replacement=True,
        )
        result = r.get_audit_log(key_id="k1")
        assert result["retrieved"] is True
        assert result["count"] >= 3  # revoke + cascade + replacement

    def test_get_audit_log_all(self):
        r = InstantRevocator()
        r.revoke_key(key_id="a", reason="manual")
        r.revoke_key(key_id="b", reason="leaked")
        result = r.get_audit_log()
        assert result["count"] >= 2

    def test_summary_by_reason(self):
        r = InstantRevocator()
        r.revoke_key(key_id="a", reason="leaked")
        r.revoke_key(key_id="b", reason="leaked")
        r.revoke_key(key_id="c", reason="manual")
        s = r.get_summary()
        assert s["by_reason"]["leaked"] == 2
        assert s["by_reason"]["manual"] == 1

    def test_revocation_reasons(self):
        assert "leaked" in InstantRevocator.REVOCATION_REASONS
        assert "compromised" in InstantRevocator.REVOCATION_REASONS


# ==================== KeyHealthScore ====================


class TestKeyHealthScore:
    """KeyHealthScore testleri."""

    def test_init(self):
        h = KeyHealthScore()
        assert h.scored_count == 0
        s = h.get_summary()
        assert s["retrieved"] is True

    def test_calculate_age_score(self):
        h = KeyHealthScore()
        assert h.calculate_age_score(0) == 100.0
        assert h.calculate_age_score(365) == 0.0
        assert 40 < h.calculate_age_score(180) < 60

    def test_calculate_usage_score(self):
        h = KeyHealthScore()
        # Never used
        assert h.calculate_usage_score(0) == 30.0
        # Good usage
        assert h.calculate_usage_score(100, 0, 0) == 100.0
        # High errors
        score = h.calculate_usage_score(10, 8, 0)
        assert score < 70

    def test_calculate_usage_score_inactive(self):
        h = KeyHealthScore()
        score = h.calculate_usage_score(
            total_usage=10,
            error_count=0,
            days_since_last_use=100,
        )
        assert score < 80

    def test_calculate_permission_score(self):
        h = KeyHealthScore()
        # Perfect
        assert h.calculate_permission_score(
            2, 2, False,
        ) == 100.0
        # Admin penalty
        score = h.calculate_permission_score(
            3, 3, True,
        )
        assert score < 100
        # Unused scopes
        score2 = h.calculate_permission_score(
            10, 2, False,
        )
        assert score2 < 60

    def test_calculate_rotation_score(self):
        h = KeyHealthScore()
        # Fresh rotation
        assert h.calculate_rotation_score(
            10, 90, 1,
        ) == 100.0
        # Overdue
        score = h.calculate_rotation_score(
            200, 90, 1,
        )
        assert score < 40

    def test_calculate_rotation_never_rotated(self):
        h = KeyHealthScore()
        score = h.calculate_rotation_score(
            10, 90, 0,
        )
        assert score <= 60

    def test_calculate_anomaly_score(self):
        h = KeyHealthScore()
        assert h.calculate_anomaly_score(
            0, 0,
        ) == 100.0
        score = h.calculate_anomaly_score(
            3, 2,
        )
        assert score < 50

    def test_calculate_health_full(self):
        h = KeyHealthScore()
        r = h.calculate_health(
            key_id="k1",
            age_days=30,
            total_usage=50,
            error_count=2,
            days_since_last_use=1,
            total_scopes=3,
            used_scopes=3,
            has_admin=False,
            days_since_rotation=30,
            rotation_policy_days=90,
            rotation_count=2,
            anomaly_count=0,
            critical_anomalies=0,
        )
        assert r["calculated"] is True
        assert r["overall_score"] > 80
        assert r["grade"] in ("excellent", "good")

    def test_calculate_health_poor(self):
        h = KeyHealthScore()
        r = h.calculate_health(
            key_id="k2",
            age_days=350,
            total_usage=5,
            error_count=4,
            days_since_last_use=100,
            total_scopes=15,
            used_scopes=2,
            has_admin=True,
            days_since_rotation=300,
            rotation_policy_days=90,
            rotation_count=0,
            anomaly_count=5,
            critical_anomalies=3,
        )
        assert r["calculated"] is True
        assert r["overall_score"] < 30
        assert r["grade"] == "critical"

    def test_set_weights(self):
        h = KeyHealthScore()
        r = h.set_weights({"age": 0.5})
        assert r["updated"] is True
        assert r["weights"]["age"] == 0.5

    def test_assess_fleet(self):
        h = KeyHealthScore()
        keys = [
            {
                "key_id": "k1",
                "age_days": 10,
                "total_usage": 100,
            },
            {
                "key_id": "k2",
                "age_days": 300,
                "total_usage": 0,
            },
        ]
        r = h.assess_fleet(key_data=keys)
        assert r["assessed"] is True
        assert r["total_keys"] == 2
        assert r["average_score"] > 0

    def test_get_score(self):
        h = KeyHealthScore()
        h.calculate_health(key_id="k1")
        r = h.get_score("k1")
        assert r["found"] is True

    def test_get_score_not_found(self):
        h = KeyHealthScore()
        r = h.get_score("none")
        assert r["found"] is False

    def test_health_grades(self):
        assert "excellent" in KeyHealthScore.HEALTH_GRADES
        assert "critical" in KeyHealthScore.HEALTH_GRADES


# ==================== RotationVerifier ====================


class TestRotationVerifier:
    """RotationVerifier testleri."""

    def test_init(self):
        v = RotationVerifier()
        assert v.verification_count == 0
        s = v.get_summary()
        assert s["retrieved"] is True

    def test_init_custom(self):
        v = RotationVerifier(
            auto_rollback=False,
            max_test_retries=5,
        )
        assert v._auto_rollback is False
        assert v._max_retries == 5

    def test_start_verification(self):
        v = RotationVerifier()
        r = v.start_verification(
            key_id="k1",
            rotation_id="rot1",
            new_key_prefix="abc12345",
            services=["api", "web"],
        )
        assert r["started"] is True
        assert v.verification_count == 1

    def test_run_test(self):
        v = RotationVerifier()
        sv = v.start_verification(
            key_id="k1",
        )
        vid = sv["verification_id"]
        r = v.run_test(
            verification_id=vid,
            test_type="connectivity",
            service="api",
            test_result=True,
            response_time_ms=50,
        )
        assert r["tested"] is True
        assert r["passed"] is True

    def test_run_test_invalid_type(self):
        v = RotationVerifier()
        sv = v.start_verification(key_id="k1")
        vid = sv["verification_id"]
        r = v.run_test(
            verification_id=vid,
            test_type="invalid",
        )
        assert r["tested"] is False

    def test_run_test_no_verification(self):
        v = RotationVerifier()
        r = v.run_test(
            verification_id="none",
        )
        assert r["tested"] is False

    def test_run_full_verification_pass(self):
        v = RotationVerifier()
        sv = v.start_verification(key_id="k1")
        vid = sv["verification_id"]
        r = v.run_full_verification(
            verification_id=vid,
            test_results=[
                {
                    "test_type": "connectivity",
                    "passed": True,
                },
                {
                    "test_type": "authentication",
                    "passed": True,
                },
            ],
        )
        assert r["verified"] is True
        assert r["all_passed"] is True
        assert r["status"] == "passed"

    def test_run_full_verification_fail(self):
        v = RotationVerifier(
            auto_rollback=True,
        )
        sv = v.start_verification(key_id="k1")
        vid = sv["verification_id"]
        r = v.run_full_verification(
            verification_id=vid,
            test_results=[
                {
                    "test_type": "connectivity",
                    "passed": True,
                },
                {
                    "test_type": "authentication",
                    "passed": False,
                },
            ],
        )
        assert r["verified"] is True
        assert r["all_passed"] is False
        assert r["status"] == "rolled_back"

    def test_run_full_fail_no_rollback(self):
        v = RotationVerifier(
            auto_rollback=False,
        )
        sv = v.start_verification(key_id="k1")
        vid = sv["verification_id"]
        r = v.run_full_verification(
            verification_id=vid,
            test_results=[
                {
                    "test_type": "connectivity",
                    "passed": False,
                },
            ],
        )
        assert r["status"] == "failed"

    def test_trigger_rollback(self):
        v = RotationVerifier()
        sv = v.start_verification(key_id="k1")
        vid = sv["verification_id"]
        r = v.trigger_rollback(vid)
        assert r["rolled_back"] is True

    def test_get_verification(self):
        v = RotationVerifier()
        sv = v.start_verification(key_id="k1")
        vid = sv["verification_id"]
        r = v.get_verification(vid)
        assert r["found"] is True
        assert r["key_id"] == "k1"

    def test_get_verification_not_found(self):
        v = RotationVerifier()
        r = v.get_verification("none")
        assert r["found"] is False

    def test_summary_by_status(self):
        v = RotationVerifier()
        sv1 = v.start_verification(key_id="k1")
        sv2 = v.start_verification(key_id="k2")
        v.run_full_verification(
            sv1["verification_id"],
            test_results=[
                {"test_type": "connectivity", "passed": True},
            ],
        )
        s = v.get_summary()
        assert "passed" in s["by_status"]
        assert "pending" in s["by_status"]

    def test_test_types(self):
        assert "connectivity" in RotationVerifier.TEST_TYPES
        assert "performance" in RotationVerifier.TEST_TYPES


# ==================== CredLifeOrchestrator ====================


class TestCredLifeOrchestrator:
    """CredLifeOrchestrator testleri."""

    def test_init(self):
        o = CredLifeOrchestrator()
        s = o.get_summary()
        assert s["retrieved"] is True
        assert s["total_keys"] == 0

    def test_init_custom(self):
        o = CredLifeOrchestrator(
            default_rotation_days=30,
            auto_revoke_leaked=False,
            auto_rollback=False,
        )
        assert o.scheduler._default_days == 30
        assert o.leak_detector._auto_revoke is False
        assert o.verifier._auto_rollback is False

    def test_create_key(self):
        o = CredLifeOrchestrator()
        r = o.create_key(
            name="test-key",
            key_type="api_key",
            owner="fatih",
            service="mapa",
            scopes=["read", "write"],
            expires_days=60,
        )
        assert r["created"] is True
        assert r["monitoring"] is True
        assert o.inventory.key_count == 1
        assert o.scheduler.schedule_count == 1

    def test_create_key_invalid_type(self):
        o = CredLifeOrchestrator()
        r = o.create_key(
            name="bad",
            key_type="invalid",
        )
        assert r.get("registered") is False

    def test_rotate_key(self):
        o = CredLifeOrchestrator()
        ck = o.create_key(
            name="rot-test",
            expires_days=90,
        )
        kid = ck["key_id"]
        r = o.rotate_key(
            key_id=kid, verify=True,
        )
        assert r["rotated"] is True
        assert r["verification"] is not None

    def test_rotate_key_no_verify(self):
        o = CredLifeOrchestrator()
        ck = o.create_key(name="nv")
        kid = ck["key_id"]
        r = o.rotate_key(
            key_id=kid, verify=False,
        )
        assert r["rotated"] is True
        assert r["verification"] is None

    def test_revoke_key(self):
        o = CredLifeOrchestrator()
        ck = o.create_key(name="rev-test")
        kid = ck["key_id"]
        r = o.revoke_key(
            key_id=kid,
            reason="leaked",
        )
        assert r["revoked"] is True
        key = o.inventory.get_key(kid)
        assert key["status"] == "revoked"

    def test_revoke_with_replacement(self):
        o = CredLifeOrchestrator()
        ck = o.create_key(name="rr")
        kid = ck["key_id"]
        r = o.revoke_key(
            key_id=kid,
            reason="compromised",
            generate_replacement=True,
        )
        assert r["replacement"] is not None

    def test_check_health(self):
        o = CredLifeOrchestrator()
        r = o.check_health(
            key_id="k1",
            age_days=30,
            total_usage=50,
            total_scopes=3,
            used_scopes=3,
        )
        assert r["calculated"] is True
        assert r["overall_score"] > 0

    def test_scan_for_leaks(self):
        o = CredLifeOrchestrator()
        r = o.scan_for_leaks(
            content="AKIAIOSFODNN7EXAMPLE",
            source="github_public",
        )
        assert r["scanned"] is True
        assert r["findings"] > 0

    def test_check_permissions(self):
        o = CredLifeOrchestrator()
        r = o.check_permissions(
            key_id="k1",
            current_scopes=[
                "read", "write", "admin",
            ],
            used_scopes=["read"],
        )
        assert r["checked"] is True
        assert r["remediation"] is not None

    def test_check_permissions_clean(self):
        o = CredLifeOrchestrator()
        r = o.check_permissions(
            key_id="k2",
            current_scopes=["read"],
            used_scopes=["read"],
        )
        assert r["checked"] is True
        assert r["remediation"] is None

    def test_get_analytics(self):
        o = CredLifeOrchestrator()
        o.create_key(name="a1")
        r = o.get_analytics()
        assert r["retrieved"] is True
        assert "inventory" in r
        assert "scheduler" in r
        assert "health" in r

    def test_full_lifecycle(self):
        """Tam yasam dongusu testi."""
        o = CredLifeOrchestrator()

        # 1. Olustur
        ck = o.create_key(
            name="lifecycle-test",
            key_type="api_key",
            owner="fatih",
            service="atlas",
            scopes=["read", "write"],
            expires_days=90,
        )
        assert ck["created"] is True
        kid = ck["key_id"]

        # 2. Saglik kontrol
        h = o.check_health(
            key_id=kid,
            age_days=0,
            total_usage=10,
        )
        assert h["calculated"] is True

        # 3. Rotate
        rot = o.rotate_key(kid)
        assert rot["rotated"] is True

        # 4. Iptal
        rev = o.revoke_key(
            key_id=kid,
            reason="rotation",
            generate_replacement=True,
        )
        assert rev["revoked"] is True

        s = o.get_summary()
        assert s["total_revocations"] >= 1


# ==================== Models ====================


class TestCredLifeModels:
    """Credlife modelleri testleri."""

    def test_key_type_enum(self):
        assert KeyType.API_KEY == "api_key"
        assert KeyType.SSH_KEY == "ssh_key"

    def test_key_status_enum(self):
        assert KeyStatus.ACTIVE == "active"
        assert KeyStatus.REVOKED == "revoked"

    def test_rotation_strategy_enum(self):
        assert RotationStrategy.TIME_BASED == "time_based"

    def test_leak_source_enum(self):
        assert LeakSource.GITHUB_PUBLIC == "github_public"
        assert LeakSource.DARK_WEB == "dark_web"

    def test_revocation_reason_enum(self):
        assert RevocationReason.LEAKED == "leaked"
        assert RevocationReason.MANUAL == "manual"

    def test_health_grade_enum(self):
        assert HealthGrade.EXCELLENT == "excellent"
        assert HealthGrade.CRITICAL == "critical"

    def test_verification_status_enum(self):
        assert VerificationStatus.PENDING == "pending"
        assert VerificationStatus.ROLLED_BACK == "rolled_back"

    def test_key_record_model(self):
        r = KeyRecord(
            key_id="k1",
            name="test",
            key_type=KeyType.API_KEY,
        )
        assert r.key_id == "k1"
        assert r.status == KeyStatus.ACTIVE

    def test_rotation_schedule_model(self):
        r = RotationSchedule(
            schedule_id="s1",
            key_id="k1",
            rotation_days=60,
        )
        assert r.rotation_days == 60

    def test_usage_log_model(self):
        u = UsageLog(
            key_id="k1",
            action="read",
            response_code=200,
        )
        assert u.response_code == 200

    def test_leak_alert_model(self):
        a = LeakAlert(
            alert_id="a1",
            severity="emergency",
            auto_revoked=True,
        )
        assert a.auto_revoked is True

    def test_revocation_record_model(self):
        r = RevocationRecord(
            revocation_id="r1",
            key_id="k1",
            reason=RevocationReason.LEAKED,
        )
        assert r.reason == RevocationReason.LEAKED

    def test_health_report_model(self):
        h = HealthReport(
            key_id="k1",
            overall_score=85.5,
            grade=HealthGrade.GOOD,
        )
        assert h.overall_score == 85.5

    def test_verification_result_model(self):
        v = VerificationResult(
            verification_id="v1",
            status=VerificationStatus.PASSED,
        )
        assert v.status == VerificationStatus.PASSED

    def test_credlife_status_model(self):
        s = CredLifeStatus(
            total_keys=10,
            active_keys=8,
            average_health=75.0,
        )
        assert s.total_keys == 10
