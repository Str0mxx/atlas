"""ATLAS Duygu Takipçisi modülü.

Duygu analizi, ruh hali takibi,
trend tespiti, negatif uyarı,
geçmiş görünüm.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PeopleSentimentTracker:
    """Duygu takipçisi.

    Kişi duygularını takip eder.

    Attributes:
        _sentiments: Duygu kayıtları.
        _alerts: Uyarı kayıtları.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._sentiments: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "sentiments_analyzed": 0,
            "negative_alerts": 0,
            "trends_detected": 0,
        }

        logger.info(
            "PeopleSentimentTracker "
            "baslatildi",
        )

    def analyze_sentiment(
        self,
        contact_id: str,
        text: str = "",
        score: float = 0.5,
        context: str = "",
    ) -> dict[str, Any]:
        """Duygu analiz eder.

        Args:
            contact_id: Kişi ID.
            text: Metin.
            score: Puan (0-1).
            context: Bağlam.

        Returns:
            Analiz bilgisi.
        """
        level = (
            "very_positive"
            if score >= 0.8
            else "positive"
            if score >= 0.6
            else "neutral"
            if score >= 0.4
            else "negative"
            if score >= 0.2
            else "very_negative"
        )

        entry = {
            "score": score,
            "level": level,
            "context": context,
            "timestamp": time.time(),
        }

        if (
            contact_id
            not in self._sentiments
        ):
            self._sentiments[
                contact_id
            ] = []
        self._sentiments[
            contact_id
        ].append(entry)

        self._stats[
            "sentiments_analyzed"
        ] += 1

        # Negatif uyarı
        alert = None
        if score < 0.3:
            alert = self._create_alert(
                contact_id, level, context,
            )

        return {
            "contact_id": contact_id,
            "score": score,
            "level": level,
            "alert": alert,
            "analyzed": True,
        }

    def track_mood(
        self,
        contact_id: str,
    ) -> dict[str, Any]:
        """Ruh hali takip eder.

        Args:
            contact_id: Kişi ID.

        Returns:
            Ruh hali bilgisi.
        """
        history = self._sentiments.get(
            contact_id, [],
        )

        if not history:
            return {
                "contact_id": contact_id,
                "mood": "unknown",
                "avg_score": 0,
                "data_points": 0,
            }

        scores = [
            s["score"] for s in history
        ]
        avg = round(
            sum(scores) / len(scores), 2,
        )
        recent = scores[-1]

        mood = (
            "positive"
            if avg >= 0.6
            else "neutral"
            if avg >= 0.4
            else "negative"
        )

        return {
            "contact_id": contact_id,
            "mood": mood,
            "avg_score": avg,
            "recent_score": recent,
            "data_points": len(history),
        }

    def detect_trend(
        self,
        contact_id: str,
        window: int = 5,
    ) -> dict[str, Any]:
        """Trend tespit eder.

        Args:
            contact_id: Kişi ID.
            window: Pencere boyutu.

        Returns:
            Trend bilgisi.
        """
        history = self._sentiments.get(
            contact_id, [],
        )

        if len(history) < 2:
            return {
                "contact_id": contact_id,
                "trend": "insufficient_data",
                "data_points": len(history),
            }

        recent = history[-window:]
        scores = [
            s["score"] for s in recent
        ]

        first_half = scores[
            :len(scores) // 2
        ]
        second_half = scores[
            len(scores) // 2:
        ]

        avg_first = sum(first_half) / max(
            len(first_half), 1,
        )
        avg_second = sum(
            second_half,
        ) / max(len(second_half), 1)

        diff = round(
            avg_second - avg_first, 3,
        )

        trend = (
            "improving"
            if diff > 0.1
            else "declining"
            if diff < -0.1
            else "stable"
        )

        self._stats[
            "trends_detected"
        ] += 1

        return {
            "contact_id": contact_id,
            "trend": trend,
            "change": diff,
            "data_points": len(recent),
        }

    def alert_on_negative(
        self,
        contact_id: str,
        threshold: float = 0.3,
    ) -> dict[str, Any]:
        """Negatif uyarı kontrol eder.

        Args:
            contact_id: Kişi ID.
            threshold: Eşik.

        Returns:
            Uyarı bilgisi.
        """
        history = self._sentiments.get(
            contact_id, [],
        )

        if not history:
            return {
                "contact_id": contact_id,
                "alert": False,
            }

        recent = history[-1]
        should_alert = (
            recent["score"] < threshold
        )

        if should_alert:
            self._create_alert(
                contact_id,
                recent["level"],
                "threshold_breach",
            )

        return {
            "contact_id": contact_id,
            "alert": should_alert,
            "current_score": recent[
                "score"
            ],
            "threshold": threshold,
        }

    def get_historical(
        self,
        contact_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Geçmiş görünüm döndürür.

        Args:
            contact_id: Kişi ID.
            limit: Limit.

        Returns:
            Geçmiş listesi.
        """
        return self._sentiments.get(
            contact_id, [],
        )[-limit:]

    def _create_alert(
        self,
        contact_id: str,
        level: str,
        context: str,
    ) -> dict[str, Any]:
        """Uyarı oluşturur."""
        alert = {
            "contact_id": contact_id,
            "level": level,
            "context": context,
            "timestamp": time.time(),
        }
        self._alerts.append(alert)
        self._stats[
            "negative_alerts"
        ] += 1
        return alert

    @property
    def analyzed_count(self) -> int:
        """Analiz sayısı."""
        return self._stats[
            "sentiments_analyzed"
        ]

    @property
    def alert_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats[
            "negative_alerts"
        ]
