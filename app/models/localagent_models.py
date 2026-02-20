"""
Local Machine Agent sistem modelleri.

Pydantic modelleri ve enum tanimlari.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enumlar ─────────────────────────────────────────────────────────────────


class ConnectionState(str, Enum):
    """Baglanti durumu."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class CommandStatus(str, Enum):
    """Komut durumu."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ProcessState(str, Enum):
    """Proses durumu."""

    RUNNING = "running"
    SLEEPING = "sleeping"
    STOPPED = "stopped"
    ZOMBIE = "zombie"
    UNKNOWN = "unknown"


class CaptureType(str, Enum):
    """Ekran yakalama tipi."""

    SCREEN = "screen"
    REGION = "region"
    WINDOW = "window"
    RECORDING = "recording"


class RiskLevel(str, Enum):
    """Risk seviyesi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FileType(str, Enum):
    """Dosya tipi."""

    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    OTHER = "other"


# ── Pydantic Modelleri ───────────────────────────────────────────────────────


class BridgeStatus(BaseModel):
    """Agent Bridge baglanti durumu."""

    connected: bool = Field(description="Bagli mi")
    authenticated: bool = Field(default=False, description="Kimlik dogrulandi mi")
    host: str = Field(default="", description="Baglantili sunucu")
    port: int = Field(default=0, ge=0, description="Port numarasi")
    channel_id: str = Field(default="", description="Kanal ID")
    reconnect_count: int = Field(default=0, ge=0, description="Yeniden baglanti sayisi")


class BridgeSummary(BaseModel):
    """AgentBridge ozeti."""

    connected: bool = Field(description="Bagli mi")
    authenticated: bool = Field(description="Kimlik dogrulandi mi")
    reconnect_count: int = Field(ge=0, description="Yeniden baglanti sayisi")
    stats: dict[str, int] = Field(description="Istatistikler")


class CommandResult(BaseModel):
    """Komut yurütme sonucu."""

    execution_id: str = Field(description="Yurutme ID")
    command: str = Field(description="Calistirilan komut")
    status: CommandStatus = Field(description="Komut durumu")
    stdout: str = Field(default="", description="Standart cikti")
    stderr: str = Field(default="", description="Hata ciktisi")
    return_code: int = Field(default=0, description="Donus kodu")
    duration: float = Field(default=0.0, ge=0.0, description="Sure (saniye)")
    timestamp: float = Field(description="Unix zaman damgasi")


class ExecutorSummary(BaseModel):
    """ShellExecutor ozeti."""

    working_directory: str = Field(description="Calisma dizini")
    env_var_count: int = Field(ge=0, description="Ortam degiskeni sayisi")
    history_count: int = Field(ge=0, description="Gecmis kayit sayisi")
    stats: dict[str, int] = Field(description="Istatistikler")


class FileEntry(BaseModel):
    """Dosya sistemi girisi."""

    name: str = Field(description="Dosya adi")
    path: str = Field(description="Tam yol")
    type: FileType = Field(description="Dosya tipi")
    size: int = Field(default=0, ge=0, description="Boyut (bayt)")
    modified: float = Field(default=0.0, description="Son degisiklik zamani")
    exists: bool = Field(default=True, description="Mevcut mu")


class SearchResult(BaseModel):
    """Dosya arama sonucu."""

    pattern: str = Field(description="Arama deseni")
    root: str = Field(description="Kök dizin")
    matches: list[str] = Field(default_factory=list, description="Eslesen yollar")
    count: int = Field(ge=0, description="Sonuc sayisi")
    truncated: bool = Field(default=False, description="Kisaltildi mi")


class FilePermissions(BaseModel):
    """Dosya izinleri."""

    path: str = Field(description="Dosya yolu")
    readable: bool = Field(description="Okunabilir mi")
    writable: bool = Field(description="Yazilabilir mi")
    executable: bool = Field(description="Calistirilabilir mi")
    mode: str = Field(default="", description="Izin modu (octal)")


class NavigatorSummary(BaseModel):
    """FileSystemNavigator ozeti."""

    base_path: str = Field(description="Taban yol")
    stats: dict[str, int] = Field(description="Istatistikler")


class ProcessInfo(BaseModel):
    """Proses bilgisi."""

    pid: int = Field(ge=0, description="Proses ID")
    name: str = Field(default="", description="Proses adi")
    state: ProcessState = Field(
        default=ProcessState.UNKNOWN, description="Proses durumu"
    )
    cpu_percent: float = Field(default=0.0, ge=0.0, description="CPU kullanimi (%)")
    memory_mb: float = Field(
        default=0.0, ge=0.0, description="Bellek kullanimi (MB)"
    )
    started_by_us: bool = Field(default=False, description="Bizim baslattigimiz mi")


class ProcessSummary(BaseModel):
    """ProcessManager ozeti."""

    tracked_count: int = Field(ge=0, description="Izlenen proses sayisi")
    monitored_count: int = Field(ge=0, description="Monitore edilen sayisi")
    stats: dict[str, int] = Field(description="Istatistikler")


class ClipboardEntry(BaseModel):
    """Pano gecmis girisi."""

    content_preview: str = Field(description="Icerik onizlemesi (ilk 200 karakter)")
    format: str = Field(default="text", description="Icerik formati")
    timestamp: float = Field(description="Unix zaman damgasi")
    size: int = Field(ge=0, description="Icerik boyutu (karakter)")


class ClipboardSummary(BaseModel):
    """ClipboardAccess ozeti."""

    has_display: bool = Field(description="Gercek pano erisimi var mi")
    history_count: int = Field(ge=0, description="Gecmis kayit sayisi")
    current_format: str = Field(description="Mevcut format")
    stats: dict[str, int] = Field(description="Istatistikler")


class CaptureMetadata(BaseModel):
    """Ekran yakalama metadata."""

    capture_id: str = Field(description="Yakalama ID")
    type: CaptureType = Field(description="Yakalama tipi")
    format: str = Field(default="png", description="Goruntu formati")
    filepath: str = Field(default="", description="Dosya yolu")
    timestamp: float = Field(description="Unix zaman damgasi")
    width: int = Field(default=0, ge=0, description="Genislik (piksel)")
    height: int = Field(default=0, ge=0, description="Yukseklik (piksel)")
    size_bytes: int = Field(default=0, ge=0, description="Dosya boyutu (bayt)")


class CaptureSummary(BaseModel):
    """AgentScreenCapture ozeti."""

    has_display: bool = Field(description="Ekran erisimi var mi")
    capture_count: int = Field(ge=0, description="Toplam yakalama sayisi")
    is_recording: bool = Field(description="Kayit yapiliyor mu")
    stats: dict[str, int] = Field(description="Istatistikler")


class CheckResult(BaseModel):
    """Sandbox kontrol sonucu."""

    allowed: bool = Field(description="Izinli mi")
    reason: str = Field(default="", description="Karar aciklamasi")
    risk_score: float = Field(default=0.0, ge=0.0, description="Risk skoru")


class AuditEntry(BaseModel):
    """Denetim izi kaydi."""

    timestamp: float = Field(description="Unix zaman damgasi")
    action: str = Field(description="Eylem adi")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Eylem detaylari"
    )
    allowed: bool = Field(default=True, description="Izin verildi mi")


class SandboxSummary(BaseModel):
    """SandboxEnforcer ozeti."""

    enabled: bool = Field(description="Aktif mi")
    allowed_paths: int = Field(ge=0, description="Izinli yol sayisi")
    blocked_commands: int = Field(ge=0, description="Engelli komut sayisi")
    audit_entries: int = Field(ge=0, description="Denetim kaydi sayisi")
    stats: dict[str, int] = Field(description="Istatistikler")


class WhitelistEntry(BaseModel):
    """Whitelist girisi."""

    pattern: str = Field(description="Komut deseni")
    risk_level: str = Field(default="low", description="Risk seviyesi")
    description: str = Field(default="", description="Aciklama")
    added_at: float = Field(description="Eklenme zamani")


class WhitelistCheckResult(BaseModel):
    """Whitelist kontrol sonucu."""

    command: str = Field(description="Kontrol edilen komut")
    allowed: bool = Field(description="Izinli mi")
    matched_pattern: str = Field(default="", description="Eslesen desen")
    risk_score: float = Field(default=0.0, ge=0.0, description="Risk skoru")
    via_override: bool = Field(default=False, description="Override ile mi izin verildi")


class WhitelistSummary(BaseModel):
    """CommandWhitelist ozeti."""

    entry_count: int = Field(ge=0, description="Whitelist girisi sayisi")
    override_count: int = Field(ge=0, description="Override sayisi")
    log_count: int = Field(ge=0, description="Log kaydi sayisi")
    stats: dict[str, int] = Field(description="Istatistikler")


class LocalAgentConfig(BaseModel):
    """Local Agent konfigurasyonu."""

    enabled: bool = Field(default=True, description="Aktif mi")
    sandbox_mode: bool = Field(default=True, description="Sandbox modu")
    allowed_paths: str = Field(default="", description="Izinli yollar (virgülle ayri)")
    command_timeout: int = Field(
        default=30, ge=1, description="Komut zaman asimi (saniye)"
    )
    require_approval: bool = Field(
        default=False, description="Onay gerektir mi"
    )
