"""ATLAS Zayiflik Tespiti modulu.

Basarisiz gorev analizi, eksik yetenek tespiti,
yavas islem belirleme, hata odaklari ve kullanici sikayet kaliplari.
"""

import logging
from typing import Any

from app.models.evolution import (
    ChangeSeverity,
    PerformanceMetric,
    WeaknessReport,
    WeaknessType,
)

logger = logging.getLogger(__name__)

# Hata mesaji -> ciddiyet eslesmesi
_SEVERITY_KEYWORDS: dict[str, ChangeSeverity] = {
    "critical": ChangeSeverity.CRITICAL,
    "fatal": ChangeSeverity.CRITICAL,
    "crash": ChangeSeverity.CRITICAL,
    "security": ChangeSeverity.CRITICAL,
    "timeout": ChangeSeverity.MAJOR,
    "connection": ChangeSeverity.MAJOR,
    "memory": ChangeSeverity.MAJOR,
    "slow": ChangeSeverity.MINOR,
    "warning": ChangeSeverity.MINOR,
    "deprecated": ChangeSeverity.MINOR,
}


class WeaknessDetector:
    """Zayiflik tespit sistemi.

    Performans metriklerinden, hata kayitlarindan ve
    kullanici geri bildirimlerinden zayifliklari tespit eder.

    Attributes:
        _weaknesses: Tespit edilen zayifliklar.
        _complaints: Kullanici sikayetleri.
        _thresholds: Esik degerleri.
    """

    def __init__(
        self,
        failure_rate_threshold: float = 0.2,
        slow_operation_ms: float = 5000.0,
        error_hotspot_count: int = 5,
    ) -> None:
        """Zayiflik tespitcisini baslatir.

        Args:
            failure_rate_threshold: Basarisizlik orani esigi.
            slow_operation_ms: Yavas islem esigi (ms).
            error_hotspot_count: Hata odagi esigi.
        """
        self._weaknesses: list[WeaknessReport] = []
        self._complaints: list[dict[str, Any]] = []
        self._thresholds = {
            "failure_rate": failure_rate_threshold,
            "slow_ms": slow_operation_ms,
            "hotspot_count": error_hotspot_count,
        }

        logger.info(
            "WeaknessDetector baslatildi (failure=%.0f%%, slow=%.0fms)",
            failure_rate_threshold * 100,
            slow_operation_ms,
        )

    def analyze_failures(self, metrics: list[PerformanceMetric]) -> list[WeaknessReport]:
        """Basarisizlik orani yuksek metrikleri analiz eder.

        Args:
            metrics: Performans metrikleri.

        Returns:
            WeaknessReport listesi.
        """
        reports: list[WeaknessReport] = []
        threshold = self._thresholds["failure_rate"]

        for metric in metrics:
            if metric.total_count == 0:
                continue
            if metric.error_rate > threshold:
                severity = ChangeSeverity.MINOR
                if metric.error_rate >= 0.5:
                    severity = ChangeSeverity.CRITICAL
                elif metric.error_rate > 0.3:
                    severity = ChangeSeverity.MAJOR

                report = WeaknessReport(
                    weakness_type=WeaknessType.FAILURE,
                    component=f"{metric.agent_name}:{metric.task_type}",
                    description=f"Basarisizlik orani %{metric.error_rate * 100:.0f} (esik: %{threshold * 100:.0f})",
                    severity=severity,
                    frequency=metric.failure_count,
                    impact_score=min(metric.error_rate * 10, 10.0),
                )
                reports.append(report)
                self._weaknesses.append(report)

        return reports

    def detect_missing_capabilities(self, failed_tasks: list[dict[str, Any]]) -> list[WeaknessReport]:
        """Eksik yetenekleri tespit eder.

        Args:
            failed_tasks: Basarisiz gorevler (task_type, error icermeli).

        Returns:
            WeaknessReport listesi.
        """
        missing: dict[str, int] = {}

        for task in failed_tasks:
            error = task.get("error", "")
            if any(kw in error.lower() for kw in ("not supported", "not implemented", "unknown", "no handler")):
                task_type = task.get("task_type", "unknown")
                missing[task_type] = missing.get(task_type, 0) + 1

        reports: list[WeaknessReport] = []
        for capability, count in missing.items():
            report = WeaknessReport(
                weakness_type=WeaknessType.MISSING_CAPABILITY,
                component=capability,
                description=f"Eksik yetenek: {capability} ({count} kez basarisiz)",
                severity=ChangeSeverity.MAJOR if count > 3 else ChangeSeverity.MINOR,
                frequency=count,
                impact_score=min(count * 2.0, 10.0),
            )
            reports.append(report)
            self._weaknesses.append(report)

        return reports

    def find_slow_operations(self, metrics: list[PerformanceMetric]) -> list[WeaknessReport]:
        """Yavas islemleri bulur.

        Args:
            metrics: Performans metrikleri.

        Returns:
            WeaknessReport listesi.
        """
        reports: list[WeaknessReport] = []
        threshold = self._thresholds["slow_ms"]

        for metric in metrics:
            if metric.avg_response_ms > threshold:
                severity = ChangeSeverity.MINOR
                if metric.avg_response_ms > threshold * 3:
                    severity = ChangeSeverity.MAJOR

                report = WeaknessReport(
                    weakness_type=WeaknessType.SLOW_OPERATION,
                    component=f"{metric.agent_name}:{metric.task_type}",
                    description=f"Ortalama yanit: {metric.avg_response_ms:.0f}ms (esik: {threshold:.0f}ms)",
                    severity=severity,
                    frequency=metric.total_count,
                    impact_score=min((metric.avg_response_ms / threshold) * 3, 10.0),
                )
                reports.append(report)
                self._weaknesses.append(report)

        return reports

    def find_error_hotspots(self, error_patterns: list[dict[str, Any]]) -> list[WeaknessReport]:
        """Hata odaklarini bulur.

        Args:
            error_patterns: Hata kaliplari (pattern, count icermeli).

        Returns:
            WeaknessReport listesi.
        """
        reports: list[WeaknessReport] = []
        threshold = self._thresholds["hotspot_count"]

        for ep in error_patterns:
            count = ep.get("count", 0)
            if count >= threshold:
                pattern = ep.get("pattern", "")
                severity = self._classify_error_severity(pattern)

                report = WeaknessReport(
                    weakness_type=WeaknessType.ERROR_HOTSPOT,
                    component=pattern,
                    description=f"Hata odagi: {count} kez tekrarlandi",
                    severity=severity,
                    frequency=count,
                    impact_score=min(count * 1.5, 10.0),
                    examples=[pattern],
                )
                reports.append(report)
                self._weaknesses.append(report)

        return reports

    def record_complaint(self, user: str, complaint: str, component: str = "") -> WeaknessReport:
        """Kullanici sikayetini kaydeder.

        Args:
            user: Kullanici adi.
            complaint: Sikayet metni.
            component: Ilgili bilesen.

        Returns:
            WeaknessReport nesnesi.
        """
        self._complaints.append({
            "user": user,
            "complaint": complaint,
            "component": component,
        })

        report = WeaknessReport(
            weakness_type=WeaknessType.USER_COMPLAINT,
            component=component or "general",
            description=f"Kullanici sikayeti: {complaint}",
            severity=ChangeSeverity.MAJOR,
            frequency=1,
            impact_score=5.0,
            examples=[f"{user}: {complaint}"],
        )
        self._weaknesses.append(report)
        return report

    def analyze_complaint_patterns(self, min_count: int = 2) -> list[dict[str, Any]]:
        """Sikayet kaliplarini analiz eder.

        Args:
            min_count: Minimum tekrar sayisi.

        Returns:
            Kalip listesi.
        """
        components: dict[str, int] = {}
        for c in self._complaints:
            comp = c.get("component", "general")
            components[comp] = components.get(comp, 0) + 1

        return [
            {"component": comp, "count": count}
            for comp, count in sorted(components.items(), key=lambda x: x[1], reverse=True)
            if count >= min_count
        ]

    def get_all_weaknesses(self, min_impact: float = 0.0) -> list[WeaknessReport]:
        """Tum zayifliklari getirir.

        Args:
            min_impact: Minimum etki puani.

        Returns:
            WeaknessReport listesi.
        """
        filtered = [w for w in self._weaknesses if w.impact_score >= min_impact]
        filtered.sort(key=lambda w: w.impact_score, reverse=True)
        return filtered

    def run_full_analysis(
        self,
        metrics: list[PerformanceMetric],
        error_patterns: list[dict[str, Any]] | None = None,
        failed_tasks: list[dict[str, Any]] | None = None,
    ) -> list[WeaknessReport]:
        """Tam analiz calistirir.

        Args:
            metrics: Performans metrikleri.
            error_patterns: Hata kaliplari.
            failed_tasks: Basarisiz gorevler.

        Returns:
            Tum zayifliklar.
        """
        results: list[WeaknessReport] = []
        results.extend(self.analyze_failures(metrics))
        results.extend(self.find_slow_operations(metrics))

        if error_patterns:
            results.extend(self.find_error_hotspots(error_patterns))
        if failed_tasks:
            results.extend(self.detect_missing_capabilities(failed_tasks))

        results.sort(key=lambda w: w.impact_score, reverse=True)
        return results

    def _classify_error_severity(self, error_text: str) -> ChangeSeverity:
        """Hata metninden ciddiyet belirler."""
        lower = error_text.lower()
        for keyword, severity in _SEVERITY_KEYWORDS.items():
            if keyword in lower:
                return severity
        return ChangeSeverity.MINOR

    @property
    def weakness_count(self) -> int:
        """Zayiflik sayisi."""
        return len(self._weaknesses)

    @property
    def complaint_count(self) -> int:
        """Sikayet sayisi."""
        return len(self._complaints)
