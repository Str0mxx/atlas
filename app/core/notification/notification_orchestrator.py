"""ATLAS Bildirim Orkestratoru modulu.

Tam bildirim pipeline, akilli
yonlendirme, analitik, siklik
sinirlama ve tum sistemlerle
entegrasyon.
"""

import logging
import time
from typing import Any

from app.models.notification_system import (
    NotificationChannel,
    NotificationPriority,
    NotificationSnapshot,
    NotificationStatus,
)

from app.core.notification.alert_engine import AlertEngine
from app.core.notification.channel_dispatcher import (
    ChannelDispatcher,
)
from app.core.notification.delivery_tracker import (
    DeliveryTracker,
)
from app.core.notification.digest_builder import DigestBuilder
from app.core.notification.escalation_manager import (
    EscalationManager,
)
from app.core.notification.notification_manager import (
    NotificationManager,
)
from app.core.notification.preference_manager import (
    NotificationPreferenceManager,
)
from app.core.notification.template_engine import (
    NotificationTemplateEngine,
)

logger = logging.getLogger(__name__)


class NotificationOrchestrator:
    """Bildirim orkestratoru.

    Tum bildirim alt sistemlerini
    koordine eder ve birlesik
    arayuz saglar.

    Attributes:
        manager: Bildirim yoneticisi.
        dispatcher: Kanal dagitici.
        alerts: Uyari motoru.
        preferences: Tercih yoneticisi.
        templates: Sablon motoru.
        delivery: Teslimat takipcisi.
        digests: Ozet olusturucu.
        escalation: Eskalasyon yoneticisi.
    """

    def __init__(
        self,
        default_channel: str = "log",
        quiet_start: str = "22:00",
        quiet_end: str = "08:00",
        max_daily: int = 100,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            default_channel: Varsayilan kanal.
            quiet_start: Sessiz baslangic.
            quiet_end: Sessiz bitis.
            max_daily: Gunluk maks bildirim.
        """
        self.manager = NotificationManager()
        self.dispatcher = ChannelDispatcher()
        self.alerts = AlertEngine()
        self.preferences = NotificationPreferenceManager(
            quiet_start=quiet_start,
            quiet_end=quiet_end,
        )
        self.templates = NotificationTemplateEngine()
        self.delivery = DeliveryTracker()
        self.digests = DigestBuilder()
        self.escalation = EscalationManager()

        self._default_channel = default_channel
        self._max_daily = max_daily
        self._daily_count = 0
        self._start_time = time.time()

        logger.info(
            "NotificationOrchestrator baslatildi",
        )

    def send_notification(
        self,
        title: str,
        message: str,
        recipient: str = "",
        channel: NotificationChannel | None = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        category: str = "general",
        template: str | None = None,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Bildirim gonderir (tam pipeline).

        Args:
            title: Baslik.
            message: Mesaj.
            recipient: Alici.
            channel: Kanal.
            priority: Oncelik.
            category: Kategori.
            template: Sablon adi.
            variables: Sablon degiskenleri.

        Returns:
            Gonderim sonucu.
        """
        # 1. Gunluk limit kontrolu
        if self._daily_count >= self._max_daily:
            return {
                "sent": False,
                "reason": "daily_limit_reached",
            }

        # 2. Tercih kontrolu
        if recipient:
            if not self.preferences.is_category_allowed(
                recipient, category,
            ):
                return {
                    "sent": False,
                    "reason": "category_blocked",
                }
            if not self.preferences.check_rate_limit(
                recipient,
            ):
                return {
                    "sent": False,
                    "reason": "rate_limited",
                }

        # 3. Sablon render
        final_title = title
        final_message = message
        if template:
            rendered = self.templates.render(
                template, variables,
            )
            final_title = rendered.get(
                "subject", title,
            )
            final_message = rendered.get(
                "body", message,
            )

        # 4. Kanal belirleme
        ch = channel
        if not ch:
            try:
                ch = NotificationChannel(
                    self._default_channel,
                )
            except ValueError:
                ch = NotificationChannel.LOG

        # Kritik oncelik her zaman gonder
        if priority == NotificationPriority.CRITICAL:
            ch = NotificationChannel.TELEGRAM

        # 5. Bildirim olustur
        record = self.manager.create(
            title=final_title,
            message=final_message,
            priority=priority,
            channel=ch,
            category=category,
            recipient=recipient,
        )

        # 6. Gonder
        result = self.dispatcher.dispatch(
            ch, recipient, final_title, final_message,
        )

        # 7. Teslimat takibi
        delivery = self.delivery.track(
            record.notification_id, ch,
        )

        if result["status"] == NotificationStatus.SENT.value:
            self.manager.mark_sent(
                record.notification_id,
            )
            self.delivery.mark_sent(
                delivery.delivery_id,
            )
            self._daily_count += 1
            if recipient:
                self.preferences.record_sent(recipient)
        else:
            self.manager.mark_failed(
                record.notification_id,
            )
            self.delivery.mark_failed(
                delivery.delivery_id,
                result.get("reason", ""),
            )

        # 8. Ozete ekle
        self.digests.add_item(
            category, final_title,
            final_message[:100], priority,
        )

        return {
            "sent": result["status"] == NotificationStatus.SENT.value,
            "notification_id": record.notification_id,
            "delivery_id": delivery.delivery_id,
            "channel": ch.value,
        }

    def check_alerts(
        self,
        metric: str,
        value: float,
    ) -> list[dict[str, Any]]:
        """Uyari kontrolu ve bildirim.

        Args:
            metric: Metrik adi.
            value: Deger.

        Returns:
            Tetiklenen uyarilar.
        """
        triggered = self.alerts.check_threshold(
            metric, value,
        )
        results: list[dict[str, Any]] = []

        for alert in triggered:
            result = self.send_notification(
                title=f"Alert: {metric}",
                message=alert.message,
                priority=alert.severity,
                category="alert",
            )
            results.append({
                "alert_id": alert.alert_id,
                **result,
            })

        return results

    def get_analytics(self) -> dict[str, Any]:
        """Analitik verileri getirir.

        Returns:
            Analitik.
        """
        delivery_analytics = self.delivery.get_analytics()

        return {
            "total_notifications": (
                self.manager.total_count
            ),
            "pending": self.manager.pending_count,
            "daily_sent": self._daily_count,
            "daily_limit": self._max_daily,
            "active_alerts": self.alerts.active_count,
            "active_escalations": (
                self.escalation.active_count
            ),
            "delivery": delivery_analytics,
            "channels": self.dispatcher.get_stats(),
        }

    def get_snapshot(self) -> NotificationSnapshot:
        """Goruntusu getirir.

        Returns:
            Goruntusu.
        """
        analytics = self.delivery.get_analytics()

        return NotificationSnapshot(
            total_notifications=(
                self.manager.total_count
            ),
            pending=self.manager.pending_count,
            sent=analytics["sent"],
            failed=analytics["failed"],
            active_alerts=self.alerts.active_count,
            suppressed=0,
            delivery_rate=analytics["delivery_rate"],
            escalations=self.escalation.active_count,
        )

    @property
    def daily_count(self) -> int:
        """Gunluk gonderim sayisi."""
        return self._daily_count
