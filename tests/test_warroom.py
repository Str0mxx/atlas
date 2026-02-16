"""ATLAS Competitive War Room testleri."""

import pytest

from app.models.warroom_models import (
    CompetitorRecord,
    CompetitorStatus,
    IntelRecord,
    IntelSource,
    LaunchPhase,
    PatentRecord,
    PriceAction,
    PriceRecord,
    SignalStrength,
    ThreatLevel,
)
from app.core.warroom import (
    CompetitiveIntelAggregator,
    CompetitorPatentMonitor,
    CompetitorProfileCard,
    CompetitorTracker,
    HiringSignalAnalyzer,
    PriceWatcher,
    ProductLaunchDetector,
    ThreatAssessor,
    WarRoomOrchestrator,
)


# ── Model testleri ──


class TestCompetitorStatus:
    def test_values(self):
        assert CompetitorStatus.ACTIVE == "active"
        assert CompetitorStatus.ACQUIRED == "acquired"

    def test_member_count(self):
        assert len(CompetitorStatus) == 5


class TestThreatLevel:
    def test_values(self):
        assert ThreatLevel.MINIMAL == "minimal"
        assert ThreatLevel.CRITICAL == "critical"

    def test_member_count(self):
        assert len(ThreatLevel) == 5


class TestPriceAction:
    def test_values(self):
        assert PriceAction.INCREASE == "increase"
        assert PriceAction.DISCONTINUED == "discontinued"

    def test_member_count(self):
        assert len(PriceAction) == 5


class TestLaunchPhase:
    def test_values(self):
        assert LaunchPhase.RUMOR == "rumor"
        assert LaunchPhase.MATURE == "mature"

    def test_member_count(self):
        assert len(LaunchPhase) == 5


class TestIntelSource:
    def test_values(self):
        assert IntelSource.NEWS == "news"
        assert IntelSource.WEBSITE_CHANGES == "website_changes"

    def test_member_count(self):
        assert len(IntelSource) == 5


class TestSignalStrength:
    def test_values(self):
        assert SignalStrength.WEAK == "weak"
        assert SignalStrength.VERIFIED == "verified"

    def test_member_count(self):
        assert len(SignalStrength) == 5


class TestCompetitorRecord:
    def test_defaults(self):
        r = CompetitorRecord()
        assert len(r.competitor_id) == 8
        assert r.status == CompetitorStatus.ACTIVE

    def test_custom(self):
        r = CompetitorRecord(name="rival", threat_level=ThreatLevel.HIGH)
        assert r.name == "rival"
        assert r.threat_level == ThreatLevel.HIGH


class TestPriceRecord:
    def test_defaults(self):
        r = PriceRecord()
        assert r.price == 0.0
        assert r.action == PriceAction.STABLE

    def test_custom(self):
        r = PriceRecord(product="widget", price=29.99)
        assert r.product == "widget"


class TestIntelRecord:
    def test_defaults(self):
        r = IntelRecord()
        assert r.source == IntelSource.NEWS
        assert r.signal_strength == SignalStrength.MODERATE

    def test_custom(self):
        r = IntelRecord(content="test intel")
        assert r.content == "test intel"


class TestPatentRecord:
    def test_defaults(self):
        r = PatentRecord()
        assert r.filed_year == 2024

    def test_custom(self):
        r = PatentRecord(title="AI method", technology="ai")
        assert r.title == "AI method"


# ── CompetitorTracker testleri ──


class TestMonitorCompetitor:
    def test_basic(self):
        t = CompetitorTracker()
        r = t.monitor_competitor("Rival Inc", "tech")
        assert r["monitoring"] is True
        assert r["name"] == "Rival Inc"
        assert r["competitor_id"].startswith("comp_")

    def test_count(self):
        t = CompetitorTracker()
        t.monitor_competitor("a")
        t.monitor_competitor("b")
        assert t.competitor_count == 2


class TestTrackActivity:
    def test_basic(self):
        t = CompetitorTracker()
        c = t.monitor_competitor("rival")
        r = t.track_activity(c["competitor_id"], "product_update", "new feature", 0.8)
        assert r["tracked"] is True
        assert r["significance"] == 0.8

    def test_count(self):
        t = CompetitorTracker()
        c = t.monitor_competitor("rival")
        t.track_activity(c["competitor_id"], "a")
        t.track_activity(c["competitor_id"], "b")
        assert t.activity_count == 2


class TestCheckNews:
    def test_basic(self):
        t = CompetitorTracker()
        c = t.monitor_competitor("rival")
        r = t.check_news(c["competitor_id"], ["funding", "launch"])
        assert r["checked"] is True
        assert r["alert_count"] == 2


class TestMonitorSocial:
    def test_basic(self):
        t = CompetitorTracker()
        r = t.monitor_social("c1", ["twitter", "linkedin"])
        assert r["monitored"] is True
        assert r["avg_sentiment"] == 0.6


class TestDetectWebsiteChanges:
    def test_basic(self):
        t = CompetitorTracker()
        r = t.detect_website_changes("c1", ["pricing", "products"])
        assert r["detected"] is True
        assert r["sections_checked"] == 2


# ── PriceWatcher testleri ──


class TestMonitorPrice:
    def test_basic(self):
        w = PriceWatcher()
        r = w.monitor_price("c1", "widget", 29.99)
        assert r["monitored"] is True
        assert r["price"] == 29.99

    def test_count(self):
        w = PriceWatcher()
        w.monitor_price("c1", "a", 10.0)
        w.monitor_price("c1", "b", 20.0)
        assert w.monitor_count == 2


class TestDetectChange:
    def test_increase(self):
        w = PriceWatcher()
        r = w.detect_change("c1", "widget", 100.0, 120.0)
        assert r["detected"] is True
        assert r["direction"] == "increase"
        assert r["change_pct"] == 20.0
        assert r["significant"] is True

    def test_stable(self):
        w = PriceWatcher()
        r = w.detect_change("c1", "widget", 100.0, 100.0)
        assert r["direction"] == "stable"
        assert r["significant"] is False


class TestAnalyzeTrend:
    def test_increasing(self):
        w = PriceWatcher()
        r = w.analyze_trend("c1", "widget", [10, 11, 12, 15, 18, 20])
        assert r["analyzed"] is True
        assert r["trend"] == "increasing"

    def test_insufficient(self):
        w = PriceWatcher()
        r = w.analyze_trend("c1", "widget", [10])
        assert r["analyzed"] is False


class TestComparePrices:
    def test_basic(self):
        w = PriceWatcher()
        r = w.compare_prices(50.0, {"rival_a": 60.0, "rival_b": 40.0})
        assert r["compared"] is True
        assert r["cheaper_than"] == 1
        assert r["total_compared"] == 2


class TestGeneratePriceAlert:
    def test_basic(self):
        w = PriceWatcher()
        r = w.generate_alert("c1", "widget", "price_drop", "high")
        assert r["generated"] is True
        assert r["severity"] == "high"

    def test_count(self):
        w = PriceWatcher()
        w.generate_alert("c1", "a")
        assert w.alert_count == 1


# ── ProductLaunchDetector testleri ──


class TestDetectLaunch:
    def test_high_confidence(self):
        d = ProductLaunchDetector()
        r = d.detect_launch("c1", "new_app", ["press_release", "beta", "landing_page"])
        assert r["detected"] is True
        assert r["confidence"] == "high"

    def test_low_confidence(self):
        d = ProductLaunchDetector()
        r = d.detect_launch("c1", "maybe", ["rumor"])
        assert r["confidence"] == "low"

    def test_count(self):
        d = ProductLaunchDetector()
        d.detect_launch("c1", "p1")
        assert d.launch_count == 1


class TestAnalyzeFeatures:
    def test_behind(self):
        d = ProductLaunchDetector()
        l = d.detect_launch("c1", "test")
        r = d.analyze_features(l["launch_id"], ["a", "b", "c"], ["a"])
        assert r["analyzed"] is True
        assert r["position"] == "behind"

    def test_ahead(self):
        d = ProductLaunchDetector()
        l = d.detect_launch("c1", "test")
        r = d.analyze_features(l["launch_id"], ["a"], ["a", "b", "c"])
        assert r["position"] == "ahead"


class TestReviewPositioning:
    def test_premium(self):
        d = ProductLaunchDetector()
        r = d.review_positioning("l1", "enterprise", "premium")
        assert r["reviewed"] is True
        assert r["segment"] == "high_end"


class TestAssessLaunchImpact:
    def test_critical(self):
        d = ProductLaunchDetector()
        r = d.assess_impact("l1", 0.9, 0.8, 0.7)
        # 0.9*0.4 + 0.8*0.35 + 0.7*0.25 = 0.36+0.28+0.175 = 0.815
        assert r["severity"] == "critical"

    def test_low(self):
        d = ProductLaunchDetector()
        r = d.assess_impact("l1", 0.1, 0.1, 0.1)
        assert r["severity"] == "low"


class TestPlanResponse:
    def test_critical(self):
        d = ProductLaunchDetector()
        r = d.plan_response("l1", "critical")
        assert r["planned"] is True
        assert r["action_count"] == 3

    def test_count(self):
        d = ProductLaunchDetector()
        d.plan_response("l1")
        assert d.response_count == 1


# ── HiringSignalAnalyzer testleri ──


class TestAnalyzePostings:
    def test_basic(self):
        h = HiringSignalAnalyzer()
        r = h.analyze_postings("c1", [
            {"title": "Engineer", "department": "engineering"},
            {"title": "Engineer 2", "department": "engineering"},
            {"title": "Analyst", "department": "data"},
        ])
        assert r["analyzed"] is True
        assert r["total_postings"] == 3
        assert r["top_department"] == "engineering"

    def test_count(self):
        h = HiringSignalAnalyzer()
        h.analyze_postings("c1", [{"title": "a", "department": "b"}])
        assert h.analysis_count == 1


class TestDetectGrowth:
    def test_rapid(self):
        h = HiringSignalAnalyzer()
        r = h.detect_growth("c1", 100, 25)
        assert r["detected"] is True
        assert r["signal"] == "rapid_expansion"

    def test_stable(self):
        h = HiringSignalAnalyzer()
        r = h.detect_growth("c1", 100, 0)
        assert r["signal"] == "stable"


class TestAnalyzeSkills:
    def test_engineering(self):
        h = HiringSignalAnalyzer()
        r = h.analyze_skills("c1", ["python", "react", "docker"])
        assert r["analyzed"] is True
        assert r["primary_focus"] == "engineering"


class TestDetectExpansion:
    def test_major(self):
        h = HiringSignalAnalyzer()
        r = h.detect_expansion("c1", ["NY", "London"], ["AI", "Security"])
        # 2*2 + 2 = 6
        assert r["expansion_level"] == "major"

    def test_none(self):
        h = HiringSignalAnalyzer()
        r = h.detect_expansion("c1")
        assert r["expansion_level"] == "none"


class TestInferDirection:
    def test_product_dev(self):
        h = HiringSignalAnalyzer()
        r = h.infer_direction("c1", "engineering", 25.0)
        assert r["inferred"] is True
        assert r["inferred_direction"] == "product_development"
        assert r["urgency"] == "aggressive"


# ── CompetitorPatentMonitor testleri ──


class TestTrackPatent:
    def test_basic(self):
        m = CompetitorPatentMonitor()
        r = m.track_patent("c1", "AI method", "ai", 2025)
        assert r["tracked"] is True
        assert r["technology"] == "ai"

    def test_count(self):
        m = CompetitorPatentMonitor()
        m.track_patent("c1", "a")
        m.track_patent("c1", "b")
        assert m.patent_count == 2


class TestAnalyzeFilings:
    def test_active(self):
        m = CompetitorPatentMonitor()
        for i in range(6):
            m.track_patent("c1", f"pat_{i}", "ai")
        r = m.analyze_filings("c1")
        assert r["analyzed"] is True
        assert r["activity_level"] == "active"

    def test_inactive(self):
        m = CompetitorPatentMonitor()
        r = m.analyze_filings("c1")
        assert r["activity_level"] == "inactive"


class TestIdentifyTrends:
    def test_basic(self):
        m = CompetitorPatentMonitor()
        r = m.identify_trends([
            {"technology": "ai", "year": 2024},
            {"technology": "ai", "year": 2025},
            {"technology": "blockchain", "year": 2025},
        ])
        assert r["identified"] is True
        assert "ai" in r["trending_technologies"]


class TestMapIPLandscape:
    def test_leader(self):
        m = CompetitorPatentMonitor()
        r = m.map_ip_landscape({"rival": 30}, 50)
        assert r["mapped"] is True
        assert r["leader"] == "us"
        assert r["our_share"] == 62.5


class TestAssessPatentThreat:
    def test_critical(self):
        m = CompetitorPatentMonitor()
        r = m.assess_threat("c1", 0.9, 8, 0.9)
        assert r["assessed"] is True
        assert r["level"] == "critical"

    def test_count(self):
        m = CompetitorPatentMonitor()
        m.assess_threat("c1")
        assert m.threat_count == 1


# ── CompetitorProfileCard testleri ──


class TestCompileProfile:
    def test_basic(self):
        p = CompetitorProfileCard()
        r = p.compile_profile("c1", "Rival Inc", "tech", 2015, "SF", 500)
        assert r["compiled"] is True
        assert r["size_category"] == "mid_market"

    def test_count(self):
        p = CompetitorProfileCard()
        p.compile_profile("c1", "a")
        assert p.profile_count == 1


class TestAnalyzeSWOT:
    def test_favorable(self):
        p = CompetitorProfileCard()
        r = p.analyze_swot("c1", ["strong_brand", "tech"], ["slow"], ["growth"], [])
        assert r["analyzed"] is True
        assert r["outlook"] == "favorable"

    def test_vulnerable(self):
        p = CompetitorProfileCard()
        r = p.analyze_swot("c1", [], ["weak"], [], ["competition"])
        assert r["outlook"] == "vulnerable"

    def test_count(self):
        p = CompetitorProfileCard()
        p.analyze_swot("c1")
        assert p.swot_count == 1


class TestTrackMetrics:
    def test_basic(self):
        p = CompetitorProfileCard()
        p.compile_profile("c1", "test")
        r = p.track_metrics("c1", {"revenue": 1000000, "growth": 0.15})
        assert r["tracked"] is True
        assert r["metrics_tracked"] == 2


class TestAddTimelineEvent:
    def test_basic(self):
        p = CompetitorProfileCard()
        p.compile_profile("c1", "test")
        r = p.add_timeline_event("c1", "Series B funding", "2025-01", 0.9)
        assert r["added"] is True
        assert r["total_events"] == 1


class TestGetQuickReference:
    def test_found(self):
        p = CompetitorProfileCard()
        p.compile_profile("c1", "Rival", "tech")
        p.analyze_swot("c1", ["brand"])
        r = p.get_quick_reference("c1")
        assert r["found"] is True
        assert r["completeness"] == 70  # name(20) + industry(20) + swot(30)

    def test_not_found(self):
        p = CompetitorProfileCard()
        r = p.get_quick_reference("nonexistent")
        assert r["found"] is False


# ── ThreatAssessor testleri ──


class TestScoreThreat:
    def test_critical(self):
        t = ThreatAssessor()
        r = t.score_threat("c1", 0.9, 0.9, 0.8, 0.9)
        assert r["scored"] is True
        assert r["level"] == "critical"

    def test_low(self):
        t = ThreatAssessor()
        r = t.score_threat("c1", 0.1, 0.1, 0.1, 0.1)
        assert r["level"] == "minimal"

    def test_count(self):
        t = ThreatAssessor()
        t.score_threat("c1")
        assert t.assessment_count == 1


class TestEvaluatePosition:
    def test_leader(self):
        t = ThreatAssessor()
        r = t.evaluate_position(0.4, {"a": 0.3, "b": 0.2})
        assert r["position"] == "leader"
        assert r["rank"] == 1

    def test_follower(self):
        t = ThreatAssessor()
        r = t.evaluate_position(0.05, {"a": 0.4, "b": 0.3, "c": 0.2})
        assert r["position"] == "follower"


class TestAnalyzeThreatRisk:
    def test_basic(self):
        t = ThreatAssessor()
        r = t.analyze_risk("c1", [
            {"area": "pricing", "probability": 0.8, "impact": 0.9},
            {"area": "tech", "probability": 0.3, "impact": 0.2},
        ])
        assert r["analyzed"] is True
        assert r["critical_risks"] == 1
        assert r["risks"][0]["area"] == "pricing"


class TestIssueWarning:
    def test_basic(self):
        t = ThreatAssessor()
        r = t.issue_warning("c1", "price_war", "Competitor dropping prices", "high")
        assert r["issued"] is True
        assert r["urgency"] == "high"

    def test_count(self):
        t = ThreatAssessor()
        t.issue_warning("c1")
        assert t.warning_count == 1


class TestPrioritizeResponse:
    def test_basic(self):
        t = ThreatAssessor()
        r = t.prioritize_response([
            {"competitor_id": "a", "score": 0.8, "urgency": "critical"},
            {"competitor_id": "b", "score": 0.9, "urgency": "low"},
        ])
        assert r["ranked"] is True
        assert r["top_priority"] == "a"  # 0.8*3.0=2.4 > 0.9*0.5=0.45


# ── CompetitiveIntelAggregator testleri ──


class TestCollectIntel:
    def test_verified(self):
        a = CompetitiveIntelAggregator()
        r = a.collect_intel("c1", "news", "funding round", 0.9)
        assert r["collected"] is True
        assert r["reliability"] == "verified"

    def test_unconfirmed(self):
        a = CompetitiveIntelAggregator()
        r = a.collect_intel("c1", "rumor", "maybe", 0.2)
        assert r["reliability"] == "unconfirmed"

    def test_count(self):
        a = CompetitiveIntelAggregator()
        a.collect_intel("c1")
        assert a.intel_count == 1


class TestFuseSignals:
    def test_basic(self):
        a = CompetitiveIntelAggregator()
        r = a.fuse_signals("c1", [
            {"source": "news", "confidence": 0.7},
            {"source": "social", "confidence": 0.8},
        ])
        assert r["fused"] is True
        assert r["source_diversity"] == 2
        assert r["fused_confidence"] > 0.75  # avg 0.75 + diversity bonus

    def test_empty(self):
        a = CompetitiveIntelAggregator()
        r = a.fuse_signals("c1", [])
        assert r["fused"] is False


class TestExtractInsights:
    def test_basic(self):
        a = CompetitiveIntelAggregator()
        r = a.extract_insights("c1", [
            {"category": "product", "confidence": 0.8},
            {"category": "product", "confidence": 0.7},
            {"category": "hiring", "confidence": 0.5},
        ])
        assert r["extracted"] is True
        assert r["dominant_theme"] == "product"
        assert r["high_confidence_count"] == 2


class TestGenerateReport:
    def test_basic(self):
        a = CompetitiveIntelAggregator()
        r = a.generate_report("c1", "detailed", ["overview", "threats"])
        assert r["generated"] is True
        assert r["section_count"] == 2

    def test_count(self):
        a = CompetitiveIntelAggregator()
        a.generate_report("c1")
        assert a.report_count == 1


class TestDistributeIntel:
    def test_basic(self):
        a = CompetitiveIntelAggregator()
        r = a.distribute_intel("rpt_1", ["email", "slack"], ["user1", "user2"])
        assert r["distributed"] is True
        assert r["recipient_count"] == 2


# ── WarRoomOrchestrator testleri ──


class TestFullCompetitorAnalysis:
    def test_basic(self):
        o = WarRoomOrchestrator()
        r = o.full_competitor_analysis("Rival Corp", "tech", 0.2)
        assert r["pipeline_complete"] is True
        assert r["name"] == "Rival Corp"
        assert r["threat_level"] in (
            "minimal", "low", "moderate", "high", "critical",
        )

    def test_count(self):
        o = WarRoomOrchestrator()
        o.full_competitor_analysis("a")
        o.full_competitor_analysis("b")
        assert o.pipeline_count == 2
        assert o.analyzed_count == 2


class TestMonitorAndAlert:
    def test_basic(self):
        o = WarRoomOrchestrator()
        c = o.tracker.monitor_competitor("rival")
        r = o.monitor_and_alert(c["competitor_id"])
        assert r["monitored"] is True
        assert r["alert_count"] == 2


class TestWarRoomGetAnalytics:
    def test_initial(self):
        o = WarRoomOrchestrator()
        a = o.get_analytics()
        assert a["pipelines_run"] == 0
        assert a["competitors_tracked"] == 0

    def test_after_operations(self):
        o = WarRoomOrchestrator()
        o.full_competitor_analysis("rival")
        a = o.get_analytics()
        assert a["pipelines_run"] == 1
        assert a["competitors_tracked"] == 1
        assert a["profiles_compiled"] == 1
        assert a["threats_scored"] == 1
        assert a["intel_collected"] == 1
