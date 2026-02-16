"""ATLAS İlişki Puanlayıcı modülü.

İlişki gücü, bağlılık seviyesi,
güncellik ağırlığı, güven puanlama,
trend analizi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RelationshipScorer:
    """İlişki puanlayıcı.

    Kişi ilişkilerini puanlar.

    Attributes:
        _scores: Puan kayıtları.
        _history: Puan geçmişi.
    """

    def __init__(self) -> None:
        """Puanlayıcıyı başlatır."""
        self._scores: dict[
            str, dict[str, Any]
        ] = {}
        self._history: dict[
            str, list[float]
        ] = {}
        self._stats = {
            "scores_calculated": 0,
            "trends_analyzed": 0,
        }

        logger.info(
            "RelationshipScorer "
            "baslatildi",
        )

    def calculate_strength(
        self,
        contact_id: str,
        interaction_count: int = 0,
        recency_days: float = 30.0,
        sentiment_avg: float = 0.5,
        response_rate: float = 0.5,
    ) -> dict[str, Any]:
        """İlişki gücü hesaplar.

        Args:
            contact_id: Kişi ID.
            interaction_count: Etkileşim.
            recency_days: Güncellik (gün).
            sentiment_avg: Ortalama duygu.
            response_rate: Yanıt oranı.

        Returns:
            Güç bilgisi.
        """
        # Etkileşim puanı (0-30)
        int_score = min(
            interaction_count * 3, 30,
        )

        # Güncellik puanı (0-25)
        if recency_days <= 7:
            rec_score = 25
        elif recency_days <= 30:
            rec_score = 20
        elif recency_days <= 90:
            rec_score = 10
        else:
            rec_score = 5

        # Duygu puanı (0-25)
        sent_score = round(
            sentiment_avg * 25, 1,
        )

        # Yanıt puanı (0-20)
        resp_score = round(
            response_rate * 20, 1,
        )

        total = round(
            int_score + rec_score
            + sent_score + resp_score, 1,
        )
        total = min(total, 100)

        strength = (
            "strong" if total >= 70
            else "moderate" if total >= 40
            else "weak" if total >= 20
            else "dormant"
        )

        self._scores[contact_id] = {
            "score": total,
            "strength": strength,
            "timestamp": time.time(),
        }

        if contact_id not in self._history:
            self._history[contact_id] = []
        self._history[contact_id].append(
            total,
        )

        self._stats[
            "scores_calculated"
        ] += 1

        return {
            "contact_id": contact_id,
            "score": total,
            "strength": strength,
            "breakdown": {
                "interaction": int_score,
                "recency": rec_score,
                "sentiment": sent_score,
                "response": resp_score,
            },
        }

    def get_engagement_level(
        self,
        contact_id: str,
    ) -> dict[str, Any]:
        """Bağlılık seviyesi döndürür.

        Args:
            contact_id: Kişi ID.

        Returns:
            Bağlılık bilgisi.
        """
        score_data = self._scores.get(
            contact_id,
        )
        if not score_data:
            return {
                "contact_id": contact_id,
                "engagement": "unknown",
                "score": 0,
            }

        score = score_data["score"]
        engagement = (
            "highly_engaged"
            if score >= 80
            else "engaged" if score >= 60
            else "moderate" if score >= 40
            else "low" if score >= 20
            else "disengaged"
        )

        return {
            "contact_id": contact_id,
            "engagement": engagement,
            "score": score,
        }

    def apply_recency_weight(
        self,
        contact_id: str,
        days_since: float,
        decay_rate: float = 0.02,
    ) -> dict[str, Any]:
        """Güncellik ağırlığı uygular.

        Args:
            contact_id: Kişi ID.
            days_since: Geçen gün.
            decay_rate: Azalma oranı.

        Returns:
            Ağırlık bilgisi.
        """
        weight = round(
            max(
                1 - days_since * decay_rate,
                0.1,
            ), 3,
        )

        score_data = self._scores.get(
            contact_id, {},
        )
        original = score_data.get(
            "score", 50,
        )
        weighted = round(
            original * weight, 1,
        )

        return {
            "contact_id": contact_id,
            "original_score": original,
            "weight": weight,
            "weighted_score": weighted,
            "days_since": days_since,
        }

    def score_trust(
        self,
        contact_id: str,
        reliability: float = 0.5,
        consistency: float = 0.5,
        transparency: float = 0.5,
    ) -> dict[str, Any]:
        """Güven puanlar.

        Args:
            contact_id: Kişi ID.
            reliability: Güvenilirlik.
            consistency: Tutarlılık.
            transparency: Şeffaflık.

        Returns:
            Güven bilgisi.
        """
        trust = round(
            (reliability * 0.4
             + consistency * 0.35
             + transparency * 0.25)
            * 100, 1,
        )
        trust = min(trust, 100)

        level = (
            "high" if trust >= 75
            else "medium" if trust >= 50
            else "low"
        )

        return {
            "contact_id": contact_id,
            "trust_score": trust,
            "trust_level": level,
            "factors": {
                "reliability": reliability,
                "consistency": consistency,
                "transparency": transparency,
            },
        }

    def analyze_trend(
        self,
        contact_id: str,
    ) -> dict[str, Any]:
        """Trend analiz eder.

        Args:
            contact_id: Kişi ID.

        Returns:
            Trend bilgisi.
        """
        history = self._history.get(
            contact_id, [],
        )

        if len(history) < 2:
            return {
                "contact_id": contact_id,
                "trend": "insufficient_data",
                "data_points": len(history),
            }

        recent = history[-1]
        previous = history[-2]
        change = round(
            recent - previous, 1,
        )

        trend = (
            "improving"
            if change > 5
            else "declining"
            if change < -5
            else "stable"
        )

        self._stats[
            "trends_analyzed"
        ] += 1

        return {
            "contact_id": contact_id,
            "trend": trend,
            "change": change,
            "current_score": recent,
            "data_points": len(history),
        }

    def get_score(
        self, contact_id: str,
    ) -> dict[str, Any] | None:
        """Puan döndürür."""
        return self._scores.get(
            contact_id,
        )

    @property
    def scored_count(self) -> int:
        """Puanlanan kişi sayısı."""
        return self._stats[
            "scores_calculated"
        ]
