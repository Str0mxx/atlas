"""ATLAS Konum Takipçisi modülü.

Gerçek zamanlı takip, cihaz konumları,
geçmiş kayıt, doğruluk yönetimi,
batarya optimizasyonu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LocationTracker:
    """Konum takipçisi.

    Cihaz konumlarını gerçek zamanlı takip eder.

    Attributes:
        _devices: Cihaz konum kayıtları.
        _history: Konum geçmişi.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._devices: dict[
            str, dict[str, Any]
        ] = {}
        self._history: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "updates_received": 0,
            "devices_tracked": 0,
        }

        logger.info(
            "LocationTracker baslatildi",
        )

    def track_realtime(
        self,
        device_id: str,
        lat: float,
        lon: float,
        accuracy_m: float = 10.0,
    ) -> dict[str, Any]:
        """Gerçek zamanlı konum takibi.

        Args:
            device_id: Cihaz kimliği.
            lat: Enlem.
            lon: Boylam.
            accuracy_m: Doğruluk (metre).

        Returns:
            Takip bilgisi.
        """
        is_new = (
            device_id not in self._devices
        )

        self._devices[device_id] = {
            "device_id": device_id,
            "lat": lat,
            "lon": lon,
            "accuracy_m": accuracy_m,
            "updated_at": time.time(),
        }

        self._history.append({
            "device_id": device_id,
            "lat": lat,
            "lon": lon,
            "accuracy_m": accuracy_m,
            "timestamp": time.time(),
        })

        self._stats[
            "updates_received"
        ] += 1
        if is_new:
            self._stats[
                "devices_tracked"
            ] += 1

        return {
            "device_id": device_id,
            "lat": lat,
            "lon": lon,
            "accuracy_m": accuracy_m,
            "tracked": True,
        }

    def get_device_location(
        self,
        device_id: str,
    ) -> dict[str, Any]:
        """Cihaz konumunu döndürür.

        Args:
            device_id: Cihaz kimliği.

        Returns:
            Konum bilgisi.
        """
        dev = self._devices.get(device_id)
        if not dev:
            return {
                "device_id": device_id,
                "found": False,
            }

        return {
            "device_id": device_id,
            "lat": dev["lat"],
            "lon": dev["lon"],
            "accuracy_m": dev[
                "accuracy_m"
            ],
            "found": True,
        }

    def log_history(
        self,
        device_id: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Konum geçmişini sorgular.

        Args:
            device_id: Cihaz kimliği.
            limit: Kayıt limiti.

        Returns:
            Geçmiş bilgisi.
        """
        entries = [
            h
            for h in self._history
            if h["device_id"] == device_id
        ][-limit:]

        return {
            "device_id": device_id,
            "entries": len(entries),
            "history": entries,
            "retrieved": True,
        }

    def handle_accuracy(
        self,
        device_id: str,
        accuracy_m: float,
    ) -> dict[str, Any]:
        """Doğruluk seviyesini değerlendirir.

        Args:
            device_id: Cihaz kimliği.
            accuracy_m: Doğruluk (metre).

        Returns:
            Değerlendirme bilgisi.
        """
        if accuracy_m <= 5:
            quality = "excellent"
        elif accuracy_m <= 15:
            quality = "good"
        elif accuracy_m <= 50:
            quality = "moderate"
        else:
            quality = "poor"

        return {
            "device_id": device_id,
            "accuracy_m": accuracy_m,
            "quality": quality,
            "usable": accuracy_m <= 100,
            "evaluated": True,
        }

    def optimize_battery(
        self,
        device_id: str,
        battery_pct: float = 100.0,
        movement_detected: bool = True,
    ) -> dict[str, Any]:
        """Batarya optimizasyonu önerir.

        Args:
            device_id: Cihaz kimliği.
            battery_pct: Batarya yüzdesi.
            movement_detected: Hareket var mı.

        Returns:
            Optimizasyon bilgisi.
        """
        if battery_pct < 10:
            interval = 300
            mode = "ultra_saver"
        elif battery_pct < 30:
            interval = 120
            mode = "power_saver"
        elif not movement_detected:
            interval = 60
            mode = "stationary"
        else:
            interval = 10
            mode = "normal"

        return {
            "device_id": device_id,
            "battery_pct": battery_pct,
            "recommended_interval": interval,
            "mode": mode,
            "optimized": True,
        }

    @property
    def update_count(self) -> int:
        """Güncelleme sayısı."""
        return self._stats[
            "updates_received"
        ]

    @property
    def device_count(self) -> int:
        """Takip edilen cihaz sayısı."""
        return self._stats[
            "devices_tracked"
        ]
