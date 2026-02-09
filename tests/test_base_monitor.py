"""BaseMonitor ve MonitorResult testleri.

MonitorResult Pydantic modeli, BaseMonitor init/properties,
start/stop yasam dongusu, bildirim kararlari, alert formatlama
ve monitor dongusu davranislarini test eder.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import BaseAgent, TaskResult
from app.core.decision_matrix import ActionType, DecisionMatrix
from app.monitors.base_monitor import BaseMonitor, MonitorResult


# === ConcreteMonitor: test icin somut alt sinif ===


class ConcreteMonitor(BaseMonitor):
    """Test amacli somut monitor sinifi.

    BaseMonitor soyut oldugu icin dogrudan orneklenemez;
    bu sinif check() metodunu implement eder.
    """

    def __init__(
        self,
        name: str = "test_monitor",
        agent: BaseAgent | None = None,
        check_interval: int = 300,
        decision_matrix: DecisionMatrix | None = None,
        telegram_bot: object | None = None,
        check_result: MonitorResult | None = None,
        check_side_effect: Exception | None = None,
    ) -> None:
        """ConcreteMonitor'u baslatir.

        Args:
            name: Monitor adi.
            agent: Kullanilan agent (None ise mock olusturulur).
            check_interval: Kontrol araligi.
            decision_matrix: Karar matrisi.
            telegram_bot: Telegram bot nesnesi.
            check_result: check() metodunun donecegi sonuc.
            check_side_effect: check() metodunun firlatacagi hata.
        """
        if agent is None:
            agent = _make_mock_agent()
        if decision_matrix is None:
            decision_matrix = _make_mock_decision_matrix()
        super().__init__(
            name=name,
            agent=agent,
            check_interval=check_interval,
            decision_matrix=decision_matrix,
            telegram_bot=telegram_bot,
        )
        self._check_result = check_result or MonitorResult(
            monitor_name=name,
            risk="low",
            urgency="low",
            action="log",
            summary="Test kontrol sonucu",
        )
        self._check_side_effect = check_side_effect
        self.check_call_count = 0

    async def check(self) -> MonitorResult:
        """Test kontrol islemi.

        Returns:
            Yapilandirilan MonitorResult.

        Raises:
            Exception: check_side_effect verilmisse.
        """
        self.check_call_count += 1
        if self._check_side_effect:
            raise self._check_side_effect
        return self._check_result


# === Yardimci fonksiyonlar ===


def _make_mock_agent() -> MagicMock:
    """Mock BaseAgent olusturur."""
    agent = MagicMock(spec=BaseAgent)
    agent.name = "MockAgent"
    agent.run = AsyncMock(
        return_value=TaskResult(success=True, message="ok")
    )
    agent.execute = AsyncMock(
        return_value=TaskResult(success=True, message="ok")
    )
    agent.analyze = AsyncMock(return_value={})
    agent.report = AsyncMock(return_value="rapor")
    return agent


def _make_mock_decision_matrix(
    default_action: ActionType = ActionType.LOG,
) -> MagicMock:
    """Mock DecisionMatrix olusturur.

    Args:
        default_action: get_action_for varsayilan donus degeri.
    """
    dm = MagicMock(spec=DecisionMatrix)
    dm.get_action_for = MagicMock(return_value=default_action)
    return dm


def _make_mock_telegram() -> MagicMock:
    """Mock TelegramBot olusturur."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


def _make_monitor_result(
    monitor_name: str = "test_monitor",
    risk: str = "low",
    urgency: str = "low",
    action: str = "log",
    summary: str = "Test sonucu",
    details: list | None = None,
    alerts_sent: int = 0,
) -> MonitorResult:
    """Test icin MonitorResult olusturur."""
    return MonitorResult(
        monitor_name=monitor_name,
        risk=risk,
        urgency=urgency,
        action=action,
        summary=summary,
        details=details or [],
        alerts_sent=alerts_sent,
    )


# === Fixtures ===


@pytest.fixture
def mock_agent() -> MagicMock:
    """Mock BaseAgent."""
    return _make_mock_agent()


@pytest.fixture
def mock_decision_matrix() -> MagicMock:
    """Mock DecisionMatrix (varsayilan LOG)."""
    return _make_mock_decision_matrix()


@pytest.fixture
def mock_telegram() -> MagicMock:
    """Mock TelegramBot."""
    return _make_mock_telegram()


@pytest.fixture
def monitor(mock_agent: MagicMock, mock_decision_matrix: MagicMock) -> ConcreteMonitor:
    """Varsayilan ConcreteMonitor."""
    return ConcreteMonitor(
        name="test_monitor",
        agent=mock_agent,
        check_interval=300,
        decision_matrix=mock_decision_matrix,
    )


@pytest.fixture
def monitor_with_telegram(
    mock_agent: MagicMock,
    mock_decision_matrix: MagicMock,
    mock_telegram: MagicMock,
) -> ConcreteMonitor:
    """Telegram bot'lu ConcreteMonitor."""
    return ConcreteMonitor(
        name="alert_monitor",
        agent=mock_agent,
        check_interval=300,
        decision_matrix=mock_decision_matrix,
        telegram_bot=mock_telegram,
    )


# === TestMonitorResult ===


class TestMonitorResult:
    """MonitorResult Pydantic model testleri."""

    def test_default_values(self) -> None:
        """Varsayilan degerler dogru."""
        result = MonitorResult()
        assert result.monitor_name == ""
        assert result.risk == "low"
        assert result.urgency == "low"
        assert result.action == "log"
        assert result.summary == ""
        assert result.details == []
        assert result.alerts_sent == 0

    def test_check_time_auto_generated(self) -> None:
        """check_time otomatik olusturulur."""
        result = MonitorResult()
        assert isinstance(result.check_time, datetime)
        assert result.check_time.tzinfo is not None

    def test_custom_values(self) -> None:
        """Ozel degerlerle olusturma."""
        result = MonitorResult(
            monitor_name="security_monitor",
            risk="high",
            urgency="high",
            action="immediate",
            summary="Kritik tehdit tespit edildi",
            details=[{"host": "10.0.0.1", "issue": "brute force"}],
            alerts_sent=2,
        )
        assert result.monitor_name == "security_monitor"
        assert result.risk == "high"
        assert result.urgency == "high"
        assert result.action == "immediate"
        assert result.summary == "Kritik tehdit tespit edildi"
        assert len(result.details) == 1
        assert result.details[0]["host"] == "10.0.0.1"
        assert result.alerts_sent == 2

    def test_details_is_list_of_dicts(self) -> None:
        """Details alani dict listesi kabul eder."""
        details = [
            {"key1": "value1", "count": 10},
            {"key2": "value2", "count": 20},
        ]
        result = MonitorResult(details=details)
        assert len(result.details) == 2
        assert result.details[0]["count"] == 10
        assert result.details[1]["count"] == 20

    def test_alerts_sent_mutable(self) -> None:
        """alerts_sent sonradan degistirilebilir."""
        result = MonitorResult()
        assert result.alerts_sent == 0
        result.alerts_sent += 1
        assert result.alerts_sent == 1


# === TestBaseMonitorInit ===


class TestBaseMonitorInit:
    """BaseMonitor baslatma testleri."""

    def test_init_with_all_params(
        self, mock_agent: MagicMock, mock_decision_matrix: MagicMock, mock_telegram: MagicMock,
    ) -> None:
        """Tum parametrelerle baslatma."""
        mon = ConcreteMonitor(
            name="full_monitor",
            agent=mock_agent,
            check_interval=600,
            decision_matrix=mock_decision_matrix,
            telegram_bot=mock_telegram,
        )
        assert mon.name == "full_monitor"
        assert mon.agent is mock_agent
        assert mon.check_interval == 600
        assert mon.decision_matrix is mock_decision_matrix
        assert mon.telegram_bot is mock_telegram

    def test_init_minimal(self, mock_agent: MagicMock) -> None:
        """Minimal parametrelerle baslatma."""
        mon = ConcreteMonitor(name="minimal", agent=mock_agent)
        assert mon.name == "minimal"
        assert mon.telegram_bot is None
        assert mon.check_interval == 300

    def test_init_default_decision_matrix(self) -> None:
        """DecisionMatrix None ise mock olusturulur."""
        mon = ConcreteMonitor(name="dm_test")
        assert mon.decision_matrix is not None

    def test_init_internal_state(self, monitor: ConcreteMonitor) -> None:
        """Ic durum degiskenleri dogru baslatilir."""
        assert monitor._task is None
        assert monitor._running is False
        assert monitor._last_result is None
        assert monitor._check_count == 0

    def test_init_logger_name(self, monitor: ConcreteMonitor) -> None:
        """Logger ismi monitor adini icerir."""
        assert monitor.logger.name == "atlas.monitor.test_monitor"

    def test_is_running_initially_false(self, monitor: ConcreteMonitor) -> None:
        """is_running baslangicta False."""
        assert monitor.is_running is False

    def test_last_result_initially_none(self, monitor: ConcreteMonitor) -> None:
        """last_result baslangicta None."""
        assert monitor.last_result is None


# === TestBaseMonitorStartStop ===


class TestBaseMonitorStartStop:
    """Monitor start/stop yasam dongusu testleri."""

    @pytest.mark.asyncio
    async def test_start_sets_running(self, monitor: ConcreteMonitor) -> None:
        """Start _running'i True yapar ve task olusturur."""
        await monitor.start()

        assert monitor._running is True
        assert monitor._task is not None

        await monitor.stop()

    @pytest.mark.asyncio
    async def test_stop_sets_not_running(self, monitor: ConcreteMonitor) -> None:
        """Stop _running'i False yapar ve task'i siler."""
        await monitor.start()
        await monitor.stop()

        assert monitor._running is False
        assert monitor._task is None

    @pytest.mark.asyncio
    async def test_start_twice_does_not_create_second_task(
        self, monitor: ConcreteMonitor,
    ) -> None:
        """Cift start cagrisi ikinci task olusturmaz."""
        await monitor.start()
        first_task = monitor._task

        await monitor.start()
        second_task = monitor._task

        assert first_task is second_task

        await monitor.stop()

    @pytest.mark.asyncio
    async def test_stop_without_start(self, monitor: ConcreteMonitor) -> None:
        """Start edilmeden stop hatasz calisir."""
        await monitor.stop()

        assert monitor._running is False
        assert monitor._task is None

    @pytest.mark.asyncio
    async def test_is_running_true_while_active(self, monitor: ConcreteMonitor) -> None:
        """Aktif monitor icin is_running True doner."""
        await monitor.start()

        assert monitor.is_running is True

        await monitor.stop()

    @pytest.mark.asyncio
    async def test_is_running_false_after_stop(self, monitor: ConcreteMonitor) -> None:
        """Durdurulan monitor icin is_running False doner."""
        await monitor.start()
        await monitor.stop()

        assert monitor.is_running is False


# === TestBaseMonitorNotification ===


class TestBaseMonitorNotification:
    """Bildirim kararlari ve alert testleri."""

    def test_should_notify_returns_false_for_log(self, monitor: ConcreteMonitor) -> None:
        """LOG aksiyonu icin bildirim gerekli degil."""
        monitor.decision_matrix.get_action_for = MagicMock(return_value=ActionType.LOG)

        result = monitor._should_notify("low", "low")

        assert result is False
        monitor.decision_matrix.get_action_for.assert_called_once_with("low", "low")

    def test_should_notify_returns_true_for_notify(self, monitor: ConcreteMonitor) -> None:
        """NOTIFY aksiyonu icin bildirim gerekli."""
        monitor.decision_matrix.get_action_for = MagicMock(return_value=ActionType.NOTIFY)

        result = monitor._should_notify("medium", "low")

        assert result is True

    def test_should_notify_returns_true_for_auto_fix(self, monitor: ConcreteMonitor) -> None:
        """AUTO_FIX aksiyonu icin bildirim gerekli."""
        monitor.decision_matrix.get_action_for = MagicMock(return_value=ActionType.AUTO_FIX)

        result = monitor._should_notify("medium", "high")

        assert result is True

    def test_should_notify_returns_true_for_immediate(self, monitor: ConcreteMonitor) -> None:
        """IMMEDIATE aksiyonu icin bildirim gerekli."""
        monitor.decision_matrix.get_action_for = MagicMock(return_value=ActionType.IMMEDIATE)

        result = monitor._should_notify("high", "high")

        assert result is True

    def test_format_alert_contains_monitor_name(self, monitor: ConcreteMonitor) -> None:
        """Alert metni monitor adini icerir."""
        result = _make_monitor_result(monitor_name="security_monitor")

        alert = monitor._format_alert(result)

        assert "SECURITY_MONITOR" in alert

    def test_format_alert_contains_risk_and_urgency(self, monitor: ConcreteMonitor) -> None:
        """Alert metni risk ve aciliyet bilgisini icerir."""
        result = _make_monitor_result(risk="high", urgency="medium")

        alert = monitor._format_alert(result)

        assert "high" in alert
        assert "medium" in alert

    def test_format_alert_contains_action(self, monitor: ConcreteMonitor) -> None:
        """Alert metni aksiyon tipini icerir."""
        result = _make_monitor_result(action="immediate")

        alert = monitor._format_alert(result)

        assert "immediate" in alert

    def test_format_alert_contains_summary(self, monitor: ConcreteMonitor) -> None:
        """Alert metni ozet bilgisini icerir."""
        result = _make_monitor_result(summary="Sunucu yanit vermiyor")

        alert = monitor._format_alert(result)

        assert "Sunucu yanit vermiyor" in alert

    def test_format_alert_contains_details(self, monitor: ConcreteMonitor) -> None:
        """Alert metni detay bilgilerini icerir."""
        result = _make_monitor_result(
            details=[{"host": "10.0.0.1", "status": "down"}],
        )

        alert = monitor._format_alert(result)

        assert "host: 10.0.0.1" in alert
        assert "status: down" in alert

    def test_format_alert_limits_details_to_10(self, monitor: ConcreteMonitor) -> None:
        """Alert metni en fazla 10 detay gosterir."""
        details = [{"item": f"detail_{i}"} for i in range(15)]
        result = _make_monitor_result(details=details)

        alert = monitor._format_alert(result)

        assert "detail_9" in alert
        assert "detail_10" not in alert

    def test_format_alert_without_details(self, monitor: ConcreteMonitor) -> None:
        """Detay olmadan alert metni olusturulur."""
        result = _make_monitor_result(details=[])

        alert = monitor._format_alert(result)

        assert "UYARI" in alert

    @pytest.mark.asyncio
    async def test_send_alert_with_telegram(
        self, monitor_with_telegram: ConcreteMonitor,
    ) -> None:
        """Telegram bot varken bildirim gonderilir."""
        result = _make_monitor_result(summary="Test uyarisi")

        await monitor_with_telegram._send_alert(result)

        monitor_with_telegram.telegram_bot.send_message.assert_awaited_once()
        call_args = monitor_with_telegram.telegram_bot.send_message.call_args[0]
        assert "Test uyarisi" in call_args[0]

    @pytest.mark.asyncio
    async def test_send_alert_increments_alerts_sent(
        self, monitor_with_telegram: ConcreteMonitor,
    ) -> None:
        """Basarili bildirim sonrasi alerts_sent artar."""
        result = _make_monitor_result()
        assert result.alerts_sent == 0

        await monitor_with_telegram._send_alert(result)

        assert result.alerts_sent == 1

    @pytest.mark.asyncio
    async def test_send_alert_without_telegram(self, monitor: ConcreteMonitor) -> None:
        """Telegram bot yokken bildirim sessizce atlanir."""
        result = _make_monitor_result()

        await monitor._send_alert(result)

        assert result.alerts_sent == 0

    @pytest.mark.asyncio
    async def test_send_alert_telegram_error_handled(
        self, monitor_with_telegram: ConcreteMonitor,
    ) -> None:
        """Telegram hatasi sessizce loglanir."""
        monitor_with_telegram.telegram_bot.send_message = AsyncMock(
            side_effect=Exception("Telegram baglanti hatasi")
        )
        result = _make_monitor_result()

        await monitor_with_telegram._send_alert(result)

        # alerts_sent artmamali (hata oldugu icin)
        assert result.alerts_sent == 0


# === TestBaseMonitorLoop ===


class TestBaseMonitorLoop:
    """Monitor dongusu davranis testleri."""

    @pytest.mark.asyncio
    async def test_monitor_loop_runs_check(self) -> None:
        """Dongudeki check() en az bir kez cagrilir."""
        mon = ConcreteMonitor(
            name="loop_test",
            check_interval=1,
        )

        await mon.start()
        await asyncio.sleep(0.1)
        await mon.stop()

        assert mon.check_call_count >= 1

    @pytest.mark.asyncio
    async def test_monitor_loop_updates_last_result(self) -> None:
        """Dongu last_result'i gunceller."""
        expected_result = _make_monitor_result(
            monitor_name="loop_monitor",
            summary="Dongu test sonucu",
        )
        mon = ConcreteMonitor(
            name="loop_monitor",
            check_interval=1,
            check_result=expected_result,
        )

        await mon.start()
        await asyncio.sleep(0.1)
        await mon.stop()

        assert mon.last_result is not None
        assert mon.last_result.summary == "Dongu test sonucu"

    @pytest.mark.asyncio
    async def test_monitor_loop_increments_check_count(self) -> None:
        """Dongu _check_count'u arttirir."""
        mon = ConcreteMonitor(
            name="count_test",
            check_interval=1,
        )

        await mon.start()
        await asyncio.sleep(0.1)
        await mon.stop()

        assert mon._check_count >= 1

    @pytest.mark.asyncio
    async def test_monitor_loop_sends_alert_when_needed(self) -> None:
        """Bildirim gerektiginde alert gonderilir."""
        telegram = _make_mock_telegram()
        dm = _make_mock_decision_matrix(default_action=ActionType.NOTIFY)
        result = _make_monitor_result(
            risk="medium",
            urgency="high",
            summary="Dikkat gerektiren durum",
        )
        mon = ConcreteMonitor(
            name="alert_loop",
            check_interval=1,
            decision_matrix=dm,
            telegram_bot=telegram,
            check_result=result,
        )

        await mon.start()
        await asyncio.sleep(0.1)
        await mon.stop()

        telegram.send_message.assert_awaited()

    @pytest.mark.asyncio
    async def test_monitor_loop_no_alert_for_log(self) -> None:
        """LOG aksiyonunda alert gonderilmez."""
        telegram = _make_mock_telegram()
        dm = _make_mock_decision_matrix(default_action=ActionType.LOG)
        mon = ConcreteMonitor(
            name="no_alert_loop",
            check_interval=1,
            decision_matrix=dm,
            telegram_bot=telegram,
        )

        await mon.start()
        await asyncio.sleep(0.1)
        await mon.stop()

        telegram.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_monitor_loop_handles_check_exception(self) -> None:
        """check() hatasi donguyu durdurmaz."""
        mon = ConcreteMonitor(
            name="error_loop",
            check_interval=1,
            check_side_effect=RuntimeError("Baglanti hatasi"),
        )

        await mon.start()
        await asyncio.sleep(0.2)
        await mon.stop()

        # Hata sonrasi dongu devam etmeli
        assert mon.check_call_count >= 1

    @pytest.mark.asyncio
    async def test_get_info_basic(self, monitor: ConcreteMonitor) -> None:
        """get_info temel bilgileri dondurur."""
        info = monitor.get_info()

        assert info["name"] == "test_monitor"
        assert info["is_running"] is False
        assert info["check_interval"] == 300
        assert info["check_count"] == 0
        assert info["last_check"] is None

    @pytest.mark.asyncio
    async def test_get_info_after_check(self) -> None:
        """Kontrol sonrasi get_info guncellenmis bilgi dondurur."""
        mon = ConcreteMonitor(
            name="info_test",
            check_interval=1,
        )

        await mon.start()
        await asyncio.sleep(0.1)
        await mon.stop()

        info = mon.get_info()

        assert info["check_count"] >= 1
        assert info["last_check"] is not None
