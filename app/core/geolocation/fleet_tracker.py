"""ATLAS Filo Takipçisi modülü.

Araç takibi, sürücü ataması,
durum izleme, performans metrikleri,
sevkiyat optimizasyonu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FleetTracker:
    """Filo takipçisi.

    Araç filosunu takip ve yönetir.

    Attributes:
        _vehicles: Araç kayıtları.
        _drivers: Sürücü atamaları.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._vehicles: dict[
            str, dict[str, Any]
        ] = {}
        self._drivers: dict[
            str, str
        ] = {}
        self._stats = {
            "vehicles_tracked": 0,
            "dispatches_done": 0,
        }

        logger.info(
            "FleetTracker baslatildi",
        )

    def track_vehicle(
        self,
        vehicle_id: str,
        lat: float,
        lon: float,
        speed_kmh: float = 0.0,
        heading: float = 0.0,
    ) -> dict[str, Any]:
        """Araç takibi yapar.

        Args:
            vehicle_id: Araç kimliği.
            lat: Enlem.
            lon: Boylam.
            speed_kmh: Hız (km/s).
            heading: Yön (derece).

        Returns:
            Takip bilgisi.
        """
        is_new = (
            vehicle_id
            not in self._vehicles
        )

        if speed_kmh > 0:
            status = "moving"
        else:
            status = "idle"

        self._vehicles[vehicle_id] = {
            "vehicle_id": vehicle_id,
            "lat": lat,
            "lon": lon,
            "speed_kmh": speed_kmh,
            "heading": heading,
            "status": status,
            "updated_at": time.time(),
        }

        if is_new:
            self._stats[
                "vehicles_tracked"
            ] += 1

        return {
            "vehicle_id": vehicle_id,
            "lat": lat,
            "lon": lon,
            "status": status,
            "tracked": True,
        }

    def assign_driver(
        self,
        vehicle_id: str,
        driver_id: str,
    ) -> dict[str, Any]:
        """Sürücü atar.

        Args:
            vehicle_id: Araç kimliği.
            driver_id: Sürücü kimliği.

        Returns:
            Atama bilgisi.
        """
        self._drivers[vehicle_id] = (
            driver_id
        )

        if vehicle_id in self._vehicles:
            self._vehicles[vehicle_id][
                "driver_id"
            ] = driver_id

        return {
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "assigned": True,
        }

    def monitor_status(
        self,
        vehicle_id: str,
    ) -> dict[str, Any]:
        """Araç durumu izler.

        Args:
            vehicle_id: Araç kimliği.

        Returns:
            Durum bilgisi.
        """
        vehicle = self._vehicles.get(
            vehicle_id,
        )
        if not vehicle:
            return {
                "vehicle_id": vehicle_id,
                "found": False,
            }

        age = (
            time.time()
            - vehicle["updated_at"]
        )

        if age > 600:
            connectivity = "lost"
        elif age > 120:
            connectivity = "weak"
        else:
            connectivity = "strong"

        return {
            "vehicle_id": vehicle_id,
            "status": vehicle["status"],
            "speed_kmh": vehicle[
                "speed_kmh"
            ],
            "connectivity": connectivity,
            "last_update_sec": round(
                age, 0,
            ),
            "driver_id": self._drivers.get(
                vehicle_id, "",
            ),
            "monitored": True,
        }

    def get_performance(
        self,
        vehicle_id: str,
        total_km: float = 0.0,
        fuel_liters: float = 0.0,
        hours_driven: float = 0.0,
    ) -> dict[str, Any]:
        """Performans metriklerini hesaplar.

        Args:
            vehicle_id: Araç kimliği.
            total_km: Toplam mesafe.
            fuel_liters: Yakıt tüketimi.
            hours_driven: Sürüş saati.

        Returns:
            Performans bilgisi.
        """
        fuel_efficiency = (
            total_km / fuel_liters
            if fuel_liters > 0
            else 0.0
        )

        avg_speed = (
            total_km / hours_driven
            if hours_driven > 0
            else 0.0
        )

        if fuel_efficiency >= 15:
            efficiency_rating = "excellent"
        elif fuel_efficiency >= 10:
            efficiency_rating = "good"
        elif fuel_efficiency >= 5:
            efficiency_rating = "average"
        else:
            efficiency_rating = "poor"

        return {
            "vehicle_id": vehicle_id,
            "total_km": total_km,
            "fuel_efficiency_km_l": round(
                fuel_efficiency, 1,
            ),
            "avg_speed_kmh": round(
                avg_speed, 1,
            ),
            "efficiency_rating": (
                efficiency_rating
            ),
            "calculated": True,
        }

    def dispatch_vehicle(
        self,
        vehicle_id: str,
        dest_lat: float,
        dest_lon: float,
        priority: str = "normal",
    ) -> dict[str, Any]:
        """Araç sevkiyatı yapar.

        Args:
            vehicle_id: Araç kimliği.
            dest_lat: Hedef enlemi.
            dest_lon: Hedef boylamı.
            priority: Öncelik.

        Returns:
            Sevkiyat bilgisi.
        """
        vehicle = self._vehicles.get(
            vehicle_id,
        )
        if not vehicle:
            return {
                "vehicle_id": vehicle_id,
                "found": False,
            }

        vehicle["dispatch"] = {
            "dest_lat": dest_lat,
            "dest_lon": dest_lon,
            "priority": priority,
            "dispatched_at": time.time(),
        }
        vehicle["status"] = "dispatched"

        self._stats[
            "dispatches_done"
        ] += 1

        return {
            "vehicle_id": vehicle_id,
            "dest_lat": dest_lat,
            "dest_lon": dest_lon,
            "priority": priority,
            "dispatched": True,
        }

    @property
    def vehicle_count(self) -> int:
        """Araç sayısı."""
        return self._stats[
            "vehicles_tracked"
        ]

    @property
    def dispatch_count(self) -> int:
        """Sevkiyat sayısı."""
        return self._stats[
            "dispatches_done"
        ]
