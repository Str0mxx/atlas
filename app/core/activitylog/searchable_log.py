"""
Aranabilir log modulu.

Tam metin arama, fasetli arama,
vurgulama, oneriler, son aramalar.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SearchableLog:
    """Aranabilir log.

    Attributes:
        _entries: Log kayitlari.
        _recent_searches: Son aramalar.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Aranabilir logu baslatir."""
        self._entries: list[dict] = []
        self._recent_searches: list[dict] = []
        self._stats: dict[str, int] = {
            "searches_performed": 0,
            "entries_indexed": 0,
        }
        logger.info(
            "SearchableLog baslatildi"
        )

    @property
    def entry_count(self) -> int:
        """Kayit sayisi."""
        return len(self._entries)

    @property
    def search_count(self) -> int:
        """Arama sayisi."""
        return self._stats[
            "searches_performed"
        ]

    def index_entry(
        self,
        content: str = "",
        source: str = "",
        entry_type: str = "log",
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Kayit indeksler.

        Args:
            content: Icerik.
            source: Kaynak.
            entry_type: Kayit turu.
            tags: Etiketler.
            metadata: Ek veri.

        Returns:
            Indeksleme bilgisi.
        """
        try:
            eid = f"se_{uuid4()!s:.8}"
            entry = {
                "entry_id": eid,
                "content": content,
                "source": source,
                "entry_type": entry_type,
                "tags": tags or [],
                "metadata": metadata or {},
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
                "content_lower": (
                    content.lower()
                ),
            }
            self._entries.append(entry)
            self._stats[
                "entries_indexed"
            ] += 1

            return {
                "entry_id": eid,
                "source": source,
                "entry_type": entry_type,
                "indexed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "indexed": False,
                "error": str(e),
            }

    def search(
        self,
        query: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Tam metin arama yapar.

        Args:
            query: Arama sorgusu.
            limit: Sonuc limiti.

        Returns:
            Arama sonuclari.
        """
        try:
            query_lower = query.lower()
            results = []

            for entry in self._entries:
                content = entry.get(
                    "content_lower", ""
                )
                if query_lower in content:
                    score = self._score_match(
                        query_lower, content
                    )
                    results.append({
                        **{
                            k: v
                            for k, v in entry.items()
                            if k
                            != "content_lower"
                        },
                        "relevance_score": score,
                        "highlights": (
                            self._highlight(
                                entry[
                                    "content"
                                ],
                                query,
                            )
                        ),
                    })

            results.sort(
                key=lambda x: x.get(
                    "relevance_score", 0
                ),
                reverse=True,
            )
            results = results[:limit]

            self._recent_searches.append({
                "query": query,
                "result_count": len(results),
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            })
            if len(self._recent_searches) > 50:
                self._recent_searches = (
                    self._recent_searches[-50:]
                )

            self._stats[
                "searches_performed"
            ] += 1

            return {
                "query": query,
                "results": results,
                "result_count": len(results),
                "searched": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "searched": False,
                "error": str(e),
            }

    def faceted_search(
        self,
        query: str = "",
        source: str = "",
        entry_type: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Fasetli arama yapar.

        Args:
            query: Arama sorgusu.
            source: Kaynak filtresi.
            entry_type: Tur filtresi.
            tags: Etiket filtresi.

        Returns:
            Arama sonuclari.
        """
        try:
            query_lower = query.lower()
            tag_set = set(tags or [])
            results = []

            for entry in self._entries:
                if query_lower:
                    content = entry.get(
                        "content_lower", ""
                    )
                    if (
                        query_lower
                        not in content
                    ):
                        continue

                if source and entry.get(
                    "source"
                ) != source:
                    continue

                if (
                    entry_type
                    and entry.get("entry_type")
                    != entry_type
                ):
                    continue

                if tag_set:
                    entry_tags = set(
                        entry.get("tags", [])
                    )
                    if not tag_set.intersection(
                        entry_tags
                    ):
                        continue

                results.append({
                    k: v
                    for k, v in entry.items()
                    if k != "content_lower"
                })

            facets = self._build_facets(
                results
            )
            self._stats[
                "searches_performed"
            ] += 1

            return {
                "query": query,
                "results": results,
                "result_count": len(results),
                "facets": facets,
                "searched": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "searched": False,
                "error": str(e),
            }

    def get_suggestions(
        self,
        partial: str = "",
    ) -> dict[str, Any]:
        """Arama onerileri getirir.

        Args:
            partial: Kismi sorgu.

        Returns:
            Oneriler.
        """
        try:
            partial_lower = partial.lower()
            suggestions: list[str] = []
            seen: set[str] = set()

            for search in reversed(
                self._recent_searches
            ):
                q = search.get("query", "")
                q_lower = q.lower()
                if (
                    partial_lower in q_lower
                    and q_lower not in seen
                ):
                    suggestions.append(q)
                    seen.add(q_lower)

            for entry in self._entries:
                tags = entry.get("tags", [])
                for tag in tags:
                    tl = tag.lower()
                    if (
                        partial_lower in tl
                        and tl not in seen
                    ):
                        suggestions.append(tag)
                        seen.add(tl)

            return {
                "partial": partial,
                "suggestions": suggestions[
                    :10
                ],
                "suggestion_count": min(
                    10, len(suggestions)
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_recent_searches(
        self,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Son aramalari getirir.

        Args:
            limit: Sonuc limiti.

        Returns:
            Son arama listesi.
        """
        try:
            recent = list(
                reversed(
                    self._recent_searches
                )
            )[:limit]

            return {
                "searches": recent,
                "search_count": len(recent),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def _score_match(
        self,
        query: str,
        content: str,
    ) -> float:
        """Esleme puani hesaplar."""
        if not content:
            return 0.0

        count = content.count(query)
        position = content.find(query)

        score = count * 10.0
        if position == 0:
            score += 20.0
        elif position < 50:
            score += 10.0

        ratio = len(query) / max(
            len(content), 1
        )
        score += ratio * 30.0

        return round(score, 1)

    def _highlight(
        self,
        content: str,
        query: str,
    ) -> list[str]:
        """Eslesen kisimlari vurgular."""
        if not query:
            return []

        highlights = []
        lower_content = content.lower()
        lower_query = query.lower()
        pos = 0

        while True:
            idx = lower_content.find(
                lower_query, pos
            )
            if idx == -1:
                break

            start = max(0, idx - 20)
            end = min(
                len(content),
                idx + len(query) + 20,
            )
            snippet = content[start:end]
            highlights.append(snippet)
            pos = idx + 1

        return highlights[:5]

    def _build_facets(
        self,
        results: list[dict],
    ) -> dict[str, dict]:
        """Fasetler olusturur."""
        sources: dict[str, int] = {}
        types: dict[str, int] = {}
        tags: dict[str, int] = {}

        for r in results:
            src = r.get("source", "unknown")
            sources[src] = (
                sources.get(src, 0) + 1
            )

            etype = r.get(
                "entry_type", "unknown"
            )
            types[etype] = (
                types.get(etype, 0) + 1
            )

            for tag in r.get("tags", []):
                tags[tag] = (
                    tags.get(tag, 0) + 1
                )

        return {
            "sources": sources,
            "types": types,
            "tags": tags,
        }
