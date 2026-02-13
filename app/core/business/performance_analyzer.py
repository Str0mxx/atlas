"""ATLAS Performans Analiz modulu.

KPI takibi, hedef-gercek karsilastirmasi, trend tespiti,
anomali algilama ve rapor uretimi islemleri.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any

from app.models.business import (
    Anomaly,
    AnomalySeverity,
    KPIDataPoint,
    KPIDefinition,
    KPIDirection,
    PerformanceReport,
)

logger = logging.getLogger(__name__)

# Anomali standart sapma esikleri
_ANOMALY_SIGMA_THRESHOLDS = {
    AnomalySeverity.LOW: 1.5,
    AnomalySeverity.MEDIUM: 2.0,
    AnomalySeverity.HIGH: 2.5,
    AnomalySeverity.CRITICAL: 3.0,
}


class PerformanceAnalyzer:
    """Performans analiz sistemi.

    KPI'lari tanimlar ve takip eder, hedeflere karsi
    gercek degerleri karsilastirir, trendleri tespit eder,
    anomalileri algilar ve raporlar uretir.

    Attributes:
        _kpis: KPI tanimlari (id -> KPIDefinition).
        _data_points: KPI veri noktalari (kpi_id -> [KPIDataPoint]).
        _anomalies: Tespit edilen anomaliler.
        _reports: Uretilen raporlar (id -> PerformanceReport).
    """

    def __init__(self) -> None:
        """Performans analiz sistemini baslatir."""
        self._kpis: dict[str, KPIDefinition] = {}
        self._data_points: dict[str, list[KPIDataPoint]] = {}
        self._anomalies: list[Anomaly] = []
        self._reports: dict[str, PerformanceReport] = {}

        logger.info("PerformanceAnalyzer baslatildi")

    def define_kpi(
        self,
        name: str,
        unit: str = "",
        direction: KPIDirection = KPIDirection.HIGHER_IS_BETTER,
        target_value: float = 0.0,
        warning_threshold: float | None = None,
        critical_threshold: float | None = None,
        description: str = "",
    ) -> KPIDefinition:
        """Yeni KPI tanimlar.

        Args:
            name: KPI adi.
            unit: Birim.
            direction: KPI yonu.
            target_value: Hedef deger.
            warning_threshold: Uyari esigi.
            critical_threshold: Kritik esik.
            description: KPI aciklamasi.

        Returns:
            Olusturulan KPIDefinition nesnesi.
        """
        kpi = KPIDefinition(
            name=name,
            unit=unit,
            direction=direction,
            target_value=target_value,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            description=description,
        )
        self._kpis[kpi.id] = kpi
        self._data_points[kpi.id] = []
        logger.info("KPI tanimlandi: %s (hedef=%.2f %s)", name, target_value, unit)
        return kpi

    def record_value(self, kpi_id: str, value: float, context: dict[str, Any] | None = None) -> KPIDataPoint | None:
        """KPI degeri kaydeder.

        Args:
            kpi_id: KPI ID.
            value: Olculen deger.
            context: Baglamsal bilgi.

        Returns:
            Olusturulan KPIDataPoint veya None (KPI bulunamazsa).
        """
        if kpi_id not in self._kpis:
            return None

        dp = KPIDataPoint(
            kpi_id=kpi_id,
            value=value,
            context=context or {},
        )
        self._data_points[kpi_id].append(dp)
        return dp

    def get_latest_value(self, kpi_id: str) -> float | None:
        """KPI son degerini getirir.

        Args:
            kpi_id: KPI ID.

        Returns:
            Son olculen deger veya None.
        """
        points = self._data_points.get(kpi_id, [])
        if not points:
            return None
        return points[-1].value

    def compare_goal_vs_actual(self, kpi_id: str) -> dict[str, Any]:
        """Hedef ile gercek degeri karsilastirir.

        Args:
            kpi_id: KPI ID.

        Returns:
            Karsilastirma sonucu:
            - kpi_name: KPI adi
            - target: Hedef deger
            - actual: Gercek deger
            - gap: Fark
            - gap_pct: Fark yuzdesi
            - on_track: Hedefe uygun mu
        """
        kpi = self._kpis.get(kpi_id)
        if not kpi:
            return {}

        actual = self.get_latest_value(kpi_id)
        if actual is None:
            return {"kpi_name": kpi.name, "target": kpi.target_value, "actual": None, "on_track": False}

        gap = actual - kpi.target_value
        gap_pct = (gap / kpi.target_value * 100) if kpi.target_value != 0 else 0.0

        if kpi.direction == KPIDirection.HIGHER_IS_BETTER:
            on_track = actual >= kpi.target_value
        elif kpi.direction == KPIDirection.LOWER_IS_BETTER:
            on_track = actual <= kpi.target_value
        else:
            on_track = abs(gap) <= abs(kpi.target_value * 0.1)

        return {
            "kpi_name": kpi.name,
            "target": kpi.target_value,
            "actual": actual,
            "gap": gap,
            "gap_pct": gap_pct,
            "on_track": on_track,
        }

    def detect_trend(self, kpi_id: str, window: int = 5) -> str:
        """KPI verilerinde trend tespit eder.

        Son n veri noktasindan trend yonunu belirler.

        Args:
            kpi_id: KPI ID.
            window: Analiz penceresi (veri noktasi sayisi).

        Returns:
            Trend yonu: 'increasing', 'decreasing' veya 'stable'.
        """
        points = self._data_points.get(kpi_id, [])
        if len(points) < 2:
            return "stable"

        recent = [p.value for p in points[-window:]]
        if len(recent) < 2:
            return "stable"

        # Basit regresyon egimi
        n = len(recent)
        x_mean = (n - 1) / 2.0
        y_mean = sum(recent) / n
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(recent))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0.0

        # Normalize et
        threshold = abs(y_mean) * 0.02 if y_mean != 0 else 0.01
        if slope > threshold:
            return "increasing"
        elif slope < -threshold:
            return "decreasing"
        return "stable"

    def detect_anomalies(self, kpi_id: str, window: int = 10) -> list[Anomaly]:
        """KPI verilerinde anomali tespit eder.

        Z-score yontemiyle son degerin istatistiksel olarak
        normal araliktan ne kadar saptigini olcer.

        Args:
            kpi_id: KPI ID.
            window: Analiz penceresi.

        Returns:
            Tespit edilen anomaliler listesi.
        """
        points = self._data_points.get(kpi_id, [])
        if len(points) < 3:
            return []

        recent_values = [p.value for p in points[-window:]]
        mean = sum(recent_values) / len(recent_values)
        variance = sum((v - mean) ** 2 for v in recent_values) / len(recent_values)
        std_dev = math.sqrt(variance) if variance > 0 else 0.001

        last_value = recent_values[-1]
        z_score = abs(last_value - mean) / std_dev
        deviation_pct = ((last_value - mean) / mean * 100) if mean != 0 else 0.0

        found: list[Anomaly] = []
        # En yuksek siiddetten baslayarak kontrol et
        for severity in [AnomalySeverity.CRITICAL, AnomalySeverity.HIGH, AnomalySeverity.MEDIUM, AnomalySeverity.LOW]:
            threshold = _ANOMALY_SIGMA_THRESHOLDS[severity]
            if z_score >= threshold:
                anomaly = Anomaly(
                    kpi_id=kpi_id,
                    severity=severity,
                    expected_value=mean,
                    actual_value=last_value,
                    deviation_pct=deviation_pct,
                    description=f"{self._kpis.get(kpi_id, KPIDefinition(name='?')).name}: "
                                f"z-score={z_score:.2f} ({severity.value})",
                )
                found.append(anomaly)
                self._anomalies.append(anomaly)
                break  # En yuksek uygun severity'yi al

        if found:
            logger.warning("Anomali tespit edildi: kpi=%s, z=%.2f", kpi_id[:8], z_score)
        return found

    def generate_report(
        self,
        strategy_id: str = "",
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> PerformanceReport:
        """Performans raporu olusturur.

        Tum KPI sonuclarini, hedef ilerlemelerini ve
        anomalileri iceren kapsamli rapor uretir.

        Args:
            strategy_id: Iliskili strateji ID.
            period_start: Donem baslangici.
            period_end: Donem bitisi.

        Returns:
            Olusturulan PerformanceReport nesnesi.
        """
        kpi_results: dict[str, float] = {}
        goal_progress: dict[str, float] = {}

        for kpi_id, kpi in self._kpis.items():
            latest = self.get_latest_value(kpi_id)
            if latest is not None:
                kpi_results[kpi.name] = latest
                if kpi.target_value != 0:
                    goal_progress[kpi.name] = (latest / kpi.target_value) * 100

        # Anomali ozetini olustur
        anomaly_count = len(self._anomalies)
        on_track_count = sum(1 for k in self._kpis if self.compare_goal_vs_actual(k).get("on_track", False))

        summary = (
            f"{len(self._kpis)} KPI izleniyor. "
            f"{on_track_count}/{len(self._kpis)} hedefe uygun. "
            f"{anomaly_count} anomali tespit edildi."
        )

        report = PerformanceReport(
            strategy_id=strategy_id,
            period_start=period_start,
            period_end=period_end,
            kpi_results=kpi_results,
            goal_progress=goal_progress,
            anomalies=list(self._anomalies),
            summary=summary,
        )
        self._reports[report.id] = report
        logger.info("Performans raporu olusturuldu: %s", report.id[:8])
        return report

    def get_kpi(self, kpi_id: str) -> KPIDefinition | None:
        """KPI tanimi getirir.

        Args:
            kpi_id: KPI ID.

        Returns:
            KPIDefinition nesnesi veya None.
        """
        return self._kpis.get(kpi_id)

    @property
    def kpi_count(self) -> int:
        """Toplam KPI sayisi."""
        return len(self._kpis)

    @property
    def anomaly_count(self) -> int:
        """Toplam anomali sayisi."""
        return len(self._anomalies)
