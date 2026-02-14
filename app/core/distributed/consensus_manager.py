"""ATLAS Konsensus Yoneticisi modulu.

Oylama protokolleri, quorum hesaplama,
anlasma saglama, catisma cozumu
ve Bizans hata toleransi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ConsensusManager:
    """Konsensus yoneticisi.

    Dagitik konsensus saglar.

    Attributes:
        _nodes: Katilimci dugumler.
        _proposals: Teklifler.
    """

    def __init__(self) -> None:
        """Konsensus yoneticisini baslatir."""
        self._nodes: dict[
            str, dict[str, Any]
        ] = {}
        self._proposals: list[
            dict[str, Any]
        ] = []
        self._decisions: list[
            dict[str, Any]
        ] = []

        logger.info(
            "ConsensusManager baslatildi",
        )

    def add_node(
        self,
        node_id: str,
        weight: float = 1.0,
    ) -> dict[str, Any]:
        """Dugum ekler.

        Args:
            node_id: Dugum ID.
            weight: Oy agirligi.

        Returns:
            Dugum bilgisi.
        """
        node = {
            "node_id": node_id,
            "weight": weight,
            "active": True,
            "votes_cast": 0,
        }
        self._nodes[node_id] = node
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
            return True
        return False

    def calculate_quorum(
        self,
        quorum_type: str = "majority",
    ) -> dict[str, Any]:
        """Quorum hesaplar.

        Args:
            quorum_type: Quorum tipi.

        Returns:
            Quorum bilgisi.
        """
        active = [
            n for n in self._nodes.values()
            if n["active"]
        ]
        total = len(active)

        if quorum_type == "majority":
            needed = total // 2 + 1
        elif quorum_type == "unanimity":
            needed = total
        elif quorum_type == "byzantine":
            # f hata icin 3f+1 gerekir
            f = (total - 1) // 3
            needed = 2 * f + 1
        else:
            needed = total // 2 + 1

        return {
            "type": quorum_type,
            "total_nodes": total,
            "needed": needed,
            "achievable": total >= needed,
        }

    def propose(
        self,
        proposal_id: str,
        value: Any,
        proposer: str = "",
    ) -> dict[str, Any]:
        """Teklif yapar.

        Args:
            proposal_id: Teklif ID.
            value: Teklif degeri.
            proposer: Teklif sahibi.

        Returns:
            Teklif bilgisi.
        """
        proposal = {
            "proposal_id": proposal_id,
            "value": value,
            "proposer": proposer,
            "votes_for": [],
            "votes_against": [],
            "status": "pending",
            "timestamp": time.time(),
        }
        self._proposals.append(proposal)
        return {
            "proposal_id": proposal_id,
            "status": "pending",
        }

    def vote(
        self,
        proposal_id: str,
        node_id: str,
        approve: bool = True,
    ) -> dict[str, Any]:
        """Oy verir.

        Args:
            proposal_id: Teklif ID.
            node_id: Oylayan dugum.
            approve: Onay mi.

        Returns:
            Oy sonucu.
        """
        proposal = self._find_proposal(
            proposal_id,
        )
        if not proposal:
            return {
                "status": "error",
                "reason": "proposal_not_found",
            }

        node = self._nodes.get(node_id)
        if not node or not node["active"]:
            return {
                "status": "error",
                "reason": "invalid_node",
            }

        # Cift oy kontrolu
        all_voters = (
            proposal["votes_for"]
            + proposal["votes_against"]
        )
        if node_id in all_voters:
            return {
                "status": "error",
                "reason": "already_voted",
            }

        if approve:
            proposal["votes_for"].append(node_id)
        else:
            proposal["votes_against"].append(
                node_id,
            )

        node["votes_cast"] += 1

        return {
            "proposal_id": proposal_id,
            "node_id": node_id,
            "vote": "for" if approve else "against",
            "total_for": len(
                proposal["votes_for"],
            ),
            "total_against": len(
                proposal["votes_against"],
            ),
        }

    def check_consensus(
        self,
        proposal_id: str,
        consensus_type: str = "majority",
    ) -> dict[str, Any]:
        """Konsensus kontrol eder.

        Args:
            proposal_id: Teklif ID.
            consensus_type: Konsensus tipi.

        Returns:
            Kontrol sonucu.
        """
        proposal = self._find_proposal(
            proposal_id,
        )
        if not proposal:
            return {
                "status": "error",
                "reason": "proposal_not_found",
            }

        quorum = self.calculate_quorum(
            consensus_type,
        )
        votes_for = len(proposal["votes_for"])
        votes_against = len(
            proposal["votes_against"],
        )
        needed = quorum["needed"]

        if votes_for >= needed:
            proposal["status"] = "accepted"
            self._decisions.append({
                "proposal_id": proposal_id,
                "value": proposal["value"],
                "decision": "accepted",
                "votes_for": votes_for,
                "votes_against": votes_against,
                "timestamp": time.time(),
            })
            return {
                "proposal_id": proposal_id,
                "reached": True,
                "decision": "accepted",
                "votes_for": votes_for,
            }

        if votes_against >= needed:
            proposal["status"] = "rejected"
            self._decisions.append({
                "proposal_id": proposal_id,
                "value": proposal["value"],
                "decision": "rejected",
                "votes_for": votes_for,
                "votes_against": votes_against,
                "timestamp": time.time(),
            })
            return {
                "proposal_id": proposal_id,
                "reached": True,
                "decision": "rejected",
                "votes_against": votes_against,
            }

        return {
            "proposal_id": proposal_id,
            "reached": False,
            "votes_for": votes_for,
            "votes_against": votes_against,
            "needed": needed,
        }

    def resolve_conflict(
        self,
        values: list[Any],
        strategy: str = "latest",
    ) -> dict[str, Any]:
        """Catisma cozer.

        Args:
            values: Catisan degerler.
            strategy: Cozum stratejisi.

        Returns:
            Cozum sonucu.
        """
        if not values:
            return {
                "resolved": False,
                "reason": "no_values",
            }

        if strategy == "latest":
            winner = values[-1]
        elif strategy == "first":
            winner = values[0]
        elif strategy == "majority":
            # En cok tekrar eden
            counts: dict[str, int] = {}
            for v in values:
                key = str(v)
                counts[key] = counts.get(
                    key, 0,
                ) + 1
            winner_key = max(
                counts, key=counts.get,  # type: ignore[arg-type]
            )
            winner = next(
                v for v in values
                if str(v) == winner_key
            )
        else:
            winner = values[0]

        return {
            "resolved": True,
            "strategy": strategy,
            "winner": winner,
            "candidates": len(values),
        }

    def _find_proposal(
        self,
        proposal_id: str,
    ) -> dict[str, Any] | None:
        """Teklif bulur.

        Args:
            proposal_id: Teklif ID.

        Returns:
            Teklif veya None.
        """
        for p in self._proposals:
            if p["proposal_id"] == proposal_id:
                return p
        return None

    @property
    def node_count(self) -> int:
        """Dugum sayisi."""
        return len(self._nodes)

    @property
    def proposal_count(self) -> int:
        """Teklif sayisi."""
        return len(self._proposals)

    @property
    def decision_count(self) -> int:
        """Karar sayisi."""
        return len(self._decisions)
