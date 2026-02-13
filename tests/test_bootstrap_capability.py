"""CapabilityBuilder testleri.

Agent, tool, monitor, API istemci ve plugin
sablon olusturma ve scaffold uretim testleri.
"""

from unittest.mock import MagicMock

import pytest

from app.core.bootstrap.capability_builder import (
    BASE_CLASSES,
    CapabilityBuilder,
    DEFAULT_AGENT_METHODS,
)
from app.models.bootstrap import (
    CapabilityCategory,
    CapabilityTemplate,
    ScaffoldResult,
)


# === Yardimci Fonksiyonlar ===


def _make_builder() -> CapabilityBuilder:
    """Test icin CapabilityBuilder olusturur."""
    return CapabilityBuilder()


def _make_template(**kwargs) -> CapabilityTemplate:
    """Test icin CapabilityTemplate olusturur."""
    defaults = {"name": "test_capability"}
    defaults.update(kwargs)
    return CapabilityTemplate(**defaults)


# === Enum ve Model Testleri ===


class TestCapabilityCategory:
    """CapabilityCategory enum testleri."""

    def test_agent(self) -> None:
        assert CapabilityCategory.AGENT == "agent"

    def test_tool(self) -> None:
        assert CapabilityCategory.TOOL == "tool"

    def test_monitor(self) -> None:
        assert CapabilityCategory.MONITOR == "monitor"

    def test_api_client(self) -> None:
        assert CapabilityCategory.API_CLIENT == "api_client"

    def test_plugin(self) -> None:
        assert CapabilityCategory.PLUGIN == "plugin"


class TestCapabilityTemplate:
    """CapabilityTemplate model testleri."""

    def test_defaults(self) -> None:
        t = _make_template()
        assert t.name == "test_capability"
        assert t.category == CapabilityCategory.TOOL
        assert t.methods == []

    def test_unique_ids(self) -> None:
        a = _make_template()
        b = _make_template()
        assert a.id != b.id

    def test_timestamp(self) -> None:
        t = _make_template()
        assert t.generated_at is not None


class TestScaffoldResult:
    """ScaffoldResult model testleri."""

    def test_defaults(self) -> None:
        r = ScaffoldResult(template_id="abc")
        assert r.template_id == "abc"
        assert r.files_generated == []
        assert r.success is True

    def test_with_files(self) -> None:
        r = ScaffoldResult(
            template_id="abc",
            files_generated=["agent.py", "test_agent.py"],
            total_loc=150,
        )
        assert len(r.files_generated) == 2
        assert r.total_loc == 150


# === CapabilityBuilder Init Testleri ===


class TestCapabilityBuilderInit:
    """CapabilityBuilder init testleri."""

    def test_empty(self) -> None:
        cb = _make_builder()
        assert cb.templates == {}


# === CreateAgentTemplate Testleri ===


class TestCreateAgentTemplate:
    """create_agent_template testleri."""

    def test_basic(self) -> None:
        cb = _make_builder()
        t = cb.create_agent_template("stock_agent")
        assert t.name == "stock_agent"
        assert t.category == CapabilityCategory.AGENT
        assert t.base_class == "BaseAgent"
        assert len(t.methods) == len(DEFAULT_AGENT_METHODS)

    def test_with_keywords(self) -> None:
        cb = _make_builder()
        t = cb.create_agent_template("stock_agent", keywords=["stok", "envanter"])
        assert any("keywords" in d for d in t.dependencies)

    def test_with_methods(self) -> None:
        cb = _make_builder()
        t = cb.create_agent_template("custom", methods=["run", "stop"])
        assert len(t.methods) == 2
        assert t.methods[0]["name"] == "run"

    def test_stored_in_templates(self) -> None:
        cb = _make_builder()
        t = cb.create_agent_template("stock_agent")
        assert cb.templates[t.id] is t


# === CreateToolTemplate Testleri ===


class TestCreateToolTemplate:
    """create_tool_template testleri."""

    def test_basic(self) -> None:
        cb = _make_builder()
        t = cb.create_tool_template("data_fetcher")
        assert t.name == "data_fetcher"
        assert t.category == CapabilityCategory.TOOL
        assert t.base_class == "object"

    def test_with_dependencies(self) -> None:
        cb = _make_builder()
        t = cb.create_tool_template("scraper", dependencies=["httpx", "bs4"])
        assert t.dependencies == ["httpx", "bs4"]

    def test_custom_methods(self) -> None:
        cb = _make_builder()
        t = cb.create_tool_template("parser", methods=["parse", "clean"])
        assert len(t.methods) == 2


# === CreateMonitorTemplate Testleri ===


class TestCreateMonitorTemplate:
    """create_monitor_template testleri."""

    def test_basic(self) -> None:
        cb = _make_builder()
        t = cb.create_monitor_template("health_monitor")
        assert t.name == "health_monitor"
        assert t.category == CapabilityCategory.MONITOR
        assert t.base_class == "BaseMonitor"

    def test_has_default_methods(self) -> None:
        cb = _make_builder()
        t = cb.create_monitor_template("test_mon")
        method_names = [m["name"] for m in t.methods]
        assert "check" in method_names
        assert "evaluate" in method_names
        assert "alert" in method_names


# === CreateApiClientTemplate Testleri ===


class TestCreateApiClientTemplate:
    """create_api_client_template testleri."""

    def test_basic(self) -> None:
        cb = _make_builder()
        t = cb.create_api_client_template("weather_api")
        assert t.name == "weather_api"
        assert t.category == CapabilityCategory.API_CLIENT

    def test_with_endpoints(self) -> None:
        cb = _make_builder()
        t = cb.create_api_client_template(
            "weather_api",
            endpoints=[
                {"name": "get_weather", "method": "GET", "path": "/weather"},
                {"name": "post_data", "method": "POST", "path": "/data"},
            ],
        )
        assert len(t.methods) == 2
        assert t.methods[0]["name"] == "get_weather"

    def test_default_methods_when_no_endpoints(self) -> None:
        cb = _make_builder()
        t = cb.create_api_client_template("basic_api")
        assert len(t.methods) == 2  # get, post


# === CreatePluginScaffold Testleri ===


class TestCreatePluginScaffold:
    """create_plugin_scaffold testleri."""

    def test_basic(self) -> None:
        cb = _make_builder()
        t = cb.create_plugin_scaffold("my_plugin")
        assert t.name == "my_plugin"
        assert t.category == CapabilityCategory.PLUGIN

    def test_has_lifecycle_methods(self) -> None:
        cb = _make_builder()
        t = cb.create_plugin_scaffold("my_plugin")
        method_names = [m["name"] for m in t.methods]
        assert "on_load" in method_names
        assert "on_enable" in method_names
        assert "on_disable" in method_names


# === GenerateClassCode Testleri ===


class TestGenerateClassCode:
    """generate_class_code testleri."""

    def test_agent_code(self) -> None:
        cb = _make_builder()
        t = cb.create_agent_template("stock_agent")
        code = cb.generate_class_code(t)
        assert "class StockAgent" in code
        assert "BaseAgent" in code

    def test_tool_code(self) -> None:
        cb = _make_builder()
        t = cb.create_tool_template("data_fetcher")
        code = cb.generate_class_code(t)
        assert "class DataFetcher" in code

    def test_monitor_code(self) -> None:
        cb = _make_builder()
        t = cb.create_monitor_template("health_monitor")
        code = cb.generate_class_code(t)
        assert "class HealthMonitor" in code
        assert "BaseMonitor" in code


# === GenerateTestCode Testleri ===


class TestGenerateTestCode:
    """generate_test_code testleri."""

    def test_generates_test(self) -> None:
        cb = _make_builder()
        t = cb.create_agent_template("stock_agent")
        code = cb.generate_test_code(t)
        assert "TestStockAgentInit" in code
        assert "def test_create" in code

    def test_includes_method_tests(self) -> None:
        cb = _make_builder()
        t = cb.create_tool_template("parser", methods=["parse"])
        code = cb.generate_test_code(t)
        assert "test_parse_basic" in code


# === GenerateManifest Testleri ===


class TestGenerateManifest:
    """generate_manifest testleri."""

    def test_agent_manifest(self) -> None:
        cb = _make_builder()
        t = cb.create_agent_template("stock_agent")
        manifest = cb.generate_manifest(t)
        assert manifest["name"] == "stock_agent"
        assert manifest["type"] == "agent"
        assert "agents" in manifest["provides"]

    def test_tool_manifest(self) -> None:
        cb = _make_builder()
        t = cb.create_tool_template("data_fetcher")
        manifest = cb.generate_manifest(t)
        assert manifest["type"] == "tool"
        assert "tools" in manifest["provides"]


# === GetTemplate Testleri ===


class TestGetTemplate:
    """get_template testleri."""

    def test_found(self) -> None:
        cb = _make_builder()
        t = cb.create_agent_template("test")
        result = cb.get_template(t.id)
        assert result is t

    def test_not_found(self) -> None:
        cb = _make_builder()
        result = cb.get_template("nonexistent")
        assert result is None


# === ListTemplates Testleri ===


class TestListTemplates:
    """list_templates testleri."""

    def test_empty(self) -> None:
        cb = _make_builder()
        assert cb.list_templates() == []

    def test_all(self) -> None:
        cb = _make_builder()
        cb.create_agent_template("a1")
        cb.create_tool_template("t1")
        assert len(cb.list_templates()) == 2

    def test_filter_by_category(self) -> None:
        cb = _make_builder()
        cb.create_agent_template("a1")
        cb.create_tool_template("t1")
        agents = cb.list_templates(category=CapabilityCategory.AGENT)
        assert len(agents) == 1
        assert agents[0].name == "a1"
