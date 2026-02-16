"""ATLAS Doküman Sınıflandırıcı modülü.

Otomatik sınıflandırma, tip tespiti,
kategori atama, güven puanlama,
çoklu etiket desteği.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """Doküman sınıflandırıcı.

    Dokümanları otomatik sınıflandırır.

    Attributes:
        _classifications: Sınıflandırma kayıtları.
        _rules: Sınıflandırma kuralları.
    """

    def __init__(self) -> None:
        """Sınıflandırıcıyı başlatır."""
        self._classifications: list[
            dict[str, Any]
        ] = []
        self._rules: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "documents_classified": 0,
            "multi_label_count": 0,
        }
        self._type_keywords: dict[
            str, list[str]
        ] = {
            "contract": [
                "contract",
                "agreement",
                "terms",
                "sözleşme",
            ],
            "invoice": [
                "invoice",
                "fatura",
                "payment",
                "ödeme",
            ],
            "report": [
                "report",
                "rapor",
                "analysis",
                "analiz",
            ],
            "proposal": [
                "proposal",
                "teklif",
                "offer",
                "öneri",
            ],
        }

        logger.info(
            "DocumentClassifier baslatildi",
        )

    def auto_classify(
        self,
        title: str = "",
        content: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Otomatik sınıflandırma yapar.

        Args:
            title: Başlık.
            content: İçerik.
            metadata: Üstveri.

        Returns:
            Sınıflandırma bilgisi.
        """
        self._counter += 1
        cid = f"cls_{self._counter}"

        doc_type = self._detect_type(
            title, content,
        )
        category = self._assign_category(
            title, content,
        )
        confidence = self._calculate_confidence(
            title, content, doc_type,
        )

        result = {
            "classification_id": cid,
            "title": title,
            "doc_type": doc_type,
            "category": category,
            "confidence": confidence,
            "classified": True,
            "timestamp": time.time(),
        }

        self._classifications.append(result)
        self._stats[
            "documents_classified"
        ] += 1

        return result

    def detect_type(
        self,
        title: str = "",
        content: str = "",
    ) -> dict[str, Any]:
        """Tip tespiti yapar.

        Args:
            title: Başlık.
            content: İçerik.

        Returns:
            Tespit bilgisi.
        """
        doc_type = self._detect_type(
            title, content,
        )
        confidence = self._calculate_confidence(
            title, content, doc_type,
        )

        return {
            "doc_type": doc_type,
            "confidence": confidence,
            "detected": True,
        }

    def assign_category(
        self,
        title: str = "",
        content: str = "",
        custom_category: str = "",
    ) -> dict[str, Any]:
        """Kategori atar.

        Args:
            title: Başlık.
            content: İçerik.
            custom_category: Özel kategori.

        Returns:
            Atama bilgisi.
        """
        if custom_category:
            category = custom_category
        else:
            category = self._assign_category(
                title, content,
            )

        return {
            "category": category,
            "custom": bool(custom_category),
            "assigned": True,
        }

    def score_confidence(
        self,
        title: str = "",
        content: str = "",
        doc_type: str = "",
    ) -> dict[str, Any]:
        """Güven puanı hesaplar.

        Args:
            title: Başlık.
            content: İçerik.
            doc_type: Doküman tipi.

        Returns:
            Puan bilgisi.
        """
        confidence = self._calculate_confidence(
            title, content, doc_type,
        )

        level = (
            "high"
            if confidence >= 0.8
            else "medium"
            if confidence >= 0.5
            else "low"
        )

        return {
            "confidence": confidence,
            "level": level,
            "scored": True,
        }

    def multi_label_classify(
        self,
        title: str = "",
        content: str = "",
    ) -> dict[str, Any]:
        """Çoklu etiket sınıflandırma yapar.

        Args:
            title: Başlık.
            content: İçerik.

        Returns:
            Sınıflandırma bilgisi.
        """
        labels = []
        text = f"{title} {content}".lower()

        for dtype, keywords in (
            self._type_keywords.items()
        ):
            for kw in keywords:
                if kw in text:
                    labels.append(dtype)
                    break

        if not labels:
            labels = ["report"]

        self._stats[
            "multi_label_count"
        ] += 1

        return {
            "labels": labels,
            "count": len(labels),
            "multi_label": len(labels) > 1,
            "classified": True,
        }

    def _detect_type(
        self,
        title: str,
        content: str,
    ) -> str:
        """Tip tespit eder."""
        text = f"{title} {content}".lower()

        for dtype, keywords in (
            self._type_keywords.items()
        ):
            for kw in keywords:
                if kw in text:
                    return dtype

        return "report"

    def _assign_category(
        self,
        title: str,
        content: str,
    ) -> str:
        """Kategori atar."""
        text = f"{title} {content}".lower()

        category_keywords = {
            "legal": [
                "legal",
                "hukuk",
                "contract",
                "sözleşme",
            ],
            "financial": [
                "financial",
                "finans",
                "invoice",
                "fatura",
            ],
            "technical": [
                "technical",
                "teknik",
                "code",
                "system",
            ],
            "marketing": [
                "marketing",
                "pazarlama",
                "campaign",
                "reklam",
            ],
        }

        for cat, keywords in (
            category_keywords.items()
        ):
            for kw in keywords:
                if kw in text:
                    return cat

        return "technical"

    def _calculate_confidence(
        self,
        title: str,
        content: str,
        doc_type: str,
    ) -> float:
        """Güven puanı hesaplar."""
        score = 0.3

        if title:
            score += 0.2
        if content:
            score += 0.2

        text = f"{title} {content}".lower()
        keywords = self._type_keywords.get(
            doc_type, [],
        )
        match_count = sum(
            1 for kw in keywords
            if kw in text
        )
        if match_count > 0:
            score += min(
                match_count * 0.15, 0.3,
            )

        return round(min(score, 1.0), 2)

    @property
    def classification_count(self) -> int:
        """Sınıflandırma sayısı."""
        return self._stats[
            "documents_classified"
        ]

    @property
    def multi_label_count(self) -> int:
        """Çoklu etiket sayısı."""
        return self._stats[
            "multi_label_count"
        ]
