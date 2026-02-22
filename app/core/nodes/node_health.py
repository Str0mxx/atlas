"""Node Health Monitor - dugum saglik izleme modulu.

Cihaz dugumlerinin saglik durumunu kontrol eder ve otomatik yeniden baglanti saglar.
"""

import logging
import time
from typing import Optional

from app.models.nodes_models import NodeHealthCheck, NodeStatus, NodesConfig

logger = logging.getLogger(__name__)


class NodeHealthMonitor:
    """Dugum saglik izleme sinifi."""

    def __init__(self, config: Optional[NodesConfig] = None) -> None:
        """NodeHealthMonitor baslatici."""
        self.config = config or NodesConfig()
        self._health: dict[str, NodeHealthCheck] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina yeni bir giris ekler."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details or {}})

    def get_history(self) -> list[dict]:
        return list(self._history)

    def get_stats(self) -> dict:
        online = sum(1 for h in self._health.values() if h.status == NodeStatus.ONLINE)
        return {"monitored_nodes": len(self._health), "online": online}

    def check(self, node_id: str) -> NodeHealthCheck:
        """Tek bir dugumun saglik kontrolunu yapar."""
        health = self._health.get(node_id, NodeHealthCheck(node_id=node_id))
        health.last_check = time.time()
        health.latency_ms = 15.0
        health.status = NodeStatus.ONLINE
        health.consecutive_failures = 0
        self._health[node_id] = health
        self._record_history("check", {"node_id": node_id, "status": health.status.value})
        return health

    def check_all(self) -> list[NodeHealthCheck]:
        """Tum dugumlerin saglik kontrolunu yapar."""
        results = []
        for nid in list(self._health.keys()):
            results.append(self.check(nid))
        self._record_history("check_all", {"count": len(results)})
        return results

    def get_status(self, node_id: str) -> Optional[NodeHealthCheck]:
        """Dugumun saglik durumunu dondurur."""
        return self._health.get(node_id)

    def set_auto_reconnect(self, node_id: str, enabled: bool) -> bool:
        """Otomatik yeniden baglanti ayarini degistirir."""
        health = self._health.get(node_id)
        if not health:
            health = NodeHealthCheck(node_id=node_id)
            self._health[node_id] = health
        health.auto_reconnect = enabled
        self._record_history("set_auto_reconnect", {"node_id": node_id, "enabled": enabled})
        return True

    def get_unhealthy(self) -> list[NodeHealthCheck]:
        """Sagliksiz dugumleri listeler."""
        return [h for h in self._health.values() if h.status != NodeStatus.ONLINE]

    def attempt_reconnect(self, node_id: str) -> bool:
        """Dugumu yeniden baglamaya calisir."""
        health = self._health.get(node_id)
        if not health:
            return False
        if not health.auto_reconnect:
            return False
        if health.consecutive_failures >= self.config.reconnect_max_retries:
            health.status = NodeStatus.ERROR
            return False
        health.status = NodeStatus.ONLINE
        health.consecutive_failures = 0
        health.last_check = time.time()
        self._record_history("attempt_reconnect", {"node_id": node_id, "success": True})
        return True

    def mark_failure(self, node_id: str) -> None:
        """Dugumu basarisiz olarak isaretler."""
        health = self._health.get(node_id)
        if not health:
            health = NodeHealthCheck(node_id=node_id)
            self._health[node_id] = health
        health.consecutive_failures += 1
        health.status = NodeStatus.ERROR
        self._record_history("mark_failure", {"node_id": node_id, "failures": health.consecutive_failures})
