"""ATLAS Onbellek Yoneticisi modulu.

Cok katmanli onbellekleme,
strateji yonetimi, gecersiz kilma,
isitma ve isabet takibi.
"""

import logging
import time
from typing import Any

from app.models.caching import (
    CacheLayer,
    CacheStrategy,
)

logger = logging.getLogger(__name__)


class CacheManager:
    """Onbellek yoneticisi.

    Cok katmanli onbellek sistemi
    yonetir ve koordine eder.

    Attributes:
        _stores: Katman depolari.
        _stats: Istatistikler.
    """

    def __init__(
        self,
        default_ttl: int = 300,
        strategy: CacheStrategy = CacheStrategy.LRU,
    ) -> None:
        """Onbellek yoneticisini baslatir.

        Args:
            default_ttl: Varsayilan TTL (sn).
            strategy: Onbellek stratejisi.
        """
        self._stores: dict[
            str, dict[str, Any]
        ] = {}
        self._ttls: dict[str, float] = {}
        self._access_times: dict[
            str, float
        ] = {}
        self._access_counts: dict[str, int] = {}
        self._default_ttl = default_ttl
        self._strategy = strategy
        self._hits = 0
        self._misses = 0
        self._max_size = 10000
        self._warm_keys: list[str] = []

        logger.info("CacheManager baslatildi")

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Onbellekten deger getirir.

        Args:
            key: Anahtar.
            default: Varsayilan deger.

        Returns:
            Deger veya varsayilan.
        """
        if key in self._stores:
            # TTL kontrolu
            expiry = self._ttls.get(key, 0)
            if expiry and time.time() > expiry:
                self._remove(key)
                self._misses += 1
                return default

            self._hits += 1
            self._access_times[key] = time.time()
            self._access_counts[key] = (
                self._access_counts.get(key, 0) + 1
            )
            return self._stores[key]["value"]

        self._misses += 1
        return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        layer: str = "memory",
    ) -> None:
        """Onbellege deger yazar.

        Args:
            key: Anahtar.
            value: Deger.
            ttl: Yasam suresi.
            layer: Katman.
        """
        # Boyut limiti
        if (
            key not in self._stores
            and len(self._stores) >= self._max_size
        ):
            self._evict()

        actual_ttl = ttl if ttl is not None else self._default_ttl
        self._stores[key] = {
            "value": value,
            "layer": layer,
            "set_at": time.time(),
        }
        if actual_ttl > 0:
            self._ttls[key] = (
                time.time() + actual_ttl
            )
        self._access_times[key] = time.time()
        self._access_counts[key] = (
            self._access_counts.get(key, 0)
        )

    def delete(self, key: str) -> bool:
        """Onbellekten siler.

        Args:
            key: Anahtar.

        Returns:
            Basarili ise True.
        """
        if key in self._stores:
            self._remove(key)
            return True
        return False

    def invalidate(
        self,
        pattern: str = "",
    ) -> int:
        """Onbellegi gecersiz kilar.

        Args:
            pattern: Anahtar deseni.

        Returns:
            Silinen anahtar sayisi.
        """
        if not pattern:
            count = len(self._stores)
            self._stores.clear()
            self._ttls.clear()
            self._access_times.clear()
            self._access_counts.clear()
            return count

        keys_to_remove = [
            k for k in self._stores
            if pattern in k
        ]
        for k in keys_to_remove:
            self._remove(k)
        return len(keys_to_remove)

    def warm(
        self,
        entries: dict[str, Any],
        ttl: int | None = None,
    ) -> int:
        """Onbellegi isitir.

        Args:
            entries: Anahtar-deger cifti.
            ttl: Yasam suresi.

        Returns:
            Eklenen anahtar sayisi.
        """
        count = 0
        for key, value in entries.items():
            self.set(key, value, ttl)
            self._warm_keys.append(key)
            count += 1
        return count

    def exists(self, key: str) -> bool:
        """Anahtar var mi kontrol eder.

        Args:
            key: Anahtar.

        Returns:
            Varsa True.
        """
        if key not in self._stores:
            return False

        expiry = self._ttls.get(key, 0)
        if expiry and time.time() > expiry:
            self._remove(key)
            return False
        return True

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri getirir.

        Returns:
            Istatistik bilgisi.
        """
        total = self._hits + self._misses
        hit_rate = (
            round(self._hits / max(1, total), 3)
        )
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": hit_rate,
            "entries": len(self._stores),
            "strategy": self._strategy.value,
        }

    def _evict(self) -> None:
        """Tahliye politikasi uygular."""
        if not self._stores:
            return

        if self._strategy == CacheStrategy.LRU:
            oldest_key = min(
                self._access_times,
                key=self._access_times.get,
            )
            self._remove(oldest_key)
        elif self._strategy == CacheStrategy.LFU:
            least_key = min(
                self._access_counts,
                key=self._access_counts.get,
            )
            self._remove(least_key)
        elif self._strategy == CacheStrategy.FIFO:
            first_key = next(iter(self._stores))
            self._remove(first_key)
        else:
            # TTL: en yakin suresi dolacak
            if self._ttls:
                nearest = min(
                    self._ttls,
                    key=self._ttls.get,
                )
                self._remove(nearest)

    def _remove(self, key: str) -> None:
        """Anahtari kaldirir.

        Args:
            key: Anahtar.
        """
        self._stores.pop(key, None)
        self._ttls.pop(key, None)
        self._access_times.pop(key, None)
        self._access_counts.pop(key, None)

    @property
    def size(self) -> int:
        """Onbellek boyutu."""
        return len(self._stores)

    @property
    def hit_count(self) -> int:
        """Isabet sayisi."""
        return self._hits

    @property
    def miss_count(self) -> int:
        """Iskalanma sayisi."""
        return self._misses
