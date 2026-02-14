"""ATLAS Sorgu Isleyici modulu.

Okuma modeli sorgulari, projeksiyon
sorgulari, onbellek, sayfalama
ve filtreleme.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class QueryHandler:
    """Sorgu isleyici.

    Okuma modelinden sorgu yapar.

    Attributes:
        _handlers: Sorgu isleyicileri.
        _cache: Sorgu onbellegi.
    """

    def __init__(
        self,
        cache_ttl: int = 300,
    ) -> None:
        """Sorgu isleyiciyi baslatir.

        Args:
            cache_ttl: Onbellek suresi (sn).
        """
        self._handlers: dict[
            str, dict[str, Any]
        ] = {}
        self._cache: dict[
            str, dict[str, Any]
        ] = {}
        self._cache_ttl = cache_ttl
        self._query_log: list[
            dict[str, Any]
        ] = []

        logger.info("QueryHandler baslatildi")

    def register_handler(
        self,
        query_type: str,
        handler: Callable[..., Any],
    ) -> dict[str, Any]:
        """Sorgu isleyici kaydeder.

        Args:
            query_type: Sorgu tipi.
            handler: Isleyici fonksiyon.

        Returns:
            Kayit bilgisi.
        """
        self._handlers[query_type] = {
            "query_type": query_type,
            "handler": handler,
            "call_count": 0,
        }
        return {"query_type": query_type}

    def query(
        self,
        query_type: str,
        params: dict[str, Any] | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Sorgu yapar.

        Args:
            query_type: Sorgu tipi.
            params: Sorgu parametreleri.
            use_cache: Onbellek kullan.

        Returns:
            Sorgu sonucu.
        """
        params = params or {}

        # Onbellek kontrol
        if use_cache:
            cache_key = (
                f"{query_type}:{sorted(params.items())}"
            )
            cached = self._get_cached(cache_key)
            if cached is not None:
                self._log_query(
                    query_type, params,
                    "cache_hit",
                )
                return cached

        entry = self._handlers.get(query_type)
        if not entry:
            return {
                "query_type": query_type,
                "status": "not_found",
                "data": None,
            }

        try:
            data = entry["handler"](params)
            entry["call_count"] += 1

            result = {
                "query_type": query_type,
                "status": "success",
                "data": data,
                "timestamp": time.time(),
            }

            # Onbellege kaydet
            if use_cache:
                self._set_cached(
                    cache_key, result,
                )

            self._log_query(
                query_type, params, "success",
            )
            return result

        except Exception as e:
            self._log_query(
                query_type, params, "error",
            )
            return {
                "query_type": query_type,
                "status": "error",
                "error": str(e),
            }

    def query_paginated(
        self,
        query_type: str,
        params: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Sayfalanmis sorgu yapar.

        Args:
            query_type: Sorgu tipi.
            params: Sorgu parametreleri.
            page: Sayfa numarasi.
            page_size: Sayfa boyutu.

        Returns:
            Sayfalanmis sonuc.
        """
        result = self.query(
            query_type, params,
            use_cache=False,
        )
        if result["status"] != "success":
            return result

        data = result.get("data")
        if not isinstance(data, list):
            return result

        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        page_data = data[start:end]

        return {
            "query_type": query_type,
            "status": "success",
            "data": page_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (
                    (total + page_size - 1)
                    // page_size
                ),
            },
            "timestamp": time.time(),
        }

    def query_filtered(
        self,
        query_type: str,
        params: dict[str, Any] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Filtrelenmis sorgu yapar.

        Args:
            query_type: Sorgu tipi.
            params: Sorgu parametreleri.
            filters: Filtre kriterleri.

        Returns:
            Filtrelenmis sonuc.
        """
        result = self.query(
            query_type, params,
            use_cache=False,
        )
        if result["status"] != "success":
            return result

        data = result.get("data")
        if (
            not isinstance(data, list)
            or not filters
        ):
            return result

        filtered = []
        for item in data:
            if not isinstance(item, dict):
                continue
            match = all(
                item.get(k) == v
                for k, v in filters.items()
            )
            if match:
                filtered.append(item)

        return {
            "query_type": query_type,
            "status": "success",
            "data": filtered,
            "filtered_count": len(filtered),
            "original_count": len(data),
            "timestamp": time.time(),
        }

    def _get_cached(
        self,
        key: str,
    ) -> dict[str, Any] | None:
        """Onbellekten getirir.

        Args:
            key: Anahtar.

        Returns:
            Deger veya None.
        """
        entry = self._cache.get(key)
        if not entry:
            return None

        if (
            time.time() - entry["cached_at"]
            > self._cache_ttl
        ):
            del self._cache[key]
            return None

        return entry["value"]

    def _set_cached(
        self,
        key: str,
        value: dict[str, Any],
    ) -> None:
        """Onbellege kaydeder.

        Args:
            key: Anahtar.
            value: Deger.
        """
        self._cache[key] = {
            "value": value,
            "cached_at": time.time(),
        }

    def _log_query(
        self,
        query_type: str,
        params: dict[str, Any],
        status: str,
    ) -> None:
        """Sorgu loglar.

        Args:
            query_type: Sorgu tipi.
            params: Parametreler.
            status: Durum.
        """
        self._query_log.append({
            "query_type": query_type,
            "status": status,
            "timestamp": time.time(),
        })

    def invalidate_cache(
        self,
        query_type: str | None = None,
    ) -> int:
        """Onbellegi gecersiz kilar.

        Args:
            query_type: Sorgu tipi filtresi.

        Returns:
            Temizlenen sayi.
        """
        if query_type is None:
            count = len(self._cache)
            self._cache.clear()
            return count

        keys_to_remove = [
            k for k in self._cache
            if k.startswith(f"{query_type}:")
        ]
        for k in keys_to_remove:
            del self._cache[k]
        return len(keys_to_remove)

    @property
    def handler_count(self) -> int:
        """Isleyici sayisi."""
        return len(self._handlers)

    @property
    def cache_size(self) -> int:
        """Onbellek boyutu."""
        return len(self._cache)

    @property
    def query_count(self) -> int:
        """Sorgu sayisi."""
        return len(self._query_log)
