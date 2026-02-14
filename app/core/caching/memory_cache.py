"""ATLAS Bellek Onbellegi modulu.

In-memory depolama, boyut limiti,
tahliye politikasi, is parcacigi
guvenligi ve sure asimi.
"""

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


class MemoryCache:
    """Bellek onbellegi.

    Thread-safe in-memory onbellek
    saglar.

    Attributes:
        _data: Veri deposu.
        _lock: Thread kilidi.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 300,
    ) -> None:
        """Bellek onbellegini baslatir.

        Args:
            max_size: Maks girdi sayisi.
            default_ttl: Varsayilan TTL.
        """
        self._data: dict[
            str, dict[str, Any]
        ] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

        logger.info("MemoryCache baslatildi")

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Deger getirir.

        Args:
            key: Anahtar.
            default: Varsayilan.

        Returns:
            Deger veya varsayilan.
        """
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                self._misses += 1
                return default

            # TTL kontrolu
            if entry["expires_at"] > 0:
                if time.time() > entry["expires_at"]:
                    del self._data[key]
                    self._misses += 1
                    return default

            entry["hits"] += 1
            entry["last_access"] = time.time()
            self._hits += 1
            return entry["value"]

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Deger yazar.

        Args:
            key: Anahtar.
            value: Deger.
            ttl: Yasam suresi.
        """
        with self._lock:
            if (
                key not in self._data
                and len(self._data)
                >= self._max_size
            ):
                self._evict_one()

            actual_ttl = (
                ttl if ttl is not None
                else self._default_ttl
            )
            expires = (
                time.time() + actual_ttl
                if actual_ttl > 0
                else 0
            )

            self._data[key] = {
                "value": value,
                "hits": 0,
                "created_at": time.time(),
                "last_access": time.time(),
                "expires_at": expires,
            }

    def delete(self, key: str) -> bool:
        """Siler.

        Args:
            key: Anahtar.

        Returns:
            Basarili ise True.
        """
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def clear(self) -> int:
        """Tumu temizler.

        Returns:
            Silinen girdi sayisi.
        """
        with self._lock:
            count = len(self._data)
            self._data.clear()
            return count

    def exists(self, key: str) -> bool:
        """Var mi kontrol eder.

        Args:
            key: Anahtar.

        Returns:
            Varsa True.
        """
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                return False
            if entry["expires_at"] > 0:
                if time.time() > entry["expires_at"]:
                    del self._data[key]
                    return False
            return True

    def get_many(
        self,
        keys: list[str],
    ) -> dict[str, Any]:
        """Birden fazla deger getirir.

        Args:
            keys: Anahtar listesi.

        Returns:
            Anahtar-deger cifti.
        """
        result: dict[str, Any] = {}
        for key in keys:
            val = self.get(key)
            if val is not None:
                result[key] = val
        return result

    def set_many(
        self,
        entries: dict[str, Any],
        ttl: int | None = None,
    ) -> int:
        """Birden fazla deger yazar.

        Args:
            entries: Anahtar-deger cifti.
            ttl: Yasam suresi.

        Returns:
            Yazilan girdi sayisi.
        """
        count = 0
        for key, value in entries.items():
            self.set(key, value, ttl)
            count += 1
        return count

    def cleanup_expired(self) -> int:
        """Suresi dolanlari temizler.

        Returns:
            Temizlenen girdi sayisi.
        """
        with self._lock:
            now = time.time()
            expired = [
                k for k, v in self._data.items()
                if v["expires_at"] > 0
                and now > v["expires_at"]
            ]
            for k in expired:
                del self._data[k]
            return len(expired)

    def _evict_one(self) -> None:
        """Bir girdi tahliye eder (LRU)."""
        if not self._data:
            return

        oldest_key = min(
            self._data,
            key=lambda k: (
                self._data[k]["last_access"]
            ),
        )
        del self._data[oldest_key]

    def get_stats(self) -> dict[str, Any]:
        """Istatistik getirir.

        Returns:
            Istatistik.
        """
        total = self._hits + self._misses
        return {
            "size": len(self._data),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(
                self._hits / max(1, total), 3,
            ),
        }

    @property
    def size(self) -> int:
        """Girdi sayisi."""
        return len(self._data)

    @property
    def hit_count(self) -> int:
        """Isabet sayisi."""
        return self._hits

    @property
    def miss_count(self) -> int:
        """Iskalanma sayisi."""
        return self._misses
