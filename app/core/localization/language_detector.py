"""ATLAS Dil Tespiti modulu.

Otomatik dil tespiti, yazi sistemi
tanima, guven puanlama, coklu dil
metin ve kullanici tercihi ogrenme.
"""

import logging
import re
from typing import Any

from app.models.localization import (
    DetectionResult,
    LanguageCode,
    ScriptType,
)

logger = logging.getLogger(__name__)

# Dil karakteristik kaliplari
_LANG_PATTERNS: dict[str, list[str]] = {
    "tr": [
        "ç", "ğ", "ı", "ö", "ş", "ü",
        "bir", "ve", "bu", "ile", "için",
    ],
    "en": [
        "the", "is", "are", "was", "were",
        "and", "or", "but", "with", "for",
    ],
    "de": [
        "ä", "ö", "ü", "ß",
        "und", "der", "die", "das", "ist",
    ],
    "fr": [
        "é", "è", "ê", "ë", "ç", "à",
        "les", "des", "une", "est", "dans",
    ],
    "es": [
        "ñ", "¿", "¡",
        "los", "las", "una", "del", "por",
    ],
    "ar": [
        "ال", "في", "من", "على", "إلى",
    ],
    "ru": [
        "и", "в", "на", "не", "что",
    ],
}

# Yazi sistemi araliklari
_SCRIPT_RANGES: dict[str, list[tuple[int, int]]] = {
    "arabic": [(0x0600, 0x06FF), (0xFE70, 0xFEFF)],
    "cyrillic": [(0x0400, 0x04FF)],
    "cjk": [
        (0x4E00, 0x9FFF), (0x3040, 0x309F),
        (0x30A0, 0x30FF),
    ],
    "devanagari": [(0x0900, 0x097F)],
}


class LanguageDetector:
    """Dil tespiti.

    Metnin dilini ve yazi sistemini
    tespit eder, kullanici tercihlerini
    ogrenir.

    Attributes:
        _user_prefs: Kullanici dil tercihleri.
        _detection_history: Tespit gecmisi.
    """

    def __init__(self) -> None:
        """Dil tespitcisini baslatir."""
        self._user_prefs: dict[str, LanguageCode] = {}
        self._detection_history: list[DetectionResult] = []

        logger.info("LanguageDetector baslatildi")

    def detect(self, text: str) -> DetectionResult:
        """Dil tespiti yapar.

        Args:
            text: Tespit edilecek metin.

        Returns:
            Tespit sonucu.
        """
        if not text.strip():
            return DetectionResult(
                text=text,
                detected_language=LanguageCode.EN,
                confidence=0.0,
            )

        script = self._detect_script(text)
        scores = self._score_languages(text)

        # En yuksek puan
        if scores:
            best_lang = max(scores, key=scores.get)
            best_score = scores[best_lang]
        else:
            best_lang = "en"
            best_score = 0.1

        # Alternatifler
        alts = [
            {"language": lang, "score": round(sc, 3)}
            for lang, sc in sorted(
                scores.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            if lang != best_lang
        ][:3]

        try:
            lang_code = LanguageCode(best_lang)
        except ValueError:
            lang_code = LanguageCode.EN

        result = DetectionResult(
            text=text[:100],
            detected_language=lang_code,
            confidence=round(min(1.0, best_score), 3),
            script=script,
            alternatives=alts,
        )
        self._detection_history.append(result)
        return result

    def detect_script(self, text: str) -> ScriptType:
        """Yazi sistemi tespiti yapar.

        Args:
            text: Metin.

        Returns:
            Yazi sistemi.
        """
        return self._detect_script(text)

    def set_user_preference(
        self,
        user_id: str,
        language: LanguageCode,
    ) -> None:
        """Kullanici dil tercihi ayarlar.

        Args:
            user_id: Kullanici ID.
            language: Tercih edilen dil.
        """
        self._user_prefs[user_id] = language

    def get_user_preference(
        self,
        user_id: str,
    ) -> LanguageCode | None:
        """Kullanici dil tercihi getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Dil kodu veya None.
        """
        return self._user_prefs.get(user_id)

    def learn_from_history(
        self,
        user_id: str,
    ) -> LanguageCode | None:
        """Gecmisten kullanici dilini ogrenir.

        Args:
            user_id: Kullanici ID.

        Returns:
            En sik kullanilan dil veya None.
        """
        if not self._detection_history:
            return None

        lang_counts: dict[str, int] = {}
        for result in self._detection_history:
            lang = result.detected_language.value
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

        if lang_counts:
            best = max(lang_counts, key=lang_counts.get)
            try:
                lang_code = LanguageCode(best)
                self._user_prefs[user_id] = lang_code
                return lang_code
            except ValueError:
                pass
        return None

    def _detect_script(self, text: str) -> ScriptType:
        """Yazi sistemini tespit eder.

        Args:
            text: Metin.

        Returns:
            Yazi sistemi.
        """
        for char in text:
            code = ord(char)
            for script_name, ranges in _SCRIPT_RANGES.items():
                for start, end in ranges:
                    if start <= code <= end:
                        return ScriptType(script_name)
        return ScriptType.LATIN

    def _score_languages(
        self,
        text: str,
    ) -> dict[str, float]:
        """Diller icin puan hesaplar.

        Args:
            text: Metin.

        Returns:
            Dil -> puan eslesmesi.
        """
        text_lower = text.lower()
        words = re.findall(r"\w+", text_lower)
        scores: dict[str, float] = {}

        for lang, patterns in _LANG_PATTERNS.items():
            score = 0.0
            for pattern in patterns:
                if len(pattern) <= 2:
                    # Karakter kontrolu
                    if pattern in text_lower:
                        score += 0.15
                else:
                    # Kelime kontrolu
                    if pattern in words:
                        score += 0.2
            scores[lang] = score

        return scores

    @property
    def detection_count(self) -> int:
        """Tespit sayisi."""
        return len(self._detection_history)

    @property
    def user_pref_count(self) -> int:
        """Kullanici tercihi sayisi."""
        return len(self._user_prefs)
