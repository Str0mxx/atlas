"""ATLAS Token Kovasi modulu.

Token uretimi, tuketimi, patlama
yonetimi, dolum hizi, kapasite limiti.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token kovasi algoritması.

    Sabit hizla token uretir, istek basina
    token tuketir.

    Attributes:
        _buckets: Kova kayitlari.
    """

    def __init__(
        self,
        default_capacity: int = 100,
        default_refill_rate: float = 10.0,
        burst_multiplier: float = 1.5,
    ) -> None:
        """Token kovasini baslatir.

        Args:
            default_capacity: Varsayilan kapasite.
            default_refill_rate: Varsayilan dolum hizi (token/sn).
            burst_multiplier: Patlama carpani.
        """
        self._buckets: dict[
            str, dict[str, Any]
        ] = {}
        self._default_capacity = default_capacity
        self._default_refill_rate = default_refill_rate
        self._burst_multiplier = burst_multiplier
        self._stats = {
            "allowed": 0,
            "rejected": 0,
            "tokens_consumed": 0,
        }

        logger.info(
            "TokenBucket baslatildi",
        )

    def create_bucket(
        self,
        key: str,
        capacity: int | None = None,
        refill_rate: float | None = None,
        burst_capacity: int | None = None,
    ) -> dict[str, Any]:
        """Kova olusturur.

        Args:
            key: Kova anahtari.
            capacity: Kapasite.
            refill_rate: Dolum hizi.
            burst_capacity: Patlama kapasitesi.

        Returns:
            Kova bilgisi.
        """
        cap = capacity or self._default_capacity
        rate = refill_rate or self._default_refill_rate
        burst = burst_capacity or int(
            cap * self._burst_multiplier,
        )

        self._buckets[key] = {
            "key": key,
            "capacity": cap,
            "burst_capacity": burst,
            "tokens": float(cap),
            "refill_rate": rate,
            "last_refill": time.time(),
            "created_at": time.time(),
        }

        return {
            "key": key,
            "capacity": cap,
            "burst_capacity": burst,
            "status": "created",
        }

    def consume(
        self,
        key: str,
        tokens: int = 1,
    ) -> dict[str, Any]:
        """Token tuketir.

        Args:
            key: Kova anahtari.
            tokens: Tuketilecek token sayisi.

        Returns:
            Tuketim sonucu.
        """
        bucket = self._buckets.get(key)
        if not bucket:
            return {
                "allowed": False,
                "reason": "bucket_not_found",
            }

        self._refill(key)

        if bucket["tokens"] >= tokens:
            bucket["tokens"] -= tokens
            self._stats["allowed"] += 1
            self._stats["tokens_consumed"] += tokens

            return {
                "allowed": True,
                "remaining": int(bucket["tokens"]),
                "limit": bucket["capacity"],
            }

        self._stats["rejected"] += 1
        wait_time = (
            (tokens - bucket["tokens"])
            / bucket["refill_rate"]
        )

        return {
            "allowed": False,
            "reason": "insufficient_tokens",
            "remaining": int(bucket["tokens"]),
            "retry_after": round(wait_time, 2),
        }

    def consume_burst(
        self,
        key: str,
        tokens: int = 1,
    ) -> dict[str, Any]:
        """Patlama tuketimi (burst kapasite kullanir).

        Args:
            key: Kova anahtari.
            tokens: Tuketilecek token sayisi.

        Returns:
            Tuketim sonucu.
        """
        bucket = self._buckets.get(key)
        if not bucket:
            return {
                "allowed": False,
                "reason": "bucket_not_found",
            }

        self._refill(key)

        if bucket["tokens"] >= tokens:
            bucket["tokens"] -= tokens
            self._stats["allowed"] += 1
            self._stats["tokens_consumed"] += tokens
            return {
                "allowed": True,
                "remaining": int(bucket["tokens"]),
                "burst": True,
            }

        self._stats["rejected"] += 1
        return {
            "allowed": False,
            "reason": "burst_exceeded",
            "remaining": int(bucket["tokens"]),
        }

    def get_bucket(
        self,
        key: str,
    ) -> dict[str, Any] | None:
        """Kova bilgisi getirir.

        Args:
            key: Kova anahtari.

        Returns:
            Kova bilgisi veya None.
        """
        bucket = self._buckets.get(key)
        if not bucket:
            return None
        self._refill(key)
        return dict(bucket)

    def reset_bucket(
        self,
        key: str,
    ) -> dict[str, Any]:
        """Kovayi sifirlar.

        Args:
            key: Kova anahtari.

        Returns:
            Sifirlama sonucu.
        """
        bucket = self._buckets.get(key)
        if not bucket:
            return {"error": "bucket_not_found"}

        bucket["tokens"] = float(
            bucket["capacity"],
        )
        bucket["last_refill"] = time.time()

        return {
            "key": key,
            "tokens": bucket["capacity"],
            "status": "reset",
        }

    def delete_bucket(
        self,
        key: str,
    ) -> bool:
        """Kovayi siler.

        Args:
            key: Kova anahtari.

        Returns:
            Basarili mi.
        """
        if key not in self._buckets:
            return False
        del self._buckets[key]
        return True

    def update_rate(
        self,
        key: str,
        refill_rate: float | None = None,
        capacity: int | None = None,
    ) -> dict[str, Any]:
        """Kova ayarlarini gunceller.

        Args:
            key: Kova anahtari.
            refill_rate: Yeni dolum hizi.
            capacity: Yeni kapasite.

        Returns:
            Guncelleme sonucu.
        """
        bucket = self._buckets.get(key)
        if not bucket:
            return {"error": "bucket_not_found"}

        if refill_rate is not None:
            bucket["refill_rate"] = refill_rate
        if capacity is not None:
            bucket["capacity"] = capacity
            bucket["burst_capacity"] = int(
                capacity * self._burst_multiplier,
            )

        return {
            "key": key,
            "status": "updated",
        }

    def list_buckets(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Kovalari listeler.

        Args:
            limit: Limit.

        Returns:
            Kova listesi.
        """
        for key in self._buckets:
            self._refill(key)
        items = list(self._buckets.values())
        return items[-limit:]

    def _refill(self, key: str) -> None:
        """Kovayi doldurur.

        Args:
            key: Kova anahtari.
        """
        bucket = self._buckets.get(key)
        if not bucket:
            return

        now = time.time()
        elapsed = now - bucket["last_refill"]
        new_tokens = elapsed * bucket["refill_rate"]

        if new_tokens > 0:
            bucket["tokens"] = min(
                bucket["tokens"] + new_tokens,
                float(bucket["burst_capacity"]),
            )
            bucket["last_refill"] = now

    @property
    def bucket_count(self) -> int:
        """Kova sayisi."""
        return len(self._buckets)

    @property
    def allowed_count(self) -> int:
        """Izin verilen istek sayisi."""
        return self._stats["allowed"]

    @property
    def rejected_count(self) -> int:
        """Reddedilen istek sayisi."""
        return self._stats["rejected"]
