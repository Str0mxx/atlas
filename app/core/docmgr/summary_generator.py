"""ATLAS Doküman Özet Üretici modülü.

Otomatik özetleme, anahtar nokta çıkarma,
TL;DR üretimi, özel uzunluk,
çoklu doküman özeti.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DocSummaryGenerator:
    """Doküman özet üretici.

    Dokümanlardan özet üretir.

    Attributes:
        _summaries: Özet kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Üreticiyi başlatır."""
        self._summaries: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "summaries_generated": 0,
            "multi_doc_summaries": 0,
        }

        logger.info(
            "DocSummaryGenerator "
            "baslatildi",
        )

    def auto_summarize(
        self,
        doc_id: str,
        content: str = "",
        max_sentences: int = 3,
    ) -> dict[str, Any]:
        """Otomatik özetleme yapar.

        Args:
            doc_id: Doküman kimliği.
            content: İçerik.
            max_sentences: Maks cümle.

        Returns:
            Özet bilgisi.
        """
        self._counter += 1
        sid = f"sum_{self._counter}"

        sentences = self._split_sentences(
            content,
        )
        selected = sentences[:max_sentences]
        summary = " ".join(selected)

        result = {
            "summary_id": sid,
            "doc_id": doc_id,
            "summary": summary,
            "sentence_count": len(selected),
            "original_length": len(content),
            "summary_length": len(summary),
            "compression_ratio": round(
                len(summary)
                / max(len(content), 1),
                2,
            ),
            "summarized": True,
        }

        self._summaries.append(result)
        self._stats[
            "summaries_generated"
        ] += 1

        return result

    def extract_key_points(
        self,
        doc_id: str,
        content: str = "",
        max_points: int = 5,
    ) -> dict[str, Any]:
        """Anahtar nokta çıkarır.

        Args:
            doc_id: Doküman kimliği.
            content: İçerik.
            max_points: Maks nokta.

        Returns:
            Çıkarma bilgisi.
        """
        sentences = self._split_sentences(
            content,
        )

        # Uzun cümleleri anahtar nokta
        # olarak seç
        scored = []
        for s in sentences:
            words = s.split()
            score = len(words)
            scored.append((s, score))

        scored.sort(
            key=lambda x: x[1],
            reverse=True,
        )

        points = [
            s for s, _ in scored
        ][:max_points]

        return {
            "doc_id": doc_id,
            "key_points": points,
            "count": len(points),
            "extracted": True,
        }

    def generate_tldr(
        self,
        doc_id: str,
        content: str = "",
        max_words: int = 30,
    ) -> dict[str, Any]:
        """TL;DR üretir.

        Args:
            doc_id: Doküman kimliği.
            content: İçerik.
            max_words: Maks kelime.

        Returns:
            TL;DR bilgisi.
        """
        sentences = self._split_sentences(
            content,
        )
        if not sentences:
            return {
                "doc_id": doc_id,
                "tldr": "",
                "generated": False,
            }

        # İlk cümleyi kısalt
        first = sentences[0]
        words = first.split()[:max_words]
        tldr = " ".join(words)

        if len(first.split()) > max_words:
            tldr += "..."

        return {
            "doc_id": doc_id,
            "tldr": tldr,
            "word_count": len(
                tldr.split(),
            ),
            "generated": True,
        }

    def custom_length_summary(
        self,
        doc_id: str,
        content: str = "",
        target_length: int = 100,
    ) -> dict[str, Any]:
        """Özel uzunluk özet üretir.

        Args:
            doc_id: Doküman kimliği.
            content: İçerik.
            target_length: Hedef uzunluk.

        Returns:
            Özet bilgisi.
        """
        sentences = self._split_sentences(
            content,
        )

        summary = ""
        for s in sentences:
            if (
                len(summary) + len(s)
                <= target_length
            ):
                if summary:
                    summary += " "
                summary += s
            else:
                break

        if not summary and sentences:
            summary = sentences[0][
                :target_length
            ]

        return {
            "doc_id": doc_id,
            "summary": summary,
            "length": len(summary),
            "target_length": target_length,
            "generated": True,
        }

    def multi_document_summary(
        self,
        documents: list[
            dict[str, Any]
        ]
        | None = None,
        max_sentences: int = 5,
    ) -> dict[str, Any]:
        """Çoklu doküman özeti üretir.

        Args:
            documents: Dokümanlar.
            max_sentences: Maks cümle.

        Returns:
            Özet bilgisi.
        """
        documents = documents or []

        all_sentences: list[
            tuple[str, str]
        ] = []
        for doc in documents:
            did = doc.get("doc_id", "")
            content = doc.get("content", "")
            for s in self._split_sentences(
                content,
            ):
                all_sentences.append(
                    (did, s),
                )

        # Uzun cümleleri seç
        all_sentences.sort(
            key=lambda x: len(x[1].split()),
            reverse=True,
        )

        selected = all_sentences[
            :max_sentences
        ]
        summary = " ".join(
            s for _, s in selected
        )

        self._stats[
            "multi_doc_summaries"
        ] += 1

        return {
            "documents_count": len(documents),
            "summary": summary,
            "sentences_used": len(selected),
            "generated": True,
        }

    def _split_sentences(
        self,
        text: str,
    ) -> list[str]:
        """Cümlelere böler."""
        if not text:
            return []

        sentences = []
        current = ""

        for char in text:
            current += char
            if char in ".!?":
                stripped = current.strip()
                if stripped:
                    sentences.append(stripped)
                current = ""

        if current.strip():
            sentences.append(
                current.strip(),
            )

        return sentences

    @property
    def summary_count(self) -> int:
        """Özet sayısı."""
        return self._stats[
            "summaries_generated"
        ]

    @property
    def multi_doc_count(self) -> int:
        """Çoklu doküman özet sayısı."""
        return self._stats[
            "multi_doc_summaries"
        ]
