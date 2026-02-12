"""Plugin modelleri testleri."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.plugin import (
    AgentProvision,
    HookEvent,
    HookProvision,
    MonitorProvision,
    PluginConfigField,
    PluginInfo,
    PluginListResponse,
    PluginManifest,
    PluginProvides,
    PluginState,
    PluginType,
    ToolProvision,
)


# === Yardimci Fonksiyonlar ===


def _make_manifest(**kwargs) -> PluginManifest:
    """Test icin PluginManifest olusturur."""
    defaults = {
        "name": "test_plugin",
        "version": "1.0.0",
    }
    defaults.update(kwargs)
    return PluginManifest(**defaults)


def _make_plugin_info(**kwargs) -> PluginInfo:
    """Test icin PluginInfo olusturur."""
    manifest = kwargs.pop("manifest", _make_manifest())
    defaults = {
        "manifest": manifest,
    }
    defaults.update(kwargs)
    return PluginInfo(**defaults)


# === PluginType Testleri ===


class TestPluginType:
    """Plugin tipi enum testleri."""

    def test_all_values(self) -> None:
        """Tum plugin tipleri mevcut olmali."""
        assert PluginType.AGENT == "agent"
        assert PluginType.TOOL == "tool"
        assert PluginType.MONITOR == "monitor"
        assert PluginType.HOOK == "hook"
        assert PluginType.MIXED == "mixed"

    def test_count(self) -> None:
        """5 plugin tipi olmali."""
        assert len(PluginType) == 5


# === PluginState Testleri ===


class TestPluginState:
    """Plugin durumu enum testleri."""

    def test_all_values(self) -> None:
        """Tum plugin durumlari mevcut olmali."""
        assert PluginState.DISCOVERED == "discovered"
        assert PluginState.LOADED == "loaded"
        assert PluginState.ENABLED == "enabled"
        assert PluginState.DISABLED == "disabled"
        assert PluginState.ERROR == "error"

    def test_count(self) -> None:
        """5 plugin durumu olmali."""
        assert len(PluginState) == 5


# === HookEvent Testleri ===


class TestHookEvent:
    """Hook olay enum testleri."""

    def test_task_events(self) -> None:
        """Gorev olaylari mevcut olmali."""
        assert HookEvent.TASK_CREATED == "task_created"
        assert HookEvent.TASK_STARTED == "task_started"
        assert HookEvent.TASK_COMPLETED == "task_completed"
        assert HookEvent.TASK_FAILED == "task_failed"
        assert HookEvent.TASK_CANCELLED == "task_cancelled"

    def test_agent_events(self) -> None:
        """Agent olaylari mevcut olmali."""
        assert HookEvent.AGENT_SELECTED == "agent_selected"
        assert HookEvent.AGENT_REGISTERED == "agent_registered"
        assert HookEvent.AGENT_UNREGISTERED == "agent_unregistered"

    def test_system_events(self) -> None:
        """Sistem olaylari mevcut olmali."""
        assert HookEvent.SYSTEM_STARTUP == "system_startup"
        assert HookEvent.SYSTEM_SHUTDOWN == "system_shutdown"

    def test_plugin_events(self) -> None:
        """Plugin olaylari mevcut olmali."""
        assert HookEvent.PLUGIN_LOADED == "plugin_loaded"
        assert HookEvent.PLUGIN_ENABLED == "plugin_enabled"
        assert HookEvent.PLUGIN_DISABLED == "plugin_disabled"

    def test_decision_events(self) -> None:
        """Karar olaylari mevcut olmali."""
        assert HookEvent.DECISION_MADE == "decision_made"
        assert HookEvent.APPROVAL_REQUESTED == "approval_requested"
        assert HookEvent.APPROVAL_RESPONDED == "approval_responded"

    def test_total_count(self) -> None:
        """16 hook olayi olmali."""
        assert len(HookEvent) == 16


# === PluginConfigField Testleri ===


class TestPluginConfigField:
    """Plugin yapilandirma alani testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler dogru olmali."""
        field = PluginConfigField()
        assert field.type == "str"
        assert field.default is None
        assert field.description == ""
        assert field.required is False

    def test_custom_values(self) -> None:
        """Ozel degerler atanabilmeli."""
        field = PluginConfigField(
            type="int",
            default=42,
            description="Test alani",
            required=True,
        )
        assert field.type == "int"
        assert field.default == 42
        assert field.description == "Test alani"
        assert field.required is True


# === Provision Modelleri Testleri ===


class TestAgentProvision:
    """Agent provision testleri."""

    def test_required_fields(self) -> None:
        """class_name ve module zorunlu olmali."""
        prov = AgentProvision(class_name="TestAgent", module="agent")
        assert prov.class_name == "TestAgent"
        assert prov.module == "agent"
        assert prov.keywords == []

    def test_with_keywords(self) -> None:
        """Anahtar kelimeler atanabilmeli."""
        prov = AgentProvision(
            class_name="TestAgent",
            module="agent",
            keywords=["test", "deneme"],
        )
        assert prov.keywords == ["test", "deneme"]

    def test_missing_class_name_raises(self) -> None:
        """class_name olmadan hata vermeli."""
        with pytest.raises(ValidationError):
            AgentProvision(module="agent")  # type: ignore[call-arg]

    def test_missing_module_raises(self) -> None:
        """module olmadan hata vermeli."""
        with pytest.raises(ValidationError):
            AgentProvision(class_name="Test")  # type: ignore[call-arg]


class TestMonitorProvision:
    """Monitor provision testleri."""

    def test_defaults(self) -> None:
        """Varsayilan check_interval 300 olmali."""
        prov = MonitorProvision(class_name="TestMonitor", module="monitor")
        assert prov.check_interval == 300

    def test_custom_interval(self) -> None:
        """Ozel interval atanabilmeli."""
        prov = MonitorProvision(
            class_name="TestMonitor", module="monitor", check_interval=60
        )
        assert prov.check_interval == 60


class TestHookProvision:
    """Hook provision testleri."""

    def test_required_fields(self) -> None:
        """event ve handler zorunlu olmali."""
        prov = HookProvision(event="task_completed", handler="hooks.on_done")
        assert prov.event == "task_completed"
        assert prov.handler == "hooks.on_done"
        assert prov.priority == 100

    def test_custom_priority(self) -> None:
        """Ozel oncelik atanabilmeli."""
        prov = HookProvision(
            event="task_created", handler="hooks.on_create", priority=10
        )
        assert prov.priority == 10


class TestToolProvision:
    """Tool provision testleri."""

    def test_required_fields(self) -> None:
        """class_name ve module zorunlu olmali."""
        prov = ToolProvision(class_name="TestTool", module="tools")
        assert prov.class_name == "TestTool"
        assert prov.module == "tools"


# === PluginProvides Testleri ===


class TestPluginProvides:
    """Plugin provides testleri."""

    def test_empty_defaults(self) -> None:
        """Varsayilan olarak tum listeler bos olmali."""
        provides = PluginProvides()
        assert provides.agents == []
        assert provides.monitors == []
        assert provides.tools == []
        assert provides.hooks == []

    def test_with_agents(self) -> None:
        """Agent listesi atanabilmeli."""
        agents = [AgentProvision(class_name="A", module="a")]
        provides = PluginProvides(agents=agents)
        assert len(provides.agents) == 1
        assert provides.agents[0].class_name == "A"

    def test_mixed_provisions(self) -> None:
        """Karisik bilesenler atanabilmeli."""
        provides = PluginProvides(
            agents=[AgentProvision(class_name="A", module="a")],
            hooks=[HookProvision(event="task_created", handler="h.f")],
        )
        assert len(provides.agents) == 1
        assert len(provides.hooks) == 1


# === PluginManifest Testleri ===


class TestPluginManifest:
    """Plugin manifest testleri."""

    def test_minimal(self) -> None:
        """Sadece name ve version ile olusturulabilmeli."""
        m = _make_manifest()
        assert m.name == "test_plugin"
        assert m.version == "1.0.0"
        assert m.description == ""
        assert m.author == ""
        assert m.plugin_type == PluginType.MIXED
        assert m.atlas_version == ">=0.1.0"
        assert m.dependencies == []

    def test_full(self) -> None:
        """Tum alanlarla olusturulabilmeli."""
        m = _make_manifest(
            description="Test plugin",
            author="Fatih",
            plugin_type=PluginType.AGENT,
            atlas_version=">=1.0.0",
            dependencies=["other_plugin"],
        )
        assert m.description == "Test plugin"
        assert m.author == "Fatih"
        assert m.plugin_type == PluginType.AGENT
        assert m.dependencies == ["other_plugin"]

    def test_missing_name_raises(self) -> None:
        """name olmadan hata vermeli."""
        with pytest.raises(ValidationError):
            PluginManifest(version="1.0.0")  # type: ignore[call-arg]

    def test_missing_version_raises(self) -> None:
        """version olmadan hata vermeli."""
        with pytest.raises(ValidationError):
            PluginManifest(name="test")  # type: ignore[call-arg]

    def test_with_config(self) -> None:
        """Config alanlari atanabilmeli."""
        m = _make_manifest(
            config={
                "api_url": PluginConfigField(
                    type="str", default="http://localhost", description="API URL"
                )
            }
        )
        assert "api_url" in m.config
        assert m.config["api_url"].default == "http://localhost"

    def test_with_provides(self) -> None:
        """Provides blogu atanabilmeli."""
        provides = PluginProvides(
            agents=[AgentProvision(class_name="TestAgent", module="agent")]
        )
        m = _make_manifest(provides=provides)
        assert len(m.provides.agents) == 1


# === PluginInfo Testleri ===


class TestPluginInfo:
    """Plugin bilgi modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler dogru olmali."""
        info = _make_plugin_info()
        assert info.state == PluginState.DISCOVERED
        assert info.load_time is None
        assert info.error_message is None
        assert info.plugin_dir == ""
        assert info.config_values == {}

    def test_id_is_uuid(self) -> None:
        """id gecerli UUID olmali."""
        info = _make_plugin_info()
        uuid.UUID(info.id)  # gecersiz ise ValueError

    def test_unique_ids(self) -> None:
        """Her info farkli id'ye sahip olmali."""
        info1 = _make_plugin_info()
        info2 = _make_plugin_info()
        assert info1.id != info2.id

    def test_custom_state(self) -> None:
        """Ozel durum atanabilmeli."""
        info = _make_plugin_info(state=PluginState.ENABLED)
        assert info.state == PluginState.ENABLED

    def test_error_state_with_message(self) -> None:
        """Hata durumunda mesaj atanabilmeli."""
        info = _make_plugin_info(
            state=PluginState.ERROR,
            error_message="Import hatasi",
        )
        assert info.state == PluginState.ERROR
        assert info.error_message == "Import hatasi"

    def test_load_time(self) -> None:
        """Yuklenme zamani atanabilmeli."""
        now = datetime.now(timezone.utc)
        info = _make_plugin_info(load_time=now)
        assert info.load_time == now

    def test_set_defaults_applies_config(self) -> None:
        """set_defaults manifest config degerlerini uygulamali."""
        manifest = _make_manifest(
            config={
                "url": PluginConfigField(type="str", default="http://x"),
                "port": PluginConfigField(type="int", default=8080),
            }
        )
        info = _make_plugin_info(manifest=manifest)
        info.set_defaults()
        assert info.config_values["url"] == "http://x"
        assert info.config_values["port"] == 8080

    def test_set_defaults_preserves_existing(self) -> None:
        """set_defaults mevcut degerleri ezmemeli."""
        manifest = _make_manifest(
            config={
                "url": PluginConfigField(type="str", default="http://x"),
            }
        )
        info = _make_plugin_info(
            manifest=manifest,
            config_values={"url": "http://custom"},
        )
        info.set_defaults()
        assert info.config_values["url"] == "http://custom"


# === PluginListResponse Testleri ===


class TestPluginListResponse:
    """Plugin listesi yanit testleri."""

    def test_empty(self) -> None:
        """Bos liste."""
        resp = PluginListResponse()
        assert resp.total == 0
        assert resp.plugins == []

    def test_with_plugins(self) -> None:
        """Plugin listesi atanabilmeli."""
        info = _make_plugin_info()
        resp = PluginListResponse(total=1, plugins=[info])
        assert resp.total == 1
        assert len(resp.plugins) == 1
