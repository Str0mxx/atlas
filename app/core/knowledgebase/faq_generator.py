"""ATLAS SSS Üretici modülü.

Soru çıkarma, yanıt üretimi,
kategori gruplama, popülerlik sıralaması,
otomatik güncelleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FAQGenerator:
    """SSS üretici.

    Sıkça sorulan soruları üretir.

    Attributes:
        _faqs: SSS kayıtları.
        _categories: Kategori grupları.
    """

    def __init__(self) -> None:
        """Üreticiyi başlatır."""
        self._faqs: dict[
            str, dict[str, Any]
        ] = {}
        self._categories: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "faqs_generated": 0,
            "questions_extracted": 0,
        }

        logger.info(
            "FAQGenerator baslatildi",
        )

    def extract_questions(
        self,
        content: str,
        source: str = "",
    ) -> dict[str, Any]:
        """Soru çıkarır.

        Args:
            content: İçerik metni.
            source: Kaynak.

        Returns:
            Çıkarma bilgisi.
        """
        sentences = [
            s.strip()
            for s in content.split(".")
            if s.strip()
        ]

        questions = [
            s for s in sentences
            if "?" in s
            or s.lower().startswith(
                ("how", "what", "why",
                 "when", "nasıl", "ne",
                 "neden", "nerede"),
            )
        ]

        if not questions and sentences:
            questions = [
                f"{s}?"
                for s in sentences[:3]
            ]

        self._stats[
            "questions_extracted"
        ] += len(questions)

        return {
            "questions": questions,
            "count": len(questions),
            "source": source,
            "extracted": True,
        }

    def generate_answer(
        self,
        question: str,
        context: str = "",
        category: str = "general",
    ) -> dict[str, Any]:
        """Yanıt üretir.

        Args:
            question: Soru.
            context: Bağlam.
            category: Kategori.

        Returns:
            Üretim bilgisi.
        """
        self._counter += 1
        fid = f"faq_{self._counter}"

        answer = (
            f"Answer for: {question}"
        )
        if context:
            answer = (
                f"Based on context: "
                f"{context[:50]}. "
                f"{answer}"
            )

        self._faqs[fid] = {
            "faq_id": fid,
            "question": question,
            "answer": answer,
            "category": category,
            "views": 0,
            "helpful": 0,
            "timestamp": time.time(),
        }

        cat_list = self._categories.get(
            category, [],
        )
        cat_list.append(fid)
        self._categories[
            category
        ] = cat_list

        self._stats[
            "faqs_generated"
        ] += 1

        return {
            "faq_id": fid,
            "question": question,
            "answer": answer,
            "category": category,
            "generated": True,
        }

    def group_by_category(
        self,
    ) -> dict[str, Any]:
        """Kategoriye göre gruplar.

        Returns:
            Gruplama bilgisi.
        """
        grouped: dict[
            str, list[dict[str, Any]]
        ] = {}

        for fid, faq in self._faqs.items():
            cat = faq.get(
                "category", "general",
            )
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append({
                "faq_id": fid,
                "question": faq["question"],
            })

        return {
            "categories": list(
                grouped.keys(),
            ),
            "grouped": grouped,
            "category_count": len(grouped),
            "total_faqs": len(self._faqs),
            "grouped_ok": True,
        }

    def rank_by_popularity(
        self,
    ) -> dict[str, Any]:
        """Popülerliğe göre sıralar.

        Returns:
            Sıralama bilgisi.
        """
        ranked = sorted(
            self._faqs.values(),
            key=lambda f: f.get(
                "views", 0,
            ),
            reverse=True,
        )

        return {
            "ranked": [
                {
                    "faq_id": f["faq_id"],
                    "question": f["question"],
                    "views": f["views"],
                }
                for f in ranked
            ],
            "count": len(ranked),
            "ranked_ok": True,
        }

    def auto_update(
        self,
        faq_id: str,
        new_answer: str = "",
        increment_views: bool = False,
    ) -> dict[str, Any]:
        """Otomatik günceller.

        Args:
            faq_id: SSS kimliği.
            new_answer: Yeni yanıt.
            increment_views: Görüntü artır.

        Returns:
            Güncelleme bilgisi.
        """
        faq = self._faqs.get(faq_id)
        if not faq:
            return {
                "faq_id": faq_id,
                "found": False,
            }

        if new_answer:
            faq["answer"] = new_answer

        if increment_views:
            faq["views"] = (
                faq.get("views", 0) + 1
            )

        return {
            "faq_id": faq_id,
            "views": faq["views"],
            "updated": True,
        }

    @property
    def faq_count(self) -> int:
        """SSS sayısı."""
        return self._stats[
            "faqs_generated"
        ]

    @property
    def question_count(self) -> int:
        """Çıkarılan soru sayısı."""
        return self._stats[
            "questions_extracted"
        ]
