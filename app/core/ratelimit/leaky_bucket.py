"""ATLAS Sizdiran Kova modulu.

Sabit hizda cikis, kuyruk yonetimi,
taşma, yumusatma, gecikme hesaplama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LeakyBucket:
    """Sizdiran kova algoritmasi.

    Istekleri sabit hizda isler,
    fazlasini kuyruklar veya reddeder.

    Attributes:
        _buckets: Kova kayitlari.
    """

    def __init__(
        self,
        default_capacity: int = 100,
        default_leak_rate: float = 10.0,
    ) -> None:
        """Sizdiran kovayi baslatir.

        Args:
            default_capacity: Varsayilan kuyruk kapasitesi.
            default_leak_rate: Varsayilan sizinti hizi (istek/sn).
        """
        self._buckets: dict[
            str, dict[str, Any]
        ] = {}
        self._default_capacity = default_capacity
        self._default_leak_rate = default_leak_rate
        self._stats = {
            "accepted": 0,
            "leaked": 0,
            "overflowed": 0,
        }

        logger.info(
            "LeakyBucket baslatildi",
        )

    def create_bucket(
        self,
        key: str,
        capacity: int | None = None,
        leak_rate: float | None = None,
    ) -> dict[str, Any]:
        """Kova olusturur.

        Args:
            key: Kova anahtari.
            capacity: Kuyruk kapasitesi.
            leak_rate: Sizinti hizi.

        Returns:
            Kova bilgisi.
        """
        cap = capacity or self._default_capacity
        rate = leak_rate or self._default_leak_rate

        self._buckets[key] = {
            "key": key,
            "capacity": cap,
            "leak_rate": rate,
            "queue_size": 0.0,
            "last_leak": time.time(),
            "total_accepted": 0,
            "total_leaked": 0,
            "created_at": time.time(),
        }

        return {
            "key": key,
            "capacity": cap,
            "leak_rate": rate,
            "status": "created",
        }

    def add(
        self,
        key: str,
        count: int = 1,
    ) -> dict[str, Any]:
        """Kovaya istek ekler.

        Args:
            key: Kova anahtari.
            count: Eklenecek istek sayisi.

        Returns:
            Ekleme sonucu.
        """
        bucket = self._buckets.get(key)
        if not bucket:
            return {
                "accepted": False,
                "reason": "bucket_not_found",
            }

        self._leak(key)

        remaining_cap = (
            bucket["capacity"] - bucket["queue_size"]
        )

        if count <= remaining_cap:
            bucket["queue_size"] += count
            bucket["total_accepted"] += count
            self._stats["accepted"] += count

            delay = self._calc_delay(key, count)

            return {
                "accepted": True,
                "queue_size": int(
                    bucket["queue_size"],
                ),
                "capacity": bucket["capacity"],
                "delay": round(delay, 3),
            }

        self._stats["overflowed"] += 1

        return {
            "accepted": False,
            "reason": "overflow",
            "queue_size": int(
                bucket["queue_size"],
            ),
            "capacity": bucket["capacity"],
        }

    def leak(
        self,
        key: str,
    ) -> dict[str, Any]:
        """Kovayi sizdirir (dis cagriya acik).

        Args:
            key: Kova anahtari.

        Returns:
            Sizinti sonucu.
        """
        bucket = self._buckets.get(key)
        if not bucket:
            return {"error": "bucket_not_found"}

        leaked = self._leak(key)

        return {
            "key": key,
            "leaked": leaked,
            "queue_size": int(
                bucket["queue_size"],
            ),
        }

    def get_delay(
        self,
        key: str,
        count: int = 1,
    ) -> float:
        """Bekleme suresini hesaplar.

        Args:
            key: Kova anahtari.
            count: Istek sayisi.

        Returns:
            Bekleme suresi (sn).
        """
        bucket = self._buckets.get(key)
        if not bucket:
            return 0

        self._leak(key)
        return self._calc_delay(key, count)

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
        self._leak(key)
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

        bucket["queue_size"] = 0.0
        bucket["last_leak"] = time.time()

        return {
            "key": key,
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
        leak_rate: float | None = None,
        capacity: int | None = None,
    ) -> dict[str, Any]:
        """Kova ayarlarini gunceller.

        Args:
            key: Kova anahtari.
            leak_rate: Yeni sizinti hizi.
            capacity: Yeni kapasite.

        Returns:
            Guncelleme sonucu.
        """
        bucket = self._buckets.get(key)
        if not bucket:
            return {"error": "bucket_not_found"}

        if leak_rate is not None:
            bucket["leak_rate"] = leak_rate
        if capacity is not None:
            bucket["capacity"] = capacity

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
            self._leak(key)
        items = list(self._buckets.values())
        return items[-limit:]

    def _leak(self, key: str) -> int:
        """Kovayi sizdirir.

        Args:
            key: Kova anahtari.

        Returns:
            Sizdirilan istek sayisi.
        """
        bucket = self._buckets[key]
        now = time.time()
        elapsed = now - bucket["last_leak"]
        leaked = elapsed * bucket["leak_rate"]

        if leaked > 0:
            actual_leaked = min(
                leaked, bucket["queue_size"],
            )
            bucket["queue_size"] = max(
                bucket["queue_size"] - leaked, 0,
            )
            bucket["last_leak"] = now
            int_leaked = int(actual_leaked)
            bucket["total_leaked"] += int_leaked
            self._stats["leaked"] += int_leaked
            return int_leaked

        return 0

    def _calc_delay(
        self,
        key: str,
        count: int,
    ) -> float:
        """Gecikme hesaplar.

        Args:
            key: Kova anahtari.
            count: Istek sayisi.

        Returns:
            Gecikme suresi (sn).
        """
        bucket = self._buckets[key]
        if bucket["leak_rate"] <= 0:
            return 0
        return (
            (bucket["queue_size"] + count - 1)
            / bucket["leak_rate"]
        )

    @property
    def bucket_count(self) -> int:
        """Kova sayisi."""
        return len(self._buckets)

    @property
    def accepted_count(self) -> int:
        """Kabul edilen sayisi."""
        return self._stats["accepted"]

    @property
    def overflow_count(self) -> int:
        """Tasmis sayisi."""
        return self._stats["overflowed"]
