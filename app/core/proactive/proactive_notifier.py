"""ATLAS Proaktif Bildirimci modülü.

Akıllı bildirimler, kanal seçimi,
zamanlama optimizasyonu, gruplama,
öncelik override.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProactiveNotifier:
    """Proaktif bildirimci.

    Akıllı bildirim yönetimi yapar.

    Attributes:
        _notifications: Bildirim kayıtları.
        _channels: Kanal yapılandırmaları.
        _batch_buffer: Gruplama tamponu.
    """

    def __init__(
        self,
        default_channel: str = "log",
        batch_window: int = 60,
    ) -> None:
        """Bildirimciyi başlatır.

        Args:
            default_channel: Varsayılan kanal.
            batch_window: Gruplama penceresi (sn).
        """
        self._notifications: list[
            dict[str, Any]
        ] = []
        self._channels: dict[
            str, dict[str, Any]
        ] = {
            "log": {
                "enabled": True,
                "priority_min": 1,
            },
            "telegram": {
                "enabled": True,
                "priority_min": 3,
            },
            "email": {
                "enabled": True,
                "priority_min": 5,
            },
            "sms": {
                "enabled": True,
                "priority_min": 8,
            },
        }
        self._batch_buffer: list[
            dict[str, Any]
        ] = []
        self._default_channel = default_channel
        self._batch_window = batch_window
        self._counter = 0
        self._stats = {
            "notifications_sent": 0,
            "batches_sent": 0,
            "priority_overrides": 0,
        }

        logger.info(
            "ProactiveNotifier baslatildi",
        )

    def send_notification(
        self,
        title: str,
        message: str,
        priority: int = 5,
        channel: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Bildirim gönderir.

        Args:
            title: Bildirim başlığı.
            message: Mesaj.
            priority: Öncelik (1-10).
            channel: Kanal (None=otomatik).
            context: Bağlam.

        Returns:
            Bildirim bilgisi.
        """
        self._counter += 1
        nid = f"notif_{self._counter}"
        priority = max(1, min(10, priority))

        # Kanal seçimi
        selected_channel = (
            channel
            or self._select_channel(priority)
        )

        notification = {
            "notification_id": nid,
            "title": title,
            "message": message,
            "priority": priority,
            "channel": selected_channel,
            "context": context or {},
            "sent_at": time.time(),
            "status": "sent",
        }
        self._notifications.append(notification)
        self._stats["notifications_sent"] += 1

        return notification

    def _select_channel(
        self,
        priority: int,
    ) -> str:
        """Önceliğe göre kanal seçer.

        Args:
            priority: Öncelik seviyesi.

        Returns:
            Seçilen kanal.
        """
        best = self._default_channel
        for name, config in self._channels.items():
            if not config.get("enabled"):
                continue
            if priority >= config.get(
                "priority_min", 1,
            ):
                best = name

        return best

    def configure_channel(
        self,
        channel: str,
        enabled: bool = True,
        priority_min: int = 1,
    ) -> dict[str, Any]:
        """Kanal yapılandırır.

        Args:
            channel: Kanal adı.
            enabled: Etkin mi.
            priority_min: Min öncelik.

        Returns:
            Yapılandırma bilgisi.
        """
        self._channels[channel] = {
            "enabled": enabled,
            "priority_min": priority_min,
        }
        return {
            "channel": channel,
            "configured": True,
        }

    def optimize_timing(
        self,
        notification_id: str,
        preferred_hour: int | None = None,
        quiet_hours: tuple[int, int]
        | None = None,
    ) -> dict[str, Any]:
        """Zamanlama optimize eder.

        Args:
            notification_id: Bildirim ID.
            preferred_hour: Tercih edilen saat.
            quiet_hours: Sessiz saatler (start, end).

        Returns:
            Zamanlama bilgisi.
        """
        notif = None
        for n in self._notifications:
            if (
                n["notification_id"]
                == notification_id
            ):
                notif = n
                break

        if not notif:
            return {
                "error": "notification_not_found",
            }

        should_defer = False
        if quiet_hours:
            start, end = quiet_hours
            import datetime

            current_hour = (
                datetime.datetime.now(
                    datetime.timezone.utc,
                ).hour
            )
            if start <= current_hour < end:
                should_defer = True
                # Yüksek öncelik override
                if notif["priority"] >= 8:
                    should_defer = False
                    self._stats[
                        "priority_overrides"
                    ] += 1

        notif["deferred"] = should_defer

        return {
            "notification_id": notification_id,
            "deferred": should_defer,
            "priority": notif["priority"],
        }

    def batch_notifications(
        self,
        notifications: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Bildirimleri gruplar.

        Args:
            notifications: Bildirim listesi.

        Returns:
            Gruplama bilgisi.
        """
        if not notifications:
            return {
                "batched": False,
                "count": 0,
            }

        # Kanala göre grupla
        by_channel: dict[
            str, list[dict[str, Any]]
        ] = {}
        for n in notifications:
            ch = n.get(
                "channel", self._default_channel,
            )
            if ch not in by_channel:
                by_channel[ch] = []
            by_channel[ch].append(n)

        batches = []
        for channel, items in by_channel.items():
            batch = {
                "channel": channel,
                "count": len(items),
                "items": items,
                "max_priority": max(
                    i.get("priority", 1)
                    for i in items
                ),
                "batched_at": time.time(),
            }
            batches.append(batch)
            self._stats["batches_sent"] += 1

        return {
            "batched": True,
            "batch_count": len(batches),
            "total_notifications": len(
                notifications,
            ),
            "batches": batches,
        }

    def priority_override(
        self,
        notification_id: str,
        new_priority: int,
        reason: str = "",
    ) -> dict[str, Any]:
        """Öncelik override eder.

        Args:
            notification_id: Bildirim ID.
            new_priority: Yeni öncelik.
            reason: Neden.

        Returns:
            Override bilgisi.
        """
        notif = None
        for n in self._notifications:
            if (
                n["notification_id"]
                == notification_id
            ):
                notif = n
                break

        if not notif:
            return {
                "error": "notification_not_found",
            }

        old_priority = notif["priority"]
        notif["priority"] = max(
            1, min(10, new_priority),
        )
        notif["channel"] = self._select_channel(
            notif["priority"],
        )
        self._stats["priority_overrides"] += 1

        return {
            "notification_id": notification_id,
            "old_priority": old_priority,
            "new_priority": notif["priority"],
            "reason": reason,
        }

    def get_notifications(
        self,
        channel: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Bildirimleri getirir.

        Args:
            channel: Kanal filtresi.
            limit: Maks kayıt.

        Returns:
            Bildirim listesi.
        """
        results = self._notifications
        if channel:
            results = [
                n for n in results
                if n.get("channel") == channel
            ]
        return list(results[-limit:])

    @property
    def notification_count(self) -> int:
        """Bildirim sayısı."""
        return self._stats[
            "notifications_sent"
        ]

    @property
    def channel_count(self) -> int:
        """Kanal sayısı."""
        return len(self._channels)
