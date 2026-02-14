"""ATLAS Bellek Yoneticisi modulu.

Bellek izleme, cop toplama tetikleme,
bellek limitleri, sizinti tespiti
ve onbellek tasirma.
"""

import logging
from typing import Any

from app.models.resource import ResourceStatus

logger = logging.getLogger(__name__)


class MemoryManager:
    """Bellek yoneticisi.

    Bellek kaynaklarini izler ve yonetir.

    Attributes:
        _allocations: Tahsis kayitlari.
        _usage_history: Kullanim gecmisi.
        _threshold: Uyari esigi.
        _total_mb: Toplam bellek (MB).
        _used_mb: Kullanilan bellek (MB).
    """

    def __init__(
        self,
        threshold: float = 0.8,
        total_mb: int = 8192,
    ) -> None:
        """Bellek yoneticisini baslatir.

        Args:
            threshold: Uyari esigi.
            total_mb: Toplam bellek (MB).
        """
        self._allocations: dict[str, dict[str, Any]] = {}
        self._usage_history: list[float] = []
        self._threshold = max(0.1, min(1.0, threshold))
        self._total_mb = max(1, total_mb)
        self._used_mb = 0.0
        self._gc_triggers = 0
        self._leaks_detected: list[dict[str, Any]] = []
        self._cache: dict[str, dict[str, Any]] = {}

        logger.info(
            "MemoryManager baslatildi (total=%dMB, threshold=%.0f%%)",
            self._total_mb, self._threshold * 100,
        )

    def record_usage(self, used_mb: float) -> ResourceStatus:
        """Bellek kullanimini kaydeder.

        Args:
            used_mb: Kullanilan bellek (MB).

        Returns:
            Kaynak durumu.
        """
        self._used_mb = max(0.0, min(float(self._total_mb), used_mb))
        ratio = self._used_mb / self._total_mb
        self._usage_history.append(ratio)

        if ratio >= 0.95:
            return ResourceStatus.CRITICAL
        if ratio >= self._threshold:
            return ResourceStatus.WARNING
        return ResourceStatus.NORMAL

    def allocate(
        self,
        name: str,
        size_mb: float,
    ) -> bool:
        """Bellek tahsis eder.

        Args:
            name: Tahsis adi.
            size_mb: Boyut (MB).

        Returns:
            Basarili ise True.
        """
        if self._used_mb + size_mb > self._total_mb:
            return False

        self._allocations[name] = {
            "name": name,
            "size_mb": size_mb,
        }
        self._used_mb += size_mb
        return True

    def release(self, name: str) -> bool:
        """Bellek serbest birakir.

        Args:
            name: Tahsis adi.

        Returns:
            Basarili ise True.
        """
        alloc = self._allocations.get(name)
        if not alloc:
            return False
        self._used_mb = max(0.0, self._used_mb - alloc["size_mb"])
        del self._allocations[name]
        return True

    def trigger_gc(self) -> dict[str, Any]:
        """Cop toplama tetikler.

        Returns:
            GC sonucu.
        """
        self._gc_triggers += 1
        # Simulasyon: kucuk tahsisleri temizle
        freed = 0.0
        to_remove = [
            n for n, a in self._allocations.items()
            if a["size_mb"] < 1.0
        ]
        for name in to_remove:
            freed += self._allocations[name]["size_mb"]
            del self._allocations[name]

        self._used_mb = max(0.0, self._used_mb - freed)
        return {
            "freed_mb": freed,
            "removed_count": len(to_remove),
            "gc_count": self._gc_triggers,
        }

    def set_limit(
        self,
        name: str,
        max_mb: float,
    ) -> bool:
        """Bellek limiti ayarlar.

        Args:
            name: Tahsis adi.
            max_mb: Maks bellek (MB).

        Returns:
            Basarili ise True.
        """
        alloc = self._allocations.get(name)
        if not alloc:
            return False
        alloc["limit_mb"] = max_mb
        return True

    def detect_leaks(self) -> list[dict[str, Any]]:
        """Bellek sizintisi tespit eder.

        Returns:
            Tespit edilen sizintilar.
        """
        leaks: list[dict[str, Any]] = []
        # Buyuk tahsisler potansiyel sizinti
        for name, alloc in self._allocations.items():
            limit = alloc.get("limit_mb", float("inf"))
            if alloc["size_mb"] > limit:
                leak = {
                    "name": name,
                    "size_mb": alloc["size_mb"],
                    "limit_mb": limit,
                    "excess_mb": alloc["size_mb"] - limit,
                }
                leaks.append(leak)
                self._leaks_detected.append(leak)
        return leaks

    def cache_put(
        self,
        key: str,
        size_mb: float,
        priority: int = 5,
    ) -> bool:
        """Onbellege ekler.

        Args:
            key: Anahtar.
            size_mb: Boyut.
            priority: Oncelik (1-10).

        Returns:
            Basarili ise True.
        """
        self._cache[key] = {
            "size_mb": size_mb,
            "priority": max(1, min(10, priority)),
            "hits": 0,
        }
        return True

    def cache_evict(
        self,
        target_mb: float = 0.0,
    ) -> int:
        """Dusuk oncelikli onbellek tasirma.

        Args:
            target_mb: Hedef serbest birakma.

        Returns:
            Tasirilan kayit sayisi.
        """
        if not self._cache:
            return 0

        sorted_cache = sorted(
            self._cache.items(),
            key=lambda x: (x[1]["priority"], x[1]["hits"]),
        )

        evicted = 0
        freed = 0.0
        for key, entry in sorted_cache:
            if target_mb > 0 and freed >= target_mb:
                break
            freed += entry["size_mb"]
            del self._cache[key]
            evicted += 1

            if target_mb <= 0:
                break  # Sadece bir tane tasir

        return evicted

    def get_usage_ratio(self) -> float:
        """Kullanim oranini getirir.

        Returns:
            Kullanim orani (0.0-1.0).
        """
        return self._used_mb / self._total_mb

    @property
    def used_mb(self) -> float:
        """Kullanilan bellek (MB)."""
        return self._used_mb

    @property
    def available_mb(self) -> float:
        """Kullanilabilir bellek (MB)."""
        return self._total_mb - self._used_mb

    @property
    def allocation_count(self) -> int:
        """Tahsis sayisi."""
        return len(self._allocations)

    @property
    def gc_count(self) -> int:
        """GC tetikleme sayisi."""
        return self._gc_triggers

    @property
    def leak_count(self) -> int:
        """Tespit edilen sizinti sayisi."""
        return len(self._leaks_detected)

    @property
    def cache_count(self) -> int:
        """Onbellek kaydi sayisi."""
        return len(self._cache)
