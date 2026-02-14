"""Security Hardening sistemi testleri."""

import time

import pytest

from app.models.security_hardening import (
    AccessAction,
    AccessRecord,
    AuditEntry,
    AuditEventType,
    FirewallAction,
    SecuritySnapshot,
    SessionRecord,
    SessionStatus,
    ThreatLevel,
    ThreatRecord,
    ThreatType,
)
from app.core.security.threat_detector import ThreatDetector
from app.core.security.access_controller import AccessController
from app.core.security.encryption_manager import EncryptionManager
from app.core.security.input_validator import InputValidator
from app.core.security.secret_manager import SecretManager
from app.core.security.session_guardian import SessionGuardian
from app.core.security.firewall import Firewall
from app.core.security.audit_logger import AuditLogger
from app.core.security.security_orchestrator import SecurityOrchestrator


# ── Model Testleri ──────────────────────────────────────────


class TestModels:
    """Veri modeli testleri."""

    def test_threat_level_values(self):
        assert ThreatLevel.NONE == "none"
        assert ThreatLevel.LOW == "low"
        assert ThreatLevel.MEDIUM == "medium"
        assert ThreatLevel.HIGH == "high"
        assert ThreatLevel.CRITICAL == "critical"

    def test_threat_type_values(self):
        assert ThreatType.BRUTE_FORCE == "brute_force"
        assert ThreatType.INJECTION == "injection"
        assert ThreatType.XSS == "xss"
        assert ThreatType.DDOS == "ddos"

    def test_access_action_values(self):
        assert AccessAction.READ == "read"
        assert AccessAction.WRITE == "write"
        assert AccessAction.DELETE == "delete"
        assert AccessAction.ADMIN == "admin"

    def test_audit_event_type_values(self):
        assert AuditEventType.LOGIN == "login"
        assert AuditEventType.ACCESS == "access"
        assert AuditEventType.CHANGE == "change"
        assert AuditEventType.THREAT == "threat"

    def test_session_status_values(self):
        assert SessionStatus.ACTIVE == "active"
        assert SessionStatus.EXPIRED == "expired"
        assert SessionStatus.REVOKED == "revoked"

    def test_firewall_action_values(self):
        assert FirewallAction.ALLOW == "allow"
        assert FirewallAction.BLOCK == "block"
        assert FirewallAction.RATE_LIMIT == "rate_limit"

    def test_threat_record_defaults(self):
        r = ThreatRecord()
        assert len(r.threat_id) == 8
        assert r.threat_type == ThreatType.ANOMALY
        assert r.level == ThreatLevel.LOW
        assert r.blocked is False

    def test_access_record_defaults(self):
        r = AccessRecord()
        assert len(r.access_id) == 8
        assert r.action == AccessAction.READ
        assert r.granted is False

    def test_audit_entry_defaults(self):
        e = AuditEntry()
        assert len(e.entry_id) == 8
        assert e.event_type == AuditEventType.ACCESS
        assert e.severity == ThreatLevel.NONE

    def test_session_record_defaults(self):
        r = SessionRecord()
        assert len(r.session_id) == 8
        assert r.status == SessionStatus.ACTIVE

    def test_security_snapshot_defaults(self):
        s = SecuritySnapshot()
        assert s.total_threats == 0
        assert s.active_sessions == 0
        assert s.uptime_seconds == 0.0


# ── ThreatDetector Testleri ─────────────────────────────────


class TestThreatDetector:
    """Tehdit tespit testleri."""

    @pytest.fixture()
    def detector(self):
        return ThreatDetector(max_login_attempts=3)

    def test_init(self, detector):
        assert detector.threat_count == 0
        assert detector.pattern_count == 4

    def test_detect_sql_injection(self, detector):
        threat = detector.detect_intrusion(
            "1.2.3.4", "/api", "' OR 1=1 --",
        )
        assert threat is not None
        assert threat.threat_type == ThreatType.INJECTION
        assert threat.level == ThreatLevel.HIGH
        assert threat.blocked is True

    def test_detect_xss(self, detector):
        threat = detector.detect_intrusion(
            "1.2.3.4", "/search", "<script>alert(1)</script>",
        )
        assert threat is not None
        assert threat.threat_type == ThreatType.XSS

    def test_detect_command_injection(self, detector):
        threat = detector.detect_intrusion(
            "1.2.3.4", "/cmd", "; rm -rf /",
        )
        assert threat is not None
        assert threat.threat_type == ThreatType.INJECTION

    def test_detect_path_traversal(self, detector):
        threat = detector.detect_intrusion(
            "1.2.3.4", "/../etc/passwd", "",
        )
        assert threat is not None
        assert threat.threat_type == ThreatType.INTRUSION

    def test_no_threat(self, detector):
        threat = detector.detect_intrusion(
            "1.2.3.4", "/api/users", "normal data",
        )
        assert threat is None

    def test_anomaly_baseline_set(self, detector):
        threat = detector.detect_anomaly("cpu", 50.0)
        assert threat is None  # Ilk deger = baseline

    def test_anomaly_detection(self, detector):
        detector.set_baseline("cpu", 50.0)
        threat = detector.detect_anomaly("cpu", 150.0, 2.0)
        assert threat is not None
        assert threat.threat_type == ThreatType.ANOMALY

    def test_anomaly_normal(self, detector):
        detector.set_baseline("cpu", 50.0)
        threat = detector.detect_anomaly("cpu", 80.0, 2.0)
        assert threat is None

    def test_brute_force_below_limit(self, detector):
        threat = detector.detect_brute_force("user1", False)
        assert threat is None
        threat = detector.detect_brute_force("user1", False)
        assert threat is None

    def test_brute_force_at_limit(self, detector):
        for _ in range(3):
            threat = detector.detect_brute_force("user1", False)
        assert threat is not None
        assert threat.threat_type == ThreatType.BRUTE_FORCE
        assert threat.level == ThreatLevel.HIGH

    def test_brute_force_critical(self, detector):
        for _ in range(6):
            threat = detector.detect_brute_force("user2", False)
        assert threat is not None
        assert threat.level == ThreatLevel.CRITICAL

    def test_brute_force_reset_on_success(self, detector):
        detector.detect_brute_force("user1", False)
        detector.detect_brute_force("user1", False)
        detector.detect_brute_force("user1", True)
        assert detector.get_login_attempts("user1") == 0

    def test_ddos_detection(self, detector):
        threat = detector.detect_ddos("1.2.3.4", 200, 100)
        assert threat is not None
        assert threat.threat_type == ThreatType.DDOS

    def test_ddos_critical(self, detector):
        threat = detector.detect_ddos("1.2.3.4", 600, 100)
        assert threat is not None
        assert threat.level == ThreatLevel.CRITICAL

    def test_ddos_below_threshold(self, detector):
        threat = detector.detect_ddos("1.2.3.4", 50, 100)
        assert threat is None

    def test_add_pattern(self, detector):
        detector.add_pattern(
            "custom", ["MALWARE"], ThreatType.INTRUSION,
        )
        assert detector.pattern_count == 5
        threat = detector.detect_intrusion(
            "1.2.3.4", "/", "MALWARE detected",
        )
        assert threat is not None

    def test_get_threats_filtered(self, detector):
        detector.detect_intrusion("1.2.3.4", "/", "' OR 1=1")
        detector.detect_ddos("5.6.7.8", 200)
        threats = detector.get_threats(threat_type=ThreatType.DDOS)
        assert len(threats) == 1
        assert threats[0]["type"] == "ddos"

    def test_get_threats_by_level(self, detector):
        detector.detect_ddos("1.2.3.4", 200, 100)
        detector.detect_ddos("5.6.7.8", 600, 100)
        threats = detector.get_threats(level=ThreatLevel.CRITICAL)
        assert len(threats) == 1

    def test_blocked_count(self, detector):
        detector.detect_intrusion("1.2.3.4", "/", "' OR 1=1")
        assert detector.blocked_count == 1

    def test_reset_login_attempts(self, detector):
        detector.detect_brute_force("user1", False)
        detector.reset_login_attempts("user1")
        assert detector.get_login_attempts("user1") == 0


# ── AccessController Testleri ───────────────────────────────


class TestAccessController:
    """Erisim kontrol testleri."""

    @pytest.fixture()
    def ac(self):
        return AccessController()

    def test_init(self, ac):
        assert ac.role_count == 0
        assert ac.user_count == 0

    def test_create_role(self, ac):
        role = ac.create_role("admin", "Yonetici")
        assert role["name"] == "admin"

    def test_assign_role(self, ac):
        ac.create_role("editor")
        result = ac.assign_role("alice", "editor")
        assert result is True
        assert ac.user_count == 1

    def test_assign_nonexistent_role(self, ac):
        result = ac.assign_role("alice", "nonexistent")
        assert result is False

    def test_revoke_role(self, ac):
        ac.create_role("viewer")
        ac.assign_role("bob", "viewer")
        result = ac.revoke_role("bob", "viewer")
        assert result is True

    def test_revoke_nonexistent(self, ac):
        result = ac.revoke_role("ghost", "admin")
        assert result is False

    def test_grant_permission(self, ac):
        ac.create_role("editor")
        result = ac.grant_permission(
            "editor", "articles",
            [AccessAction.READ, AccessAction.WRITE],
        )
        assert result is True

    def test_check_access_granted(self, ac):
        ac.create_role("editor")
        ac.grant_permission(
            "editor", "articles", [AccessAction.READ],
        )
        ac.assign_role("alice", "editor")
        assert ac.check_access(
            "alice", "articles", AccessAction.READ,
        ) is True

    def test_check_access_denied(self, ac):
        ac.create_role("viewer")
        ac.grant_permission(
            "viewer", "articles", [AccessAction.READ],
        )
        ac.assign_role("bob", "viewer")
        assert ac.check_access(
            "bob", "articles", AccessAction.DELETE,
        ) is False
        assert ac.denial_count == 1

    def test_role_inheritance(self, ac):
        ac.create_role("base")
        ac.grant_permission(
            "base", "system", [AccessAction.READ],
        )
        ac.create_role("admin", parent="base")
        ac.assign_role("super", "admin")
        assert ac.check_access(
            "super", "system", AccessAction.READ,
        ) is True

    def test_get_user_roles(self, ac):
        ac.create_role("r1")
        ac.create_role("r2")
        ac.assign_role("alice", "r1")
        ac.assign_role("alice", "r2")
        roles = ac.get_user_roles("alice")
        assert len(roles) == 2

    def test_get_user_permissions(self, ac):
        ac.create_role("editor")
        ac.grant_permission(
            "editor", "docs", [AccessAction.WRITE],
        )
        ac.assign_role("alice", "editor")
        perms = ac.get_user_permissions("alice")
        assert len(perms) == 1

    def test_get_access_log(self, ac):
        ac.create_role("viewer")
        ac.assign_role("bob", "viewer")
        ac.check_access("bob", "x", AccessAction.READ)
        log = ac.get_access_log()
        assert len(log) == 1

    def test_get_access_log_filtered(self, ac):
        ac.create_role("viewer")
        ac.assign_role("alice", "viewer")
        ac.assign_role("bob", "viewer")
        ac.check_access("alice", "x", AccessAction.READ)
        ac.check_access("bob", "x", AccessAction.READ)
        log = ac.get_access_log(user="alice")
        assert len(log) == 1

    def test_duplicate_role_assign(self, ac):
        ac.create_role("editor")
        ac.assign_role("alice", "editor")
        ac.assign_role("alice", "editor")
        roles = ac.get_user_roles("alice")
        assert len(roles) == 1


# ── EncryptionManager Testleri ──────────────────────────────


class TestEncryptionManager:
    """Sifreleme testleri."""

    @pytest.fixture()
    def em(self):
        return EncryptionManager()

    def test_init(self, em):
        assert em.key_count == 0
        assert em.operation_count == 0

    def test_generate_key(self, em):
        result = em.generate_key("main", 256)
        assert result["name"] == "main"
        assert result["size"] == 256
        assert em.key_count == 1

    def test_encrypt(self, em):
        em.generate_key("k1")
        result = em.encrypt("hello", "k1")
        assert result["success"] is True
        assert "ciphertext" in result

    def test_encrypt_missing_key(self, em):
        result = em.encrypt("hello", "missing")
        assert result["success"] is False

    def test_decrypt(self, em):
        em.generate_key("k1")
        result = em.decrypt("cipher", "k1")
        assert result["success"] is True

    def test_decrypt_missing_key(self, em):
        result = em.decrypt("cipher", "missing")
        assert result["success"] is False

    def test_hash_sha256(self, em):
        h = em.hash_data("test", "sha256")
        assert len(h) == 64

    def test_hash_sha512(self, em):
        h = em.hash_data("test", "sha512")
        assert len(h) == 128

    def test_hash_md5(self, em):
        h = em.hash_data("test", "md5")
        assert len(h) == 32

    def test_hash_unknown_defaults_sha256(self, em):
        h = em.hash_data("test", "unknown")
        assert len(h) == 64

    def test_verify_hash(self, em):
        h = em.hash_data("test")
        assert em.verify_hash("test", h) is True

    def test_verify_hash_mismatch(self, em):
        assert em.verify_hash("test", "wrong") is False

    def test_generate_hmac(self, em):
        em.generate_key("k1")
        result = em.generate_hmac("data", "k1")
        assert len(result) == 64

    def test_hmac_missing_key(self, em):
        result = em.generate_hmac("data", "missing")
        assert result == ""

    def test_rotate_key(self, em):
        em.generate_key("k1")
        result = em.rotate_key("k1")
        assert result["success"] is True

    def test_rotate_missing_key(self, em):
        result = em.rotate_key("missing")
        assert result["success"] is False

    def test_deactivate_key(self, em):
        em.generate_key("k1")
        assert em.deactivate_key("k1") is True
        assert em.active_key_count == 0

    def test_deactivate_missing_key(self, em):
        assert em.deactivate_key("missing") is False

    def test_encrypt_inactive_key(self, em):
        em.generate_key("k1")
        em.deactivate_key("k1")
        result = em.encrypt("hello", "k1")
        assert result["success"] is False


# ── InputValidator Testleri ─────────────────────────────────


class TestInputValidator:
    """Girdi dogrulama testleri."""

    @pytest.fixture()
    def iv(self):
        return InputValidator()

    def test_init(self, iv):
        assert iv.rule_count == 4
        assert iv.violation_count == 0

    def test_safe_input(self, iv):
        result = iv.validate("normal text")
        assert result["safe"] is True

    def test_sql_injection(self, iv):
        result = iv.validate("' OR '1'='1")
        assert result["safe"] is False

    def test_xss_detection(self, iv):
        result = iv.validate("<script>alert(1)</script>")
        assert result["safe"] is False

    def test_command_injection(self, iv):
        result = iv.validate("data; rm -rf /")
        assert result["safe"] is False

    def test_path_traversal(self, iv):
        result = iv.validate("../../etc/passwd")
        assert result["safe"] is False

    def test_specific_checks(self, iv):
        result = iv.validate(
            "' OR 1=1", checks=["xss"],
        )
        assert result["safe"] is True  # SQL tespit edilmez

    def test_sanitize_html(self, iv):
        result = iv.sanitize("<b>test</b>")
        assert "<" not in result
        assert ">" not in result

    def test_sanitize_sql(self, iv):
        result = iv.sanitize_sql("it's a test -- comment")
        assert "''" in result
        assert "--" not in result

    def test_sanitize_path(self, iv):
        result = iv.sanitize_path("../../file.txt")
        assert ".." not in result

    def test_validate_email_valid(self, iv):
        assert iv.validate_email("user@example.com") is True

    def test_validate_email_invalid(self, iv):
        assert iv.validate_email("not-email") is False

    def test_validate_url_valid(self, iv):
        assert iv.validate_url("https://example.com") is True

    def test_validate_url_invalid(self, iv):
        assert iv.validate_url("ftp://bad") is False

    def test_add_rule(self, iv):
        iv.add_rule("custom", [r"DANGER"])
        assert iv.rule_count == 5
        result = iv.validate("DANGER zone")
        assert result["safe"] is False

    def test_disable_rule(self, iv):
        assert iv.disable_rule("sql_injection") is True
        result = iv.validate("' OR 1=1")
        assert result["safe"] is True  # Devre disi

    def test_enable_rule(self, iv):
        iv.disable_rule("sql_injection")
        iv.enable_rule("sql_injection")
        result = iv.validate("' OR '1'='1")
        assert result["safe"] is False

    def test_disable_nonexistent_rule(self, iv):
        assert iv.disable_rule("nope") is False

    def test_enable_nonexistent_rule(self, iv):
        assert iv.enable_rule("nope") is False

    def test_violation_count_tracks(self, iv):
        iv.validate("' OR 1=1")
        iv.validate("<script>x</script>")
        assert iv.violation_count == 2


# ── SecretManager Testleri ──────────────────────────────────


class TestSecretManager:
    """Gizli veri yonetimi testleri."""

    @pytest.fixture()
    def sm(self):
        return SecretManager()

    def test_init(self, sm):
        assert sm.secret_count == 0

    def test_store_secret(self, sm):
        result = sm.store_secret("api_key", "secret123")
        assert result["name"] == "api_key"
        assert sm.secret_count == 1

    def test_store_with_ttl(self, sm):
        result = sm.store_secret("temp", "val", ttl_hours=1)
        assert result["expires_at"] is not None

    def test_get_secret(self, sm):
        sm.store_secret("key", "val123")
        value = sm.get_secret("key")
        assert value == "val123"

    def test_get_nonexistent(self, sm):
        assert sm.get_secret("nope") is None

    def test_get_secret_logs_access(self, sm):
        sm.store_secret("key", "val")
        sm.get_secret("key", accessor="admin")
        assert sm.access_count == 1

    def test_rotate_secret(self, sm):
        sm.store_secret("key", "old")
        result = sm.rotate_secret("key", "new")
        assert result["success"] is True
        assert result["version"] == 2
        assert sm.get_secret("key") == "new"

    def test_rotate_nonexistent(self, sm):
        result = sm.rotate_secret("nope", "val")
        assert result["success"] is False

    def test_delete_secret(self, sm):
        sm.store_secret("key", "val")
        assert sm.delete_secret("key") is True
        assert sm.secret_count == 0

    def test_delete_nonexistent(self, sm):
        assert sm.delete_secret("nope") is False

    def test_hash_password(self, sm):
        h = sm.hash_password("alice", "pass123")
        assert len(h) > 0
        assert sm.password_count == 1

    def test_verify_password_correct(self, sm):
        sm.hash_password("alice", "pass123")
        assert sm.verify_password("alice", "pass123") is True

    def test_verify_password_wrong(self, sm):
        sm.hash_password("alice", "pass123")
        assert sm.verify_password("alice", "wrong") is False

    def test_verify_nonexistent_user(self, sm):
        assert sm.verify_password("ghost", "pass") is False

    def test_list_secrets(self, sm):
        sm.store_secret("a", "1")
        sm.store_secret("b", "2")
        lst = sm.list_secrets()
        assert len(lst) == 2
        assert "value" not in lst[0]  # Deger gizli

    def test_cleanup_expired(self, sm):
        sm.store_secret("temp", "val", ttl_hours=0)
        # ttl=0 = sinirsiz, temizlenmemeli
        cleaned = sm.cleanup_expired()
        assert cleaned == 0

    def test_store_with_metadata(self, sm):
        sm.store_secret("k", "v", metadata={"env": "prod"})
        lst = sm.list_secrets()
        assert lst[0]["has_metadata"] is True


# ── SessionGuardian Testleri ────────────────────────────────


class TestSessionGuardian:
    """Oturum yonetimi testleri."""

    @pytest.fixture()
    def sg(self):
        return SessionGuardian(
            session_timeout=30, max_concurrent=2,
        )

    def test_init(self, sg):
        assert sg.active_count == 0
        assert sg.total_count == 0

    def test_create_session(self, sg):
        result = sg.create_session("alice", "1.2.3.4")
        assert "session_id" in result
        assert "token" in result
        assert sg.active_count == 1

    def test_validate_token(self, sg):
        result = sg.create_session("alice", "1.2.3.4")
        validation = sg.validate_token(result["token"], "1.2.3.4")
        assert validation["valid"] is True
        assert validation["user"] == "alice"

    def test_validate_invalid_token(self, sg):
        result = sg.validate_token("bad_token")
        assert result["valid"] is False

    def test_ip_hijacking_detection(self, sg):
        result = sg.create_session("alice", "1.2.3.4")
        validation = sg.validate_token(result["token"], "5.6.7.8")
        assert validation["valid"] is False
        assert validation.get("hijacking_suspected") is True

    def test_revoke_session(self, sg):
        result = sg.create_session("alice")
        assert sg.revoke_session(result["session_id"]) is True
        assert sg.revoked_count == 1

    def test_revoke_nonexistent(self, sg):
        assert sg.revoke_session("fake") is False

    def test_revoke_user_sessions(self, sg):
        sg.create_session("alice")
        sg.create_session("alice")
        count = sg.revoke_user_sessions("alice")
        assert count == 2

    def test_extend_session(self, sg):
        result = sg.create_session("alice")
        assert sg.extend_session(result["session_id"]) is True

    def test_extend_nonexistent(self, sg):
        assert sg.extend_session("fake") is False

    def test_concurrent_limit(self, sg):
        sg.create_session("alice")
        sg.create_session("alice")
        sg.create_session("alice")  # 3. oturum, limit=2
        # En eski iptal edilmeli
        assert sg.active_count == 2

    def test_get_user_sessions(self, sg):
        sg.create_session("alice")
        sg.create_session("bob")
        sessions = sg.get_user_sessions("alice")
        assert len(sessions) == 1

    def test_cleanup_expired(self, sg):
        sg_short = SessionGuardian(session_timeout=1)
        result = sg_short.create_session("alice")
        # Oturumu elle surdur
        session = sg_short._sessions[result["session_id"]]
        from datetime import timedelta
        session.expires_at = session.created_at - timedelta(minutes=1)
        cleaned = sg_short.cleanup_expired()
        assert cleaned == 1

    def test_validate_revoked_token(self, sg):
        result = sg.create_session("alice")
        sg.revoke_session(result["session_id"])
        validation = sg.validate_token(result["token"])
        assert validation["valid"] is False


# ── Firewall Testleri ───────────────────────────────────────


class TestFirewall:
    """Guvenlik duvari testleri."""

    @pytest.fixture()
    def fw(self):
        return Firewall()

    def test_init(self, fw):
        assert fw.whitelist_count == 0
        assert fw.blacklist_count == 0

    def test_add_whitelist(self, fw):
        fw.add_to_whitelist("1.2.3.4")
        assert fw.whitelist_count == 1

    def test_add_blacklist(self, fw):
        fw.add_to_blacklist("1.2.3.4")
        assert fw.blacklist_count == 1

    def test_whitelist_removes_from_blacklist(self, fw):
        fw.add_to_blacklist("1.2.3.4")
        fw.add_to_whitelist("1.2.3.4")
        assert fw.blacklist_count == 0
        assert fw.whitelist_count == 1

    def test_blacklist_removes_from_whitelist(self, fw):
        fw.add_to_whitelist("1.2.3.4")
        fw.add_to_blacklist("1.2.3.4")
        assert fw.whitelist_count == 0
        assert fw.blacklist_count == 1

    def test_check_whitelist_allows(self, fw):
        fw.add_to_whitelist("1.2.3.4")
        result = fw.check_request("1.2.3.4")
        assert result["action"] == "allow"
        assert result["reason"] == "whitelist"

    def test_check_blacklist_blocks(self, fw):
        fw.add_to_blacklist("1.2.3.4")
        result = fw.check_request("1.2.3.4")
        assert result["action"] == "block"

    def test_check_default_allow(self, fw):
        result = fw.check_request("1.2.3.4")
        assert result["action"] == "allow"
        assert result["reason"] == "default_allow"

    def test_geo_block(self, fw):
        fw.block_country("CN")
        result = fw.check_request("1.2.3.4", country="CN")
        assert result["action"] == "block"

    def test_unblock_country(self, fw):
        fw.block_country("CN")
        assert fw.unblock_country("CN") is True
        result = fw.check_request("1.2.3.4", country="CN")
        assert result["action"] == "allow"

    def test_unblock_nonexistent_country(self, fw):
        assert fw.unblock_country("XX") is False

    def test_rate_limit(self, fw):
        fw.set_rate_limit("1.2.3.4", 2)
        fw.check_request("1.2.3.4")  # count -> 1
        fw.check_request("1.2.3.4")  # count -> 2
        result = fw.check_request("1.2.3.4")  # rate limited
        assert result["action"] == "rate_limit"

    def test_global_rate_limit(self, fw):
        fw.set_global_rate_limit(1)
        fw.check_request("1.2.3.4")  # count -> 1
        result = fw.check_request("1.2.3.4")
        assert result["action"] == "rate_limit"

    def test_add_rule_block(self, fw):
        fw.add_rule("block_admin", FirewallAction.BLOCK, "/admin")
        result = fw.check_request("1.2.3.4", "/admin/panel")
        assert result["action"] == "block"

    def test_add_rule_ip_pattern(self, fw):
        fw.add_rule(
            "block_range", FirewallAction.BLOCK,
            ip_pattern="10.0.",
        )
        result = fw.check_request("10.0.1.1", "/")
        assert result["action"] == "block"

    def test_remove_from_whitelist(self, fw):
        fw.add_to_whitelist("1.2.3.4")
        assert fw.remove_from_whitelist("1.2.3.4") is True
        assert fw.whitelist_count == 0

    def test_remove_from_whitelist_nonexistent(self, fw):
        assert fw.remove_from_whitelist("1.2.3.4") is False

    def test_remove_from_blacklist(self, fw):
        fw.add_to_blacklist("1.2.3.4")
        assert fw.remove_from_blacklist("1.2.3.4") is True

    def test_remove_from_blacklist_nonexistent(self, fw):
        assert fw.remove_from_blacklist("1.2.3.4") is False

    def test_blocked_requests_log(self, fw):
        fw.add_to_blacklist("1.2.3.4")
        fw.check_request("1.2.3.4", "/test")
        blocked = fw.get_blocked_requests()
        assert len(blocked) == 1
        assert blocked[0]["ip"] == "1.2.3.4"

    def test_reset_counters(self, fw):
        fw.set_global_rate_limit(100)
        fw.check_request("1.2.3.4")
        fw.reset_counters()
        # Rate limit sifirlanmis, tekrar izin vermeli
        result = fw.check_request("1.2.3.4")
        assert result["action"] == "allow"

    def test_geo_block_count(self, fw):
        fw.block_country("CN")
        fw.block_country("RU")
        assert fw.geo_block_count == 2


# ── AuditLogger Testleri ────────────────────────────────────


class TestAuditLogger:
    """Denetim gunlugu testleri."""

    @pytest.fixture()
    def al(self):
        return AuditLogger(retention_days=30)

    def test_init(self, al):
        assert al.entry_count == 0
        assert al.retention_days == 30

    def test_log_event(self, al):
        entry = al.log_event(
            AuditEventType.ACCESS, "alice", "read", "docs",
        )
        assert entry.actor == "alice"
        assert al.entry_count == 1

    def test_log_login_success(self, al):
        entry = al.log_login("alice", True, "1.2.3.4")
        assert entry.event_type == AuditEventType.LOGIN
        assert entry.action == "login_success"

    def test_log_login_failure(self, al):
        entry = al.log_login("alice", False)
        assert entry.action == "login_failure"
        assert entry.severity == ThreatLevel.LOW

    def test_log_access_granted(self, al):
        entry = al.log_access("alice", "docs", "read", True)
        assert entry.severity == ThreatLevel.NONE

    def test_log_access_denied(self, al):
        entry = al.log_access("alice", "admin", "write", False)
        assert entry.severity == ThreatLevel.MEDIUM

    def test_log_change(self, al):
        entry = al.log_change("admin", "config", "old", "new")
        assert entry.event_type == AuditEventType.CHANGE
        assert entry.details["old_value"] == "old"

    def test_log_threat(self, al):
        entry = al.log_threat(
            "1.2.3.4", "injection",
            severity=ThreatLevel.HIGH,
        )
        assert entry.event_type == AuditEventType.THREAT

    def test_high_severity_creates_alert(self, al):
        al.log_event(
            AuditEventType.THREAT, "attacker", "intrusion",
            severity=ThreatLevel.HIGH,
        )
        assert al.alert_count == 1

    def test_critical_severity_creates_alert(self, al):
        al.log_event(
            AuditEventType.THREAT, "attacker", "ddos",
            severity=ThreatLevel.CRITICAL,
        )
        assert al.alert_count == 1

    def test_low_severity_no_alert(self, al):
        al.log_event(
            AuditEventType.LOGIN, "user", "login_failure",
            severity=ThreatLevel.LOW,
        )
        assert al.alert_count == 0

    def test_get_entries(self, al):
        al.log_login("alice", True)
        al.log_login("bob", False)
        entries = al.get_entries()
        assert len(entries) == 2

    def test_get_entries_by_type(self, al):
        al.log_login("alice", True)
        al.log_access("bob", "x", "read", True)
        entries = al.get_entries(event_type=AuditEventType.LOGIN)
        assert len(entries) == 1

    def test_get_entries_by_actor(self, al):
        al.log_login("alice", True)
        al.log_login("bob", True)
        entries = al.get_entries(actor="alice")
        assert len(entries) == 1

    def test_get_entries_by_severity(self, al):
        al.log_login("alice", True)  # NONE
        al.log_login("bob", False)   # LOW
        entries = al.get_entries(severity=ThreatLevel.LOW)
        assert len(entries) == 1

    def test_compliance_report(self, al):
        al.log_login("alice", True)
        al.log_login("bob", False)
        al.log_access("alice", "x", "read", False)
        report = al.get_compliance_report()
        assert report["total_entries"] == 3
        assert report["failed_logins"] == 1
        assert report["access_denials"] == 1

    def test_forensic_timeline(self, al):
        al.log_login("alice", True)
        al.log_access("alice", "docs", "read", True)
        timeline = al.get_forensic_timeline(actor="alice")
        assert len(timeline) == 2

    def test_forensic_timeline_by_resource(self, al):
        al.log_access("alice", "docs", "read", True)
        al.log_access("bob", "admin", "read", True)
        timeline = al.get_forensic_timeline(resource="docs")
        assert len(timeline) == 1

    def test_retention_days_minimum(self):
        al = AuditLogger(retention_days=0)
        assert al.retention_days == 1


# ── SecurityOrchestrator Testleri ───────────────────────────


class TestSecurityOrchestrator:
    """Guvenlik orkestratoru testleri."""

    @pytest.fixture()
    def so(self):
        return SecurityOrchestrator(
            session_timeout=30,
            max_login_attempts=3,
            audit_retention_days=30,
        )

    def test_init(self, so):
        assert so.incident_count == 0
        assert so.policy_count == 0

    def test_process_request_clean(self, so):
        result = so.process_request("1.2.3.4", "/api")
        assert result["allowed"] is True
        assert result["reason"] == "all_checks_passed"

    def test_process_request_blacklisted(self, so):
        so.firewall.add_to_blacklist("1.2.3.4")
        result = so.process_request("1.2.3.4", "/api")
        assert result["allowed"] is False
        assert "firewall" in result["reason"]

    def test_process_request_rate_limited(self, so):
        so.firewall.set_rate_limit("1.2.3.4", 1)
        so.firewall.check_request("1.2.3.4")  # count to 1
        result = so.process_request("1.2.3.4", "/api")
        assert result["allowed"] is False
        assert result["reason"] == "rate_limited"

    def test_process_request_input_violation(self, so):
        result = so.process_request(
            "1.2.3.4", "/api",
            payload="<script>alert(1)</script>",
        )
        assert result["allowed"] is False
        assert result["reason"] == "input_validation_failed"

    def test_process_request_threat_detected(self, so):
        result = so.process_request(
            "1.2.3.4", "/api",
            payload="' OR 1=1 --",
        )
        assert result["allowed"] is False
        # Input validator catches it first or threat detector
        assert not result["allowed"]

    def test_authenticate_user_success(self, so):
        so.secrets.hash_password("alice", "pass123")
        result = so.authenticate_user("alice", "pass123", "1.2.3.4")
        assert result["authenticated"] is True
        assert "token" in result

    def test_authenticate_user_failure(self, so):
        so.secrets.hash_password("alice", "pass123")
        result = so.authenticate_user("alice", "wrong")
        assert result["authenticated"] is False

    def test_authenticate_brute_force(self, so):
        so.secrets.hash_password("alice", "pass123")
        for _ in range(3):
            so.authenticate_user("alice", "wrong", "1.2.3.4")
        result = so.authenticate_user("alice", "wrong", "1.2.3.4")
        assert result["authenticated"] is False
        assert result["reason"] == "brute_force_detected"

    def test_check_authorization(self, so):
        so.access_controller.create_role("admin")
        so.access_controller.grant_permission(
            "admin", "system", [AccessAction.ADMIN],
        )
        so.access_controller.assign_role("alice", "admin")
        assert so.check_authorization(
            "alice", "system", AccessAction.ADMIN,
        ) is True

    def test_check_authorization_denied(self, so):
        so.access_controller.create_role("viewer")
        so.access_controller.assign_role("bob", "viewer")
        assert so.check_authorization(
            "bob", "admin_panel", AccessAction.ADMIN,
        ) is False

    def test_add_security_policy(self, so):
        policy = so.add_security_policy(
            "password_policy",
            {"min_length": 8, "require_special": True},
        )
        assert policy["name"] == "password_policy"
        assert so.policy_count == 1

    def test_respond_to_threat_high(self, so):
        result = so.respond_to_threat(
            ThreatType.INJECTION, "1.2.3.4",
            ThreatLevel.HIGH,
        )
        assert "ip_blacklisted" in result["actions_taken"]
        assert so.incident_count == 1

    def test_respond_to_threat_brute_force(self, so):
        # Simulate some attempts first
        so.threat_detector.detect_brute_force("attacker", False)
        result = so.respond_to_threat(
            ThreatType.BRUTE_FORCE, "attacker",
            ThreatLevel.HIGH,
        )
        assert "attempts_reset" in result["actions_taken"]

    def test_respond_to_threat_low(self, so):
        result = so.respond_to_threat(
            ThreatType.ANOMALY, "metric",
            ThreatLevel.LOW,
        )
        # Low severity: IP engellenmemeli
        assert "ip_blacklisted" not in result["actions_taken"]
        assert "audit_logged" in result["actions_taken"]

    def test_security_snapshot(self, so):
        snapshot = so.get_security_snapshot()
        assert isinstance(snapshot, SecuritySnapshot)
        assert snapshot.uptime_seconds >= 0

    def test_snapshot_after_activity(self, so):
        so.secrets.hash_password("alice", "pass123")
        so.authenticate_user("alice", "pass123")
        so.secrets.store_secret("key", "value")
        snapshot = so.get_security_snapshot()
        assert snapshot.active_sessions >= 1
        assert snapshot.secrets_managed >= 1
        assert snapshot.audit_entries >= 1

    def test_process_request_with_token(self, so):
        so.secrets.hash_password("alice", "pass123")
        auth = so.authenticate_user("alice", "pass123", "1.2.3.4")
        result = so.process_request(
            "1.2.3.4", "/api",
            token=auth["token"],
        )
        assert result["allowed"] is True

    def test_process_request_invalid_token(self, so):
        result = so.process_request(
            "1.2.3.4", "/api",
            token="invalid_token",
        )
        assert result["allowed"] is False
        assert "session" in result["reason"]

    def test_incident_creation(self, so):
        so.respond_to_threat(
            ThreatType.DDOS, "1.2.3.4",
            ThreatLevel.CRITICAL,
        )
        assert so.incident_count == 1


# ── Entegrasyon Testleri ────────────────────────────────────


class TestSecurityIntegration:
    """Entegrasyon testleri."""

    def test_full_security_pipeline(self):
        so = SecurityOrchestrator()
        # Kullanici olustur
        so.secrets.hash_password("alice", "secure123")
        so.access_controller.create_role("user")
        so.access_controller.grant_permission(
            "user", "data", [AccessAction.READ],
        )
        so.access_controller.assign_role("alice", "user")

        # Dogrulama
        auth = so.authenticate_user("alice", "secure123", "1.2.3.4")
        assert auth["authenticated"] is True

        # Yetkilendirme
        assert so.check_authorization(
            "alice", "data", AccessAction.READ,
        ) is True

        # Istek isleme
        result = so.process_request(
            "1.2.3.4", "/data",
            token=auth["token"],
        )
        assert result["allowed"] is True

    def test_attack_sequence(self):
        so = SecurityOrchestrator(max_login_attempts=3)
        so.secrets.hash_password("admin", "pass123")

        # Saldiri: yanlis parola
        for _ in range(3):
            so.authenticate_user("admin", "wrong", "10.0.0.1")

        # Brute force engelleme
        result = so.authenticate_user("admin", "wrong", "10.0.0.1")
        assert result["authenticated"] is False

        # IP kara listede
        fw_result = so.firewall.check_request("10.0.0.1")
        assert fw_result["action"] == "block"

    def test_threat_response_and_audit(self):
        so = SecurityOrchestrator()
        so.respond_to_threat(
            ThreatType.INJECTION, "attacker_ip",
            ThreatLevel.HIGH,
        )
        # Denetim kaydinda olmali
        entries = so.audit.get_entries(
            event_type=AuditEventType.THREAT,
        )
        assert len(entries) >= 1

    def test_snapshot_reflects_state(self):
        so = SecurityOrchestrator()
        so.firewall.add_to_blacklist("1.2.3.4")
        so.firewall.check_request("1.2.3.4")
        so.encryption.generate_key("main")
        so.encryption.encrypt("data", "main")
        snapshot = so.get_security_snapshot()
        assert snapshot.firewall_blocks >= 1
        assert snapshot.encryption_operations >= 2  # gen + encrypt

    def test_all_components_accessible(self):
        so = SecurityOrchestrator()
        assert so.threat_detector is not None
        assert so.access_controller is not None
        assert so.encryption is not None
        assert so.validator is not None
        assert so.secrets is not None
        assert so.sessions is not None
        assert so.firewall is not None
        assert so.audit is not None
