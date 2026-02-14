"""ATLAS Icerik Yerellestirici modulu.

Dokuman yerellestirme, gorsel
yerellestirme, UI uyarlama, yazi
yonu (RTL/LTR) ve font secimi.
"""

import logging
from typing import Any

from app.models.localization import (
    LanguageCode,
    TextDirection,
)

logger = logging.getLogger(__name__)

# Font onerileri
_FONT_RECOMMENDATIONS: dict[str, list[str]] = {
    "latin": ["Inter", "Roboto", "Open Sans"],
    "arabic": ["Noto Sans Arabic", "Cairo", "Amiri"],
    "cyrillic": ["Roboto", "PT Sans", "Open Sans"],
    "cjk": ["Noto Sans CJK", "Source Han Sans"],
    "devanagari": ["Noto Sans Devanagari", "Poppins"],
}


class ContentLocalizer:
    """Icerik yerellestirici.

    Icerik ve arayuzleri hedef dil
    ve bolgeye uyarlar.

    Attributes:
        _localizations: Yerellestirmeler.
        _layouts: Duzenleme ayarlari.
    """

    def __init__(self) -> None:
        """Icerik yerellestiriciyi baslatir."""
        self._localizations: list[dict[str, Any]] = []
        self._layouts: dict[str, dict[str, Any]] = {}
        self._font_overrides: dict[str, str] = {}

        logger.info("ContentLocalizer baslatildi")

    def localize_document(
        self,
        content: str,
        source_lang: str,
        target_lang: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Dokuman yerellestirme.

        Args:
            content: Icerik.
            source_lang: Kaynak dil.
            target_lang: Hedef dil.
            metadata: Ek bilgi.

        Returns:
            Yerellestirme sonucu.
        """
        direction = self._get_direction(target_lang)

        result = {
            "source_lang": source_lang,
            "target_lang": target_lang,
            "content": content,
            "direction": direction.value,
            "font": self._get_font(target_lang),
            "metadata": metadata or {},
        }
        self._localizations.append(result)
        return result

    def adapt_ui(
        self,
        components: list[str],
        target_lang: str,
    ) -> dict[str, Any]:
        """UI uyarlama.

        Args:
            components: Bilesenler.
            target_lang: Hedef dil.

        Returns:
            UI uyarlama bilgisi.
        """
        direction = self._get_direction(target_lang)
        is_rtl = direction == TextDirection.RTL

        adapted = {
            "target_lang": target_lang,
            "direction": direction.value,
            "is_rtl": is_rtl,
            "font": self._get_font(target_lang),
            "components": [],
        }

        for comp in components:
            adapted["components"].append({
                "name": comp,
                "mirror": is_rtl,
                "text_align": "right" if is_rtl else "left",
            })

        return adapted

    def set_layout(
        self,
        language: str,
        layout: dict[str, Any],
    ) -> None:
        """Duzenleme ayari yapar.

        Args:
            language: Dil kodu.
            layout: Duzenleme.
        """
        self._layouts[language] = layout

    def get_layout(
        self,
        language: str,
    ) -> dict[str, Any]:
        """Duzenleme ayari getirir.

        Args:
            language: Dil kodu.

        Returns:
            Duzenleme.
        """
        direction = self._get_direction(language)
        default = {
            "direction": direction.value,
            "font": self._get_font(language),
            "text_align": (
                "right" if direction == TextDirection.RTL
                else "left"
            ),
        }
        custom = self._layouts.get(language, {})
        return {**default, **custom}

    def localize_image(
        self,
        image_id: str,
        alt_texts: dict[str, str],
        target_lang: str,
    ) -> dict[str, Any]:
        """Gorsel yerellestirme.

        Args:
            image_id: Gorsel ID.
            alt_texts: Dil -> alt metin.
            target_lang: Hedef dil.

        Returns:
            Gorsel bilgisi.
        """
        alt = alt_texts.get(
            target_lang,
            alt_texts.get("en", ""),
        )
        direction = self._get_direction(target_lang)

        return {
            "image_id": image_id,
            "alt_text": alt,
            "direction": direction.value,
            "mirror": direction == TextDirection.RTL,
        }

    def get_font_recommendation(
        self,
        script: str,
    ) -> list[str]:
        """Font onerisi getirir.

        Args:
            script: Yazi sistemi.

        Returns:
            Font listesi.
        """
        return _FONT_RECOMMENDATIONS.get(
            script, _FONT_RECOMMENDATIONS["latin"],
        )

    def set_font_override(
        self,
        language: str,
        font: str,
    ) -> None:
        """Font gecersiz kilmasi ayarlar.

        Args:
            language: Dil kodu.
            font: Font adi.
        """
        self._font_overrides[language] = font

    def _get_direction(
        self,
        language: str,
    ) -> TextDirection:
        """Metin yonu getirir.

        Args:
            language: Dil kodu.

        Returns:
            Metin yonu.
        """
        rtl_langs = {"ar", "he", "fa", "ur"}
        if language in rtl_langs:
            return TextDirection.RTL
        return TextDirection.LTR

    def _get_font(self, language: str) -> str:
        """Font getirir.

        Args:
            language: Dil kodu.

        Returns:
            Font adi.
        """
        override = self._font_overrides.get(language)
        if override:
            return override

        script_map = {
            "ar": "arabic",
            "he": "arabic",
            "fa": "arabic",
            "ru": "cyrillic",
            "zh": "cjk",
            "ja": "cjk",
            "ko": "cjk",
            "hi": "devanagari",
        }
        script = script_map.get(language, "latin")
        fonts = _FONT_RECOMMENDATIONS.get(
            script, _FONT_RECOMMENDATIONS["latin"],
        )
        return fonts[0] if fonts else "sans-serif"

    @property
    def localization_count(self) -> int:
        """Yerellestirme sayisi."""
        return len(self._localizations)

    @property
    def layout_count(self) -> int:
        """Duzenleme sayisi."""
        return len(self._layouts)
