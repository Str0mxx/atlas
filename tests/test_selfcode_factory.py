"""AgentFactory testleri.

Agent olusturma, sablon secimi, yetenek ekleme, arac baglama,
kod uretimi ve kayit defteri yonetimi testleri.
"""

import pytest

from app.core.selfcode.agent_factory import (
    AGENT_TEMPLATES,
    AgentFactory,
)
from app.models.selfcode import AgentBlueprint


# === Yardimci Fonksiyonlar ===


def _make_factory(**kwargs) -> AgentFactory:
    """Test icin AgentFactory olusturur."""
    return AgentFactory(**kwargs)


# === Init Testleri ===


class TestInit:
    """AgentFactory init testleri."""

    def test_defaults(self) -> None:
        af = _make_factory()
        assert af.auto_register is True
        assert af._registry == {}

    def test_auto_register_off(self) -> None:
        af = _make_factory(auto_register=False)
        assert af.auto_register is False


# === CreateAgent Testleri ===


class TestCreateAgent:
    """create_agent() testleri."""

    def test_basic_creation(self) -> None:
        af = _make_factory()
        bp = af.create_agent("test_agent", description="Test")
        assert isinstance(bp, AgentBlueprint)
        assert bp.name == "test_agent"

    def test_monitor_category(self) -> None:
        af = _make_factory()
        bp = af.create_agent("my_monitor", category="monitor")
        assert bp.base_class == "BaseMonitor"
        assert "monitoring" in bp.capabilities

    def test_analyzer_category(self) -> None:
        af = _make_factory()
        bp = af.create_agent("my_analyzer", category="analyzer")
        assert "analysis" in bp.capabilities

    def test_security_category(self) -> None:
        af = _make_factory()
        bp = af.create_agent("sec_agent", category="security")
        assert "security" in bp.capabilities

    def test_with_capabilities(self) -> None:
        af = _make_factory()
        bp = af.create_agent("agent", capabilities=["logging", "caching"])
        assert "logging" in bp.capabilities
        assert "caching" in bp.capabilities

    def test_with_tools(self) -> None:
        af = _make_factory()
        bp = af.create_agent("agent", tools=["ssh", "email"])
        assert "ssh" in bp.tools
        assert "email" in bp.tools

    def test_auto_register(self) -> None:
        af = _make_factory(auto_register=True)
        af.create_agent("auto_agent")
        assert af.get_agent("auto_agent") is not None

    def test_no_auto_register(self) -> None:
        af = _make_factory(auto_register=False)
        af.create_agent("no_reg_agent")
        assert af.get_agent("no_reg_agent") is None

    def test_with_config(self) -> None:
        af = _make_factory()
        bp = af.create_agent("agent", config={"key": "value"})
        assert bp.config["key"] == "value"

    def test_unknown_category_fallback(self) -> None:
        af = _make_factory()
        bp = af.create_agent("agent", category="nonexistent")
        assert bp.base_class == "BaseAgent"


# === SelectTemplate Testleri ===


class TestSelectTemplate:
    """select_template() testleri."""

    def test_monitor_template(self) -> None:
        af = _make_factory()
        t = af.select_template("monitor")
        assert t["base_class"] == "BaseMonitor"

    def test_generic_template(self) -> None:
        af = _make_factory()
        t = af.select_template("generic")
        assert t["capabilities"] == []

    def test_unknown_falls_back(self) -> None:
        af = _make_factory()
        t = af.select_template("unknown_category")
        assert t == AGENT_TEMPLATES["generic"]


# === InjectCapabilities Testleri ===


class TestInjectCapabilities:
    """inject_capabilities() testleri."""

    def test_add_capabilities(self) -> None:
        af = _make_factory()
        bp = AgentBlueprint(name="test", capabilities=["a"])
        af.inject_capabilities(bp, ["b", "c"])
        assert "b" in bp.capabilities
        assert "c" in bp.capabilities

    def test_no_duplicates(self) -> None:
        af = _make_factory()
        bp = AgentBlueprint(name="test", capabilities=["a", "b"])
        af.inject_capabilities(bp, ["a", "c"])
        assert bp.capabilities.count("a") == 1


# === BindTools Testleri ===


class TestBindTools:
    """bind_tools() testleri."""

    def test_add_tools(self) -> None:
        af = _make_factory()
        bp = AgentBlueprint(name="test")
        af.bind_tools(bp, ["ssh", "email"])
        assert "ssh" in bp.tools
        assert "email" in bp.tools

    def test_no_duplicate_tools(self) -> None:
        af = _make_factory()
        bp = AgentBlueprint(name="test", tools=["ssh"])
        af.bind_tools(bp, ["ssh", "email"])
        assert bp.tools.count("ssh") == 1


# === GenerateCode Testleri ===


class TestGenerateCode:
    """generate_code() testleri."""

    def test_code_generated(self) -> None:
        af = _make_factory()
        bp = af.create_agent("my_agent", description="Test agent")
        code = af.generate_code(bp)
        assert "class" in code
        assert "Agent" in code

    def test_has_init(self) -> None:
        af = _make_factory()
        bp = af.create_agent("worker")
        code = af.generate_code(bp)
        assert "__init__" in code

    def test_has_execute(self) -> None:
        af = _make_factory()
        bp = af.create_agent("worker")
        code = af.generate_code(bp)
        assert "execute" in code

    def test_has_analyze(self) -> None:
        af = _make_factory()
        bp = af.create_agent("worker")
        code = af.generate_code(bp)
        assert "analyze" in code

    def test_has_docstring(self) -> None:
        af = _make_factory()
        bp = af.create_agent("doc_agent", description="My desc")
        code = af.generate_code(bp)
        assert '"""' in code


# === Registry Testleri ===


class TestRegistry:
    """register/unregister/list/get testleri."""

    def test_register(self) -> None:
        af = _make_factory(auto_register=False)
        bp = AgentBlueprint(name="reg_test")
        af.register_agent(bp)
        assert af.get_agent("reg_test") is not None

    def test_unregister(self) -> None:
        af = _make_factory(auto_register=False)
        bp = AgentBlueprint(name="unreg_test")
        af.register_agent(bp)
        result = af.unregister_agent("unreg_test")
        assert result is True
        assert af.get_agent("unreg_test") is None

    def test_unregister_not_found(self) -> None:
        af = _make_factory()
        assert af.unregister_agent("nonexistent") is False

    def test_list_agents(self) -> None:
        af = _make_factory()
        af.create_agent("a1")
        af.create_agent("a2")
        agents = af.list_agents()
        assert len(agents) == 2

    def test_get_agent_not_found(self) -> None:
        af = _make_factory()
        assert af.get_agent("missing") is None

    def test_overwrite_on_re_register(self) -> None:
        af = _make_factory(auto_register=False)
        bp1 = AgentBlueprint(name="dup", description="first")
        bp2 = AgentBlueprint(name="dup", description="second")
        af.register_agent(bp1)
        af.register_agent(bp2)
        assert af.get_agent("dup").description == "second"


# === ToClassName Testleri ===


class TestToClassName:
    """_to_class_name() testleri."""

    def test_snake_case(self) -> None:
        assert AgentFactory._to_class_name("my_custom") == "MyCustomAgent"

    def test_already_has_agent(self) -> None:
        assert AgentFactory._to_class_name("security_agent") == "SecurityAgent"

    def test_dash_case(self) -> None:
        assert AgentFactory._to_class_name("data-processor") == "DataProcessorAgent"

    def test_single_word(self) -> None:
        assert AgentFactory._to_class_name("monitor") == "MonitorAgent"


# === AGENT_TEMPLATES Testleri ===


class TestAgentTemplates:
    """AGENT_TEMPLATES sabitleri testleri."""

    def test_monitor_exists(self) -> None:
        assert "monitor" in AGENT_TEMPLATES

    def test_analyzer_exists(self) -> None:
        assert "analyzer" in AGENT_TEMPLATES

    def test_communicator_exists(self) -> None:
        assert "communicator" in AGENT_TEMPLATES

    def test_security_exists(self) -> None:
        assert "security" in AGENT_TEMPLATES

    def test_generic_exists(self) -> None:
        assert "generic" in AGENT_TEMPLATES
