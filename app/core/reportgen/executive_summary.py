"""ATLAS Yönetici Özeti modülü.

Anahtar nokta çıkarma, öne çıkan üretimi,
TL;DR oluşturma, öncelik sıralama,
aksiyon maddeleri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ExecutiveSummary:
    """Yönetici özeti üretici.

    Uzun raporlardan kısa özetler üretir.

    Attributes:
        _summaries: Özet geçmişi.
    """

    def __init__(
        self,
        max_key_points: int = 5,
    ) -> None:
        """Özet üreticiyi başlatır.

        Args:
            max_key_points: Maks anahtar nokta.
        """
        self._summaries: list[
            dict[str, Any]
        ] = []
        self._max_key_points = max_key_points
        self._counter = 0
        self._stats = {
            "summaries_created": 0,
            "key_points_extracted": 0,
            "action_items_generated": 0,
        }

        logger.info(
            "ExecutiveSummary baslatildi",
        )

    def extract_key_points(
        self,
        content: str,
        max_points: int | None = None,
    ) -> dict[str, Any]:
        """Anahtar noktaları çıkarır.

        Args:
            content: Kaynak içerik.
            max_points: Maks nokta sayısı.

        Returns:
            Çıkarma bilgisi.
        """
        limit = max_points or self._max_key_points
        sentences = [
            s.strip()
            for s in content.split(".")
            if s.strip()
        ]
        points = sentences[:limit]

        self._stats[
            "key_points_extracted"
        ] += len(points)

        return {
            "key_points": points,
            "count": len(points),
            "source_length": len(content),
        }

    def generate_highlights(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Öne çıkanları üretir.

        Args:
            data: Kaynak veri.

        Returns:
            Öne çıkan bilgisi.
        """
        highlights = []
        for key, value in data.items():
            highlights.append({
                "metric": key,
                "value": value,
                "highlight": (
                    f"{key}: {value}"
                ),
            })

        return {
            "highlights": highlights,
            "count": len(highlights),
        }

    def create_tldr(
        self,
        content: str,
        max_chars: int = 280,
    ) -> dict[str, Any]:
        """TL;DR oluşturur.

        Args:
            content: Kaynak içerik.
            max_chars: Maks karakter.

        Returns:
            TL;DR bilgisi.
        """
        words = content.split()
        tldr = ""
        for word in words:
            candidate = (
                f"{tldr} {word}".strip()
            )
            if len(candidate) > max_chars:
                break
            tldr = candidate

        if tldr and not tldr.endswith("."):
            tldr += "."

        return {
            "tldr": tldr,
            "length": len(tldr),
            "max_chars": max_chars,
            "truncated": len(content) > len(
                tldr,
            ),
        }

    def rank_priorities(
        self,
        items: list[dict[str, Any]],
        sort_by: str = "score",
    ) -> dict[str, Any]:
        """Öncelik sıralar.

        Args:
            items: Öğe listesi.
            sort_by: Sıralama kriteri.

        Returns:
            Sıralama bilgisi.
        """
        ranked = sorted(
            items,
            key=lambda x: x.get(sort_by, 0),
            reverse=True,
        )
        for i, item in enumerate(ranked):
            item["rank"] = i + 1

        return {
            "ranked_items": ranked,
            "count": len(ranked),
            "sort_by": sort_by,
        }

    def generate_action_items(
        self,
        insights: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Aksiyon maddeleri üretir.

        Args:
            insights: İçgörü listesi.

        Returns:
            Aksiyon bilgisi.
        """
        actions = []
        for insight in insights:
            action = {
                "action": insight.get(
                    "recommendation",
                    insight.get(
                        "description", "",
                    ),
                ),
                "priority": insight.get(
                    "priority", "medium",
                ),
                "owner": insight.get(
                    "owner", "unassigned",
                ),
                "deadline": insight.get(
                    "deadline", None,
                ),
            }
            actions.append(action)
            self._stats[
                "action_items_generated"
            ] += 1

        return {
            "action_items": actions,
            "count": len(actions),
        }

    def create_summary(
        self,
        report_id: str,
        content: str,
        data: dict[str, Any] | None = None,
        insights: list[
            dict[str, Any]
        ] | None = None,
    ) -> dict[str, Any]:
        """Tam özet oluşturur.

        Args:
            report_id: Rapor ID.
            content: İçerik.
            data: Veri.
            insights: İçgörüler.

        Returns:
            Özet bilgisi.
        """
        self._counter += 1
        sid = f"sum_{self._counter}"

        key_points = self.extract_key_points(
            content,
        )
        tldr = self.create_tldr(content)
        highlights = self.generate_highlights(
            data or {},
        )
        actions = self.generate_action_items(
            insights or [],
        )

        summary = {
            "summary_id": sid,
            "report_id": report_id,
            "tldr": tldr["tldr"],
            "key_points": (
                key_points["key_points"]
            ),
            "highlights": (
                highlights["highlights"]
            ),
            "action_items": (
                actions["action_items"]
            ),
            "created_at": time.time(),
        }
        self._summaries.append(summary)
        self._stats["summaries_created"] += 1

        return summary

    def get_summaries(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Özetleri getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Özet listesi.
        """
        return list(
            self._summaries[-limit:],
        )

    @property
    def summary_count(self) -> int:
        """Özet sayısı."""
        return self._stats[
            "summaries_created"
        ]

    @property
    def action_item_count(self) -> int:
        """Aksiyon maddesi sayısı."""
        return self._stats[
            "action_items_generated"
        ]
