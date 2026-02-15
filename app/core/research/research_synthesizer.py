"""ATLAS Araştırma Sentezleyici modülü.

Bilgi füzyonu, boşluk tespiti,
anlatı oluşturma, anahtar çıkarım,
yönetici özeti.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ResearchSynthesizer:
    """Araştırma sentezleyici.

    Birden fazla kaynaktan gelen bilgileri
    sentezler ve anlamlı çıkarımlar yapar.

    Attributes:
        _syntheses: Sentez geçmişi.
        _insights: Çıkarım kayıtları.
    """

    def __init__(self) -> None:
        """Sentezleyiciyi başlatır."""
        self._syntheses: list[
            dict[str, Any]
        ] = []
        self._insights: list[
            dict[str, Any]
        ] = []
        self._gaps: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "syntheses": 0,
            "insights_extracted": 0,
            "gaps_identified": 0,
            "summaries_generated": 0,
        }

        logger.info(
            "ResearchSynthesizer baslatildi",
        )

    def synthesize(
        self,
        facts: list[dict[str, Any]],
        topic: str = "",
    ) -> dict[str, Any]:
        """Bilgileri sentezler.

        Args:
            facts: Gerçek listesi.
            topic: Araştırma konusu.

        Returns:
            Sentez bilgisi.
        """
        self._counter += 1
        sid = f"syn_{self._counter}"

        # Bilgi füzyonu
        fused = self._fuse_information(facts)

        # Boşluk tespiti
        gaps = self._identify_gaps(
            facts, topic,
        )

        # Anahtar çıkarımlar
        insights = self._extract_insights(
            fused,
        )

        # Anlatı
        narrative = self._build_narrative(
            fused, topic,
        )

        synthesis = {
            "synthesis_id": sid,
            "topic": topic,
            "fused_facts": fused,
            "fact_count": len(fused),
            "gaps": gaps,
            "insights": insights,
            "narrative": narrative,
            "timestamp": time.time(),
        }
        self._syntheses.append(synthesis)
        self._stats["syntheses"] += 1

        return synthesis

    def _fuse_information(
        self,
        facts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Bilgi füzyonu yapar."""
        fused = []
        seen_content = set()

        for fact in sorted(
            facts,
            key=lambda f: f.get(
                "confidence", 0,
            ),
            reverse=True,
        ):
            content = fact.get(
                "content", "",
            ).lower()[:50]
            if content not in seen_content:
                seen_content.add(content)
                fused.append(dict(fact))

        return fused

    def _identify_gaps(
        self,
        facts: list[dict[str, Any]],
        topic: str,
    ) -> list[dict[str, Any]]:
        """Bilgi boşluklarını tespit eder."""
        gaps = []
        topic_words = topic.lower().split()

        # Eksik konuları bul
        covered_topics = set()
        for fact in facts:
            content = fact.get(
                "content", "",
            ).lower()
            for word in topic_words:
                if word in content:
                    covered_topics.add(word)

        uncovered = [
            w for w in topic_words
            if w not in covered_topics
            and len(w) > 3
        ]

        for word in uncovered:
            gap = {
                "topic": word,
                "type": "uncovered_aspect",
                "suggestion": (
                    f"Research more about "
                    f"'{word}' aspect"
                ),
            }
            gaps.append(gap)
            self._gaps.append(gap)
            self._stats["gaps_identified"] += 1

        # Düşük güvenli alanlar
        low_confidence = [
            f for f in facts
            if f.get("confidence", 0) < 0.3
        ]
        if low_confidence:
            gaps.append({
                "topic": "low_confidence_areas",
                "type": "verification_needed",
                "count": len(low_confidence),
                "suggestion": (
                    "Verify facts with "
                    "low confidence scores"
                ),
            })
            self._stats["gaps_identified"] += 1

        return gaps

    def _extract_insights(
        self,
        fused_facts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Anahtar çıkarımlar çıkarır."""
        insights = []

        # En güvenilir gerçeklerden çıkarım
        top_facts = sorted(
            fused_facts,
            key=lambda f: f.get(
                "confidence", 0,
            ),
            reverse=True,
        )[:5]

        for i, fact in enumerate(top_facts):
            insight = {
                "rank": i + 1,
                "content": fact.get(
                    "content", "",
                ),
                "confidence": fact.get(
                    "confidence", 0,
                ),
                "type": "key_finding",
            }
            insights.append(insight)
            self._insights.append(insight)
            self._stats[
                "insights_extracted"
            ] += 1

        return insights

    def _build_narrative(
        self,
        fused_facts: list[dict[str, Any]],
        topic: str,
    ) -> str:
        """Anlatı oluşturur."""
        if not fused_facts:
            return (
                f"No information found "
                f"about {topic}."
            )

        parts = [
            f"Research on '{topic}' "
            f"revealed {len(fused_facts)} "
            f"key findings.",
        ]

        for fact in fused_facts[:3]:
            content = fact.get("content", "")
            if content:
                parts.append(content)

        return " ".join(parts)

    def generate_executive_summary(
        self,
        synthesis_id: str,
    ) -> dict[str, Any]:
        """Yönetici özeti üretir.

        Args:
            synthesis_id: Sentez ID.

        Returns:
            Özet bilgisi.
        """
        synthesis = None
        for s in self._syntheses:
            if s["synthesis_id"] == synthesis_id:
                synthesis = s
                break

        if not synthesis:
            return {
                "error": "synthesis_not_found",
            }

        insights = synthesis.get("insights", [])
        gaps = synthesis.get("gaps", [])

        summary = {
            "synthesis_id": synthesis_id,
            "topic": synthesis["topic"],
            "key_findings": len(insights),
            "knowledge_gaps": len(gaps),
            "top_insights": insights[:3],
            "narrative": synthesis["narrative"],
            "recommendation": (
                "Address knowledge gaps"
                if gaps else
                "Research is comprehensive"
            ),
        }
        self._stats[
            "summaries_generated"
        ] += 1

        return summary

    def get_insights(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Çıkarımları getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Çıkarım listesi.
        """
        return list(self._insights[-limit:])

    def get_gaps(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Boşlukları getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Boşluk listesi.
        """
        return list(self._gaps[-limit:])

    @property
    def synthesis_count(self) -> int:
        """Sentez sayısı."""
        return self._stats["syntheses"]

    @property
    def insight_count(self) -> int:
        """Çıkarım sayısı."""
        return self._stats[
            "insights_extracted"
        ]

    @property
    def gap_count(self) -> int:
        """Boşluk sayısı."""
        return self._stats["gaps_identified"]
