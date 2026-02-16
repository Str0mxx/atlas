"""ATLAS Kriz Tespitçisi modülü.

Anomali tespiti, eşik izleme,
kalıp tanıma, çoklu sinyal birleştirme,
erken uyarı.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CrisisMgrDetector:
    """Kriz tespitçisi.

    Kriz durumlarını tespit eder.

    Attributes:
        _thresholds: Eşik kayıtları.
        _signals: Sinyal kayıtları.
    """

    def __init__(self) -> None:
        """Tespitçiyi başlatır."""
        self._thresholds: dict[
            str, dict[str, Any]
        ] = {}
        self._signals: list[
            dict[str, Any]
        ] = []
        self._patterns: list[
            dict[str, Any]
        ] = []
        self._warnings: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "anomalies_detected": 0,
            "warnings_issued": 0,
        }

        logger.info(
            "CrisisMgrDetector baslatildi",
        )

    def detect_anomaly(
        self,
        metric_name: str,
        current_value: float,
        baseline: float = 0.0,
        std_dev: float = 1.0,
        sensitivity: float = 2.0,
    ) -> dict[str, Any]:
        """Anomali tespit eder.

        Args:
            metric_name: Metrik adı.
            current_value: Güncel değer.
            baseline: Taban değer.
            std_dev: Standart sapma.
            sensitivity: Hassasiyet.

        Returns:
            Tespit bilgisi.
        """
        deviation = abs(
            current_value - baseline
        )
        z_score = (
            deviation
            / max(std_dev, 0.001)
        )
        is_anomaly = z_score > sensitivity

        if is_anomaly:
            self._stats[
                "anomalies_detected"
            ] += 1

        severity = (
            "critical"
            if z_score > sensitivity * 2
            else "high"
            if z_score > sensitivity * 1.5
            else "moderate"
            if is_anomaly
            else "low"
        )

        return {
            "metric": metric_name,
            "z_score": round(z_score, 2),
            "is_anomaly": is_anomaly,
            "severity": severity,
            "detected": True,
        }

    def monitor_threshold(
        self,
        metric_name: str,
        value: float,
        warn_threshold: float = 0.0,
        critical_threshold: float = 0.0,
        direction: str = "above",
    ) -> dict[str, Any]:
        """Eşik izler.

        Args:
            metric_name: Metrik adı.
            value: Değer.
            warn_threshold: Uyarı eşiği.
            critical_threshold: Kritik eşik.
            direction: Yön (above/below).

        Returns:
            İzleme bilgisi.
        """
        self._thresholds[
            metric_name
        ] = {
            "warn": warn_threshold,
            "critical": critical_threshold,
            "direction": direction,
        }

        if direction == "above":
            is_critical = (
                value >= critical_threshold
            )
            is_warning = (
                value >= warn_threshold
                and not is_critical
            )
        else:
            is_critical = (
                value <= critical_threshold
            )
            is_warning = (
                value <= warn_threshold
                and not is_critical
            )

        status = (
            "critical"
            if is_critical
            else "warning"
            if is_warning
            else "normal"
        )

        return {
            "metric": metric_name,
            "value": value,
            "status": status,
            "monitored": True,
        }

    def recognize_pattern(
        self,
        events: list[dict[str, Any]],
        pattern_type: str = "spike",
    ) -> dict[str, Any]:
        """Kalıp tanır.

        Args:
            events: Olay listesi.
            pattern_type: Kalıp tipi.

        Returns:
            Tanıma bilgisi.
        """
        if not events:
            return {
                "pattern": pattern_type,
                "matched": False,
            }

        values = [
            e.get("value", 0)
            for e in events
        ]

        matched = False
        if pattern_type == "spike":
            if len(values) >= 2:
                last = values[-1]
                avg = (
                    sum(values[:-1])
                    / max(
                        len(values) - 1, 1,
                    )
                )
                matched = (
                    last > avg * 2
                )
        elif pattern_type == "trend_up":
            if len(values) >= 3:
                matched = all(
                    values[i] < values[i + 1]
                    for i in range(
                        len(values) - 1,
                    )
                )
        elif pattern_type == "sustained":
            if len(values) >= 3:
                matched = all(
                    v > 0 for v in values[-3:]
                )

        if matched:
            self._patterns.append({
                "pattern": pattern_type,
                "event_count": len(events),
                "timestamp": time.time(),
            })

        return {
            "pattern": pattern_type,
            "matched": matched,
            "event_count": len(events),
            "recognized": True,
        }

    def fuse_signals(
        self,
        signals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Çoklu sinyal birleştirir.

        Args:
            signals: Sinyal listesi.

        Returns:
            Birleştirme bilgisi.
        """
        if not signals:
            return {
                "crisis_level": "low",
                "signal_count": 0,
                "fused": True,
            }

        severities = {
            "critical": 4,
            "high": 3,
            "moderate": 2,
            "low": 1,
        }

        total_score = sum(
            severities.get(
                s.get("severity", "low"),
                1,
            )
            for s in signals
        )
        avg_score = (
            total_score / len(signals)
        )

        crisis_level = (
            "critical"
            if avg_score >= 3.5
            else "high"
            if avg_score >= 2.5
            else "moderate"
            if avg_score >= 1.5
            else "low"
        )

        for s in signals:
            self._signals.append(s)

        return {
            "crisis_level": crisis_level,
            "avg_score": round(
                avg_score, 2,
            ),
            "signal_count": len(signals),
            "fused": True,
        }

    def issue_early_warning(
        self,
        crisis_type: str,
        confidence: float = 0.0,
        message: str = "",
    ) -> dict[str, Any]:
        """Erken uyarı verir.

        Args:
            crisis_type: Kriz tipi.
            confidence: Güven düzeyi.
            message: Mesaj.

        Returns:
            Uyarı bilgisi.
        """
        self._counter += 1
        wid = f"wrn_{self._counter}"

        self._warnings.append({
            "warning_id": wid,
            "crisis_type": crisis_type,
            "confidence": confidence,
            "message": message,
            "timestamp": time.time(),
        })

        self._stats[
            "warnings_issued"
        ] += 1

        return {
            "warning_id": wid,
            "crisis_type": crisis_type,
            "confidence": confidence,
            "issued": True,
        }

    @property
    def anomaly_count(self) -> int:
        """Anomali sayısı."""
        return self._stats[
            "anomalies_detected"
        ]

    @property
    def warning_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats[
            "warnings_issued"
        ]
