"""ATLAS Market & Trend Intelligence testleri.

TrendTracker, InvestmentAnalyzer, CompetitorMapper,
PatentScanner, AcademicTracker, RegulationMonitor,
MarketSizeEstimator, SignalAggregator,
MarketIntelOrchestrator testleri.
"""

import pytest


# ===================== TrendTracker =====================

class TestTrendTrackerInit:
    """TrendTracker başlatma testleri."""

    def test_init(self):
        from app.core.marketintel.trend_tracker import TrendTracker
        tt = TrendTracker()
        assert tt.trend_count == 0
        assert tt.alert_count == 0


class TestTrendTrackerDetect:
    """TrendTracker tespit testleri."""

    def test_detect_trend(self):
        from app.core.marketintel.trend_tracker import TrendTracker
        tt = TrendTracker()
        result = tt.detect_trend(
            name="AI in Healthcare",
            data_points=[10, 15, 22, 30, 42],
            category="technology",
        )
        assert result["detected"] is True
        assert result["trend_id"].startswith("tr_")
        assert result["stage"] in tt.STAGES
        assert tt.trend_count == 1

    def test_detect_declining_trend(self):
        from app.core.marketintel.trend_tracker import TrendTracker
        tt = TrendTracker()
        result = tt.detect_trend(
            name="Legacy Tech",
            data_points=[100, 90, 75, 60, 45],
        )
        assert result["momentum"] < 0

    def test_detect_stable_trend(self):
        from app.core.marketintel.trend_tracker import TrendTracker
        tt = TrendTracker()
        result = tt.detect_trend(
            name="Stable Market",
            data_points=[50, 50, 50, 50, 50],
        )
        assert result["momentum"] == 0.0


class TestTrendTrackerAnalysis:
    """TrendTracker analiz testleri."""

    def test_analyze_momentum(self):
        from app.core.marketintel.trend_tracker import TrendTracker
        tt = TrendTracker()
        t = tt.detect_trend("T1", [10, 20, 30])
        result = tt.analyze_momentum(t["trend_id"])
        assert "momentum" in result
        assert "direction" in result
        assert result["direction"] == "up"

    def test_analyze_momentum_not_found(self):
        from app.core.marketintel.trend_tracker import TrendTracker
        tt = TrendTracker()
        result = tt.analyze_momentum("nonexistent")
        assert result["error"] == "trend_not_found"

    def test_get_lifecycle_stage(self):
        from app.core.marketintel.trend_tracker import TrendTracker
        tt = TrendTracker()
        t = tt.detect_trend("T1", [10, 20, 30, 50])
        result = tt.get_lifecycle_stage(t["trend_id"])
        assert "stage" in result

    def test_predict(self):
        from app.core.marketintel.trend_tracker import TrendTracker
        tt = TrendTracker()
        t = tt.detect_trend("T1", [10, 20, 30])
        result = tt.predict(t["trend_id"], periods=3)
        assert len(result["predictions"]) == 3
        assert result["predictions"][0] > 30

    def test_predict_not_found(self):
        from app.core.marketintel.trend_tracker import TrendTracker
        tt = TrendTracker()
        result = tt.predict("nonexistent")
        assert result["error"] == "trend_not_found"


class TestTrendTrackerAlert:
    """TrendTracker uyarı testleri."""

    def test_generate_alert(self):
        from app.core.marketintel.trend_tracker import TrendTracker
        tt = TrendTracker()
        t = tt.detect_trend("T1", [10, 20, 30])
        result = tt.generate_alert(
            t["trend_id"],
            alert_type="momentum_shift",
        )
        assert result["generated"] is True
        assert tt.alert_count == 1

    def test_add_data_point(self):
        from app.core.marketintel.trend_tracker import TrendTracker
        tt = TrendTracker()
        t = tt.detect_trend("T1", [10, 20])
        result = tt.add_data_point(t["trend_id"], 35)
        assert result["added"] is True
        assert result["total_points"] == 3

    def test_get_trends_filter(self):
        from app.core.marketintel.trend_tracker import TrendTracker
        tt = TrendTracker()
        tt.detect_trend("T1", [10, 20], category="tech")
        tt.detect_trend("T2", [5, 10], category="health")
        results = tt.get_trends(category="tech")
        assert len(results) == 1


# ===================== InvestmentAnalyzer =====================

class TestInvestmentAnalyzerInit:
    """InvestmentAnalyzer başlatma testleri."""

    def test_init(self):
        from app.core.marketintel.investment_analyzer import InvestmentAnalyzer
        ia = InvestmentAnalyzer()
        assert ia.investment_count == 0
        assert ia.investor_count == 0


class TestInvestmentAnalyzerTrack:
    """InvestmentAnalyzer takip testleri."""

    def test_track_investment(self):
        from app.core.marketintel.investment_analyzer import InvestmentAnalyzer
        ia = InvestmentAnalyzer()
        result = ia.track_investment(
            company="TechCo",
            amount=5_000_000,
            round_type="series_a",
            sector="technology",
        )
        assert result["tracked"] is True
        assert ia.investment_count == 1

    def test_analyze_patterns(self):
        from app.core.marketintel.investment_analyzer import InvestmentAnalyzer
        ia = InvestmentAnalyzer()
        ia.track_investment("A", 1_000_000, "seed", sector="tech")
        ia.track_investment("B", 5_000_000, "series_a", sector="tech")
        ia.track_investment("C", 500_000, "seed", sector="tech")
        result = ia.analyze_patterns(sector="tech")
        assert result["total_investments"] == 3
        assert result["total_amount"] == 6_500_000

    def test_analyze_patterns_empty(self):
        from app.core.marketintel.investment_analyzer import InvestmentAnalyzer
        ia = InvestmentAnalyzer()
        result = ia.analyze_patterns()
        assert result["total"] == 0

    def test_valuation_trends(self):
        from app.core.marketintel.investment_analyzer import InvestmentAnalyzer
        ia = InvestmentAnalyzer()
        ia.track_investment("Co", 1_000_000, "seed")
        ia.track_investment("Co", 5_000_000, "series_a")
        result = ia.get_valuation_trends(company="Co")
        assert result["trend"] == "increasing"

    def test_map_investor(self):
        from app.core.marketintel.investment_analyzer import InvestmentAnalyzer
        ia = InvestmentAnalyzer()
        result = ia.map_investor(
            name="VC Fund",
            focus_areas=["AI", "SaaS"],
            portfolio_size=50,
        )
        assert result["mapped"] is True
        assert ia.investor_count == 1

    def test_deal_flow(self):
        from app.core.marketintel.investment_analyzer import InvestmentAnalyzer
        ia = InvestmentAnalyzer()
        ia.track_investment("A", 1_000_000, "seed")
        result = ia.analyze_deal_flow(period_days=30)
        assert result["deal_count"] == 1


# ===================== CompetitorMapper =====================

class TestCompetitorMapperInit:
    """CompetitorMapper başlatma testleri."""

    def test_init(self):
        from app.core.marketintel.competitor_mapper import CompetitorMapper
        cm = CompetitorMapper()
        assert cm.competitor_count == 0
        assert cm.movement_count == 0


class TestCompetitorMapperCRUD:
    """CompetitorMapper CRUD testleri."""

    def test_add_competitor(self):
        from app.core.marketintel.competitor_mapper import CompetitorMapper
        cm = CompetitorMapper()
        result = cm.add_competitor(
            name="CompetitorX",
            market="healthcare",
            market_share=25.0,
        )
        assert result["added"] is True
        assert cm.competitor_count == 1

    def test_get_competitor(self):
        from app.core.marketintel.competitor_mapper import CompetitorMapper
        cm = CompetitorMapper()
        added = cm.add_competitor("X", market="tech")
        result = cm.get_competitor(added["competitor_id"])
        assert result["name"] == "X"

    def test_get_competitor_not_found(self):
        from app.core.marketintel.competitor_mapper import CompetitorMapper
        cm = CompetitorMapper()
        result = cm.get_competitor("nonexistent")
        assert result["error"] == "competitor_not_found"

    def test_analyze_positioning_leader(self):
        from app.core.marketintel.competitor_mapper import CompetitorMapper
        cm = CompetitorMapper()
        added = cm.add_competitor("X", market_share=35.0)
        result = cm.analyze_positioning(added["competitor_id"])
        assert result["positioning"] == "leader"

    def test_analyze_positioning_niche(self):
        from app.core.marketintel.competitor_mapper import CompetitorMapper
        cm = CompetitorMapper()
        added = cm.add_competitor("Y", market_share=3.0)
        result = cm.analyze_positioning(added["competitor_id"])
        assert result["positioning"] == "niche"


class TestCompetitorMapperAnalysis:
    """CompetitorMapper analiz testleri."""

    def test_set_strengths_weaknesses(self):
        from app.core.marketintel.competitor_mapper import CompetitorMapper
        cm = CompetitorMapper()
        added = cm.add_competitor("X")
        result = cm.set_strengths_weaknesses(
            added["competitor_id"],
            strengths=["brand", "tech", "funding"],
            weaknesses=["slow"],
        )
        assert result["updated"] is True
        assert result["threat_level"] == "high"

    def test_detect_strategy_cost(self):
        from app.core.marketintel.competitor_mapper import CompetitorMapper
        cm = CompetitorMapper()
        added = cm.add_competitor("X")
        result = cm.detect_strategy(
            added["competitor_id"],
            observations=["Lowering price", "cheap alternative"],
        )
        assert result["strategy"] == "cost_leadership"

    def test_detect_strategy_differentiation(self):
        from app.core.marketintel.competitor_mapper import CompetitorMapper
        cm = CompetitorMapper()
        added = cm.add_competitor("X")
        result = cm.detect_strategy(
            added["competitor_id"],
            observations=["Premium product", "highest quality"],
        )
        assert result["strategy"] == "differentiation"

    def test_track_movement(self):
        from app.core.marketintel.competitor_mapper import CompetitorMapper
        cm = CompetitorMapper()
        added = cm.add_competitor("X")
        result = cm.track_movement(
            added["competitor_id"],
            movement_type="product_launch",
            description="New AI product",
        )
        assert result["tracked"] is True
        assert cm.movement_count == 1

    def test_get_competitors_filter(self):
        from app.core.marketintel.competitor_mapper import CompetitorMapper
        cm = CompetitorMapper()
        cm.add_competitor("X", market="tech")
        cm.add_competitor("Y", market="health")
        results = cm.get_competitors(market="tech")
        assert len(results) == 1


# ===================== PatentScanner =====================

class TestPatentScannerInit:
    """PatentScanner başlatma testleri."""

    def test_init(self):
        from app.core.marketintel.patent_scanner import PatentScanner
        ps = PatentScanner()
        assert ps.patent_count == 0
        assert ps.search_count == 0


class TestPatentScannerScan:
    """PatentScanner tarama testleri."""

    def test_scan_patent(self):
        from app.core.marketintel.patent_scanner import PatentScanner
        ps = PatentScanner()
        result = ps.scan_patent(
            title="AI-based Diagnosis",
            assignee="TechCorp",
            status="granted",
            keywords=["AI", "diagnosis", "healthcare"],
        )
        assert result["scanned"] is True
        assert ps.patent_count == 1

    def test_search_patents(self):
        from app.core.marketintel.patent_scanner import PatentScanner
        ps = PatentScanner()
        ps.scan_patent("AI Diagnosis", keywords=["AI", "medical"])
        ps.scan_patent("Water Filter", keywords=["water", "filter"])
        result = ps.search_patents("AI")
        assert result["total"] == 1

    def test_search_by_assignee(self):
        from app.core.marketintel.patent_scanner import PatentScanner
        ps = PatentScanner()
        ps.scan_patent("P1", assignee="CompA")
        ps.scan_patent("P2", assignee="CompB")
        result = ps.search_patents("P", assignee="CompA")
        assert result["total"] == 1


class TestPatentScannerAnalysis:
    """PatentScanner analiz testleri."""

    def test_analyze_filing_trends(self):
        from app.core.marketintel.patent_scanner import PatentScanner
        ps = PatentScanner()
        ps.scan_patent("P1", status="granted")
        ps.scan_patent("P2", status="pending")
        ps.scan_patent("P3", status="granted")
        result = ps.analyze_filing_trends()
        assert result["total_patents"] == 3
        assert result["status_distribution"]["granted"] == 2

    def test_map_innovation(self):
        from app.core.marketintel.patent_scanner import PatentScanner
        ps = PatentScanner()
        ps.scan_patent("P1", keywords=["AI", "ML"])
        ps.scan_patent("P2", keywords=["AI", "NLP"])
        result = ps.map_innovation()
        assert result["top_keywords"]["AI"] == 2

    def test_freedom_to_operate_clear(self):
        from app.core.marketintel.patent_scanner import PatentScanner
        ps = PatentScanner()
        ps.scan_patent("P1", status="expired", keywords=["old"])
        result = ps.check_freedom_to_operate(
            technology="new_tech",
            keywords=["new"],
        )
        assert result["freedom"] is True
        assert result["risk_level"] == "low"

    def test_freedom_to_operate_blocked(self):
        from app.core.marketintel.patent_scanner import PatentScanner
        ps = PatentScanner()
        ps.scan_patent("P1", status="granted", keywords=["AI", "ML"])
        result = ps.check_freedom_to_operate(
            technology="AI system",
            keywords=["AI"],
        )
        assert result["freedom"] is False
        assert result["blocking_count"] == 1

    def test_get_competitor_patents(self):
        from app.core.marketintel.patent_scanner import PatentScanner
        ps = PatentScanner()
        ps.scan_patent("P1", assignee="CompA")
        ps.scan_patent("P2", assignee="CompB")
        ps.scan_patent("P3", assignee="CompA")
        results = ps.get_competitor_patents("CompA")
        assert len(results) == 2


# ===================== AcademicTracker =====================

class TestAcademicTrackerInit:
    """AcademicTracker başlatma testleri."""

    def test_init(self):
        from app.core.marketintel.academic_tracker import AcademicTracker
        at = AcademicTracker()
        assert at.publication_count == 0
        assert at.author_count == 0


class TestAcademicTrackerTrack:
    """AcademicTracker takip testleri."""

    def test_track_publication(self):
        from app.core.marketintel.academic_tracker import AcademicTracker
        at = AcademicTracker()
        result = at.track_publication(
            title="Deep Learning in Medicine",
            authors=["Dr. Smith", "Dr. Jones"],
            journal="Nature",
            citations=150,
        )
        assert result["tracked"] is True
        assert at.publication_count == 1

    def test_analyze_publications(self):
        from app.core.marketintel.academic_tracker import AcademicTracker
        at = AcademicTracker()
        at.track_publication("P1", ["A1"], citations=50, keywords=["AI"])
        at.track_publication("P2", ["A2"], citations=30, keywords=["ML"])
        result = at.analyze_publications()
        assert result["total_publications"] == 2
        assert result["total_citations"] == 80

    def test_analyze_by_keyword(self):
        from app.core.marketintel.academic_tracker import AcademicTracker
        at = AcademicTracker()
        at.track_publication("AI Research", ["A1"], keywords=["AI"])
        at.track_publication("Water Study", ["A2"], keywords=["water"])
        result = at.analyze_publications(keyword="AI")
        assert result["total_publications"] == 1

    def test_map_author(self):
        from app.core.marketintel.academic_tracker import AcademicTracker
        at = AcademicTracker()
        result = at.map_author(
            name="Dr. Smith",
            institution="MIT",
            h_index=45,
        )
        assert result["mapped"] is True
        assert at.author_count == 1


class TestAcademicTrackerCitation:
    """AcademicTracker atıf testleri."""

    def test_citation_trends_publication(self):
        from app.core.marketintel.academic_tracker import AcademicTracker
        at = AcademicTracker()
        pub = at.track_publication("P1", ["A1"], citations=100)
        result = at.get_citation_trends(pub["publication_id"])
        assert result["impact"] == "high"

    def test_citation_trends_general(self):
        from app.core.marketintel.academic_tracker import AcademicTracker
        at = AcademicTracker()
        at.track_publication("P1", ["A1"], year=2023, citations=50)
        at.track_publication("P2", ["A2"], year=2024, citations=80)
        result = at.get_citation_trends()
        assert 2023 in result["citations_by_year"]

    def test_detect_breakthroughs(self):
        from app.core.marketintel.academic_tracker import AcademicTracker
        at = AcademicTracker()
        at.track_publication("Breakthrough!", ["A1"], citations=200)
        at.track_publication("Normal paper", ["A2"], citations=5)
        result = at.detect_breakthroughs(citation_threshold=50)
        assert result["count"] == 1
        assert result["breakthroughs"][0]["citations"] == 200

    def test_detect_no_breakthroughs(self):
        from app.core.marketintel.academic_tracker import AcademicTracker
        at = AcademicTracker()
        at.track_publication("P1", ["A1"], citations=10)
        result = at.detect_breakthroughs(citation_threshold=50)
        assert result["count"] == 0


# ===================== RegulationMonitor =====================

class TestRegulationMonitorInit:
    """RegulationMonitor başlatma testleri."""

    def test_init(self):
        from app.core.marketintel.regulation_monitor import RegulationMonitor
        rm = RegulationMonitor()
        assert rm.regulation_count == 0
        assert rm.alert_count == 0


class TestRegulationMonitorTrack:
    """RegulationMonitor takip testleri."""

    def test_track_regulation(self):
        from app.core.marketintel.regulation_monitor import RegulationMonitor
        rm = RegulationMonitor()
        result = rm.track_regulation(
            title="KVKK",
            reg_type="law",
            jurisdiction="TR",
            sectors=["technology", "healthcare"],
        )
        assert result["tracked"] is True
        assert rm.regulation_count == 1

    def test_track_policy_change(self):
        from app.core.marketintel.regulation_monitor import RegulationMonitor
        rm = RegulationMonitor()
        reg = rm.track_regulation("GDPR", sectors=["all"])
        result = rm.track_policy_change(
            reg["regulation_id"],
            change_type="amendment",
            description="New data transfer rules",
        )
        assert result["tracked"] is True

    def test_track_policy_change_not_found(self):
        from app.core.marketintel.regulation_monitor import RegulationMonitor
        rm = RegulationMonitor()
        result = rm.track_policy_change("nonexistent", "update")
        assert result["error"] == "regulation_not_found"


class TestRegulationMonitorImpact:
    """RegulationMonitor etki testleri."""

    def test_assess_compliance_impact(self):
        from app.core.marketintel.regulation_monitor import RegulationMonitor
        rm = RegulationMonitor()
        reg = rm.track_regulation(
            "KVKK", sectors=["technology", "healthcare"],
        )
        result = rm.assess_compliance_impact(
            reg["regulation_id"],
            business_areas=["technology", "finance"],
        )
        assert result["assessed"] is True
        assert result["compliance_needed"] is True
        assert "technology" in result["affected_areas"]

    def test_assess_no_impact(self):
        from app.core.marketintel.regulation_monitor import RegulationMonitor
        rm = RegulationMonitor()
        reg = rm.track_regulation("AgriLaw", sectors=["agriculture"])
        result = rm.assess_compliance_impact(
            reg["regulation_id"],
            business_areas=["technology"],
        )
        assert result["impact_level"] == "low"

    def test_assess_risk(self):
        from app.core.marketintel.regulation_monitor import RegulationMonitor
        rm = RegulationMonitor()
        reg = rm.track_regulation(
            "Major Law",
            sectors=["tech", "health", "finance", "retail"],
            effective_date="2025-01-01",
        )
        result = rm.assess_risk(reg["regulation_id"])
        assert result["risk_level"] == "critical"

    def test_create_timeline_alert(self):
        from app.core.marketintel.regulation_monitor import RegulationMonitor
        rm = RegulationMonitor()
        reg = rm.track_regulation("KVKK")
        result = rm.create_timeline_alert(
            reg["regulation_id"],
            alert_date="2025-06-01",
        )
        assert result["created"] is True
        assert rm.alert_count == 1

    def test_get_regulations_filter(self):
        from app.core.marketintel.regulation_monitor import RegulationMonitor
        rm = RegulationMonitor()
        rm.track_regulation("R1", jurisdiction="TR")
        rm.track_regulation("R2", jurisdiction="EU")
        results = rm.get_regulations(jurisdiction="TR")
        assert len(results) == 1


# ===================== MarketSizeEstimator =====================

class TestMarketSizeEstimatorInit:
    """MarketSizeEstimator başlatma testleri."""

    def test_init(self):
        from app.core.marketintel.market_size_estimator import MarketSizeEstimator
        mse = MarketSizeEstimator()
        assert mse.estimate_count == 0
        assert mse.projection_count == 0


class TestMarketSizeEstimatorTAM:
    """MarketSizeEstimator TAM/SAM/SOM testleri."""

    def test_estimate_tam_sam_som(self):
        from app.core.marketintel.market_size_estimator import MarketSizeEstimator
        mse = MarketSizeEstimator()
        result = mse.estimate_tam_sam_som(
            market_name="Medical Tourism",
            tam=10_000_000_000,
            sam_ratio=0.2,
            som_ratio=0.05,
        )
        assert result["estimated"] is True
        assert result["tam"] == 10_000_000_000
        assert result["sam"] == 2_000_000_000
        assert result["som"] == 500_000_000
        assert mse.estimate_count == 1

    def test_project_growth(self):
        from app.core.marketintel.market_size_estimator import MarketSizeEstimator
        mse = MarketSizeEstimator()
        est = mse.estimate_tam_sam_som("Test", tam=1_000_000)
        result = mse.project_growth(
            est["estimate_id"],
            growth_rate=0.1,
            years=3,
        )
        assert result["projected"] is True
        assert len(result["projections"]) == 3
        assert result["final_tam"] > 1_000_000

    def test_project_growth_not_found(self):
        from app.core.marketintel.market_size_estimator import MarketSizeEstimator
        mse = MarketSizeEstimator()
        result = mse.project_growth("nonexistent", 0.1)
        assert result["error"] == "estimate_not_found"


class TestMarketSizeEstimatorAnalysis:
    """MarketSizeEstimator analiz testleri."""

    def test_analyze_segments(self):
        from app.core.marketintel.market_size_estimator import MarketSizeEstimator
        mse = MarketSizeEstimator()
        result = mse.analyze_segments(
            market_name="Cosmetics",
            segments={
                "skincare": 40,
                "fragrance": 30,
                "haircare": 20,
                "makeup": 10,
            },
        )
        assert result["largest_segment"] == "skincare"
        assert result["largest_share"] == 40.0

    def test_analyze_segments_empty(self):
        from app.core.marketintel.market_size_estimator import MarketSizeEstimator
        mse = MarketSizeEstimator()
        result = mse.analyze_segments("Test", {})
        assert result["largest"] is None

    def test_geographic_breakdown(self):
        from app.core.marketintel.market_size_estimator import MarketSizeEstimator
        mse = MarketSizeEstimator()
        est = mse.estimate_tam_sam_som("Global", tam=1_000_000)
        result = mse.geographic_breakdown(
            est["estimate_id"],
            regions={"EU": 0.4, "US": 0.3, "Asia": 0.3},
        )
        assert result["breakdown"]["EU"] == 400_000

    def test_get_methodology(self):
        from app.core.marketintel.market_size_estimator import MarketSizeEstimator
        mse = MarketSizeEstimator()
        est = mse.estimate_tam_sam_som("Test", tam=1_000_000)
        result = mse.get_methodology(est["estimate_id"])
        assert result["approach"] == "top_down"


# ===================== SignalAggregator =====================

class TestSignalAggregatorInit:
    """SignalAggregator başlatma testleri."""

    def test_init(self):
        from app.core.marketintel.signal_aggregator import SignalAggregator
        sa = SignalAggregator()
        assert sa.signal_count == 0
        assert sa.actionable_count == 0


class TestSignalAggregatorCollect:
    """SignalAggregator toplama testleri."""

    def test_collect_signal(self):
        from app.core.marketintel.signal_aggregator import SignalAggregator
        sa = SignalAggregator()
        result = sa.collect_signal(
            source_type="market",
            title="AI market growing",
            strength=0.8,
        )
        assert result["collected"] is True
        assert result["weighted_strength"] > 0
        assert sa.signal_count == 1

    def test_collect_actionable(self):
        from app.core.marketintel.signal_aggregator import SignalAggregator
        sa = SignalAggregator()
        result = sa.collect_signal(
            source_type="market",
            title="Strong signal",
            strength=0.9,
        )
        assert result["actionable"] is True

    def test_collect_weak_signal(self):
        from app.core.marketintel.signal_aggregator import SignalAggregator
        sa = SignalAggregator()
        result = sa.collect_signal(
            source_type="social",
            title="Weak signal",
            strength=0.3,
        )
        # social weight is 0.3, so 0.3 * 0.3 = 0.09
        assert result["actionable"] is False

    def test_set_source_weight(self):
        from app.core.marketintel.signal_aggregator import SignalAggregator
        sa = SignalAggregator()
        result = sa.set_source_weight("news", 0.8)
        assert result["set"] is True
        assert result["weight"] == 0.8


class TestSignalAggregatorFilter:
    """SignalAggregator filtreleme testleri."""

    def test_filter_noise(self):
        from app.core.marketintel.signal_aggregator import SignalAggregator
        sa = SignalAggregator()
        sa.collect_signal("market", "Strong", strength=0.9)
        sa.collect_signal("social", "Weak", strength=0.1)
        result = sa.filter_noise(threshold=0.3)
        assert result["filtered"] >= 1
        assert result["after"] < result["before"]

    def test_find_correlations(self):
        from app.core.marketintel.signal_aggregator import SignalAggregator
        sa = SignalAggregator()
        sa.collect_signal("market", "AI growth in healthcare sector")
        sa.collect_signal("academic", "AI research in healthcare domain")
        result = sa.find_correlations()
        assert "correlations" in result

    def test_get_actionable_signals(self):
        from app.core.marketintel.signal_aggregator import SignalAggregator
        sa = SignalAggregator()
        sa.collect_signal("market", "Strong 1", strength=0.9)
        sa.collect_signal("market", "Strong 2", strength=0.8)
        sa.collect_signal("social", "Weak", strength=0.1)
        results = sa.get_actionable_signals()
        assert len(results) >= 2

    def test_get_signals_filter(self):
        from app.core.marketintel.signal_aggregator import SignalAggregator
        sa = SignalAggregator()
        sa.collect_signal("market", "M1", strength=0.5)
        sa.collect_signal("patent", "P1", strength=0.7)
        results = sa.get_signals(source_type="market")
        assert len(results) == 1

    def test_get_summary(self):
        from app.core.marketintel.signal_aggregator import SignalAggregator
        sa = SignalAggregator()
        sa.collect_signal("market", "M1", strength=0.8)
        sa.collect_signal("patent", "P1", strength=0.6)
        summary = sa.get_summary()
        assert summary["total_signals"] == 2
        assert summary["sources"] == 2


# ===================== MarketIntelOrchestrator =====================

class TestMarketIntelOrchestratorInit:
    """MarketIntelOrchestrator başlatma testleri."""

    def test_init(self):
        from app.core.marketintel.marketintel_orchestrator import MarketIntelOrchestrator
        orch = MarketIntelOrchestrator()
        assert orch.scan_count == 0
        assert orch.trends is not None
        assert orch.competitors is not None
        assert orch.signals is not None


class TestMarketIntelOrchestratorScan:
    """MarketIntelOrchestrator tarama testleri."""

    def test_scan_market_full(self):
        from app.core.marketintel.marketintel_orchestrator import MarketIntelOrchestrator
        orch = MarketIntelOrchestrator()
        result = orch.scan_market(
            market_name="Medical Tourism",
            data_points=[100, 120, 150, 180],
            competitors=[
                {"name": "CompA", "market_share": 30},
                {"name": "CompB", "market_share": 20},
            ],
            tam=5_000_000_000,
        )
        assert result["success"] is True
        assert result["trend_detected"] is True
        assert result["competitors_added"] == 2
        assert result["market_estimated"] is True
        assert orch.scan_count == 1

    def test_scan_market_minimal(self):
        from app.core.marketintel.marketintel_orchestrator import MarketIntelOrchestrator
        orch = MarketIntelOrchestrator()
        result = orch.scan_market(market_name="Test")
        assert result["success"] is True
        assert result["competitors_added"] == 0

    def test_analyze_competitive_landscape(self):
        from app.core.marketintel.marketintel_orchestrator import MarketIntelOrchestrator
        orch = MarketIntelOrchestrator()
        orch.competitors.add_competitor("X", market="tech", market_share=25)
        orch.competitors.add_competitor("Y", market="tech", market_share=15)
        result = orch.analyze_competitive_landscape("tech")
        assert result["competitors"] == 2
        assert result["total_market_share"] == 40.0


class TestMarketIntelOrchestratorPredict:
    """MarketIntelOrchestrator tahmin testleri."""

    def test_predict_trends(self):
        from app.core.marketintel.marketintel_orchestrator import MarketIntelOrchestrator
        orch = MarketIntelOrchestrator()
        orch.trends.detect_trend("T1", [10, 20, 30])
        result = orch.predict_trends(periods=3)
        assert result["trends"] == 1
        assert len(result["predictions"]) == 1

    def test_generate_alerts(self):
        from app.core.marketintel.marketintel_orchestrator import MarketIntelOrchestrator
        orch = MarketIntelOrchestrator()
        orch.trends.detect_trend(
            "Fast Trend", [10, 20, 40, 80],
        )
        orch.signals.collect_signal("market", "Alert", strength=0.9)
        result = orch.generate_alerts()
        assert result["count"] >= 1

    def test_get_analytics(self):
        from app.core.marketintel.marketintel_orchestrator import MarketIntelOrchestrator
        orch = MarketIntelOrchestrator()
        orch.scan_market("Test", data_points=[10, 20])
        analytics = orch.get_analytics()
        assert analytics["scans_completed"] == 1
        assert "trends_tracked" in analytics
        assert "competitors_mapped" in analytics

    def test_get_status(self):
        from app.core.marketintel.marketintel_orchestrator import MarketIntelOrchestrator
        orch = MarketIntelOrchestrator()
        status = orch.get_status()
        assert "scans_completed" in status
        assert "trends" in status
        assert "actionable_signals" in status


# ===================== Imports & Models & Config =====================

class TestMarketIntelImports:
    """Import testleri."""

    def test_import_all(self):
        from app.core.marketintel import (
            AcademicTracker,
            CompetitorMapper,
            InvestmentAnalyzer,
            MarketIntelOrchestrator,
            MarketSizeEstimator,
            PatentScanner,
            RegulationMonitor,
            SignalAggregator,
            TrendTracker,
        )
        assert AcademicTracker is not None
        assert CompetitorMapper is not None
        assert InvestmentAnalyzer is not None
        assert MarketIntelOrchestrator is not None
        assert MarketSizeEstimator is not None
        assert PatentScanner is not None
        assert RegulationMonitor is not None
        assert SignalAggregator is not None
        assert TrendTracker is not None


class TestMarketIntelModels:
    """Model testleri."""

    def test_trend_stage_enum(self):
        from app.models.marketintel_models import TrendStage
        assert TrendStage.EMERGING == "emerging"
        assert TrendStage.DECLINING == "declining"

    def test_signal_type_enum(self):
        from app.models.marketintel_models import SignalType
        assert SignalType.MARKET == "market"
        assert SignalType.PATENT == "patent"

    def test_competitor_threat_enum(self):
        from app.models.marketintel_models import CompetitorThreat
        assert CompetitorThreat.HIGH == "high"

    def test_patent_status_enum(self):
        from app.models.marketintel_models import PatentStatus
        assert PatentStatus.GRANTED == "granted"

    def test_regulation_type_enum(self):
        from app.models.marketintel_models import RegulationType
        assert RegulationType.LAW == "law"

    def test_market_segment_enum(self):
        from app.models.marketintel_models import MarketSegment
        assert MarketSegment.TAM == "tam"

    def test_trend_record(self):
        from app.models.marketintel_models import TrendRecord
        rec = TrendRecord(name="AI Trend")
        assert rec.name == "AI Trend"
        assert len(rec.trend_id) == 8

    def test_competitor_record(self):
        from app.models.marketintel_models import CompetitorRecord
        rec = CompetitorRecord(name="CompX")
        assert rec.name == "CompX"
        assert rec.threat_level == "unknown"

    def test_signal_record(self):
        from app.models.marketintel_models import SignalRecord
        rec = SignalRecord(source="news")
        assert rec.source == "news"

    def test_marketintel_snapshot(self):
        from app.models.marketintel_models import MarketIntelSnapshot
        snap = MarketIntelSnapshot()
        assert snap.trends_tracked == 0
        assert snap.timestamp is not None


class TestMarketIntelConfig:
    """Config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.marketintel_enabled is True
        assert s.scan_frequency_hours == 24
        assert s.competitor_tracking is True
        assert s.patent_alerts is True
        assert s.regulation_monitoring is True
