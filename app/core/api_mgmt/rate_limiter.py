"""ATLAS API Hiz Siniri modulu.

Token bucket, kayar pencere,
kullanici bazli, endpoint bazli
sinirlar ve burst yonetimi.
"""

import logging
import time
from typing import Any

from app.models.api_mgmt import RateLimitStrategy

logger = logging.getLogger(__name__)


class APIRateLimiter:
    """API hiz sinirlandirici.

    Farkli stratejilerle istek
    hizi sinirlar.

    Attributes:
        _buckets: Token bucket'lar.
        _windows: Kayar pencereler.
    """

    def __init__(
        self,
        default_limit: int = 100,
        window_seconds: int = 60,
    ) -> None:
        """Hiz sinirlandiriciyi baslatir.

        Args:
            default_limit: Varsayilan sinir.
            window_seconds: Pencere suresi.
        """
        self._default_limit = default_limit
        self._window_seconds = window_seconds
        self._buckets: dict[
            str, dict[str, Any]
        ] = {}
        self._windows: dict[
            str, list[float]
        ] = {}
        self._limits: dict[str, int] = {}
        self._user_limits: dict[str, int] = {}
        self._endpoint_limits: dict[
            str, int
        ] = {}

        logger.info(
            "APIRateLimiter baslatildi",
        )

    def check(
        self,
        key: str,
        cost: int = 1,
    ) -> dict[str, Any]:
        """Hiz sinirini kontrol eder.

        Args:
            key: Sinir anahtari.
            cost: Istek maliyeti.

        Returns:
            Kontrol sonucu.
        """
        limit = self._limits.get(
            key, self._default_limit,
        )

        # Kayar pencere kontrolu
        now = time.time()
        window = self._windows.get(key, [])

        # Eski kayitlari temizle
        cutoff = now - self._window_seconds
        window = [
            t for t in window if t > cutoff
        ]
        self._windows[key] = window

        remaining = limit - len(window)
        allowed = remaining >= cost

        if allowed:
            for _ in range(cost):
                window.append(now)

        return {
            "allowed": allowed,
            "limit": limit,
            "remaining": max(0, remaining - cost),
            "reset_at": cutoff + self._window_seconds,
        }

    def set_limit(
        self,
        key: str,
        limit: int,
    ) -> None:
        """Sinir ayarlar.

        Args:
            key: Sinir anahtari.
            limit: Sinir degeri.
        """
        self._limits[key] = limit

    def set_user_limit(
        self,
        user_id: str,
        limit: int,
    ) -> None:
        """Kullanici siniri ayarlar.

        Args:
            user_id: Kullanici ID.
            limit: Sinir degeri.
        """
        self._user_limits[user_id] = limit
        self._limits[f"user:{user_id}"] = limit

    def set_endpoint_limit(
        self,
        endpoint: str,
        limit: int,
    ) -> None:
        """Endpoint siniri ayarlar.

        Args:
            endpoint: Endpoint yolu.
            limit: Sinir degeri.
        """
        self._endpoint_limits[endpoint] = limit
        self._limits[
            f"endpoint:{endpoint}"
        ] = limit

    def check_user(
        self,
        user_id: str,
        cost: int = 1,
    ) -> dict[str, Any]:
        """Kullanici sinirini kontrol eder.

        Args:
            user_id: Kullanici ID.
            cost: Istek maliyeti.

        Returns:
            Kontrol sonucu.
        """
        return self.check(
            f"user:{user_id}", cost,
        )

    def check_endpoint(
        self,
        endpoint: str,
        cost: int = 1,
    ) -> dict[str, Any]:
        """Endpoint sinirini kontrol eder.

        Args:
            endpoint: Endpoint yolu.
            cost: Istek maliyeti.

        Returns:
            Kontrol sonucu.
        """
        return self.check(
            f"endpoint:{endpoint}", cost,
        )

    def init_token_bucket(
        self,
        key: str,
        capacity: int,
        refill_rate: float = 1.0,
    ) -> dict[str, Any]:
        """Token bucket baslatir.

        Args:
            key: Bucket anahtari.
            capacity: Kapasite.
            refill_rate: Dolum hizi (token/sn).

        Returns:
            Bucket bilgisi.
        """
        bucket = {
            "capacity": capacity,
            "tokens": capacity,
            "refill_rate": refill_rate,
            "last_refill": time.time(),
        }
        self._buckets[key] = bucket
        return bucket

    def consume_token(
        self,
        key: str,
        count: int = 1,
    ) -> dict[str, Any]:
        """Token tuketir.

        Args:
            key: Bucket anahtari.
            count: Token sayisi.

        Returns:
            Tuketim sonucu.
        """
        bucket = self._buckets.get(key)
        if not bucket:
            return {
                "allowed": False,
                "reason": "bucket_not_found",
            }

        # Refill
        now = time.time()
        elapsed = now - bucket["last_refill"]
        refill = elapsed * bucket["refill_rate"]
        bucket["tokens"] = min(
            bucket["capacity"],
            bucket["tokens"] + refill,
        )
        bucket["last_refill"] = now

        if bucket["tokens"] >= count:
            bucket["tokens"] -= count
            return {
                "allowed": True,
                "remaining": int(
                    bucket["tokens"],
                ),
            }

        return {
            "allowed": False,
            "remaining": int(bucket["tokens"]),
            "reason": "insufficient_tokens",
        }

    def reset(self, key: str) -> bool:
        """Siniri sifirlar.

        Args:
            key: Sinir anahtari.

        Returns:
            Basarili ise True.
        """
        if key in self._windows:
            self._windows[key] = []
            return True
        if key in self._buckets:
            self._buckets[key]["tokens"] = (
                self._buckets[key]["capacity"]
            )
            return True
        return False

    def get_status(
        self,
        key: str,
    ) -> dict[str, Any]:
        """Sinir durumunu getirir.

        Args:
            key: Sinir anahtari.

        Returns:
            Durum bilgisi.
        """
        limit = self._limits.get(
            key, self._default_limit,
        )
        window = self._windows.get(key, [])
        now = time.time()
        cutoff = now - self._window_seconds
        current = len(
            [t for t in window if t > cutoff],
        )

        return {
            "key": key,
            "limit": limit,
            "current": current,
            "remaining": max(0, limit - current),
        }

    @property
    def limit_count(self) -> int:
        """Sinir sayisi."""
        return len(self._limits)

    @property
    def bucket_count(self) -> int:
        """Bucket sayisi."""
        return len(self._buckets)

    @property
    def user_limit_count(self) -> int:
        """Kullanici siniri sayisi."""
        return len(self._user_limits)

    @property
    def endpoint_limit_count(self) -> int:
        """Endpoint siniri sayisi."""
        return len(self._endpoint_limits)
