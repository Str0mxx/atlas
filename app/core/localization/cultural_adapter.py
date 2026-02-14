"""ATLAS Kulturel Adaptor modulu.

Kulturel normlar, iletisim stilleri,
resmiyet seviyeleri, renk/sembol
anlamlari ve tabu farkindaligi.
"""

import logging
from typing import Any

from app.models.localization import (
    FormalityLevel,
    LanguageCode,
    TextDirection,
)

logger = logging.getLogger(__name__)

# Kultur profilleri
_CULTURE_PROFILES: dict[str, dict[str, Any]] = {
    "tr": {
        "direction": TextDirection.LTR,
        "formality": FormalityLevel.FORMAL,
        "greeting": "Merhaba",
        "farewell": "Hoşça kalın",
        "colors": {"green": "positive", "red": "negative"},
        "taboos": ["domuz", "alkol reklamı"],
        "communication": "indirect",
        "hierarchy": "high",
    },
    "en": {
        "direction": TextDirection.LTR,
        "formality": FormalityLevel.NEUTRAL,
        "greeting": "Hello",
        "farewell": "Goodbye",
        "colors": {"green": "positive", "red": "negative"},
        "taboos": [],
        "communication": "direct",
        "hierarchy": "low",
    },
    "de": {
        "direction": TextDirection.LTR,
        "formality": FormalityLevel.FORMAL,
        "greeting": "Guten Tag",
        "farewell": "Auf Wiedersehen",
        "colors": {"green": "positive", "red": "negative"},
        "taboos": [],
        "communication": "direct",
        "hierarchy": "medium",
    },
    "ar": {
        "direction": TextDirection.RTL,
        "formality": FormalityLevel.VERY_FORMAL,
        "greeting": "السلام عليكم",
        "farewell": "مع السلامة",
        "colors": {"green": "positive", "black": "formal"},
        "taboos": ["domuz", "alkol", "kumar"],
        "communication": "indirect",
        "hierarchy": "high",
    },
    "ja": {
        "direction": TextDirection.LTR,
        "formality": FormalityLevel.VERY_FORMAL,
        "greeting": "こんにちは",
        "farewell": "さようなら",
        "colors": {"white": "purity", "red": "luck"},
        "taboos": ["sayı 4"],
        "communication": "indirect",
        "hierarchy": "very_high",
    },
}


class CulturalAdapter:
    """Kulturel adaptor.

    Kulturel normlara uygun iletisim
    ve icerik uyarlamasi yapar.

    Attributes:
        _custom_profiles: Ozel profiller.
        _formality_overrides: Resmiyet gecersiz kilmalari.
    """

    def __init__(self) -> None:
        """Kulturel adaptoru baslatir."""
        self._custom_profiles: dict[
            str, dict[str, Any]
        ] = {}
        self._formality_overrides: dict[
            str, FormalityLevel
        ] = {}

        logger.info("CulturalAdapter baslatildi")

    def get_profile(
        self,
        language: str,
    ) -> dict[str, Any]:
        """Kultur profili getirir.

        Args:
            language: Dil kodu.

        Returns:
            Kultur profili.
        """
        custom = self._custom_profiles.get(language)
        if custom:
            return custom

        profile = _CULTURE_PROFILES.get(language)
        if profile:
            return {"language": language, **profile}

        return {
            "language": language,
            "direction": TextDirection.LTR,
            "formality": FormalityLevel.NEUTRAL,
            "supported": False,
        }

    def get_text_direction(
        self,
        language: str,
    ) -> TextDirection:
        """Metin yonu getirir.

        Args:
            language: Dil kodu.

        Returns:
            Metin yonu.
        """
        profile = _CULTURE_PROFILES.get(language, {})
        return profile.get(
            "direction", TextDirection.LTR,
        )

    def get_formality(
        self,
        language: str,
    ) -> FormalityLevel:
        """Resmiyet seviyesi getirir.

        Args:
            language: Dil kodu.

        Returns:
            Resmiyet seviyesi.
        """
        override = self._formality_overrides.get(language)
        if override:
            return override

        profile = _CULTURE_PROFILES.get(language, {})
        return profile.get(
            "formality", FormalityLevel.NEUTRAL,
        )

    def set_formality(
        self,
        language: str,
        level: FormalityLevel,
    ) -> None:
        """Resmiyet seviyesi ayarlar.

        Args:
            language: Dil kodu.
            level: Resmiyet seviyesi.
        """
        self._formality_overrides[language] = level

    def check_taboo(
        self,
        text: str,
        language: str,
    ) -> list[str]:
        """Tabu kontrol eder.

        Args:
            text: Metin.
            language: Dil kodu.

        Returns:
            Bulunan tabular.
        """
        profile = _CULTURE_PROFILES.get(language, {})
        taboos = profile.get("taboos", [])
        text_lower = text.lower()

        found: list[str] = []
        for taboo in taboos:
            if taboo.lower() in text_lower:
                found.append(taboo)
        return found

    def get_greeting(
        self,
        language: str,
    ) -> str:
        """Selamlama getirir.

        Args:
            language: Dil kodu.

        Returns:
            Selamlama mesaji.
        """
        profile = _CULTURE_PROFILES.get(language, {})
        return profile.get("greeting", "Hello")

    def get_color_meaning(
        self,
        color: str,
        language: str,
    ) -> str:
        """Renk anlami getirir.

        Args:
            color: Renk.
            language: Dil kodu.

        Returns:
            Anlam.
        """
        profile = _CULTURE_PROFILES.get(language, {})
        colors = profile.get("colors", {})
        return colors.get(color, "neutral")

    def adapt_communication(
        self,
        message: str,
        language: str,
        formality: FormalityLevel | None = None,
    ) -> dict[str, Any]:
        """Iletisimi uyarlar.

        Args:
            message: Mesaj.
            language: Dil kodu.
            formality: Resmiyet seviyesi.

        Returns:
            Uyarlanmis iletisim bilgisi.
        """
        profile = _CULTURE_PROFILES.get(language, {})
        level = formality or self.get_formality(language)

        return {
            "message": message,
            "language": language,
            "formality": level.value,
            "direction": self.get_text_direction(
                language,
            ).value,
            "style": profile.get(
                "communication", "direct",
            ),
            "taboo_warnings": self.check_taboo(
                message, language,
            ),
        }

    def add_custom_profile(
        self,
        language: str,
        profile: dict[str, Any],
    ) -> None:
        """Ozel kultur profili ekler.

        Args:
            language: Dil kodu.
            profile: Profil verileri.
        """
        self._custom_profiles[language] = {
            "language": language,
            **profile,
        }

    @property
    def supported_cultures(self) -> list[str]:
        """Desteklenen kulturler."""
        return list(_CULTURE_PROFILES.keys())

    @property
    def custom_count(self) -> int:
        """Ozel profil sayisi."""
        return len(self._custom_profiles)
