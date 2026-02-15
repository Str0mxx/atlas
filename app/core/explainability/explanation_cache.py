"""ATLAS Aciklama Onbellegi modulu.

Aciklama onbellekleme, yeniden kullanim,
degisiklikte guncelleme, gecersiz kilma, performans.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ExplanationCache:
    """Aciklama onbellegi.

    Aciklamalari onbellekte tutar.

    Attributes:
        _cache: Onbellek deposu.
        _patterns: Yeniden kullanim kaliplari.
    """

    def __init__(
        self,
        default_ttl: int = 3600,
        max_size: int = 1000,
    ) -> None:
        """Aciklama onbellegini baslatir.

        Args:
            default_ttl: Varsayilan yasam suresi (sn).
            max_size: Maks boyut.
        """
        self._cache: dict[
            str, dict[str, Any]
        ] = {}
        self._patterns: dict[
            str, dict[str, Any]
        ] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
        }

        logger.info(
            "ExplanationCache baslatildi",
        )

    def get(
        self,
        key: str,
    ) -> dict[str, Any] | None:
        """Onbellekten getirir.

        Args:
            key: Anahtar.

        Returns:
            Onbellekteki veri veya None.
        """
        entry = self._cache.get(key)
        if not entry:
            self._stats["misses"] += 1
            return None

        # TTL kontrolu
        if (
            time.time() - entry["cached_at"]
            > entry["ttl"]
        ):
            del self._cache[key]
            self._stats["misses"] += 1
            return None

        entry["access_count"] += 1
        entry["last_accessed"] = time.time()
        self._stats["hits"] += 1

        return entry["data"]

    def set(
        self,
        key: str,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> dict[str, Any]:
        """Onbellege yazar.

        Args:
            key: Anahtar.
            data: Veri.
            ttl: Yasam suresi.

        Returns:
            Yazma bilgisi.
        """
        # Boyut kontrolu
        if (
            len(self._cache) >= self._max_size
            and key not in self._cache
        ):
            self._evict()

        self._cache[key] = {
            "data": dict(data),
            "ttl": ttl or self._default_ttl,
            "cached_at": time.time(),
            "last_accessed": time.time(),
            "access_count": 0,
        }
        self._stats["sets"] += 1

        return {
            "key": key,
            "cached": True,
            "ttl": ttl or self._default_ttl,
        }

    def invalidate(
        self,
        key: str,
    ) -> dict[str, Any]:
        """Onbellegi gecersiz kilar.

        Args:
            key: Anahtar.

        Returns:
            Gecersiz kilma bilgisi.
        """
        if key in self._cache:
            del self._cache[key]
            return {
                "key": key,
                "invalidated": True,
            }

        return {
            "key": key,
            "invalidated": False,
            "reason": "not_found",
        }

    def invalidate_pattern(
        self,
        pattern: str,
    ) -> dict[str, Any]:
        """Kaliba gore gecersiz kilar.

        Args:
            pattern: Anahtar kalibi.

        Returns:
            Gecersiz kilma bilgisi.
        """
        keys_to_remove = [
            k for k in self._cache
            if pattern in k
        ]

        for key in keys_to_remove:
            del self._cache[key]

        return {
            "pattern": pattern,
            "invalidated": len(keys_to_remove),
        }

    def update(
        self,
        key: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Onbellegi gunceller.

        Args:
            key: Anahtar.
            data: Yeni veri.

        Returns:
            Guncelleme bilgisi.
        """
        if key not in self._cache:
            return {
                "key": key,
                "updated": False,
                "reason": "not_found",
            }

        self._cache[key]["data"] = dict(data)
        self._cache[key][
            "last_accessed"
        ] = time.time()

        return {
            "key": key,
            "updated": True,
        }

    def register_pattern(
        self,
        pattern_name: str,
        key_template: str,
        ttl: int | None = None,
    ) -> dict[str, Any]:
        """Yeniden kullanim kalibi kaydeder.

        Args:
            pattern_name: Kalip adi.
            key_template: Anahtar sablonu.
            ttl: Yasam suresi.

        Returns:
            Kayit bilgisi.
        """
        self._patterns[pattern_name] = {
            "name": pattern_name,
            "key_template": key_template,
            "ttl": ttl or self._default_ttl,
            "usage_count": 0,
            "created_at": time.time(),
        }

        return {
            "pattern": pattern_name,
            "registered": True,
        }

    def get_by_pattern(
        self,
        pattern_name: str,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Kalip ile onbellekten getirir.

        Args:
            pattern_name: Kalip adi.
            **kwargs: Sablon parametreleri.

        Returns:
            Veri veya None.
        """
        pattern = self._patterns.get(
            pattern_name,
        )
        if not pattern:
            return None

        key = pattern["key_template"].format(
            **kwargs,
        )
        pattern["usage_count"] += 1

        return self.get(key)

    def _evict(self) -> None:
        """En az kullanilani cikarir."""
        if not self._cache:
            return

        lru_key = min(
            self._cache,
            key=lambda k: self._cache[k][
                "last_accessed"
            ],
        )
        del self._cache[lru_key]
        self._stats["evictions"] += 1

    def clear(self) -> dict[str, Any]:
        """Onbellegi temizler.

        Returns:
            Temizleme bilgisi.
        """
        count = len(self._cache)
        self._cache.clear()

        return {
            "cleared": count,
        }

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        total = (
            self._stats["hits"]
            + self._stats["misses"]
        )
        hit_rate = (
            self._stats["hits"] / total * 100
            if total > 0
            else 0.0
        )

        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": round(hit_rate, 1),
            "sets": self._stats["sets"],
            "evictions": self._stats[
                "evictions"
            ],
        }

    @property
    def size(self) -> int:
        """Onbellek boyutu."""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Hit orani."""
        total = (
            self._stats["hits"]
            + self._stats["misses"]
        )
        if total == 0:
            return 0.0
        return round(
            self._stats["hits"]
            / total * 100, 1,
        )
