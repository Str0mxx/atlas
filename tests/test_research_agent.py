"""ResearchAgent unit testleri.

HTTP istekleri mock'lanarak arastirma agent davranislari test edilir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.agents.base_agent import TaskResult
from app.agents.research_agent import ResearchAgent
from app.core.decision_matrix import ActionType, RiskLevel, UrgencyLevel
from app.models.research import (
    CompanyInfo,
    ReliabilityLevel,
    ResearchConfig,
    ResearchResult,
    ResearchType,
    ScrapedPage,
    SupplierScore,
    WebSearchResult,
)


# === Fixtures ===


@pytest.fixture
def config() -> ResearchConfig:
    """Ornek arastirma yapilandirmasi."""
    return ResearchConfig(
        max_results=3,
        scraping_timeout=5,
    )


@pytest.fixture
def agent(config: ResearchConfig) -> ResearchAgent:
    """Yapilandirilmis ResearchAgent."""
    return ResearchAgent(config=config)


SAMPLE_HTML = """
<html>
<head>
    <title>Test Firma</title>
    <meta name="description" content="Kaliteli urunler sunan firma">
</head>
<body>
    <nav>Navigasyon</nav>
    <h1>Hosgeldiniz</h1>
    <p>Firmamiz ISO 9001 sertifikali olup kaliteli urunler uretmektedir.</p>
    <p>Iletisim: info@testfirma.com | +90 555 123 4567</p>
    <p>Adres: Istanbul, Kadikoy, Ornek Sokak No:1</p>
    <p>Fiyat listemiz icin bize ulasin.</p>
    <p>Teslimat suresi 3-5 is gunudur.</p>
    <p>Referanslarimiz: ABC Corp, XYZ Ltd</p>
    <a href="https://facebook.com/testfirma">Facebook</a>
    <a href="https://instagram.com/testfirma">Instagram</a>
    <a href="https://linkedin.com/company/testfirma">LinkedIn</a>
    <footer>Footer</footer>
</body>
</html>
"""

MINIMAL_HTML = """
<html>
<head><title>Minimal</title></head>
<body><p>Kisa icerik.</p></body>
</html>
"""

EMPTY_HTML = """
<html><head><title>Bos</title></head><body></body></html>
"""


def _mock_response(status_code: int = 200, text: str = SAMPLE_HTML) -> httpx.Response:
    """Mock httpx.Response olusturur."""
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(
        status_code=status_code,
        text=text,
        request=request,
    )
    return response


# === Escalation testleri ===


class TestEscalation:
    """Risk/aciliyet yukseltme testleri."""

    def test_escalate_risk_upgrades(self) -> None:
        result = ResearchAgent._escalate_risk(RiskLevel.LOW, RiskLevel.MEDIUM)
        assert result == RiskLevel.MEDIUM

    def test_escalate_risk_no_downgrade(self) -> None:
        result = ResearchAgent._escalate_risk(RiskLevel.HIGH, RiskLevel.LOW)
        assert result == RiskLevel.HIGH

    def test_escalate_risk_same_level(self) -> None:
        result = ResearchAgent._escalate_risk(RiskLevel.MEDIUM, RiskLevel.MEDIUM)
        assert result == RiskLevel.MEDIUM

    def test_escalate_urgency_upgrades(self) -> None:
        result = ResearchAgent._escalate_urgency(UrgencyLevel.LOW, UrgencyLevel.HIGH)
        assert result == UrgencyLevel.HIGH

    def test_escalate_urgency_no_downgrade(self) -> None:
        result = ResearchAgent._escalate_urgency(UrgencyLevel.HIGH, UrgencyLevel.LOW)
        assert result == UrgencyLevel.HIGH


# === Aksiyon belirleme testleri ===


class TestActionDetermination:
    """Aksiyon tipi belirleme testleri."""

    def test_low_low_logs(self) -> None:
        assert ResearchAgent._determine_action(RiskLevel.LOW, UrgencyLevel.LOW) == ActionType.LOG

    def test_medium_medium_notifies(self) -> None:
        assert ResearchAgent._determine_action(RiskLevel.MEDIUM, UrgencyLevel.MEDIUM) == ActionType.NOTIFY

    def test_high_high_immediate(self) -> None:
        assert ResearchAgent._determine_action(RiskLevel.HIGH, UrgencyLevel.HIGH) == ActionType.IMMEDIATE


# === Firma guvenilirlik hesaplama testleri ===


class TestCalculateReliability:
    """_calculate_reliability testleri."""

    def test_high_reliability(self) -> None:
        """Tam bilgili firma HIGH olmali."""
        info = CompanyInfo(
            has_ssl=True,
            has_contact_info=True,
            has_physical_address=True,
            social_media_count=3,
        )
        assert ResearchAgent._calculate_reliability(info) == ReliabilityLevel.HIGH

    def test_medium_reliability(self) -> None:
        """Kismi bilgili firma MEDIUM olmali."""
        info = CompanyInfo(
            has_ssl=True,
            has_contact_info=True,
            has_physical_address=False,
            social_media_count=0,
        )
        assert ResearchAgent._calculate_reliability(info) == ReliabilityLevel.MEDIUM

    def test_low_reliability(self) -> None:
        """Bos bilgili firma LOW olmali."""
        info = CompanyInfo(
            has_ssl=False,
            has_contact_info=False,
            has_physical_address=False,
            social_media_count=0,
            red_flags=["SSL yok", "Adres yok", "Iletisim yok"],
        )
        assert ResearchAgent._calculate_reliability(info) == ReliabilityLevel.LOW

    def test_red_flags_reduce_score(self) -> None:
        """Red flag'ler puani dusturmeli."""
        info = CompanyInfo(
            has_ssl=True,
            has_contact_info=True,
            has_physical_address=True,
            social_media_count=2,
            red_flags=["flag1", "flag2", "flag3", "flag4", "flag5", "flag6"],
        )
        # 2+2+2+2 = 8, minus 6 red flags = 2 -> MEDIUM
        assert ResearchAgent._calculate_reliability(info) == ReliabilityLevel.MEDIUM


# === Scraping testleri ===


class TestScraping:
    """_scrape_page testleri."""

    @pytest.mark.asyncio
    async def test_scrape_success(self, agent: ResearchAgent) -> None:
        """Basarili scraping."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response())
        mock_client.is_closed = False
        agent._http_client = mock_client

        page = await agent._scrape_page("https://example.com")

        assert page.success is True
        assert page.title == "Test Firma"
        assert page.status_code == 200
        assert page.word_count > 0
        assert "ISO" in page.content or "kaliteli" in page.content
        assert "Kaliteli urunler" in page.meta_description

    @pytest.mark.asyncio
    async def test_scrape_removes_nav_footer(self, agent: ResearchAgent) -> None:
        """Scraping nav/footer/script temizlemeli."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response())
        mock_client.is_closed = False
        agent._http_client = mock_client

        page = await agent._scrape_page("https://example.com")

        assert "Navigasyon" not in page.content
        assert "Footer" not in page.content

    @pytest.mark.asyncio
    async def test_scrape_http_error(self, agent: ResearchAgent) -> None:
        """HTTP hata durumunda basarisiz donmeli."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Baglanti reddedildi"),
        )
        mock_client.is_closed = False
        agent._http_client = mock_client

        page = await agent._scrape_page("https://example.com")

        assert page.success is False
        assert "Baglanti reddedildi" in page.error

    @pytest.mark.asyncio
    async def test_scrape_minimal_page(self, agent: ResearchAgent) -> None:
        """Minimal sayfa scraping."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(text=MINIMAL_HTML))
        mock_client.is_closed = False
        agent._http_client = mock_client

        page = await agent._scrape_page("https://example.com")

        assert page.success is True
        assert page.title == "Minimal"
        assert page.word_count < 10


# === Tedarikci arastirma testleri ===


class TestSupplierResearch:
    """_research_supplier testleri."""

    @pytest.mark.asyncio
    async def test_supplier_with_good_site(self, agent: ResearchAgent) -> None:
        """Iyi bir tedarikci sitesi yuksek puan almali."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response())
        mock_client.is_closed = False
        agent._http_client = mock_client

        supplier = await agent._research_supplier("Test Firma", "https://testfirma.com")

        assert supplier.name == "Test Firma"
        assert supplier.overall_score > 5.0
        assert supplier.reliability in (ReliabilityLevel.MEDIUM, ReliabilityLevel.HIGH)
        assert len(supplier.scores) == 5
        assert supplier.scores["fiyat"] > 4.0  # "fiyat" keyword in HTML
        assert supplier.scores["kalite"] > 4.0  # "ISO", "kalite" keywords
        assert supplier.scores["iletisim"] > 4.0  # email + phone + address
        assert len(supplier.pros) > 0

    @pytest.mark.asyncio
    async def test_supplier_with_empty_site(self, agent: ResearchAgent) -> None:
        """Bos site dusuk puan almali."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(text=EMPTY_HTML))
        mock_client.is_closed = False
        agent._http_client = mock_client

        supplier = await agent._research_supplier("Bos Firma", "https://bosfirma.com")

        assert supplier.overall_score < 5.0
        assert supplier.reliability == ReliabilityLevel.LOW

    @pytest.mark.asyncio
    async def test_supplier_unreachable(self, agent: ResearchAgent) -> None:
        """Erisilemez site LOW guvenilirlik donmeli."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Timeout"),
        )
        mock_client.is_closed = False
        agent._http_client = mock_client

        supplier = await agent._research_supplier("Timeout Firma", "https://timeout.com")

        assert supplier.reliability == ReliabilityLevel.LOW
        assert any("erisilemedi" in n for n in supplier.notes)

    @pytest.mark.asyncio
    async def test_supplier_no_url(self, agent: ResearchAgent) -> None:
        """URL'siz tedarikci LOW donmeli."""
        supplier = await agent._research_supplier("NoURL Firma", "")

        assert supplier.reliability == ReliabilityLevel.LOW


# === Firma kontrolu testleri ===


class TestCompanyCheck:
    """_check_company testleri."""

    @pytest.mark.asyncio
    async def test_check_good_company(self, agent: ResearchAgent) -> None:
        """Iyi bir firmanin kontrolu."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response())
        mock_client.is_closed = False
        agent._http_client = mock_client

        info = await agent._check_company("https://testfirma.com")

        assert info.has_ssl is True
        assert info.has_contact_info is True
        assert info.has_physical_address is True
        assert info.social_media_count >= 3
        assert info.reliability == ReliabilityLevel.HIGH
        assert len(info.green_flags) > 0

    @pytest.mark.asyncio
    async def test_check_http_site(self, agent: ResearchAgent) -> None:
        """HTTP (SSL'siz) site red flag almali."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(text=MINIMAL_HTML))
        mock_client.is_closed = False
        agent._http_client = mock_client

        info = await agent._check_company("http://nosslsite.com")

        assert info.has_ssl is False
        assert any("SSL" in f for f in info.red_flags)

    @pytest.mark.asyncio
    async def test_check_unreachable_company(self, agent: ResearchAgent) -> None:
        """Erisilemez firma LOW donmeli."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Refused"),
        )
        mock_client.is_closed = False
        agent._http_client = mock_client

        info = await agent._check_company("https://unreachable.com")

        assert info.reliability == ReliabilityLevel.LOW
        assert any("erisilemez" in f.lower() for f in info.red_flags)

    @pytest.mark.asyncio
    async def test_check_empty_site(self, agent: ResearchAgent) -> None:
        """Bos site red flag almali."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response(text=EMPTY_HTML))
        mock_client.is_closed = False
        agent._http_client = mock_client

        info = await agent._check_company("https://emptysite.com")

        assert any("az icerik" in f.lower() for f in info.red_flags)


# === Web arama testleri ===


class TestWebSearch:
    """_web_search testleri."""

    @pytest.mark.asyncio
    async def test_search_with_api_key(self, agent: ResearchAgent) -> None:
        """API key varsa arama yapilmali."""
        mock_response = httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Test Sonuc",
                        "url": "https://example.com/result",
                        "content": "Test snippet icerigi",
                        "score": 0.95,
                    },
                ],
            },
            request=httpx.Request("POST", "https://api.tavily.com/search"),
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        agent._http_client = mock_client

        with patch("app.agents.research_agent.settings") as mock_settings:
            mock_settings.tavily_api_key = MagicMock()
            mock_settings.tavily_api_key.get_secret_value.return_value = "test-key"

            results = await agent._web_search("test query")

        assert len(results) == 1
        assert results[0].title == "Test Sonuc"
        assert results[0].url == "https://example.com/result"
        assert results[0].relevance_score == 0.95

    @pytest.mark.asyncio
    async def test_search_without_api_key(self, agent: ResearchAgent) -> None:
        """API key yoksa bos sonuc donmeli."""
        with patch("app.agents.research_agent.settings") as mock_settings:
            mock_settings.tavily_api_key = MagicMock()
            mock_settings.tavily_api_key.get_secret_value.return_value = ""

            results = await agent._web_search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_api_error(self, agent: ResearchAgent) -> None:
        """API hatasi durumunda bos sonuc donmeli."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPError("API error"),
        )
        mock_client.is_closed = False
        agent._http_client = mock_client

        with patch("app.agents.research_agent.settings") as mock_settings:
            mock_settings.tavily_api_key = MagicMock()
            mock_settings.tavily_api_key.get_secret_value.return_value = "test-key"

            results = await agent._web_search("test query")

        assert results == []


# === Analiz testleri ===


class TestAnalyze:
    """analyze() metodu testleri."""

    @pytest.mark.asyncio
    async def test_clean_analysis(self, agent: ResearchAgent) -> None:
        """Temiz arama: LOW risk, LOG action."""
        result = ResearchResult(
            research_type=ResearchType.WEB_SEARCH,
            search_results=[
                WebSearchResult(title="Test", url="https://example.com"),
            ],
        )
        analysis = await agent.analyze({"research_result": result.model_dump()})

        assert analysis["risk"] == RiskLevel.LOW.value
        assert analysis["action"] == ActionType.LOG.value

    @pytest.mark.asyncio
    async def test_unreliable_company_analysis(self, agent: ResearchAgent) -> None:
        """Guvenilmez firma: HIGH risk, IMMEDIATE action."""
        result = ResearchResult(
            research_type=ResearchType.COMPANY_CHECK,
            company_info=CompanyInfo(
                name="Shady Corp",
                reliability=ReliabilityLevel.LOW,
                red_flags=["SSL yok", "Adres yok"],
            ),
        )
        analysis = await agent.analyze({"research_result": result.model_dump()})

        assert analysis["risk"] == RiskLevel.HIGH.value
        assert analysis["urgency"] == UrgencyLevel.HIGH.value
        assert analysis["action"] == ActionType.IMMEDIATE.value

    @pytest.mark.asyncio
    async def test_all_low_score_suppliers(self, agent: ResearchAgent) -> None:
        """Tum tedarikciler dusuk puanli: HIGH risk."""
        result = ResearchResult(
            research_type=ResearchType.SUPPLIER_RESEARCH,
            suppliers=[
                SupplierScore(name="A", overall_score=2.0, reliability=ReliabilityLevel.LOW),
                SupplierScore(name="B", overall_score=3.0, reliability=ReliabilityLevel.LOW),
            ],
        )
        analysis = await agent.analyze({"research_result": result.model_dump()})

        assert analysis["risk"] == RiskLevel.HIGH.value

    @pytest.mark.asyncio
    async def test_mixed_suppliers(self, agent: ResearchAgent) -> None:
        """Karisik tedarikciler: MEDIUM risk."""
        result = ResearchResult(
            research_type=ResearchType.SUPPLIER_RESEARCH,
            suppliers=[
                SupplierScore(name="Good", overall_score=8.0, reliability=ReliabilityLevel.HIGH),
                SupplierScore(name="Bad", overall_score=3.0, reliability=ReliabilityLevel.LOW),
            ],
        )
        analysis = await agent.analyze({"research_result": result.model_dump()})

        assert analysis["risk"] == RiskLevel.MEDIUM.value

    @pytest.mark.asyncio
    async def test_failed_scraping_analysis(self, agent: ResearchAgent) -> None:
        """Basarisiz scraping: MEDIUM risk."""
        result = ResearchResult(
            research_type=ResearchType.SCRAPE,
            scraped_pages=[
                ScrapedPage(url="a.com", success=False),
                ScrapedPage(url="b.com", success=False),
                ScrapedPage(url="c.com", success=True, word_count=100),
            ],
        )
        analysis = await agent.analyze({"research_result": result.model_dump()})

        assert analysis["risk"] == RiskLevel.MEDIUM.value


# === Rapor format testleri ===


class TestReport:
    """report() metodu testleri."""

    @pytest.mark.asyncio
    async def test_report_contains_header(self, agent: ResearchAgent) -> None:
        """Rapor baslik icermeli."""
        task_result = TaskResult(
            success=True,
            data={
                "research_result": {"research_type": "web_search", "query": "test"},
                "analysis": {
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                    "summary": "Test tamamlandi.",
                    "details": [],
                },
            },
            message="ok",
        )
        report = await agent.report(task_result)
        assert "ARASTIRMA RAPORU" in report

    @pytest.mark.asyncio
    async def test_report_contains_supplier_details(self, agent: ResearchAgent) -> None:
        """Rapor tedarikci detaylarini icermeli."""
        task_result = TaskResult(
            success=True,
            data={
                "research_result": {"research_type": "supplier_research", "query": ""},
                "analysis": {
                    "risk": "medium",
                    "urgency": "medium",
                    "action": "notify",
                    "summary": "2 tedarikci incelendi.",
                    "details": [
                        {
                            "type": "supplier_research",
                            "total": 2,
                            "low_score_count": 1,
                            "unreliable_count": 1,
                            "best": "Good Corp",
                        },
                    ],
                },
            },
            message="ok",
        )
        report = await agent.report(task_result)
        assert "Tedarikci" in report
        assert "Good Corp" in report

    @pytest.mark.asyncio
    async def test_report_contains_company_check(self, agent: ResearchAgent) -> None:
        """Rapor firma kontrol detaylarini icermeli."""
        task_result = TaskResult(
            success=True,
            data={
                "research_result": {"research_type": "company_check", "query": ""},
                "analysis": {
                    "risk": "high",
                    "urgency": "high",
                    "action": "immediate",
                    "summary": "Guvenilmez firma.",
                    "details": [
                        {
                            "type": "company_check",
                            "name": "Shady Corp",
                            "reliability": "low",
                            "red_flags": ["SSL yok"],
                            "green_flags": [],
                        },
                    ],
                },
            },
            message="risk",
        )
        report = await agent.report(task_result)
        assert "Shady Corp" in report
        assert "SSL yok" in report

    @pytest.mark.asyncio
    async def test_report_contains_errors(self, agent: ResearchAgent) -> None:
        """Rapor hatalari icermeli."""
        task_result = TaskResult(
            success=False,
            data={
                "research_result": {"research_type": "scrape", "query": ""},
                "analysis": {
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                    "summary": "",
                    "details": [],
                },
            },
            message="hata",
            errors=["https://fail.com: Timeout"],
        )
        report = await agent.report(task_result)
        assert "HATALAR" in report
        assert "Timeout" in report


# === Execute testleri ===


class TestExecute:
    """execute() metodu testleri."""

    @pytest.mark.asyncio
    async def test_execute_invalid_type(self, agent: ResearchAgent) -> None:
        """Gecersiz arastirma tipi hata donmeli."""
        result = await agent.execute({"research_type": "invalid_type"})
        assert result.success is False
        assert "Gecersiz" in result.message

    @pytest.mark.asyncio
    async def test_execute_search_no_query(self, agent: ResearchAgent) -> None:
        """Sorgu olmadan web arama hata donmeli."""
        result = await agent.execute({"research_type": "web_search"})
        assert result.success is False
        assert "query" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_execute_scrape_no_urls(self, agent: ResearchAgent) -> None:
        """URL olmadan scraping hata donmeli."""
        result = await agent.execute({"research_type": "scrape"})
        assert result.success is False
        assert "urls" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_execute_company_check_no_url(self, agent: ResearchAgent) -> None:
        """URL olmadan firma kontrolu hata donmeli."""
        result = await agent.execute({"research_type": "company_check"})
        assert result.success is False
        assert "company_url" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_execute_supplier_no_data(self, agent: ResearchAgent) -> None:
        """Tedarikci listesi ve sorgu olmadan hata donmeli."""
        result = await agent.execute({"research_type": "supplier_research"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_scrape_success(self, agent: ResearchAgent) -> None:
        """Basarili scraping execute akisi."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response())
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock()
        agent._http_client = mock_client

        result = await agent.execute({
            "research_type": "scrape",
            "urls": ["https://example.com"],
        })

        assert result.success is True
        assert "research_result" in result.data
        assert "analysis" in result.data

    @pytest.mark.asyncio
    async def test_execute_company_check_success(self, agent: ResearchAgent) -> None:
        """Basarili firma kontrolu execute akisi."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response())
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock()
        agent._http_client = mock_client

        result = await agent.execute({
            "research_type": "company_check",
            "company_url": "https://testfirma.com",
        })

        assert result.success is True
        research = result.data["research_result"]
        assert research["company_info"] is not None
        assert research["company_info"]["has_ssl"] is True

    @pytest.mark.asyncio
    async def test_execute_supplier_research_success(self, agent: ResearchAgent) -> None:
        """Basarili tedarikci arastirma execute akisi."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=_mock_response())
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock()
        agent._http_client = mock_client

        result = await agent.execute({
            "research_type": "supplier_research",
            "suppliers": [
                {"name": "Test Firma", "url": "https://testfirma.com"},
            ],
        })

        assert result.success is True
        suppliers = result.data["research_result"]["suppliers"]
        assert len(suppliers) == 1
        assert suppliers[0]["name"] == "Test Firma"
        assert suppliers[0]["overall_score"] > 0


# === Model testleri ===


class TestModels:
    """Arastirma veri modeli testleri."""

    def test_research_config_defaults(self) -> None:
        config = ResearchConfig()
        assert config.max_results == 5
        assert config.search_engine == "tavily"
        assert len(config.supplier_criteria) == 5
        assert abs(sum(config.supplier_criteria.values()) - 1.0) < 0.01

    def test_web_search_result(self) -> None:
        r = WebSearchResult(query="test", title="Result", url="https://example.com")
        assert r.query == "test"
        assert r.relevance_score == 0.0

    def test_scraped_page_defaults(self) -> None:
        p = ScrapedPage()
        assert p.success is True
        assert p.word_count == 0

    def test_supplier_score_defaults(self) -> None:
        s = SupplierScore(name="Test")
        assert s.overall_score == 0.0
        assert s.reliability == ReliabilityLevel.UNKNOWN
        assert s.pros == []

    def test_company_info_defaults(self) -> None:
        c = CompanyInfo(name="Test")
        assert c.has_ssl is False
        assert c.reliability == ReliabilityLevel.UNKNOWN

    def test_research_result_defaults(self) -> None:
        r = ResearchResult()
        assert r.research_type == ResearchType.WEB_SEARCH
        assert r.search_results == []
        assert r.company_info is None

    def test_research_type_values(self) -> None:
        assert ResearchType.WEB_SEARCH.value == "web_search"
        assert ResearchType.SUPPLIER_RESEARCH.value == "supplier_research"
        assert ResearchType.COMPANY_CHECK.value == "company_check"
        assert ResearchType.SCRAPE.value == "scrape"
