"""ATLAS Deep Research Engine testleri.

Çoklu kaynak tarama, sorgu genişletme,
kaynak sıralama, bilgi çıkarma,
çapraz doğrulama, sentez, sürekli takip,
raporlama, orkestrasyon testleri.
"""

from app.models.research_engine_models import (
    SourceType,
    CredibilityLevel,
    ResearchStatus,
    ReportFormat,
    ValidationResult,
    TrackingFrequency,
    ResearchRecord,
    SourceRecord,
    FactRecord,
    ResearchSnapshot,
)
from app.core.research.multi_source_crawler import (
    MultiSourceCrawler,
)
from app.core.research.query_expander import (
    QueryExpander,
)
from app.core.research.source_ranker import (
    SourceRanker,
)
from app.core.research.information_extractor import (
    InformationExtractor,
)
from app.core.research.cross_validator import (
    CrossValidator,
)
from app.core.research.research_synthesizer import (
    ResearchSynthesizer,
)
from app.core.research.continuous_tracker import (
    ContinuousTracker,
)
from app.core.research.research_reporter import (
    ResearchReporter,
)
from app.core.research.research_orchestrator import (
    ResearchOrchestrator,
)


# ========== Model Testleri ==========


class TestResearchEngineModels:
    """Model testleri."""

    def test_source_type_enum(self):
        assert SourceType.web == "web"
        assert SourceType.academic == "academic"
        assert SourceType.news == "news"
        assert SourceType.social == "social"
        assert SourceType.database == "database"
        assert SourceType.api == "api"

    def test_credibility_level_enum(self):
        assert CredibilityLevel.authoritative == "authoritative"
        assert CredibilityLevel.high == "high"
        assert CredibilityLevel.moderate == "moderate"
        assert CredibilityLevel.low == "low"
        assert CredibilityLevel.unknown == "unknown"
        assert CredibilityLevel.unreliable == "unreliable"

    def test_research_status_enum(self):
        assert ResearchStatus.queued == "queued"
        assert ResearchStatus.crawling == "crawling"
        assert ResearchStatus.extracting == "extracting"
        assert ResearchStatus.validating == "validating"
        assert ResearchStatus.synthesizing == "synthesizing"
        assert ResearchStatus.completed == "completed"

    def test_report_format_enum(self):
        assert ReportFormat.markdown == "markdown"
        assert ReportFormat.html == "html"
        assert ReportFormat.json == "json"
        assert ReportFormat.pdf == "pdf"
        assert ReportFormat.text == "text"
        assert ReportFormat.executive == "executive"

    def test_validation_result_enum(self):
        assert ValidationResult.verified == "verified"
        assert ValidationResult.likely_true == "likely_true"
        assert ValidationResult.uncertain == "uncertain"
        assert ValidationResult.contradicted == "contradicted"
        assert ValidationResult.unverifiable == "unverifiable"
        assert ValidationResult.false == "false"

    def test_tracking_frequency_enum(self):
        assert TrackingFrequency.realtime == "realtime"
        assert TrackingFrequency.hourly == "hourly"
        assert TrackingFrequency.daily == "daily"
        assert TrackingFrequency.weekly == "weekly"
        assert TrackingFrequency.monthly == "monthly"
        assert TrackingFrequency.on_change == "on_change"

    def test_research_record_model(self):
        record = ResearchRecord(
            query="test query",
            status=ResearchStatus.crawling,
        )
        assert record.query == "test query"
        assert record.status == ResearchStatus.crawling
        assert record.research_id
        assert record.created_at

    def test_source_record_model(self):
        record = SourceRecord(
            url="https://example.com",
            source_type=SourceType.academic,
            credibility=CredibilityLevel.high,
        )
        assert record.url == "https://example.com"
        assert record.source_type == SourceType.academic
        assert record.credibility == CredibilityLevel.high

    def test_fact_record_model(self):
        record = FactRecord(
            content="Some fact",
            source_count=3,
            validation=ValidationResult.verified,
        )
        assert record.content == "Some fact"
        assert record.source_count == 3
        assert record.validation == ValidationResult.verified

    def test_research_snapshot_model(self):
        snap = ResearchSnapshot(
            active_research=2,
            total_sources=15,
        )
        assert snap.active_research == 2
        assert snap.total_sources == 15
        assert snap.snapshot_id


# ========== MultiSourceCrawler Testleri ==========


class TestMultiSourceCrawler:
    """Çoklu kaynak tarayıcı testleri."""

    def test_init(self):
        crawler = MultiSourceCrawler()
        assert crawler.crawl_count == 0
        assert crawler.source_count == 0

    def test_crawl_basic(self):
        crawler = MultiSourceCrawler()
        result = crawler.crawl(
            query="artificial intelligence",
        )
        assert result["results_count"] > 0
        assert result["query"] == "artificial intelligence"
        assert crawler.crawl_count == 1

    def test_crawl_specific_types(self):
        crawler = MultiSourceCrawler()
        result = crawler.crawl(
            query="test",
            source_types=["web", "news"],
        )
        assert result["source_types"] == ["web", "news"]
        assert result["results_count"] > 0

    def test_crawl_max_results(self):
        crawler = MultiSourceCrawler()
        result = crawler.crawl(
            query="test", max_results=3,
        )
        assert len(result["results"]) <= 3

    def test_set_rate_limit(self):
        crawler = MultiSourceCrawler()
        result = crawler.set_rate_limit(
            source_type="web",
            max_requests=5,
            window=60,
        )
        assert result["set"] is True

    def test_retry_failed(self):
        crawler = MultiSourceCrawler()
        result = crawler.retry_failed("crawl_1")
        assert result["retried"] is True

    def test_extract_content(self):
        crawler = MultiSourceCrawler()
        result = crawler.extract_content("src_1")
        assert result["extracted"] is True
        assert result["word_count"] > 0

    def test_get_results(self):
        crawler = MultiSourceCrawler()
        crawler.crawl(query="test1")
        crawler.crawl(query="test2")
        results = crawler.get_results()
        assert len(results) == 2

    def test_content_count(self):
        crawler = MultiSourceCrawler()
        crawler.crawl(query="test")
        assert crawler.content_count > 0


# ========== QueryExpander Testleri ==========


class TestQueryExpander:
    """Sorgu genişletici testleri."""

    def test_init(self):
        expander = QueryExpander()
        assert expander.expansion_count == 0

    def test_expand_basic(self):
        expander = QueryExpander()
        result = expander.expand("buy cheap phone")
        assert result["original_query"] == "buy cheap phone"
        assert result["total_queries"] > 1
        assert expander.expansion_count == 1

    def test_expand_synonyms(self):
        expander = QueryExpander()
        result = expander.expand(
            "buy good product",
            include_questions=False,
            include_variants=False,
        )
        # "buy" ve "good" eşanlamlıları olmalı
        assert len(result["synonyms_used"]) > 0
        assert result["total_queries"] > 1

    def test_expand_questions(self):
        expander = QueryExpander()
        result = expander.expand(
            "machine learning",
            include_synonyms=False,
            include_variants=False,
        )
        assert len(result["questions"]) > 0
        assert expander.question_count > 0

    def test_expand_variants(self):
        expander = QueryExpander()
        result = expander.expand(
            "deep learning algorithms",
            include_synonyms=False,
            include_questions=False,
        )
        assert len(result["variants"]) > 0

    def test_add_synonym(self):
        expander = QueryExpander()
        result = expander.add_synonym(
            "car", ["vehicle", "automobile"],
        )
        assert result["added"] is True
        assert len(result["synonyms"]) == 2

    def test_add_related_terms(self):
        expander = QueryExpander()
        result = expander.add_related_terms(
            "ai", ["ml", "deep learning", "neural"],
        )
        assert result["added"] is True

    def test_broaden_scope(self):
        expander = QueryExpander()
        result = expander.broaden_scope(
            "electric car prices",
        )
        assert result["broadened"] is True
        assert len(result["broader_queries"]) > 0

    def test_broaden_with_related(self):
        expander = QueryExpander()
        expander.add_related_terms(
            "electric", ["ev", "hybrid", "battery"],
        )
        result = expander.broaden_scope(
            "electric vehicles",
        )
        assert result["broadened"] is True

    def test_get_expansions(self):
        expander = QueryExpander()
        expander.expand("test1")
        expander.expand("test2")
        expansions = expander.get_expansions()
        assert len(expansions) == 2


# ========== SourceRanker Testleri ==========


class TestSourceRanker:
    """Kaynak sıralayıcı testleri."""

    def test_init(self):
        ranker = SourceRanker()
        assert ranker.ranked_count == 0

    def test_rank_basic(self):
        ranker = SourceRanker()
        sources = [
            {"url": "https://example.com/a", "snippet": "info"},
            {"url": "https://example.edu/b", "snippet": "data"},
            {"url": "https://example.gov/c", "snippet": "official"},
        ]
        ranked = ranker.rank(sources)
        assert len(ranked) > 0
        # .gov en üstte olmalı
        assert ranked[0]["credibility_score"] >= ranked[-1]["credibility_score"]

    def test_rank_filtering(self):
        ranker = SourceRanker(min_credibility=0.8)
        sources = [
            {"url": "https://x.com/a", "snippet": "low"},
            {"url": "https://x.gov/b", "snippet": "high"},
        ]
        ranked = ranker.rank(sources)
        # Düşük güvenilirlikli filtrelenmeli
        assert ranker.filtered_count >= 0

    def test_assess_authority(self):
        ranker = SourceRanker()
        result = ranker.assess_authority(
            url="https://mit.edu/research",
            author="Dr. Smith",
            citations=150,
        )
        assert result["authority_score"] > 0.5

    def test_assess_authority_no_citations(self):
        ranker = SourceRanker()
        result = ranker.assess_authority(
            url="https://blog.com/post",
        )
        assert "authority_score" in result

    def test_detect_bias(self):
        ranker = SourceRanker()
        sources = [
            {
                "url": "https://x.com/a",
                "snippet": "Everyone obviously knows this is always true",
            },
        ]
        ranked = ranker.rank(sources)
        # Önyargı tespit edilmeli
        assert ranker.bias_count >= 1

    def test_add_bias_pattern(self):
        ranker = SourceRanker()
        result = ranker.add_bias_pattern(
            name="sponsored",
            keywords=["sponsored", "ad", "paid"],
        )
        assert result["added"] is True

    def test_set_domain_score(self):
        ranker = SourceRanker()
        result = ranker.set_domain_score("wiki", 0.65)
        assert result["set"] is True

    def test_assess_freshness(self):
        ranker = SourceRanker()
        r1 = ranker.assess_freshness(age_hours=0.5)
        assert r1["freshness_score"] == 1.0
        r2 = ranker.assess_freshness(age_hours=100)
        assert r2["freshness_score"] == 0.7
        r3 = ranker.assess_freshness(age_hours=10000)
        assert r3["freshness_score"] == 0.1

    def test_get_rankings(self):
        ranker = SourceRanker()
        ranker.rank([{"url": "https://x.com/a", "snippet": "x"}])
        rankings = ranker.get_rankings()
        assert len(rankings) == 1

    def test_credibility_levels(self):
        ranker = SourceRanker(min_credibility=0.0)
        sources = [
            {"url": "https://x.gov/a", "snippet": "gov", "freshness": 0.9},
            {"url": "https://x.edu/b", "snippet": "edu", "freshness": 0.9},
        ]
        ranked = ranker.rank(sources)
        for s in ranked:
            assert s["credibility_level"] in (
                "authoritative", "high", "moderate", "low", "unreliable",
            )


# ========== InformationExtractor Testleri ==========


class TestInformationExtractor:
    """Bilgi çıkarıcı testleri."""

    def test_init(self):
        ext = InformationExtractor()
        assert ext.extraction_count == 0

    def test_extract_facts(self):
        ext = InformationExtractor()
        result = ext.extract_facts(
            content="The market grew by 15 percent. Revenue exceeded expectations. New products launched.",
            source_id="src1",
        )
        assert result["fact_count"] > 0
        assert ext.fact_count > 0
        assert ext.extraction_count == 1

    def test_extract_facts_short(self):
        ext = InformationExtractor()
        result = ext.extract_facts(content="Short.")
        assert result["fact_count"] == 0

    def test_recognize_entities(self):
        ext = InformationExtractor()
        result = ext.recognize_entities(
            "The CEO of Apple said Microsoft is growing.",
        )
        assert result["entity_count"] > 0
        assert ext.entity_count > 0

    def test_recognize_entities_empty(self):
        ext = InformationExtractor()
        result = ext.recognize_entities("all lowercase text here")
        assert result["entity_count"] == 0

    def test_map_relationships(self):
        ext = InformationExtractor()
        entities = [
            {"text": "Apple"},
            {"text": "Microsoft"},
            {"text": "Google"},
        ]
        result = ext.map_relationships(
            entities, context="tech industry",
        )
        assert result["count"] == 3  # 3 pairs
        assert ext.relationship_count == 3

    def test_extract_quotes(self):
        ext = InformationExtractor()
        result = ext.extract_quotes(
            'He said "this is important" and she replied "I agree".',
            source_id="src1",
        )
        assert result["quote_count"] == 2

    def test_extract_quotes_none(self):
        ext = InformationExtractor()
        result = ext.extract_quotes("No quotes here.")
        assert result["quote_count"] == 0

    def test_extract_data_numbers(self):
        ext = InformationExtractor()
        result = ext.extract_data(
            "Revenue was 150.5 million with 23 percent growth",
        )
        assert result["count"] >= 2

    def test_get_all_facts(self):
        ext = InformationExtractor()
        ext.extract_facts("First sentence here. Second sentence here.")
        ext.extract_facts("Third sentence here. Fourth sentence here.")
        facts = ext.get_all_facts()
        assert len(facts) >= 2

    def test_get_entities(self):
        ext = InformationExtractor()
        ext.recognize_entities("Apple and Google compete")
        entities = ext.get_entities()
        assert isinstance(entities, list)


# ========== CrossValidator Testleri ==========


class TestCrossValidator:
    """Çapraz doğrulayıcı testleri."""

    def test_init(self):
        cv = CrossValidator()
        assert cv.validation_count == 0

    def test_validate_fact_verified(self):
        cv = CrossValidator(min_sources=2)
        fact = "Python is a programming language"
        sources = [
            {"snippet": "Python is a widely used programming language"},
            {"snippet": "Python programming language is popular"},
            {"snippet": "The programming language Python is versatile"},
        ]
        result = cv.validate_fact(fact, sources)
        assert result["result"] in ("verified", "likely_true")
        assert result["supporting_sources"] > 0

    def test_validate_fact_insufficient(self):
        cv = CrossValidator(min_sources=3)
        result = cv.validate_fact(
            "some fact",
            [{"snippet": "related content"}],
        )
        assert result["result"] == "uncertain"

    def test_validate_fact_no_sources(self):
        cv = CrossValidator()
        result = cv.validate_fact("fact", [])
        assert result["result"] == "unverifiable"

    def test_compare_sources(self):
        cv = CrossValidator()
        sources = [
            {"content": "Python is great for data science"},
            {"content": "Python is widely used in data science"},
            {"content": "Java is better for enterprise"},
        ]
        result = cv.compare_sources(sources, topic="programming")
        assert result["source_count"] == 3
        assert "agreement_rate" in result

    def test_detect_contradictions(self):
        cv = CrossValidator()
        facts = [
            {"content": "The company is not profitable"},
            {"content": "The company is profitable and growing"},
        ]
        contradictions = cv.detect_contradictions(facts)
        assert isinstance(contradictions, list)

    def test_find_consensus(self):
        cv = CrossValidator()
        facts = [
            {"content": "Fact A", "confidence": 0.9},
            {"content": "Fact B", "confidence": 0.5},
            {"content": "Fact C", "confidence": 0.3},
        ]
        result = cv.find_consensus(facts)
        assert result["consensus_found"] is True
        assert result["confidence"] == 0.9

    def test_find_consensus_empty(self):
        cv = CrossValidator()
        result = cv.find_consensus([])
        assert result["consensus_found"] is False

    def test_get_validations(self):
        cv = CrossValidator()
        cv.validate_fact("f1", [{"snippet": "s1"}])
        cv.validate_fact("f2", [{"snippet": "s2"}])
        validations = cv.get_validations()
        assert len(validations) == 2

    def test_get_validations_filtered(self):
        cv = CrossValidator()
        cv.validate_fact("f1", [])
        results = cv.get_validations(
            result_filter="unverifiable",
        )
        assert len(results) == 1

    def test_confidence_scoring(self):
        cv = CrossValidator()
        result = cv.validate_fact(
            "fact",
            [
                {"snippet": "fact is true"},
                {"snippet": "fact confirmed"},
            ],
        )
        assert 0 <= result["confidence"] <= 1


# ========== ResearchSynthesizer Testleri ==========


class TestResearchSynthesizer:
    """Araştırma sentezleyici testleri."""

    def test_init(self):
        synth = ResearchSynthesizer()
        assert synth.synthesis_count == 0

    def test_synthesize(self):
        synth = ResearchSynthesizer()
        facts = [
            {"content": "Fact one about AI", "confidence": 0.9},
            {"content": "Fact two about machine learning", "confidence": 0.8},
            {"content": "Fact three about deep learning", "confidence": 0.7},
        ]
        result = synth.synthesize(
            facts=facts, topic="artificial intelligence",
        )
        assert result["fact_count"] > 0
        assert "narrative" in result
        assert synth.synthesis_count == 1

    def test_synthesize_dedup(self):
        synth = ResearchSynthesizer()
        facts = [
            {"content": "Same fact here", "confidence": 0.9},
            {"content": "Same fact here", "confidence": 0.7},
        ]
        result = synth.synthesize(facts=facts, topic="test")
        assert result["fact_count"] == 1

    def test_synthesize_gaps(self):
        synth = ResearchSynthesizer()
        facts = [
            {"content": "Information about market only", "confidence": 0.8},
        ]
        result = synth.synthesize(
            facts=facts,
            topic="market trends analysis prediction",
        )
        assert len(result["gaps"]) > 0
        assert synth.gap_count > 0

    def test_synthesize_insights(self):
        synth = ResearchSynthesizer()
        facts = [
            {"content": f"Important fact {i}", "confidence": 0.9 - i * 0.1}
            for i in range(6)
        ]
        result = synth.synthesize(
            facts=facts, topic="research",
        )
        assert len(result["insights"]) > 0
        assert synth.insight_count > 0

    def test_generate_executive_summary(self):
        synth = ResearchSynthesizer()
        facts = [
            {"content": "Key finding", "confidence": 0.9},
        ]
        synthesis = synth.synthesize(
            facts=facts, topic="test",
        )
        summary = synth.generate_executive_summary(
            synthesis["synthesis_id"],
        )
        assert "topic" in summary
        assert "key_findings" in summary
        assert "recommendation" in summary

    def test_generate_executive_summary_not_found(self):
        synth = ResearchSynthesizer()
        result = synth.generate_executive_summary("x")
        assert "error" in result

    def test_synthesize_empty(self):
        synth = ResearchSynthesizer()
        result = synth.synthesize(facts=[], topic="empty")
        assert result["fact_count"] == 0
        assert "No information" in result["narrative"]

    def test_get_insights(self):
        synth = ResearchSynthesizer()
        synth.synthesize(
            facts=[{"content": "x", "confidence": 0.9}],
            topic="test",
        )
        insights = synth.get_insights()
        assert isinstance(insights, list)

    def test_get_gaps(self):
        synth = ResearchSynthesizer()
        synth.synthesize(
            facts=[{"content": "partial info", "confidence": 0.2}],
            topic="comprehensive analysis",
        )
        gaps = synth.get_gaps()
        assert isinstance(gaps, list)


# ========== ContinuousTracker Testleri ==========


class TestContinuousTracker:
    """Sürekli takipçi testleri."""

    def test_init(self):
        tracker = ContinuousTracker()
        assert tracker.topic_count == 0

    def test_track_topic(self):
        tracker = ContinuousTracker()
        result = tracker.track_topic(
            topic="AI trends",
            frequency="daily",
        )
        assert result["tracking"] is True
        assert tracker.topic_count == 1

    def test_detect_change(self):
        tracker = ContinuousTracker()
        topic = tracker.track_topic("test")
        result = tracker.detect_change(
            tracker_id=topic["tracker_id"],
            new_data={
                "type": "update",
                "summary": "New development",
                "significance": "low",
            },
        )
        assert result["change_detected"] is True
        assert tracker.change_count == 1

    def test_detect_change_not_found(self):
        tracker = ContinuousTracker()
        result = tracker.detect_change(
            "nonexistent", {},
        )
        assert "error" in result

    def test_detect_change_high_significance(self):
        tracker = ContinuousTracker()
        topic = tracker.track_topic("security")
        tracker.detect_change(
            tracker_id=topic["tracker_id"],
            new_data={
                "type": "alert",
                "summary": "Critical vulnerability",
                "significance": "critical",
            },
        )
        assert tracker.alert_count == 1

    def test_get_trends(self):
        tracker = ContinuousTracker()
        topic = tracker.track_topic("market")
        for i in range(5):
            tracker.detect_change(
                tracker_id=topic["tracker_id"],
                new_data={
                    "type": "update",
                    "summary": f"Change {i}",
                    "significance": "low",
                },
            )
        trends = tracker.get_trends(
            topic["tracker_id"],
        )
        assert trends["total_changes"] == 5

    def test_get_trends_not_found(self):
        tracker = ContinuousTracker()
        result = tracker.get_trends("x")
        assert "error" in result

    def test_stop_tracking(self):
        tracker = ContinuousTracker()
        topic = tracker.track_topic("test")
        result = tracker.stop_tracking(
            topic["tracker_id"],
        )
        assert result["stopped"] is True

    def test_stop_tracking_not_found(self):
        tracker = ContinuousTracker()
        result = tracker.stop_tracking("x")
        assert "error" in result

    def test_get_alerts(self):
        tracker = ContinuousTracker()
        topic = tracker.track_topic("test")
        tracker.detect_change(
            tracker_id=topic["tracker_id"],
            new_data={"significance": "high", "summary": "alert"},
        )
        alerts = tracker.get_alerts()
        assert len(alerts) == 1

    def test_get_alerts_filtered(self):
        tracker = ContinuousTracker()
        t1 = tracker.track_topic("a")
        t2 = tracker.track_topic("b")
        tracker.detect_change(t1["tracker_id"], {"significance": "high", "summary": "x"})
        tracker.detect_change(t2["tracker_id"], {"significance": "high", "summary": "y"})
        alerts = tracker.get_alerts(
            tracker_id=t1["tracker_id"],
        )
        assert len(alerts) == 1

    def test_get_changes(self):
        tracker = ContinuousTracker()
        topic = tracker.track_topic("test")
        tracker.detect_change(
            topic["tracker_id"],
            {"summary": "change1"},
        )
        changes = tracker.get_changes()
        assert len(changes) == 1

    def test_get_tracked_topics(self):
        tracker = ContinuousTracker()
        tracker.track_topic("a")
        tracker.track_topic("b")
        topics = tracker.get_tracked_topics()
        assert len(topics) == 2

    def test_get_tracked_topics_active_only(self):
        tracker = ContinuousTracker()
        t1 = tracker.track_topic("active")
        t2 = tracker.track_topic("inactive")
        tracker.stop_tracking(t2["tracker_id"])
        active = tracker.get_tracked_topics(active_only=True)
        assert len(active) == 1


# ========== ResearchReporter Testleri ==========


class TestResearchReporter:
    """Araştırma raporlayıcı testleri."""

    def test_init(self):
        reporter = ResearchReporter()
        assert reporter.report_count == 0

    def test_generate_report_markdown(self):
        reporter = ResearchReporter()
        synthesis = {
            "narrative": "Research shows positive results.",
            "insights": [
                {"content": "Key finding 1", "confidence": 0.9},
            ],
            "gaps": [],
            "fused_facts": [
                {"content": "Fact 1", "source_id": "s1"},
            ],
        }
        result = reporter.generate_report(
            title="Test Report",
            synthesis=synthesis,
        )
        assert result["format"] == "markdown"
        assert "# Test Report" in result["content"]
        assert reporter.report_count == 1

    def test_generate_report_html(self):
        reporter = ResearchReporter()
        synthesis = {
            "narrative": "Summary.",
            "insights": [],
            "gaps": [],
            "fused_facts": [],
        }
        result = reporter.generate_report(
            title="HTML Report",
            synthesis=synthesis,
            report_format="html",
        )
        assert "<h1>" in result["content"]

    def test_generate_report_executive(self):
        reporter = ResearchReporter()
        synthesis = {
            "narrative": "Executive info.",
            "insights": [{"content": "Insight"}],
            "gaps": [{"suggestion": "Fill gap"}],
            "fused_facts": [],
        }
        result = reporter.generate_report(
            title="Exec Report",
            synthesis=synthesis,
            report_format="executive",
        )
        assert "EXECUTIVE SUMMARY" in result["content"]

    def test_generate_report_with_citations(self):
        reporter = ResearchReporter()
        synthesis = {
            "narrative": "Data.",
            "insights": [],
            "gaps": [],
            "fused_facts": [
                {"content": "Fact", "source_id": "src1"},
                {"content": "Fact2", "source_id": "src2"},
            ],
        }
        result = reporter.generate_report(
            title="Cited Report",
            synthesis=synthesis,
        )
        assert result["citation_count"] == 2
        assert reporter.citation_count == 2

    def test_add_citation(self):
        reporter = ResearchReporter()
        result = reporter.add_citation(
            source_id="s1",
            title="Source Title",
            url="https://example.com",
            author="Author",
        )
        assert result["added"] is True

    def test_export(self):
        reporter = ResearchReporter()
        synthesis = {
            "narrative": "Data.",
            "insights": [],
            "gaps": [],
            "fused_facts": [],
        }
        report = reporter.generate_report(
            title="Export Test",
            synthesis=synthesis,
        )
        result = reporter.export(
            report["report_id"],
        )
        assert result["exported"] is True
        assert reporter.export_count == 1

    def test_export_not_found(self):
        reporter = ResearchReporter()
        result = reporter.export("nonexistent")
        assert "error" in result

    def test_get_report(self):
        reporter = ResearchReporter()
        synthesis = {
            "narrative": "x",
            "insights": [],
            "gaps": [],
            "fused_facts": [],
        }
        created = reporter.generate_report(
            title="Get Test", synthesis=synthesis,
        )
        result = reporter.get_report(
            created["report_id"],
        )
        assert result["title"] == "Get Test"

    def test_get_report_not_found(self):
        reporter = ResearchReporter()
        result = reporter.get_report("x")
        assert "error" in result

    def test_get_reports(self):
        reporter = ResearchReporter()
        synth = {
            "narrative": "",
            "insights": [],
            "gaps": [],
            "fused_facts": [],
        }
        reporter.generate_report("A", synth)
        reporter.generate_report("B", synth)
        reports = reporter.get_reports()
        assert len(reports) == 2

    def test_get_citations(self):
        reporter = ResearchReporter()
        reporter.add_citation("s1", "Title1")
        reporter.add_citation("s2", "Title2")
        citations = reporter.get_citations()
        assert len(citations) == 2


# ========== ResearchOrchestrator Testleri ==========


class TestResearchOrchestrator:
    """Orkestratör testleri."""

    def test_init(self):
        orch = ResearchOrchestrator()
        assert orch.research_count == 0

    def test_research_basic(self):
        orch = ResearchOrchestrator()
        result = orch.research(
            query="artificial intelligence trends",
        )
        assert result["success"] is True
        assert result["sources_found"] > 0
        assert result["facts_extracted"] > 0
        assert result["report_id"]
        assert orch.research_count == 1

    def test_research_no_expand(self):
        orch = ResearchOrchestrator()
        result = orch.research(
            query="simple query",
            expand_query=False,
        )
        assert result["success"] is True
        assert result["expanded_queries"] == 1

    def test_research_custom_format(self):
        orch = ResearchOrchestrator()
        result = orch.research(
            query="test",
            report_format="html",
        )
        assert result["report_format"] == "html"

    def test_research_max_sources(self):
        orch = ResearchOrchestrator()
        result = orch.research(
            query="test",
            max_sources=5,
        )
        assert result["sources_found"] <= 15

    def test_track_topic(self):
        orch = ResearchOrchestrator()
        result = orch.track_topic(
            topic="AI safety",
            frequency="weekly",
        )
        assert result["tracking"] is True

    def test_get_analytics(self):
        orch = ResearchOrchestrator()
        orch.research(query="test")
        analytics = orch.get_analytics()
        assert analytics["research_completed"] == 1
        assert analytics["total_crawls"] >= 1
        assert analytics["facts_extracted"] >= 0
        assert "reports_generated" in analytics

    def test_get_status(self):
        orch = ResearchOrchestrator()
        status = orch.get_status()
        assert "research_completed" in status
        assert "pipeline_runs" in status

    def test_full_pipeline(self):
        orch = ResearchOrchestrator()

        # Araştırma yap
        r1 = orch.research(
            query="machine learning in healthcare",
        )
        assert r1["success"] is True

        # Konu takibi
        t1 = orch.track_topic("AI healthcare")
        assert t1["tracking"] is True

        # İkinci araştırma
        r2 = orch.research(
            query="deep learning applications",
        )
        assert r2["success"] is True

        assert orch.research_count == 2

    def test_multiple_research(self):
        orch = ResearchOrchestrator()
        for i in range(3):
            orch.research(query=f"topic {i}")
        assert orch.research_count == 3
        analytics = orch.get_analytics()
        assert analytics["pipeline_runs"] == 3


# ========== Config Testleri ==========


class TestResearchEngineConfig:
    """Config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.research_enabled is True
        assert s.max_sources == 10
        assert s.min_credibility_score == 0.3
        assert s.continuous_tracking is True
        assert s.report_format == "markdown"


# ========== Import Testleri ==========


class TestResearchEngineImports:
    """Import testleri."""

    def test_import_all_from_init(self):
        from app.core.research import (
            ContinuousTracker,
            CrossValidator,
            InformationExtractor,
            MultiSourceCrawler,
            QueryExpander,
            ResearchOrchestrator,
            ResearchReporter,
            ResearchSynthesizer,
            SourceRanker,
        )
        assert ContinuousTracker is not None
        assert CrossValidator is not None
        assert InformationExtractor is not None
        assert MultiSourceCrawler is not None
        assert QueryExpander is not None
        assert ResearchOrchestrator is not None
        assert ResearchReporter is not None
        assert ResearchSynthesizer is not None
        assert SourceRanker is not None

    def test_import_all_models(self):
        from app.models.research_engine_models import (
            SourceType,
            CredibilityLevel,
            ResearchStatus,
            ReportFormat,
            ValidationResult,
            TrackingFrequency,
            ResearchRecord,
            SourceRecord,
            FactRecord,
            ResearchSnapshot,
        )
        assert SourceType is not None
        assert CredibilityLevel is not None
        assert ResearchStatus is not None
        assert ReportFormat is not None
        assert ValidationResult is not None
        assert TrackingFrequency is not None
        assert ResearchRecord is not None
        assert SourceRecord is not None
        assert FactRecord is not None
        assert ResearchSnapshot is not None
