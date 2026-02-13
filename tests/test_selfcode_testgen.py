"""TestGenerator testleri.

Birim test uretimi, kenar durum tespiti, mock uretimi,
fixture olusturma ve assertion onerisi testleri.
"""

import pytest

from app.core.selfcode.test_generator import (
    DEFAULT_TEST_VALUES,
    TestGenerator,
)
from app.models.selfcode import TestCase, TestSuite, TestType


# === Yardimci Fonksiyonlar ===


def _make_testgen(**kwargs) -> TestGenerator:
    """Test icin TestGenerator olusturur."""
    return TestGenerator(**kwargs)


SIMPLE_FUNC_SOURCE = """\
def add(a: int, b: int) -> int:
    return a + b
"""

ASYNC_FUNC_SOURCE = """\
async def fetch_data(url: str) -> dict:
    return {"url": url}
"""

CLASS_SOURCE = """\
class Calculator:
    def __init__(self, precision: int = 2) -> None:
        self.precision = precision

    def add(self, a: float, b: float) -> float:
        return round(a + b, self.precision)

    def subtract(self, a: float, b: float) -> float:
        return round(a - b, self.precision)
"""

OPTIONAL_PARAM_SOURCE = """\
from typing import Optional

def process(name: str, data: Optional[dict] = None) -> str:
    return name
"""

MULTI_TYPE_SOURCE = """\
def transform(text: str, count: int, items: list, config: dict) -> dict:
    return {}
"""

PRIVATE_FUNC_SOURCE = """\
def _internal_helper(x: int) -> int:
    return x * 2

def public_func(x: int) -> int:
    return _internal_helper(x)
"""

EXTERNAL_DEP_SOURCE = """\
import requests
import redis

def fetch(url: str) -> str:
    resp = requests.get(url)
    return resp.text
"""

SYNTAX_ERROR_SOURCE = """\
def broken(
    return 1
"""


# === Init Testleri ===


class TestInit:
    """TestGenerator init testleri."""

    def test_defaults(self) -> None:
        tg = _make_testgen()
        assert tg.coverage_target == 80.0
        assert tg.include_edge_cases is True
        assert tg.max_tests_per_function == 5

    def test_custom_coverage(self) -> None:
        tg = _make_testgen(coverage_target=95.0)
        assert tg.coverage_target == 95.0

    def test_custom_edge_cases(self) -> None:
        tg = _make_testgen(include_edge_cases=False)
        assert tg.include_edge_cases is False

    def test_custom_max_tests(self) -> None:
        tg = _make_testgen(max_tests_per_function=10)
        assert tg.max_tests_per_function == 10


# === GenerateTests Testleri ===


class TestGenerateTests:
    """generate_tests() testleri."""

    def test_simple_function(self) -> None:
        tg = _make_testgen()
        suite = tg.generate_tests(SIMPLE_FUNC_SOURCE, "math_utils")
        assert isinstance(suite, TestSuite)
        assert len(suite.tests) > 0

    def test_suite_name(self) -> None:
        tg = _make_testgen()
        suite = tg.generate_tests(SIMPLE_FUNC_SOURCE, "my_module")
        assert "My" in suite.name or "my" in suite.name.lower()

    def test_imports_include_pytest(self) -> None:
        tg = _make_testgen()
        suite = tg.generate_tests(SIMPLE_FUNC_SOURCE, "mod")
        assert any("pytest" in imp for imp in suite.imports)

    def test_class_methods_tested(self) -> None:
        tg = _make_testgen()
        suite = tg.generate_tests(CLASS_SOURCE, "calc")
        # add ve subtract icin en az 2 test
        assert len(suite.tests) >= 2

    def test_edge_cases_included(self) -> None:
        tg = _make_testgen(include_edge_cases=True)
        suite = tg.generate_tests(MULTI_TYPE_SOURCE, "mod")
        edge = [t for t in suite.tests if t.test_type == TestType.EDGE_CASE]
        assert len(edge) > 0

    def test_no_edge_cases(self) -> None:
        tg = _make_testgen(include_edge_cases=False)
        suite = tg.generate_tests(SIMPLE_FUNC_SOURCE, "mod")
        edge = [t for t in suite.tests if t.test_type == TestType.EDGE_CASE]
        assert len(edge) == 0

    def test_syntax_error_returns_empty_suite(self) -> None:
        tg = _make_testgen()
        suite = tg.generate_tests(SYNTAX_ERROR_SOURCE, "bad")
        assert len(suite.tests) == 0

    def test_coverage_target_set(self) -> None:
        tg = _make_testgen(coverage_target=90.0)
        suite = tg.generate_tests(SIMPLE_FUNC_SOURCE, "mod")
        assert suite.coverage_target == 90.0

    def test_private_functions_skipped(self) -> None:
        tg = _make_testgen()
        suite = tg.generate_tests(PRIVATE_FUNC_SOURCE, "mod")
        private_tests = [t for t in suite.tests if "_internal" in t.target_function]
        assert len(private_tests) == 0

    def test_mock_imports_added(self) -> None:
        tg = _make_testgen()
        suite = tg.generate_tests(EXTERNAL_DEP_SOURCE, "mod")
        assert any("mock" in imp.lower() or "Mock" in imp for imp in suite.imports)


# === GenerateUnitTest Testleri ===


class TestGenerateUnitTest:
    """generate_unit_test() testleri."""

    def test_basic_test(self) -> None:
        tg = _make_testgen()
        func_info = {
            "name": "add",
            "params": [("a", "int"), ("b", "int")],
            "return_type": "int",
            "is_async": False,
            "class_name": "",
            "decorators": [],
        }
        tc = tg.generate_unit_test(func_info, "math_utils")
        assert tc is not None
        assert "test_add" in tc.name
        assert tc.test_type == TestType.UNIT

    def test_async_test(self) -> None:
        tg = _make_testgen()
        func_info = {
            "name": "fetch",
            "params": [("url", "str")],
            "return_type": "dict",
            "is_async": True,
            "class_name": "",
            "decorators": [],
        }
        tc = tg.generate_unit_test(func_info)
        assert tc is not None
        assert "async" in tc.code

    def test_class_method_test(self) -> None:
        tg = _make_testgen()
        func_info = {
            "name": "process",
            "params": [("data", "dict")],
            "return_type": "dict",
            "is_async": False,
            "class_name": "MyService",
            "decorators": [],
        }
        tc = tg.generate_unit_test(func_info)
        assert tc is not None
        assert "MyService" in tc.code

    def test_private_func_skipped(self) -> None:
        tg = _make_testgen()
        func_info = {
            "name": "_helper",
            "params": [],
            "return_type": "None",
            "is_async": False,
            "class_name": "",
            "decorators": [],
        }
        tc = tg.generate_unit_test(func_info)
        assert tc is None

    def test_test_has_assertion(self) -> None:
        tg = _make_testgen()
        func_info = {
            "name": "compute",
            "params": [("x", "int")],
            "return_type": "int",
            "is_async": False,
            "class_name": "",
            "decorators": [],
        }
        tc = tg.generate_unit_test(func_info)
        assert "assert" in tc.code


# === GenerateEdgeCases Testleri ===


class TestGenerateEdgeCases:
    """generate_edge_cases() testleri."""

    def test_optional_param_none_test(self) -> None:
        tg = _make_testgen()
        func_info = {
            "name": "process",
            "params": [("name", "str"), ("data", "Optional[dict]")],
            "return_type": "str",
            "is_async": False,
            "class_name": "",
            "decorators": [],
        }
        cases = tg.generate_edge_cases(func_info)
        none_cases = [c for c in cases if "none" in c.name.lower()]
        assert len(none_cases) > 0

    def test_empty_string_test(self) -> None:
        tg = _make_testgen()
        func_info = {
            "name": "greet",
            "params": [("name", "str")],
            "return_type": "str",
            "is_async": False,
            "class_name": "",
            "decorators": [],
        }
        cases = tg.generate_edge_cases(func_info)
        empty_cases = [c for c in cases if "empty" in c.name.lower()]
        assert len(empty_cases) > 0

    def test_boundary_int_test(self) -> None:
        tg = _make_testgen()
        func_info = {
            "name": "calc",
            "params": [("count", "int")],
            "return_type": "int",
            "is_async": False,
            "class_name": "",
            "decorators": [],
        }
        cases = tg.generate_edge_cases(func_info)
        boundary = [c for c in cases if "boundary" in c.name.lower()]
        assert len(boundary) > 0

    def test_type_error_test(self) -> None:
        tg = _make_testgen()
        func_info = {
            "name": "process",
            "params": [("x", "int")],
            "return_type": "int",
            "is_async": False,
            "class_name": "",
            "decorators": [],
        }
        cases = tg.generate_edge_cases(func_info)
        type_cases = [c for c in cases if "type_error" in c.name]
        assert len(type_cases) > 0
        assert "pytest.raises" in type_cases[0].code

    def test_private_func_no_edge_cases(self) -> None:
        tg = _make_testgen()
        func_info = {
            "name": "_internal",
            "params": [("x", "int")],
            "return_type": "int",
            "is_async": False,
            "class_name": "",
            "decorators": [],
        }
        cases = tg.generate_edge_cases(func_info)
        assert len(cases) == 0

    def test_all_edge_case_type(self) -> None:
        tg = _make_testgen()
        func_info = {
            "name": "f",
            "params": [("x", "int")],
            "return_type": "int",
            "is_async": False,
            "class_name": "",
            "decorators": [],
        }
        cases = tg.generate_edge_cases(func_info)
        assert all(c.test_type == TestType.EDGE_CASE for c in cases)


# === GenerateMockCode Testleri ===


class TestGenerateMockCode:
    """generate_mock_code() testleri."""

    def test_external_dependency_detected(self) -> None:
        tg = _make_testgen()
        func_info = {"name": "fetch", "decorators": []}
        mocks = tg.generate_mock_code(func_info, EXTERNAL_DEP_SOURCE)
        assert len(mocks) > 0

    def test_no_external_deps(self) -> None:
        tg = _make_testgen()
        func_info = {"name": "add", "decorators": []}
        mocks = tg.generate_mock_code(func_info, SIMPLE_FUNC_SOURCE)
        assert len(mocks) == 0

    def test_celery_task_detected(self) -> None:
        tg = _make_testgen()
        func_info = {"name": "my_task", "decorators": ["celery.task"]}
        mocks = tg.generate_mock_code(func_info, "")
        assert len(mocks) > 0


# === GenerateFixtures Testleri ===


class TestGenerateFixtures:
    """generate_fixtures() testleri."""

    def test_class_fixture(self) -> None:
        tg = _make_testgen()
        classes = [{"name": "MyService"}]
        code = tg.generate_fixtures([], classes)
        assert "fixture" in code
        assert "MyService" in code

    def test_str_param_fixture(self) -> None:
        tg = _make_testgen()
        funcs = [{"params": [("name", "str")]}]
        code = tg.generate_fixtures(funcs, [])
        assert "sample_text" in code

    def test_dict_param_fixture(self) -> None:
        tg = _make_testgen()
        funcs = [{"params": [("config", "dict")]}]
        code = tg.generate_fixtures(funcs, [])
        assert "sample_dict" in code

    def test_list_param_fixture(self) -> None:
        tg = _make_testgen()
        funcs = [{"params": [("items", "list")]}]
        code = tg.generate_fixtures(funcs, [])
        assert "sample_list" in code

    def test_no_fixtures_needed(self) -> None:
        tg = _make_testgen()
        code = tg.generate_fixtures([], [])
        assert code == ""


# === SuggestAssertions Testleri ===


class TestSuggestAssertions:
    """suggest_assertions() testleri."""

    def test_str_return(self) -> None:
        tg = _make_testgen()
        asserts = tg.suggest_assertions("str")
        assert any("isinstance" in a for a in asserts)

    def test_int_return(self) -> None:
        tg = _make_testgen()
        asserts = tg.suggest_assertions("int")
        assert any("int" in a for a in asserts)

    def test_bool_return(self) -> None:
        tg = _make_testgen()
        asserts = tg.suggest_assertions("bool")
        assert any("bool" in a for a in asserts)

    def test_none_return(self) -> None:
        tg = _make_testgen()
        asserts = tg.suggest_assertions("None")
        assert any("None" in a for a in asserts)

    def test_optional_return(self) -> None:
        tg = _make_testgen()
        asserts = tg.suggest_assertions("Optional[str]")
        assert len(asserts) > 0

    def test_unknown_return(self) -> None:
        tg = _make_testgen()
        asserts = tg.suggest_assertions("CustomType")
        assert any("not None" in a for a in asserts)


# === DefaultTestValues Testleri ===


class TestDefaultValues:
    """DEFAULT_TEST_VALUES sabitleri testleri."""

    def test_str_values(self) -> None:
        assert "str" in DEFAULT_TEST_VALUES
        assert "" in DEFAULT_TEST_VALUES["str"]

    def test_int_values(self) -> None:
        assert "int" in DEFAULT_TEST_VALUES
        assert 0 in DEFAULT_TEST_VALUES["int"]

    def test_bool_values(self) -> None:
        assert "bool" in DEFAULT_TEST_VALUES
        assert True in DEFAULT_TEST_VALUES["bool"]
        assert False in DEFAULT_TEST_VALUES["bool"]

    def test_none_values(self) -> None:
        assert "None" in DEFAULT_TEST_VALUES
        assert None in DEFAULT_TEST_VALUES["None"]


# === BaseType Yardimci Testleri ===


class TestBaseType:
    """_base_type() testleri."""

    def test_simple_type(self) -> None:
        tg = _make_testgen()
        assert tg._base_type("str") == "str"

    def test_optional(self) -> None:
        tg = _make_testgen()
        assert tg._base_type("Optional[str]") == "str"

    def test_generic(self) -> None:
        tg = _make_testgen()
        assert tg._base_type("list[int]") == "list"

    def test_union_none(self) -> None:
        tg = _make_testgen()
        assert tg._base_type("str | None") == "str"

    def test_empty(self) -> None:
        tg = _make_testgen()
        assert tg._base_type("") == ""
