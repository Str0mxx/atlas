"""MarketingAgent unit testleri.

Google Ads API mock'lanarak marketing agent davranislari test edilir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import TaskResult
from app.agents.marketing_agent import MarketingAgent, _MICRO
from app.core.decision_matrix import ActionType, RiskLevel, UrgencyLevel
from app.models.marketing import (
    AdCheckType,
    AdDisapproval,
    BudgetRecommendation,
    CampaignMetrics,
    KeywordMetrics,
    MarketingAnalysisResult,
    MarketingConfig,
    PerformanceLevel,
)


# === Fixtures ===


@pytest.fixture
def config() -> MarketingConfig:
    """Ornek marketing yapilandirmasi."""
    return MarketingConfig(
        customer_id="1234567890",
        date_range_days=7,
        cpc_threshold=15.0,
        cpa_threshold=200.0,
        roas_min_threshold=2.0,
        ctr_min_threshold=1.0,
        low_quality_score_threshold=4,
        budget_waste_threshold=30.0,
    )


@pytest.fixture
def agent(config: MarketingConfig) -> MarketingAgent:
    """Yapilandirilmis MarketingAgent."""
    return MarketingAgent(config=config)


@pytest.fixture
def excellent_result() -> MarketingAnalysisResult:
    """Mukemmel performansli analiz sonucu."""
    return MarketingAnalysisResult(
        performance_level=PerformanceLevel.EXCELLENT,
        campaigns=[
            CampaignMetrics(
                campaign_id="1",
                campaign_name="Sac Ekimi - Search",
                status="ENABLED",
                impressions=10000,
                clicks=500,
                cost=500 * _MICRO,
                conversions=25.0,
                conversion_value=25000.0,
                cpc=5.0,
                cpa=20.0,
                ctr=5.0,
                roas=50.0,
                daily_budget=100 * _MICRO,
                performance_level=PerformanceLevel.EXCELLENT,
            ),
        ],
        total_spend=500.0,
        total_conversions=25.0,
        total_conversion_value=25000.0,
        overall_roas=50.0,
        overall_ctr=5.0,
    )


@pytest.fixture
def poor_result() -> MarketingAnalysisResult:
    """Dusuk performansli analiz sonucu."""
    return MarketingAnalysisResult(
        performance_level=PerformanceLevel.POOR,
        campaigns=[
            CampaignMetrics(
                campaign_id="2",
                campaign_name="Genel Kampanya",
                status="ENABLED",
                impressions=5000,
                clicks=20,
                cost=300 * _MICRO,
                conversions=1.0,
                conversion_value=100.0,
                cpc=15.0,
                cpa=300.0,
                ctr=0.4,
                roas=0.33,
                daily_budget=50 * _MICRO,
                performance_level=PerformanceLevel.POOR,
            ),
        ],
        poor_campaigns=[
            CampaignMetrics(
                campaign_id="2",
                campaign_name="Genel Kampanya",
                performance_level=PerformanceLevel.POOR,
                roas=0.33,
                ctr=0.4,
                cpa=300.0,
            ),
        ],
        total_spend=300.0,
        total_conversions=1.0,
        total_conversion_value=100.0,
        overall_roas=0.33,
        overall_ctr=0.4,
    )


@pytest.fixture
def disapproval_result() -> MarketingAnalysisResult:
    """Reddedilen reklamli analiz sonucu."""
    return MarketingAnalysisResult(
        performance_level=PerformanceLevel.POOR,
        disapprovals=[
            AdDisapproval(
                ad_id="101",
                campaign_name="Dis Tedavisi",
                headline="En Ucuz Dis Beyazlatma",
                policy_topic="healthcare",
                policy_type="DISAPPROVED",
            ),
            AdDisapproval(
                ad_id="102",
                campaign_name="Estetik",
                headline="Garanti Sonuc",
                policy_topic="misleading_claims",
                policy_type="DISAPPROVED",
            ),
        ],
        total_spend=200.0,
        overall_roas=1.5,
    )


# === Kampanya performans degerlendirme testleri ===


class TestCampaignPerformanceEvaluation:
    """_evaluate_campaign_performance testleri."""

    def test_excellent_performance(self, agent: MarketingAgent) -> None:
        """Yuksek ROAS + CTR + dusuk CPC/CPA -> EXCELLENT."""
        perf = agent._evaluate_campaign_performance(
            cpc=3.0, cpa=50.0, roas=5.0, ctr=3.0,
        )
        assert perf == PerformanceLevel.EXCELLENT

    def test_good_performance(self, agent: MarketingAgent) -> None:
        """ROAS >= threshold, iyi CTR -> GOOD."""
        perf = agent._evaluate_campaign_performance(
            cpc=10.0, cpa=150.0, roas=2.5, ctr=1.5,
        )
        assert perf == PerformanceLevel.GOOD

    def test_average_performance(self, agent: MarketingAgent) -> None:
        """ROAS >= 1.0, orta CTR -> AVERAGE."""
        perf = agent._evaluate_campaign_performance(
            cpc=12.0, cpa=180.0, roas=1.2, ctr=1.0,
        )
        assert perf == PerformanceLevel.AVERAGE

    def test_poor_performance(self, agent: MarketingAgent) -> None:
        """Dusuk ROAS, dusuk CTR, yuksek CPC -> POOR."""
        perf = agent._evaluate_campaign_performance(
            cpc=16.0, cpa=180.0, roas=0.8, ctr=0.8,
        )
        # ROAS=0.8 (<1.0 -> 0), CTR=0.8 (<1.0 -> 0), CPC=16 (>15 -> -1), CPA=180 (<200 -> 0)
        # score = -1 -> POOR
        assert perf == PerformanceLevel.POOR

    def test_critical_performance(self, agent: MarketingAgent) -> None:
        """Sifir ROAS, sifir CTR, cok yuksek CPC/CPA -> CRITICAL."""
        perf = agent._evaluate_campaign_performance(
            cpc=25.0, cpa=500.0, roas=0.0, ctr=0.1,
        )
        assert perf == PerformanceLevel.CRITICAL

    def test_high_roas_compensates_high_cpc(self, agent: MarketingAgent) -> None:
        """Yuksek ROAS, yuksek CPC'yi telafi etmeli."""
        perf = agent._evaluate_campaign_performance(
            cpc=20.0, cpa=50.0, roas=4.5, ctr=2.5,
        )
        # ROAS=4.5 (>=4.0 -> +3), CTR=2.5 (>=2.0 -> +2), CPC=20 (>15 -> -1), CPA=50 (<=100 -> +1)
        # score = 3+2-1+1 = 5 -> EXCELLENT
        assert perf == PerformanceLevel.EXCELLENT


# === Anahtar kelime performans degerlendirme testleri ===


class TestKeywordPerformanceEvaluation:
    """_evaluate_keyword_performance testleri."""

    def test_low_quality_score_low_ctr_critical(self, agent: MarketingAgent) -> None:
        """Dusuk kalite puani + dusuk CTR -> CRITICAL."""
        perf = agent._evaluate_keyword_performance(
            quality_score=3, ctr=0.5, cpc=10.0, conversions=0, cost=100.0,
        )
        assert perf == PerformanceLevel.CRITICAL

    def test_low_quality_score_ok_ctr_poor(self, agent: MarketingAgent) -> None:
        """Dusuk kalite puani + iyi CTR -> POOR."""
        perf = agent._evaluate_keyword_performance(
            quality_score=3, ctr=1.5, cpc=10.0, conversions=1.0, cost=100.0,
        )
        assert perf == PerformanceLevel.POOR

    def test_high_cost_zero_conversions_critical(self, agent: MarketingAgent) -> None:
        """Yuksek harcama + sifir donusum -> CRITICAL."""
        perf = agent._evaluate_keyword_performance(
            quality_score=6, ctr=1.5, cpc=15.0, conversions=0, cost=250.0,
        )
        assert perf == PerformanceLevel.CRITICAL

    def test_very_low_ctr_poor(self, agent: MarketingAgent) -> None:
        """Cok dusuk CTR -> POOR."""
        perf = agent._evaluate_keyword_performance(
            quality_score=6, ctr=0.3, cpc=5.0, conversions=1.0, cost=50.0,
        )
        assert perf == PerformanceLevel.POOR

    def test_high_quality_good_ctr_good(self, agent: MarketingAgent) -> None:
        """Yuksek kalite puani + iyi CTR -> GOOD."""
        perf = agent._evaluate_keyword_performance(
            quality_score=8, ctr=2.0, cpc=5.0, conversions=5.0, cost=100.0,
        )
        assert perf == PerformanceLevel.GOOD

    def test_mid_range_average(self, agent: MarketingAgent) -> None:
        """Orta kalite + orta CTR -> AVERAGE."""
        perf = agent._evaluate_keyword_performance(
            quality_score=6, ctr=1.0, cpc=10.0, conversions=2.0, cost=100.0,
        )
        assert perf == PerformanceLevel.AVERAGE

    def test_zero_quality_score_treated_as_unknown(self, agent: MarketingAgent) -> None:
        """Kalite puani 0 (bilinmiyor) dusuk olarak degerlendirilmemeli."""
        perf = agent._evaluate_keyword_performance(
            quality_score=0, ctr=1.5, cpc=5.0, conversions=3.0, cost=50.0,
        )
        # QS=0 atlanir, cost=50 < cpa_threshold=200, conversions > 0, CTR >= threshold
        assert perf == PerformanceLevel.AVERAGE


# === Genel performans seviyesi hesaplama testleri ===


class TestOverallPerformance:
    """_calculate_overall_performance testleri."""

    def test_excellent_roas(self, agent: MarketingAgent) -> None:
        """ROAS >= threshold*2 -> EXCELLENT."""
        result = MarketingAnalysisResult(overall_roas=5.0)
        assert agent._calculate_overall_performance(result) == PerformanceLevel.EXCELLENT

    def test_good_roas(self, agent: MarketingAgent) -> None:
        """ROAS >= threshold -> GOOD."""
        result = MarketingAnalysisResult(overall_roas=2.5)
        assert agent._calculate_overall_performance(result) == PerformanceLevel.GOOD

    def test_average_roas(self, agent: MarketingAgent) -> None:
        """ROAS >= 1.0 -> AVERAGE."""
        result = MarketingAnalysisResult(overall_roas=1.3)
        assert agent._calculate_overall_performance(result) == PerformanceLevel.AVERAGE

    def test_poor_roas(self, agent: MarketingAgent) -> None:
        """ROAS > 0 ama < 1.0 -> POOR."""
        result = MarketingAnalysisResult(overall_roas=0.5)
        assert agent._calculate_overall_performance(result) == PerformanceLevel.POOR

    def test_zero_roas(self, agent: MarketingAgent) -> None:
        """ROAS == 0 -> CRITICAL."""
        result = MarketingAnalysisResult(overall_roas=0.0)
        assert agent._calculate_overall_performance(result) == PerformanceLevel.CRITICAL

    def test_disapprovals_override_good_roas(self, agent: MarketingAgent) -> None:
        """Reddedilen reklam varsa ROAS ne olursa olsun dusurulmeli."""
        result = MarketingAnalysisResult(
            overall_roas=5.0,
            disapprovals=[
                AdDisapproval(ad_id="1", headline="Test", policy_topic="test"),
            ],
        )
        assert agent._calculate_overall_performance(result) == PerformanceLevel.POOR

    def test_many_disapprovals_critical(self, agent: MarketingAgent) -> None:
        """3+ reddedilen reklam -> CRITICAL."""
        result = MarketingAnalysisResult(
            overall_roas=5.0,
            disapprovals=[
                AdDisapproval(ad_id=str(i), headline=f"Ad {i}", policy_topic="t")
                for i in range(3)
            ],
        )
        assert agent._calculate_overall_performance(result) == PerformanceLevel.CRITICAL

    def test_poor_campaign_ratio_downgrades(self, agent: MarketingAgent) -> None:
        """Dusuk performansli kampanya orani %50+ -> EXCELLENT/GOOD dusurulmeli."""
        good = CampaignMetrics(campaign_id="1", performance_level=PerformanceLevel.GOOD)
        poor = CampaignMetrics(campaign_id="2", performance_level=PerformanceLevel.POOR)
        result = MarketingAnalysisResult(
            overall_roas=5.0,
            campaigns=[good, poor],
            poor_campaigns=[poor],
        )
        assert agent._calculate_overall_performance(result) == PerformanceLevel.AVERAGE

    def test_poor_campaign_ratio_no_downgrade_for_average(self, agent: MarketingAgent) -> None:
        """AVERAGE zaten dusukse daha fazla dusurulmemeli."""
        poor = CampaignMetrics(campaign_id="1", performance_level=PerformanceLevel.POOR)
        result = MarketingAnalysisResult(
            overall_roas=1.2,
            campaigns=[poor],
            poor_campaigns=[poor],
        )
        # ROAS=1.2 -> AVERAGE, poor_ratio=1.0 ama AVERAGE "good/excellent" degil -> dusurme yok
        assert agent._calculate_overall_performance(result) == PerformanceLevel.AVERAGE


# === Risk/Aciliyet eslestirme testleri ===


class TestRiskUrgencyMapping:
    """Performans -> RiskLevel/UrgencyLevel eslestirme testleri."""

    def test_excellent_maps_to_low_low(self) -> None:
        result = MarketingAnalysisResult(performance_level=PerformanceLevel.EXCELLENT)
        risk, urgency = MarketingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.LOW

    def test_good_maps_to_low_low(self) -> None:
        result = MarketingAnalysisResult(performance_level=PerformanceLevel.GOOD)
        risk, urgency = MarketingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.LOW

    def test_average_maps_to_low_medium(self) -> None:
        result = MarketingAnalysisResult(performance_level=PerformanceLevel.AVERAGE)
        risk, urgency = MarketingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.MEDIUM

    def test_poor_maps_to_medium_medium(self) -> None:
        result = MarketingAnalysisResult(performance_level=PerformanceLevel.POOR)
        risk, urgency = MarketingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.MEDIUM

    def test_poor_with_budget_waste_escalates_urgency(self) -> None:
        """POOR + ROAS < 1.0 + harcama var -> aciliyet yukselmeli."""
        result = MarketingAnalysisResult(
            performance_level=PerformanceLevel.POOR,
            total_spend=500.0,
            overall_roas=0.5,
        )
        risk, urgency = MarketingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.HIGH

    def test_critical_maps_to_high_high(self) -> None:
        result = MarketingAnalysisResult(performance_level=PerformanceLevel.CRITICAL)
        risk, urgency = MarketingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.HIGH

    def test_disapprovals_override_performance(self) -> None:
        """Reddedilen reklam performans seviyesinden bagimsiz HIGH risk."""
        result = MarketingAnalysisResult(
            performance_level=PerformanceLevel.GOOD,
            disapprovals=[
                AdDisapproval(ad_id="1", headline="Test", policy_topic="test"),
            ],
        )
        risk, urgency = MarketingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.MEDIUM

    def test_many_disapprovals_high_high(self) -> None:
        """3+ reddedilen reklam -> HIGH/HIGH."""
        result = MarketingAnalysisResult(
            performance_level=PerformanceLevel.GOOD,
            disapprovals=[
                AdDisapproval(ad_id=str(i), headline=f"Ad {i}", policy_topic="t")
                for i in range(4)
            ],
        )
        risk, urgency = MarketingAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.HIGH


# === Aksiyon belirleme testleri ===


class TestActionDetermination:
    """Aksiyon tipi belirleme testleri."""

    def test_low_low_logs(self) -> None:
        action = MarketingAgent._determine_action(RiskLevel.LOW, UrgencyLevel.LOW)
        assert action == ActionType.LOG

    def test_low_medium_logs(self) -> None:
        action = MarketingAgent._determine_action(RiskLevel.LOW, UrgencyLevel.MEDIUM)
        assert action == ActionType.LOG

    def test_medium_medium_notifies(self) -> None:
        action = MarketingAgent._determine_action(RiskLevel.MEDIUM, UrgencyLevel.MEDIUM)
        assert action == ActionType.NOTIFY

    def test_medium_high_auto_fix(self) -> None:
        action = MarketingAgent._determine_action(RiskLevel.MEDIUM, UrgencyLevel.HIGH)
        assert action == ActionType.AUTO_FIX

    def test_high_medium_auto_fix(self) -> None:
        action = MarketingAgent._determine_action(RiskLevel.HIGH, UrgencyLevel.MEDIUM)
        assert action == ActionType.AUTO_FIX

    def test_high_high_immediate(self) -> None:
        action = MarketingAgent._determine_action(RiskLevel.HIGH, UrgencyLevel.HIGH)
        assert action == ActionType.IMMEDIATE


# === Butce onerisi testleri ===


class TestBudgetRecommendations:
    """_generate_budget_recommendations testleri."""

    def test_high_performance_budget_increase(self, agent: MarketingAgent) -> None:
        """Yuksek performansli kampanya butce artirimi onerisi almali."""
        result = MarketingAnalysisResult(
            campaigns=[
                CampaignMetrics(
                    campaign_name="Iyi Kampanya",
                    status="ENABLED",
                    performance_level=PerformanceLevel.EXCELLENT,
                    roas=5.0,
                    daily_budget=100 * _MICRO,
                    cost=700 * _MICRO,  # 7 gun icin 100/gun, %100 kullanim
                ),
            ],
        )
        agent._generate_budget_recommendations(result)

        assert len(result.budget_recommendations) == 1
        rec = result.budget_recommendations[0]
        assert rec.recommended_budget > rec.current_budget
        assert "ROAS" in rec.reason

    def test_critical_performance_budget_decrease(self, agent: MarketingAgent) -> None:
        """Kritik dusuk performansli kampanya butce azaltimi onerisi almali."""
        result = MarketingAnalysisResult(
            campaigns=[
                CampaignMetrics(
                    campaign_name="Kotu Kampanya",
                    status="ENABLED",
                    performance_level=PerformanceLevel.CRITICAL,
                    roas=0.1,
                    daily_budget=200 * _MICRO,
                    cost=1400 * _MICRO,
                ),
            ],
        )
        agent._generate_budget_recommendations(result)

        assert len(result.budget_recommendations) == 1
        rec = result.budget_recommendations[0]
        assert rec.recommended_budget < rec.current_budget
        assert rec.priority == 1

    def test_poor_low_roas_budget_decrease(self, agent: MarketingAgent) -> None:
        """POOR + dusuk ROAS -> butce azaltimi onerisi."""
        result = MarketingAnalysisResult(
            campaigns=[
                CampaignMetrics(
                    campaign_name="Orta Kotu",
                    status="ENABLED",
                    performance_level=PerformanceLevel.POOR,
                    roas=1.0,
                    daily_budget=100 * _MICRO,
                    cost=700 * _MICRO,
                ),
            ],
        )
        agent._generate_budget_recommendations(result)

        assert len(result.budget_recommendations) == 1
        rec = result.budget_recommendations[0]
        assert rec.recommended_budget == pytest.approx(70.0)

    def test_paused_campaign_skipped(self, agent: MarketingAgent) -> None:
        """PAUSED kampanya icin oneri uretilmemeli."""
        result = MarketingAnalysisResult(
            campaigns=[
                CampaignMetrics(
                    campaign_name="Durdurulmus",
                    status="PAUSED",
                    performance_level=PerformanceLevel.CRITICAL,
                    daily_budget=100 * _MICRO,
                ),
            ],
        )
        agent._generate_budget_recommendations(result)
        assert len(result.budget_recommendations) == 0

    def test_zero_budget_campaign_skipped(self, agent: MarketingAgent) -> None:
        """Butcesiz kampanya icin oneri uretilmemeli."""
        result = MarketingAnalysisResult(
            campaigns=[
                CampaignMetrics(
                    campaign_name="Butcesiz",
                    status="ENABLED",
                    performance_level=PerformanceLevel.CRITICAL,
                    daily_budget=0,
                ),
            ],
        )
        agent._generate_budget_recommendations(result)
        assert len(result.budget_recommendations) == 0

    def test_average_performance_no_recommendation(self, agent: MarketingAgent) -> None:
        """Orta performansli kampanya icin oneri uretilmemeli."""
        result = MarketingAnalysisResult(
            campaigns=[
                CampaignMetrics(
                    campaign_name="Orta",
                    status="ENABLED",
                    performance_level=PerformanceLevel.AVERAGE,
                    roas=1.5,
                    daily_budget=100 * _MICRO,
                    cost=350 * _MICRO,  # %50 kullanim
                ),
            ],
        )
        agent._generate_budget_recommendations(result)
        assert len(result.budget_recommendations) == 0


# === Ozet olusturma testleri ===


class TestBuildSummary:
    """_build_summary testleri."""

    def test_clean_summary(self, agent: MarketingAgent) -> None:
        """Temiz sonuc ozeti kampanya sayisini icermeli."""
        result = MarketingAnalysisResult(
            campaigns=[CampaignMetrics(campaign_id="1")],
            overall_roas=3.0,
            overall_ctr=2.5,
            total_spend=1000.0,
        )
        summary = agent._build_summary(result)
        assert "1 kampanya" in summary
        assert "ROAS=3.00" in summary
        assert "CTR=2.50%" in summary

    def test_summary_includes_poor_campaigns(self, agent: MarketingAgent) -> None:
        """Ozet dusuk performansli kampanya sayisini gostermeli."""
        poor = CampaignMetrics(campaign_id="1", performance_level=PerformanceLevel.POOR)
        result = MarketingAnalysisResult(
            campaigns=[poor],
            poor_campaigns=[poor],
        )
        summary = agent._build_summary(result)
        assert "dusuk performansli" in summary

    def test_summary_includes_disapprovals(self, agent: MarketingAgent) -> None:
        """Ozet reddedilen reklam sayisini gostermeli."""
        result = MarketingAnalysisResult(
            disapprovals=[
                AdDisapproval(ad_id="1", headline="T", policy_topic="t"),
            ],
        )
        summary = agent._build_summary(result)
        assert "reddedilen" in summary

    def test_summary_includes_budget_recommendations(self, agent: MarketingAgent) -> None:
        """Ozet butce onerisi sayisini gostermeli."""
        result = MarketingAnalysisResult(
            budget_recommendations=[
                BudgetRecommendation(campaign_name="X", current_budget=100, recommended_budget=120),
            ],
        )
        summary = agent._build_summary(result)
        assert "butce onerisi" in summary


# === Analiz testleri ===


class TestAnalyze:
    """analyze() metodu testleri."""

    @pytest.mark.asyncio
    async def test_excellent_analysis(
        self, agent: MarketingAgent, excellent_result: MarketingAnalysisResult,
    ) -> None:
        """Mukemmel performans: LOW risk, LOW urgency, LOG action."""
        analysis = await agent.analyze({"result": excellent_result.model_dump()})
        assert analysis["performance_level"] == PerformanceLevel.EXCELLENT.value
        assert analysis["risk"] == RiskLevel.LOW.value
        assert analysis["urgency"] == UrgencyLevel.LOW.value
        assert analysis["action"] == ActionType.LOG.value

    @pytest.mark.asyncio
    async def test_poor_analysis(
        self, agent: MarketingAgent, poor_result: MarketingAnalysisResult,
    ) -> None:
        """Dusuk performans: MEDIUM risk, bildirim."""
        analysis = await agent.analyze({"result": poor_result.model_dump()})
        assert analysis["risk"] == RiskLevel.MEDIUM.value

    @pytest.mark.asyncio
    async def test_disapproval_analysis(
        self, agent: MarketingAgent, disapproval_result: MarketingAnalysisResult,
    ) -> None:
        """Reddedilen reklam: HIGH risk."""
        analysis = await agent.analyze({"result": disapproval_result.model_dump()})
        assert analysis["risk"] == RiskLevel.HIGH.value
        assert analysis["stats"]["disapproval_count"] == 2

    @pytest.mark.asyncio
    async def test_analysis_issues_list(self, agent: MarketingAgent) -> None:
        """Issues listesi tum bulgu turlerini icermeli."""
        result = MarketingAnalysisResult(
            performance_level=PerformanceLevel.POOR,
            disapprovals=[
                AdDisapproval(
                    ad_id="1", headline="Reddedilen", policy_topic="healthcare",
                ),
            ],
            poor_campaigns=[
                CampaignMetrics(
                    campaign_name="Kotu Kampanya", roas=0.5, ctr=0.3, cpa=300.0,
                ),
            ],
            poor_keywords=[
                KeywordMetrics(
                    keyword_text="kotu kelime", quality_score=2, ctr=0.2,
                ),
            ],
            budget_recommendations=[
                BudgetRecommendation(
                    campaign_name="X", current_budget=100, recommended_budget=50,
                    reason="Dusuk ROAS",
                ),
            ],
        )
        analysis = await agent.analyze({"result": result.model_dump()})
        issues = analysis["issues"]
        assert any("REDDEDILDI" in i for i in issues)
        assert any("Dusuk performans" in i for i in issues)
        assert any("Dusuk kelime" in i for i in issues)
        assert any("Butce onerisi" in i for i in issues)

    @pytest.mark.asyncio
    async def test_analysis_stats(
        self, agent: MarketingAgent, poor_result: MarketingAnalysisResult,
    ) -> None:
        """Analiz istatistikleri dogru olmali."""
        analysis = await agent.analyze({"result": poor_result.model_dump()})
        stats = analysis["stats"]
        assert stats["total_spend"] == 300.0
        assert stats["total_conversions"] == 1.0
        assert stats["overall_roas"] == pytest.approx(0.33)
        assert stats["poor_campaign_count"] == 1

    @pytest.mark.asyncio
    async def test_empty_result_analysis(self, agent: MarketingAgent) -> None:
        """Bos sonuc varsayilan AVERAGE perf -> LOW/MEDIUM."""
        result = MarketingAnalysisResult()
        # Varsayilan performance_level=AVERAGE, ROAS=0, ama analyze()
        # _map_to_risk_urgency icin performance_level'i kullanir
        analysis = await agent.analyze({"result": result.model_dump()})
        assert analysis["risk"] == RiskLevel.LOW.value
        assert analysis["urgency"] == UrgencyLevel.MEDIUM.value


# === Rapor format testleri ===


class TestReport:
    """report() metodu testleri."""

    @pytest.mark.asyncio
    async def test_report_contains_header(self, agent: MarketingAgent) -> None:
        """Rapor baslik icermeli."""
        task_result = TaskResult(
            success=True,
            data={
                "analysis": {
                    "performance_level": "good",
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                    "summary": "Performans iyi.",
                    "issues": [],
                    "stats": {
                        "total_spend": 500.0,
                        "total_conversions": 20.0,
                        "overall_roas": 3.0,
                        "overall_ctr": 2.5,
                        "poor_campaign_count": 0,
                        "poor_keyword_count": 0,
                        "disapproval_count": 0,
                        "recommendation_count": 0,
                    },
                },
            },
            message="ok",
        )
        report = await agent.report(task_result)
        assert "GOOGLE ADS PERFORMANS RAPORU" in report

    @pytest.mark.asyncio
    async def test_report_contains_metrics(self, agent: MarketingAgent) -> None:
        """Rapor metrik degerlerini icermeli."""
        task_result = TaskResult(
            success=True,
            data={
                "analysis": {
                    "performance_level": "good",
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                    "summary": "",
                    "issues": [],
                    "stats": {
                        "total_spend": 1234.56,
                        "total_conversions": 15.0,
                        "overall_roas": 3.50,
                        "overall_ctr": 2.80,
                        "poor_campaign_count": 0,
                        "poor_keyword_count": 0,
                        "disapproval_count": 0,
                        "recommendation_count": 0,
                    },
                },
            },
            message="ok",
        )
        report = await agent.report(task_result)
        assert "1234.56 TRY" in report
        assert "15.0" in report
        assert "3.50" in report
        assert "2.80" in report

    @pytest.mark.asyncio
    async def test_report_contains_issues(self, agent: MarketingAgent) -> None:
        """Rapor detay bulgularini icermeli."""
        task_result = TaskResult(
            success=True,
            data={
                "analysis": {
                    "performance_level": "poor",
                    "risk": "medium",
                    "urgency": "medium",
                    "action": "notify",
                    "summary": "",
                    "issues": [
                        "Reklam REDDEDILDI: Test (healthcare)",
                        "Dusuk performans: Kampanya X",
                    ],
                    "stats": {
                        "total_spend": 0,
                        "total_conversions": 0,
                        "overall_roas": 0,
                        "overall_ctr": 0,
                        "poor_campaign_count": 1,
                        "poor_keyword_count": 0,
                        "disapproval_count": 1,
                        "recommendation_count": 0,
                    },
                },
            },
            message="sorun",
        )
        report = await agent.report(task_result)
        assert "Detaylar" in report
        assert "REDDEDILDI" in report
        assert "Dusuk performans" in report

    @pytest.mark.asyncio
    async def test_report_contains_errors(self, agent: MarketingAgent) -> None:
        """Rapor hatalari icermeli."""
        task_result = TaskResult(
            success=False,
            data={
                "analysis": {
                    "performance_level": "critical",
                    "risk": "high",
                    "urgency": "high",
                    "action": "immediate",
                    "summary": "",
                    "issues": [],
                    "stats": {},
                },
            },
            message="hata",
            errors=["Google Ads API: Authentication failed"],
        )
        report = await agent.report(task_result)
        assert "HATALAR" in report
        assert "Authentication failed" in report


# === Execute testleri ===


class TestExecute:
    """execute() metodu testleri."""

    @pytest.mark.asyncio
    async def test_execute_no_customer_id(self) -> None:
        """Musteri ID yoksa hata donmeli."""
        agent = MarketingAgent(config=MarketingConfig(customer_id=""))
        with patch("app.agents.marketing_agent.settings") as mock_settings:
            mock_settings.google_ads_customer_id = ""
            result = await agent.execute({})
        assert result.success is False
        assert "customer_id" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_execute_api_error_handled(self) -> None:
        """Google Ads API hatasi graceful handling."""
        agent = MarketingAgent(config=MarketingConfig(
            customer_id="1234567890",
            checks=[AdCheckType.CAMPAIGN_PERFORMANCE],
        ))

        with patch.object(agent, "_get_ads_client") as mock_client:
            mock_client.side_effect = ValueError("Token yapilandirilmamis")
            with patch("app.agents.marketing_agent.settings") as mock_settings:
                mock_settings.google_ads_customer_id = "1234567890"
                result = await agent.execute({"customer_id": "1234567890"})

        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_with_task_config_override(self) -> None:
        """Task'tan config override edilebilmeli."""
        agent = MarketingAgent(config=MarketingConfig(
            customer_id="1234567890",
            checks=[],
        ))

        with patch.object(agent, "_get_ads_client") as mock_get_client:
            mock_client = MagicMock()
            mock_service = MagicMock()
            mock_service.search.return_value = []
            mock_client.get_service.return_value = mock_service
            mock_get_client.return_value = mock_client

            with patch("app.agents.marketing_agent.settings") as mock_settings:
                mock_settings.google_ads_customer_id = "1234567890"
                result = await agent.execute({
                    "customer_id": "1234567890",
                    "checks": ["campaign_performance"],
                    "date_range_days": 14,
                })

        assert result.success is True
        assert agent.config.date_range_days == 14

    @pytest.mark.asyncio
    async def test_execute_strips_dashes_from_customer_id(self) -> None:
        """Customer ID'deki tireler temizlenmeli."""
        agent = MarketingAgent(config=MarketingConfig(checks=[]))

        with patch.object(agent, "_get_ads_client") as mock_get_client:
            mock_client = MagicMock()
            mock_service = MagicMock()
            mock_service.search.return_value = []
            mock_client.get_service.return_value = mock_service
            mock_get_client.return_value = mock_client

            with patch("app.agents.marketing_agent.settings") as mock_settings:
                mock_settings.google_ads_customer_id = ""
                result = await agent.execute({
                    "customer_id": "123-456-7890",
                })

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_campaign_analysis_with_mock(self) -> None:
        """Mock Google Ads API ile kampanya analizi."""
        agent = MarketingAgent(config=MarketingConfig(
            customer_id="1234567890",
            checks=[AdCheckType.CAMPAIGN_PERFORMANCE, AdCheckType.BUDGET_ANALYSIS],
        ))

        # Mock Google Ads API row
        mock_row = MagicMock()
        mock_row.campaign.id = 12345
        mock_row.campaign.name = "Sac Ekimi Search"
        mock_row.campaign.status.name = "ENABLED"
        mock_row.campaign_budget.amount_micros = 100 * _MICRO
        mock_row.metrics.impressions = 10000
        mock_row.metrics.clicks = 500
        mock_row.metrics.cost_micros = 500 * _MICRO
        mock_row.metrics.conversions = 25.0
        mock_row.metrics.conversions_value = 25000.0
        mock_row.metrics.average_cpc = 1 * _MICRO
        mock_row.metrics.ctr = 0.05  # 5%

        with patch.object(agent, "_get_ads_client") as mock_get_client:
            mock_client = MagicMock()
            mock_service = MagicMock()
            mock_service.search.return_value = [mock_row]
            mock_client.get_service.return_value = mock_service
            mock_get_client.return_value = mock_client

            with patch("app.agents.marketing_agent.settings") as mock_settings:
                mock_settings.google_ads_customer_id = "1234567890"
                result = await agent.execute({"customer_id": "1234567890"})

        assert result.success is True
        assert "analysis_result" in result.data
        assert "analysis" in result.data

        analysis_result = result.data["analysis_result"]
        assert len(analysis_result["campaigns"]) == 1
        assert analysis_result["total_spend"] == 500.0
        assert analysis_result["total_conversions"] == 25.0
        assert analysis_result["overall_roas"] == pytest.approx(50.0)

    @pytest.mark.asyncio
    async def test_execute_only_budget_analysis(self) -> None:
        """Sadece butce analizi calistirilabilmeli."""
        agent = MarketingAgent(config=MarketingConfig(
            customer_id="1234567890",
            checks=[AdCheckType.BUDGET_ANALYSIS],
        ))

        with patch.object(agent, "_get_ads_client") as mock_get_client:
            mock_client = MagicMock()
            mock_service = MagicMock()
            mock_client.get_service.return_value = mock_service
            mock_get_client.return_value = mock_client

            with patch("app.agents.marketing_agent.settings") as mock_settings:
                mock_settings.google_ads_customer_id = "1234567890"
                result = await agent.execute({"customer_id": "1234567890"})

        assert result.success is True
        # search cagrilmamali (sadece budget_analysis)
        mock_service.search.assert_not_called()


# === Model testleri ===


class TestModels:
    """Marketing veri modeli testleri."""

    def test_marketing_config_defaults(self) -> None:
        """MarketingConfig varsayilan degerler dogru olmali."""
        config = MarketingConfig()
        assert len(config.checks) == 4
        assert config.date_range_days == 7
        assert config.cpc_threshold == 15.0
        assert config.roas_min_threshold == 2.0

    def test_campaign_metrics_defaults(self) -> None:
        """CampaignMetrics varsayilan degerler dogru olmali."""
        cm = CampaignMetrics()
        assert cm.impressions == 0
        assert cm.cpc == 0.0
        assert cm.performance_level == PerformanceLevel.AVERAGE

    def test_keyword_metrics(self) -> None:
        """KeywordMetrics dogru olusturulmali."""
        km = KeywordMetrics(
            keyword_text="sac ekimi istanbul",
            quality_score=8,
            match_type="EXACT",
        )
        assert km.keyword_text == "sac ekimi istanbul"
        assert km.quality_score == 8
        assert km.match_type == "EXACT"

    def test_ad_disapproval(self) -> None:
        """AdDisapproval dogru olusturulmali."""
        ad = AdDisapproval(
            ad_id="123",
            headline="Test Reklam",
            policy_topic="healthcare",
            evidence=["before/after images"],
        )
        assert ad.policy_topic == "healthcare"
        assert len(ad.evidence) == 1

    def test_budget_recommendation(self) -> None:
        """BudgetRecommendation dogru olusturulmali."""
        rec = BudgetRecommendation(
            campaign_name="Test",
            current_budget=100.0,
            recommended_budget=120.0,
            reason="Yuksek ROAS",
            priority=1,
        )
        assert rec.recommended_budget > rec.current_budget
        assert rec.priority == 1

    def test_marketing_analysis_result_defaults(self) -> None:
        """MarketingAnalysisResult varsayilan degerler dogru olmali."""
        result = MarketingAnalysisResult()
        assert result.performance_level == PerformanceLevel.AVERAGE
        assert result.campaigns == []
        assert result.total_spend == 0.0
        assert result.disapprovals == []

    def test_performance_level_values(self) -> None:
        """PerformanceLevel enum degerleri dogru olmali."""
        assert PerformanceLevel.EXCELLENT.value == "excellent"
        assert PerformanceLevel.GOOD.value == "good"
        assert PerformanceLevel.AVERAGE.value == "average"
        assert PerformanceLevel.POOR.value == "poor"
        assert PerformanceLevel.CRITICAL.value == "critical"

    def test_ad_check_type_values(self) -> None:
        """AdCheckType enum degerleri dogru olmali."""
        assert AdCheckType.CAMPAIGN_PERFORMANCE.value == "campaign_performance"
        assert AdCheckType.KEYWORD_PERFORMANCE.value == "keyword_performance"
        assert AdCheckType.AD_DISAPPROVALS.value == "ad_disapprovals"
        assert AdCheckType.BUDGET_ANALYSIS.value == "budget_analysis"


# === BaseAgent entegrasyon testleri ===


class TestBaseAgentIntegration:
    """BaseAgent miras ve entegrasyon testleri."""

    def test_agent_name(self, agent: MarketingAgent) -> None:
        """Agent ismi 'marketing' olmali."""
        assert agent.name == "marketing"

    def test_agent_info(self, agent: MarketingAgent) -> None:
        """get_info() dogru bilgi donmeli."""
        info = agent.get_info()
        assert info["name"] == "marketing"
        assert info["status"] == "idle"
        assert info["task_count"] == 0

    @pytest.mark.asyncio
    async def test_run_wraps_execute(self) -> None:
        """run() execute()'u sarmalayip hata yakalamali."""
        agent = MarketingAgent(config=MarketingConfig(customer_id=""))
        with patch("app.agents.marketing_agent.settings") as mock_settings:
            mock_settings.google_ads_customer_id = ""
            result = await agent.run({})
        # run() hata durumunda bile TaskResult donmeli
        assert isinstance(result, TaskResult)
        assert result.success is False
