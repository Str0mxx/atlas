"""CodeAnalyzer testleri.

AST ayristirma, bagimlilik cikarimi, karmasiklik hesaplama,
kod kokusu tespiti ve guvenlik acigi taramasi testleri.
"""

import pytest

from app.core.selfcode.code_analyzer import CodeAnalyzer
from app.models.selfcode import (
    AnalysisIssue,
    AnalysisSeverity,
    CodeAnalysisReport,
    CodeSmellType,
    ComplexityMetrics,
    DependencyInfo,
)


# === Yardimci Fonksiyonlar ===


def _make_analyzer(**kwargs) -> CodeAnalyzer:
    """Test icin CodeAnalyzer olusturur."""
    return CodeAnalyzer(**kwargs)


SIMPLE_SOURCE = """\
import os
import json
from pathlib import Path

def hello(name: str) -> str:
    return f"Hello {name}"
"""

CLASS_SOURCE = """\
import logging

class MyService:
    def __init__(self, name: str) -> None:
        self.name = name

    def greet(self) -> str:
        return f"Hello {self.name}"

    def process(self, data: dict) -> dict:
        result = {}
        for key, value in data.items():
            result[key] = str(value)
        return result
"""

SECURITY_SOURCE = """\
import os
import pickle

def dangerous():
    eval("1+1")
    exec("print('hi')")
    os.system("ls")
    pickle.loads(b"data")
"""

COMPLEX_SOURCE = """\
def complex_func(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            else:
                return x + y
        elif y < 0:
            for i in range(x):
                if i % 2 == 0:
                    return i
        else:
            return x
    elif x < 0:
        while y > 0:
            y -= 1
            if y == 5:
                break
    else:
        try:
            return x / y
        except ZeroDivisionError:
            return 0
    return None
"""

DEAD_CODE_SOURCE = """\
def with_dead_code():
    return 42
    print("unreachable")
"""

LONG_METHOD_SOURCE = "\n".join(
    ["def long_func():"]
    + [f"    x_{i} = {i}" for i in range(60)]
    + ["    return x_0"]
)

SYNTAX_ERROR_SOURCE = """\
def broken(
    return None
"""

LOCAL_IMPORT_SOURCE = """\
from app.models.selfcode import CodeAnalysisReport
from app.core.selfcode.code_analyzer import CodeAnalyzer
import requests
"""


# === Parse Testleri ===


class TestParse:
    """parse() testleri."""

    def test_valid_source(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse(SIMPLE_SOURCE)
        assert tree is not None

    def test_syntax_error(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse(SYNTAX_ERROR_SOURCE)
        assert tree is None

    def test_empty_source(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("")
        assert tree is not None

    def test_single_expression(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("x = 1")
        assert tree is not None


# === Analyze Testleri ===


class TestAnalyze:
    """analyze() testleri."""

    def test_simple_analysis(self) -> None:
        ca = _make_analyzer()
        report = ca.analyze(SIMPLE_SOURCE, "test.py")
        assert isinstance(report, CodeAnalysisReport)
        assert report.file_path == "test.py"
        assert report.score > 0

    def test_syntax_error_score_zero(self) -> None:
        ca = _make_analyzer()
        report = ca.analyze(SYNTAX_ERROR_SOURCE, "bad.py")
        assert report.score == 0.0
        assert len(report.issues) > 0

    def test_security_lowers_score(self) -> None:
        ca = _make_analyzer()
        report = ca.analyze(SECURITY_SOURCE, "danger.py")
        assert report.score < 100.0
        assert len(report.security_issues) > 0

    def test_clean_code_high_score(self) -> None:
        ca = _make_analyzer()
        report = ca.analyze("def add(a, b):\n    return a + b\n")
        assert report.score >= 90.0

    def test_report_has_dependencies(self) -> None:
        ca = _make_analyzer()
        report = ca.analyze(SIMPLE_SOURCE)
        assert len(report.dependencies) > 0

    def test_report_has_complexity(self) -> None:
        ca = _make_analyzer()
        report = ca.analyze(SIMPLE_SOURCE)
        assert report.complexity.lines_of_code > 0


# === ExtractDependencies Testleri ===


class TestExtractDependencies:
    """extract_dependencies() testleri."""

    def test_import_statement(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("import os")
        deps = ca.extract_dependencies(tree)
        assert len(deps) == 1
        assert deps[0].module == "os"
        assert deps[0].is_stdlib is True

    def test_from_import(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("from pathlib import Path")
        deps = ca.extract_dependencies(tree)
        assert len(deps) == 1
        assert deps[0].module == "pathlib"
        assert "Path" in deps[0].names

    def test_local_import(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("from app.models import Task")
        deps = ca.extract_dependencies(tree)
        assert len(deps) == 1
        assert deps[0].is_local is True

    def test_third_party_import(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("import requests")
        deps = ca.extract_dependencies(tree)
        assert len(deps) == 1
        assert deps[0].is_stdlib is False
        assert deps[0].is_local is False

    def test_multiple_imports(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse(SIMPLE_SOURCE)
        deps = ca.extract_dependencies(tree)
        assert len(deps) == 3

    def test_aliased_import(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("import numpy as np")
        deps = ca.extract_dependencies(tree)
        assert len(deps) == 1
        assert "np" in deps[0].names

    def test_mixed_imports(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse(LOCAL_IMPORT_SOURCE)
        deps = ca.extract_dependencies(tree)
        local = [d for d in deps if d.is_local]
        assert len(local) == 2


# === CalculateComplexity Testleri ===


class TestCalculateComplexity:
    """calculate_complexity() testleri."""

    def test_simple_function(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("def f():\n    return 1\n")
        cx = ca.calculate_complexity(tree, "def f():\n    return 1\n")
        assert cx.cyclomatic >= 1

    def test_complex_function(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse(COMPLEX_SOURCE)
        cx = ca.calculate_complexity(tree, COMPLEX_SOURCE)
        assert cx.cyclomatic > 5

    def test_lines_of_code(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse(SIMPLE_SOURCE)
        cx = ca.calculate_complexity(tree, SIMPLE_SOURCE)
        assert cx.lines_of_code > 0

    def test_maintainability_index(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("x = 1\n")
        cx = ca.calculate_complexity(tree, "x = 1\n")
        assert 0.0 <= cx.maintainability_index <= 100.0

    def test_halstead_volume(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("x = 1 + 2\n")
        cx = ca.calculate_complexity(tree, "x = 1 + 2\n")
        assert cx.halstead_volume > 0

    def test_cognitive_complexity(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse(COMPLEX_SOURCE)
        cx = ca.calculate_complexity(tree, COMPLEX_SOURCE)
        assert cx.cognitive > 0


# === DetectCodeSmells Testleri ===


class TestDetectCodeSmells:
    """detect_code_smells() testleri."""

    def test_no_smells(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("def f():\n    return 1\n")
        smells, issues = ca.detect_code_smells(tree, "def f():\n    return 1\n")
        assert len(smells) == 0

    def test_long_method(self) -> None:
        ca = _make_analyzer(max_method_lines=10)
        tree = ca.parse(LONG_METHOD_SOURCE)
        smells, issues = ca.detect_code_smells(tree, LONG_METHOD_SOURCE)
        assert CodeSmellType.LONG_METHOD in smells

    def test_dead_code(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse(DEAD_CODE_SOURCE)
        smells, issues = ca.detect_code_smells(tree, DEAD_CODE_SOURCE)
        assert CodeSmellType.DEAD_CODE in smells

    def test_god_class(self) -> None:
        methods = "\n".join(
            [f"    def method_{i}(self):\n        pass" for i in range(25)]
        )
        source = f"class Huge:\n{methods}\n"
        ca = _make_analyzer()
        tree = ca.parse(source)
        smells, issues = ca.detect_code_smells(tree, source)
        assert CodeSmellType.GOD_CLASS in smells

    def test_smell_issues_have_details(self) -> None:
        ca = _make_analyzer(max_method_lines=10)
        tree = ca.parse(LONG_METHOD_SOURCE)
        _, issues = ca.detect_code_smells(tree, LONG_METHOD_SOURCE)
        assert len(issues) > 0
        assert issues[0].rule == "long_method"
        assert issues[0].suggestion != ""


# === DetectSecurityIssues Testleri ===


class TestDetectSecurityIssues:
    """detect_security_issues() testleri."""

    def test_eval_detected(self) -> None:
        ca = _make_analyzer()
        issues = ca.detect_security_issues('eval("1+1")')
        assert len(issues) > 0
        assert any("eval" in i.message for i in issues)

    def test_exec_detected(self) -> None:
        ca = _make_analyzer()
        issues = ca.detect_security_issues('exec("code")')
        assert len(issues) > 0

    def test_os_system_detected(self) -> None:
        ca = _make_analyzer()
        issues = ca.detect_security_issues('os.system("ls")')
        assert len(issues) > 0

    def test_pickle_loads_detected(self) -> None:
        ca = _make_analyzer()
        issues = ca.detect_security_issues('pickle.loads(data)')
        assert len(issues) > 0

    def test_clean_code_no_issues(self) -> None:
        ca = _make_analyzer()
        issues = ca.detect_security_issues("x = 1 + 2")
        assert len(issues) == 0

    def test_multiple_issues(self) -> None:
        ca = _make_analyzer()
        issues = ca.detect_security_issues(SECURITY_SOURCE)
        assert len(issues) >= 3

    def test_severity_is_critical(self) -> None:
        ca = _make_analyzer()
        issues = ca.detect_security_issues('eval("x")')
        assert all(i.severity == AnalysisSeverity.CRITICAL for i in issues)


# === GetFunctions / GetClasses Testleri ===


class TestGetFunctionsClasses:
    """get_functions() ve get_classes() testleri."""

    def test_get_functions(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse(SIMPLE_SOURCE)
        funcs = ca.get_functions(tree)
        assert len(funcs) == 1
        assert funcs[0]["name"] == "hello"

    def test_async_function(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("async def afunc():\n    pass\n")
        funcs = ca.get_functions(tree)
        assert funcs[0]["is_async"] is True

    def test_get_classes(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse(CLASS_SOURCE)
        classes = ca.get_classes(tree)
        assert len(classes) == 1
        assert classes[0]["name"] == "MyService"

    def test_class_methods(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse(CLASS_SOURCE)
        classes = ca.get_classes(tree)
        assert classes[0]["method_count"] >= 2

    def test_class_bases(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("class Child(Parent):\n    pass\n")
        classes = ca.get_classes(tree)
        assert "Parent" in classes[0]["bases"]

    def test_decorated_function(self) -> None:
        ca = _make_analyzer()
        tree = ca.parse("@staticmethod\ndef f():\n    pass\n")
        funcs = ca.get_functions(tree)
        assert len(funcs[0]["decorators"]) > 0


# === Init Testleri ===


class TestInit:
    """CodeAnalyzer init testleri."""

    def test_defaults(self) -> None:
        ca = _make_analyzer()
        assert ca.max_method_lines == 50
        assert ca.max_class_lines == 300
        assert ca.max_complexity == 10

    def test_custom_thresholds(self) -> None:
        ca = _make_analyzer(max_method_lines=20, max_class_lines=100, max_complexity=5)
        assert ca.max_method_lines == 20
        assert ca.max_class_lines == 100
        assert ca.max_complexity == 5
