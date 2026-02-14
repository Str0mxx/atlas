"""ATLAS Saglik Tarayici modulu.

Tam sistem taramasi, bilesen saglik kontrolu,
performans metrikleri, kaynak kullanimi
ve anomali tespiti.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.diagnostic import HealthReport, HealthStatus

logger = logging.getLogger(__name__)


class HealthScanner:
    """Saglik tarayici.

    Tum sistemi tarayarak saglik durumunu
    belirler ve anomalileri tespit eder.

    Attributes:
        _components: Kayitli bilesenler.
        _reports: Saglik raporlari.
        _baselines: Normal metrik degerleri.
        _anomalies: Tespit edilen anomaliler.
    """

    def __init__(self) -> None:
        """Saglik tarayiciyi baslatir."""
        self._components: dict[str, dict[str, Any]] = {}
        self._reports: list[HealthReport] = []
        self._baselines: dict[str, dict[str, float]] = {}
        self._anomalies: list[dict[str, Any]] = []

        logger.info("HealthScanner baslatildi")

    def register_component(
        self,
        name: str,
        component_type: str = "service",
        thresholds: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Bilesen kaydeder.

        Args:
            name: Bilesen adi.
            component_type: Bilesen turu.
            thresholds: Esik degerleri.

        Returns:
            Kayit bilgisi.
        """
        self._components[name] = {
            "type": component_type,
            "thresholds": thresholds or {},
            "last_status": HealthStatus.UNKNOWN.value,
            "scan_count": 0,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("Bilesen kaydedildi: %s (%s)", name, component_type)
        return self._components[name]

    def scan_component(
        self,
        name: str,
        metrics: dict[str, float],
    ) -> HealthReport:
        """Bilesen tarar.

        Args:
            name: Bilesen adi.
            metrics: Metrik degerleri.

        Returns:
            HealthReport nesnesi.
        """
        comp = self._components.get(name)
        thresholds = comp.get("thresholds", {}) if comp else {}

        issues: list[str] = []
        total_score = 0.0
        metric_count = 0

        for metric, value in metrics.items():
            threshold = thresholds.get(metric)
            if threshold is not None and value > threshold:
                issues.append(
                    f"{metric}: {value:.2f} > esik {threshold:.2f}",
                )

            # Anomali kontrolu
            self._check_anomaly(name, metric, value)

            # Skor hesapla (0-1 arasi normalize)
            normalized = max(0.0, min(1.0, 1.0 - value))
            total_score += normalized
            metric_count += 1

        avg_score = (
            round(total_score / metric_count, 3)
            if metric_count > 0 else 0.5
        )

        status = self._score_to_status(avg_score, len(issues))

        report = HealthReport(
            component=name,
            status=status,
            score=avg_score,
            metrics=metrics,
            issues=issues,
        )
        self._reports.append(report)

        if comp:
            comp["last_status"] = status.value
            comp["scan_count"] += 1

        return report

    def full_scan(
        self,
        component_metrics: dict[str, dict[str, float]],
    ) -> dict[str, Any]:
        """Tam sistem taramasi yapar.

        Args:
            component_metrics: Bilesen -> metrikler eslesmesi.

        Returns:
            Tarama sonucu.
        """
        reports: list[HealthReport] = []
        for name, metrics in component_metrics.items():
            report = self.scan_component(name, metrics)
            reports.append(report)

        total_score = sum(r.score for r in reports)
        avg_score = (
            round(total_score / len(reports), 3)
            if reports else 0.5
        )
        overall_status = self._score_to_status(
            avg_score,
            sum(len(r.issues) for r in reports),
        )

        return {
            "overall_status": overall_status.value,
            "overall_score": avg_score,
            "components_scanned": len(reports),
            "total_issues": sum(len(r.issues) for r in reports),
            "reports": reports,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def set_baseline(
        self,
        component: str,
        metrics: dict[str, float],
    ) -> None:
        """Normal metrik degerlerini ayarlar.

        Args:
            component: Bilesen adi.
            metrics: Normal degerler.
        """
        self._baselines[component] = dict(metrics)

    def detect_anomaly(
        self,
        component: str,
        metric: str,
        value: float,
        deviation_threshold: float = 0.3,
    ) -> dict[str, Any] | None:
        """Anomali tespit eder.

        Args:
            component: Bilesen adi.
            metric: Metrik adi.
            value: Mevcut deger.
            deviation_threshold: Sapma esigi.

        Returns:
            Anomali bilgisi veya None.
        """
        baseline = self._baselines.get(component, {}).get(metric)
        if baseline is None:
            return None

        deviation = abs(value - baseline)
        if baseline > 0:
            relative_dev = deviation / baseline
        else:
            relative_dev = deviation

        if relative_dev > deviation_threshold:
            anomaly = {
                "component": component,
                "metric": metric,
                "value": value,
                "baseline": baseline,
                "deviation": round(relative_dev, 3),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._anomalies.append(anomaly)
            return anomaly

        return None

    def get_component_history(
        self,
        name: str,
        limit: int = 10,
    ) -> list[HealthReport]:
        """Bilesen gecmisini getirir.

        Args:
            name: Bilesen adi.
            limit: Maks kayit.

        Returns:
            Rapor listesi.
        """
        history = [r for r in self._reports if r.component == name]
        return history[-limit:]

    def get_unhealthy_components(self) -> list[str]:
        """Sagliksiz bilesenleri getirir.

        Returns:
            Bilesen adi listesi.
        """
        unhealthy = []
        for name, comp in self._components.items():
            if comp["last_status"] in (
                HealthStatus.UNHEALTHY.value,
                HealthStatus.CRITICAL.value,
            ):
                unhealthy.append(name)
        return unhealthy

    def _check_anomaly(
        self,
        component: str,
        metric: str,
        value: float,
    ) -> None:
        """Anomali kontrolu.

        Args:
            component: Bilesen.
            metric: Metrik.
            value: Deger.
        """
        self.detect_anomaly(component, metric, value)

    def _score_to_status(
        self,
        score: float,
        issue_count: int,
    ) -> HealthStatus:
        """Skordan durum belirler.

        Args:
            score: Skor (0-1).
            issue_count: Sorun sayisi.

        Returns:
            HealthStatus.
        """
        if issue_count > 3 or score < 0.2:
            return HealthStatus.CRITICAL
        if issue_count > 1 or score < 0.4:
            return HealthStatus.UNHEALTHY
        if issue_count > 0 or score < 0.7:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    @property
    def component_count(self) -> int:
        """Bilesen sayisi."""
        return len(self._components)

    @property
    def report_count(self) -> int:
        """Rapor sayisi."""
        return len(self._reports)

    @property
    def anomaly_count(self) -> int:
        """Anomali sayisi."""
        return len(self._anomalies)
