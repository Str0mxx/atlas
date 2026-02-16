"""ATLAS Smart Document Manager testleri.

DocumentClassifier, AutoTagger,
DocVersionTracker, DocSearchEngine,
DocSummaryGenerator, DocTemplateManager,
ExpiryTracker, DocAccessController,
DocMgrOrchestrator testleri.
"""

import pytest

from app.core.docmgr.access_controller import (
    DocAccessController,
)
from app.core.docmgr.auto_tagger import (
    AutoTagger,
)
from app.core.docmgr.doc_search_engine import (
    DocSearchEngine,
)
from app.core.docmgr.docmgr_orchestrator import (
    DocMgrOrchestrator,
)
from app.core.docmgr.document_classifier import (
    DocumentClassifier,
)
from app.core.docmgr.expiry_tracker import (
    ExpiryTracker,
)
from app.core.docmgr.summary_generator import (
    DocSummaryGenerator,
)
from app.core.docmgr.template_manager import (
    DocTemplateManager,
)
from app.core.docmgr.version_tracker import (
    DocVersionTracker,
)
from app.models.docmgr_models import (
    AccessLevel,
    DocumentCategory,
    DocumentRecord,
    DocumentType,
    ExpiryRecord,
    ExpiryStatus,
    TagRecord,
    TagSource,
    VersionRecord,
    VersionStatus,
)


# ── DocumentClassifier ───────────────────


class TestAutoClassify:
    """auto_classify testleri."""

    def test_contract(self):
        c = DocumentClassifier()
        r = c.auto_classify(
            title="Service Agreement",
            content="This contract terms",
        )
        assert r["classified"] is True
        assert r["doc_type"] == "contract"

    def test_invoice(self):
        c = DocumentClassifier()
        r = c.auto_classify(
            title="Fatura 2024",
            content="ödeme yapılacak",
        )
        assert r["doc_type"] == "invoice"

    def test_report(self):
        c = DocumentClassifier()
        r = c.auto_classify(
            title="Monthly Report",
            content="analysis of results",
        )
        assert r["doc_type"] == "report"

    def test_default_type(self):
        c = DocumentClassifier()
        r = c.auto_classify(
            title="Unknown",
            content="generic text",
        )
        assert r["doc_type"] == "report"

    def test_counter(self):
        c = DocumentClassifier()
        c.auto_classify(title="A")
        c.auto_classify(title="B")
        assert c.classification_count == 2


class TestDetectType:
    """detect_type testleri."""

    def test_proposal(self):
        c = DocumentClassifier()
        r = c.detect_type(
            title="Teklif Sunumu",
        )
        assert r["detected"] is True
        assert r["doc_type"] == "proposal"

    def test_confidence(self):
        c = DocumentClassifier()
        r = c.detect_type(
            title="Contract Agreement",
            content="terms and conditions",
        )
        assert r["confidence"] > 0


class TestAssignCategory:
    """assign_category testleri."""

    def test_legal(self):
        c = DocumentClassifier()
        r = c.assign_category(
            content="legal contract hukuk",
        )
        assert r["assigned"] is True
        assert r["category"] == "legal"

    def test_custom(self):
        c = DocumentClassifier()
        r = c.assign_category(
            custom_category="hr",
        )
        assert r["category"] == "hr"
        assert r["custom"] is True

    def test_financial(self):
        c = DocumentClassifier()
        r = c.assign_category(
            content="financial invoice data",
        )
        assert r["category"] == "financial"


class TestScoreConfidence:
    """score_confidence testleri."""

    def test_high(self):
        c = DocumentClassifier()
        r = c.score_confidence(
            title="Contract Agreement",
            content="contract terms clause",
            doc_type="contract",
        )
        assert r["scored"] is True
        assert r["level"] in (
            "high", "medium",
        )

    def test_low(self):
        c = DocumentClassifier()
        r = c.score_confidence(
            doc_type="unknown",
        )
        assert r["level"] == "low"


class TestMultiLabelClassify:
    """multi_label_classify testleri."""

    def test_multi(self):
        c = DocumentClassifier()
        r = c.multi_label_classify(
            title="Contract Invoice",
            content="agreement payment",
        )
        assert r["classified"] is True
        assert r["count"] >= 2
        assert r["multi_label"] is True

    def test_single(self):
        c = DocumentClassifier()
        r = c.multi_label_classify(
            title="Report",
            content="analysis rapor",
        )
        assert r["classified"] is True
        assert c.multi_label_count >= 1


# ── AutoTagger ────────────────────────────


class TestExtractKeywords:
    """extract_keywords testleri."""

    def test_basic(self):
        t = AutoTagger()
        r = t.extract_keywords(
            "doc1",
            content="python data python code",
        )
        assert r["extracted"] is True
        assert r["count"] > 0

    def test_stop_words_filtered(self):
        t = AutoTagger()
        r = t.extract_keywords(
            "doc1",
            content="the a an is are for",
        )
        assert r["count"] == 0

    def test_max_keywords(self):
        t = AutoTagger()
        r = t.extract_keywords(
            "doc1",
            content="a1 b1 c1 d1 e1 f1 g1",
            max_keywords=3,
        )
        assert r["count"] <= 3


class TestTagEntities:
    """tag_entities testleri."""

    def test_basic(self):
        t = AutoTagger()
        r = t.tag_entities(
            "doc1",
            content="Fatih Istanbul Mapa",
        )
        assert r["tagged"] is True
        assert r["count"] >= 2

    def test_no_entities(self):
        t = AutoTagger()
        r = t.tag_entities(
            "doc1",
            content="lower case only",
        )
        assert r["count"] == 0


class TestDetectTopics:
    """detect_topics testleri."""

    def test_technology(self):
        t = AutoTagger()
        r = t.detect_topics(
            "doc1",
            content="software code api system",
        )
        assert r["detected"] is True
        assert r["count"] > 0
        assert r["topics"][0][
            "topic"
        ] == "technology"

    def test_no_topics(self):
        t = AutoTagger()
        r = t.detect_topics(
            "doc1",
            content="random words xyz",
        )
        assert r["count"] == 0


class TestAddCustomTag:
    """add_custom_tag testleri."""

    def test_basic(self):
        t = AutoTagger()
        r = t.add_custom_tag(
            "doc1", tag="important",
        )
        assert r["added"] is True
        assert r["tag"] == "important"

    def test_counter(self):
        t = AutoTagger()
        t.add_custom_tag("d1", tag="a")
        t.add_custom_tag("d1", tag="b")
        assert t.tag_count >= 2


class TestSuggestTags:
    """suggest_tags testleri."""

    def test_basic(self):
        t = AutoTagger()
        r = t.suggest_tags(
            "doc1",
            content=(
                "software code api data "
                "system revenue market"
            ),
        )
        assert r["suggested"] is True
        assert r["count"] > 0

    def test_max_suggestions(self):
        t = AutoTagger()
        r = t.suggest_tags(
            "doc1",
            content="software code api",
            max_suggestions=2,
        )
        assert r["count"] <= 2


# ── DocVersionTracker ─────────────────────


class TestCreateVersion:
    """create_version testleri."""

    def test_basic(self):
        v = DocVersionTracker()
        r = v.create_version(
            "doc1",
            content="Hello",
            author="fatih",
        )
        assert r["created"] is True
        assert r["version"] == "1.0"

    def test_increments(self):
        v = DocVersionTracker()
        v.create_version("doc1")
        r = v.create_version("doc1")
        assert r["version"] == "2.0"

    def test_counter(self):
        v = DocVersionTracker()
        v.create_version("d1")
        v.create_version("d2")
        assert v.version_count == 2


class TestGetHistory:
    """get_history testleri."""

    def test_basic(self):
        v = DocVersionTracker()
        v.create_version(
            "doc1", message="init",
        )
        v.create_version(
            "doc1", message="update",
        )
        r = v.get_history("doc1")
        assert r["retrieved"] is True
        assert r["total"] == 2

    def test_empty(self):
        v = DocVersionTracker()
        r = v.get_history("none")
        assert r["retrieved"] is False


class TestTrackChanges:
    """track_changes testleri."""

    def test_basic(self):
        v = DocVersionTracker()
        v.create_version(
            "doc1", content="Hello",
        )
        v.create_version(
            "doc1", content="Hello World",
        )
        r = v.track_changes("doc1")
        assert r["tracked"] is True
        assert r["changes"][0][
            "chars_added"
        ] > 0

    def test_insufficient_versions(self):
        v = DocVersionTracker()
        v.create_version("doc1")
        r = v.track_changes("doc1")
        assert r["tracked"] is False


class TestGenerateDiff:
    """generate_diff testleri."""

    def test_basic(self):
        v = DocVersionTracker()
        v.create_version(
            "doc1", content="line1\nline2",
        )
        v.create_version(
            "doc1", content="line1\nline3",
        )
        r = v.generate_diff(
            "doc1", "1.0", "2.0",
        )
        assert r["generated"] is True
        assert r["lines_added"] >= 1

    def test_empty(self):
        v = DocVersionTracker()
        r = v.generate_diff("none", "", "")
        assert r["generated"] is False


class TestRollback:
    """rollback testleri."""

    def test_basic(self):
        v = DocVersionTracker()
        v.create_version(
            "doc1", content="v1",
        )
        v.create_version(
            "doc1", content="v2",
        )
        r = v.rollback("doc1", "1.0")
        assert r["rolled_back"] is True
        assert r["restored_from"] == "1.0"
        assert v.rollback_count == 1

    def test_not_found(self):
        v = DocVersionTracker()
        v.create_version("doc1")
        r = v.rollback("doc1", "99.0")
        assert r["rolled_back"] is False


class TestCreateBranch:
    """create_branch testleri."""

    def test_basic(self):
        v = DocVersionTracker()
        v.create_version("doc1")
        r = v.create_branch(
            "doc1",
            branch_name="feature",
            from_version="1.0",
        )
        assert r["created"] is True
        assert r["branch_name"] == "feature"


# ── DocSearchEngine ───────────────────────


class TestIndexDocument:
    """index_document testleri."""

    def test_basic(self):
        s = DocSearchEngine()
        r = s.index_document(
            "doc1",
            title="Test",
            content="hello world",
        )
        assert r["indexed"] is True
        assert s.index_count == 1


class TestFullTextSearch:
    """full_text_search testleri."""

    def test_found(self):
        s = DocSearchEngine()
        s.index_document(
            "doc1",
            title="Python Guide",
            content="learn python programming",
        )
        r = s.full_text_search("python")
        assert r["searched"] is True
        assert r["total"] >= 1

    def test_not_found(self):
        s = DocSearchEngine()
        s.index_document(
            "doc1", title="Test",
        )
        r = s.full_text_search("xyz123")
        assert r["total"] == 0


class TestSemanticSearch:
    """semantic_search testleri."""

    def test_basic(self):
        s = DocSearchEngine()
        s.index_document(
            "doc1",
            title="Machine Learning",
            content="neural network deep",
        )
        r = s.semantic_search("learning")
        assert r["searched"] is True
        assert r["total"] >= 1


class TestFilterSearch:
    """filter_search testleri."""

    def test_by_category(self):
        s = DocSearchEngine()
        s.index_document(
            "doc1",
            title="A",
            category="legal",
        )
        s.index_document(
            "doc2",
            title="B",
            category="tech",
        )
        r = s.filter_search(
            category="legal",
        )
        assert r["filtered"] is True
        assert r["total"] == 1

    def test_by_tags(self):
        s = DocSearchEngine()
        s.index_document(
            "doc1",
            title="A",
            tags=["python"],
        )
        r = s.filter_search(
            tags=["python"],
        )
        assert r["total"] == 1


class TestFacetedSearch:
    """faceted_search testleri."""

    def test_basic(self):
        s = DocSearchEngine()
        s.index_document(
            "doc1",
            title="Test",
            content="hello",
            category="legal",
            tags=["a"],
        )
        r = s.faceted_search("hello")
        assert r["searched"] is True
        assert "categories" in r["facets"]

    def test_no_query(self):
        s = DocSearchEngine()
        s.index_document(
            "doc1",
            title="X",
            category="tech",
        )
        r = s.faceted_search("")
        assert r["facets"][
            "categories"
        ]["tech"] == 1


class TestRankRelevance:
    """rank_relevance testleri."""

    def test_basic(self):
        s = DocSearchEngine()
        s.index_document(
            "doc1",
            title="Python Guide",
            content="learn python",
        )
        r = s.rank_relevance(
            "python", "doc1",
        )
        assert r["ranked"] is True
        assert r["relevance_score"] > 0

    def test_not_found(self):
        s = DocSearchEngine()
        r = s.rank_relevance("x", "none")
        assert r["ranked"] is False


# ── DocSummaryGenerator ───────────────────


class TestAutoSummarize:
    """auto_summarize testleri."""

    def test_basic(self):
        g = DocSummaryGenerator()
        r = g.auto_summarize(
            "doc1",
            content=(
                "First sentence. "
                "Second sentence. "
                "Third sentence."
            ),
        )
        assert r["summarized"] is True
        assert r["sentence_count"] == 3

    def test_max_sentences(self):
        g = DocSummaryGenerator()
        r = g.auto_summarize(
            "doc1",
            content=(
                "A. B. C. D. E."
            ),
            max_sentences=2,
        )
        assert r["sentence_count"] == 2

    def test_counter(self):
        g = DocSummaryGenerator()
        g.auto_summarize("d1", content="A.")
        assert g.summary_count == 1


class TestExtractKeyPoints:
    """extract_key_points testleri."""

    def test_basic(self):
        g = DocSummaryGenerator()
        r = g.extract_key_points(
            "doc1",
            content=(
                "Short. "
                "A longer sentence here. "
                "Medium one."
            ),
        )
        assert r["extracted"] is True
        assert r["count"] > 0

    def test_max_points(self):
        g = DocSummaryGenerator()
        r = g.extract_key_points(
            "doc1",
            content="A. B. C. D. E.",
            max_points=2,
        )
        assert r["count"] <= 2


class TestGenerateTldr:
    """generate_tldr testleri."""

    def test_basic(self):
        g = DocSummaryGenerator()
        r = g.generate_tldr(
            "doc1",
            content="This is a summary.",
        )
        assert r["generated"] is True
        assert r["tldr"] != ""

    def test_empty(self):
        g = DocSummaryGenerator()
        r = g.generate_tldr("doc1")
        assert r["generated"] is False

    def test_truncation(self):
        g = DocSummaryGenerator()
        r = g.generate_tldr(
            "doc1",
            content=(
                "word " * 50 + "end."
            ),
            max_words=5,
        )
        assert r["word_count"] <= 6


class TestCustomLengthSummary:
    """custom_length_summary testleri."""

    def test_basic(self):
        g = DocSummaryGenerator()
        r = g.custom_length_summary(
            "doc1",
            content=(
                "First sentence. "
                "Second sentence."
            ),
            target_length=50,
        )
        assert r["generated"] is True
        assert r["length"] <= 50


class TestMultiDocumentSummary:
    """multi_document_summary testleri."""

    def test_basic(self):
        g = DocSummaryGenerator()
        docs = [
            {
                "doc_id": "d1",
                "content": "First doc content.",
            },
            {
                "doc_id": "d2",
                "content": (
                    "Second doc content here."
                ),
            },
        ]
        r = g.multi_document_summary(docs)
        assert r["generated"] is True
        assert r["documents_count"] == 2
        assert g.multi_doc_count == 1


# ── DocTemplateManager ────────────────────


class TestCreateTemplate:
    """create_template testleri."""

    def test_basic(self):
        m = DocTemplateManager()
        r = m.create_template(
            "invoice",
            content="Dear {{name}}",
            variables=["name"],
        )
        assert r["created"] is True
        assert m.template_count == 1

    def test_variables(self):
        m = DocTemplateManager()
        r = m.create_template(
            "letter",
            variables=["name", "date"],
        )
        assert len(r["variables"]) == 2


class TestSubstituteVariables:
    """substitute_variables testleri."""

    def test_basic(self):
        m = DocTemplateManager()
        m.create_template(
            "greet",
            content="Hello {{name}}!",
            variables=["name"],
        )
        r = m.substitute_variables(
            "greet",
            values={"name": "Fatih"},
        )
        assert r["substituted"] is True
        assert "Fatih" in r["content"]

    def test_not_found(self):
        m = DocTemplateManager()
        r = m.substitute_variables("none")
        assert r["substituted"] is False

    def test_counter(self):
        m = DocTemplateManager()
        m.create_template("t", content="X")
        m.substitute_variables("t")
        assert m.usage_count == 1


class TestUpdateTemplate:
    """update_template testleri."""

    def test_basic(self):
        m = DocTemplateManager()
        m.create_template("t", content="v1")
        r = m.update_template(
            "t", content="v2",
        )
        assert r["updated"] is True
        assert r["version"] == 2

    def test_not_found(self):
        m = DocTemplateManager()
        r = m.update_template("none")
        assert r["updated"] is False


class TestShareTemplate:
    """share_template testleri."""

    def test_basic(self):
        m = DocTemplateManager()
        m.create_template("t")
        r = m.share_template(
            "t", users=["user1", "user2"],
        )
        assert r["shared"] is True
        assert r["total_shared"] == 2

    def test_not_found(self):
        m = DocTemplateManager()
        r = m.share_template("none")
        assert r["shared"] is False


class TestTemplateAnalytics:
    """get_analytics testleri."""

    def test_specific(self):
        m = DocTemplateManager()
        m.create_template("t", content="X")
        m.substitute_variables("t")
        r = m.get_analytics("t")
        assert r["found"] is True
        assert r["usage_count"] == 1

    def test_all(self):
        m = DocTemplateManager()
        m.create_template("a")
        m.create_template("b")
        r = m.get_analytics()
        assert r["total_templates"] == 2


# ── ExpiryTracker ─────────────────────────


class TestSetExpiration:
    """set_expiration testleri."""

    def test_active(self):
        e = ExpiryTracker()
        r = e.set_expiration(
            "doc1",
            days_until_expiry=365,
        )
        assert r["set"] is True
        assert r["status"] == "active"

    def test_expiring_soon(self):
        e = ExpiryTracker(alert_days=30)
        r = e.set_expiration(
            "doc1",
            days_until_expiry=15,
        )
        assert r["status"] == "expiring_soon"

    def test_expired(self):
        e = ExpiryTracker()
        r = e.set_expiration(
            "doc1",
            days_until_expiry=0,
        )
        assert r["status"] == "expired"

    def test_counter(self):
        e = ExpiryTracker()
        e.set_expiration("d1")
        e.set_expiration("d2")
        assert e.tracked_count == 2


class TestCheckRenewals:
    """check_renewals testleri."""

    def test_basic(self):
        e = ExpiryTracker(alert_days=30)
        e.set_expiration(
            "doc1",
            days_until_expiry=10,
        )
        e.set_expiration(
            "doc2",
            days_until_expiry=0,
        )
        r = e.check_renewals()
        assert r["checked"] is True
        assert r["renewal_count"] >= 1
        assert r["expired_count"] >= 1


class TestCheckCompliance:
    """check_compliance testleri."""

    def test_basic(self):
        e = ExpiryTracker()
        e.set_expiration(
            "doc1",
            days_until_expiry=30,
        )
        e.set_expiration(
            "doc2",
            days_until_expiry=365,
        )
        r = e.check_compliance(
            compliance_days=90,
        )
        assert r["checked"] is True
        assert r["at_risk_count"] >= 1
        assert r["compliant_count"] >= 1


class TestAutoArchive:
    """auto_archive testleri."""

    def test_basic(self):
        e = ExpiryTracker()
        e.set_expiration(
            "doc1",
            days_until_expiry=0,
        )
        e.set_expiration(
            "doc2",
            days_until_expiry=100,
        )
        r = e.auto_archive()
        assert r["performed"] is True
        assert r["count"] == 1
        assert e.archived_count == 1

    def test_none_expired(self):
        e = ExpiryTracker()
        e.set_expiration(
            "doc1",
            days_until_expiry=100,
        )
        r = e.auto_archive()
        assert r["performed"] is False


class TestGenerateAlerts:
    """generate_alerts testleri."""

    def test_basic(self):
        e = ExpiryTracker(alert_days=30)
        e.set_expiration(
            "doc1",
            days_until_expiry=0,
        )
        e.set_expiration(
            "doc2",
            days_until_expiry=5,
        )
        e.set_expiration(
            "doc3",
            days_until_expiry=20,
        )
        r = e.generate_alerts()
        assert r["generated"] is True
        assert r["count"] == 3
        assert e.alert_count >= 3

    def test_no_alerts(self):
        e = ExpiryTracker(alert_days=30)
        e.set_expiration(
            "doc1",
            days_until_expiry=365,
        )
        r = e.generate_alerts()
        assert r["generated"] is False


# ── DocAccessController ───────────────────


class TestSetPermission:
    """set_permission testleri."""

    def test_basic(self):
        a = DocAccessController()
        r = a.set_permission(
            "doc1",
            user="fatih",
            level="internal",
        )
        assert r["set"] is True
        assert a.permission_count == 1

    def test_full_access(self):
        a = DocAccessController()
        r = a.set_permission(
            "doc1",
            user="admin",
            can_read=True,
            can_write=True,
            can_share=True,
        )
        assert r["set"] is True


class TestCheckAccess:
    """check_access testleri."""

    def test_allowed(self):
        a = DocAccessController()
        a.set_permission(
            "doc1",
            user="fatih",
            can_read=True,
        )
        r = a.check_access(
            "doc1", user="fatih",
            action="read",
        )
        assert r["allowed"] is True

    def test_denied(self):
        a = DocAccessController()
        a.set_permission(
            "doc1",
            user="fatih",
            can_write=False,
        )
        r = a.check_access(
            "doc1", user="fatih",
            action="write",
        )
        assert r["allowed"] is False

    def test_no_permission(self):
        a = DocAccessController()
        r = a.check_access(
            "doc1", user="stranger",
        )
        assert r["allowed"] is False
        assert r["reason"] == "no_permission"


class TestShareDocument:
    """share_document testleri."""

    def test_basic(self):
        a = DocAccessController()
        a.set_permission(
            "doc1",
            user="owner",
            can_share=True,
        )
        r = a.share_document(
            "doc1",
            owner="owner",
            recipient="user1",
        )
        assert r["shared"] is True

    def test_no_share_perm(self):
        a = DocAccessController()
        a.set_permission(
            "doc1",
            user="owner",
            can_share=False,
        )
        r = a.share_document(
            "doc1",
            owner="owner",
            recipient="user1",
        )
        assert r["shared"] is False


class TestGetAuditLog:
    """get_audit_log testleri."""

    def test_basic(self):
        a = DocAccessController()
        a.set_permission(
            "doc1", user="fatih",
        )
        r = a.get_audit_log("doc1")
        assert r["retrieved"] is True
        assert r["total"] >= 1

    def test_all(self):
        a = DocAccessController()
        a.set_permission(
            "doc1", user="a",
        )
        a.set_permission(
            "doc2", user="b",
        )
        r = a.get_audit_log()
        assert r["total"] >= 2


class TestEncryptDocument:
    """encrypt_document testleri."""

    def test_basic(self):
        a = DocAccessController()
        r = a.encrypt_document("doc1")
        assert r["encrypted"] is True
        assert r["algorithm"] == "AES-256"


class TestAddWatermark:
    """add_watermark testleri."""

    def test_basic(self):
        a = DocAccessController()
        r = a.add_watermark(
            "doc1",
            watermark_text="CONFIDENTIAL",
        )
        assert r["watermarked"] is True
        assert a.audit_count >= 1


# ── DocMgrOrchestrator ────────────────────


class TestUploadClassifyTagIndex:
    """upload_classify_tag_index testleri."""

    def test_basic(self):
        o = DocMgrOrchestrator()
        r = o.upload_classify_tag_index(
            doc_id="doc1",
            title="Contract Agreement",
            content=(
                "This contract terms "
                "agreement clause"
            ),
            author="fatih",
        )
        assert r["pipeline_complete"] is True
        assert r["doc_type"] == "contract"
        assert r["indexed"] is True
        assert r["versioned"] is True

    def test_counter(self):
        o = DocMgrOrchestrator()
        o.upload_classify_tag_index(
            "d1", title="A",
        )
        o.upload_classify_tag_index(
            "d2", title="B",
        )
        assert o.pipeline_count == 2


class TestManageLifecycle:
    """manage_lifecycle testleri."""

    def test_basic(self):
        o = DocMgrOrchestrator()
        r = o.manage_lifecycle(
            doc_id="doc1",
            title="Report",
            content=(
                "This is a report. "
                "It has analysis."
            ),
            expiry_days=365,
            owner="fatih",
        )
        assert r["managed"] is True
        assert r["pipeline"] is True
        assert r["expiry_status"] == "active"
        assert r["owner"] == "fatih"


class TestOrchestratorAnalytics:
    """get_analytics testleri."""

    def test_basic(self):
        o = DocMgrOrchestrator()
        o.upload_classify_tag_index(
            "doc1", title="Test",
            content="hello world",
        )
        r = o.get_analytics()
        assert r["pipelines_run"] >= 1
        assert r["classifications"] >= 1
        assert r["versions"] >= 1
        assert r["indexed"] >= 1


# ── Models ────────────────────────────────


class TestDocmgrModels:
    """Model testleri."""

    def test_document_type(self):
        assert (
            DocumentType.CONTRACT
            == "contract"
        )
        assert (
            DocumentType.INVOICE
            == "invoice"
        )

    def test_document_category(self):
        assert (
            DocumentCategory.LEGAL == "legal"
        )
        assert (
            DocumentCategory.FINANCIAL
            == "financial"
        )

    def test_access_level(self):
        assert (
            AccessLevel.PUBLIC == "public"
        )
        assert (
            AccessLevel.RESTRICTED
            == "restricted"
        )

    def test_version_status(self):
        assert (
            VersionStatus.DRAFT == "draft"
        )
        assert (
            VersionStatus.APPROVED
            == "approved"
        )

    def test_expiry_status(self):
        assert (
            ExpiryStatus.ACTIVE == "active"
        )
        assert (
            ExpiryStatus.EXPIRED == "expired"
        )

    def test_tag_source(self):
        assert TagSource.AUTO == "auto"
        assert TagSource.ENTITY == "entity"

    def test_document_record(self):
        r = DocumentRecord(title="Test")
        assert r.title == "Test"
        assert r.doc_id

    def test_version_record(self):
        r = VersionRecord(version="2.0")
        assert r.version == "2.0"
        assert r.version_id

    def test_tag_record(self):
        r = TagRecord(
            tag="python",
            confidence=0.9,
        )
        assert r.tag == "python"
        assert r.confidence == 0.9

    def test_expiry_record(self):
        r = ExpiryRecord(
            days_remaining=30,
        )
        assert r.days_remaining == 30
        assert r.status == "active"
