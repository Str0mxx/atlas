"""ATLAS Yerellestirme Orkestratoru modulu.

Tam yerellestirme pipeline, coklu
dil destegi, kullanici dil tercihleri,
yedek islemleri ve analitik.
"""

import logging
from typing import Any

from app.models.localization import (
    LanguageCode,
    LocalizationSnapshot,
    TextDirection,
)

from app.core.localization.content_localizer import (
    ContentLocalizer,
)
from app.core.localization.cultural_adapter import (
    CulturalAdapter,
)
from app.core.localization.language_detector import (
    LanguageDetector,
)
from app.core.localization.locale_manager import LocaleManager
from app.core.localization.message_catalog import (
    MessageCatalog,
)
from app.core.localization.quality_checker import (
    LocalizationQualityChecker,
)
from app.core.localization.terminology_manager import (
    TerminologyManager,
)
from app.core.localization.translator import Translator

logger = logging.getLogger(__name__)


class LocalizationOrchestrator:
    """Yerellestirme orkestratoru.

    Tum yerellestirme alt sistemlerini
    koordine eder.

    Attributes:
        detector: Dil tespiti.
        translator: Cevirmen.
        locale: Yerel ayar yoneticisi.
        catalog: Mesaj katalogu.
        culture: Kulturel adaptor.
        content: Icerik yerellestirici.
        terminology: Terminoloji yoneticisi.
        quality: Kalite kontrolu.
    """

    def __init__(
        self,
        default_language: str = "en",
        supported_languages: str = "en,tr,de,fr",
        auto_detect: bool = True,
        cache_enabled: bool = True,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            default_language: Varsayilan dil.
            supported_languages: Desteklenen diller.
            auto_detect: Otomatik tespit.
            cache_enabled: Onbellek aktif.
        """
        self.detector = LanguageDetector()
        self.translator = Translator(
            cache_enabled=cache_enabled,
        )
        self.locale = LocaleManager(
            default_locale=default_language,
        )
        self.catalog = MessageCatalog()
        self.culture = CulturalAdapter()
        self.content = ContentLocalizer()
        self.terminology = TerminologyManager()
        self.quality = LocalizationQualityChecker()

        self._default_language = default_language
        self._supported = [
            s.strip()
            for s in supported_languages.split(",")
        ]
        self._auto_detect = auto_detect
        self._user_languages: dict[str, str] = {}
        self._fallback_chain: dict[str, list[str]] = {}

        logger.info("LocalizationOrchestrator baslatildi")

    def localize(
        self,
        text: str,
        target_lang: str | None = None,
        user_id: str | None = None,
        domain: str = "general",
    ) -> dict[str, Any]:
        """Metin yerellestirme (tam pipeline).

        Args:
            text: Kaynak metin.
            target_lang: Hedef dil.
            user_id: Kullanici ID.
            domain: Alan.

        Returns:
            Yerellestirme sonucu.
        """
        # 1. Dil tespiti
        if self._auto_detect:
            detection = self.detector.detect(text)
            source_lang = detection.detected_language.value
        else:
            source_lang = self._default_language

        # 2. Hedef dil belirleme
        if not target_lang:
            if user_id:
                target_lang = self._user_languages.get(
                    user_id, self._default_language,
                )
            else:
                target_lang = self._default_language

        # 3. Katalogdan kontrol
        catalog_text = self.catalog.get_message(
            text, lang=target_lang, fallback=None,
        )

        # 4. Ceviri
        if catalog_text and catalog_text != text:
            translated = catalog_text
            quality_score = 1.0
        else:
            try:
                src = LanguageCode(source_lang)
                tgt = LanguageCode(target_lang)
            except ValueError:
                src = LanguageCode.EN
                tgt = LanguageCode.EN

            record = self.translator.translate(
                text, src, tgt, domain=domain,
            )
            translated = record.translated_text
            quality_score = record.quality_score

        # 5. Kulturel uyarlama
        culture_info = self.culture.adapt_communication(
            translated, target_lang,
        )

        return {
            "source_text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "translated": translated,
            "quality_score": quality_score,
            "direction": culture_info["direction"],
            "formality": culture_info["formality"],
            "taboo_warnings": culture_info[
                "taboo_warnings"
            ],
        }

    def set_user_language(
        self,
        user_id: str,
        language: str,
    ) -> None:
        """Kullanici dil tercihi ayarlar.

        Args:
            user_id: Kullanici ID.
            language: Dil kodu.
        """
        self._user_languages[user_id] = language
        try:
            lang = LanguageCode(language)
            self.detector.set_user_preference(
                user_id, lang,
            )
        except ValueError:
            pass

    def get_user_language(
        self,
        user_id: str,
    ) -> str:
        """Kullanici dil tercihini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Dil kodu.
        """
        return self._user_languages.get(
            user_id, self._default_language,
        )

    def set_fallback_chain(
        self,
        language: str,
        fallbacks: list[str],
    ) -> None:
        """Yedek dil zinciri ayarlar.

        Args:
            language: Dil kodu.
            fallbacks: Yedek diller.
        """
        self._fallback_chain[language] = fallbacks

    def get_with_fallback(
        self,
        key: str,
        language: str,
    ) -> str:
        """Yedek zinciri ile mesaj getirir.

        Args:
            key: Mesaj anahtari.
            language: Dil kodu.

        Returns:
            Mesaj.
        """
        entry = self.catalog._messages.get(key)
        if not entry:
            return key

        # Oncelik: istenen dil
        if language in entry.translations:
            return entry.translations[language]

        # Yedek zinciri
        fallbacks = self._fallback_chain.get(
            language, [self._default_language],
        )
        for fb in fallbacks:
            if fb in entry.translations:
                return entry.translations[fb]

        return key

    def get_analytics(self) -> dict[str, Any]:
        """Analitik verileri getirir.

        Returns:
            Analitik.
        """
        quality_report = self.quality.get_quality_report()

        return {
            "supported_languages": len(self._supported),
            "total_messages": self.catalog.message_count,
            "glossary_terms": self.terminology.total_terms,
            "detection_count": (
                self.detector.detection_count
            ),
            "translation_memory": (
                self.translator.memory_count
            ),
            "cache_hit_rate": (
                self.translator.cache_hit_rate
            ),
            "quality": quality_report,
            "user_preferences": len(
                self._user_languages,
            ),
        }

    def get_snapshot(self) -> LocalizationSnapshot:
        """Goruntusu getirir.

        Returns:
            Goruntusu.
        """
        quality_report = self.quality.get_quality_report()

        return LocalizationSnapshot(
            supported_languages=len(self._supported),
            total_messages=self.catalog.message_count,
            translation_coverage=0.0,
            quality_score=quality_report.get(
                "avg_score", 0.0,
            ),
            glossary_terms=self.terminology.total_terms,
            pending_reviews=self.quality.issue_count,
            detected_languages=(
                self.detector.detection_count
            ),
            cache_hit_rate=self.translator.cache_hit_rate,
        )

    @property
    def supported_languages(self) -> list[str]:
        """Desteklenen diller."""
        return list(self._supported)

    @property
    def default_language(self) -> str:
        """Varsayilan dil."""
        return self._default_language

    @property
    def user_count(self) -> int:
        """Kullanici tercihi sayisi."""
        return len(self._user_languages)
