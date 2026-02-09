"""OpportunityMonitor unit testleri.

ResearchAgent mock'lanarak firsat izleme davranislari test edilir.
Normal tarama, dusuk guvenilirlik, on-demand kontrol ve
hata senaryolari kapsanir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import TaskResult
from app.monitors.base_monitor import MonitorResult
from app.monitors.opportunity_monitor import OpportunityMonitor


# === Fixtures ===


@pytest.fixture
def mock_agent_cls():
    """ResearchAgent sinifini mock'lar."""
    with patch("app.monitors.opportunity_monitor.ResearchAgent") as cls:
        cls.return_value = AsyncMock()
        yield cls


@pytest.fixture
def monitor(mock_agent_cls):
    """Mock agent ile yapilandirilmis OpportunityMonitor."""
    mon = OpportunityMonitor()
    return mon


@pytest.fixture
def monitor_with_suppliers(mock_agent_cls):
    """Tedarikci listesi olan OpportunityMonitor."""
    suppliers = [
        {"name": "Tedarikci A", "url": "https://supplier-a.com"},
        {"name": "Tedarikci B", "url": "https://supplier-b.com"},
    ]
    companies = ["https://competitor1.com", "https://competitor2.com"]
    mon = OpportunityMonitor(
        watched_suppliers=suppliers,
        watched_companies=companies,
    )
    return mon


@pytest.fixture
def normal_scan_result() -> TaskResult:
    """Normal firsat izleme sonucu."""
    return TaskResult(
        success=True,
        data={
            "analysis": {
                "risk": "low",
                "urgency": "low",
                "action": "log",
                "summary": "Tedarikci fiyatlari stabil.",
                "details": [
                    {"supplier": "Tedarikci A", "price_change": 0.0},
                ],
            },
        },
        message="ok",
    )


@pytest.fixture
def low_reliability_result() -> TaskResult:
    """Dusuk firma guvenilirlik sonucu."""
    return TaskResult(
        success=True,
        data={
            "analysis": {
                "risk": "medium",
                "urgency": "medium",
                "action": "notify",
                "summary": "Tedarikci B guvenilirlik puani dusuk.",
                "details": [
                    {"supplier": "Tedarikci B", "reliability_score": 35, "issues": ["Geciken teslimler"]},
                ],
            },
        },
        message="uyari",
    )


@pytest.fixture
def opportunity_found_result() -> TaskResult:
    """Firsat tespiti iceren sonuc."""
    return TaskResult(
        success=True,
        data={
            "analysis": {
                "risk": "low",
                "urgency": "medium",
                "action": "notify",
                "summary": "Yeni tedarikci firsati: %30 daha ucuz hammadde.",
                "details": [
                    {"type": "price_opportunity", "supplier": "Yeni Tedarikci", "savings": "30%"},
                ],
            },
        },
        message="firsat",
    )


@pytest.fixture
def scan_failure_result() -> TaskResult:
    """Basarisiz firsat izleme sonucu."""
    return TaskResult(
        success=False,
        data={},
        message="Web scraping hatasi",
        errors=["Connection timeout"],
    )


# === Init testleri ===


class TestOpportunityMonitorInit:
    """OpportunityMonitor olusturma testleri."""

    def test_default_init(self, mock_agent_cls) -> None:
        """Varsayilan parametrelerle monitor olusturulmali."""
        monitor = OpportunityMonitor()
        assert monitor.name == "opportunity"
        assert monitor.config is None
        assert monitor.watched_suppliers == []
        assert monitor.watched_companies == []
        assert monitor.check_interval == 86400
        mock_agent_cls.assert_called_once()

    def test_custom_check_interval(self, mock_agent_cls) -> None:
        """Ozel kontrol araligi ayarlanabilmeli."""
        monitor = OpportunityMonitor(check_interval=43200)
        assert monitor.check_interval == 43200

    def test_agent_created_with_config(self, mock_agent_cls) -> None:
        """Agent research config ile olusturulmali."""
        config = MagicMock()
        monitor = OpportunityMonitor(config=config)
        mock_agent_cls.assert_called_once_with(config=config)
        assert monitor.config is config

    def test_watched_suppliers_set(self, mock_agent_cls) -> None:
        """Izlenecek tedarikci listesi ayarlanabilmeli."""
        suppliers = [{"name": "Test", "url": "https://test.com"}]
        monitor = OpportunityMonitor(watched_suppliers=suppliers)
        assert monitor.watched_suppliers == suppliers

    def test_watched_companies_set(self, mock_agent_cls) -> None:
        """Izlenecek firma URL'leri ayarlanabilmeli."""
        companies = ["https://company1.com"]
        monitor = OpportunityMonitor(watched_companies=companies)
        assert monitor.watched_companies == companies

    def test_telegram_bot_assignment(self, mock_agent_cls) -> None:
        """Telegram bot nesnesi atanabilmeli."""
        bot = MagicMock()
        monitor = OpportunityMonitor(telegram_bot=bot)
        assert monitor.telegram_bot is bot

    def test_decision_matrix_default(self, mock_agent_cls) -> None:
        """Karar matrisi belirtilmezse varsayilan olusturulmali."""
        monitor = OpportunityMonitor()
        assert monitor.decision_matrix is not None


# === Check testleri ===


class TestOpportunityMonitorCheck:
    """OpportunityMonitor.check() metodu testleri."""

    @pytest.mark.asyncio
    async def test_normal_scan(self, monitor, normal_scan_result) -> None:
        """Normal tarama: low risk, low urgency, log action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = normal_scan_result

        result = await monitor.check()

        assert isinstance(result, MonitorResult)
        assert result.monitor_name == "opportunity"
        assert result.risk == "low"
        assert result.urgency == "low"
        assert result.action == "log"
        assert "stabil" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_low_reliability(self, monitor, low_reliability_result) -> None:
        """Dusuk guvenilirlik: medium risk, medium urgency, notify action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = low_reliability_result

        result = await monitor.check()

        assert result.risk == "medium"
        assert result.urgency == "medium"
        assert result.action == "notify"
        assert "guvenilirlik" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_opportunity_found(self, monitor, opportunity_found_result) -> None:
        """Firsat tespiti: low risk, medium urgency, notify action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = opportunity_found_result

        result = await monitor.check()

        assert result.risk == "low"
        assert result.urgency == "medium"
        assert result.action == "notify"
        assert "firsat" in result.summary.lower() or "ucuz" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_scan_failure(self, monitor, scan_failure_result) -> None:
        """Tarama hatasi: low risk, low urgency, log action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = scan_failure_result

        result = await monitor.check()

        assert result.risk == "low"
        assert result.urgency == "low"
        assert result.action == "log"
        assert "basarisiz" in result.summary.lower()
        assert len(result.details) == 1
        assert result.details[0]["error"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_check_with_defaults_when_no_analysis(self, monitor) -> None:
        """Analiz verisi bos oldugunda varsayilan degerler kullanilmali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(
            success=True,
            data={"analysis": {}},
        )

        result = await monitor.check()

        assert result.risk == "low"
        assert result.urgency == "low"
        assert result.action == "log"
        assert result.summary == "Firsat izleme tamamlandi"

    @pytest.mark.asyncio
    async def test_check_passes_suppliers_and_companies(
        self, monitor_with_suppliers,
    ) -> None:
        """check() izlenen tedarikci ve firmalari agent'a iletmeli."""
        monitor_with_suppliers.agent = AsyncMock()
        monitor_with_suppliers.agent.run.return_value = TaskResult(
            success=True,
            data={},
        )

        await monitor_with_suppliers.check()

        call_args = monitor_with_suppliers.agent.run.call_args[0][0]
        assert call_args["research_type"] == "supplier_research"
        assert len(call_args["suppliers"]) == 2
        assert call_args["suppliers"][0]["name"] == "Tedarikci A"
        assert len(call_args["companies"]) == 2

    @pytest.mark.asyncio
    async def test_check_calls_agent_run(self, monitor) -> None:
        """check() agent.run'i dogru task ile cagirmali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(success=True, data={})

        await monitor.check()

        call_args = monitor.agent.run.call_args[0][0]
        assert call_args["description"] == "Periyodik firsat izleme"
        assert call_args["research_type"] == "supplier_research"


# === On-demand testleri ===


class TestOpportunityMonitorOnDemand:
    """OpportunityMonitor.check_on_demand() metodu testleri."""

    @pytest.mark.asyncio
    async def test_on_demand_success(self, monitor) -> None:
        """On-demand basarili kontrol."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(
            success=True,
            data={
                "analysis": {
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                    "summary": "Tedarikci fiyatlari kontrol edildi.",
                    "details": [{"price_check": "ok"}],
                },
            },
        )

        task = {"description": "Tek seferlik tedarikci kontrolu", "url": "https://test.com"}
        result = await monitor.check_on_demand(task)

        assert isinstance(result, MonitorResult)
        assert result.monitor_name == "opportunity"
        assert result.risk == "low"
        assert result.summary == "Tedarikci fiyatlari kontrol edildi."

    @pytest.mark.asyncio
    async def test_on_demand_passes_custom_task(self, monitor) -> None:
        """On-demand ozel task'i agent'a iletmeli."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(success=True, data={})

        custom_task = {
            "description": "Ozel arastirma",
            "research_type": "company_check",
            "url": "https://competitor.com",
        }
        await monitor.check_on_demand(custom_task)

        monitor.agent.run.assert_called_once_with(custom_task)

    @pytest.mark.asyncio
    async def test_on_demand_failure(self, monitor) -> None:
        """On-demand hata durumu: low risk, low urgency, log action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(
            success=False,
            data={},
            message="URL erisilemez",
            errors=["HTTP 404"],
        )

        task = {"description": "Kontrol", "url": "https://broken.com"}
        result = await monitor.check_on_demand(task)

        assert result.risk == "low"
        assert result.urgency == "low"
        assert result.action == "log"
        assert "on-demand" in result.summary.lower()
        assert "basarisiz" in result.summary.lower()
        assert result.details[0]["error"] == "HTTP 404"

    @pytest.mark.asyncio
    async def test_on_demand_defaults_when_no_analysis(self, monitor) -> None:
        """On-demand analiz verisi bos oldugunda varsayilan degerler kullanilmali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(
            success=True,
            data={"analysis": {}},
        )

        task = {"description": "Bos analiz testi"}
        result = await monitor.check_on_demand(task)

        assert result.risk == "low"
        assert result.urgency == "low"
        assert result.action == "log"
        assert result.summary == "On-demand kontrol tamamlandi"
