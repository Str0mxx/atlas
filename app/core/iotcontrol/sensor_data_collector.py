"""ATLAS Sensör Veri Toplayıcı modülü.

Veri toplama, akış işleme,
toplama, anomali tespiti,
depolama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SensorDataCollector:
    """Sensör veri toplayıcı.

    Sensör verilerini toplar ve işler.

    Attributes:
        _readings: Okuma kayıtları.
        _aggregated: Toplu veriler.
    """

    def __init__(self) -> None:
        """Toplayıcıyı başlatır."""
        self._readings: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._aggregated: dict[
            str, dict[str, Any]
        ] = {}
        self._stored: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "readings_collected": 0,
            "anomalies_detected": 0,
        }

        logger.info(
            "SensorDataCollector "
            "baslatildi",
        )

    def collect_data(
        self,
        device_id: str,
        sensor_type: str = "temperature",
        value: float = 0.0,
        unit: str = "",
    ) -> dict[str, Any]:
        """Veri toplar.

        Args:
            device_id: Cihaz kimliği.
            sensor_type: Sensör tipi.
            value: Değer.
            unit: Birim.

        Returns:
            Toplama bilgisi.
        """
        self._counter += 1
        rid = f"read_{self._counter}"

        key = f"{device_id}_{sensor_type}"
        if key not in self._readings:
            self._readings[key] = []

        reading = {
            "reading_id": rid,
            "device_id": device_id,
            "sensor_type": sensor_type,
            "value": value,
            "unit": unit,
            "timestamp": time.time(),
        }
        self._readings[key].append(reading)
        self._stats[
            "readings_collected"
        ] += 1

        return {
            "reading_id": rid,
            "device_id": device_id,
            "sensor_type": sensor_type,
            "value": value,
            "collected": True,
        }

    def process_stream(
        self,
        device_id: str,
        sensor_type: str = "temperature",
        window_size: int = 10,
    ) -> dict[str, Any]:
        """Akış işleme yapar.

        Args:
            device_id: Cihaz kimliği.
            sensor_type: Sensör tipi.
            window_size: Pencere boyutu.

        Returns:
            İşleme bilgisi.
        """
        key = f"{device_id}_{sensor_type}"
        readings = self._readings.get(
            key, [],
        )

        window = readings[-window_size:]
        if not window:
            return {
                "device_id": device_id,
                "data_points": 0,
                "processed": True,
            }

        values = [
            r["value"] for r in window
        ]
        avg = sum(values) / len(values)
        latest = values[-1]

        return {
            "device_id": device_id,
            "sensor_type": sensor_type,
            "data_points": len(window),
            "avg_value": round(avg, 2),
            "latest_value": latest,
            "processed": True,
        }

    def aggregate(
        self,
        device_id: str,
        sensor_type: str = "temperature",
    ) -> dict[str, Any]:
        """Veri toplar.

        Args:
            device_id: Cihaz kimliği.
            sensor_type: Sensör tipi.

        Returns:
            Toplam bilgisi.
        """
        key = f"{device_id}_{sensor_type}"
        readings = self._readings.get(
            key, [],
        )

        if not readings:
            return {
                "device_id": device_id,
                "count": 0,
                "aggregated": True,
            }

        values = [
            r["value"] for r in readings
        ]
        result = {
            "device_id": device_id,
            "sensor_type": sensor_type,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": round(
                sum(values) / len(values),
                2,
            ),
            "sum": round(sum(values), 2),
            "aggregated": True,
        }

        self._aggregated[key] = result
        return result

    def detect_anomaly(
        self,
        device_id: str,
        sensor_type: str = "temperature",
        value: float = 0.0,
    ) -> dict[str, Any]:
        """Anomali tespiti yapar.

        Args:
            device_id: Cihaz kimliği.
            sensor_type: Sensör tipi.
            value: Kontrol değeri.

        Returns:
            Tespit bilgisi.
        """
        key = f"{device_id}_{sensor_type}"
        readings = self._readings.get(
            key, [],
        )

        if len(readings) < 3:
            return {
                "is_anomaly": False,
                "reason": "insufficient_data",
                "detected": True,
            }

        values = [
            r["value"] for r in readings
        ]
        avg = sum(values) / len(values)
        std = (
            sum(
                (v - avg) ** 2
                for v in values
            )
            / len(values)
        ) ** 0.5

        z_score = (
            abs(value - avg) / std
            if std > 0
            else 0
        )
        is_anomaly = z_score > 2.0

        if is_anomaly:
            self._stats[
                "anomalies_detected"
            ] += 1

        return {
            "device_id": device_id,
            "value": value,
            "avg": round(avg, 2),
            "z_score": round(z_score, 2),
            "is_anomaly": is_anomaly,
            "detected": True,
        }

    def store_data(
        self,
        device_id: str,
        sensor_type: str = "temperature",
    ) -> dict[str, Any]:
        """Veri depolar.

        Args:
            device_id: Cihaz kimliği.
            sensor_type: Sensör tipi.

        Returns:
            Depolama bilgisi.
        """
        key = f"{device_id}_{sensor_type}"
        readings = self._readings.get(
            key, [],
        )

        for r in readings:
            self._stored.append(r)

        return {
            "device_id": device_id,
            "records_stored": len(readings),
            "stored": True,
        }

    @property
    def reading_count(self) -> int:
        """Okuma sayısı."""
        return self._stats[
            "readings_collected"
        ]

    @property
    def anomaly_count(self) -> int:
        """Anomali sayısı."""
        return self._stats[
            "anomalies_detected"
        ]
