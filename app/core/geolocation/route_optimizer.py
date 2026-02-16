"""ATLAS Rota Optimizasyonu modülü.

Yol optimizasyonu, çoklu durak,
trafik değerlendirmesi, zaman pencereleri,
kısıt yönetimi.
"""

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)


class RouteOptimizer:
    """Rota optimizasyonu.

    Rota planlama ve optimizasyon sağlar.

    Attributes:
        _routes: Rota kayıtları.
        _constraints: Kısıt kayıtları.
    """

    def __init__(self) -> None:
        """Optimizer'ı başlatır."""
        self._routes: dict[
            str, dict[str, Any]
        ] = {}
        self._constraints: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "routes_optimized": 0,
            "stops_processed": 0,
        }

        logger.info(
            "RouteOptimizer baslatildi",
        )

    def optimize_path(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        strategy: str = "fastest",
    ) -> dict[str, Any]:
        """Yol optimizasyonu yapar.

        Args:
            origin_lat: Başlangıç enlemi.
            origin_lon: Başlangıç boylamı.
            dest_lat: Hedef enlemi.
            dest_lon: Hedef boylamı.
            strategy: Strateji.

        Returns:
            Optimizasyon bilgisi.
        """
        self._counter += 1
        rid = f"route_{self._counter}"

        dist_km = self._calc_distance_km(
            origin_lat,
            origin_lon,
            dest_lat,
            dest_lon,
        )

        if strategy == "fastest":
            speed_kmh = 60
        elif strategy == "economical":
            speed_kmh = 45
        elif strategy == "shortest":
            speed_kmh = 50
        else:
            speed_kmh = 55

        duration_min = (
            dist_km / speed_kmh * 60
        )

        self._routes[rid] = {
            "route_id": rid,
            "origin": (
                origin_lat,
                origin_lon,
            ),
            "dest": (dest_lat, dest_lon),
            "distance_km": round(
                dist_km, 2,
            ),
            "duration_min": round(
                duration_min, 1,
            ),
            "strategy": strategy,
            "created_at": time.time(),
        }

        self._stats[
            "routes_optimized"
        ] += 1

        return {
            "route_id": rid,
            "distance_km": round(
                dist_km, 2,
            ),
            "duration_min": round(
                duration_min, 1,
            ),
            "strategy": strategy,
            "optimized": True,
        }

    def multi_stop_route(
        self,
        stops: list[
            tuple[float, float]
        ],
        strategy: str = "fastest",
    ) -> dict[str, Any]:
        """Çoklu duraklı rota planlar.

        Args:
            stops: Durak koordinatları.
            strategy: Strateji.

        Returns:
            Rota bilgisi.
        """
        if len(stops) < 2:
            return {
                "stops": len(stops),
                "error": "min_2_stops",
                "planned": False,
            }

        total_dist = 0.0
        segments = []

        for i in range(len(stops) - 1):
            seg_dist = (
                self._calc_distance_km(
                    stops[i][0],
                    stops[i][1],
                    stops[i + 1][0],
                    stops[i + 1][1],
                )
            )
            total_dist += seg_dist
            segments.append({
                "from_stop": i,
                "to_stop": i + 1,
                "distance_km": round(
                    seg_dist, 2,
                ),
            })

        self._stats[
            "stops_processed"
        ] += len(stops)

        if strategy == "fastest":
            speed = 60
        elif strategy == "economical":
            speed = 45
        else:
            speed = 55

        total_min = (
            total_dist / speed * 60
        )

        return {
            "stop_count": len(stops),
            "segments": len(segments),
            "total_distance_km": round(
                total_dist, 2,
            ),
            "total_duration_min": round(
                total_min, 1,
            ),
            "strategy": strategy,
            "planned": True,
        }

    def consider_traffic(
        self,
        route_id: str,
        traffic_factor: float = 1.0,
    ) -> dict[str, Any]:
        """Trafik etkisini hesaplar.

        Args:
            route_id: Rota kimliği.
            traffic_factor: Trafik çarpanı (1.0=normal).

        Returns:
            Trafik bilgisi.
        """
        route = self._routes.get(route_id)
        if not route:
            return {
                "route_id": route_id,
                "found": False,
            }

        adjusted_min = (
            route["duration_min"]
            * traffic_factor
        )

        if traffic_factor <= 1.0:
            level = "clear"
        elif traffic_factor <= 1.3:
            level = "moderate"
        elif traffic_factor <= 1.7:
            level = "heavy"
        else:
            level = "severe"

        return {
            "route_id": route_id,
            "original_min": route[
                "duration_min"
            ],
            "adjusted_min": round(
                adjusted_min, 1,
            ),
            "traffic_factor": (
                traffic_factor
            ),
            "traffic_level": level,
            "adjusted": True,
        }

    def set_time_window(
        self,
        route_id: str,
        earliest: str = "",
        latest: str = "",
    ) -> dict[str, Any]:
        """Zaman penceresi belirler.

        Args:
            route_id: Rota kimliği.
            earliest: En erken saat.
            latest: En geç saat.

        Returns:
            Pencere bilgisi.
        """
        route = self._routes.get(route_id)
        if not route:
            return {
                "route_id": route_id,
                "found": False,
            }

        route["time_window"] = {
            "earliest": earliest,
            "latest": latest,
        }

        return {
            "route_id": route_id,
            "earliest": earliest,
            "latest": latest,
            "window_set": True,
        }

    def add_constraint(
        self,
        route_id: str,
        constraint_type: str = "",
        value: Any = None,
    ) -> dict[str, Any]:
        """Kısıt ekler.

        Args:
            route_id: Rota kimliği.
            constraint_type: Kısıt tipi.
            value: Kısıt değeri.

        Returns:
            Kısıt bilgisi.
        """
        self._constraints.append({
            "route_id": route_id,
            "type": constraint_type,
            "value": value,
            "added_at": time.time(),
        })

        return {
            "route_id": route_id,
            "constraint_type": (
                constraint_type
            ),
            "added": True,
        }

    def _calc_distance_km(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Haversine mesafe (km).

        Args:
            lat1: Enlem 1.
            lon1: Boylam 1.
            lat2: Enlem 2.
            lon2: Boylam 2.

        Returns:
            Mesafe (km).
        """
        r = 6371
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lam = math.radians(lon2 - lon1)

        a = (
            math.sin(d_phi / 2) ** 2
            + math.cos(phi1)
            * math.cos(phi2)
            * math.sin(d_lam / 2) ** 2
        )
        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a),
        )

        return r * c

    @property
    def route_count(self) -> int:
        """Rota sayısı."""
        return self._stats[
            "routes_optimized"
        ]

    @property
    def stops_count(self) -> int:
        """İşlenen durak sayısı."""
        return self._stats[
            "stops_processed"
        ]
