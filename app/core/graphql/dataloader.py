"""ATLAS Veri Yukleyici modulu.

Toplu yukleme, onbellekleme,
N+1 onleme, istek tekrarsizlastirma
ve onbellek gecersiz kilma.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DataLoader:
    """Veri yukleyici.

    Veri erisimini toplar ve optimize eder.

    Attributes:
        _loaders: Kayitli yukleyiciler.
        _cache: Veri onbellegi.
    """

    def __init__(
        self,
        cache_enabled: bool = True,
    ) -> None:
        """Yukleyiciyi baslatir.

        Args:
            cache_enabled: Onbellek aktif mi.
        """
        self._cache_enabled = cache_enabled
        self._loaders: dict[
            str, Callable[[list[Any]], list[Any]]
        ] = {}
        self._cache: dict[
            str, dict[Any, Any]
        ] = {}
        self._pending: dict[
            str, list[Any]
        ] = {}
        self._stats = {
            "loads": 0,
            "batch_loads": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        logger.info(
            "DataLoader baslatildi: "
            "cache=%s",
            cache_enabled,
        )

    def register(
        self,
        name: str,
        batch_fn: Callable[
            [list[Any]], list[Any]
        ],
    ) -> dict[str, Any]:
        """Yukleyici kaydeder.

        Args:
            name: Yukleyici adi.
            batch_fn: Toplu yukleme fonksiyonu.

        Returns:
            Kayit bilgisi.
        """
        self._loaders[name] = batch_fn
        self._cache[name] = {}
        self._pending[name] = []

        return {"name": name, "status": "registered"}

    def load(
        self,
        name: str,
        key: Any,
    ) -> Any:
        """Tekli yukleme yapar.

        Args:
            name: Yukleyici adi.
            key: Anahtar.

        Returns:
            Yuklenen deger.
        """
        self._stats["loads"] += 1

        # Onbellek kontrolu
        if (
            self._cache_enabled
            and name in self._cache
        ):
            cached = self._cache[name].get(key)
            if cached is not None:
                self._stats["cache_hits"] += 1
                return cached

        self._stats["cache_misses"] += 1

        # Tekli yukleme - batch ile
        results = self.load_many(name, [key])
        return results[0] if results else None

    def load_many(
        self,
        name: str,
        keys: list[Any],
    ) -> list[Any]:
        """Toplu yukleme yapar.

        Args:
            name: Yukleyici adi.
            keys: Anahtarlar.

        Returns:
            Yuklenen degerler.
        """
        loader = self._loaders.get(name)
        if not loader:
            return [None] * len(keys)

        # Tekrarsizlastir
        unique_keys = list(dict.fromkeys(keys))

        # Onbellekten bul
        to_load: list[Any] = []
        cached_results: dict[Any, Any] = {}

        if self._cache_enabled:
            for k in unique_keys:
                cached = self._cache[name].get(k)
                if cached is not None:
                    cached_results[k] = cached
                    self._stats["cache_hits"] += 1
                else:
                    to_load.append(k)
                    self._stats["cache_misses"] += 1
        else:
            to_load = unique_keys

        # Toplu yukle
        if to_load:
            self._stats["batch_loads"] += 1
            try:
                loaded = loader(to_load)
                for k, v in zip(to_load, loaded):
                    cached_results[k] = v
                    if self._cache_enabled:
                        self._cache[name][k] = v
            except Exception as e:
                logger.error(
                    "Batch load hatasi: %s", e,
                )
                for k in to_load:
                    cached_results[k] = None

        # Sonuclari orijinal siraya diz
        return [
            cached_results.get(k) for k in keys
        ]

    def prime(
        self,
        name: str,
        key: Any,
        value: Any,
    ) -> None:
        """Onbellegi onceden doldurur.

        Args:
            name: Yukleyici adi.
            key: Anahtar.
            value: Deger.
        """
        if name in self._cache:
            self._cache[name][key] = value

    def clear(
        self,
        name: str,
        key: Any | None = None,
    ) -> int:
        """Onbellegi temizler.

        Args:
            name: Yukleyici adi.
            key: Anahtar (None=tumu).

        Returns:
            Silinen kayit sayisi.
        """
        if name not in self._cache:
            return 0

        if key is not None:
            if key in self._cache[name]:
                del self._cache[name][key]
                return 1
            return 0

        count = len(self._cache[name])
        self._cache[name] = {}
        return count

    def clear_all(self) -> int:
        """Tum onbellegi temizler.

        Returns:
            Silinen toplam kayit.
        """
        total = sum(
            len(c) for c in self._cache.values()
        )
        for name in self._cache:
            self._cache[name] = {}
        return total

    def get_stats(self) -> dict[str, int]:
        """Istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        return dict(self._stats)

    @property
    def loader_count(self) -> int:
        """Yukleyici sayisi."""
        return len(self._loaders)

    @property
    def cache_size(self) -> int:
        """Onbellek boyutu."""
        return sum(
            len(c) for c in self._cache.values()
        )

    @property
    def load_count(self) -> int:
        """Yukleme sayisi."""
        return self._stats["loads"]

    @property
    def batch_count(self) -> int:
        """Toplu yukleme sayisi."""
        return self._stats["batch_loads"]
