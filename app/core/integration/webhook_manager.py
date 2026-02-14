"""ATLAS Webhook Yoneticisi modulu.

Gelen ve giden webhook'lar, imza dogrulama,
yeniden deneme ve olay yonlendirme.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any

from app.models.integration import WebhookDirection, WebhookRecord

logger = logging.getLogger(__name__)


class WebhookManager:
    """Webhook yoneticisi.

    Gelen ve giden webhook olaylarini
    yonetir ve yonlendirir.

    Attributes:
        _webhooks: Kayitli webhook'lar.
        _events: Islenen olaylar.
        _routes: Olay yonlendirme kurallari.
        _secrets: Imza dogrulama gizli anahtarlari.
        _max_retries: Maks yeniden deneme.
    """

    def __init__(self, max_retries: int = 3) -> None:
        """Webhook yoneticisini baslatir.

        Args:
            max_retries: Maks yeniden deneme.
        """
        self._webhooks: list[WebhookRecord] = []
        self._events: list[dict[str, Any]] = []
        self._routes: dict[str, list[str]] = {}
        self._secrets: dict[str, str] = {}
        self._max_retries = max(1, max_retries)

        logger.info(
            "WebhookManager baslatildi (max_retries=%d)",
            self._max_retries,
        )

    def register_webhook(
        self,
        url: str,
        event_type: str,
        direction: WebhookDirection = WebhookDirection.INCOMING,
        secret: str = "",
    ) -> WebhookRecord:
        """Webhook kaydeder.

        Args:
            url: Webhook URL.
            event_type: Olay turu.
            direction: Yon.
            secret: Gizli anahtar.

        Returns:
            Webhook kaydi.
        """
        record = WebhookRecord(
            direction=direction,
            url=url,
            event_type=event_type,
            verified=bool(secret),
        )
        self._webhooks.append(record)

        if secret:
            self._secrets[record.webhook_id] = secret

        # Yonlendirme ekle
        if event_type not in self._routes:
            self._routes[event_type] = []
        self._routes[event_type].append(record.webhook_id)

        logger.info(
            "Webhook kaydedildi: %s (%s, %s)",
            event_type, direction.value, url,
        )
        return record

    def process_incoming(
        self,
        event_type: str,
        payload: dict[str, Any],
        signature: str = "",
        webhook_id: str = "",
    ) -> dict[str, Any]:
        """Gelen webhook isler.

        Args:
            event_type: Olay turu.
            payload: Veri yukü.
            signature: Imza.
            webhook_id: Webhook ID.

        Returns:
            Isleme sonucu.
        """
        # Imza dogrulama
        if webhook_id and webhook_id in self._secrets:
            if not self.verify_signature(
                payload, signature, webhook_id,
            ):
                return {
                    "success": False,
                    "error": "Imza dogrulanamadi",
                }

        event = {
            "event_type": event_type,
            "direction": "incoming",
            "payload": payload,
            "webhook_id": webhook_id,
            "processed": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._events.append(event)

        # Yonlendirme
        routed_to = self._routes.get(event_type, [])

        logger.info(
            "Gelen webhook islendi: %s (%d hedefe yonlendirildi)",
            event_type, len(routed_to),
        )
        return {
            "success": True,
            "event_type": event_type,
            "routed_to": routed_to,
        }

    def send_outgoing(
        self,
        event_type: str,
        payload: dict[str, Any],
        target_url: str = "",
    ) -> dict[str, Any]:
        """Giden webhook gonderir.

        Args:
            event_type: Olay turu.
            payload: Veri yuku.
            target_url: Hedef URL.

        Returns:
            Gonderim sonucu.
        """
        # Hedef bul
        targets: list[str] = []
        if target_url:
            targets.append(target_url)
        else:
            for wh in self._webhooks:
                if (wh.event_type == event_type
                        and wh.direction == WebhookDirection.OUTGOING):
                    targets.append(wh.url)

        event = {
            "event_type": event_type,
            "direction": "outgoing",
            "payload": payload,
            "targets": targets,
            "sent": len(targets) > 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._events.append(event)

        return {
            "success": len(targets) > 0,
            "targets_count": len(targets),
            "targets": targets,
        }

    def verify_signature(
        self,
        payload: dict[str, Any],
        signature: str,
        webhook_id: str,
    ) -> bool:
        """Imza dogrular.

        Args:
            payload: Veri yuku.
            signature: Imza.
            webhook_id: Webhook ID.

        Returns:
            Gecerli ise True.
        """
        secret = self._secrets.get(webhook_id)
        if not secret:
            return False

        payload_str = str(sorted(payload.items()))
        expected = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def generate_signature(
        self,
        payload: dict[str, Any],
        secret: str,
    ) -> str:
        """Imza uretir.

        Args:
            payload: Veri yuku.
            secret: Gizli anahtar.

        Returns:
            HMAC-SHA256 imza.
        """
        payload_str = str(sorted(payload.items()))
        return hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256,
        ).hexdigest()

    def retry_failed(
        self,
        event_type: str,
    ) -> dict[str, Any]:
        """Basarisiz webhook'lari yeniden dener.

        Args:
            event_type: Olay turu.

        Returns:
            Yeniden deneme sonucu.
        """
        failed = [
            e for e in self._events
            if (e.get("event_type") == event_type
                and not e.get("sent", True))
        ]

        retried = 0
        for event in failed:
            retry = event.get("retry_count", 0)
            if retry < self._max_retries:
                event["retry_count"] = retry + 1
                event["sent"] = True
                retried += 1

        return {
            "failed_count": len(failed),
            "retried": retried,
            "max_retries": self._max_retries,
        }

    def add_route(
        self,
        event_type: str,
        webhook_id: str,
    ) -> None:
        """Olay yonlendirmesi ekler.

        Args:
            event_type: Olay turu.
            webhook_id: Webhook ID.
        """
        if event_type not in self._routes:
            self._routes[event_type] = []
        if webhook_id not in self._routes[event_type]:
            self._routes[event_type].append(webhook_id)

    def get_routes(
        self,
        event_type: str = "",
    ) -> dict[str, list[str]]:
        """Yonlendirmeleri getirir.

        Args:
            event_type: Olay filtresi.

        Returns:
            Yonlendirme haritasi.
        """
        if event_type:
            return {
                event_type: self._routes.get(event_type, []),
            }
        return dict(self._routes)

    def get_events(
        self,
        event_type: str = "",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Olaylari getirir.

        Args:
            event_type: Olay filtresi.
            limit: Maks kayit.

        Returns:
            Olay listesi.
        """
        events = self._events
        if event_type:
            events = [
                e for e in events
                if e.get("event_type") == event_type
            ]
        return events[-limit:]

    @property
    def webhook_count(self) -> int:
        """Webhook sayisi."""
        return len(self._webhooks)

    @property
    def event_count(self) -> int:
        """Olay sayisi."""
        return len(self._events)

    @property
    def route_count(self) -> int:
        """Yonlendirme sayisi."""
        return sum(len(v) for v in self._routes.values())
