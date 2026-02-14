"""ATLAS Teslimat Takipcisi modulu.

Teslimat durumu, okundu bilgisi,
yeniden deneme yonetimi, hata islemleri
ve analitik.
"""

import logging
import time
from typing import Any

from app.models.notification_system import (
    DeliveryRecord,
    NotificationChannel,
    NotificationStatus,
)

logger = logging.getLogger(__name__)


class DeliveryTracker:
    """Teslimat takipcisi.

    Bildirim teslimatlarini takip eder
    ve yeniden deneme yonetir.

    Attributes:
        _deliveries: Teslimat kayitlari.
        _max_retries: Maks yeniden deneme.
    """

    def __init__(
        self,
        max_retries: int = 3,
    ) -> None:
        """Teslimat takipcisini baslatir.

        Args:
            max_retries: Maks yeniden deneme.
        """
        self._deliveries: dict[
            str, DeliveryRecord
        ] = {}
        self._max_retries = max_retries
        self._read_receipts: dict[str, float] = {}

        logger.info("DeliveryTracker baslatildi")

    def track(
        self,
        notification_id: str,
        channel: NotificationChannel,
    ) -> DeliveryRecord:
        """Teslimat baslatir.

        Args:
            notification_id: Bildirim ID.
            channel: Kanal.

        Returns:
            Teslimat kaydi.
        """
        record = DeliveryRecord(
            notification_id=notification_id,
            channel=channel,
            status=NotificationStatus.PENDING,
        )
        self._deliveries[record.delivery_id] = record
        return record

    def mark_sent(
        self,
        delivery_id: str,
    ) -> bool:
        """Gonderildi isaretler.

        Args:
            delivery_id: Teslimat ID.

        Returns:
            Basarili ise True.
        """
        rec = self._deliveries.get(delivery_id)
        if not rec:
            return False
        rec.status = NotificationStatus.SENT
        rec.attempts += 1
        return True

    def mark_delivered(
        self,
        delivery_id: str,
    ) -> bool:
        """Teslim edildi isaretler.

        Args:
            delivery_id: Teslimat ID.

        Returns:
            Basarili ise True.
        """
        rec = self._deliveries.get(delivery_id)
        if not rec:
            return False
        rec.status = NotificationStatus.DELIVERED
        return True

    def mark_read(
        self,
        delivery_id: str,
    ) -> bool:
        """Okundu isaretler.

        Args:
            delivery_id: Teslimat ID.

        Returns:
            Basarili ise True.
        """
        rec = self._deliveries.get(delivery_id)
        if not rec:
            return False
        rec.status = NotificationStatus.READ
        self._read_receipts[delivery_id] = time.time()
        return True

    def mark_failed(
        self,
        delivery_id: str,
        error: str = "",
    ) -> bool:
        """Basarisiz isaretler.

        Args:
            delivery_id: Teslimat ID.
            error: Hata mesaji.

        Returns:
            Basarili ise True.
        """
        rec = self._deliveries.get(delivery_id)
        if not rec:
            return False
        rec.status = NotificationStatus.FAILED
        rec.last_error = error
        rec.attempts += 1
        return True

    def should_retry(
        self,
        delivery_id: str,
    ) -> bool:
        """Yeniden deneme kontrol eder.

        Args:
            delivery_id: Teslimat ID.

        Returns:
            Yeniden denemeli ise True.
        """
        rec = self._deliveries.get(delivery_id)
        if not rec:
            return False
        return (
            rec.status == NotificationStatus.FAILED
            and rec.attempts < self._max_retries
        )

    def get_failed(self) -> list[DeliveryRecord]:
        """Basarisiz teslimatlari getirir.

        Returns:
            Basarisiz teslimatlar.
        """
        return [
            r for r in self._deliveries.values()
            if r.status == NotificationStatus.FAILED
        ]

    def get_retryable(self) -> list[DeliveryRecord]:
        """Yeniden denenebilir teslimatlari getirir.

        Returns:
            Yeniden denenebilir teslimatlar.
        """
        return [
            r for r in self._deliveries.values()
            if (
                r.status == NotificationStatus.FAILED
                and r.attempts < self._max_retries
            )
        ]

    def get_analytics(self) -> dict[str, Any]:
        """Analitik verileri getirir.

        Returns:
            Analitik.
        """
        total = len(self._deliveries)
        sent = sum(
            1 for r in self._deliveries.values()
            if r.status in (
                NotificationStatus.SENT,
                NotificationStatus.DELIVERED,
                NotificationStatus.READ,
            )
        )
        failed = sum(
            1 for r in self._deliveries.values()
            if r.status == NotificationStatus.FAILED
        )
        read = len(self._read_receipts)

        return {
            "total": total,
            "sent": sent,
            "failed": failed,
            "read": read,
            "delivery_rate": round(
                sent / max(1, total), 3,
            ),
            "read_rate": round(
                read / max(1, sent), 3,
            ),
        }

    @property
    def delivery_count(self) -> int:
        """Teslimat sayisi."""
        return len(self._deliveries)

    @property
    def read_count(self) -> int:
        """Okunma sayisi."""
        return len(self._read_receipts)
