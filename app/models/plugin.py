"""Plugin sistemi veri modelleri.

Plugin manifest, durum, yapilandirma ve provision modelleri.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# === Enum'lar ===


class PluginType(str, Enum):
    """Plugin tipi."""

    AGENT = "agent"
    TOOL = "tool"
    MONITOR = "monitor"
    HOOK = "hook"
    MIXED = "mixed"


class PluginState(str, Enum):
    """Plugin yasam dongusu durumu."""

    DISCOVERED = "discovered"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


class HookEvent(str, Enum):
    """Sistemde dinlenebilir olay tipleri."""

    # Gorev yasam dongusu
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"

    # Agent olaylari
    AGENT_SELECTED = "agent_selected"
    AGENT_REGISTERED = "agent_registered"
    AGENT_UNREGISTERED = "agent_unregistered"

    # Sistem olaylari
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"

    # Plugin olaylari
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_ENABLED = "plugin_enabled"
    PLUGIN_DISABLED = "plugin_disabled"

    # Karar olaylari
    DECISION_MADE = "decision_made"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESPONDED = "approval_responded"


# === Provision Modelleri ===


class PluginConfigField(BaseModel):
    """Plugin yapilandirma alani tanimi.

    Attributes:
        type: Alan tipi (str, int, float, bool).
        default: Varsayilan deger.
        description: Alan aciklamasi.
        required: Zorunlu mu.
    """

    type: str = "str"
    default: Any = None
    description: str = ""
    required: bool = False


class AgentProvision(BaseModel):
    """Plugin'in saglayacagi agent tanimi.

    Attributes:
        class_name: Agent sinif adi.
        module: Moduldeki kaynak dosya adi (uzantisiz).
        keywords: MasterAgent yonlendirme icin anahtar kelimeler.
    """

    class_name: str
    module: str
    keywords: list[str] = Field(default_factory=list)


class MonitorProvision(BaseModel):
    """Plugin'in saglayacagi monitor tanimi.

    Attributes:
        class_name: Monitor sinif adi.
        module: Moduldeki kaynak dosya adi.
        check_interval: Kontrol araligi (saniye).
    """

    class_name: str
    module: str
    check_interval: int = 300


class HookProvision(BaseModel):
    """Plugin'in saglayacagi hook tanimi.

    Attributes:
        event: Dinlenecek olay.
        handler: Handler dotted path (ornek: 'hooks.on_task_completed').
        priority: Oncelik (dusuk sayi = yuksek oncelik).
    """

    event: str
    handler: str
    priority: int = 100


class ToolProvision(BaseModel):
    """Plugin'in saglayacagi tool tanimi.

    Attributes:
        class_name: Tool sinif adi.
        module: Moduldeki kaynak dosya adi.
    """

    class_name: str
    module: str


class PluginProvides(BaseModel):
    """Plugin'in saglayacagi tum bilesenler.

    Attributes:
        agents: Saglanan agent listesi.
        monitors: Saglanan monitor listesi.
        tools: Saglanan tool listesi.
        hooks: Saglanan hook listesi.
    """

    agents: list[AgentProvision] = Field(default_factory=list)
    monitors: list[MonitorProvision] = Field(default_factory=list)
    tools: list[ToolProvision] = Field(default_factory=list)
    hooks: list[HookProvision] = Field(default_factory=list)


# === Ana Modeller ===


class PluginManifest(BaseModel):
    """Plugin manifest verisi (plugin.json'dan yuklenir).

    Attributes:
        name: Benzersiz plugin adi.
        version: Semantik surum.
        description: Plugin aciklamasi.
        author: Yazar adi.
        plugin_type: Plugin tipi.
        atlas_version: Gereken minimum ATLAS surumu.
        provides: Saglanan bilesenler.
        config: Plugin yapilandirma alanlari.
        dependencies: Bagimli plugin adlari.
    """

    name: str
    version: str
    description: str = ""
    author: str = ""
    plugin_type: PluginType = PluginType.MIXED
    atlas_version: str = ">=0.1.0"
    provides: PluginProvides = Field(default_factory=PluginProvides)
    config: dict[str, PluginConfigField] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


class PluginInfo(BaseModel):
    """Calisma zamaninda plugin durumu.

    Attributes:
        id: Benzersiz plugin ID.
        manifest: Plugin manifest verisi.
        state: Mevcut durum.
        load_time: Yuklenme zamani.
        error_message: Hata mesaji (varsa).
        plugin_dir: Plugin dizin yolu.
        config_values: Aktif yapilandirma degerleri.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    manifest: PluginManifest
    state: PluginState = PluginState.DISCOVERED
    load_time: datetime | None = None
    error_message: str | None = None
    plugin_dir: str = ""
    config_values: dict[str, Any] = Field(default_factory=dict)

    def set_defaults(self) -> None:
        """Manifest'teki varsayilan config degerlerini uygular."""
        for key, field in self.manifest.config.items():
            if key not in self.config_values:
                self.config_values[key] = field.default


class PluginListResponse(BaseModel):
    """Plugin listesi API yaniti.

    Attributes:
        total: Toplam plugin sayisi.
        plugins: Plugin bilgi listesi.
    """

    total: int = 0
    plugins: list[PluginInfo] = Field(default_factory=list)
