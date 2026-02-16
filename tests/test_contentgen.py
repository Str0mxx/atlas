"""ATLAS Content & Copy Generator testleri.

CopyWriter, SEOOptimizer, MultiLangContent,
ABTestCopy, BrandVoiceManager, ContentCalendar,
PlatformAdapter, ContentPerformanceAnalyzer,
ContentGenOrchestrator.
"""

import pytest

from app.core.contentgen.copy_writer import (
    CopyWriter,
)
from app.core.contentgen.seo_optimizer import (
    SEOOptimizer,
)
from app.core.contentgen.multilang_content import (
    MultiLangContent,
)
from app.core.contentgen.ab_test_copy import (
    ABTestCopy,
)
from app.core.contentgen.brand_voice_manager import (
    BrandVoiceManager,
)
from app.core.contentgen.content_calendar import (
    ContentCalendar,
)
from app.core.contentgen.platform_adapter import (
    PlatformAdapter,
)
from app.core.contentgen.performance_analyzer import (
    ContentPerformanceAnalyzer,
)
from app.core.contentgen.contentgen_orchestrator import (
    ContentGenOrchestrator,
)


# ── CopyWriter ──────────────────────────


class TestCopyWriterInit:
    def test_init(self):
        w = CopyWriter()
        assert w.copy_count == 0
        assert w.headline_count == 0


class TestWriteAdCopy:
    def test_basic(self):
        w = CopyWriter()
        r = w.write_ad_copy(
            product="Atlas AI",
            benefit="saves time",
        )
        assert r["created"] is True
        assert "Atlas AI" in r["text"]
        assert w.copy_count == 1

    def test_no_benefit(self):
        w = CopyWriter()
        r = w.write_ad_copy(
            product="Atlas AI",
        )
        assert r["created"] is True
        assert r["char_count"] > 0

    def test_max_length(self):
        w = CopyWriter()
        r = w.write_ad_copy(
            product="Atlas AI",
            benefit="saves time",
            max_length=20,
        )
        assert r["char_count"] <= 20


class TestCreateHeadline:
    def test_direct(self):
        w = CopyWriter()
        r = w.create_headline(
            product="Atlas", benefit="speed",
        )
        assert r["style"] == "direct"
        assert w.headline_count == 1

    def test_question(self):
        w = CopyWriter()
        r = w.create_headline(
            product="Atlas",
            benefit="speed",
            style="question",
        )
        assert "?" in r["headline"]

    def test_how_to(self):
        w = CopyWriter()
        r = w.create_headline(
            product="Atlas",
            style="how_to",
        )
        assert "How" in r["headline"]

    def test_max_length(self):
        w = CopyWriter()
        r = w.create_headline(
            product="Atlas",
            max_length=10,
        )
        assert r["char_count"] <= 10


class TestWriteDescription:
    def test_with_features(self):
        w = CopyWriter()
        r = w.write_description(
            product="Atlas",
            features=["fast", "smart"],
        )
        assert r["features_used"] == 2
        assert "fast" in r["description"]

    def test_no_features(self):
        w = CopyWriter()
        r = w.write_description(
            product="Atlas",
        )
        assert r["features_used"] == 0


class TestGenerateCTA:
    def test_buy(self):
        w = CopyWriter()
        r = w.generate_cta(action="buy")
        assert r["cta"] == "Buy Now"

    def test_urgency(self):
        w = CopyWriter()
        r = w.generate_cta(
            action="buy", urgency=True,
        )
        assert "Limited" in r["cta"]

    def test_unknown_action(self):
        w = CopyWriter()
        r = w.generate_cta(action="xyz")
        assert r["cta"] == "Learn More"


class TestCreateVariations:
    def test_rephrase(self):
        w = CopyWriter()
        r = w.create_variations(
            "Hello World", count=3,
        )
        assert r["count"] == 3

    def test_shorten(self):
        w = CopyWriter()
        r = w.create_variations(
            "one two three four",
            variation_type="shorten",
        )
        assert r["count"] >= 1

    def test_extend(self):
        w = CopyWriter()
        r = w.create_variations(
            "Hello", count=2,
            variation_type="extend",
        )
        assert r["count"] == 2


class TestGetCopy:
    def test_exists(self):
        w = CopyWriter()
        r = w.write_ad_copy(product="T")
        c = w.get_copy(r["copy_id"])
        assert c is not None

    def test_missing(self):
        w = CopyWriter()
        assert w.get_copy("x") is None


# ── SEOOptimizer ────────────────────────


class TestSEOInit:
    def test_init(self):
        s = SEOOptimizer()
        assert s.optimization_count == 0
        assert s.score_count == 0


class TestIntegrateKeywords:
    def test_present(self):
        s = SEOOptimizer()
        r = s.integrate_keywords(
            "Atlas AI is fast and smart",
            keywords=["fast", "smart"],
        )
        assert r["present_count"] == 2
        assert r["missing_count"] == 0

    def test_missing(self):
        s = SEOOptimizer()
        r = s.integrate_keywords(
            "Hello world",
            keywords=["atlas"],
        )
        assert r["missing_count"] == 1

    def test_empty(self):
        s = SEOOptimizer()
        r = s.integrate_keywords("text")
        assert r["present_count"] == 0


class TestGenerateMetaTags:
    def test_basic(self):
        s = SEOOptimizer()
        r = s.generate_meta_tags(
            title="Atlas AI",
            description="Best AI tool",
            keywords=["ai", "automation"],
        )
        assert r["meta_title"] == "Atlas AI"
        assert r["issue_count"] == 0

    def test_long_title(self):
        s = SEOOptimizer()
        r = s.generate_meta_tags(
            title="A" * 80,
        )
        assert len(r["meta_title"]) <= 60
        assert r["issue_count"] >= 1

    def test_no_keywords(self):
        s = SEOOptimizer()
        r = s.generate_meta_tags(title="T")
        assert "No keywords" in (
            r["issues"][0]
        )


class TestCheckReadability:
    def test_easy(self):
        s = SEOOptimizer()
        r = s.check_readability(
            "This is a simple text. "
            "It has short sentences. "
            "Easy to read. Very clear. "
            "Good for users. " * 5,
        )
        assert r["level"] == "easy"

    def test_word_count(self):
        s = SEOOptimizer()
        r = s.check_readability(
            "Hello world here.",
        )
        assert r["word_count"] == 3


class TestOptimizeStructure:
    def test_all_present(self):
        s = SEOOptimizer()
        r = s.optimize_structure(
            "x " * 400,
            has_headings=True,
            has_lists=True,
            has_images=True,
        )
        assert r["structure_score"] == 100

    def test_nothing(self):
        s = SEOOptimizer()
        r = s.optimize_structure("short")
        assert len(r["suggestions"]) >= 3


class TestCalculateScore:
    def test_high(self):
        s = SEOOptimizer()
        text = "atlas ai " * 200
        r = s.calculate_score(
            text,
            keywords=["atlas"],
            has_meta=True,
            has_headings=True,
        )
        assert r["seo_score"] >= 60
        assert s.score_count == 1

    def test_low(self):
        s = SEOOptimizer()
        r = s.calculate_score("short")
        assert r["level"] == "poor"


# ── MultiLangContent ────────────────────


class TestMultiLangInit:
    def test_init(self):
        m = MultiLangContent()
        assert m.translation_count == 0
        assert m.localization_count == 0


class TestTranslate:
    def test_basic(self):
        m = MultiLangContent()
        r = m.translate(
            "Hello", target_lang="tr",
        )
        assert r["translated_ok"] is True
        assert "[tr]" in r["translated"]
        assert m.translation_count == 1

    def test_custom_source(self):
        m = MultiLangContent()
        r = m.translate(
            "Hallo", source_lang="de",
            target_lang="en",
        )
        assert r["source_lang"] == "de"


class TestLocalize:
    def test_turkish(self):
        m = MultiLangContent()
        r = m.localize(
            "Hello", target_lang="tr",
        )
        assert r["adjustment_count"] >= 1
        assert m.localization_count == 1

    def test_arabic(self):
        m = MultiLangContent()
        r = m.localize(
            "Hello", target_lang="ar",
        )
        assert "RTL" in str(
            r["adjustments"],
        )

    def test_with_region(self):
        m = MultiLangContent()
        r = m.localize(
            "Hello", target_lang="en",
            region="US",
        )
        assert r["adjustment_count"] >= 1


class TestAdaptCultural:
    def test_turkish(self):
        m = MultiLangContent()
        r = m.adapt_cultural(
            "Buy now", target_culture="tr",
        )
        assert r["adapted"] is True
        assert r["consideration_count"] >= 1

    def test_unknown(self):
        m = MultiLangContent()
        r = m.adapt_cultural(
            "text", target_culture="xx",
        )
        assert r["adapted"] is True


class TestPreserveTone:
    def test_preserved(self):
        m = MultiLangContent()
        r = m.preserve_tone(
            "Hello world",
            "[tr] Hello world",
        )
        assert r["tone_preserved"] is True

    def test_markers(self):
        m = MultiLangContent()
        r = m.preserve_tone(
            "Please help now",
            "[tr] Please help now",
            tone="professional",
        )
        assert r["original_markers"] >= 1


class TestQualityCheck:
    def test_good(self):
        m = MultiLangContent()
        r = m.quality_check(
            "Hello world",
            "[tr] Merhaba dunya",
        )
        assert r["passed"] is True
        assert m._stats["quality_checks"] == 1

    def test_empty_translation(self):
        m = MultiLangContent()
        r = m.quality_check(
            "Hello", "   ",
        )
        assert r["issue_count"] >= 1

    def test_too_long(self):
        m = MultiLangContent()
        r = m.quality_check(
            "Hi", "X" * 500,
        )
        assert r["issue_count"] >= 1


class TestSupportedLanguages:
    def test_list(self):
        m = MultiLangContent()
        langs = m.get_supported_languages()
        assert "en" in langs
        assert "tr" in langs


# ── ABTestCopy ──────────────────────────


class TestABTestInit:
    def test_init(self):
        a = ABTestCopy()
        assert a.test_count == 0
        assert a.winner_count == 0


class TestGenerateABVariations:
    def test_tone(self):
        a = ABTestCopy()
        r = a.generate_variations(
            "Buy now", variation_count=2,
        )
        assert r["count"] >= 3

    def test_cta(self):
        a = ABTestCopy()
        r = a.generate_variations(
            "Shop", variation_type="cta",
        )
        assert r["count"] >= 1

    def test_length(self):
        a = ABTestCopy()
        r = a.generate_variations(
            "one two three four",
            variation_type="length",
        )
        assert r["count"] >= 1


class TestCreateHypothesis:
    def test_basic(self):
        a = ABTestCopy()
        r = a.create_hypothesis(
            "Test 1", "Buy now",
            "Shop today",
        )
        assert r["created"] is True
        assert a.test_count == 1

    def test_custom_hypothesis(self):
        a = ABTestCopy()
        r = a.create_hypothesis(
            "Test 1", "A", "B",
            hypothesis="B is better",
        )
        assert r["hypothesis"] == (
            "B is better"
        )


class TestTrackABPerformance:
    def test_basic(self):
        a = ABTestCopy()
        h = a.create_hypothesis(
            "T", "A", "B",
        )
        r = a.track_performance(
            h["test_id"], variant="a",
            impressions=1000, clicks=50,
        )
        assert r["tracked"] is True
        assert r["click_rate"] == 5.0

    def test_missing(self):
        a = ABTestCopy()
        r = a.track_performance("none")
        assert r["tracked"] is False


class TestSelectWinner:
    def test_winner(self):
        a = ABTestCopy()
        h = a.create_hypothesis(
            "T", "A", "B",
        )
        tid = h["test_id"]
        a.track_performance(
            tid, "a",
            impressions=1000, clicks=30,
        )
        a.track_performance(
            tid, "b",
            impressions=1000, clicks=50,
        )
        r = a.select_winner(tid)
        assert r["winner"] == "b"
        assert a.winner_count == 1

    def test_insufficient(self):
        a = ABTestCopy()
        h = a.create_hypothesis(
            "T", "A", "B",
        )
        r = a.select_winner(h["test_id"])
        assert r["winner"] is None

    def test_missing(self):
        a = ABTestCopy()
        r = a.select_winner("none")
        assert r["winner"] is None


class TestExtractLearning:
    def test_basic(self):
        a = ABTestCopy()
        h = a.create_hypothesis(
            "T", "A", "B",
        )
        tid = h["test_id"]
        a.track_performance(
            tid, "a",
            impressions=1000, clicks=30,
        )
        a.track_performance(
            tid, "b",
            impressions=1000, clicks=50,
        )
        r = a.extract_learning(tid)
        assert r["count"] >= 1

    def test_missing(self):
        a = ABTestCopy()
        r = a.extract_learning("none")
        assert r["learnings"] == []


# ── BrandVoiceManager ──────────────────


class TestBrandVoiceInit:
    def test_init(self):
        b = BrandVoiceManager()
        assert b.voice_count == 0
        assert b.check_count == 0


class TestDefineVoice:
    def test_basic(self):
        b = BrandVoiceManager()
        r = b.define_voice(
            brand_name="Atlas",
            tone="professional",
            personality=["smart", "reliable"],
        )
        assert r["defined"] is True
        assert r["personality_count"] == 2
        assert b.voice_count == 1


class TestCheckConsistency:
    def test_consistent(self):
        b = BrandVoiceManager()
        r = b.define_voice(
            "Atlas",
            do_words=["innovative"],
            dont_words=["cheap"],
        )
        vid = r["voice_id"]
        c = b.check_consistency(
            vid, "Atlas is innovative",
        )
        assert c["consistent"] is True
        assert b.check_count == 1

    def test_inconsistent(self):
        b = BrandVoiceManager()
        r = b.define_voice(
            "Atlas",
            dont_words=[
                "cheap", "bad", "ugly",
                "terrible",
            ],
        )
        vid = r["voice_id"]
        c = b.check_consistency(
            vid,
            "This is cheap bad ugly terrible",
        )
        assert c["consistent"] is False

    def test_missing(self):
        b = BrandVoiceManager()
        c = b.check_consistency(
            "none", "text",
        )
        assert c["consistent"] is False


class TestGetToneGuidelines:
    def test_professional(self):
        b = BrandVoiceManager()
        r = b.define_voice(
            "Atlas", tone="professional",
        )
        g = b.get_tone_guidelines(
            r["voice_id"],
        )
        assert g["found"] is True
        assert len(g["guidelines"]) >= 3

    def test_casual(self):
        b = BrandVoiceManager()
        r = b.define_voice(
            "Atlas", tone="casual",
        )
        g = b.get_tone_guidelines(
            r["voice_id"],
        )
        assert "conversational" in str(
            g["guidelines"],
        ).lower()

    def test_missing(self):
        b = BrandVoiceManager()
        g = b.get_tone_guidelines("none")
        assert g["found"] is False


class TestEnforceStyle:
    def test_remove_words(self):
        b = BrandVoiceManager()
        r = b.define_voice(
            "Atlas",
            dont_words=["cheap"],
        )
        vid = r["voice_id"]
        e = b.enforce_style(
            vid, "This is cheap stuff",
        )
        assert e["enforced"] is True
        assert e["change_count"] >= 1

    def test_missing(self):
        b = BrandVoiceManager()
        e = b.enforce_style("none", "text")
        assert e["enforced"] is False


class TestTrain:
    def test_basic(self):
        b = BrandVoiceManager()
        r = b.define_voice("Atlas")
        vid = r["voice_id"]
        t = b.train(
            vid,
            examples=[
                "Atlas is innovative",
                "Atlas delivers results",
            ],
        )
        assert t["trained"] is True
        assert t["examples_used"] == 2

    def test_missing(self):
        b = BrandVoiceManager()
        t = b.train("none")
        assert t["trained"] is False


# ── ContentCalendar ─────────────────────


class TestCalendarInit:
    def test_init(self):
        c = ContentCalendar()
        assert c.entry_count == 0
        assert c.topic_count == 0


class TestSchedulePublish:
    def test_basic(self):
        c = ContentCalendar()
        r = c.schedule_publish(
            title="Blog Post",
            platform="website",
            scheduled_date="2026-03-01",
        )
        assert r["scheduled"] is True
        assert c.entry_count == 1

    def test_with_assignee(self):
        c = ContentCalendar()
        r = c.schedule_publish(
            title="Post",
            assignee="marketing",
        )
        assert r["scheduled"] is True


class TestPlanTopic:
    def test_basic(self):
        c = ContentCalendar()
        r = c.plan_topic(
            topic="AI Trends",
            platforms=["website", "linkedin"],
        )
        assert r["planned"] is True
        assert r["platform_count"] == 2
        assert c.topic_count == 1


class TestCoordinateChannels:
    def test_basic(self):
        c = ContentCalendar()
        e = c.schedule_publish(
            title="Post",
            scheduled_date="2026-03-01",
        )
        r = c.coordinate_channels(
            e["entry_id"],
            channels=["facebook", "twitter"],
        )
        assert r["coordinated"] is True
        assert r["channel_count"] == 2

    def test_missing(self):
        c = ContentCalendar()
        r = c.coordinate_channels("none")
        assert r["coordinated"] is False


class TestTrackCalendarDeadline:
    def test_basic(self):
        c = ContentCalendar()
        e = c.schedule_publish(
            title="Post",
            scheduled_date="2026-03-01",
        )
        r = c.track_deadline(e["entry_id"])
        assert r["tracked"] is True

    def test_missing(self):
        c = ContentCalendar()
        r = c.track_deadline("none")
        assert r["tracked"] is False


class TestDetectGaps:
    def test_with_gaps(self):
        c = ContentCalendar()
        c.schedule_publish(
            title="Post",
            platform="website",
            scheduled_date="2026-03-01",
        )
        r = c.detect_gaps(
            platform="website",
            date_range=[
                "2026-03-01",
                "2026-03-02",
                "2026-03-03",
            ],
        )
        assert r["gap_count"] == 2

    def test_no_range(self):
        c = ContentCalendar()
        r = c.detect_gaps()
        assert r["coverage_pct"] == 100.0


class TestListEntries:
    def test_filter_platform(self):
        c = ContentCalendar()
        c.schedule_publish(
            title="A", platform="website",
        )
        c.schedule_publish(
            title="B", platform="facebook",
        )
        lst = c.list_entries(
            platform="website",
        )
        assert len(lst) == 1

    def test_all(self):
        c = ContentCalendar()
        c.schedule_publish(title="A")
        lst = c.list_entries()
        assert len(lst) == 1


# ── PlatformAdapter ─────────────────────


class TestPlatformAdapterInit:
    def test_init(self):
        p = PlatformAdapter()
        assert p.adaptation_count == 0
        assert p.preview_count == 0


class TestAdaptFormat:
    def test_within_limit(self):
        p = PlatformAdapter()
        r = p.adapt_format(
            "Short text",
            platform="twitter",
        )
        assert r["within_limit"] is True
        assert r["truncated"] is False
        assert p.adaptation_count == 1

    def test_truncated(self):
        p = PlatformAdapter()
        r = p.adapt_format(
            "X" * 500,
            platform="twitter",
        )
        assert r["truncated"] is True
        assert r["adapted_length"] <= 280


class TestOptimizeLength:
    def test_too_long(self):
        p = PlatformAdapter()
        r = p.optimize_length(
            "X" * 500,
            platform="twitter",
        )
        assert len(r["suggestions"]) >= 1

    def test_too_short(self):
        p = PlatformAdapter()
        r = p.optimize_length(
            "Hi", platform="linkedin",
        )
        assert r["optimal"] is False

    def test_optimal(self):
        p = PlatformAdapter()
        r = p.optimize_length(
            "X" * 200,
            platform="twitter",
        )
        assert r["optimal"] is True


class TestGetFeatures:
    def test_google_ads(self):
        p = PlatformAdapter()
        r = p.get_features("google_ads")
        assert r["supported"] is True
        assert r["feature_count"] >= 1

    def test_unknown(self):
        p = PlatformAdapter()
        r = p.get_features("unknown")
        assert r["supported"] is False


class TestGetBestPractices:
    def test_known(self):
        p = PlatformAdapter()
        r = p.get_best_practices(
            "instagram",
        )
        assert r["count"] >= 3

    def test_unknown(self):
        p = PlatformAdapter()
        r = p.get_best_practices("xyz")
        assert r["count"] >= 3


class TestGeneratePreview:
    def test_basic(self):
        p = PlatformAdapter()
        r = p.generate_preview(
            "Buy our product",
            platform="facebook",
            headline="Great Deal",
        )
        assert r["preview_generated"] is True
        assert p.preview_count == 1


class TestSupportedPlatforms:
    def test_list(self):
        p = PlatformAdapter()
        lst = p.get_supported_platforms()
        assert "google_ads" in lst
        assert "twitter" in lst


# ── ContentPerformanceAnalyzer ──────────


class TestPerfAnalyzerInit:
    def test_init(self):
        p = ContentPerformanceAnalyzer()
        assert p.analysis_count == 0
        assert p.recommendation_count == 0


class TestTrackEngagement:
    def test_excellent(self):
        p = ContentPerformanceAnalyzer()
        r = p.track_engagement(
            "c1", views=1000,
            likes=30, shares=20,
            comments=10,
        )
        assert r["tracked"] is True
        assert r["level"] == "excellent"

    def test_poor(self):
        p = ContentPerformanceAnalyzer()
        r = p.track_engagement(
            "c1", views=10000,
            likes=1,
        )
        assert r["level"] == "poor"


class TestTrackConversion:
    def test_basic(self):
        p = ContentPerformanceAnalyzer()
        r = p.track_conversion(
            "c1",
            impressions=1000,
            clicks=100,
            conversions=10,
        )
        assert r["tracked"] is True
        assert r["ctr"] == 10.0
        assert r["conversion_rate"] == 10.0


class TestCompareContent:
    def test_basic(self):
        p = ContentPerformanceAnalyzer()
        p.track_engagement(
            "a", views=1000, likes=50,
        )
        p.track_engagement(
            "b", views=1000, likes=100,
        )
        r = p.compare_content("a", "b")
        assert r["compared"] is True
        assert r["winner"] == "b"

    def test_missing(self):
        p = ContentPerformanceAnalyzer()
        r = p.compare_content("a", "b")
        assert r["compared"] is False


class TestDetectContentTrends:
    def test_improving(self):
        p = ContentPerformanceAnalyzer()
        p.track_engagement(
            "c1", views=1000, likes=10,
        )
        p.track_engagement(
            "c2", views=1000, likes=50,
        )
        r = p.detect_trends(["c1", "c2"])
        assert r["trend"] == "improving"

    def test_insufficient(self):
        p = ContentPerformanceAnalyzer()
        r = p.detect_trends()
        assert r["trend"] == (
            "insufficient_data"
        )


class TestContentRecommend:
    def test_poor_content(self):
        p = ContentPerformanceAnalyzer()
        p.track_engagement(
            "c1", views=50, likes=0,
        )
        r = p.recommend("c1")
        assert r["count"] >= 2
        assert p.recommendation_count == 1

    def test_no_metrics(self):
        p = ContentPerformanceAnalyzer()
        r = p.recommend("none")
        assert "tracking" in str(
            r["recommendations"],
        ).lower()

    def test_excellent(self):
        p = ContentPerformanceAnalyzer()
        p.track_engagement(
            "c1", views=1000,
            likes=30, shares=20,
            comments=10,
        )
        r = p.recommend("c1")
        assert "Replicate" in str(
            r["recommendations"],
        )


# ── ContentGenOrchestrator ──────────────


class TestOrchInit:
    def test_init(self):
        o = ContentGenOrchestrator()
        assert o.content_count == 0
        assert o.pipeline_count == 0


class TestCreateContentOrch:
    def test_basic(self):
        o = ContentGenOrchestrator()
        r = o.create_content(
            product="Atlas AI",
            platform="facebook",
        )
        assert r["created"] is True
        assert o.content_count == 1

    def test_with_keywords(self):
        o = ContentGenOrchestrator()
        r = o.create_content(
            product="Atlas AI",
            keywords=["ai", "automation"],
        )
        assert r["created"] is True


class TestRunFullPipelineOrch:
    def test_basic(self):
        o = ContentGenOrchestrator()
        r = o.run_full_pipeline(
            product="Atlas AI",
            benefit="saves time",
            platforms=["website", "facebook"],
        )
        assert r["pipeline_complete"] is True
        assert r["translated"] is False
        assert o.pipeline_count == 1

    def test_with_translation(self):
        o = ContentGenOrchestrator()
        r = o.run_full_pipeline(
            product="Atlas",
            language="tr",
        )
        assert r["translated"] is True


class TestMultiPlatformPublish:
    def test_basic(self):
        o = ContentGenOrchestrator()
        r = o.multi_platform_publish(
            product="Atlas",
            platforms=["website", "facebook"],
        )
        assert r["published"] is True
        assert r["platform_count"] == 2


class TestOrchAnalytics:
    def test_basic(self):
        o = ContentGenOrchestrator()
        o.create_content(product="T")
        a = o.get_analytics()
        assert a["content_created"] == 1
        assert a["copies_written"] >= 1

    def test_after_pipeline(self):
        o = ContentGenOrchestrator()
        o.run_full_pipeline(product="T")
        a = o.get_analytics()
        assert a["pipelines_run"] == 1


# ── Config ──────────────────────────────


class TestContentGenConfig:
    def test_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.contentgen_enabled is True
        assert s.default_language == "en"
        assert s.seo_optimization is True
        assert s.brand_voice_check is True
        assert s.ab_test_auto is True


# ── __init__ imports ────────────────────


class TestContentGenImports:
    def test_all_imports(self):
        from app.core.contentgen import (
            ABTestCopy,
            BrandVoiceManager,
            ContentCalendar,
            ContentGenOrchestrator,
            ContentPerformanceAnalyzer,
            CopyWriter,
            MultiLangContent,
            PlatformAdapter,
            SEOOptimizer,
        )
        assert ABTestCopy is not None
        assert BrandVoiceManager is not None
        assert ContentCalendar is not None
        assert ContentGenOrchestrator is not None
        assert ContentPerformanceAnalyzer is not None
        assert CopyWriter is not None
        assert MultiLangContent is not None
        assert PlatformAdapter is not None
        assert SEOOptimizer is not None
