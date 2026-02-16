"""ATLAS Bilgi Boşluğu Bulucu modülü.

Kapsam analizi, eksik konular,
güncel olmayan içerik, kalite boşlukları,
öncelik önerileri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeGapFinder:
    """Bilgi boşluğu bulucu.

    Bilgi tabanındaki boşlukları tespit eder.

    Attributes:
        _pages: Sayfa kayıtları.
        _gaps: Boşluk kayıtları.
    """

    def __init__(self) -> None:
        """Boşluk bulucuyu başlatır."""
        self._pages: dict[
            str, dict[str, Any]
        ] = {}
        self._expected_topics: list[
            str
        ] = []
        self._gaps: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "gaps_found": 0,
            "analyses_run": 0,
        }

        logger.info(
            "KnowledgeGapFinder baslatildi",
        )

    def add_page(
        self,
        page_id: str,
        title: str = "",
        topics: list[str]
        | None = None,
        quality_score: float = 0.0,
        last_updated: float = 0.0,
    ) -> dict[str, Any]:
        """Sayfa ekler.

        Args:
            page_id: Sayfa kimliği.
            title: Başlık.
            topics: Konular.
            quality_score: Kalite puanı.
            last_updated: Son güncelleme.

        Returns:
            Ekleme bilgisi.
        """
        topics = topics or []

        self._pages[page_id] = {
            "page_id": page_id,
            "title": title,
            "topics": topics,
            "quality_score": quality_score,
            "last_updated": (
                last_updated
                or time.time()
            ),
        }

        return {
            "page_id": page_id,
            "added": True,
        }

    def set_expected_topics(
        self,
        topics: list[str],
    ) -> dict[str, Any]:
        """Beklenen konuları ayarlar.

        Args:
            topics: Beklenen konular.

        Returns:
            Ayarlama bilgisi.
        """
        self._expected_topics = topics

        return {
            "topics_set": len(topics),
            "set_ok": True,
        }

    def analyze_coverage(
        self,
    ) -> dict[str, Any]:
        """Kapsam analizi yapar.

        Returns:
            Analiz bilgisi.
        """
        covered_topics: set[str] = set()
        for page in self._pages.values():
            for t in page.get(
                "topics", [],
            ):
                covered_topics.add(
                    t.lower(),
                )

        expected = set(
            t.lower()
            for t in self._expected_topics
        )

        missing = expected - covered_topics
        coverage_pct = round(
            len(covered_topics & expected)
            / max(len(expected), 1) * 100,
            1,
        )

        self._stats["analyses_run"] += 1

        return {
            "covered": len(
                covered_topics & expected,
            ),
            "total_expected": len(expected),
            "missing": list(missing),
            "coverage_percentage": (
                coverage_pct
            ),
            "analyzed": True,
        }

    def find_missing_topics(
        self,
    ) -> dict[str, Any]:
        """Eksik konuları bulur.

        Returns:
            Eksik konu bilgisi.
        """
        covered: set[str] = set()
        for page in self._pages.values():
            for t in page.get(
                "topics", [],
            ):
                covered.add(t.lower())

        expected = set(
            t.lower()
            for t in self._expected_topics
        )

        missing = list(
            expected - covered,
        )

        for topic in missing:
            self._counter += 1
            gid = f"gap_{self._counter}"
            self._gaps.append({
                "gap_id": gid,
                "topic": topic,
                "type": "missing",
                "severity": "high",
            })
            self._stats["gaps_found"] += 1

        return {
            "missing_topics": missing,
            "count": len(missing),
            "found": True,
        }

    def find_outdated(
        self,
        max_age_days: int = 90,
    ) -> dict[str, Any]:
        """Güncel olmayan içerik bulur.

        Args:
            max_age_days: Maks yaş (gün).

        Returns:
            Güncel olmayan bilgisi.
        """
        now = time.time()
        max_age_secs = (
            max_age_days * 86400
        )

        outdated: list[
            dict[str, Any]
        ] = []

        for pid, page in (
            self._pages.items()
        ):
            age = (
                now
                - page.get(
                    "last_updated", now,
                )
            )
            if age > max_age_secs:
                outdated.append({
                    "page_id": pid,
                    "title": page.get(
                        "title", "",
                    ),
                    "age_days": round(
                        age / 86400,
                    ),
                })

        return {
            "outdated": outdated,
            "count": len(outdated),
            "max_age_days": max_age_days,
            "found": True,
        }

    def find_quality_gaps(
        self,
        min_score: float = 0.6,
    ) -> dict[str, Any]:
        """Kalite boşlukları bulur.

        Args:
            min_score: Minimum puan.

        Returns:
            Kalite boşluk bilgisi.
        """
        low_quality: list[
            dict[str, Any]
        ] = []

        for pid, page in (
            self._pages.items()
        ):
            score = page.get(
                "quality_score", 0.0,
            )
            if score < min_score:
                low_quality.append({
                    "page_id": pid,
                    "title": page.get(
                        "title", "",
                    ),
                    "score": score,
                    "gap": round(
                        min_score - score, 2,
                    ),
                })

        low_quality.sort(
            key=lambda p: p["score"],
        )

        return {
            "low_quality": low_quality,
            "count": len(low_quality),
            "min_score": min_score,
            "found": True,
        }

    def suggest_priorities(
        self,
    ) -> dict[str, Any]:
        """Öncelik önerisi verir.

        Returns:
            Öneri bilgisi.
        """
        suggestions: list[
            dict[str, Any]
        ] = []

        coverage = self.analyze_coverage()
        missing = coverage.get(
            "missing", [],
        )
        for topic in missing[:5]:
            suggestions.append({
                "action": "create",
                "topic": topic,
                "priority": "high",
                "reason": "Missing topic",
            })

        quality = self.find_quality_gaps()
        for page in quality.get(
            "low_quality", [],
        )[:5]:
            suggestions.append({
                "action": "improve",
                "page_id": page["page_id"],
                "priority": "medium",
                "reason": "Low quality",
            })

        return {
            "suggestions": suggestions,
            "count": len(suggestions),
            "suggested": True,
        }

    @property
    def gap_count(self) -> int:
        """Boşluk sayısı."""
        return self._stats["gaps_found"]

    @property
    def analysis_count(self) -> int:
        """Analiz sayısı."""
        return self._stats[
            "analyses_run"
        ]
