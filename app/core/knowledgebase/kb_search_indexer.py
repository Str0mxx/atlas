"""ATLAS Arama İndeksleyici modülü.

Tam metin indeksleme, semantik indeksleme,
gerçek zamanlı güncelleme, ilgililik ayarı,
eşanlamlı desteği.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class KBSearchIndexer:
    """Arama indeksleyici.

    Bilgi tabanı içeriğini indeksler.

    Attributes:
        _index: İndeks kayıtları.
        _synonyms: Eşanlamlı haritası.
    """

    def __init__(self) -> None:
        """İndeksleyiciyi başlatır."""
        self._index: dict[
            str, dict[str, Any]
        ] = {}
        self._synonyms: dict[
            str, list[str]
        ] = {}
        self._word_index: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "pages_indexed": 0,
            "searches_performed": 0,
        }

        logger.info(
            "KBSearchIndexer baslatildi",
        )

    def index_fulltext(
        self,
        page_id: str,
        title: str = "",
        content: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Tam metin indeksler.

        Args:
            page_id: Sayfa kimliği.
            title: Başlık.
            content: İçerik.
            tags: Etiketler.

        Returns:
            İndeksleme bilgisi.
        """
        tags = tags or []

        text = f"{title} {content}"
        words = [
            w.lower().strip(".,!?;:")
            for w in text.split()
            if len(w) > 2
        ]

        self._index[page_id] = {
            "page_id": page_id,
            "title": title,
            "content": content,
            "tags": tags,
            "words": words,
            "word_count": len(words),
            "timestamp": time.time(),
        }

        for word in set(words):
            pages = self._word_index.get(
                word, [],
            )
            if page_id not in pages:
                pages.append(page_id)
            self._word_index[word] = pages

        self._stats[
            "pages_indexed"
        ] += 1

        return {
            "page_id": page_id,
            "words_indexed": len(
                set(words),
            ),
            "indexed": True,
        }

    def index_semantic(
        self,
        page_id: str,
        content: str = "",
        keywords: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Semantik indeksler.

        Args:
            page_id: Sayfa kimliği.
            content: İçerik.
            keywords: Anahtar kelimeler.

        Returns:
            İndeksleme bilgisi.
        """
        keywords = keywords or []

        entry = self._index.get(page_id)
        if entry:
            entry["keywords"] = keywords
            entry["semantic"] = True
        else:
            self._index[page_id] = {
                "page_id": page_id,
                "content": content,
                "keywords": keywords,
                "semantic": True,
                "timestamp": time.time(),
            }

        for kw in keywords:
            pages = self._word_index.get(
                kw.lower(), [],
            )
            if page_id not in pages:
                pages.append(page_id)
            self._word_index[
                kw.lower()
            ] = pages

        return {
            "page_id": page_id,
            "keywords_indexed": len(
                keywords,
            ),
            "semantic_indexed": True,
        }

    def update_realtime(
        self,
        page_id: str,
        new_content: str = "",
    ) -> dict[str, Any]:
        """Gerçek zamanlı günceller.

        Args:
            page_id: Sayfa kimliği.
            new_content: Yeni içerik.

        Returns:
            Güncelleme bilgisi.
        """
        entry = self._index.get(page_id)
        if not entry:
            return {
                "page_id": page_id,
                "found": False,
            }

        old_words = set(
            entry.get("words", []),
        )
        new_words = [
            w.lower().strip(".,!?;:")
            for w in new_content.split()
            if len(w) > 2
        ]

        entry["content"] = new_content
        entry["words"] = new_words
        entry["word_count"] = len(
            new_words,
        )
        entry["timestamp"] = time.time()

        for w in old_words:
            pages = self._word_index.get(
                w, [],
            )
            if page_id in pages:
                pages.remove(page_id)

        for w in set(new_words):
            pages = self._word_index.get(
                w, [],
            )
            if page_id not in pages:
                pages.append(page_id)
            self._word_index[w] = pages

        return {
            "page_id": page_id,
            "words_reindexed": len(
                set(new_words),
            ),
            "updated": True,
        }

    def tune_relevance(
        self,
        query: str,
        boost_fields: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """İlgililik ayarı yapar.

        Args:
            query: Arama sorgusu.
            boost_fields: Alan ağırlıkları.

        Returns:
            Arama bilgisi.
        """
        boost_fields = boost_fields or {
            "title": 2.0,
            "content": 1.0,
            "tags": 1.5,
        }

        terms = [
            t.lower()
            for t in query.split()
        ]

        results: list[
            dict[str, Any]
        ] = []

        for pid, entry in (
            self._index.items()
        ):
            score = 0.0
            title = entry.get(
                "title", "",
            ).lower()
            content = entry.get(
                "content", "",
            ).lower()
            tags = [
                t.lower()
                for t in entry.get(
                    "tags", [],
                )
            ]

            for term in terms:
                expanded = [term] + (
                    self._synonyms.get(
                        term, [],
                    )
                )
                for t in expanded:
                    if t in title:
                        score += boost_fields.get(
                            "title", 2.0,
                        )
                    if t in content:
                        score += boost_fields.get(
                            "content", 1.0,
                        )
                    if t in tags:
                        score += boost_fields.get(
                            "tags", 1.5,
                        )

            if score > 0:
                results.append({
                    "page_id": pid,
                    "score": score,
                    "title": entry.get(
                        "title", "",
                    ),
                })

        results.sort(
            key=lambda r: r["score"],
            reverse=True,
        )

        self._stats[
            "searches_performed"
        ] += 1

        return {
            "query": query,
            "results": results,
            "count": len(results),
            "searched": True,
        }

    def add_synonym(
        self,
        word: str,
        synonyms: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Eşanlamlı ekler.

        Args:
            word: Kelime.
            synonyms: Eşanlamlılar.

        Returns:
            Ekleme bilgisi.
        """
        synonyms = synonyms or []

        existing = self._synonyms.get(
            word.lower(), [],
        )
        for s in synonyms:
            if s.lower() not in existing:
                existing.append(s.lower())

        self._synonyms[
            word.lower()
        ] = existing

        return {
            "word": word,
            "synonyms": existing,
            "count": len(existing),
            "added": True,
        }

    @property
    def index_count(self) -> int:
        """İndeks sayısı."""
        return self._stats[
            "pages_indexed"
        ]

    @property
    def search_count(self) -> int:
        """Arama sayısı."""
        return self._stats[
            "searches_performed"
        ]
