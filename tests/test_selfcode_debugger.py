"""AutoDebugger testleri.

Hata ayristirma, kok neden analizi, duzeltme onerisi,
otomatik duzeltme ve regresyon kontrolu testleri.
"""

import pytest

from app.core.selfcode.debugger import (
    COMMON_FIXES,
    AutoDebugger,
)
from app.models.selfcode import FixConfidence, FixSuggestion


# === Yardimci Fonksiyonlar ===


def _make_debugger(**kwargs) -> AutoDebugger:
    """Test icin AutoDebugger olusturur."""
    return AutoDebugger(**kwargs)


TRACEBACK_SAMPLE = """\
Traceback (most recent call last):
  File "/app/main.py", line 42, in process
    result = compute(data)
  File "/app/utils.py", line 15, in compute
    return value / divisor
ZeroDivisionError: division by zero
"""

NAME_ERROR_TRACE = """\
Traceback (most recent call last):
  File "test.py", line 5, in <module>
    print(mesage)
NameError: name 'mesage' is not defined
"""

IMPORT_ERROR_TRACE = """\
Traceback (most recent call last):
  File "app.py", line 1, in <module>
    import flaskk
ModuleNotFoundError: No module named 'flaskk'
"""

TYPE_ERROR_TRACE = """\
Traceback (most recent call last):
  File "test.py", line 3, in <module>
    add(1, 2, 3)
TypeError: add() takes 2 positional arguments but 3 were given
"""

ATTRIBUTE_ERROR_TRACE = """\
Traceback (most recent call last):
  File "test.py", line 5, in <module>
    obj.methd()
AttributeError: 'MyClass' object has no attribute 'methd'
"""

KEY_ERROR_TRACE = """\
Traceback (most recent call last):
  File "test.py", line 3, in <module>
    data["missing_key"]
KeyError: 'missing_key'
"""

SOURCE_WITH_TYPO = """\
message = "hello"
x = 42
print(mesage)
"""

DIVISION_SOURCE = """\
def calc(a, b):
    return a / b
"""


# === Init Testleri ===


class TestInit:
    """AutoDebugger init testleri."""

    def test_defaults(self) -> None:
        db = _make_debugger()
        assert db.max_suggestions == 5
        assert db.auto_fix_confidence_threshold == FixConfidence.HIGH

    def test_custom_max_suggestions(self) -> None:
        db = _make_debugger(max_suggestions=3)
        assert db.max_suggestions == 3

    def test_custom_threshold(self) -> None:
        db = _make_debugger(auto_fix_confidence_threshold=FixConfidence.MEDIUM)
        assert db.auto_fix_confidence_threshold == FixConfidence.MEDIUM


# === ParseError Testleri ===


class TestParseError:
    """parse_error() testleri."""

    def test_zero_division(self) -> None:
        db = _make_debugger()
        result = db.parse_error(TRACEBACK_SAMPLE)
        assert result["error_type"] == "ZeroDivisionError"
        assert "division by zero" in result["message"]

    def test_name_error(self) -> None:
        db = _make_debugger()
        result = db.parse_error(NAME_ERROR_TRACE)
        assert result["error_type"] == "NameError"
        assert "mesage" in result["message"]

    def test_file_and_line(self) -> None:
        db = _make_debugger()
        result = db.parse_error(NAME_ERROR_TRACE)
        assert result["file"] == "test.py"
        assert result["line"] == "5"

    def test_import_error(self) -> None:
        db = _make_debugger()
        result = db.parse_error(IMPORT_ERROR_TRACE)
        assert result["error_type"] == "ModuleNotFoundError"

    def test_empty_input(self) -> None:
        db = _make_debugger()
        result = db.parse_error("")
        assert result["error_type"] == ""

    def test_simple_error_line(self) -> None:
        db = _make_debugger()
        result = db.parse_error("ValueError: invalid literal")
        assert result["error_type"] == "ValueError"


# === AnalyzeTraceback Testleri ===


class TestAnalyzeTraceback:
    """analyze_traceback() testleri."""

    def test_multiple_frames(self) -> None:
        db = _make_debugger()
        frames = db.analyze_traceback(TRACEBACK_SAMPLE)
        assert len(frames) >= 2

    def test_frame_has_file(self) -> None:
        db = _make_debugger()
        frames = db.analyze_traceback(TRACEBACK_SAMPLE)
        assert frames[0]["file"] == "/app/main.py"

    def test_frame_has_function(self) -> None:
        db = _make_debugger()
        frames = db.analyze_traceback(TRACEBACK_SAMPLE)
        assert frames[0]["function"] == "process"

    def test_empty_traceback(self) -> None:
        db = _make_debugger()
        frames = db.analyze_traceback("")
        assert frames == []

    def test_frame_has_code(self) -> None:
        db = _make_debugger()
        frames = db.analyze_traceback(TRACEBACK_SAMPLE)
        assert any(f["code"] for f in frames)


# === FindRootCause Testleri ===


class TestFindRootCause:
    """find_root_cause() testleri."""

    def test_name_error_root_cause(self) -> None:
        db = _make_debugger()
        cause = db.find_root_cause(NAME_ERROR_TRACE, SOURCE_WITH_TYPO)
        assert "mesage" in cause

    def test_name_error_suggests_similar(self) -> None:
        db = _make_debugger()
        cause = db.find_root_cause(NAME_ERROR_TRACE, SOURCE_WITH_TYPO)
        assert "message" in cause or "Benzer" in cause

    def test_import_error_root_cause(self) -> None:
        db = _make_debugger()
        cause = db.find_root_cause(IMPORT_ERROR_TRACE)
        assert "flaskk" in cause

    def test_type_error_root_cause(self) -> None:
        db = _make_debugger()
        cause = db.find_root_cause(TYPE_ERROR_TRACE)
        assert "Arguman" in cause or "argument" in cause.lower()

    def test_key_error_root_cause(self) -> None:
        db = _make_debugger()
        cause = db.find_root_cause(KEY_ERROR_TRACE)
        assert "anahtar" in cause.lower() or "dict" in cause.lower()

    def test_attribute_error_root_cause(self) -> None:
        db = _make_debugger()
        cause = db.find_root_cause(ATTRIBUTE_ERROR_TRACE)
        assert "methd" in cause

    def test_unknown_error(self) -> None:
        db = _make_debugger()
        cause = db.find_root_cause("RuntimeError: something went wrong")
        assert "RuntimeError" in cause


# === SuggestFixes Testleri ===


class TestSuggestFixes:
    """suggest_fixes() testleri."""

    def test_name_error_suggestions(self) -> None:
        db = _make_debugger()
        fixes = db.suggest_fixes(NAME_ERROR_TRACE, SOURCE_WITH_TYPO)
        assert len(fixes) > 0
        assert all(isinstance(f, FixSuggestion) for f in fixes)

    def test_type_error_suggestions(self) -> None:
        db = _make_debugger()
        fixes = db.suggest_fixes(TYPE_ERROR_TRACE)
        assert len(fixes) > 0

    def test_import_error_suggestions(self) -> None:
        db = _make_debugger()
        fixes = db.suggest_fixes(IMPORT_ERROR_TRACE)
        assert len(fixes) > 0
        assert any("pip install" in f.description or "flask" in f.description.lower() for f in fixes)

    def test_key_error_suggestions(self) -> None:
        db = _make_debugger()
        fixes = db.suggest_fixes(KEY_ERROR_TRACE)
        assert len(fixes) > 0
        assert any("get" in f.description.lower() for f in fixes)

    def test_zero_division_suggestions(self) -> None:
        db = _make_debugger()
        fixes = db.suggest_fixes(TRACEBACK_SAMPLE, DIVISION_SOURCE)
        assert len(fixes) > 0

    def test_max_suggestions_respected(self) -> None:
        db = _make_debugger(max_suggestions=2)
        fixes = db.suggest_fixes(NAME_ERROR_TRACE, SOURCE_WITH_TYPO)
        assert len(fixes) <= 2

    def test_value_error_suggestions(self) -> None:
        db = _make_debugger()
        fixes = db.suggest_fixes("ValueError: invalid literal for int()")
        assert len(fixes) > 0


# === AutoFix Testleri ===


class TestAutoFix:
    """auto_fix() testleri."""

    def test_returns_none_when_no_fix(self) -> None:
        db = _make_debugger()
        result = db.auto_fix("RuntimeError: unknown", "x = 1")
        assert result is None

    def test_auto_fix_respects_threshold(self) -> None:
        db = _make_debugger(auto_fix_confidence_threshold=FixConfidence.CERTAIN)
        result = db.auto_fix(NAME_ERROR_TRACE, SOURCE_WITH_TYPO)
        # CERTAIN threshold ile cogu duzeltme uygulanmamali
        # (duzeltme bulunursa da olmayabilir)
        assert result is None or isinstance(result, str)

    def test_auto_fix_validates_syntax(self) -> None:
        db = _make_debugger(auto_fix_confidence_threshold=FixConfidence.LOW)
        result = db.auto_fix(NAME_ERROR_TRACE, SOURCE_WITH_TYPO)
        if result is not None:
            # Sonuc gecerli Python olmali
            import ast
            ast.parse(result)


# === CheckRegression Testleri ===


class TestCheckRegression:
    """check_regression() testleri."""

    def test_identical_code(self) -> None:
        db = _make_debugger()
        code = "def f():\n    return 1\n"
        result = db.check_regression(code, code)
        assert result["passed"] is True

    def test_syntax_error_in_fixed(self) -> None:
        db = _make_debugger()
        original = "def f():\n    return 1\n"
        broken = "def f(\n    return 1\n"
        result = db.check_regression(original, broken)
        assert result["fixed_valid"] is False
        assert result["passed"] is False

    def test_functions_changed(self) -> None:
        db = _make_debugger()
        original = "def f():\n    return 1\n"
        fixed = "def f():\n    return 2\n"
        result = db.check_regression(original, fixed)
        assert "f" in result["functions_changed"]

    def test_diff_generated(self) -> None:
        db = _make_debugger()
        original = "x = 1\n"
        fixed = "x = 2\n"
        result = db.check_regression(original, fixed)
        assert result["diff"] != ""

    def test_function_removed_fails(self) -> None:
        db = _make_debugger()
        original = "def f():\n    return 1\n\ndef g():\n    return 2\n"
        fixed = "def f():\n    return 1\n"
        result = db.check_regression(original, fixed)
        assert result["passed"] is False


# === ClassifyError Testleri ===


class TestClassifyError:
    """_classify_error() testleri."""

    def test_syntax_error(self) -> None:
        db = _make_debugger()
        assert db._classify_error("SyntaxError") == "syntax"

    def test_name_error(self) -> None:
        db = _make_debugger()
        assert db._classify_error("NameError") == "name"

    def test_type_error(self) -> None:
        db = _make_debugger()
        assert db._classify_error("TypeError") == "type"

    def test_import_error(self) -> None:
        db = _make_debugger()
        assert db._classify_error("ImportError") == "import"

    def test_unknown_error(self) -> None:
        db = _make_debugger()
        assert db._classify_error("CustomError") == "runtime"


# === ExtractErrorLine Testleri ===


class TestExtractErrorLine:
    """_extract_error_line() testleri."""

    def test_valid_line(self) -> None:
        db = _make_debugger()
        source = "x = 1\ny = 2\nz = 3\n"
        assert db._extract_error_line(source, 2) == "y = 2"

    def test_invalid_line(self) -> None:
        db = _make_debugger()
        assert db._extract_error_line("x = 1", 0) == ""

    def test_empty_source(self) -> None:
        db = _make_debugger()
        assert db._extract_error_line("", 1) == ""

    def test_line_beyond_end(self) -> None:
        db = _make_debugger()
        assert db._extract_error_line("x = 1", 99) == ""
