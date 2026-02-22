"""Node Registry - cihaz dugum kayit modulu.

Cihaz dugumlerinin kaydi, eslesmesi ve yonetimi.
"""

import logging
import time
import uuid
from typing import Optional

from app.models.nodes_models import DeviceNode, NodeStatus, NodeType, NodesConfig

logger = logging.getLogger(__name__)


class NodeRegistry:
    """Cihaz dugumlerini kaydeden ve yoneten sinif."""

    def __init__(self, config: Optional[NodesConfig] = None) -> None:
        """NodeRegistry baslatici."""
        self.config = config or NodesConfig()
        self._nodes: dict[str, DeviceNode] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina yeni bir giris ekler."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details or {}})

    def get_history(self) -> list[dict]:
        """Tum gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Kayit defteri istatistiklerini dondurur."""
        online = sum(1 for n in self._nodes.values() if n.status == NodeStatus.ONLINE)
        paired = sum(1 for n in self._nodes.values() if n.is_paired)
        return {"total_nodes": len(self._nodes), "online": online, "paired": paired}

    def register(self, node_id: str, node_type: NodeType, name: str = "") -> DeviceNode:
        """Yeni bir cihaz dugumu kaydeder."""
        if not node_id:
            node_id = str(uuid.uuid4())
        node = DeviceNode(node_id=node_id, name=name or node_id, node_type=node_type, status=NodeStatus.OFFLINE)
        self._nodes[node_id] = node
        self._record_history("register", {"node_id": node_id, "type": node_type.value})
        return node

    def unregister(self, node_id: str) -> bool:
        """Dugumu kayittan siler."""
        if node_id in self._nodes:
            del self._nodes[node_id]
            self._record_history("unregister", {"node_id": node_id})
            return True
        return False

    def pair(self, node_id: str) -> bool:
        """Dugumu eslestirilmis olarak isaretler."""
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.is_paired = True
        node.paired_at = time.time()
        node.status = NodeStatus.ONLINE
        self._record_history("pair", {"node_id": node_id})
        return True

    def unpair(self, node_id: str) -> bool:
        """Dugum eslesmesini kaldirir."""
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.is_paired = False
        node.paired_at = 0.0
        node.status = NodeStatus.OFFLINE
        self._record_history("unpair", {"node_id": node_id})
        return True

    def get(self, node_id: str) -> Optional[DeviceNode]:
        """Dugum bilgilerini dondurur."""
        return self._nodes.get(node_id)

    def list_nodes(self, node_type: Optional[NodeType] = None, status: Optional[NodeStatus] = None) -> list[DeviceNode]:
        """Dugumleri filtreler ve listeler."""
        nodes = list(self._nodes.values())
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]
        if status:
            nodes = [n for n in nodes if n.status == status]
        return nodes

    def update_heartbeat(self, node_id: str) -> bool:
        """Dugumun son gorulme zamanini gunceller."""
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.last_heartbeat = time.time()
        if node.is_paired and node.status != NodeStatus.ONLINE:
            node.status = NodeStatus.ONLINE
        return True

    def clear_pending(self) -> int:
        """Eslesmemis dugumleri temizler."""
        to_remove = [nid for nid, n in self._nodes.items() if not n.is_paired]
        for nid in to_remove:
            del self._nodes[nid]
        self._record_history("clear_pending", {"removed": len(to_remove)})
        return len(to_remove)

    def remove_all(self, confirm: bool = False) -> bool:
        """Tum dugumleri siler."""
        if not confirm:
            return False
        count = len(self._nodes)
        self._nodes.clear()
        self._record_history("remove_all", {"removed": count})
        return True
