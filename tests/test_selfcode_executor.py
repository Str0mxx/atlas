"""SafeExecutor testleri.

Guvenlik kontrolu, sandbox calistirma, dosya calistirma,
test calistirma, cikti yakalama ve temizlik testleri.
"""

import os
import pytest

from app.core.selfcode.code_executor import (
    DANGEROUS_PATTERNS,
    SafeExecutor,
)
from app.models.selfcode import (
    ExecutionConfig,
    ExecutionResult,
    ExecutionStatus,
)


# === Yardimci Fonksiyonlar ===


def _make_executor(**kwargs) -> SafeExecutor:
    """Test icin SafeExecutor olusturur."""
    return SafeExecutor(**kwargs)


SAFE_CODE = """\
x = 1 + 2
print(x)
"""

DANGEROUS_CODE_EVAL = """\
result = eval("1 + 2")
"""

DANGEROUS_CODE_OS = """\
import os
os.system("ls")
"""

DANGEROUS_CODE_EXEC = """\
exec("print('hello')")
"""

DANGEROUS_CODE_IMPORT = """\
mod = __import__("os")
"""

TEST_CODE = """\
def test_add():
    assert 1 + 1 == 2

def test_sub():
    assert 3 - 1 == 2
"""

COMPLEX_CODE = """\
import json

class MyClass:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello {self.name}"

def process(data):
    return json.dumps(data)
"""


# === Init Testleri ===


class TestInit:
    """SafeExecutor init testleri."""

    def test_defaults(self) -> None:
        se = _make_executor()
        assert se.sandbox_mode is True
        assert se.config.timeout == 30.0

    def test_custom_config(self) -> None:
        config = ExecutionConfig(timeout=10.0, max_memory_mb=128)
        se = _make_executor(config=config)
        assert se.config.timeout == 10.0
        assert se.config.max_memory_mb == 128

    def test_sandbox_mode_off(self) -> None:
        se = _make_executor(sandbox_mode=False)
        assert se.sandbox_mode is False


# === CheckSafety Testleri ===


class TestCheckSafety:
    """check_safety() testleri."""

    def test_safe_code(self) -> None:
        se = _make_executor()
        is_safe, violations = se.check_safety(SAFE_CODE)
        assert is_safe is True
        assert violations == []

    def test_eval_detected(self) -> None:
        se = _make_executor()
        is_safe, violations = se.check_safety(DANGEROUS_CODE_EVAL)
        assert is_safe is False
        assert len(violations) > 0

    def test_os_system_detected(self) -> None:
        se = _make_executor()
        is_safe, violations = se.check_safety(DANGEROUS_CODE_OS)
        assert is_safe is False

    def test_exec_detected(self) -> None:
        se = _make_executor()
        is_safe, violations = se.check_safety(DANGEROUS_CODE_EXEC)
        assert is_safe is False

    def test_import_hack_detected(self) -> None:
        se = _make_executor()
        is_safe, violations = se.check_safety(DANGEROUS_CODE_IMPORT)
        assert is_safe is False

    def test_empty_code_safe(self) -> None:
        se = _make_executor()
        is_safe, _ = se.check_safety("")
        assert is_safe is True

    def test_multiple_violations(self) -> None:
        se = _make_executor()
        code = 'eval("x")\nexec("y")\nos.system("z")'
        is_safe, violations = se.check_safety(code)
        assert is_safe is False
        assert len(violations) >= 3


# === Execute (Sandbox) Testleri ===


class TestExecuteSandbox:
    """execute() sandbox modu testleri."""

    def test_safe_code_succeeds(self) -> None:
        se = _make_executor(sandbox_mode=True)
        result = se.execute(SAFE_CODE)
        assert result.status == ExecutionStatus.COMPLETED
        assert result.exit_code == 0

    def test_dangerous_code_rejected(self) -> None:
        se = _make_executor(sandbox_mode=True)
        result = se.execute(DANGEROUS_CODE_EVAL)
        assert result.status == ExecutionStatus.FAILED
        assert "Guvenlik" in result.stderr or "ihlal" in result.stderr.lower()

    def test_sandbox_stdout_has_info(self) -> None:
        se = _make_executor(sandbox_mode=True)
        result = se.execute(SAFE_CODE)
        assert "SANDBOX" in result.stdout

    def test_complex_code_info(self) -> None:
        se = _make_executor(sandbox_mode=True)
        result = se.execute(COMPLEX_CODE)
        assert "Fonksiyon" in result.stdout or "fonksiyon" in result.stdout.lower()
        assert "Sinif" in result.stdout or "sinif" in result.stdout.lower()

    def test_result_has_id(self) -> None:
        se = _make_executor(sandbox_mode=True)
        result = se.execute(SAFE_CODE)
        assert result.id != ""

    def test_duration_zero_in_sandbox(self) -> None:
        se = _make_executor(sandbox_mode=True)
        result = se.execute(SAFE_CODE)
        assert result.duration == 0.0


# === ExecuteTests (Sandbox) Testleri ===


class TestExecuteTestsSandbox:
    """execute_tests() sandbox modu testleri."""

    def test_test_code_succeeds(self) -> None:
        se = _make_executor(sandbox_mode=True)
        result = se.execute_tests(TEST_CODE)
        assert result.status == ExecutionStatus.COMPLETED

    def test_test_count_detected(self) -> None:
        se = _make_executor(sandbox_mode=True)
        result = se.execute_tests(TEST_CODE)
        assert "2" in result.stdout  # 2 test fonksiyonu

    def test_dangerous_test_rejected(self) -> None:
        se = _make_executor(sandbox_mode=True)
        result = se.execute_tests('def test_bad():\n    eval("1")\n')
        assert result.status == ExecutionStatus.FAILED

    def test_empty_tests(self) -> None:
        se = _make_executor(sandbox_mode=True)
        result = se.execute_tests("# no tests")
        assert result.status == ExecutionStatus.COMPLETED


# === SetResourceLimits Testleri ===


class TestSetResourceLimits:
    """set_resource_limits() testleri."""

    def test_set_timeout(self) -> None:
        se = _make_executor()
        se.set_resource_limits(timeout=60.0)
        assert se.config.timeout == 60.0

    def test_set_memory(self) -> None:
        se = _make_executor()
        se.set_resource_limits(max_memory_mb=512)
        assert se.config.max_memory_mb == 512

    def test_set_output_lines(self) -> None:
        se = _make_executor()
        se.set_resource_limits(max_output_lines=500)
        assert se.config.max_output_lines == 500

    def test_none_preserves_value(self) -> None:
        se = _make_executor()
        original = se.config.timeout
        se.set_resource_limits(max_memory_mb=512)
        assert se.config.timeout == original


# === CaptureOutput Testleri ===


class TestCaptureOutput:
    """capture_output() testleri."""

    def test_short_output(self) -> None:
        se = _make_executor()
        result = se.capture_output("line1\nline2\n")
        assert result == "line1\nline2\n"

    def test_empty_output(self) -> None:
        se = _make_executor()
        assert se.capture_output("") == ""

    def test_truncation(self) -> None:
        config = ExecutionConfig(max_output_lines=3)
        se = _make_executor(config=config)
        long_output = "\n".join(f"line {i}" for i in range(100))
        result = se.capture_output(long_output)
        assert "kesildi" in result


# === Cleanup Testleri ===


class TestCleanup:
    """cleanup() testleri."""

    def test_cleanup_empty(self) -> None:
        se = _make_executor()
        se.cleanup()
        assert se._temp_files == []

    def test_temp_file_tracked(self) -> None:
        se = _make_executor()
        path = se._create_temp_file("x = 1")
        assert path is not None
        assert len(se._temp_files) == 1
        se.cleanup()
        assert se._temp_files == []

    def test_temp_file_deleted(self) -> None:
        se = _make_executor()
        path = se._create_temp_file("x = 1")
        assert os.path.exists(path)
        se.cleanup()
        assert not os.path.exists(path)


# === ParseTestResults Testleri ===


class TestParseTestResults:
    """_parse_test_results() testleri."""

    def test_all_passed(self) -> None:
        se = _make_executor()
        passed, failed, errors = se._parse_test_results("5 passed in 1.0s")
        assert passed == 5
        assert failed == 0

    def test_mixed_results(self) -> None:
        se = _make_executor()
        passed, failed, errors = se._parse_test_results(
            "3 passed, 2 failed, 1 error"
        )
        assert passed == 3
        assert failed == 2
        assert errors == 1

    def test_empty_output(self) -> None:
        se = _make_executor()
        passed, failed, errors = se._parse_test_results("")
        assert passed == 0
        assert failed == 0
        assert errors == 0


# === DangerousPatterns Testleri ===


class TestDangerousPatterns:
    """DANGEROUS_PATTERNS sabitleri testleri."""

    def test_patterns_exist(self) -> None:
        assert len(DANGEROUS_PATTERNS) > 0

    def test_eval_pattern(self) -> None:
        import re
        assert any(re.search(p, "eval('x')") for p in DANGEROUS_PATTERNS)

    def test_safe_code_not_matched(self) -> None:
        import re
        safe = "x = 1 + 2"
        assert not any(re.search(p, safe) for p in DANGEROUS_PATTERNS)


# === ExecutionConfig Testleri ===


class TestExecutionConfig:
    """ExecutionConfig model testleri."""

    def test_defaults(self) -> None:
        config = ExecutionConfig()
        assert config.timeout == 30.0
        assert config.max_memory_mb == 256
        assert config.allow_network is False
        assert config.allow_filesystem is False

    def test_custom(self) -> None:
        config = ExecutionConfig(
            timeout=60.0, allow_network=True
        )
        assert config.timeout == 60.0
        assert config.allow_network is True
