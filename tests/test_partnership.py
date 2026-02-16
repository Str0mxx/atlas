"""ATLAS Network & Partnership Finder testleri."""

import pytest

from app.core.partnership import (
    ConnectionBroker,
    DealFlowManager,
    IndustryMapper,
    InvestorFinder,
    NetworkingEventFinder,
    PartnerCompatibilityScorer,
    PartnerDiscovery,
    PartnershipOrchestrator,
    PartnershipTracker,
)
from app.models.partnership_models import (
    CompatibilityLevel,
    DealRecord,
    DealStage,
    EventRecord,
    EventType,
    InvestorRecord,
    InvestorType,
    PartnerRecord,
    PartnershipStatus,
    PartnerType,
)


# ── Model Testleri ──


class TestPartnerType:
    """PartnerType enum testleri."""

    def test_values(self) -> None:
        assert PartnerType.STRATEGIC == "strategic"
        assert PartnerType.TECHNOLOGY == "technology"
        assert PartnerType.INVESTOR == "investor"
        assert PartnerType.RESELLER == "reseller"

    def test_member_count(self) -> None:
        assert len(PartnerType) == 6


class TestDealStage:
    """DealStage enum testleri."""

    def test_values(self) -> None:
        assert DealStage.PROSPECT == "prospect"
        assert DealStage.QUALIFIED == "qualified"
        assert DealStage.CLOSED_WON == "closed_won"
        assert DealStage.CLOSED_LOST == "closed_lost"

    def test_member_count(self) -> None:
        assert len(DealStage) == 6


class TestPartnershipStatus:
    """PartnershipStatus enum testleri."""

    def test_values(self) -> None:
        assert PartnershipStatus.EXPLORING == "exploring"
        assert PartnershipStatus.ACTIVE == "active"
        assert PartnershipStatus.TERMINATED == "terminated"

    def test_member_count(self) -> None:
        assert len(PartnershipStatus) == 4


class TestEventType:
    """EventType enum testleri."""

    def test_values(self) -> None:
        assert EventType.CONFERENCE == "conference"
        assert EventType.MEETUP == "meetup"
        assert EventType.WEBINAR == "webinar"

    def test_member_count(self) -> None:
        assert len(EventType) == 4


class TestInvestorType:
    """InvestorType enum testleri."""

    def test_values(self) -> None:
        assert InvestorType.ANGEL == "angel"
        assert InvestorType.VC == "vc"
        assert InvestorType.PE == "pe"
        assert InvestorType.CORPORATE == "corporate"

    def test_member_count(self) -> None:
        assert len(InvestorType) == 5


class TestCompatibilityLevel:
    """CompatibilityLevel enum testleri."""

    def test_values(self) -> None:
        assert CompatibilityLevel.EXCELLENT == "excellent"
        assert CompatibilityLevel.GOOD == "good"
        assert CompatibilityLevel.LOW == "low"

    def test_member_count(self) -> None:
        assert len(CompatibilityLevel) == 4


class TestPartnerRecord:
    """PartnerRecord model testleri."""

    def test_defaults(self) -> None:
        r = PartnerRecord()
        assert r.name == ""
        assert r.partner_type == "strategic"
        assert r.compatibility == 0.0
        assert r.record_id

    def test_custom(self) -> None:
        r = PartnerRecord(
            name="Acme Corp",
            partner_type="technology",
            industry="tech",
            compatibility=0.85,
        )
        assert r.name == "Acme Corp"
        assert r.compatibility == 0.85


class TestDealRecord:
    """DealRecord model testleri."""

    def test_defaults(self) -> None:
        r = DealRecord()
        assert r.stage == "prospect"
        assert r.value == 0.0

    def test_custom(self) -> None:
        r = DealRecord(
            partner_id="p1",
            stage="negotiation",
            value=50000.0,
            probability=0.7,
        )
        assert r.value == 50000.0


class TestEventRecord:
    """EventRecord model testleri."""

    def test_defaults(self) -> None:
        r = EventRecord()
        assert r.event_type == "conference"
        assert r.relevance == 0.0

    def test_custom(self) -> None:
        r = EventRecord(
            name="Tech Summit",
            event_type="conference",
            location="Istanbul",
        )
        assert r.name == "Tech Summit"


class TestInvestorRecord:
    """InvestorRecord model testleri."""

    def test_defaults(self) -> None:
        r = InvestorRecord()
        assert r.investor_type == "vc"
        assert r.portfolio_size == 0

    def test_custom(self) -> None:
        r = InvestorRecord(
            name="Capital Fund",
            investor_type="vc",
            thesis_match=0.9,
            portfolio_size=30,
        )
        assert r.name == "Capital Fund"


# ── PartnerDiscovery Testleri ──


class TestSearchPartners:
    """search_partners testleri."""

    def test_basic(self) -> None:
        d = PartnerDiscovery()
        r = d.search_partners("AI startup", "technology", "TR")
        assert r["discovered"] is True
        assert r["query"] == "AI startup"
        assert r["industry"] == "technology"

    def test_count(self) -> None:
        d = PartnerDiscovery()
        d.search_partners("A")
        d.search_partners("B")
        assert d.discovered_count == 2
        assert d.search_count == 2


class TestFilterByIndustry:
    """filter_by_industry testleri."""

    def test_basic(self) -> None:
        d = PartnerDiscovery()
        d.search_partners("X", "technology")
        r = d.filter_by_industry("technology")
        assert r["filtered"] is True
        assert r["matches"] == 1

    def test_no_matches(self) -> None:
        d = PartnerDiscovery()
        r = d.filter_by_industry("unknown")
        assert r["matches"] == 0


class TestMatchBySize:
    """match_by_size testleri."""

    def test_enterprise(self) -> None:
        d = PartnerDiscovery()
        r = d.match_by_size(min_employees=5000)
        assert r["size_category"] == "enterprise"

    def test_small(self) -> None:
        d = PartnerDiscovery()
        r = d.match_by_size(min_employees=10)
        assert r["size_category"] == "small"


class TestTargetGeography:
    """target_geography testleri."""

    def test_local(self) -> None:
        d = PartnerDiscovery()
        r = d.target_geography("TR", "Istanbul", 50)
        assert r["scope"] == "local"

    def test_national(self) -> None:
        d = PartnerDiscovery()
        r = d.target_geography("TR")
        assert r["scope"] == "national"

    def test_global(self) -> None:
        d = PartnerDiscovery()
        r = d.target_geography()
        assert r["scope"] == "global"


class TestMatchCapabilities:
    """match_capabilities testleri."""

    def test_full_coverage(self) -> None:
        d = PartnerDiscovery()
        r = d.match_capabilities(["ai", "ml"], ["ai", "ml", "data"])
        assert r["coverage"] == 1.0

    def test_partial_coverage(self) -> None:
        d = PartnerDiscovery()
        r = d.match_capabilities(["ai", "ml"], ["ai"])
        assert r["coverage"] == 0.5

    def test_no_required(self) -> None:
        d = PartnerDiscovery()
        r = d.match_capabilities([], ["ai"])
        assert r["coverage"] == 0.0


# ── PartnerCompatibilityScorer Testleri ──


class TestCalculateCompatibility:
    """calculate_compatibility testleri."""

    def test_excellent(self) -> None:
        s = PartnerCompatibilityScorer()
        r = s.calculate_compatibility("p1", 0.9, 0.9, 0.9, 0.9)
        assert r["calculated"] is True
        assert r["level"] == "excellent"
        assert r["score"] == 0.9

    def test_good(self) -> None:
        s = PartnerCompatibilityScorer()
        r = s.calculate_compatibility("p1", 0.7, 0.7, 0.7, 0.5)
        assert r["level"] == "good"

    def test_low(self) -> None:
        s = PartnerCompatibilityScorer()
        r = s.calculate_compatibility("p1", 0.1, 0.1, 0.1, 0.1)
        assert r["level"] == "low"

    def test_count(self) -> None:
        s = PartnerCompatibilityScorer()
        s.calculate_compatibility("p1", 0.5, 0.5, 0.5, 0.5)
        s.calculate_compatibility("p2", 0.5, 0.5, 0.5, 0.5)
        assert s.score_count == 2


class TestAnalyzeSynergy:
    """analyze_synergy testleri."""

    def test_complementary(self) -> None:
        s = PartnerCompatibilityScorer()
        r = s.analyze_synergy("p1", ["ai", "data"], ["marketing", "sales"])
        assert r["analyzed"] is True
        assert "ai" in r["complementary"]

    def test_overlapping(self) -> None:
        s = PartnerCompatibilityScorer()
        r = s.analyze_synergy("p1", ["ai", "data"], ["ai", "marketing"])
        assert "ai" in r["overlapping"]


class TestAssessRisk:
    """assess_risk testleri."""

    def test_high_risk(self) -> None:
        s = PartnerCompatibilityScorer()
        r = s.assess_risk("p1", 0.9, 0.8, 0.7)
        assert r["assessed"] is True
        assert r["risk_level"] == "high"

    def test_low_risk(self) -> None:
        s = PartnerCompatibilityScorer()
        r = s.assess_risk("p1", 0.1, 0.1, 0.1)
        assert r["risk_level"] == "low"

    def test_count(self) -> None:
        s = PartnerCompatibilityScorer()
        s.assess_risk("p1")
        assert s.assessment_count == 1


class TestEvaluateCulturalFit:
    """evaluate_cultural_fit testleri."""

    def test_basic(self) -> None:
        s = PartnerCompatibilityScorer()
        r = s.evaluate_cultural_fit("p1", 0.8, 0.7, 0.9)
        assert r["evaluated"] is True
        assert r["cultural_fit"] == 0.8


class TestCheckStrategicAlignment:
    """check_strategic_alignment testleri."""

    def test_aligned(self) -> None:
        s = PartnerCompatibilityScorer()
        r = s.check_strategic_alignment("p1", 0.8, 0.7, 0.6)
        assert r["checked"] is True
        assert r["aligned"] is True

    def test_not_aligned(self) -> None:
        s = PartnerCompatibilityScorer()
        r = s.check_strategic_alignment("p1", 0.1, 0.1, 0.1)
        assert r["aligned"] is False


# ── IndustryMapper Testleri ──


class TestClassifyIndustry:
    """classify_industry testleri."""

    def test_technology(self) -> None:
        m = IndustryMapper()
        r = m.classify_industry("TechCo", "software ai saas")
        assert r["classified"] is True
        assert r["industry"] == "technology"

    def test_healthcare(self) -> None:
        m = IndustryMapper()
        r = m.classify_industry("HealthCo", "medical health")
        assert r["industry"] == "healthcare"

    def test_general(self) -> None:
        m = IndustryMapper()
        r = m.classify_industry("GenCo", "consulting services")
        assert r["industry"] == "general"

    def test_count(self) -> None:
        m = IndustryMapper()
        m.classify_industry("A", "tech")
        assert m.classified_count == 1


class TestMapValueChain:
    """map_value_chain testleri."""

    def test_default_stages(self) -> None:
        m = IndustryMapper()
        r = m.map_value_chain("retail")
        assert r["mapped"] is True
        assert r["stage_count"] == 5

    def test_custom_stages(self) -> None:
        m = IndustryMapper()
        r = m.map_value_chain("tech", ["design", "develop", "deploy"])
        assert r["stage_count"] == 3


class TestAnalyzeEcosystem:
    """analyze_ecosystem testleri."""

    def test_dense(self) -> None:
        m = IndustryMapper()
        r = m.analyze_ecosystem("tech", [f"p{i}" for i in range(15)])
        assert r["density"] == "dense"

    def test_sparse(self) -> None:
        m = IndustryMapper()
        r = m.analyze_ecosystem("niche", ["a", "b"])
        assert r["density"] == "sparse"


class TestIdentifyTrends:
    """identify_trends testleri."""

    def test_basic(self) -> None:
        m = IndustryMapper()
        r = m.identify_trends("tech", ["ai", "blockchain"])
        assert r["identified"] is True
        assert r["trend_count"] == 2


class TestSpotOpportunity:
    """spot_opportunity testleri."""

    def test_basic(self) -> None:
        m = IndustryMapper()
        r = m.spot_opportunity("tech", "AI gap", 100000.0)
        assert r["spotted"] is True
        assert r["potential_value"] == 100000.0

    def test_count(self) -> None:
        m = IndustryMapper()
        m.spot_opportunity("a", "gap")
        assert m.opportunity_count == 1


# ── NetworkingEventFinder Testleri ──


class TestDiscoverEvents:
    """discover_events testleri."""

    def test_basic(self) -> None:
        e = NetworkingEventFinder()
        r = e.discover_events("tech", "conference", "Istanbul")
        assert r["discovered"] is True
        assert r["event_type"] == "conference"

    def test_count(self) -> None:
        e = NetworkingEventFinder()
        e.discover_events("tech")
        e.discover_events("health")
        assert e.event_count == 2


class TestScoreEventRelevance:
    """score_relevance testleri."""

    def test_basic(self) -> None:
        e = NetworkingEventFinder()
        r = e.score_relevance("e1", 0.8, 0.7, 0.9)
        assert r["scored"] is True
        assert r["relevance_score"] > 0


class TestTrackRegistration:
    """track_registration testleri."""

    def test_basic(self) -> None:
        e = NetworkingEventFinder()
        r = e.track_registration("e1", "registered", 500.0)
        assert r["tracked"] is True
        assert r["cost"] == 500.0

    def test_count(self) -> None:
        e = NetworkingEventFinder()
        e.track_registration("e1")
        assert e.registration_count == 1


class TestIntegrateCalendar:
    """integrate_calendar testleri."""

    def test_basic(self) -> None:
        e = NetworkingEventFinder()
        r = e.integrate_calendar("e1", "2025-03-15")
        assert r["integrated"] is True
        assert r["reminder"] is True


class TestTrackEventROI:
    """track_roi testleri."""

    def test_basic(self) -> None:
        e = NetworkingEventFinder()
        r = e.track_roi("e1", 1000.0, 20, 3)
        assert r["tracked"] is True
        assert r["cost_per_connection"] == 50.0

    def test_no_connections(self) -> None:
        e = NetworkingEventFinder()
        r = e.track_roi("e1", 500.0, 0, 0)
        assert r["cost_per_connection"] == 0.0


# ── ConnectionBroker Testleri ──


class TestFacilitateIntro:
    """facilitate_intro testleri."""

    def test_basic(self) -> None:
        b = ConnectionBroker()
        r = b.facilitate_intro("Alice", "Bob", "partnership")
        assert r["facilitated"] is True
        assert r["person_a"] == "Alice"

    def test_count(self) -> None:
        b = ConnectionBroker()
        b.facilitate_intro("A", "B")
        b.facilitate_intro("C", "D")
        assert b.intro_count == 2


class TestFindWarmPaths:
    """find_warm_paths testleri."""

    def test_basic(self) -> None:
        b = ConnectionBroker()
        r = b.find_warm_paths("target", ["a", "b", "c", "d"])
        assert r["searched"] is True
        assert r["paths_found"] == 3

    def test_empty_network(self) -> None:
        b = ConnectionBroker()
        r = b.find_warm_paths("target")
        assert r["paths_found"] == 0


class TestFindMutualConnections:
    """find_mutual_connections testleri."""

    def test_basic(self) -> None:
        b = ConnectionBroker()
        r = b.find_mutual_connections(
            "A", "B", ["X", "Y", "Z"], ["Y", "Z", "W"],
        )
        assert r["found"] is True
        assert r["mutual_count"] == 2

    def test_no_mutual(self) -> None:
        b = ConnectionBroker()
        r = b.find_mutual_connections("A", "B", ["X"], ["Y"])
        assert r["mutual_count"] == 0


class TestCreateTemplate:
    """create_template testleri."""

    def test_basic(self) -> None:
        b = ConnectionBroker()
        r = b.create_template("t1", "Hello {name}")
        assert r["created"] is True


class TestTrackFollowup:
    """track_followup testleri."""

    def test_basic(self) -> None:
        b = ConnectionBroker()
        r = b.track_followup("c1", "pending", "Waiting for reply")
        assert r["tracked"] is True

    def test_count(self) -> None:
        b = ConnectionBroker()
        b.track_followup("c1")
        b.track_followup("c2")
        assert b.followup_count == 2


# ── PartnershipTracker Testleri ──


class TestCreatePartnership:
    """create_partnership testleri."""

    def test_basic(self) -> None:
        t = PartnershipTracker()
        r = t.create_partnership("ps1", "Acme Corp", "technology")
        assert r["created"] is True
        assert r["status"] == "active"

    def test_count(self) -> None:
        t = PartnershipTracker()
        t.create_partnership("ps1", "A")
        t.create_partnership("ps2", "B")
        assert t.tracked_count == 2


class TestTrackAgreement:
    """track_agreement testleri."""

    def test_basic(self) -> None:
        t = PartnershipTracker()
        t.create_partnership("ps1", "A")
        r = t.track_agreement("ps1", "Standard terms", 24)
        assert r["tracked"] is True
        assert r["duration_months"] == 24

    def test_not_found(self) -> None:
        t = PartnershipTracker()
        r = t.track_agreement("missing")
        assert r["found"] is False


class TestGetPerformance:
    """get_performance testleri."""

    def test_strong(self) -> None:
        t = PartnershipTracker()
        t.create_partnership("ps1", "A")
        r = t.get_performance("ps1", 10000.0, 50)
        assert r["retrieved"] is True
        assert r["performance"] == "strong"

    def test_weak(self) -> None:
        t = PartnershipTracker()
        t.create_partnership("ps1", "A")
        r = t.get_performance("ps1", 500.0)
        assert r["performance"] == "weak"

    def test_not_found(self) -> None:
        t = PartnershipTracker()
        r = t.get_performance("missing")
        assert r["found"] is False


class TestManageRenewal:
    """manage_renewal testleri."""

    def test_renew(self) -> None:
        t = PartnershipTracker()
        t.create_partnership("ps1", "A")
        r = t.manage_renewal("ps1", "renew")
        assert r["managed"] is True

    def test_terminate(self) -> None:
        t = PartnershipTracker()
        t.create_partnership("ps1", "A")
        r = t.manage_renewal("ps1", "terminate")
        assert r["managed"] is True

    def test_not_found(self) -> None:
        t = PartnershipTracker()
        r = t.manage_renewal("missing")
        assert r["found"] is False

    def test_count(self) -> None:
        t = PartnershipTracker()
        t.create_partnership("ps1", "A")
        t.manage_renewal("ps1")
        assert t.renewal_count == 1


class TestCalculateHealth:
    """calculate_health testleri."""

    def test_healthy(self) -> None:
        t = PartnershipTracker()
        t.create_partnership("ps1", "A")
        r = t.calculate_health("ps1", 0.8, 0.7, 0.9)
        assert r["calculated"] is True
        assert r["status"] == "healthy"

    def test_critical(self) -> None:
        t = PartnershipTracker()
        t.create_partnership("ps1", "A")
        r = t.calculate_health("ps1", 0.1, 0.1, 0.1)
        assert r["status"] == "critical"

    def test_not_found(self) -> None:
        t = PartnershipTracker()
        r = t.calculate_health("missing")
        assert r["found"] is False


# ── DealFlowManager Testleri ──


class TestCreateDeal:
    """create_deal testleri."""

    def test_basic(self) -> None:
        d = DealFlowManager()
        r = d.create_deal("d1", "p1", 50000.0)
        assert r["created"] is True
        assert r["stage"] == "prospect"

    def test_count(self) -> None:
        d = DealFlowManager()
        d.create_deal("d1", "p1")
        d.create_deal("d2", "p2")
        assert d.deal_count == 2


class TestAdvanceStage:
    """advance_stage testleri."""

    def test_basic(self) -> None:
        d = DealFlowManager()
        d.create_deal("d1", "p1")
        r = d.advance_stage("d1")
        assert r["advanced"] is True
        assert r["new_stage"] == "qualified"
        assert r["probability"] == 0.3

    def test_multiple_advances(self) -> None:
        d = DealFlowManager()
        d.create_deal("d1", "p1")
        d.advance_stage("d1")  # qualified
        d.advance_stage("d1")  # proposal
        r = d.advance_stage("d1")  # negotiation
        assert r["new_stage"] == "negotiation"
        assert r["probability"] == 0.7

    def test_not_found(self) -> None:
        d = DealFlowManager()
        r = d.advance_stage("missing")
        assert r["found"] is False


class TestGetConversionRates:
    """get_conversion_rates testleri."""

    def test_basic(self) -> None:
        d = DealFlowManager()
        d.create_deal("d1", "p1")
        d.create_deal("d2", "p2")
        d.advance_stage("d1")
        r = d.get_conversion_rates()
        assert r["calculated"] is True
        assert r["total_deals"] == 2


class TestForecastPipeline:
    """forecast_pipeline testleri."""

    def test_basic(self) -> None:
        d = DealFlowManager()
        d.create_deal("d1", "p1", 10000.0)
        d.create_deal("d2", "p2", 20000.0)
        r = d.forecast_pipeline()
        assert r["forecasted"] is True
        assert r["total_value"] == 30000.0
        assert r["weighted_value"] == 3000.0  # both at 0.1 probability


class TestPrioritizeDeals:
    """prioritize_deals testleri."""

    def test_basic(self) -> None:
        d = DealFlowManager()
        d.create_deal("d1", "p1", 10000.0)
        d.create_deal("d2", "p2", 50000.0)
        r = d.prioritize_deals()
        assert r["prioritized"] is True
        assert r["total_deals"] == 2
        assert r["top_deals"][0]["deal_id"] == "d2"


# ── InvestorFinder Testleri ──


class TestDiscoverInvestors:
    """discover_investors testleri."""

    def test_basic(self) -> None:
        f = InvestorFinder()
        r = f.discover_investors("tech", "vc", "seed")
        assert r["discovered"] is True
        assert r["investor_type"] == "vc"

    def test_count(self) -> None:
        f = InvestorFinder()
        f.discover_investors("tech")
        f.discover_investors("health")
        assert f.found_count == 2


class TestMatchThesis:
    """match_thesis testleri."""

    def test_full_match(self) -> None:
        f = InvestorFinder()
        r = f.match_thesis("i1", ["ai", "saas"], ["ai", "saas", "data"])
        assert r["matched"] is True
        assert r["match_score"] == 1.0

    def test_partial_match(self) -> None:
        f = InvestorFinder()
        r = f.match_thesis("i1", ["ai", "saas"], ["ai"])
        assert r["match_score"] == 0.5

    def test_no_thesis(self) -> None:
        f = InvestorFinder()
        r = f.match_thesis("i1", [], ["ai"])
        assert r["match_score"] == 0.0


class TestAnalyzePortfolio:
    """analyze_portfolio testleri."""

    def test_very_active(self) -> None:
        f = InvestorFinder()
        r = f.analyze_portfolio("i1", [f"c{i}" for i in range(25)])
        assert r["activity_level"] == "very_active"

    def test_selective(self) -> None:
        f = InvestorFinder()
        r = f.analyze_portfolio("i1", ["a", "b"])
        assert r["activity_level"] == "selective"


class TestInvestorWarmPaths:
    """find_warm_paths testleri."""

    def test_basic(self) -> None:
        f = InvestorFinder()
        r = f.find_warm_paths("i1", ["a", "b"])
        assert r["searched"] is True
        assert r["paths_found"] == 2


class TestInvestorOutreach:
    """track_outreach testleri."""

    def test_basic(self) -> None:
        f = InvestorFinder()
        r = f.track_outreach("i1", "sent", "email")
        assert r["tracked"] is True

    def test_count(self) -> None:
        f = InvestorFinder()
        f.track_outreach("i1")
        f.track_outreach("i2")
        assert f.outreach_count == 2


# ── PartnershipOrchestrator Testleri ──


class TestDiscoverAndScore:
    """discover_and_score testleri."""

    def test_basic(self) -> None:
        o = PartnershipOrchestrator()
        r = o.discover_and_score("AI company", "technology")
        assert r["pipeline_complete"] is True
        assert r["compatibility"] > 0

    def test_count(self) -> None:
        o = PartnershipOrchestrator()
        o.discover_and_score("A")
        o.discover_and_score("B")
        assert o.pipeline_count == 2


class TestInitiatePartnership:
    """initiate_partnership testleri."""

    def test_basic(self) -> None:
        o = PartnershipOrchestrator()
        r = o.initiate_partnership("Acme Corp", "strategic")
        assert r["initiated"] is True
        assert r["partner_name"] == "Acme Corp"

    def test_count(self) -> None:
        o = PartnershipOrchestrator()
        o.initiate_partnership("A")
        o.initiate_partnership("B")
        assert o.initiated_count == 2


class TestOrchestratorGetAnalytics:
    """get_analytics testleri."""

    def test_basic(self) -> None:
        o = PartnershipOrchestrator()
        a = o.get_analytics()
        assert "pipelines_run" in a
        assert "partners_discovered" in a
        assert "deals_created" in a
        assert "investors_found" in a

    def test_after_operations(self) -> None:
        o = PartnershipOrchestrator()
        o.discover_and_score("Test")
        o.initiate_partnership("Acme")
        a = o.get_analytics()
        assert a["pipelines_run"] == 1
        assert a["partnerships_initiated"] == 1
        assert a["partnerships_tracked"] == 1
