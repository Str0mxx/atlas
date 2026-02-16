"""ATLAS Kullanıcı Memnuniyeti Takipçisi modülü.

Memnuniyet puanlama, NPS takibi,
duygu analizi, geri bildirim toplama,
trend tespiti.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class UserSatisfactionTracker:
    """Kullanıcı memnuniyeti takipçisi.

    Kullanıcı memnuniyetini ölçer ve izler.

    Attributes:
        _feedbacks: Geri bildirim kayıtları.
        _nps_scores: NPS puanları.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._feedbacks: list[
            dict[str, Any]
        ] = []
        self._nps_scores: list[int] = []
        self._sentiments: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "feedbacks_collected": 0,
            "nps_responses": 0,
        }

        logger.info(
            "UserSatisfactionTracker "
            "baslatildi",
        )

    def score_satisfaction(
        self,
        user_id: str,
        score: float,
        category: str = "general",
        comment: str = "",
    ) -> dict[str, Any]:
        """Memnuniyet puanlar.

        Args:
            user_id: Kullanıcı ID.
            score: Puan (0-100).
            category: Kategori.
            comment: Yorum.

        Returns:
            Puanlama bilgisi.
        """
        self._counter += 1
        fid = f"sat_{self._counter}"

        level = (
            "delighted" if score >= 90
            else "satisfied" if score >= 70
            else "neutral" if score >= 50
            else "dissatisfied"
            if score >= 30
            else "frustrated"
        )

        entry = {
            "feedback_id": fid,
            "user_id": user_id,
            "score": score,
            "level": level,
            "category": category,
            "comment": comment,
            "timestamp": time.time(),
        }
        self._feedbacks.append(entry)
        self._stats[
            "feedbacks_collected"
        ] += 1

        return {
            "feedback_id": fid,
            "score": score,
            "level": level,
            "recorded": True,
        }

    def track_nps(
        self,
        user_id: str,
        score: int,
    ) -> dict[str, Any]:
        """NPS puanı takip eder.

        Args:
            user_id: Kullanıcı ID.
            score: NPS puanı (0-10).

        Returns:
            NPS bilgisi.
        """
        score = max(0, min(10, score))
        self._nps_scores.append(score)
        self._stats["nps_responses"] += 1

        category = (
            "promoter" if score >= 9
            else "passive"
            if score >= 7
            else "detractor"
        )

        # NPS hesapla
        if self._nps_scores:
            promoters = sum(
                1 for s in self._nps_scores
                if s >= 9
            )
            detractors = sum(
                1 for s in self._nps_scores
                if s <= 6
            )
            total = len(self._nps_scores)
            nps = round(
                (promoters - detractors)
                / total * 100,
                1,
            )
        else:
            nps = 0.0

        return {
            "user_id": user_id,
            "score": score,
            "category": category,
            "current_nps": nps,
            "tracked": True,
        }

    def analyze_sentiment(
        self,
        text: str,
        source: str = "feedback",
    ) -> dict[str, Any]:
        """Duygu analizi yapar.

        Args:
            text: Metin.
            source: Kaynak.

        Returns:
            Duygu bilgisi.
        """
        positive_words = {
            "great", "good", "excellent",
            "love", "amazing", "awesome",
            "perfect", "happy", "fast",
            "helpful",
        }
        negative_words = {
            "bad", "slow", "terrible",
            "hate", "awful", "poor",
            "broken", "worst", "bug",
            "crash",
        }

        words = text.lower().split()
        pos = sum(
            1 for w in words
            if w in positive_words
        )
        neg = sum(
            1 for w in words
            if w in negative_words
        )
        total = pos + neg

        if total == 0:
            sentiment = "neutral"
            confidence = 0.5
        elif pos > neg:
            sentiment = "positive"
            confidence = round(
                pos / total, 2,
            )
        elif neg > pos:
            sentiment = "negative"
            confidence = round(
                neg / total, 2,
            )
        else:
            sentiment = "mixed"
            confidence = 0.5

        entry = {
            "text": text[:100],
            "sentiment": sentiment,
            "source": source,
            "timestamp": time.time(),
        }
        self._sentiments.append(entry)

        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "positive_count": pos,
            "negative_count": neg,
            "analyzed": True,
        }

    def collect_feedback(
        self,
        user_id: str,
        feedback_type: str = "rating",
        value: Any = None,
        context: str = "",
    ) -> dict[str, Any]:
        """Geri bildirim toplar.

        Args:
            user_id: Kullanıcı ID.
            feedback_type: Geri bildirim tipi.
            value: Değer.
            context: Bağlam.

        Returns:
            Toplama bilgisi.
        """
        self._counter += 1
        fid = f"fb_{self._counter}"

        entry = {
            "feedback_id": fid,
            "user_id": user_id,
            "type": feedback_type,
            "value": value,
            "context": context,
            "timestamp": time.time(),
        }
        self._feedbacks.append(entry)
        self._stats[
            "feedbacks_collected"
        ] += 1

        return {
            "feedback_id": fid,
            "type": feedback_type,
            "collected": True,
        }

    def detect_trend(
        self,
        category: str = "general",
        window: int = 10,
    ) -> dict[str, Any]:
        """Trend tespit eder.

        Args:
            category: Kategori.
            window: Pencere boyutu.

        Returns:
            Trend bilgisi.
        """
        scored = [
            f for f in self._feedbacks
            if f.get("score") is not None
            and f.get("category") == category
        ]

        if len(scored) < 3:
            return {
                "category": category,
                "detected": False,
                "reason": "Insufficient data",
            }

        recent = scored[-window:]
        scores = [
            f["score"] for f in recent
        ]
        avg = round(
            sum(scores) / len(scores), 1,
        )

        half = len(scores) // 2
        first_half = scores[:half] or [0]
        second_half = scores[half:] or [0]
        first_avg = sum(first_half) / len(
            first_half,
        )
        second_avg = sum(second_half) / len(
            second_half,
        )

        if second_avg > first_avg * 1.1:
            trend = "improving"
        elif second_avg < first_avg * 0.9:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "category": category,
            "avg_score": avg,
            "trend": trend,
            "data_points": len(scores),
            "detected": True,
        }

    @property
    def feedback_count(self) -> int:
        """Geri bildirim sayısı."""
        return self._stats[
            "feedbacks_collected"
        ]

    @property
    def nps_count(self) -> int:
        """NPS sayısı."""
        return self._stats[
            "nps_responses"
        ]
