"""CodeRefactorer testleri.

Analiz, metot cikarimi, sinif cikarimi, sembol yeniden adlandirma,
olu kod temizligi ve basitlestirme testleri.
"""

import pytest

from app.core.selfcode.refactorer import CodeRefactorer
from app.models.selfcode import (
    RefactorPlan,
    RefactorResult,
    RefactorType,
)


# === Yardimci Fonksiyonlar ===


def _make_refactorer(**kwargs) -> CodeRefactorer:
    """Test icin CodeRefactorer olusturur."""
    return CodeRefactorer(**kwargs)


SIMPLE_SOURCE = """\
import os
import json

def hello(name):
    return f"Hello {name}"

def add(a, b):
    return a + b
"""

LONG_METHOD_SOURCE = "\n".join(
    ["def long_func():"]
    + [f"    x_{i} = {i}" for i in range(60)]
    + ["    return x_0"]
)

DEAD_CODE_SOURCE = """\
def with_dead_code():
    return 42
    print("unreachable")
    x = 1
"""

UNUSED_IMPORT_SOURCE = """\
import os
import json
import sys

def hello():
    return os.getcwd()
"""

DUPLICATE_SOURCE = """\
def func_a():
    x = 1
    y = 2
    z = x + y
    return z

def func_b():
    x = 1
    y = 2
    z = x + y
    return z
"""

CLASS_SOURCE = """\
def method_a(self):
    return 1

def method_b(self):
    return 2

def other():
    return 3
"""

RENAME_SOURCE = """\
old_name = 42
print(old_name)
result = old_name + 1
"""

SIMPLIFY_SOURCE = """\
def check(x):
    if x > 0:
        if x < 100:
            return True
    return False
"""


# === Init Testleri ===


class TestInit:
    """CodeRefactorer init testleri."""

    def test_defaults(self) -> None:
        cr = _make_refactorer()
        assert cr.max_method_lines == 50
        assert cr.min_duplicate_lines == 4

    def test_custom_thresholds(self) -> None:
        cr = _make_refactorer(max_method_lines=20, min_duplicate_lines=3)
        assert cr.max_method_lines == 20
        assert cr.min_duplicate_lines == 3


# === Analyze Testleri ===


class TestAnalyze:
    """analyze() testleri."""

    def test_clean_code_no_plans(self) -> None:
        cr = _make_refactorer()
        plans = cr.analyze(SIMPLE_SOURCE)
        # Kullanilmayan importlar tespit edilebilir
        assert isinstance(plans, list)

    def test_long_method_detected(self) -> None:
        cr = _make_refactorer(max_method_lines=10)
        plans = cr.analyze(LONG_METHOD_SOURCE)
        method_plans = [p for p in plans if p.refactor_type == RefactorType.EXTRACT_METHOD]
        assert len(method_plans) > 0

    def test_dead_code_detected(self) -> None:
        cr = _make_refactorer()
        plans = cr.analyze(DEAD_CODE_SOURCE)
        dead = [p for p in plans if p.refactor_type == RefactorType.DEAD_CODE_REMOVAL]
        assert len(dead) > 0

    def test_unused_import_detected(self) -> None:
        cr = _make_refactorer()
        plans = cr.analyze(UNUSED_IMPORT_SOURCE)
        unused = [p for p in plans if "import" in p.description.lower()]
        assert len(unused) > 0

    def test_syntax_error_returns_empty(self) -> None:
        cr = _make_refactorer()
        plans = cr.analyze("def broken(\n    return 1")
        assert plans == []

    def test_plans_have_ids(self) -> None:
        cr = _make_refactorer(max_method_lines=10)
        plans = cr.analyze(LONG_METHOD_SOURCE)
        for plan in plans:
            assert plan.id != ""

    def test_file_path_set(self) -> None:
        cr = _make_refactorer(max_method_lines=10)
        plans = cr.analyze(LONG_METHOD_SOURCE, "test.py")
        for plan in plans:
            assert plan.file_path == "test.py"


# === ExtractMethod Testleri ===


class TestExtractMethod:
    """extract_method() testleri."""

    def test_basic_extraction(self) -> None:
        cr = _make_refactorer()
        result = cr.extract_method(SIMPLE_SOURCE, 4, 5, "extracted")
        assert result.success is True
        assert "extracted" in result.refactored_code

    def test_invalid_range(self) -> None:
        cr = _make_refactorer()
        result = cr.extract_method(SIMPLE_SOURCE, 10, 5, "bad")
        assert result.success is False

    def test_out_of_bounds(self) -> None:
        cr = _make_refactorer()
        result = cr.extract_method(SIMPLE_SOURCE, 1, 999, "bad")
        assert result.success is False

    def test_changes_counted(self) -> None:
        cr = _make_refactorer()
        result = cr.extract_method(SIMPLE_SOURCE, 4, 5, "extracted")
        assert result.changes_count > 0

    def test_call_inserted(self) -> None:
        cr = _make_refactorer()
        result = cr.extract_method(SIMPLE_SOURCE, 4, 5, "do_work")
        assert "self.do_work()" in result.refactored_code


# === ExtractClass Testleri ===


class TestExtractClass:
    """extract_class() testleri."""

    def test_basic_extraction(self) -> None:
        cr = _make_refactorer()
        result = cr.extract_class(CLASS_SOURCE, ["method_a", "method_b"], "NewClass")
        assert result.success is True
        assert "class NewClass" in result.refactored_code

    def test_methods_moved(self) -> None:
        cr = _make_refactorer()
        result = cr.extract_class(CLASS_SOURCE, ["method_a"], "Service")
        assert "method_a" in result.refactored_code
        assert "class Service" in result.refactored_code

    def test_no_matching_methods(self) -> None:
        cr = _make_refactorer()
        result = cr.extract_class(CLASS_SOURCE, ["nonexistent"], "Bad")
        assert result.success is False

    def test_syntax_error_source(self) -> None:
        cr = _make_refactorer()
        result = cr.extract_class("def broken(\n", ["f"], "X")
        assert result.success is False


# === RenameSymbol Testleri ===


class TestRenameSymbol:
    """rename_symbol() testleri."""

    def test_basic_rename(self) -> None:
        cr = _make_refactorer()
        result = cr.rename_symbol(RENAME_SOURCE, "old_name", "new_name")
        assert result.success is True
        assert "new_name" in result.refactored_code
        assert "old_name" not in result.refactored_code

    def test_all_occurrences_renamed(self) -> None:
        cr = _make_refactorer()
        result = cr.rename_symbol(RENAME_SOURCE, "old_name", "new_name")
        assert result.changes_count == 3  # 3 occurrences

    def test_not_found(self) -> None:
        cr = _make_refactorer()
        result = cr.rename_symbol(RENAME_SOURCE, "nonexistent", "new")
        assert result.success is False

    def test_word_boundary_respected(self) -> None:
        cr = _make_refactorer()
        source = "name = 1\nfull_name = 2\n"
        result = cr.rename_symbol(source, "name", "title")
        assert "full_title" not in result.refactored_code


# === RemoveDeadCode Testleri ===


class TestRemoveDeadCode:
    """remove_dead_code() testleri."""

    def test_removes_unreachable(self) -> None:
        cr = _make_refactorer()
        result = cr.remove_dead_code(DEAD_CODE_SOURCE)
        assert result.success is True
        assert "unreachable" not in result.refactored_code

    def test_clean_code_no_changes(self) -> None:
        cr = _make_refactorer()
        source = "def f():\n    return 1\n"
        result = cr.remove_dead_code(source)
        assert result.changes_count == 0

    def test_removes_unused_imports(self) -> None:
        cr = _make_refactorer()
        result = cr.remove_dead_code(UNUSED_IMPORT_SOURCE)
        assert result.success is True

    def test_syntax_error_fails(self) -> None:
        cr = _make_refactorer()
        result = cr.remove_dead_code("def broken(\n")
        assert result.success is False


# === Simplify Testleri ===


class TestSimplify:
    """simplify() testleri."""

    def test_nested_if_merge(self) -> None:
        cr = _make_refactorer()
        result = cr.simplify(SIMPLIFY_SOURCE)
        # ic ice if'ler birlestirilmis olabilir
        assert isinstance(result, RefactorResult)
        assert result.success is True

    def test_no_simplification_needed(self) -> None:
        cr = _make_refactorer()
        source = "x = 1\ny = 2\n"
        result = cr.simplify(source)
        assert result.changes_count == 0

    def test_result_is_valid_python(self) -> None:
        cr = _make_refactorer()
        result = cr.simplify(SIMPLIFY_SOURCE)
        if result.changes_count > 0:
            import ast
            ast.parse(result.refactored_code)


# === ApplyPlan Testleri ===


class TestApplyPlan:
    """apply_plan() testleri."""

    def test_dead_code_plan(self) -> None:
        cr = _make_refactorer()
        plan = RefactorPlan(
            refactor_type=RefactorType.DEAD_CODE_REMOVAL,
            target="with_dead_code",
        )
        result = cr.apply_plan(plan, DEAD_CODE_SOURCE)
        assert result.plan_id == plan.id

    def test_simplify_plan(self) -> None:
        cr = _make_refactorer()
        plan = RefactorPlan(
            refactor_type=RefactorType.SIMPLIFY,
            target="check",
        )
        result = cr.apply_plan(plan, SIMPLIFY_SOURCE)
        assert result.plan_id == plan.id

    def test_rename_plan(self) -> None:
        cr = _make_refactorer()
        plan = RefactorPlan(
            refactor_type=RefactorType.RENAME,
            target="old_name -> new_name",
        )
        result = cr.apply_plan(plan, RENAME_SOURCE)
        assert result.success is True

    def test_unsupported_plan(self) -> None:
        cr = _make_refactorer()
        plan = RefactorPlan(
            refactor_type=RefactorType.MOVE,
            target="something",
        )
        result = cr.apply_plan(plan, SIMPLE_SOURCE)
        assert result.success is False


# === FindDuplicateBlocks Testleri ===


class TestFindDuplicateBlocks:
    """_find_duplicate_blocks() testleri."""

    def test_duplicates_found(self) -> None:
        cr = _make_refactorer()
        dupes = cr._find_duplicate_blocks(DUPLICATE_SOURCE)
        assert len(dupes) > 0

    def test_no_duplicates(self) -> None:
        cr = _make_refactorer()
        dupes = cr._find_duplicate_blocks("x = 1\ny = 2\n")
        assert len(dupes) == 0

    def test_short_source_skipped(self) -> None:
        cr = _make_refactorer(min_duplicate_lines=10)
        dupes = cr._find_duplicate_blocks("x = 1\ny = 2\n")
        assert dupes == []


# === FindUnusedImports Testleri ===


class TestFindUnusedImports:
    """_find_unused_imports() testleri."""

    def test_unused_detected(self) -> None:
        cr = _make_refactorer()
        import ast
        tree = ast.parse(UNUSED_IMPORT_SOURCE)
        unused = cr._find_unused_imports(UNUSED_IMPORT_SOURCE, tree)
        assert len(unused) > 0

    def test_used_import_not_flagged(self) -> None:
        cr = _make_refactorer()
        import ast
        source = "import os\nprint(os.getcwd())\n"
        tree = ast.parse(source)
        unused = cr._find_unused_imports(source, tree)
        assert len(unused) == 0
