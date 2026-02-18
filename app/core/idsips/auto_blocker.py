"""
Otomatik engelleyici modulu.

IP engelleme, hiz sinirlandirma,
cografi engelleme, beyaz/kara liste,
gecici yasaklar.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class AutoBlocker:
    """Otomatik engelleyici.

    Attributes:
        _blocked: Engelli IP kayitlari.
        _whitelist: Beyaz liste.
        _blacklist: Kara liste.
        _rate_limits: Hiz limitleri.
        _geo_blocks: Cografi engeller.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Engelleyiciyi baslatir."""
        self._blocked: dict[
            str, dict
        ] = {}
        self._whitelist: set[str] = set()
        self._blacklist: set[str] = set()
        self._rate_limits: dict[
            str, dict
        ] = {}
        self._geo_blocks: set[str] = set()
        self._stats: dict[str, int] = {
            "ips_blocked": 0,
            "ips_unblocked": 0,
            "rate_limited": 0,
            "geo_blocked": 0,
        }
        logger.info(
            "AutoBlocker baslatildi"
        )

    @property
    def blocked_count(self) -> int:
        """Engelli IP sayisi."""
        return len(self._blocked)

    def block_ip(
        self,
        ip: str = "",
        reason: str = "",
        duration_minutes: int = 60,
        permanent: bool = False,
    ) -> dict[str, Any]:
        """IP engeller.

        Args:
            ip: IP adresi.
            reason: Sebep.
            duration_minutes: Sure (dakika).
            permanent: Kalici mi.

        Returns:
            Engelleme bilgisi.
        """
        try:
            if ip in self._whitelist:
                return {
                    "blocked": False,
                    "error": (
                        "IP beyaz listede"
                    ),
                }

            bid = f"bl_{uuid4()!s:.8}"
            self._blocked[ip] = {
                "block_id": bid,
                "reason": reason,
                "duration": duration_minutes,
                "permanent": permanent,
                "blocked_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats["ips_blocked"] += 1

            return {
                "block_id": bid,
                "ip": ip,
                "permanent": permanent,
                "blocked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "blocked": False,
                "error": str(e),
            }

    def unblock_ip(
        self,
        ip: str = "",
    ) -> dict[str, Any]:
        """IP engelini kaldirir.

        Args:
            ip: IP adresi.

        Returns:
            Kaldirma bilgisi.
        """
        try:
            if ip in self._blocked:
                del self._blocked[ip]
                self._stats[
                    "ips_unblocked"
                ] += 1
                return {
                    "ip": ip,
                    "unblocked": True,
                }
            return {
                "unblocked": False,
                "error": "IP engelli degil",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "unblocked": False,
                "error": str(e),
            }

    def is_blocked(
        self,
        ip: str = "",
    ) -> bool:
        """IP engelli mi kontrol eder."""
        if ip in self._blacklist:
            return True
        return ip in self._blocked

    def check_rate_limit(
        self,
        ip: str = "",
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> dict[str, Any]:
        """Hiz limiti kontrol eder.

        Args:
            ip: IP adresi.
            max_requests: Maks istek.
            window_seconds: Pencere (saniye).

        Returns:
            Kontrol bilgisi.
        """
        try:
            if ip not in self._rate_limits:
                self._rate_limits[ip] = {
                    "count": 0,
                    "window_start": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                }

            self._rate_limits[ip][
                "count"
            ] += 1
            count = self._rate_limits[ip][
                "count"
            ]
            exceeded = count > max_requests

            if exceeded:
                self._stats[
                    "rate_limited"
                ] += 1

            return {
                "ip": ip,
                "requests": count,
                "max_requests": max_requests,
                "exceeded": exceeded,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def add_to_whitelist(
        self,
        ip: str = "",
    ) -> dict[str, Any]:
        """Beyaz listeye ekler.

        Args:
            ip: IP adresi.

        Returns:
            Ekleme bilgisi.
        """
        try:
            self._whitelist.add(ip)
            if ip in self._blocked:
                del self._blocked[ip]

            return {
                "ip": ip,
                "whitelisted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "whitelisted": False,
                "error": str(e),
            }

    def remove_from_whitelist(
        self,
        ip: str = "",
    ) -> dict[str, Any]:
        """Beyaz listeden cikarir.

        Args:
            ip: IP adresi.

        Returns:
            Cikarma bilgisi.
        """
        try:
            self._whitelist.discard(ip)
            return {
                "ip": ip,
                "removed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "removed": False,
                "error": str(e),
            }

    def add_to_blacklist(
        self,
        ip: str = "",
    ) -> dict[str, Any]:
        """Kara listeye ekler.

        Args:
            ip: IP adresi.

        Returns:
            Ekleme bilgisi.
        """
        try:
            self._blacklist.add(ip)
            return {
                "ip": ip,
                "blacklisted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "blacklisted": False,
                "error": str(e),
            }

    def block_country(
        self,
        country_code: str = "",
    ) -> dict[str, Any]:
        """Ulke engeller.

        Args:
            country_code: Ulke kodu.

        Returns:
            Engelleme bilgisi.
        """
        try:
            code = country_code.upper()
            self._geo_blocks.add(code)
            self._stats["geo_blocked"] += 1

            return {
                "country": code,
                "geo_blocked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "geo_blocked": False,
                "error": str(e),
            }

    def unblock_country(
        self,
        country_code: str = "",
    ) -> dict[str, Any]:
        """Ulke engelini kaldirir.

        Args:
            country_code: Ulke kodu.

        Returns:
            Kaldirma bilgisi.
        """
        try:
            code = country_code.upper()
            self._geo_blocks.discard(code)
            return {
                "country": code,
                "unblocked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "unblocked": False,
                "error": str(e),
            }

    def is_country_blocked(
        self,
        country_code: str = "",
    ) -> bool:
        """Ulke engelli mi kontrol eder."""
        return (
            country_code.upper()
            in self._geo_blocks
        )

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir.

        Returns:
            Ozet bilgisi.
        """
        try:
            return {
                "blocked_ips": len(
                    self._blocked
                ),
                "whitelist_size": len(
                    self._whitelist
                ),
                "blacklist_size": len(
                    self._blacklist
                ),
                "geo_blocked_countries": len(
                    self._geo_blocks
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
