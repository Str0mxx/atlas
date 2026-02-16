"""ATLAS Legal & Contract Analyzer testleri.

ContractParser, ClauseExtractor, RiskHighlighter,
LegalComplianceChecker, LegalDeadlineExtractor,
LegalSummarizer, ContractComparator,
LegalNegotiationAdvisor, LegalOrchestrator.
"""

import pytest

from app.core.legal.contract_parser import (
    ContractParser,
)
from app.core.legal.clause_extractor import (
    ClauseExtractor,
)
from app.core.legal.risk_highlighter import (
    RiskHighlighter,
)
from app.core.legal.compliance_checker import (
    LegalComplianceChecker,
)
from app.core.legal.deadline_extractor import (
    LegalDeadlineExtractor,
)
from app.core.legal.legal_summarizer import (
    LegalSummarizer,
)
from app.core.legal.contract_comparator import (
    ContractComparator,
)
from app.core.legal.negotiation_advisor import (
    LegalNegotiationAdvisor,
)
from app.core.legal.legal_orchestrator import (
    LegalOrchestrator,
)


# ── ContractParser ──────────────────────


class TestContractParserInit:
    def test_init(self):
        p = ContractParser()
        assert p.contract_count == 0
        assert p.section_count == 0


class TestParseDocument:
    def test_basic(self):
        p = ContractParser()
        r = p.parse_document(
            title="NDA",
            content="1. DEFINITIONS\nSome text",
        )
        assert r["parsed"] is True
        assert r["title"] == "NDA"
        assert "contract_id" in r

    def test_with_type(self):
        p = ContractParser()
        r = p.parse_document(
            title="SLA",
            contract_type="service",
        )
        assert r["parsed"] is True
        assert p.contract_count == 1

    def test_sections_detected(self):
        p = ContractParser()
        content = (
            "1. DEFINITIONS\n"
            "Some text\n"
            "2. OBLIGATIONS\n"
            "More text"
        )
        r = p.parse_document(
            title="T", content=content,
        )
        assert r["sections_found"] >= 2

    def test_word_count(self):
        p = ContractParser()
        r = p.parse_document(
            title="T",
            content="one two three four",
        )
        assert r["word_count"] == 4


class TestDetectSections:
    def test_existing(self):
        p = ContractParser()
        r = p.parse_document(
            title="T",
            content="1. INTRO\ntext",
        )
        cid = r["contract_id"]
        s = p.detect_sections(cid)
        assert s["detected"] is True
        assert s["count"] >= 1

    def test_missing(self):
        p = ContractParser()
        s = p.detect_sections("none")
        assert s["detected"] is False


class TestExtractStructure:
    def test_existing(self):
        p = ContractParser()
        r = p.parse_document(
            title="SLA",
            content="1. SCOPE\ntext",
        )
        cid = r["contract_id"]
        s = p.extract_structure(cid)
        assert s["extracted"] is True
        assert "structure" in s

    def test_missing(self):
        p = ContractParser()
        s = p.extract_structure("none")
        assert s["extracted"] is False


class TestExtractMetadata:
    def test_basic(self):
        p = ContractParser()
        r = p.parse_document(title="T")
        cid = r["contract_id"]
        m = p.extract_metadata(
            cid, parties=["A", "B"],
        )
        assert m["extracted"] is True
        assert m["metadata"]["party_count"] == 2

    def test_missing(self):
        p = ContractParser()
        m = p.extract_metadata("none")
        assert m["extracted"] is False


class TestHandleFormat:
    def test_supported(self):
        p = ContractParser()
        r = p.handle_format(
            "text", source_format="pdf",
        )
        assert r["supported"] is True

    def test_unsupported(self):
        p = ContractParser()
        r = p.handle_format(
            "text", source_format="xyz",
        )
        assert r["supported"] is False

    def test_char_count(self):
        p = ContractParser()
        r = p.handle_format("hello world")
        assert r["char_count"] == 11


class TestGetContract:
    def test_exists(self):
        p = ContractParser()
        r = p.parse_document(title="T")
        c = p.get_contract(
            r["contract_id"],
        )
        assert c is not None
        assert c["title"] == "T"

    def test_missing(self):
        p = ContractParser()
        assert p.get_contract("x") is None


class TestListContracts:
    def test_empty(self):
        p = ContractParser()
        assert p.list_contracts() == []

    def test_multiple(self):
        p = ContractParser()
        p.parse_document(title="A")
        p.parse_document(title="B")
        lst = p.list_contracts()
        assert len(lst) == 2


# ── ClauseExtractor ─────────────────────


class TestClauseExtractorInit:
    def test_init(self):
        c = ClauseExtractor()
        assert c.clause_count == 0
        assert c.obligation_count == 0


class TestIdentifyClause:
    def test_basic(self):
        c = ClauseExtractor()
        r = c.identify_clause(
            "cid1", "shall pay $100",
            clause_type="payment",
        )
        assert r["identified"] is True
        assert r["type"] == "payment"
        assert c.clause_count == 1

    def test_with_section(self):
        c = ClauseExtractor()
        r = c.identify_clause(
            "cid1", "text",
            section="3.1",
        )
        assert r["section"] == "3.1"


class TestClassifyType:
    def test_obligation(self):
        c = ClauseExtractor()
        r = c.classify_type(
            "Party shall deliver "
            "the goods as required",
        )
        assert r["classified_type"] in (
            "obligation", "right",
        )
        assert r["confidence"] > 0

    def test_payment(self):
        c = ClauseExtractor()
        r = c.classify_type(
            "The fee is $500 and "
            "the price includes tax",
        )
        assert r["classified_type"] == "payment"

    def test_unknown(self):
        c = ClauseExtractor()
        r = c.classify_type("hello world")
        assert r["classified_type"] == "other"
        assert r["confidence"] == 0.0


class TestExtractKeyTerms:
    def test_found(self):
        c = ClauseExtractor()
        r = c.extract_key_terms(
            "This includes liability "
            "and indemnification clauses",
        )
        assert r["count"] >= 2
        assert "liability" in r["terms"]

    def test_max_terms(self):
        c = ClauseExtractor()
        r = c.extract_key_terms(
            "liability warranty "
            "termination breach remedy "
            "damages covenant obligation",
            max_terms=3,
        )
        assert r["count"] <= 3

    def test_empty(self):
        c = ClauseExtractor()
        r = c.extract_key_terms("hello")
        assert r["count"] == 0


class TestDetectObligations:
    def test_found(self):
        c = ClauseExtractor()
        c.identify_clause(
            "cid1", "must deliver",
            clause_type="obligation",
        )
        r = c.detect_obligations("cid1")
        assert r["count"] == 1

    def test_empty(self):
        c = ClauseExtractor()
        r = c.detect_obligations("none")
        assert r["count"] == 0


class TestMapRights:
    def test_found(self):
        c = ClauseExtractor()
        c.identify_clause(
            "cid1", "may use",
            clause_type="right",
        )
        r = c.map_rights("cid1")
        assert r["count"] == 1

    def test_empty(self):
        c = ClauseExtractor()
        r = c.map_rights("none")
        assert r["count"] == 0


class TestGetClauses:
    def test_by_type(self):
        c = ClauseExtractor()
        c.identify_clause(
            "cid1", "t1",
            clause_type="payment",
        )
        c.identify_clause(
            "cid1", "t2",
            clause_type="right",
        )
        lst = c.get_clauses(
            "cid1", clause_type="payment",
        )
        assert len(lst) == 1

    def test_all(self):
        c = ClauseExtractor()
        c.identify_clause("cid1", "t")
        lst = c.get_clauses("cid1")
        assert len(lst) == 1


# ── RiskHighlighter ──────────────────────


class TestRiskHighlighterInit:
    def test_init(self):
        r = RiskHighlighter()
        assert r.risk_count == 0
        assert r.red_flag_count == 0


class TestIdentifyRisk:
    def test_basic(self):
        r = RiskHighlighter()
        res = r.identify_risk(
            "cid1", "No liability cap",
            severity="high",
            category="liability",
        )
        assert res["identified"] is True
        assert res["severity"] == "high"
        assert r.risk_count == 1

    def test_multiple(self):
        r = RiskHighlighter()
        r.identify_risk("c1", "r1")
        r.identify_risk("c1", "r2")
        assert r.risk_count == 2


class TestScoreSeverity:
    def test_critical(self):
        r = RiskHighlighter()
        res = r.score_severity(
            impact=1.0,
            likelihood=1.0,
            exposure=1.0,
        )
        assert res["severity"] == "critical"
        assert res["score"] == 100

    def test_low(self):
        r = RiskHighlighter()
        res = r.score_severity(
            impact=0.2,
            likelihood=0.2,
            exposure=0.2,
        )
        assert res["severity"] == "low"

    def test_medium(self):
        r = RiskHighlighter()
        res = r.score_severity(
            impact=0.5,
            likelihood=0.5,
            exposure=0.5,
        )
        assert res["severity"] == "medium"


class TestCheckIndustryStandards:
    def test_general(self):
        r = RiskHighlighter()
        res = r.check_industry_standards(
            "cid1",
            clauses=["liability"],
        )
        assert "liability" in res["present"]
        assert len(res["missing"]) > 0

    def test_full_compliance(self):
        r = RiskHighlighter()
        res = r.check_industry_standards(
            "cid1",
            clauses=[
                "liability", "termination",
                "confidentiality",
                "dispute_resolution",
            ],
        )
        assert res["compliance_pct"] == 100.0

    def test_technology(self):
        r = RiskHighlighter()
        res = r.check_industry_standards(
            "cid1",
            industry="technology",
        )
        assert "ip_ownership" in res["required"]


class TestDetectRedFlags:
    def test_found(self):
        r = RiskHighlighter()
        res = r.detect_red_flags(
            "cid1",
            text="unlimited liability clause",
        )
        assert res["count"] >= 1
        assert res["clean"] is False

    def test_clean(self):
        r = RiskHighlighter()
        res = r.detect_red_flags(
            "cid1", text="standard terms",
        )
        assert res["count"] == 0
        assert res["clean"] is True

    def test_multiple_flags(self):
        r = RiskHighlighter()
        res = r.detect_red_flags(
            "cid1",
            text=(
                "unlimited liability and "
                "sole discretion"
            ),
        )
        assert res["count"] >= 2


class TestSuggestMitigation:
    def test_liability(self):
        r = RiskHighlighter()
        res = r.suggest_mitigation(
            "r1", category="liability",
        )
        assert res["count"] >= 3

    def test_critical_adds_counsel(self):
        r = RiskHighlighter()
        res = r.suggest_mitigation(
            "r1", severity="critical",
        )
        assert "Seek legal counsel" in (
            res["suggestions"]
        )

    def test_general(self):
        r = RiskHighlighter()
        res = r.suggest_mitigation("r1")
        assert res["count"] >= 3


class TestGetRisks:
    def test_by_severity(self):
        r = RiskHighlighter()
        r.identify_risk(
            "c1", "d1", severity="high",
        )
        r.identify_risk(
            "c1", "d2", severity="low",
        )
        lst = r.get_risks(
            "c1", severity="high",
        )
        assert len(lst) == 1

    def test_all(self):
        r = RiskHighlighter()
        r.identify_risk("c1", "d1")
        lst = r.get_risks("c1")
        assert len(lst) == 1


# ── LegalComplianceChecker ───────────────


class TestComplianceInit:
    def test_init(self):
        c = LegalComplianceChecker()
        assert c.check_count == 0
        assert c.issue_count == 0


class TestCheckRegulatory:
    def test_gdpr_compliant(self):
        c = LegalComplianceChecker()
        r = c.check_regulatory(
            "cid1", "gdpr",
            present_clauses=[
                "data_processing",
                "consent",
                "right_to_delete",
                "data_portability",
                "breach_notification",
            ],
        )
        assert r["status"] == "compliant"
        assert r["compliance_pct"] == 100.0

    def test_partial(self):
        c = LegalComplianceChecker()
        r = c.check_regulatory(
            "cid1", "gdpr",
            present_clauses=["consent"],
        )
        assert r["status"] == "partial"
        assert len(r["missing"]) > 0

    def test_non_compliant(self):
        c = LegalComplianceChecker()
        r = c.check_regulatory(
            "cid1", "gdpr",
        )
        assert r["status"] == "non_compliant"

    def test_unknown_regulation(self):
        c = LegalComplianceChecker()
        r = c.check_regulatory(
            "cid1", "unknown",
        )
        assert r["status"] == "compliant"


class TestCheckStandardClauses:
    def test_some_present(self):
        c = LegalComplianceChecker()
        r = c.check_standard_clauses(
            "cid1",
            clauses=[
                "governing_law",
                "termination",
            ],
        )
        assert len(r["present"]) == 2
        assert len(r["missing"]) > 0

    def test_empty(self):
        c = LegalComplianceChecker()
        r = c.check_standard_clauses("cid1")
        assert r["coverage_pct"] == 0.0


class TestFindMissingRequirements:
    def test_service(self):
        c = LegalComplianceChecker()
        r = c.find_missing_requirements(
            "cid1", contract_type="service",
        )
        assert r["missing_count"] > 0
        assert r["severity"] == "high"

    def test_nda(self):
        c = LegalComplianceChecker()
        r = c.find_missing_requirements(
            "cid1",
            contract_type="nda",
            present=["definition", "obligations",
                      "exclusions", "duration",
                      "return_of_materials"],
        )
        assert r["missing_count"] == 0
        assert r["severity"] == "low"


class TestCheckJurisdiction:
    def test_valid(self):
        c = LegalComplianceChecker()
        r = c.check_jurisdiction(
            "cid1",
            jurisdiction="Turkey",
            governing_law="Turkey",
        )
        assert r["valid"] is True

    def test_no_jurisdiction(self):
        c = LegalComplianceChecker()
        r = c.check_jurisdiction("cid1")
        assert r["valid"] is False
        assert len(r["issues"]) == 2

    def test_mismatch(self):
        c = LegalComplianceChecker()
        r = c.check_jurisdiction(
            "cid1",
            jurisdiction="USA",
            governing_law="UK",
        )
        assert r["valid"] is False


class TestTrackUpdate:
    def test_basic(self):
        c = LegalComplianceChecker()
        r = c.track_update(
            "gdpr", description="update",
        )
        assert r["tracked"] is True


# ── LegalDeadlineExtractor ───────────────


class TestDeadlineInit:
    def test_init(self):
        d = LegalDeadlineExtractor()
        assert d.deadline_count == 0
        assert d.renewal_count == 0


class TestExtractDates:
    def test_basic(self):
        d = LegalDeadlineExtractor()
        r = d.extract_dates(
            "cid1",
            effective_date="2025-01-01",
            expiry_date="2026-01-01",
        )
        assert r["extracted"] is True
        assert r["count"] == 2

    def test_empty(self):
        d = LegalDeadlineExtractor()
        r = d.extract_dates("cid1")
        assert r["count"] == 0


class TestCalculateDeadline:
    def test_basic(self):
        d = LegalDeadlineExtractor()
        r = d.calculate_deadline(
            "cid1", "expiry", "2026-12-31",
            notice_days=30,
        )
        assert r["calculated"] is True
        assert r["notice_days"] == 30
        assert d.deadline_count == 1

    def test_description(self):
        d = LegalDeadlineExtractor()
        r = d.calculate_deadline(
            "cid1", "renewal", "2026-06-01",
            description="Auto",
        )
        assert r["calculated"] is True


class TestTrackRenewal:
    def test_auto(self):
        d = LegalDeadlineExtractor()
        r = d.track_renewal(
            "cid1", "2026-12-31",
            auto_renew=True,
        )
        assert r["auto_renew"] is True
        assert d.renewal_count == 1

    def test_manual(self):
        d = LegalDeadlineExtractor()
        r = d.track_renewal(
            "cid1", "2026-12-31",
            auto_renew=False,
            notice_required_days=60,
        )
        assert r["auto_renew"] is False


class TestTrackNoticePeriod:
    def test_basic(self):
        d = LegalDeadlineExtractor()
        r = d.track_notice_period(
            "cid1", days=60,
        )
        assert r["tracked"] is True
        assert r["days"] == 60

    def test_custom_type(self):
        d = LegalDeadlineExtractor()
        r = d.track_notice_period(
            "cid1",
            notice_type="renewal",
            days=90,
        )
        assert r["notice_type"] == "renewal"


class TestAddToCalendar:
    def test_basic(self):
        d = LegalDeadlineExtractor()
        r = d.add_to_calendar(
            "dl_1", reminder_days=14,
            assignee="legal",
        )
        assert r["added_to_calendar"] is True

    def test_default(self):
        d = LegalDeadlineExtractor()
        r = d.add_to_calendar("dl_1")
        assert r["reminder_days"] == 7


class TestGetDeadlines:
    def test_by_type(self):
        d = LegalDeadlineExtractor()
        d.calculate_deadline(
            "c1", "expiry", "2026-12-31",
        )
        d.calculate_deadline(
            "c1", "renewal", "2027-01-01",
        )
        lst = d.get_deadlines(
            "c1", deadline_type="expiry",
        )
        assert len(lst) == 1

    def test_all(self):
        d = LegalDeadlineExtractor()
        d.calculate_deadline(
            "c1", "expiry", "2026-12-31",
        )
        lst = d.get_deadlines("c1")
        assert len(lst) == 1


class TestGetUpcoming:
    def test_active(self):
        d = LegalDeadlineExtractor()
        d.calculate_deadline(
            "c1", "expiry", "2026-12-31",
        )
        lst = d.get_upcoming()
        assert len(lst) == 1

    def test_empty(self):
        d = LegalDeadlineExtractor()
        assert d.get_upcoming() == []


# ── LegalSummarizer ─────────────────────


class TestSummarizerInit:
    def test_init(self):
        s = LegalSummarizer()
        assert s.summary_count == 0


class TestCreateExecutiveSummary:
    def test_basic(self):
        s = LegalSummarizer()
        r = s.create_executive_summary(
            "cid1", title="NDA",
            parties=["A", "B"],
        )
        assert r["created"] is True
        assert r["party_count"] == 2
        assert s.summary_count == 1

    def test_with_value(self):
        s = LegalSummarizer()
        r = s.create_executive_summary(
            "cid1", title="SLA",
            value=50000.0,
        )
        assert r["value"] == 50000.0


class TestExtractKeyPoints:
    def test_found(self):
        s = LegalSummarizer()
        r = s.extract_key_points(
            "cid1",
            clauses=[
                {"type": "obligation",
                 "text": "shall deliver"},
                {"type": "payment",
                 "text": "pay $100"},
            ],
        )
        assert r["count"] == 2

    def test_empty(self):
        s = LegalSummarizer()
        r = s.extract_key_points("cid1")
        assert r["count"] == 0

    def test_filters(self):
        s = LegalSummarizer()
        r = s.extract_key_points(
            "cid1",
            clauses=[
                {"type": "other", "text": "x"},
            ],
        )
        assert r["count"] == 0


class TestToPlainLanguage:
    def test_simplify(self):
        s = LegalSummarizer()
        r = s.to_plain_language(
            "The party hereinafter "
            "shall comply",
        )
        assert r["simplifications"] >= 2
        assert r["complexity"] == "medium"

    def test_no_change(self):
        s = LegalSummarizer()
        r = s.to_plain_language(
            "Simple text here",
        )
        assert r["simplifications"] == 0
        assert r["complexity"] == "low"

    def test_high_complexity(self):
        s = LegalSummarizer()
        r = s.to_plain_language(
            "hereinafter whereas "
            "notwithstanding pursuant to "
            "shall therein hereby",
        )
        assert r["complexity"] == "high"


class TestExtractObligations:
    def test_found(self):
        s = LegalSummarizer()
        r = s.extract_obligations(
            "cid1",
            parties=["A"],
            clauses=[
                {"type": "obligation",
                 "party": "A",
                 "text": "deliver"},
            ],
        )
        assert r["total_obligations"] == 1

    def test_empty(self):
        s = LegalSummarizer()
        r = s.extract_obligations("cid1")
        assert r["total_obligations"] == 0

    def test_default_party(self):
        s = LegalSummarizer()
        r = s.extract_obligations(
            "cid1",
            parties=["A"],
            clauses=[
                {"type": "obligation",
                 "party": "X",
                 "text": "pay"},
            ],
        )
        assert r["total_obligations"] == 1


class TestExtractFinancialTerms:
    def test_basic(self):
        s = LegalSummarizer()
        r = s.extract_financial_terms(
            "cid1",
            total_value=10000.0,
            penalties=["late fee"],
        )
        assert r["has_financial_terms"] is True
        assert r["penalty_count"] == 1

    def test_no_value(self):
        s = LegalSummarizer()
        r = s.extract_financial_terms("cid1")
        assert r["has_financial_terms"] is False


class TestGetSummary:
    def test_exists(self):
        s = LegalSummarizer()
        s.create_executive_summary(
            "cid1", title="T",
        )
        assert s.get_summary("cid1") is not None

    def test_missing(self):
        s = LegalSummarizer()
        assert s.get_summary("x") is None


# ── ContractComparator ───────────────────


class TestComparatorInit:
    def test_init(self):
        c = ContractComparator()
        assert c.comparison_count == 0
        assert c.version_count == 0


class TestCompareSideBySide:
    def test_basic(self):
        c = ContractComparator()
        r = c.compare_side_by_side(
            "a", "b",
            clauses_a=[
                {"type": "payment"},
                {"type": "liability"},
            ],
            clauses_b=[
                {"type": "payment"},
                {"type": "termination"},
            ],
        )
        assert r["compared"] is True
        assert r["common_count"] == 1
        assert r["only_a_count"] == 1
        assert r["only_b_count"] == 1
        assert c.comparison_count == 1

    def test_identical(self):
        c = ContractComparator()
        clauses = [{"type": "x"}]
        r = c.compare_side_by_side(
            "a", "b",
            clauses_a=clauses,
            clauses_b=clauses,
        )
        assert r["only_a_count"] == 0
        assert r["only_b_count"] == 0


class TestDetectDifferences:
    def test_similar(self):
        c = ContractComparator()
        r = c.detect_differences(
            "hello world foo",
            "hello world bar",
        )
        assert r["similarity_pct"] > 0
        assert r["added_words"] >= 1
        assert r["removed_words"] >= 1

    def test_identical(self):
        c = ContractComparator()
        r = c.detect_differences(
            "same text", "same text",
        )
        assert r["similarity_pct"] == 100.0
        assert r["significant_change"] is False

    def test_different(self):
        c = ContractComparator()
        r = c.detect_differences(
            "alpha beta", "gamma delta",
        )
        assert r["similarity_pct"] == 0.0
        assert r["significant_change"] is True


class TestTrackVersion:
    def test_basic(self):
        c = ContractComparator()
        r = c.track_version(
            "c1", "v1.0",
            changes=["added clause"],
        )
        assert r["tracked"] is True
        assert r["change_count"] == 1
        assert c.version_count == 1

    def test_multiple(self):
        c = ContractComparator()
        c.track_version("c1", "v1.0")
        c.track_version("c1", "v2.0")
        assert c.version_count == 2


class TestHighlightChanges:
    def test_found(self):
        c = ContractComparator()
        c.track_version(
            "c1", "v1.0",
            changes=["old"],
        )
        c.track_version(
            "c1", "v2.0",
            changes=["added liability cap"],
        )
        r = c.highlight_changes(
            "c1",
            old_version="v1.0",
            new_version="v2.0",
        )
        assert r["highlighted"] is True
        assert r["change_count"] == 1

    def test_not_found(self):
        c = ContractComparator()
        r = c.highlight_changes(
            "c1", new_version="v3.0",
        )
        assert r["highlighted"] is False


class TestAnalyzeImpact:
    def test_high(self):
        c = ContractComparator()
        r = c.analyze_impact(
            changes=[
                "Changed liability cap",
                "Updated payment terms",
            ],
        )
        assert r["impact_level"] == "high"
        assert r["high_impact_count"] >= 1

    def test_none(self):
        c = ContractComparator()
        r = c.analyze_impact()
        assert r["impact_level"] == "none"

    def test_medium(self):
        c = ContractComparator()
        r = c.analyze_impact(
            changes=["Fixed typo"],
        )
        assert r["impact_level"] == "medium"


class TestGetVersions:
    def test_exists(self):
        c = ContractComparator()
        c.track_version("c1", "v1.0")
        lst = c.get_versions("c1")
        assert len(lst) == 1

    def test_empty(self):
        c = ContractComparator()
        assert c.get_versions("x") == []


# ── LegalNegotiationAdvisor ──────────────


class TestAdvisorInit:
    def test_init(self):
        a = LegalNegotiationAdvisor()
        assert a.point_count == 0
        assert a.strategy_count == 0


class TestIdentifyNegotiationPoints:
    def test_from_risks(self):
        a = LegalNegotiationAdvisor()
        r = a.identify_negotiation_points(
            "cid1",
            risks=[
                {"description": "no cap",
                 "severity": "high"},
            ],
        )
        assert r["count"] == 1
        assert r["points"][0]["priority"] == (
            "must_have"
        )

    def test_from_clauses(self):
        a = LegalNegotiationAdvisor()
        r = a.identify_negotiation_points(
            "cid1",
            clauses=[
                {"type": "liability"},
                {"type": "payment"},
            ],
        )
        assert r["count"] == 2

    def test_empty(self):
        a = LegalNegotiationAdvisor()
        r = a.identify_negotiation_points(
            "cid1",
        )
        assert r["count"] == 0


class TestSuggestAlternatives:
    def test_liability(self):
        a = LegalNegotiationAdvisor()
        r = a.suggest_alternatives(
            "liability",
        )
        assert r["count"] >= 3

    def test_unknown(self):
        a = LegalNegotiationAdvisor()
        r = a.suggest_alternatives("xyz")
        assert r["count"] >= 3

    def test_payment(self):
        a = LegalNegotiationAdvisor()
        r = a.suggest_alternatives("payment")
        assert r["count"] >= 3


class TestCheckMarketStandards:
    def test_known(self):
        a = LegalNegotiationAdvisor()
        r = a.check_market_standards(
            "payment_terms",
        )
        assert r["market_standard"]["standard"] == (
            "Net 30"
        )

    def test_unknown(self):
        a = LegalNegotiationAdvisor()
        r = a.check_market_standards("xyz")
        assert r["market_standard"]["standard"] == (
            "Varies"
        )


class TestAnalyzeLeverage:
    def test_strong(self):
        a = LegalNegotiationAdvisor()
        r = a.analyze_leverage(
            "cid1",
            our_position="buyer",
            market_alternatives=5,
            urgency="low",
        )
        assert r["level"] == "strong"

    def test_weak(self):
        a = LegalNegotiationAdvisor()
        r = a.analyze_leverage(
            "cid1",
            our_position="sole_source",
            market_alternatives=0,
            urgency="high",
        )
        assert r["level"] == "weak"

    def test_moderate(self):
        a = LegalNegotiationAdvisor()
        r = a.analyze_leverage(
            "cid1",
            our_position="seller",
            market_alternatives=1,
            urgency="medium",
        )
        assert r["level"] == "moderate"


class TestSuggestStrategy:
    def test_strong(self):
        a = LegalNegotiationAdvisor()
        r = a.suggest_strategy(
            "cid1", leverage_level="strong",
        )
        assert r["count"] >= 3
        assert a.strategy_count == 1

    def test_weak(self):
        a = LegalNegotiationAdvisor()
        r = a.suggest_strategy(
            "cid1", leverage_level="weak",
        )
        assert r["count"] >= 3

    def test_with_issues(self):
        a = LegalNegotiationAdvisor()
        r = a.suggest_strategy(
            "cid1",
            key_issues=["liability", "payment"],
        )
        assert r["count"] >= 4


# ── LegalOrchestrator ───────────────────


class TestOrchestratorInit:
    def test_init(self):
        o = LegalOrchestrator()
        assert o.contract_count == 0
        assert o.pipeline_count == 0


class TestAnalyzeContract:
    def test_basic(self):
        o = LegalOrchestrator()
        r = o.analyze_contract(
            title="NDA",
            content="standard terms",
            parties=["A", "B"],
        )
        assert r["analyzed"] is True
        assert r["title"] == "NDA"
        assert r["parties"] == 2
        assert o.contract_count == 1

    def test_with_red_flags(self):
        o = LegalOrchestrator()
        r = o.analyze_contract(
            title="Bad Contract",
            content="unlimited liability "
                    "and sole discretion",
        )
        assert r["red_flags"] >= 2


class TestRunFullPipeline:
    def test_basic(self):
        o = LegalOrchestrator()
        r = o.run_full_pipeline(
            title="SLA",
            content="standard terms",
            parties=["A", "B"],
        )
        assert r["pipeline_complete"] is True
        assert r["compliance_status"] == (
            "not_checked"
        )
        assert o.pipeline_count == 1

    def test_with_regulation(self):
        o = LegalOrchestrator()
        r = o.run_full_pipeline(
            title="SLA",
            regulation="gdpr",
        )
        assert r["compliance_status"] != (
            "not_checked"
        )


class TestGetContractLifecycle:
    def test_existing(self):
        o = LegalOrchestrator()
        r = o.analyze_contract(title="T")
        cid = r["contract_id"]
        lc = o.get_contract_lifecycle(cid)
        assert lc["exists"] is True

    def test_missing(self):
        o = LegalOrchestrator()
        lc = o.get_contract_lifecycle("none")
        assert lc["exists"] is False


class TestOrchestratorAnalytics:
    def test_basic(self):
        o = LegalOrchestrator()
        o.analyze_contract(title="T")
        a = o.get_analytics()
        assert a["contracts_analyzed"] == 1
        assert a["total_contracts"] == 1
        assert a["full_pipelines"] == 0

    def test_after_pipeline(self):
        o = LegalOrchestrator()
        o.run_full_pipeline(title="T")
        a = o.get_analytics()
        assert a["full_pipelines"] == 1
        assert a["contracts_analyzed"] == 1


# ── Config ──────────────────────────────


class TestLegalConfig:
    def test_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.legal_enabled is True
        assert s.risk_threshold == "medium"
        assert s.auto_extract_deadlines is True
        assert s.compliance_check is True
        assert s.comparison_highlight is True


# ── __init__ imports ────────────────────


class TestLegalImports:
    def test_all_imports(self):
        from app.core.legal import (
            ClauseExtractor,
            ContractComparator,
            ContractParser,
            LegalComplianceChecker,
            LegalDeadlineExtractor,
            LegalNegotiationAdvisor,
            LegalOrchestrator,
            LegalSummarizer,
            RiskHighlighter,
        )
        assert ClauseExtractor is not None
        assert ContractComparator is not None
        assert ContractParser is not None
        assert LegalComplianceChecker is not None
        assert LegalDeadlineExtractor is not None
        assert LegalNegotiationAdvisor is not None
        assert LegalOrchestrator is not None
        assert LegalSummarizer is not None
        assert RiskHighlighter is not None
