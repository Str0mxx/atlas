"""ATLAS Yanit Onbellegi modulu.

Akilli onbellekleme, TTL yonetimi,
gecersiz kilma, isinma ve vuruş orani.
"""

import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from app.models.integration import CacheEntry

logger = logging.getLogger(__name__)


class ResponseCache:
    """Yanit onbellegi.

    API yanitlarini onbellegeler ve
    performansi optimize eder.

    Attributes:
        _cache: Onbellek girdileri.
        _invalidation_rules: Gecersiz kilma kurallari.
        _stats: Istatistikler.
        _default_ttl: Varsayilan TTL (sn).
    """

    def __init__(self, default_ttl: int = 300) -> None:
        """Yanit onbellegini baslatir.

        Args:
            default_ttl: Varsayilan TTL (sn).
        """
        self._cache: dict[str, CacheEntry] = {}
        self._invalidation_rules: dict[str, dict[str, Any]] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }
        self._default_ttl = max(1, default_ttl)

        logger.info(
            "ResponseCache baslatildi (ttl=%d sn)",
            self._default_ttl,
        )

    def get(
        self,
        key: str,
        service: str = "",
    ) -> dict[str, Any] | None:
        """Onbellekten veri getirir.

        Args:
            key: Anahtar.
            service: Servis adi.

        Returns:
            Veri veya None.
        """
        cache_key = self._make_key(key, service)
        entry = self._cache.get(cache_key)

        if not entry:
            self._stats["misses"] += 1
            return None

        # TTL kontrolu
        now = datetime.now(timezone.utc)
        if now > entry.expires_at:
            del self._cache[cache_key]
            self._stats["misses"] += 1
            self._stats["evictions"] += 1
            return None

        entry.hit_count += 1
        self._stats["hits"] += 1
        return entry.data

    def set(
        self,
        key: str,
        data: dict[str, Any],
        service: str = "",
        ttl: int | None = None,
    ) -> CacheEntry:
        """Onbellege veri yazar.

        Args:
            key: Anahtar.
            data: Veri.
            service: Servis adi.
            ttl: TTL (sn).

        Returns:
            Onbellek girdisi.
        """
        cache_key = self._make_key(key, service)
        ttl_seconds = ttl or self._default_ttl
        now = datetime.now(timezone.utc)

        entry = CacheEntry(
            cache_key=cache_key,
            service=service,
            data=data,
            ttl_seconds=ttl_seconds,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        self._cache[cache_key] = entry

        return entry

    def invalidate(
        self,
        key: str,
        service: str = "",
    ) -> bool:
        """Onbellek girdisini gecersiz kilar.

        Args:
            key: Anahtar.
            service: Servis adi.

        Returns:
            Silindi ise True.
        """
        cache_key = self._make_key(key, service)
        if cache_key in self._cache:
            del self._cache[cache_key]
            self._stats["evictions"] += 1
            return True
        return False

    def invalidate_service(
        self,
        service: str,
    ) -> int:
        """Servisin tum onbellegini temizler.

        Args:
            service: Servis adi.

        Returns:
            Temizlenen girdi sayisi.
        """
        keys_to_remove = [
            k for k, v in self._cache.items()
            if v.service == service
        ]
        for key in keys_to_remove:
            del self._cache[key]

        self._stats["evictions"] += len(keys_to_remove)
        return len(keys_to_remove)

    def add_invalidation_rule(
        self,
        pattern: str,
        trigger: str,
        service: str = "",
    ) -> dict[str, Any]:
        """Gecersiz kilma kurali ekler.

        Args:
            pattern: Anahtar deseni.
            trigger: Tetikleyici olay.
            service: Servis adi.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "pattern": pattern,
            "trigger": trigger,
            "service": service,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._invalidation_rules[pattern] = rule
        return rule

    def warm_cache(
        self,
        entries: list[dict[str, Any]],
    ) -> int:
        """Onbellegi isindirir.

        Args:
            entries: Girdi listesi (key, data, service, ttl).

        Returns:
            Eklenen girdi sayisi.
        """
        added = 0
        for entry in entries:
            key = entry.get("key", "")
            data = entry.get("data", {})
            service = entry.get("service", "")
            ttl = entry.get("ttl")

            if key and data:
                self.set(key, data, service, ttl)
                added += 1

        logger.info("Onbellek isindirildi: %d girdi", added)
        return added

    def cleanup_expired(self) -> int:
        """Suresi dolanlari temizler.

        Returns:
            Temizlenen sayisi.
        """
        now = datetime.now(timezone.utc)
        expired = [
            k for k, v in self._cache.items()
            if now > v.expires_at
        ]
        for key in expired:
            del self._cache[key]

        self._stats["evictions"] += len(expired)
        return len(expired)

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri getirir.

        Returns:
            Istatistik sozlugu.
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (
            self._stats["hits"] / total if total > 0 else 0.0
        )
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "hit_rate": round(hit_rate, 3),
            "total_entries": len(self._cache),
        }

    def _make_key(self, key: str, service: str) -> str:
        """Onbellek anahtari uretir.

        Args:
            key: Ham anahtar.
            service: Servis adi.

        Returns:
            Hash anahtar.
        """
        raw = f"{service}:{key}" if service else key
        return hashlib.md5(raw.encode()).hexdigest()

    @property
    def entry_count(self) -> int:
        """Girdi sayisi."""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Vurus orani."""
        total = self._stats["hits"] + self._stats["misses"]
        return round(self._stats["hits"] / total, 3) if total > 0 else 0.0

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._invalidation_rules)
