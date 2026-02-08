"""CreativeAgent unit testleri.

Anthropic API mock'lanarak creative agent davranislari test edilir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import TaskResult
from app.agents.creative_agent import CreativeAgent, _TASK_PROMPTS, _ITEM_MODELS
from app.core.decision_matrix import ActionType, RiskLevel, UrgencyLevel
from app.models.creative import (
    AdCopy,
    BrandSuggestion,
    ContentPiece,
    CreativeConfig,
    CreativeResult,
    CreativeType,
    PackagingIdea,
    ProductIdea,
)


# === Fixtures ===


@pytest.fixture
def config() -> CreativeConfig:
    """Ornek yaratici agent yapilandirmasi."""
    return CreativeConfig(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        creativity_level=0.8,
        language="tr",
        brand_voice="profesyonel, samimi",
    )


@pytest.fixture
def agent(config: CreativeConfig) -> CreativeAgent:
    """Yapilandirilmis CreativeAgent."""
    return CreativeAgent(config=config)


def _mock_anthropic_response(json_text: str) -> MagicMock:
    """Anthropic API yaniti icin mock olusturur."""
    content_block = MagicMock()
    content_block.text = json_text
    response = MagicMock()
    response.content = [content_block]
    return response


# === Ornek LLM yanitlari ===

PRODUCT_IDEA_RESPONSE = '''{
    "items": [
        {
            "name": "HairVital Serum",
            "description": "Sac ekimi sonrasi bakim serumu",
            "target_audience": "Sac ekimi hastalari",
            "unique_value": "Dogal icerikli, klinik testli",
            "estimated_cost": "50-80 TL/adet",
            "market_potential": "Yuksek - medikal turizm buyuyor"
        },
        {
            "name": "DermaCare Kit",
            "description": "Estetik operasyon sonrasi bakim seti",
            "target_audience": "Estetik hastalari",
            "unique_value": "Hastaneyle ortak marka",
            "estimated_cost": "150-200 TL/set",
            "market_potential": "Orta-yuksek"
        }
    ],
    "summary": "Medikal turizm sektorune yonelik 2 urun fikri uretildi.",
    "recommendations": ["Klinik testler yapilmali", "Uluslararasi sertifika alinmali"]
}'''

CONTENT_RESPONSE = '''{
    "items": [
        {
            "title": "Sac Ekimi Sonrasi 10 Altin Kural",
            "body": "Sac ekimi sonrasi bakim sureci cok onemlidir. Iste dikkat edilmesi gereken 10 onemli nokta...",
            "content_type": "blog",
            "target_platform": "Instagram",
            "hashtags": ["#sacekimi", "#mapaheath", "#medikal"],
            "cta": "Ucretsiz danismanlik icin bize ulasin!"
        }
    ],
    "summary": "1 blog icerigi uretildi.",
    "recommendations": ["Haftalik icerik takvimi olusturun"]
}'''

AD_COPY_RESPONSE = '''{
    "items": [
        {
            "headline": "Sac Ekiminde Turkiye Farki",
            "description": "Uzman ekibimizle dogal sonuclar. Ucretsiz online konsultasyon.",
            "cta": "Hemen Randevu Al",
            "target_audience": "25-55 yas erkek, sac dokulmesi yasayan",
            "platform": "Google Ads",
            "variations": [
                {"headline": "Dogal Gorunum, Kalici Sonuc", "description": "VIP transfer ve otel dahil paketler."}
            ]
        }
    ],
    "summary": "1 reklam metni uretildi.",
    "recommendations": ["A/B test yapilmali"]
}'''

BRAND_NAME_RESPONSE = '''{
    "items": [
        {
            "name": "VitaNova",
            "tagline": "Yenilenmenin Baslangici",
            "reasoning": "Vita (yasam) + Nova (yeni) bilesimi. Medikal turizm ve kisisel bakim alaninda yenilenmeyi cagristirir.",
            "domain_suggestions": ["vitanova.com.tr", "vitanova.health"]
        },
        {
            "name": "PureEssence",
            "tagline": "Dogal Guzelligin Ozu",
            "reasoning": "Kozmetik urunler icin dogallik ve sadelik vurgusu.",
            "domain_suggestions": ["pureessence.com.tr"]
        }
    ],
    "summary": "2 marka isim onerisi uretildi.",
    "recommendations": ["Marka tescil arastirmasi yapilmali"]
}'''

PACKAGING_RESPONSE = '''{
    "items": [
        {
            "concept": "Minimalist lüks kozmetik ambalaji",
            "materials": ["Geri donusturulmus cam", "Bambu kapak"],
            "colors": ["#F5F5DC", "#2C3E50", "#C0A060"],
            "style": "Minimalist & surdurulebilir",
            "sustainability": "Cam sise yeniden kullanilabilir, bambu kapak biyobozunur."
        }
    ],
    "summary": "1 ambalaj tasarimi onerisi uretildi.",
    "recommendations": ["Prototip uretimi yapilmali", "Maliyet analizi cikarilmali"]
}'''


# === Test Siniflari ===


class TestCreativeAgentInit:
    """Agent baslangic testleri."""

    def test_default_config(self) -> None:
        """Varsayilan yapilandirma ile olusturulur."""
        agent = CreativeAgent()
        assert agent.name == "creative"
        assert agent.config.creativity_level == 0.8
        assert agent.config.brand_voice == "profesyonel, samimi, guven veren"

    def test_custom_config(self, config: CreativeConfig) -> None:
        """Ozel yapilandirma ile olusturulur."""
        agent = CreativeAgent(config=config)
        assert agent.config.brand_voice == "profesyonel, samimi"

    def test_lazy_client(self, agent: CreativeAgent) -> None:
        """Client baslangicta None olmali."""
        assert agent._client is None


class TestCreativeAgentGetClient:
    """API client testleri."""

    @patch("app.agents.creative_agent.settings")
    def test_get_client_success(self, mock_settings: MagicMock, agent: CreativeAgent) -> None:
        """API key varsa client olusturulur."""
        mock_settings.anthropic_api_key.get_secret_value.return_value = "test-key"
        client = agent._get_client()
        assert client is not None

    @patch("app.agents.creative_agent.settings")
    def test_get_client_cached(self, mock_settings: MagicMock, agent: CreativeAgent) -> None:
        """Client tekrar olusturulmaz."""
        mock_settings.anthropic_api_key.get_secret_value.return_value = "test-key"
        c1 = agent._get_client()
        c2 = agent._get_client()
        assert c1 is c2

    @patch("app.agents.creative_agent.settings")
    def test_get_client_no_key(self, mock_settings: MagicMock, agent: CreativeAgent) -> None:
        """API key yoksa ValueError firlatilir."""
        mock_settings.anthropic_api_key.get_secret_value.return_value = ""
        with pytest.raises(ValueError, match="API key"):
            agent._get_client()


class TestCreativeAgentExecute:
    """Execute metodu testleri."""

    @pytest.mark.asyncio
    async def test_invalid_task_type(self, agent: CreativeAgent) -> None:
        """Gecersiz icerik tipi hata dondurur."""
        result = await agent.execute({"task_type": "invalid", "description": "test"})
        assert not result.success
        assert "Gecersiz icerik tipi" in result.message

    @pytest.mark.asyncio
    async def test_missing_description(self, agent: CreativeAgent) -> None:
        """Aciklama yoksa hata dondurur."""
        result = await agent.execute({"task_type": "content"})
        assert not result.success
        assert "aciklama" in result.message.lower()

    @pytest.mark.asyncio
    async def test_product_idea_success(self, agent: CreativeAgent) -> None:
        """Urun fikri uretimi basarili calisir."""
        mock_response = _mock_anthropic_response(PRODUCT_IDEA_RESPONSE)
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "task_type": "product_idea",
            "description": "Mapa Health medikal turizm icin urun fikirleri",
        })

        assert result.success
        creative = result.data["creative_result"]
        assert creative["creative_type"] == "product_idea"
        assert len(creative["items"]) == 2
        assert creative["items"][0]["name"] == "HairVital Serum"

    @pytest.mark.asyncio
    async def test_content_success(self, agent: CreativeAgent) -> None:
        """Icerik uretimi basarili calisir."""
        mock_response = _mock_anthropic_response(CONTENT_RESPONSE)
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "task_type": "content",
            "description": "Sac ekimi hakkinda blog yazisi",
        })

        assert result.success
        creative = result.data["creative_result"]
        assert len(creative["items"]) == 1
        assert creative["items"][0]["content_type"] == "blog"
        assert len(creative["items"][0]["hashtags"]) == 3

    @pytest.mark.asyncio
    async def test_ad_copy_success(self, agent: CreativeAgent) -> None:
        """Reklam metni uretimi basarili calisir."""
        mock_response = _mock_anthropic_response(AD_COPY_RESPONSE)
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "task_type": "ad_copy",
            "description": "Mapa Health Google Ads kampanyasi",
        })

        assert result.success
        creative = result.data["creative_result"]
        assert creative["items"][0]["platform"] == "Google Ads"
        assert len(creative["items"][0]["variations"]) == 1

    @pytest.mark.asyncio
    async def test_brand_name_success(self, agent: CreativeAgent) -> None:
        """Marka ismi onerisi basarili calisir."""
        mock_response = _mock_anthropic_response(BRAND_NAME_RESPONSE)
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "task_type": "brand_name",
            "description": "Kozmetik ve kisisel bakim markasi",
        })

        assert result.success
        creative = result.data["creative_result"]
        assert len(creative["items"]) == 2
        assert creative["items"][0]["name"] == "VitaNova"
        assert len(creative["items"][0]["domain_suggestions"]) == 2

    @pytest.mark.asyncio
    async def test_packaging_success(self, agent: CreativeAgent) -> None:
        """Ambalaj tasarimi onerisi basarili calisir."""
        mock_response = _mock_anthropic_response(PACKAGING_RESPONSE)
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "task_type": "packaging",
            "description": "FTRK Store parfum ambalaji",
        })

        assert result.success
        creative = result.data["creative_result"]
        assert len(creative["items"]) == 1
        assert len(creative["items"][0]["materials"]) == 2
        assert len(creative["items"][0]["colors"]) == 3

    @pytest.mark.asyncio
    async def test_config_override(self, agent: CreativeAgent) -> None:
        """Task dict'ten config override yapilir."""
        mock_response = _mock_anthropic_response(CONTENT_RESPONSE)
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(return_value=mock_response)

        await agent.execute({
            "task_type": "content",
            "description": "Test",
            "config": {"creativity_level": 0.5, "max_tokens": 1024},
        })

        assert agent.config.creativity_level == 0.5
        assert agent.config.max_tokens == 1024

    @pytest.mark.asyncio
    async def test_brand_voice_override(self, agent: CreativeAgent) -> None:
        """Task dict'ten brand_voice override yapilir."""
        mock_response = _mock_anthropic_response(CONTENT_RESPONSE)
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(return_value=mock_response)

        await agent.execute({
            "task_type": "content",
            "description": "Test",
            "brand_voice": "enerjik, genc",
        })

        assert agent.config.brand_voice == "enerjik, genc"

    @pytest.mark.asyncio
    async def test_llm_error(self, agent: CreativeAgent) -> None:
        """LLM hatasi durumunda hata dondurulur."""
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(side_effect=Exception("API hatasi"))

        result = await agent.execute({
            "task_type": "content",
            "description": "Test icerigi",
        })

        assert not result.success
        assert "API hatasi" in result.message


class TestCreativeAgentParseLLM:
    """LLM yanit parse testleri."""

    def test_parse_clean_json(self) -> None:
        """Temiz JSON parse edilir."""
        result = CreativeAgent._parse_llm_response('{"items": []}')
        assert result["items"] == []

    def test_parse_json_in_code_block(self) -> None:
        """Kod blogu icindeki JSON parse edilir."""
        text = '```json\n{"items": [{"name": "test"}]}\n```'
        result = CreativeAgent._parse_llm_response(text)
        assert len(result["items"]) == 1

    def test_parse_json_with_surrounding_text(self) -> None:
        """JSON etrafinda metin varsa { } blogu cikarilir."""
        text = 'Iste oneriler:\n{"items": [], "summary": "test"}\nBitti.'
        result = CreativeAgent._parse_llm_response(text)
        assert result["summary"] == "test"

    def test_parse_invalid_json(self) -> None:
        """Parse edilemeyen yanit raw_text ile doner."""
        result = CreativeAgent._parse_llm_response("JSON degil bir yazi")
        assert "raw_text" in result


class TestCreativeAgentBuildResult:
    """Result building testleri."""

    def test_product_idea_items(self) -> None:
        """ProductIdea ogelerini dogru parse eder."""
        import json
        llm_data = json.loads(PRODUCT_IDEA_RESPONSE)
        result = CreativeAgent._build_result(CreativeType.PRODUCT_IDEA, llm_data)

        assert result.creative_type == "product_idea"
        assert len(result.items) == 2
        assert result.items[0]["name"] == "HairVital Serum"
        assert result.summary != ""

    def test_content_items(self) -> None:
        """ContentPiece ogelerini dogru parse eder."""
        import json
        llm_data = json.loads(CONTENT_RESPONSE)
        result = CreativeAgent._build_result(CreativeType.CONTENT, llm_data)

        assert result.creative_type == "content"
        assert len(result.items) == 1
        assert result.items[0]["content_type"] == "blog"

    def test_ad_copy_items(self) -> None:
        """AdCopy ogelerini dogru parse eder."""
        import json
        llm_data = json.loads(AD_COPY_RESPONSE)
        result = CreativeAgent._build_result(CreativeType.AD_COPY, llm_data)

        assert result.creative_type == "ad_copy"
        assert result.items[0]["headline"] == "Sac Ekiminde Turkiye Farki"

    def test_brand_name_items(self) -> None:
        """BrandSuggestion ogelerini dogru parse eder."""
        import json
        llm_data = json.loads(BRAND_NAME_RESPONSE)
        result = CreativeAgent._build_result(CreativeType.BRAND_NAME, llm_data)

        assert len(result.items) == 2
        assert result.items[0]["name"] == "VitaNova"

    def test_packaging_items(self) -> None:
        """PackagingIdea ogelerini dogru parse eder."""
        import json
        llm_data = json.loads(PACKAGING_RESPONSE)
        result = CreativeAgent._build_result(CreativeType.PACKAGING, llm_data)

        assert len(result.items) == 1
        assert len(result.items[0]["materials"]) == 2

    def test_empty_items(self) -> None:
        """Bos item listesi duzgun islenir."""
        result = CreativeAgent._build_result(CreativeType.CONTENT, {"items": []})
        assert result.items == []

    def test_invalid_items_fallback(self) -> None:
        """Dogrulama basarisiz olursa ham dict kullanilir."""
        llm_data = {"items": [{"unexpected_field": "value"}]}
        result = CreativeAgent._build_result(CreativeType.PRODUCT_IDEA, llm_data)

        # ProductIdea tum alanlari varsayilan degerli, bu yuzden validate olur
        # Ama beklenmeyen alan ignore edilir (Pydantic v2 default)
        assert len(result.items) == 1

    def test_non_dict_items_skipped(self) -> None:
        """Dict olmayan item'lar atlanir."""
        llm_data = {"items": ["string_item", 123, {"name": "valid"}]}
        result = CreativeAgent._build_result(CreativeType.PRODUCT_IDEA, llm_data)

        # Sadece dict olan item'lar islenir
        assert len(result.items) == 1

    def test_summary_and_recommendations(self) -> None:
        """Summary ve recommendations dogru aktarilir."""
        llm_data = {
            "items": [],
            "summary": "Test ozet",
            "recommendations": ["Oneri 1", "Oneri 2"],
        }
        result = CreativeAgent._build_result(CreativeType.CONTENT, llm_data)

        assert result.summary == "Test ozet"
        assert len(result.recommendations) == 2


class TestCreativeAgentRiskUrgency:
    """Risk/urgency eslestirme testleri."""

    def test_content_low_risk(self) -> None:
        """Icerik uretimi -> LOW risk."""
        result = CreativeResult(creative_type="content", items=[{"title": "test"}])
        risk, urgency = CreativeAgent._map_to_risk_urgency("content", result)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.LOW

    def test_product_idea_low_risk(self) -> None:
        """Urun fikri -> LOW risk."""
        result = CreativeResult(creative_type="product_idea", items=[{"name": "test"}])
        risk, urgency = CreativeAgent._map_to_risk_urgency("product_idea", result)
        assert risk == RiskLevel.LOW

    def test_ad_copy_medium_risk(self) -> None:
        """Reklam metni -> MEDIUM risk (dis dunyaya yansir)."""
        result = CreativeResult(creative_type="ad_copy", items=[{"headline": "test"}])
        risk, urgency = CreativeAgent._map_to_risk_urgency("ad_copy", result)
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.LOW

    def test_brand_name_medium_risk(self) -> None:
        """Marka ismi -> MEDIUM risk (dis dunyaya yansir)."""
        result = CreativeResult(creative_type="brand_name", items=[{"name": "test"}])
        risk, urgency = CreativeAgent._map_to_risk_urgency("brand_name", result)
        assert risk == RiskLevel.MEDIUM

    def test_packaging_low_risk(self) -> None:
        """Ambalaj tasarimi -> LOW risk."""
        result = CreativeResult(creative_type="packaging", items=[{"concept": "test"}])
        risk, urgency = CreativeAgent._map_to_risk_urgency("packaging", result)
        assert risk == RiskLevel.LOW

    def test_empty_items_medium_urgency(self) -> None:
        """Bos sonuc -> MEDIUM urgency."""
        result = CreativeResult(creative_type="content")
        risk, urgency = CreativeAgent._map_to_risk_urgency("content", result)
        assert urgency == UrgencyLevel.MEDIUM


class TestCreativeAgentDetermineAction:
    """Aksiyon belirleme testleri."""

    def test_low_low_logs(self) -> None:
        """LOW/LOW -> LOG."""
        action = CreativeAgent._determine_action(RiskLevel.LOW, UrgencyLevel.LOW)
        assert action == ActionType.LOG

    def test_medium_low_notify(self) -> None:
        """MEDIUM/LOW -> NOTIFY."""
        action = CreativeAgent._determine_action(RiskLevel.MEDIUM, UrgencyLevel.LOW)
        assert action == ActionType.NOTIFY

    def test_low_medium_log(self) -> None:
        """LOW/MEDIUM -> LOG."""
        action = CreativeAgent._determine_action(RiskLevel.LOW, UrgencyLevel.MEDIUM)
        assert action == ActionType.LOG


class TestCreativeAgentAnalyze:
    """Analyze metodu testleri."""

    @pytest.mark.asyncio
    async def test_analyze_returns_fields(self, agent: CreativeAgent) -> None:
        """Analyze gerekli alanlari dondurur."""
        result = CreativeResult(
            creative_type="content",
            items=[{"title": "test"}],
            summary="Test ozet",
            recommendations=["Oneri"],
        )

        analysis = await agent.analyze({
            "creative_type": "content",
            "result": result.model_dump(),
        })

        assert analysis["creative_type"] == "content"
        assert analysis["risk"] == "low"
        assert analysis["urgency"] == "low"
        assert analysis["action"] == "log"
        assert analysis["summary"] == "Test ozet"
        assert analysis["item_count"] == 1
        assert len(analysis["recommendations"]) == 1

    @pytest.mark.asyncio
    async def test_analyze_ad_copy_medium_risk(self, agent: CreativeAgent) -> None:
        """Ad copy analizi medium risk dondurur."""
        result = CreativeResult(
            creative_type="ad_copy",
            items=[{"headline": "test"}],
        )

        analysis = await agent.analyze({
            "creative_type": "ad_copy",
            "result": result.model_dump(),
        })

        assert analysis["risk"] == "medium"
        assert analysis["action"] == "notify"


class TestCreativeAgentReport:
    """Report metodu testleri."""

    @pytest.mark.asyncio
    async def test_product_idea_report(self, agent: CreativeAgent) -> None:
        """Urun fikri raporu dogru formatlanir."""
        task_result = TaskResult(
            success=True,
            data={
                "creative_result": {
                    "creative_type": "product_idea",
                    "items": [
                        {"name": "TestUrun", "description": "Aciklama", "target_audience": "Herkes", "estimated_cost": "100 TL"},
                    ],
                    "summary": "1 urun fikri",
                    "recommendations": ["Test onerisi"],
                },
                "analysis": {
                    "creative_type": "product_idea",
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                    "item_count": 1,
                },
            },
        )

        report_text = await agent.report(task_result)

        assert "YARATICI ICERIK RAPORU" in report_text
        assert "PRODUCT_IDEA" in report_text
        assert "TestUrun" in report_text
        assert "Test onerisi" in report_text

    @pytest.mark.asyncio
    async def test_content_report(self, agent: CreativeAgent) -> None:
        """Icerik raporu dogru formatlanir."""
        task_result = TaskResult(
            success=True,
            data={
                "creative_result": {
                    "creative_type": "content",
                    "items": [
                        {"title": "Test Baslik", "content_type": "blog", "target_platform": "Instagram", "body": "Test icerik...", "hashtags": ["#test"]},
                    ],
                    "summary": "1 icerik uretildi",
                    "recommendations": [],
                },
                "analysis": {
                    "creative_type": "content",
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                    "item_count": 1,
                },
            },
        )

        report_text = await agent.report(task_result)

        assert "Test Baslik" in report_text
        assert "blog" in report_text
        assert "Instagram" in report_text
        assert "#test" in report_text

    @pytest.mark.asyncio
    async def test_ad_copy_report(self, agent: CreativeAgent) -> None:
        """Reklam metni raporu dogru formatlanir."""
        task_result = TaskResult(
            success=True,
            data={
                "creative_result": {
                    "creative_type": "ad_copy",
                    "items": [
                        {"headline": "Test Baslik", "description": "Aciklama", "cta": "Tikla", "platform": "Google Ads", "variations": [{"headline": "Alt"}]},
                    ],
                    "summary": "1 reklam metni",
                    "recommendations": [],
                },
                "analysis": {
                    "creative_type": "ad_copy",
                    "risk": "medium",
                    "urgency": "low",
                    "action": "notify",
                    "item_count": 1,
                },
            },
        )

        report_text = await agent.report(task_result)

        assert "Test Baslik" in report_text
        assert "Tikla" in report_text
        assert "Google Ads" in report_text
        assert "Varyasyon sayisi: 1" in report_text

    @pytest.mark.asyncio
    async def test_brand_name_report(self, agent: CreativeAgent) -> None:
        """Marka isim raporu dogru formatlanir."""
        task_result = TaskResult(
            success=True,
            data={
                "creative_result": {
                    "creative_type": "brand_name",
                    "items": [
                        {"name": "TestMarka", "tagline": "Slogan", "reasoning": "Gerekce", "domain_suggestions": ["test.com"]},
                    ],
                    "summary": "1 marka onerisi",
                    "recommendations": [],
                },
                "analysis": {
                    "creative_type": "brand_name",
                    "risk": "medium",
                    "urgency": "low",
                    "action": "notify",
                    "item_count": 1,
                },
            },
        )

        report_text = await agent.report(task_result)

        assert "TestMarka" in report_text
        assert "Slogan" in report_text
        assert "test.com" in report_text

    @pytest.mark.asyncio
    async def test_packaging_report(self, agent: CreativeAgent) -> None:
        """Ambalaj raporu dogru formatlanir."""
        task_result = TaskResult(
            success=True,
            data={
                "creative_result": {
                    "creative_type": "packaging",
                    "items": [
                        {"concept": "Minimalist", "style": "Modern", "materials": ["Cam"], "colors": ["#FFF"]},
                    ],
                    "summary": "1 ambalaj onerisi",
                    "recommendations": [],
                },
                "analysis": {
                    "creative_type": "packaging",
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                    "item_count": 1,
                },
            },
        )

        report_text = await agent.report(task_result)

        assert "Minimalist" in report_text
        assert "Modern" in report_text
        assert "Cam" in report_text

    @pytest.mark.asyncio
    async def test_report_with_errors(self, agent: CreativeAgent) -> None:
        """Hatali rapor hatalari icerir."""
        task_result = TaskResult(
            success=False,
            data={
                "creative_result": {
                    "creative_type": "content",
                    "items": [],
                    "summary": "",
                    "recommendations": [],
                },
                "analysis": {
                    "creative_type": "content",
                    "risk": "low",
                    "urgency": "medium",
                    "action": "log",
                    "item_count": 0,
                },
            },
            errors=["Test hatasi"],
        )

        report_text = await agent.report(task_result)
        assert "HATALAR" in report_text
        assert "Test hatasi" in report_text


class TestCreativeAgentRunSafely:
    """run() metodu (BaseAgent) testleri."""

    @pytest.mark.asyncio
    async def test_run_catches_exceptions(self, agent: CreativeAgent) -> None:
        """run() icindeki hatalar yakalanir."""
        agent._client = MagicMock()
        agent._client.messages.create = AsyncMock(
            side_effect=RuntimeError("Beklenmeyen hata")
        )

        result = await agent.run({
            "task_type": "content",
            "description": "Test",
        })

        assert not result.success
        assert "Beklenmeyen hata" in result.message or "hata" in result.message.lower()


class TestCreativeAgentPromptTemplates:
    """Prompt template testleri."""

    def test_all_types_have_prompts(self) -> None:
        """Her icerik tipi icin prompt sablonu vardir."""
        for creative_type in CreativeType:
            assert creative_type in _TASK_PROMPTS

    def test_all_types_have_item_models(self) -> None:
        """Her icerik tipi icin item modeli vardir."""
        for creative_type in CreativeType:
            assert creative_type in _ITEM_MODELS

    def test_prompts_contain_placeholders(self) -> None:
        """Prompt sablonlari gerekli placeholder'lari icerir."""
        for creative_type, template in _TASK_PROMPTS.items():
            assert "{description}" in template
            assert "{context}" in template


class TestCreativeModels:
    """Pydantic model testleri."""

    def test_creative_config_bounds(self) -> None:
        """CreativeConfig creativity_level 0-1 araligindadir."""
        config = CreativeConfig(creativity_level=0.5)
        assert config.creativity_level == 0.5

        with pytest.raises(Exception):
            CreativeConfig(creativity_level=1.5)

        with pytest.raises(Exception):
            CreativeConfig(creativity_level=-0.1)

    def test_product_idea_defaults(self) -> None:
        """ProductIdea varsayilan degerleri dogru."""
        idea = ProductIdea()
        assert idea.name == ""
        assert idea.target_audience == ""

    def test_content_piece_defaults(self) -> None:
        """ContentPiece varsayilan degerleri dogru."""
        piece = ContentPiece()
        assert piece.content_type == "social"
        assert piece.hashtags == []

    def test_ad_copy_defaults(self) -> None:
        """AdCopy varsayilan degerleri dogru."""
        ad = AdCopy()
        assert ad.variations == []

    def test_brand_suggestion_defaults(self) -> None:
        """BrandSuggestion varsayilan degerleri dogru."""
        brand = BrandSuggestion()
        assert brand.domain_suggestions == []

    def test_packaging_idea_defaults(self) -> None:
        """PackagingIdea varsayilan degerleri dogru."""
        pkg = PackagingIdea()
        assert pkg.materials == []
        assert pkg.colors == []

    def test_creative_result_defaults(self) -> None:
        """CreativeResult varsayilan degerleri dogru."""
        result = CreativeResult(creative_type="content")
        assert result.items == []
        assert result.recommendations == []
