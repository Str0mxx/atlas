"""
Interactive Setup Wizard sistem modelleri.

Pydantic modelleri ve enum tanimlari.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enumlar ─────────────────────────────────────────────────────────────────


class WizardStep(str, Enum):
    """Sihirbaz adim durumu."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class ValidationRule(str, Enum):
    """Dogrulama kurali tipleri."""

    NOT_EMPTY = "not_empty"
    POSITIVE_INT = "positive_int"
    EMAIL = "email"
    URL = "url"
    CUSTOM = "custom"


class ChannelType(str, Enum):
    """Kanal tipleri."""

    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    SLACK = "slack"
    WEBCHAT = "webchat"


class ModelProvider(str, Enum):
    """Model saglayici tipleri."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    CUSTOM = "custom"


class TestStatus(str, Enum):
    """Test durumu."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


class DependencyStatus(str, Enum):
    """Bagimlilik durumu."""

    INSTALLED = "installed"
    MISSING = "missing"
    OPTIONAL = "optional"
    UNKNOWN = "unknown"


# ── Pydantic Modelleri ───────────────────────────────────────────────────────


class StepInfo(BaseModel):
    """Sihirbaz adim bilgisi."""

    index: int = Field(ge=0, description="Adim indeksi")
    name: str = Field(description="Adim adi")
    title: str = Field(default="", description="Adim basligi")
    description: str = Field(default="", description="Adim aciklamasi")
    required: bool = Field(default=True, description="Zorunlu mu")
    status: WizardStep = Field(
        default=WizardStep.PENDING, description="Adim durumu"
    )


class WizardProgress(BaseModel):
    """Sihirbaz ilerleme bilgisi."""

    current: int = Field(ge=1, description="Mevcut adim (1-bazli)")
    total: int = Field(ge=0, description="Toplam adim sayisi")
    completed: int = Field(ge=0, description="Tamamlanan adim sayisi")
    percent: int = Field(ge=0, le=100, description="Tamamlanma yuzdesi")


class ValidationResult(BaseModel):
    """Dogrulama sonucu."""

    valid: bool = Field(description="Gecerli mi")
    value: Any = Field(default=None, description="Dogrulanan deger")
    rule: str = Field(default="", description="Kullanilan kural")
    error: str | None = Field(default=None, description="Hata mesaji")


class APIKeyCheckResult(BaseModel):
    """API anahtar kontrol sonucu."""

    valid: bool = Field(description="Gecerli mi")
    provider: str = Field(description="Saglayici adi")
    checks: dict[str, bool] = Field(
        default_factory=dict, description="Alt kontroller"
    )
    passed_count: int = Field(default=0, description="Gecen kontrol sayisi")
    total_checks: int = Field(default=0, description="Toplam kontrol sayisi")


class ChannelConfig(BaseModel):
    """Kanal konfigurasyonu."""

    channel: str = Field(description="Kanal adi")
    enabled: bool = Field(default=True, description="Etkin mi")
    status: str = Field(default="configured", description="Durum")


class TelegramChannelConfig(ChannelConfig):
    """Telegram kanal konfigurasyonu."""

    token: str = Field(description="Bot token")
    chat_id: str = Field(default="", description="Chat ID")
    webhook_url: str = Field(default="", description="Webhook URL")


class WhatsAppChannelConfig(ChannelConfig):
    """WhatsApp kanal konfigurasyonu."""

    phone: str = Field(description="Telefon numarasi")
    api_key: str = Field(description="API anahtari")
    business_id: str = Field(default="", description="Is hesap ID")


class ModelInfo(BaseModel):
    """Model bilgisi."""

    model_id: str = Field(description="Model kimlik")
    name: str = Field(description="Model adi")
    provider: str = Field(description="Saglayici")
    cost_per_1k_input: float = Field(
        ge=0.0, description="1K token giris maliyeti"
    )
    cost_per_1k_output: float = Field(
        ge=0.0, description="1K token cikis maliyeti"
    )
    context_window: int = Field(ge=0, description="Baglam penceresi")
    capabilities: list[str] = Field(
        default_factory=list, description="Yetenekler"
    )
    recommended_for: list[str] = Field(
        default_factory=list, description="Onerildig kullanim durumu"
    )


class ModelRecommendation(BaseModel):
    """Model onerisi."""

    recommended: str = Field(description="Onerilen model ID")
    name: str = Field(default="", description="Model adi")
    reason: str = Field(description="Oneri sebebi")
    use_case: str = Field(description="Kullanim durumu")


class CostComparison(BaseModel):
    """Maliyet karsilastirma sonucu."""

    compared: bool = Field(description="Karsilastirildi mi")
    models: list[dict] = Field(
        default_factory=list, description="Karsilastirilan modeller"
    )
    cheapest: str | None = Field(
        default=None, description="En ucuz model"
    )
    count: int = Field(default=0, description="Karsilastirilan model sayisi")


class TestResult(BaseModel):
    """Test sonucu."""

    passed: bool = Field(description="Gecti mi")
    test: str = Field(description="Test adi")
    error: str | None = Field(default=None, description="Hata mesaji")
    skipped: bool = Field(default=False, description="Atlandi mi")


class ConnectivityTestResult(TestResult):
    """Baglanti test sonucu."""

    host: str = Field(default="", description="Test edilen host")
    latency_ms: int | None = Field(
        default=None, description="Gecikme (ms)"
    )


class LLMTestResult(TestResult):
    """LLM test sonucu."""

    provider: str = Field(default="", description="Saglayici")
    model: str = Field(default="", description="Model")
    response_time_ms: int | None = Field(
        default=None, description="Yanit suresi (ms)"
    )


class SystemTestResult(TestResult):
    """Sistem test sonucu."""

    python_version: str = Field(default="", description="Python versiyonu")
    python_ok: bool = Field(default=False, description="Python OK mi")
    platform: str = Field(default="", description="Platform")


class AllTestsResult(BaseModel):
    """Tum testler sonucu."""

    completed: bool = Field(description="Tamamlandi mi")
    total: int = Field(default=0, description="Toplam test sayisi")
    passed: int = Field(default=0, description="Gecen test sayisi")
    failed: int = Field(default=0, description="Basarisiz test sayisi")
    success: bool = Field(default=False, description="Basarili mi")
    results: list[dict] = Field(
        default_factory=list, description="Test sonuclari"
    )


class DependencyCheckResult(BaseModel):
    """Bagimlilik kontrol sonucu."""

    passed: bool = Field(description="Gecti mi")
    check: str = Field(description="Kontrol adi")
    package: str | None = Field(
        default=None, description="Paket adi"
    )
    installed: bool | None = Field(
        default=None, description="Kurulu mu"
    )
    required: bool = Field(default=True, description="Zorunlu mu")


class AllDepsResult(BaseModel):
    """Tum bagimlilik kontrolleri sonucu."""

    completed: bool = Field(description="Tamamlandi mi")
    total: int = Field(default=0, description="Toplam kontrol sayisi")
    passed: int = Field(default=0, description="Gecen kontrol sayisi")
    failed: int = Field(default=0, description="Basarisiz kontrol sayisi")
    ready: bool = Field(default=False, description="Hazir mi")
    recommendations: list[str] = Field(
        default_factory=list, description="Onerilir aksiyonlar"
    )
    results: list[dict] = Field(
        default_factory=list, description="Kontrol sonuclari"
    )


class EnvVariable(BaseModel):
    """Env degiskeni."""

    key: str = Field(description="Degisken adi")
    value: str = Field(default="", description="Degisken degeri")
    required: bool = Field(default=False, description="Zorunlu mu")
    masked: bool = Field(default=False, description="Maskeli mi")


class EnvFileResult(BaseModel):
    """Env dosyasi islem sonucu."""

    written: bool = Field(description="Yazildi mi")
    path: str = Field(default="", description="Dosya yolu")
    variable_count: int = Field(
        default=0, description="Degisken sayisi"
    )
    backup: dict | None = Field(
        default=None, description="Yedek bilgisi"
    )


class EnvValidationResult(BaseModel):
    """Env dogrulama sonucu."""

    valid: bool = Field(description="Gecerli mi")
    path: str = Field(default="", description="Dosya yolu")
    missing_vars: list[str] = Field(
        default_factory=list, description="Eksik degiskenler"
    )
    empty_vars: list[str] = Field(
        default_factory=list, description="Bos degiskenler"
    )
    required_count: int = Field(
        default=0, description="Zorunlu degisken sayisi"
    )


class WizardSummary(BaseModel):
    """Sihirbaz ozet bilgisi."""

    title: str = Field(description="Sihirbaz basligi")
    step_count: int = Field(ge=0, description="Adim sayisi")
    current_step: int = Field(ge=0, description="Mevcut adim")
    completed_steps: int = Field(ge=0, description="Tamamlanan adim sayisi")
    is_completed: bool = Field(description="Tamamlandi mi")
    answers_count: int = Field(ge=0, description="Cevap sayisi")


class SetupWizardConfig(BaseModel):
    """Setup wizard konfigurasyonu."""

    enabled: bool = Field(default=True, description="Aktif mi")
    interactive: bool = Field(default=True, description="Interaktif mod")
    auto_test: bool = Field(
        default=True, description="Otomatik test"
    )
    backup_existing: bool = Field(
        default=True, description="Mevcut dosyalari yedekle"
    )
