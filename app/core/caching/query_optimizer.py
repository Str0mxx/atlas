"""ATLAS Sorgu Optimizasyonu modulu.

Sorgu analizi, indeks onerileri,
sorgu onbellekleme, calistirma
planlari ve yavas sorgu tespiti.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """Sorgu optimize edici.

    Sorgu analizi ve optimizasyon
    onerileri saglar.

    Attributes:
        _cache: Sorgu onbellegi.
        _history: Sorgu gecmisi.
    """

    def __init__(
        self,
        slow_threshold: float = 1.0,
        cache_size: int = 500,
    ) -> None:
        """Sorgu optimize ediciyi baslatir.

        Args:
            slow_threshold: Yavas esik (sn).
            cache_size: Onbellek boyutu.
        """
        self._cache: dict[
            str, dict[str, Any]
        ] = {}
        self._history: list[
            dict[str, Any]
        ] = []
        self._indexes: dict[
            str, list[str]
        ] = {}
        self._slow_threshold = slow_threshold
        self._cache_size = cache_size
        self._slow_queries: list[
            dict[str, Any]
        ] = []

        logger.info(
            "QueryOptimizer baslatildi",
        )

    def analyze_query(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sorgu analiz eder.

        Args:
            query: Sorgu metni.
            params: Parametreler.

        Returns:
            Analiz sonucu.
        """
        # Basit sorgu analizi
        q_lower = query.lower().strip()
        has_where = "where" in q_lower
        has_join = "join" in q_lower
        has_orderby = "order by" in q_lower
        has_groupby = "group by" in q_lower
        has_select_all = "select *" in q_lower

        suggestions: list[str] = []
        if has_select_all:
            suggestions.append(
                "Avoid SELECT *, specify columns",
            )
        if has_join and not has_where:
            suggestions.append(
                "Add WHERE clause for JOIN",
            )

        complexity = (
            1
            + int(has_join) * 2
            + int(has_groupby)
            + int(has_orderby)
        )

        return {
            "query": query,
            "has_where": has_where,
            "has_join": has_join,
            "has_orderby": has_orderby,
            "has_groupby": has_groupby,
            "complexity": complexity,
            "suggestions": suggestions,
        }

    def suggest_indexes(
        self,
        table: str,
        columns: list[str],
    ) -> dict[str, Any]:
        """Indeks onerir.

        Args:
            table: Tablo adi.
            columns: Kolon listesi.

        Returns:
            Indeks onerisi.
        """
        existing = self._indexes.get(table, [])
        needed = [
            c for c in columns
            if c not in existing
        ]

        suggestion = {
            "table": table,
            "existing_indexes": existing,
            "suggested_indexes": needed,
            "impact": (
                "high" if len(needed) > 2
                else "medium" if needed
                else "none"
            ),
        }
        return suggestion

    def add_index(
        self,
        table: str,
        column: str,
    ) -> None:
        """Indeks ekler.

        Args:
            table: Tablo adi.
            column: Kolon adi.
        """
        if table not in self._indexes:
            self._indexes[table] = []
        if column not in self._indexes[table]:
            self._indexes[table].append(column)

    def cache_query(
        self,
        query: str,
        result: Any,
        ttl: int = 60,
    ) -> None:
        """Sorgu sonucunu onbellekler.

        Args:
            query: Sorgu.
            result: Sonuc.
            ttl: Yasam suresi.
        """
        if len(self._cache) >= self._cache_size:
            oldest = next(iter(self._cache))
            del self._cache[oldest]

        self._cache[query] = {
            "result": result,
            "expires_at": time.time() + ttl,
            "cached_at": time.time(),
        }

    def get_cached(
        self,
        query: str,
    ) -> Any | None:
        """Onbellekli sorgu getirir.

        Args:
            query: Sorgu.

        Returns:
            Sonuc veya None.
        """
        entry = self._cache.get(query)
        if not entry:
            return None

        if time.time() > entry["expires_at"]:
            del self._cache[query]
            return None

        return entry["result"]

    def record_execution(
        self,
        query: str,
        duration: float,
        rows_affected: int = 0,
    ) -> dict[str, Any]:
        """Sorgu calistirmasini kaydeder.

        Args:
            query: Sorgu.
            duration: Sure.
            rows_affected: Etkilenen satir.

        Returns:
            Kayit.
        """
        record = {
            "query": query,
            "duration": duration,
            "rows_affected": rows_affected,
            "at": time.time(),
            "slow": duration > self._slow_threshold,
        }
        self._history.append(record)

        if record["slow"]:
            self._slow_queries.append(record)

        return record

    def get_execution_plan(
        self,
        query: str,
    ) -> dict[str, Any]:
        """Calistirma plani olusturur.

        Args:
            query: Sorgu.

        Returns:
            Calistirma plani.
        """
        analysis = self.analyze_query(query)
        cached = query in self._cache

        steps: list[str] = []
        if cached:
            steps.append("cache_lookup")
        else:
            steps.append("full_scan")
            if analysis["has_where"]:
                steps.append("filter")
            if analysis["has_join"]:
                steps.append("join")
            if analysis["has_orderby"]:
                steps.append("sort")
            if analysis["has_groupby"]:
                steps.append("aggregate")

        return {
            "query": query,
            "steps": steps,
            "estimated_cost": analysis[
                "complexity"
            ],
            "use_cache": cached,
        }

    def get_slow_queries(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Yavas sorgulari getirir.

        Args:
            limit: Limit.

        Returns:
            Yavas sorgu listesi.
        """
        return self._slow_queries[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Istatistik getirir.

        Returns:
            Istatistik.
        """
        durations = [
            r["duration"]
            for r in self._history
        ]
        avg = (
            round(
                sum(durations) / len(durations),
                4,
            )
            if durations
            else 0.0
        )

        return {
            "total_queries": len(self._history),
            "cached_queries": len(self._cache),
            "slow_queries": len(
                self._slow_queries,
            ),
            "avg_duration": avg,
            "indexes": sum(
                len(v)
                for v in self._indexes.values()
            ),
        }

    @property
    def cache_count(self) -> int:
        """Onbellek boyutu."""
        return len(self._cache)

    @property
    def history_count(self) -> int:
        """Gecmis boyutu."""
        return len(self._history)

    @property
    def slow_count(self) -> int:
        """Yavas sorgu sayisi."""
        return len(self._slow_queries)
