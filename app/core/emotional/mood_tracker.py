"""ATLAS Ruh Hali Takip modulu.

Kullanici ruh hali gecmisi, zaman icinde kaliplar,
tetikleyici tespiti, ruh hali tahmini ve proaktif destek.
"""

import logging
from typing import Any

from app.models.emotional import (
    Emotion,
    MoodEntry,
    MoodLevel,
    SentimentResult,
)

logger = logging.getLogger(__name__)

# Mood level -> sayisal deger
_MOOD_VALUES: dict[MoodLevel, float] = {
    MoodLevel.VERY_LOW: 1.0,
    MoodLevel.LOW: 2.0,
    MoodLevel.NEUTRAL: 3.0,
    MoodLevel.HIGH: 4.0,
    MoodLevel.VERY_HIGH: 5.0,
}

_VALUE_TO_MOOD: list[tuple[float, MoodLevel]] = [
    (1.5, MoodLevel.VERY_LOW),
    (2.5, MoodLevel.LOW),
    (3.5, MoodLevel.NEUTRAL),
    (4.5, MoodLevel.HIGH),
    (5.1, MoodLevel.VERY_HIGH),
]


class MoodTracker:
    """Ruh hali takip sistemi.

    Kullanici ruh hali gecmisini kaydeder, kaliplari
    analiz eder ve proaktif destek oneriri.

    Attributes:
        _entries: Kullanici bazli ruh hali kayitlari.
        _triggers: Bilinen tetikleyiciler.
    """

    def __init__(self, max_history: int = 100) -> None:
        """Ruh hali takipcisini baslatir.

        Args:
            max_history: Kullanici basina maks gecmis.
        """
        self._entries: dict[str, list[MoodEntry]] = {}
        self._triggers: dict[str, list[str]] = {}
        self._max_history = max_history

        logger.info("MoodTracker baslatildi (max_history=%d)", max_history)

    def record(self, user_id: str, mood: MoodLevel, emotion: Emotion, trigger: str = "", context: str = "") -> MoodEntry:
        """Ruh hali kaydeder.

        Args:
            user_id: Kullanici ID.
            mood: Ruh hali seviyesi.
            emotion: Duygu sinifi.
            trigger: Tetikleyici.
            context: Baglam.

        Returns:
            MoodEntry nesnesi.
        """
        entry = MoodEntry(
            user_id=user_id,
            mood=mood,
            emotion=emotion,
            trigger=trigger,
            context=context,
        )

        entries = self._entries.setdefault(user_id, [])
        entries.append(entry)

        # Gecmis limiti
        if len(entries) > self._max_history:
            self._entries[user_id] = entries[-self._max_history:]

        # Tetikleyici kaydet
        if trigger:
            triggers = self._triggers.setdefault(user_id, [])
            triggers.append(trigger)

        return entry

    def record_from_sentiment(self, user_id: str, result: SentimentResult, context: str = "") -> MoodEntry:
        """Sentiment sonucundan ruh hali kaydeder.

        Args:
            user_id: Kullanici ID.
            result: Duygu analiz sonucu.
            context: Baglam.

        Returns:
            MoodEntry nesnesi.
        """
        mood = self._sentiment_to_mood(result)
        trigger = ", ".join(result.keywords) if result.keywords else ""
        return self.record(user_id, mood, result.emotion, trigger, context)

    def get_history(self, user_id: str, limit: int = 20) -> list[MoodEntry]:
        """Ruh hali gecmisini getirir.

        Args:
            user_id: Kullanici ID.
            limit: Maks kayit sayisi.

        Returns:
            MoodEntry listesi.
        """
        entries = self._entries.get(user_id, [])
        return entries[-limit:]

    def get_current_mood(self, user_id: str) -> MoodLevel:
        """Mevcut ruh halini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            MoodLevel degeri.
        """
        entries = self._entries.get(user_id, [])
        if not entries:
            return MoodLevel.NEUTRAL
        return entries[-1].mood

    def analyze_patterns(self, user_id: str) -> dict[str, Any]:
        """Ruh hali kaliplarini analiz eder.

        Args:
            user_id: Kullanici ID.

        Returns:
            Kalip analizi.
        """
        entries = self._entries.get(user_id, [])
        if not entries:
            return {"avg_mood": 3.0, "trend": "stable", "dominant_emotion": Emotion.TRUST.value}

        values = [_MOOD_VALUES[e.mood] for e in entries]
        avg = sum(values) / len(values)

        # Trend
        if len(values) >= 4:
            mid = len(values) // 2
            first = sum(values[:mid]) / mid
            second = sum(values[mid:]) / (len(values) - mid)
            if second - first > 0.3:
                trend = "improving"
            elif first - second > 0.3:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Baskin duygu
        emotion_counts: dict[str, int] = {}
        for e in entries:
            emotion_counts[e.emotion.value] = emotion_counts.get(e.emotion.value, 0) + 1
        dominant = max(emotion_counts, key=emotion_counts.get) if emotion_counts else Emotion.TRUST.value  # type: ignore[arg-type]

        return {
            "avg_mood": round(avg, 2),
            "trend": trend,
            "dominant_emotion": dominant,
            "total_entries": len(entries),
        }

    def identify_triggers(self, user_id: str, min_count: int = 2) -> list[dict[str, Any]]:
        """Tetikleyicileri tespit eder.

        Args:
            user_id: Kullanici ID.
            min_count: Minimum tekrar.

        Returns:
            Tetikleyici listesi.
        """
        triggers = self._triggers.get(user_id, [])
        counts: dict[str, int] = {}
        for t in triggers:
            if t:
                counts[t] = counts.get(t, 0) + 1

        return [
            {"trigger": t, "count": c}
            for t, c in sorted(counts.items(), key=lambda x: x[1], reverse=True)
            if c >= min_count
        ]

    def predict_mood(self, user_id: str) -> MoodLevel:
        """Ruh hali tahmini yapar.

        Args:
            user_id: Kullanici ID.

        Returns:
            Tahmini MoodLevel.
        """
        entries = self._entries.get(user_id, [])
        if len(entries) < 3:
            return MoodLevel.NEUTRAL

        # Son 5 kayitin agirliklı ortalamasi
        recent = entries[-5:]
        weights = list(range(1, len(recent) + 1))
        total_weight = sum(weights)
        weighted_sum = sum(_MOOD_VALUES[e.mood] * w for e, w in zip(recent, weights))
        predicted = weighted_sum / total_weight

        for threshold, level in _VALUE_TO_MOOD:
            if predicted < threshold:
                return level

        return MoodLevel.VERY_HIGH

    def needs_proactive_support(self, user_id: str) -> bool:
        """Proaktif destek gerekli mi kontrol eder.

        Args:
            user_id: Kullanici ID.

        Returns:
            Destek gerekli mi.
        """
        entries = self._entries.get(user_id, [])
        if len(entries) < 3:
            return False

        # Son 3 kayit kotu mu?
        recent = entries[-3:]
        low_count = sum(
            1 for e in recent
            if e.mood in (MoodLevel.LOW, MoodLevel.VERY_LOW)
        )
        return low_count >= 2

    def get_mood_distribution(self, user_id: str) -> dict[str, int]:
        """Ruh hali dagilimini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Dagilim sozlugu.
        """
        entries = self._entries.get(user_id, [])
        dist: dict[str, int] = {}
        for e in entries:
            dist[e.mood.value] = dist.get(e.mood.value, 0) + 1
        return dist

    def _sentiment_to_mood(self, result: SentimentResult) -> MoodLevel:
        """Sentiment sonucunu mood'a cevirir."""
        if result.sentiment.value == "positive":
            return MoodLevel.VERY_HIGH if result.intensity > 0.7 else MoodLevel.HIGH
        if result.sentiment.value == "negative":
            return MoodLevel.VERY_LOW if result.intensity > 0.7 else MoodLevel.LOW
        return MoodLevel.NEUTRAL

    @property
    def tracked_users(self) -> int:
        """Takip edilen kullanici sayisi."""
        return len(self._entries)

    @property
    def total_entries(self) -> int:
        """Toplam kayit sayisi."""
        return sum(len(e) for e in self._entries.values())
