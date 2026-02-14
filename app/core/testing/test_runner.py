"""ATLAS Test Calistirici modulu.

Paralel calistirma, test secimi,
yeniden deneme, zaman asimi
ve sonuc toplama.
"""

import logging
import time
from typing import Any

from app.models.testing import TestStatus

logger = logging.getLogger(__name__)


class TestRunner:
    """Test calistirici.

    Testleri calistirir ve sonuclari
    toplar.

    Attributes:
        _results: Test sonuclari.
        _suites: Test suitleri.
    """

    def __init__(
        self,
        max_retries: int = 2,
        timeout_ms: int = 30000,
        parallel: bool = False,
    ) -> None:
        """Test calistiriciya baslatir.

        Args:
            max_retries: Maks yeniden deneme.
            timeout_ms: Zaman asimi (ms).
            parallel: Paralel calistirma.
        """
        self._max_retries = max_retries
        self._timeout_ms = timeout_ms
        self._parallel = parallel
        self._results: list[
            dict[str, Any]
        ] = []
        self._suites: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._filters: dict[str, Any] = {}

        logger.info(
            "TestRunner baslatildi",
        )

    def run_test(
        self,
        name: str,
        test_fn: Any = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Tek test calistirir.

        Args:
            name: Test adi.
            test_fn: Test fonksiyonu.
            tags: Etiketler.

        Returns:
            Test sonucu.
        """
        start = time.time()
        status = TestStatus.PASSED
        error_msg = ""
        retries = 0

        for attempt in range(
            self._max_retries + 1
        ):
            try:
                if test_fn is not None:
                    test_fn()
                status = TestStatus.PASSED
                error_msg = ""
                break
            except Exception as e:
                error_msg = str(e)
                status = TestStatus.FAILED
                retries = attempt

        elapsed = (time.time() - start) * 1000

        # Zaman asimi kontrolu
        if elapsed > self._timeout_ms:
            status = TestStatus.ERROR
            error_msg = "timeout_exceeded"

        result = {
            "name": name,
            "status": status.value,
            "duration_ms": round(elapsed, 2),
            "error": error_msg,
            "retries": retries,
            "tags": tags or [],
            "timestamp": time.time(),
        }
        self._results.append(result)
        return result

    def run_suite(
        self,
        suite_name: str,
        tests: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Test suite calistirir.

        Args:
            suite_name: Suite adi.
            tests: Test listesi.

        Returns:
            Suite sonucu.
        """
        suite_results = []
        passed = 0
        failed = 0
        errors = 0

        for test in tests:
            name = test.get("name", "unnamed")
            fn = test.get("fn")
            tags = test.get("tags", [])

            result = self.run_test(
                name, fn, tags,
            )
            suite_results.append(result)

            if result["status"] == "passed":
                passed += 1
            elif result["status"] == "failed":
                failed += 1
            else:
                errors += 1

        self._suites[suite_name] = suite_results

        return {
            "suite": suite_name,
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "results": suite_results,
        }

    def run_filtered(
        self,
        tests: list[dict[str, Any]],
        tags: list[str] | None = None,
        name_pattern: str = "",
    ) -> dict[str, Any]:
        """Filtreli test calistirir.

        Args:
            tests: Tum testler.
            tags: Filtre etiketleri.
            name_pattern: Isim deseni.

        Returns:
            Filtrelenmis sonuc.
        """
        filtered = tests
        if tags:
            filtered = [
                t for t in filtered
                if any(
                    tag in t.get("tags", [])
                    for tag in tags
                )
            ]
        if name_pattern:
            filtered = [
                t for t in filtered
                if name_pattern in t.get("name", "")
            ]

        results = []
        for test in filtered:
            r = self.run_test(
                test.get("name", "unnamed"),
                test.get("fn"),
                test.get("tags"),
            )
            results.append(r)

        passed = sum(
            1 for r in results
            if r["status"] == "passed"
        )
        return {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "results": results,
        }

    def get_summary(self) -> dict[str, Any]:
        """Ozet getirir.

        Returns:
            Ozet bilgisi.
        """
        total = len(self._results)
        passed = sum(
            1 for r in self._results
            if r["status"] == "passed"
        )
        failed = sum(
            1 for r in self._results
            if r["status"] == "failed"
        )
        errors = sum(
            1 for r in self._results
            if r["status"] == "error"
        )
        total_duration = sum(
            r["duration_ms"]
            for r in self._results
        )

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": round(
                passed / total if total else 0.0,
                4,
            ),
            "total_duration_ms": round(
                total_duration, 2,
            ),
        }

    def get_failures(self) -> list[dict[str, Any]]:
        """Basarisiz testleri getirir.

        Returns:
            Basarisiz testler.
        """
        return [
            r for r in self._results
            if r["status"] in ("failed", "error")
        ]

    def set_filter(
        self,
        key: str,
        value: Any,
    ) -> None:
        """Filtre ayarlar.

        Args:
            key: Filtre anahtari.
            value: Filtre degeri.
        """
        self._filters[key] = value

    def reset(self) -> None:
        """Sonuclari sifirlar."""
        self._results = []
        self._suites = {}

    @property
    def result_count(self) -> int:
        """Sonuc sayisi."""
        return len(self._results)

    @property
    def suite_count(self) -> int:
        """Suite sayisi."""
        return len(self._suites)

    @property
    def pass_rate(self) -> float:
        """Basari orani."""
        total = len(self._results)
        if not total:
            return 0.0
        passed = sum(
            1 for r in self._results
            if r["status"] == "passed"
        )
        return round(passed / total, 4)
