"""ATLAS Geofence Yöneticisi modülü.

Zone tanımlama, polygon/circle desteği,
giriş/çıkış tespiti, örtüşme yönetimi,
zone grupları.
"""

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)


class GeofenceManager:
    """Geofence yöneticisi.

    Coğrafi sınır alanlarını yönetir.

    Attributes:
        _zones: Zone kayıtları.
        _groups: Zone grupları.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._zones: dict[
            str, dict[str, Any]
        ] = {}
        self._groups: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "zones_created": 0,
            "checks_done": 0,
        }

        logger.info(
            "GeofenceManager baslatildi",
        )

    def define_zone(
        self,
        name: str,
        shape: str = "circle",
        center_lat: float = 0.0,
        center_lon: float = 0.0,
        radius_m: float = 100.0,
        polygon: list[tuple[float, float]]
        | None = None,
    ) -> dict[str, Any]:
        """Zone tanımlar.

        Args:
            name: Zone adı.
            shape: Şekil tipi.
            center_lat: Merkez enlem.
            center_lon: Merkez boylam.
            radius_m: Yarıçap (metre).
            polygon: Poligon köşeleri.

        Returns:
            Tanım bilgisi.
        """
        self._counter += 1
        zid = f"zone_{self._counter}"

        self._zones[zid] = {
            "zone_id": zid,
            "name": name,
            "shape": shape,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "radius_m": radius_m,
            "polygon": polygon or [],
            "created_at": time.time(),
        }

        self._stats["zones_created"] += 1

        return {
            "zone_id": zid,
            "name": name,
            "shape": shape,
            "created": True,
        }

    def check_point_in_zone(
        self,
        zone_id: str,
        lat: float,
        lon: float,
    ) -> dict[str, Any]:
        """Noktanın zone içinde olup olmadığını kontrol eder.

        Args:
            zone_id: Zone kimliği.
            lat: Enlem.
            lon: Boylam.

        Returns:
            Kontrol bilgisi.
        """
        zone = self._zones.get(zone_id)
        if not zone:
            return {
                "zone_id": zone_id,
                "found": False,
            }

        self._stats["checks_done"] += 1

        if zone["shape"] == "circle":
            dist = self._haversine(
                zone["center_lat"],
                zone["center_lon"],
                lat,
                lon,
            )
            inside = dist <= zone["radius_m"]
        elif zone["shape"] == "polygon":
            inside = self._point_in_polygon(
                lat,
                lon,
                zone["polygon"],
            )
        else:
            inside = False

        return {
            "zone_id": zone_id,
            "lat": lat,
            "lon": lon,
            "inside": inside,
            "checked": True,
        }

    def detect_entry_exit(
        self,
        zone_id: str,
        prev_lat: float,
        prev_lon: float,
        curr_lat: float,
        curr_lon: float,
    ) -> dict[str, Any]:
        """Giriş/çıkış tespiti yapar.

        Args:
            zone_id: Zone kimliği.
            prev_lat: Önceki enlem.
            prev_lon: Önceki boylam.
            curr_lat: Şimdiki enlem.
            curr_lon: Şimdiki boylam.

        Returns:
            Tespit bilgisi.
        """
        prev = self.check_point_in_zone(
            zone_id, prev_lat, prev_lon,
        )
        curr = self.check_point_in_zone(
            zone_id, curr_lat, curr_lon,
        )

        if not prev.get("checked"):
            return {
                "zone_id": zone_id,
                "found": False,
            }

        was_inside = prev["inside"]
        is_inside = curr["inside"]

        event = "none"
        if not was_inside and is_inside:
            event = "entry"
        elif was_inside and not is_inside:
            event = "exit"
        elif is_inside:
            event = "stay"

        return {
            "zone_id": zone_id,
            "event": event,
            "was_inside": was_inside,
            "is_inside": is_inside,
            "detected": True,
        }

    def check_overlap(
        self,
        zone_id_a: str,
        zone_id_b: str,
    ) -> dict[str, Any]:
        """İki zone'un örtüşmesini kontrol eder.

        Args:
            zone_id_a: Birinci zone.
            zone_id_b: İkinci zone.

        Returns:
            Örtüşme bilgisi.
        """
        za = self._zones.get(zone_id_a)
        zb = self._zones.get(zone_id_b)

        if not za or not zb:
            return {
                "zone_a": zone_id_a,
                "zone_b": zone_id_b,
                "found": False,
            }

        if (
            za["shape"] == "circle"
            and zb["shape"] == "circle"
        ):
            dist = self._haversine(
                za["center_lat"],
                za["center_lon"],
                zb["center_lat"],
                zb["center_lon"],
            )
            overlap = dist < (
                za["radius_m"]
                + zb["radius_m"]
            )
        else:
            overlap = False

        return {
            "zone_a": zone_id_a,
            "zone_b": zone_id_b,
            "overlapping": overlap,
            "checked": True,
        }

    def manage_group(
        self,
        group_name: str,
        zone_ids: list[str] | None = None,
        action: str = "create",
    ) -> dict[str, Any]:
        """Zone grubu yönetir.

        Args:
            group_name: Grup adı.
            zone_ids: Zone kimlikleri.
            action: Aksiyon.

        Returns:
            Yönetim bilgisi.
        """
        zone_ids = zone_ids or []

        if action == "create":
            self._groups[group_name] = (
                zone_ids
            )
        elif action == "add":
            existing = self._groups.get(
                group_name, [],
            )
            existing.extend(zone_ids)
            self._groups[group_name] = (
                existing
            )
        elif action == "delete":
            self._groups.pop(
                group_name, None,
            )

        return {
            "group_name": group_name,
            "action": action,
            "zone_count": len(
                self._groups.get(
                    group_name, [],
                ),
            ),
            "managed": True,
        }

    def _haversine(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Haversine mesafe hesabı (metre).

        Args:
            lat1: Enlem 1.
            lon1: Boylam 1.
            lat2: Enlem 2.
            lon2: Boylam 2.

        Returns:
            Mesafe (metre).
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

        return r * c

    def _point_in_polygon(
        self,
        lat: float,
        lon: float,
        polygon: list[tuple[float, float]],
    ) -> bool:
        """Ray-casting algoritmasıyla nokta-poligon testi.

        Args:
            lat: Enlem.
            lon: Boylam.
            polygon: Poligon köşeleri.

        Returns:
            İçeride mi.
        """
        n = len(polygon)
        if n < 3:
            return False

        inside = False
        j = n - 1
        for i in range(n):
            lat_i, lon_i = polygon[i]
            lat_j, lon_j = polygon[j]

            if (
                (lat_i > lat)
                != (lat_j > lat)
            ) and (
                lon
                < (lon_j - lon_i)
                * (lat - lat_i)
                / (lat_j - lat_i)
                + lon_i
            ):
                inside = not inside
            j = i

        return inside

    @property
    def zone_count(self) -> int:
        """Zone sayısı."""
        return self._stats[
            "zones_created"
        ]

    @property
    def check_count(self) -> int:
        """Kontrol sayısı."""
        return self._stats["checks_done"]
