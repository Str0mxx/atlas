"""ATLAS Hız Limiti Uygulayıcı modulu.

API hız limitleri, platform limitleri,
özel limitler, kota takibi, geri çekilme stratejileri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RateLimitEnforcer:
    """Hız limiti uygulayıcı.

    Hız limitlerini tanımlar ve uygular.

    Attributes:
        _limits: Limit tanımları.
        _usage: Kullanım kayıtları.
    """

    def __init__(self) -> None:
        """Uygulayıcıyı başlatır."""
        self._limits: dict[
            str, dict[str, Any]
        ] = {}
        self._usage: dict[
            str, list[float]
        ] = {}
        self._counter = 0
        self._stats = {
            "limits_defined": 0,
            "checks": 0,
            "blocked": 0,
        }

        logger.info(
            "RateLimitEnforcer baslatildi",
        )

    def define_limit(
        self,
        name: str,
        max_requests: int,
        window_seconds: int = 60,
        limit_type: str = "api",
    ) -> dict[str, Any]:
        """Limit tanımlar.

        Args:
            name: Limit adı.
            max_requests: Maks istek sayısı.
            window_seconds: Pencere süresi.
            limit_type: Limit tipi.

        Returns:
            Tanımlama bilgisi.
        """
        self._counter += 1
        lid = f"lim_{self._counter}"

        self._limits[lid] = {
            "limit_id": lid,
            "name": name,
            "max_requests": max_requests,
            "window_seconds": window_seconds,
            "limit_type": limit_type,
            "active": True,
            "created_at": time.time(),
        }
        self._usage[lid] = []
        self._stats["limits_defined"] += 1

        return {
            "limit_id": lid,
            "name": name,
            "max_requests": max_requests,
            "window_seconds": window_seconds,
            "defined": True,
        }

    def check_limit(
        self,
        limit_id: str,
    ) -> dict[str, Any]:
        """Limit kontrolü yapar.

        Args:
            limit_id: Limit ID.

        Returns:
            Kontrol bilgisi.
        """
        lim = self._limits.get(limit_id)
        if not lim:
            return {
                "error": "limit_not_found",
            }

        self._stats["checks"] += 1
        now = time.time()
        window = lim["window_seconds"]
        max_req = lim["max_requests"]

        # Eski kayıtları temizle
        self._usage[limit_id] = [
            t for t in self._usage[limit_id]
            if now - t < window
        ]

        current = len(
            self._usage[limit_id],
        )
        allowed = current < max_req
        remaining = max(0, max_req - current)

        if not allowed:
            self._stats["blocked"] += 1

        return {
            "limit_id": limit_id,
            "allowed": allowed,
            "current": current,
            "max_requests": max_req,
            "remaining": remaining,
            "window_seconds": window,
        }

    def record_usage(
        self,
        limit_id: str,
    ) -> dict[str, Any]:
        """Kullanım kaydeder.

        Args:
            limit_id: Limit ID.

        Returns:
            Kayıt bilgisi.
        """
        if limit_id not in self._limits:
            return {
                "error": "limit_not_found",
            }

        self._usage[limit_id].append(
            time.time(),
        )

        return {
            "limit_id": limit_id,
            "recorded": True,
        }

    def get_backoff_time(
        self,
        limit_id: str,
    ) -> dict[str, Any]:
        """Geri çekilme süresi hesaplar.

        Args:
            limit_id: Limit ID.

        Returns:
            Geri çekilme bilgisi.
        """
        lim = self._limits.get(limit_id)
        if not lim:
            return {
                "error": "limit_not_found",
            }

        now = time.time()
        window = lim["window_seconds"]
        timestamps = self._usage.get(
            limit_id, [],
        )

        if not timestamps:
            return {
                "limit_id": limit_id,
                "backoff_seconds": 0,
                "strategy": "none",
            }

        # En eski kaydın süresi dolana kadar
        oldest_in_window = [
            t for t in timestamps
            if now - t < window
        ]

        if (
            len(oldest_in_window)
            >= lim["max_requests"]
        ):
            earliest = min(oldest_in_window)
            wait = window - (now - earliest)
            return {
                "limit_id": limit_id,
                "backoff_seconds": round(
                    max(0, wait), 2,
                ),
                "strategy": "wait_for_window",
            }

        return {
            "limit_id": limit_id,
            "backoff_seconds": 0,
            "strategy": "none",
        }

    def get_quota_status(
        self,
        limit_id: str,
    ) -> dict[str, Any]:
        """Kota durumu getirir.

        Args:
            limit_id: Limit ID.

        Returns:
            Kota bilgisi.
        """
        lim = self._limits.get(limit_id)
        if not lim:
            return {
                "error": "limit_not_found",
            }

        now = time.time()
        window = lim["window_seconds"]
        max_req = lim["max_requests"]

        active = [
            t for t in self._usage.get(
                limit_id, [],
            )
            if now - t < window
        ]
        used = len(active)
        pct = round(
            used / max(max_req, 1) * 100, 1,
        )

        return {
            "limit_id": limit_id,
            "name": lim["name"],
            "used": used,
            "max": max_req,
            "remaining": max(0, max_req - used),
            "usage_percent": pct,
        }

    def list_limits(
        self,
        limit_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Limitleri listeler.

        Args:
            limit_type: Tip filtresi.

        Returns:
            Limit listesi.
        """
        results = []
        for lim in self._limits.values():
            if limit_type and (
                lim["limit_type"] != limit_type
            ):
                continue
            results.append({
                "limit_id": lim["limit_id"],
                "name": lim["name"],
                "max_requests": lim[
                    "max_requests"
                ],
                "limit_type": lim["limit_type"],
            })
        return results

    @property
    def limit_count(self) -> int:
        """Limit sayısı."""
        return self._stats["limits_defined"]

    @property
    def blocked_count(self) -> int:
        """Engellenen sayısı."""
        return self._stats["blocked"]
