"""ATLAS Mesaj Katalogu modulu.

String yonetimi, placeholder islemleri,
cogullastirma, cinsiyet islemleri
ve baglam varyantlari.
"""

import logging
import re
from typing import Any

from app.models.localization import (
    LanguageCode,
    MessageEntry,
    PluralForm,
)

logger = logging.getLogger(__name__)

# Dil cogul kurallari
_PLURAL_RULES: dict[str, Any] = {
    "tr": lambda n: PluralForm.ONE if n == 1
    else PluralForm.OTHER,
    "en": lambda n: PluralForm.ONE if n == 1
    else PluralForm.OTHER,
    "ar": lambda n: (
        PluralForm.ZERO if n == 0
        else PluralForm.ONE if n == 1
        else PluralForm.TWO if n == 2
        else PluralForm.FEW if 3 <= n <= 10
        else PluralForm.MANY if 11 <= n <= 99
        else PluralForm.OTHER
    ),
    "fr": lambda n: PluralForm.ONE if n in (0, 1)
    else PluralForm.OTHER,
}


class MessageCatalog:
    """Mesaj katalogu.

    Coklu dil mesajlarini yonetir,
    cogullastirma ve placeholder
    islemleri yapar.

    Attributes:
        _messages: Mesaj girisler.
        _contexts: Baglam varyantlari.
    """

    def __init__(self) -> None:
        """Mesaj katalogu baslatir."""
        self._messages: dict[str, MessageEntry] = {}
        self._contexts: dict[str, dict[str, str]] = {}

        logger.info("MessageCatalog baslatildi")

    def add_message(
        self,
        key: str,
        translations: dict[str, str],
        context: str = "",
        plurals: dict[str, str] | None = None,
    ) -> MessageEntry:
        """Mesaj ekler.

        Args:
            key: Mesaj anahtari.
            translations: Dil -> ceviri eslesmesi.
            context: Baglam.
            plurals: Cogul formlar.

        Returns:
            Mesaj girisi.
        """
        entry = MessageEntry(
            key=key,
            translations=translations,
            context=context,
            plurals=plurals or {},
        )
        self._messages[key] = entry
        return entry

    def get_message(
        self,
        key: str,
        lang: str = "en",
        fallback: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Mesaj getirir.

        Args:
            key: Mesaj anahtari.
            lang: Dil kodu.
            fallback: Yedek metin.
            **kwargs: Placeholder degerleri.

        Returns:
            Cevrilmis ve bicimlenmis mesaj.
        """
        entry = self._messages.get(key)
        if not entry:
            return fallback or key

        text = entry.translations.get(lang)
        if not text:
            # Ingilizce'ye geri don
            text = entry.translations.get("en")
        if not text:
            # Herhangi bir dili kullan
            if entry.translations:
                text = next(iter(entry.translations.values()))
            else:
                return fallback or key

        # Placeholder yer degistirme
        if kwargs:
            text = self._apply_placeholders(text, kwargs)

        return text

    def get_plural(
        self,
        key: str,
        count: int,
        lang: str = "en",
        **kwargs: Any,
    ) -> str:
        """Cogul mesaj getirir.

        Args:
            key: Mesaj anahtari.
            count: Sayi.
            lang: Dil kodu.
            **kwargs: Placeholder degerleri.

        Returns:
            Cogul mesaj.
        """
        entry = self._messages.get(key)
        if not entry:
            return key

        rule_fn = _PLURAL_RULES.get(
            lang,
            _PLURAL_RULES.get("en"),
        )
        if rule_fn:
            form = rule_fn(count)
        else:
            form = (
                PluralForm.ONE if count == 1
                else PluralForm.OTHER
            )

        # Cogul formdan metin al
        text = entry.plurals.get(
            f"{lang}:{form.value}",
        )
        if not text:
            text = entry.plurals.get(form.value)
        if not text:
            text = self.get_message(key, lang)

        kwargs["count"] = count
        return self._apply_placeholders(text, kwargs)

    def add_context_variant(
        self,
        key: str,
        context: str,
        translations: dict[str, str],
    ) -> None:
        """Baglam varyanti ekler.

        Args:
            key: Mesaj anahtari.
            context: Baglam.
            translations: Ceviri eslesmesi.
        """
        ctx_key = f"{key}:{context}"
        self._contexts[ctx_key] = translations

    def get_with_context(
        self,
        key: str,
        context: str,
        lang: str = "en",
    ) -> str:
        """Baglamli mesaj getirir.

        Args:
            key: Mesaj anahtari.
            context: Baglam.
            lang: Dil kodu.

        Returns:
            Mesaj.
        """
        ctx_key = f"{key}:{context}"
        translations = self._contexts.get(ctx_key)
        if translations:
            text = translations.get(lang)
            if text:
                return text

        return self.get_message(key, lang)

    def get_missing_translations(
        self,
        lang: str,
    ) -> list[str]:
        """Eksik cevirileri bulur.

        Args:
            lang: Dil kodu.

        Returns:
            Eksik anahtar listesi.
        """
        missing: list[str] = []
        for key, entry in self._messages.items():
            if lang not in entry.translations:
                missing.append(key)
        return missing

    def get_coverage(
        self,
        lang: str,
    ) -> float:
        """Ceviri kapsam orani getirir.

        Args:
            lang: Dil kodu.

        Returns:
            Kapsam orani (0.0-1.0).
        """
        if not self._messages:
            return 0.0

        translated = sum(
            1 for entry in self._messages.values()
            if lang in entry.translations
        )
        return round(
            translated / len(self._messages), 3,
        )

    def remove_message(self, key: str) -> bool:
        """Mesaj siler.

        Args:
            key: Mesaj anahtari.

        Returns:
            Basarili ise True.
        """
        if key in self._messages:
            del self._messages[key]
            return True
        return False

    def _apply_placeholders(
        self,
        text: str,
        values: dict[str, Any],
    ) -> str:
        """Placeholder yer degistirme.

        Args:
            text: Metin.
            values: Degerler.

        Returns:
            Bicimlenmis metin.
        """
        result = text
        for key, val in values.items():
            result = result.replace(
                f"{{{key}}}", str(val),
            )
        return result

    @property
    def message_count(self) -> int:
        """Mesaj sayisi."""
        return len(self._messages)

    @property
    def context_count(self) -> int:
        """Baglam varyant sayisi."""
        return len(self._contexts)
