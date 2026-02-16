"""ATLAS Kriz Sonrası Analizcisi modülü.

Kök neden analizi, zaman çizelgesi yeniden
yapılandırma, etki değerlendirmesi,
alınan dersler, iyileştirme önerileri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PostCrisisAnalyzer:
    """Kriz sonrası analizcisi.

    Kriz sonrası analizleri yapar.

    Attributes:
        _analyses: Analiz kayıtları.
        _lessons: Ders kayıtları.
    """

    def __init__(self) -> None:
        """Analizciyi başlatır."""
        self._analyses: dict[
            str, dict[str, Any]
        ] = {}
        self._lessons: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "analyses_completed": 0,
            "lessons_learned": 0,
        }

        logger.info(
            "PostCrisisAnalyzer "
            "baslatildi",
        )

    def root_cause_analysis(
        self,
        crisis_id: str,
        symptoms: list[str]
        | None = None,
        contributing_factors: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Kök neden analizi yapar.

        Args:
            crisis_id: Kriz kimliği.
            symptoms: Belirtiler.
            contributing_factors: Katkı
                yapan faktörler.

        Returns:
            Analiz bilgisi.
        """
        symptoms = symptoms or []
        contributing_factors = (
            contributing_factors or []
        )

        root_cause = (
            contributing_factors[0]
            if contributing_factors
            else "Unknown"
        )

        self._analyses[crisis_id] = {
            "crisis_id": crisis_id,
            "root_cause": root_cause,
            "symptoms": symptoms,
            "factors": (
                contributing_factors
            ),
            "timestamp": time.time(),
        }

        self._stats[
            "analyses_completed"
        ] += 1

        return {
            "crisis_id": crisis_id,
            "root_cause": root_cause,
            "symptom_count": len(symptoms),
            "factor_count": len(
                contributing_factors,
            ),
            "analyzed": True,
        }

    def reconstruct_timeline(
        self,
        crisis_id: str,
        events: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Zaman çizelgesi yeniden yapılandırır.

        Args:
            crisis_id: Kriz kimliği.
            events: Olaylar.

        Returns:
            Çizelge bilgisi.
        """
        events = events or []

        sorted_events = sorted(
            events,
            key=lambda e: e.get(
                "timestamp", 0,
            ),
        )

        if len(sorted_events) >= 2:
            duration = (
                sorted_events[-1].get(
                    "timestamp", 0,
                )
                - sorted_events[0].get(
                    "timestamp", 0,
                )
            )
        else:
            duration = 0

        return {
            "crisis_id": crisis_id,
            "events": sorted_events,
            "event_count": len(
                sorted_events,
            ),
            "duration_seconds": duration,
            "reconstructed": True,
        }

    def assess_impact(
        self,
        crisis_id: str,
        financial_impact: float = 0.0,
        affected_users: int = 0,
        downtime_minutes: int = 0,
        reputation_impact: str = "low",
    ) -> dict[str, Any]:
        """Etki değerlendirmesi yapar.

        Args:
            crisis_id: Kriz kimliği.
            financial_impact: Mali etki.
            affected_users: Etkilenen kullanıcı.
            downtime_minutes: Kesinti süresi.
            reputation_impact: İtibar etkisi.

        Returns:
            Değerlendirme bilgisi.
        """
        severity_scores = {
            "low": 1,
            "moderate": 2,
            "high": 3,
            "critical": 4,
        }

        impact_score = (
            severity_scores.get(
                reputation_impact, 1,
            )
        )
        if financial_impact > 10000:
            impact_score += 2
        elif financial_impact > 1000:
            impact_score += 1

        if affected_users > 1000:
            impact_score += 2
        elif affected_users > 100:
            impact_score += 1

        overall = (
            "critical"
            if impact_score >= 7
            else "high"
            if impact_score >= 5
            else "moderate"
            if impact_score >= 3
            else "low"
        )

        analysis = self._analyses.get(
            crisis_id, {},
        )
        analysis["impact"] = {
            "financial": financial_impact,
            "affected_users": (
                affected_users
            ),
            "downtime_minutes": (
                downtime_minutes
            ),
            "overall": overall,
        }

        return {
            "crisis_id": crisis_id,
            "overall_impact": overall,
            "impact_score": impact_score,
            "assessed": True,
        }

    def extract_lessons(
        self,
        crisis_id: str,
        lessons: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Alınan dersleri çıkarır.

        Args:
            crisis_id: Kriz kimliği.
            lessons: Dersler.

        Returns:
            Çıkarma bilgisi.
        """
        lessons = lessons or []

        for lesson in lessons:
            self._counter += 1
            lid = f"lsn_{self._counter}"
            self._lessons.append({
                "lesson_id": lid,
                "crisis_id": crisis_id,
                "lesson": lesson,
                "timestamp": time.time(),
            })
            self._stats[
                "lessons_learned"
            ] += 1

        return {
            "crisis_id": crisis_id,
            "lessons_added": len(lessons),
            "total_lessons": len(
                self._lessons,
            ),
            "extracted": True,
        }

    def recommend_improvements(
        self,
        crisis_id: str,
    ) -> dict[str, Any]:
        """İyileştirme önerir.

        Args:
            crisis_id: Kriz kimliği.

        Returns:
            Öneri bilgisi.
        """
        analysis = self._analyses.get(
            crisis_id,
        )
        recommendations = []

        if analysis:
            factors = analysis.get(
                "factors", [],
            )
            for f in factors:
                recommendations.append({
                    "area": f,
                    "action": (
                        f"Address: {f}"
                    ),
                    "priority": "high",
                })

        impact = (
            analysis.get("impact", {})
            if analysis
            else {}
        )
        if impact.get(
            "downtime_minutes", 0,
        ) > 60:
            recommendations.append({
                "area": "redundancy",
                "action": (
                    "Improve system "
                    "redundancy"
                ),
                "priority": "high",
            })

        if not recommendations:
            recommendations.append({
                "area": "general",
                "action": (
                    "Continue monitoring"
                ),
                "priority": "low",
            })

        return {
            "crisis_id": crisis_id,
            "recommendations": (
                recommendations
            ),
            "count": len(recommendations),
            "recommended": True,
        }

    @property
    def analysis_count(self) -> int:
        """Analiz sayısı."""
        return self._stats[
            "analyses_completed"
        ]

    @property
    def lesson_count(self) -> int:
        """Ders sayısı."""
        return self._stats[
            "lessons_learned"
        ]
