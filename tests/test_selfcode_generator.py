"""CodeGenerator testleri.

Sablon uretimi, fonksiyon/sinif/modul uretimi, docstring ekleme,
import yonetimi ve stil uygulamasi testleri.
"""

import pytest

from app.core.selfcode.code_generator import (
    TEMPLATES,
    TYPE_HINT_MAP,
    CodeGenerator,
)
from app.models.selfcode import (
    CodeGenerationRequest,
    CodeGenStrategy,
    CodeStyle,
    GeneratedCode,
)


# === Yardimci Fonksiyonlar ===


def _make_generator(**kwargs) -> CodeGenerator:
    """Test icin CodeGenerator olusturur."""
    return CodeGenerator(**kwargs)


def _make_request(**kwargs) -> CodeGenerationRequest:
    """Test icin CodeGenerationRequest olusturur."""
    return CodeGenerationRequest(**kwargs)


# === Init Testleri ===


class TestInit:
    """CodeGenerator init testleri."""

    def test_defaults(self) -> None:
        cg = _make_generator()
        assert cg.default_style == CodeStyle.PEP8
        assert cg.indent_size == 4
        assert cg.max_line_length == 88

    def test_custom_style(self) -> None:
        cg = _make_generator(default_style=CodeStyle.GOOGLE)
        assert cg.default_style == CodeStyle.GOOGLE

    def test_custom_indent(self) -> None:
        cg = _make_generator(indent_size=2)
        assert cg.indent_size == 2
        assert cg._indent == "  "


# === Generate Testleri ===


class TestGenerate:
    """generate() testleri."""

    def test_template_strategy(self) -> None:
        cg = _make_generator()
        req = _make_request(
            description="Basit fonksiyon",
            strategy=CodeGenStrategy.TEMPLATE,
            context={"name": "my_func", "body": "return 42"},
        )
        result = cg.generate(req)
        assert isinstance(result, GeneratedCode)
        assert result.confidence > 0
        assert "my_func" in result.code

    def test_llm_strategy_returns_placeholder(self) -> None:
        cg = _make_generator()
        req = _make_request(
            description="LLM test",
            strategy=CodeGenStrategy.LLM,
        )
        result = cg.generate(req)
        assert result.confidence == 0.0
        assert "LLM" in result.metadata.get("note", "")

    def test_hybrid_strategy(self) -> None:
        cg = _make_generator()
        req = _make_request(
            description="Hibrit test",
            strategy=CodeGenStrategy.HYBRID,
            context={"name": "hybrid_func"},
        )
        result = cg.generate(req)
        assert isinstance(result, GeneratedCode)

    def test_request_id_carried(self) -> None:
        cg = _make_generator()
        req = _make_request(description="ID test")
        result = cg.generate(req)
        assert result.request_id == req.id

    def test_style_enforced(self) -> None:
        cg = _make_generator()
        req = _make_request(
            description="Stil test",
            context={"body": "return  42"},
        )
        result = cg.generate(req)
        assert result.code.endswith("\n")


# === GenerateFromTemplate Testleri ===


class TestGenerateFromTemplate:
    """generate_from_template() testleri."""

    def test_function_template(self) -> None:
        cg = _make_generator()
        req = _make_request(
            context={"template": "function", "name": "add", "params": "a, b", "return_type": "int", "body": "return a + b"},
        )
        result = cg.generate_from_template(req)
        assert "def add" in result.code
        assert result.confidence > 0

    def test_class_template(self) -> None:
        cg = _make_generator()
        req = _make_request(
            context={"template": "class", "name": "Service", "docstring": "Servis sinifi"},
        )
        result = cg.generate_from_template(req)
        assert "class Service" in result.code

    def test_async_template(self) -> None:
        cg = _make_generator()
        req = _make_request(
            context={"template": "async_function", "name": "fetch", "body": "pass"},
        )
        result = cg.generate_from_template(req)
        assert "async def fetch" in result.code

    def test_pydantic_template(self) -> None:
        cg = _make_generator()
        req = _make_request(
            context={"template": "pydantic_model", "name": "UserModel"},
        )
        result = cg.generate_from_template(req)
        assert "BaseModel" in result.code

    def test_test_class_template(self) -> None:
        cg = _make_generator()
        req = _make_request(
            context={"template": "test_class", "name": "MyService"},
        )
        result = cg.generate_from_template(req)
        assert "TestMyService" in result.code

    def test_unknown_template_fallback(self) -> None:
        cg = _make_generator()
        req = _make_request(
            context={"template": "nonexistent"},
        )
        result = cg.generate_from_template(req)
        assert result.confidence == 0.5

    def test_dependencies_carried_as_imports(self) -> None:
        cg = _make_generator()
        req = _make_request(
            dependencies=["import os", "from typing import Any"],
        )
        result = cg.generate_from_template(req)
        assert len(result.imports) == 2


# === GenerateFunction Testleri ===


class TestGenerateFunction:
    """generate_function() testleri."""

    def test_simple_function(self) -> None:
        cg = _make_generator()
        code = cg.generate_function("greet", [], "str", 'return "hello"')
        assert "def greet" in code
        assert "str" in code

    def test_with_params(self) -> None:
        cg = _make_generator()
        params = [{"name": "name", "type": "str"}, {"name": "count", "type": "int"}]
        code = cg.generate_function("process", params, "None")
        assert "name: str" in code
        assert "count: int" in code

    def test_with_defaults(self) -> None:
        cg = _make_generator()
        params = [{"name": "limit", "type": "int", "default": "10"}]
        code = cg.generate_function("fetch", params)
        assert "limit: int = 10" in code

    def test_async_function(self) -> None:
        cg = _make_generator()
        code = cg.generate_function("fetch", [], is_async=True)
        assert "async def fetch" in code

    def test_docstring_included(self) -> None:
        cg = _make_generator()
        code = cg.generate_function("f", [], docstring="Ozel docstring")
        assert "Ozel docstring" in code

    def test_auto_docstring(self) -> None:
        cg = _make_generator()
        code = cg.generate_function("calc", [])
        assert '"""' in code


# === GenerateClass Testleri ===


class TestGenerateClass:
    """generate_class() testleri."""

    def test_simple_class(self) -> None:
        cg = _make_generator()
        code = cg.generate_class("MyClass")
        assert "class MyClass" in code
        assert "__init__" in code

    def test_with_bases(self) -> None:
        cg = _make_generator()
        code = cg.generate_class("Child", bases=["Parent"])
        assert "class Child(Parent)" in code

    def test_with_init_params(self) -> None:
        cg = _make_generator()
        params = [{"name": "name", "type": "str"}]
        code = cg.generate_class("User", init_params=params)
        assert "self.name = name" in code

    def test_with_methods(self) -> None:
        cg = _make_generator()
        methods = [{"name": "do_work", "body": "pass", "return_type": "None"}]
        code = cg.generate_class("Worker", methods=methods)
        assert "do_work" in code

    def test_async_method(self) -> None:
        cg = _make_generator()
        methods = [{"name": "fetch", "is_async": True, "body": "pass"}]
        code = cg.generate_class("Client", methods=methods)
        assert "async def fetch" in code

    def test_docstring(self) -> None:
        cg = _make_generator()
        code = cg.generate_class("Svc", docstring="Servis sinifi")
        assert "Servis sinifi" in code


# === GenerateModule Testleri ===


class TestGenerateModule:
    """generate_module() testleri."""

    def test_basic_module(self) -> None:
        cg = _make_generator()
        code = cg.generate_module("Test modulu")
        assert "Test modulu" in code
        assert "logger" in code

    def test_with_imports(self) -> None:
        cg = _make_generator()
        code = cg.generate_module("Mod", imports=["import os"])
        assert "import os" in code

    def test_with_classes(self) -> None:
        cg = _make_generator()
        cls = cg.generate_class("Foo")
        code = cg.generate_module("Mod", classes=[cls])
        assert "class Foo" in code

    def test_with_functions(self) -> None:
        cg = _make_generator()
        fn = cg.generate_function("bar", [])
        code = cg.generate_module("Mod", functions=[fn])
        assert "def bar" in code


# === AddDocstring Testleri ===


class TestAddDocstring:
    """add_docstring() testleri."""

    def test_basic_docstring(self) -> None:
        cg = _make_generator()
        code = "def f():\n    pass"
        result = cg.add_docstring(code, description="Basit fonksiyon")
        assert "Basit fonksiyon" in result

    def test_with_args(self) -> None:
        cg = _make_generator()
        code = "def f(x):\n    pass"
        result = cg.add_docstring(code, args={"x": "Girdi degeri"})
        assert "Args:" in result
        assert "x: Girdi degeri" in result

    def test_with_returns(self) -> None:
        cg = _make_generator()
        code = "def f():\n    return 1"
        result = cg.add_docstring(code, returns="Sonuc degeri")
        assert "Returns:" in result

    def test_with_raises(self) -> None:
        cg = _make_generator()
        code = "def f():\n    raise ValueError()"
        result = cg.add_docstring(code, raises={"ValueError": "Gecersiz deger"})
        assert "Raises:" in result


# === ManageImports Testleri ===


class TestManageImports:
    """manage_imports() testleri."""

    def test_empty_imports(self) -> None:
        cg = _make_generator()
        assert cg.manage_imports([]) == []

    def test_deduplication(self) -> None:
        cg = _make_generator()
        result = cg.manage_imports(["import os", "import os"])
        assert result.count("import os") == 1

    def test_sorting(self) -> None:
        cg = _make_generator()
        result = cg.manage_imports(["import sys", "import os"])
        assert result.index("import os") < result.index("import sys")

    def test_stdlib_first(self) -> None:
        cg = _make_generator()
        result = cg.manage_imports(["import requests", "import os"])
        assert result[0] == "import os"

    def test_local_last(self) -> None:
        cg = _make_generator()
        result = cg.manage_imports(["from app.core import x", "import os"])
        assert result[-1].startswith("from app")


# === EnforceStyle Testleri ===


class TestEnforceStyle:
    """enforce_style() testleri."""

    def test_trailing_whitespace_removed(self) -> None:
        cg = _make_generator()
        result = cg.enforce_style("x = 1   \n")
        assert "   \n" not in result

    def test_tabs_converted(self) -> None:
        cg = _make_generator()
        result = cg.enforce_style("\tx = 1")
        assert "\t" not in result

    def test_excessive_blank_lines(self) -> None:
        cg = _make_generator()
        result = cg.enforce_style("x = 1\n\n\n\n\ny = 2")
        # En fazla 2 bos satir olmali
        assert "\n\n\n\n" not in result

    def test_ends_with_newline(self) -> None:
        cg = _make_generator()
        result = cg.enforce_style("x = 1")
        assert result.endswith("\n")

    def test_empty_input(self) -> None:
        cg = _make_generator()
        result = cg.enforce_style("")
        assert result == "\n" or result == ""


# === GenerateTypeHints Testleri ===


class TestGenerateTypeHints:
    """_generate_type_hints() testleri."""

    def test_name_param(self) -> None:
        cg = _make_generator()
        assert cg._generate_type_hints("name") == "str"

    def test_count_param(self) -> None:
        cg = _make_generator()
        assert cg._generate_type_hints("count") == "int"

    def test_enabled_param(self) -> None:
        cg = _make_generator()
        assert cg._generate_type_hints("enabled") == "bool"

    def test_items_param(self) -> None:
        cg = _make_generator()
        assert cg._generate_type_hints("items") == "list"

    def test_config_param(self) -> None:
        cg = _make_generator()
        assert cg._generate_type_hints("config") == "dict"

    def test_prefix_match(self) -> None:
        cg = _make_generator()
        assert cg._generate_type_hints("is_active") == "bool"

    def test_unknown_param(self) -> None:
        cg = _make_generator()
        assert cg._generate_type_hints("foobar_xyz") == "Any"


# === Templates Testleri ===


class TestTemplates:
    """TEMPLATES sabitleri testleri."""

    def test_function_template_exists(self) -> None:
        assert "function" in TEMPLATES

    def test_class_template_exists(self) -> None:
        assert "class" in TEMPLATES

    def test_async_template_exists(self) -> None:
        assert "async_function" in TEMPLATES

    def test_pydantic_template_exists(self) -> None:
        assert "pydantic_model" in TEMPLATES

    def test_test_class_template_exists(self) -> None:
        assert "test_class" in TEMPLATES

    def test_fastapi_template_exists(self) -> None:
        assert "fastapi_endpoint" in TEMPLATES
