"""ATLAS monitor Celery gorevleri.

Her monitor icin periyodik Celery task tanimlar.
Async monitor.check() metodunu asyncio.run() ile calistirir,
sonucu loglar ve gerektiginde Telegram bildirimi gonderir.
"""

import asyncio
import logging
from typing import Any

from celery import Task

from app.celery_app import celery_app
from app.config import settings
from app.monitors.ads_monitor import AdsMonitor
from app.monitors.base_monitor import MonitorResult
from app.monitors.opportunity_monitor import OpportunityMonitor
from app.monitors.security_monitor import SecurityMonitor
from app.monitors.server_monitor import ServerMonitor
from app.tools.telegram_bot import TelegramBot

logger = logging.getLogger(__name__)


def _handle_result(result: MonitorResult) -> None:
    """Monitor sonucunu isler: loglar ve gerekirse bildirim gonderir.

    Args:
        result: Monitor kontrol sonucu.
    """
    logger.info(
        "[%s] Kontrol tamamlandi: risk=%s, urgency=%s, action=%s — %s",
        result.monitor_name,
        result.risk,
        result.urgency,
        result.action,
        result.summary,
    )

    # Bildirim gerekli mi kontrol et
    if result.action in ("notify", "auto_fix", "immediate"):
        _send_telegram_notification(result)


def _send_telegram_notification(result: MonitorResult) -> None:
    """Telegram bildirimi gonderir.

    Args:
        result: Monitor kontrol sonucu.
    """
    try:
        bot = TelegramBot()
        message = _format_notification(result)
        asyncio.run(bot.send_message(message))
        logger.info("[%s] Telegram bildirimi gonderildi", result.monitor_name)
    except Exception as exc:
        logger.error(
            "[%s] Telegram bildirimi gonderilemedi: %s",
            result.monitor_name, exc,
        )


def _format_notification(result: MonitorResult) -> str:
    """Monitor sonucunu bildirim mesajina formatlar.

    Args:
        result: Monitor kontrol sonucu.

    Returns:
        Formatlanmis bildirim metni.
    """
    lines = [
        f"=== {result.monitor_name.upper()} MONITOR ===",
        f"Risk: {result.risk} | Aciliyet: {result.urgency}",
        f"Aksiyon: {result.action}",
        "",
        result.summary,
    ]
    if result.details:
        lines.append("")
        for detail in result.details[:5]:
            for k, v in detail.items():
                lines.append(f"  {k}: {v}")
    return "\n".join(lines)


# === Celery Tasklari ===


@celery_app.task(
    name="app.tasks.monitor_tasks.run_server_monitor",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=270,
    time_limit=300,
)
def run_server_monitor(self: Task) -> dict[str, Any]:
    """Sunucu saglik kontrolu Celery taski.

    ServerMonitor.check() metodunu calistirir,
    sonucu isler ve JSON-serializable dict olarak dondurur.

    Args:
        self: Celery task nesnesi (bind=True).

    Returns:
        Monitor kontrol sonucu (dict).
    """
    try:
        logger.info("Sunucu monitor taski baslatiliyor...")
        monitor = ServerMonitor(
            check_interval=settings.server_monitor_interval,
        )
        result = asyncio.run(monitor.check())
        _handle_result(result)
        return result.model_dump(mode="json")
    except Exception as exc:
        logger.error("Sunucu monitor taski hatasi: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.monitor_tasks.run_security_monitor",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    soft_time_limit=3300,
    time_limit=3600,
)
def run_security_monitor(self: Task) -> dict[str, Any]:
    """Guvenlik taramasi Celery taski.

    SecurityMonitor.check() metodunu calistirir,
    sonucu isler ve JSON-serializable dict olarak dondurur.

    Args:
        self: Celery task nesnesi (bind=True).

    Returns:
        Monitor kontrol sonucu (dict).
    """
    try:
        logger.info("Guvenlik monitor taski baslatiliyor...")
        monitor = SecurityMonitor(
            check_interval=settings.security_monitor_interval,
        )
        result = asyncio.run(monitor.check())
        _handle_result(result)
        return result.model_dump(mode="json")
    except Exception as exc:
        logger.error("Guvenlik monitor taski hatasi: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.monitor_tasks.run_ads_monitor",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    soft_time_limit=3300,
    time_limit=3600,
)
def run_ads_monitor(self: Task) -> dict[str, Any]:
    """Reklam performans kontrolu Celery taski.

    AdsMonitor.check() metodunu calistirir,
    sonucu isler ve JSON-serializable dict olarak dondurur.

    Args:
        self: Celery task nesnesi (bind=True).

    Returns:
        Monitor kontrol sonucu (dict).
    """
    try:
        logger.info("Reklam monitor taski baslatiliyor...")
        monitor = AdsMonitor(
            check_interval=settings.ads_monitor_interval,
        )
        result = asyncio.run(monitor.check())
        _handle_result(result)
        return result.model_dump(mode="json")
    except Exception as exc:
        logger.error("Reklam monitor taski hatasi: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.monitor_tasks.run_opportunity_monitor",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    soft_time_limit=82800,
    time_limit=86400,
)
def run_opportunity_monitor(self: Task) -> dict[str, Any]:
    """Firsat izleme Celery taski.

    OpportunityMonitor.check() metodunu calistirir,
    sonucu isler ve JSON-serializable dict olarak dondurur.

    Args:
        self: Celery task nesnesi (bind=True).

    Returns:
        Monitor kontrol sonucu (dict).
    """
    try:
        logger.info("Firsat monitor taski baslatiliyor...")
        monitor = OpportunityMonitor(
            check_interval=settings.opportunity_monitor_interval,
        )
        result = asyncio.run(monitor.check())
        _handle_result(result)
        return result.model_dump(mode="json")
    except Exception as exc:
        logger.error("Firsat monitor taski hatasi: %s", exc)
        raise self.retry(exc=exc)
