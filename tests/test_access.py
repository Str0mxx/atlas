"""DM Pairing & Dynamic Access sistemi testleri."""

import json
import time
import pytest

from app.models.access_models import (
    AccessAuditEntry, AccessConfig, AllowlistEntry, ChannelType,
    DMPolicy, DMPolicyMode, PairedDevice, PairingRequest, PairingStatus,
)
from app.core.access.pairing import PairingManager
from app.core.access.allowlist import AllowlistManager
from app.core.access.dm_policy import DMPolicyManager


# ======================= Model Tests =======================


class TestAccessModels:
    """Erisim modelleri testleri."""

    def test_pairing_request_defaults(self):
        """PairingRequest varsayilan degerleri."""
        req = PairingRequest()
        assert req.request_id == ""
        assert req.status == PairingStatus.PENDING
        assert req.attempts == 0
        assert req.channel == ChannelType.GENERIC

    def test_pairing_request_custom(self):
        """PairingRequest ozel degerlerle."""
        req = PairingRequest(request_id="r1", sender_id="u1", channel=ChannelType.TELEGRAM, pairing_code="123456")
        assert req.request_id == "r1"
        assert req.sender_id == "u1"
        assert req.channel == ChannelType.TELEGRAM
        assert req.pairing_code == "123456"

    def test_paired_device_defaults(self):
        """PairedDevice varsayilan degerleri."""
        dev = PairedDevice()
        assert dev.is_active is True
        assert dev.permissions == []

    def test_allowlist_entry(self):
        """AllowlistEntry olusturma."""
        entry = AllowlistEntry(entry_id="e1", sender_id="u1", channel=ChannelType.WHATSAPP, is_wildcard=True)
        assert entry.is_wildcard is True
        assert entry.channel == ChannelType.WHATSAPP

    def test_dm_policy_defaults(self):
        """DMPolicy varsayilan degerleri."""
        policy = DMPolicy()
        assert policy.mode == DMPolicyMode.PAIRING
        assert policy.pairing_code_length == 6
        assert policy.max_attempts == 3

    def test_access_config(self):
        """AccessConfig varsayilan degerleri."""
        config = AccessConfig()
        assert config.default_policy == DMPolicyMode.PAIRING
        assert config.enable_qr_pairing is True

    def test_channel_type_values(self):
        """ChannelType degerleri."""
        assert ChannelType.TELEGRAM.value == "telegram"
        assert ChannelType.DISCORD.value == "discord"
        assert ChannelType.SIGNAL.value == "signal"

    def test_pairing_status_values(self):
        """PairingStatus degerleri."""
        assert PairingStatus.PENDING.value == "pending"
        assert PairingStatus.PAIRED.value == "paired"
        assert PairingStatus.BLOCKED.value == "blocked"

    def test_access_audit_entry(self):
        """AccessAuditEntry olusturma."""
        entry = AccessAuditEntry(entry_id="a1", action="check", sender_id="u1", result="allowed")
        assert entry.action == "check"
        assert entry.result == "allowed"


# ======================= PairingManager Tests =======================


class TestPairingManager:
    """Eslestirme yoneticisi testleri."""

    def test_generate_code(self):
        """Eslestirme kodu uretimi."""
        pm = PairingManager()
        req = pm.generate_code("user1", ChannelType.TELEGRAM)
        assert req.sender_id == "user1"
        assert req.channel == ChannelType.TELEGRAM
        assert len(req.pairing_code) == 6
        assert req.status == PairingStatus.PENDING

    def test_generate_code_custom_length(self):
        """Ozel uzunlukta kod uretimi."""
        pm = PairingManager(code_length=8)
        req = pm.generate_code("user1")
        assert len(req.pairing_code) == 8

    def test_verify_code_success(self):
        """Basarili kod dogrulama."""
        pm = PairingManager()
        req = pm.generate_code("user1")
        assert pm.verify_code("user1", req.pairing_code) is True

    def test_verify_code_wrong(self):
        """Hatali kod dogrulama."""
        pm = PairingManager()
        pm.generate_code("user1")
        assert pm.verify_code("user1", "000000") is False

    def test_verify_code_no_request(self):
        """Istek olmadan dogrulama."""
        pm = PairingManager()
        assert pm.verify_code("user1", "123456") is False

    def test_verify_code_expired(self):
        """Suresi dolmus kod dogrulama."""
        pm = PairingManager(expiry_seconds=0)
        req = pm.generate_code("user1")
        import time as t; t.sleep(0.01)
        assert pm.verify_code("user1", req.pairing_code) is False

    def test_verify_code_blocked_after_max_attempts(self):
        """Cok fazla denemede engelleme."""
        pm = PairingManager(max_attempts=1)
        pm.generate_code("user1")
        pm.verify_code("user1", "000000")
        pm.verify_code("user1", "000000")
        assert pm.is_blocked("user1") is True

    def test_unblock(self):
        """Engel kaldirma."""
        pm = PairingManager(max_attempts=1)
        pm.generate_code("user1")
        pm.verify_code("user1", "000000")
        pm.verify_code("user1", "000000")
        assert pm.unblock("user1") is True
        assert pm.is_blocked("user1") is False

    def test_blocked_generate_raises(self):
        """Engelli kullanici kod uretme hatasi."""
        pm = PairingManager(max_attempts=1)
        pm.generate_code("user1")
        pm.verify_code("user1", "000000")
        pm.verify_code("user1", "000000")
        with pytest.raises(ValueError):
            pm.generate_code("user1")

    def test_get_request(self):
        """Istek sorgulama."""
        pm = PairingManager()
        pm.generate_code("user1")
        req = pm.get_request("user1")
        assert req is not None

    def test_paired_devices(self):
        """Eslestirilmis cihaz listesi."""
        pm = PairingManager()
        req = pm.generate_code("user1")
        pm.verify_code("user1", req.pairing_code)
        devices = pm.get_paired_devices()
        assert len(devices) == 1

    def test_unpair(self):
        """Eslestirme kaldirma."""
        pm = PairingManager()
        req = pm.generate_code("user1")
        pm.verify_code("user1", req.pairing_code)
        devices = pm.get_paired_devices()
        assert pm.unpair(devices[0].device_id) is True
        assert len(pm.get_paired_devices()) == 0

    def test_expire_old_requests(self):
        """Suresi dolmus istek temizleme."""
        pm = PairingManager(expiry_seconds=0)
        pm.generate_code("user1")
        import time as t; t.sleep(0.01)
        assert pm.expire_old_requests() >= 1

    def test_generate_qr_data(self):
        """QR kod verisi uretimi."""
        pm = PairingManager()
        req = pm.generate_code("user1", ChannelType.TELEGRAM)
        qr = pm.generate_qr_data(req)
        data = json.loads(qr)
        assert data["type"] == "atlas_pairing"

    def test_get_stats(self):
        """Istatistik kontrolu."""
        pm = PairingManager()
        pm.generate_code("user1")
        stats = pm.get_stats()
        assert stats["total_requests"] == 1

    def test_get_history(self):
        """Gecmis kayit kontrolu."""
        pm = PairingManager()
        pm.generate_code("user1")
        assert len(pm.get_history()) >= 1


# ======================= AllowlistManager Tests =======================


class TestAllowlistManager:
    """Izin listesi yoneticisi testleri."""

    def test_add_entry(self):
        """Izin listesine ekleme."""
        am = AllowlistManager()
        entry = am.add("user1", ChannelType.TELEGRAM)
        assert entry.sender_id == "user1"

    def test_is_allowed(self):
        """Izin kontrolu."""
        am = AllowlistManager()
        am.add("user1", ChannelType.TELEGRAM)
        assert am.is_allowed("user1", ChannelType.TELEGRAM) is True
        assert am.is_allowed("user2", ChannelType.TELEGRAM) is False

    def test_remove_entry(self):
        """Izin listesinden cikarma."""
        am = AllowlistManager()
        am.add("user1", ChannelType.TELEGRAM)
        assert am.remove("user1", ChannelType.TELEGRAM) is True

    def test_wildcard(self):
        """Wildcard izin."""
        am = AllowlistManager()
        am.add_wildcard(ChannelType.TELEGRAM)
        assert am.is_allowed("anyone", ChannelType.TELEGRAM) is True

    def test_get_entries(self):
        """Giris listesi sorgulama."""
        am = AllowlistManager()
        am.add("user1", ChannelType.TELEGRAM)
        am.add("user2", ChannelType.DISCORD)
        assert len(am.get_entries()) == 2

    def test_clear(self):
        """Kanal temizleme."""
        am = AllowlistManager()
        am.add("user1", ChannelType.TELEGRAM)
        am.add("user2", ChannelType.TELEGRAM)
        assert am.clear(ChannelType.TELEGRAM) == 2

    def test_import_list(self):
        """Toplu iceri aktarma."""
        am = AllowlistManager()
        entries = [{"sender_id": "u1", "channel": "telegram"}, {"sender_id": "u2", "channel": "discord"}]
        count = am.import_list(entries)
        assert count == 2

    def test_export_list(self):
        """Disi aktarma."""
        am = AllowlistManager()
        am.add("user1", ChannelType.TELEGRAM)
        exported = am.export_list(ChannelType.TELEGRAM)
        assert len(exported) == 1

    def test_doctor_repair(self):
        """Onarim islemi."""
        am = AllowlistManager()
        am.add("user1", ChannelType.TELEGRAM)
        repairs = am.doctor_repair()
        assert isinstance(repairs, list)

    def test_get_stats(self):
        """Istatistik kontrolu."""
        am = AllowlistManager()
        am.add("user1", ChannelType.TELEGRAM)
        assert am.get_stats()["total_entries"] == 1


# ======================= DMPolicyManager Tests =======================


class TestDMPolicyManager:
    """DM politika yoneticisi testleri."""

    def test_set_policy(self):
        """Politika ayarlama."""
        dpm = DMPolicyManager()
        policy = dpm.set_policy(ChannelType.TELEGRAM, DMPolicyMode.OPEN)
        assert policy.mode == DMPolicyMode.OPEN

    def test_get_policy_default(self):
        """Varsayilan politika."""
        dpm = DMPolicyManager()
        policy = dpm.get_policy(ChannelType.TELEGRAM)
        assert policy.mode == DMPolicyMode.PAIRING

    def test_check_access_open(self):
        """Acik politika erisim kontrolu."""
        dpm = DMPolicyManager()
        dpm.set_policy(ChannelType.TELEGRAM, DMPolicyMode.OPEN)
        allowed, msg = dpm.check_access("user1", ChannelType.TELEGRAM)
        assert allowed is True

    def test_check_access_allowlist_denied(self):
        """Allowlist reddedilme."""
        dpm = DMPolicyManager()
        am = AllowlistManager()
        dpm.set_allowlist_manager(am)
        dpm.set_policy(ChannelType.TELEGRAM, DMPolicyMode.ALLOWLIST)
        allowed, _ = dpm.check_access("user1", ChannelType.TELEGRAM)
        assert allowed is False

    def test_check_access_allowlist_allowed(self):
        """Allowlist izin."""
        dpm = DMPolicyManager()
        am = AllowlistManager()
        am.add("user1", ChannelType.TELEGRAM)
        dpm.set_allowlist_manager(am)
        dpm.set_policy(ChannelType.TELEGRAM, DMPolicyMode.ALLOWLIST)
        allowed, _ = dpm.check_access("user1", ChannelType.TELEGRAM)
        assert allowed is True

    def test_check_access_pairing_denied(self):
        """Pairing reddedilme."""
        dpm = DMPolicyManager()
        pm = PairingManager()
        dpm.set_pairing_manager(pm)
        allowed, _ = dpm.check_access("user1", ChannelType.GENERIC)
        assert allowed is False

    def test_check_access_pairing_allowed(self):
        """Pairing erisim."""
        dpm = DMPolicyManager()
        pm = PairingManager()
        dpm.set_pairing_manager(pm)
        req = pm.generate_code("user1", ChannelType.GENERIC)
        pm.verify_code("user1", req.pairing_code)
        allowed, _ = dpm.check_access("user1", ChannelType.GENERIC)
        assert allowed is True

    def test_set_default_policy(self):
        """Varsayilan politika."""
        dpm = DMPolicyManager()
        dpm.set_default_policy(DMPolicyMode.OPEN)
        assert dpm.get_policy(ChannelType.DISCORD).mode == DMPolicyMode.OPEN

    def test_audit_policies(self):
        """Politika denetimi."""
        dpm = DMPolicyManager()
        dpm.set_policy(ChannelType.TELEGRAM, DMPolicyMode.OPEN)
        warnings = dpm.audit_policies()
        assert len(warnings) >= 1

    def test_override_policy(self):
        """Politika override."""
        dpm = DMPolicyManager()
        dpm.override_policy(ChannelType.TELEGRAM, DMPolicyMode.OPEN)
        assert dpm.get_policy(ChannelType.TELEGRAM).mode == DMPolicyMode.OPEN

    def test_get_all_policies(self):
        """Tum politikalar."""
        dpm = DMPolicyManager()
        dpm.set_policy(ChannelType.TELEGRAM, DMPolicyMode.OPEN)
        dpm.set_policy(ChannelType.DISCORD, DMPolicyMode.ALLOWLIST)
        assert len(dpm.get_all_policies()) == 2

    def test_get_audit_log(self):
        """Denetim gunlugu."""
        dpm = DMPolicyManager()
        dpm.set_policy(ChannelType.TELEGRAM, DMPolicyMode.OPEN)
        dpm.check_access("user1", ChannelType.TELEGRAM)
        assert len(dpm.get_audit_log()) >= 1

    def test_get_stats(self):
        """Istatistik kontrolu."""
        dpm = DMPolicyManager()
        dpm.set_policy(ChannelType.TELEGRAM, DMPolicyMode.OPEN)
        assert dpm.get_stats()["total_policies"] == 1
