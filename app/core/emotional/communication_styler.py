"""ATLAS Iletisim Stili modulu.

Ruh haline gore ton adaptasyonu, resmi/gunluk tespit,
mizah uygunlugu, aciliyet tanima ve kulturel duyarlilik.
"""

import logging
import re
from typing import Any

from app.models.emotional import (
    CommunicationTone,
    FormalityLevel,
    MoodLevel,
    StyleProfile,
    UserEmotionalState,
)

logger = logging.getLogger(__name__)

# Resmi kelimeler
_FORMAL_WORDS: set[str] = {
    "sayin", "rica", "arz", "bilgilerinize", "husus", "talep",
    "please", "kindly", "regarding", "sincerely", "respectfully",
    "mevzubahis", "tevcih", "muhatap", "ilgi", "merci",
}

# Gunluk kelimeler
_CASUAL_WORDS: set[str] = {
    "yav", "lan", "abi", "kanka", "hadi", "bak", "ya",
    "hey", "dude", "cool", "nah", "gonna", "wanna", "lol",
    "moruk", "hocam", "reis", "agam",
}

# Aciliyet kelimeleri
_URGENCY_WORDS: set[str] = {
    "acil", "hemen", "simdi", "derhal", "kritik", "urgent",
    "asap", "immediately", "emergency", "critical", "now",
    "bekleyemez", "coktu", "down", "patliyor",
}

# Mood -> ton eslesmesi
_MOOD_TONE_MAP: dict[MoodLevel, CommunicationTone] = {
    MoodLevel.VERY_LOW: CommunicationTone.EMPATHETIC,
    MoodLevel.LOW: CommunicationTone.SUPPORTIVE,
    MoodLevel.NEUTRAL: CommunicationTone.PROFESSIONAL,
    MoodLevel.HIGH: CommunicationTone.CASUAL,
    MoodLevel.VERY_HIGH: CommunicationTone.ENTHUSIASTIC,
}


class CommunicationStyler:
    """Iletisim stili sistemi.

    Kullanicinin ruh haline ve tercihlerine gore
    iletisim tonunu ve stilini adapte eder.

    Attributes:
        _profiles: Kullanici stil profilleri.
        _humor_enabled: Mizah aktif mi.
    """

    def __init__(self, humor_enabled: bool = True, default_formality: str = "neutral") -> None:
        """Iletisim stilcisini baslatir.

        Args:
            humor_enabled: Mizah aktif mi.
            default_formality: Varsayilan resmiyet.
        """
        self._profiles: dict[str, StyleProfile] = {}
        self._humor_enabled = humor_enabled
        self._default_formality = default_formality

        logger.info("CommunicationStyler baslatildi (humor=%s)", humor_enabled)

    def adapt_tone(self, user_id: str, mood: MoodLevel) -> CommunicationTone:
        """Ruh haline gore ton adapte eder.

        Args:
            user_id: Kullanici ID.
            mood: Mevcut ruh hali.

        Returns:
            CommunicationTone degeri.
        """
        profile = self._profiles.get(user_id)
        if profile:
            # Profil tercihi ile mood'u dengele
            if mood in (MoodLevel.VERY_LOW, MoodLevel.LOW):
                return CommunicationTone.EMPATHETIC
            return profile.preferred_tone

        return _MOOD_TONE_MAP.get(mood, CommunicationTone.PROFESSIONAL)

    def detect_formality(self, text: str) -> FormalityLevel:
        """Resmiyet seviyesini tespit eder.

        Args:
            text: Metin.

        Returns:
            FormalityLevel degeri.
        """
        lower = text.lower()
        words = set(re.findall(r'\w+', lower))

        formal_count = len(words & _FORMAL_WORDS)
        casual_count = len(words & _CASUAL_WORDS)

        if formal_count > casual_count + 1:
            return FormalityLevel.VERY_FORMAL
        if formal_count > casual_count:
            return FormalityLevel.FORMAL
        if casual_count > formal_count + 1:
            return FormalityLevel.VERY_CASUAL
        if casual_count > formal_count:
            return FormalityLevel.CASUAL
        return FormalityLevel.NEUTRAL

    def is_humor_appropriate(self, state: UserEmotionalState | None) -> bool:
        """Mizah uygun mu kontrol eder.

        Args:
            state: Kullanici duygusal durumu.

        Returns:
            Mizah uygun mu.
        """
        if not self._humor_enabled:
            return False
        if not state:
            return True

        # Kotu ruh halinde mizah uygun degil
        if state.current_mood in (MoodLevel.VERY_LOW, MoodLevel.LOW):
            return False
        if state.frustration_level > 0.5:
            return False

        return True

    def detect_urgency(self, text: str) -> bool:
        """Aciliyet tespit eder.

        Args:
            text: Metin.

        Returns:
            Acil mi.
        """
        lower = text.lower()
        words = set(re.findall(r'\w+', lower))
        return bool(words & _URGENCY_WORDS)

    def update_profile(self, user_id: str, text: str) -> StyleProfile:
        """Kullanici profilini gunceller.

        Args:
            user_id: Kullanici ID.
            text: Kullanici metni.

        Returns:
            Guncellenmis StyleProfile.
        """
        profile = self._get_or_create_profile(user_id)

        formality = self.detect_formality(text)
        # Ortalama al
        profile.formality = formality

        # Uzunluk tercihi
        word_count = len(text.split())
        if word_count > 50:
            profile.preferred_length = "long"
        elif word_count < 10:
            profile.preferred_length = "short"
        else:
            profile.preferred_length = "medium"

        return profile

    def get_style_recommendation(self, user_id: str, mood: MoodLevel | None = None) -> dict[str, Any]:
        """Stil onerisi getirir.

        Args:
            user_id: Kullanici ID.
            mood: Mevcut ruh hali.

        Returns:
            Stil onerisi sozlugu.
        """
        profile = self._profiles.get(user_id)
        effective_mood = mood or MoodLevel.NEUTRAL

        tone = self.adapt_tone(user_id, effective_mood)
        formality = profile.formality if profile else FormalityLevel.NEUTRAL
        length = profile.preferred_length if profile else "medium"

        return {
            "tone": tone.value,
            "formality": formality.value,
            "length": length,
            "humor_ok": self._humor_enabled and effective_mood not in (MoodLevel.VERY_LOW, MoodLevel.LOW),
            "urgency_aware": False,
        }

    def get_profile(self, user_id: str) -> StyleProfile | None:
        """Profil getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            StyleProfile veya None.
        """
        return self._profiles.get(user_id)

    def _get_or_create_profile(self, user_id: str) -> StyleProfile:
        """Profili getirir veya olusturur."""
        if user_id not in self._profiles:
            self._profiles[user_id] = StyleProfile(user_id=user_id)
        return self._profiles[user_id]

    @property
    def profile_count(self) -> int:
        """Profil sayisi."""
        return len(self._profiles)
