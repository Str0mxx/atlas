"""ATLAS Otomatik Etiketleyici modülü.

Anahtar kelime çıkarma, varlık etiketleme,
konu tespiti, özel etiketler,
etiket önerileri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AutoTagger:
    """Otomatik etiketleyici.

    Dokümanları otomatik etiketler.

    Attributes:
        _tags: Etiket kayıtları.
        _custom_tags: Özel etiketler.
    """

    def __init__(self) -> None:
        """Etiketleyiciyi başlatır."""
        self._tags: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._custom_tags: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "documents_tagged": 0,
            "tags_generated": 0,
        }

        logger.info(
            "AutoTagger baslatildi",
        )

    def extract_keywords(
        self,
        doc_id: str,
        content: str = "",
        max_keywords: int = 10,
    ) -> dict[str, Any]:
        """Anahtar kelime çıkarır.

        Args:
            doc_id: Doküman kimliği.
            content: İçerik.
            max_keywords: Maks anahtar kelime.

        Returns:
            Çıkarma bilgisi.
        """
        words = content.lower().split()
        # Basit frekans analizi
        freq: dict[str, int] = {}
        stop_words = {
            "the", "a", "an", "is", "are",
            "was", "were", "in", "on", "at",
            "to", "for", "of", "and", "or",
            "bir", "ve", "ile", "için", "bu",
        }

        for w in words:
            clean = w.strip(".,;:!?()[]")
            if (
                len(clean) > 2
                and clean not in stop_words
            ):
                freq[clean] = (
                    freq.get(clean, 0) + 1
                )

        sorted_kw = sorted(
            freq.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:max_keywords]

        keywords = [
            {"word": w, "count": c}
            for w, c in sorted_kw
        ]

        self._add_tags(
            doc_id,
            [k["word"] for k in keywords],
            "keyword",
        )

        return {
            "doc_id": doc_id,
            "keywords": keywords,
            "count": len(keywords),
            "extracted": True,
        }

    def tag_entities(
        self,
        doc_id: str,
        content: str = "",
    ) -> dict[str, Any]:
        """Varlık etiketleme yapar.

        Args:
            doc_id: Doküman kimliği.
            content: İçerik.

        Returns:
            Etiketleme bilgisi.
        """
        entities = []
        words = content.split()

        for w in words:
            clean = w.strip(".,;:!?()[]")
            if (
                clean
                and clean[0].isupper()
                and len(clean) > 1
            ):
                entities.append({
                    "entity": clean,
                    "type": "proper_noun",
                })

        # Deduplicate
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for e in entities:
            if e["entity"] not in seen:
                seen.add(e["entity"])
                unique.append(e)

        self._add_tags(
            doc_id,
            [e["entity"] for e in unique],
            "entity",
        )

        return {
            "doc_id": doc_id,
            "entities": unique,
            "count": len(unique),
            "tagged": True,
        }

    def detect_topics(
        self,
        doc_id: str,
        content: str = "",
    ) -> dict[str, Any]:
        """Konu tespiti yapar.

        Args:
            doc_id: Doküman kimliği.
            content: İçerik.

        Returns:
            Tespit bilgisi.
        """
        topic_keywords = {
            "technology": [
                "software", "code", "api",
                "system", "data",
            ],
            "business": [
                "revenue", "profit", "market",
                "sales", "growth",
            ],
            "legal": [
                "contract", "law", "clause",
                "agreement", "legal",
            ],
            "finance": [
                "budget", "cost", "payment",
                "invoice", "tax",
            ],
        }

        text = content.lower()
        topics = []

        for topic, keywords in (
            topic_keywords.items()
        ):
            match_count = sum(
                1 for kw in keywords
                if kw in text
            )
            if match_count > 0:
                topics.append({
                    "topic": topic,
                    "relevance": round(
                        match_count
                        / len(keywords),
                        2,
                    ),
                })

        topics.sort(
            key=lambda x: x["relevance"],
            reverse=True,
        )

        self._add_tags(
            doc_id,
            [t["topic"] for t in topics],
            "topic",
        )

        return {
            "doc_id": doc_id,
            "topics": topics,
            "count": len(topics),
            "detected": True,
        }

    def add_custom_tag(
        self,
        doc_id: str,
        tag: str = "",
        category: str = "custom",
    ) -> dict[str, Any]:
        """Özel etiket ekler.

        Args:
            doc_id: Doküman kimliği.
            tag: Etiket.
            category: Kategori.

        Returns:
            Ekleme bilgisi.
        """
        if doc_id not in self._custom_tags:
            self._custom_tags[doc_id] = []

        self._custom_tags[doc_id].append(tag)
        self._add_tags(
            doc_id, [tag], "custom",
        )

        return {
            "doc_id": doc_id,
            "tag": tag,
            "category": category,
            "added": True,
        }

    def suggest_tags(
        self,
        doc_id: str,
        content: str = "",
        max_suggestions: int = 5,
    ) -> dict[str, Any]:
        """Etiket önerir.

        Args:
            doc_id: Doküman kimliği.
            content: İçerik.
            max_suggestions: Maks öneri.

        Returns:
            Öneri bilgisi.
        """
        # Combine keyword + topic based
        kw_result = self.extract_keywords(
            doc_id, content,
            max_keywords=max_suggestions,
        )
        topic_result = self.detect_topics(
            doc_id, content,
        )

        suggestions = []
        for kw in kw_result.get(
            "keywords", [],
        )[:3]:
            suggestions.append({
                "tag": kw["word"],
                "source": "keyword",
                "confidence": round(
                    min(kw["count"] / 5, 1.0),
                    2,
                ),
            })

        for tp in topic_result.get(
            "topics", [],
        )[:2]:
            suggestions.append({
                "tag": tp["topic"],
                "source": "topic",
                "confidence": tp[
                    "relevance"
                ],
            })

        return {
            "doc_id": doc_id,
            "suggestions": suggestions[
                :max_suggestions
            ],
            "count": min(
                len(suggestions),
                max_suggestions,
            ),
            "suggested": True,
        }

    def _add_tags(
        self,
        doc_id: str,
        tags: list[str],
        source: str,
    ) -> None:
        """Etiketleri ekler."""
        if doc_id not in self._tags:
            self._tags[doc_id] = []
            self._stats[
                "documents_tagged"
            ] += 1

        for tag in tags:
            self._counter += 1
            self._tags[doc_id].append({
                "tag_id": (
                    f"tag_{self._counter}"
                ),
                "tag": tag,
                "source": source,
                "timestamp": time.time(),
            })
            self._stats[
                "tags_generated"
            ] += 1

    @property
    def tag_count(self) -> int:
        """Etiket sayısı."""
        return self._stats[
            "tags_generated"
        ]

    @property
    def document_count(self) -> int:
        """Etiketlenen doküman sayısı."""
        return self._stats[
            "documents_tagged"
        ]
