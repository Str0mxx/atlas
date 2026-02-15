"""ATLAS Sorgu Yurutucu modulu.

Sorgu ayrıstirma, dogrulama,
yurutme, sonuc bicimlendirme
ve hata yonetimi.
"""

import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)


class QueryExecutor:
    """Sorgu yurutucu.

    GraphQL sorgularini ayristirir ve yurutur.

    Attributes:
        _cache: Sorgu onbellegi.
        _history: Sorgu gecmisi.
    """

    def __init__(self) -> None:
        """Yurutucuyu baslatir."""
        self._cache: dict[
            str, dict[str, Any]
        ] = {}
        self._history: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "executed": 0,
            "errors": 0,
            "cached": 0,
        }

        logger.info(
            "QueryExecutor baslatildi",
        )

    def parse(
        self,
        query: str,
    ) -> dict[str, Any]:
        """Sorguyu ayristirir.

        Args:
            query: GraphQL sorgusu.

        Returns:
            Ayristirma sonucu.
        """
        query = query.strip()
        if not query:
            return {"error": "empty_query"}

        # Islem tipini belirle
        operation = "query"
        if query.startswith("mutation"):
            operation = "mutation"
        elif query.startswith("subscription"):
            operation = "subscription"

        # Alan adlarini cikar
        field_pattern = re.findall(
            r'(\w+)\s*[{(]', query,
        )
        fields = [
            f for f in field_pattern
            if f not in (
                "query", "mutation",
                "subscription", "fragment",
            )
        ]

        # Derinlik hesapla
        depth = 0
        max_depth = 0
        for ch in query:
            if ch == '{':
                depth += 1
                max_depth = max(max_depth, depth)
            elif ch == '}':
                depth -= 1

        return {
            "operation": operation,
            "fields": fields,
            "depth": max_depth,
            "raw": query,
        }

    def validate(
        self,
        parsed: dict[str, Any],
        schema_types: dict[str, Any]
            | None = None,
    ) -> dict[str, Any]:
        """Sorguyu dogrular.

        Args:
            parsed: Ayristirma sonucu.
            schema_types: Sema tipleri.

        Returns:
            Dogrulama sonucu.
        """
        errors: list[str] = []

        if "error" in parsed:
            errors.append(parsed["error"])
            return {
                "valid": False,
                "errors": errors,
            }

        if not parsed.get("fields"):
            errors.append("no_fields_selected")

        # Derinlik kontrolu
        if parsed.get("depth", 0) > 20:
            errors.append("max_depth_exceeded")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "operation": parsed.get("operation"),
            "depth": parsed.get("depth", 0),
        }

    def execute(
        self,
        query: str,
        variables: dict[str, Any]
            | None = None,
        context: dict[str, Any]
            | None = None,
        resolver_fn: Any | None = None,
    ) -> dict[str, Any]:
        """Sorguyu yurutur.

        Args:
            query: GraphQL sorgusu.
            variables: Degiskenler.
            context: Baglam.
            resolver_fn: Cozumleyici fonksiyonu.

        Returns:
            Yurutme sonucu.
        """
        start = time.time()

        # Onbellek kontrolu
        cache_key = f"{query}:{str(variables)}"
        if cache_key in self._cache:
            self._stats["cached"] += 1
            return self._cache[cache_key]

        # Ayristir
        parsed = self.parse(query)
        if "error" in parsed:
            self._stats["errors"] += 1
            return {
                "data": None,
                "errors": [
                    {"message": parsed["error"]},
                ],
            }

        # Dogrula
        validation = self.validate(parsed)
        if not validation["valid"]:
            self._stats["errors"] += 1
            return {
                "data": None,
                "errors": [
                    {"message": e}
                    for e in validation["errors"]
                ],
            }

        # Yurutme
        data: dict[str, Any] = {}
        errors: list[dict[str, Any]] = []

        for field in parsed.get("fields", []):
            if resolver_fn:
                try:
                    data[field] = resolver_fn(
                        field,
                        variables or {},
                        context or {},
                    )
                except Exception as e:
                    errors.append({
                        "message": str(e),
                        "path": [field],
                    })
            else:
                data[field] = None

        duration = (time.time() - start) * 1000
        self._stats["executed"] += 1

        result = {
            "data": data,
            "errors": errors if errors else None,
            "extensions": {
                "duration_ms": duration,
                "depth": parsed.get("depth", 0),
            },
        }

        self._history.append({
            "query": query[:200],
            "operation": parsed["operation"],
            "duration_ms": duration,
            "has_errors": bool(errors),
            "timestamp": time.time(),
        })

        return result

    def execute_cached(
        self,
        query: str,
        variables: dict[str, Any]
            | None = None,
        ttl: int = 60,
        resolver_fn: Any | None = None,
    ) -> dict[str, Any]:
        """Onbellekli sorgu yurutur.

        Args:
            query: GraphQL sorgusu.
            variables: Degiskenler.
            ttl: Onbellek suresi (sn).
            resolver_fn: Cozumleyici.

        Returns:
            Yurutme sonucu.
        """
        cache_key = f"{query}:{str(variables)}"

        cached = self._cache.get(cache_key)
        if cached:
            cached_at = cached.get(
                "_cached_at", 0,
            )
            if time.time() - cached_at < ttl:
                self._stats["cached"] += 1
                return cached

        result = self.execute(
            query, variables,
            resolver_fn=resolver_fn,
        )
        result["_cached_at"] = time.time()
        self._cache[cache_key] = result

        return result

    def clear_cache(self) -> int:
        """Onbellegi temizler.

        Returns:
            Silinen kayit sayisi.
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    def get_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Sorgu gecmisini getirir.

        Args:
            limit: Limit.

        Returns:
            Gecmis listesi.
        """
        return self._history[-limit:]

    def get_stats(self) -> dict[str, int]:
        """Istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        return dict(self._stats)

    @property
    def executed_count(self) -> int:
        """Yurutulen sorgu sayisi."""
        return self._stats["executed"]

    @property
    def error_count(self) -> int:
        """Hata sayisi."""
        return self._stats["errors"]

    @property
    def cache_count(self) -> int:
        """Onbellek kayit sayisi."""
        return len(self._cache)

    @property
    def history_count(self) -> int:
        """Gecmis sayisi."""
        return len(self._history)
