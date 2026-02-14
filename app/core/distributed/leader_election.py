"""ATLAS Lider Secimi modulu.

Bully algoritmasi, Raft konsensus,
lider heartbeat, failover isleme
ve split-brain onleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LeaderElection:
    """Lider secimi yoneticisi.

    Dagitik sistemde lider secimi saglar.

    Attributes:
        _nodes: Dugum listesi.
        _leader_id: Mevcut lider ID.
    """

    def __init__(
        self,
        node_id: str = "node_0",
        heartbeat_interval: int = 5,
    ) -> None:
        """Lider secimini baslatir.

        Args:
            node_id: Bu dugumun ID'si.
            heartbeat_interval: Heartbeat suresi (sn).
        """
        self._node_id = node_id
        self._heartbeat_interval = heartbeat_interval
        self._nodes: dict[
            str, dict[str, Any]
        ] = {}
        self._leader_id: str | None = None
        self._term: int = 0
        self._votes: dict[str, str] = {}
        self._heartbeats: dict[
            str, float
        ] = {}
        self._election_history: list[
            dict[str, Any]
        ] = []

        # Kendini kaydet
        self._nodes[node_id] = {
            "node_id": node_id,
            "priority": 0,
            "status": "active",
            "joined_at": time.time(),
        }

        logger.info(
            "LeaderElection baslatildi: %s",
            node_id,
        )

    def add_node(
        self,
        node_id: str,
        priority: int = 0,
    ) -> dict[str, Any]:
        """Dugum ekler.

        Args:
            node_id: Dugum ID.
            priority: Oncelik.

        Returns:
            Dugum bilgisi.
        """
        node = {
            "node_id": node_id,
            "priority": priority,
            "status": "active",
            "joined_at": time.time(),
        }
        self._nodes[node_id] = node
        self._heartbeats[node_id] = time.time()
        return node

    def remove_node(
        self,
        node_id: str,
    ) -> bool:
        """Dugumu kaldirir.

        Args:
            node_id: Dugum ID.

        Returns:
            Basarili mi.
        """
        if node_id in self._nodes:
            del self._nodes[node_id]
            self._heartbeats.pop(node_id, None)
            if self._leader_id == node_id:
                self._leader_id = None
            return True
        return False

    def elect_bully(self) -> dict[str, Any]:
        """Bully algoritmasi ile secer.

        Returns:
            Secim sonucu.
        """
        self._term += 1
        active = [
            n for n in self._nodes.values()
            if n["status"] == "active"
        ]
        if not active:
            return {
                "term": self._term,
                "leader": None,
                "algorithm": "bully",
            }

        # En yuksek oncelikli (ayni ise ID'ye gore)
        winner = max(
            active,
            key=lambda n: (
                n["priority"],
                n["node_id"],
            ),
        )
        self._leader_id = winner["node_id"]

        record = {
            "term": self._term,
            "leader": self._leader_id,
            "algorithm": "bully",
            "candidates": len(active),
            "timestamp": time.time(),
        }
        self._election_history.append(record)
        return record

    def elect_raft(self) -> dict[str, Any]:
        """Raft konsensus ile secer.

        Returns:
            Secim sonucu.
        """
        self._term += 1
        active = [
            nid for nid, n in self._nodes.items()
            if n["status"] == "active"
        ]
        if not active:
            return {
                "term": self._term,
                "leader": None,
                "algorithm": "raft",
            }

        # Oy toplama
        self._votes.clear()
        quorum = len(active) // 2 + 1

        # Bu dugum aday olur
        candidate = self._node_id
        vote_count = 0
        for nid in active:
            # Basit: her dugum adaya oy verir
            self._votes[nid] = candidate
            vote_count += 1

        if vote_count >= quorum:
            self._leader_id = candidate
        else:
            self._leader_id = None

        record = {
            "term": self._term,
            "leader": self._leader_id,
            "algorithm": "raft",
            "votes": vote_count,
            "quorum": quorum,
            "timestamp": time.time(),
        }
        self._election_history.append(record)
        return record

    def heartbeat(
        self,
        node_id: str,
    ) -> bool:
        """Heartbeat alir.

        Args:
            node_id: Dugum ID.

        Returns:
            Gecerli mi.
        """
        if node_id in self._nodes:
            self._heartbeats[node_id] = time.time()
            return True
        return False

    def check_leader_health(
        self,
    ) -> dict[str, Any]:
        """Lider sagligini kontrol eder.

        Returns:
            Kontrol sonucu.
        """
        if not self._leader_id:
            return {
                "healthy": False,
                "reason": "no_leader",
            }

        last_hb = self._heartbeats.get(
            self._leader_id, 0,
        )
        elapsed = time.time() - last_hb
        healthy = (
            elapsed < self._heartbeat_interval * 3
        )

        if not healthy:
            self._nodes[self._leader_id][
                "status"
            ] = "suspect"

        return {
            "leader": self._leader_id,
            "healthy": healthy,
            "last_heartbeat_ago": round(
                elapsed, 2,
            ),
        }

    def detect_split_brain(
        self,
    ) -> dict[str, Any]:
        """Split-brain tespit eder.

        Returns:
            Tespit sonucu.
        """
        active = [
            nid for nid, n in self._nodes.items()
            if n["status"] == "active"
        ]
        total = len(self._nodes)
        quorum = total // 2 + 1
        has_quorum = len(active) >= quorum

        return {
            "active_nodes": len(active),
            "total_nodes": total,
            "quorum_needed": quorum,
            "has_quorum": has_quorum,
            "split_brain_risk": not has_quorum,
        }

    def failover(self) -> dict[str, Any]:
        """Failover uygular.

        Returns:
            Failover sonucu.
        """
        old_leader = self._leader_id
        if old_leader and old_leader in self._nodes:
            self._nodes[old_leader][
                "status"
            ] = "failed"

        result = self.elect_bully()
        return {
            "old_leader": old_leader,
            "new_leader": result["leader"],
            "term": result["term"],
        }

    @property
    def leader_id(self) -> str | None:
        """Mevcut lider."""
        return self._leader_id

    @property
    def term(self) -> int:
        """Mevcut donem."""
        return self._term

    @property
    def node_count(self) -> int:
        """Dugum sayisi."""
        return len(self._nodes)

    @property
    def election_count(self) -> int:
        """Secim sayisi."""
        return len(self._election_history)
