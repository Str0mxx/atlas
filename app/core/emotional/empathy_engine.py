"""ATLAS Empati Motoru modulu.

Kullanici duygusal durum takibi, uygun yanit tonu,
destekleyici dil uretimi, hayal kirikligi tespiti
ve kutlama tanima.
"""

import logging

from app.models.emotional import (
    CommunicationTone,
    Emotion,
    MoodLevel,
    Sentiment,
    SentimentResult,
    UserEmotionalState,
)

logger = logging.getLogger(__name__)

# Sentiment -> ton eslesmesi
_TONE_MAP: dict[Sentiment, CommunicationTone] = {
    Sentiment.POSITIVE: CommunicationTone.ENTHUSIASTIC,
    Sentiment.NEGATIVE: CommunicationTone.EMPATHETIC,
    Sentiment.NEUTRAL: CommunicationTone.PROFESSIONAL,
    Sentiment.MIXED: CommunicationTone.SUPPORTIVE,
}

# Destek mesajlari
_SUPPORT_MESSAGES: dict[Emotion, list[str]] = {
    Emotion.SAD: [
        "Anliyorum, bu zor bir durum.",
        "Yanindayim, birlikte cozum bulalim.",
        "Uzulme, elimden geleni yapacagim.",
    ],
    Emotion.ANGRY: [
        "Haklisikayetini anliyorum.",
        "Bu durumun sinir bozucu oldugunu biliyorum.",
        "Hemen cozum uretmeye calisayim.",
    ],
    Emotion.FEAR: [
        "Endiselenme, kontrol altinda.",
        "Birlikte ustesinden geliriz.",
        "Seni bilgilendirmeye devam edecegim.",
    ],
    Emotion.HAPPY: [
        "Ne guzel haber!",
        "Basarini kutluyorum!",
        "Bu harika bir gelisme!",
    ],
    Emotion.SURPRISE: [
        "Evet, bu beklenmedik bir gelisme!",
        "Ilginc, hemen inceleyelim.",
    ],
}


class EmpathyEngine:
    """Empati motoru.

    Kullanicinin duygusal durumunu takip eder ve
    uygun tonda yanit uretir.

    Attributes:
        _states: Kullanici duygusal durumlari.
        _empathy_level: Empati seviyesi.
    """

    def __init__(self, empathy_level: str = "medium") -> None:
        """Empati motorunu baslatir.

        Args:
            empathy_level: Empati seviyesi (low/medium/high).
        """
        self._states: dict[str, UserEmotionalState] = {}
        self._empathy_level = empathy_level

        logger.info("EmpathyEngine baslatildi (level=%s)", empathy_level)

    def update_state(self, user_id: str, sentiment: SentimentResult) -> UserEmotionalState:
        """Kullanici duygusal durumunu gunceller.

        Args:
            user_id: Kullanici ID.
            sentiment: Duygu analiz sonucu.

        Returns:
            Guncellenenmis UserEmotionalState.
        """
        state = self._get_or_create(user_id)
        state.last_sentiment = sentiment.sentiment
        state.current_emotion = sentiment.emotion
        state.interaction_count += 1

        # Frustration guncelle
        if sentiment.sentiment == Sentiment.NEGATIVE:
            state.frustration_level = min(state.frustration_level + 0.2, 1.0)
            state.satisfaction_level = max(state.satisfaction_level - 0.1, 0.0)
        elif sentiment.sentiment == Sentiment.POSITIVE:
            state.frustration_level = max(state.frustration_level - 0.15, 0.0)
            state.satisfaction_level = min(state.satisfaction_level + 0.15, 1.0)
        else:
            # Zamanla sakinlesme
            state.frustration_level = max(state.frustration_level - 0.05, 0.0)

        # Mood guncelle
        state.current_mood = self._calculate_mood(state)

        return state

    def get_appropriate_tone(self, user_id: str) -> CommunicationTone:
        """Uygun yanit tonunu belirler.

        Args:
            user_id: Kullanici ID.

        Returns:
            CommunicationTone degeri.
        """
        state = self._states.get(user_id)
        if not state:
            return CommunicationTone.PROFESSIONAL

        # Yuksek frustration -> empathetic
        if state.frustration_level > 0.7:
            return CommunicationTone.EMPATHETIC
        if state.frustration_level > 0.4:
            return CommunicationTone.SUPPORTIVE

        return _TONE_MAP.get(state.last_sentiment, CommunicationTone.PROFESSIONAL)

    def generate_supportive_response(self, user_id: str, context: str = "") -> str:
        """Destekleyici yanit uretir.

        Args:
            user_id: Kullanici ID.
            context: Baglam.

        Returns:
            Destekleyici mesaj.
        """
        state = self._states.get(user_id)
        if not state:
            return "Nasil yardimci olabilirim?"

        emotion = state.current_emotion
        messages = _SUPPORT_MESSAGES.get(emotion, ["Nasil yardimci olabilirim?"])

        # Empati seviyesine gore mesaj sec
        idx = min(len(messages) - 1, {"low": 0, "medium": 0, "high": len(messages) - 1}.get(self._empathy_level, 0))
        message = messages[idx]

        # Yuksek empati seviyesinde baglam ekle
        if self._empathy_level == "high" and context:
            message = f"{message} ({context} hakkinda)"

        return message

    def detect_frustration(self, user_id: str) -> bool:
        """Hayal kiriikligi tespit eder.

        Args:
            user_id: Kullanici ID.

        Returns:
            Frustrasyon var mi.
        """
        state = self._states.get(user_id)
        if not state:
            return False
        return state.frustration_level > 0.5

    def detect_celebration(self, sentiment: SentimentResult) -> bool:
        """Kutlama durumu tespit eder.

        Args:
            sentiment: Duygu analiz sonucu.

        Returns:
            Kutlama durumu var mi.
        """
        return (
            sentiment.sentiment == Sentiment.POSITIVE
            and sentiment.emotion in (Emotion.HAPPY, Emotion.SURPRISE)
            and sentiment.intensity > 0.6
        )

    def get_state(self, user_id: str) -> UserEmotionalState | None:
        """Kullanici durumunu getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            UserEmotionalState veya None.
        """
        return self._states.get(user_id)

    def _get_or_create(self, user_id: str) -> UserEmotionalState:
        """Durumu getirir veya olusturur."""
        if user_id not in self._states:
            self._states[user_id] = UserEmotionalState(user_id=user_id)
        return self._states[user_id]

    def _calculate_mood(self, state: UserEmotionalState) -> MoodLevel:
        """Ruh hali hesaplar."""
        score = state.satisfaction_level - state.frustration_level

        if score > 0.4:
            return MoodLevel.VERY_HIGH
        if score > 0.15:
            return MoodLevel.HIGH
        if score > -0.15:
            return MoodLevel.NEUTRAL
        if score > -0.4:
            return MoodLevel.LOW
        return MoodLevel.VERY_LOW

    @property
    def tracked_users(self) -> int:
        """Takip edilen kullanici sayisi."""
        return len(self._states)

    @property
    def empathy_level(self) -> str:
        """Empati seviyesi."""
        return self._empathy_level
