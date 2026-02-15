"""ATLAS Anomali Tespiti modulu.

Istatistiksel tespit, ML-tabanli tespit,
temel cizgi ogrenme, uyari uretimi
ve kok neden ipuclari.
"""

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Anomali tespitcisi.

    Metriklerdeki anomalileri tespit eder.

    Attributes:
        _baselines: Temel cizgiler.
        _anomalies: Tespit edilen anomaliler.
    """

    def __init__(
        self,
        sensitivity: float = 2.0,
    ) -> None:
        """Anomali tespitcisini baslatir.

        Args:
            sensitivity: Hassasiyet (std sapma carpani).
        """
        self._baselines: dict[
            str, dict[str, Any]
        ] = {}
        self._anomalies: list[
            dict[str, Any]
        ] = []
        self._sensitivity = sensitivity
        self._data_points: dict[
            str, list[float]
        ] = {}
        self._root_cause_hints: dict[
            str, list[str]
        ] = {}

        logger.info(
            "AnomalyDetector baslatildi: "
            "sensitivity=%.1f",
            sensitivity,
        )

    def add_data_point(
        self,
        metric_name: str,
        value: float,
    ) -> dict[str, Any] | None:
        """Veri noktasi ekler ve anomali kontrol eder.

        Args:
            metric_name: Metrik adi.
            value: Deger.

        Returns:
            Anomali bilgisi veya None.
        """
        if metric_name not in self._data_points:
            self._data_points[metric_name] = []
        self._data_points[metric_name].append(value)

        # Temel cizgi varsa anomali kontrol et
        baseline = self._baselines.get(metric_name)
        if baseline:
            is_anomaly = self._check_statistical(
                value, baseline,
            )
            if is_anomaly:
                anomaly = {
                    "metric": metric_name,
                    "value": value,
                    "baseline_mean": baseline["mean"],
                    "baseline_std": baseline["std"],
                    "deviation": abs(
                        value - baseline["mean"]
                    ),
                    "type": self._classify_anomaly(
                        value, baseline,
                    ),
                    "timestamp": time.time(),
                }
                self._anomalies.append(anomaly)
                return anomaly

        return None

    def learn_baseline(
        self,
        metric_name: str,
        min_points: int = 10,
    ) -> dict[str, Any]:
        """Temel cizgi ogrenir.

        Args:
            metric_name: Metrik adi.
            min_points: Minimum veri noktasi.

        Returns:
            Temel cizgi bilgisi.
        """
        points = self._data_points.get(
            metric_name, [],
        )
        if len(points) < min_points:
            return {
                "status": "insufficient_data",
                "points": len(points),
                "required": min_points,
            }

        mean = sum(points) / len(points)
        variance = sum(
            (x - mean) ** 2 for x in points
        ) / len(points)
        std = math.sqrt(variance)

        self._baselines[metric_name] = {
            "mean": mean,
            "std": std,
            "min": min(points),
            "max": max(points),
            "count": len(points),
            "learned_at": time.time(),
        }

        return {
            "metric": metric_name,
            "mean": round(mean, 4),
            "std": round(std, 4),
            "status": "learned",
        }

    def set_baseline(
        self,
        metric_name: str,
        mean: float,
        std: float,
    ) -> None:
        """Temel cizgi ayarlar.

        Args:
            metric_name: Metrik adi.
            mean: Ortalama.
            std: Standart sapma.
        """
        self._baselines[metric_name] = {
            "mean": mean,
            "std": std,
            "min": mean - 3 * std,
            "max": mean + 3 * std,
            "count": 0,
            "learned_at": time.time(),
        }

    def _check_statistical(
        self,
        value: float,
        baseline: dict[str, Any],
    ) -> bool:
        """Istatistiksel anomali kontrol eder.

        Args:
            value: Deger.
            baseline: Temel cizgi.

        Returns:
            Anomali mi.
        """
        mean = baseline["mean"]
        std = baseline["std"]
        if std == 0:
            return value != mean
        z_score = abs(value - mean) / std
        return z_score > self._sensitivity

    def _classify_anomaly(
        self,
        value: float,
        baseline: dict[str, Any],
    ) -> str:
        """Anomali tipini siniflandirir.

        Args:
            value: Deger.
            baseline: Temel cizgi.

        Returns:
            Anomali tipi.
        """
        mean = baseline["mean"]
        if value > mean:
            return "spike"
        return "drop"

    def add_root_cause_hint(
        self,
        metric_name: str,
        hint: str,
    ) -> None:
        """Kok neden ipucu ekler.

        Args:
            metric_name: Metrik adi.
            hint: Ipucu.
        """
        if metric_name not in self._root_cause_hints:
            self._root_cause_hints[metric_name] = []
        self._root_cause_hints[metric_name].append(
            hint,
        )

    def get_root_cause_hints(
        self,
        metric_name: str,
    ) -> list[str]:
        """Kok neden ipuclarini getirir.

        Args:
            metric_name: Metrik adi.

        Returns:
            Ipucu listesi.
        """
        return list(
            self._root_cause_hints.get(
                metric_name, [],
            ),
        )

    def get_anomalies(
        self,
        metric_name: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Anomalileri getirir.

        Args:
            metric_name: Filtre.
            limit: Limit.

        Returns:
            Anomali listesi.
        """
        anomalies = self._anomalies
        if metric_name:
            anomalies = [
                a for a in anomalies
                if a["metric"] == metric_name
            ]
        return anomalies[-limit:]

    def detect_trend(
        self,
        metric_name: str,
        window: int = 10,
    ) -> dict[str, Any]:
        """Trend tespit eder.

        Args:
            metric_name: Metrik adi.
            window: Pencere boyutu.

        Returns:
            Trend bilgisi.
        """
        points = self._data_points.get(
            metric_name, [],
        )
        if len(points) < window:
            return {
                "trend": "unknown",
                "reason": "insufficient_data",
            }

        recent = points[-window:]
        first_half = recent[:window // 2]
        second_half = recent[window // 2:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(
            second_half,
        )

        diff = avg_second - avg_first
        if abs(diff) < 0.01 * abs(avg_first or 1):
            trend = "stable"
        elif diff > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        return {
            "metric": metric_name,
            "trend": trend,
            "change": round(diff, 4),
            "window": window,
        }

    def clear_anomalies(
        self,
        metric_name: str | None = None,
    ) -> int:
        """Anomalileri temizler.

        Args:
            metric_name: Filtre (None=tumu).

        Returns:
            Temizlenen sayi.
        """
        if metric_name is None:
            count = len(self._anomalies)
            self._anomalies.clear()
            return count

        original = len(self._anomalies)
        self._anomalies = [
            a for a in self._anomalies
            if a["metric"] != metric_name
        ]
        return original - len(self._anomalies)

    @property
    def baseline_count(self) -> int:
        """Temel cizgi sayisi."""
        return len(self._baselines)

    @property
    def anomaly_count(self) -> int:
        """Anomali sayisi."""
        return len(self._anomalies)

    @property
    def metric_count(self) -> int:
        """Izlenen metrik sayisi."""
        return len(self._data_points)
