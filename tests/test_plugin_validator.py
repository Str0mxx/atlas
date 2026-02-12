"""PluginValidator testleri."""

from typing import Any

import pytest

from app.agents.base_agent import BaseAgent, TaskResult
from app.core.plugins.validator import PluginValidator
from app.models.plugin import (
    AgentProvision,
    HookProvision,
    PluginConfigField,
    PluginManifest,
    PluginProvides,
)
from app.monitors.base_monitor import BaseMonitor, MonitorResult


# === Yardimci Siniflar ===


class ValidAgent(BaseAgent):
    """Gecerli test agent'i."""

    def __init__(self) -> None:
        super().__init__(name="valid_test")

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        return TaskResult(success=True)

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def report(self, result: TaskResult) -> str:
        return ""


class AgentMissingReport(BaseAgent):
    """report metodu eksik agent (hala soyut)."""

    def __init__(self) -> None:
        super().__init__(name="incomplete")

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        return TaskResult(success=True)

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {}


class SyncMethodAgent(BaseAgent):
    """Sync execute metodu olan agent."""

    def __init__(self) -> None:
        super().__init__(name="sync_agent")

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        return TaskResult(success=True)

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {}

    def report(self, result: TaskResult) -> str:  # type: ignore[override]
        return ""


class ValidMonitor(BaseMonitor):
    """Gecerli test monitor'u."""

    async def check(self) -> MonitorResult:
        return MonitorResult()


class NotAClass:
    """BaseAgent'dan miras almayan sinif."""

    pass


# === Yardimci Fonksiyonlar ===


def _make_validator() -> PluginValidator:
    """Test icin PluginValidator olusturur."""
    return PluginValidator()


def _make_manifest(**kwargs) -> PluginManifest:
    """Test icin manifest olusturur."""
    defaults: dict[str, Any] = {
        "name": "test_plugin",
        "version": "1.0.0",
    }
    defaults.update(kwargs)
    return PluginManifest(**defaults)


# === Manifest Dogrulama Testleri ===


class TestValidateManifest:
    """Manifest dogrulama testleri."""

    def test_valid_manifest(self) -> None:
        """Gecerli manifest hata donmemeli."""
        v = _make_validator()
        m = _make_manifest()
        assert v.validate_manifest(m) == []

    def test_empty_name(self) -> None:
        """Bos isimli manifest hata donmeli."""
        v = _make_validator()
        m = _make_manifest(name="")
        errors = v.validate_manifest(m)
        assert any("bos" in e for e in errors)

    def test_whitespace_name(self) -> None:
        """Bosluklu isim hata donmeli."""
        v = _make_validator()
        m = _make_manifest(name="   ")
        errors = v.validate_manifest(m)
        assert len(errors) > 0

    def test_invalid_name_chars(self) -> None:
        """Gecersiz karakterli isim hata donmeli."""
        v = _make_validator()
        m = _make_manifest(name="test plugin!")
        errors = v.validate_manifest(m)
        assert any("Gecersiz plugin adi" in e for e in errors)

    def test_valid_name_with_dash_underscore(self) -> None:
        """Tire ve alt cizgi iceren isim gecerli olmali."""
        v = _make_validator()
        m = _make_manifest(name="my-test_plugin")
        assert v.validate_manifest(m) == []

    def test_empty_version(self) -> None:
        """Bos surum hata donmeli."""
        v = _make_validator()
        m = _make_manifest(version="")
        errors = v.validate_manifest(m)
        assert any("surum" in e.lower() or "bos" in e for e in errors)

    def test_invalid_hook_event(self) -> None:
        """Gecersiz hook olayi hata donmeli."""
        v = _make_validator()
        m = _make_manifest(
            provides=PluginProvides(
                hooks=[HookProvision(event="nonexistent_event", handler="h.f")]
            )
        )
        errors = v.validate_manifest(m)
        assert any("Gecersiz hook olayi" in e for e in errors)

    def test_valid_hook_event(self) -> None:
        """Gecerli hook olayi hata donmemeli."""
        v = _make_validator()
        m = _make_manifest(
            provides=PluginProvides(
                hooks=[HookProvision(event="task_created", handler="h.f")]
            )
        )
        assert v.validate_manifest(m) == []

    def test_invalid_handler_path(self) -> None:
        """Dotted path olmayan handler hata donmeli."""
        v = _make_validator()
        m = _make_manifest(
            provides=PluginProvides(
                hooks=[HookProvision(event="task_created", handler="nopath")]
            )
        )
        errors = v.validate_manifest(m)
        assert any("Gecersiz handler yolu" in e for e in errors)


# === Agent Sinif Dogrulama Testleri ===


class TestValidateAgentClass:
    """Agent sinif dogrulama testleri."""

    def test_valid_agent(self) -> None:
        """Gecerli agent sinifi hata donmemeli."""
        v = _make_validator()
        assert v.validate_agent_class(ValidAgent) == []

    def test_not_subclass(self) -> None:
        """BaseAgent'dan miras almayan sinif hata donmeli."""
        v = _make_validator()
        errors = v.validate_agent_class(NotAClass)
        assert any("miras almiyor" in e for e in errors)

    def test_not_a_class(self) -> None:
        """Sinif olmayan deger hata donmeli."""
        v = _make_validator()
        errors = v.validate_agent_class("not_a_class")  # type: ignore[arg-type]
        assert any("miras almiyor" in e for e in errors)

    def test_abstract_method_still_abstract(self) -> None:
        """Soyut metodu implement etmeyen sinif hata donmeli."""
        v = _make_validator()
        # AgentMissingReport cannot be instantiated but we can check the class
        # Since it still has abstract report, validation should catch it
        errors = v.validate_agent_class(AgentMissingReport)
        assert any("report" in e and "soyut" in e for e in errors)

    def test_sync_method_error(self) -> None:
        """Sync metodu olan agent hata donmeli."""
        v = _make_validator()
        errors = v.validate_agent_class(SyncMethodAgent)
        assert any("async" in e for e in errors)

    def test_base_agent_itself(self) -> None:
        """BaseAgent soyut sinifinin kendisi hata donmeli."""
        v = _make_validator()
        errors = v.validate_agent_class(BaseAgent)
        assert len(errors) > 0


# === Monitor Sinif Dogrulama Testleri ===


class TestValidateMonitorClass:
    """Monitor sinif dogrulama testleri."""

    def test_valid_monitor(self) -> None:
        """Gecerli monitor sinifi hata donmemeli."""
        v = _make_validator()
        assert v.validate_monitor_class(ValidMonitor) == []

    def test_not_subclass(self) -> None:
        """BaseMonitor'dan miras almayan sinif hata donmeli."""
        v = _make_validator()
        errors = v.validate_monitor_class(NotAClass)
        assert any("miras almiyor" in e for e in errors)

    def test_base_monitor_itself(self) -> None:
        """BaseMonitor soyut sinifinin kendisi hata donmeli."""
        v = _make_validator()
        errors = v.validate_monitor_class(BaseMonitor)
        assert len(errors) > 0

    def test_not_a_class(self) -> None:
        """Sinif olmayan deger hata donmeli."""
        v = _make_validator()
        errors = v.validate_monitor_class(42)  # type: ignore[arg-type]
        assert any("miras almiyor" in e for e in errors)


# === Tool Sinif Dogrulama Testleri ===


class TestValidateToolClass:
    """Tool sinif dogrulama testleri."""

    def test_valid_tool(self) -> None:
        """Herhangi bir sinif gecerli olmali."""
        v = _make_validator()
        assert v.validate_tool_class(NotAClass) == []

    def test_not_a_class(self) -> None:
        """Sinif olmayan deger hata donmeli."""
        v = _make_validator()
        errors = v.validate_tool_class("not_a_class")  # type: ignore[arg-type]
        assert any("sinif degil" in e for e in errors)


# === Config Key Dogrulama Testleri ===


class TestValidateConfigKeys:
    """Config anahtar cakisma testleri."""

    def test_no_collision(self) -> None:
        """Cakisma olmadan hata donmemeli."""
        v = _make_validator()
        config = {"my_key": PluginConfigField()}
        existing = {"other_key"}
        assert v.validate_config_keys("test", config, existing) == []

    def test_collision(self) -> None:
        """Cakisma durumunda hata donmeli."""
        v = _make_validator()
        config = {"database_url": PluginConfigField()}
        existing = {"database_url", "redis_url"}
        errors = v.validate_config_keys("test", config, existing)
        assert any("cakismasi" in e for e in errors)

    def test_multiple_collisions(self) -> None:
        """Birden fazla cakisma raporlanmali."""
        v = _make_validator()
        config = {
            "key_a": PluginConfigField(),
            "key_b": PluginConfigField(),
        }
        existing = {"key_a", "key_b"}
        errors = v.validate_config_keys("test", config, existing)
        assert len(errors) == 2

    def test_empty_config(self) -> None:
        """Bos config hata donmemeli."""
        v = _make_validator()
        assert v.validate_config_keys("test", {}, {"key_a"}) == []


# === Hook Handler Dogrulama Testleri ===


class TestValidateHookHandler:
    """Hook handler dogrulama testleri."""

    def test_valid_async_handler(self) -> None:
        """Gecerli async handler hata donmemeli."""
        v = _make_validator()

        async def handler(**kwargs):
            pass

        assert v.validate_hook_handler(handler) == []

    def test_sync_handler(self) -> None:
        """Sync handler hata donmeli."""
        v = _make_validator()

        def handler(**kwargs):
            pass

        errors = v.validate_hook_handler(handler)
        assert any("async" in e for e in errors)

    def test_not_callable(self) -> None:
        """Callable olmayan deger hata donmeli."""
        v = _make_validator()
        errors = v.validate_hook_handler("not_callable")
        assert any("callable" in e for e in errors)

    def test_none_handler(self) -> None:
        """None handler hata donmeli."""
        v = _make_validator()
        errors = v.validate_hook_handler(None)
        assert any("callable" in e for e in errors)
