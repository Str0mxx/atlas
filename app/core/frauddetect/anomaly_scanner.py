"""ATLAS Anomali Tarayıcı modülü.

Kalıp analizi, istatistiksel tespit,
zaman serisi anomalileri, davranışsal
anomaliler, çok boyutlu analiz.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AnomalyScanner:
    """Anomali tarayıcı.

    Verilerde anomalileri tespit eder.

    Attributes:
        _data: Veri kayıtları.
        _anomalies: Anomali kayıtları.
    """

    def __init__(self) -> None:
        """Tarayıcıyı başlatır."""
        self._data: dict[
            str, list[float]
        ] = {}
        self._anomalies: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "scans_performed": 0,
            "anomalies_found": 0,
        }

        logger.info(
            "AnomalyScanner baslatildi",
        )

    def add_data_point(
        self,
        source: str,
        value: float,
    ) -> dict[str, Any]:
        """Veri noktası ekler.

        Args:
            source: Kaynak.
            value: Değer.

        Returns:
            Ekleme bilgisi.
        """
        if source not in self._data:
            self._data[source] = []
        self._data[source].append(value)

        return {
            "source": source,
            "value": value,
            "data_points": len(
                self._data[source],
            ),
            "added": True,
        }

    def analyze_pattern(
        self,
        source: str,
    ) -> dict[str, Any]:
        """Kalıp analizi yapar.

        Args:
            source: Kaynak.

        Returns:
            Analiz bilgisi.
        """
        values = self._data.get(source, [])
        if len(values) < 5:
            return {
                "source": source,
                "analyzed": False,
                "reason": "Insufficient data",
            }

        avg = sum(values) / len(values)
        std = (
            sum(
                (v - avg) ** 2
                for v in values
            ) / len(values)
        ) ** 0.5

        # Monoton artış/azalış kontrolü
        increases = sum(
            1 for i in range(1, len(values))
            if values[i] > values[i - 1]
        )
        ratio = increases / (
            len(values) - 1
        )

        pattern = (
            "increasing"
            if ratio > 0.75
            else "decreasing"
            if ratio < 0.25
            else "volatile"
            if std > avg * 0.3
            else "stable"
        )

        self._stats[
            "scans_performed"
        ] += 1

        return {
            "source": source,
            "avg": round(avg, 2),
            "std": round(std, 2),
            "pattern": pattern,
            "data_points": len(values),
            "analyzed": True,
        }

    def detect_statistical(
        self,
        source: str,
        value: float,
        sigma: float = 3.0,
    ) -> dict[str, Any]:
        """İstatistiksel anomali tespit eder.

        Args:
            source: Kaynak.
            value: Test değeri.
            sigma: Sigma eşiği.

        Returns:
            Tespit bilgisi.
        """
        values = self._data.get(source, [])
        if len(values) < 3:
            return {
                "source": source,
                "is_anomaly": False,
                "reason": "Insufficient data",
            }

        avg = sum(values) / len(values)
        std = (
            sum(
                (v - avg) ** 2
                for v in values
            ) / len(values)
        ) ** 0.5

        if std == 0:
            is_anomaly = value != avg
        else:
            z_score = abs(value - avg) / std
            is_anomaly = z_score > sigma

        if is_anomaly:
            self._counter += 1
            self._anomalies.append({
                "anomaly_id": (
                    f"anom_{self._counter}"
                ),
                "source": source,
                "type": "statistical",
                "value": value,
                "timestamp": time.time(),
            })
            self._stats[
                "anomalies_found"
            ] += 1

        return {
            "source": source,
            "value": value,
            "avg": round(avg, 2),
            "std": round(std, 2),
            "is_anomaly": is_anomaly,
            "detection_type": "statistical",
        }

    def detect_timeseries(
        self,
        source: str,
        window: int = 5,
    ) -> dict[str, Any]:
        """Zaman serisi anomalisi tespit eder.

        Args:
            source: Kaynak.
            window: Pencere boyutu.

        Returns:
            Tespit bilgisi.
        """
        values = self._data.get(source, [])
        if len(values) < window + 2:
            return {
                "source": source,
                "anomalies": [],
                "detected": False,
            }

        anomaly_indices = []
        for i in range(
            window, len(values),
        ):
            win = values[i - window:i]
            avg = sum(win) / len(win)
            std = (
                sum(
                    (v - avg) ** 2
                    for v in win
                ) / len(win)
            ) ** 0.5
            threshold = avg + 2.5 * (
                std if std > 0 else 1
            )

            if abs(values[i] - avg) > (
                threshold - avg
            ):
                anomaly_indices.append(i)

        self._stats[
            "scans_performed"
        ] += 1

        return {
            "source": source,
            "anomalies": anomaly_indices,
            "anomaly_count": len(
                anomaly_indices,
            ),
            "detected": len(
                anomaly_indices,
            ) > 0,
        }

    def detect_behavioral(
        self,
        entity: str,
        current_behavior: dict[str, float]
        | None = None,
        expected: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Davranışsal anomali tespit eder.

        Args:
            entity: Varlık.
            current_behavior: Mevcut davranış.
            expected: Beklenen davranış.

        Returns:
            Tespit bilgisi.
        """
        current_behavior = (
            current_behavior or {}
        )
        expected = expected or {}

        deviations = []
        for key, cur_val in (
            current_behavior.items()
        ):
            exp_val = expected.get(key, 0)
            if exp_val > 0:
                dev_pct = abs(
                    cur_val - exp_val,
                ) / exp_val * 100
                if dev_pct > 50:
                    deviations.append({
                        "metric": key,
                        "current": cur_val,
                        "expected": exp_val,
                        "deviation_pct": round(
                            dev_pct, 1,
                        ),
                    })

        is_anomaly = len(deviations) > 0

        if is_anomaly:
            self._stats[
                "anomalies_found"
            ] += 1

        return {
            "entity": entity,
            "deviations": deviations,
            "deviation_count": len(
                deviations,
            ),
            "is_anomaly": is_anomaly,
        }

    def scan_multidimensional(
        self,
        source: str,
        dimensions: dict[str, float]
        | None = None,
        thresholds: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Çok boyutlu tarama yapar.

        Args:
            source: Kaynak.
            dimensions: Boyutlar.
            thresholds: Eşikler.

        Returns:
            Tarama bilgisi.
        """
        dimensions = dimensions or {}
        thresholds = thresholds or {}

        violations = []
        for dim, val in dimensions.items():
            thresh = thresholds.get(dim, 100)
            if val > thresh:
                violations.append({
                    "dimension": dim,
                    "value": val,
                    "threshold": thresh,
                })

        risk = (
            "critical"
            if len(violations) >= 3
            else "high"
            if len(violations) >= 2
            else "medium"
            if len(violations) >= 1
            else "low"
        )

        self._stats[
            "scans_performed"
        ] += 1

        return {
            "source": source,
            "violations": violations,
            "violation_count": len(
                violations,
            ),
            "risk": risk,
            "scanned": True,
        }

    @property
    def scan_count(self) -> int:
        """Tarama sayısı."""
        return self._stats[
            "scans_performed"
        ]

    @property
    def anomaly_count(self) -> int:
        """Anomali sayısı."""
        return self._stats[
            "anomalies_found"
        ]
