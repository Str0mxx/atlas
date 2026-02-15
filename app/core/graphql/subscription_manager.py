"""ATLAS Abonelik Yoneticisi modulu.

WebSocket yonetimi, olay yayinlama,
abonelik filtreleme, baglanti
yonetimi ve heartbeat.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """Abonelik yoneticisi.

    GraphQL aboneliklerini yonetir.

    Attributes:
        _subscriptions: Aktif abonelikler.
        _connections: Baglantilar.
    """

    def __init__(
        self,
        heartbeat_interval: int = 30,
    ) -> None:
        """Yoneticiyi baslatir.

        Args:
            heartbeat_interval: Heartbeat araligi.
        """
        self._heartbeat_interval = heartbeat_interval
        self._subscriptions: dict[
            str, dict[str, Any]
        ] = {}
        self._connections: dict[
            str, dict[str, Any]
        ] = {}
        self._event_log: list[
            dict[str, Any]
        ] = []
        self._filters: dict[
            str, Callable[[dict[str, Any]], bool]
        ] = {}

        logger.info(
            "SubscriptionManager baslatildi",
        )

    def connect(
        self,
        connection_id: str,
        metadata: dict[str, Any]
            | None = None,
    ) -> dict[str, Any]:
        """Baglanti kurar.

        Args:
            connection_id: Baglanti ID.
            metadata: Ek bilgi.

        Returns:
            Baglanti bilgisi.
        """
        self._connections[connection_id] = {
            "id": connection_id,
            "status": "connected",
            "metadata": metadata or {},
            "subscriptions": [],
            "connected_at": time.time(),
            "last_heartbeat": time.time(),
        }

        return {
            "connection_id": connection_id,
            "status": "connected",
        }

    def disconnect(
        self,
        connection_id: str,
    ) -> dict[str, Any]:
        """Baglanti keser.

        Args:
            connection_id: Baglanti ID.

        Returns:
            Kesme bilgisi.
        """
        conn = self._connections.pop(
            connection_id, None,
        )
        if not conn:
            return {"error": "not_connected"}

        # Abonelikleri temizle
        for sub_id in conn.get(
            "subscriptions", [],
        ):
            self._subscriptions.pop(sub_id, None)

        return {
            "connection_id": connection_id,
            "status": "disconnected",
        }

    def subscribe(
        self,
        connection_id: str,
        subscription_id: str,
        event_type: str,
        filter_fn: Callable[
            [dict[str, Any]], bool
        ] | None = None,
    ) -> dict[str, Any]:
        """Abonelik olusturur.

        Args:
            connection_id: Baglanti ID.
            subscription_id: Abonelik ID.
            event_type: Olay tipi.
            filter_fn: Filtre fonksiyonu.

        Returns:
            Abonelik bilgisi.
        """
        conn = self._connections.get(
            connection_id,
        )
        if not conn:
            return {"error": "not_connected"}

        self._subscriptions[subscription_id] = {
            "id": subscription_id,
            "connection_id": connection_id,
            "event_type": event_type,
            "status": "active",
            "events_received": 0,
            "created_at": time.time(),
        }

        conn["subscriptions"].append(
            subscription_id,
        )

        if filter_fn:
            self._filters[subscription_id] = (
                filter_fn
            )

        return {
            "subscription_id": subscription_id,
            "event_type": event_type,
            "status": "active",
        }

    def unsubscribe(
        self,
        subscription_id: str,
    ) -> bool:
        """Aboneligi iptal eder.

        Args:
            subscription_id: Abonelik ID.

        Returns:
            Basarili mi.
        """
        sub = self._subscriptions.pop(
            subscription_id, None,
        )
        if not sub:
            return False

        conn = self._connections.get(
            sub["connection_id"],
        )
        if conn:
            subs = conn["subscriptions"]
            if subscription_id in subs:
                subs.remove(subscription_id)

        self._filters.pop(
            subscription_id, None,
        )
        return True

    def publish(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Olay yayinlar.

        Args:
            event_type: Olay tipi.
            data: Olay verisi.

        Returns:
            Yayinlama bilgisi.
        """
        delivered = 0

        for sub_id, sub in (
            self._subscriptions.items()
        ):
            if (
                sub["event_type"] == event_type
                and sub["status"] == "active"
            ):
                # Filtre kontrolu
                flt = self._filters.get(sub_id)
                if flt and not flt(data):
                    continue

                sub["events_received"] += 1
                delivered += 1

        self._event_log.append({
            "event_type": event_type,
            "data": data,
            "delivered": delivered,
            "timestamp": time.time(),
        })

        return {
            "event_type": event_type,
            "delivered": delivered,
        }

    def heartbeat(
        self,
        connection_id: str,
    ) -> dict[str, Any]:
        """Heartbeat gonderir.

        Args:
            connection_id: Baglanti ID.

        Returns:
            Heartbeat bilgisi.
        """
        conn = self._connections.get(
            connection_id,
        )
        if not conn:
            return {"error": "not_connected"}

        conn["last_heartbeat"] = time.time()
        return {
            "connection_id": connection_id,
            "status": "alive",
        }

    def check_stale_connections(
        self,
        timeout: int | None = None,
    ) -> list[str]:
        """Bayat baglantilari bulur.

        Args:
            timeout: Zaman asimi.

        Returns:
            Bayat baglanti ID'leri.
        """
        to = timeout or (
            self._heartbeat_interval * 3
        )
        now = time.time()
        stale: list[str] = []

        for cid, conn in self._connections.items():
            elapsed = now - conn["last_heartbeat"]
            if elapsed > to:
                stale.append(cid)

        return stale

    def get_subscription(
        self,
        subscription_id: str,
    ) -> dict[str, Any] | None:
        """Abonelik bilgisini getirir.

        Args:
            subscription_id: Abonelik ID.

        Returns:
            Bilgi veya None.
        """
        return self._subscriptions.get(
            subscription_id,
        )

    def get_connection(
        self,
        connection_id: str,
    ) -> dict[str, Any] | None:
        """Baglanti bilgisini getirir.

        Args:
            connection_id: Baglanti ID.

        Returns:
            Bilgi veya None.
        """
        return self._connections.get(
            connection_id,
        )

    def get_events(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Olay logunu getirir.

        Args:
            limit: Limit.

        Returns:
            Olay listesi.
        """
        return self._event_log[-limit:]

    @property
    def subscription_count(self) -> int:
        """Abonelik sayisi."""
        return len(self._subscriptions)

    @property
    def connection_count(self) -> int:
        """Baglanti sayisi."""
        return len(self._connections)

    @property
    def active_count(self) -> int:
        """Aktif abonelik sayisi."""
        return sum(
            1 for s in self._subscriptions.values()
            if s["status"] == "active"
        )

    @property
    def event_count(self) -> int:
        """Olay sayisi."""
        return len(self._event_log)
