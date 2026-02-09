"""ATLAS ornek veri yukleme scripti.

Gelistirme ve test ortaminda kullanilabilecek
ornek gorev, bildirim ve karar verilerini yukler.

Kullanim:
    python -m scripts.seed_data
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.core.database import async_session_factory, close_db, init_db
from app.models.notification import (
    NotificationChannel,
    NotificationEventType,
    NotificationPriority,
    NotificationRecord,
    NotificationStatus,
)
from app.models.task import TaskRecord, TaskStatus

logger = logging.getLogger("atlas.scripts.seed_data")


async def seed_tasks(session: object) -> int:
    """Ornek gorev kayitlari olusturur.

    Args:
        session: Async veritabani oturumu.

    Returns:
        Olusturulan kayit sayisi.
    """
    tasks = [
        TaskRecord(
            id=str(uuid.uuid4()),
            description="Sunucu saglik kontrolu calistir",
            status=TaskStatus.COMPLETED.value,
            agent="server_monitor",
            risk="low",
            urgency="low",
            result_message="Tum sunucular saglikli",
            result_success=True,
            confidence=0.95,
        ),
        TaskRecord(
            id=str(uuid.uuid4()),
            description="Google Ads kampanya analizi",
            status=TaskStatus.COMPLETED.value,
            agent="marketing",
            risk="medium",
            urgency="medium",
            result_message="2 kampanya dusuk performansli",
            result_success=True,
            confidence=0.80,
        ),
        TaskRecord(
            id=str(uuid.uuid4()),
            description="Guvenlik taramasi calistir",
            status=TaskStatus.RUNNING.value,
            agent="security",
        ),
        TaskRecord(
            id=str(uuid.uuid4()),
            description="Tedarikci fiyat arastirmasi",
            status=TaskStatus.PENDING.value,
        ),
        TaskRecord(
            id=str(uuid.uuid4()),
            description="SSL sertifika yenileme",
            status=TaskStatus.FAILED.value,
            agent="security",
            result_message="Certbot hatasi: rate limit",
            result_success=False,
        ),
    ]

    for task in tasks:
        session.add(task)
    return len(tasks)


async def seed_notifications(session: object) -> int:
    """Ornek bildirim kayitlari olusturur.

    Args:
        session: Async veritabani oturumu.

    Returns:
        Olusturulan kayit sayisi.
    """
    now = datetime.now(timezone.utc)
    notifications = [
        NotificationRecord(
            id=str(uuid.uuid4()),
            event_type=NotificationEventType.SERVER_ALERT.value,
            priority=NotificationPriority.HIGH.value,
            status=NotificationStatus.SENT.value,
            message="Sunucu CPU kullanimi %95 uzerinde",
            channel=NotificationChannel.TELEGRAM.value,
            sent_at=now,
        ),
        NotificationRecord(
            id=str(uuid.uuid4()),
            event_type=NotificationEventType.ADS_ALERT.value,
            priority=NotificationPriority.CRITICAL.value,
            status=NotificationStatus.ACKNOWLEDGED.value,
            message="3 reklam reddedildi",
            channel=NotificationChannel.TELEGRAM.value,
            sent_at=now,
            acknowledged_at=now,
        ),
        NotificationRecord(
            id=str(uuid.uuid4()),
            event_type=NotificationEventType.SECURITY_ALERT.value,
            priority=NotificationPriority.MEDIUM.value,
            status=NotificationStatus.PENDING.value,
            message="5 basarisiz giris denemesi tespit edildi",
            channel=NotificationChannel.TELEGRAM.value,
        ),
        NotificationRecord(
            id=str(uuid.uuid4()),
            event_type=NotificationEventType.TASK_COMPLETED.value,
            priority=NotificationPriority.LOW.value,
            status=NotificationStatus.SENT.value,
            message="Haftalik rapor olusturuldu",
            channel=NotificationChannel.EMAIL.value,
            sent_at=now,
        ),
        NotificationRecord(
            id=str(uuid.uuid4()),
            event_type=NotificationEventType.SYSTEM_ERROR.value,
            priority=NotificationPriority.HIGH.value,
            status=NotificationStatus.FAILED.value,
            message="Redis baglantisi koptu",
            details="ConnectionRefusedError: localhost:6379",
            channel=NotificationChannel.TELEGRAM.value,
        ),
    ]

    for notification in notifications:
        session.add(notification)
    return len(notifications)


async def seed_all() -> None:
    """Tum ornek verileri yukler."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    await init_db()

    if async_session_factory is None:
        logger.error("Session factory baslatilmamis")
        return

    try:
        async with async_session_factory() as session:
            task_count = await seed_tasks(session)
            notif_count = await seed_notifications(session)
            await session.commit()
            logger.info(
                "Seed tamamlandi: %d gorev, %d bildirim",
                task_count, notif_count,
            )
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(seed_all())
