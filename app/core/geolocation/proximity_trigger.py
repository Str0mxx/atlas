"""ATLAS Yakınlık Tetikleyici modülü.

Mesafe hesaplama, yakınlık uyarıları,
menzil eşikleri, çoklu hedef takibi,
aksiyon tetikleme.
"""

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProximityTrigger:
    """Yakınlık tetikleyici.

    Konum tabanlı yakınlık olaylarını yönetir.

    Attributes:
        _targets: Hedef kayıtları.
        _triggers: Tetik kayıtları.
    """

    def __init__(self) -> None:
        """Tetikleyiciyi başlatır."""
        self._targets: dict[
            str, dict[str, Any]
        ] = {}
        self._triggers: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "triggers_fired": 0,
            "distances_calculated": 0,
        }

        logger.info(
            "ProximityTrigger baslatildi",
        )

    def calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> dict[str, Any]:
        """İki nokta arası mesafe hesaplar.

        Args:
            lat1: Enlem 1.
            lon1: Boylam 1.
            lat2: Enlem 2.
            lon2: Boylam 2.

        Returns:
            Mesafe bilgisi.
        """
        r = 6371000
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

        dist_m = r * c

        self._stats[
            "distances_calculated"
        ] += 1

        return {
            "distance_m": round(
                dist_m, 2,
            ),
            "distance_km": round(
                dist_m / 1000, 3,
            ),
            "calculated": True,
        }

    def set_proximity_alert(
        self,
        target_id: str,
        target_lat: float,
        target_lon: float,
        range_m: float = 100.0,
        action: str = "",
    ) -> dict[str, Any]:
        """Yakınlık uyarısı tanımlar.

        Args:
            target_id: Hedef kimliği.
            target_lat: Hedef enlemi.
            target_lon: Hedef boylamı.
            range_m: Menzil (metre).
            action: Tetiklenecek aksiyon.

        Returns:
            Uyarı bilgisi.
        """
        self._targets[target_id] = {
            "target_id": target_id,
            "lat": target_lat,
            "lon": target_lon,
            "range_m": range_m,
            "action": action,
            "created_at": time.time(),
        }

        return {
            "target_id": target_id,
            "range_m": range_m,
            "action": action,
            "alert_set": True,
        }

    def check_range(
        self,
        target_id: str,
        current_lat: float,
        current_lon: float,
    ) -> dict[str, Any]:
        """Menzil kontrolü yapar.

        Args:
            target_id: Hedef kimliği.
            current_lat: Şimdiki enlem.
            current_lon: Şimdiki boylam.

        Returns:
            Kontrol bilgisi.
        """
        target = self._targets.get(
            target_id,
        )
        if not target:
            return {
                "target_id": target_id,
                "found": False,
            }

        dist = self.calculate_distance(
            current_lat,
            current_lon,
            target["lat"],
            target["lon"],
        )

        in_range = (
            dist["distance_m"]
            <= target["range_m"]
        )

        return {
            "target_id": target_id,
            "distance_m": dist[
                "distance_m"
            ],
            "range_m": target["range_m"],
            "in_range": in_range,
            "checked": True,
        }

    def track_multi_target(
        self,
        current_lat: float,
        current_lon: float,
    ) -> dict[str, Any]:
        """Çoklu hedef takibi yapar.

        Args:
            current_lat: Şimdiki enlem.
            current_lon: Şimdiki boylam.

        Returns:
            Takip bilgisi.
        """
        results = []
        in_range_count = 0

        for tid, target in (
            self._targets.items()
        ):
            dist = self.calculate_distance(
                current_lat,
                current_lon,
                target["lat"],
                target["lon"],
            )
            in_range = (
                dist["distance_m"]
                <= target["range_m"]
            )
            if in_range:
                in_range_count += 1

            results.append({
                "target_id": tid,
                "distance_m": dist[
                    "distance_m"
                ],
                "in_range": in_range,
            })

        return {
            "targets_checked": len(
                results,
            ),
            "in_range_count": (
                in_range_count
            ),
            "results": results,
            "tracked": True,
        }

    def fire_trigger(
        self,
        target_id: str,
        current_lat: float,
        current_lon: float,
    ) -> dict[str, Any]:
        """Tetikleme aksiyonu çalıştırır.

        Args:
            target_id: Hedef kimliği.
            current_lat: Şimdiki enlem.
            current_lon: Şimdiki boylam.

        Returns:
            Tetik bilgisi.
        """
        check = self.check_range(
            target_id,
            current_lat,
            current_lon,
        )

        if not check.get("checked"):
            return {
                "target_id": target_id,
                "found": False,
            }

        fired = False
        action = ""
        if check["in_range"]:
            target = self._targets[
                target_id
            ]
            action = target.get(
                "action", "",
            )
            fired = True
            self._stats[
                "triggers_fired"
            ] += 1

            self._triggers.append({
                "target_id": target_id,
                "action": action,
                "distance_m": check[
                    "distance_m"
                ],
                "timestamp": time.time(),
            })

        return {
            "target_id": target_id,
            "fired": fired,
            "action": action,
            "distance_m": check[
                "distance_m"
            ],
        }

    @property
    def trigger_count(self) -> int:
        """Tetik sayısı."""
        return self._stats[
            "triggers_fired"
        ]

    @property
    def distance_count(self) -> int:
        """Hesaplama sayısı."""
        return self._stats[
            "distances_calculated"
        ]
