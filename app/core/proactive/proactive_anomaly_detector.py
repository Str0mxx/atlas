"""ATLAS Proaktif Anomali Dedektörü modülü.

Bazal öğrenme, sapma tespiti,
şiddet sınıflandırma, kök neden ipuçları,
uyarı üretimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProactiveAnomalyDetector:
    """Proaktif anomali dedektörü.

    Metriklerdeki anormallikleri tespit eder.

    Attributes:
        _baselines: Öğrenilmiş bazal değerler.
        _anomalies: Tespit edilen anomaliler.
        _alerts: Üretilen uyarılar.
    """

    def __init__(
        self,
        sensitivity: float = 2.0,
    ) -> None:
        """Dedektörü başlatır.

        Args:
            sensitivity: Hassasiyet çarpanı.
        """
        self._baselines: dict[
            str, dict[str, Any]
        ] = {}
        self._anomalies: list[
            dict[str, Any]
        ] = []
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._sensitivity = sensitivity
        self._counter = 0
        self._stats = {
            "anomalies_detected": 0,
            "alerts_generated": 0,
            "baselines_learned": 0,
        }

        logger.info(
            "ProactiveAnomalyDetector "
            "baslatildi",
        )

    def learn_baseline(
        self,
        metric: str,
        values: list[float],
    ) -> dict[str, Any]:
        """Bazal değer öğrenir.

        Args:
            metric: Metrik adı.
            values: Değer listesi.

        Returns:
            Bazal bilgisi.
        """
        if not values:
            return {"error": "empty_values"}

        n = len(values)
        mean = sum(values) / n
        variance = (
            sum((v - mean) ** 2 for v in values)
            / n
        )
        std_dev = variance ** 0.5

        baseline = {
            "metric": metric,
            "mean": round(mean, 4),
            "std_dev": round(std_dev, 4),
            "min": min(values),
            "max": max(values),
            "sample_count": n,
            "learned_at": time.time(),
        }
        self._baselines[metric] = baseline
        self._stats["baselines_learned"] += 1

        return baseline

    def detect_anomaly(
        self,
        metric: str,
        value: float,
    ) -> dict[str, Any]:
        """Anomali tespit eder.

        Args:
            metric: Metrik adı.
            value: Güncel değer.

        Returns:
            Tespit bilgisi.
        """
        baseline = self._baselines.get(metric)
        if not baseline:
            return {
                "anomaly": False,
                "reason": "no_baseline",
            }

        mean = baseline["mean"]
        std_dev = baseline["std_dev"]
        threshold = self._sensitivity

        if std_dev == 0:
            is_anomaly = value != mean
            deviation = (
                abs(value - mean) if is_anomaly
                else 0.0
            )
        else:
            deviation = abs(value - mean) / std_dev
            is_anomaly = deviation > threshold

        severity = self._classify_severity(
            deviation,
        )

        result = {
            "metric": metric,
            "value": value,
            "anomaly": is_anomaly,
            "deviation": round(deviation, 4),
            "severity": severity,
            "baseline_mean": mean,
            "baseline_std": std_dev,
            "timestamp": time.time(),
        }

        if is_anomaly:
            self._counter += 1
            result["anomaly_id"] = (
                f"anom_{self._counter}"
            )
            self._anomalies.append(result)
            self._stats["anomalies_detected"] += 1

            # Kök neden ipucu
            result["root_cause_hints"] = (
                self._get_root_cause_hints(
                    metric, value, mean,
                )
            )

        return result

    def _classify_severity(
        self,
        deviation: float,
    ) -> str:
        """Şiddet sınıflandırır.

        Args:
            deviation: Sapma miktarı.

        Returns:
            Şiddet seviyesi.
        """
        if deviation > 5.0:
            return "critical"
        if deviation > 3.0:
            return "warning"
        if deviation > 2.0:
            return "notice"
        if deviation > 1.0:
            return "info"
        return "normal"

    def _get_root_cause_hints(
        self,
        metric: str,
        value: float,
        mean: float,
    ) -> list[str]:
        """Kök neden ipuçları üretir.

        Args:
            metric: Metrik adı.
            value: Güncel değer.
            mean: Ortalama değer.

        Returns:
            İpucu listesi.
        """
        hints = []
        direction = (
            "above" if value > mean else "below"
        )
        hints.append(
            f"Value is {direction} baseline "
            f"mean ({mean})",
        )

        if value > mean * 2:
            hints.append(
                "Possible spike or "
                "sudden increase",
            )
        elif value < mean * 0.5:
            hints.append(
                "Possible drop or "
                "service degradation",
            )

        if "error" in metric.lower():
            hints.append(
                "Check error logs for details",
            )
        if "latency" in metric.lower():
            hints.append(
                "Check network or "
                "service performance",
            )
        if "cpu" in metric.lower():
            hints.append(
                "Check running processes",
            )
        if "memory" in metric.lower():
            hints.append(
                "Check for memory leaks",
            )

        return hints

    def generate_alert(
        self,
        anomaly_id: str,
        channel: str = "log",
    ) -> dict[str, Any]:
        """Uyarı üretir.

        Args:
            anomaly_id: Anomali ID.
            channel: Bildirim kanalı.

        Returns:
            Uyarı bilgisi.
        """
        anomaly = None
        for a in self._anomalies:
            if a.get("anomaly_id") == anomaly_id:
                anomaly = a
                break

        if not anomaly:
            return {"error": "anomaly_not_found"}

        alert = {
            "anomaly_id": anomaly_id,
            "metric": anomaly["metric"],
            "severity": anomaly["severity"],
            "channel": channel,
            "message": (
                f"Anomaly detected in "
                f"{anomaly['metric']}: "
                f"value={anomaly['value']}, "
                f"deviation={anomaly['deviation']}"
            ),
            "generated_at": time.time(),
        }
        self._alerts.append(alert)
        self._stats["alerts_generated"] += 1

        return alert

    def batch_detect(
        self,
        metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Toplu anomali tespiti yapar.

        Args:
            metrics: Metrik-değer çiftleri.

        Returns:
            Toplu tespit bilgisi.
        """
        results = {}
        anomalies_found = 0

        for metric, value in metrics.items():
            result = self.detect_anomaly(
                metric, value,
            )
            results[metric] = result
            if result.get("anomaly"):
                anomalies_found += 1

        return {
            "results": results,
            "metrics_checked": len(metrics),
            "anomalies_found": anomalies_found,
        }

    def get_anomalies(
        self,
        severity: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Anomalileri getirir.

        Args:
            severity: Şiddet filtresi.
            limit: Maks kayıt.

        Returns:
            Anomali listesi.
        """
        results = self._anomalies
        if severity:
            results = [
                a for a in results
                if a.get("severity") == severity
            ]
        return list(results[-limit:])

    @property
    def anomaly_count(self) -> int:
        """Anomali sayısı."""
        return self._stats["anomalies_detected"]

    @property
    def baseline_count(self) -> int:
        """Bazal sayısı."""
        return len(self._baselines)

    @property
    def alert_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats["alerts_generated"]
