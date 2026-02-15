"""ATLAS Benchmark Orkestrator modulu.

Tam benchmarking pipeline, zamanlanmis degerlendirme,
surekli izleme, entegrasyon, analitik.
"""

import logging
import time
from typing import Any

from app.core.benchmark.ab_tester import (
    ABTester,
)
from app.core.benchmark.alert_manager import (
    BenchmarkAlertManager,
)
from app.core.benchmark.comparison_engine import (
    ComparisonEngine,
)
from app.core.benchmark.kpi_definer import (
    KPIDefiner,
)
from app.core.benchmark.metric_collector import (
    BenchmarkMetricCollector,
)
from app.core.benchmark.performance_scorer import (
    PerformanceScorer,
)
from app.core.benchmark.report_generator import (
    BenchmarkReportGenerator,
)
from app.core.benchmark.trend_analyzer import (
    BenchmarkTrendAnalyzer,
)

logger = logging.getLogger(__name__)


class BenchmarkOrchestrator:
    """Benchmark orkestrator.

    Tum benchmark bilesenleri koordine eder.

    Attributes:
        kpis: KPI tanimlayici.
        metrics: Metrik toplayici.
        scorer: Performans puanlayici.
        trends: Trend analizcisi.
        ab_tester: A/B test motoru.
        comparison: Karsilastirma motoru.
        reports: Rapor uretici.
        alerts: Uyari yoneticisi.
    """

    def __init__(
        self,
        ab_min_samples: int = 30,
        alert_on_degradation: bool = True,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            ab_min_samples: A/B test min ornek.
            alert_on_degradation: Bozulmada uyar.
        """
        self.kpis = KPIDefiner()
        self.metrics = BenchmarkMetricCollector()
        self.scorer = PerformanceScorer()
        self.trends = BenchmarkTrendAnalyzer()
        self.ab_tester = ABTester(
            min_samples=ab_min_samples,
        )
        self.comparison = ComparisonEngine()
        self.reports = BenchmarkReportGenerator()
        self.alerts = BenchmarkAlertManager()

        self._alert_on_degradation = (
            alert_on_degradation
        )
        self._stats = {
            "evaluations": 0,
        }

        logger.info(
            "BenchmarkOrchestrator baslatildi",
        )

    def evaluate_kpi(
        self,
        kpi_id: str,
        value: float,
    ) -> dict[str, Any]:
        """KPI degerlendirir (tam pipeline).

        Args:
            kpi_id: KPI ID.
            value: Guncel deger.

        Returns:
            Degerlendirme sonucu.
        """
        # 1. Metrik topla
        self.metrics.collect(kpi_id, value)

        # 2. Trend verisi ekle
        self.trends.add_data_point(kpi_id, value)

        # 3. Puanla
        kpi = self.kpis.get_kpi(kpi_id)
        score_result = None
        if kpi and kpi.get("target") is not None:
            score_result = self.scorer.score(
                kpi_id,
                value,
                target=kpi["target"],
                threshold=kpi.get("threshold"),
            )

            # 4. Esik uyarisi
            alert = self.alerts.alert_threshold(
                kpi_id, value, kpi["target"],
            )

        # 5. Bozulma kontrolu
        degradation_alert = None
        if self._alert_on_degradation:
            trend = self.trends.analyze_trend(
                kpi_id,
            )
            if trend.get("direction") == "degrading":
                degradation_alert = (
                    self.alerts.alert_degradation(
                        kpi_id,
                        trend.get("change_pct", 0),
                    )
                )

        # 6. Anomali kontrolu
        anomaly = self.trends.detect_anomaly(
            kpi_id, value,
        )

        self._stats["evaluations"] += 1

        return {
            "kpi_id": kpi_id,
            "value": value,
            "score": (
                score_result.get("score")
                if score_result
                else None
            ),
            "meets_target": (
                score_result.get("meets_target")
                if score_result
                else None
            ),
            "is_anomaly": anomaly.get(
                "is_anomaly", False,
            ),
            "degradation_alert": (
                degradation_alert is not None
            ),
        }

    def run_evaluation(
        self,
    ) -> dict[str, Any]:
        """Tam degerlendirme calistirir.

        Returns:
            Degerlendirme sonucu.
        """
        all_kpis = self.kpis.list_kpis()
        results = {}

        for kpi in all_kpis:
            kpi_id = kpi["kpi_id"]
            latest = self.metrics.get_latest(kpi_id)
            if latest:
                r = self.evaluate_kpi(
                    kpi_id, latest["value"],
                )
                results[kpi_id] = r

        # Rapor uret
        scores = {}
        for kpi_id, r in results.items():
            if r.get("score") is not None:
                scores[kpi_id] = {
                    "score": r["score"],
                    "meets_target": r["meets_target"],
                }

        report = None
        if scores:
            report = (
                self.reports.generate_performance_report(
                    scores,
                )
            )

        return {
            "kpis_evaluated": len(results),
            "results": results,
            "report": report,
        }

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        return {
            "total_kpis": self.kpis.kpi_count,
            "metrics_tracked": (
                self.metrics.metric_count
            ),
            "total_scores": (
                self.scorer.total_scores
            ),
            "active_experiments": (
                self.ab_tester.active_count
            ),
            "active_alerts": (
                self.alerts.active_count
            ),
            "reports_generated": (
                self.reports.report_count
            ),
            "evaluations": (
                self._stats["evaluations"]
            ),
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        all_kpis = self.kpis.list_kpis()
        trend_data = {}
        for kpi in all_kpis:
            kid = kpi["kpi_id"]
            trend_data[kid] = (
                self.trends.analyze_trend(kid)
            )

        return {
            "kpi_count": len(all_kpis),
            "trends": trend_data,
            "anomalies": self.trends.get_anomalies(
                limit=10,
            ),
            "active_alerts": (
                self.alerts.get_active_alerts()
            ),
            "experiments": (
                self.ab_tester.experiment_count
            ),
        }

    @property
    def evaluation_count(self) -> int:
        """Degerlendirme sayisi."""
        return self._stats["evaluations"]
