"""ATLAS Konum Geçmişi modülü.

Geçmiş depolama, yol görselleştirme,
bekleme tespiti, örüntü analizi,
gizlilik kontrolleri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LocationHistory:
    """Konum geçmişi.

    Konum geçmişini depolar ve analiz eder.

    Attributes:
        _records: Geçmiş kayıtları.
        _privacy: Gizlilik ayarları.
    """

    def __init__(self) -> None:
        """Geçmişi başlatır."""
        self._records: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._privacy: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "records_stored": 0,
            "dwells_detected": 0,
        }

        logger.info(
            "LocationHistory baslatildi",
        )

    def store_location(
        self,
        device_id: str,
        lat: float,
        lon: float,
        accuracy_m: float = 10.0,
    ) -> dict[str, Any]:
        """Konum kaydı depolar.

        Args:
            device_id: Cihaz kimliği.
            lat: Enlem.
            lon: Boylam.
            accuracy_m: Doğruluk.

        Returns:
            Depolama bilgisi.
        """
        if device_id not in self._records:
            self._records[device_id] = []

        self._records[device_id].append({
            "lat": lat,
            "lon": lon,
            "accuracy_m": accuracy_m,
            "timestamp": time.time(),
        })

        self._stats[
            "records_stored"
        ] += 1

        return {
            "device_id": device_id,
            "total_records": len(
                self._records[device_id],
            ),
            "stored": True,
        }

    def get_path(
        self,
        device_id: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Yol verisi döndürür.

        Args:
            device_id: Cihaz kimliği.
            limit: Kayıt limiti.

        Returns:
            Yol bilgisi.
        """
        records = self._records.get(
            device_id, [],
        )[-limit:]

        points = [
            {
                "lat": r["lat"],
                "lon": r["lon"],
            }
            for r in records
        ]

        return {
            "device_id": device_id,
            "point_count": len(points),
            "points": points,
            "retrieved": True,
        }

    def detect_dwell(
        self,
        device_id: str,
        radius_m: float = 50.0,
        min_points: int = 3,
    ) -> dict[str, Any]:
        """Bekleme tespiti yapar.

        Args:
            device_id: Cihaz kimliği.
            radius_m: Yarıçap eşiği.
            min_points: Minimum nokta sayısı.

        Returns:
            Tespit bilgisi.
        """
        records = self._records.get(
            device_id, [],
        )

        if len(records) < min_points:
            return {
                "device_id": device_id,
                "dwell_detected": False,
                "reason": (
                    "insufficient_data"
                ),
            }

        recent = records[-min_points:]

        avg_lat = sum(
            r["lat"] for r in recent
        ) / len(recent)
        avg_lon = sum(
            r["lon"] for r in recent
        ) / len(recent)

        max_deviation = max(
            abs(r["lat"] - avg_lat)
            + abs(r["lon"] - avg_lon)
            for r in recent
        )

        degree_threshold = (
            radius_m / 111000
        )
        is_dwell = (
            max_deviation
            < degree_threshold
        )

        if is_dwell:
            self._stats[
                "dwells_detected"
            ] += 1

        return {
            "device_id": device_id,
            "dwell_detected": is_dwell,
            "center_lat": round(
                avg_lat, 6,
            ),
            "center_lon": round(
                avg_lon, 6,
            ),
            "points_analyzed": len(
                recent,
            ),
            "detected": True,
        }

    def analyze_patterns(
        self,
        device_id: str,
    ) -> dict[str, Any]:
        """Konum örüntülerini analiz eder.

        Args:
            device_id: Cihaz kimliği.

        Returns:
            Analiz bilgisi.
        """
        records = self._records.get(
            device_id, [],
        )

        if not records:
            return {
                "device_id": device_id,
                "patterns_found": 0,
                "analyzed": False,
            }

        lats = [r["lat"] for r in records]
        lons = [r["lon"] for r in records]

        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)

        if lat_range < 0.001 and (
            lon_range < 0.001
        ):
            pattern = "stationary"
        elif lat_range < 0.01:
            pattern = "local"
        else:
            pattern = "mobile"

        return {
            "device_id": device_id,
            "total_points": len(records),
            "pattern": pattern,
            "lat_range": round(
                lat_range, 6,
            ),
            "lon_range": round(
                lon_range, 6,
            ),
            "analyzed": True,
        }

    def set_privacy(
        self,
        device_id: str,
        retention_days: int = 30,
        anonymize: bool = False,
        share_enabled: bool = False,
    ) -> dict[str, Any]:
        """Gizlilik ayarlarını belirler.

        Args:
            device_id: Cihaz kimliği.
            retention_days: Saklama süresi.
            anonymize: Anonimleştirme.
            share_enabled: Paylaşım.

        Returns:
            Ayar bilgisi.
        """
        self._privacy[device_id] = {
            "retention_days": (
                retention_days
            ),
            "anonymize": anonymize,
            "share_enabled": share_enabled,
            "updated_at": time.time(),
        }

        return {
            "device_id": device_id,
            "retention_days": (
                retention_days
            ),
            "anonymize": anonymize,
            "share_enabled": share_enabled,
            "privacy_set": True,
        }

    @property
    def record_count(self) -> int:
        """Kayıt sayısı."""
        return self._stats[
            "records_stored"
        ]

    @property
    def dwell_count(self) -> int:
        """Bekleme tespiti sayısı."""
        return self._stats[
            "dwells_detected"
        ]
