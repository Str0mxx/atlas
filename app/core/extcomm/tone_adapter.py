"""ATLAS Ton Adaptörü modülü.

Alıcı analizi, resmiyet ayarı,
kültürel adaptasyon, sektör eşleme,
kişisel stil.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ToneAdapter:
    """Ton adaptörü.

    İletişim tonunu alıcıya göre ayarlar.

    Attributes:
        _profiles: Ton profilleri.
    """

    FORMALITY_LEVELS = {
        "very_formal": {
            "greeting": "Dear Sir/Madam",
            "closing": (
                "Yours faithfully"
            ),
            "style": "third_person",
        },
        "formal": {
            "greeting": "Dear {name}",
            "closing": "Best regards",
            "style": "professional",
        },
        "professional": {
            "greeting": "Hello {name}",
            "closing": "Kind regards",
            "style": "friendly_pro",
        },
        "friendly": {
            "greeting": "Hi {name}",
            "closing": "Best",
            "style": "conversational",
        },
        "casual": {
            "greeting": "Hey {name}",
            "closing": "Cheers",
            "style": "informal",
        },
    }

    INDUSTRY_TONES = {
        "healthcare": "formal",
        "finance": "formal",
        "technology": "professional",
        "education": "professional",
        "creative": "friendly",
        "startup": "casual",
        "government": "very_formal",
        "legal": "very_formal",
        "retail": "friendly",
        "hospitality": "friendly",
    }

    CULTURAL_PREFERENCES = {
        "tr": {
            "formality": "professional",
            "greeting_style": "warm",
            "directness": "indirect",
        },
        "en": {
            "formality": "professional",
            "greeting_style": "standard",
            "directness": "direct",
        },
        "de": {
            "formality": "formal",
            "greeting_style": "formal",
            "directness": "direct",
        },
        "jp": {
            "formality": "very_formal",
            "greeting_style": "respectful",
            "directness": "indirect",
        },
        "fr": {
            "formality": "formal",
            "greeting_style": "polite",
            "directness": "indirect",
        },
    }

    def __init__(
        self,
        default_tone: str = "professional",
    ) -> None:
        """Adaptörü başlatır.

        Args:
            default_tone: Varsayılan ton.
        """
        self._default_tone = default_tone
        self._profiles: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "adaptations": 0,
            "profiles_created": 0,
        }

        logger.info(
            "ToneAdapter baslatildi",
        )

    def analyze_recipient(
        self,
        name: str,
        company: str = "",
        role: str = "",
        industry: str = "",
        culture: str = "en",
    ) -> dict[str, Any]:
        """Alıcıyı analiz eder.

        Args:
            name: İsim.
            company: Şirket.
            role: Rol.
            industry: Sektör.
            culture: Kültür kodu.

        Returns:
            Analiz bilgisi.
        """
        # Sektör tonu
        industry_tone = (
            self.INDUSTRY_TONES.get(
                industry.lower(),
                self._default_tone,
            )
        )

        # Kültürel tercih
        cultural = (
            self.CULTURAL_PREFERENCES.get(
                culture.lower(),
                self.CULTURAL_PREFERENCES[
                    "en"
                ],
            )
        )

        # Rol bazlı ayar
        role_lower = role.lower()
        if any(
            t in role_lower
            for t in [
                "ceo", "director",
                "president", "vp",
            ]
        ):
            formality = "formal"
        elif any(
            t in role_lower
            for t in [
                "manager", "lead", "head",
            ]
        ):
            formality = "professional"
        else:
            formality = industry_tone

        recommended = self._resolve_tone(
            formality,
            cultural["formality"],
            industry_tone,
        )

        return {
            "name": name,
            "recommended_tone": recommended,
            "industry_tone": industry_tone,
            "cultural_formality": cultural[
                "formality"
            ],
            "greeting_style": cultural[
                "greeting_style"
            ],
            "directness": cultural[
                "directness"
            ],
        }

    def adapt_text(
        self,
        text: str,
        target_tone: str,
        recipient_name: str = "",
    ) -> dict[str, Any]:
        """Metni adapte eder.

        Args:
            text: Metin.
            target_tone: Hedef ton.
            recipient_name: Alıcı adı.

        Returns:
            Adaptasyon bilgisi.
        """
        level = self.FORMALITY_LEVELS.get(
            target_tone,
            self.FORMALITY_LEVELS[
                "professional"
            ],
        )

        # Selamlama
        greeting = level["greeting"]
        if recipient_name:
            greeting = greeting.replace(
                "{name}", recipient_name,
            )
        else:
            greeting = greeting.replace(
                " {name}", "",
            )

        # Kapanış
        closing = level["closing"]

        # Ton ayarı
        adapted = self._apply_tone(
            text, target_tone,
        )

        self._stats["adaptations"] += 1

        return {
            "original_length": len(text),
            "adapted_text": adapted,
            "greeting": greeting,
            "closing": closing,
            "tone": target_tone,
            "style": level["style"],
            "adapted": True,
        }

    def create_profile(
        self,
        contact_id: str,
        preferred_tone: str,
        industry: str = "",
        culture: str = "en",
        notes: str = "",
    ) -> dict[str, Any]:
        """Ton profili oluşturur.

        Args:
            contact_id: Kişi ID.
            preferred_tone: Tercih edilen ton.
            industry: Sektör.
            culture: Kültür.
            notes: Notlar.

        Returns:
            Profil bilgisi.
        """
        profile = {
            "contact_id": contact_id,
            "preferred_tone": preferred_tone,
            "industry": industry,
            "culture": culture,
            "notes": notes,
        }
        self._profiles[contact_id] = profile
        self._stats["profiles_created"] += 1

        return {
            "contact_id": contact_id,
            "tone": preferred_tone,
            "created": True,
        }

    def get_profile(
        self,
        contact_id: str,
    ) -> dict[str, Any]:
        """Profil getirir.

        Args:
            contact_id: Kişi ID.

        Returns:
            Profil bilgisi.
        """
        profile = self._profiles.get(
            contact_id,
        )
        if not profile:
            return {
                "error": "profile_not_found",
            }
        return dict(profile)

    def _resolve_tone(
        self,
        *tones: str,
    ) -> str:
        """Tonları çözümler."""
        order = [
            "very_formal", "formal",
            "professional", "friendly",
            "casual",
        ]
        indices = []
        for t in tones:
            if t in order:
                indices.append(
                    order.index(t),
                )
        if not indices:
            return self._default_tone
        # En resmi olanı seç
        return order[min(indices)]

    def _apply_tone(
        self,
        text: str,
        tone: str,
    ) -> str:
        """Tonu uygular."""
        if tone in (
            "very_formal", "formal",
        ):
            text = text.replace(
                "Hi ", "Dear ",
            )
            text = text.replace(
                "Thanks", "Thank you",
            )
            text = text.replace(
                "ASAP",
                "at your earliest convenience",
            )
        elif tone == "casual":
            text = text.replace(
                "Dear ", "Hey ",
            )
            text = text.replace(
                "Thank you", "Thanks",
            )
            text = text.replace(
                "Best regards", "Cheers",
            )
        return text

    @property
    def adaptation_count(self) -> int:
        """Adaptasyon sayısı."""
        return self._stats["adaptations"]

    @property
    def profile_count(self) -> int:
        """Profil sayısı."""
        return len(self._profiles)
