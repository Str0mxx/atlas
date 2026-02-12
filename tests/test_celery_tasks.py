"""ATLAS Celery gorev testleri.

Celery app yapilandirmasi, monitor tasklari,
sonuc isleme ve retry mekanizmasi testleri.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import MaxRetriesExceededError

from app.celery_app import celery_app
from app.config import settings
from app.monitors.base_monitor import MonitorResult
from app.tasks.monitor_tasks import (
    _format_notification,
    _handle_result,
    _send_telegram_notification,
    run_ads_monitor,
    run_opportunity_monitor,
    run_security_monitor,
    run_server_monitor,
)


# === Yardimci fonksiyonlar ===


def _make_monitor_result(
    monitor_name: str = "test",
    risk: str = "low",
    urgency: str = "low",
    action: str = "log",
    summary: str = "Test ozeti",
    details: list | None = None,
) -> MonitorResult:
    """Test icin MonitorResult olusturur."""
    return MonitorResult(
        monitor_name=monitor_name,
        check_time=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        risk=risk,
        urgency=urgency,
        action=action,
        summary=summary,
        details=details or [],
    )


def _make_mock_monitor(result: MonitorResult | None = None) -> MagicMock:
    """Mock monitor olusturur."""
    mock = MagicMock()
    mock.check = AsyncMock(return_value=result or _make_monitor_result())
    return mock


# === TestCeleryAppConfig ===


class TestCeleryAppConfig:
    """Celery uygulama yapilandirma testleri."""

    def test_broker_url_matches_settings(self) -> None:
        """Broker URL'i settings ile eslesir."""
        assert celery_app.conf.broker_url == settings.celery_broker_url

    def test_result_backend_matches_settings(self) -> None:
        """Result backend settings ile eslesir."""
        assert celery_app.conf.result_backend == settings.celery_result_backend

    def test_task_serializer_is_json(self) -> None:
        """Task serializer JSON olmali."""
        assert celery_app.conf.task_serializer == "json"

    def test_result_serializer_is_json(self) -> None:
        """Result serializer JSON olmali."""
        assert celery_app.conf.result_serializer == "json"

    def test_accept_content_is_json(self) -> None:
        """Kabul edilen icerik JSON olmali."""
        assert "json" in celery_app.conf.accept_content

    def test_timezone_is_utc(self) -> None:
        """Zaman dilimi UTC olmali."""
        assert celery_app.conf.timezone == "UTC"

    def test_enable_utc(self) -> None:
        """UTC etkin olmali."""
        assert celery_app.conf.enable_utc is True

    def test_task_track_started(self) -> None:
        """Task baslangiclari izlenmeli."""
        assert celery_app.conf.task_track_started is True

    def test_task_acks_late(self) -> None:
        """Task onaylari gec olmali (guvenilirlik)."""
        assert celery_app.conf.task_acks_late is True

    def test_worker_prefetch_multiplier(self) -> None:
        """Worker prefetch multiplier 1 olmali."""
        assert celery_app.conf.worker_prefetch_multiplier == 1

    def test_celery_app_name(self) -> None:
        """Celery app adi atlas olmali."""
        assert celery_app.main == "atlas"

    def test_beat_schedule_has_four_tasks(self) -> None:
        """Beat schedule 4 gorev icermeli."""
        assert len(celery_app.conf.beat_schedule) == 4

    def test_beat_schedule_server_monitor(self) -> None:
        """Server monitor zamanlama dogru olmali."""
        entry = celery_app.conf.beat_schedule["server-monitor"]
        assert entry["task"] == "app.tasks.monitor_tasks.run_server_monitor"
        assert entry["schedule"] == settings.server_monitor_interval

    def test_beat_schedule_security_monitor(self) -> None:
        """Security monitor zamanlama dogru olmali."""
        entry = celery_app.conf.beat_schedule["security-monitor"]
        assert entry["task"] == "app.tasks.monitor_tasks.run_security_monitor"
        assert entry["schedule"] == settings.security_monitor_interval

    def test_beat_schedule_ads_monitor(self) -> None:
        """Ads monitor zamanlama dogru olmali."""
        entry = celery_app.conf.beat_schedule["ads-monitor"]
        assert entry["task"] == "app.tasks.monitor_tasks.run_ads_monitor"
        assert entry["schedule"] == settings.ads_monitor_interval

    def test_beat_schedule_opportunity_monitor(self) -> None:
        """Opportunity monitor zamanlama dogru olmali."""
        entry = celery_app.conf.beat_schedule["opportunity-monitor"]
        assert entry["task"] == "app.tasks.monitor_tasks.run_opportunity_monitor"
        assert entry["schedule"] == settings.opportunity_monitor_interval

    def test_worker_hijack_root_logger_disabled(self) -> None:
        """Root logger hijack devre disi olmali."""
        assert celery_app.conf.worker_hijack_root_logger is False


# === TestFormatNotification ===


class TestFormatNotification:
    """Bildirim formatlama testleri."""

    def test_basic_format(self) -> None:
        """Temel formatlama dogru olmali."""
        result = _make_monitor_result(
            monitor_name="server",
            risk="high",
            urgency="high",
            action="immediate",
            summary="CPU %95",
        )
        text = _format_notification(result)
        assert "SERVER MONITOR" in text
        assert "Risk: high" in text
        assert "Aciliyet: high" in text
        assert "Aksiyon: immediate" in text
        assert "CPU %95" in text

    def test_format_with_details(self) -> None:
        """Detayli formatlama dogru olmali."""
        result = _make_monitor_result(
            monitor_name="security",
            details=[{"type": "failed_login", "ip": "1.2.3.4"}],
        )
        text = _format_notification(result)
        assert "type: failed_login" in text
        assert "ip: 1.2.3.4" in text

    def test_format_limits_details_to_five(self) -> None:
        """Detaylar en fazla 5 tane gosterilmeli."""
        details = [{"index": str(i)} for i in range(10)]
        result = _make_monitor_result(details=details)
        text = _format_notification(result)
        assert "index: 4" in text
        assert "index: 5" not in text

    def test_format_empty_details(self) -> None:
        """Bos detay listesi sorunsuz olmali."""
        result = _make_monitor_result(details=[])
        text = _format_notification(result)
        assert "MONITOR" in text

    def test_format_monitor_name_uppercase(self) -> None:
        """Monitor adi buyuk harfle gosterilmeli."""
        result = _make_monitor_result(monitor_name="opportunity")
        text = _format_notification(result)
        assert "OPPORTUNITY MONITOR" in text


# === TestHandleResult ===


class TestHandleResult:
    """Sonuc isleme testleri."""

    @patch("app.tasks.monitor_tasks._send_telegram_notification")
    def test_log_action_no_notification(self, mock_notify: MagicMock) -> None:
        """LOG aksiyonu bildirim gondermemeli."""
        result = _make_monitor_result(action="log")
        _handle_result(result)
        mock_notify.assert_not_called()

    @patch("app.tasks.monitor_tasks._send_telegram_notification")
    def test_notify_action_sends_notification(self, mock_notify: MagicMock) -> None:
        """NOTIFY aksiyonu bildirim gondermeli."""
        result = _make_monitor_result(action="notify")
        _handle_result(result)
        mock_notify.assert_called_once_with(result)

    @patch("app.tasks.monitor_tasks._send_telegram_notification")
    def test_auto_fix_sends_notification(self, mock_notify: MagicMock) -> None:
        """AUTO_FIX aksiyonu bildirim gondermeli."""
        result = _make_monitor_result(action="auto_fix")
        _handle_result(result)
        mock_notify.assert_called_once_with(result)

    @patch("app.tasks.monitor_tasks._send_telegram_notification")
    def test_immediate_sends_notification(self, mock_notify: MagicMock) -> None:
        """IMMEDIATE aksiyonu bildirim gondermeli."""
        result = _make_monitor_result(action="immediate")
        _handle_result(result)
        mock_notify.assert_called_once_with(result)


# === TestSendTelegramNotification ===


class TestSendTelegramNotification:
    """Telegram bildirim gonderimi testleri."""

    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.TelegramBot")
    def test_sends_message(
        self, mock_bot_cls: MagicMock, mock_run: MagicMock,
    ) -> None:
        """Telegram mesaji gonderilmeli."""
        mock_bot = MagicMock()
        mock_bot_cls.return_value = mock_bot

        result = _make_monitor_result(
            monitor_name="server",
            action="notify",
            summary="Test bildirimi",
        )
        _send_telegram_notification(result)

        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args[0][0]
        assert "SERVER MONITOR" in call_args
        mock_run.assert_called_once()

    @patch("app.tasks.monitor_tasks.TelegramBot")
    def test_handles_send_error(self, mock_bot_cls: MagicMock) -> None:
        """Gonderim hatasi loglanir, exception yutulur."""
        mock_bot_cls.side_effect = RuntimeError("Bot baslatilamadi")
        result = _make_monitor_result(action="notify")
        # Exception firlatmamali
        _send_telegram_notification(result)

    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.TelegramBot")
    def test_asyncio_run_used_for_send(
        self, mock_bot_cls: MagicMock, mock_run: MagicMock,
    ) -> None:
        """asyncio.run ile send_message cagrilmali."""
        mock_bot = MagicMock()
        mock_bot_cls.return_value = mock_bot

        result = _make_monitor_result(action="notify")
        _send_telegram_notification(result)

        mock_run.assert_called_once()
        # asyncio.run'a verilen arguman send_message'in donus degeri
        mock_bot.send_message.assert_called_once()


# === TestRunServerMonitor ===


class TestRunServerMonitor:
    """Server monitor taski testleri."""

    @patch("app.tasks.monitor_tasks._handle_result")
    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.ServerMonitor")
    def test_creates_monitor_and_calls_check(
        self,
        mock_monitor_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        mock_handle: MagicMock,
    ) -> None:
        """Monitor olusturulup check() cagrilmali."""
        mock_result = _make_monitor_result(monitor_name="server")
        mock_asyncio_run.return_value = mock_result

        # Celery task'i dogrudan fonksiyon olarak cagir
        result = run_server_monitor()

        mock_monitor_cls.assert_called_once()
        mock_asyncio_run.assert_called_once()
        mock_handle.assert_called_once_with(mock_result)
        assert result == mock_result.model_dump(mode="json")

    @patch("app.tasks.monitor_tasks._handle_result")
    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.ServerMonitor")
    def test_returns_dict(
        self,
        mock_monitor_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        mock_handle: MagicMock,
    ) -> None:
        """Dict olarak sonuc dondurmeli."""
        mock_result = _make_monitor_result(monitor_name="server", risk="high")
        mock_asyncio_run.return_value = mock_result

        result = run_server_monitor()

        assert isinstance(result, dict)
        assert result["risk"] == "high"
        assert result["monitor_name"] == "server"

    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.ServerMonitor")
    def test_retry_on_exception(
        self,
        mock_monitor_cls: MagicMock,
        mock_asyncio_run: MagicMock,
    ) -> None:
        """Hata durumunda retry denemeli."""
        mock_asyncio_run.side_effect = ConnectionError("Baglanti hatasi")

        with pytest.raises((ConnectionError, Exception)):
            run_server_monitor()

    def test_task_registered(self) -> None:
        """Task Celery'de kayitli olmali."""
        assert "app.tasks.monitor_tasks.run_server_monitor" in celery_app.tasks

    def test_task_max_retries(self) -> None:
        """Max retry 3 olmali."""
        task = celery_app.tasks["app.tasks.monitor_tasks.run_server_monitor"]
        assert task.max_retries == 3

    def test_task_default_retry_delay(self) -> None:
        """Default retry delay 60 saniye olmali."""
        task = celery_app.tasks["app.tasks.monitor_tasks.run_server_monitor"]
        assert task.default_retry_delay == 60

    def test_task_soft_time_limit(self) -> None:
        """Soft time limit 270 saniye olmali."""
        task = celery_app.tasks["app.tasks.monitor_tasks.run_server_monitor"]
        assert task.soft_time_limit == 270

    def test_task_time_limit(self) -> None:
        """Time limit 300 saniye olmali."""
        task = celery_app.tasks["app.tasks.monitor_tasks.run_server_monitor"]
        assert task.time_limit == 300


# === TestRunSecurityMonitor ===


class TestRunSecurityMonitor:
    """Security monitor taski testleri."""

    @patch("app.tasks.monitor_tasks._handle_result")
    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.SecurityMonitor")
    def test_creates_monitor_and_calls_check(
        self,
        mock_monitor_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        mock_handle: MagicMock,
    ) -> None:
        """Monitor olusturulup check() cagrilmali."""
        mock_result = _make_monitor_result(monitor_name="security")
        mock_asyncio_run.return_value = mock_result

        result = run_security_monitor()

        mock_monitor_cls.assert_called_once()
        mock_asyncio_run.assert_called_once()
        mock_handle.assert_called_once_with(mock_result)
        assert result == mock_result.model_dump(mode="json")

    @patch("app.tasks.monitor_tasks._handle_result")
    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.SecurityMonitor")
    def test_returns_dict_with_risk(
        self,
        mock_monitor_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        mock_handle: MagicMock,
    ) -> None:
        """Dict olarak sonuc dondurmeli."""
        mock_result = _make_monitor_result(
            monitor_name="security", risk="high", urgency="high",
        )
        mock_asyncio_run.return_value = mock_result

        result = run_security_monitor()

        assert result["risk"] == "high"
        assert result["urgency"] == "high"

    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.SecurityMonitor")
    def test_retry_on_exception(
        self,
        mock_monitor_cls: MagicMock,
        mock_asyncio_run: MagicMock,
    ) -> None:
        """Hata durumunda retry denemeli."""
        mock_asyncio_run.side_effect = RuntimeError("Tarama hatasi")

        with pytest.raises((RuntimeError, Exception)):
            run_security_monitor()

    def test_task_registered(self) -> None:
        """Task Celery'de kayitli olmali."""
        assert "app.tasks.monitor_tasks.run_security_monitor" in celery_app.tasks

    def test_task_max_retries(self) -> None:
        """Max retry 3 olmali."""
        task = celery_app.tasks["app.tasks.monitor_tasks.run_security_monitor"]
        assert task.max_retries == 3

    def test_task_default_retry_delay(self) -> None:
        """Default retry delay 120 saniye olmali."""
        task = celery_app.tasks["app.tasks.monitor_tasks.run_security_monitor"]
        assert task.default_retry_delay == 120

    def test_task_soft_time_limit(self) -> None:
        """Soft time limit 3300 saniye olmali."""
        task = celery_app.tasks["app.tasks.monitor_tasks.run_security_monitor"]
        assert task.soft_time_limit == 3300


# === TestRunAdsMonitor ===


class TestRunAdsMonitor:
    """Ads monitor taski testleri."""

    @patch("app.tasks.monitor_tasks._handle_result")
    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.AdsMonitor")
    def test_creates_monitor_and_calls_check(
        self,
        mock_monitor_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        mock_handle: MagicMock,
    ) -> None:
        """Monitor olusturulup check() cagrilmali."""
        mock_result = _make_monitor_result(monitor_name="ads")
        mock_asyncio_run.return_value = mock_result

        result = run_ads_monitor()

        mock_monitor_cls.assert_called_once()
        mock_asyncio_run.assert_called_once()
        mock_handle.assert_called_once_with(mock_result)
        assert result == mock_result.model_dump(mode="json")

    @patch("app.tasks.monitor_tasks._handle_result")
    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.AdsMonitor")
    def test_returns_dict_with_summary(
        self,
        mock_monitor_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        mock_handle: MagicMock,
    ) -> None:
        """Dict olarak sonuc dondurmeli."""
        mock_result = _make_monitor_result(
            monitor_name="ads", summary="Reklam performansi normal",
        )
        mock_asyncio_run.return_value = mock_result

        result = run_ads_monitor()

        assert result["summary"] == "Reklam performansi normal"

    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.AdsMonitor")
    def test_retry_on_exception(
        self,
        mock_monitor_cls: MagicMock,
        mock_asyncio_run: MagicMock,
    ) -> None:
        """Hata durumunda retry denemeli."""
        mock_asyncio_run.side_effect = ConnectionError("API hatasi")

        with pytest.raises((ConnectionError, Exception)):
            run_ads_monitor()

    def test_task_registered(self) -> None:
        """Task Celery'de kayitli olmali."""
        assert "app.tasks.monitor_tasks.run_ads_monitor" in celery_app.tasks

    def test_task_max_retries(self) -> None:
        """Max retry 3 olmali."""
        task = celery_app.tasks["app.tasks.monitor_tasks.run_ads_monitor"]
        assert task.max_retries == 3

    def test_task_default_retry_delay(self) -> None:
        """Default retry delay 120 saniye olmali."""
        task = celery_app.tasks["app.tasks.monitor_tasks.run_ads_monitor"]
        assert task.default_retry_delay == 120


# === TestRunOpportunityMonitor ===


class TestRunOpportunityMonitor:
    """Opportunity monitor taski testleri."""

    @patch("app.tasks.monitor_tasks._handle_result")
    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.OpportunityMonitor")
    def test_creates_monitor_and_calls_check(
        self,
        mock_monitor_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        mock_handle: MagicMock,
    ) -> None:
        """Monitor olusturulup check() cagrilmali."""
        mock_result = _make_monitor_result(monitor_name="opportunity")
        mock_asyncio_run.return_value = mock_result

        result = run_opportunity_monitor()

        mock_monitor_cls.assert_called_once()
        mock_asyncio_run.assert_called_once()
        mock_handle.assert_called_once_with(mock_result)
        assert result == mock_result.model_dump(mode="json")

    @patch("app.tasks.monitor_tasks._handle_result")
    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.OpportunityMonitor")
    def test_returns_dict_with_details(
        self,
        mock_monitor_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        mock_handle: MagicMock,
    ) -> None:
        """Dict olarak detaylarla sonuc dondurmeli."""
        mock_result = _make_monitor_result(
            monitor_name="opportunity",
            details=[{"type": "price_drop", "supplier": "test"}],
        )
        mock_asyncio_run.return_value = mock_result

        result = run_opportunity_monitor()

        assert len(result["details"]) == 1
        assert result["details"][0]["type"] == "price_drop"

    @patch("app.tasks.monitor_tasks.asyncio.run")
    @patch("app.tasks.monitor_tasks.OpportunityMonitor")
    def test_retry_on_exception(
        self,
        mock_monitor_cls: MagicMock,
        mock_asyncio_run: MagicMock,
    ) -> None:
        """Hata durumunda retry denemeli."""
        mock_asyncio_run.side_effect = TimeoutError("Zaman asimi")

        with pytest.raises((TimeoutError, Exception)):
            run_opportunity_monitor()

    def test_task_registered(self) -> None:
        """Task Celery'de kayitli olmali."""
        assert "app.tasks.monitor_tasks.run_opportunity_monitor" in celery_app.tasks

    def test_task_max_retries(self) -> None:
        """Max retry 3 olmali."""
        task = celery_app.tasks["app.tasks.monitor_tasks.run_opportunity_monitor"]
        assert task.max_retries == 3

    def test_task_default_retry_delay(self) -> None:
        """Default retry delay 300 saniye olmali."""
        task = celery_app.tasks["app.tasks.monitor_tasks.run_opportunity_monitor"]
        assert task.default_retry_delay == 300

    def test_task_soft_time_limit(self) -> None:
        """Soft time limit 82800 saniye olmali."""
        task = celery_app.tasks["app.tasks.monitor_tasks.run_opportunity_monitor"]
        assert task.soft_time_limit == 82800

    def test_task_time_limit(self) -> None:
        """Time limit 86400 saniye olmali."""
        task = celery_app.tasks["app.tasks.monitor_tasks.run_opportunity_monitor"]
        assert task.time_limit == 86400


# === TestMonitorResultSerialization ===


class TestMonitorResultSerialization:
    """MonitorResult JSON serializasyon testleri."""

    def test_model_dump_json_mode(self) -> None:
        """model_dump(mode='json') dogru formatta olmali."""
        result = _make_monitor_result(
            monitor_name="server",
            risk="high",
            urgency="medium",
            action="auto_fix",
            summary="Test",
            details=[{"cpu": "95%"}],
        )
        data = result.model_dump(mode="json")

        assert isinstance(data, dict)
        assert data["monitor_name"] == "server"
        assert data["risk"] == "high"
        assert data["urgency"] == "medium"
        assert data["action"] == "auto_fix"
        assert isinstance(data["check_time"], str)
        assert isinstance(data["details"], list)

    def test_model_dump_roundtrip(self) -> None:
        """model_dump ve yeniden olusturma dogru olmali."""
        original = _make_monitor_result(
            monitor_name="security",
            risk="medium",
            details=[{"type": "ssl_expiring", "days": "5"}],
        )
        data = original.model_dump()
        restored = MonitorResult(**data)

        assert restored.monitor_name == original.monitor_name
        assert restored.risk == original.risk
        assert restored.details == original.details


# === TestTasksPackageImport ===


class TestTasksPackageImport:
    """app.tasks paketi import testleri."""

    def test_import_run_server_monitor(self) -> None:
        """run_server_monitor import edilebilmeli."""
        from app.tasks import run_server_monitor as task
        assert callable(task)

    def test_import_run_security_monitor(self) -> None:
        """run_security_monitor import edilebilmeli."""
        from app.tasks import run_security_monitor as task
        assert callable(task)

    def test_import_run_ads_monitor(self) -> None:
        """run_ads_monitor import edilebilmeli."""
        from app.tasks import run_ads_monitor as task
        assert callable(task)

    def test_import_run_opportunity_monitor(self) -> None:
        """run_opportunity_monitor import edilebilmeli."""
        from app.tasks import run_opportunity_monitor as task
        assert callable(task)

    def test_celery_app_importable_from_main(self) -> None:
        """celery_app app.main'den import edilebilmeli."""
        from app.main import celery_app as ca
        assert ca is celery_app


# === TestCeleryAppFromMain ===


class TestCeleryAppFromMain:
    """app.main modulu uzerinden celery_app erisimi testleri."""

    def test_celery_app_is_same_instance(self) -> None:
        """main.celery_app ve celery_app ayni nesne olmali."""
        from app.main import celery_app as main_ca
        from app.celery_app import celery_app as direct_ca
        assert main_ca is direct_ca

    def test_celery_app_has_tasks(self) -> None:
        """celery_app'de kayitli tasklar olmali."""
        from app.main import celery_app as ca
        task_names = [
            "app.tasks.monitor_tasks.run_server_monitor",
            "app.tasks.monitor_tasks.run_security_monitor",
            "app.tasks.monitor_tasks.run_ads_monitor",
            "app.tasks.monitor_tasks.run_opportunity_monitor",
        ]
        for name in task_names:
            assert name in ca.tasks


# === TestHandleResultEdgeCases ===


class TestHandleResultEdgeCases:
    """Sonuc isleme kenar durum testleri."""

    @patch("app.tasks.monitor_tasks._send_telegram_notification")
    def test_empty_summary(self, mock_notify: MagicMock) -> None:
        """Bos ozet sorunsuz islenmeli."""
        result = _make_monitor_result(summary="", action="log")
        _handle_result(result)
        mock_notify.assert_not_called()

    @patch("app.tasks.monitor_tasks._send_telegram_notification")
    def test_unknown_action_no_notification(self, mock_notify: MagicMock) -> None:
        """Bilinmeyen aksiyon bildirim gondermemeli."""
        result = _make_monitor_result(action="unknown")
        _handle_result(result)
        mock_notify.assert_not_called()

    @patch("app.tasks.monitor_tasks._send_telegram_notification")
    def test_multiple_details(self, mock_notify: MagicMock) -> None:
        """Coklu detay sorunsuz islenmeli."""
        details = [{"key": f"val_{i}"} for i in range(20)]
        result = _make_monitor_result(action="notify", details=details)
        _handle_result(result)
        mock_notify.assert_called_once()


# === TestBeatScheduleIntervals ===


class TestBeatScheduleIntervals:
    """Beat zamanlama araliklari testleri."""

    def test_server_monitor_interval_default(self) -> None:
        """Server monitor varsayilan 300s (5 dk) olmali."""
        entry = celery_app.conf.beat_schedule["server-monitor"]
        assert entry["schedule"] == 300

    def test_security_monitor_interval_default(self) -> None:
        """Security monitor varsayilan 3600s (1 saat) olmali."""
        entry = celery_app.conf.beat_schedule["security-monitor"]
        assert entry["schedule"] == 3600

    def test_ads_monitor_interval_default(self) -> None:
        """Ads monitor varsayilan 3600s (1 saat) olmali."""
        entry = celery_app.conf.beat_schedule["ads-monitor"]
        assert entry["schedule"] == 3600

    def test_opportunity_monitor_interval_default(self) -> None:
        """Opportunity monitor varsayilan 86400s (24 saat) olmali."""
        entry = celery_app.conf.beat_schedule["opportunity-monitor"]
        assert entry["schedule"] == 86400


# === TestTaskNames ===


class TestTaskNames:
    """Celery task isimlendirme testleri."""

    def test_server_task_name(self) -> None:
        """Server task adi dogru olmali."""
        assert run_server_monitor.name == "app.tasks.monitor_tasks.run_server_monitor"

    def test_security_task_name(self) -> None:
        """Security task adi dogru olmali."""
        assert run_security_monitor.name == "app.tasks.monitor_tasks.run_security_monitor"

    def test_ads_task_name(self) -> None:
        """Ads task adi dogru olmali."""
        assert run_ads_monitor.name == "app.tasks.monitor_tasks.run_ads_monitor"

    def test_opportunity_task_name(self) -> None:
        """Opportunity task adi dogru olmali."""
        assert run_opportunity_monitor.name == "app.tasks.monitor_tasks.run_opportunity_monitor"
