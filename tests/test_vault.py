"""Vault & Secret Manager testleri."""

import hashlib

import pytest

from app.core.vault.access_token_manager import (
    AccessTokenManager,
)
from app.core.vault.emergency_revocation import (
    EmergencyRevocation,
)
from app.core.vault.encrypted_vault import (
    EncryptedVault,
)
from app.core.vault.key_rotation_engine import (
    KeyRotationEngine,
)
from app.core.vault.secret_leak_scanner import (
    SecretLeakScanner,
)
from app.core.vault.secret_versioning import (
    SecretVersioning,
)
from app.core.vault.vault_audit_log import (
    VaultAuditLog,
)
from app.core.vault.vault_orchestrator import (
    VaultOrchestrator,
)
from app.core.vault.zero_knowledge_access import (
    ZeroKnowledgeAccess,
)
from app.models.vault_models import (
    AuditAction,
    AuditEntry,
    EncryptionAlgorithm,
    KeyRecord,
    RevocationRecord,
    RevocationStatus,
    ScanResult,
    ScanSeverity,
    SecretCategory,
    SecretRecord,
    TokenRecord,
    TokenScope,
)


# ============================================================
# EncryptedVault Tests
# ============================================================
class TestEncryptedVault:
    """EncryptedVault testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.vault = EncryptedVault()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.vault.secret_count == 0

    def test_store_secret(self) -> None:
        """Gizli bilgi depolama."""
        r = self.vault.store_secret(
            name="db_pass",
            value="secret123",
            category="database",
            owner="user1",
        )
        assert r["stored"] is True
        assert "secret_id" in r
        assert self.vault.secret_count == 1

    def test_store_overwrites(self) -> None:
        """Tekrar depolama (uzerine yazar)."""
        self.vault.store_secret(
            name="key1", value="v1", owner="u1"
        )
        r = self.vault.store_secret(
            name="key1", value="v2", owner="u1"
        )
        assert r["stored"] is True
        assert self.vault.secret_count == 1

    def test_retrieve_secret_owner(self) -> None:
        """Sahip erisimi."""
        self.vault.store_secret(
            name="key1",
            value="val1",
            owner="user1",
        )
        r = self.vault.retrieve_secret(
            name="key1", user_id="user1"
        )
        assert r["retrieved"] is True
        assert "encrypted_value" in r

    def test_retrieve_secret_allowed(self) -> None:
        """Izinli kullanici erisimi."""
        self.vault.store_secret(
            name="key1",
            value="val1",
            owner="user1",
            allowed_users=["user2"],
        )
        r = self.vault.retrieve_secret(
            name="key1", user_id="user2"
        )
        assert r["retrieved"] is True

    def test_retrieve_secret_denied(self) -> None:
        """Yetkisiz erisim."""
        self.vault.store_secret(
            name="key1",
            value="val1",
            owner="user1",
        )
        r = self.vault.retrieve_secret(
            name="key1", user_id="user3"
        )
        assert r["retrieved"] is False

    def test_retrieve_nonexistent(self) -> None:
        """Olmayan gizli bilgi."""
        r = self.vault.retrieve_secret(
            name="nope", user_id="u1"
        )
        assert r["retrieved"] is True
        assert r["found"] is False

    def test_update_secret(self) -> None:
        """Guncelleme."""
        self.vault.store_secret(
            name="key1",
            value="old",
            owner="user1",
        )
        r = self.vault.update_secret(
            name="key1",
            value="new",
            user_id="user1",
        )
        assert r["updated"] is True

    def test_update_not_owner(self) -> None:
        """Sahip olmayan guncelleme."""
        self.vault.store_secret(
            name="key1",
            value="old",
            owner="user1",
        )
        r = self.vault.update_secret(
            name="key1",
            value="new",
            user_id="user2",
        )
        assert r["updated"] is False

    def test_delete_secret(self) -> None:
        """Silme."""
        self.vault.store_secret(
            name="key1",
            value="val",
            owner="user1",
        )
        r = self.vault.delete_secret(
            name="key1", user_id="user1"
        )
        assert r["deleted"] is True

    def test_delete_not_owner(self) -> None:
        """Sahip olmayan silme."""
        self.vault.store_secret(
            name="key1",
            value="val",
            owner="user1",
        )
        r = self.vault.delete_secret(
            name="key1", user_id="user2"
        )
        assert r["deleted"] is False

    def test_list_secrets(self) -> None:
        """Listeleme."""
        self.vault.store_secret(
            name="k1",
            value="v1",
            category="db",
            owner="u1",
        )
        self.vault.store_secret(
            name="k2",
            value="v2",
            category="api",
            owner="u1",
        )
        r = self.vault.list_secrets()
        assert r["listed"] is True
        assert r["count"] == 2

    def test_list_by_category(self) -> None:
        """Kategoriye gore listeleme."""
        self.vault.store_secret(
            name="k1",
            value="v1",
            category="db",
            owner="u1",
        )
        self.vault.store_secret(
            name="k2",
            value="v2",
            category="api",
            owner="u1",
        )
        r = self.vault.list_secrets(category="db")
        assert r["count"] == 1

    def test_list_by_owner(self) -> None:
        """Sahibe gore listeleme."""
        self.vault.store_secret(
            name="k1",
            value="v1",
            owner="u1",
        )
        self.vault.store_secret(
            name="k2",
            value="v2",
            owner="u2",
        )
        r = self.vault.list_secrets(owner="u1")
        assert r["count"] == 1

    def test_create_backup(self) -> None:
        """Yedekleme."""
        self.vault.store_secret(
            name="k1",
            value="v1",
            owner="u1",
        )
        r = self.vault.create_backup()
        assert r["created"] is True
        assert r["secret_count"] == 1


# ============================================================
# KeyRotationEngine Tests
# ============================================================
class TestKeyRotationEngine:
    """KeyRotationEngine testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.engine = KeyRotationEngine()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.engine.key_count == 0

    def test_create_key(self) -> None:
        """Anahtar olusturma."""
        r = self.engine.create_key(
            key_name="main_key",
            algorithm="aes256",
            rotation_days=90,
            owner="admin",
        )
        assert r["created"] is True
        assert "key_id" in r
        assert self.engine.key_count == 1

    def test_create_overwrites_key(self) -> None:
        """Tekrar olusturma (uzerine yazar)."""
        self.engine.create_key(
            key_name="k1", owner="admin"
        )
        r = self.engine.create_key(
            key_name="k1", owner="admin2"
        )
        assert r["created"] is True
        assert self.engine.key_count == 1

    def test_rotate_key(self) -> None:
        """Anahtar rotasyonu."""
        self.engine.create_key(
            key_name="k1", owner="admin"
        )
        r = self.engine.rotate_key(
            key_name="k1",
            reason="scheduled",
        )
        assert r["rotated"] is True
        assert r["new_version"] == 2

    def test_rotate_nonexistent(self) -> None:
        """Olmayan anahtar rotasyonu."""
        r = self.engine.rotate_key(
            key_name="nope"
        )
        assert r["rotated"] is False

    def test_schedule_rotation(self) -> None:
        """Rotasyon zamanlama."""
        self.engine.create_key(
            key_name="k1", owner="admin"
        )
        r = self.engine.schedule_rotation(
            key_name="k1",
            rotation_days=30,
            auto_rotate=True,
        )
        assert r["scheduled"] is True

    def test_get_key_info(self) -> None:
        """Anahtar bilgisi."""
        self.engine.create_key(
            key_name="k1",
            algorithm="rsa",
            owner="admin",
        )
        r = self.engine.get_key_info(
            key_name="k1"
        )
        assert r["retrieved"] is True
        assert r["found"] is True
        assert r["algorithm"] == "rsa"

    def test_get_key_info_not_found(self) -> None:
        """Olmayan anahtar bilgisi."""
        r = self.engine.get_key_info(
            key_name="nope"
        )
        assert r["retrieved"] is True
        assert r["found"] is False

    def test_version_history(self) -> None:
        """Surum gecmisi."""
        self.engine.create_key(
            key_name="k1", owner="admin"
        )
        self.engine.rotate_key(key_name="k1")
        self.engine.rotate_key(key_name="k1")
        r = self.engine.get_version_history(
            key_name="k1"
        )
        assert r["retrieved"] is True
        assert r["total"] == 3

    def test_rollback_key(self) -> None:
        """Anahtar geri alma."""
        self.engine.create_key(
            key_name="k1", owner="admin"
        )
        self.engine.rotate_key(key_name="k1")
        r = self.engine.rollback_key(
            key_name="k1", target_version=1
        )
        assert r["rolled_back"] is True

    def test_check_rotation_due(self) -> None:
        """Rotasyon kontrolu."""
        self.engine.create_key(
            key_name="k1",
            rotation_days=0,
            owner="admin",
        )
        self.engine.schedule_rotation(
            key_name="k1", rotation_days=0
        )
        r = self.engine.check_rotation_due()
        assert r["checked"] is True


# ============================================================
# AccessTokenManager Tests
# ============================================================
class TestAccessTokenManager:
    """AccessTokenManager testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.mgr = AccessTokenManager()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.mgr.token_count == 0

    def test_generate_token(self) -> None:
        """Token uretme."""
        r = self.mgr.generate_token(
            user_id="user1",
            scopes=["read", "write"],
            ttl_hours=24,
        )
        assert r["generated"] is True
        assert "token_id" in r
        assert "token_value" in r
        assert self.mgr.token_count == 1

    def test_validate_token(self) -> None:
        """Token dogrulama."""
        gen = self.mgr.generate_token(
            user_id="u1", scopes=["read"]
        )
        r = self.mgr.validate_token(
            token_id=gen["token_id"],
            required_scope="read",
        )
        assert r["valid"] is True

    def test_validate_wrong_scope(self) -> None:
        """Yanlis kapsam."""
        gen = self.mgr.generate_token(
            user_id="u1", scopes=["read"]
        )
        r = self.mgr.validate_token(
            token_id=gen["token_id"],
            required_scope="admin",
        )
        assert r["valid"] is False

    def test_validate_nonexistent(self) -> None:
        """Olmayan token."""
        r = self.mgr.validate_token(
            token_id="fake"
        )
        assert r["valid"] is False

    def test_revoke_token(self) -> None:
        """Token iptal."""
        gen = self.mgr.generate_token(
            user_id="u1", scopes=["read"]
        )
        r = self.mgr.revoke_token(
            token_id=gen["token_id"],
            reason="test",
        )
        assert r["revoked"] is True

    def test_validate_revoked(self) -> None:
        """Iptal edilmis token dogrulama."""
        gen = self.mgr.generate_token(
            user_id="u1", scopes=["read"]
        )
        self.mgr.revoke_token(
            token_id=gen["token_id"]
        )
        r = self.mgr.validate_token(
            token_id=gen["token_id"]
        )
        assert r["valid"] is False

    def test_revoke_user_tokens(self) -> None:
        """Kullanici tokenlarini iptal."""
        self.mgr.generate_token(
            user_id="u1", scopes=["read"]
        )
        self.mgr.generate_token(
            user_id="u1", scopes=["write"]
        )
        r = self.mgr.revoke_user_tokens(
            user_id="u1", reason="security"
        )
        assert r["revoked"] is True
        assert r["revoked_count"] == 2

    def test_update_scopes(self) -> None:
        """Kapsam guncelleme."""
        gen = self.mgr.generate_token(
            user_id="u1", scopes=["read"]
        )
        r = self.mgr.update_scopes(
            token_id=gen["token_id"],
            scopes=["read", "write", "admin"],
        )
        assert r["updated"] is True

    def test_get_usage_stats(self) -> None:
        """Kullanim istatistikleri."""
        gen = self.mgr.generate_token(
            user_id="u1", scopes=["read"]
        )
        self.mgr.validate_token(
            token_id=gen["token_id"]
        )
        r = self.mgr.get_usage_stats(
            token_id=gen["token_id"]
        )
        assert r["retrieved"] is True
        assert r["usage_count"] == 1

    def test_list_active_tokens(self) -> None:
        """Aktif token listeleme."""
        self.mgr.generate_token(
            user_id="u1", scopes=["read"]
        )
        self.mgr.generate_token(
            user_id="u1", scopes=["write"]
        )
        r = self.mgr.list_active_tokens(
            user_id="u1"
        )
        assert r["listed"] is True
        assert r["count"] == 2


# ============================================================
# SecretVersioning Tests
# ============================================================
class TestSecretVersioning:
    """SecretVersioning testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.ver = SecretVersioning()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.ver.secret_count == 0

    def test_create_version(self) -> None:
        """Surum olusturma."""
        r = self.ver.create_version(
            secret_name="db_pass",
            value_hash="hash1",
            author="admin",
            change_note="initial",
        )
        assert r["created"] is True
        assert r["version"] == 1
        assert self.ver.secret_count == 1

    def test_multiple_versions(self) -> None:
        """Coklu surum."""
        self.ver.create_version(
            secret_name="key1",
            value_hash="h1",
            author="admin",
        )
        r = self.ver.create_version(
            secret_name="key1",
            value_hash="h2",
            author="admin",
        )
        assert r["version"] == 2

    def test_get_history(self) -> None:
        """Gecmis getirme."""
        self.ver.create_version(
            secret_name="key1",
            value_hash="h1",
            author="a1",
        )
        self.ver.create_version(
            secret_name="key1",
            value_hash="h2",
            author="a2",
        )
        r = self.ver.get_history(
            secret_name="key1"
        )
        assert r["retrieved"] is True
        assert r["total_versions"] == 2

    def test_get_history_empty(self) -> None:
        """Bos gecmis."""
        r = self.ver.get_history(
            secret_name="nope"
        )
        assert r["retrieved"] is True
        assert r["history"] == []

    def test_get_diff(self) -> None:
        """Fark gosterme."""
        self.ver.create_version(
            secret_name="key1",
            value_hash="h1",
            author="a1",
        )
        self.ver.create_version(
            secret_name="key1",
            value_hash="h2",
            author="a2",
        )
        r = self.ver.get_diff(
            secret_name="key1",
            version_a=1,
            version_b=2,
        )
        assert r["retrieved"] is True
        assert r["identical"] is False

    def test_get_diff_identical(self) -> None:
        """Ayni fark."""
        self.ver.create_version(
            secret_name="key1",
            value_hash="same",
            author="a1",
        )
        self.ver.create_version(
            secret_name="key1",
            value_hash="same",
            author="a2",
        )
        r = self.ver.get_diff(
            secret_name="key1",
            version_a=1,
            version_b=2,
        )
        assert r["identical"] is True

    def test_rollback(self) -> None:
        """Geri alma."""
        self.ver.create_version(
            secret_name="key1",
            value_hash="h1",
            author="a1",
        )
        self.ver.create_version(
            secret_name="key1",
            value_hash="h2",
            author="a2",
        )
        r = self.ver.rollback(
            secret_name="key1",
            target_version=1,
        )
        assert r["rolled_back"] is True
        assert r["to_version"] == 1

    def test_rollback_not_found(self) -> None:
        """Olmayan surum geri alma."""
        self.ver.create_version(
            secret_name="key1",
            value_hash="h1",
            author="a1",
        )
        r = self.ver.rollback(
            secret_name="key1",
            target_version=99,
        )
        assert r["rolled_back"] is False

    def test_set_retention_policy(self) -> None:
        """Saklama politikasi."""
        r = self.ver.set_retention_policy(
            secret_name="key1",
            max_versions=5,
            min_age_days=7,
        )
        assert r["set"] is True
        assert r["max_versions"] == 5

    def test_apply_retention(self) -> None:
        """Saklama uygulama."""
        for i in range(5):
            self.ver.create_version(
                secret_name="key1",
                value_hash=f"h{i}",
                author="admin",
            )
        self.ver.set_retention_policy(
            secret_name="key1",
            max_versions=2,
        )
        r = self.ver.apply_retention(
            secret_name="key1"
        )
        assert r["applied"] is True
        assert r["purged"] == 3
        assert r["remaining"] == 2

    def test_apply_retention_no_policy(
        self,
    ) -> None:
        """Politikasiz uygulama."""
        r = self.ver.apply_retention(
            secret_name="key1"
        )
        assert r["applied"] is False


# ============================================================
# SecretLeakScanner Tests
# ============================================================
class TestSecretLeakScanner:
    """SecretLeakScanner testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.scanner = SecretLeakScanner()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.scanner.scan_count == 0

    def test_scan_clean_content(self) -> None:
        """Temiz icerik tarama."""
        r = self.scanner.scan_content(
            content="hello world",
            source="test.py",
        )
        assert r["scanned"] is True
        assert r["leak_detected"] is False

    def test_scan_with_api_key(self) -> None:
        """API key tarama."""
        r = self.scanner.scan_content(
            content=(
                'api_key = "abcdefghijklmnopqrst'
                'uvwxyz1234"'
            ),
            source="config.py",
        )
        assert r["scanned"] is True
        assert r["leak_detected"] is True
        assert len(r["findings"]) > 0

    def test_scan_with_password(self) -> None:
        """Sifre tarama."""
        r = self.scanner.scan_content(
            content=(
                'password = "SuperSecret123!"'
            ),
            source="settings.py",
        )
        assert r["scanned"] is True
        assert r["leak_detected"] is True

    def test_scan_with_private_key(self) -> None:
        """Ozel anahtar tarama."""
        r = self.scanner.scan_content(
            content=(
                "-----BEGIN PRIVATE KEY-----\n"
                "MIIEvQIBADANBg..."
            ),
            source="cert.pem",
        )
        assert r["leak_detected"] is True

    def test_scan_with_connection_string(
        self,
    ) -> None:
        """Baglanti dizesi tarama."""
        r = self.scanner.scan_content(
            content=(
                "postgres://user:pass"
                "@localhost/db"
            ),
            source="db.py",
        )
        assert r["leak_detected"] is True

    def test_scan_log(self) -> None:
        """Log tarama."""
        r = self.scanner.scan_log(
            log_content="normal log entry",
            log_source="app.log",
        )
        assert r["scanned"] is True
        assert r["leak_detected"] is False

    def test_add_pattern(self) -> None:
        """Oruntu ekleme."""
        r = self.scanner.add_pattern(
            name="aws_key",
            pattern=r"AKIA[0-9A-Z]{16}",
            severity="critical",
        )
        assert r["added"] is True

    def test_add_invalid_pattern(self) -> None:
        """Gecersiz regex."""
        r = self.scanner.add_pattern(
            name="bad",
            pattern=r"[invalid",
        )
        assert r["added"] is False

    def test_get_alerts(self) -> None:
        """Uyari getirme."""
        self.scanner.scan_content(
            content='password = "test12345678"',
            source="bad.py",
        )
        r = self.scanner.get_alerts()
        assert r["retrieved"] is True
        assert r["count"] > 0

    def test_get_alerts_by_severity(self) -> None:
        """Ciddiyete gore uyari."""
        self.scanner.scan_content(
            content='password = "test12345678"',
            source="bad.py",
        )
        r = self.scanner.get_alerts(
            severity="critical"
        )
        assert r["retrieved"] is True

    def test_resolve_alert(self) -> None:
        """Uyari cozme."""
        self.scanner.scan_content(
            content='password = "test12345678"',
            source="bad.py",
        )
        alerts = self.scanner.get_alerts()
        alert_id = alerts["alerts"][0][
            "alert_id"
        ]
        r = self.scanner.resolve_alert(
            alert_id=alert_id,
            remediation="Removed from code",
        )
        assert r["resolved"] is True

    def test_resolve_nonexistent(self) -> None:
        """Olmayan uyari cozme."""
        r = self.scanner.resolve_alert(
            alert_id="fake"
        )
        assert r["resolved"] is False

    def test_get_scan_summary(self) -> None:
        """Tarama ozeti."""
        self.scanner.scan_content(
            content="clean", source="a.py"
        )
        self.scanner.scan_content(
            content='password = "badpass123x"',
            source="b.py",
        )
        r = self.scanner.get_scan_summary()
        assert r["retrieved"] is True
        assert r["total_scans"] == 2

    def test_scan_count_property(self) -> None:
        """Tarama sayisi."""
        self.scanner.scan_content(
            content="test", source="a.py"
        )
        self.scanner.scan_content(
            content="test2", source="b.py"
        )
        assert self.scanner.scan_count == 2


# ============================================================
# ZeroKnowledgeAccess Tests
# ============================================================
class TestZeroKnowledgeAccess:
    """ZeroKnowledgeAccess testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.zk = ZeroKnowledgeAccess()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.zk.proof_count == 0

    def test_register_proof(self) -> None:
        """Kanit kaydi."""
        r = self.zk.register_proof(
            user_id="user1",
            secret_hash="myhash",
        )
        assert r["registered"] is True
        assert "commitment" in r
        assert self.zk.proof_count == 1

    def test_create_challenge(self) -> None:
        """Sorgu olusturma."""
        self.zk.register_proof(
            user_id="user1",
            secret_hash="hash1",
        )
        r = self.zk.create_challenge(
            user_id="user1"
        )
        assert r["created"] is True
        assert "nonce" in r

    def test_create_challenge_no_proof(
        self,
    ) -> None:
        """Kanitsiz sorgu."""
        r = self.zk.create_challenge(
            user_id="nobody"
        )
        assert r["created"] is False

    def test_verify_correct_response(
        self,
    ) -> None:
        """Dogru yanit dogrulama."""
        reg = self.zk.register_proof(
            user_id="user1",
            secret_hash="hash1",
        )
        challenge = self.zk.create_challenge(
            user_id="user1"
        )

        commitment = reg["commitment"]
        nonce = challenge["nonce"]
        expected = hashlib.sha256(
            (nonce + commitment).encode()
        ).hexdigest()

        r = self.zk.verify_response(
            challenge_id=challenge[
                "challenge_id"
            ],
            response_hash=expected,
        )
        assert r["verified"] is True
        assert r["session_id"] is not None

    def test_verify_wrong_response(self) -> None:
        """Yanlis yanit."""
        self.zk.register_proof(
            user_id="user1",
            secret_hash="hash1",
        )
        challenge = self.zk.create_challenge(
            user_id="user1"
        )
        r = self.zk.verify_response(
            challenge_id=challenge[
                "challenge_id"
            ],
            response_hash="wronghash",
        )
        assert r["verified"] is False

    def test_verify_used_challenge(self) -> None:
        """Kullanilmis sorgu."""
        reg = self.zk.register_proof(
            user_id="user1",
            secret_hash="hash1",
        )
        challenge = self.zk.create_challenge(
            user_id="user1"
        )

        commitment = reg["commitment"]
        nonce = challenge["nonce"]
        expected = hashlib.sha256(
            (nonce + commitment).encode()
        ).hexdigest()

        self.zk.verify_response(
            challenge_id=challenge[
                "challenge_id"
            ],
            response_hash=expected,
        )
        r = self.zk.verify_response(
            challenge_id=challenge[
                "challenge_id"
            ],
            response_hash=expected,
        )
        assert r["verified"] is False

    def test_verify_nonexistent_challenge(
        self,
    ) -> None:
        """Olmayan sorgu."""
        r = self.zk.verify_response(
            challenge_id="fake",
            response_hash="hash",
        )
        assert r["verified"] is False

    def test_get_audit_trail(self) -> None:
        """Denetim izi."""
        reg = self.zk.register_proof(
            user_id="user1",
            secret_hash="hash1",
        )
        ch = self.zk.create_challenge(
            user_id="user1"
        )
        nonce = ch["nonce"]
        commitment = reg["commitment"]
        expected = hashlib.sha256(
            (nonce + commitment).encode()
        ).hexdigest()
        self.zk.verify_response(
            challenge_id=ch["challenge_id"],
            response_hash=expected,
        )
        r = self.zk.get_audit_trail(
            user_id="user1"
        )
        assert r["retrieved"] is True
        assert r["total"] == 1

    def test_revoke_proof(self) -> None:
        """Kanit iptal."""
        self.zk.register_proof(
            user_id="user1",
            secret_hash="hash1",
        )
        r = self.zk.revoke_proof(
            user_id="user1"
        )
        assert r["revoked"] is True

    def test_revoke_nonexistent(self) -> None:
        """Olmayan kanit iptal."""
        r = self.zk.revoke_proof(
            user_id="nobody"
        )
        assert r["revoked"] is False


# ============================================================
# EmergencyRevocation Tests
# ============================================================
class TestEmergencyRevocation:
    """EmergencyRevocation testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.rev = EmergencyRevocation()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.rev.revocation_count == 0

    def test_revoke_immediately(self) -> None:
        """Aninda iptal."""
        r = self.rev.revoke_immediately(
            target_type="secret",
            target_id="sec1",
            reason="breach",
            initiated_by="admin",
            severity="critical",
        )
        assert r["revoked"] is True
        assert r["status"] == "completed"
        assert self.rev.revocation_count == 1

    def test_cascade_revoke(self) -> None:
        """Kaskad iptal."""
        r = self.rev.cascade_revoke(
            root_target_id="root1",
            related_ids=["r1", "r2", "r3"],
            reason="breach",
            initiated_by="admin",
        )
        assert r["cascaded"] is True
        assert r["total_revoked"] == 4
        assert self.rev.revocation_count == 4

    def test_cascade_no_related(self) -> None:
        """Iliskili hedefsiz kaskad."""
        r = self.rev.cascade_revoke(
            root_target_id="root1",
            reason="test",
            initiated_by="admin",
        )
        assert r["cascaded"] is True
        assert r["total_revoked"] == 1

    def test_get_notifications(self) -> None:
        """Bildirim getirme."""
        self.rev.revoke_immediately(
            target_id="sec1",
            reason="test",
            initiated_by="admin",
        )
        r = self.rev.get_notifications()
        assert r["retrieved"] is True
        assert r["count"] > 0

    def test_get_unread_notifications(
        self,
    ) -> None:
        """Okunmamis bildirimler."""
        self.rev.revoke_immediately(
            target_id="sec1",
            reason="test",
            initiated_by="admin",
        )
        r = self.rev.get_notifications(
            unread_only=True
        )
        assert r["count"] > 0

    def test_initiate_recovery(self) -> None:
        """Kurtarma baslatma."""
        rev = self.rev.revoke_immediately(
            target_id="sec1",
            reason="false alarm",
            initiated_by="admin",
        )
        r = self.rev.initiate_recovery(
            revocation_id=rev["revocation_id"],
            recovery_plan="restore from backup",
            initiated_by="admin",
        )
        assert r["recovered"] is True

    def test_recovery_not_found(self) -> None:
        """Olmayan iptal kurtarma."""
        r = self.rev.initiate_recovery(
            revocation_id="fake",
            recovery_plan="plan",
        )
        assert r["recovered"] is False

    def test_get_revocation_log(self) -> None:
        """Iptal logu."""
        self.rev.revoke_immediately(
            target_id="s1",
            severity="high",
            initiated_by="admin",
        )
        self.rev.revoke_immediately(
            target_id="s2",
            severity="critical",
            initiated_by="admin",
        )
        r = self.rev.get_revocation_log()
        assert r["retrieved"] is True
        assert r["total"] == 2

    def test_get_revocation_log_severity(
        self,
    ) -> None:
        """Ciddiyete gore iptal logu."""
        self.rev.revoke_immediately(
            target_id="s1",
            severity="high",
            initiated_by="admin",
        )
        self.rev.revoke_immediately(
            target_id="s2",
            severity="critical",
            initiated_by="admin",
        )
        r = self.rev.get_revocation_log(
            severity="critical"
        )
        assert r["total"] == 1


# ============================================================
# VaultAuditLog Tests
# ============================================================
class TestVaultAuditLog:
    """VaultAuditLog testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.audit = VaultAuditLog()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.audit.log_count == 0

    def test_log_access(self) -> None:
        """Erisim loglama."""
        r = self.audit.log_access(
            action="read",
            resource="db_pass",
            user_id="user1",
        )
        assert r["logged"] is True
        assert "hash" in r
        assert self.audit.log_count == 1

    def test_hash_chain(self) -> None:
        """Ozet zinciri."""
        r1 = self.audit.log_access(
            action="read", resource="k1"
        )
        r2 = self.audit.log_access(
            action="write", resource="k2"
        )
        assert r1["hash"] != r2["hash"]

    def test_search_logs(self) -> None:
        """Log arama."""
        self.audit.log_access(
            action="read",
            resource="k1",
            user_id="u1",
        )
        self.audit.log_access(
            action="write",
            resource="k2",
            user_id="u2",
        )
        r = self.audit.search_logs(
            action="read"
        )
        assert r["searched"] is True
        assert r["total_matches"] == 1

    def test_search_by_user(self) -> None:
        """Kullaniciya gore arama."""
        self.audit.log_access(
            action="read", user_id="u1"
        )
        self.audit.log_access(
            action="write", user_id="u2"
        )
        r = self.audit.search_logs(
            user_id="u2"
        )
        assert r["total_matches"] == 1

    def test_search_by_result(self) -> None:
        """Sonuca gore arama."""
        self.audit.log_access(
            action="read", result="success"
        )
        self.audit.log_access(
            action="write", result="denied"
        )
        r = self.audit.search_logs(
            result="denied"
        )
        assert r["total_matches"] == 1

    def test_verify_integrity_empty(
        self,
    ) -> None:
        """Bos log butunluk."""
        r = self.audit.verify_integrity()
        assert r["verified"] is True
        assert r["intact"] is True

    def test_verify_integrity_valid(
        self,
    ) -> None:
        """Gecerli butunluk."""
        self.audit.log_access(action="read")
        self.audit.log_access(action="write")
        r = self.audit.verify_integrity()
        assert r["intact"] is True

    def test_export_logs(self) -> None:
        """Log disa aktarma."""
        self.audit.log_access(
            action="read", user_id="u1"
        )
        self.audit.log_access(
            action="write", user_id="u2"
        )
        r = self.audit.export_logs()
        assert r["exported"] is True
        assert r["entry_count"] == 2

    def test_export_filtered(self) -> None:
        """Filtreli disa aktarma."""
        self.audit.log_access(
            action="read", user_id="u1"
        )
        self.audit.log_access(
            action="write", user_id="u2"
        )
        r = self.audit.export_logs(
            user_id="u1"
        )
        assert r["entry_count"] == 1

    def test_compliance_report(self) -> None:
        """Uyumluluk raporu."""
        self.audit.log_access(
            action="read",
            user_id="u1",
            result="success",
        )
        self.audit.log_access(
            action="write",
            user_id="u2",
            result="denied",
        )
        r = self.audit.get_compliance_report()
        assert r["generated"] is True
        assert r["total_events"] == 2
        assert r["denied_access"] == 1
        assert r["unique_users"] == 2

    def test_get_user_activity(self) -> None:
        """Kullanici aktivitesi."""
        self.audit.log_access(
            action="read", user_id="u1"
        )
        self.audit.log_access(
            action="write", user_id="u1"
        )
        self.audit.log_access(
            action="read", user_id="u2"
        )
        r = self.audit.get_user_activity(
            user_id="u1"
        )
        assert r["retrieved"] is True
        assert r["total_events"] == 2


# ============================================================
# VaultOrchestrator Tests
# ============================================================
class TestVaultOrchestrator:
    """VaultOrchestrator testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.orch = VaultOrchestrator()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.orch.vault is not None
        assert self.orch.rotation is not None
        assert self.orch.tokens is not None
        assert self.orch.versioning is not None
        assert self.orch.scanner is not None
        assert self.orch.zk_access is not None
        assert self.orch.revocation is not None
        assert self.orch.audit is not None

    def test_store_and_audit(self) -> None:
        """Depolama ve denetim."""
        r = self.orch.store_and_audit(
            name="db_pass",
            value="secret123",
            category="database",
            owner="admin",
        )
        assert r["stored"] is True
        assert r["audited"] is True
        assert r["versioned"] is True

    def test_store_and_audit_leak(self) -> None:
        """Sizinti ile depolama."""
        r = self.orch.store_and_audit(
            name="config",
            value=(
                'api_key = "abcdefghijklmnopq'
                'rstuvwxyz1234"'
            ),
            owner="admin",
        )
        assert r["stored"] is True
        assert r["leak_check"] is True

    def test_secure_access(self) -> None:
        """Guvenli erisim."""
        self.orch.store_and_audit(
            name="key1",
            value="val1",
            owner="user1",
        )
        r = self.orch.secure_access(
            name="key1", user_id="user1"
        )
        assert r["accessed"] is True
        assert r["audited"] is True

    def test_secure_access_denied(self) -> None:
        """Reddedilen erisim."""
        self.orch.store_and_audit(
            name="key1",
            value="val1",
            owner="user1",
        )
        r = self.orch.secure_access(
            name="key1", user_id="hacker"
        )
        assert r["accessed"] is False

    def test_secure_access_with_token(
        self,
    ) -> None:
        """Token ile erisim."""
        self.orch.store_and_audit(
            name="key1",
            value="val1",
            owner="user1",
        )
        gen = self.orch.tokens.generate_token(
            user_id="user1", scopes=["read"]
        )
        r = self.orch.secure_access(
            name="key1",
            user_id="user1",
            token_id=gen["token_id"],
        )
        assert r["accessed"] is True

    def test_secure_access_invalid_token(
        self,
    ) -> None:
        """Gecersiz token ile erisim."""
        self.orch.store_and_audit(
            name="key1",
            value="val1",
            owner="user1",
        )
        r = self.orch.secure_access(
            name="key1",
            user_id="user1",
            token_id="fake_token",
        )
        assert r["accessed"] is False

    def test_emergency_response(self) -> None:
        """Acil durum yaniti."""
        r = self.orch.emergency_response(
            target_id="secret1",
            reason="breach detected",
            initiated_by="admin",
        )
        assert r["revoked"] is True
        assert r["audited"] is True

    def test_emergency_cascade(self) -> None:
        """Kaskad acil durum."""
        r = self.orch.emergency_response(
            target_id="root1",
            reason="compromise",
            initiated_by="admin",
            related_ids=["r1", "r2"],
        )
        assert r["revoked"] is True

    def test_security_scan(self) -> None:
        """Guvenlik taramasi."""
        r = self.orch.security_scan(
            content="clean code",
            source="app.py",
        )
        assert r["scanned"] is True
        assert r["leak_detected"] is False

    def test_security_scan_with_leak(
        self,
    ) -> None:
        """Sizinti ile guvenlik taramasi."""
        r = self.orch.security_scan(
            content=(
                'password = "mysecretpass1"'
            ),
            source="config.py",
        )
        assert r["scanned"] is True
        assert r["leak_detected"] is True

    def test_full_vault_status(self) -> None:
        """Tam kasa durumu."""
        self.orch.store_and_audit(
            name="k1",
            value="v1",
            owner="admin",
        )
        r = self.orch.full_vault_status()
        assert r["retrieved"] is True
        assert r["secrets_count"] == 1
        assert r["audit_integrity"] is True

    def test_get_analytics(self) -> None:
        """Analitik."""
        self.orch.store_and_audit(
            name="k1",
            value="v1",
            owner="admin",
        )
        r = self.orch.get_analytics()
        assert r["retrieved"] is True
        assert r["total_secrets"] == 1
        assert r["total_audit_logs"] >= 1


# ============================================================
# Model Tests
# ============================================================
class TestVaultModels:
    """Vault model testleri."""

    def test_secret_category_enum(self) -> None:
        """Kategori enum."""
        assert (
            SecretCategory.API_KEY == "api_key"
        )
        assert (
            SecretCategory.DATABASE == "database"
        )

    def test_encryption_algorithm_enum(
        self,
    ) -> None:
        """Algoritma enum."""
        assert (
            EncryptionAlgorithm.AES256
            == "aes256"
        )
        assert EncryptionAlgorithm.RSA == "rsa"

    def test_token_scope_enum(self) -> None:
        """Token kapsam enum."""
        assert TokenScope.READ == "read"
        assert TokenScope.ADMIN == "admin"

    def test_scan_severity_enum(self) -> None:
        """Tarama ciddiyet enum."""
        assert ScanSeverity.CRITICAL == "critical"
        assert ScanSeverity.HIGH == "high"

    def test_revocation_status_enum(
        self,
    ) -> None:
        """Iptal durum enum."""
        assert (
            RevocationStatus.COMPLETED
            == "completed"
        )
        assert (
            RevocationStatus.RECOVERED
            == "recovered"
        )

    def test_audit_action_enum(self) -> None:
        """Denetim aksiyon enum."""
        assert AuditAction.STORE == "store"
        assert AuditAction.REVOKE == "revoke"

    def test_secret_record(self) -> None:
        """Gizli bilgi kaydi."""
        rec = SecretRecord(
            name="test",
            category="api_key",
            owner="admin",
        )
        assert rec.name == "test"
        assert rec.encrypted is True

    def test_key_record(self) -> None:
        """Anahtar kaydi."""
        rec = KeyRecord(
            key_name="main",
            algorithm="rsa",
            owner="admin",
        )
        assert rec.key_name == "main"
        assert rec.version == 1

    def test_token_record(self) -> None:
        """Token kaydi."""
        rec = TokenRecord(
            user_id="u1",
            scopes=["read", "write"],
            ttl_hours=48,
        )
        assert len(rec.scopes) == 2

    def test_scan_result(self) -> None:
        """Tarama sonucu."""
        rec = ScanResult(
            source="test.py",
            leak_detected=True,
            findings_count=2,
        )
        assert rec.leak_detected is True

    def test_revocation_record(self) -> None:
        """Iptal kaydi."""
        rec = RevocationRecord(
            target_id="s1",
            reason="breach",
            severity="critical",
        )
        assert rec.target_id == "s1"
        assert rec.recovered is False

    def test_audit_entry(self) -> None:
        """Denetim kaydi."""
        rec = AuditEntry(
            action="read",
            resource="db_pass",
            user_id="admin",
        )
        assert rec.result == "success"
