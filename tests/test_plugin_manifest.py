"""Plugin manifest yukleme testleri."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.plugins.manifest import (
    _parse_manifest_data,
    discover_manifests,
    load_manifest_from_file,
    load_manifest_from_string,
)
from app.models.plugin import PluginType


# === Yardimci Fonksiyonlar ===


def _make_manifest_dict(**kwargs) -> dict:
    """Test icin ham manifest sozlugu olusturur."""
    defaults = {
        "name": "test_plugin",
        "version": "1.0.0",
    }
    defaults.update(kwargs)
    return defaults


def _make_manifest_json(**kwargs) -> str:
    """Test icin manifest JSON string olusturur."""
    return json.dumps(_make_manifest_dict(**kwargs))


def _write_plugin(tmp_path: Path, name: str, manifest: dict) -> Path:
    """tmp_path altinda plugin dizini ve manifest dosyasi olusturur."""
    plugin_dir = tmp_path / name
    plugin_dir.mkdir()
    manifest_file = plugin_dir / "plugin.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    return plugin_dir


# === load_manifest_from_string Testleri ===


class TestLoadFromString:
    """JSON string'den manifest yukleme testleri."""

    def test_minimal(self) -> None:
        """Minimal manifest yuklenebilmeli."""
        m = load_manifest_from_string(_make_manifest_json())
        assert m.name == "test_plugin"
        assert m.version == "1.0.0"

    def test_full(self) -> None:
        """Tum alanlarla yuklenebilmeli."""
        raw = _make_manifest_json(
            description="Tam manifest",
            author="Fatih",
            type="agent",
        )
        m = load_manifest_from_string(raw)
        assert m.description == "Tam manifest"
        assert m.author == "Fatih"
        assert m.plugin_type == PluginType.AGENT

    def test_invalid_json_raises(self) -> None:
        """Gecersiz JSON hata vermeli."""
        with pytest.raises(json.JSONDecodeError):
            load_manifest_from_string("{invalid json")

    def test_missing_name_raises(self) -> None:
        """name olmadan hata vermeli."""
        with pytest.raises(ValidationError):
            load_manifest_from_string('{"version": "1.0.0"}')

    def test_missing_version_raises(self) -> None:
        """version olmadan hata vermeli."""
        with pytest.raises(ValidationError):
            load_manifest_from_string('{"name": "test"}')

    def test_with_provides_agents(self) -> None:
        """Agent provision yuklenebilmeli."""
        raw = _make_manifest_json(
            provides={
                "agents": [
                    {"class": "TestAgent", "module": "agent", "keywords": ["test"]}
                ]
            }
        )
        m = load_manifest_from_string(raw)
        assert len(m.provides.agents) == 1
        assert m.provides.agents[0].class_name == "TestAgent"
        assert m.provides.agents[0].keywords == ["test"]

    def test_with_provides_monitors(self) -> None:
        """Monitor provision yuklenebilmeli."""
        raw = _make_manifest_json(
            provides={
                "monitors": [
                    {"class": "TestMon", "module": "mon", "check_interval": 60}
                ]
            }
        )
        m = load_manifest_from_string(raw)
        assert len(m.provides.monitors) == 1
        assert m.provides.monitors[0].class_name == "TestMon"

    def test_with_provides_hooks(self) -> None:
        """Hook provision yuklenebilmeli."""
        raw = _make_manifest_json(
            provides={
                "hooks": [{"event": "task_created", "handler": "hooks.on_create"}]
            }
        )
        m = load_manifest_from_string(raw)
        assert len(m.provides.hooks) == 1

    def test_with_config(self) -> None:
        """Config alanlari yuklenebilmeli."""
        raw = _make_manifest_json(
            config={
                "api_url": {"type": "str", "default": "http://x", "description": "URL"}
            }
        )
        m = load_manifest_from_string(raw)
        assert "api_url" in m.config
        assert m.config["api_url"].default == "http://x"

    def test_with_dependencies(self) -> None:
        """Bagimliliklar yuklenebilmeli."""
        raw = _make_manifest_json(dependencies=["dep_a", "dep_b"])
        m = load_manifest_from_string(raw)
        assert m.dependencies == ["dep_a", "dep_b"]


# === load_manifest_from_file Testleri ===


class TestLoadFromFile:
    """Dosyadan manifest yukleme testleri."""

    def test_load(self, tmp_path: Path) -> None:
        """Dosyadan manifest yuklenebilmeli."""
        manifest_file = tmp_path / "plugin.json"
        manifest_file.write_text(_make_manifest_json(), encoding="utf-8")
        m = load_manifest_from_file(manifest_file)
        assert m.name == "test_plugin"

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Olmayan dosya icin hata vermeli."""
        with pytest.raises(FileNotFoundError):
            load_manifest_from_file(tmp_path / "nonexistent.json")

    def test_invalid_json(self, tmp_path: Path) -> None:
        """Gecersiz JSON icin hata vermeli."""
        f = tmp_path / "plugin.json"
        f.write_text("{bad}", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_manifest_from_file(f)

    def test_utf8_encoding(self, tmp_path: Path) -> None:
        """UTF-8 karakterler dogru okunmali."""
        data = _make_manifest_dict(description="Türkçe açıklama")
        f = tmp_path / "plugin.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        m = load_manifest_from_file(f)
        assert "Türkçe" in m.description


# === _parse_manifest_data Testleri ===


class TestParseManifestData:
    """Manifest sozluk parse testleri."""

    def test_type_to_plugin_type(self) -> None:
        """'type' alani 'plugin_type'a eslenmeli."""
        data = _make_manifest_dict(type="agent")
        m = _parse_manifest_data(data)
        assert m.plugin_type == PluginType.AGENT

    def test_class_to_class_name_in_agents(self) -> None:
        """'class' alani 'class_name'e eslenmeli (agents)."""
        data = _make_manifest_dict(
            provides={"agents": [{"class": "Foo", "module": "foo"}]}
        )
        m = _parse_manifest_data(data)
        assert m.provides.agents[0].class_name == "Foo"

    def test_class_to_class_name_in_monitors(self) -> None:
        """'class' alani 'class_name'e eslenmeli (monitors)."""
        data = _make_manifest_dict(
            provides={"monitors": [{"class": "Mon", "module": "mon"}]}
        )
        m = _parse_manifest_data(data)
        assert m.provides.monitors[0].class_name == "Mon"

    def test_class_to_class_name_in_tools(self) -> None:
        """'class' alani 'class_name'e eslenmeli (tools)."""
        data = _make_manifest_dict(
            provides={"tools": [{"class": "Tool", "module": "tool"}]}
        )
        m = _parse_manifest_data(data)
        assert m.provides.tools[0].class_name == "Tool"

    def test_plugin_type_not_overwritten(self) -> None:
        """'plugin_type' zaten varsa 'type' eslenmemeli."""
        data = _make_manifest_dict(plugin_type="tool", type="agent")
        m = _parse_manifest_data(data)
        # type kaldirilir ama plugin_type korunur
        assert m.plugin_type == PluginType.TOOL

    def test_class_name_not_overwritten(self) -> None:
        """'class_name' zaten varsa 'class' eslenmemeli."""
        data = _make_manifest_dict(
            provides={"agents": [{"class_name": "Real", "class": "Fake", "module": "m"}]}
        )
        m = _parse_manifest_data(data)
        assert m.provides.agents[0].class_name == "Real"


# === discover_manifests Testleri ===


class TestDiscoverManifests:
    """Manifest kesfi testleri."""

    def test_discover_single(self, tmp_path: Path) -> None:
        """Tek plugin kesfedilmeli."""
        _write_plugin(tmp_path, "my_plugin", _make_manifest_dict(name="my_plugin"))
        results = discover_manifests(tmp_path)
        assert len(results) == 1
        assert results[0][1].name == "my_plugin"

    def test_discover_multiple(self, tmp_path: Path) -> None:
        """Birden fazla plugin kesfedilmeli."""
        _write_plugin(tmp_path, "p1", _make_manifest_dict(name="p1"))
        _write_plugin(tmp_path, "p2", _make_manifest_dict(name="p2"))
        results = discover_manifests(tmp_path)
        assert len(results) == 2

    def test_skip_underscore_dirs(self, tmp_path: Path) -> None:
        """Alt cizgi ile baslayan dizinler atlanmali."""
        _write_plugin(tmp_path, "_example", _make_manifest_dict(name="_example"))
        _write_plugin(tmp_path, "real", _make_manifest_dict(name="real"))
        results = discover_manifests(tmp_path)
        assert len(results) == 1
        assert results[0][1].name == "real"

    def test_skip_dot_dirs(self, tmp_path: Path) -> None:
        """Nokta ile baslayan dizinler atlanmali."""
        _write_plugin(tmp_path, ".hidden", _make_manifest_dict(name="hidden"))
        results = discover_manifests(tmp_path)
        assert len(results) == 0

    def test_skip_no_manifest(self, tmp_path: Path) -> None:
        """Manifest olmayan dizinler atlanmali."""
        (tmp_path / "empty_dir").mkdir()
        results = discover_manifests(tmp_path)
        assert len(results) == 0

    def test_skip_files(self, tmp_path: Path) -> None:
        """Dosyalar (dizin degil) atlanmali."""
        (tmp_path / "some_file.txt").write_text("hello")
        results = discover_manifests(tmp_path)
        assert len(results) == 0

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        """Olmayan dizin bos liste donmeli."""
        results = discover_manifests(tmp_path / "nonexistent")
        assert results == []

    def test_invalid_manifest_skipped(self, tmp_path: Path) -> None:
        """Gecersiz manifest atlanmali, hata vermemeli."""
        plugin_dir = tmp_path / "bad_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text("{invalid", encoding="utf-8")
        _write_plugin(tmp_path, "good", _make_manifest_dict(name="good"))
        results = discover_manifests(tmp_path)
        assert len(results) == 1
        assert results[0][1].name == "good"

    def test_returns_plugin_dir_path(self, tmp_path: Path) -> None:
        """Sonuc plugin dizin yolunu icermeli."""
        _write_plugin(tmp_path, "my_plugin", _make_manifest_dict(name="my_plugin"))
        results = discover_manifests(tmp_path)
        assert results[0][0] == tmp_path / "my_plugin"

    def test_sorted_alphabetically(self, tmp_path: Path) -> None:
        """Sonuclar alfabetik siralanmali."""
        _write_plugin(tmp_path, "zebra", _make_manifest_dict(name="zebra"))
        _write_plugin(tmp_path, "alpha", _make_manifest_dict(name="alpha"))
        results = discover_manifests(tmp_path)
        assert results[0][1].name == "alpha"
        assert results[1][1].name == "zebra"
