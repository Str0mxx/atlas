"""AdsMonitor unit testleri.

MarketingAgent mock'lanarak reklam performans izleme
davranislari test edilir. Iyi/kotu performans, reddedilen
reklamlar ve API hata senaryolari kapsanir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import TaskResult
from app.monitors.ads_monitor import AdsMonitor
from app.monitors.base_monitor import MonitorResult


# === Fixtures ===


@pytest.fixture
def mock_agent_cls():
    """MarketingAgent sinifini mock'lar."""
    with patch("app.monitors.ads_monitor.MarketingAgent") as cls:
        cls.return_value = AsyncMock()
        yield cls


@pytest.fixture
def monitor(mock_agent_cls):
    """Mock agent ile yapilandirilmis AdsMonitor."""
    mon = AdsMonitor()
    return mon


@pytest.fixture
def good_performance_result() -> TaskResult:
    """Iyi reklam performansi sonucu."""
    return TaskResult(
        success=True,
        data={
            "analysis": {
                "risk": "low",
                "urgency": "low",
                "action": "log",
                "summary": "Kampanya performansi iyi.",
                "details": [
                    {"campaign": "Sac Ekimi", "ctr": 3.5, "cpc": 0.45},
                ],
            },
        },
        message="ok",
    )


@pytest.fixture
def bad_performance_result() -> TaskResult:
    """Kotu reklam performansi sonucu."""
    return TaskResult(
        success=True,
        data={
            "analysis": {
                "risk": "medium",
                "urgency": "medium",
                "action": "notify",
                "summary": "CTR dusuk, optimizasyon gerekli.",
                "details": [
                    {"campaign": "Dis Tedavisi", "ctr": 0.8, "cpc": 1.20},
                ],
            },
        },
        message="uyari",
    )


@pytest.fixture
def disapproval_result() -> TaskResult:
    """Reddedilen reklam iceren sonuc."""
    return TaskResult(
        success=True,
        data={
            "analysis": {
                "risk": "low",
                "urgency": "low",
                "action": "log",
                "summary": "Kampanya kontrolu tamamlandi.",
                "details": [
                    {"campaign": "Sac Ekimi", "ctr": 3.0, "cpc": 0.50},
                ],
                "disapprovals": [
                    {"ad_id": "123", "reason": "Misleading content"},
                    {"ad_id": "456", "reason": "Policy violation"},
                ],
            },
        },
        message="disapproval",
    )


@pytest.fixture
def api_error_result() -> TaskResult:
    """Google Ads API hata sonucu."""
    return TaskResult(
        success=False,
        data={},
        message="Google Ads API hatasi: QuotaExceeded",
        errors=["QuotaExceeded"],
    )


# === Init testleri ===


class TestAdsMonitorInit:
    """AdsMonitor olusturma testleri."""

    def test_default_init(self, mock_agent_cls) -> None:
        """Varsayilan parametrelerle monitor olusturulmali."""
        monitor = AdsMonitor()
        assert monitor.name == "ads"
        assert monitor.config is None
        assert monitor.check_interval == 3600
        mock_agent_cls.assert_called_once()

    def test_custom_check_interval(self, mock_agent_cls) -> None:
        """Ozel kontrol araligi ayarlanabilmeli."""
        monitor = AdsMonitor(check_interval=1800)
        assert monitor.check_interval == 1800

    def test_agent_created_with_config(self, mock_agent_cls) -> None:
        """Agent marketing config ile olusturulmali."""
        config = MagicMock()
        monitor = AdsMonitor(config=config)
        mock_agent_cls.assert_called_once_with(config=config)
        assert monitor.config is config

    def test_telegram_bot_assignment(self, mock_agent_cls) -> None:
        """Telegram bot nesnesi atanabilmeli."""
        bot = MagicMock()
        monitor = AdsMonitor(telegram_bot=bot)
        assert monitor.telegram_bot is bot

    def test_decision_matrix_default(self, mock_agent_cls) -> None:
        """Karar matrisi belirtilmezse varsayilan olusturulmali."""
        monitor = AdsMonitor()
        assert monitor.decision_matrix is not None


# === Check testleri ===


class TestAdsMonitorCheck:
    """AdsMonitor.check() metodu testleri."""

    @pytest.mark.asyncio
    async def test_good_performance(self, monitor, good_performance_result) -> None:
        """Iyi performans: low risk, low urgency, log action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = good_performance_result

        result = await monitor.check()

        assert isinstance(result, MonitorResult)
        assert result.monitor_name == "ads"
        assert result.risk == "low"
        assert result.urgency == "low"
        assert result.action == "log"
        assert "iyi" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_bad_performance(self, monitor, bad_performance_result) -> None:
        """Kotu performans: medium risk, medium urgency, notify action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = bad_performance_result

        result = await monitor.check()

        assert result.risk == "medium"
        assert result.urgency == "medium"
        assert result.action == "notify"
        assert "ctr" in result.summary.lower() or "optimizasyon" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_disapproval_escalates_to_high(
        self, monitor, disapproval_result,
    ) -> None:
        """Reddedilen reklam: risk ve urgency HIGH'a yukseltilmeli."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = disapproval_result

        result = await monitor.check()

        assert result.risk == "high"
        assert result.urgency == "high"
        assert result.action == "immediate"
        assert "reddedilen" in result.summary.lower()
        assert "2 adet" in result.summary

    @pytest.mark.asyncio
    async def test_disapproval_details_prepended(
        self, monitor, disapproval_result,
    ) -> None:
        """Reddedilen reklam detaylari listenin basina eklenmeli."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = disapproval_result

        result = await monitor.check()

        # Ilk 2 detail disapproval olmali
        assert result.details[0]["disapproval"]["ad_id"] == "123"
        assert result.details[1]["disapproval"]["ad_id"] == "456"
        # Sonraki detail kampanya bilgisi olmali
        assert result.details[2]["campaign"] == "Sac Ekimi"

    @pytest.mark.asyncio
    async def test_api_error(self, monitor, api_error_result) -> None:
        """API hatasi: medium risk, medium urgency, notify action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = api_error_result

        result = await monitor.check()

        assert result.risk == "medium"
        assert result.urgency == "medium"
        assert result.action == "notify"
        assert "basarisiz" in result.summary.lower()
        assert len(result.details) == 1
        assert result.details[0]["error"] == "QuotaExceeded"

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
        assert result.summary == "Reklam kontrolu tamamlandi"

    @pytest.mark.asyncio
    async def test_check_calls_agent_run(self, monitor) -> None:
        """check() agent.run'i dogru task ile cagirmali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(success=True, data={})

        await monitor.check()

        monitor.agent.run.assert_called_once_with(
            {"description": "Periyodik reklam performans kontrolu"},
        )
