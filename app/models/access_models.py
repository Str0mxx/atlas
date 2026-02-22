"""DM Pairing & Dynamic Access modelleri."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DMPolicyMode(str, Enum):
    """DM politika modlari."""
    PAIRING = "pairing"
    OPEN = "open"
    ALLOWLIST = "allowlist"


class PairingStatus(str, Enum):
    """Eslestirme durumlari."""
    PENDING = "pending"
    PAIRED = "paired"
    EXPIRED = "expired"
    BLOCKED = "blocked"
    REJECTED = "rejected"


class ChannelType(str, Enum):
    """Kanal turleri."""
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    SLACK = "slack"
    SIGNAL = "signal"
    IMESSAGE = "imessage"
    GENERIC = "generic"


class PairingRequest(BaseModel):
    """Eslestirme istegi modeli."""
    request_id: str = ""
    sender_id: str = ""
    channel: ChannelType = ChannelType.GENERIC
    pairing_code: str = ""
    created_at: float = 0.0
    expires_at: float = 0.0
    attempts: int = 0
    status: PairingStatus = PairingStatus.PENDING
    metadata: dict[str, Any] = Field(default_factory=dict)


class PairedDevice(BaseModel):
    """Eslestirilmis cihaz modeli."""
    device_id: str = ""
    sender_id: str = ""
    channel: ChannelType = ChannelType.GENERIC
    paired_at: float = 0.0
    last_activity: float = 0.0
    is_active: bool = True
    display_name: str = ""
    permissions: list[str] = Field(default_factory=list)


class AllowlistEntry(BaseModel):
    """Izin listesi girisi modeli."""
    entry_id: str = ""
    sender_id: str = ""
    channel: ChannelType = ChannelType.GENERIC
    added_at: float = 0.0
    added_by: str = ""
    is_wildcard: bool = False
    notes: str = ""


class DMPolicy(BaseModel):
    """DM politikasi modeli."""
    channel: ChannelType = ChannelType.GENERIC
    mode: DMPolicyMode = DMPolicyMode.PAIRING
    pairing_code_length: int = 6
    pairing_expiry_seconds: int = 300
    max_attempts: int = 3
    block_duration_seconds: int = 600
    auto_approve: bool = False


class AccessAuditEntry(BaseModel):
    """Erisim denetim girisi modeli."""
    entry_id: str = ""
    action: str = ""
    sender_id: str = ""
    channel: ChannelType = ChannelType.GENERIC
    result: str = ""
    timestamp: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)


class AccessConfig(BaseModel):
    """Erisim yapilandirma modeli."""
    default_policy: DMPolicyMode = DMPolicyMode.PAIRING
    pairing_code_length: int = 6
    pairing_expiry: int = 300
    max_attempts: int = 3
    block_duration: int = 600
    enable_qr_pairing: bool = True
    string_id_enforcement: bool = True
    audit_enabled: bool = True
