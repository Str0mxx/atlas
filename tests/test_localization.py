"""Multi-Language & Localization sistemi testleri."""

import pytest

from app.models.localization import (
    DetectionResult,
    FormalityLevel,
    LanguageCode,
    LocalizationSnapshot,
    MessageEntry,
    PluralForm,
    QualityLevel,
    ScriptType,
    TextDirection,
    TranslationRecord,
)

from app.core.localization import (
    ContentLocalizer,
    CulturalAdapter,
    LanguageDetector,
    LocaleManager,
    LocalizationOrchestrator,
    LocalizationQualityChecker,
    MessageCatalog,
    TerminologyManager,
    Translator,
)


# ── Model Testleri ──────────────────────────────────


class TestLocalizationModels:
    """Model testleri."""

    def test_language_code_enum(self):
        assert LanguageCode.TR == "tr"
        assert LanguageCode.EN == "en"
        assert LanguageCode.AR == "ar"

    def test_script_type_enum(self):
        assert ScriptType.LATIN == "latin"
        assert ScriptType.ARABIC == "arabic"
        assert ScriptType.CJK == "cjk"

    def test_text_direction_enum(self):
        assert TextDirection.LTR == "ltr"
        assert TextDirection.RTL == "rtl"

    def test_formality_level_enum(self):
        assert FormalityLevel.INFORMAL == "informal"
        assert FormalityLevel.VERY_FORMAL == "very_formal"

    def test_quality_level_enum(self):
        assert QualityLevel.POOR == "poor"
        assert QualityLevel.EXCELLENT == "excellent"

    def test_plural_form_enum(self):
        assert PluralForm.ONE == "one"
        assert PluralForm.MANY == "many"

    def test_detection_result_defaults(self):
        r = DetectionResult()
        assert r.result_id
        assert r.confidence == 0.0
        assert r.script == ScriptType.LATIN

    def test_translation_record_defaults(self):
        r = TranslationRecord()
        assert r.translation_id
        assert r.source_lang == LanguageCode.EN
        assert r.quality_score == 0.0

    def test_message_entry_defaults(self):
        e = MessageEntry()
        assert e.key == ""
        assert e.translations == {}

    def test_localization_snapshot_defaults(self):
        s = LocalizationSnapshot()
        assert s.supported_languages == 0
        assert s.total_messages == 0
        assert s.cache_hit_rate == 0.0


# ── LanguageDetector Testleri ───────────────────────


class TestLanguageDetector:
    """LanguageDetector testleri."""

    def test_init(self):
        ld = LanguageDetector()
        assert ld.detection_count == 0

    def test_detect_turkish(self):
        ld = LanguageDetector()
        result = ld.detect("Bu bir test ve çalışıyor")
        assert result.detected_language == LanguageCode.TR
        assert result.confidence > 0

    def test_detect_english(self):
        ld = LanguageDetector()
        result = ld.detect(
            "The quick brown fox is running",
        )
        assert result.detected_language == LanguageCode.EN

    def test_detect_empty(self):
        ld = LanguageDetector()
        result = ld.detect("")
        assert result.confidence == 0.0

    def test_detect_script_latin(self):
        ld = LanguageDetector()
        assert (
            ld.detect_script("Hello world")
            == ScriptType.LATIN
        )

    def test_detect_script_arabic(self):
        ld = LanguageDetector()
        assert (
            ld.detect_script("مرحبا بالعالم")
            == ScriptType.ARABIC
        )

    def test_detect_script_cyrillic(self):
        ld = LanguageDetector()
        assert (
            ld.detect_script("Привет мир")
            == ScriptType.CYRILLIC
        )

    def test_user_preference(self):
        ld = LanguageDetector()
        ld.set_user_preference("u1", LanguageCode.TR)
        assert (
            ld.get_user_preference("u1")
            == LanguageCode.TR
        )
        assert ld.get_user_preference("u2") is None

    def test_learn_from_history(self):
        ld = LanguageDetector()
        ld.detect("Bu bir test ve bu da test")
        ld.detect("Bu çalışıyor ve güzel")
        result = ld.learn_from_history("u1")
        assert result is not None
        assert ld.user_pref_count >= 1

    def test_learn_empty_history(self):
        ld = LanguageDetector()
        assert ld.learn_from_history("u1") is None

    def test_alternatives(self):
        ld = LanguageDetector()
        result = ld.detect(
            "This is a test with the word and",
        )
        assert isinstance(result.alternatives, list)

    def test_detection_count(self):
        ld = LanguageDetector()
        ld.detect("test")
        ld.detect("test2")
        assert ld.detection_count == 2


# ── Translator Testleri ─────────────────────────────


class TestTranslator:
    """Translator testleri."""

    def test_init(self):
        t = Translator()
        assert t.memory_count == 0

    def test_translate_same_lang(self):
        t = Translator()
        rec = t.translate(
            "hello", LanguageCode.EN, LanguageCode.EN,
        )
        assert rec.translated_text == "hello"
        assert rec.quality_score == 1.0

    def test_translate_different_lang(self):
        t = Translator()
        rec = t.translate(
            "hello", LanguageCode.EN, LanguageCode.TR,
        )
        assert rec.translated_text
        assert rec.source_lang == LanguageCode.EN
        assert rec.target_lang == LanguageCode.TR

    def test_add_to_memory(self):
        t = Translator()
        t.add_to_memory(
            "hello", "merhaba",
            LanguageCode.EN, LanguageCode.TR,
        )
        assert t.memory_count == 1

    def test_memory_lookup(self):
        t = Translator()
        t.add_to_memory(
            "hello", "merhaba",
            LanguageCode.EN, LanguageCode.TR,
        )
        rec = t.translate(
            "hello", LanguageCode.EN, LanguageCode.TR,
        )
        assert rec.translated_text == "merhaba"

    def test_domain_term(self):
        t = Translator()
        t.add_domain_term(
            "medical",
            "surgery",
            {"tr": "ameliyat"},
        )
        rec = t.translate(
            "surgery",
            LanguageCode.EN, LanguageCode.TR,
            domain="medical",
        )
        assert "ameliyat" in rec.translated_text

    def test_cache_hit(self):
        t = Translator(cache_enabled=True)
        t.translate(
            "test", LanguageCode.EN, LanguageCode.TR,
        )
        t.translate(
            "test", LanguageCode.EN, LanguageCode.TR,
        )
        assert t.cache_hit_rate > 0

    def test_cache_disabled(self):
        t = Translator(cache_enabled=False)
        t.translate(
            "test", LanguageCode.EN, LanguageCode.TR,
        )
        assert t.cache_hit_rate == 0.0

    def test_clear_cache(self):
        t = Translator()
        t.translate(
            "test", LanguageCode.EN, LanguageCode.TR,
        )
        count = t.clear_cache()
        assert count >= 0

    def test_get_memory_entries(self):
        t = Translator()
        t.add_to_memory(
            "hi", "merhaba",
            LanguageCode.EN, LanguageCode.TR,
        )
        t.add_to_memory(
            "bye", "hoşçakal",
            LanguageCode.EN, LanguageCode.TR,
        )
        entries = t.get_memory_entries(
            source=LanguageCode.EN,
        )
        assert len(entries) == 2

    def test_domain_count(self):
        t = Translator()
        t.add_domain_term("med", "x", {"tr": "y"})
        t.add_domain_term("tech", "a", {"tr": "b"})
        assert t.domain_count == 2


# ── LocaleManager Testleri ──────────────────────────


class TestLocaleManager:
    """LocaleManager testleri."""

    def test_init(self):
        lm = LocaleManager()
        assert lm.default_locale == "en"

    def test_format_number_en(self):
        lm = LocaleManager("en")
        result = lm.format_number(1234567.89)
        assert "1" in result
        assert "." in result

    def test_format_number_tr(self):
        lm = LocaleManager("tr")
        result = lm.format_number(1234.56)
        assert "," in result  # Ondalik ayirac

    def test_format_number_negative(self):
        lm = LocaleManager("en")
        result = lm.format_number(-42.5)
        assert result.startswith("-")

    def test_format_currency_en(self):
        lm = LocaleManager("en")
        result = lm.format_currency(99.99)
        assert "$" in result

    def test_format_currency_tr(self):
        lm = LocaleManager("tr")
        result = lm.format_currency(99.99)
        assert "₺" in result

    def test_format_date_en(self):
        lm = LocaleManager("en")
        result = lm.format_date(2026, 2, 14)
        assert "02/14/2026" == result

    def test_format_date_tr(self):
        lm = LocaleManager("tr")
        result = lm.format_date(2026, 2, 14)
        assert "14.02.2026" == result

    def test_convert_length(self):
        lm = LocaleManager()
        result = lm.convert_unit(1.0, "km", "m")
        assert result == 1000.0

    def test_convert_weight(self):
        lm = LocaleManager()
        result = lm.convert_unit(
            1.0, "kg", "g", "weight",
        )
        assert result == 1000.0

    def test_convert_temperature(self):
        lm = LocaleManager()
        result = lm.convert_unit(
            100, "C", "F", "temperature",
        )
        assert result == 212.0

    def test_convert_temp_k(self):
        lm = LocaleManager()
        result = lm.convert_unit(
            0, "C", "K", "temperature",
        )
        assert result == 273.15

    def test_convert_unknown(self):
        lm = LocaleManager()
        assert lm.convert_unit(
            1, "xyz", "abc",
        ) is None

    def test_get_locale_info(self):
        lm = LocaleManager("tr")
        info = lm.get_locale_info()
        assert info["locale"] == "tr"
        assert info["currency"] == "TRY"

    def test_get_locale_unsupported(self):
        lm = LocaleManager()
        info = lm.get_locale_info("xx")
        assert info.get("supported") is False

    def test_supported_locales(self):
        lm = LocaleManager()
        locales = lm.get_supported_locales()
        assert "en" in locales
        assert "tr" in locales

    def test_custom_format(self):
        lm = LocaleManager()
        lm.set_custom_format("en", "date", "YYYY-MM-DD")
        assert lm._custom_formats["en"]["date"] == "YYYY-MM-DD"


# ── MessageCatalog Testleri ─────────────────────────


class TestMessageCatalog:
    """MessageCatalog testleri."""

    def test_init(self):
        mc = MessageCatalog()
        assert mc.message_count == 0

    def test_add_message(self):
        mc = MessageCatalog()
        entry = mc.add_message(
            "greeting",
            {"en": "Hello", "tr": "Merhaba"},
        )
        assert entry.key == "greeting"
        assert mc.message_count == 1

    def test_get_message(self):
        mc = MessageCatalog()
        mc.add_message(
            "greeting",
            {"en": "Hello", "tr": "Merhaba"},
        )
        assert mc.get_message("greeting", "tr") == "Merhaba"
        assert mc.get_message("greeting", "en") == "Hello"

    def test_get_message_fallback(self):
        mc = MessageCatalog()
        mc.add_message("hi", {"en": "Hello"})
        # Turkce yok, Ingilizce'ye geri don
        assert mc.get_message("hi", "tr") == "Hello"

    def test_get_message_missing(self):
        mc = MessageCatalog()
        assert mc.get_message("nope") == "nope"
        assert (
            mc.get_message("nope", fallback="?") == "?"
        )

    def test_placeholder(self):
        mc = MessageCatalog()
        mc.add_message(
            "welcome",
            {"en": "Hello {name}!", "tr": "Merhaba {name}!"},
        )
        result = mc.get_message(
            "welcome", "tr", name="Fatih",
        )
        assert result == "Merhaba Fatih!"

    def test_plural(self):
        mc = MessageCatalog()
        mc.add_message(
            "items",
            {"en": "{count} items"},
            plurals={
                "one": "{count} item",
                "other": "{count} items",
            },
        )
        assert mc.get_plural("items", 1, "en") == "1 item"
        assert (
            mc.get_plural("items", 5, "en") == "5 items"
        )

    def test_context_variant(self):
        mc = MessageCatalog()
        mc.add_message("save", {"en": "Save"})
        mc.add_context_variant(
            "save", "file",
            {"en": "Save File", "tr": "Dosya Kaydet"},
        )
        assert (
            mc.get_with_context("save", "file", "en")
            == "Save File"
        )
        assert (
            mc.get_with_context("save", "file", "tr")
            == "Dosya Kaydet"
        )

    def test_context_fallback(self):
        mc = MessageCatalog()
        mc.add_message("save", {"en": "Save"})
        # Baglam yok, normal mesaja geri don
        result = mc.get_with_context(
            "save", "unknown", "en",
        )
        assert result == "Save"

    def test_missing_translations(self):
        mc = MessageCatalog()
        mc.add_message("a", {"en": "A"})
        mc.add_message("b", {"en": "B", "tr": "B"})
        missing = mc.get_missing_translations("tr")
        assert "a" in missing
        assert "b" not in missing

    def test_coverage(self):
        mc = MessageCatalog()
        mc.add_message("a", {"en": "A", "tr": "A"})
        mc.add_message("b", {"en": "B"})
        assert mc.get_coverage("en") == 1.0
        assert mc.get_coverage("tr") == 0.5

    def test_coverage_empty(self):
        mc = MessageCatalog()
        assert mc.get_coverage("en") == 0.0

    def test_remove_message(self):
        mc = MessageCatalog()
        mc.add_message("x", {"en": "X"})
        assert mc.remove_message("x")
        assert mc.message_count == 0
        assert not mc.remove_message("x")


# ── CulturalAdapter Testleri ────────────────────────


class TestCulturalAdapter:
    """CulturalAdapter testleri."""

    def test_init(self):
        ca = CulturalAdapter()
        assert len(ca.supported_cultures) > 0

    def test_get_profile_tr(self):
        ca = CulturalAdapter()
        profile = ca.get_profile("tr")
        assert profile["formality"] == FormalityLevel.FORMAL

    def test_get_profile_unknown(self):
        ca = CulturalAdapter()
        profile = ca.get_profile("xx")
        assert profile.get("supported") is False

    def test_text_direction_ltr(self):
        ca = CulturalAdapter()
        assert (
            ca.get_text_direction("en")
            == TextDirection.LTR
        )

    def test_text_direction_rtl(self):
        ca = CulturalAdapter()
        assert (
            ca.get_text_direction("ar")
            == TextDirection.RTL
        )

    def test_formality(self):
        ca = CulturalAdapter()
        assert (
            ca.get_formality("ja")
            == FormalityLevel.VERY_FORMAL
        )

    def test_set_formality(self):
        ca = CulturalAdapter()
        ca.set_formality("en", FormalityLevel.FORMAL)
        assert (
            ca.get_formality("en")
            == FormalityLevel.FORMAL
        )

    def test_check_taboo(self):
        ca = CulturalAdapter()
        found = ca.check_taboo("domuz eti", "tr")
        assert len(found) > 0

    def test_check_no_taboo(self):
        ca = CulturalAdapter()
        found = ca.check_taboo("hello world", "en")
        assert len(found) == 0

    def test_greeting(self):
        ca = CulturalAdapter()
        assert ca.get_greeting("tr") == "Merhaba"
        assert ca.get_greeting("en") == "Hello"

    def test_color_meaning(self):
        ca = CulturalAdapter()
        assert (
            ca.get_color_meaning("green", "en")
            == "positive"
        )
        assert (
            ca.get_color_meaning("unknown", "en")
            == "neutral"
        )

    def test_adapt_communication(self):
        ca = CulturalAdapter()
        result = ca.adapt_communication(
            "Test mesajı", "ar",
        )
        assert result["direction"] == "rtl"
        assert result["formality"] == "very_formal"

    def test_custom_profile(self):
        ca = CulturalAdapter()
        ca.add_custom_profile("ko", {
            "formality": FormalityLevel.FORMAL,
        })
        profile = ca.get_profile("ko")
        assert profile["formality"] == FormalityLevel.FORMAL
        assert ca.custom_count == 1


# ── ContentLocalizer Testleri ───────────────────────


class TestContentLocalizer:
    """ContentLocalizer testleri."""

    def test_init(self):
        cl = ContentLocalizer()
        assert cl.localization_count == 0

    def test_localize_document(self):
        cl = ContentLocalizer()
        result = cl.localize_document(
            "Hello world", "en", "tr",
        )
        assert result["source_lang"] == "en"
        assert result["target_lang"] == "tr"
        assert result["direction"] == "ltr"
        assert cl.localization_count == 1

    def test_localize_document_rtl(self):
        cl = ContentLocalizer()
        result = cl.localize_document(
            "content", "en", "ar",
        )
        assert result["direction"] == "rtl"

    def test_adapt_ui(self):
        cl = ContentLocalizer()
        result = cl.adapt_ui(["btn", "nav"], "en")
        assert result["direction"] == "ltr"
        assert not result["is_rtl"]
        assert len(result["components"]) == 2

    def test_adapt_ui_rtl(self):
        cl = ContentLocalizer()
        result = cl.adapt_ui(["btn"], "ar")
        assert result["is_rtl"]
        assert (
            result["components"][0]["text_align"]
            == "right"
        )

    def test_set_get_layout(self):
        cl = ContentLocalizer()
        cl.set_layout("tr", {"margin": "10px"})
        layout = cl.get_layout("tr")
        assert layout["margin"] == "10px"
        assert layout["direction"] == "ltr"

    def test_localize_image(self):
        cl = ContentLocalizer()
        result = cl.localize_image(
            "img1",
            {"en": "Logo", "tr": "Logo TR"},
            "tr",
        )
        assert result["alt_text"] == "Logo TR"

    def test_localize_image_fallback(self):
        cl = ContentLocalizer()
        result = cl.localize_image(
            "img1", {"en": "Logo"}, "fr",
        )
        assert result["alt_text"] == "Logo"

    def test_font_recommendation(self):
        cl = ContentLocalizer()
        fonts = cl.get_font_recommendation("arabic")
        assert len(fonts) > 0

    def test_font_override(self):
        cl = ContentLocalizer()
        cl.set_font_override("tr", "CustomFont")
        layout = cl.get_layout("tr")
        assert layout["font"] == "CustomFont"


# ── TerminologyManager Testleri ─────────────────────


class TestTerminologyManager:
    """TerminologyManager testleri."""

    def test_init(self):
        tm = TerminologyManager()
        assert tm.total_terms == 0

    def test_add_term(self):
        tm = TerminologyManager()
        result = tm.add_term(
            "medical",
            "surgery",
            {"tr": "ameliyat", "de": "Operation"},
        )
        assert result["term"] == "surgery"
        assert tm.total_terms == 1

    def test_get_term(self):
        tm = TerminologyManager()
        tm.add_term(
            "medical", "surgery", {"tr": "ameliyat"},
        )
        assert (
            tm.get_term("medical", "surgery", "tr")
            == "ameliyat"
        )
        assert (
            tm.get_term("medical", "surgery", "fr")
            is None
        )

    def test_search_term(self):
        tm = TerminologyManager()
        tm.add_term("med", "surgery", {"tr": "ameliyat"})
        tm.add_term("med", "doctor", {"tr": "doktor"})
        results = tm.search_term("surg")
        assert len(results) == 1
        assert results[0]["term"] == "surgery"

    def test_search_by_translation(self):
        tm = TerminologyManager()
        tm.add_term("med", "doctor", {"tr": "doktor"})
        results = tm.search_term("doktor")
        assert len(results) == 1

    def test_search_with_domain(self):
        tm = TerminologyManager()
        tm.add_term("med", "test", {"tr": "test1"})
        tm.add_term("tech", "test", {"tr": "test2"})
        results = tm.search_term("test", domain="med")
        assert len(results) == 1

    def test_add_synonym(self):
        tm = TerminologyManager()
        tm.add_synonym("car", ["auto", "vehicle"])
        assert "auto" in tm.get_synonyms("car")
        assert "vehicle" in tm.get_synonyms("car")
        assert tm.synonym_count == 1

    def test_get_synonyms_empty(self):
        tm = TerminologyManager()
        assert tm.get_synonyms("nope") == []

    def test_preferred_term(self):
        tm = TerminologyManager()
        tm.set_preferred("colour", "color")
        assert tm.get_preferred("colour") == "color"
        assert tm.get_preferred("other") == "other"

    def test_custom_dict(self):
        tm = TerminologyManager()
        result = tm.create_custom_dict(
            "brands", {"FTRK": "FTRK Store"},
        )
        assert result["entries"] == 1
        assert (
            tm.lookup_custom("brands", "FTRK")
            == "FTRK Store"
        )
        assert tm.lookup_custom("brands", "x") is None
        assert tm.dict_count == 1

    def test_extract_terms(self):
        tm = TerminologyManager()
        tm.add_term("med", "surgery", {"tr": "ameliyat"})
        tm.add_term("med", "doctor", {"tr": "doktor"})
        found = tm.extract_terms(
            "The surgery was performed by a doctor",
            "med",
        )
        assert "surgery" in found
        assert "doctor" in found

    def test_get_glossary(self):
        tm = TerminologyManager()
        tm.add_term("med", "x", {"tr": "y"})
        glossary = tm.get_glossary("med")
        assert "x" in glossary

    def test_remove_term(self):
        tm = TerminologyManager()
        tm.add_term("med", "x", {"tr": "y"})
        assert tm.remove_term("med", "x")
        assert tm.total_terms == 0
        assert not tm.remove_term("med", "x")

    def test_glossary_count(self):
        tm = TerminologyManager()
        tm.add_term("med", "x", {"tr": "y"})
        tm.add_term("tech", "a", {"tr": "b"})
        assert tm.glossary_count == 2


# ── LocalizationQualityChecker Testleri ─────────────


class TestQualityChecker:
    """LocalizationQualityChecker testleri."""

    def test_init(self):
        qc = LocalizationQualityChecker()
        assert qc.check_count == 0

    def test_check_good_translation(self):
        qc = LocalizationQualityChecker()
        result = qc.check_translation(
            "Hello world",
            "Merhaba dünya",
        )
        assert result["score"] > 0.5
        assert len(result["issues"]) == 0

    def test_check_empty_translation(self):
        qc = LocalizationQualityChecker()
        result = qc.check_translation("Hello", "")
        assert result["score"] == 0.0
        assert "empty_translation" in result["issues"]

    def test_check_untranslated(self):
        qc = LocalizationQualityChecker()
        result = qc.check_translation("Hello", "Hello")
        assert "untranslated" in result["issues"]

    def test_check_placeholder_mismatch(self):
        qc = LocalizationQualityChecker()
        result = qc.check_translation(
            "Hello {name}",
            "Merhaba",
        )
        assert "placeholder_mismatch" in result["issues"]

    def test_check_placeholder_match(self):
        qc = LocalizationQualityChecker()
        result = qc.check_translation(
            "Hello {name}",
            "Merhaba {name}",
        )
        assert "placeholder_mismatch" not in result["issues"]

    def test_check_number_mismatch(self):
        qc = LocalizationQualityChecker()
        result = qc.check_translation(
            "Order 12345",
            "Sipariş",
        )
        assert "number_mismatch" in result["issues"]

    def test_check_consistency(self):
        qc = LocalizationQualityChecker()
        result = qc.check_consistency(
            {"en": "Save", "tr": "Kaydet", "de": "Speichern"},
            "save",
        )
        assert result["languages"] == 3
        assert result["consistent"]

    def test_check_missing(self):
        qc = LocalizationQualityChecker()
        messages = {
            "hello": {"en": "Hello", "tr": "Merhaba"},
            "bye": {"en": "Bye"},
        }
        result = qc.check_missing(
            messages, ["en", "tr"],
        )
        assert result["total_missing"] == 1
        assert "bye" in result["missing"]

    def test_check_missing_full_coverage(self):
        qc = LocalizationQualityChecker()
        messages = {
            "a": {"en": "A", "tr": "A"},
        }
        result = qc.check_missing(
            messages, ["en", "tr"],
        )
        assert result["coverage"] == 1.0

    def test_validate_format_date(self):
        qc = LocalizationQualityChecker()
        assert qc.validate_format(
            "2026-02-14", "date_iso",
        )
        assert not qc.validate_format(
            "14/02/2026", "date_iso",
        )

    def test_validate_format_email(self):
        qc = LocalizationQualityChecker()
        assert qc.validate_format(
            "test@example.com", "email",
        )

    def test_validate_format_unknown(self):
        qc = LocalizationQualityChecker()
        assert qc.validate_format("anything", "unknown")

    def test_quality_report(self):
        qc = LocalizationQualityChecker()
        qc.check_translation("Hello", "Merhaba")
        report = qc.get_quality_report()
        assert report["total_checks"] == 1
        assert report["avg_score"] > 0

    def test_quality_report_empty(self):
        qc = LocalizationQualityChecker()
        report = qc.get_quality_report()
        assert report["total_checks"] == 0

    def test_add_rule(self):
        qc = LocalizationQualityChecker()
        qc.add_quality_rule("max_len", {"max": 100})
        assert qc.rule_count == 1


# ── LocalizationOrchestrator Testleri ───────────────


class TestLocalizationOrchestrator:
    """LocalizationOrchestrator testleri."""

    def test_init(self):
        lo = LocalizationOrchestrator()
        assert lo.default_language == "en"
        assert "en" in lo.supported_languages

    def test_localize_basic(self):
        lo = LocalizationOrchestrator()
        result = lo.localize("test text")
        assert result["translated"]
        assert result["source_lang"]
        assert result["target_lang"] == "en"

    def test_localize_with_target(self):
        lo = LocalizationOrchestrator()
        result = lo.localize(
            "hello", target_lang="tr",
        )
        assert result["target_lang"] == "tr"

    def test_localize_with_user(self):
        lo = LocalizationOrchestrator()
        lo.set_user_language("u1", "tr")
        result = lo.localize("hello", user_id="u1")
        assert result["target_lang"] == "tr"

    def test_set_get_user_language(self):
        lo = LocalizationOrchestrator()
        lo.set_user_language("u1", "de")
        assert lo.get_user_language("u1") == "de"
        assert lo.get_user_language("u2") == "en"
        assert lo.user_count == 1

    def test_fallback_chain(self):
        lo = LocalizationOrchestrator()
        lo.catalog.add_message(
            "hello", {"en": "Hello", "de": "Hallo"},
        )
        lo.set_fallback_chain("tr", ["de", "en"])
        msg = lo.get_with_fallback("hello", "tr")
        assert msg == "Hallo"

    def test_fallback_to_default(self):
        lo = LocalizationOrchestrator()
        lo.catalog.add_message("hi", {"en": "Hi"})
        msg = lo.get_with_fallback("hi", "fr")
        assert msg == "Hi"

    def test_fallback_key_only(self):
        lo = LocalizationOrchestrator()
        msg = lo.get_with_fallback("missing", "tr")
        assert msg == "missing"

    def test_get_analytics(self):
        lo = LocalizationOrchestrator()
        lo.localize("test")
        analytics = lo.get_analytics()
        assert "supported_languages" in analytics
        assert "total_messages" in analytics
        assert "cache_hit_rate" in analytics

    def test_get_snapshot(self):
        lo = LocalizationOrchestrator()
        snap = lo.get_snapshot()
        assert isinstance(snap, LocalizationSnapshot)
        assert snap.supported_languages > 0

    def test_all_components_accessible(self):
        lo = LocalizationOrchestrator()
        assert lo.detector is not None
        assert lo.translator is not None
        assert lo.locale is not None
        assert lo.catalog is not None
        assert lo.culture is not None
        assert lo.content is not None
        assert lo.terminology is not None
        assert lo.quality is not None

    def test_localize_with_catalog(self):
        lo = LocalizationOrchestrator()
        lo.catalog.add_message(
            "welcome",
            {"en": "Welcome", "tr": "Hoşgeldiniz"},
        )
        result = lo.localize(
            "welcome", target_lang="tr",
        )
        assert result["translated"] == "Hoşgeldiniz"
        assert result["quality_score"] == 1.0


# ── Entegrasyon Testleri ────────────────────────────


class TestLocalizationIntegration:
    """Entegrasyon testleri."""

    def test_full_localization_pipeline(self):
        lo = LocalizationOrchestrator()
        # Terim ekle
        lo.terminology.add_term(
            "medical", "surgery",
            {"tr": "ameliyat", "de": "Operation"},
        )
        # Mesaj ekle
        lo.catalog.add_message(
            "appointment",
            {
                "en": "Your appointment is confirmed",
                "tr": "Randevunuz onaylandı",
            },
        )
        # Yerellestir
        result = lo.localize(
            "appointment", target_lang="tr",
        )
        assert "onaylandı" in result["translated"]

    def test_quality_with_translation(self):
        lo = LocalizationOrchestrator()
        lo.translator.add_to_memory(
            "hello", "merhaba",
            LanguageCode.EN, LanguageCode.TR,
        )
        lo.quality.check_translation(
            "hello", "merhaba",
        )
        report = lo.quality.get_quality_report()
        assert report["total_checks"] >= 1

    def test_cultural_with_content(self):
        lo = LocalizationOrchestrator()
        # Kulturel kontrol
        culture = lo.culture.adapt_communication(
            "Test mesajı", "ar",
        )
        assert culture["direction"] == "rtl"
        # Icerik uyarlama
        ui = lo.content.adapt_ui(["menu"], "ar")
        assert ui["is_rtl"]

    def test_locale_formatting(self):
        lo = LocalizationOrchestrator()
        num = lo.locale.format_number(
            1234.56, locale="tr",
        )
        assert "," in num  # TR ondalik
        curr = lo.locale.format_currency(
            99.99, locale="tr",
        )
        assert "₺" in curr

    def test_multi_user_preferences(self):
        lo = LocalizationOrchestrator()
        lo.set_user_language("u1", "tr")
        lo.set_user_language("u2", "de")
        lo.set_user_language("u3", "fr")
        lo.catalog.add_message(
            "hi",
            {"tr": "Merhaba", "de": "Hallo", "fr": "Bonjour"},
        )
        r1 = lo.localize("hi", user_id="u1")
        r2 = lo.localize("hi", user_id="u2")
        assert r1["translated"] == "Merhaba"
        assert r2["translated"] == "Hallo"
