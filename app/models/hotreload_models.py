"""
Hot Reload & Live Config sistem modelleri.

Pydantic modelleri ve enum tanimlari.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enumlar ─────────────────────────────────────────────────────────────────


class FileEventType(str, Enum):
    """Dosya olay tipi."""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


class ReloadSource(str, Enum):
    """Yeniden yukleme kaynagi."""

    FILE = "file"
    API = "api"
    TELEGRAM = "telegram"
    MANUAL = "manual"
    ROLLBACK = "rollback"


class ChangeType(str, Enum):
    """Degisiklik tipi."""

    ADD = "add"
    UPDATE = "update"
    REMOVE = "remove"


class ValidationErrorType(str, Enum):
    """Dogrulama hata tipi."""

    WRONG_TYPE = "yanlis_tip"
    REQUIRED_MISSING = "zorunlu_alan_eksik"
    BELOW_MINIMUM = "minimum_altinda"
    ABOVE_MAXIMUM = "maximum_ustunde"
    TOO_SHORT = "cok_kisa"
    TOO_LONG = "cok_uzun"
    INVALID_VALUE = "gecersiz_deger"
    DEPENDENCY_ERROR = "bagimlilik_hatasi"


class RuleType(str, Enum):
    """Kural tipi."""

    DEPENDENCY = "dependency"
    CONFLICT = "conflict"
    REQUIRED_IF = "required_if"


class TelegramAction(str, Enum):
    """Telegram islem tipi."""

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    PENDING = "pending"


# ── Pydantic Modelleri ───────────────────────────────────────────────────────


class WatchEntry(BaseModel):
    """Izleme kaydi."""

    path: str = Field(description="Izlenen yol")
    recursive: bool = Field(default=False, description="Alt dizinler dahil mi")
    exists: bool = Field(default=True, description="Dosya/dizin mevcut mu")


class FileEvent(BaseModel):
    """Dosya degisiklik olayi."""

    path: str = Field(description="Degisen dosya yolu")
    event: FileEventType = Field(description="Olay tipi")
    timestamp: float = Field(description="Unix zaman damgasi")


class FilterConfig(BaseModel):
    """Filtre konfigurasyonu."""

    include: list[str] = Field(
        default_factory=list, description="Dahil edilen kaliplar"
    )
    exclude: list[str] = Field(
        default_factory=list, description="Hariç tutulan kaliplar"
    )


class WatcherSummary(BaseModel):
    """FileWatcher ozeti."""

    watched_count: int = Field(ge=0, description="Izlenen dosya sayisi")
    callback_count: int = Field(ge=0, description="Callback sayisi")
    include_filters: int = Field(ge=0, description="Dahil filtreleri")
    exclude_filters: int = Field(ge=0, description="Hariç filtreleri")
    debounce_ms: int = Field(ge=0, description="Debounce suresi")


class ConfigChange(BaseModel):
    """Konfig degisikligi."""

    key: str = Field(description="Degisen anahtar")
    old: Any = Field(default=None, description="Eski deger")
    new: Any = Field(default=None, description="Yeni deger")
    type: ChangeType = Field(
        default=ChangeType.UPDATE, description="Degisiklik tipi"
    )


class ReloadRecord(BaseModel):
    """Yeniden yukleme kaydi."""

    timestamp: float = Field(description="Unix zaman damgasi")
    source: str = Field(description="Kaynak")
    changes: list[dict] = Field(
        default_factory=list, description="Degisiklikler"
    )
    key_count: int = Field(ge=0, description="Toplam anahtar sayisi")


class ReloadResult(BaseModel):
    """Yeniden yukleme sonucu."""

    reloaded: bool = Field(description="Basarili mi")
    changed: bool = Field(default=False, description="Degisiklik var mi")
    changes: list[dict] = Field(
        default_factory=list, description="Degisiklikler"
    )
    source: str = Field(default="", description="Kaynak")
    error: str | None = Field(default=None, description="Hata mesaji")


class RollbackResult(BaseModel):
    """Geri alma sonucu."""

    rolled_back: bool = Field(description="Geri alindi mi")
    changes_reverted: int = Field(
        default=0, description="Geri alinan degisiklik sayisi"
    )
    reason: str | None = Field(default=None, description="Sebep")


class ReloaderSummary(BaseModel):
    """ConfigHotReloader ozeti."""

    key_count: int = Field(ge=0, description="Konfig anahtar sayisi")
    has_previous: bool = Field(description="Onceki konfig var mi")
    reload_count: int = Field(ge=0, description="Basarili yukleme sayisi")
    history_count: int = Field(ge=0, description="Gecmis kayit sayisi")
    listener_count: int = Field(ge=0, description="Dinleyici sayisi")


class PendingUpdate(BaseModel):
    """Onay bekleyen guncelleme."""

    chat_id: str = Field(description="Telegram chat ID")
    key: str = Field(description="Guncellenecek anahtar")
    old_value: Any = Field(default=None, description="Eski deger")
    new_value: Any = Field(default=None, description="Yeni deger")
    requested_at: float = Field(description="Talep zamani")


class UpdateRequest(BaseModel):
    """Guncelleme talep sonucu."""

    requested: bool = Field(description="Talep olusturuldu mu")
    request_id: str = Field(default="", description="Talep ID")
    key: str = Field(default="", description="Anahtar")
    message: str = Field(default="", description="Telegram mesaji")


class HistoryRecord(BaseModel):
    """Gecmis kaydi."""

    request_id: str = Field(default="", description="Talep ID")
    chat_id: str = Field(default="", description="Chat ID")
    key: str = Field(default="", description="Anahtar")
    old_value: Any = Field(default=None, description="Eski deger")
    new_value: Any = Field(default=None, description="Yeni deger")
    timestamp: float = Field(description="Unix zaman damgasi")
    action: str = Field(description="Islem (confirmed/cancelled)")


class TelegramInterfaceSummary(BaseModel):
    """TelegramConfigInterface ozeti."""

    config_keys: int = Field(ge=0, description="Konfig anahtar sayisi")
    pending_count: int = Field(ge=0, description="Bekleyen talep sayisi")
    history_count: int = Field(ge=0, description="Gecmis kayit sayisi")
    masked_keys: int = Field(ge=0, description="Maskeli anahtar sayisi")


class SchemaField(BaseModel):
    """Sema alani tanimi."""

    type: str = Field(default="str", description="Beklenen tip")
    required: bool = Field(default=False, description="Zorunlu mu")
    min: float | None = Field(default=None, description="Minimum deger")
    max: float | None = Field(default=None, description="Maximum deger")
    min_length: int | None = Field(default=None, description="Minimum uzunluk")
    max_length: int | None = Field(default=None, description="Maximum uzunluk")
    allowed: list[Any] = Field(
        default_factory=list, description="Izin verilen degerler"
    )
    default: Any = Field(default=None, description="Varsayilan deger")


class ValidationError(BaseModel):
    """Dogrulama hatasi."""

    key: str = Field(description="Hatalı anahtar")
    error: str = Field(description="Hata kodu")
    message: str = Field(description="Hata mesaji")
    severity: str = Field(default="error", description="Siddet (error/warning)")


class ValidationResult(BaseModel):
    """Dogrulama sonucu."""

    valid: bool = Field(description="Gecerli mi")
    errors: list[dict] = Field(
        default_factory=list, description="Hata listesi"
    )
    error_count: int = Field(ge=0, description="Hata sayisi")
    checked_keys: int = Field(ge=0, description="Kontrol edilen anahtar sayisi")


class ValidationRule(BaseModel):
    """Dogrulama kurali."""

    name: str = Field(description="Kural adi")
    description: str = Field(default="", description="Kural aciklamasi")
    keys: list[str] = Field(
        default_factory=list, description="Ilgili anahtarlar"
    )
    type: RuleType = Field(
        default=RuleType.DEPENDENCY, description="Kural tipi"
    )


class ErrorMessage(BaseModel):
    """Hata mesaji."""

    key: str = Field(default="", description="Anahtar")
    message: str = Field(description="Mesaj")
    severity: str = Field(default="error", description="Siddet")


class ValidationEngineSummary(BaseModel):
    """ValidationEngine ozeti."""

    schema_count: int = Field(ge=0, description="Sema sayisi")
    rule_count: int = Field(ge=0, description="Kural sayisi")
    last_error_count: int = Field(ge=0, description="Son hata sayisi")


class HotReloadConfig(BaseModel):
    """Hot reload konfigurasyonu."""

    enabled: bool = Field(default=True, description="Aktif mi")
    watch_interval_ms: int = Field(
        default=1000, ge=100, description="Izleme araligi (ms)"
    )
    telegram_config: bool = Field(
        default=True, description="Telegram konfig arayuzu"
    )
    auto_validate: bool = Field(
        default=True, description="Otomatik dogrulama"
    )
