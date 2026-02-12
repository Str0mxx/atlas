"""ATLAS Celery uygulama modulu.

Celery worker ve beat icin uygulama nesnesi ve yapilandirma.
Periyodik gorevler (monitor tasklari) burada zamanlanir.
"""

import logging

from celery import Celery

from app.config import settings

logger = logging.getLogger(__name__)

# Celery uygulama nesnesi
celery_app = Celery("atlas")

celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_hijack_root_logger=False,
)

# Otomatik task kesfet
celery_app.autodiscover_tasks(["app.tasks"])

# Beat zamanlama — periyodik monitor gorevleri
celery_app.conf.beat_schedule = {
    "server-monitor": {
        "task": "app.tasks.monitor_tasks.run_server_monitor",
        "schedule": settings.server_monitor_interval,
    },
    "security-monitor": {
        "task": "app.tasks.monitor_tasks.run_security_monitor",
        "schedule": settings.security_monitor_interval,
    },
    "ads-monitor": {
        "task": "app.tasks.monitor_tasks.run_ads_monitor",
        "schedule": settings.ads_monitor_interval,
    },
    "opportunity-monitor": {
        "task": "app.tasks.monitor_tasks.run_opportunity_monitor",
        "schedule": settings.opportunity_monitor_interval,
    },
}

logger.info(
    "Celery uygulama yapilandirildi (broker=%s, %d periyodik gorev)",
    settings.celery_broker_url,
    len(celery_app.conf.beat_schedule),
)
