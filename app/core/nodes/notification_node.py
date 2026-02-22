"""Notification Node - bildirim dugum modulu.

Cihazlara push bildirim gonderme islevleri.
"""

import logging
import time
import uuid
from typing import Optional

from app.models.nodes_models import NodeNotification, NodesConfig

logger = logging.getLogger(__name__)


class NotificationNode:
    """Bildirim dugumu yonetim sinifi."""

    def __init__(self, config: Optional[NodesConfig] = None) -> None:
        """NotificationNode baslatici."""
        self.config = config or NodesConfig()
        self._notifications: dict[str, NodeNotification] = {}
        self._node_notifications: dict[str, list[str]] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina yeni bir giris ekler."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details or {}})

    def get_history(self) -> list[dict]:
        return list(self._history)

    def get_stats(self) -> dict:
        delivered = sum(1 for n in self._notifications.values() if n.delivered)
        return {"total_sent": len(self._notifications), "delivered": delivered}

    def send(self, node_id: str, title: str, body: str, priority: str = "normal") -> NodeNotification:
        """Tek bir cihaza bildirim gonderir."""
        nid = str(uuid.uuid4())
        notif = NodeNotification(notification_id=nid, node_id=node_id, title=title,
            body=body, priority=priority, sent_at=time.time(), delivered=True)
        self._notifications[nid] = notif
        self._node_notifications.setdefault(node_id, []).append(nid)
        self._record_history("send", {"node_id": node_id, "notification_id": nid})
        return notif

    def send_batch(self, node_ids: list[str], title: str, body: str) -> list[NodeNotification]:
        """Birden fazla cihaza bildirim gonderir."""
        results = []
        for nid in node_ids:
            results.append(self.send(nid, title, body))
        self._record_history("send_batch", {"count": len(node_ids)})
        return results

    def get_delivery_status(self, notification_id: str) -> Optional[bool]:
        """Bildirim teslimat durumunu kontrol eder."""
        notif = self._notifications.get(notification_id)
        return notif.delivered if notif else None

    def get_sent(self, node_id: str, limit: int = 10) -> list[NodeNotification]:
        """Dugume gonderilmis bildirimleri listeler."""
        ids = self._node_notifications.get(node_id, [])[-limit:]
        return [self._notifications[i] for i in ids if i in self._notifications]
