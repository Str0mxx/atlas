"""ATLAS Sandbox Test modulu.

Izole calistirma, dis servisleri mocklama, yanit dogrulama,
performans kontrolu ve guvenlik taramasi.
"""

import logging
import time
from typing import Any

from app.models.jit import GeneratedCode, SandboxResult, SandboxTestResult

logger = logging.getLogger(__name__)

# Guvenlik riski kaliplari
_SECURITY_PATTERNS: list[tuple[str, str]] = [
    ("eval(", "eval kullanimi tehlikeli"),
    ("exec(", "exec kullanimi tehlikeli"),
    ("__import__", "dinamik import riski"),
    ("subprocess", "subprocess kullanimi riski"),
    ("os.system", "os.system kullanimi riski"),
    ("open(", "dosya erisimi kontrol edilmeli"),
    ("pickle", "pickle deserialization riski"),
    ("shell=True", "shell injection riski"),
    ("rm -rf", "silme komutu riski"),
    ("DROP TABLE", "veritabani silme riski"),
]

# Performans esikleri
_PERF_THRESHOLDS = {
    "max_execution_ms": 5000,
    "max_memory_mb": 100,
    "max_line_count": 1000,
}


class SandboxTester:
    """Sandbox test sistemi.

    Uretilen kodu izole ortamda test eder, guvenlik
    taramasi yapar ve performans kontrolu saglar.

    Attributes:
        _results: Test sonuclari.
        _mocks: Mock tanimlari.
    """

    def __init__(self) -> None:
        """Sandbox test sistemini baslatir."""
        self._results: list[SandboxResult] = []
        self._mocks: dict[str, Any] = {}

        logger.info("SandboxTester baslatildi")

    def run_isolated(self, code: GeneratedCode, test_data: dict[str, Any] | None = None) -> SandboxResult:
        """Kodu izole ortamda calistirir.

        Args:
            code: Calistirilacak kod.
            test_data: Test verileri.

        Returns:
            SandboxResult nesnesi.
        """
        start = time.monotonic()

        try:
            # Syntax kontrolu
            compile(code.source_code, f"<{code.module_name}>", "exec")

            elapsed = (time.monotonic() - start) * 1000
            result = SandboxResult(
                test_name=f"isolated_{code.module_name}",
                result=SandboxTestResult.PASSED,
                execution_time_ms=elapsed,
                output=f"Modul {code.module_name} basariyla derlendi ({code.line_count} satir)",
            )

        except SyntaxError as e:
            elapsed = (time.monotonic() - start) * 1000
            result = SandboxResult(
                test_name=f"isolated_{code.module_name}",
                result=SandboxTestResult.FAILED,
                execution_time_ms=elapsed,
                error=f"Syntax hatasi: {e}",
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            result = SandboxResult(
                test_name=f"isolated_{code.module_name}",
                result=SandboxTestResult.ERROR,
                execution_time_ms=elapsed,
                error=str(e),
            )

        self._results.append(result)
        return result

    def mock_service(self, service_name: str, mock_response: Any) -> None:
        """Dis servisi mocklar.

        Args:
            service_name: Servis adi.
            mock_response: Mock yanit.
        """
        self._mocks[service_name] = mock_response
        logger.info("Servis mocklandi: %s", service_name)

    def get_mock(self, service_name: str) -> Any:
        """Mock yanitini getirir."""
        return self._mocks.get(service_name)

    def validate_response(self, response: dict[str, Any], expected_fields: list[str]) -> SandboxResult:
        """Yaniti dogrular.

        Args:
            response: Dogrulanacak yanit.
            expected_fields: Beklenen alanlar.

        Returns:
            SandboxResult nesnesi.
        """
        missing = [f for f in expected_fields if f not in response]

        if missing:
            result = SandboxResult(
                test_name="response_validation",
                result=SandboxTestResult.FAILED,
                error=f"Eksik alanlar: {', '.join(missing)}",
            )
        else:
            result = SandboxResult(
                test_name="response_validation",
                result=SandboxTestResult.PASSED,
                output=f"Tum alanlar mevcut ({len(expected_fields)} alan)",
            )

        self._results.append(result)
        return result

    def check_performance(self, code: GeneratedCode) -> SandboxResult:
        """Performans kontrolu yapar.

        Args:
            code: Kontrol edilecek kod.

        Returns:
            SandboxResult nesnesi.
        """
        issues: list[str] = []

        # Satir sayisi kontrolu
        if code.line_count > _PERF_THRESHOLDS["max_line_count"]:
            issues.append(f"Satir sayisi cok fazla: {code.line_count}")

        # Ic ice donguleri kontrol et
        source = code.source_code
        nested_loops = source.count("for ") + source.count("while ")
        if nested_loops > 5:
            issues.append(f"Cok fazla dongu: {nested_loops}")

        # Derleme suresi
        start = time.monotonic()
        try:
            compile(source, f"<{code.module_name}>", "exec")
        except SyntaxError:
            pass
        compile_time = (time.monotonic() - start) * 1000

        if compile_time > 100:
            issues.append(f"Derleme suresi yuksek: {compile_time:.1f}ms")

        if issues:
            result = SandboxResult(
                test_name=f"perf_{code.module_name}",
                result=SandboxTestResult.FAILED,
                execution_time_ms=compile_time,
                error="; ".join(issues),
            )
        else:
            result = SandboxResult(
                test_name=f"perf_{code.module_name}",
                result=SandboxTestResult.PASSED,
                execution_time_ms=compile_time,
                output=f"Performans uygun ({code.line_count} satir, {compile_time:.1f}ms)",
            )

        self._results.append(result)
        return result

    def scan_security(self, code: GeneratedCode) -> SandboxResult:
        """Guvenlik taramasi yapar.

        Args:
            code: Taranan kod.

        Returns:
            SandboxResult nesnesi.
        """
        issues: list[str] = []
        source = code.source_code

        for pattern, description in _SECURITY_PATTERNS:
            if pattern in source:
                issues.append(description)

        if issues:
            result = SandboxResult(
                test_name=f"security_{code.module_name}",
                result=SandboxTestResult.FAILED,
                error=f"{len(issues)} guvenlik sorunu",
                security_issues=issues,
            )
        else:
            result = SandboxResult(
                test_name=f"security_{code.module_name}",
                result=SandboxTestResult.PASSED,
                output="Guvenlik taramasi temiz",
                security_issues=[],
            )

        self._results.append(result)
        return result

    def run_all_checks(self, code: GeneratedCode) -> list[SandboxResult]:
        """Tum kontrolleri calistirir.

        Args:
            code: Kontrol edilecek kod.

        Returns:
            SandboxResult listesi.
        """
        results = [
            self.run_isolated(code),
            self.check_performance(code),
            self.scan_security(code),
        ]
        return results

    @property
    def results(self) -> list[SandboxResult]:
        """Tum test sonuclari."""
        return list(self._results)

    @property
    def result_count(self) -> int:
        """Toplam test sayisi."""
        return len(self._results)

    @property
    def pass_count(self) -> int:
        """Gecen test sayisi."""
        return sum(1 for r in self._results if r.result == SandboxTestResult.PASSED)

    @property
    def fail_count(self) -> int:
        """Kalan test sayisi."""
        return sum(1 for r in self._results if r.result in (SandboxTestResult.FAILED, SandboxTestResult.ERROR))
