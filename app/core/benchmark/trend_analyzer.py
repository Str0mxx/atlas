"""ATLAS Benchmark Trend Analizcisi modulu.

Iyilestirme takibi, bozulma tespiti,
mevsimsel kalipler, anomali tespiti, tahmin.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BenchmarkTrendAnalyzer:
    """Benchmark trend analizcisi.

    Metrik trendlerini analiz eder.

    Attributes:
        _trend_data: Trend verileri.
        _anomalies: Anomali kayitlari.
    """

    def __init__(
        self,
        anomaly_threshold: float = 2.0,
    ) -> None:
        """Trend analizcisini baslatir.

        Args:
            anomaly_threshold: Anomali esigi (std sapma carpani).
        """
        self._trend_data: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._anomalies: list[
            dict[str, Any]
        ] = []
        self._anomaly_threshold = anomaly_threshold
        self._stats = {
            "analyses": 0,
            "anomalies": 0,
        }

        logger.info(
            "BenchmarkTrendAnalyzer baslatildi",
        )

    def add_data_point(
        self,
        kpi_id: str,
        value: float,
        timestamp: float | None = None,
    ) -> dict[str, Any]:
        """Veri noktasi ekler.

        Args:
            kpi_id: KPI ID.
            value: Deger.
            timestamp: Zaman damgasi.

        Returns:
            Ekleme bilgisi.
        """
        if kpi_id not in self._trend_data:
            self._trend_data[kpi_id] = []

        self._trend_data[kpi_id].append({
            "value": value,
            "timestamp": timestamp or time.time(),
        })

        return {
            "kpi_id": kpi_id,
            "count": len(self._trend_data[kpi_id]),
            "added": True,
        }

    def analyze_trend(
        self,
        kpi_id: str,
    ) -> dict[str, Any]:
        """Trend analizi yapar.

        Args:
            kpi_id: KPI ID.

        Returns:
            Trend bilgisi.
        """
        data = self._trend_data.get(kpi_id, [])

        if len(data) < 4:
            return {
                "kpi_id": kpi_id,
                "direction": "insufficient",
                "count": len(data),
            }

        self._stats["analyses"] += 1

        mid = len(data) // 2
        first = [d["value"] for d in data[:mid]]
        second = [d["value"] for d in data[mid:]]

        first_avg = sum(first) / len(first)
        second_avg = sum(second) / len(second)

        if first_avg == 0:
            change_pct = (
                100.0
                if second_avg != 0
                else 0.0
            )
        else:
            change_pct = (
                (second_avg - first_avg)
                / abs(first_avg) * 100
            )

        if change_pct > 10:
            direction = "improving"
        elif change_pct < -10:
            direction = "degrading"
        else:
            direction = "stable"

        return {
            "kpi_id": kpi_id,
            "direction": direction,
            "change_pct": round(change_pct, 2),
            "first_avg": round(first_avg, 4),
            "second_avg": round(second_avg, 4),
            "data_points": len(data),
        }

    def detect_degradation(
        self,
        kpi_id: str,
        window: int = 5,
    ) -> dict[str, Any]:
        """Bozulma tespit eder.

        Args:
            kpi_id: KPI ID.
            window: Pencere boyutu.

        Returns:
            Bozulma bilgisi.
        """
        data = self._trend_data.get(kpi_id, [])

        if len(data) < window * 2:
            return {
                "kpi_id": kpi_id,
                "degrading": False,
                "reason": "insufficient_data",
            }

        recent = [
            d["value"]
            for d in data[-window:]
        ]
        previous = [
            d["value"]
            for d in data[-window * 2:-window]
        ]

        recent_avg = sum(recent) / len(recent)
        prev_avg = sum(previous) / len(previous)

        degrading = recent_avg < prev_avg * 0.9

        return {
            "kpi_id": kpi_id,
            "degrading": degrading,
            "recent_avg": round(recent_avg, 4),
            "previous_avg": round(prev_avg, 4),
        }

    def detect_anomaly(
        self,
        kpi_id: str,
        value: float,
    ) -> dict[str, Any]:
        """Anomali tespit eder.

        Args:
            kpi_id: KPI ID.
            value: Deger.

        Returns:
            Anomali bilgisi.
        """
        data = self._trend_data.get(kpi_id, [])
        values = [d["value"] for d in data]

        if len(values) < 5:
            return {
                "kpi_id": kpi_id,
                "is_anomaly": False,
                "reason": "insufficient_data",
            }

        mean = sum(values) / len(values)
        variance = sum(
            (v - mean) ** 2 for v in values
        ) / len(values)
        std = variance ** 0.5

        if std == 0:
            is_anomaly = value != mean
        else:
            z_score = abs(value - mean) / std
            is_anomaly = (
                z_score > self._anomaly_threshold
            )

        if is_anomaly:
            self._anomalies.append({
                "kpi_id": kpi_id,
                "value": value,
                "mean": round(mean, 4),
                "std": round(std, 4),
                "timestamp": time.time(),
            })
            self._stats["anomalies"] += 1

        return {
            "kpi_id": kpi_id,
            "value": value,
            "is_anomaly": is_anomaly,
            "mean": round(mean, 4),
            "std": round(std, 4),
        }

    def forecast(
        self,
        kpi_id: str,
        steps: int = 5,
    ) -> dict[str, Any]:
        """Basit tahmin yapar.

        Args:
            kpi_id: KPI ID.
            steps: Adim sayisi.

        Returns:
            Tahmin bilgisi.
        """
        data = self._trend_data.get(kpi_id, [])

        if len(data) < 3:
            return {
                "kpi_id": kpi_id,
                "forecasted": False,
                "reason": "insufficient_data",
            }

        values = [d["value"] for d in data]
        # Basit dogrusal trend
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum(
            (i - x_mean) * (v - y_mean)
            for i, v in enumerate(values)
        )
        denominator = sum(
            (i - x_mean) ** 2
            for i in range(n)
        )

        slope = (
            numerator / denominator
            if denominator != 0
            else 0
        )
        intercept = y_mean - slope * x_mean

        predictions = [
            round(slope * (n + i) + intercept, 4)
            for i in range(steps)
        ]

        return {
            "kpi_id": kpi_id,
            "forecasted": True,
            "predictions": predictions,
            "slope": round(slope, 4),
            "current_avg": round(y_mean, 4),
        }

    def get_anomalies(
        self,
        kpi_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Anomalileri getirir.

        Args:
            kpi_id: KPI filtresi.
            limit: Limit.

        Returns:
            Anomali listesi.
        """
        anomalies = self._anomalies
        if kpi_id:
            anomalies = [
                a for a in anomalies
                if a["kpi_id"] == kpi_id
            ]
        return list(anomalies[-limit:])

    @property
    def tracked_kpi_count(self) -> int:
        """Izlenen KPI sayisi."""
        return len(self._trend_data)

    @property
    def anomaly_count(self) -> int:
        """Anomali sayisi."""
        return len(self._anomalies)
