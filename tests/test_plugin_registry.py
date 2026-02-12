"""PluginRegistry testleri."""

import pytest

from app.core.plugins.registry import PluginRegistry
from app.models.plugin import (
    PluginInfo,
    PluginManifest,
    PluginState,
    PluginType,
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


def _make_info(name: str = "test_plugin", **kwargs) -> PluginInfo:
    """Test icin PluginInfo olusturur."""
    manifest = kwargs.pop("manifest", _make_manifest(name=name))
    return PluginInfo(manifest=manifest, **kwargs)


def _make_registry() -> PluginRegistry:
    """Test icin temiz PluginRegistry olusturur."""
    return PluginRegistry()


# === Init Testleri ===


class TestRegistryInit:
    """Registry baslatma testleri."""

    def test_empty_init(self) -> None:
        """Bos registry ile baslamali."""
        reg = _make_registry()
        assert reg.count_total() == 0
        assert reg.count_enabled() == 0

    def test_list_all_empty(self) -> None:
        """Bos registry bos liste donmeli."""
        reg = _make_registry()
        assert reg.list_all() == []


# === Register Testleri ===


class TestRegistryRegister:
    """Plugin kayit testleri."""

    def test_register(self) -> None:
        """Plugin kaydedilmeli."""
        reg = _make_registry()
        info = _make_info("my_plugin")
        reg.register(info)
        assert reg.count_total() == 1
        assert reg.has("my_plugin")

    def test_register_duplicate_raises(self) -> None:
        """Ayni isimli plugin tekrar kaydedilmemeli."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        with pytest.raises(ValueError, match="zaten kayitli"):
            reg.register(_make_info("p1"))

    def test_register_multiple(self) -> None:
        """Birden fazla plugin kaydedilmeli."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        reg.register(_make_info("p2"))
        assert reg.count_total() == 2


# === Unregister Testleri ===


class TestRegistryUnregister:
    """Plugin kayit silme testleri."""

    def test_unregister(self) -> None:
        """Plugin kaydi silinmeli."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        result = reg.unregister("p1")
        assert result is not None
        assert not reg.has("p1")

    def test_unregister_nonexistent(self) -> None:
        """Olmayan plugin icin None donmeli."""
        reg = _make_registry()
        assert reg.unregister("nonexistent") is None

    def test_unregister_preserves_others(self) -> None:
        """Diger plugin'ler korunmali."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        reg.register(_make_info("p2"))
        reg.unregister("p1")
        assert reg.has("p2")
        assert reg.count_total() == 1


# === Get Testleri ===


class TestRegistryGet:
    """Plugin sorgulama testleri."""

    def test_get_existing(self) -> None:
        """Kayitli plugin bulunmali."""
        reg = _make_registry()
        info = _make_info("p1")
        reg.register(info)
        result = reg.get("p1")
        assert result is not None
        assert result.manifest.name == "p1"

    def test_get_nonexistent(self) -> None:
        """Kayitsiz plugin icin None donmeli."""
        reg = _make_registry()
        assert reg.get("nonexistent") is None

    def test_has_true(self) -> None:
        """Kayitli plugin icin True donmeli."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        assert reg.has("p1") is True

    def test_has_false(self) -> None:
        """Kayitsiz plugin icin False donmeli."""
        reg = _make_registry()
        assert reg.has("p1") is False


# === List Testleri ===


class TestRegistryList:
    """Plugin listeleme testleri."""

    def test_list_all(self) -> None:
        """Tum plugin'ler listelenmeli."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        reg.register(_make_info("p2"))
        assert len(reg.list_all()) == 2

    def test_list_by_state(self) -> None:
        """Durum bazli filtreleme calismali."""
        reg = _make_registry()
        reg.register(_make_info("p1", state=PluginState.ENABLED))
        reg.register(_make_info("p2", state=PluginState.DISABLED))
        reg.register(_make_info("p3", state=PluginState.ENABLED))
        enabled = reg.list_by_state(PluginState.ENABLED)
        assert len(enabled) == 2

    def test_list_by_state_empty(self) -> None:
        """Esilesen durum yoksa bos liste donmeli."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        assert reg.list_by_state(PluginState.ENABLED) == []

    def test_list_by_type(self) -> None:
        """Tip bazli filtreleme calismali."""
        reg = _make_registry()
        m1 = _make_manifest(name="p1", plugin_type=PluginType.AGENT)
        m2 = _make_manifest(name="p2", plugin_type=PluginType.TOOL)
        m3 = _make_manifest(name="p3", plugin_type=PluginType.AGENT)
        reg.register(PluginInfo(manifest=m1))
        reg.register(PluginInfo(manifest=m2))
        reg.register(PluginInfo(manifest=m3))
        agents = reg.list_by_type(PluginType.AGENT)
        assert len(agents) == 2

    def test_get_names(self) -> None:
        """Plugin adlari listelenmeli."""
        reg = _make_registry()
        reg.register(_make_info("alpha"))
        reg.register(_make_info("beta"))
        names = reg.get_names()
        assert "alpha" in names
        assert "beta" in names


# === Update State Testleri ===


class TestRegistryUpdateState:
    """Plugin durum guncelleme testleri."""

    def test_update_state(self) -> None:
        """Durum guncellenebilmeli."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        result = reg.update_state("p1", PluginState.LOADED)
        assert result is not None
        assert result.state == PluginState.LOADED

    def test_update_state_nonexistent(self) -> None:
        """Olmayan plugin icin None donmeli."""
        reg = _make_registry()
        assert reg.update_state("x", PluginState.LOADED) is None

    def test_update_state_error_with_message(self) -> None:
        """Hata durumunda mesaj atanmali."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        result = reg.update_state("p1", PluginState.ERROR, "Import hatasi")
        assert result is not None
        assert result.error_message == "Import hatasi"

    def test_update_state_clears_error_message(self) -> None:
        """Hata disindaki durumda hata mesaji temizlenmeli."""
        reg = _make_registry()
        reg.register(_make_info("p1", state=PluginState.ERROR, error_message="eski"))
        result = reg.update_state("p1", PluginState.LOADED)
        assert result is not None
        assert result.error_message is None


# === Count Testleri ===


class TestRegistryCount:
    """Sayim testleri."""

    def test_count_total(self) -> None:
        """Toplam sayi dogru olmali."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        reg.register(_make_info("p2"))
        assert reg.count_total() == 2

    def test_count_enabled(self) -> None:
        """Etkin sayi dogru olmali."""
        reg = _make_registry()
        reg.register(_make_info("p1", state=PluginState.ENABLED))
        reg.register(_make_info("p2", state=PluginState.DISABLED))
        assert reg.count_enabled() == 1

    def test_count_by_state(self) -> None:
        """Durum bazinda sayim dogru olmali."""
        reg = _make_registry()
        reg.register(_make_info("p1", state=PluginState.ENABLED))
        reg.register(_make_info("p2", state=PluginState.ENABLED))
        reg.register(_make_info("p3", state=PluginState.ERROR, error_message="x"))
        counts = reg.count_by_state()
        assert counts["enabled"] == 2
        assert counts["error"] == 1


# === Config Testleri ===


class TestRegistryConfig:
    """Plugin yapilandirma testleri."""

    def test_set_config_value(self) -> None:
        """Config degeri atanabilmeli."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        assert reg.set_config_value("p1", "url", "http://x") is True

    def test_get_config_value(self) -> None:
        """Config degeri okunabilmeli."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        reg.set_config_value("p1", "url", "http://x")
        assert reg.get_config_value("p1", "url") == "http://x"

    def test_get_config_default(self) -> None:
        """Olmayan anahtar icin varsayilan donmeli."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        assert reg.get_config_value("p1", "missing", "default") == "default"

    def test_config_nonexistent_plugin(self) -> None:
        """Olmayan plugin icin set/get calismali."""
        reg = _make_registry()
        assert reg.set_config_value("x", "k", "v") is False
        assert reg.get_config_value("x", "k") is None


# === Clear Testleri ===


class TestRegistryClear:
    """Registry temizleme testleri."""

    def test_clear(self) -> None:
        """Clear tum kayitlari silmeli."""
        reg = _make_registry()
        reg.register(_make_info("p1"))
        reg.register(_make_info("p2"))
        reg.clear()
        assert reg.count_total() == 0

    def test_clear_empty(self) -> None:
        """Bos registry temizlenebilmeli."""
        reg = _make_registry()
        reg.clear()
        assert reg.count_total() == 0
