"""ATLAS Duygusal Hafiza Yonetimi modulu.

Duygusal etkilesimleri hatirlama, iliski kalitesi takibi,
duygu gecmisi, onemli olaylar ve kullanici tercih evrimi.
"""

import logging
from typing import Any

from app.models.emotional import (
    EmotionalInteraction,
    Emotion,
    RelationshipQuality,
    Sentiment,
)

logger = logging.getLogger(__name__)

# Sentiment -> iliski etkisi
_SENTIMENT_IMPACT: dict[Sentiment, float] = {
    Sentiment.POSITIVE: 0.1,
    Sentiment.NEGATIVE: -0.15,
    Sentiment.NEUTRAL: 0.0,
    Sentiment.MIXED: -0.05,
}


class EmotionalMemoryManager:
    """Duygusal hafiza yonetim sistemi.

    Duygusal etkilesimleri kaydeder, iliski kalitesini
    takip eder ve onemli olaylari hatirlar.

    Attributes:
        _interactions: Etkilesim gecmisi.
        _relationship_scores: Iliski puanlari.
        _important_events: Onemli olaylar.
        _preferences: Kullanici tercihleri.
    """

    def __init__(self, max_memory: int = 500) -> None:
        """Duygusal hafizayi baslatir.

        Args:
            max_memory: Kullanici basina maks kayit.
        """
        self._interactions: dict[str, list[EmotionalInteraction]] = {}
        self._relationship_scores: dict[str, float] = {}
        self._important_events: dict[str, list[EmotionalInteraction]] = {}
        self._preferences: dict[str, dict[str, Any]] = {}
        self._max_memory = max_memory

        logger.info("EmotionalMemoryManager baslatildi (max=%d)", max_memory)

    def record_interaction(
        self,
        user_id: str,
        sentiment: Sentiment,
        emotion: Emotion,
        event_type: str = "",
        summary: str = "",
        importance: float = 0.5,
    ) -> EmotionalInteraction:
        """Duygusal etkilesimi kaydeder.

        Args:
            user_id: Kullanici ID.
            sentiment: Duygu polaritesi.
            emotion: Duygu sinifi.
            event_type: Olay tipi.
            summary: Ozet.
            importance: Onem derecesi.

        Returns:
            EmotionalInteraction nesnesi.
        """
        quality = self._get_relationship_quality(user_id)

        interaction = EmotionalInteraction(
            user_id=user_id,
            sentiment=sentiment,
            emotion=emotion,
            relationship_quality=quality,
            event_type=event_type,
            summary=summary,
            importance=importance,
        )

        # Kaydet
        history = self._interactions.setdefault(user_id, [])
        history.append(interaction)
        if len(history) > self._max_memory:
            self._interactions[user_id] = history[-self._max_memory:]

        # Iliski puani guncelle
        self._update_relationship(user_id, sentiment)

        # Onemli olay mi?
        if importance > 0.7:
            events = self._important_events.setdefault(user_id, [])
            events.append(interaction)

        return interaction

    def get_history(self, user_id: str, limit: int = 20) -> list[EmotionalInteraction]:
        """Etkilesim gecmisini getirir.

        Args:
            user_id: Kullanici ID.
            limit: Maks kayit.

        Returns:
            EmotionalInteraction listesi.
        """
        history = self._interactions.get(user_id, [])
        return history[-limit:]

    def get_relationship_quality(self, user_id: str) -> RelationshipQuality:
        """Iliski kalitesini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            RelationshipQuality degeri.
        """
        return self._get_relationship_quality(user_id)

    def get_sentiment_history(self, user_id: str) -> list[Sentiment]:
        """Duygu gecmisini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Sentiment listesi.
        """
        history = self._interactions.get(user_id, [])
        return [i.sentiment for i in history]

    def get_important_events(self, user_id: str) -> list[EmotionalInteraction]:
        """Onemli olaylari getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            EmotionalInteraction listesi.
        """
        return list(self._important_events.get(user_id, []))

    def update_preference(self, user_id: str, key: str, value: Any) -> None:
        """Kullanici tercihini gunceller.

        Args:
            user_id: Kullanici ID.
            key: Tercih anahtari.
            value: Tercih degeri.
        """
        prefs = self._preferences.setdefault(user_id, {})
        prefs[key] = value

    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """Kullanici tercihini getirir.

        Args:
            user_id: Kullanici ID.
            key: Tercih anahtari.
            default: Varsayilan deger.

        Returns:
            Tercih degeri.
        """
        prefs = self._preferences.get(user_id, {})
        return prefs.get(key, default)

    def get_emotion_distribution(self, user_id: str) -> dict[str, int]:
        """Duygu dagilimini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Duygu -> sayi sozlugu.
        """
        history = self._interactions.get(user_id, [])
        dist: dict[str, int] = {}
        for i in history:
            dist[i.emotion.value] = dist.get(i.emotion.value, 0) + 1
        return dist

    def get_user_summary(self, user_id: str) -> dict[str, Any]:
        """Kullanici ozeti getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Ozet sozlugu.
        """
        history = self._interactions.get(user_id, [])
        quality = self._get_relationship_quality(user_id)

        pos = sum(1 for i in history if i.sentiment == Sentiment.POSITIVE)
        neg = sum(1 for i in history if i.sentiment == Sentiment.NEGATIVE)

        return {
            "user_id": user_id,
            "total_interactions": len(history),
            "positive_count": pos,
            "negative_count": neg,
            "relationship_quality": quality.value,
            "important_events": len(self._important_events.get(user_id, [])),
            "preferences": dict(self._preferences.get(user_id, {})),
        }

    def _update_relationship(self, user_id: str, sentiment: Sentiment) -> None:
        """Iliski puanini gunceller."""
        current = self._relationship_scores.get(user_id, 0.5)
        impact = _SENTIMENT_IMPACT.get(sentiment, 0.0)
        new_score = max(0.0, min(1.0, current + impact))
        self._relationship_scores[user_id] = new_score

    def _get_relationship_quality(self, user_id: str) -> RelationshipQuality:
        """Iliski kalitesini hesaplar."""
        score = self._relationship_scores.get(user_id, 0.5)

        if score > 0.8:
            return RelationshipQuality.EXCELLENT
        if score > 0.6:
            return RelationshipQuality.GOOD
        if score > 0.4:
            return RelationshipQuality.NEUTRAL
        if score > 0.2:
            return RelationshipQuality.STRAINED
        return RelationshipQuality.POOR

    @property
    def tracked_users(self) -> int:
        """Takip edilen kullanici sayisi."""
        return len(self._interactions)

    @property
    def total_interactions(self) -> int:
        """Toplam etkilesim sayisi."""
        return sum(len(h) for h in self._interactions.values())
