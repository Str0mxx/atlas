"""ATLAS Tembel Yukleyici modulu.

Ertelemeli yukleme, sayfalama,
sonsuz kayma, on-yukleme
ve oncelikli yukleme.
"""

import logging
import time
from typing import Any, Callable

from app.models.caching import LoadPriority

logger = logging.getLogger(__name__)


class LazyLoader:
    """Tembel yukleyici.

    Kaynaklari ihtiyac duyuldugunda
    yukler ve onbellekler.

    Attributes:
        _loaders: Yukleme fonksiyonlari.
        _cache: Yuklenenmis veri.
    """

    def __init__(
        self,
        page_size: int = 20,
        prefetch_count: int = 2,
    ) -> None:
        """Tembel yukleyiciyi baslatir.

        Args:
            page_size: Sayfa boyutu.
            prefetch_count: On-yukleme sayisi.
        """
        self._loaders: dict[
            str, Callable[..., Any]
        ] = {}
        self._cache: dict[str, Any] = {}
        self._priorities: dict[
            str, str
        ] = {}
        self._page_size = page_size
        self._prefetch_count = prefetch_count
        self._load_count = 0
        self._prefetch_queue: list[str] = []

        logger.info("LazyLoader baslatildi")

    def register(
        self,
        resource: str,
        loader: Callable[..., Any],
        priority: str = LoadPriority.NORMAL.value,
    ) -> None:
        """Yukleyici kaydeder.

        Args:
            resource: Kaynak adi.
            loader: Yukleme fonksiyonu.
            priority: Oncelik.
        """
        self._loaders[resource] = loader
        self._priorities[resource] = priority

    def load(
        self,
        resource: str,
        **kwargs: Any,
    ) -> Any:
        """Kaynak yukler.

        Args:
            resource: Kaynak adi.
            **kwargs: Ek parametreler.

        Returns:
            Yuklenen veri.
        """
        # Onbellekte varsa don
        cache_key = f"{resource}:{hash(str(kwargs))}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        loader = self._loaders.get(resource)
        if not loader:
            return None

        data = loader(**kwargs)
        self._cache[cache_key] = data
        self._load_count += 1
        return data

    def paginate(
        self,
        items: list[Any],
        page: int = 1,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """Sayfalama yapar.

        Args:
            items: Ogelerin tamami.
            page: Sayfa numarasi.
            page_size: Sayfa boyutu.

        Returns:
            Sayfa bilgisi.
        """
        ps = page_size or self._page_size
        total = len(items)
        total_pages = max(
            1, (total + ps - 1) // ps,
        )
        page = max(1, min(page, total_pages))

        start = (page - 1) * ps
        end = start + ps
        page_items = items[start:end]

        return {
            "items": page_items,
            "page": page,
            "page_size": ps,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    def infinite_scroll(
        self,
        items: list[Any],
        offset: int = 0,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Sonsuz kayma verir.

        Args:
            items: Tam liste.
            offset: Baslangic.
            limit: Sayi.

        Returns:
            Kayma bilgisi.
        """
        lim = limit or self._page_size
        chunk = items[offset:offset + lim]
        has_more = (offset + lim) < len(items)

        return {
            "items": chunk,
            "offset": offset,
            "limit": lim,
            "has_more": has_more,
            "next_offset": (
                offset + lim if has_more else None
            ),
            "total": len(items),
        }

    def prefetch(
        self,
        resources: list[str],
    ) -> int:
        """On-yukleme yapar.

        Args:
            resources: Kaynak listesi.

        Returns:
            Yuklenen sayisi.
        """
        loaded = 0
        for resource in resources[
            :self._prefetch_count
        ]:
            if resource in self._loaders:
                data = self.load(resource)
                if data is not None:
                    loaded += 1
                    self._prefetch_queue.append(
                        resource,
                    )
        return loaded

    def get_by_priority(
        self,
        priority: str,
    ) -> list[str]:
        """Oncelege gore kaynaklar getirir.

        Args:
            priority: Oncelik.

        Returns:
            Kaynak listesi.
        """
        return [
            r for r, p in self._priorities.items()
            if p == priority
        ]

    def invalidate(
        self,
        resource: str,
    ) -> int:
        """Kaynak onbellegini temizler.

        Args:
            resource: Kaynak adi.

        Returns:
            Temizlenen girdi sayisi.
        """
        keys_to_remove = [
            k for k in self._cache
            if k.startswith(f"{resource}:")
        ]
        for k in keys_to_remove:
            del self._cache[k]
        return len(keys_to_remove)

    def clear_cache(self) -> int:
        """Tum onbellegi temizler.

        Returns:
            Temizlenen girdi sayisi.
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    @property
    def loader_count(self) -> int:
        """Yukleyici sayisi."""
        return len(self._loaders)

    @property
    def cache_size(self) -> int:
        """Onbellek boyutu."""
        return len(self._cache)

    @property
    def load_count(self) -> int:
        """Yukleme sayisi."""
        return self._load_count
