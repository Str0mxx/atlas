"""ATLAS Log Arayici modulu.

Tam metin arama, seviye filtresi,
zaman filtresi, kaynak filtresi
ve regex arama.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class LogSearcher:
    """Log arayici.

    Log kayitlarinda arama yapar.

    Attributes:
        _index: Arama indeksi.
        _search_count: Arama sayisi.
    """

    def __init__(self) -> None:
        """Log arayiciyi baslatir."""
        self._logs: list[dict[str, Any]] = []
        self._search_count = 0

        logger.info(
            "LogSearcher baslatildi",
        )

    def index_logs(
        self,
        logs: list[dict[str, Any]],
    ) -> int:
        """Loglari indeksler.

        Args:
            logs: Log kayitlari.

        Returns:
            Indekslenen sayi.
        """
        self._logs.extend(logs)
        return len(logs)

    def search(
        self,
        query: str,
        case_sensitive: bool = False,
    ) -> list[dict[str, Any]]:
        """Tam metin arama.

        Args:
            query: Arama sorgusu.
            case_sensitive: Buyuk/kucuk harf duyarli.

        Returns:
            Eslesen loglar.
        """
        self._search_count += 1
        results = []
        for log in self._logs:
            msg = log.get("message", "")
            if case_sensitive:
                if query in msg:
                    results.append(log)
            else:
                if query.lower() in msg.lower():
                    results.append(log)
        return results

    def filter_by_level(
        self,
        level: str,
        logs: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Seviyeye gore filtreler.

        Args:
            level: Log seviyesi.
            logs: Log listesi (None=tum).

        Returns:
            Filtrelenmis loglar.
        """
        self._search_count += 1
        source = logs if logs is not None else self._logs
        return [
            r for r in source
            if r.get("level", "").lower()
            == level.lower()
        ]

    def filter_by_time(
        self,
        start: float | None = None,
        end: float | None = None,
        logs: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Zamana gore filtreler.

        Args:
            start: Baslangic zamani.
            end: Bitis zamani.
            logs: Log listesi (None=tum).

        Returns:
            Filtrelenmis loglar.
        """
        self._search_count += 1
        source = logs if logs is not None else self._logs
        result = source
        if start is not None:
            result = [
                r for r in result
                if r.get("timestamp", 0) >= start
            ]
        if end is not None:
            result = [
                r for r in result
                if r.get("timestamp", 0) <= end
            ]
        return result

    def filter_by_source(
        self,
        source: str,
        logs: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Kaynaga gore filtreler.

        Args:
            source: Kaynak adi.
            logs: Log listesi (None=tum).

        Returns:
            Filtrelenmis loglar.
        """
        self._search_count += 1
        log_source = (
            logs if logs is not None
            else self._logs
        )
        return [
            r for r in log_source
            if r.get("source", "") == source
        ]

    def regex_search(
        self,
        pattern: str,
        logs: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Regex ile arama.

        Args:
            pattern: Regex deseni.
            logs: Log listesi (None=tum).

        Returns:
            Eslesen loglar.
        """
        self._search_count += 1
        source = logs if logs is not None else self._logs
        try:
            compiled = re.compile(pattern)
        except re.error:
            return []

        return [
            r for r in source
            if compiled.search(
                r.get("message", ""),
            )
        ]

    def combined_search(
        self,
        query: str = "",
        level: str = "",
        source: str = "",
        start: float | None = None,
        end: float | None = None,
    ) -> list[dict[str, Any]]:
        """Kombine arama.

        Args:
            query: Metin sorgusu.
            level: Seviye filtresi.
            source: Kaynak filtresi.
            start: Baslangic zamani.
            end: Bitis zamani.

        Returns:
            Sonuclar.
        """
        self._search_count += 1
        result = list(self._logs)

        if query:
            q_lower = query.lower()
            result = [
                r for r in result
                if q_lower
                in r.get("message", "").lower()
            ]
        if level:
            result = [
                r for r in result
                if r.get("level", "").lower()
                == level.lower()
            ]
        if source:
            result = [
                r for r in result
                if r.get("source", "") == source
            ]
        if start is not None:
            result = [
                r for r in result
                if r.get("timestamp", 0) >= start
            ]
        if end is not None:
            result = [
                r for r in result
                if r.get("timestamp", 0) <= end
            ]

        return result

    def clear_index(self) -> int:
        """Indeksi temizler.

        Returns:
            Temizlenen sayi.
        """
        count = len(self._logs)
        self._logs = []
        return count

    @property
    def indexed_count(self) -> int:
        """Indekslenen log sayisi."""
        return len(self._logs)

    @property
    def search_count(self) -> int:
        """Arama sayisi."""
        return self._search_count
