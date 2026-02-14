"""ATLAS Geri Bildirim Isleyici modulu.

Kullanici geri bildirim analizi,
ortuk geri bildirim tespiti, duygu
cikarma, tercih cikarimi ve duzeltme
ogrenme.
"""

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.models.adaptive import FeedbackType

logger = logging.getLogger(__name__)


class FeedbackProcessor:
    """Geri bildirim isleyici.

    Acik ve ortuk geri bildirimleri
    isler, tercihleri cikarir.

    Attributes:
        _feedbacks: Geri bildirim deposu.
        _preferences: Cikarilan tercihler.
        _corrections: Duzeltme gecmisi.
    """

    def __init__(self) -> None:
        """Geri bildirim isleyiciyi baslatir."""
        self._feedbacks: list[dict[str, Any]] = []
        self._preferences: dict[str, dict[str, Any]] = {}
        self._corrections: list[dict[str, Any]] = []
        self._sentiment_counts: dict[str, int] = {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
        }

        logger.info("FeedbackProcessor baslatildi")

    def process_explicit(
        self,
        source: str,
        content: str,
        rating: float = 0.0,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Acik geri bildirimi isler.

        Args:
            source: Kaynak (kullanici).
            content: Icerik.
            rating: Puan (-1.0 ile 1.0).
            context: Baglam.

        Returns:
            Isleme sonucu.
        """
        sentiment = self._analyze_sentiment(content, rating)

        feedback = {
            "type": FeedbackType.EXPLICIT.value,
            "source": source,
            "content": content,
            "rating": max(-1.0, min(1.0, rating)),
            "sentiment": sentiment,
            "context": context or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._feedbacks.append(feedback)
        self._sentiment_counts[sentiment] += 1

        # Tercihleri guncelle
        if context:
            self._update_preferences(source, context, rating)

        return feedback

    def process_implicit(
        self,
        source: str,
        action: str,
        duration: float = 0.0,
        completed: bool = True,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ortuk geri bildirimi isler.

        Args:
            source: Kaynak.
            action: Aksiyon.
            duration: Sure (saniye).
            completed: Tamamlandi mi.
            context: Baglam.

        Returns:
            Isleme sonucu.
        """
        # Ortuk sinyal: uzun sure = zorluk, tamamlanmama = olumsuz
        inferred_rating = 0.0
        if completed:
            inferred_rating = 0.5
            if duration > 0 and duration < 5.0:
                inferred_rating = 0.8  # Hizli tamamlama = iyi
        else:
            inferred_rating = -0.5

        sentiment = self._analyze_sentiment("", inferred_rating)

        feedback = {
            "type": FeedbackType.IMPLICIT.value,
            "source": source,
            "action": action,
            "duration": duration,
            "completed": completed,
            "inferred_rating": inferred_rating,
            "sentiment": sentiment,
            "context": context or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._feedbacks.append(feedback)
        self._sentiment_counts[sentiment] += 1
        return feedback

    def process_correction(
        self,
        source: str,
        original_action: str,
        corrected_action: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Duzeltme isler.

        Args:
            source: Kaynak.
            original_action: Orijinal aksiyon.
            corrected_action: Duzeltilmis aksiyon.
            context: Baglam.

        Returns:
            Isleme sonucu.
        """
        correction = {
            "type": FeedbackType.CORRECTION.value,
            "source": source,
            "original": original_action,
            "corrected": corrected_action,
            "context": context or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._corrections.append(correction)
        self._feedbacks.append(correction)

        return correction

    def infer_preferences(
        self,
        source: str,
    ) -> dict[str, Any]:
        """Tercihleri cikarir.

        Args:
            source: Kaynak (kullanici).

        Returns:
            Tercih profili.
        """
        return self._preferences.get(source, {})

    def get_sentiment_summary(self) -> dict[str, Any]:
        """Duygu ozeti getirir.

        Returns:
            Duygu dagalimi.
        """
        total = sum(self._sentiment_counts.values())
        return {
            "total": total,
            "positive": self._sentiment_counts["positive"],
            "negative": self._sentiment_counts["negative"],
            "neutral": self._sentiment_counts["neutral"],
            "positivity_rate": (
                self._sentiment_counts["positive"] / total
                if total > 0 else 0.0
            ),
        }

    def get_corrections(
        self,
        source: str = "",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Duzeltmeleri getirir.

        Args:
            source: Kaynak filtresi.
            limit: Maks kayit.

        Returns:
            Duzeltme listesi.
        """
        corrections = self._corrections
        if source:
            corrections = [
                c for c in corrections
                if c.get("source") == source
            ]
        return corrections[-limit:]

    def get_feedback_by_source(
        self,
        source: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Kaynaga gore geri bildirimleri getirir.

        Args:
            source: Kaynak.
            limit: Maks kayit.

        Returns:
            Geri bildirim listesi.
        """
        filtered = [
            f for f in self._feedbacks
            if f.get("source") == source
        ]
        return filtered[-limit:]

    def _analyze_sentiment(
        self,
        content: str,
        rating: float,
    ) -> str:
        """Duygu analizi yapar.

        Args:
            content: Icerik.
            rating: Puan.

        Returns:
            Duygu etiketi.
        """
        # Basit kural tabanli
        positive_words = {
            "iyi", "guzel", "harika", "super",
            "basarili", "good", "great", "nice",
        }
        negative_words = {
            "kotu", "hatali", "yanlis", "basarisiz",
            "bad", "wrong", "error", "fail",
        }

        if content:
            words = set(content.lower().split())
            pos = len(words & positive_words)
            neg = len(words & negative_words)
            if pos > neg:
                return "positive"
            if neg > pos:
                return "negative"

        if rating > 0.2:
            return "positive"
        if rating < -0.2:
            return "negative"
        return "neutral"

    def _update_preferences(
        self,
        source: str,
        context: dict[str, Any],
        rating: float,
    ) -> None:
        """Tercihleri gunceller.

        Args:
            source: Kaynak.
            context: Baglam.
            rating: Puan.
        """
        if source not in self._preferences:
            self._preferences[source] = {
                "likes": [],
                "dislikes": [],
                "interaction_count": 0,
            }

        prefs = self._preferences[source]
        prefs["interaction_count"] += 1

        for key, value in context.items():
            entry = f"{key}={value}"
            if rating > 0.3:
                if entry not in prefs["likes"]:
                    prefs["likes"].append(entry)
            elif rating < -0.3:
                if entry not in prefs["dislikes"]:
                    prefs["dislikes"].append(entry)

    @property
    def feedback_count(self) -> int:
        """Geri bildirim sayisi."""
        return len(self._feedbacks)

    @property
    def correction_count(self) -> int:
        """Duzeltme sayisi."""
        return len(self._corrections)

    @property
    def preference_count(self) -> int:
        """Tercih profili sayisi."""
        return len(self._preferences)
