"""ATLAS Bildirim Yoneticisi modulu.

Bildirim olusturma, onceliklendirme,
kategorize etme, toplu bildirim
ve yasam dongusu yonetimi.
"""

import logging
from typing import Any

from app.models.notification_system import (
    NotificationChannel,
    NotificationPriority,
    NotificationRecord,
    NotificationStatus,
)

logger = logging.getLogger(__name__)


class NotificationManager:
    """Bildirim yoneticisi.

    Bildirimleri olusturur, yonetir
    ve yasam dongusunu takip eder.

    Attributes:
        _notifications: Bildirimler.
        _categories: Kategori sayaclari.
    """

    def __init__(self) -> None:
        """Bildirim yoneticisini baslatir."""
        self._notifications: dict[
            str, NotificationRecord
        ] = {}
        self._categories: dict[str, int] = {}

        logger.info("NotificationManager baslatildi")

    def create(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        channel: NotificationChannel = NotificationChannel.LOG,
        category: str = "general",
        recipient: str = "",
    ) -> NotificationRecord:
        """Bildirim olusturur.

        Args:
            title: Baslik.
            message: Mesaj.
            priority: Oncelik.
            channel: Kanal.
            category: Kategori.
            recipient: Alici.

        Returns:
            Bildirim kaydi.
        """
        record = NotificationRecord(
            title=title,
            message=message,
            priority=priority,
            channel=channel,
            category=category,
            recipient=recipient,
        )
        self._notifications[record.notification_id] = record
        self._categories[category] = (
            self._categories.get(category, 0) + 1
        )
        logger.info("Bildirim olusturuldu: %s", title)
        return record

    def create_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[NotificationRecord]:
        """Toplu bildirim olusturur.

        Args:
            items: Bildirim verileri listesi.

        Returns:
            Bildirim kayitlari.
        """
        records: list[NotificationRecord] = []
        for item in items:
            rec = self.create(
                title=item.get("title", ""),
                message=item.get("message", ""),
                priority=item.get(
                    "priority", NotificationPriority.MEDIUM,
                ),
                channel=item.get(
                    "channel", NotificationChannel.LOG,
                ),
                category=item.get("category", "general"),
                recipient=item.get("recipient", ""),
            )
            records.append(rec)
        return records

    def mark_sent(
        self,
        notification_id: str,
    ) -> bool:
        """Bildirim gonderildi isaretler.

        Args:
            notification_id: Bildirim ID.

        Returns:
            Basarili ise True.
        """
        rec = self._notifications.get(notification_id)
        if not rec:
            return False
        rec.status = NotificationStatus.SENT
        return True

    def mark_read(
        self,
        notification_id: str,
    ) -> bool:
        """Bildirim okundu isaretler.

        Args:
            notification_id: Bildirim ID.

        Returns:
            Basarili ise True.
        """
        rec = self._notifications.get(notification_id)
        if not rec:
            return False
        rec.status = NotificationStatus.READ
        return True

    def mark_failed(
        self,
        notification_id: str,
    ) -> bool:
        """Bildirim basarisiz isaretler.

        Args:
            notification_id: Bildirim ID.

        Returns:
            Basarili ise True.
        """
        rec = self._notifications.get(notification_id)
        if not rec:
            return False
        rec.status = NotificationStatus.FAILED
        return True

    def get(
        self,
        notification_id: str,
    ) -> NotificationRecord | None:
        """Bildirim getirir.

        Args:
            notification_id: Bildirim ID.

        Returns:
            Bildirim veya None.
        """
        return self._notifications.get(notification_id)

    def get_by_priority(
        self,
        priority: NotificationPriority,
    ) -> list[NotificationRecord]:
        """Oncelige gore getirir.

        Args:
            priority: Oncelik.

        Returns:
            Bildirim listesi.
        """
        return [
            r for r in self._notifications.values()
            if r.priority == priority
        ]

    def get_by_category(
        self,
        category: str,
    ) -> list[NotificationRecord]:
        """Kategoriye gore getirir.

        Args:
            category: Kategori.

        Returns:
            Bildirim listesi.
        """
        return [
            r for r in self._notifications.values()
            if r.category == category
        ]

    def get_pending(self) -> list[NotificationRecord]:
        """Bekleyen bildirimleri getirir.

        Returns:
            Bekleyen bildirimler.
        """
        return [
            r for r in self._notifications.values()
            if r.status == NotificationStatus.PENDING
        ]

    def delete(self, notification_id: str) -> bool:
        """Bildirim siler.

        Args:
            notification_id: Bildirim ID.

        Returns:
            Basarili ise True.
        """
        if notification_id in self._notifications:
            del self._notifications[notification_id]
            return True
        return False

    @property
    def total_count(self) -> int:
        """Toplam bildirim sayisi."""
        return len(self._notifications)

    @property
    def pending_count(self) -> int:
        """Bekleyen bildirim sayisi."""
        return sum(
            1 for r in self._notifications.values()
            if r.status == NotificationStatus.PENDING
        )

    @property
    def category_count(self) -> int:
        """Kategori sayisi."""
        return len(self._categories)
