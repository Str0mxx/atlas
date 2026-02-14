"""ATLAS QA Orkestratoru modulu.

Tam QA pipeline, CI/CD entegrasyonu,
kalite kapilari, bildirim
ve analitik.
"""

import logging
import time
from typing import Any

from app.core.testing.test_generator import (
    TestGenerator,
)
from app.core.testing.test_runner import (
    TestRunner,
)
from app.core.testing.coverage_analyzer import (
    CoverageAnalyzer,
)
from app.core.testing.mutation_tester import (
    MutationTester,
)
from app.core.testing.regression_detector import (
    RegressionDetector,
)
from app.core.testing.load_tester import (
    LoadTester,
)
from app.core.testing.quality_scorer import (
    QualityScorer,
)
from app.core.testing.report_generator import (
    TestReportGenerator,
)

logger = logging.getLogger(__name__)


class QAOrchestrator:
    """QA orkestratoru.

    Tum QA bilesenlerini koordine eder.

    Attributes:
        generator: Test ureticisi.
        runner: Test calistirici.
        coverage: Kapsam analizcisi.
        mutation: Mutasyon test edici.
        regression: Regresyon tespitcisi.
        load: Yuk test edici.
        quality: Kalite puanlayici.
        reports: Rapor ureticisi.
    """

    def __init__(
        self,
        min_coverage: float = 80.0,
        mutation_threshold: float = 0.8,
    ) -> None:
        """QA orkestratorunu baslatir.

        Args:
            min_coverage: Minimum kapsam.
            mutation_threshold: Mutasyon esigi.
        """
        self._started_at = time.time()

        self.generator = TestGenerator()
        self.runner = TestRunner()
        self.coverage = CoverageAnalyzer(
            min_coverage=min_coverage,
        )
        self.mutation = MutationTester(
            threshold=mutation_threshold,
        )
        self.regression = RegressionDetector()
        self.load = LoadTester()
        self.quality = QualityScorer()
        self.reports = TestReportGenerator()

        self._pipeline_runs: list[
            dict[str, Any]
        ] = []
        self._notifications: list[
            dict[str, Any]
        ] = []

        logger.info(
            "QAOrchestrator baslatildi",
        )

    def run_qa_pipeline(
        self,
        tests: list[dict[str, Any]],
        coverage_data: dict[str, Any] | None = None,
        run_load: bool = False,
    ) -> dict[str, Any]:
        """Tam QA pipeline calistirir.

        Args:
            tests: Testler.
            coverage_data: Kapsam verileri.
            run_load: Yuk testi calistir.

        Returns:
            Pipeline sonucu.
        """
        start = time.time()

        # 1. Testleri calistir
        test_results = self.runner.run_suite(
            "qa_pipeline", tests,
        )

        # 2. Kapsam degerlendirmesi
        cov_summary = {}
        if coverage_data:
            for mod, data in coverage_data.items():
                self.coverage.add_module_coverage(
                    module=mod,
                    total_lines=data.get(
                        "total_lines", 0,
                    ),
                    covered_lines=data.get(
                        "covered_lines", 0,
                    ),
                    total_branches=data.get(
                        "total_branches", 0,
                    ),
                    covered_branches=data.get(
                        "covered_branches", 0,
                    ),
                )
            cov_summary = (
                self.coverage.get_summary()
            )

        # 3. Yuk testi
        load_result = None
        if run_load:
            load_result = (
                self.load.run_throughput_test(
                    "pipeline_load",
                )
            )

        # 4. Kalite kontrolu
        quality_summary = (
            self.quality.get_overall_score()
        )

        elapsed = time.time() - start

        pipeline = {
            "test_results": {
                "total": test_results["total"],
                "passed": test_results["passed"],
                "failed": test_results["failed"],
            },
            "coverage": cov_summary,
            "load_test": load_result,
            "quality": quality_summary,
            "duration_s": round(elapsed, 2),
            "timestamp": time.time(),
        }
        self._pipeline_runs.append(pipeline)

        # Bildirim
        if test_results["failed"] > 0:
            self._notify(
                "QA Pipeline: Test basarisizliklari",
                "warning",
            )

        return pipeline

    def check_quality_gate(
        self,
        values: dict[str, float],
    ) -> dict[str, Any]:
        """Kalite kapisini kontrol eder.

        Args:
            values: Metrik degerleri.

        Returns:
            Kontrol sonucu.
        """
        return self.quality.check_quality_gates(
            values,
        )

    def run_regression_check(
        self,
        name: str,
        current: dict[str, float],
    ) -> dict[str, Any]:
        """Regresyon kontrolu yapar.

        Args:
            name: Metrik adi.
            current: Mevcut degerler.

        Returns:
            Kontrol sonucu.
        """
        result = (
            self.regression
            .compare_with_baseline(name, current)
        )

        if result.get("has_regression"):
            self._notify(
                f"Regression detected: {name}",
                "error",
            )

        return result

    def _notify(
        self,
        message: str,
        level: str = "info",
    ) -> None:
        """Bildirim olusturur.

        Args:
            message: Mesaj.
            level: Seviye.
        """
        self._notifications.append({
            "message": message,
            "level": level,
            "timestamp": time.time(),
        })

    def get_analytics(self) -> dict[str, Any]:
        """Analitik getirir.

        Returns:
            Analitik bilgisi.
        """
        total_runs = len(self._pipeline_runs)
        total_tests = self.runner.result_count

        return {
            "pipeline_runs": total_runs,
            "total_tests_run": total_tests,
            "pass_rate": self.runner.pass_rate,
            "coverage": (
                self.coverage.overall_coverage
            ),
            "mutations": (
                self.mutation.mutation_count
            ),
            "regressions": (
                self.regression.regression_count
            ),
            "quality_score": (
                self.quality
                .get_overall_score()
                .get("score", 0.0)
            ),
            "notifications": len(
                self._notifications,
            ),
        }

    def snapshot(self) -> dict[str, Any]:
        """QA durumunu dondurur.

        Returns:
            Durum bilgisi.
        """
        return {
            "uptime": round(
                time.time() - self._started_at,
                2,
            ),
            "pipeline_runs": len(
                self._pipeline_runs,
            ),
            "tests_generated": (
                self.generator.generated_count
            ),
            "tests_run": (
                self.runner.result_count
            ),
            "coverage_modules": (
                self.coverage.module_count
            ),
            "mutations": (
                self.mutation.mutation_count
            ),
            "regressions": (
                self.regression.regression_count
            ),
            "load_tests": (
                self.load.result_count
            ),
            "quality_metrics": (
                self.quality.metric_count
            ),
            "reports": (
                self.reports.report_count
            ),
            "notifications": len(
                self._notifications,
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline calistirma sayisi."""
        return len(self._pipeline_runs)

    @property
    def notification_count(self) -> int:
        """Bildirim sayisi."""
        return len(self._notifications)
