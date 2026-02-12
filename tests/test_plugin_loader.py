"""PluginLoader testleri."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.agents.base_agent import BaseAgent, TaskResult
from app.core.plugins.loader import LoadedComponents, PluginLoader, PluginLoadError
from app.core.plugins.validator import PluginValidator
from app.models.plugin import (
    AgentProvision,
    HookProvision,
    MonitorProvision,
    PluginManifest,
    PluginProvides,
    ToolProvision,
)
from app.monitors.base_monitor import BaseMonitor, MonitorResult


# === Yardimci Fonksiyonlar ===


def _make_manifest(**kwargs) -> PluginManifest:
    """Test icin PluginManifest olusturur."""
    defaults: dict[str, Any] = {"name": "test_plugin", "version": "1.0.0"}
    defaults.update(kwargs)
    return PluginManifest(**defaults)


def _make_loader(plugins_dir: Path) -> PluginLoader:
    """Test icin PluginLoader olusturur."""
    return PluginLoader(plugins_dir=plugins_dir)


def _write_agent_module(plugin_dir: Path, class_name: str = "TestAgent") -> None:
    """Test icin gecerli agent modulu yazar."""
    code = f'''
from typing import Any
from app.agents.base_agent import BaseAgent, TaskResult

class {class_name}(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="{class_name}")

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        return TaskResult(success=True, message="test")

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {{"status": "ok"}}

    async def report(self, result: TaskResult) -> str:
        return "test rapor"
'''
    (plugin_dir / "agent.py").write_text(code, encoding="utf-8")


def _write_monitor_module(plugin_dir: Path, class_name: str = "TestMonitor") -> None:
    """Test icin gecerli monitor modulu yazar."""
    code = f'''
from typing import Any
from app.agents.base_agent import BaseAgent, TaskResult
from app.monitors.base_monitor import BaseMonitor, MonitorResult
from unittest.mock import MagicMock

class {class_name}(BaseMonitor):
    def __init__(self, **kwargs):
        agent = MagicMock(spec=BaseAgent)
        agent.name = "mock_agent"
        super().__init__(name="test_monitor", agent=agent, **kwargs)

    async def check(self) -> MonitorResult:
        return MonitorResult(monitor_name="test")
'''
    (plugin_dir / "monitor.py").write_text(code, encoding="utf-8")


def _write_hook_module(plugin_dir: Path) -> None:
    """Test icin gecerli hook modulu yazar."""
    code = '''
from typing import Any

async def on_task_completed(**kwargs: Any) -> None:
    """Test hook handler."""
    pass

async def on_task_created(**kwargs: Any) -> None:
    """Test hook handler."""
    pass
'''
    (plugin_dir / "hooks.py").write_text(code, encoding="utf-8")


def _write_tool_module(plugin_dir: Path, class_name: str = "TestTool") -> None:
    """Test icin gecerli tool modulu yazar."""
    code = f'''
class {class_name}:
    """Test tool."""
    def __init__(self) -> None:
        self.name = "{class_name}"
'''
    (plugin_dir / "tools.py").write_text(code, encoding="utf-8")


def _setup_plugin(
    tmp_path: Path,
    name: str = "test_plugin",
    manifest: PluginManifest | None = None,
    write_agent: bool = False,
    write_monitor: bool = False,
    write_hook: bool = False,
    write_tool: bool = False,
) -> tuple[Path, PluginManifest]:
    """Test icin plugin dizini ve dosyalarini olusturur."""
    plugin_dir = tmp_path / name
    plugin_dir.mkdir(exist_ok=True)
    (plugin_dir / "__init__.py").write_text("", encoding="utf-8")

    if manifest is None:
        manifest = _make_manifest(name=name)

    manifest_file = plugin_dir / "plugin.json"
    manifest_file.write_text(
        json.dumps(manifest.model_dump(mode="json")), encoding="utf-8"
    )

    if write_agent:
        _write_agent_module(plugin_dir)
    if write_monitor:
        _write_monitor_module(plugin_dir)
    if write_hook:
        _write_hook_module(plugin_dir)
    if write_tool:
        _write_tool_module(plugin_dir)

    return plugin_dir, manifest


# === LoadedComponents Testleri ===


class TestLoadedComponents:
    """Yuklenen bilesen kapsayici testleri."""

    def test_empty_init(self) -> None:
        """Bos bilesenlerle baslamali."""
        c = LoadedComponents()
        assert c.agents == []
        assert c.monitors == []
        assert c.tools == []
        assert c.hooks == []


# === PluginLoader Init Testleri ===


class TestPluginLoaderInit:
    """PluginLoader baslatma testleri."""

    def test_init(self, tmp_path: Path) -> None:
        """Varsayilan degerlerle baslatilabilmeli."""
        loader = _make_loader(tmp_path)
        assert loader.loaded_plugin_names == []

    def test_init_with_validator(self, tmp_path: Path) -> None:
        """Ozel validator ile baslatilabilmeli."""
        v = PluginValidator()
        loader = PluginLoader(tmp_path, validator=v)
        assert loader._validator is v


# === Discover Testleri ===


class TestPluginLoaderDiscover:
    """Plugin kesfi testleri."""

    def test_discover_empty(self, tmp_path: Path) -> None:
        """Bos dizinde bos liste donmeli."""
        loader = _make_loader(tmp_path)
        assert loader.discover() == []

    def test_discover_plugin(self, tmp_path: Path) -> None:
        """Gecerli plugin kesfedilmeli."""
        _setup_plugin(tmp_path, "my_plugin")
        loader = _make_loader(tmp_path)
        results = loader.discover()
        assert len(results) == 1
        assert results[0][1].name == "my_plugin"


# === Load Agent Plugin Testleri ===


class TestLoadAgentPlugin:
    """Agent plugin yukleme testleri."""

    def test_load_agent(self, tmp_path: Path) -> None:
        """Agent plugin yuklenebilmeli."""
        manifest = _make_manifest(
            name="agent_plugin",
            provides=PluginProvides(
                agents=[AgentProvision(class_name="TestAgent", module="agent")]
            ),
        )
        plugin_dir, _ = _setup_plugin(
            tmp_path, "agent_plugin", manifest, write_agent=True
        )
        loader = _make_loader(tmp_path)
        components = loader.load_plugin(plugin_dir, manifest)
        assert len(components.agents) == 1
        agent_instance, keywords = components.agents[0]
        assert agent_instance.name == "TestAgent"

    def test_load_agent_with_keywords(self, tmp_path: Path) -> None:
        """Agent keywords yuklenebilmeli."""
        manifest = _make_manifest(
            name="kw_plugin",
            provides=PluginProvides(
                agents=[
                    AgentProvision(
                        class_name="TestAgent",
                        module="agent",
                        keywords=["test", "deneme"],
                    )
                ]
            ),
        )
        plugin_dir, _ = _setup_plugin(
            tmp_path, "kw_plugin", manifest, write_agent=True
        )
        loader = _make_loader(tmp_path)
        components = loader.load_plugin(plugin_dir, manifest)
        _, keywords = components.agents[0]
        assert keywords == ["test", "deneme"]

    def test_load_missing_module_raises(self, tmp_path: Path) -> None:
        """Modul dosyasi yoksa hata vermeli."""
        manifest = _make_manifest(
            name="no_module",
            provides=PluginProvides(
                agents=[AgentProvision(class_name="Ghost", module="missing")]
            ),
        )
        plugin_dir, _ = _setup_plugin(tmp_path, "no_module", manifest)
        loader = _make_loader(tmp_path)
        with pytest.raises(PluginLoadError, match="bulunamadi"):
            loader.load_plugin(plugin_dir, manifest)

    def test_load_missing_class_raises(self, tmp_path: Path) -> None:
        """Sinif modülde yoksa hata vermeli."""
        manifest = _make_manifest(
            name="no_class",
            provides=PluginProvides(
                agents=[AgentProvision(class_name="NonExistent", module="agent")]
            ),
        )
        plugin_dir, _ = _setup_plugin(
            tmp_path, "no_class", manifest, write_agent=True
        )
        loader = _make_loader(tmp_path)
        with pytest.raises(PluginLoadError, match="bulunamadi"):
            loader.load_plugin(plugin_dir, manifest)

    def test_load_invalid_agent_class_raises(self, tmp_path: Path) -> None:
        """BaseAgent'dan miras almayan sinif hata vermeli."""
        manifest = _make_manifest(
            name="bad_agent",
            provides=PluginProvides(
                agents=[AgentProvision(class_name="BadAgent", module="agent")]
            ),
        )
        plugin_dir, _ = _setup_plugin(tmp_path, "bad_agent", manifest)
        (plugin_dir / "agent.py").write_text(
            "class BadAgent:\n    pass\n", encoding="utf-8"
        )
        loader = _make_loader(tmp_path)
        with pytest.raises(PluginLoadError, match="dogrulama hatasi"):
            loader.load_plugin(plugin_dir, manifest)


# === Load Hook Plugin Testleri ===


class TestLoadHookPlugin:
    """Hook plugin yukleme testleri."""

    def test_load_hooks(self, tmp_path: Path) -> None:
        """Hook handler'lar yuklenebilmeli."""
        manifest = _make_manifest(
            name="hook_plugin",
            provides=PluginProvides(
                hooks=[
                    HookProvision(
                        event="task_completed",
                        handler="hooks.on_task_completed",
                    )
                ]
            ),
        )
        plugin_dir, _ = _setup_plugin(
            tmp_path, "hook_plugin", manifest, write_hook=True
        )
        loader = _make_loader(tmp_path)
        components = loader.load_plugin(plugin_dir, manifest)
        assert len(components.hooks) == 1
        event, handler, priority = components.hooks[0]
        assert event == "task_completed"
        assert callable(handler)

    def test_load_invalid_handler_path_raises(self, tmp_path: Path) -> None:
        """Gecersiz handler path hata vermeli."""
        manifest = _make_manifest(
            name="bad_hook",
            provides=PluginProvides(
                hooks=[
                    HookProvision(
                        event="task_created", handler="nonexistent.func"
                    )
                ]
            ),
        )
        plugin_dir, _ = _setup_plugin(tmp_path, "bad_hook", manifest)
        loader = _make_loader(tmp_path)
        with pytest.raises(PluginLoadError):
            loader.load_plugin(plugin_dir, manifest)


# === Load Tool Plugin Testleri ===


class TestLoadToolPlugin:
    """Tool plugin yukleme testleri."""

    def test_load_tool(self, tmp_path: Path) -> None:
        """Tool plugin yuklenebilmeli."""
        manifest = _make_manifest(
            name="tool_plugin",
            provides=PluginProvides(
                tools=[ToolProvision(class_name="TestTool", module="tools")]
            ),
        )
        plugin_dir, _ = _setup_plugin(
            tmp_path, "tool_plugin", manifest, write_tool=True
        )
        loader = _make_loader(tmp_path)
        components = loader.load_plugin(plugin_dir, manifest)
        assert len(components.tools) == 1


# === Load Monitor Plugin Testleri ===


class TestLoadMonitorPlugin:
    """Monitor plugin yukleme testleri."""

    def test_load_monitor(self, tmp_path: Path) -> None:
        """Monitor plugin yuklenebilmeli."""
        manifest = _make_manifest(
            name="monitor_plugin",
            provides=PluginProvides(
                monitors=[
                    MonitorProvision(
                        class_name="TestMonitor", module="monitor", check_interval=60
                    )
                ]
            ),
        )
        plugin_dir, _ = _setup_plugin(
            tmp_path, "monitor_plugin", manifest, write_monitor=True
        )
        loader = _make_loader(tmp_path)
        components = loader.load_plugin(plugin_dir, manifest)
        assert len(components.monitors) == 1
        mon_cls, interval = components.monitors[0]
        assert interval == 60


# === Mixed Plugin Testleri ===


class TestLoadMixedPlugin:
    """Karisik bilesen plugin testleri."""

    def test_load_mixed(self, tmp_path: Path) -> None:
        """Birden fazla bilesen tipi yuklenebilmeli."""
        manifest = _make_manifest(
            name="mixed",
            provides=PluginProvides(
                agents=[AgentProvision(class_name="TestAgent", module="agent")],
                hooks=[
                    HookProvision(event="task_created", handler="hooks.on_task_created")
                ],
            ),
        )
        plugin_dir, _ = _setup_plugin(
            tmp_path, "mixed", manifest, write_agent=True, write_hook=True
        )
        loader = _make_loader(tmp_path)
        components = loader.load_plugin(plugin_dir, manifest)
        assert len(components.agents) == 1
        assert len(components.hooks) == 1


# === Unload Plugin Testleri ===


class TestUnloadPlugin:
    """Plugin bosaltma testleri."""

    def test_unload(self, tmp_path: Path) -> None:
        """Plugin modulleri temizlenmeli."""
        manifest = _make_manifest(
            name="unload_test",
            provides=PluginProvides(
                agents=[AgentProvision(class_name="TestAgent", module="agent")]
            ),
        )
        plugin_dir, _ = _setup_plugin(
            tmp_path, "unload_test", manifest, write_agent=True
        )
        loader = _make_loader(tmp_path)
        loader.load_plugin(plugin_dir, manifest)
        assert "unload_test" in loader.loaded_plugin_names
        loader.unload_plugin("unload_test")
        assert "unload_test" not in loader.loaded_plugin_names

    def test_unload_nonexistent(self, tmp_path: Path) -> None:
        """Olmayan plugin icin hata vermemeli."""
        loader = _make_loader(tmp_path)
        loader.unload_plugin("nonexistent")  # hata yok


# === Manifest Dogrulama Testleri ===


class TestLoaderManifestValidation:
    """Loader'in manifest dogrulama entegrasyonu."""

    def test_invalid_manifest_name_raises(self, tmp_path: Path) -> None:
        """Gecersiz manifest ismi hata vermeli."""
        manifest = _make_manifest(name="bad name!")
        plugin_dir = tmp_path / "bad_name"
        plugin_dir.mkdir()
        loader = _make_loader(tmp_path)
        with pytest.raises(PluginLoadError, match="dogrulama hatasi"):
            loader.load_plugin(plugin_dir, manifest)

    def test_empty_provides_ok(self, tmp_path: Path) -> None:
        """Bos provides ile plugin yuklenebilmeli."""
        manifest = _make_manifest(name="empty_provides")
        plugin_dir = tmp_path / "empty_provides"
        plugin_dir.mkdir()
        loader = _make_loader(tmp_path)
        components = loader.load_plugin(plugin_dir, manifest)
        assert components.agents == []
        assert components.hooks == []


# === Import Hatasi Testleri ===


class TestImportErrors:
    """Modul import hatasi testleri."""

    def test_syntax_error_in_module_raises(self, tmp_path: Path) -> None:
        """Sozdizimi hatali modul hata vermeli."""
        manifest = _make_manifest(
            name="syntax_err",
            provides=PluginProvides(
                agents=[AgentProvision(class_name="X", module="agent")]
            ),
        )
        plugin_dir, _ = _setup_plugin(tmp_path, "syntax_err", manifest)
        (plugin_dir / "agent.py").write_text(
            "def broken(\n", encoding="utf-8"
        )
        loader = _make_loader(tmp_path)
        with pytest.raises(PluginLoadError, match="import hatasi"):
            loader.load_plugin(plugin_dir, manifest)
