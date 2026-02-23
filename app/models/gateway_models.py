"""ATLAS Gateway & Infrastructure modelleri."""

from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class AuthMode(str, Enum):
    """Kimlik dogrulama modu."""

    TOKEN = "token"
    NONE = "none"
    BASIC = "basic"


class ChannelStatus(str, Enum):
    """Kanal durumu."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    RESTARTING = "restarting"
    CRASH_LOOP = "crash_loop"


class GatewayToken(BaseModel):
    """Gateway kimlik dogrulama jetonu.

    Attributes:
        token: Jeton degeri (UUID4).
        scope: Yetki kapsami.
        device_id: Cihaz tanimlayici.
        created_at: Olusturma zamani.
        last_used: Son kullanim zamani.
        expires_at: Sona erme zamani.
    """

    token: str = Field(
        default_factory=lambda: str(uuid4()),
    )
    scope: str = "operator.*"
    device_id: str = ""
    created_at: float = 0.0
    last_used: float = 0.0
    expires_at: float = 0.0


class PairedDevice(BaseModel):
    """Eslesmis cihaz bilgisi.

    Attributes:
        device_id: Cihaz tanimlayici.
        name: Cihaz adi.
        token: Kimlik dogrulama jetonu.
        scopes: Yetki kapsamlari.
        paired_at: Eslesme zamani.
        last_seen: Son gorulme zamani.
    """

    device_id: str = ""
    name: str = ""
    token: str = ""
    scopes: list[str] = Field(
        default_factory=list,
    )
    paired_at: float = 0.0
    last_seen: float = 0.0


class ChannelHealthStatus(BaseModel):
    """Kanal saglik durumu.

    Attributes:
        channel: Kanal adi.
        status: Kanal durumu.
        last_check: Son kontrol zamani.
        check_interval_minutes: Kontrol araligi.
        crash_count: Cokme sayisi.
        last_restart: Son yeniden baslatma.
        uptime_seconds: Calisma suresi.
        error_message: Hata mesaji.
    """

    channel: str = ""
    status: ChannelStatus = ChannelStatus.HEALTHY
    last_check: float = 0.0
    check_interval_minutes: int = 5
    crash_count: int = 0
    last_restart: float = 0.0
    uptime_seconds: float = 0.0
    error_message: str = ""


class DiagnosticResult(BaseModel):
    """Tanilama sonucu.

    Attributes:
        category: Kategori.
        issue: Sorun aciklamasi.
        severity: Ciddiyet seviyesi.
        auto_fixable: Otomatik duzeltilebilir.
        fixed: Duzeltildi mi.
        details: Detaylar.
    """

    category: str = ""
    issue: str = ""
    severity: str = "warning"
    auto_fixable: bool = False
    fixed: bool = False
    details: str = ""


class UpdateResult(BaseModel):
    """Guncelleme sonucu.

    Attributes:
        version: Hedef surum.
        success: Basarili mi.
        doctor_result: Doktor sonuclari.
        restart_required: Yeniden baslatma gerekli.
        context_preserved: Baglam korundu.
        error: Hata mesaji.
    """

    version: str = ""
    success: bool = False
    doctor_result: dict = Field(
        default_factory=dict,
    )
    restart_required: bool = False
    context_preserved: bool = False
    error: str = ""


class ConfigDiff(BaseModel):
    """Yapilandirma farki.

    Attributes:
        key: Ayar anahtari.
        old_value: Eski deger.
        new_value: Yeni deger.
        action: Islem turu.
    """

    key: str = ""
    old_value: str = ""
    new_value: str = ""
    action: str = "changed"
