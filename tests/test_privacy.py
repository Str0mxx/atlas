"""
Data Encryption & Privacy Engine testleri.

TransitEncryptor, AtRestEncryptor,
FieldLevelEncryption, DataMasker,
AnonymizationEngine, GDPRComplianceChecker,
KVKKComplianceChecker, RightToDeleteHandler,
PrivacyOrchestrator ve modeller.
"""

import pytest

from app.core.privacy.transit_encryptor import (
    TransitEncryptor,
)
from app.core.privacy.at_rest_encryptor import (
    AtRestEncryptor,
)
from app.core.privacy.field_level_encryption import (
    FieldLevelEncryption,
)
from app.core.privacy.data_masker import (
    DataMasker,
)
from app.core.privacy.anonymization_engine import (
    AnonymizationEngine,
)
from app.core.privacy.gdpr_compliance_checker import (
    GDPRComplianceChecker,
)
from app.core.privacy.kvkk_compliance_checker import (
    KVKKComplianceChecker,
)
from app.core.privacy.right_to_delete_handler import (
    RightToDeleteHandler,
)
from app.core.privacy.privacy_orchestrator import (
    PrivacyOrchestrator,
)
from app.models.privacy_models import (
    EncryptionAlgorithm,
    MaskType,
    PIIType,
    LawfulBasis,
    DeletionStatus,
    PrivacyRiskLevel,
    EncryptionKeyRecord,
    EncryptedDataRecord,
    MaskingRuleRecord,
    ConsentRecord,
    DeletionRequestRecord,
    BreachRecord,
    PrivacyStatusRecord,
)


# ===================== TransitEncryptor =====================


class TestTransitEncryptor:
    """TransitEncryptor testleri."""

    def setup_method(self):
        self.te = TransitEncryptor()

    def test_init(self):
        assert self.te.channel_count == 0

    def test_create_channel(self):
        r = self.te.create_channel(
            name="api",
            endpoint="api.example.com",
            protocol="TLS 1.3",
        )
        assert r["created"] is True
        assert r["protocol"] == "TLS 1.3"
        assert self.te.channel_count == 1

    def test_create_channel_tls12(self):
        r = self.te.create_channel(
            name="legacy",
            endpoint="old.example.com",
            protocol="TLS 1.2",
        )
        assert r["created"] is True

    def test_create_channel_unsupported(self):
        r = self.te.create_channel(
            name="bad",
            endpoint="x",
            protocol="SSL 3.0",
        )
        assert r["created"] is False

    def test_register_certificate(self):
        r = self.te.register_certificate(
            domain="example.com",
            issuer="LE",
            expires_at="2027-01-01",
            key_size=4096,
        )
        assert r["registered"] is True
        assert r["valid"] is True

    def test_register_certificate_weak(self):
        r = self.te.register_certificate(
            domain="weak.com",
            issuer="self",
            expires_at="2027-01-01",
            key_size=1024,
        )
        assert r["valid"] is False

    def test_perform_handshake(self):
        ch = self.te.create_channel(
            name="hs",
            endpoint="h.com",
            protocol="TLS 1.3",
        )
        r = self.te.perform_handshake(
            channel_id=ch["channel_id"],
            client_hello="hello",
        )
        assert r["completed"] is True

    def test_perform_handshake_no_channel(self):
        r = self.te.perform_handshake(
            channel_id="bad",
        )
        assert r["completed"] is False

    def test_validate_channel(self):
        ch = self.te.create_channel(
            name="val",
            endpoint="v.com",
            protocol="TLS 1.3",
        )
        r = self.te.validate_channel(
            channel_id=ch["channel_id"],
        )
        assert r["validated"] is True
        assert r["valid"] is True

    def test_validate_channel_not_found(self):
        r = self.te.validate_channel(
            channel_id="none",
        )
        assert r["valid"] is False

    def test_close_channel(self):
        ch = self.te.create_channel(
            name="cl",
            endpoint="c.com",
        )
        r = self.te.close_channel(
            channel_id=ch["channel_id"],
        )
        assert r["closed"] is True

    def test_close_channel_not_found(self):
        r = self.te.close_channel(
            channel_id="none",
        )
        assert r["closed"] is False

    def test_get_summary(self):
        self.te.create_channel(
            name="s",
            endpoint="s.com",
        )
        r = self.te.get_summary()
        assert r["retrieved"] is True
        assert r["total_channels"] == 1


# ===================== AtRestEncryptor =====================


class TestAtRestEncryptor:
    """AtRestEncryptor testleri."""

    def setup_method(self):
        self.ar = AtRestEncryptor()

    def test_init(self):
        assert self.ar.key_count == 0

    def test_create_key(self):
        r = self.ar.create_key(
            name="master",
            algorithm="AES-256-GCM",
        )
        assert r["created"] is True
        assert self.ar.key_count == 1

    def test_create_key_default_algo(self):
        r = self.ar.create_key(
            name="default",
        )
        assert r["created"] is True
        assert r["algorithm"] == "AES-256-GCM"

    def test_create_key_unsupported(self):
        r = self.ar.create_key(
            name="bad",
            algorithm="DES",
        )
        assert r["created"] is False

    def test_encrypt(self):
        k = self.ar.create_key(name="enc")
        r = self.ar.encrypt(
            data="secret data",
            key_id=k["key_id"],
            context="test",
        )
        assert r["encrypted"] is True
        assert "ENC[" in r["ciphertext"]

    def test_encrypt_no_key(self):
        r = self.ar.encrypt(
            data="x",
            key_id="bad",
        )
        assert r["encrypted"] is False

    def test_decrypt(self):
        k = self.ar.create_key(name="dec")
        enc = self.ar.encrypt(
            data="hello",
            key_id=k["key_id"],
        )
        r = self.ar.decrypt(
            encryption_id=enc["encryption_id"],
        )
        assert r["decrypted"] is True

    def test_decrypt_not_found(self):
        r = self.ar.decrypt(
            encryption_id="bad",
        )
        assert r["decrypted"] is False

    def test_rotate_key(self):
        k = self.ar.create_key(name="rot")
        r = self.ar.rotate_key(
            key_id=k["key_id"],
        )
        assert r["rotated"] is True
        assert r["old_version"] == 1
        assert r["new_version"] == 2

    def test_rotate_key_not_found(self):
        r = self.ar.rotate_key(key_id="bad")
        assert r["rotated"] is False

    def test_revoke_key(self):
        k = self.ar.create_key(name="rev")
        r = self.ar.revoke_key(
            key_id=k["key_id"],
        )
        assert r["revoked"] is True

    def test_encrypt_with_revoked_key(self):
        k = self.ar.create_key(name="rk")
        self.ar.revoke_key(key_id=k["key_id"])
        r = self.ar.encrypt(
            data="test",
            key_id=k["key_id"],
        )
        assert r["encrypted"] is False

    def test_encrypt_file(self):
        k = self.ar.create_key(name="file")
        r = self.ar.encrypt_file(
            file_path="/data/file.db",
            key_id=k["key_id"],
        )
        assert r["encrypted"] is True

    def test_encrypt_file_bad_key(self):
        r = self.ar.encrypt_file(
            file_path="/data/x",
            key_id="bad",
        )
        assert r["encrypted"] is False

    def test_get_summary(self):
        self.ar.create_key(name="s")
        r = self.ar.get_summary()
        assert r["retrieved"] is True
        assert r["total_keys"] == 1
        assert r["active_keys"] == 1


# ===================== FieldLevelEncryption =====================


class TestFieldLevelEncryption:
    """FieldLevelEncryption testleri."""

    def setup_method(self):
        self.fe = FieldLevelEncryption()

    def test_init(self):
        assert self.fe.field_count == 0

    def test_create_field_key(self):
        r = self.fe.create_field_key(
            field_name="email",
        )
        assert r["created"] is True

    def test_encrypt_field(self):
        self.fe.create_field_key(
            field_name="ssn",
        )
        r = self.fe.encrypt_field(
            record_id="r1",
            field_name="ssn",
            value="123-45-6789",
        )
        assert r["encrypted"] is True
        assert "FE[" in r["encrypted_value"]

    def test_encrypt_field_no_key(self):
        r = self.fe.encrypt_field(
            record_id="r1",
            field_name="no_key",
            value="test",
        )
        assert r["encrypted"] is False

    def test_encrypt_field_format_preserving(self):
        self.fe.create_field_key(
            field_name="phone",
            format_preserving=True,
        )
        r = self.fe.encrypt_field(
            record_id="r1",
            field_name="phone",
            value="5551234567",
        )
        assert r["encrypted"] is True
        assert len(r["encrypted_value"]) == 10

    def test_encrypt_field_searchable(self):
        self.fe.create_field_key(
            field_name="name",
        )
        r = self.fe.encrypt_field(
            record_id="r1",
            field_name="name",
            value="John",
            searchable=True,
        )
        assert r["encrypted"] is True
        assert r["searchable"] is True

    def test_search_encrypted(self):
        self.fe.create_field_key(
            field_name="email",
        )
        self.fe.encrypt_field(
            record_id="r1",
            field_name="email",
            value="test@example.com",
            searchable=True,
        )
        r = self.fe.search_encrypted(
            field_name="email",
            search_value="test@example.com",
        )
        assert r["searched"] is True
        assert r["match_count"] == 1

    def test_search_encrypted_no_match(self):
        r = self.fe.search_encrypted(
            field_name="x",
            search_value="none",
        )
        assert r["match_count"] == 0

    def test_decrypt_field(self):
        self.fe.create_field_key(
            field_name="card",
        )
        self.fe.encrypt_field(
            record_id="r1",
            field_name="card",
            value="4111111111111111",
        )
        r = self.fe.decrypt_field(
            record_id="r1",
            field_name="card",
        )
        assert r["decrypted"] is True

    def test_decrypt_field_not_found(self):
        r = self.fe.decrypt_field(
            record_id="bad",
            field_name="bad",
        )
        assert r["decrypted"] is False

    def test_get_summary(self):
        r = self.fe.get_summary()
        assert r["retrieved"] is True


# ===================== DataMasker =====================


class TestDataMasker:
    """DataMasker testleri."""

    def setup_method(self):
        self.dm = DataMasker()

    def test_init(self):
        assert self.dm.mask_count == 0

    def test_add_rule(self):
        r = self.dm.add_rule(
            name="email_mask",
            field="email",
            mask_type="email",
        )
        assert r["added"] is True

    def test_mask_value_full(self):
        r = self.dm.mask_value(
            value="secret",
            mask_type="full",
        )
        assert r["masked_ok"] is True
        assert r["masked"] == "******"

    def test_mask_value_partial(self):
        r = self.dm.mask_value(
            value="1234567890",
            mask_type="partial",
            visible_chars=4,
        )
        assert r["masked_ok"] is True
        assert r["masked"].endswith("7890")
        assert r["masked"].startswith("*")

    def test_mask_value_partial_short(self):
        r = self.dm.mask_value(
            value="ab",
            mask_type="partial",
            visible_chars=4,
        )
        assert r["masked"] == "**"

    def test_mask_value_email(self):
        r = self.dm.mask_value(
            value="john@example.com",
            mask_type="email",
        )
        assert r["masked_ok"] is True
        assert "@example.com" in r["masked"]
        assert r["masked"].startswith("j")

    def test_mask_value_email_short(self):
        r = self.dm.mask_value(
            value="ab@x.com",
            mask_type="email",
        )
        assert r["masked_ok"] is True
        assert "**@x.com" == r["masked"]

    def test_detect_pii_email(self):
        r = self.dm.detect_pii(
            text="Contact: test@example.com"
        )
        assert r["detected"] is True
        assert r["has_pii"] is True
        assert r["pii_count"] >= 1

    def test_detect_pii_phone(self):
        r = self.dm.detect_pii(
            text="Call 555-123-4567"
        )
        assert r["has_pii"] is True

    def test_detect_pii_ssn(self):
        r = self.dm.detect_pii(
            text="SSN: 123-45-6789"
        )
        assert r["has_pii"] is True

    def test_detect_pii_none(self):
        r = self.dm.detect_pii(
            text="Hello world"
        )
        assert r["has_pii"] is False

    def test_mask_pii(self):
        r = self.dm.mask_pii(
            text="Email: user@test.com"
        )
        assert r["masked_ok"] is True
        assert "[EMAIL]" in r["masked"]

    def test_mask_pii_multiple(self):
        r = self.dm.mask_pii(
            text="user@test.com 555-123-4567"
        )
        assert r["pii_masked"] >= 2

    def test_set_role_access(self):
        r = self.dm.set_role_access(
            role="admin",
            visible_fields=["name", "email"],
        )
        assert r["set"] is True

    def test_apply_role_mask(self):
        self.dm.set_role_access(
            role="viewer",
            visible_fields=["name"],
        )
        r = self.dm.apply_role_mask(
            data={"name": "John", "ssn": "123"},
            role="viewer",
        )
        assert r["masked_ok"] is True
        assert r["data"]["name"] == "John"
        assert r["data"]["ssn"] == "***"

    def test_apply_role_mask_no_rule(self):
        r = self.dm.apply_role_mask(
            data={"a": "1"},
            role="unknown",
        )
        assert r["data"]["a"] == "***"

    def test_mask_reversible(self):
        r = self.dm.mask_reversible(
            value="secret_data",
            context="test",
        )
        assert r["masked_ok"] is True
        assert r["reversible"] is True
        assert "MASKED[" in r["masked"]

    def test_unmask(self):
        mr = self.dm.mask_reversible(
            value="original",
        )
        r = self.dm.unmask(
            mask_id=mr["mask_id"],
        )
        assert r["unmasked"] is True
        assert r["original"] == "original"

    def test_unmask_not_found(self):
        r = self.dm.unmask(mask_id="bad")
        assert r["unmasked"] is False

    def test_mask_log(self):
        r = self.dm.mask_log(
            log_line="User test@x.com logged in"
        )
        assert r["masked_ok"] is True
        assert "[EMAIL]" in r["masked"]

    def test_mask_log_no_pii(self):
        r = self.dm.mask_log(
            log_line="System started"
        )
        assert r["masked_ok"] is True
        assert r["pii_masked"] == 0

    def test_get_summary(self):
        r = self.dm.get_summary()
        assert r["retrieved"] is True


# ===================== AnonymizationEngine =====================


class TestAnonymizationEngine:
    """AnonymizationEngine testleri."""

    def setup_method(self):
        self.ae = AnonymizationEngine()

    def test_init(self):
        assert self.ae.anonymized_count == 0

    def test_anonymize_record(self):
        r = self.ae.anonymize_record(
            record={
                "name": "John",
                "age": "35",
                "city": "Istanbul",
            },
            quasi_identifiers=["age", "city"],
            sensitive_fields=["name"],
        )
        assert r["anonymized_ok"] is True
        assert r["anonymized"]["name"] == "[SUPPRESSED]"
        assert "30-39" in r["anonymized"]["age"]

    def test_anonymize_empty(self):
        r = self.ae.anonymize_record()
        assert r["anonymized_ok"] is True

    def test_generalize_age(self):
        r = self.ae._generalize("age", "25")
        assert r == "20-29"

    def test_generalize_location(self):
        r = self.ae._generalize("city", "Istanbul")
        assert r == "[REGION]"

    def test_generalize_zip(self):
        r = self.ae._generalize("zip_code", "34100")
        assert r == "341**"

    def test_generalize_other(self):
        r = self.ae._generalize("other", "abcdef")
        assert r == "ab***"

    def test_pseudonymize(self):
        r = self.ae.pseudonymize(
            identifier="john@test.com",
            context="email",
        )
        assert r["created"] is True
        assert r["pseudonym"].startswith("PSE_")

    def test_pseudonymize_consistent(self):
        r1 = self.ae.pseudonymize(
            identifier="same",
            context="ctx",
        )
        r2 = self.ae.pseudonymize(
            identifier="same",
            context="ctx",
        )
        assert r1["pseudonym"] == r2["pseudonym"]

    def test_depseudonymize(self):
        ps = self.ae.pseudonymize(
            identifier="test_id",
        )
        r = self.ae.depseudonymize(
            pseudonym_id=ps["pseudonym_id"],
        )
        assert r["resolved"] is True
        assert r["original"] == "test_id"

    def test_depseudonymize_not_found(self):
        r = self.ae.depseudonymize(
            pseudonym_id="bad",
        )
        assert r["resolved"] is False

    def test_assess_risk_compliant(self):
        r = self.ae.assess_risk(
            dataset_size=1000,
            quasi_identifier_count=3,
            unique_combinations=100,
        )
        assert r["assessed"] is True
        assert r["k_achieved"] == 10
        assert r["compliant"] is True

    def test_assess_risk_non_compliant(self):
        r = self.ae.assess_risk(
            dataset_size=10,
            quasi_identifier_count=5,
            unique_combinations=5,
        )
        assert r["k_achieved"] == 2
        assert r["compliant"] is False

    def test_assess_risk_zero(self):
        r = self.ae.assess_risk(
            dataset_size=0,
        )
        assert r["risk_score"] == 0.0
        assert r["compliant"] is False

    def test_assess_risk_levels(self):
        r = self.ae.assess_risk(
            dataset_size=100,
            quasi_identifier_count=3,
            unique_combinations=60,
        )
        assert r["risk_level"] == "high"

    def test_add_policy(self):
        r = self.ae.add_policy(
            name="pii_policy",
            data_type="personal",
            action="anonymize",
            retention_days=90,
        )
        assert r["added"] is True

    def test_get_summary(self):
        self.ae.anonymize_record(
            record={"x": "1"},
        )
        r = self.ae.get_summary()
        assert r["retrieved"] is True
        assert r["total_datasets"] == 1


# ===================== GDPRComplianceChecker =====================


class TestGDPRComplianceChecker:
    """GDPRComplianceChecker testleri."""

    def setup_method(self):
        self.gc = GDPRComplianceChecker()

    def test_init(self):
        assert self.gc.consent_count == 0

    def test_map_data(self):
        r = self.gc.map_data(
            data_category="personal",
            purpose="marketing",
            lawful_basis="consent",
        )
        assert r["mapped"] is True

    def test_map_data_invalid_basis(self):
        r = self.gc.map_data(
            data_category="x",
            lawful_basis="invalid",
        )
        assert r["mapped"] is False

    def test_record_consent(self):
        r = self.gc.record_consent(
            data_subject="user1",
            purpose="marketing",
            granted=True,
        )
        assert r["recorded"] is True
        assert self.gc.consent_count == 1

    def test_check_consent_exists(self):
        self.gc.record_consent(
            data_subject="u1",
            purpose="p1",
            granted=True,
        )
        r = self.gc.check_consent(
            data_subject="u1",
            purpose="p1",
        )
        assert r["checked"] is True
        assert r["has_consent"] is True

    def test_check_consent_missing(self):
        r = self.gc.check_consent(
            data_subject="nobody",
            purpose="x",
        )
        assert r["has_consent"] is False

    def test_withdraw_consent(self):
        self.gc.record_consent(
            data_subject="u2",
            purpose="p2",
        )
        r = self.gc.withdraw_consent(
            data_subject="u2",
            purpose="p2",
        )
        assert r["withdrawn"] is True

    def test_withdraw_consent_not_found(self):
        r = self.gc.withdraw_consent(
            data_subject="x",
            purpose="y",
        )
        assert r["withdrawn"] is False

    def test_report_breach(self):
        r = self.gc.report_breach(
            description="Data leak",
            affected_count=5000,
            severity="high",
        )
        assert r["reported"] is True
        assert r["notify_authority"] is True
        assert r["deadline_hours"] == 72

    def test_report_breach_low(self):
        r = self.gc.report_breach(
            description="Minor issue",
            affected_count=5,
            severity="low",
        )
        assert r["notify_authority"] is False

    def test_run_dpia(self):
        r = self.gc.run_dpia(
            processing_name="profiling",
            risk_level="high",
            mitigations=["encrypt", "minimize", "pseudonymize"],
        )
        assert r["assessed"] is True
        assert r["residual_risk"] == "low"
        assert r["approved"] is True

    def test_run_dpia_high_risk(self):
        r = self.gc.run_dpia(
            processing_name="tracking",
            risk_level="high",
        )
        assert r["residual_risk"] == "high"
        assert r["approved"] is False

    def test_run_dpia_medium_mitigated(self):
        r = self.gc.run_dpia(
            processing_name="analytics",
            risk_level="high",
            mitigations=["encrypt"],
        )
        assert r["residual_risk"] == "medium"

    def test_check_compliance_empty(self):
        r = self.gc.check_compliance()
        assert r["checked"] is True
        assert r["compliant"] is False
        assert "no_data_mapping" in r["issues"]

    def test_check_compliance_ok(self):
        self.gc.map_data(
            data_category="personal",
            purpose="service",
            lawful_basis="contract",
        )
        self.gc.record_consent(
            data_subject="u1",
            purpose="service",
        )
        r = self.gc.check_compliance()
        assert r["compliant"] is True

    def test_get_summary(self):
        r = self.gc.get_summary()
        assert r["retrieved"] is True


# ===================== KVKKComplianceChecker =====================


class TestKVKKComplianceChecker:
    """KVKKComplianceChecker testleri."""

    def setup_method(self):
        self.kc = KVKKComplianceChecker()

    def test_init(self):
        assert self.kc.inventory_count == 0

    def test_add_inventory_item(self):
        r = self.kc.add_inventory_item(
            data_category="personal",
            data_owner="ATLAS",
            storage_location="postgres",
        )
        assert r["added"] is True
        assert self.kc.inventory_count == 1

    def test_add_special_item(self):
        r = self.kc.add_inventory_item(
            data_category="health",
            data_owner="ATLAS",
            is_special=True,
        )
        assert r["is_special"] is True

    def test_register_purpose(self):
        r = self.kc.register_purpose(
            name="marketing",
            description="Pazarlama",
            legal_basis="consent",
        )
        assert r["registered"] is True

    def test_record_transfer_domestic(self):
        r = self.kc.record_transfer(
            data_category="personal",
            recipient="partner",
            destination="domestic",
        )
        assert r["recorded"] is True
        assert r["compliant"] is True

    def test_record_transfer_intl_compliant(self):
        r = self.kc.record_transfer(
            data_category="personal",
            recipient="eu_partner",
            destination="international",
            legal_basis="consent",
            has_contract=True,
        )
        assert r["compliant"] is True

    def test_record_transfer_intl_no_contract(self):
        r = self.kc.record_transfer(
            data_category="personal",
            recipient="foreign",
            destination="international",
            legal_basis="consent",
            has_contract=False,
        )
        assert r["compliant"] is False
        assert "no_contract_intl" in r["issues"]

    def test_record_transfer_intl_no_basis(self):
        r = self.kc.record_transfer(
            data_category="personal",
            recipient="foreign",
            destination="international",
        )
        assert r["compliant"] is False

    def test_check_special_category(self):
        r = self.kc.check_special_category(
            data_category="health",
            has_explicit_consent=True,
        )
        assert r["is_special"] is True
        assert r["processing_allowed"] is True

    def test_check_special_no_consent(self):
        r = self.kc.check_special_category(
            data_category="biometric",
            has_explicit_consent=False,
        )
        assert r["processing_allowed"] is False

    def test_check_non_special(self):
        r = self.kc.check_special_category(
            data_category="contact_info",
        )
        assert r["is_special"] is False
        assert r["processing_allowed"] is True

    def test_generate_verbis_report(self):
        self.kc.add_inventory_item(
            data_category="personal",
            data_owner="ATLAS",
        )
        self.kc.register_purpose(
            name="service",
        )
        r = self.kc.generate_verbis_report()
        assert r["generated"] is True
        assert r["inventory_count"] == 1

    def test_check_compliance_empty(self):
        r = self.kc.check_compliance()
        assert r["compliant"] is False
        assert "no_data_inventory" in r["issues"]

    def test_check_compliance_ok(self):
        self.kc.add_inventory_item(
            data_category="personal",
            data_owner="ATLAS",
        )
        self.kc.register_purpose(
            name="service",
        )
        r = self.kc.check_compliance()
        assert r["checked"] is True
        assert r["compliant"] is True

    def test_get_summary(self):
        r = self.kc.get_summary()
        assert r["retrieved"] is True


# ===================== RightToDeleteHandler =====================


class TestRightToDeleteHandler:
    """RightToDeleteHandler testleri."""

    def setup_method(self):
        self.rd = RightToDeleteHandler()

    def test_init(self):
        assert self.rd.request_count == 0

    def test_submit_request_verified(self):
        r = self.rd.submit_request(
            data_subject="user1",
            reason="GDPR Art 17",
            verified=True,
        )
        assert r["submitted"] is True
        assert r["status"] == "pending"
        assert r["deadline_days"] == 30

    def test_submit_request_unverified(self):
        r = self.rd.submit_request(
            data_subject="user2",
            verified=False,
        )
        assert r["status"] == "verifying"

    def test_verify_identity(self):
        sub = self.rd.submit_request(
            data_subject="u1",
            verified=False,
        )
        r = self.rd.verify_identity(
            request_id=sub["request_id"],
            verification_method="email",
            verified=True,
        )
        assert r["verified_ok"] is True
        assert r["status"] == "pending"

    def test_verify_identity_failed(self):
        sub = self.rd.submit_request(
            data_subject="u2",
            verified=False,
        )
        r = self.rd.verify_identity(
            request_id=sub["request_id"],
            verification_method="id_check",
            verified=False,
        )
        assert r["status"] == "rejected"

    def test_verify_not_found(self):
        r = self.rd.verify_identity(
            request_id="bad",
        )
        assert r["verified_ok"] is False

    def test_discover_data(self):
        sub = self.rd.submit_request(
            data_subject="u3",
            verified=True,
        )
        r = self.rd.discover_data(
            request_id=sub["request_id"],
        )
        assert r["discovered"] is True
        assert r["total_findings"] >= 1

    def test_discover_data_not_found(self):
        r = self.rd.discover_data(
            request_id="bad",
        )
        assert r["discovered"] is False

    def test_execute_deletion(self):
        sub = self.rd.submit_request(
            data_subject="u4",
            verified=True,
        )
        self.rd.discover_data(
            request_id=sub["request_id"],
        )
        r = self.rd.execute_deletion(
            request_id=sub["request_id"],
        )
        assert r["deleted"] is True
        assert r["records_deleted"] >= 1

    def test_execute_deletion_not_verified(self):
        sub = self.rd.submit_request(
            data_subject="u5",
            verified=False,
        )
        r = self.rd.execute_deletion(
            request_id=sub["request_id"],
        )
        assert r["deleted"] is False

    def test_execute_deletion_cascade(self):
        sub = self.rd.submit_request(
            data_subject="u6",
            verified=True,
        )
        r = self.rd.execute_deletion(
            request_id=sub["request_id"],
            cascade=True,
        )
        assert r["deleted"] is True
        assert r["cascade"] is True

    def test_reject_request(self):
        sub = self.rd.submit_request(
            data_subject="u7",
            verified=True,
        )
        r = self.rd.reject_request(
            request_id=sub["request_id"],
            reason="legal_obligation",
        )
        assert r["rejected"] is True

    def test_reject_not_found(self):
        r = self.rd.reject_request(
            request_id="bad",
        )
        assert r["rejected"] is False

    def test_get_request_status(self):
        sub = self.rd.submit_request(
            data_subject="u8",
            verified=True,
        )
        r = self.rd.get_request_status(
            request_id=sub["request_id"],
        )
        assert r["found"] is True
        assert r["status"] == "pending"

    def test_get_request_status_not_found(self):
        r = self.rd.get_request_status(
            request_id="bad",
        )
        assert r["found"] is False

    def test_get_audit_trail(self):
        sub = self.rd.submit_request(
            data_subject="u9",
            verified=True,
        )
        self.rd.discover_data(
            request_id=sub["request_id"],
        )
        self.rd.execute_deletion(
            request_id=sub["request_id"],
        )
        r = self.rd.get_audit_trail(
            request_id=sub["request_id"],
        )
        assert r["found"] is True
        assert len(r["deletions"]) >= 1

    def test_get_audit_trail_not_found(self):
        r = self.rd.get_audit_trail(
            request_id="bad",
        )
        assert r["found"] is False

    def test_get_summary(self):
        self.rd.submit_request(
            data_subject="s1",
            verified=True,
        )
        r = self.rd.get_summary()
        assert r["retrieved"] is True
        assert r["total_requests"] == 1


# ===================== PrivacyOrchestrator =====================


class TestPrivacyOrchestrator:
    """PrivacyOrchestrator testleri."""

    def setup_method(self):
        self.po = PrivacyOrchestrator()

    def test_init(self):
        assert self.po.transit is not None
        assert self.po.at_rest is not None
        assert self.po.masker is not None

    def test_protect_data(self):
        r = self.po.protect_data(
            data={
                "name": "John",
                "email": "j@x.com",
                "age": "30",
            },
            encrypt_fields=["email"],
            mask_fields=["name"],
            anonymize_fields=["age"],
            record_id="r1",
        )
        assert r["protected"] is True
        assert r["fields_protected"] == 3
        assert r["protected_data"]["age"] == "[ANONYMIZED]"

    def test_protect_data_empty(self):
        r = self.po.protect_data()
        assert r["protected"] is True
        assert r["fields_protected"] == 0

    def test_scan_pii(self):
        r = self.po.scan_pii(
            text="Contact test@example.com",
        )
        assert r["scanned"] is True
        assert r["has_pii"] is True

    def test_scan_pii_auto_mask(self):
        r = self.po.scan_pii(
            text="Email: user@test.com",
            auto_mask=True,
        )
        assert r["scanned"] is True
        assert "[EMAIL]" in r["masked_text"]

    def test_scan_pii_no_pii(self):
        r = self.po.scan_pii(
            text="Hello world",
        )
        assert r["has_pii"] is False

    def test_handle_deletion_request(self):
        r = self.po.handle_deletion_request(
            data_subject="user1",
            reason="GDPR",
            verified=True,
        )
        assert r["handled"] is True
        assert r["auto_executed"] is False

    def test_handle_deletion_auto(self):
        r = self.po.handle_deletion_request(
            data_subject="user2",
            reason="GDPR",
            verified=True,
            auto_execute=True,
        )
        assert r["handled"] is True
        assert r["auto_executed"] is True

    def test_compliance_status(self):
        r = self.po.compliance_status()
        assert r["retrieved"] is True
        assert "gdpr" in r
        assert "kvkk" in r

    def test_get_analytics(self):
        r = self.po.get_analytics()
        assert r["retrieved"] is True
        assert "transit_channels" in r
        assert "encryption_keys" in r

    def test_get_summary(self):
        r = self.po.get_summary()
        assert r["retrieved"] is True
        assert "transit" in r
        assert "gdpr" in r
        assert "kvkk" in r


# ===================== Privacy Models =====================


class TestPrivacyModels:
    """Privacy model testleri."""

    def test_encryption_algorithm_enum(self):
        assert (
            EncryptionAlgorithm.AES_256_GCM
            == "AES-256-GCM"
        )
        assert (
            EncryptionAlgorithm.CHACHA20
            == "ChaCha20-Poly1305"
        )

    def test_mask_type_enum(self):
        assert MaskType.FULL == "full"
        assert MaskType.PARTIAL == "partial"
        assert MaskType.EMAIL == "email"
        assert MaskType.REVERSIBLE == "reversible"

    def test_pii_type_enum(self):
        assert PIIType.EMAIL == "email"
        assert PIIType.SSN == "ssn"

    def test_lawful_basis_enum(self):
        assert LawfulBasis.CONSENT == "consent"
        assert (
            LawfulBasis.LEGITIMATE_INTEREST
            == "legitimate_interest"
        )

    def test_deletion_status_enum(self):
        assert DeletionStatus.PENDING == "pending"
        assert DeletionStatus.COMPLETED == "completed"

    def test_privacy_risk_level_enum(self):
        assert PrivacyRiskLevel.LOW == "low"
        assert PrivacyRiskLevel.CRITICAL == "critical"

    def test_encryption_key_record(self):
        r = EncryptionKeyRecord(
            key_id="k1",
            name="master",
            algorithm=EncryptionAlgorithm.AES_256_GCM,
        )
        assert r.key_id == "k1"
        assert r.active is True
        assert r.version == 1

    def test_encrypted_data_record(self):
        r = EncryptedDataRecord(
            encryption_id="e1",
            key_id="k1",
            ciphertext="ENC[abc]",
        )
        assert r.encryption_id == "e1"

    def test_masking_rule_record(self):
        r = MaskingRuleRecord(
            rule_id="m1",
            name="email",
            mask_type=MaskType.EMAIL,
        )
        assert r.mask_type == MaskType.EMAIL

    def test_consent_record(self):
        r = ConsentRecord(
            consent_id="c1",
            data_subject="user1",
            purpose="marketing",
        )
        assert r.granted is True
        assert r.expiry_days == 365

    def test_deletion_request_record(self):
        r = DeletionRequestRecord(
            request_id="d1",
            data_subject="user1",
        )
        assert r.status == DeletionStatus.PENDING

    def test_breach_record(self):
        r = BreachRecord(
            breach_id="b1",
            description="leak",
            affected_count=100,
        )
        assert r.deadline_hours == 72

    def test_privacy_status_record(self):
        r = PrivacyStatusRecord(
            transit_channels=5,
            encryption_keys=3,
            overall_compliant=True,
            overall_score=0.95,
        )
        assert r.transit_channels == 5
        assert r.overall_score == 0.95

    def test_privacy_status_defaults(self):
        r = PrivacyStatusRecord()
        assert r.overall_compliant is False
        assert r.overall_score == 0.0
