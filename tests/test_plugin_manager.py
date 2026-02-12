"""PluginManager testleri."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base_agent import BaseAgent
from app.core.plugins.loader import PluginLoadError
from app.core.plugins.manager import PluginManager
from app.models.plugin import (
    AgentProvision,
    HookEvent,
    HookProvision,
    PluginInfo,
    PluginManifest,
    PluginProvides,
    PluginState,
)


# === Yardimci Fonksiyonlar ===


def _make_manifest(**kwargs) -> PluginManifest:
    """Test icin PluginManifest olusturur."""
    defaults: dict[str, Any] = {"name": "test_plugin", "version": "1.0.0"}
    defaults.update(kwargs)
    return PluginManifest(**defaults)


def _make_mock_master() -> MagicMock:
    """Test icin mock MasterAgent olusturur."""
    master = MagicMock()
    master.register_agent = MagicMock()
    master.register_agent_keywords = MagicMock()
    master.unregister_agent = MagicMock()
    return master


def _write_agent_module(plugin_dir: Path, class_name: str = "TestAgent") -> None:
    """Gecerli agent modul dosyasi yazar."""
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


def _write_hook_module(plugin_dir: Path) -> None:
    """Gecerli hook modul dosyasi yazar."""
    code = '''
from typing import Any

async def on_task_completed(**kwargs: Any) -> None:
    pass
'''
    (plugin_dir / "hooks.py").write_text(code, encoding="utf-8")


def _setup_full_plugin(
    tmp_path: Path,
    name: str = "test_plugin",
    with_agent: bool = True,
    with_hooks: bool = False,
    keywords: list[str] | None = None,
    dependencies: list[str] | None = None,
) -> Path:
    """Tam plugin dizini olusturur (manifest + modüller)."""
    plugin_dir = tmp_path / name
    plugin_dir.mkdir(exist_ok=True)
    (plugin_dir / "__init__.py").write_text("", encoding="utf-8")

    provides: dict[str, Any] = {}
    if with_agent:
        provides["agents"] = [
            {"class": "TestAgent", "module": "agent", "keywords": keywords or []}
        ]
        _write_agent_module(plugin_dir)

    if with_hooks:
        provides["hooks"] = [
            {"event": "task_completed", "handler": "hooks.on_task_completed"}
        ]
        _write_hook_module(plugin_dir)

    manifest_data = {
        "name": name,
        "version": "1.0.0",
        "provides": provides,
        "dependencies": dependencies or [],
    }

    (plugin_dir / "plugin.json").write_text(
        json.dumps(manifest_data), encoding="utf-8"
    )
    return plugin_dir


# === Init Testleri ===


class TestPluginManagerInit:
    """PluginManager baslatma testleri."""

    def test_init(self, tmp_path: Path) -> None:
        """Varsayilan degerlerle baslatilabilmeli."""
        mgr = PluginManager(plugins_dir=tmp_path)
        assert mgr.registry.count_total() == 0
        assert mgr.hooks.total_handlers == 0

    def test_init_with_master(self, tmp_path: Path) -> None:
        """MasterAgent referansi ile baslatilabilmeli."""
        master = _make_mock_master()
        mgr = PluginManager(master_agent=master, plugins_dir=tmp_path)
        assert mgr._master_agent is master


# === Initialize Testleri ===


class TestPluginManagerInitialize:
    """Plugin kesfi testleri."""

    async def test_initialize_empty(self, tmp_path: Path) -> None:
        """Bos dizinde 0 plugin kesfedilmeli."""
        mgr = PluginManager(plugins_dir=tmp_path)
        count = await mgr.initialize()
        assert count == 0

    async def test_initialize_discovers(self, tmp_path: Path) -> None:
        """Plugin'ler kesfedilmeli."""
        _setup_full_plugin(tmp_path, "plugin_a")
        mgr = PluginManager(plugins_dir=tmp_path)
        count = await mgr.initialize()
        assert count == 1
        assert mgr.registry.has("plugin_a")
        info = mgr.registry.get("plugin_a")
        assert info is not None
        assert info.state == PluginState.DISCOVERED

    async def test_initialize_multiple(self, tmp_path: Path) -> None:
        """Birden fazla plugin kesfedilmeli."""
        _setup_full_plugin(tmp_path, "p1")
        _setup_full_plugin(tmp_path, "p2")
        mgr = PluginManager(plugins_dir=tmp_path)
        count = await mgr.initialize()
        assert count == 2

    async def test_initialize_sets_defaults(self, tmp_path: Path) -> None:
        """Config varsayilan degerleri atanmali."""
        plugin_dir = tmp_path / "cfg_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "__init__.py").write_text("")
        manifest = {
            "name": "cfg_plugin",
            "version": "1.0.0",
            "config": {"url": {"type": "str", "default": "http://test"}},
        }
        (plugin_dir / "plugin.json").write_text(json.dumps(manifest))
        _write_agent_module(plugin_dir)

        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()
        info = mgr.registry.get("cfg_plugin")
        assert info is not None
        assert info.config_values.get("url") == "http://test"


# === Load Plugin Testleri ===


class TestPluginManagerLoad:
    """Plugin yukleme testleri."""

    async def test_load_plugin(self, tmp_path: Path) -> None:
        """Plugin yuklenebilmeli."""
        _setup_full_plugin(tmp_path, "loadable")
        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()
        info = await mgr.load_plugin("loadable")
        assert info.state == PluginState.LOADED
        assert info.load_time is not None

    async def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        """Olmayan plugin icin hata vermeli."""
        mgr = PluginManager(plugins_dir=tmp_path)
        with pytest.raises(ValueError, match="bulunamadi"):
            await mgr.load_plugin("ghost")

    async def test_load_emits_hook(self, tmp_path: Path) -> None:
        """Yukleme PLUGIN_LOADED hook'u tetiklemeli."""
        _setup_full_plugin(tmp_path, "hooktest")
        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()

        handler = AsyncMock()
        mgr.hooks.register(HookEvent.PLUGIN_LOADED, "test", handler)
        await mgr.load_plugin("hooktest")
        handler.assert_called_once_with(plugin_name="hooktest")


# === Enable Plugin Testleri ===


class TestPluginManagerEnable:
    """Plugin etkinlestirme testleri."""

    async def test_enable_registers_agent(self, tmp_path: Path) -> None:
        """Enable agent'i MasterAgent'a kaydettirmeli."""
        _setup_full_plugin(tmp_path, "agent_p")
        master = _make_mock_master()
        mgr = PluginManager(master_agent=master, plugins_dir=tmp_path)
        await mgr.initialize()
        await mgr.load_plugin("agent_p")
        await mgr.enable_plugin("agent_p")

        master.register_agent.assert_called_once()
        info = mgr.registry.get("agent_p")
        assert info is not None
        assert info.state == PluginState.ENABLED

    async def test_enable_registers_keywords(self, tmp_path: Path) -> None:
        """Enable keyword'leri MasterAgent'a kaydettirmeli."""
        _setup_full_plugin(tmp_path, "kw_p", keywords=["stok", "envanter"])
        master = _make_mock_master()
        mgr = PluginManager(master_agent=master, plugins_dir=tmp_path)
        await mgr.initialize()
        await mgr.load_plugin("kw_p")
        await mgr.enable_plugin("kw_p")

        master.register_agent_keywords.assert_called_once()

    async def test_enable_registers_hooks(self, tmp_path: Path) -> None:
        """Enable hook handler'lari kaydettirmeli."""
        _setup_full_plugin(tmp_path, "hook_p", with_agent=False, with_hooks=True)
        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()
        await mgr.load_plugin("hook_p")
        await mgr.enable_plugin("hook_p")

        hooks = mgr.hooks.get_plugin_hooks("hook_p")
        assert HookEvent.TASK_COMPLETED in hooks

    async def test_enable_emits_hook(self, tmp_path: Path) -> None:
        """Enable PLUGIN_ENABLED hook'u tetiklemeli."""
        _setup_full_plugin(tmp_path, "emit_p", with_agent=False)
        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()
        await mgr.load_plugin("emit_p")

        handler = AsyncMock()
        mgr.hooks.register(HookEvent.PLUGIN_ENABLED, "test", handler)
        await mgr.enable_plugin("emit_p")
        handler.assert_called_once_with(plugin_name="emit_p")

    async def test_enable_not_loaded_raises(self, tmp_path: Path) -> None:
        """Yuklenmemis plugin etkinlestirilemezken hata vermeli."""
        _setup_full_plugin(tmp_path, "not_loaded")
        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()
        with pytest.raises(ValueError, match="etkinlestirilemez"):
            await mgr.enable_plugin("not_loaded")

    async def test_enable_nonexistent_raises(self, tmp_path: Path) -> None:
        """Olmayan plugin icin hata vermeli."""
        mgr = PluginManager(plugins_dir=tmp_path)
        with pytest.raises(ValueError, match="bulunamadi"):
            await mgr.enable_plugin("ghost")

    async def test_enable_without_master_agent(self, tmp_path: Path) -> None:
        """MasterAgent olmadan da etkinlestirilebilmeli."""
        _setup_full_plugin(tmp_path, "no_master")
        mgr = PluginManager(plugins_dir=tmp_path)  # master_agent=None
        await mgr.initialize()
        await mgr.load_plugin("no_master")
        info = await mgr.enable_plugin("no_master")
        assert info.state == PluginState.ENABLED


# === Disable Plugin Testleri ===


class TestPluginManagerDisable:
    """Plugin devre disi birakma testleri."""

    async def test_disable_unregisters_agent(self, tmp_path: Path) -> None:
        """Disable agent kaydini silmeli."""
        _setup_full_plugin(tmp_path, "dis_p")
        master = _make_mock_master()
        mgr = PluginManager(master_agent=master, plugins_dir=tmp_path)
        await mgr.initialize()
        await mgr.load_plugin("dis_p")
        await mgr.enable_plugin("dis_p")
        await mgr.disable_plugin("dis_p")

        master.unregister_agent.assert_called_once()
        info = mgr.registry.get("dis_p")
        assert info is not None
        assert info.state == PluginState.DISABLED

    async def test_disable_unregisters_hooks(self, tmp_path: Path) -> None:
        """Disable hook kayitlarini silmeli."""
        _setup_full_plugin(tmp_path, "dhook_p", with_agent=False, with_hooks=True)
        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()
        await mgr.load_plugin("dhook_p")
        await mgr.enable_plugin("dhook_p")
        await mgr.disable_plugin("dhook_p")

        assert mgr.hooks.get_plugin_hooks("dhook_p") == {}

    async def test_disable_emits_hook(self, tmp_path: Path) -> None:
        """Disable PLUGIN_DISABLED hook'u tetiklemeli."""
        _setup_full_plugin(tmp_path, "demit_p", with_agent=False)
        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()
        await mgr.load_plugin("demit_p")
        await mgr.enable_plugin("demit_p")

        handler = AsyncMock()
        mgr.hooks.register(HookEvent.PLUGIN_DISABLED, "test", handler)
        await mgr.disable_plugin("demit_p")
        handler.assert_called_once_with(plugin_name="demit_p")

    async def test_disable_nonexistent_raises(self, tmp_path: Path) -> None:
        """Olmayan plugin icin hata vermeli."""
        mgr = PluginManager(plugins_dir=tmp_path)
        with pytest.raises(ValueError, match="bulunamadi"):
            await mgr.disable_plugin("ghost")


# === Load All Testleri ===


class TestPluginManagerLoadAll:
    """Toplu yukleme testleri."""

    async def test_load_all(self, tmp_path: Path) -> None:
        """Tum plugin'ler yuklenip etkinlestirilmeli."""
        _setup_full_plugin(tmp_path, "la_p1")
        _setup_full_plugin(tmp_path, "la_p2", with_agent=False)
        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()
        results = await mgr.load_all()
        assert len(results) == 2
        for info in results.values():
            assert info.state == PluginState.ENABLED

    async def test_load_all_with_error(self, tmp_path: Path) -> None:
        """Hatali plugin'ler ERROR durumunda olmali, digerlerini engellememeli."""
        _setup_full_plugin(tmp_path, "good_p")
        bad_dir = tmp_path / "bad_p"
        bad_dir.mkdir()
        (bad_dir / "__init__.py").write_text("")
        (bad_dir / "plugin.json").write_text(json.dumps({
            "name": "bad_p",
            "version": "1.0.0",
            "provides": {"agents": [{"class": "X", "module": "missing"}]},
        }))

        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()
        results = await mgr.load_all()

        good = results.get("good_p")
        bad = results.get("bad_p")
        assert good is not None and good.state == PluginState.ENABLED
        assert bad is not None and bad.state == PluginState.ERROR

    async def test_load_all_respects_dependencies(self, tmp_path: Path) -> None:
        """Bagimlilik sirasina gore yuklemeli."""
        _setup_full_plugin(tmp_path, "dep_base")
        _setup_full_plugin(tmp_path, "dep_child", dependencies=["dep_base"])
        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()
        results = await mgr.load_all()
        # Her iki plugin de ENABLED olmali
        assert results["dep_base"].state == PluginState.ENABLED
        assert results["dep_child"].state == PluginState.ENABLED


# === Reload Plugin Testleri ===


class TestPluginManagerReload:
    """Plugin yeniden yukleme testleri."""

    async def test_reload(self, tmp_path: Path) -> None:
        """Plugin yeniden yuklenebilmeli."""
        _setup_full_plugin(tmp_path, "reload_p")
        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()
        await mgr.load_plugin("reload_p")
        await mgr.enable_plugin("reload_p")

        info = await mgr.reload_plugin("reload_p")
        assert info.state == PluginState.ENABLED

    async def test_reload_nonexistent_raises(self, tmp_path: Path) -> None:
        """Olmayan plugin icin hata vermeli."""
        mgr = PluginManager(plugins_dir=tmp_path)
        with pytest.raises(ValueError, match="bulunamadi"):
            await mgr.reload_plugin("ghost")


# === Shutdown Testleri ===


class TestPluginManagerShutdown:
    """Plugin sistemi kapatma testleri."""

    async def test_shutdown(self, tmp_path: Path) -> None:
        """Shutdown tum plugin'leri devre disi birakip temizlemeli."""
        _setup_full_plugin(tmp_path, "sd_p1")
        _setup_full_plugin(tmp_path, "sd_p2", with_agent=False, with_hooks=True)
        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()
        await mgr.load_all()
        await mgr.shutdown()

        assert mgr.hooks.total_handlers == 0
        for info in mgr.registry.list_all():
            assert info.state != PluginState.ENABLED

    async def test_shutdown_empty(self, tmp_path: Path) -> None:
        """Bos durumda shutdown hata vermemeli."""
        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.shutdown()  # hata yok


# === Config Testleri ===


class TestPluginManagerConfig:
    """Plugin yapilandirma testleri."""

    async def test_get_plugin_config(self, tmp_path: Path) -> None:
        """Plugin config degeri okunabilmeli."""
        plugin_dir = tmp_path / "cfg_p"
        plugin_dir.mkdir()
        (plugin_dir / "__init__.py").write_text("")
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "name": "cfg_p",
            "version": "1.0.0",
            "config": {"api_url": {"type": "str", "default": "http://test"}},
        }))

        mgr = PluginManager(plugins_dir=tmp_path)
        await mgr.initialize()
        assert mgr.get_plugin_config("cfg_p", "api_url") == "http://test"

    def test_get_config_nonexistent(self, tmp_path: Path) -> None:
        """Olmayan plugin config icin default donmeli."""
        mgr = PluginManager(plugins_dir=tmp_path)
        assert mgr.get_plugin_config("ghost", "key", "fallback") == "fallback"


# === Dependency Sort Testleri ===


class TestDependencySort:
    """Bagimlilik siralama testleri."""

    def test_no_dependencies(self, tmp_path: Path) -> None:
        """Bagimliligi olmayan plugin'ler sirada kalir."""
        mgr = PluginManager(plugins_dir=tmp_path)
        infos = [
            PluginInfo(manifest=_make_manifest(name="b")),
            PluginInfo(manifest=_make_manifest(name="a")),
        ]
        result = mgr._sort_by_dependencies(infos)
        assert len(result) == 2

    def test_with_dependency(self, tmp_path: Path) -> None:
        """Bagimlilik once gelmeli."""
        mgr = PluginManager(plugins_dir=tmp_path)
        child = PluginInfo(
            manifest=_make_manifest(name="child", dependencies=["parent"])
        )
        parent = PluginInfo(manifest=_make_manifest(name="parent"))
        result = mgr._sort_by_dependencies([child, parent])
        names = [r.manifest.name for r in result]
        assert names.index("parent") < names.index("child")

    def test_missing_dependency(self, tmp_path: Path) -> None:
        """Eksik bagimlilik atlanmali."""
        mgr = PluginManager(plugins_dir=tmp_path)
        orphan = PluginInfo(
            manifest=_make_manifest(name="orphan", dependencies=["missing"])
        )
        result = mgr._sort_by_dependencies([orphan])
        assert len(result) == 1
