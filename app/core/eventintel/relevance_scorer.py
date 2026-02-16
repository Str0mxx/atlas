"""ATLAS Etkinlik Alaka Puanlayıcı.

Alaka puanlama, ilgi eşleme, ROI tahmini,
öncelik sıralama ve kişiselleştirme.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventRelevanceScorer:
    """Etkinlik alaka puanlayıcısı.

    Etkinliklerin alakasını puanlar,
    ilgi alanlarıyla eşler ve önceliklendirir.

    Attributes:
        _scores: Puan kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Puanlayıcıyı başlatır."""
        self._scores: dict[str, dict] = {}
        self._stats = {
            "events_scored": 0,
            "priorities_set": 0,
        }
        logger.info(
            "EventRelevanceScorer "
            "baslatildi",
        )

    @property
    def scored_count(self) -> int:
        """Puanlanan etkinlik sayısı."""
        return self._stats["events_scored"]

    @property
    def priority_count(self) -> int:
        """Önceliklendirilen sayı."""
        return self._stats["priorities_set"]

    def score_relevance(
        self,
        event_id: str,
        topic_match: float = 0.0,
        speaker_quality: float = 0.0,
        networking_value: float = 0.0,
    ) -> dict[str, Any]:
        """Alaka puanı hesaplar.

        Args:
            event_id: Etkinlik kimliği.
            topic_match: Konu eşleşmesi.
            speaker_quality: Konuşmacı kalitesi.
            networking_value: Ağ kurma değeri.

        Returns:
            Puan bilgisi.
        """
        score = (
            topic_match * 0.4
            + speaker_quality * 0.3
            + networking_value * 0.3
        )

        if score >= 0.8:
            level = "must_attend"
        elif score >= 0.6:
            level = "recommended"
        elif score >= 0.4:
            level = "consider"
        else:
            level = "skip"

        self._scores[event_id] = {
            "score": round(score, 2),
            "level": level,
        }
        self._stats["events_scored"] += 1

        logger.info(
            "Alaka puani: %s -> %.2f (%s)",
            event_id,
            score,
            level,
        )

        return {
            "event_id": event_id,
            "score": round(score, 2),
            "level": level,
            "scored": True,
        }

    def match_interests(
        self,
        event_id: str,
        event_topics: list[str]
        | None = None,
        user_interests: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """İlgi eşlemesi yapar.

        Args:
            event_id: Etkinlik kimliği.
            event_topics: Etkinlik konuları.
            user_interests: Kullanıcı ilgileri.

        Returns:
            Eşleme bilgisi.
        """
        if event_topics is None:
            event_topics = []
        if user_interests is None:
            user_interests = []

        e_set = set(event_topics)
        u_set = set(user_interests)
        overlap = e_set & u_set
        match = (
            len(overlap) / len(e_set)
            if e_set
            else 0.0
        )

        return {
            "event_id": event_id,
            "overlap": sorted(overlap),
            "match_score": round(match, 2),
            "matched": True,
        }

    def estimate_roi(
        self,
        event_id: str,
        ticket_cost: float = 0.0,
        travel_cost: float = 0.0,
        expected_leads: int = 0,
        lead_value: float = 0.0,
    ) -> dict[str, Any]:
        """ROI tahmini yapar.

        Args:
            event_id: Etkinlik kimliği.
            ticket_cost: Bilet maliyeti.
            travel_cost: Seyahat maliyeti.
            expected_leads: Beklenen lead sayısı.
            lead_value: Lead değeri.

        Returns:
            ROI tahmini bilgisi.
        """
        total_cost = ticket_cost + travel_cost
        expected_revenue = (
            expected_leads * lead_value
        )
        roi = (
            (expected_revenue - total_cost)
            / total_cost
            * 100
            if total_cost > 0
            else 0.0
        )

        return {
            "event_id": event_id,
            "total_cost": total_cost,
            "expected_revenue": (
                expected_revenue
            ),
            "estimated_roi": round(roi, 1),
            "estimated": True,
        }

    def rank_priority(
        self,
        events: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Öncelik sıralaması yapar.

        Args:
            events: Etkinlik listesi
                (id, score çiftleri).

        Returns:
            Sıralama bilgisi.
        """
        if events is None:
            events = []

        ranked = sorted(
            events,
            key=lambda x: x.get("score", 0),
            reverse=True,
        )
        self._stats[
            "priorities_set"
        ] += len(ranked)

        return {
            "ranked": ranked,
            "total": len(ranked),
            "ranked_done": True,
        }

    def personalize_score(
        self,
        event_id: str,
        base_score: float = 0.0,
        past_attendance: int = 0,
        preference_boost: float = 0.0,
    ) -> dict[str, Any]:
        """Kişiselleştirilmiş puan hesaplar.

        Args:
            event_id: Etkinlik kimliği.
            base_score: Temel puan.
            past_attendance: Geçmiş katılım.
            preference_boost: Tercih artışı.

        Returns:
            Kişisel puan bilgisi.
        """
        attendance_bonus = min(
            past_attendance * 0.05, 0.2,
        )
        final = min(
            base_score
            + attendance_bonus
            + preference_boost,
            1.0,
        )

        return {
            "event_id": event_id,
            "base_score": base_score,
            "final_score": round(final, 2),
            "personalized": True,
        }
