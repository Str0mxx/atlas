"""ATLAS Doküman Arama Motoru modülü.

Tam metin arama, semantik arama,
filtre desteği, fasetli arama,
ilgililik sıralama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DocSearchEngine:
    """Doküman arama motoru.

    Dokümanlarda arama yapar.

    Attributes:
        _index: Arama indeksi.
        _queries: Sorgu geçmişi.
    """

    def __init__(self) -> None:
        """Motoru başlatır."""
        self._index: dict[
            str, dict[str, Any]
        ] = {}
        self._queries: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "documents_indexed": 0,
            "searches_performed": 0,
        }

        logger.info(
            "DocSearchEngine baslatildi",
        )

    def index_document(
        self,
        doc_id: str,
        title: str = "",
        content: str = "",
        tags: list[str] | None = None,
        category: str = "",
    ) -> dict[str, Any]:
        """Doküman indeksler.

        Args:
            doc_id: Doküman kimliği.
            title: Başlık.
            content: İçerik.
            tags: Etiketler.
            category: Kategori.

        Returns:
            İndeksleme bilgisi.
        """
        tags = tags or []

        words = set(
            f"{title} {content}".lower()
            .split()
        )

        self._index[doc_id] = {
            "doc_id": doc_id,
            "title": title,
            "content": content,
            "tags": tags,
            "category": category,
            "words": words,
            "timestamp": time.time(),
        }
        self._stats[
            "documents_indexed"
        ] += 1

        return {
            "doc_id": doc_id,
            "indexed": True,
            "word_count": len(words),
        }

    def full_text_search(
        self,
        query: str = "",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Tam metin arama yapar.

        Args:
            query: Sorgu.
            limit: Sınır.

        Returns:
            Arama bilgisi.
        """
        self._stats[
            "searches_performed"
        ] += 1
        self._queries.append({
            "query": query,
            "type": "full_text",
            "timestamp": time.time(),
        })

        query_words = set(
            query.lower().split(),
        )
        results = []

        for doc_id, doc in (
            self._index.items()
        ):
            match_count = len(
                query_words & doc["words"],
            )
            if match_count > 0:
                score = round(
                    match_count
                    / max(len(query_words), 1),
                    2,
                )
                results.append({
                    "doc_id": doc_id,
                    "title": doc["title"],
                    "score": score,
                })

        results.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        return {
            "query": query,
            "results": results[:limit],
            "total": len(results),
            "searched": True,
        }

    def semantic_search(
        self,
        query: str = "",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Semantik arama yapar.

        Args:
            query: Sorgu.
            limit: Sınır.

        Returns:
            Arama bilgisi.
        """
        self._stats[
            "searches_performed"
        ] += 1
        self._queries.append({
            "query": query,
            "type": "semantic",
            "timestamp": time.time(),
        })

        query_words = set(
            query.lower().split(),
        )
        results = []

        for doc_id, doc in (
            self._index.items()
        ):
            # Basit semantik benzerlik
            content_words = set(
                doc["content"].lower().split(),
            )
            title_words = set(
                doc["title"].lower().split(),
            )

            all_words = (
                content_words | title_words
            )
            overlap = len(
                query_words & all_words,
            )
            similarity = round(
                overlap
                / max(
                    len(
                        query_words
                        | all_words
                    ),
                    1,
                ),
                3,
            )

            if similarity > 0:
                results.append({
                    "doc_id": doc_id,
                    "title": doc["title"],
                    "similarity": similarity,
                })

        results.sort(
            key=lambda x: x["similarity"],
            reverse=True,
        )

        return {
            "query": query,
            "results": results[:limit],
            "total": len(results),
            "searched": True,
        }

    def filter_search(
        self,
        category: str = "",
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Filtreli arama yapar.

        Args:
            category: Kategori filtresi.
            tags: Etiket filtresi.
            limit: Sınır.

        Returns:
            Arama bilgisi.
        """
        tags = tags or []
        results = []

        for doc_id, doc in (
            self._index.items()
        ):
            match = True

            if category and (
                doc["category"] != category
            ):
                match = False

            if tags:
                doc_tags = set(doc["tags"])
                if not set(tags) & doc_tags:
                    match = False

            if match:
                results.append({
                    "doc_id": doc_id,
                    "title": doc["title"],
                    "category": doc[
                        "category"
                    ],
                    "tags": doc["tags"],
                })

        return {
            "category": category,
            "tags": tags,
            "results": results[:limit],
            "total": len(results),
            "filtered": True,
        }

    def faceted_search(
        self,
        query: str = "",
    ) -> dict[str, Any]:
        """Fasetli arama yapar.

        Args:
            query: Sorgu.

        Returns:
            Arama bilgisi.
        """
        categories: dict[str, int] = {}
        all_tags: dict[str, int] = {}

        query_words = set(
            query.lower().split(),
        ) if query else None

        for doc in self._index.values():
            if query_words:
                if not (
                    query_words & doc["words"]
                ):
                    continue

            cat = doc["category"] or "other"
            categories[cat] = (
                categories.get(cat, 0) + 1
            )

            for tag in doc["tags"]:
                all_tags[tag] = (
                    all_tags.get(tag, 0) + 1
                )

        return {
            "query": query,
            "facets": {
                "categories": categories,
                "tags": all_tags,
            },
            "searched": True,
        }

    def rank_relevance(
        self,
        query: str = "",
        doc_id: str = "",
    ) -> dict[str, Any]:
        """İlgililik sıralar.

        Args:
            query: Sorgu.
            doc_id: Doküman kimliği.

        Returns:
            Sıralama bilgisi.
        """
        doc = self._index.get(doc_id)
        if not doc:
            return {
                "doc_id": doc_id,
                "ranked": False,
            }

        query_words = set(
            query.lower().split(),
        )

        # Başlık ağırlığı daha yüksek
        title_words = set(
            doc["title"].lower().split(),
        )
        content_words = doc["words"]

        title_match = len(
            query_words & title_words,
        )
        content_match = len(
            query_words & content_words,
        )

        score = round(
            (title_match * 2 + content_match)
            / max(
                len(query_words) * 3, 1,
            ),
            3,
        )

        return {
            "doc_id": doc_id,
            "query": query,
            "relevance_score": min(
                score, 1.0,
            ),
            "title_matches": title_match,
            "content_matches": content_match,
            "ranked": True,
        }

    @property
    def index_count(self) -> int:
        """İndeks sayısı."""
        return self._stats[
            "documents_indexed"
        ]

    @property
    def search_count(self) -> int:
        """Arama sayısı."""
        return self._stats[
            "searches_performed"
        ]
