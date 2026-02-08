"""AnalysisAgent unit testleri.

Anthropic API mock'lanarak analysis agent davranislari test edilir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import TaskResult
from app.agents.analysis_agent import AnalysisAgent, _TASK_PROMPTS
from app.core.decision_matrix import ActionType, RiskLevel, UrgencyLevel
from app.models.analysis import (
    AnalysisConfig,
    AnalysisReport,
    AnalysisType,
    CompetitorInfo,
    FeasibilityResult,
    FinancialResult,
    MarketResult,
    PerformanceResult,
)


# === Fixtures ===


@pytest.fixture
def config() -> AnalysisConfig:
    """Ornek analiz yapilandirmasi."""
    return AnalysisConfig(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        currency="TRY",
        language="tr",
    )


@pytest.fixture
def agent(config: AnalysisConfig) -> AnalysisAgent:
    """Yapilandirilmis AnalysisAgent."""
    return AnalysisAgent(config=config)


def _mock_anthropic_response(json_text: str) -> MagicMock:
    """Anthropic API yaniti icin mock olusturur."""
    content_block = MagicMock()
    content_block.text = json_text
    response = MagicMock()
    response.content = [content_block]
    return response


# === Ornek LLM yanitlari ===

FEASIBILITY_RESPONSE = '''{
    "score": 75,
    "strengths": ["Guclu ekip", "Buyuk pazar"],
    "weaknesses": ["Yuksek rekabet"],
    "opportunities": ["Dijital donusum trendi"],
    "threats": ["Ekonomik belirsizlik"],
    "recommendation": "Projeye devam edilmeli, ancak rekabet analizi derinlestirilmeli.",
    "estimated_timeline": "6-8 ay"
}'''

FINANCIAL_RESPONSE = '''{
    "investment": 500000,
    "revenue_estimate": 120000,
    "costs": {"personel": 200000, "pazarlama": 100000, "altyapi": 50000},
    "roi_estimate": 45.5,
    "break_even_months": 8,
    "risk_factors": ["Kur riski", "Musteri kaybetme riski"],
    "currency": "TRY"
}'''

MARKET_RESPONSE = '''{
    "market_size": "5 milyar TL",
    "growth_rate": 12.5,
    "competitors": [
        {"name": "Rakip A", "strengths": ["Marka bilinirlik"], "weaknesses": ["Yuksek fiyat"], "market_share_estimate": 25.0},
        {"name": "Rakip B", "strengths": ["Genis urun yelpazesi"], "weaknesses": ["Zayif dijital"], "market_share_estimate": 15.0}
    ],
    "target_audience": "25-45 yas arasi profesyoneller",
    "trends": ["Dijitallesme", "Surdurulebilirlik"],
    "entry_barriers": ["Yuksek sermaye gereksinimi"]
}'''

COMPETITOR_RESPONSE = '''{
    "competitors": [
        {"name": "Rakip X", "strengths": ["Teknoloji"], "weaknesses": ["Fiyat"], "market_share_estimate": 30.0},
        {"name": "Rakip Y", "strengths": ["Dagitim agi"], "weaknesses": ["Inovasyon"], "market_share_estimate": 20.0}
    ],
    "market_size": "3 milyar TL",
    "trends": ["AI entegrasyonu"],
    "target_audience": "KOBIler"
}'''

PERFORMANCE_RESPONSE = '''{
    "metric_name": "Aylik gelir",
    "current_value": 85000,
    "target_value": 120000,
    "trend": "up",
    "gap_percentage": 29.2,
    "recommendations": ["Yeni satis kanallari ekle", "Fiyat optimizasyonu yap", "Musteri sadakat programi baslat"]
}'''


# === Test Siniflari ===


class TestAnalysisAgentInit:
    """Agent baslangic testleri."""

    def test_default_config(self) -> None:
        """Varsayilan yapilandirma ile olusturulur."""
        agent = AnalysisAgent()
        assert agent.name == "analysis"
        assert agent.config.model == "claude-sonnet-4-5-20250929"
        assert agent.config.currency == "TRY"
        assert agent.config.language == "tr"

    def test_custom_config(self, config: AnalysisConfig) -> None:
        """Ozel yapilandirma ile olusturulur."""
        agent = AnalysisAgent(config=config)
        assert agent.config.max_tokens == 2048

    def test_lazy_client(self, agent: AnalysisAgent) -> None:
        """Client baslangicta None olmali."""
        assert agent._client is None


class TestAnalysisAgentGetClient:
    """API client testleri."""

    @patch("app.agents.analysis_agent.settings")
    def test_get_client_success(self, mock_settings: MagicMock, agent: AnalysisAgent) -> None:
        """API key varsa client olusturulur."""
        mock_settings.anthropic_api_key.get_secret_value.return_value = "test-key"
        client = agent._get_client()
        assert client is not None
        assert agent._client is not None

    @patch("app.agents.analysis_agent.settings")
    def test_get_client_cached(self, mock_settings: MagicMock, agent: AnalysisAgent) -> None:
        """Client tekrar olusturulmaz."""
        mock_settings.anthropic_api_key.get_secret_value.return_value = "test-key"
        client1 = agent._get_client()
        client2 = agent._get_client()
        assert client1 is client2

    @patch("app.agents.analysis_agent.settings")
    def test_get_client_no_key(self, mock_settings: MagicMock, agent: AnalysisAgent) -> None:
        """API key yoksa ValueError firlatilir."""
        mock_settings.anthropic_api_key.get_secret_value.return_value = ""
        with pytest.raises(ValueError, match="API key"):
            agent._get_client()


class TestAnalysisAgentExecute:
    """Execute metodu testleri."""

    @pytest.mark.asyncio
    async def test_invalid_task_type(self, agent: AnalysisAgent) -> None:
        """Gecersiz analiz tipi hata dondurur."""
        result = await agent.execute({"task_type": "invalid", "description": "test"})
        assert not result.success
        assert "Gecersiz analiz tipi" in result.message

    @pytest.mark.asyncio
    async def test_missing_description(self, agent: AnalysisAgent) -> None:
        """Aciklama yoksa hata dondurur."""
        result = await agent.execute({"task_type": "feasibility"})
        assert not result.success
        assert "aciklama" in result.message.lower()

    @pytest.mark.asyncio
    async def test_feasibility_success(self, agent: AnalysisAgent) -> None:
        """Fizibilite analizi basarili calisir."""
        mock_response = _mock_anthropic_response(FEASIBILITY_RESPONSE)
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "task_type": "feasibility",
            "description": "Yeni e-ticaret platformu",
            "context": "FTRK Store icin",
        })

        assert result.success
        report = result.data["report"]
        assert report["analysis_type"] == "feasibility"
        assert report["data"]["score"] == 75
        assert len(report["data"]["strengths"]) == 2
        assert len(report["data"]["weaknesses"]) == 1
        assert report["risk_level"] == "low"  # score >= 70

    @pytest.mark.asyncio
    async def test_financial_success(self, agent: AnalysisAgent) -> None:
        """Finansal analiz basarili calisir."""
        mock_response = _mock_anthropic_response(FINANCIAL_RESPONSE)
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "task_type": "financial",
            "description": "FTRK Store kozmetik serisi",
        })

        assert result.success
        report = result.data["report"]
        assert report["analysis_type"] == "financial"
        assert report["data"]["investment"] == 500000
        assert report["data"]["roi_estimate"] == 45.5
        assert report["data"]["break_even_months"] == 8
        assert report["risk_level"] == "medium"  # ROI 10-50

    @pytest.mark.asyncio
    async def test_market_success(self, agent: AnalysisAgent) -> None:
        """Pazar analizi basarili calisir."""
        mock_response = _mock_anthropic_response(MARKET_RESPONSE)
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "task_type": "market",
            "description": "Medikal turizm sektoru",
        })

        assert result.success
        report = result.data["report"]
        assert report["analysis_type"] == "market"
        assert len(report["data"]["competitors"]) == 2
        assert report["data"]["growth_rate"] == 12.5
        assert report["risk_level"] == "medium"  # 1 entry_barrier

    @pytest.mark.asyncio
    async def test_competitor_success(self, agent: AnalysisAgent) -> None:
        """Rakip analizi basarili calisir."""
        mock_response = _mock_anthropic_response(COMPETITOR_RESPONSE)
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "task_type": "competitor",
            "description": "Kozmetik sektoru rakipleri",
        })

        assert result.success
        report = result.data["report"]
        assert report["analysis_type"] == "competitor"
        assert len(report["data"]["competitors"]) == 2

    @pytest.mark.asyncio
    async def test_performance_success(self, agent: AnalysisAgent) -> None:
        """Performans analizi basarili calisir."""
        mock_response = _mock_anthropic_response(PERFORMANCE_RESPONSE)
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "task_type": "performance",
            "description": "FTRK Store aylik gelir metrigi",
        })

        assert result.success
        report = result.data["report"]
        assert report["analysis_type"] == "performance"
        assert report["data"]["current_value"] == 85000
        assert report["data"]["target_value"] == 120000
        assert report["data"]["gap_percentage"] == 29.2
        assert report["risk_level"] == "medium"  # gap 10-30

    @pytest.mark.asyncio
    async def test_config_override(self, agent: AnalysisAgent) -> None:
        """Task dict'ten config override yapilir."""
        mock_response = _mock_anthropic_response(FEASIBILITY_RESPONSE)
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(return_value=mock_response)

        await agent.execute({
            "task_type": "feasibility",
            "description": "Test",
            "config": {"currency": "USD", "max_tokens": 1024},
        })

        assert agent.config.currency == "USD"
        assert agent.config.max_tokens == 1024

    @pytest.mark.asyncio
    async def test_llm_error(self, agent: AnalysisAgent) -> None:
        """LLM hatasi durumunda hata dondurulur."""
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(side_effect=Exception("API hatasi"))

        result = await agent.execute({
            "task_type": "feasibility",
            "description": "Test projesi",
        })

        assert not result.success
        assert "API hatasi" in result.message


class TestAnalysisAgentParseLLM:
    """LLM yanit parse testleri."""

    def test_parse_clean_json(self) -> None:
        """Temiz JSON parse edilir."""
        result = AnalysisAgent._parse_llm_response('{"score": 80}')
        assert result["score"] == 80

    def test_parse_json_in_code_block(self) -> None:
        """Kod blogu icindeki JSON parse edilir."""
        text = '```json\n{"score": 75}\n```'
        result = AnalysisAgent._parse_llm_response(text)
        assert result["score"] == 75

    def test_parse_json_with_text(self) -> None:
        """JSON etrafinda metin varsa { } blogu cikarilir."""
        text = 'Analiz sonucu:\n{"score": 60, "recommendation": "devam"}\nSon.'
        result = AnalysisAgent._parse_llm_response(text)
        assert result["score"] == 60

    def test_parse_invalid_json(self) -> None:
        """Parse edilemeyen yanit raw_text ile doner."""
        result = AnalysisAgent._parse_llm_response("Bu bir JSON degil")
        assert "raw_text" in result


class TestAnalysisAgentBuildReport:
    """Report building testleri."""

    def test_feasibility_high_score(self, agent: AnalysisAgent) -> None:
        """Yuksek fizibilite skoru dusuk risk uretir."""
        import json
        llm_data = json.loads(FEASIBILITY_RESPONSE)
        report = agent._build_report(AnalysisType.FEASIBILITY, llm_data)

        assert report.analysis_type == "feasibility"
        assert report.risk_level == "low"
        assert report.data["score"] == 75
        assert "fizibil" in report.summary.lower()

    def test_feasibility_low_score(self, agent: AnalysisAgent) -> None:
        """Dusuk fizibilite skoru yuksek risk uretir."""
        llm_data = {"score": 25, "strengths": [], "weaknesses": ["Cok riskli"]}
        report = agent._build_report(AnalysisType.FEASIBILITY, llm_data)

        assert report.risk_level == "high"
        assert "yuksek riskli" in report.summary.lower()

    def test_feasibility_medium_score(self, agent: AnalysisAgent) -> None:
        """Orta fizibilite skoru orta risk uretir."""
        llm_data = {"score": 55}
        report = agent._build_report(AnalysisType.FEASIBILITY, llm_data)

        assert report.risk_level == "medium"

    def test_financial_high_roi(self, agent: AnalysisAgent) -> None:
        """Yuksek ROI dusuk risk uretir."""
        llm_data = {"roi_estimate": 80, "investment": 100000}
        report = agent._build_report(AnalysisType.FINANCIAL, llm_data)

        assert report.risk_level == "low"
        assert "olumlu" in report.summary.lower()

    def test_financial_low_roi(self, agent: AnalysisAgent) -> None:
        """Dusuk ROI yuksek risk uretir."""
        llm_data = {"roi_estimate": 5, "investment": 100000}
        report = agent._build_report(AnalysisType.FINANCIAL, llm_data)

        assert report.risk_level == "high"
        assert "riskli" in report.summary.lower()

    def test_market_many_barriers(self, agent: AnalysisAgent) -> None:
        """Cok engel yuksek risk uretir."""
        llm_data = {
            "entry_barriers": ["Sermaye", "Regulasyon", "Marka bilinirlik"],
            "competitors": [],
        }
        report = agent._build_report(AnalysisType.MARKET, llm_data)

        assert report.risk_level == "high"

    def test_market_no_barriers(self, agent: AnalysisAgent) -> None:
        """Engel yoksa dusuk risk uretir."""
        llm_data = {
            "entry_barriers": [],
            "competitors": [{"name": "Test"}],
        }
        report = agent._build_report(AnalysisType.MARKET, llm_data)

        assert report.risk_level == "low"

    def test_performance_large_gap(self, agent: AnalysisAgent) -> None:
        """Buyuk performans farki yuksek risk uretir."""
        llm_data = {"gap_percentage": 50, "metric_name": "Gelir"}
        report = agent._build_report(AnalysisType.PERFORMANCE, llm_data)

        assert report.risk_level == "high"
        assert "acil" in report.summary.lower()

    def test_performance_small_gap(self, agent: AnalysisAgent) -> None:
        """Kucuk performans farki dusuk risk uretir."""
        llm_data = {"gap_percentage": 5, "metric_name": "Gelir"}
        report = agent._build_report(AnalysisType.PERFORMANCE, llm_data)

        assert report.risk_level == "low"

    def test_confidence_map(self, agent: AnalysisAgent) -> None:
        """Risk seviyesine gore guven skoru atanir."""
        low_report = agent._build_report(AnalysisType.FEASIBILITY, {"score": 80})
        med_report = agent._build_report(AnalysisType.FEASIBILITY, {"score": 50})
        high_report = agent._build_report(AnalysisType.FEASIBILITY, {"score": 20})

        assert low_report.confidence == 0.8
        assert med_report.confidence == 0.6
        assert high_report.confidence == 0.5

    def test_invalid_llm_data(self, agent: AnalysisAgent) -> None:
        """Gecersiz LLM verisi varsayilan degerlerle raporlanir."""
        llm_data = {"score": "not_a_number"}
        report = agent._build_report(AnalysisType.FEASIBILITY, llm_data)

        # ValueError yakalanir, varsayilan score=50 kullanilir
        assert report.data["score"] == 50
        assert report.risk_level == "medium"


class TestAnalysisAgentRiskUrgency:
    """Risk/urgency eslestirme testleri."""

    def test_high_risk_medium_urgency(self) -> None:
        """Yuksek riskli rapor -> HIGH risk, MEDIUM urgency."""
        report = AnalysisReport(
            analysis_type="feasibility",
            risk_level="high",
            recommendations=["Oneri 1"],
        )
        risk, urgency = AnalysisAgent._map_to_risk_urgency(report)
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.MEDIUM

    def test_medium_risk_low_urgency(self) -> None:
        """Orta riskli rapor -> MEDIUM risk, LOW urgency."""
        report = AnalysisReport(
            analysis_type="financial",
            risk_level="medium",
        )
        risk, urgency = AnalysisAgent._map_to_risk_urgency(report)
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.LOW

    def test_low_risk_low_urgency(self) -> None:
        """Dusuk riskli rapor -> LOW risk, LOW urgency."""
        report = AnalysisReport(
            analysis_type="market",
            risk_level="low",
        )
        risk, urgency = AnalysisAgent._map_to_risk_urgency(report)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.LOW

    def test_many_recommendations_escalate_urgency(self) -> None:
        """3'ten fazla oneri urgency'yi artirir."""
        report = AnalysisReport(
            analysis_type="performance",
            risk_level="medium",
            recommendations=["1", "2", "3", "4"],
        )
        risk, urgency = AnalysisAgent._map_to_risk_urgency(report)
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.MEDIUM  # LOW -> MEDIUM

    def test_high_risk_many_recs_escalate_to_high(self) -> None:
        """Yuksek risk + cok oneri -> HIGH urgency."""
        report = AnalysisReport(
            analysis_type="feasibility",
            risk_level="high",
            recommendations=["1", "2", "3", "4"],
        )
        risk, urgency = AnalysisAgent._map_to_risk_urgency(report)
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.HIGH  # MEDIUM -> HIGH


class TestAnalysisAgentDetermineAction:
    """Aksiyon belirleme testleri."""

    def test_low_low_logs(self) -> None:
        """LOW/LOW -> LOG."""
        action = AnalysisAgent._determine_action(RiskLevel.LOW, UrgencyLevel.LOW)
        assert action == ActionType.LOG

    def test_high_high_immediate(self) -> None:
        """HIGH/HIGH -> IMMEDIATE."""
        action = AnalysisAgent._determine_action(RiskLevel.HIGH, UrgencyLevel.HIGH)
        assert action == ActionType.IMMEDIATE

    def test_medium_high_auto_fix(self) -> None:
        """MEDIUM/HIGH -> AUTO_FIX."""
        action = AnalysisAgent._determine_action(RiskLevel.MEDIUM, UrgencyLevel.HIGH)
        assert action == ActionType.AUTO_FIX

    def test_high_medium_auto_fix(self) -> None:
        """HIGH/MEDIUM -> AUTO_FIX."""
        action = AnalysisAgent._determine_action(RiskLevel.HIGH, UrgencyLevel.MEDIUM)
        assert action == ActionType.AUTO_FIX


class TestAnalysisAgentAnalyze:
    """Analyze metodu testleri."""

    @pytest.mark.asyncio
    async def test_analyze_returns_fields(self, agent: AnalysisAgent) -> None:
        """Analyze gerekli alanlari dondurur."""
        report = AnalysisReport(
            analysis_type="feasibility",
            summary="Test ozet",
            risk_level="low",
            confidence=0.8,
            recommendations=["Oneri 1"],
        )

        result = await agent.analyze({
            "analysis_type": "feasibility",
            "report": report.model_dump(),
        })

        assert result["analysis_type"] == "feasibility"
        assert result["risk"] == "low"
        assert result["urgency"] == "low"
        assert result["action"] == "log"
        assert result["summary"] == "Test ozet"
        assert result["confidence"] == 0.8
        assert len(result["recommendations"]) == 1


class TestAnalysisAgentReport:
    """Report metodu testleri."""

    @pytest.mark.asyncio
    async def test_feasibility_report_format(self, agent: AnalysisAgent) -> None:
        """Fizibilite raporu dogru formatlanir."""
        task_result = TaskResult(
            success=True,
            data={
                "report": {
                    "analysis_type": "feasibility",
                    "title": "Test Fizibilite",
                    "summary": "Proje fizibil",
                    "data": {
                        "score": 80,
                        "strengths": ["Guclu ekip"],
                        "weaknesses": ["Rekabet"],
                        "opportunities": [],
                        "threats": [],
                    },
                    "recommendations": ["Devam et"],
                    "risk_level": "low",
                    "confidence": 0.8,
                },
                "analysis": {
                    "analysis_type": "feasibility",
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                    "confidence": 0.8,
                },
            },
        )

        report_text = await agent.report(task_result)

        assert "IS ANALIZ RAPORU" in report_text
        assert "FEASIBILITY" in report_text
        assert "80/100" in report_text
        assert "Guclu ekip" in report_text

    @pytest.mark.asyncio
    async def test_financial_report_format(self, agent: AnalysisAgent) -> None:
        """Finansal rapor dogru formatlanir."""
        task_result = TaskResult(
            success=True,
            data={
                "report": {
                    "analysis_type": "financial",
                    "title": "Finansal Analiz",
                    "summary": "ROI olumlu",
                    "data": {
                        "investment": 500000,
                        "revenue_estimate": 120000,
                        "roi_estimate": 45.5,
                        "break_even_months": 8,
                        "costs": {"personel": 200000},
                        "currency": "TRY",
                    },
                    "recommendations": [],
                    "risk_level": "medium",
                    "confidence": 0.6,
                },
                "analysis": {
                    "analysis_type": "financial",
                    "risk": "medium",
                    "urgency": "low",
                    "action": "notify",
                },
            },
        )

        report_text = await agent.report(task_result)

        assert "Finansal" in report_text
        assert "500,000" in report_text
        assert "120,000" in report_text
        assert "45.5" in report_text
        assert "8 ay" in report_text

    @pytest.mark.asyncio
    async def test_report_with_errors(self, agent: AnalysisAgent) -> None:
        """Hatali rapor hatalari icerir."""
        task_result = TaskResult(
            success=False,
            data={
                "report": {
                    "analysis_type": "feasibility",
                    "title": "",
                    "summary": "",
                    "data": {},
                    "recommendations": [],
                    "risk_level": "low",
                    "confidence": 0.7,
                },
                "analysis": {
                    "analysis_type": "feasibility",
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                },
            },
            errors=["Test hatasi"],
        )

        report_text = await agent.report(task_result)
        assert "HATALAR" in report_text
        assert "Test hatasi" in report_text


class TestAnalysisAgentRunSafely:
    """run() metodu (BaseAgent) testleri."""

    @pytest.mark.asyncio
    async def test_run_catches_exceptions(self, agent: AnalysisAgent) -> None:
        """run() icindeki hatalar yakalanir."""
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(
            side_effect=RuntimeError("Beklenmeyen hata")
        )

        result = await agent.run({
            "task_type": "feasibility",
            "description": "Test",
        })

        assert not result.success
        assert "Beklenmeyen hata" in result.message or "hata" in result.message.lower()


class TestAnalysisAgentPromptTemplates:
    """Prompt template testleri."""

    def test_all_types_have_prompts(self) -> None:
        """Her analiz tipi icin prompt sablonu vardir."""
        for analysis_type in AnalysisType:
            assert analysis_type in _TASK_PROMPTS

    def test_prompts_contain_placeholders(self) -> None:
        """Prompt sablonlari gerekli placeholder'lari icerir."""
        for analysis_type, template in _TASK_PROMPTS.items():
            assert "{description}" in template
            assert "{context}" in template


class TestAnalysisModels:
    """Pydantic model testleri."""

    def test_feasibility_score_bounds(self) -> None:
        """FeasibilityResult skoru 0-100 araligindadir."""
        result = FeasibilityResult(score=75)
        assert result.score == 75

        with pytest.raises(Exception):
            FeasibilityResult(score=150)

        with pytest.raises(Exception):
            FeasibilityResult(score=-10)

    def test_analysis_report_confidence_bounds(self) -> None:
        """AnalysisReport confidence 0-1 araligindadir."""
        report = AnalysisReport(analysis_type="test", confidence=0.8)
        assert report.confidence == 0.8

        with pytest.raises(Exception):
            AnalysisReport(analysis_type="test", confidence=1.5)

    def test_competitor_info(self) -> None:
        """CompetitorInfo dogru olusturulur."""
        comp = CompetitorInfo(
            name="Test Rakip",
            strengths=["Guclu marka"],
            weaknesses=["Yuksek fiyat"],
            market_share_estimate=15.5,
        )
        assert comp.name == "Test Rakip"
        assert comp.url is None
        assert len(comp.strengths) == 1

    def test_financial_result_defaults(self) -> None:
        """FinancialResult varsayilan degerleri dogru."""
        result = FinancialResult()
        assert result.investment == 0.0
        assert result.currency == "TRY"
        assert result.costs == {}

    def test_performance_result_defaults(self) -> None:
        """PerformanceResult varsayilan degerleri dogru."""
        result = PerformanceResult()
        assert result.trend == "stable"
        assert result.gap_percentage == 0.0

    def test_analysis_config_defaults(self) -> None:
        """AnalysisConfig varsayilan degerleri dogru."""
        config = AnalysisConfig()
        assert config.currency == "TRY"
        assert config.language == "tr"
        assert config.max_tokens == 4096
