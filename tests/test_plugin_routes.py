"""Plugin API endpoint testleri."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.plugins.registry import PluginRegistry
from app.main import app
from app.models.plugin import (
    PluginInfo,
    PluginManifest,
    PluginState,
)


# === Yardimci Fonksiyonlar ===


def _make_manifest(**kwargs) -> PluginManifest:
    """Test icin PluginManifest olusturur."""
    defaults = {"name": "test_plugin", "version": "1.0.0"}
    defaults.update(kwargs)
    return PluginManifest(**defaults)


def _make_info(name: str = "test_plugin", **kwargs) -> PluginInfo:
    """Test icin PluginInfo olusturur."""
    manifest = kwargs.pop("manifest", _make_manifest(name=name))
    return PluginInfo(manifest=manifest, **kwargs)


def _make_mock_plugin_manager(
    plugins: list[PluginInfo] | None = None,
) -> MagicMock:
    """Test icin mock PluginManager olusturur."""
    pm = MagicMock()
    registry = PluginRegistry()
    if plugins:
        for info in plugins:
            registry.register(info)
    pm.registry = registry
    pm.enable_plugin = AsyncMock()
    pm.disable_plugin = AsyncMock()
    pm.shutdown = AsyncMock()
    pm.initialize = AsyncMock(return_value=0)
    pm.load_all = AsyncMock(return_value={})
    return pm


@pytest.fixture
def client() -> TestClient:
    """FastAPI test istemcisi."""
    return TestClient(app, raise_server_exceptions=False)


# === List Plugins Testleri ===


class TestListPlugins:
    """GET /api/plugins testleri."""

    def test_list_empty(self, client: TestClient) -> None:
        """Bos plugin listesi donmeli."""
        pm = _make_mock_plugin_manager()
        with patch.object(app.state, "plugin_manager", pm, create=True):
            resp = client.get("/api/plugins")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["plugins"] == []

    def test_list_with_plugins(self, client: TestClient) -> None:
        """Plugin listesi donmeli."""
        plugins = [_make_info("p1"), _make_info("p2")]
        pm = _make_mock_plugin_manager(plugins)
        with patch.object(app.state, "plugin_manager", pm, create=True):
            resp = client.get("/api/plugins")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_list_no_plugin_manager(self, client: TestClient) -> None:
        """Plugin manager yoksa 503 donmeli."""
        with patch.object(app.state, "plugin_manager", None, create=True):
            resp = client.get("/api/plugins")
        assert resp.status_code == 503


# === Get Plugin Testleri ===


class TestGetPlugin:
    """GET /api/plugins/{name} testleri."""

    def test_get_existing(self, client: TestClient) -> None:
        """Var olan plugin detayi donmeli."""
        pm = _make_mock_plugin_manager([_make_info("my_plugin")])
        with patch.object(app.state, "plugin_manager", pm, create=True):
            resp = client.get("/api/plugins/my_plugin")
        assert resp.status_code == 200
        data = resp.json()
        assert data["manifest"]["name"] == "my_plugin"

    def test_get_nonexistent(self, client: TestClient) -> None:
        """Olmayan plugin icin 404 donmeli."""
        pm = _make_mock_plugin_manager()
        with patch.object(app.state, "plugin_manager", pm, create=True):
            resp = client.get("/api/plugins/ghost")
        assert resp.status_code == 404


# === Enable Plugin Testleri ===


class TestEnablePlugin:
    """POST /api/plugins/{name}/enable testleri."""

    def test_enable_success(self, client: TestClient) -> None:
        """Plugin etkinlestirme basarili olmali."""
        info = _make_info("p1", state=PluginState.LOADED)
        pm = _make_mock_plugin_manager([info])
        pm.enable_plugin = AsyncMock(return_value=_make_info("p1", state=PluginState.ENABLED))
        with patch.object(app.state, "plugin_manager", pm, create=True):
            resp = client.post("/api/plugins/p1/enable")
        assert resp.status_code == 200
        assert resp.json()["status"] == "enabled"

    def test_enable_error(self, client: TestClient) -> None:
        """Etkinlestirme hatasi 400 donmeli."""
        pm = _make_mock_plugin_manager()
        pm.enable_plugin = AsyncMock(side_effect=ValueError("hatali"))
        with patch.object(app.state, "plugin_manager", pm, create=True):
            resp = client.post("/api/plugins/err/enable")
        assert resp.status_code == 400


# === Disable Plugin Testleri ===


class TestDisablePlugin:
    """POST /api/plugins/{name}/disable testleri."""

    def test_disable_success(self, client: TestClient) -> None:
        """Plugin devre disi birakma basarili olmali."""
        pm = _make_mock_plugin_manager([_make_info("p1", state=PluginState.ENABLED)])
        pm.disable_plugin = AsyncMock(return_value=_make_info("p1", state=PluginState.DISABLED))
        with patch.object(app.state, "plugin_manager", pm, create=True):
            resp = client.post("/api/plugins/p1/disable")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disabled"

    def test_disable_error(self, client: TestClient) -> None:
        """Devre disi birakma hatasi 400 donmeli."""
        pm = _make_mock_plugin_manager()
        pm.disable_plugin = AsyncMock(side_effect=ValueError("yok"))
        with patch.object(app.state, "plugin_manager", pm, create=True):
            resp = client.post("/api/plugins/ghost/disable")
        assert resp.status_code == 400


# === Reload Testleri ===


class TestReloadPlugins:
    """POST /api/plugins/reload testleri."""

    def test_reload_success(self, client: TestClient) -> None:
        """Reload basarili olmali."""
        pm = _make_mock_plugin_manager()
        pm.shutdown = AsyncMock()
        pm.initialize = AsyncMock(return_value=2)
        pm.load_all = AsyncMock(return_value={
            "p1": _make_info("p1", state=PluginState.ENABLED),
            "p2": _make_info("p2", state=PluginState.ENABLED),
        })
        with patch.object(app.state, "plugin_manager", pm, create=True):
            resp = client.post("/api/plugins/reload")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "reloaded"
        assert data["discovered"] == 2
        assert data["enabled"] == 2

    def test_reload_no_manager(self, client: TestClient) -> None:
        """Plugin manager yoksa 503 donmeli."""
        with patch.object(app.state, "plugin_manager", None, create=True):
            resp = client.post("/api/plugins/reload")
        assert resp.status_code == 503
