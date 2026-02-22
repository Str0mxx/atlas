"""DM politika yoneticisi - kanal bazli erisim politikasi yonetimi.

Her kanal icin eslestirme, acik veya izin listesi modunu ayarlar ve
erisim kontrolu saglar.
"""

import logging
import time
import uuid
from typing import Optional

from app.models.access_models import (
    AccessAuditEntry, AccessConfig, ChannelType, DMPolicy, DMPolicyMode, PairingStatus,
)

logger = logging.getLogger(__name__)


class DMPolicyManager:
    """Kanal bazli DM politikasi yoneticisi."""

    def __init__(self, config: Optional[AccessConfig] = None) -> None:
        """DMPolicyManager baslatici."""
        self.config = config or AccessConfig()
        self._policies: dict[str, DMPolicy] = {}
        self._audit_log: list[AccessAuditEntry] = []
        self._history: list[dict] = []
        self._pairing_manager = None
        self._allowlist_manager = None

    def set_pairing_manager(self, manager: object) -> None:
        """Eslestirme yoneticisini baglar."""
        self._pairing_manager = manager

    def set_allowlist_manager(self, manager: object) -> None:
        """Izin listesi yoneticisini baglar."""
        self._allowlist_manager = manager

    def _record_history(self, action: str, details: dict) -> None:
        """Gecmis kaydini tutar."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details})

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        mode_counts: dict[str, int] = {}
        for policy in self._policies.values():
            m = policy.mode.value
            mode_counts[m] = mode_counts.get(m, 0) + 1
        return {"total_policies": len(self._policies), "mode_distribution": mode_counts, "audit_entries": len(self._audit_log), "history_count": len(self._history), "default_policy": self.config.default_policy.value}

    def set_policy(self, channel: ChannelType, mode: DMPolicyMode) -> DMPolicy:
        """Kanal icin politika belirler."""
        policy = DMPolicy(channel=channel, mode=mode, pairing_code_length=self.config.pairing_code_length, pairing_expiry_seconds=self.config.pairing_expiry, max_attempts=self.config.max_attempts, block_duration_seconds=self.config.block_duration)
        self._policies[channel.value] = policy
        self._record_history("set_policy", {"channel": channel.value, "mode": mode.value})
        return policy

    def get_policy(self, channel: ChannelType) -> DMPolicy:
        """Kanal icin gecerli politikayi dondurur."""
        if channel.value in self._policies:
            return self._policies[channel.value]
        return DMPolicy(channel=channel, mode=self.config.default_policy, pairing_code_length=self.config.pairing_code_length, pairing_expiry_seconds=self.config.pairing_expiry, max_attempts=self.config.max_attempts, block_duration_seconds=self.config.block_duration)

    def check_access(self, sender_id: str, channel: ChannelType) -> tuple[bool, str]:
        """Gondericinin erisim iznini kontrol eder."""
        policy = self.get_policy(channel)
        audit = AccessAuditEntry(entry_id=str(uuid.uuid4()), action="check_access", sender_id=sender_id, channel=channel, timestamp=time.time())
        if policy.mode == DMPolicyMode.OPEN:
            audit.result = "allowed"
            audit.details = {"reason": "open_policy"}
            self._audit_log.append(audit)
            return True, "Access granted: open policy"
        if policy.mode == DMPolicyMode.ALLOWLIST:
            if self._allowlist_manager and self._allowlist_manager.is_allowed(sender_id, channel):
                audit.result = "allowed"
                audit.details = {"reason": "allowlist"}
                self._audit_log.append(audit)
                return True, "Access granted: allowlist"
            audit.result = "denied"
            audit.details = {"reason": "not_in_allowlist"}
            self._audit_log.append(audit)
            return False, "Access denied: not in allowlist"
        if policy.mode == DMPolicyMode.PAIRING:
            if self._pairing_manager:
                for device in self._pairing_manager.get_paired_devices():
                    if device.sender_id == sender_id and device.channel == channel and device.is_active:
                        audit.result = "allowed"
                        audit.details = {"reason": "paired_device"}
                        self._audit_log.append(audit)
                        return True, "Access granted: paired device"
            audit.result = "denied"
            audit.details = {"reason": "not_paired"}
            self._audit_log.append(audit)
            return False, "Access denied: pairing required"
        audit.result = "denied"
        self._audit_log.append(audit)
        return False, "Access denied: unknown policy mode"

    def set_default_policy(self, mode: DMPolicyMode) -> None:
        """Varsayilan politikayi ayarlar."""
        self.config.default_policy = mode
        self._record_history("set_default_policy", {"mode": mode.value})

    def get_all_policies(self) -> list[DMPolicy]:
        """Tum politikalari dondurur."""
        return list(self._policies.values())

    def audit_policies(self) -> list[str]:
        """Politikalarin guvenlik denetimini yapar."""
        warnings: list[str] = []
        if self.config.default_policy == DMPolicyMode.OPEN:
            warnings.append("WARNING: Default policy is OPEN - all senders allowed")
        for ch, policy in self._policies.items():
            if policy.mode == DMPolicyMode.OPEN:
                warnings.append(f"WARNING: Channel {ch} has OPEN policy")
            if policy.max_attempts > 10:
                warnings.append(f"WARNING: Channel {ch} allows too many attempts ({policy.max_attempts})")
        self._record_history("audit_policies", {"warnings": len(warnings)})
        return warnings

    def override_policy(self, channel: ChannelType, mode: DMPolicyMode) -> DMPolicy:
        """Kanal politikasini gecici olarak degistirir."""
        policy = self.set_policy(channel, mode)
        self._record_history("override_policy", {"channel": channel.value, "mode": mode.value})
        return policy

    def get_audit_log(self) -> list[AccessAuditEntry]:
        """Denetim gunlugunu dondurur."""
        return list(self._audit_log)
