"""ATLAS Bozulma Tahmincisi modülü.

Performans trendleri, anomali tespiti,
arıza tahmini, erken uyarı,
risk puanlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DegradationPredictor:
    """Bozulma tahmincisi.

    Sistem bozulmalarını önceden tahmin eder.

    Attributes:
        _metrics: Metrik kayıtları.
        _predictions: Tahmin kayıtları.
    """

    def __init__(self) -> None:
        """Tahminciyı başlatır."""
        self._metrics: dict[
            str, list[float]
        ] = {}
        self._predictions: list[
            dict[str, Any]
        ] = []
        self._thresholds: dict[
            str, float
        ] = {}
        self._counter = 0
        self._stats = {
            "predictions_made": 0,
            "anomalies_detected": 0,
        }

        logger.info(
            "DegradationPredictor "
            "baslatildi",
        )

    def record_metric(
        self,
        component: str,
        value: float,
        metric_type: str = "latency",
    ) -> dict[str, Any]:
        """Metrik kaydeder.

        Args:
            component: Bileşen.
            value: Değer.
            metric_type: Metrik tipi.

        Returns:
            Kayıt bilgisi.
        """
        key = f"{component}:{metric_type}"
        if key not in self._metrics:
            self._metrics[key] = []
        self._metrics[key].append(value)

        return {
            "component": component,
            "metric_type": metric_type,
            "value": value,
            "data_points": len(
                self._metrics[key],
            ),
            "recorded": True,
        }

    def analyze_trend(
        self,
        component: str,
        metric_type: str = "latency",
    ) -> dict[str, Any]:
        """Performans trendi analiz eder.

        Args:
            component: Bileşen.
            metric_type: Metrik tipi.

        Returns:
            Trend bilgisi.
        """
        key = f"{component}:{metric_type}"
        values = self._metrics.get(key, [])

        if len(values) < 3:
            return {
                "component": component,
                "analyzed": False,
                "reason": "Insufficient data",
            }

        avg = sum(values) / len(values)
        recent = values[-3:]
        recent_avg = sum(recent) / len(
            recent,
        )

        change_pct = round(
            (recent_avg - avg) / avg * 100,
            1,
        ) if avg > 0 else 0.0

        trend = (
            "degrading"
            if change_pct > 15
            else "improving"
            if change_pct < -15
            else "stable"
        )

        return {
            "component": component,
            "metric_type": metric_type,
            "avg": round(avg, 2),
            "recent_avg": round(
                recent_avg, 2,
            ),
            "change_pct": change_pct,
            "trend": trend,
            "analyzed": True,
        }

    def detect_anomaly(
        self,
        component: str,
        value: float,
        metric_type: str = "latency",
    ) -> dict[str, Any]:
        """Anomali tespit eder.

        Args:
            component: Bileşen.
            value: Değer.
            metric_type: Metrik tipi.

        Returns:
            Anomali bilgisi.
        """
        key = f"{component}:{metric_type}"
        values = self._metrics.get(key, [])

        if len(values) < 3:
            return {
                "component": component,
                "is_anomaly": False,
                "reason": "Insufficient data",
            }

        avg = sum(values) / len(values)
        max_val = max(values)
        threshold = avg + (max_val - avg) * 1.5

        is_anomaly = value > threshold

        if is_anomaly:
            self._stats[
                "anomalies_detected"
            ] += 1

        return {
            "component": component,
            "value": value,
            "threshold": round(
                threshold, 2,
            ),
            "avg": round(avg, 2),
            "is_anomaly": is_anomaly,
            "deviation": round(
                value - avg, 2,
            ),
        }

    def predict_failure(
        self,
        component: str,
        metric_type: str = "latency",
    ) -> dict[str, Any]:
        """Arıza tahmini yapar.

        Args:
            component: Bileşen.
            metric_type: Metrik tipi.

        Returns:
            Tahmin bilgisi.
        """
        trend = self.analyze_trend(
            component, metric_type,
        )
        if not trend.get("analyzed"):
            return {
                "component": component,
                "predicted": False,
            }

        change = trend["change_pct"]
        risk = (
            "critical"
            if change > 50
            else "high"
            if change > 30
            else "medium"
            if change > 15
            else "low"
            if change > 0
            else "none"
        )

        # Tahmini arıza süresi (saat)
        hours_to_failure = (
            round(100 / change, 1)
            if change > 0
            else None
        )

        self._counter += 1
        prediction = {
            "component": component,
            "risk": risk,
            "change_pct": change,
            "hours_to_failure": (
                hours_to_failure
            ),
            "timestamp": time.time(),
        }
        self._predictions.append(prediction)
        self._stats[
            "predictions_made"
        ] += 1

        return {
            "component": component,
            "risk": risk,
            "change_pct": change,
            "hours_to_failure": (
                hours_to_failure
            ),
            "predicted": True,
        }

    def generate_early_warning(
        self,
        component: str,
        metric_type: str = "latency",
    ) -> dict[str, Any]:
        """Erken uyarı üretir.

        Args:
            component: Bileşen.
            metric_type: Metrik tipi.

        Returns:
            Uyarı bilgisi.
        """
        prediction = self.predict_failure(
            component, metric_type,
        )
        if not prediction.get("predicted"):
            return {
                "component": component,
                "warning": False,
            }

        risk = prediction["risk"]
        should_warn = risk in (
            "critical", "high", "medium",
        )

        urgency = (
            "immediate"
            if risk == "critical"
            else "soon"
            if risk == "high"
            else "monitor"
            if risk == "medium"
            else "none"
        )

        return {
            "component": component,
            "risk": risk,
            "urgency": urgency,
            "warning": should_warn,
            "hours_to_failure": prediction[
                "hours_to_failure"
            ],
        }

    def calculate_risk_score(
        self,
        component: str,
    ) -> dict[str, Any]:
        """Risk puanı hesaplar.

        Args:
            component: Bileşen.

        Returns:
            Risk bilgisi.
        """
        # Tüm metrik tipleri için trend
        keys = [
            k for k in self._metrics
            if k.startswith(f"{component}:")
        ]

        if not keys:
            return {
                "component": component,
                "risk_score": 0,
                "calculated": False,
            }

        total_change = 0.0
        count = 0
        for key in keys:
            metric_type = key.split(":")[1]
            trend = self.analyze_trend(
                component, metric_type,
            )
            if trend.get("analyzed"):
                total_change += max(
                    trend["change_pct"], 0,
                )
                count += 1

        avg_change = (
            total_change / count
            if count > 0
            else 0.0
        )
        score = min(
            round(avg_change), 100,
        )

        level = (
            "critical" if score >= 70
            else "high" if score >= 50
            else "medium" if score >= 25
            else "low" if score > 0
            else "none"
        )

        return {
            "component": component,
            "risk_score": score,
            "level": level,
            "metrics_analyzed": count,
            "calculated": True,
        }

    @property
    def prediction_count(self) -> int:
        """Tahmin sayısı."""
        return self._stats[
            "predictions_made"
        ]

    @property
    def anomaly_count(self) -> int:
        """Anomali sayısı."""
        return self._stats[
            "anomalies_detected"
        ]
