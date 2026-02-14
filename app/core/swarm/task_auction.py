"""ATLAS Gorev Acik Artirma modulu.

Gorev yayinlama, teklif verme, kazanan secimi,
adil dagitim ve yetenek bazli teklif.
"""

import logging
from typing import Any

from app.models.swarm import AuctionRecord, AuctionState

logger = logging.getLogger(__name__)


class TaskAuction:
    """Gorev acik artirma sistemi.

    Gorevleri yayinlar, agent'lardan teklif alir
    ve en uygun agent'a atar.

    Attributes:
        _auctions: Acik artirmalar.
        _agent_wins: Agent kazanma sayilari.
        _agent_capabilities: Agent yetenekleri.
    """

    def __init__(self) -> None:
        """Acik artirma sistemini baslatir."""
        self._auctions: dict[str, AuctionRecord] = {}
        self._agent_wins: dict[str, int] = {}
        self._agent_capabilities: dict[str, list[str]] = {}

        logger.info("TaskAuction baslatildi")

    def register_agent(
        self,
        agent_id: str,
        capabilities: list[str],
    ) -> None:
        """Agent'i kaydeder.

        Args:
            agent_id: Agent ID.
            capabilities: Yetenekler.
        """
        self._agent_capabilities[agent_id] = capabilities

    def create_auction(
        self,
        task_id: str,
        description: str = "",
        required_capabilities: list[str] | None = None,
    ) -> AuctionRecord:
        """Acik artirma olusturur.

        Args:
            task_id: Gorev ID.
            description: Aciklama.
            required_capabilities: Gereken yetenekler.

        Returns:
            AuctionRecord nesnesi.
        """
        auction = AuctionRecord(
            task_id=task_id,
            task_description=description,
            state=AuctionState.OPEN,
            required_capabilities=required_capabilities or [],
        )
        self._auctions[auction.auction_id] = auction

        logger.info("Acik artirma: %s (%s)", task_id, auction.auction_id)
        return auction

    def place_bid(
        self,
        auction_id: str,
        agent_id: str,
        bid_score: float,
    ) -> bool:
        """Teklif verir.

        Args:
            auction_id: Artirma ID.
            agent_id: Agent ID.
            bid_score: Teklif puani (yuksek = daha istekli).

        Returns:
            Basarili ise True.
        """
        auction = self._auctions.get(auction_id)
        if not auction or auction.state not in (AuctionState.OPEN, AuctionState.BIDDING):
            return False

        # Yetenek kontrolu
        if auction.required_capabilities:
            agent_caps = self._agent_capabilities.get(agent_id, [])
            if not all(c in agent_caps for c in auction.required_capabilities):
                return False

        auction.bids[agent_id] = bid_score
        auction.state = AuctionState.BIDDING
        return True

    def close_auction(
        self,
        auction_id: str,
        fairness_weight: float = 0.3,
    ) -> str:
        """Acik artirmayi kapatir ve kazanani secer.

        Args:
            auction_id: Artirma ID.
            fairness_weight: Adillik agirligi (0-1).

        Returns:
            Kazanan agent ID.
        """
        auction = self._auctions.get(auction_id)
        if not auction or auction.state == AuctionState.CLOSED:
            return ""

        if not auction.bids:
            auction.state = AuctionState.CANCELLED
            return ""

        # Puanlama: bid_score + adillik bonusu
        scores: dict[str, float] = {}
        for agent_id, bid_score in auction.bids.items():
            wins = self._agent_wins.get(agent_id, 0)
            # Az kazanan agent'a bonus
            fairness_bonus = 1.0 / (1.0 + wins) * fairness_weight
            scores[agent_id] = bid_score + fairness_bonus

        winner = max(scores, key=scores.get)

        auction.winner_id = winner
        auction.state = AuctionState.AWARDED
        self._agent_wins[winner] = self._agent_wins.get(winner, 0) + 1

        logger.info("Artirma kazanani: %s -> %s", auction_id, winner)
        return winner

    def cancel_auction(self, auction_id: str) -> bool:
        """Acik artirmayi iptal eder.

        Args:
            auction_id: Artirma ID.

        Returns:
            Basarili ise True.
        """
        auction = self._auctions.get(auction_id)
        if not auction:
            return False

        auction.state = AuctionState.CANCELLED
        return True

    def get_auction(self, auction_id: str) -> AuctionRecord | None:
        """Artirma bilgisini getirir.

        Args:
            auction_id: Artirma ID.

        Returns:
            AuctionRecord veya None.
        """
        return self._auctions.get(auction_id)

    def get_open_auctions(self) -> list[AuctionRecord]:
        """Acik artirmalari getirir.

        Returns:
            AuctionRecord listesi.
        """
        return [
            a for a in self._auctions.values()
            if a.state in (AuctionState.OPEN, AuctionState.BIDDING)
        ]

    def get_agent_wins(self, agent_id: str) -> int:
        """Agent kazanma sayisini getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Kazanma sayisi.
        """
        return self._agent_wins.get(agent_id, 0)

    def get_statistics(self) -> dict[str, Any]:
        """Istatistikleri getirir.

        Returns:
            Istatistik sozlugu.
        """
        states: dict[str, int] = {}
        for a in self._auctions.values():
            states[a.state.value] = states.get(a.state.value, 0) + 1

        return {
            "total_auctions": len(self._auctions),
            "state_distribution": states,
            "registered_agents": len(self._agent_capabilities),
            "total_bids": sum(len(a.bids) for a in self._auctions.values()),
        }

    @property
    def total_auctions(self) -> int:
        """Toplam artirma sayisi."""
        return len(self._auctions)

    @property
    def open_auction_count(self) -> int:
        """Acik artirma sayisi."""
        return len(self.get_open_auctions())
