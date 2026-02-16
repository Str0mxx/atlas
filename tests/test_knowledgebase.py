"""ATLAS Knowledge Base & Wiki Engine testleri.

WikiBuilder, AutoDocumenter,
FAQGenerator, KBSearchIndexer,
KnowledgeLinker, KnowledgeGapFinder,
VersionedContent, KBContributor,
KnowledgeBaseOrchestrator testleri.
"""

import pytest

from app.core.knowledgebase.auto_documenter import (
    AutoDocumenter,
)
from app.core.knowledgebase.faq_generator import (
    FAQGenerator,
)
from app.core.knowledgebase.gap_finder import (
    KnowledgeGapFinder,
)
from app.core.knowledgebase.kb_contributor import (
    KBContributor,
)
from app.core.knowledgebase.kb_search_indexer import (
    KBSearchIndexer,
)
from app.core.knowledgebase.knowledge_linker import (
    KnowledgeLinker,
)
from app.core.knowledgebase.knowledgebase_orchestrator import (
    KnowledgeBaseOrchestrator,
)
from app.core.knowledgebase.versioned_content import (
    VersionedContent,
)
from app.core.knowledgebase.wiki_builder import (
    WikiBuilder,
)
from app.models.knowledgebase_models import (
    ContributionRecord,
    ContributionType,
    ContentType,
    FAQRecord,
    GapRecord,
    GapSeverity,
    LinkType,
    PageRecord,
    PageStatus,
    ReviewStatus,
)


# ── WikiBuilder ─────────────────────────


class TestCreatePage:
    """create_page testleri."""

    def test_basic(self):
        w = WikiBuilder()
        r = w.create_page(title="Test")
        assert r["created"] is True
        assert r["title"] == "Test"
        assert r["status"] == "draft"

    def test_with_content(self):
        w = WikiBuilder()
        r = w.create_page(
            title="Guide",
            content="Some content",
            author="fatih",
        )
        assert r["created"] is True
        assert w.page_count == 1

    def test_with_parent(self):
        w = WikiBuilder()
        p1 = w.create_page(title="Parent")
        p2 = w.create_page(
            title="Child",
            parent_id=p1["page_id"],
        )
        assert p2["created"] is True

    def test_with_tags(self):
        w = WikiBuilder()
        r = w.create_page(
            title="Tagged",
            tags=["python", "guide"],
        )
        assert r["created"] is True


class TestManageHierarchy:
    """manage_hierarchy testleri."""

    def test_get_children(self):
        w = WikiBuilder()
        p1 = w.create_page(title="Root")
        w.create_page(
            title="C1",
            parent_id=p1["page_id"],
        )
        r = w.manage_hierarchy(
            p1["page_id"],
        )
        assert r["count"] == 1

    def test_move(self):
        w = WikiBuilder()
        p1 = w.create_page(title="A")
        p2 = w.create_page(title="B")
        p3 = w.create_page(
            title="C",
            parent_id=p1["page_id"],
        )
        r = w.manage_hierarchy(
            p3["page_id"],
            action="move",
            target_id=p2["page_id"],
        )
        assert r["moved"] is True


class TestAddLink:
    """add_link testleri."""

    def test_basic(self):
        w = WikiBuilder()
        p1 = w.create_page(title="A")
        p2 = w.create_page(title="B")
        r = w.add_link(
            p1["page_id"],
            p2["page_id"],
        )
        assert r["linked"] is True


class TestUseTemplate:
    """use_template testleri."""

    def test_article(self):
        w = WikiBuilder()
        r = w.use_template(
            "article",
            {"title": "Hello", "content": "World"},
        )
        assert r["applied"] is True
        assert "Hello" in r["rendered"]

    def test_guide(self):
        w = WikiBuilder()
        r = w.use_template(
            "guide",
            {"title": "Setup"},
        )
        assert "Steps" in r["rendered"]
        assert w.template_usage == 1


class TestFormatContent:
    """format_content testleri."""

    def test_markdown(self):
        w = WikiBuilder()
        p = w.create_page(
            title="Test", content="Body",
        )
        r = w.format_content(
            p["page_id"], "markdown",
        )
        assert r["formatted_ok"] is True
        assert "# Test" in r["formatted"]

    def test_html(self):
        w = WikiBuilder()
        p = w.create_page(
            title="Test", content="Body",
        )
        r = w.format_content(
            p["page_id"], "html",
        )
        assert "<h1>" in r["formatted"]

    def test_not_found(self):
        w = WikiBuilder()
        r = w.format_content("xxx")
        assert r["found"] is False


# ── AutoDocumenter ──────────────────────


class TestAutoDocument:
    """auto_document testleri."""

    def test_basic(self):
        d = AutoDocumenter()
        r = d.auto_document("Source text")
        assert r["generated"] is True
        assert r["doc_type"] == "general"

    def test_with_context(self):
        d = AutoDocumenter()
        r = d.auto_document(
            "Source", context="API docs",
        )
        assert r["generated"] is True
        assert d.doc_count == 1


class TestDocumentCode:
    """document_code testleri."""

    def test_basic(self):
        d = AutoDocumenter()
        code = "def hello():\n    pass"
        r = d.document_code(code)
        assert r["documented"] is True
        assert r["functions_found"] == 1

    def test_class(self):
        d = AutoDocumenter()
        code = "class Foo:\n    pass"
        r = d.document_code(code)
        assert r["functions_found"] == 1


class TestDocumentProcess:
    """document_process testleri."""

    def test_basic(self):
        d = AutoDocumenter()
        r = d.document_process(
            "Deploy",
            steps=["Build", "Test", "Ship"],
        )
        assert r["documented"] is True
        assert r["step_count"] == 3


class TestDocumentDecision:
    """document_decision testleri."""

    def test_basic(self):
        d = AutoDocumenter()
        r = d.document_decision(
            "Use PostgreSQL",
            rationale="Reliability",
            alternatives=["MySQL", "SQLite"],
        )
        assert r["documented"] is True
        assert r["alternatives_count"] == 2


class TestLogChange:
    """log_change testleri."""

    def test_basic(self):
        d = AutoDocumenter()
        r = d.log_change(
            "pg_1", change_type="edit",
        )
        assert r["logged"] is True
        assert d.changelog_count == 1


# ── FAQGenerator ────────────────────────


class TestExtractQuestions:
    """extract_questions testleri."""

    def test_basic(self):
        f = FAQGenerator()
        r = f.extract_questions(
            "How to deploy? What is API?",
        )
        assert r["extracted"] is True
        assert r["count"] >= 1

    def test_no_questions(self):
        f = FAQGenerator()
        r = f.extract_questions(
            "Statement one. Statement two.",
        )
        assert r["extracted"] is True


class TestGenerateAnswer:
    """generate_answer testleri."""

    def test_basic(self):
        f = FAQGenerator()
        r = f.generate_answer(
            "How to deploy?",
        )
        assert r["generated"] is True
        assert "Answer" in r["answer"]

    def test_with_context(self):
        f = FAQGenerator()
        r = f.generate_answer(
            "What is API?",
            context="REST architecture",
        )
        assert "context" in r["answer"].lower()
        assert f.faq_count == 1


class TestGroupByCategory:
    """group_by_category testleri."""

    def test_basic(self):
        f = FAQGenerator()
        f.generate_answer(
            "Q1?", category="deploy",
        )
        f.generate_answer(
            "Q2?", category="api",
        )
        r = f.group_by_category()
        assert r["grouped_ok"] is True
        assert r["category_count"] == 2


class TestRankByPopularity:
    """rank_by_popularity testleri."""

    def test_basic(self):
        f = FAQGenerator()
        f.generate_answer("Q1?")
        f.generate_answer("Q2?")
        r = f.rank_by_popularity()
        assert r["ranked_ok"] is True
        assert r["count"] == 2


class TestAutoUpdate:
    """auto_update testleri."""

    def test_update_answer(self):
        f = FAQGenerator()
        faq = f.generate_answer("Q?")
        r = f.auto_update(
            faq["faq_id"],
            new_answer="New answer",
        )
        assert r["updated"] is True

    def test_increment_views(self):
        f = FAQGenerator()
        faq = f.generate_answer("Q?")
        r = f.auto_update(
            faq["faq_id"],
            increment_views=True,
        )
        assert r["views"] == 1

    def test_not_found(self):
        f = FAQGenerator()
        r = f.auto_update("xxx")
        assert r["found"] is False


# ── KBSearchIndexer ─────────────────────


class TestIndexFulltext:
    """index_fulltext testleri."""

    def test_basic(self):
        s = KBSearchIndexer()
        r = s.index_fulltext(
            "pg_1", title="Python Guide",
            content="Learn Python basics",
        )
        assert r["indexed"] is True
        assert r["words_indexed"] > 0

    def test_with_tags(self):
        s = KBSearchIndexer()
        r = s.index_fulltext(
            "pg_1", tags=["python"],
        )
        assert r["indexed"] is True
        assert s.index_count == 1


class TestIndexSemantic:
    """index_semantic testleri."""

    def test_basic(self):
        s = KBSearchIndexer()
        r = s.index_semantic(
            "pg_1",
            keywords=["python", "tutorial"],
        )
        assert r["semantic_indexed"] is True
        assert r["keywords_indexed"] == 2


class TestUpdateRealtime:
    """update_realtime testleri."""

    def test_basic(self):
        s = KBSearchIndexer()
        s.index_fulltext(
            "pg_1", content="old text",
        )
        r = s.update_realtime(
            "pg_1", new_content="new text",
        )
        assert r["updated"] is True

    def test_not_found(self):
        s = KBSearchIndexer()
        r = s.update_realtime("xxx")
        assert r["found"] is False


class TestTuneRelevance:
    """tune_relevance testleri."""

    def test_basic(self):
        s = KBSearchIndexer()
        s.index_fulltext(
            "pg_1",
            title="Python Guide",
            content="Learn Python",
        )
        r = s.tune_relevance("Python")
        assert r["searched"] is True
        assert r["count"] == 1

    def test_no_match(self):
        s = KBSearchIndexer()
        r = s.tune_relevance("xyz123")
        assert r["count"] == 0
        assert s.search_count == 1


class TestAddSynonym:
    """add_synonym testleri."""

    def test_basic(self):
        s = KBSearchIndexer()
        r = s.add_synonym(
            "car", ["automobile", "vehicle"],
        )
        assert r["added"] is True
        assert r["count"] == 2


# ── KnowledgeLinker ─────────────────────


class TestAutoLink:
    """auto_link testleri."""

    def test_basic(self):
        l = KnowledgeLinker()
        l.register_page(
            "pg_1", title="Python",
        )
        l.register_page(
            "pg_2", title="Django",
        )
        r = l.auto_link(
            "pg_2",
            content="Python web framework",
        )
        assert r["linked"] is True
        assert r["links_found"] >= 1

    def test_no_match(self):
        l = KnowledgeLinker()
        l.register_page(
            "pg_1", title="Python",
        )
        r = l.auto_link(
            "pg_1", content="No matches here",
        )
        assert r["links_found"] == 0


class TestFindRelated:
    """find_related testleri."""

    def test_basic(self):
        l = KnowledgeLinker()
        l.register_page(
            "pg_1", title="A",
            keywords=["python", "web"],
        )
        l.register_page(
            "pg_2", title="B",
            keywords=["python", "api"],
        )
        r = l.find_related("pg_1")
        assert r["found_ok"] is True
        assert r["count"] >= 1

    def test_not_found(self):
        l = KnowledgeLinker()
        r = l.find_related("xxx")
        assert r["found"] is False


class TestAddCrossReference:
    """add_cross_reference testleri."""

    def test_basic(self):
        l = KnowledgeLinker()
        l.register_page("pg_1")
        l.register_page("pg_2")
        r = l.add_cross_reference(
            "pg_1", "pg_2",
        )
        assert r["added"] is True
        assert l.link_count == 1


class TestGetBacklinks:
    """get_backlinks testleri."""

    def test_basic(self):
        l = KnowledgeLinker()
        l.register_page("pg_1")
        l.register_page("pg_2")
        l.add_cross_reference(
            "pg_1", "pg_2",
        )
        r = l.get_backlinks("pg_2")
        assert r["count"] == 1
        assert "pg_1" in r["backlinks"]


class TestValidateLinks:
    """validate_links testleri."""

    def test_valid(self):
        l = KnowledgeLinker()
        l.register_page("pg_1")
        l.register_page("pg_2")
        l.add_cross_reference(
            "pg_1", "pg_2",
        )
        r = l.validate_links("pg_1")
        assert r["validated"] is True
        assert r["broken_count"] == 0

    def test_broken(self):
        l = KnowledgeLinker()
        l.register_page("pg_1")
        l.add_cross_reference(
            "pg_1", "pg_999",
        )
        r = l.validate_links("pg_1")
        assert r["broken_count"] == 1


# ── KnowledgeGapFinder ──────────────────


class TestAnalyzeCoverage:
    """analyze_coverage testleri."""

    def test_full(self):
        g = KnowledgeGapFinder()
        g.set_expected_topics(
            ["python", "django"],
        )
        g.add_page(
            "pg_1", topics=["python", "django"],
        )
        r = g.analyze_coverage()
        assert r["analyzed"] is True
        assert r["coverage_percentage"] == 100.0

    def test_partial(self):
        g = KnowledgeGapFinder()
        g.set_expected_topics(
            ["python", "django", "flask"],
        )
        g.add_page(
            "pg_1", topics=["python"],
        )
        r = g.analyze_coverage()
        assert r["coverage_percentage"] < 100


class TestFindMissingTopics:
    """find_missing_topics testleri."""

    def test_basic(self):
        g = KnowledgeGapFinder()
        g.set_expected_topics(
            ["python", "django"],
        )
        g.add_page(
            "pg_1", topics=["python"],
        )
        r = g.find_missing_topics()
        assert r["found"] is True
        assert "django" in r["missing_topics"]
        assert g.gap_count >= 1


class TestFindOutdated:
    """find_outdated testleri."""

    def test_basic(self):
        g = KnowledgeGapFinder()
        g.add_page(
            "pg_1",
            last_updated=1.0,
        )
        r = g.find_outdated(max_age_days=1)
        assert r["found"] is True
        assert r["count"] >= 1


class TestFindQualityGaps:
    """find_quality_gaps testleri."""

    def test_basic(self):
        g = KnowledgeGapFinder()
        g.add_page(
            "pg_1", quality_score=0.3,
        )
        g.add_page(
            "pg_2", quality_score=0.8,
        )
        r = g.find_quality_gaps(
            min_score=0.6,
        )
        assert r["found"] is True
        assert r["count"] == 1


class TestSuggestPriorities:
    """suggest_priorities testleri."""

    def test_basic(self):
        g = KnowledgeGapFinder()
        g.set_expected_topics(["python"])
        g.add_page(
            "pg_1", quality_score=0.2,
        )
        r = g.suggest_priorities()
        assert r["suggested"] is True
        assert r["count"] >= 1


# ── VersionedContent ────────────────────


class TestCreateVersion:
    """create_version testleri."""

    def test_basic(self):
        v = VersionedContent()
        r = v.create_version(
            "pg_1", content="v1",
        )
        assert r["created"] is True
        assert r["version"] == 1

    def test_multiple(self):
        v = VersionedContent()
        v.create_version(
            "pg_1", content="v1",
        )
        r = v.create_version(
            "pg_1", content="v2",
        )
        assert r["version"] == 2
        assert v.version_count == 2


class TestGetHistory:
    """get_history testleri."""

    def test_basic(self):
        v = VersionedContent()
        v.create_version(
            "pg_1", content="v1",
            author="fatih",
        )
        v.create_version(
            "pg_1", content="v2",
            author="fatih",
        )
        r = v.get_history("pg_1")
        assert r["retrieved"] is True
        assert r["total_versions"] == 2

    def test_empty(self):
        v = VersionedContent()
        r = v.get_history("xxx")
        assert r["total_versions"] == 0


class TestViewDiff:
    """view_diff testleri."""

    def test_basic(self):
        v = VersionedContent()
        v.create_version(
            "pg_1", content="line1",
        )
        v.create_version(
            "pg_1", content="line2",
        )
        r = v.view_diff("pg_1", 1, 2)
        assert r["diff_ok"] is True
        assert r["changed"] is True

    def test_no_change(self):
        v = VersionedContent()
        v.create_version(
            "pg_1", content="same",
        )
        v.create_version(
            "pg_1", content="same",
        )
        r = v.view_diff("pg_1", 1, 2)
        assert r["changed"] is False

    def test_not_found(self):
        v = VersionedContent()
        r = v.view_diff("xxx")
        assert r["found"] is False


class TestRollback:
    """rollback testleri."""

    def test_basic(self):
        v = VersionedContent()
        v.create_version(
            "pg_1", content="v1",
        )
        v.create_version(
            "pg_1", content="v2",
        )
        r = v.rollback("pg_1", 1)
        assert r["rolled_back"] is True
        assert r["new_version"] == 3
        assert v.rollback_count == 1

    def test_not_found(self):
        v = VersionedContent()
        r = v.rollback("xxx")
        assert r["found"] is False


class TestCollaborate:
    """collaborate testleri."""

    def test_lock(self):
        v = VersionedContent()
        r = v.collaborate(
            "pg_1", action="lock",
            user="fatih",
        )
        assert r["locked"] is True

    def test_conflict(self):
        v = VersionedContent()
        v.collaborate(
            "pg_1", action="lock",
            user="fatih",
        )
        r = v.collaborate(
            "pg_1", action="lock",
            user="ali",
        )
        assert r["conflict"] is True

    def test_unlock(self):
        v = VersionedContent()
        v.collaborate(
            "pg_1", action="lock",
            user="fatih",
        )
        r = v.collaborate(
            "pg_1", action="unlock",
        )
        assert r["unlocked"] is True

    def test_status(self):
        v = VersionedContent()
        r = v.collaborate(
            "pg_1", action="status",
        )
        assert r["status_ok"] is True
        assert r["is_locked"] is False


# ── KBContributor ───────────────────────


class TestTrackContribution:
    """track_contribution testleri."""

    def test_basic(self):
        c = KBContributor()
        r = c.track_contribution(
            "fatih", "pg_1",
        )
        assert r["tracked"] is True
        assert r["points_earned"] == 5

    def test_create(self):
        c = KBContributor()
        r = c.track_contribution(
            "fatih", "pg_1",
            contribution_type="create",
        )
        assert r["points_earned"] == 10
        assert c.contribution_count == 1


class TestReviewContribution:
    """review_contribution testleri."""

    def test_basic(self):
        c = KBContributor()
        r = c.review_contribution(
            reviewer="ali",
            verdict="approved",
        )
        assert r["reviewed"] is True
        assert c.review_count == 1


class TestScoreQuality:
    """score_quality testleri."""

    def test_basic(self):
        c = KBContributor()
        c.track_contribution(
            "fatih", "pg_1",
        )
        r = c.score_quality("fatih")
        assert r["scored"] is True

    def test_not_found(self):
        c = KBContributor()
        r = c.score_quality("xxx")
        assert r["found"] is False


class TestGetGamification:
    """get_gamification testleri."""

    def test_beginner(self):
        c = KBContributor()
        c.track_contribution(
            "fatih", "pg_1",
        )
        r = c.get_gamification("fatih")
        assert r["retrieved"] is True
        assert r["level"] == "beginner"

    def test_not_found(self):
        c = KBContributor()
        r = c.get_gamification("xxx")
        assert r["found"] is False


class TestGetAttribution:
    """get_attribution testleri."""

    def test_basic(self):
        c = KBContributor()
        c.track_contribution(
            "fatih", "pg_1",
        )
        c.track_contribution(
            "ali", "pg_1",
        )
        r = c.get_attribution("pg_1")
        assert r["retrieved"] is True
        assert r["total_edits"] == 2


# ── KnowledgeBaseOrchestrator ───────────


class TestCreateIndexLink:
    """create_index_link testleri."""

    def test_basic(self):
        o = KnowledgeBaseOrchestrator()
        r = o.create_index_link(
            title="Python Guide",
            content="Learn Python programming",
            author="fatih",
        )
        assert r["pipeline_complete"] is True
        assert r["indexed"] is True
        assert r["version"] == 1

    def test_with_keywords(self):
        o = KnowledgeBaseOrchestrator()
        r = o.create_index_link(
            title="API Docs",
            content="REST API reference",
            keywords=["api", "rest"],
        )
        assert r["pipeline_complete"] is True
        assert o.pipeline_count == 1


class TestSelfUpdate:
    """self_update testleri."""

    def test_basic(self):
        o = KnowledgeBaseOrchestrator()
        p = o.create_index_link(
            title="Test",
            content="v1",
        )
        r = o.self_update(
            p["page_id"],
            new_content="v2 content",
        )
        assert r["updated"] is True
        assert r["version"] == 2


class TestGetAnalyticsOrch:
    """get_analytics testleri."""

    def test_basic(self):
        o = KnowledgeBaseOrchestrator()
        o.create_index_link(
            title="Test",
            content="Body",
        )
        r = o.get_analytics()
        assert r["pipelines_run"] == 1
        assert r["pages_created"] >= 1
        assert r["versions"] >= 1


# ── Models ──────────────────────────────


class TestModels:
    """Model testleri."""

    def test_page_status(self):
        assert PageStatus.DRAFT == "draft"
        assert PageStatus.PUBLISHED == "published"

    def test_content_type(self):
        assert ContentType.WIKI == "wiki"
        assert ContentType.FAQ == "faq"

    def test_review_status(self):
        assert ReviewStatus.PENDING == "pending"
        assert ReviewStatus.APPROVED == "approved"

    def test_gap_severity(self):
        assert GapSeverity.CRITICAL == "critical"
        assert GapSeverity.LOW == "low"

    def test_link_type(self):
        assert LinkType.RELATED == "related"
        assert LinkType.PARENT == "parent"

    def test_contribution_type(self):
        assert ContributionType.CREATE == "create"
        assert ContributionType.EDIT == "edit"

    def test_page_record(self):
        r = PageRecord(title="Test")
        assert r.title == "Test"
        assert r.page_id

    def test_faq_record(self):
        r = FAQRecord(question="Q?")
        assert r.question == "Q?"
        assert r.faq_id

    def test_gap_record(self):
        r = GapRecord(topic="API")
        assert r.topic == "API"
        assert r.severity == "medium"

    def test_contribution_record(self):
        r = ContributionRecord(
            contributor="fatih",
        )
        assert r.contributor == "fatih"
        assert r.contribution_id
