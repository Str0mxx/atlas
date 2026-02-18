"""
Cografi erisim politikasi modulu.

Konum tabanli erisim, geo-fencing,
seyahat tespiti, VPN tespiti,
risk puanlama.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class GeoAccessPolicy:
    """Cografi erisim politikasi.

    Attributes:
        _policies: Politika kayitlari.
        _access_log: Erisim gecmisi.
        _user_locations: Kullanici konumlari.
        _stats: Istatistikler.
    """

    KNOWN_VPN_RANGES: list[str] = [
        "10.0.0.",
        "172.16.",
        "192.168.",
    ]

    def __init__(self) -> None:
        """Politikayi baslatir."""
        self._policies: dict[
            str, dict
        ] = {}
        self._access_log: list[dict] = []
        self._user_locations: dict[
            str, list
        ] = {}
        self._stats: dict[str, int] = {
            "checks_performed": 0,
            "access_granted": 0,
            "access_denied": 0,
            "travel_detected": 0,
            "vpn_detected": 0,
        }
        logger.info(
            "GeoAccessPolicy baslatildi"
        )

    @property
    def policy_count(self) -> int:
        """Politika sayisi."""
        return len(self._policies)

    def create_policy(
        self,
        name: str = "",
        allowed_countries: (
            list[str] | None
        ) = None,
        blocked_countries: (
            list[str] | None
        ) = None,
        allow_vpn: bool = False,
        max_travel_speed_kmh: int = 900,
    ) -> dict[str, Any]:
        """Politika olusturur.

        Args:
            name: Politika adi.
            allowed_countries: Izin ulkeler.
            blocked_countries: Engelli ulkeler.
            allow_vpn: VPN izni.
            max_travel_speed_kmh: Max hiz.

        Returns:
            Olusturma bilgisi.
        """
        try:
            pid = f"gp_{uuid4()!s:.8}"
            self._policies[name] = {
                "policy_id": pid,
                "name": name,
                "allowed_countries": (
                    allowed_countries or []
                ),
                "blocked_countries": (
                    blocked_countries or []
                ),
                "allow_vpn": allow_vpn,
                "max_travel_speed_kmh": (
                    max_travel_speed_kmh
                ),
                "active": True,
            }

            return {
                "policy_id": pid,
                "name": name,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def check_access(
        self,
        user_id: str = "",
        country: str = "",
        ip_address: str = "",
        latitude: float = 0.0,
        longitude: float = 0.0,
        policy_name: str = "",
    ) -> dict[str, Any]:
        """Erisim kontrol eder.

        Args:
            user_id: Kullanici ID.
            country: Ulke kodu.
            ip_address: IP adresi.
            latitude: Enlem.
            longitude: Boylam.
            policy_name: Politika adi.

        Returns:
            Erisim bilgisi.
        """
        try:
            self._stats[
                "checks_performed"
            ] += 1
            policy = self._policies.get(
                policy_name
            )
            if not policy:
                return {
                    "allowed": False,
                    "error": (
                        "Politika bulunamadi"
                    ),
                }

            issues: list[str] = []
            risk_score = 0.0

            allowed = policy[
                "allowed_countries"
            ]
            blocked = policy[
                "blocked_countries"
            ]

            if allowed and (
                country not in allowed
            ):
                issues.append(
                    "country_not_allowed"
                )
                risk_score += 0.4
            if country in blocked:
                issues.append(
                    "country_blocked"
                )
                risk_score += 0.5

            vpn = self._detect_vpn(
                ip_address
            )
            if vpn and not policy[
                "allow_vpn"
            ]:
                issues.append(
                    "vpn_detected"
                )
                risk_score += 0.3
                self._stats[
                    "vpn_detected"
                ] += 1

            travel = self._check_travel(
                user_id,
                latitude,
                longitude,
                policy[
                    "max_travel_speed_kmh"
                ],
            )
            if travel.get(
                "impossible_travel"
            ):
                issues.append(
                    "impossible_travel"
                )
                risk_score += 0.5
                self._stats[
                    "travel_detected"
                ] += 1

            self._record_location(
                user_id,
                country,
                latitude,
                longitude,
                ip_address,
            )

            allowed_access = (
                len(issues) == 0
            )
            if allowed_access:
                self._stats[
                    "access_granted"
                ] += 1
            else:
                self._stats[
                    "access_denied"
                ] += 1

            risk_score = min(
                1.0, risk_score
            )

            return {
                "user_id": user_id,
                "country": country,
                "allowed": allowed_access,
                "issues": issues,
                "risk_score": round(
                    risk_score, 2
                ),
                "vpn_detected": vpn,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def _detect_vpn(
        self,
        ip_address: str,
    ) -> bool:
        """VPN tespit eder."""
        return any(
            ip_address.startswith(r)
            for r in self.KNOWN_VPN_RANGES
        )

    def _check_travel(
        self,
        user_id: str,
        lat: float,
        lon: float,
        max_speed: int,
    ) -> dict:
        """Seyahat kontrol eder."""
        locs = self._user_locations.get(
            user_id, []
        )
        if not locs:
            return {
                "impossible_travel": False,
            }

        last = locs[-1]
        dist = self._haversine(
            last["latitude"],
            last["longitude"],
            lat,
            lon,
        )
        return {
            "impossible_travel": (
                dist > max_speed * 2
            ),
            "distance_km": round(dist, 1),
        }

    def _haversine(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Haversine mesafe hesaplar."""
        r = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a),
        )
        return r * c

    def _record_location(
        self,
        user_id: str,
        country: str,
        lat: float,
        lon: float,
        ip: str,
    ) -> None:
        """Konum kaydeder."""
        if (
            user_id
            not in self._user_locations
        ):
            self._user_locations[
                user_id
            ] = []
        self._user_locations[
            user_id
        ].append({
            "country": country,
            "latitude": lat,
            "longitude": lon,
            "ip_address": ip,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        })

    def get_user_locations(
        self,
        user_id: str = "",
    ) -> dict[str, Any]:
        """Kullanici konumlarini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Konum bilgisi.
        """
        try:
            locs = (
                self._user_locations.get(
                    user_id, []
                )
            )
            return {
                "user_id": user_id,
                "locations": locs,
                "count": len(locs),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_policies": len(
                    self._policies
                ),
                "total_users_tracked": len(
                    self._user_locations
                ),
                "total_access_log": len(
                    self._access_log
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
