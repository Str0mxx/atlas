"""Digital Legacy & Backup Manager testleri."""

import pytest

from app.models.digitallegacy_models import (
    AssetType,
    BackupStatus,
    EncryptionLevel,
    VerificationStatus,
    SuccessionTrigger,
    WillStatus,
    DigitalAssetRecord,
    BackupRecord,
    SuccessionRecord,
    DigitalWillRecord,
)
from app.core.digitallegacy.digital_asset_inventory import (
    DigitalAssetInventory,
)
from app.core.digitallegacy.password_vault_sync import (
    PasswordVaultSync,
)
from app.core.digitallegacy.cloud_backup_manager import (
    CloudBackupManager,
)
from app.core.digitallegacy.succession_planner import (
    SuccessionPlanner,
)
from app.core.digitallegacy.recovery_plan_builder import (
    RecoveryPlanBuilder,
)
from app.core.digitallegacy.legacy_encryption_manager import (
    LegacyEncryptionManager,
)
from app.core.digitallegacy.periodic_verifier import (
    PeriodicVerifier,
)
from app.core.digitallegacy.digital_will_manager import (
    DigitalWillManager,
)
from app.core.digitallegacy.digitallegacy_orchestrator import (
    DigitalLegacyOrchestrator,
)


# ── Model Testleri ──


class TestDigitalLegacyModels:
    """Model testleri."""

    def test_asset_type_values(self):
        assert AssetType.account == "account"
        assert AssetType.document == "document"
        assert AssetType.media == "media"
        assert AssetType.credential == "credential"
        assert AssetType.cryptocurrency == "cryptocurrency"
        assert AssetType.subscription == "subscription"

    def test_backup_status_values(self):
        assert BackupStatus.pending == "pending"
        assert BackupStatus.in_progress == "in_progress"
        assert BackupStatus.completed == "completed"
        assert BackupStatus.failed == "failed"
        assert BackupStatus.verified == "verified"
        assert BackupStatus.expired == "expired"

    def test_encryption_level_values(self):
        assert EncryptionLevel.none == "none"
        assert EncryptionLevel.basic == "basic"
        assert EncryptionLevel.standard == "standard"
        assert EncryptionLevel.military == "military"
        assert EncryptionLevel.quantum_safe == "quantum_safe"

    def test_verification_status_values(self):
        assert VerificationStatus.not_verified == "not_verified"
        assert VerificationStatus.passed == "passed"
        assert VerificationStatus.failed == "failed"
        assert VerificationStatus.partial == "partial"
        assert VerificationStatus.scheduled == "scheduled"
        assert VerificationStatus.overdue == "overdue"

    def test_succession_trigger_values(self):
        assert SuccessionTrigger.inactivity == "inactivity"
        assert SuccessionTrigger.manual == "manual"
        assert SuccessionTrigger.date_based == "date_based"
        assert SuccessionTrigger.health_event == "health_event"
        assert SuccessionTrigger.legal_order == "legal_order"

    def test_will_status_values(self):
        assert WillStatus.draft == "draft"
        assert WillStatus.active == "active"
        assert WillStatus.updated == "updated"
        assert WillStatus.executed == "executed"
        assert WillStatus.revoked == "revoked"
        assert WillStatus.archived == "archived"

    def test_digital_asset_record(self):
        r = DigitalAssetRecord(
            name="Gmail", asset_type="account"
        )
        assert r.name == "Gmail"
        assert r.asset_type == "account"
        assert r.asset_id

    def test_backup_record(self):
        r = BackupRecord(
            source="documents",
            destination="aws_s3",
        )
        assert r.source == "documents"
        assert r.destination == "aws_s3"
        assert r.backup_id

    def test_succession_record(self):
        r = SuccessionRecord(
            beneficiary="Ali",
            trigger="inactivity",
        )
        assert r.beneficiary == "Ali"
        assert r.trigger == "inactivity"
        assert r.succession_id

    def test_digital_will_record(self):
        r = DigitalWillRecord(
            title="My Will", status="draft"
        )
        assert r.title == "My Will"
        assert r.status == "draft"
        assert r.version == 1
        assert r.will_id


# ── DigitalAssetInventory Testleri ──


class TestDigitalAssetInventory:
    """Dijital varlık envanteri testleri."""

    def setup_method(self):
        self.inv = DigitalAssetInventory()

    def test_init(self):
        assert self.inv.asset_count == 0

    def test_catalog_asset(self):
        r = self.inv.catalog_asset(
            name="Gmail",
            asset_type="account",
            platform="google",
            value_estimate=0.0,
        )
        assert r["cataloged"] is True
        assert r["name"] == "Gmail"
        assert r["asset_type"] == "account"
        assert self.inv.asset_count == 1

    def test_track_accounts(self):
        self.inv.catalog_asset(
            name="Gmail",
            asset_type="account",
            platform="google",
        )
        self.inv.catalog_asset(
            name="GitHub",
            asset_type="account",
            platform="github",
        )
        self.inv.catalog_asset(
            name="Photo",
            asset_type="media",
            platform="google",
        )
        r = self.inv.track_accounts()
        assert r["tracked"] is True
        assert r["account_count"] == 2
        assert r["platform_count"] == 2

    def test_map_credentials(self):
        c = self.inv.catalog_asset(
            name="Gmail",
            asset_type="account",
        )
        r = self.inv.map_credentials(
            asset_id=c["asset_id"],
            username="user@gmail.com",
            has_2fa=True,
            recovery_email="recovery@mail.com",
        )
        assert r["mapped"] is True
        assert r["has_2fa"] is True
        assert r["security_score"] == 100

    def test_map_credentials_no_2fa(self):
        c = self.inv.catalog_asset(
            name="Test", asset_type="account",
        )
        r = self.inv.map_credentials(
            asset_id=c["asset_id"],
            username="user",
            has_2fa=False,
            recovery_email="",
        )
        assert r["security_score"] == 50

    def test_map_credentials_not_found(self):
        r = self.inv.map_credentials(
            asset_id="nonexistent",
        )
        assert r["mapped"] is False
        assert r["error"] == "asset_not_found"

    def test_assess_value(self):
        self.inv.catalog_asset(
            name="BTC Wallet",
            asset_type="cryptocurrency",
            value_estimate=5000.0,
        )
        self.inv.catalog_asset(
            name="Domain",
            asset_type="document",
            value_estimate=500.0,
        )
        r = self.inv.assess_value()
        assert r["assessed"] is True
        assert r["total_value"] == 5500.0
        assert r["most_valuable"] == "BTC Wallet"

    def test_document_access(self):
        c = self.inv.catalog_asset(
            name="Gmail",
            asset_type="account",
        )
        r = self.inv.document_access(
            asset_id=c["asset_id"],
            access_method="browser_login",
            notes="Use Chrome",
        )
        assert r["documented"] is True
        assert r["coverage_pct"] == 100.0

    def test_document_access_not_found(self):
        r = self.inv.document_access(
            asset_id="nonexistent",
        )
        assert r["documented"] is False


# ── PasswordVaultSync Testleri ──


class TestPasswordVaultSync:
    """Şifre kasası senkronizasyon testleri."""

    def setup_method(self):
        self.pvs = PasswordVaultSync()

    def test_init(self):
        assert self.pvs.vault_count == 0

    def test_integrate_vault(self):
        r = self.pvs.integrate_vault(
            vault_name="Main Vault",
            vault_type="bitwarden",
            entry_count=50,
        )
        assert r["integrated"] is True
        assert r["name"] == "Main Vault"
        assert self.pvs.vault_count == 1

    def test_sync_vault(self):
        v = self.pvs.integrate_vault(
            vault_name="Test",
            vault_type="1password",
            entry_count=100,
        )
        r = self.pvs.sync_vault(
            vault_id=v["vault_id"],
            direction="bidirectional",
        )
        assert r["synced"] is True
        assert r["added"] >= 1
        assert r["updated"] >= 1

    def test_sync_vault_not_found(self):
        r = self.pvs.sync_vault(
            vault_id="nonexistent",
        )
        assert r["synced"] is False

    def test_resolve_conflicts(self):
        conflicts = [
            {"entry": "gmail", "source": "v1"},
            {"entry": "github", "source": "v2"},
        ]
        r = self.pvs.resolve_conflicts(
            conflicts=conflicts,
            strategy="newest_wins",
        )
        assert r["resolved"] is True
        assert r["resolved_count"] == 2

    def test_resolve_conflicts_empty(self):
        r = self.pvs.resolve_conflicts()
        assert r["resolved"] is True
        assert r["resolved_count"] == 0

    def test_get_history(self):
        v = self.pvs.integrate_vault(
            vault_name="Test",
            entry_count=50,
        )
        self.pvs.sync_vault(
            vault_id=v["vault_id"],
        )
        r = self.pvs.get_history()
        assert r["retrieved"] is True
        assert r["count"] == 1

    def test_audit_security(self):
        v = self.pvs.integrate_vault(
            vault_name="Test",
            entry_count=50,
        )
        self.pvs.sync_vault(
            vault_id=v["vault_id"],
        )
        r = self.pvs.audit_security()
        assert r["audited"] is True
        assert r["health"] == "excellent"

    def test_audit_security_no_vaults(self):
        r = self.pvs.audit_security()
        assert r["health"] == "no_vaults"


# ── CloudBackupManager Testleri ──


class TestCloudBackupManager:
    """Bulut yedekleme yöneticisi testleri."""

    def setup_method(self):
        self.cbm = CloudBackupManager()

    def test_init(self):
        assert self.cbm.backup_count == 0

    def test_create_backup(self):
        r = self.cbm.create_backup(
            source="documents",
            destination="aws_s3",
            size_mb=250.0,
            encryption="aes256",
        )
        assert r["created"] is True
        assert r["status"] == "completed"
        assert self.cbm.backup_count == 1

    def test_schedule_backup(self):
        r = self.cbm.schedule_backup(
            source="photos",
            frequency="daily",
            retention_days=30,
        )
        assert r["scheduled"] is True
        assert r["interval_hours"] == 24

    def test_schedule_backup_weekly(self):
        r = self.cbm.schedule_backup(
            source="all",
            frequency="weekly",
        )
        assert r["interval_hours"] == 168

    def test_verify_backup(self):
        b = self.cbm.create_backup(
            source="test", size_mb=10.0,
        )
        r = self.cbm.verify_backup(
            backup_id=b["backup_id"],
        )
        assert r["verified"] is True
        assert r["status"] == "verified"
        assert r["integrity"] is True

    def test_verify_backup_not_found(self):
        r = self.cbm.verify_backup(
            backup_id="nonexistent",
        )
        assert r["verified"] is False

    def test_restore_backup(self):
        b = self.cbm.create_backup(
            source="docs", size_mb=100.0,
        )
        r = self.cbm.restore_backup(
            backup_id=b["backup_id"],
            target="/restore/docs",
        )
        assert r["restored"] is True
        assert r["status"] == "restored"

    def test_restore_backup_not_found(self):
        r = self.cbm.restore_backup(
            backup_id="nonexistent",
        )
        assert r["restored"] is False

    def test_manage_versions(self):
        self.cbm.create_backup(
            source="data", size_mb=50.0,
        )
        self.cbm.create_backup(
            source="data", size_mb=55.0,
        )
        r = self.cbm.manage_versions(
            source="data", max_versions=5,
        )
        assert r["managed"] is True
        assert r["active_versions"] == 2
        assert r["pruned_versions"] == 0


# ── SuccessionPlanner Testleri ──


class TestSuccessionPlanner:
    """Veraset planlayıcı testleri."""

    def setup_method(self):
        self.sp = SuccessionPlanner()

    def test_init(self):
        assert self.sp.plan_count == 0

    def test_assign_beneficiary(self):
        r = self.sp.assign_beneficiary(
            name="Ali Yilmaz",
            email="ali@test.com",
            relationship="spouse",
            priority=1,
        )
        assert r["assigned"] is True
        assert r["name"] == "Ali Yilmaz"

    def test_delegate_access(self):
        b = self.sp.assign_beneficiary(
            name="Ali", relationship="spouse",
        )
        r = self.sp.delegate_access(
            beneficiary_id=b["beneficiary_id"],
            asset_ids=["a1", "a2", "a3"],
            access_level="full",
        )
        assert r["delegated"] is True
        assert r["asset_count"] == 3
        assert r["access_level"] == "full"

    def test_delegate_access_not_found(self):
        r = self.sp.delegate_access(
            beneficiary_id="nonexistent",
        )
        assert r["delegated"] is False

    def test_set_trigger_inactivity(self):
        r = self.sp.set_trigger(
            trigger_type="inactivity",
            threshold_days=90,
        )
        assert r["set"] is True
        assert r["urgency"] == "medium"

    def test_set_trigger_high_urgency(self):
        r = self.sp.set_trigger(
            trigger_type="health_event",
            threshold_days=7,
        )
        assert r["set"] is True
        assert r["urgency"] == "high"

    def test_set_trigger_low_urgency(self):
        r = self.sp.set_trigger(
            trigger_type="date_based",
            threshold_days=365,
        )
        assert r["urgency"] == "low"

    def test_configure_notifications(self):
        b = self.sp.assign_beneficiary(
            name="Ali", relationship="spouse",
        )
        r = self.sp.configure_notifications(
            beneficiary_id=b["beneficiary_id"],
            channels=["email", "sms"],
            frequency="on_trigger",
        )
        assert r["configured"] is True
        assert r["channel_count"] == 2

    def test_configure_notifications_not_found(self):
        r = self.sp.configure_notifications(
            beneficiary_id="nonexistent",
        )
        assert r["configured"] is False

    def test_check_compliance_us(self):
        self.sp.assign_beneficiary(
            name="Ali", relationship="spouse",
        )
        self.sp.set_trigger(
            trigger_type="inactivity",
        )
        r = self.sp.check_compliance(
            jurisdiction="US",
        )
        assert r["checked"] is True
        assert r["jurisdiction"] == "US"
        assert r["compliance_pct"] > 0

    def test_check_compliance_eu(self):
        r = self.sp.check_compliance(
            jurisdiction="EU",
        )
        assert r["checked"] is True
        assert r["status"] == "non_compliant"


# ── RecoveryPlanBuilder Testleri ──


class TestRecoveryPlanBuilder:
    """Kurtarma planı oluşturucu testleri."""

    def setup_method(self):
        self.rpb = RecoveryPlanBuilder()

    def test_init(self):
        assert self.rpb.plan_count == 0

    def test_define_scenario(self):
        r = self.rpb.define_scenario(
            name="Ransomware Attack",
            severity="critical",
            probability="low",
        )
        assert r["defined"] is True
        assert r["risk_level"] in [
            "low", "medium", "high", "critical",
        ]
        assert self.rpb.plan_count == 1

    def test_define_scenario_high_risk(self):
        r = self.rpb.define_scenario(
            name="Data Breach",
            severity="critical",
            probability="high",
        )
        assert r["risk_level"] == "critical"
        assert r["risk_score"] == 16

    def test_define_scenario_low_risk(self):
        r = self.rpb.define_scenario(
            name="Minor Outage",
            severity="low",
            probability="rare",
        )
        assert r["risk_level"] == "low"
        assert r["risk_score"] == 1

    def test_add_recovery_steps(self):
        s = self.rpb.define_scenario(
            name="Hack",
            severity="high",
        )
        r = self.rpb.add_recovery_steps(
            scenario_id=s["scenario_id"],
            steps=[
                "Isolate systems",
                "Assess damage",
                "Restore backups",
            ],
        )
        assert r["added"] is True
        assert r["step_count"] == 3

    def test_add_recovery_steps_not_found(self):
        r = self.rpb.add_recovery_steps(
            scenario_id="nonexistent",
        )
        assert r["added"] is False

    def test_prioritize_plans(self):
        self.rpb.define_scenario(
            name="Low Risk",
            severity="low",
            probability="rare",
        )
        self.rpb.define_scenario(
            name="High Risk",
            severity="critical",
            probability="high",
        )
        r = self.rpb.prioritize_plans()
        assert r["prioritized"] is True
        assert r["priorities"][0]["scenario"] == "High Risk"

    def test_manage_contacts(self):
        r = self.rpb.manage_contacts(
            name="IT Admin",
            role="sysadmin",
            phone="+905551234567",
            email="admin@test.com",
        )
        assert r["added"] is True
        assert r["total_contacts"] == 1

    def test_schedule_test(self):
        s = self.rpb.define_scenario(
            name="Test Scenario",
        )
        r = self.rpb.schedule_test(
            scenario_id=s["scenario_id"],
            frequency="quarterly",
        )
        assert r["scheduled"] is True
        assert r["interval_months"] == 3

    def test_schedule_test_not_found(self):
        r = self.rpb.schedule_test(
            scenario_id="nonexistent",
        )
        assert r["scheduled"] is False


# ── LegacyEncryptionManager Testleri ──


class TestLegacyEncryptionManager:
    """Miras şifreleme yöneticisi testleri."""

    def setup_method(self):
        self.lem = LegacyEncryptionManager()

    def test_init(self):
        assert self.lem.key_count == 0

    def test_generate_key(self):
        r = self.lem.generate_key(
            purpose="backup",
            algorithm="aes256",
            expiry_days=365,
        )
        assert r["generated"] is True
        assert r["strength"] == "strong"
        assert self.lem.key_count == 1

    def test_generate_key_military(self):
        r = self.lem.generate_key(
            algorithm="rsa4096",
        )
        assert r["strength"] == "military"

    def test_set_encryption_standard(self):
        self.lem.generate_key(
            algorithm="aes256",
        )
        r = self.lem.set_encryption_standard(
            standard="aes256",
            min_key_length=256,
        )
        assert r["set"] is True
        assert r["grade"] == "military"
        assert r["compliant_keys"] == 1

    def test_set_encryption_standard_weak(self):
        r = self.lem.set_encryption_standard(
            standard="aes128",
            min_key_length=64,
        )
        assert r["grade"] == "weak"

    def test_manage_access_grant(self):
        k = self.lem.generate_key(
            purpose="test",
        )
        r = self.lem.manage_access(
            key_id=k["key_id"],
            authorized_users=["alice", "bob"],
            action="grant",
        )
        assert r["managed"] is True
        assert r["authorized_count"] == 2

    def test_manage_access_revoke(self):
        k = self.lem.generate_key(
            purpose="test",
        )
        self.lem.manage_access(
            key_id=k["key_id"],
            authorized_users=["alice"],
            action="grant",
        )
        r = self.lem.manage_access(
            key_id=k["key_id"],
            action="revoke",
        )
        assert r["managed"] is True
        assert r["authorized_count"] == 0

    def test_manage_access_not_found(self):
        r = self.lem.manage_access(
            key_id="nonexistent",
        )
        assert r["managed"] is False

    def test_enable_emergency_access(self):
        k = self.lem.generate_key(
            purpose="legacy",
        )
        r = self.lem.enable_emergency_access(
            key_id=k["key_id"],
            emergency_contact="spouse@mail.com",
            delay_hours=48,
        )
        assert r["enabled"] is True
        assert r["status"] == "armed"
        assert r["delay_hours"] == 48

    def test_enable_emergency_not_found(self):
        r = self.lem.enable_emergency_access(
            key_id="nonexistent",
        )
        assert r["enabled"] is False

    def test_get_audit_log(self):
        self.lem.generate_key(
            purpose="test",
        )
        r = self.lem.get_audit_log()
        assert r["retrieved"] is True
        assert r["count"] >= 1


# ── PeriodicVerifier Testleri ──


class TestPeriodicVerifier:
    """Periyodik doğrulayıcı testleri."""

    def setup_method(self):
        self.pv = PeriodicVerifier()

    def test_init(self):
        assert self.pv.verification_count == 0

    def test_verify_backup_full(self):
        r = self.pv.verify_backup(
            backup_id="bk_test1",
            check_integrity=True,
            check_encryption=True,
        )
        assert r["verified"] is True
        assert r["status"] == "passed"
        assert r["pass_rate"] == 100.0

    def test_verify_backup_partial(self):
        r = self.pv.verify_backup(
            backup_id="bk_test2",
            check_integrity=False,
            check_encryption=True,
        )
        assert r["verified"] is True
        assert r["status"] == "partial"

    def test_check_integrity(self):
        items = [
            {"name": "file1.zip", "size_mb": 50},
            {"name": "file2.zip", "size_mb": 100},
            {"name": "corrupted.zip", "size_mb": 0},
        ]
        r = self.pv.check_integrity(items=items)
        assert r["checked"] is True
        assert r["intact_count"] == 2
        assert r["corrupted_count"] == 1

    def test_check_integrity_empty(self):
        r = self.pv.check_integrity()
        assert r["checked"] is True
        assert r["total_checked"] == 0

    def test_test_access(self):
        r = self.pv.test_access(
            targets=["aws_s3", "google_drive"],
        )
        assert r["tested"] is True
        assert r["accessible"] == 2
        assert r["total_tested"] == 2

    def test_test_access_empty(self):
        r = self.pv.test_access()
        assert r["tested"] is True
        assert r["total_tested"] == 0

    def test_generate_report(self):
        self.pv.verify_backup(
            backup_id="bk1",
        )
        self.pv.verify_backup(
            backup_id="bk2",
        )
        r = self.pv.generate_report()
        assert r["generated"] is True
        assert r["total_verifications"] == 2
        assert r["health"] == "excellent"

    def test_generate_report_no_data(self):
        r = self.pv.generate_report()
        assert r["health"] == "no_data"

    def test_detect_issues_none(self):
        self.pv.verify_backup(
            backup_id="bk1",
        )
        r = self.pv.detect_issues()
        assert r["detected"] is True
        assert r["issue_count"] == 0
        assert r["max_severity"] == "none"

    def test_detect_issues_with_partial(self):
        self.pv.verify_backup(
            backup_id="bk1",
            check_integrity=False,
        )
        r = self.pv.detect_issues()
        assert r["detected"] is True
        assert r["issue_count"] >= 1
        assert r["max_severity"] == "medium"


# ── DigitalWillManager Testleri ──


class TestDigitalWillManager:
    """Dijital vasiyet yöneticisi testleri."""

    def setup_method(self):
        self.dwm = DigitalWillManager()

    def test_init(self):
        assert self.dwm.will_count == 0

    def test_create_will(self):
        r = self.dwm.create_will(
            title="My Digital Will",
            description="Main will",
        )
        assert r["created"] is True
        assert r["status"] == "draft"
        assert r["version"] == 1
        assert self.dwm.will_count == 1

    def test_distribute_assets(self):
        w = self.dwm.create_will(
            title="Will",
        )
        r = self.dwm.distribute_assets(
            will_id=w["will_id"],
            distributions=[
                {"beneficiary": "Ali", "percentage": 60},
                {"beneficiary": "Veli", "percentage": 40},
            ],
        )
        assert r["distributed"] is True
        assert r["total_pct"] == 100
        assert r["coverage"] == "complete"

    def test_distribute_assets_partial(self):
        w = self.dwm.create_will(
            title="Will",
        )
        r = self.dwm.distribute_assets(
            will_id=w["will_id"],
            distributions=[
                {"beneficiary": "Ali", "percentage": 50},
            ],
        )
        assert r["coverage"] == "partial"
        assert r["remaining_pct"] == 50

    def test_distribute_exceeds_100(self):
        w = self.dwm.create_will(
            title="Will",
        )
        r = self.dwm.distribute_assets(
            will_id=w["will_id"],
            distributions=[
                {"beneficiary": "A", "percentage": 70},
                {"beneficiary": "B", "percentage": 50},
            ],
        )
        assert r["distributed"] is False
        assert r["error"] == "exceeds_100_percent"

    def test_distribute_not_found(self):
        r = self.dwm.distribute_assets(
            will_id="nonexistent",
        )
        assert r["distributed"] is False

    def test_store_instructions(self):
        w = self.dwm.create_will(
            title="Will",
        )
        r = self.dwm.store_instructions(
            will_id=w["will_id"],
            instructions=[
                "Contact lawyer",
                "Notify beneficiaries",
                "Execute distributions",
            ],
        )
        assert r["stored"] is True
        assert r["instruction_count"] == 3

    def test_store_instructions_not_found(self):
        r = self.dwm.store_instructions(
            will_id="nonexistent",
        )
        assert r["stored"] is False

    def test_update_will(self):
        w = self.dwm.create_will(
            title="Old Title",
        )
        r = self.dwm.update_will(
            will_id=w["will_id"],
            changes={"title": "New Title"},
        )
        assert r["updated"] is True
        assert r["old_version"] == 1
        assert r["new_version"] == 2
        assert r["status"] == "updated"

    def test_update_will_not_found(self):
        r = self.dwm.update_will(
            will_id="nonexistent",
        )
        assert r["updated"] is False

    def test_plan_execution_ready(self):
        w = self.dwm.create_will(
            title="Will",
        )
        self.dwm.distribute_assets(
            will_id=w["will_id"],
            distributions=[
                {"beneficiary": "Ali", "percentage": 100},
            ],
        )
        self.dwm.store_instructions(
            will_id=w["will_id"],
            instructions=["Step 1"],
        )
        self.dwm.update_will(
            will_id=w["will_id"],
            changes={"title": "Updated"},
        )
        r = self.dwm.plan_execution(
            will_id=w["will_id"],
        )
        assert r["planned"] is True
        assert r["readiness"] == "ready"

    def test_plan_execution_not_started(self):
        w = self.dwm.create_will(
            title="Empty Will",
        )
        r = self.dwm.plan_execution(
            will_id=w["will_id"],
        )
        assert r["readiness"] == "not_started"

    def test_plan_execution_not_found(self):
        r = self.dwm.plan_execution(
            will_id="nonexistent",
        )
        assert r["planned"] is False


# ── DigitalLegacyOrchestrator Testleri ──


class TestDigitalLegacyOrchestrator:
    """Dijital miras orkestratör testleri."""

    def setup_method(self):
        self.orch = DigitalLegacyOrchestrator()

    def test_init(self):
        r = self.orch.get_analytics()
        assert r["retrieved"] is True
        assert r["components"] == 8

    def test_full_legacy_cycle(self):
        r = self.orch.full_legacy_cycle(
            assets=[
                {"name": "Gmail", "type": "account", "platform": "google"},
                {"name": "BTC", "type": "cryptocurrency", "value": 5000},
            ],
            backup_dest="aws_s3",
            encryption="aes256",
        )
        assert r["completed"] is True
        assert r["cataloged"] == 2

    def test_full_legacy_cycle_empty(self):
        r = self.orch.full_legacy_cycle()
        assert r["completed"] is True
        assert r["cataloged"] == 0

    def test_peace_of_mind_unprotected(self):
        r = self.orch.peace_of_mind_check()
        assert r["checked"] is True
        assert r["status"] == "unprotected"
        assert r["peace_score"] == 0

    def test_peace_of_mind_after_cycle(self):
        self.orch.full_legacy_cycle(
            assets=[
                {"name": "Gmail", "type": "account"},
            ],
        )
        r = self.orch.peace_of_mind_check()
        assert r["checked"] is True
        assert r["peace_score"] >= 50

    def test_get_analytics(self):
        r = self.orch.get_analytics()
        assert r["retrieved"] is True
        assert r["assets"] == 0
        assert r["vaults"] == 0
        assert r["backups"] == 0

    def test_get_analytics_after_cycle(self):
        self.orch.full_legacy_cycle(
            assets=[
                {"name": "Gmail", "type": "account"},
            ],
        )
        r = self.orch.get_analytics()
        assert r["assets"] == 1
        assert r["backups"] == 1
        assert r["encryption_keys"] == 1
