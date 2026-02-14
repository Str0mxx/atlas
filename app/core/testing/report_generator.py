"""ATLAS Test Rapor Ureticisi modulu.

HTML raporlar, JUnit XML,
kapsam raporlari, trend analizi
ve yonetici ozeti.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TestReportGenerator:
    """Test rapor ureticisi.

    Test sonuclarindan raporlar uretir.

    Attributes:
        _reports: Rapor kayitlari.
        _history: Gecmis verileri.
    """

    def __init__(self) -> None:
        """Rapor ureticisini baslatir."""
        self._reports: list[
            dict[str, Any]
        ] = []
        self._history: list[
            dict[str, Any]
        ] = []

        logger.info(
            "TestReportGenerator baslatildi",
        )

    def generate_html_report(
        self,
        results: list[dict[str, Any]],
        title: str = "Test Report",
    ) -> dict[str, Any]:
        """HTML rapor uretir.

        Args:
            results: Test sonuclari.
            title: Rapor basligi.

        Returns:
            Rapor bilgisi.
        """
        passed = sum(
            1 for r in results
            if r.get("status") == "passed"
        )
        failed = sum(
            1 for r in results
            if r.get("status") == "failed"
        )
        total = len(results)

        rows = ""
        for r in results:
            status = r.get("status", "unknown")
            css = (
                "pass" if status == "passed"
                else "fail"
            )
            rows += (
                f"<tr class='{css}'>"
                f"<td>{r.get('name', '')}</td>"
                f"<td>{status}</td>"
                f"<td>{r.get('duration_ms', 0)}</td>"
                f"</tr>\n"
            )

        html = (
            f"<html><head><title>{title}</title>"
            f"</head><body>"
            f"<h1>{title}</h1>"
            f"<p>Total: {total}, "
            f"Passed: {passed}, "
            f"Failed: {failed}</p>"
            f"<table>{rows}</table>"
            f"</body></html>"
        )

        report = {
            "format": "html",
            "title": title,
            "content": html,
            "total": total,
            "passed": passed,
            "failed": failed,
            "generated_at": time.time(),
        }
        self._reports.append(report)
        return report

    def generate_junit_xml(
        self,
        results: list[dict[str, Any]],
        suite_name: str = "TestSuite",
    ) -> dict[str, Any]:
        """JUnit XML rapor uretir.

        Args:
            results: Test sonuclari.
            suite_name: Suite adi.

        Returns:
            Rapor bilgisi.
        """
        total = len(results)
        failures = sum(
            1 for r in results
            if r.get("status") == "failed"
        )
        errors = sum(
            1 for r in results
            if r.get("status") == "error"
        )

        test_cases = ""
        for r in results:
            name = r.get("name", "test")
            status = r.get("status", "passed")
            duration = r.get("duration_ms", 0) / 1000

            test_cases += (
                f'  <testcase name="{name}" '
                f'time="{duration:.3f}"'
            )
            if status == "failed":
                err = r.get("error", "")
                test_cases += (
                    f'>\n    <failure message='
                    f'"{err}"/>\n  </testcase>\n'
                )
            elif status == "error":
                err = r.get("error", "")
                test_cases += (
                    f'>\n    <error message='
                    f'"{err}"/>\n  </testcase>\n'
                )
            else:
                test_cases += "/>\n"

        xml = (
            '<?xml version="1.0"?>\n'
            f'<testsuite name="{suite_name}" '
            f'tests="{total}" '
            f'failures="{failures}" '
            f'errors="{errors}">\n'
            f'{test_cases}'
            f'</testsuite>'
        )

        report = {
            "format": "junit_xml",
            "suite_name": suite_name,
            "content": xml,
            "total": total,
            "failures": failures,
            "errors": errors,
            "generated_at": time.time(),
        }
        self._reports.append(report)
        return report

    def generate_coverage_report(
        self,
        coverage_data: dict[str, Any],
        title: str = "Coverage Report",
    ) -> dict[str, Any]:
        """Kapsam raporu uretir.

        Args:
            coverage_data: Kapsam verileri.
            title: Rapor basligi.

        Returns:
            Rapor bilgisi.
        """
        report = {
            "format": "coverage",
            "title": title,
            "data": coverage_data,
            "generated_at": time.time(),
        }
        self._reports.append(report)
        return report

    def generate_trend_analysis(
        self,
        data_points: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Trend analizi uretir.

        Args:
            data_points: Veri noktalari.

        Returns:
            Trend bilgisi.
        """
        if not data_points:
            return {
                "trend": "stable",
                "data_points": 0,
            }

        self._history.extend(data_points)

        values = [
            d.get("value", 0)
            for d in data_points
        ]

        if len(values) < 2:
            trend = "stable"
        elif values[-1] > values[0]:
            trend = "improving"
        elif values[-1] < values[0]:
            trend = "declining"
        else:
            trend = "stable"

        avg = sum(values) / len(values)

        return {
            "trend": trend,
            "data_points": len(data_points),
            "average": round(avg, 2),
            "latest": values[-1],
            "first": values[0],
            "change": round(
                values[-1] - values[0], 2,
            ),
        }

    def generate_executive_summary(
        self,
        test_results: dict[str, Any],
        coverage: dict[str, Any] | None = None,
        quality: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Yonetici ozeti uretir.

        Args:
            test_results: Test sonuclari.
            coverage: Kapsam verileri.
            quality: Kalite verileri.

        Returns:
            Ozet rapor.
        """
        summary = {
            "format": "executive_summary",
            "tests": {
                "total": test_results.get(
                    "total", 0,
                ),
                "passed": test_results.get(
                    "passed", 0,
                ),
                "failed": test_results.get(
                    "failed", 0,
                ),
                "pass_rate": test_results.get(
                    "pass_rate", 0.0,
                ),
            },
            "generated_at": time.time(),
        }

        if coverage:
            summary["coverage"] = {
                "line": coverage.get(
                    "line_coverage", 0.0,
                ),
                "branch": coverage.get(
                    "branch_coverage", 0.0,
                ),
            }

        if quality:
            summary["quality"] = {
                "score": quality.get("score", 0.0),
            }

        self._reports.append(summary)
        return summary

    def get_report(
        self,
        index: int = -1,
    ) -> dict[str, Any] | None:
        """Rapor getirir.

        Args:
            index: Rapor indeksi.

        Returns:
            Rapor veya None.
        """
        if not self._reports:
            return None
        try:
            return self._reports[index]
        except IndexError:
            return None

    @property
    def report_count(self) -> int:
        """Rapor sayisi."""
        return len(self._reports)

    @property
    def history_count(self) -> int:
        """Gecmis sayisi."""
        return len(self._history)
