"""Bildirim aktarim modulu.

Bildirimleri giyilebilir cihazlara yonlendirir,
oncelik filtreleme ve toplu gonderim saglar.
"""

import logging
import time
from typing import Any, Optional

from app.models.wearable_models import (
    NotificationPriority,
    WatchInboxItem,
)

logger = logging.getLogger(__name__)

# Oncelik sirasi
PRIORITY_ORDER = {
    NotificationPriority.LOW: 0,
    NotificationPriority.NORMAL: 1,
    NotificationPriority.HIGH: 2,
    NotificationPriority.CRITICAL: 3,
}


class NotificationRelay:
    """Bildirim aktarim yoneticisi.

    Bildirimleri cihazlara yonlendirir, filtreler
    ve toplu gonderim yapar.
    """

    def __init__(self) -> None:
        """Aktarim yoneticisini baslatir."""
        self._relay_log: list[dict] = []
        self._rules: dict[str, dict] = {}  # device_id -> rules
        self._history: list[dict] = []

    def _record_history(self, action: str, **kwargs) -> None:
        """Gecmis kaydina olay ekler."""
        self._history.append({
            "action": action,
            "timestamp": time.time(),
            **kwargs,
        })

    def relay(
        self,
        notification: dict[str, Any],
        device_ids: list[str],
    ) -> dict[str, bool]:
        """Bildirimi cihazlara aktarir.

        Args:
            notification: Bildirim verisi
            device_ids: Hedef cihaz kimlikleri

        Returns:
            Cihaz kimligi -> basari durumu eslesmesi
        """
        results = {}
        for device_id in device_ids:
            # Kural kontrolu
            rules = self._rules.get(device_id, {})
            min_priority = rules.get("min_priority", NotificationPriority.LOW)
            notif_priority = notification.get("priority", NotificationPriority.NORMAL)

            if PRIORITY_ORDER.get(notif_priority, 1) < PRIORITY_ORDER.get(min_priority, 0):
                results[device_id] = False
                continue

            # Aktarim kaydı
            self._relay_log.append({
                "device_id": device_id,
                "notification": notification,
                "timestamp": time.time(),
                "status": "relayed",
            })
            results[device_id] = True

        self._record_history(
            "relay",
            device_count=len(device_ids),
            success_count=sum(results.values()),
        )
        return results

    def filter_by_priority(
        self,
        notifications: list[dict[str, Any]],
        min_priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> list[dict[str, Any]]:
        """Bildirimleri oncelik seviyesine gore filtreler.

        Args:
            notifications: Bildirim listesi
            min_priority: Minimum oncelik seviyesi

        Returns:
            Filtrelenmis bildirim listesi
        """
        min_order = PRIORITY_ORDER.get(min_priority, 1)
        filtered = []
        for notif in notifications:
            notif_priority = notif.get("priority", NotificationPriority.NORMAL)
            if PRIORITY_ORDER.get(notif_priority, 1) >= min_order:
                filtered.append(notif)
        self._record_history(
            "filter_by_priority",
            input_count=len(notifications),
            output_count=len(filtered),
        )
        return filtered

    def batch_relay(
        self, notifications: list[dict[str, Any]], device_ids: Optional[list[str]] = None
    ) -> dict[str, int]:
        """Toplu bildirim aktarimi yapar.

        Args:
            notifications: Bildirim listesi
            device_ids: Hedef cihaz kimlikleri

        Returns:
            Toplam gonderim istatistikleri
        """
        total_sent = 0
        total_failed = 0
        targets = device_ids or []

        for notif in notifications:
            result = self.relay(notif, targets)
            total_sent += sum(1 for v in result.values() if v)
            total_failed += sum(1 for v in result.values() if not v)

        self._record_history(
            "batch_relay",
            notification_count=len(notifications),
            total_sent=total_sent,
        )
        return {
            "total_sent": total_sent,
            "total_failed": total_failed,
            "notification_count": len(notifications),
        }

    def get_relay_history(self, device_id: Optional[str] = None) -> list[dict]:
        """Aktarim gecmisini dondurur.

        Args:
            device_id: Filtrelenecek cihaz kimligi (opsiyonel)

        Returns:
            Aktarim kayitlari
        """
        if device_id:
            return [r for r in self._relay_log if r.get("device_id") == device_id]
        return list(self._relay_log)

    def set_relay_rules(self, device_id: str, rules: dict) -> None:
        """Cihaz icin aktarim kurallarini belirler.

        Args:
            device_id: Cihaz kimligi
            rules: Kural sozlugu
        """
        self._rules[device_id] = rules
        self._record_history("set_relay_rules", device_id=device_id)

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        return {
            "total_relayed": len(self._relay_log),
            "devices_with_rules": len(self._rules),
            "history_count": len(self._history),
        }
