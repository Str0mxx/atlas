"""ATLAS Duygusal Hafiza Sistemi.

Hafizalara duygusal etiketler ekler, tercihleri ve kacinmalari yonetir,
ruh haline uyumlu hatirlama saglar. Plutchik duygu modeli kullanilir.
"""

import logging
from datetime import datetime, timezone

from app.models.memory_palace import (
    EmotionalAssociation,
    EmotionType,
    Preference,
    Sentiment,
)

logger = logging.getLogger(__name__)

# Pozitif duygular grubu
_POSITIVE_EMOTIONS: set[EmotionType] = {
    EmotionType.JOY,
    EmotionType.TRUST,
    EmotionType.ANTICIPATION,
    EmotionType.SURPRISE,
}

# Negatif duygular grubu
_NEGATIVE_EMOTIONS: set[EmotionType] = {
    EmotionType.SADNESS,
    EmotionType.ANGER,
    EmotionType.FEAR,
    EmotionType.DISGUST,
}


def _infer_sentiment(emotion: EmotionType) -> Sentiment:
    """Duygu tipinden otomatik duygu degerlendirmesi cikarir.

    Args:
        emotion: Duygu tipi.

    Returns:
        Cikarilmis duygu degerlendirmesi.
    """
    if emotion in _POSITIVE_EMOTIONS:
        return Sentiment.POSITIVE
    if emotion in _NEGATIVE_EMOTIONS:
        return Sentiment.NEGATIVE
    return Sentiment.NEUTRAL


class EmotionalMemory:
    """Duygusal hafiza sistemi.

    Hafizalara duygusal etiketler ekler, tercihleri ve kacinmalari yonetir,
    ruh haline uyumlu hatirlama (mood-congruent recall) saglar.

    Attributes:
        _associations: Hafiza ID bazli duygusal iliskiler.
        _preferences: Konu bazli tercihler.
        _aversions: Konu bazli kacinma gucleri.
        _current_mood: Mevcut ruh hali.
        _emotional_weight: Duygusal agirlik katsayisi (EMA alpha).
    """

    def __init__(self, emotional_weight: float = 0.3) -> None:
        """Duygusal hafiza sistemini baslatir.

        Args:
            emotional_weight: Exponential moving average icin alpha katsayisi.
        """
        self._associations: dict[str, list[EmotionalAssociation]] = {}
        self._preferences: dict[str, Preference] = {}
        self._aversions: dict[str, float] = {}
        self._current_mood: EmotionType | None = None
        self._emotional_weight = emotional_weight
        logger.info(
            "Duygusal hafiza baslatildi, agirlik=%.2f", emotional_weight
        )

    def tag_memory(
        self,
        memory_id: str,
        emotion: EmotionType,
        intensity: float = 0.5,
    ) -> EmotionalAssociation:
        """Hafizaya duygusal etiket ekler.

        Sentiment otomatik olarak duygu tipinden cikarilir:
        JOY/TRUST/ANTICIPATION/SURPRISE -> POSITIVE,
        SADNESS/ANGER/FEAR/DISGUST -> NEGATIVE.

        Args:
            memory_id: Etiketlenecek hafiza ID.
            emotion: Duygu tipi.
            intensity: Duygu yogunlugu (0.0-1.0).

        Returns:
            Olusturulan duygusal iliski.
        """
        intensity = max(0.0, min(1.0, intensity))
        sentiment = _infer_sentiment(emotion)

        association = EmotionalAssociation(
            memory_id=memory_id,
            emotion=emotion,
            intensity=intensity,
        )

        if memory_id not in self._associations:
            self._associations[memory_id] = []
        self._associations[memory_id].append(association)

        logger.debug(
            "Hafiza etiketlendi: %s -> %s (yogunluk=%.2f, duygu=%s)",
            memory_id,
            emotion.value,
            intensity,
            sentiment.value,
        )
        return association

    def get_emotions(self, memory_id: str) -> list[EmotionalAssociation]:
        """Hafizayla iliskili tum duygusal etiketleri dondurur.

        Args:
            memory_id: Sorgulanacak hafiza ID.

        Returns:
            Duygusal iliski listesi (bos liste yoksa).
        """
        return list(self._associations.get(memory_id, []))

    def update_preference(
        self,
        subject: str,
        sentiment: Sentiment,
        score_delta: float = 0.1,
    ) -> Preference:
        """Konu bazli tercihi gunceller.

        Mevcut tercih varsa exponential moving average ile gunceller:
        new_score = old_score * (1 - alpha) + score_delta * alpha
        Burada alpha = emotional_weight. Sonuc [-1.0, 1.0] araligina kesilir.
        Yoksa yeni tercih olusturur.

        Args:
            subject: Tercih konusu.
            sentiment: Duygu degerlendirmesi.
            score_delta: Puan degisimi.

        Returns:
            Guncellenmis veya olusturulmus tercih.
        """
        if subject in self._preferences:
            pref = self._preferences[subject]
            alpha = self._emotional_weight
            new_score = pref.score * (1.0 - alpha) + score_delta * alpha
            new_score = max(-1.0, min(1.0, new_score))

            # Pydantic model'i yeniden olustur (immutable olabilir)
            self._preferences[subject] = Preference(
                id=pref.id,
                subject=pref.subject,
                sentiment=sentiment,
                score=new_score,
                interaction_count=pref.interaction_count + 1,
                last_updated=datetime.now(timezone.utc),
            )
            logger.debug(
                "Tercih guncellendi: %s -> puan=%.3f, etkilesim=%d",
                subject,
                new_score,
                self._preferences[subject].interaction_count,
            )
        else:
            clamped_score = max(-1.0, min(1.0, score_delta))
            self._preferences[subject] = Preference(
                subject=subject,
                sentiment=sentiment,
                score=clamped_score,
                interaction_count=1,
                last_updated=datetime.now(timezone.utc),
            )
            logger.debug("Yeni tercih olusturuldu: %s -> %.3f", subject, clamped_score)

        return self._preferences[subject]

    def get_preference(self, subject: str) -> Preference | None:
        """Konu bazli tercihi dondurur.

        Args:
            subject: Tercih konusu.

        Returns:
            Tercih nesnesi veya None (yoksa).
        """
        return self._preferences.get(subject)

    def record_aversion(self, subject: str, intensity: float = 0.5) -> None:
        """Kacinma davranisi kaydeder.

        Mevcut kacinma gucune ekleme yapar:
        aversion = min(1.0, current + intensity * 0.5)

        Args:
            subject: Kacinma konusu.
            intensity: Kacinma yogunlugu (0.0-1.0).
        """
        intensity = max(0.0, min(1.0, intensity))
        current = self._aversions.get(subject, 0.0)
        new_aversion = min(1.0, current + intensity * 0.5)
        self._aversions[subject] = new_aversion
        logger.debug(
            "Kacinma kaydedildi: %s -> %.3f (onceki=%.3f)",
            subject,
            new_aversion,
            current,
        )

    def get_aversion(self, subject: str) -> float:
        """Konu bazli kacinma gucunu dondurur.

        Args:
            subject: Kacinma konusu.

        Returns:
            Kacinma gucu (0.0 yoksa).
        """
        return self._aversions.get(subject, 0.0)

    def set_mood(self, mood: EmotionType) -> None:
        """Mevcut ruh halini ayarlar.

        Args:
            mood: Yeni ruh hali.
        """
        old_mood = self._current_mood
        self._current_mood = mood
        logger.info(
            "Ruh hali degistirildi: %s -> %s",
            old_mood.value if old_mood else "None",
            mood.value,
        )

    def get_mood(self) -> EmotionType | None:
        """Mevcut ruh halini dondurur.

        Returns:
            Mevcut ruh hali veya None (ayarlanmamissa).
        """
        return self._current_mood

    def mood_congruent_recall(
        self, memories: list[dict],
    ) -> list[dict]:
        """Ruh haline uyumlu hatiralari filtreler ve siralar.

        Her dict 'id' anahtari icermelidir. Ruh hali ayarlanmamissa
        tum hatiralari dondurur. Aksi halde, duygusal etiketleri
        mevcut ruh hali ile eslesen hatiralari filtreler ve
        eslesen yogunluga gore azalan sirada siralar.

        Args:
            memories: Hafiza sozluklerinin listesi (her biri 'id' anahtari icermeli).

        Returns:
            Filtrelenmis ve siralanmis hafiza listesi.
        """
        if self._current_mood is None:
            return list(memories)

        mood = self._current_mood
        scored: list[tuple[dict, float]] = []

        for memory in memories:
            memory_id = memory.get("id", "")
            associations = self._associations.get(memory_id, [])

            # Mevcut ruh hali ile eslesen iliskileri bul
            max_intensity = 0.0
            matched = False
            for assoc in associations:
                if assoc.emotion == mood:
                    matched = True
                    if assoc.intensity > max_intensity:
                        max_intensity = assoc.intensity

            if matched:
                scored.append((memory, max_intensity))

        # Yogunluga gore azalan sirada sirala
        scored.sort(key=lambda x: x[1], reverse=True)
        result = [item[0] for item in scored]

        logger.debug(
            "Ruh haline uyumlu hatirlama: mood=%s, girdi=%d, cikti=%d",
            mood.value,
            len(memories),
            len(result),
        )
        return result

    def get_sentiment_summary(self) -> dict[str, int]:
        """Tum duygusal iliskilerin duygu dagilimini dondurur.

        Returns:
            Her duygu tipinin toplam sayisini iceren sozluk.
        """
        summary: dict[str, int] = {}

        for associations in self._associations.values():
            for assoc in associations:
                emotion_name = assoc.emotion.value
                summary[emotion_name] = summary.get(emotion_name, 0) + 1

        logger.debug("Duygu dagilimi: %s", summary)
        return summary
