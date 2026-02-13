"""ATLAS Kisilik Adaptoru modulu.

Kullanici tercih ogrenme, iletisim stili hafizasi,
mizah stili eslestirme, resmiyet tercihleri ve
yanit uzunluk tercihleri.
"""

import logging
from typing import Any

from app.models.emotional import (
    CommunicationTone,
    FormalityLevel,
    PersonalityProfile,
)

logger = logging.getLogger(__name__)

# Ton -> mizah stili eslesmesi
_HUMOR_STYLES: dict[CommunicationTone, str] = {
    CommunicationTone.CASUAL: "playful",
    CommunicationTone.ENTHUSIASTIC: "energetic",
    CommunicationTone.SUPPORTIVE: "gentle",
    CommunicationTone.EMPATHETIC: "warm",
    CommunicationTone.FORMAL: "subtle",
    CommunicationTone.PROFESSIONAL: "light",
}


class PersonalityAdapter:
    """Kisilik adaptor sistemi.

    Kullanicinin iletisim tercihlerini ogrenir
    ve yanit stilini buna gore adapte eder.

    Attributes:
        _profiles: Kisilik profilleri.
        _interaction_logs: Etkilesim kayitlari.
    """

    def __init__(self) -> None:
        """Kisilik adaptorunu baslatir."""
        self._profiles: dict[str, PersonalityProfile] = {}
        self._interaction_logs: dict[str, list[dict[str, Any]]] = {}

        logger.info("PersonalityAdapter baslatildi")

    def learn_from_interaction(
        self,
        user_id: str,
        text: str,
        tone: CommunicationTone | None = None,
        formality: FormalityLevel | None = None,
    ) -> PersonalityProfile:
        """Etkilesimden ogrenir.

        Args:
            user_id: Kullanici ID.
            text: Kullanici metni.
            tone: Tespit edilen ton.
            formality: Tespit edilen resmiyet.

        Returns:
            Guncellenmis PersonalityProfile.
        """
        profile = self._get_or_create(user_id)
        profile.interactions_analyzed += 1

        # Etkilesim kaydet
        log = self._interaction_logs.setdefault(user_id, [])
        log.append({
            "text_length": len(text),
            "word_count": len(text.split()),
            "tone": tone.value if tone else None,
            "formality": formality.value if formality else None,
        })

        # Ton guncelle
        if tone:
            profile.communication_style = tone
            profile.humor_style = _HUMOR_STYLES.get(tone, "light")

        # Resmiyet guncelle
        if formality:
            profile.formality_pref = formality

        # Uzunluk tercihi guncelle
        word_count = len(text.split())
        profile.response_length_pref = self._infer_length_pref(user_id)

        # Sabir seviyesi (kisa mesajlar = dusuk sabir)
        if word_count < 5:
            profile.patience_level = max(profile.patience_level - 0.05, 0.0)
        elif word_count > 30:
            profile.patience_level = min(profile.patience_level + 0.03, 1.0)

        # Detay tercihi (uzun mesajlar = yuksek detay)
        if word_count > 50:
            profile.detail_preference = min(profile.detail_preference + 0.05, 1.0)
        elif word_count < 10:
            profile.detail_preference = max(profile.detail_preference - 0.03, 0.0)

        return profile

    def get_profile(self, user_id: str) -> PersonalityProfile | None:
        """Profil getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            PersonalityProfile veya None.
        """
        return self._profiles.get(user_id)

    def get_preferred_tone(self, user_id: str) -> CommunicationTone:
        """Tercih edilen tonu getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            CommunicationTone degeri.
        """
        profile = self._profiles.get(user_id)
        if not profile:
            return CommunicationTone.PROFESSIONAL
        return profile.communication_style

    def get_humor_style(self, user_id: str) -> str:
        """Mizah stilini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Mizah stili.
        """
        profile = self._profiles.get(user_id)
        if not profile:
            return "light"
        return profile.humor_style

    def get_formality(self, user_id: str) -> FormalityLevel:
        """Resmiyet tercihini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            FormalityLevel degeri.
        """
        profile = self._profiles.get(user_id)
        if not profile:
            return FormalityLevel.NEUTRAL
        return profile.formality_pref

    def get_response_length(self, user_id: str) -> str:
        """Yanit uzunluk tercihini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Uzunluk tercihi.
        """
        profile = self._profiles.get(user_id)
        if not profile:
            return "medium"
        return profile.response_length_pref

    def get_adaptation_summary(self, user_id: str) -> dict[str, Any]:
        """Adaptasyon ozetini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Ozet sozlugu.
        """
        profile = self._profiles.get(user_id)
        if not profile:
            return {"status": "no_profile", "user_id": user_id}

        return {
            "user_id": user_id,
            "tone": profile.communication_style.value,
            "humor_style": profile.humor_style,
            "formality": profile.formality_pref.value,
            "response_length": profile.response_length_pref,
            "patience": round(profile.patience_level, 2),
            "detail_preference": round(profile.detail_preference, 2),
            "interactions": profile.interactions_analyzed,
        }

    def _get_or_create(self, user_id: str) -> PersonalityProfile:
        """Profili getirir veya olusturur."""
        if user_id not in self._profiles:
            self._profiles[user_id] = PersonalityProfile(user_id=user_id)
        return self._profiles[user_id]

    def _infer_length_pref(self, user_id: str) -> str:
        """Uzunluk tercihini cikarir."""
        logs = self._interaction_logs.get(user_id, [])
        if not logs:
            return "medium"

        recent = logs[-10:]
        avg_words = sum(l["word_count"] for l in recent) / len(recent)

        if avg_words > 40:
            return "long"
        if avg_words < 10:
            return "short"
        return "medium"

    @property
    def profile_count(self) -> int:
        """Profil sayisi."""
        return len(self._profiles)
